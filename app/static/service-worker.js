/* ==========================================================================
   service-worker.js — basic PWA offline support (the "app shell" pattern).

   Strategy:
     - Static assets (/static/*, manifest, icons, the HTMX CDN file):
       cache-first, so the shell loads instantly and works offline.
     - Everything else (pages, HTMX partials):
       network-first, falling back to cache when offline.
     - Non-GET requests (POST/PUT/DELETE) are never cached or intercepted.

   Bump CACHE_VERSION whenever you want clients to drop the old cache.

   PRIVACY NOTE: network-first caching stores rendered pages. On a SHARED
   device that could expose one user's pages to another. For multi-user apps,
   restrict caching to truly static paths (see the `isStatic` check).
   ========================================================================== */

const CACHE_VERSION = "ogtv-writer-v1";

// Precached on install so the shell works on first offline load.
const PRECACHE_URLS = [
  "/static/css/app.css",
  "/static/js/app.js",
  "/static/icons/icon.svg",
  "/manifest.webmanifest",
  "https://unpkg.com/htmx.org@2.0.3",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      // Don't fail install if one URL (e.g. an unbuilt app.css) is missing.
      Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url)))
    )
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return; // never touch mutations

  const url = new URL(req.url);
  const isStatic =
    url.pathname.startsWith("/static/") ||
    url.pathname === "/manifest.webmanifest" ||
    url.hostname === "unpkg.com";

  if (isStatic) {
    // Cache-first.
    event.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            const copy = res.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(req, copy));
            return res;
          })
      )
    );
  } else {
    // Network-first, fall back to cache when offline.
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (url.origin === self.location.origin) {
            const copy = res.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
  }
});
