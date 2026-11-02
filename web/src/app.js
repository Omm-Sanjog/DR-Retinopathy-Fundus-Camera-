/* FundusScan Web - app logic. Everything runs in the browser; nothing is uploaded. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const nextFrame = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
  const pad = (n) => String(n).padStart(2, "0");

  // Same wording as device/server.py so the Pi and the phone give identical reports.
  const ACTIONS = {
    0: ["No referral needed", "Re-screen in 12 months. Maintain blood-sugar, blood-pressure and lipid control.", "routine"],
    1: ["No referral needed", "Re-screen in 6–12 months. Optimise diabetes control.", "routine"],
    2: ["Refer to an ophthalmologist", "Referable DR. Arrange an eye-specialist examination (non-urgent, within about 3 months).", "refer"],
    3: ["Refer to an ophthalmologist – urgent", "Severe non-proliferative DR. Arrange an eye-specialist examination within about 4 weeks.", "urgent"],
    4: ["Refer to an ophthalmologist – urgent", "Proliferative DR (sight-threatening). Arrange an eye-specialist examination within about 1 week.", "urgent"],
  };
  const FINDINGS = [
    "No visible abnormalities of diabetic retinopathy.",
    "Microaneurysms only.",
    "More than microaneurysms (haemorrhages, hard exudates or cotton-wool spots) but less than severe NPDR.",
    "Extensive intraretinal haemorrhages, venous beading or IRMA (4-2-1 rule) without proliferation.",
    "Neovascularisation and/or vitreous or pre-retinal haemorrhage.",
  ];
  const GRADE_ROWS = [
    ["0", "No DR", "No visible abnormalities.", "Re-screen in 12 months"],
    ["1", "Mild NPDR", "Microaneurysms only.", "Re-screen in 6–12 months"],
    ["2", "Moderate NPDR", "More than microaneurysms, less than severe.", "Refer (non-urgent)"],
    ["3", "Severe NPDR", "4-2-1 rule: haemorrhages, venous beading or IRMA.", "Refer urgently"],
    ["4", "Proliferative DR", "Neovascularisation, vitreous / pre-retinal haemorrhage.", "Refer urgently"],
  ];
  const LEVEL_LABEL = { routine: "No referral", refer: "Refer", urgent: "Urgent", ungradable: "Retake" };

  const S = { cfg: null, build: {}, model: null, modelReady: null, modelError: null, report: null, rev: null, lastSource: "live" };

  // ------------------------------------------------------------------ ui helpers
  let toastT;
  function toast(msg, ms = 2600) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("on");
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), ms);
  }
  function show(id) {
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === id));
    window.scrollTo(0, 0);
  }
  function busy(on, text = "", sub = "") {
    $("#busy").classList.toggle("on", on); $("#busyText").textContent = text; $("#busySub").textContent = sub;
  }
  function confirmTap(btn, msg, fn) {           // tap twice to confirm - no blocking dialogs
    if (btn.dataset.armed) { delete btn.dataset.armed; fn(); return; }
    btn.dataset.armed = "1"; toast(msg); setTimeout(() => delete btn.dataset.armed, 3000);
  }
  const sheet = (id, on) => { $(id).classList.toggle("on", on); $(id).setAttribute("aria-hidden", String(!on)); };
  $$(".sheet").forEach((s) => s.addEventListener("click", (e) => { if (e.target === s || e.target.closest("[data-close]")) sheet("#" + s.id, false); }));

  // ------------------------------------------------------------------ theme
  const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
                  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };
  const applyTheme = (t) => { if (t) document.documentElement.dataset.theme = t; };
  applyTheme(store.get("fundusscan-theme"));
  $("#btnTheme").onclick = () => {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    const t = dark ? "light" : "dark"; applyTheme(t); store.set("fundusscan-theme", t);
  };

  // ------------------------------------------------------------------ patient form
  const newId = () => { const d = new Date(); return `P-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`; };
  $("#pId").value = newId();
  $("#btnNewId").onclick = () => { $("#pId").value = newId(); $("#pAge").value = $("#pDia").value = $("#pNotes").value = ""; $$('.seg[data-name="sex"] button').forEach((b) => b.classList.remove("on")); toast("New patient"); };
  $$(".seg").forEach((seg) => seg.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const wasOn = b.classList.contains("on");
    seg.querySelectorAll("button").forEach((x) => x.classList.remove("on"));
    if (!(wasOn && seg.dataset.name === "sex")) b.classList.add("on");
  }));
  const segVal = (n) => $(`.seg[data-name="${n}"] button.on`)?.textContent || "";
  function patient() {
    return { id: $("#pId").value.trim() || newId(), age: $("#pAge").value.trim(), sex: segVal("sex"),
      eye: segVal("eye").startsWith("Left") ? "Left" : "Right", diabetes_years: $("#pDia").value.trim(), notes: $("#pNotes").value.trim() };
  }

  // ------------------------------------------------------------------ on-device storage (IndexedDB)
  const db = (() => {
    let p = null; const mem = new Map();
    const open = () => p || (p = new Promise((res, rej) => {
      const r = indexedDB.open("fundusscan", 1);
      r.onupgradeneeded = () => r.result.createObjectStore("scans", { keyPath: "id" });
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    }));
    const tx = async (mode, fn) => {
      const d = await open();
      return new Promise((res, rej) => { const t = d.transaction("scans", mode), st = t.objectStore("scans"), q = fn(st);
        t.oncomplete = () => res(q && q.result); t.onerror = () => rej(t.error); });
    };
    const safe = (f, fb) => async (...a) => { try { return await f(...a); } catch { return fb(...a); } };
    return {
      put: safe((r) => tx("readwrite", (s) => s.put(r)), (r) => mem.set(r.id, r)),
      get: safe((id) => tx("readonly", (s) => s.get(id)), (id) => mem.get(id)),
      all: safe(() => tx("readonly", (s) => s.getAll()), () => [...mem.values()]),
      del: safe((id) => tx("readwrite", (s) => s.delete(id)), (id) => mem.delete(id)),
      clear: safe(() => tx("readwrite", (s) => s.clear()), () => mem.clear()),
    };
  })();

  // ------------------------------------------------------------------ boot: config + model
  async function boot() {
    try {
      S.build = await (await fetch("build.json", { cache: "no-store" })).json();
    } catch { S.build = {}; }
    S.cfg = await (await fetch("config.json")).json();
    $("#buildInfo").textContent = `Build ${S.build.build || "dev"} · model ${S.cfg.model_name || "efficientnet_b0"} @ ${S.cfg.img_size}px · ONNX Runtime Web ${S.build.ort || ""}`;
    S.modelReady = loadModel();
  }

  async function loadModel() {
    const card = $("#modelCard"), dot = $("#modelDot"), text = $("#modelText"), sub = $("#modelSub"), bar = $("#modelBar");
    if (S.build.model === false) {
      S.modelError = "The AI model file is not included in this deployment.";
      dot.className = "dot fail"; text.textContent = "AI model not installed"; card.classList.add("ready");
      sub.textContent = "Add dr_model_fp32.onnx to device/models/ and redeploy. You can still check image quality.";
      return null;
    }
    try {
      const m = new Fundus.DRModel(S.cfg), total = S.build.modelBytes || 16e6;
      text.textContent = "Downloading the AI model…";
      await m.load(S.build.modelUrl || "models/dr_model_fp32.onnx", (got, t) => {
        const tt = t || total; bar.style.width = Math.min(100, (got / tt) * 100).toFixed(1) + "%";
        sub.textContent = `${(got / 1e6).toFixed(1)} / ${(tt / 1e6).toFixed(1)} MB · first time only, then it works offline`;
      }, S.build.ortBase || "ort/");
      text.textContent = "Starting the AI engine…";
      await m.predict({ w: 64, h: 64, d: new Uint8Array(64 * 64 * 3).fill(90) });   // warm-up
      S.model = m;
      dot.className = "dot ok"; card.classList.add("ready");
      text.textContent = "AI model ready · runs on this device";
      sub.textContent = `EfficientNet-B0 · ${S.cfg.img_size}×${S.cfg.img_size} · WebAssembly ×${m.threads} thread${m.threads > 1 ? "s" : ""} · works offline`;
      return m;
    } catch (e) {
      S.modelError = "The AI model could not be loaded: " + (e.message || e);
      dot.className = "dot fail"; card.classList.add("ready");
      text.textContent = "AI model failed to load"; sub.textContent = String(e.message || e);
      return null;
    }
  }

  // ------------------------------------------------------------------ live camera
  const L = { stream: null, track: null, running: false, torch: false, auto: true, win: null, best: null, timer: 0 };
  const video = $("#video"), overlay = $("#overlay");
  const small = document.createElement("canvas"), sctx = small.getContext("2d", { willReadFrequently: true });
  const cropC = document.createElement("canvas"), cctx = cropC.getContext("2d", { willReadFrequently: true });
  const bestC = document.createElement("canvas"), bctx = bestC.getContext("2d");

  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) { toast("Live camera needs HTTPS. Use the Camera app button instead.", 4000); return; }
    show("camera"); setChip("Starting camera…");
    try {
      L.stream = await navigator.mediaDevices.getUserMedia({ audio: false,
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } } });
    } catch (e) {
      show("home");
      toast(e.name === "NotAllowedError" ? "Camera permission was denied. Allow it in the browser settings." : "Could not open the camera: " + e.message, 4500);
      return;
    }
    L.track = L.stream.getVideoTracks()[0];
    video.srcObject = L.stream;
    await video.play().catch(() => {});
    const caps = L.track.getCapabilities ? L.track.getCapabilities() : {};
    $("#btnTorch").classList.toggle("hidden", !caps.torch);
    if (caps.focusMode && caps.focusMode.includes("continuous")) L.track.applyConstraints({ advanced: [{ focusMode: "continuous" }] }).catch(() => {});
    if (caps.zoom && caps.zoom.max > caps.zoom.min) {
      const z = $("#zoom"); z.min = caps.zoom.min; z.max = Math.min(caps.zoom.max, 5); z.step = caps.zoom.step || 0.1; z.value = caps.zoom.min;
      $("#zoomBox").classList.remove("hidden"); $("#zoomVal").textContent = (+z.value).toFixed(1) + "×";
    } else $("#zoomBox").classList.add("hidden");
    L.running = true; L.win = null; L.best = null; L.torch = false; $("#btnTorch").classList.remove("on");
    tick();
  }

  function stopCamera() {
    L.running = false; clearTimeout(L.timer);
    if (L.stream) L.stream.getTracks().forEach((t) => t.stop());
    L.stream = L.track = null; video.srcObject = null;
  }

  function setChip(text, ready = false) { const c = $("#camChip"); c.textContent = text; c.classList.toggle("ready", ready); }
  function setPill(k, st) { const p = $(`.pill[data-k="${k}"]`); p.className = "pill " + (st || ""); }
  function setProgress(f) { $("#prog").style.strokeDashoffset = String(289 * (1 - Math.max(0, Math.min(1, f)))); }

  function liveAnalyse() {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw) return null;
    const k = 160 / Math.max(vw, vh);
    small.width = Math.round(vw * k); small.height = Math.round(vh * k);
    sctx.drawImage(video, 0, 0, small.width, small.height);
    const c = Fundus.detectFundusCircle(Fundus.fromImageData(sctx.getImageData(0, 0, small.width, small.height)), S.cfg.fundus_rg_min);
    if (!c) return { found: false, vw, vh };
    const cv = { cx: c.cx / k, cy: c.cy / k, r: c.r / k }, side = 2 * cv.r, n = Math.max(32, Math.min(512, Math.round(side)));
    cropC.width = cropC.height = n;
    cctx.fillStyle = "#000"; cctx.fillRect(0, 0, n, n);
    cctx.drawImage(video, cv.cx - cv.r, cv.cy - cv.r, side, side, 0, 0, n, n);
    const img = Fundus.applyCircle(Fundus.fromImageData(cctx.getImageData(0, 0, n, n)), { cx: n / 2, cy: n / 2, r: n / 2 });
    const m = Fundus.qualityMetrics(img), rg = Fundus.fundusRatio(img), q = S.cfg.quality;
    const st = {
      retina: rg >= (S.cfg.fundus_rg_min ?? 1.6) ? "ok" : "fail",
      focus: m.sharpness >= 1.5 * q.sharpness_min ? "ok" : m.sharpness >= q.sharpness_min ? "warn" : "fail",
      light: m.brightness < q.brightness_min ? "fail" : m.brightness > q.brightness_max ? "fail" : "ok",
      size: side >= 384 ? "ok" : side >= 256 ? "warn" : "fail",
    };
    return { found: true, vw, vh, circle: cv, st, m, side, dark: m.brightness < q.brightness_min,
      ready: st.retina === "ok" && st.focus !== "fail" && st.light === "ok" && st.size !== "fail" };
  }

  function drawOverlay(a) {
    const dpr = devicePixelRatio || 1, w = overlay.clientWidth, h = overlay.clientHeight;
    if (overlay.width !== Math.round(w * dpr)) { overlay.width = Math.round(w * dpr); overlay.height = Math.round(h * dpr); }
    const ctx = overlay.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    if (!a || !a.vw) return;
    const sc = Math.min(w / a.vw, h / a.vh), ox = (w - a.vw * sc) / 2, oy = (h - a.vh * sc) / 2;
    if (!a.found) {                                            // guide ring in the centre
      ctx.setLineDash([8, 8]); ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(w / 2, h / 2, Math.min(a.vw, a.vh) * sc * 0.36, 0, 7); ctx.stroke(); return;
    }
    const c = a.circle, col = a.ready ? "#2BD08A" : a.st.retina === "ok" ? "#F2B13A" : "#FF6B5E";
    ctx.setLineDash(a.ready ? [] : [10, 8]); ctx.strokeStyle = col; ctx.lineWidth = a.ready ? 4 : 3;
    ctx.beginPath(); ctx.arc(ox + c.cx * sc, oy + c.cy * sc, c.r * sc, 0, 7); ctx.stroke();
  }

  function tick() {
    if (!L.running) return;
    let a = null;
    try { a = liveAnalyse(); } catch (e) { console.warn(e); }
    drawOverlay(a);
    const now = performance.now();
    if (a && a.found) {
      for (const k of ["retina", "focus", "light", "size"]) setPill(k, a.st[k]);
      if (a.ready) {
        if (!L.win) { L.win = { start: now }; L.best = null; }
        L.win.last = now;
        if (!L.best || a.m.sharpness > L.best.sharp) {             // keep the sharpest full-resolution frame
          bestC.width = a.vw; bestC.height = a.vh; bctx.drawImage(video, 0, 0); L.best = { sharp: a.m.sharpness };
        }
        const f = (now - L.win.start) / 1300;
        if (L.auto) { setProgress(f); setChip("Hold steady… capturing", true); if (f >= 1) { captureLive(true); return; } }
        else setChip("Ready — tap the button", true);
      } else {
        if (L.win && now - L.win.last > 600) { L.win = null; L.best = null; setProgress(0); }
        setChip(a.st.retina !== "ok" ? "Find the orange-red reflex in the lens"
          : a.st.light === "fail" ? (a.dark ? (L.torch ? "Too dark — dim the room less / bring closer" : "Too dark — turn on the torch") : "Too bright — tilt the lens slightly")
          : a.st.size === "fail" ? "Retina too small — move closer or zoom in"
          : "Move the phone slowly to focus the vessels");
      }
    } else {
      ["retina", "focus", "light", "size"].forEach((k) => setPill(k, ""));
      if (L.win && now - (L.win.last || 0) > 600) { L.win = null; L.best = null; setProgress(0); }
      setChip(video.videoWidth ? "Point the lens at the pupil — find the red reflex" : "Starting camera…");
    }
    L.timer = setTimeout(tick, 90);
  }

  function flash() { const f = $("#flash"); f.classList.add("on"); requestAnimationFrame(() => requestAnimationFrame(() => f.classList.remove("on"))); }

  function captureLive(useBest) {
    if (!video.videoWidth) return;
    flash();
    let src = bestC;
    if (!useBest || !L.best) { bestC.width = video.videoWidth; bestC.height = video.videoHeight; bctx.drawImage(video, 0, 0); }
    const img = Fundus.fromSource(src, 3000);
    stopCamera(); setProgress(0);
    openReview(img, "live");
  }

  $("#btnLive").onclick = startCamera;
  $("#btnCamClose").onclick = () => { stopCamera(); show("home"); };
  $("#btnCamHelp").onclick = () => sheet("#guideSheet", true);
  $("#btnShutter").onclick = () => captureLive(!!(L.win && L.best));
  $("#btnAuto").onclick = () => { L.auto = !L.auto; $("#btnAuto").classList.toggle("on", L.auto); setProgress(0); toast(L.auto ? "Auto-capture on" : "Auto-capture off — tap the button to capture"); };
  $("#btnTorch").onclick = async () => {
    if (!L.track) return;
    try { L.torch = !L.torch; await L.track.applyConstraints({ advanced: [{ torch: L.torch }] }); $("#btnTorch").classList.toggle("on", L.torch); }
    catch { L.torch = false; toast("Torch is not available on this phone/browser"); }
  };
  $("#zoom").oninput = (e) => { const v = +e.target.value; $("#zoomVal").textContent = v.toFixed(1) + "×"; L.track?.applyConstraints({ advanced: [{ zoom: v }] }).catch(() => {}); };
  document.addEventListener("visibilitychange", () => { if (document.hidden && L.running) { stopCamera(); show("home"); } });

  // ------------------------------------------------------------------ photo inputs
  async function fromFile(file, source) {
    if (!file) return;
    busy(true, "Opening photo…");
    try {
      const url = URL.createObjectURL(file), im = new Image(); im.src = url; await im.decode();
      const img = Fundus.fromSource(im, 3000); URL.revokeObjectURL(url);
      busy(false); openReview(img, source);
    } catch (e) { busy(false); toast("Could not open this image (" + (e.message || "unsupported format") + ")"); }
  }
  $("#inCamera").onchange = (e) => { fromFile(e.target.files[0], "camera-app"); e.target.value = ""; };
  $("#inGallery").onchange = (e) => { fromFile(e.target.files[0], "upload"); e.target.value = ""; };
  $("#btnSample").onclick = async () => {
    busy(true, "Loading sample…");
    const im = new Image(); im.src = "sample.png"; await im.decode(); busy(false);
    openReview(Fundus.fromSource(im), "sample");
  };

  // ------------------------------------------------------------------ review / crop
  const rc = $("#revCanvas");
  function openReview(img, source) {
    S.lastSource = source;
    const circle = Fundus.detectFundusCircle(img, S.cfg.fundus_rg_min);
    S.rev = { img, source, srcCanvas: Fundus.toCanvas(img), circle: circle || { cx: img.w / 2, cy: img.h / 2, r: 0.42 * Math.min(img.w, img.h) }, whole: false, auto: !!circle };
    const msg = $("#revMsg");
    msg.textContent = circle ? "Retina found. Adjust the circle if needed, then analyse." : "Retina not found automatically — drag the circle over it.";
    msg.classList.toggle("warn", !circle);
    $("#btnWhole").classList.remove("on");
    show("review");
    requestAnimationFrame(drawReview);
  }
  function revLayout() {
    const st = $(".rev-stage"), r = S.rev, maxW = st.clientWidth - 20, maxH = Math.max(200, st.clientHeight - 10);
    const sc = Math.min(maxW / r.img.w, maxH / r.img.h), dpr = devicePixelRatio || 1;
    rc.style.width = r.img.w * sc + "px"; rc.style.height = r.img.h * sc + "px";
    rc.width = Math.round(r.img.w * sc * dpr); rc.height = Math.round(r.img.h * sc * dpr);
    r.sc = sc * dpr;
  }
  function drawReview() {
    const r = S.rev; if (!r) return;
    revLayout();
    const ctx = rc.getContext("2d"), W = rc.width, H = rc.height;
    ctx.imageSmoothingQuality = "high"; ctx.drawImage(r.srcCanvas, 0, 0, W, H);
    const minDim = Math.min(r.img.w, r.img.h);
    $("#revSize").value = String((r.circle.r / minDim) * 100);
    $("#revSize").disabled = r.whole;
    if (r.whole) return;
    const cx = r.circle.cx * r.sc, cy = r.circle.cy * r.sc, rad = r.circle.r * r.sc;
    ctx.fillStyle = "rgba(0,0,0,.6)"; ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.arc(cx, cy, rad, 0, Math.PI * 2, true); ctx.fill();
    ctx.lineWidth = 3 * (devicePixelRatio || 1); ctx.strokeStyle = "#FF8A3D"; ctx.beginPath(); ctx.arc(cx, cy, rad, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = 1.5 * (devicePixelRatio || 1); ctx.strokeStyle = "rgba(255,255,255,.7)";
    ctx.beginPath(); ctx.moveTo(cx - 10, cy); ctx.lineTo(cx + 10, cy); ctx.moveTo(cx, cy - 10); ctx.lineTo(cx, cy + 10); ctx.stroke();
  }
  let drag = null;
  rc.addEventListener("pointerdown", (e) => {
    const r = S.rev; if (!r || r.whole) return;
    rc.setPointerCapture(e.pointerId);
    const k = (devicePixelRatio || 1) / r.sc;
    drag = { x: e.offsetX * k, y: e.offsetY * k, cx: r.circle.cx, cy: r.circle.cy };
  });
  rc.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const r = S.rev, k = (devicePixelRatio || 1) / r.sc;
    r.circle.cx = Math.max(0, Math.min(r.img.w, drag.cx + e.offsetX * k - drag.x));
    r.circle.cy = Math.max(0, Math.min(r.img.h, drag.cy + e.offsetY * k - drag.y));
    drawReview();
  });
  ["pointerup", "pointercancel"].forEach((t) => rc.addEventListener(t, () => (drag = null)));
  $("#revSize").oninput = (e) => { const r = S.rev; r.circle.r = (+e.target.value / 100) * Math.min(r.img.w, r.img.h); drawReview(); };
  $("#btnAutoCircle").onclick = () => {
    const r = S.rev, c = Fundus.detectFundusCircle(r.img, S.cfg.fundus_rg_min);
    if (c) { r.circle = c; r.whole = false; $("#btnWhole").classList.remove("on"); drawReview(); toast("Retina circle detected"); }
    else toast("No retina found automatically — position the circle by hand");
  };
  $("#btnWhole").onclick = () => { const r = S.rev; r.whole = !r.whole; $("#btnWhole").classList.toggle("on", r.whole); drawReview(); };
  $("#btnRetake").onclick = $("#btnRevBack").onclick = () => retake();
  window.addEventListener("resize", () => { if ($("#review").classList.contains("active")) drawReview(); });
  function retake() {
    S.rev = null;
    if (S.lastSource === "live") startCamera();
    else if (S.lastSource === "camera-app") { show("home"); $("#inCamera").click(); }
    else show("home");
  }

  // ------------------------------------------------------------------ analysis
  const toJpeg = (img, q = 0.9) => Fundus.toCanvas(img).toDataURL("image/jpeg", q);
  function makeId() { const d = new Date(); return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}-${Math.random().toString(16).slice(2, 6)}`; }

  $("#btnAnalyse").onclick = async () => {
    const r = S.rev; if (!r) return;
    if (S.modelReady && !S.model && !S.modelError) { busy(true, "Waiting for the AI model…", "It downloads once, then stays on this phone."); await S.modelReady; }
    busy(true, "Analysing…", "Checking image quality and grading on this phone");
    await nextFrame(); await nextFrame();
    try {
      const t0 = performance.now(), cfg = S.cfg;
      const rgb = r.whole ? r.img : Fundus.applyCircle(r.img, r.circle);
      const q = Fundus.qualityChecks(rgb, cfg);
      let result = null, enhanced;
      if (S.model) {
        const p = await S.model.predict(rgb);
        enhanced = p.enhanced;
        const margin = Math.min(...cfg.thresholds.map((t) => Math.abs(p.raw_score - t)));
        const [title, advice, level] = ACTIONS[p.grade], gradable = q.overall !== "fail";
        result = { grade: p.grade, grade_name: cfg.grades[p.grade], score: p.score, referable: p.referable,
          confidence: margin < 0.15 ? "Borderline" : margin < 0.35 ? "Moderate" : "High", gradable,
          action: gradable ? title : "Image not gradable – retake",
          advice: gradable ? advice : "The photo did not pass the quality checks, so the grade is not reliable. Retake the image; if three attempts fail, refer for a full eye examination.",
          level: gradable ? level : "ungradable", findings: FINDINGS[p.grade], inference_ms: p.inference_ms };
      } else enhanced = Fundus.preprocessFundus(rgb, cfg.img_size);
      const fundus = Fundus.resizeArea(Fundus.padToSquare(Fundus.cropFundus(rgb)), 768, 768);
      const report = {
        id: makeId(), time: new Date().toISOString(), source: r.source, patient: patient(), result,
        model_error: S.model ? null : (S.modelError || "AI model not loaded"),
        quality: { overall: q.overall, checks: q.checks },
        crop: r.whole ? "whole image" : "retina circle",
        model: { name: "EfficientNet-B0 (regression)", file: S.model ? S.model.file : null, input: `${cfg.img_size}×${cfg.img_size}`,
          thresholds: cfg.thresholds, trained_on: cfg.data || "APTOS 2019", test_metrics: cfg.metrics_test || {},
          runtime: S.model ? `ONNX Runtime Web ${S.build.ort || ""} · WebAssembly ×${S.model.threads}` : "—",
          total_ms: Math.round(performance.now() - t0) },
        images: { fundus: toJpeg(fundus, 0.9), enhanced: toJpeg(enhanced, 0.92) },
        thumb: toJpeg(Fundus.resizeArea(fundus, 160, 160), 0.8),
      };
      await db.put(report);
      S.rev = null; busy(false);
      openReport(report);
    } catch (e) { busy(false); console.error(e); toast("Analysis failed: " + (e.message || e), 5000); }
  };

  // ------------------------------------------------------------------ report
  function openReport(r) { S.report = r; renderReport(r); show("report"); }

  function renderReport(r) {
    const p = r.patient || {}, res = r.result, q = r.quality, m = r.model, t0 = m.test_metrics || {}, t = new Date(r.time);
    const tm = { qwk: t0.qwk, sens: t0.referable_sensitivity ?? t0.sensitivity, spec: t0.referable_specificity ?? t0.specificity, auc: t0.referable_auc ?? t0.auc };
    const level = res ? res.level : "ungradable", th = m.thresholds, edges = [-0.5, ...th, 4.5], span = 5;
    const cols = edges.slice(1).map((e, i) => (((e - edges[i]) / span) * 100).toFixed(2) + "%").join(" ");
    const pos = res ? Math.min(Math.max(((res.score + 0.5) / span) * 100, 1), 99) : 0;
    const src = { live: "Phone · lens camera", "camera-app": "Phone · camera app", upload: "Saved photo", sample: "Sample image" }[r.source] || r.source;
    document.title = `DR report ${p.id || ""}`;
    $("#repBody").innerHTML = `
    <div class="paper">
      <header class="rh"><img src="icon.svg" alt="">
        <div><h1>Diabetic Retinopathy Screening Report</h1><div class="sub">FundusScan Web · AI fundus screening prototype · KIIT School of Electronics Engineering</div></div>
        <div class="meta"><span>Report <b>${esc(r.id)}</b></span><br><span>${t.toLocaleDateString()} ${t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></div>
      </header>
      <h2>Patient &amp; examination</h2>
      <div class="grid">
        <div><small>Patient ID</small><span>${esc(p.id) || "—"}</span></div>
        <div><small>Age</small><span>${esc(p.age) || "—"}</span></div>
        <div><small>Sex</small><span>${esc(p.sex) || "—"}</span></div>
        <div><small>Eye</small><span>${p.eye === "Left" ? "Left (OS)" : "Right (OD)"}</span></div>
        <div><small>Diabetes duration</small><span>${p.diabetes_years ? esc(p.diabetes_years) + " years" : "—"}</span></div>
        <div><small>Image source</small><span>${esc(src)}</span></div>
        <div><small>Image quality</small><span class="st ${q.overall}">${{ ok: "Good", warn: "Acceptable", fail: "Not gradable" }[q.overall]}</span></div>
        <div><small>Analysis time</small><span class="num">${(m.total_ms / 1000).toFixed(1)} s</span></div>
      </div>
      ${res ? `
      <div class="result ${level}">
        <div class="grade">Grade ${res.grade} — ${esc(res.grade_name)}</div>
        <div class="action">${esc(res.action)}</div>
        <div class="tags"><span>Referable DR: ${res.gradable ? (res.referable ? "YES" : "NO") : "—"}</span><span>Confidence: ${esc(res.confidence)}</span></div>
        <div class="advice">${esc(res.advice)}</div>
      </div>
      <div class="scale"><div class="barwrap"><div class="sbar" style="--cols:${cols}">
        ${["No DR", "Mild", "Moderate", "Severe", "Prolif."].map((n, i) => `<div style="background:var(--g${i})">${n}</div>`).join("")}
      </div><span class="marker ${pos < 12 ? "l" : pos > 88 ? "r" : ""}" style="left:${pos}%" data-l="▲ score ${res.score.toFixed(2)}"></span></div></div>`
      : `<div class="result ungradable"><div class="grade">No grade</div><div class="action">AI model not available</div><div class="advice">${esc(r.model_error || "")} The image-quality checks below are still valid.</div></div>`}
      <h2>Images</h2>
      <div class="imgs">
        <figure><img src="${r.images.fundus}" alt="Captured fundus"><figcaption>Captured fundus (${esc(r.crop)})</figcaption></figure>
        <figure><img src="${r.images.enhanced}" alt="Enhanced fundus"><figcaption>Enhanced view analysed by the AI (${esc(m.input)})</figcaption></figure>
      </div>
      <div class="two">
        <div><h2>Image quality checks</h2>
          <table><tr><th>Check</th><th>Value</th><th>Result</th></tr>
          ${q.checks.map((c) => `<tr><td>${esc(c.name)}<span class="hint">${esc(c.text)}</span></td><td class="num">${esc(c.value)}</td><td><span class="st ${c.status}">${{ ok: "Pass", warn: "Caution", fail: "Fail" }[c.status]}</span></td></tr>`).join("")}
          </table></div>
        <div><h2>Grading scale (ICDR)</h2>
          <table><tr><th>Grade</th><th>Findings</th><th>Action</th></tr>
          ${GRADE_ROWS.map((g) => `<tr class="${res && String(res.grade) === g[0] ? "cur" : ""}"><td>${g[0]} · ${g[1]}</td><td>${g[2]}</td><td>${g[3]}</td></tr>`).join("")}
          </table></div>
      </div>
      <h2>Method</h2>
      <table>
        <tr><td class="k">AI model</td><td>${esc(m.name)} · input ${esc(m.input)} · ${esc(m.file || "not loaded")}</td></tr>
        <tr><td class="k">Runs on</td><td>This device, offline — ${esc(m.runtime)}. The photo was not uploaded.</td></tr>
        <tr><td class="k">Training data</td><td>${esc(m.trained_on)} (3,662 graded fundus images)</td></tr>
        <tr><td class="k">Test performance (APTOS hold-out)</td><td>QWK ${tm.qwk ?? "—"} · referable-DR sensitivity ${tm.sens ? (tm.sens * 100).toFixed(1) + " %" : "—"} · specificity ${tm.spec ? (tm.spec * 100).toFixed(1) + " %" : "—"} · AUC ${tm.auc ?? "—"}</td></tr>
        <tr><td class="k">Grade thresholds</td><td class="num">${th.map((v) => v.toFixed(2)).join(" · ")}${res ? ` · model score ${res.score.toFixed(3)} · inference ${Math.round(res.inference_ms)} ms` : ""}</td></tr>
        ${p.notes ? `<tr><td class="k">Operator notes</td><td>${esc(p.notes)}</td></tr>` : ""}
      </table>
      <div class="note"><b>Screening aid — not a medical diagnosis.</b> Produced by a research prototype that has not been clinically validated. The model was trained on clinic fundus-camera images; phone images through a lens kit can differ, so results must be confirmed by an eye-care professional. It grades diabetic retinopathy only and does not detect other eye diseases. Anyone with visual symptoms should be referred regardless of this result.</div>
      <div class="sign"><div>Screened by (name &amp; signature)</div><div>Reviewed by ophthalmologist</div></div>
      <footer><span>FundusScan · github.com/Omm-Sanjog/DR-Retinopathy-Fundus-Camera-</span><span>Generated ${new Date().toLocaleString()}</span></footer>
    </div>
    <div class="rep-actions no-print"><button id="raRetake">Retake</button><button class="primary" id="raNew">New patient</button></div>`;
    $("#raRetake").onclick = () => retake();
    $("#raNew").onclick = () => { $("#btnNewId").click(); show("home"); };
  }

  $("#btnNewScan").onclick = () => show("home");
  $("#btnPrint").onclick = () => window.print();
  $("#btnDelete").onclick = (e) => confirmTap(e.currentTarget, "Tap delete again to remove this report", async () => {
    await db.del(S.report.id); S.report = null; toast("Report deleted"); show("home");
  });

  // share: a PNG summary card (works well in WhatsApp) + text
  function wrap(ctx, text, x, y, maxW, lh) {
    const words = String(text).split(" "); let line = "";
    for (const w of words) {
      const t = line ? line + " " + w : w;
      if (ctx.measureText(t).width > maxW && line) { ctx.fillText(line, x, y); y += lh; line = w; } else line = t;
    }
    if (line) { ctx.fillText(line, x, y); y += lh; }
    return y;
  }
  async function shareCard(r) {
    await document.fonts.ready;
    const W = 1080, H = 1500, c = document.createElement("canvas"); c.width = W; c.height = H;
    const ctx = c.getContext("2d"), res = r.result, p = r.patient;
    const col = { routine: "#1F8A5B", refer: "#B07216", urgent: "#C0392B", ungradable: "#6B7686" }[res ? res.level : "ungradable"];
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#1F3864"; ctx.fillRect(0, 0, W, 170);
    ctx.fillStyle = "#fff"; ctx.font = "700 58px 'Barlow SC', Barlow, sans-serif"; ctx.fillText("FundusScan", 60, 92);
    ctx.font = "500 30px Barlow, sans-serif"; ctx.fillText("Diabetic retinopathy screening", 60, 138);
    ctx.textAlign = "right"; ctx.font = "500 28px Barlow, sans-serif"; ctx.fillText(new Date(r.time).toLocaleString(), W - 60, 92);
    ctx.textAlign = "left"; ctx.fillStyle = "#152030"; ctx.font = "600 36px Barlow, sans-serif";
    ctx.fillText([p.id, p.eye === "Left" ? "Left eye (OS)" : "Right eye (OD)", p.age && `${p.age} y`, p.sex].filter(Boolean).join("  ·  "), 60, 240);
    const im = new Image(); im.src = r.images.fundus; await im.decode();
    ctx.save(); ctx.beginPath(); ctx.arc(W / 2, 560, 270, 0, 7); ctx.clip(); ctx.drawImage(im, W / 2 - 270, 290, 540, 540); ctx.restore();
    ctx.fillStyle = col; ctx.beginPath(); ctx.roundRect(60, 870, W - 120, 250, 28); ctx.fill();
    ctx.fillStyle = "#fff"; ctx.font = "700 64px 'Barlow SC', Barlow, sans-serif";
    ctx.fillText(res ? `Grade ${res.grade} — ${res.grade_name}` : "No grade (model not loaded)", 100, 960);
    ctx.font = "700 40px 'Barlow SC', Barlow, sans-serif"; ctx.fillText(res ? res.action : "Image-quality check only", 100, 1020);
    ctx.font = "500 30px Barlow, sans-serif";
    ctx.fillText(res ? `Referable DR: ${res.gradable ? (res.referable ? "YES" : "NO") : "—"}   ·   Confidence: ${res.confidence}` : "", 100, 1080);
    ctx.fillStyle = "#152030"; ctx.font = "500 34px Barlow, sans-serif";
    let y = wrap(ctx, res ? res.advice : r.model_error || "", 60, 1190, W - 120, 46);
    ctx.fillStyle = "#4A5668"; ctx.font = "500 28px Barlow, sans-serif";
    y = wrap(ctx, `Image quality: ${{ ok: "Good", warn: "Acceptable", fail: "Not gradable" }[r.quality.overall]}  ·  Report ${r.id}`, 60, y + 16, W - 120, 40);
    ctx.fillStyle = "#7B8696"; ctx.font = "500 24px Barlow, sans-serif";
    wrap(ctx, "AI screening aid from a research prototype — not a medical diagnosis. Confirm with an eye-care professional.", 60, H - 70, W - 120, 32);
    return new Promise((ok) => c.toBlob(ok, "image/png"));
  }
  $("#btnShare").onclick = async () => {
    const r = S.report; if (!r) return;
    const res = r.result, text = `FundusScan screening — ${r.patient.id} (${r.patient.eye} eye)\n` +
      (res ? `Grade ${res.grade} – ${res.grade_name}: ${res.action}\n${res.advice}\n` : "Image-quality check only (AI model not loaded)\n") +
      "AI screening aid, not a medical diagnosis.";
    try {
      const blob = await shareCard(r), file = new File([blob], `fundusscan-${r.id}.png`, { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], title: "FundusScan report", text }); return; }
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = file.name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      try { await navigator.clipboard.writeText(text); toast("Summary image saved · text copied"); } catch { toast("Summary image saved"); }
    } catch (e) { if (e.name !== "AbortError") toast("Sharing failed: " + e.message); }
  };

  // ------------------------------------------------------------------ history
  async function renderHistory() {
    const list = (await db.all()).sort((a, b) => (a.id < b.id ? 1 : -1)), el = $("#historyList");
    if (!list.length) { el.innerHTML = `<div class="empty">No scans on this device yet.</div>`; return; }
    el.innerHTML = list.map((r) => {
      const lv = r.result ? r.result.level : "ungradable", t = new Date(r.time);
      return `<button class="hist-item" data-id="${esc(r.id)}"><img src="${r.thumb}" alt="">
        <span><b>${esc(r.patient.id)} · ${r.patient.eye === "Left" ? "OS" : "OD"}</b>
        <small>${t.toLocaleDateString()} ${t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}${r.result ? ` · Grade ${r.result.grade}` : ""}</small></span>
        <span class="lvl ${lv}">${LEVEL_LABEL[lv]}</span></button>`;
    }).join("");
  }
  $("#btnHistory").onclick = async () => { await renderHistory(); sheet("#historySheet", true); };
  $("#historyList").onclick = async (e) => {
    const b = e.target.closest(".hist-item"); if (!b) return;
    const r = await db.get(b.dataset.id); if (!r) return;
    sheet("#historySheet", false); openReport(r);
  };
  $("#btnClearAll").onclick = (e) => confirmTap(e.currentTarget, "Tap again to delete ALL scans on this device", async () => { await db.clear(); renderHistory(); toast("All scans deleted"); });
  $("#btnGuide").onclick = () => sheet("#guideSheet", true);

  // ------------------------------------------------------------------ install / offline
  let installEvt = null;
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent), standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); installEvt = e; $("#btnInstall").classList.remove("hidden"); });
  if (isIOS && !standalone) { $("#btnInstall").classList.remove("hidden"); $("#btnInstall").textContent = "Add to Home Screen"; }
  $("#btnInstall").onclick = async () => {
    if (installEvt) { installEvt.prompt(); await installEvt.userChoice; installEvt = null; $("#btnInstall").classList.add("hidden"); }
    else toast("Tap the Share button, then “Add to Home Screen”", 4500);
  };
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }

  boot().catch((e) => { $("#modelText").textContent = "Could not start: " + e.message; $("#modelDot").className = "dot fail"; });
  window.FundusScanApp = { S, openReview, openReport, db };   // handy for debugging
})();
