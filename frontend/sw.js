const CACHE_NAME = "assosa-ledger-v2";
const SHELL_FILES = [
  "/",
  "/index.html",
  "/manifest.json",
  "/icon-192.png",
  "/icon-512.png",
  "/apple-touch-icon.png",
  "/favicon-32.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

// Only handle GET requests for our own shell files.
// Everything else (API calls to Render) goes straight to the network, untouched.
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // let API calls pass through untouched

  // The app itself (the page and its logic) must always come from the
  // network first, so a new deploy is never masked by a stale cached copy.
  // Cache is only used as a fallback if the device is actually offline.
  const isAppShell = req.mode === "navigate" || url.pathname === "/" || url.pathname.endsWith("/index.html");
  if (isAppShell) {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          if (resp.ok) {
            const copy = resp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return resp;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Static assets (icons, manifest) rarely change, so cache-first is fine here.
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((resp) => {
        if (resp.ok) {
          const copy = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
        }
        return resp;
      });
    })
  );
});
