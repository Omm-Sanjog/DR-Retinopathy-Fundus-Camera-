Optional: put `dr_model_fp32.onnx` here to give the web app a different model from the Pi.
If this folder has no model, the build uses `../device/models/dr_model_fp32.onnx`.
Commit the file normally (16 MB) — **not** with Git LFS, or Vercel will only see the pointer file.
