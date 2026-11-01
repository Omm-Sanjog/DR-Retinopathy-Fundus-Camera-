#!/usr/bin/env bash
# Command-line grading inside the virtual environment.
#   ./run.sh --usbcam             capture from the USB camera and grade
#   ./run.sh --camera             capture from the Pi camera module and grade
#   ./run.sh fundus.jpg [--json]  grade a saved image
cd "$(dirname "$(readlink -f "$0")")"
if [ ! -d venv ]; then echo "Not installed yet. Run: bash install.sh"; exit 1; fi
exec ./venv/bin/python pi_inference.py "$@"
