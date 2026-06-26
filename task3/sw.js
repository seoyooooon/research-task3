const CACHE_NAME = 'poster-calendar-v1';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './manifest.json',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './sample_netflix_records.csv'
];

// 서비스 워커 설치 및 핵심 에셋 캐싱
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Caching all core assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// 활성화 및 구버전 캐시 정리
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache', key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// 네트워크 요청 가로채기 (Cache First for TMDB Images, Stale-While-Revalidate for local assets)
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // TMDB 포스터 이미지 캐싱 전략: Cache First (포스터 이미지는 변하지 않으므로 오프라인 최적화)
  if (url.hostname === 'image.tmdb.org') {
    e.respondWith(
      caches.open('tmdb-posters-cache').then((cache) => {
        return cache.match(e.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          return fetch(e.request).then((networkResponse) => {
            cache.put(e.request, networkResponse.clone());
            return networkResponse;
          });
        });
      })
    );
  } else {
    // 로컬 소스 전략: Stale-While-Revalidate
    e.respondWith(
      caches.match(e.request).then((cachedResponse) => {
        const fetchPromise = fetch(e.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && e.request.method === 'GET') {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(e.request, responseToCache);
            });
          }
          return networkResponse;
        }).catch(() => {
          // 네트워크 에러 시 오프라인 대체 제공
          console.log('[Service Worker] Network request failed. Serving from cache if available.');
        });
        return cachedResponse || fetchPromise;
      })
    );
  }
});
