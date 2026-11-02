// Tiny static server for local testing with the same headers as vercel.json.
//   npm run dev     ->  http://localhost:5173   (use your PC's IP from a phone; camera needs HTTPS or localhost)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "dist");
const port = +process.env.PORT || 5173;
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".webmanifest": "application/manifest+json", ".wasm": "application/wasm", ".onnx": "application/octet-stream",
  ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".woff2": "font/woff2" };
http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  const f = path.join(root, path.normalize(p).replace(/^(\.\.[/\\])+/, ""));
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream",
      "Cross-Origin-Opener-Policy": "same-origin", "Cross-Origin-Embedder-Policy": "require-corp", "Cache-Control": "no-cache" });
    res.end(data);
  });
}).listen(port, () => console.log(`FundusScan Web on http://localhost:${port}`));
