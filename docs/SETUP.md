# Setup guide

```
  [ Colab: train ]  ──►  dr_pi_bundle.zip  ──►  [ Raspberry Pi 5: grade offline ]
```

## A. Train the model (Google Colab, ≈ 25 min on a T4)

1. Open `training/DR_Fundus_Training.ipynb` in Colab (button in the main README).
2. `Runtime → Change runtime type → T4 GPU` (CPU also works with lighter settings).
3. `Runtime → Run all`. APTOS 2019 downloads automatically from Hugging Face.
4. At the end `dr_pi_bundle.zip` downloads — it contains `dr_model_fp32.onnx`, `config.json` and `pi_inference.py`.

Optional: paste `training/colab_upload_and_analyse.py` into a new cell to grade photos from your laptop.

## B. Raspberry Pi 5 (Raspberry Pi OS Bookworm, 64-bit)

```bash
# 1. System packages (once)
sudo apt update && sudo apt install -y python3-venv git rpicam-apps

# 2. Get the code (once)
git clone https://github.com/Omm-Sanjog/DR-Retinopathy-Fundus-Camera-.git
cd DR-Retinopathy-Fundus-Camera-/raspberry-pi

# 3. Python environment (once)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Model (once) — copy from dr_pi_bundle.zip
cp /path/to/dr_model_fp32.onnx models/

# 5. Run (every time)
source venv/bin/activate
python3 pi_inference.py ../assets/sample_fundus_synthetic.png   # self-test
python3 pi_inference.py --usbcam                                 # prototype v1 (USB webcam)
python3 pi_inference.py --camera                                 # Camera Module 3 (v2)
python3 pi_inference.py eye.jpg --json                           # JSON output
```

## C. Laptop / PC (for testing without the device)

```bash
git clone https://github.com/Omm-Sanjog/DR-Retinopathy-Fundus-Camera-.git
cd DR-Retinopathy-Fundus-Camera-/raspberry-pi
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python pi_inference.py ../assets/sample_fundus_synthetic.png
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Could not open USB camera 0` | Try `--usbcam 1`; check `ls /dev/video*` |
| “does not look like a retina photo” | Lens ~5 cm from the eye, dim room, find the red reflex, refocus with the side lever |
| “image looks blurry” | Adjust the camera carriage until vessels are sharp |
| Colab “Failed to assign a backend” | No free GPU right now — pick CPU runtime; the notebook adapts automatically |
| ~3 s per image on the Pi | Expected for FP32 at 384 px; see roadmap for optimisation |

> Research prototype — not for diagnostic use.
