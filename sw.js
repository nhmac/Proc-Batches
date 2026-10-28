// Gerado pelo build_pages.py
const CACHE = "autobatch-e3e043a4dee1";
const FICHEIROS = ["./", "fonts/Inter_18pt-Regular.ttf", "fonts/Inter_18pt-SemiBold.ttf", "fonts/OFL.txt", "icon-192.png", "icon-512.png", "icone.ico", "index.html", "manifest.webmanifest", "vendor/pdfjs/LICENSE", "vendor/pdfjs/pdf.min.js", "vendor/pdfjs/pdf.worker.min.js"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FICHEIROS)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(chaves => Promise.all(chaves.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Rede primeiro: com internet vê-se sempre a versão publicada; sem internet usa a cópia guardada
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r.ok) {
          const copia = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, copia));
        }
        return r;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
