/* ==============================================================================
   CTAS (Coastal Threat Alert System) - Service Worker
   Offline Support, App Shell, Tile Caching, and Resilience Layer
   ============================================================================== */

const CACHE_VERSION = 'v1';
const SHELL_CACHE = `ctas-shell-${CACHE_VERSION}`;
const TILE_CACHE = `ctas-tiles-${CACHE_VERSION}`;
const DATA_CACHE = `ctas-data-${CACHE_VERSION}`;

const MAX_TILES_IN_CACHE = 250;

// Core App Shell Resources
const APP_SHELL_URLS = [
  '/',
  '/frontend.html',
  '/map.html',
  '/posts.html',
  '/trends.html',
  '/manifest.json',
  '/offline-store.js',
  '/frontend/i18n/i18n.js',
  '/frontend/i18n/en.json',
  '/frontend/i18n/hi.json',
  '/frontend/i18n/ta.json',
  '/frontend/i18n/ml.json',
  '/frontend/i18n/bn.json',
  '/frontend/i18n/or.json',
  '/frontend/i18n/gu.json',
  '/frontend/i18n/kok.json',
  '/icons/icon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/logo-sakshi.jpg',
  // External CDNs used by CTAS
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@600;700&display=swap',
  'https://unpkg.com/@phosphor-icons/web@2.0.3/src/css/icons.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/leaflet.heat/dist/leaflet-heat.js'
];

// Default offline emergency contacts payload
const OFFLINE_EMERGENCY_DATA = {
  status: 'offline',
  timestamp: new Date().toISOString(),
  emergency_contacts: [
    { agency: 'National Disaster Helpline', number: '1078', type: 'Toll-Free' },
    { agency: 'State Coastal Emergency Center', number: '1070', type: 'Emergency Operations' },
    { agency: 'District Disaster Management', number: '1077', type: 'District' },
    { agency: 'Indian Coast Guard SAR', number: '1554', type: 'Maritime Rescue' },
    { agency: 'National Disaster Response Force (NDRF)', number: '011-24363260', type: 'Rescue & Evacuation' },
    { agency: 'National Emergency Number', number: '112', type: 'Police / Fire / Medical' },
    { agency: 'Ambulance & Trauma Services', number: '108', type: 'Medical' }
  ],
  offline_notice: 'You are viewing pre-cached emergency guidelines and contact information.'
};

// -----------------------------------------------------------------------------
// 1. Installation: Pre-cache App Shell
// -----------------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(async (cache) => {
      // Use individual fetches with error resilience so one CDN issue won't fail the whole install
      await Promise.all(
        APP_SHELL_URLS.map(async (url) => {
          try {
            const req = new Request(url, { mode: url.startsWith('http') ? 'cors' : 'same-origin' });
            const res = await fetch(req);
            if (res.ok) {
              await cache.put(url, res);
            }
          } catch (err) {
            console.warn(`[SW] Shell item prefetch skipped for: ${url}`, err.message);
          }
        })
      );
      return self.skipWaiting();
    })
  );
});

// -----------------------------------------------------------------------------
// 2. Activation: Clean up stale caches
// -----------------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(async (keys) => {
      const allowedCaches = [SHELL_CACHE, TILE_CACHE, DATA_CACHE];
      await Promise.all(
        keys.map((key) => {
          if (!allowedCaches.includes(key)) {
            console.log(`[SW] Purging deprecated cache: ${key}`);
            return caches.delete(key);
          }
        })
      );
      return self.clients.claim();
    })
  );
});

// -----------------------------------------------------------------------------
// Helper: Maintain LRU size in Tile Cache
// -----------------------------------------------------------------------------
async function trimCache(cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > maxItems) {
    const itemsToDelete = keys.slice(0, keys.length - maxItems);
    await Promise.all(itemsToDelete.map((key) => cache.delete(key)));
  }
}

// -----------------------------------------------------------------------------
// 3. Fetch Event Routing & Resilience
// -----------------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // A. Leaflet Map Tiles (OpenStreetMap & similar tile providers)
  // Cache-First with Network fallback & dynamic caching
  if (url.hostname.includes('tile.openstreetmap.org') || url.pathname.includes('/tile/')) {
    event.respondWith(
      caches.open(TILE_CACHE).then(async (cache) => {
        const cachedTile = await cache.match(request);
        if (cachedTile) {
          // Return cached tile immediately; refresh in background if online
          fetch(request).then((networkRes) => {
            if (networkRes && networkRes.ok) {
              cache.put(request, networkRes.clone());
            }
          }).catch(() => {});
          return cachedTile;
        }

        try {
          const networkRes = await fetch(request);
          if (networkRes && networkRes.ok) {
            cache.put(request, networkRes.clone());
            trimCache(TILE_CACHE, MAX_TILES_IN_CACHE);
          }
          return networkRes;
        } catch (err) {
          // Fallback: return a transparent 1x1 pixel SVG or cached fallback if missing
          return new Response(
            '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#130b20"/><text x="128" y="128" fill="#5b4878" font-size="12" text-anchor="middle">Offline Map Tile</text></svg>',
            { headers: { 'Content-Type': 'image/svg+xml' } }
          );
        }
      })
    );
    return;
  }

  // B. Alerts API endpoint (/alerts or /api/alerts)
  // Network-First with Cache fallback + X-Cached-At timestamp header
  if (url.pathname === '/alerts' || url.pathname.endsWith('/alerts')) {
    event.respondWith(
      fetch(request)
        .then(async (networkRes) => {
          if (networkRes && networkRes.ok) {
            const cache = await caches.open(DATA_CACHE);
            // Clone response and attach caching timestamp header
            const resClone = networkRes.clone();
            const body = await resClone.blob();
            const headers = new Headers(resClone.headers);
            headers.set('X-Cached-At', new Date().toISOString());
            headers.set('X-CTAS-Cache', 'true');

            const timedResponse = new Response(body, {
              status: resClone.status,
              statusText: resClone.statusText,
              headers: headers
            });

            await cache.put(request, timedResponse.clone());
            // Also store as normalized generic '/alerts' key
            await cache.put(new Request('/alerts'), timedResponse.clone());

            return networkRes;
          }
          return networkRes;
        })
        .catch(async () => {
          const cache = await caches.open(DATA_CACHE);
          const cached = (await cache.match(request)) || (await cache.match('/alerts'));
          if (cached) {
            return cached;
          }
          // Default empty alerts JSON fallback
          return new Response(JSON.stringify([]), {
            headers: { 'Content-Type': 'application/json', 'X-Cached-At': new Date().toISOString(), 'X-CTAS-Offline': 'true' }
          });
        })
    );
    return;
  }

  // C. Evacuation Routes API (/api/evacuation-route or /evacuation/routes)
  if (url.pathname.includes('/evacuation-route') || url.pathname.includes('/evacuation/routes')) {
    if (request.method === 'POST') {
      // POST requests cannot be directly cached with cache.put in standard cache API without matching clone
      event.respondWith(
        fetch(request.clone())
          .then(async (networkRes) => {
            if (networkRes && networkRes.ok) {
              const cache = await caches.open(DATA_CACHE);
              const resClone = networkRes.clone();
              const headers = new Headers(resClone.headers);
              headers.set('X-Cached-At', new Date().toISOString());
              const body = await resClone.blob();
              await cache.put(
                new Request('/last-cached-evacuation-route'),
                new Response(body, { headers })
              );
            }
            return networkRes;
          })
          .catch(async () => {
            const cache = await caches.open(DATA_CACHE);
            const cachedRoute = await cache.match('/last-cached-evacuation-route');
            if (cachedRoute) {
              return cachedRoute;
            }
            // Fallback synthetic route data for offline safety
            const offlineFallbackRoute = {
              status: 'cached_fallback',
              is_offline: true,
              timestamp: new Date().toISOString(),
              distance: 'Offline Estimate (8.4 km)',
              estimated_time: '18 mins (Safe inland arterial)',
              risk_level: 'Moderate',
              route: [
                [13.0827, 80.2707],
                [13.0850, 80.2600],
                [13.0900, 80.2450],
                [13.1000, 80.2300],
                [13.1100, 80.2100]
              ],
              recommendation: 'Proceed directly inland away from coastal shoreline. Head towards designated Shelter Beta.'
            };
            return new Response(JSON.stringify(offlineFallbackRoute), {
              headers: { 'Content-Type': 'application/json', 'X-Cached-At': new Date().toISOString() }
            });
          })
      );
      return;
    } else {
      // GET requests for evacuation routes
      event.respondWith(
        fetch(request)
          .then(async (networkRes) => {
            if (networkRes && networkRes.ok) {
              const cache = await caches.open(DATA_CACHE);
              cache.put(request, networkRes.clone());
            }
            return networkRes;
          })
          .catch(async () => {
            const cache = await caches.open(DATA_CACHE);
            const cached = (await cache.match(request)) || (await cache.match('/last-cached-evacuation-route'));
            if (cached) return cached;
            return new Response(JSON.stringify({ status: 'offline', message: 'Offline routes unavailable.' }), {
              headers: { 'Content-Type': 'application/json' }
            });
          })
      );
      return;
    }
  }

  // D. Emergency Contact Directory endpoint
  if (url.pathname === '/api/emergency-contacts' || url.pathname === '/emergency-contacts') {
    event.respondWith(
      fetch(request)
        .then(async (networkRes) => {
          if (networkRes && networkRes.ok) {
            const cache = await caches.open(DATA_CACHE);
            cache.put(request, networkRes.clone());
          }
          return networkRes;
        })
        .catch(async () => {
          const cache = await caches.open(DATA_CACHE);
          const cached = await cache.match(request);
          if (cached) return cached;
          return new Response(JSON.stringify(OFFLINE_EMERGENCY_DATA), {
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // E. App Shell & Static Assets: Stale-While-Revalidate with Navigation Fallback
  event.respondWith(
    caches.match(request).then(async (cachedResponse) => {
      // If found in cache, return it immediately and revalidate in background
      if (cachedResponse) {
        fetch(request)
          .then(async (networkResponse) => {
            if (networkResponse && networkResponse.ok && request.method === 'GET') {
              const cache = await caches.open(SHELL_CACHE);
              cache.put(request, networkResponse);
            }
          })
          .catch(() => {
            // In offline state, network fails quietly while cachedResponse is already served
          });
        return cachedResponse;
      }

      // Not in cache: fetch from network and cache successful GET responses
      try {
        const networkResponse = await fetch(request);
        if (networkResponse && networkResponse.ok && request.method === 'GET') {
          const isHttp = url.protocol === 'http:' || url.protocol === 'https:';
          if (isHttp && (url.origin === self.location.origin || APP_SHELL_URLS.includes(request.url))) {
            const cache = await caches.open(SHELL_CACHE);
            cache.put(request, networkResponse.clone());
          }
        }
        return networkResponse;
      } catch (error) {
        // Navigation fallback (HTML pages)
        if (request.mode === 'navigate') {
          const cache = await caches.open(SHELL_CACHE);
          if (url.pathname.includes('map')) {
            return (await cache.match('/map.html')) || (await cache.match('/'));
          }
          if (url.pathname.includes('posts')) {
            return (await cache.match('/posts.html')) || (await cache.match('/'));
          }
          return (await cache.match('/frontend.html')) || (await cache.match('/'));
        }
        throw error;
      }
    })
  );
});

// -----------------------------------------------------------------------------
// 4. Background Sync support (where supported)
// -----------------------------------------------------------------------------
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-voice-sos') {
    event.waitUntil(
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'RETRY_QUEUED_SOS' });
        });
      })
    );
  }
});
