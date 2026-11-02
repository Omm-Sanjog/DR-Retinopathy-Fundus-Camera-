/* FundusScan Web - image pipeline + model, a line-by-line port of device/pi_inference.py.
 *
 * Images are plain objects {w, h, d} where d is a Uint8Array of RGB bytes (row-major, 3 per pixel).
 * Every OpenCV call used on the Pi is re-implemented here with the same maths
 * (RGB2GRAY fixed-point weights, INTER_AREA, INTER_LINEAR, GaussianBlur kernel size,
 * BORDER_REFLECT_101, addWeighted, Laplacian), so the phone feeds the model the same tensor
 * the Raspberry Pi does (differences of at most a grey level or two from rounding).
 *
 * Prototype screening aid only - NOT a medical diagnosis.
 */
(function (global) {
  "use strict";

  // ---------------------------------------------------------------- helpers
  const clamp8 = (v) => (v < 0 ? 0 : v > 255 ? 255 : Math.round(v));
  const make = (w, h) => ({ w, h, d: new Uint8Array(w * h * 3) });

  function fromImageData(id) {
    const n = id.width * id.height, out = make(id.width, id.height), s = id.data, d = out.d;
    for (let i = 0, j = 0; i < n; i++, j += 4) { d[i * 3] = s[j]; d[i * 3 + 1] = s[j + 1]; d[i * 3 + 2] = s[j + 2]; }
    return out;
  }

  function toImageData(img) {
    const n = img.w * img.h, id = new ImageData(img.w, img.h), s = img.d, d = id.data;
    for (let i = 0, j = 0; i < n; i++, j += 4) { d[j] = s[i * 3]; d[j + 1] = s[i * 3 + 1]; d[j + 2] = s[i * 3 + 2]; d[j + 3] = 255; }
    return id;
  }

  function toCanvas(img) {
    const c = document.createElement("canvas");
    c.width = img.w; c.height = img.h;
    c.getContext("2d").putImageData(toImageData(img), 0, 0);
    return c;
  }

  /** Draw any image source onto a canvas (longest side capped) and return RGB. */
  function fromSource(src, maxSide = 3000) {
    const sw = src.videoWidth || src.naturalWidth || src.width, sh = src.videoHeight || src.naturalHeight || src.height;
    const k = Math.min(1, maxSide / Math.max(sw, sh));
    const w = Math.round(sw * k), h = Math.round(sh * k);
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(src, 0, 0, w, h);
    return fromImageData(ctx.getImageData(0, 0, w, h));
  }

  const reflect101 = (i, n) => (n === 1 ? 0 : i < 0 ? -i : i >= n ? 2 * n - 2 - i : i);

  // ------------------------------------------------- OpenCV equivalents
  /** cv2.COLOR_RGB2GRAY (fixed-point, as OpenCV does for 8-bit). */
  function gray(img) {
    const n = img.w * img.h, g = new Uint8Array(n), d = img.d;
    for (let i = 0; i < n; i++) g[i] = (d[i * 3] * 4899 + d[i * 3 + 1] * 9617 + d[i * 3 + 2] * 1868 + 8192) >> 14;
    return g;
  }

  function crop(img, x0, y0, w, h) {
    const out = make(w, h);
    for (let y = 0; y < h; y++) out.d.set(img.d.subarray(((y0 + y) * img.w + x0) * 3, ((y0 + y) * img.w + x0 + w) * 3), y * w * 3);
    return out;
  }

  /** crop_fundus(): remove the black border around the circular fundus. */
  function cropFundus(img, tol = 7) {
    const g = gray(img), { w, h } = img;
    let count = 0, r0 = h, r1 = -1, c0 = w, c1 = -1;
    for (let y = 0; y < h; y++) {
      const row = y * w;
      for (let x = 0; x < w; x++) {
        if (g[row + x] > tol) {
          count++;
          if (y < r0) r0 = y; if (y > r1) r1 = y;
          if (x < c0) c0 = x; if (x > c1) c1 = x;
        }
      }
    }
    if (count < 0.05 * w * h) return img;
    return crop(img, c0, r0, c1 - c0 + 1, r1 - r0 + 1);
  }

  /** pad_to_square(): centre the image on a black square. */
  function padToSquare(img) {
    const s = Math.max(img.w, img.h);
    if (img.w === s && img.h === s) return img;
    const out = make(s, s), y0 = (s - img.h) >> 1, x0 = (s - img.w) >> 1;
    for (let y = 0; y < img.h; y++) out.d.set(img.d.subarray(y * img.w * 3, (y + 1) * img.w * 3), ((y0 + y) * s + x0) * 3);
    return out;
  }

  /* INTER_AREA weights along one axis for downscaling (fractional pixel coverage). */
  function areaTable(src, dst) {
    const scale = src / dst, tab = [];
    for (let i = 0; i < dst; i++) {
      const f0 = i * scale, f1 = f0 + scale, idx = [], wt = [];
      let s = Math.floor(f0);
      for (; s < f1 - 1e-9 && s < src; s++) {
        const a = Math.max(f0, s), b = Math.min(f1, s + 1);
        if (b - a > 1e-9) { idx.push(s); wt.push((b - a) / scale); }
      }
      tab.push({ idx, wt });
    }
    return tab;
  }

  /* INTER_LINEAR weights along one axis (OpenCV half-pixel convention). */
  function linearTable(src, dst) {
    const scale = src / dst, tab = [];
    for (let i = 0; i < dst; i++) {
      let f = (i + 0.5) * scale - 0.5, s = Math.floor(f), t = f - s;
      if (s < 0) { s = 0; t = 0; }
      if (s >= src - 1) { s = src - 1; t = 0; }
      tab.push(t === 0 ? { idx: [s], wt: [1] } : { idx: [s, s + 1], wt: [1 - t, t] });
    }
    return tab;
  }

  function separable(img, w, h, tx, ty) {
    const tmp = new Float32Array(img.h * w * 3), out = make(w, h);
    for (let y = 0; y < img.h; y++) {
      const srow = y * img.w * 3, trow = y * w * 3;
      for (let x = 0; x < w; x++) {
        const { idx, wt } = tx[x];
        let r = 0, g = 0, b = 0;
        for (let k = 0; k < idx.length; k++) { const p = srow + idx[k] * 3, q = wt[k]; r += img.d[p] * q; g += img.d[p + 1] * q; b += img.d[p + 2] * q; }
        tmp[trow + x * 3] = r; tmp[trow + x * 3 + 1] = g; tmp[trow + x * 3 + 2] = b;
      }
    }
    for (let y = 0; y < h; y++) {
      const { idx, wt } = ty[y], orow = y * w * 3;
      for (let x = 0; x < w * 3; x++) {
        let v = 0;
        for (let k = 0; k < idx.length; k++) v += tmp[idx[k] * w * 3 + x] * wt[k];
        out.d[orow + x] = clamp8(v);
      }
    }
    return out;
  }

  /** cv2.resize(..., INTER_AREA) - area averaging when shrinking, bilinear when enlarging. */
  function resizeArea(img, w, h) {
    if (img.w === w && img.h === h) return img;
    const tx = img.w > w ? areaTable(img.w, w) : linearTable(img.w, w);
    const ty = img.h > h ? areaTable(img.h, h) : linearTable(img.h, h);
    return separable(img, w, h, tx, ty);
  }

  /** cv2.resize(..., INTER_LINEAR) - the default interpolation. */
  function resizeLinear(img, w, h) {
    return separable(img, w, h, linearTable(img.w, w), linearTable(img.h, h));
  }

  /** cv2.GaussianBlur(img, (0,0), sigma) for uint8 images (BORDER_REFLECT_101). */
  function gaussianBlur(img, sigma) {
    const ks = (Math.round(sigma * 3 * 2 + 1) | 1), r = (ks - 1) / 2, k = new Float64Array(ks);
    let sum = 0;
    for (let i = 0; i < ks; i++) { k[i] = Math.exp(-((i - r) ** 2) / (2 * sigma * sigma)); sum += k[i]; }
    for (let i = 0; i < ks; i++) k[i] /= sum;
    const { w, h } = img, tmp = new Float32Array(w * h * 3), out = make(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) {
      let v = 0;
      for (let i = 0; i < ks; i++) v += img.d[(y * w + reflect101(x + i - r, w)) * 3 + c] * k[i];
      tmp[(y * w + x) * 3 + c] = v;
    }
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) {
      let v = 0;
      for (let i = 0; i < ks; i++) v += tmp[(reflect101(y + i - r, h) * w + x) * 3 + c] * k[i];
      out.d[(y * w + x) * 3 + c] = clamp8(v);
    }
    return out;
  }

  // ------------------------------------------------ pi_inference.py port
  /** preprocess_fundus(): crop -> square -> resize -> Ben Graham -> circular mask. */
  function preprocessFundus(img, size = 384, benGraham = true) {
    let x = resizeArea(padToSquare(cropFundus(img)), size, size);
    if (benGraham) {
      const blur = gaussianBlur(x, size / 30), out = make(size, size);
      for (let i = 0; i < out.d.length; i++) out.d[i] = clamp8(x.d[i] * 4 - blur.d[i] * 4 + 128);
      x = out;
    }
    const c = size >> 1, rad = Math.trunc(size * 0.47), r2 = rad * rad;
    for (let y = 0; y < size; y++) for (let xx = 0; xx < size; xx++) {
      if ((xx - c) ** 2 + (y - c) ** 2 > r2) { const p = (y * size + xx) * 3; x.d[p] = x.d[p + 1] = x.d[p + 2] = 128; }
    }
    return x;
  }

  /** quality_metrics(): brightness and sharpness (Laplacian variance) of the green channel. */
  function qualityMetrics(img) {
    const s = 512, x = resizeArea(padToSquare(cropFundus(img)), s, s);
    const g = new Float64Array(s * s);
    for (let i = 0; i < s * s; i++) g[i] = x.d[i * 3 + 1];
    let n = 0, sum = 0, lsum = 0, lsq = 0;
    for (let y = 0; y < s; y++) for (let xx = 0; xx < s; xx++) {
      if ((xx - 256) ** 2 + (y - 256) ** 2 > 230 * 230) continue;
      const v = g[y * s + xx];
      const lap = g[reflect101(y - 1, s) * s + xx] + g[reflect101(y + 1, s) * s + xx]
        + g[y * s + reflect101(xx - 1, s)] + g[y * s + reflect101(xx + 1, s)] - 4 * v;
      n++; sum += v; lsum += lap; lsq += lap * lap;
    }
    const mean = lsum / n;
    return { brightness: sum / n, sharpness: lsq / n - mean * mean };
  }

  /** fundus_ratio(): median red/green over lit pixels (retina ~2+, skin/room ~1.2-1.4). */
  function fundusRatio(img) {
    const x = resizeLinear(img, 256, 256), vals = [];
    for (let i = 0; i < 256 * 256; i++) {
      const r = x.d[i * 3], g = x.d[i * 3 + 1], b = x.d[i * 3 + 2];
      if ((r + g + b) / 3 >= 20) vals.push(r / (g + 1));
    }
    if (vals.length < 0.05 * 256 * 256) return 0;
    const a = Float64Array.from(vals).sort(), m = a.length >> 1;
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
  }

  /** Same thresholds and wording as device/server.py quality_checks(). */
  function qualityChecks(img, cfg) {
    const q = cfg.quality, m = qualityMetrics(img), rg = fundusRatio(img), cf = cropFundus(img);
    const side = Math.min(cf.w, cf.h), rmin = cfg.fundus_rg_min ?? 1.6;
    const bOK = m.brightness >= q.brightness_min && m.brightness <= q.brightness_max;
    const checks = [
      { name: "Retina detected (red / green)", value: rg.toFixed(2), status: rg >= rmin ? "ok" : "fail",
        text: rg >= rmin ? "Fundus reflex present." : "This does not look like a retina photo. Hold the lens ~5 cm from the eye, dim the room and find the red reflex." },
      { name: "Sharpness", value: m.sharpness.toFixed(1),
        status: m.sharpness >= 1.5 * q.sharpness_min ? "ok" : m.sharpness >= q.sharpness_min ? "warn" : "fail",
        text: m.sharpness >= 1.5 * q.sharpness_min ? "Vessels in focus." : m.sharpness >= q.sharpness_min ? "Slightly soft. Move the phone slowly to fine-tune focus." : "Blurred. Move the phone back and forth until the vessels are sharp." },
      { name: "Brightness", value: `${Math.round(m.brightness)} / 255`, status: bOK ? "ok" : "fail",
        text: bOK ? "Well exposed." : m.brightness < q.brightness_min ? "Too dark. Turn on the torch or dim the room less." : "Over-exposed. Tilt the lens slightly to remove glare." },
      { name: "Fundus resolution", value: `${cf.w}×${cf.h} px`, status: side >= 384 ? "ok" : side >= 256 ? "warn" : "fail",
        text: side >= 384 ? "Enough detail for grading." : "Small fundus image. Move closer or use 2× zoom so the retina fills more of the frame." },
    ];
    const overall = checks.some((c) => c.status === "fail") ? "fail" : checks.some((c) => c.status === "warn") ? "warn" : "ok";
    return { checks, overall, metrics: m, rg };
  }

  // ---------------------------------------------- phone-specific: find the retina
  /**
   * Phone photos through a condensing lens show the face around the lens, so the black-border
   * crop alone is not enough. Find the largest strongly-red region (the fundus seen through the
   * lens) and return a circle around it, in source pixel coordinates. null = no retina found.
   */
  function detectFundusCircle(img, rgMin = 1.6) {
    const k = 160 / Math.max(img.w, img.h), w = Math.max(8, Math.round(img.w * k)), h = Math.max(8, Math.round(img.h * k));
    const s = resizeArea(img, w, h), red = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) {
      const r = s.d[i * 3], g = s.d[i * 3 + 1], b = s.d[i * 3 + 2];
      red[i] = (r + g + b) / 3 >= 20 && r / (g + 1) >= rgMin ? 1 : 0;
    }
    const dil = new Uint8Array(w * h);                   // 1-px dilation bridges dark vessels
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let v = 0;
      for (let dy = -1; dy <= 1 && !v; dy++) for (let dx = -1; dx <= 1 && !v; dx++) {
        const yy = y + dy, xx = x + dx;
        if (yy >= 0 && yy < h && xx >= 0 && xx < w && red[yy * w + xx]) v = 1;
      }
      dil[y * w + x] = v;
    }
    const lab = new Int32Array(w * h); let best = null, id = 0;
    const stack = new Int32Array(w * h);
    for (let i = 0; i < w * h; i++) {
      if (!dil[i] || lab[i]) continue;
      id++; let sp = 0, area = 0, x0 = w, x1 = 0, y0 = h, y1 = 0;
      stack[sp++] = i; lab[i] = id;
      while (sp) {
        const p = stack[--sp], x = p % w, y = (p / w) | 0;
        area++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
        const nb = [x > 0 ? p - 1 : -1, x < w - 1 ? p + 1 : -1, y > 0 ? p - w : -1, y < h - 1 ? p + w : -1];
        for (const q of nb) if (q >= 0 && dil[q] && !lab[q]) { lab[q] = id; stack[sp++] = q; }
      }
      if (!best || area > best.area) best = { area, x0, x1, y0, y1 };
    }
    if (!best || best.area < 0.015 * w * h) return null;
    const cx = (best.x0 + best.x1 + 1) / 2 / k, cy = (best.y0 + best.y1 + 1) / 2 / k;
    const r = (Math.max(best.x1 - best.x0 + 1, best.y1 - best.y0 + 1) / 2 / k) * 1.04;
    return { cx, cy, r };
  }

  /** Square crop around the circle with everything outside it set to black. */
  function applyCircle(img, c, maxSide = 1600) {
    const S = Math.max(8, Math.round(2 * c.r)), out = make(S, S);
    const x0 = Math.round(c.cx - S / 2), y0 = Math.round(c.cy - S / 2), rr = (S / 2) ** 2;
    for (let y = 0; y < S; y++) {
      const sy = y0 + y;
      if (sy < 0 || sy >= img.h) continue;
      for (let x = 0; x < S; x++) {
        const sx = x0 + x;
        if (sx < 0 || sx >= img.w || (x + 0.5 - S / 2) ** 2 + (y + 0.5 - S / 2) ** 2 > rr) continue;
        const p = (sy * img.w + sx) * 3, q = (y * S + x) * 3;
        out.d[q] = img.d[p]; out.d[q + 1] = img.d[p + 1]; out.d[q + 2] = img.d[p + 2];
      }
    }
    return S > maxSide ? resizeArea(out, maxSide, maxSide) : out;
  }

  // ------------------------------------------------------------- model
  class DRModel {
    constructor(cfg) { this.cfg = cfg; this.session = null; this.file = null; }

    async load(url, onProgress, wasmBase = "ort/") {
      const res = await fetch(url);
      if (!res.ok) throw new Error(res.status === 404 ? "model file not found on the server" : `HTTP ${res.status}`);
      const total = +res.headers.get("content-length") || 0;
      let buf;
      if (res.body && res.body.getReader) {
        const reader = res.body.getReader(), parts = []; let got = 0;
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          parts.push(value); got += value.length;
          onProgress && onProgress(got, total);
        }
        buf = new Uint8Array(got); let o = 0;
        for (const p of parts) { buf.set(p, o); o += p.length; }
      } else buf = new Uint8Array(await res.arrayBuffer());
      if (buf.length < 1e5) throw new Error("model file is too small - is it a Git LFS pointer?");
      const ort = global.ort;
      ort.env.wasm.wasmPaths = new URL(wasmBase, document.baseURI).href;
      ort.env.wasm.numThreads = global.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 2) : 1;
      this.session = await ort.InferenceSession.create(buf, { executionProviders: ["wasm"], graphOptimizationLevel: "all" });
      this.file = url.split("/").pop().split("?")[0];
      this.threads = ort.env.wasm.numThreads;
      return this;
    }

    /** Same as DRModel.predict() on the Pi, given an RGB image (already circle-cropped if needed). */
    async predict(img) {
      const cfg = this.cfg, size = cfg.img_size, pre = preprocessFundus(img, size);
      const n = size * size, x = new Float32Array(3 * n);
      for (let i = 0; i < n; i++) { x[i] = pre.d[i * 3] / 255; x[n + i] = pre.d[i * 3 + 1] / 255; x[2 * n + i] = pre.d[i * 3 + 2] / 255; }
      const ort = global.ort, t0 = performance.now();
      const out = await this.session.run({ [this.session.inputNames[0]]: new ort.Tensor("float32", x, [1, 3, size, size]) });
      const ms = performance.now() - t0, score = out[this.session.outputNames[0]].data[0];
      let grade = 0;
      for (const t of cfg.thresholds) if (score >= t) grade++;
      return { grade, grade_name: cfg.grades[grade], score: Math.round(score * 1000) / 1000, raw_score: score,
        referable: grade >= cfg.referable_min_grade, inference_ms: Math.round(ms * 10) / 10, enhanced: pre };
    }
  }

  global.Fundus = { fromImageData, toImageData, toCanvas, fromSource, gray, cropFundus, padToSquare, resizeArea, resizeLinear,
    gaussianBlur, preprocessFundus, qualityMetrics, fundusRatio, qualityChecks, detectFundusCircle, applyCircle, DRModel };
})(typeof window !== "undefined" ? window : globalThis);
