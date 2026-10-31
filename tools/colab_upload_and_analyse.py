# Paste this into a Colab cell (after training, or in a fresh session with dr_pi_bundle.zip).
#@title 📷 Upload a fundus image from your laptop and analyse it
# Works in two ways:
#  • Right after training in this session (uses the exported model automatically), or
#  • In a FRESH Colab session: when asked, upload dr_pi_bundle.zip first, then your image(s).
import os, sys, zipfile, importlib.util
import cv2, numpy as np, matplotlib.pyplot as plt
from google.colab import files

!pip -q install onnxruntime

BUNDLE = "/content/dr_project/export"          # where the training notebook saved the model
if not os.path.exists(f"{BUNDLE}/pi_inference.py"):
    print("No trained model in this session → upload dr_pi_bundle.zip")
    up = files.upload()
    zname = next(n for n in up if n.endswith(".zip"))
    BUNDLE = "/content/dr_bundle"
    with zipfile.ZipFile(zname) as z:
        z.extractall(BUNDLE)

# Load the same inference code that runs on the Raspberry Pi
spec = importlib.util.spec_from_file_location("pi_inference", f"{BUNDLE}/pi_inference.py")
pi = importlib.util.module_from_spec(spec); sys.modules["pi_inference"] = pi; spec.loader.exec_module(pi)
dr = pi.DRModel()
print(f"✅ Model loaded: {dr.model_file}\n")

def looks_like_fundus(rgb):
    """Rough check: retina photos are strongly RED-dominant (red/green ratio ~2 or more).
    Skin, sclera and front-of-eye photos sit around 1.2-1.4."""
    img = cv2.resize(rgb, (256, 256)).astype(np.float32)
    lit = img.mean(axis=2) >= 20                      # ignore black background
    if lit.mean() < 0.05:
        return False, 0.0
    rg = float(np.median(img[..., 0][lit] / (img[..., 1][lit] + 1)))
    return rg >= 1.6, rg

print("Choose one or more fundus images (jpg/png) from your laptop:")
uploaded = files.upload()

for name in uploaded:
    bgr = cv2.imread(name)
    if bgr is None:
        print(f"❌ {name}: not an image, skipped"); continue
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    is_fundus, frac = looks_like_fundus(rgb)
    r = dr.predict(rgb)

    fig, ax = plt.subplots(1, 2, figsize=(11, 5.5))
    ax[0].imshow(rgb); ax[0].set_title("Uploaded"); ax[0].axis("off")
    ax[1].imshow(pi.preprocess_fundus(rgb, dr.cfg["img_size"]))
    ax[1].set_title("What the model sees"); ax[1].axis("off")
    plt.suptitle(name); plt.tight_layout(); plt.show()

    print("=" * 56)
    print(f" File       : {name}")
    if not is_fundus:
        print(f" ❌ This does NOT look like a retina (fundus) photo "
              f"(red/green ratio {frac:.2f}, retina is usually > 1.6).")
        print("    The grade below is NOT meaningful. Retake: lens ~5 cm from eye,")
        print("    camera 30-50 cm back, light in line with camera, dark room.")
    if not r["image_ok"]:
        print(f" ⚠️  Quality: {', '.join(r['quality_issues'])} → retake recommended")
    print(f" Grade      : {r['grade']} - {r['grade_name']}   (score {r['score']})")
    print(f" Referable  : {'YES - refer to an ophthalmologist' if r['referable'] else 'No'}")
    print(f" Inference  : {r['inference_ms']} ms")
    print("=" * 56)
    print(" Prototype screening aid only — not a medical diagnosis.\n")
