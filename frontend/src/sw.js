/* 客户攻单AI Service Worker：App Shell 离线缓存（stale-while-revalidate）
   只缓存前端静态资源；后端 API（跨域 8002 端口）一律不拦截。
   业务数据（简报/会中建议）的离线兜底由页面层 localStorage 负责（closeai-cache-*）。 */
const CACHE = 'closeai-shell-v1';
const SHELL = [
  './index.html',
  './app.js',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  // 导航请求离线时回退到缓存的 index.html
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          caches.open(CACHE).then((c) => c.put('./index.html', res.clone()));
          return res;
        })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }
  // 静态资源：缓存优先 + 后台更新
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetched = fetch(event.request)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(event.request, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || fetched;
    })
  );
});
