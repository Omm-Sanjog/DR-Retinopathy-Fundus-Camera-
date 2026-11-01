# Models

Copy the trained model here from `dr_pi_bundle.zip` (produced by the Colab notebook):

| File | Size | Status |
|---|---|---|
| `dr_model_fp32.onnx` | 16.0 MB | **Deployed** (test QWK 0.877) — required |
| `dr_model_int8.onnx` | 4.8 MB | Optional — rejected in the 2026-10-31 run (test QWK 0.570) |
| `best_model.pt` | 16.3 MB | Optional — PyTorch weights for fine-tuning |

All are below GitHub's 100 MB file limit, so they can be committed directly.
`config.json` (one level up) points to `models/dr_model_fp32.onnx`.
