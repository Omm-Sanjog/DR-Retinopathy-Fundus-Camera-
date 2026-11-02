/* FundusScan Web service worker - offline support.
 * Big files (ONNX Runtime wasm, the model) live under versioned paths and are cached once.
 * Everything else is network-first, so a new deployment shows up immediately when online. */
const BUILD = "__BUILD__";
const SHELL = "fundusscan-shell-" + BUILD;
const BIG = "fundusscan-big";
const KEEP = __KEEP__;   // versioned big files of this build
const PRECACHE = ["./", "index.html", "styles.css", "app.js", "fundus.js", "config.json", "build.json", "icon.svg", "manifest.webmanifest", "sample.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith("fundusscan-shell-") && k !== SHELL) await caches.delete(k);
    const big = await caches.open(BIG);
    for (const req of await big.keys()) if (!KEEP.includes(new URL(req.url).pathname.replace(/^.*?\/(ort|models)\//, "$1/"))) await big.delete(req);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (/\/(ort|models)\//.test(url.pathname)) {                       // cache-first, immutable
    e.respondWith(caches.open(BIG).then(async (c) => {
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok) c.put(req, res.clone());
      return res;
    }));
    return;
  }
  e.respondWith((async () => {                                        // network-first
    try {
      const res = await fetch(req);
      if (res.ok) (await caches.open(SHELL)).put(req, res.clone());
      return res;
    } catch {
      return (await caches.match(req)) || (req.mode === "navigate" ? caches.match("index.html") : Response.error());
    }
  })());
});
