#!/usr/bin/env python3
"""
FundusScan - web interface server for the AI fundus camera.

Owns the camera (USB webcam on prototype v1, or the Pi Camera Module), streams a live
preview with alignment checks, captures a fundus photo, runs the quality / fundus gates
and the EfficientNet-B0 ONNX grader, and writes a full screening report for every scan.

Start it with ./start_ui.sh  (or: ./venv/bin/python server.py)  then open http://localhost:8000

Environment variables
  FUNDUS_PORT=8000              web port
  FUNDUS_CAMERA=usb|picam       camera type (default usb)
  FUNDUS_CAMERA_INDEX=0         USB camera index (/dev/videoN)
  FUNDUS_MODEL=models/xx.onnx   model file (default: recommended_model in config.json)
  FUNDUS_FAKE_IMAGE=photo.jpg   test the interface without a camera
"""
import json, os, re, shutil, threading, time, uuid
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, request, send_from_directory

import pi_inference as pi

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
SCANS = os.path.join(HERE, "scans")
os.makedirs(SCANS, exist_ok=True)

PORT = int(os.environ.get("FUNDUS_PORT", "8000"))
CAM_TYPE = os.environ.get("FUNDUS_CAMERA", "usb").lower()
CAM_INDEX = int(os.environ.get("FUNDUS_CAMERA_INDEX", "0"))
FAKE_IMAGE = os.environ.get("FUNDUS_FAKE_IMAGE", "")
WIDTH, HEIGHT = 1920, 1080

CFG = pi.load_config()
GRADES = CFG["grades"]
THRESH = CFG["thresholds"]

# ---------------------------------------------------------------------------
# Model (the server still starts if the model file is missing, and says so)
# ---------------------------------------------------------------------------
MODEL_ERROR = ""
model = None
model_path = os.environ.get("FUNDUS_MODEL", "")
try:
    model = pi.DRModel(os.path.join(HERE, model_path) if model_path and not os.path.isabs(model_path) else (model_path or None))
except Exception as e:  # noqa: BLE001
    MODEL_ERROR = (f"Model not loaded: {e}. Copy dr_model_fp32.onnx from dr_pi_bundle.zip into "
                   f"{os.path.join(HERE, 'models')}/ and restart.")
model_lock = threading.Lock()

app = Flask(__name__, static_folder=None)


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
class Camera:
    def __init__(self):
        self.frame = None                  # latest RGB frame
        self.lock = threading.Lock()
        self.status, self.message, self.fps = "starting", "", 0.0
        threading.Thread(target=self._run, daemon=True).start()

    def _set(self, rgb):
        with self.lock:
            self.frame = rgb

    def _run(self):
        if FAKE_IMAGE:
            bgr = cv2.imread(FAKE_IMAGE)
            if bgr is None:
                self.status, self.message = "missing", f"Test image not found: {FAKE_IMAGE}"
                return
            self._set(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            self.status, self.message = "ok", "Test image (no camera)"
            return
        if CAM_TYPE == "picam":
            self._run_picam()
        else:
            self._run_usb()

    def _run_usb(self):
        while True:
            cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2) if os.name != "nt" else cv2.VideoCapture(CAM_INDEX)
            if not cap.isOpened():
                self.status, self.message = "missing", f"Camera not found at /dev/video{CAM_INDEX}"
                time.sleep(3)
                continue
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            self.status, self.message = "ok", "USB camera ready"
            fails, t0, n = 0, time.time(), 0
            while True:
                ok, bgr = cap.read()
                if not ok:
                    fails += 1
                    if fails > 30:
                        self.status, self.message = "missing", "Camera stopped sending images"
                        break
                    time.sleep(0.05)
                    continue
                fails = 0
                self._set(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                n += 1
                if time.time() - t0 > 2:
                    self.fps, t0, n = n / (time.time() - t0), time.time(), 0
            cap.release()
            time.sleep(1)

    def _run_picam(self):
        try:
            from picamera2 import Picamera2
        except ImportError:
            self.status, self.message = "missing", "picamera2 not installed (sudo apt install python3-picamera2)"
            return
        cam = Picamera2()
        cam.configure(cam.create_video_configuration(main={"size": (2304, 1296), "format": "RGB888"}))
        cam.start()
        self.status, self.message = "ok", "Pi camera ready"
        t0, n = time.time(), 0
        while True:
            arr = cam.capture_array()                     # Picamera2 "RGB888" is BGR byte order
            self._set(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
            n += 1
            if time.time() - t0 > 2:
                self.fps, t0, n = n / (time.time() - t0), time.time(), 0

    def latest(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()


camera = Camera()


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
ACTIONS = {
    0: ("No referral needed", "Re-screen in 12 months. Maintain blood-sugar, blood-pressure and lipid control.", "routine"),
    1: ("No referral needed", "Re-screen in 6–12 months. Optimise diabetes control.", "routine"),
    2: ("Refer to an ophthalmologist", "Referable DR. Arrange an eye-specialist examination (non-urgent, within about 3 months).", "refer"),
    3: ("Refer to an ophthalmologist – urgent", "Severe non-proliferative DR. Arrange an eye-specialist examination within about 4 weeks.", "urgent"),
    4: ("Refer to an ophthalmologist – urgent", "Proliferative DR (sight-threatening). Arrange an eye-specialist examination within about 1 week.", "urgent"),
}
FINDINGS = [
    "No visible abnormalities of diabetic retinopathy.",
    "Microaneurysms only.",
    "More than microaneurysms (haemorrhages, hard exudates or cotton-wool spots) but less than severe NPDR.",
    "Extensive intraretinal haemorrhages, venous beading or IRMA (4-2-1 rule) without proliferation.",
    "Neovascularisation and/or vitreous or pre-retinal haemorrhage.",
]


def check(name, value, status, text):
    return {"name": name, "value": value, "status": status, "text": text}


def quality_checks(rgb):
    q = CFG["quality"]
    m = pi.quality_metrics(rgb)
    rg = pi.fundus_ratio(rgb)
    fh, fw = pi.crop_fundus(rgb).shape[:2]
    side = min(fh, fw)
    rmin = CFG.get("fundus_rg_min", 1.6)
    checks = [
        check("Retina detected (red / green)", f"{rg:.2f}",
              "ok" if rg >= rmin else "fail",
              "Fundus reflex present." if rg >= rmin else
              "This does not look like a retina photo. Hold the lens ~5 cm from the eye, dim the room and find the red reflex."),
        check("Sharpness", f"{m['sharpness']:.1f}",
              "ok" if m["sharpness"] >= 1.5 * q["sharpness_min"] else ("warn" if m["sharpness"] >= q["sharpness_min"] else "fail"),
              "Vessels in focus." if m["sharpness"] >= 1.5 * q["sharpness_min"] else
              ("Slightly soft. Fine-tune the focus lever." if m["sharpness"] >= q["sharpness_min"] else
               "Blurred. Adjust the focus lever until the vessels are sharp.")),
        check("Brightness", f"{m['brightness']:.0f} / 255",
              "ok" if q["brightness_min"] <= m["brightness"] <= q["brightness_max"] else "fail",
              "Well exposed." if q["brightness_min"] <= m["brightness"] <= q["brightness_max"] else
              ("Too dark. Increase the illumination." if m["brightness"] < q["brightness_min"] else
               "Over-exposed. Reduce the illumination.")),
        check("Fundus resolution", f"{fw}×{fh} px",
              "ok" if side >= 384 else ("warn" if side >= 256 else "fail"),
              "Enough detail for grading." if side >= 384 else "Small fundus image. Move the camera carriage to enlarge the view."),
    ]
    overall = "fail" if any(c["status"] == "fail" for c in checks) else ("warn" if any(c["status"] == "warn" for c in checks) else "ok")
    return checks, overall, m, rg


def analyse(rgb, patient, source):
    t_start = time.perf_counter()
    checks, overall, m, rg = quality_checks(rgb)
    sid = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = os.path.join(SCANS, sid)
    os.makedirs(d)

    # images for the report
    frame = rgb.copy()
    if frame.shape[1] > 1280:
        frame = cv2.resize(frame, (1280, round(1280 * frame.shape[0] / frame.shape[1])), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(d, "frame.jpg"), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    fundus = cv2.resize(pi.pad_to_square(pi.crop_fundus(rgb)), (768, 768), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(d, "fundus.jpg"), cv2.cvtColor(fundus, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    enhanced = pi.preprocess_fundus(rgb, CFG["img_size"])
    cv2.imwrite(os.path.join(d, "enhanced.png"), cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR))

    result = None
    if model is not None:
        with model_lock:
            r = model.predict(rgb)
        g, s = r["grade"], r["score"]
        margin = min(abs(s - t) for t in THRESH)
        confidence = "Borderline" if margin < 0.15 else ("Moderate" if margin < 0.35 else "High")
        title, advice, level = ACTIONS[g]
        gradable = overall != "fail"
        result = {
            "grade": g, "grade_name": GRADES[g], "score": s, "referable": g >= CFG["referable_min_grade"],
            "confidence": confidence, "gradable": gradable,
            "action": title if gradable else "Image not gradable – retake",
            "advice": advice if gradable else "The photo did not pass the quality checks, so the grade is not reliable. "
                                               "Retake the image; if three attempts fail, refer for a full eye examination.",
            "level": level if gradable else "ungradable",
            "findings": FINDINGS[g],
            "inference_ms": r["inference_ms"],
        }
    report = {
        "id": sid,
        "time": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "patient": patient,
        "result": result,
        "model_error": MODEL_ERROR or None,
        "quality": {"overall": overall, "checks": checks},
        "model": {"name": "EfficientNet-B0 (regression)", "file": model.model_file if model else None,
                  "input": f"{CFG['img_size']}×{CFG['img_size']}", "thresholds": THRESH,
                  "trained_on": CFG.get("data", "APTOS 2019"), "test_metrics": CFG.get("metrics_test", {}),
                  "total_ms": round((time.perf_counter() - t_start) * 1000, 1)},
        "images": {k: f"/scans/{sid}/{f}" for k, f in (("frame", "frame.jpg"), ("fundus", "fundus.jpg"), ("enhanced", "enhanced.png"))},
    }
    with open(os.path.join(d, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    return report


def clean_patient(src):
    src = src or {}
    def s(k, n=40):
        return str(src.get(k, "") or "").strip()[:n]
    return {"id": s("id") or "P-" + datetime.now().strftime("%Y%m%d-%H%M%S"), "age": s("age", 3), "sex": s("sex", 10),
            "eye": s("eye", 5) or "Right", "diabetes_years": s("diabetes_years", 3), "notes": s("notes", 300),
            "operator": s("operator")}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/report")
def report_page():
    return send_from_directory(STATIC, "report.html")


@app.get("/static/<path:p>")
def static_files(p):
    return send_from_directory(STATIC, p)


@app.get("/scans/<sid>/<name>")
def scan_file(sid, name):
    if not re.fullmatch(r"[\w-]+", sid):
        abort(404)
    return send_from_directory(os.path.join(SCANS, sid), name)


@app.get("/stream")
def stream():
    def gen():
        while True:
            f = camera.latest()
            if f is None:
                time.sleep(0.2)
                continue
            h, w = f.shape[:2]
            if w > 960:
                f = cv2.resize(f, (960, round(960 * h / w)), interpolation=cv2.INTER_AREA)
            ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
            time.sleep(1 / 15 if not FAKE_IMAGE else 0.5)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-store"})


@app.get("/api/status")
def status():
    f = camera.latest()
    return jsonify({
        "camera": {"status": camera.status, "message": camera.message, "fps": round(camera.fps, 1),
                   "type": "test image" if FAKE_IMAGE else CAM_TYPE,
                   "frame_size": None if f is None else [f.shape[1], f.shape[0]]},
        "model": {"loaded": model is not None, "file": model.model_file if model else None, "error": MODEL_ERROR or None,
                  "test_metrics": CFG.get("metrics_test", {}), "thresholds": THRESH},
        "scans": len([x for x in os.listdir(SCANS) if os.path.isdir(os.path.join(SCANS, x))]),
    })


@app.get("/api/live")
def live():
    f = camera.latest()
    if f is None:
        return jsonify({"ok": False})
    small = cv2.resize(f, (480, round(480 * f.shape[0] / f.shape[1])), interpolation=cv2.INTER_AREA)
    checks, overall, m, rg = quality_checks(small)
    return jsonify({"ok": True, "overall": overall,
                    "checks": [{"name": c["name"], "value": c["value"], "status": c["status"]} for c in checks[:3]]})


@app.post("/api/capture")
def capture():
    d = request.get_json(silent=True) or {}
    f = camera.latest()
    if f is None:
        return jsonify({"error": "No camera image yet. Check that the camera is connected."}), 503
    return jsonify(analyse(f, clean_patient(d.get("patient")), "camera"))


@app.post("/api/analyze")
def analyze_upload():
    file = request.files.get("photo")
    if not file:
        return jsonify({"error": "No photo was uploaded."}), 400
    data = np.frombuffer(file.read(), np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        return jsonify({"error": "That file isn't an image FundusScan can read. Use JPG or PNG."}), 400
    patient = clean_patient(json.loads(request.form.get("patient", "{}") or "{}"))
    return jsonify(analyse(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), patient, "upload"))


@app.get("/api/history")
def history():
    items = []
    for sid in sorted(os.listdir(SCANS), reverse=True)[:100]:
        p = os.path.join(SCANS, sid, "report.json")
        if os.path.exists(p):
            r = json.load(open(p))
            res = r.get("result") or {}
            items.append({"id": sid, "time": r["time"], "patient": r["patient"].get("id"), "eye": r["patient"].get("eye"),
                          "grade": res.get("grade"), "grade_name": res.get("grade_name"), "level": res.get("level"),
                          "quality": r["quality"]["overall"], "thumb": r["images"]["fundus"]})
    return jsonify(items)


@app.get("/api/scan/<sid>")
def get_scan(sid):
    p = os.path.join(SCANS, sid, "report.json")
    if not re.fullmatch(r"[\w-]+", sid) or not os.path.exists(p):
        abort(404)
    return send_from_directory(os.path.join(SCANS, sid), "report.json", mimetype="application/json")


@app.delete("/api/scan/<sid>")
def delete_scan(sid):
    p = os.path.join(SCANS, sid)
    if not re.fullmatch(r"[\w-]+", sid) or not os.path.isdir(p):
        abort(404)
    shutil.rmtree(p)
    return jsonify({"ok": True})


if __name__ == "__main__":
    print(f"FundusScan running: open http://localhost:{PORT}  (or http://<pi-ip>:{PORT} from a device on the same Wi-Fi)")
    if MODEL_ERROR:
        print("WARNING:", MODEL_ERROR)
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False)
