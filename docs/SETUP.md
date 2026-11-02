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
# 1. Get the code (once)
git clone https://github.com/Omm-Sanjog/DR-Retinopathy-Fundus-Camera-.git
cd DR-Retinopathy-Fundus-Camera-/device

# 2. Model (once) — copy from dr_pi_bundle.zip
cp /path/to/dr_model_fp32.onnx models/

# 3. Install (once) — packages, venv, self-test, FundusScan desktop icon
bash install.sh                 # or: bash install.sh --autostart   (opens full screen at boot)
```

**Every time:** double-click the **FundusScan** icon. Enter the patient ID, align until the ring turns green,
press the orange button — the diagnosis report opens automatically (Print / Save PDF from there).

Terminal alternatives:

```bash
./start_ui.sh --kiosk                       # full-screen UI
FUNDUS_CAMERA=picam ./start_ui.sh           # Camera Module 3 (v2)
./check_camera.sh                           # camera + image-quality test
./run.sh --usbcam                           # grade one capture in the terminal
./run.sh eye.jpg --json                     # JSON output
```

## C. Laptop / PC (for testing without the device)

```bash
git clone https://github.com/Omm-Sanjog/DR-Retinopathy-Fundus-Camera-.git
cd DR-Retinopathy-Fundus-Camera-/device
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python pi_inference.py ../assets/sample_fundus_synthetic.png
# full UI without a camera:
FUNDUS_FAKE_IMAGE=../assets/sample_fundus_synthetic.png python server.py   # then open http://localhost:8000
```

## D. Phone / web version (Vercel, branch `web-app`)

```bash
# deploy: commit device/models/dr_model_fp32.onnx, import the repo on vercel.com, choose this branch
# local test:
cd web && npm install && npm run dev        # http://localhost:5173
```

On the phone: open the site → *Add to Home Screen* → tap **FundusScan** → **Start lens camera**.
Full guide: [`web/README.md`](../web/README.md).

## Troubleshooting

| Problem | Fix |
|---|---|
| `Could not open USB camera 0` | Try `--usbcam 1`; check `ls /dev/video*` |
| “does not look like a retina photo” | Lens ~5 cm from the eye, dim room, find the red reflex, refocus with the side lever |
| “image looks blurry” | Adjust the camera carriage until vessels are sharp |
| Colab “Failed to assign a backend” | No free GPU right now — pick CPU runtime; the notebook adapts automatically |
| Icon does nothing / “Not installed yet” | Run `bash install.sh` in `device/`; see `device/server.log` |
| Report says “Model not loaded” | Copy `dr_model_fp32.onnx` into `device/models/` |
| Web build log says `model: missing` | Commit `dr_model_fp32.onnx` to `device/models/` without Git LFS |
| Web: camera does not open | The site must be HTTPS (Vercel is); allow camera permission in browser settings |
| ~3 s per image on the Pi | Expected for FP32 at 384 px; see roadmap for optimisation |

> Research prototype — not for diagnostic use.
