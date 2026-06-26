/* ==========================================================================
   service-worker.js — minimal PWA support, honest about the backend (STORY_024).

   Strategy:
     - Static assets (/static/*, manifest, icons, the HTMX CDN file):
       cache-first, so the shell chrome + the offline page load instantly.
     - Pages and HTMX partials: NETWORK-ONLY. Rendered content is never cached
       or served from cache — a live server always wins, and a stopped one can
       NEVER masquerade as live by serving a stale page. When a full navigation
       can't reach the server, we serve an honest "Server not running" page
       instead; a failed partial simply doesn't swap (no stale fragment).
     - Non-GET requests (POST/PUT/DELETE) are never cached or intercepted.

   Why no offline app-shell: this is an internal tool that does nothing without
   its backend, so a cached page with no server is worse than useless — it's
   misleading. We trade offline browsing for never being shown stale data.

   Bump CACHE_VERSION whenever you want clients to drop the old cache.
   ========================================================================== */

const CACHE_VERSION = "ogtv-writer-v2";
const OFFLINE_URL = "/static/offline.html";

// Precached on install so static chrome + the offline page work when the server
// is unreachable.
const PRECACHE_URLS = [
  OFFLINE_URL,
  "/static/css/app.css",
  "/static/js/app.js",
  "/static/icons/icon.svg",
  "/manifest.webmanifest",
  "https://unpkg.com/htmx.org@2.0.3",
];

// Last-resort offline page if the precache of OFFLINE_URL ever failed.
function offlineFallback() {
  return new Response(
    "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" +
      "<title>Server not running</title>" +
      "<body style=\"font-family:system-ui,sans-serif;background:#0b0f17;color:#e2e8f0;display:grid;place-items:center;height:100vh;margin:0\">" +
      "<div style='text-align:center;max-width:24rem;padding:1rem'>" +
      "<h1 style='font-size:1.25rem'>Server not running</h1>" +
      "<p style='color:#94a3b8'>OGTV Writer can't reach its backend. Start the container, then reload.</p>" +
      "<button onclick='location.reload()' style='padding:.5rem 1rem;border-radius:.5rem;border:0;background:#a78bfa;color:#0b0f17;font-weight:600;cursor:pointer'>Reload</button>" +
      "</div>",
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
  );
}

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
    return;
  }

  // Pages + HTMX partials: network-only, never cached. On failure, a navigation
  // gets the honest offline page; anything else (a partial) gets a 503 so HTMX
  // shows an error instead of swapping in stale content.
  event.respondWith(
    fetch(req).catch(async () => {
      if (req.mode === "navigate") {
        return (await caches.match(OFFLINE_URL)) || offlineFallback();
      }
      return new Response("", { status: 503, statusText: "Server unreachable" });
    })
  );
});
