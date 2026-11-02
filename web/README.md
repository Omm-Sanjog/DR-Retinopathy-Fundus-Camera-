# FundusScan Web — DR screening on any phone

```
   ___             _         ___                __      __   _    
  | __|  _ _ _  __| |_  _ __/ __| __ __ _ _ _   \ \    / /__| |__ 
  | _| || | ' \/ _` | || (_-<__ \/ _/ _` | ' \   \ \/\/ / -_) '_ \
  |_| \_,_|_||_\__,_|\_,_/__/___/\__\__,_|_||_|   \_/\_/\___|_.__/
                                                                  

   📱 phone + 20 D lens ──► live checks ──► auto-capture ──► AI grade ──► 📄 report
          (lens kit)        retina·focus·    sharpest       on the phone   share / PDF
                            light·size       frame          (no upload)
```

The same model, pre-processing and report as the Raspberry Pi app, running **inside the phone's browser**.
Open the website, point the phone (with a fundus lens kit) at the eye, and the full diagnosis report appears on the phone.
Photos are never uploaded — Vercel only serves the static files.

## How it works

```
 ┌──────────────── Vercel (static hosting only) ───────────────┐
 │ index.html · app.js · fundus.js · config.json               │
 │ ort/1.30.0/*.wasm (ONNX Runtime Web) · models/<hash>/*.onnx │
 └──────────────────────────────┬──────────────────────────────┘
                                │ downloaded once (~30 MB), then cached → works offline
 ┌──────────────────────────────▼──────────────────────────────┐
 │ PHONE BROWSER                                               │
 │  camera ─► find retina circle ─► quality gate ─► Ben Graham │
 │         ─► EfficientNet-B0 (WebAssembly) ─► grade + report  │
 │  history in IndexedDB (this device only)                    │
 └─────────────────────────────────────────────────────────────┘
```

| | Raspberry Pi app (`device/`) | Web app (`web/`) |
|---|---|---|
| Camera | USB webcam / Pi camera in the 3D-printed body | Any phone camera + lens kit |
| Model | `dr_model_fp32.onnx` (ONNX Runtime, Python) | Same file (ONNX Runtime Web, WebAssembly) |
| Pre-processing | `pi_inference.py` | `fundus.js` — line-by-line port, verified against Python |
| Start | Desktop icon | Website / home-screen icon (installable PWA) |
| Report | Print / PDF | Print / PDF + share image (WhatsApp etc.) |
| Data | Saved on the Pi | Saved in the phone's browser only |

**Verified parity** (same images, same model): quality metrics and red/green ratio identical to Python;
model input differs by ≤ 4 grey levels on ~1 % of pixels; model score within ~0.04.

## Features

- **Live lens camera** — the retina circle is found automatically; Retina / Focus / Light / Size turn green, then it
  **auto-captures the sharpest frame** of the last ~1.3 s. Torch and zoom buttons where the phone allows.
- **Camera app** (full-resolution photo) and **Photo library** inputs.
- **Retina-circle review** — drag/resize the circle; face and lens rim outside it are ignored.
- **Diagnosis report** — grade, referral advice, severity bar, captured + enhanced images, quality table,
  ICDR scale, method/metrics, disclaimer and signature lines. **Print / Save PDF**, **Share** (summary image + text).
- **History** of scans on the phone; **installable** (Add to Home Screen) and **offline** after the first load.

## Deploy on Vercel (this branch)

1. Commit the trained model to **`device/models/dr_model_fp32.onnx`** (normal Git, not LFS — 16 MB is fine).
2. [vercel.com/new](https://vercel.com/new) → import `Omm-Sanjog/DR-Retinopathy-Fundus-Camera-`.
3. Leave **Root Directory** as the repository root and Framework as **Other** — `vercel.json` already sets
   install `npm ci --prefix web`, build `npm run build --prefix web`, output `web/dist`, plus the headers.
4. Deploy. Every push to this branch gets a preview URL. To make it the main site:
   *Project → Settings → Environments → Production → Branch* = `web-app` (or whatever you named the branch).
5. Open the URL on a phone → **Add to Home Screen** → tap the FundusScan icon.

The build log prints `model: 15.9 MB, sha256 …`. If it says `model: missing`, the site still works for
image-quality checks but cannot grade.

## Run locally

```bash
cd web
npm install
npm run dev          # builds to web/dist and serves http://localhost:5173
```

The camera needs **HTTPS** (or `localhost`). To test on a phone before deploying, use the Vercel preview URL,
or a tunnel such as `npx localtunnel --port 5173`.

## Using a lens kit

```
   eye        20 D lens                         phone (torch on)
  (  ●)  ←≈5 cm→  ( )  ←──────── 15–40 cm ────────→  [▯]
```

1. 20 D (or 28 D) aspheric lens, ideally on a clip/adapter in line with the phone's main camera.
2. Dim room; dilated pupil gives far better images (only as advised by a clinician).
3. Torch on, lens ~5 cm from the eye, move the phone until the red reflex fills the lens.
4. Move slowly back and forth until the vessels are sharp — the app captures automatically.
5. Keep each attempt short (under ~1 minute of torch light per eye).

## Files

```
vercel.json              build + headers (repo root, so Vercel needs no settings)
web/
├── package.json         onnxruntime-web 1.30.0 (pinned) · build / dev scripts
├── scripts/build.mjs    copies src + ORT wasm + model + ../device/config.json → dist/
├── scripts/serve.mjs    local server with the same headers as Vercel
├── models/              optional web-only model (otherwise ../device/models is used)
└── src/
    ├── index.html       screens: home · live camera · review · report · history · guide
    ├── app.js           camera, auto-capture, review, report, share, history, PWA
    ├── fundus.js        pre-processing + quality gates + model (port of pi_inference.py)
    ├── styles.css       mobile-first, light/dark, print layout
    ├── sw.js            offline cache · manifest.webmanifest · icons/
```

`config.json` (thresholds, quality limits, metrics) is taken from `device/` at build time, so the Pi and the web
app can never disagree.

## Limits

- The model was trained on APTOS clinic fundus-camera images. Phone + lens images differ (field of view,
  reflections, colour), so **re-calibrate the quality limits and validate on real phone images** before relying on it.
- Inference on a mid-range phone takes ~0.5–3 s (WebAssembly, multi-threaded where supported).
- iPhone browsers do not expose the torch to websites — use the lens kit's own light or the **Camera app** button with flash.

> **Research prototype — a screening aid, not a medical diagnosis.** Not clinically validated.
