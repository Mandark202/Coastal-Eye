/* ==============================================================================
   CTAS (Coastal Threat Alert System) - Offline Store & Resilience Library
   IndexedDB Persistence, Offline SOS Queue, Banner & Service Worker Sync
   ============================================================================== */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CTASOffline = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const DB_NAME = 'ctas_offline_db';
  const DB_VERSION = 1;
  const STORES = {
    ALERTS: 'alerts_cache',
    ROUTES: 'evacuation_routes',
    SOS_QUEUE: 'voice_sos_queue',
    METADATA: 'system_metadata'
  };

  // ---------------------------------------------------------------------------
  // 1. IndexedDB Core Wrapper with LocalStorage Fallback
  // ---------------------------------------------------------------------------
  let dbPromise = null;

  function openDB() {
    if (dbPromise) return dbPromise;

    dbPromise = new Promise((resolve, reject) => {
      if (!('indexedDB' in window)) {
        console.warn('[CTAS Offline] IndexedDB unavailable, falling back to LocalStorage');
        resolve(null);
        return;
      }

      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORES.ALERTS)) {
          db.createObjectStore(STORES.ALERTS, { keyPath: 'key' });
        }
        if (!db.objectStoreNames.contains(STORES.ROUTES)) {
          db.createObjectStore(STORES.ROUTES, { keyPath: 'key' });
        }
        if (!db.objectStoreNames.contains(STORES.SOS_QUEUE)) {
          db.createObjectStore(STORES.SOS_QUEUE, { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains(STORES.METADATA)) {
          db.createObjectStore(STORES.METADATA, { keyPath: 'key' });
        }
      };

      request.onsuccess = (e) => resolve(e.target.result);
      request.onerror = (e) => {
        console.warn('[CTAS Offline] IndexedDB error, falling back to LocalStorage', e);
        resolve(null);
      };
    });

    return dbPromise;
  }

  // Generic Put
  async function dbPut(storeName, data) {
    const db = await openDB();
    if (!db) {
      try {
        localStorage.setItem(`ctas_${storeName}_${data.key || data.id}`, JSON.stringify(data));
      } catch (err) {
        console.error('[CTAS Offline] LocalStorage put failed', err);
      }
      return;
    }
    return new Promise((resolve, reject) => {
      try {
        const tx = db.transaction([storeName], 'readwrite');
        const store = tx.objectStore(storeName);
        store.put(data);
        tx.oncomplete = () => resolve();
        tx.onerror = (e) => reject(e);
      } catch (e) {
        reject(e);
      }
    });
  }

  // Generic Get
  async function dbGet(storeName, key) {
    const db = await openDB();
    if (!db) {
      try {
        const raw = localStorage.getItem(`ctas_${storeName}_${key}`);
        return raw ? JSON.parse(raw) : null;
      } catch (err) {
        return null;
      }
    }
    return new Promise((resolve) => {
      try {
        const tx = db.transaction([storeName], 'readonly');
        const store = tx.objectStore(storeName);
        const req = store.get(key);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => resolve(null);
      } catch (e) {
        resolve(null);
      }
    });
  }

  // Generic GetAll
  async function dbGetAll(storeName) {
    const db = await openDB();
    if (!db) {
      const results = [];
      const prefix = `ctas_${storeName}_`;
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(prefix)) {
          try {
            results.push(JSON.parse(localStorage.getItem(k)));
          } catch (e) {}
        }
      }
      return results;
    }
    return new Promise((resolve) => {
      try {
        const tx = db.transaction([storeName], 'readonly');
        const store = tx.objectStore(storeName);
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => resolve([]);
      } catch (e) {
        resolve([]);
      }
    });
  }

  // Generic Delete
  async function dbDelete(storeName, key) {
    const db = await openDB();
    if (!db) {
      localStorage.removeItem(`ctas_${storeName}_${key}`);
      return;
    }
    return new Promise((resolve) => {
      try {
        const tx = db.transaction([storeName], 'readwrite');
        const store = tx.objectStore(storeName);
        store.delete(key);
        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      } catch (e) {
        resolve();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 2. High-Level Data Handlers: Alerts & Evacuation Routes
  // ---------------------------------------------------------------------------

  async function saveAlerts(alerts, coordinates = null) {
    const record = {
      key: 'latest_alerts',
      alerts: Array.isArray(alerts) ? alerts : [],
      coordinates: coordinates,
      timestamp: Date.now()
    };
    await dbPut(STORES.ALERTS, record);
    // Also update metadata
    await dbPut(STORES.METADATA, { key: 'last_alerts_sync', timestamp: record.timestamp });
    return record;
  }

  async function getLatestAlerts() {
    const res = await dbGet(STORES.ALERTS, 'latest_alerts');
    if (res && res.alerts) {
      return {
        alerts: res.alerts,
        timestamp: res.timestamp,
        coordinates: res.coordinates
      };
    }
    return null;
  }

  async function saveEvacRoute(requestParams, routeResponse) {
    const record = {
      key: 'latest_evacuation_route',
      params: requestParams,
      data: routeResponse,
      timestamp: Date.now()
    };
    await dbPut(STORES.ROUTES, record);
    await dbPut(STORES.METADATA, { key: 'last_route_sync', timestamp: record.timestamp });
    return record;
  }

  async function getLatestEvacRoute() {
    const res = await dbGet(STORES.ROUTES, 'latest_evacuation_route');
    if (res && res.data) {
      return {
        data: res.data,
        params: res.params,
        timestamp: res.timestamp
      };
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // 3. Voice SOS Offline Queue & Auto-Retry
  // ---------------------------------------------------------------------------

  async function queueVoiceSos(payload) {
    const item = {
      id: `sos_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      transcript: payload.transcript || '',
      lat: payload.lat,
      lng: payload.lng,
      user_id: payload.user_id || null,
      created_at: new Date().toISOString(),
      attempts: 0
    };
    await dbPut(STORES.SOS_QUEUE, item);
    console.log('[CTAS Offline] Voice SOS queued offline:', item);

    // Request Background Sync if browser supports it
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      try {
        const reg = await navigator.serviceWorker.ready;
        await reg.sync.register('sync-voice-sos');
      } catch (err) {
        // Fallback to window online event
      }
    }

    return item;
  }

  async function getQueuedVoiceSos() {
    return await dbGetAll(STORES.SOS_QUEUE);
  }

  async function removeQueuedVoiceSos(id) {
    return await dbDelete(STORES.SOS_QUEUE, id);
  }

  let isFlushingSos = false;
  async function flushQueuedVoiceSos(apiBaseUrl = '') {
    if (isFlushingSos || !navigator.onLine) return;
    const queue = await getQueuedVoiceSos();
    if (!queue || queue.length === 0) return;

    isFlushingSos = true;
    console.log(`[CTAS Offline] Flushing ${queue.length} queued Voice SOS items...`);

    const origin = apiBaseUrl || window.location.origin;

    for (const item of queue) {
      try {
        const res = await fetch(`${origin}/api/voice-sos`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcript: item.transcript,
            lat: item.lat,
            lng: item.lng,
            user_id: item.user_id
          })
        });

        if (res.ok) {
          await removeQueuedVoiceSos(item.id);
          console.log(`[CTAS Offline] Successfully synced queued SOS: ${item.id}`);
          showSosNotification(`✅ Queued SOS Sent: "${item.transcript.slice(0, 30)}..."`);
        } else {
          item.attempts = (item.attempts || 0) + 1;
          await dbPut(STORES.SOS_QUEUE, item);
        }
      } catch (err) {
        console.warn(`[CTAS Offline] Failed to sync SOS item ${item.id}`, err);
        break; // Stop loop until connectivity is stable
      }
    }

    isFlushingSos = false;
  }

  function showSosNotification(msg) {
    const toast = document.getElementById('sos-status-toast');
    if (toast) {
      toast.innerText = msg;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 4500);
    }
  }

  // ---------------------------------------------------------------------------
  // 4. Emergency Directory (Pre-cached)
  // ---------------------------------------------------------------------------
  const EMERGENCY_CONTACTS = [
    { agency: 'National Disaster Helpline', number: '1078', desc: 'Central NDMA Emergency Operations' },
    { agency: 'Coastal Disaster Operations (SEOC)', number: '1070', desc: 'State Emergency Operation Centre' },
    { agency: 'District Disaster Emergency Line', number: '1077', desc: 'Local Collectorate & Response' },
    { agency: 'Indian Coast Guard SAR', number: '1554', desc: 'Maritime Search & Rescue' },
    { agency: 'NDRF Control Room', number: '011-24363260', desc: 'National Disaster Response Force' },
    { agency: 'All-India Emergency Helpline', number: '112', desc: 'Police / Fire / Ambulance' },
    { agency: 'Medical Emergency / Ambulance', number: '108', desc: 'Trauma & Coastal First Aid' }
  ];

  function getEmergencyContacts() {
    return EMERGENCY_CONTACTS;
  }

  // ---------------------------------------------------------------------------
  // 5. Offline Banner UI Component
  // ---------------------------------------------------------------------------
  function formatTimestamp(ts) {
    if (!ts) return 'recent session';
    const date = new Date(ts);
    if (isNaN(date.getTime())) return 'recent session';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' on ' +
           date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  const OfflineBanner = {
    element: null,

    init(options = {}) {
      if (document.getElementById('ctas-offline-banner')) {
        this.element = document.getElementById('ctas-offline-banner');
        return;
      }

      const banner = document.createElement('div');
      banner.id = 'ctas-offline-banner';
      banner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 99999;
        display: none;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 10px 16px;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        font-size: 0.88rem;
        font-weight: 500;
        color: #EDEAFB;
        background: rgba(13, 7, 22, 0.94);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-bottom: 2px solid #E2B714;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
        transition: all 0.35s ease;
        text-align: center;
      `;

      banner.innerHTML = `
        <span style="display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:50%; background:rgba(226,183,20,0.2); color:#E2B714; font-size:13px;">⚡</span>
        <span id="ctas-offline-banner-text">You are offline — showing last known data</span>
        <button id="ctas-offline-dismiss" style="margin-left:auto; background:none; border:none; color:rgba(237,234,251,0.6); font-size:18px; cursor:pointer; padding:0 6px;" title="Dismiss">&times;</button>
      `;

      document.body.prepend(banner);
      this.element = banner;

      document.getElementById('ctas-offline-dismiss')?.addEventListener('click', () => {
        banner.style.display = 'none';
      });

      // Listen for browser online / offline changes
      window.addEventListener('online', () => this.handleOnline());
      window.addEventListener('offline', () => this.handleOffline());

      // Initial check
      if (!navigator.onLine) {
        this.handleOffline();
      }
    },

    async showOffline(timestamp = null) {
      if (!this.element) this.init();
      if (!timestamp) {
        const meta = await dbGet(STORES.METADATA, 'last_alerts_sync');
        if (meta && meta.timestamp) timestamp = meta.timestamp;
      }
      const timeStr = formatTimestamp(timestamp);
      const textElem = document.getElementById('ctas-offline-banner-text');
      if (textElem) {
        textElem.innerHTML = `You are offline — showing last known data from <strong>${timeStr}</strong>`;
      }
      this.element.style.borderBottomColor = '#E2B714';
      this.element.style.display = 'flex';
    },

    showOnline() {
      if (!this.element) return;
      const textElem = document.getElementById('ctas-offline-banner-text');
      if (textElem) {
        textElem.innerHTML = `✅ <strong>Back online</strong> — Live coastal feeds connected.`;
      }
      this.element.style.borderBottomColor = '#00CC66';
      this.element.style.display = 'flex';
      setTimeout(() => {
        if (navigator.onLine && this.element) {
          this.element.style.display = 'none';
        }
      }, 3500);
    },

    async handleOffline() {
      const latest = await getLatestAlerts();
      this.showOffline(latest ? latest.timestamp : null);
    },

    handleOnline() {
      this.showOnline();
      flushQueuedVoiceSos();
    }
  };

  // ---------------------------------------------------------------------------
  // 6. Service Worker Registration Helper
  // ---------------------------------------------------------------------------
  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
          .then((registration) => {
            console.log('[CTAS PWA] Service Worker registered successfully, scope:', registration.scope);
            registration.onupdatefound = () => {
              const installingWorker = registration.installing;
              if (installingWorker) {
                installingWorker.onstatechange = () => {
                  if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                    console.log('[CTAS PWA] Fresh update available for offline shell.');
                  }
                };
              }
            };
          })
          .catch((err) => {
            console.error('[CTAS PWA] Service Worker registration failed:', err);
          });

        // Listen for messages from SW
        navigator.serviceWorker.addEventListener('message', (event) => {
          if (event.data && event.data.type === 'RETRY_QUEUED_SOS') {
            flushQueuedVoiceSos();
          }
        });
      });
    }
  }

  // Auto-init banner and auto-flush SOS queue on start
  if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', () => {
      OfflineBanner.init();
      if (navigator.onLine) {
        flushQueuedVoiceSos();
      }
    });
  }

  return {
    openDB,
    saveAlerts,
    getLatestAlerts,
    saveEvacRoute,
    getLatestEvacRoute,
    queueVoiceSos,
    getQueuedVoiceSos,
    removeQueuedVoiceSos,
    flushQueuedVoiceSos,
    getEmergencyContacts,
    formatTimestamp,
    OfflineBanner,
    registerServiceWorker
  };
});
