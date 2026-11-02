// Builds the static site into web/dist (Vercel serves that folder).
// Pulls shared files from the rest of the repo so there is ONE copy of each:
//   ../device/config.json         thresholds, quality limits, test metrics (same as the Pi)
//   ../device/models/*.onnx       the trained model (or put it in web/models/)
//   ../device/static/fonts        Barlow fonts
//   ../assets/sample_fundus_synthetic.png
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";

const web = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const repo = path.join(web, "..");
const dist = path.join(web, "dist");
const cp = (from, to) => { fs.mkdirSync(path.dirname(to), { recursive: true }); fs.copyFileSync(from, to); };
const first = (...c) => c.find((p) => fs.existsSync(p));

fs.rmSync(dist, { recursive: true, force: true });
fs.cpSync(path.join(web, "src"), dist, { recursive: true });

// ONNX Runtime Web (WebAssembly build only - ~14 MB wasm, cached by the service worker)
const ortVer = JSON.parse(fs.readFileSync(path.join(web, "node_modules", "onnxruntime-web", "package.json"), "utf8")).version;
const ortDir = path.join(web, "node_modules", "onnxruntime-web", "dist"), ortBase = `ort/${ortVer}/`;
const ortFiles = ["ort.wasm.min.js", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm"];
for (const f of ortFiles) cp(path.join(ortDir, f), path.join(dist, ortBase, f));

// shared files
cp(path.join(repo, "device", "config.json"), path.join(dist, "config.json"));
fs.cpSync(path.join(repo, "device", "static", "fonts"), path.join(dist, "fonts"), { recursive: true });
cp(path.join(repo, "assets", "sample_fundus_synthetic.png"), path.join(dist, "sample.png"));

const model = first(path.join(web, "models", "dr_model_fp32.onnx"), path.join(repo, "device", "models", "dr_model_fp32.onnx"));
let modelUrl = null, modelBytes = 0, modelInfo = "missing";
if (model && fs.statSync(model).size > 1e6) {
  const buf = fs.readFileSync(model), hash = crypto.createHash("sha256").update(buf).digest("hex").slice(0, 10);
  modelUrl = `models/${hash}/dr_model_fp32.onnx`; modelBytes = buf.length;
  cp(model, path.join(dist, modelUrl));
  modelInfo = `${(buf.length / 1e6).toFixed(1)} MB, sha256 ${hash}, from ${path.relative(repo, model)}`;
} else {
  console.warn("\n!! dr_model_fp32.onnx not found (or it is a Git LFS pointer).");
  console.warn("!! Commit it to device/models/ (or web/models/). The site still builds, but grading is disabled.\n");
}

// fill in build placeholders
const build = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
const keep = [...ortFiles.map((f) => ortBase + f), ...(modelUrl ? [modelUrl] : [])];
const sub = (f, pairs) => { const p = path.join(dist, f); let t = fs.readFileSync(p, "utf8"); for (const [k, v] of pairs) t = t.split(k).join(v); fs.writeFileSync(p, t); };
sub("sw.js", [["__BUILD__", build], ["__KEEP__", JSON.stringify(keep)]]);
sub("index.html", [["__ORT__", ortBase + "ort.wasm.min.js"]]);
fs.writeFileSync(path.join(dist, "build.json"), JSON.stringify({ build, ort: ortVer, ortBase, model: !!modelUrl, modelUrl, modelBytes, modelInfo }, null, 1));
console.log(`FundusScan Web built -> web/dist  (build ${build}, model: ${modelInfo})`);
