#!/usr/bin/env python3
"""
Diabetic Retinopathy screening - Raspberry Pi inference (ONNX Runtime, CPU)

  python3 pi_inference.py fundus.jpg
  python3 pi_inference.py --camera                     # capture with rpicam-still (Pi camera), then analyse
  python3 pi_inference.py --usbcam                     # capture from USB webcam (prototype v1), then analyse
  python3 pi_inference.py fundus.jpg --model models/dr_model_int8.onnx --json

Prototype screening aid only - NOT a medical diagnosis.
"""
import argparse, json, os, shutil, subprocess, sys, time
import onnxruntime as ort

import cv2
import numpy as np

def crop_fundus(img_rgb, tol=7):
    """Remove the black border around the circular fundus."""
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    mask = gray > tol
    if mask.sum() < 0.05 * mask.size:      # almost entirely dark: leave unchanged
        return img_rgb
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    return img_rgb[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]

def pad_to_square(img):
    h, w = img.shape[:2]
    s = max(h, w)
    out = np.zeros((s, s, 3), dtype=img.dtype)
    y, x = (s - h) // 2, (s - w) // 2
    out[y:y + h, x:x + w] = img
    return out

def preprocess_fundus(img_rgb, size=384, ben_graham=True):
    """RGB uint8 image in -> RGB uint8 (size x size) out. Used for training AND on the Pi."""
    img = pad_to_square(crop_fundus(img_rgb))
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    if ben_graham:   # local contrast / lighting normalisation (Ben Graham, Kaggle DR 2015)
        blur = cv2.GaussianBlur(img, (0, 0), sigmaX=size / 30)
        img = cv2.addWeighted(img, 4, blur, -4, 128)
    mask = np.zeros((size, size), np.uint8)
    cv2.circle(mask, (size // 2, size // 2), int(size * 0.47), 1, -1)
    img = img * mask[:, :, None] + 128 * (1 - mask[:, :, None])
    return img.astype(np.uint8)

def quality_metrics(img_rgb):
    """Simple image-quality numbers: brightness and sharpness of the fundus (green channel)."""
    img = pad_to_square(crop_fundus(img_rgb))
    img = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA)
    g = img[:, :, 1]
    mask = np.zeros((512, 512), np.uint8)
    cv2.circle(mask, (256, 256), 230, 1, -1)
    inside = mask == 1
    lap = cv2.Laplacian(g, cv2.CV_64F)
    return {"brightness": float(g[inside].mean()), "sharpness": float(lap[inside].var())}


def fundus_ratio(img_rgb):
    """Median red/green ratio over non-black pixels. Retina photos are strongly red (~2+);
    skin, sclera and room scenes are ~1.2-1.4."""
    img = cv2.resize(img_rgb, (256, 256)).astype(np.float32)
    lit = img.mean(axis=2) >= 20
    if lit.mean() < 0.05:
        return 0.0
    return float(np.median(img[..., 0][lit] / (img[..., 1][lit] + 1)))


HERE = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(HERE, "config.json")) as f:
        return json.load(f)


def check_quality(m, cfg):
    q, problems = cfg["quality"], []
    if m["sharpness"] < q["sharpness_min"]:
        problems.append("image looks blurry / out of focus")
    if m["brightness"] < q["brightness_min"]:
        problems.append("image too dark")
    if m["brightness"] > q["brightness_max"]:
        problems.append("image too bright / overexposed")
    return problems


def capture_usb(index=0, path="/tmp/fundus.jpg", warmup=15):
    """Grab a frame from a USB webcam (prototype v1 camera)."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        sys.exit(f"Could not open USB camera {index}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    frame = None
    for _ in range(warmup):            # let exposure settle
        ok, frame = cap.read()
    cap.release()
    if frame is None:
        sys.exit("USB camera returned no frame")
    cv2.imwrite(path, frame)
    return path


def capture(path="/tmp/fundus.jpg"):
    cam = shutil.which("rpicam-still") or shutil.which("libcamera-still")
    if not cam:
        sys.exit("rpicam-still not found. Install with: sudo apt install rpicam-apps")
    subprocess.run([cam, "-n", "-t", "1500", "-o", path], check=True)
    return path


class DRModel:
    def __init__(self, model_path=None):
        self.cfg = load_config()
        model_path = model_path or os.path.join(HERE, self.cfg["recommended_model"])
        so = ort.SessionOptions()
        so.intra_op_num_threads = os.cpu_count() or 4
        self.sess = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
        self.input_name = self.sess.get_inputs()[0].name
        self.model_file = os.path.basename(model_path)

    def predict(self, img_rgb):
        cfg = self.cfg
        problems = check_quality(quality_metrics(img_rgb), cfg)
        rg = fundus_ratio(img_rgb)
        if rg < cfg.get("fundus_rg_min", 1.6):
            problems.insert(0, f"does not look like a retina photo (red/green {rg:.2f})")
        x = preprocess_fundus(img_rgb, cfg["img_size"]).astype(np.float32) / 255.0
        x = x.transpose(2, 0, 1)[None]
        t0 = time.time()
        score = float(self.sess.run(None, {self.input_name: x})[0].reshape(-1)[0])
        ms = (time.time() - t0) * 1000
        grade = int(np.digitize(score, cfg["thresholds"]))
        return {
            "grade": grade,
            "grade_name": cfg["grades"][grade],
            "score": round(score, 3),
            "referable": grade >= cfg["referable_min_grade"],
            "image_ok": not problems,
            "fundus_rg": round(rg, 2),
            "quality_issues": problems,
            "inference_ms": round(ms, 1),
            "model": self.model_file,
        }


def main():
    ap = argparse.ArgumentParser(description="Diabetic retinopathy screening (prototype)")
    ap.add_argument("image", nargs="?", help="fundus image path")
    ap.add_argument("--camera", action="store_true", help="capture a photo with the Pi camera first")
    ap.add_argument("--usbcam", nargs="?", const=0, type=int, metavar="INDEX", help="capture from a USB webcam (default index 0)")
    ap.add_argument("--model", help="ONNX model file (default: recommended_model in config.json)")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    a = ap.parse_args()
    if not a.image and not a.camera and a.usbcam is None:
        ap.error("give an image path, --camera or --usbcam")
    path = capture() if a.camera else (capture_usb(a.usbcam) if a.usbcam is not None else a.image)
    bgr = cv2.imread(path)
    if bgr is None:
        sys.exit(f"Could not read image: {path}")
    model = DRModel(os.path.join(HERE, a.model) if a.model and not os.path.isabs(a.model) else a.model)
    r = model.predict(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    if a.json:
        print(json.dumps(r)); return
    print(f"\nImage      : {path}")
    if not r["image_ok"]:
        print(f"⚠️  Retake recommended: {', '.join(r['quality_issues'])}")
    print(f"Grade      : {r['grade']} - {r['grade_name']}  (score {r['score']})")
    print(f"Referable  : {'YES - refer to an ophthalmologist' if r['referable'] else 'No'}")
    print(f"Inference  : {r['inference_ms']} ms  [{r['model']}]")
    print("Note: prototype screening aid, not a medical diagnosis.\n")


if __name__ == "__main__":
    main()
