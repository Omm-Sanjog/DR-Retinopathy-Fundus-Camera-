#!/usr/bin/env bash
# Lists video devices, grabs one frame and prints the image-quality numbers (no AI grading).
#   ./check_camera.sh [camera_index]
cd "$(dirname "$(readlink -f "$0")")"
[ -d venv ] || { echo "Not installed yet. Run: bash install.sh"; exit 1; }
command -v v4l2-ctl >/dev/null && v4l2-ctl --list-devices || ls /dev/video* 2>/dev/null
./venv/bin/python - "${1:-0}" <<'PY'
import sys, cv2
sys.path.insert(0, ".")
from pi_inference import quality_metrics, fundus_ratio, load_config
idx = int(sys.argv[1])
cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
for _ in range(10): ok, f = cap.read()
cap.release()
if not ok: sys.exit(f"Could not read from camera {idx}. Is it plugged in? Try another index.")
cv2.imwrite("camera_test.jpg", f)
rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB); q = load_config()["quality"]; m = quality_metrics(rgb)
print(f"Saved camera_test.jpg  {f.shape[1]}x{f.shape[0]}")
print(f"brightness {m['brightness']:.1f} (want {q['brightness_min']}-{q['brightness_max']})")
print(f"sharpness  {m['sharpness']:.1f} (want >= {q['sharpness_min']})")
print(f"red/green  {fundus_ratio(rgb):.2f} (want >= 1.6 for a retina)")
PY
