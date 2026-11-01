# FundusScan — the on-device app (Raspberry Pi 5)

```
    ______                __          _____
   / ____/_  ______  ____/ /_  _____ / ___/_________ _____
  / /_  / / / / __ \/ __  / / / / __\\__ \/ ___/ __ `/ __ \
 / __/ / /_/ / / / / /_/ / /_/ (__  )__/ / /__/ /_/ / / / /
/_/    \__,_/_/ /_/\__,_/\__,_/____/____/\___/\__,_/_/ /_/

   [ icon ] ──► camera preview ──► 📸 capture ──► AI grade ──► 📄 diagnosis report
              live focus / light      quality +      EfficientNet-B0    print / save PDF
              / retina checks         retina gates   ONNX, offline
```

Double-click the **FundusScan** icon on the Pi desktop and everything else happens on its own: the
server starts, the camera opens, a full-screen interface appears, and every capture produces a
printable screening report.

## 1 · Install (once)

```bash
git clone https://github.com/Omm-Sanjog/DR-Retinopathy-Fundus-Camera-.git
cd DR-Retinopathy-Fundus-Camera-/device
cp /path/to/dr_model_fp32.onnx models/      # from dr_pi_bundle.zip (Colab notebook output)
bash install.sh                             # add --autostart to open full screen at every boot
```

`install.sh` installs the system packages, creates `venv/`, installs `onnxruntime opencv-python-headless numpy flask`,
runs a self-test on the model, and puts a **FundusScan** icon on the desktop and in the app menu.
Reboot once afterwards if the camera reports a permission error (the user was added to the `video` group).

## 2 · Use

| Step | What you do | What happens |
|---|---|---|
| 1 | Double-click **FundusScan** | Server starts, Chromium opens as an app window |
| 2 | Enter patient ID / age / eye | ID is auto-generated; everything else is optional |
| 3 | Align the lens on the eye | The ring turns green when the live checks pass (red reflex, focus, light) |
| 4 | Press the orange button (or Space) | Photo → quality gate → AI grade, ≈ 3 s on the Pi 5 |
| 5 | Read the report | Grade, referral advice, severity scale, images, quality table, method |
| 6 | **Print / Save PDF**, **Retake** or **New scan** | Every scan is kept under `scans/<id>/` and listed in **History** |

You can also grade a saved photo with **Upload**, and open the app from a phone or laptop on the same Wi-Fi at
`http://<pi-ip>:8000`.

### The diagnosis report

```
┌──────────────────────────────────────────────────────────────┐
│ ◉ Diabetic Retinopathy Screening Report         ID · date    │
│ Patient · age · sex · eye · diabetes yrs · quality · time    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Grade 2 — Moderate NPDR      REFER        Referable: YES │ │
│ └──────────────────────────────────────────────────────────┘ │
│ [ No DR | Mild | Moderate ▲ | Severe | Proliferative ]       │
│ [ captured fundus ]          [ enhanced view used by AI ]    │
│ Quality checks table         ICDR scale (current row lit)    │
│ Method · model · test metrics · thresholds · notes           │
│ Disclaimer · Screened by ____  Reviewed by ____              │
└──────────────────────────────────────────────────────────────┘
```

| Grade | Report action |
|---|---|
| 0 No DR | No referral — re-screen in 12 months |
| 1 Mild NPDR | No referral — re-screen in 6–12 months |
| 2 Moderate NPDR | Refer to an ophthalmologist (≈ 3 months) |
| 3 Severe NPDR | Urgent referral (≈ 4 weeks) |
| 4 Proliferative DR | Urgent referral (≈ 1 week) |
| — Not gradable | Retake the photo (blur / light / not a retina) |

The confidence label is **Borderline** when the model score is within 0.15 of a grade threshold.

## 3 · Options

| Variable | Default | Meaning |
|---|---|---|
| `FUNDUS_CAMERA` | `usb` | `usb` (prototype v1 webcam) or `picam` (Camera Module 3 via Picamera2) |
| `FUNDUS_CAMERA_INDEX` | `0` | USB camera index |
| `FUNDUS_PORT` | `8000` | Web port |
| `FUNDUS_MODEL` | from `config.json` | Path to another ONNX model |
| `FUNDUS_FAKE_IMAGE` | — | Use a still image instead of a camera (demo / testing) |

```bash
./start_ui.sh --kiosk                       # full screen, no browser bars (touch display)
FUNDUS_CAMERA=picam ./start_ui.sh           # Pi camera module
FUNDUS_FAKE_IMAGE=../assets/sample_fundus_synthetic.png ./start_ui.sh   # demo without a camera
```

## 4 · Command-line tools

```bash
./check_camera.sh             # list cameras, save camera_test.jpg, print brightness/sharpness/red-green
./run.sh --usbcam             # capture and grade in the terminal
./run.sh eye.jpg --json       # grade a saved photo, JSON output
```

## Files

```
device/
├── install.sh        one-time installer + desktop icon (+ --autostart)
├── start_ui.sh       what the icon runs: starts server.py, opens Chromium
├── run.sh            CLI grading (pi_inference.py) inside the venv
├── check_camera.sh   camera test
├── server.py         Flask: camera thread, /stream, /api/capture, /api/analyze, reports, history
├── pi_inference.py   gates + pre-processing + ONNX model (also usable on its own)
├── config.json       thresholds, quality limits, test metrics
├── static/           index.html (app) · report.html (printable report) · icon.svg · fonts/
├── models/           put dr_model_fp32.onnx here
└── scans/            created at run time — one folder per scan (frame, fundus, enhanced, report.json)
```

## API (for integration)

| Method | Path | Returns |
|---|---|---|
| GET | `/api/status` | camera + model state |
| GET | `/stream` | MJPEG live preview |
| GET | `/api/live` | live quality checks |
| POST | `/api/capture` | `{"patient": {...}}` → full report JSON |
| POST | `/api/analyze` | multipart `photo` (+ `patient` JSON) → report JSON |
| GET | `/api/history` · `/api/scan/<id>` | saved scans |
| GET | `/report?id=<id>` | printable report page |

Wiring: [`../hardware/wiring.md`](../hardware/wiring.md) — IR LEDs GPIO18 · white flash GPIO19 · capture button GPIO17.

> **Research prototype — a screening aid, not a medical diagnosis.** Not clinically validated.
