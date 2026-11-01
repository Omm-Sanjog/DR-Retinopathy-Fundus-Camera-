#!/usr/bin/env bash
# FundusScan - one-command installer for Raspberry Pi 5 (Raspberry Pi OS 64-bit, Bookworm)
# Usage:  bash install.sh               (add --autostart to open FundusScan full screen at boot)
set -e
cd "$(dirname "$(readlink -f "$0")")"
APP_DIR="$(pwd)"
VENV="$APP_DIR/venv"
MODEL="$APP_DIR/models/dr_model_fp32.onnx"

say()  { echo -e "\n\033[1;32m==> $*\033[0m"; }
warn() { echo -e "\033[1;33m!! $*\033[0m"; }

say "FundusScan installer - folder: $APP_DIR"

if [ "${SKIP_APT:-0}" != "1" ]; then
  say "1/5  Installing system packages (needs your password once)"
  sudo apt-get update -y
  sudo apt-get install -y python3-venv python3-pip python3-dev v4l-utils curl
  # Picamera2 comes from apt on Raspberry Pi OS; harmless if already present / unavailable
  sudo apt-get install -y python3-picamera2 2>/dev/null || true
  sudo usermod -aG video "$USER" || true
fi

say "2/5  Creating virtual environment: $VENV"
python3 -m venv --system-site-packages "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel

say "3/5  Installing Python libraries (numpy, opencv, flask)"
pip install "numpy>=1.24" "opencv-python-headless>=4.8" "flask>=3.0"

say "4/5  Installing ONNX Runtime"
pip install "onnxruntime>=1.17"

say "5/5  Self-test"
if [ -f "$MODEL" ]; then
  python - <<'PY'
import numpy as np, os, sys, time
sys.path.insert(0, os.getcwd())
from pi_inference import DRModel
m = DRModel()
img = np.zeros((512, 512, 3), np.uint8); img[..., 0] = 150; img[..., 1] = 60
t = time.time(); r = m.predict(img)
print(f"Model OK - test inference {r['inference_ms']:.0f} ms (dummy image, result not meaningful)")
PY
else
  warn "Model file not found: $MODEL"
  warn "Copy dr_model_fp32.onnx (from the Colab notebook's export step) into device/models/ before screening."
  warn "The app will still open, but it will show 'Model not loaded' until the file is there."
fi

chmod +x "$APP_DIR"/*.sh
mkdir -p "$APP_DIR/scans"

say "Adding FundusScan to the app menu and desktop"
DESKTOP_FILE="[Desktop Entry]
Type=Application
Name=FundusScan
Comment=AI diabetic retinopathy screening
Exec=$APP_DIR/start_ui.sh
Icon=$APP_DIR/static/icon.svg
Terminal=false
Categories=Science;MedicalSoftware;Education;"
mkdir -p "$HOME/.local/share/applications"
echo "$DESKTOP_FILE" > "$HOME/.local/share/applications/fundusscan.desktop"
if [ -d "$HOME/Desktop" ]; then
  echo "$DESKTOP_FILE" > "$HOME/Desktop/FundusScan.desktop"
  chmod +x "$HOME/Desktop/FundusScan.desktop"
  command -v gio >/dev/null && gio set "$HOME/Desktop/FundusScan.desktop" metadata::trusted true 2>/dev/null || true
fi

if [ "${1:-}" = "--autostart" ]; then
  mkdir -p "$HOME/.config/autostart"
  echo "${DESKTOP_FILE/start_ui.sh/start_ui.sh --kiosk}" > "$HOME/.config/autostart/fundusscan.desktop"
  echo "FundusScan will open full screen every time the Pi starts."
fi

say "Installed successfully!"
cat <<MSG

Open FundusScan:
  double-click the FundusScan icon on the desktop (or find it in the app menu)
  or run:  ./start_ui.sh          (add --kiosk for full screen)

Camera choice (default: USB fundus camera):
  FUNDUS_CAMERA=picam ./start_ui.sh      use the Pi camera module instead
  FUNDUS_CAMERA_INDEX=1 ./start_ui.sh    pick a different USB camera

Command-line tools, from this folder ($APP_DIR):
  ./check_camera.sh              list cameras, save a test photo + quality report
  ./run.sh --usbcam              take one photo and grade it in the terminal
  ./run.sh path/to/fundus.jpg    grade a saved photo

If the camera gives a permission error, reboot once (needed after joining the 'video' group).
MSG
