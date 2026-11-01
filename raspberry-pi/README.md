# Raspberry Pi 5 — on-device DR grading

```
   _____ _
  |  __ (_)   pi_inference.py
  | |__) |    capture → quality gate → fundus gate → pre-process → EfficientNet-B0 (ONNX) → grade
  |  ___/ |
  |_|   |_|   offline · CPU only · 3 Python packages
```

## Setup (Raspberry Pi OS Bookworm, 64-bit)

```bash
sudo apt update && sudo apt install -y python3-venv rpicam-apps
cd DR-Retinopathy-Fundus-Camera-/raspberry-pi
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# copy dr_model_fp32.onnx from dr_pi_bundle.zip into models/
```

## Usage

```bash
python3 pi_inference.py ../assets/sample_fundus_synthetic.png   # test image
python3 pi_inference.py eye.jpg                                   # analyse a photo
python3 pi_inference.py --camera                                  # capture with Pi camera, then analyse
python3 pi_inference.py eye.jpg --json                            # JSON output
python3 pi_inference.py eye.jpg --model models/dr_model_int8.onnx # try another model
```

## Output fields

| Field | Meaning |
|---|---|
| `grade`, `grade_name` | ICDR grade 0–4 |
| `score` | Continuous model score (before thresholds) |
| `referable` | `true` if grade ≥ 2 → refer to an ophthalmologist |
| `image_ok`, `quality_issues` | Gate verdict and reasons (blur, too dark/bright, not a retina) |
| `fundus_rg` | Median red/green ratio (retina ≳ 1.6) |
| `inference_ms`, `model` | Model latency and file used |

## Configuration (`config.json`)

- `thresholds` — `[0.58, 1.08, 1.88, 2.72]`, tuned on validation in the training run
- `quality` — sharpness ≥ 9.63, brightness 27.8–114.2 (derived from APTOS; re-calibrate for your camera)
- `fundus_rg_min` — 1.6
- `recommended_model` — `models/dr_model_fp32.onnx`

## Wiring

See [`../hardware/wiring.md`](../hardware/wiring.md). IR LEDs: GPIO18 (PWM0) · white flash: GPIO19 (PWM1) · capture button: GPIO17.

> Research prototype — not for diagnostic use.
