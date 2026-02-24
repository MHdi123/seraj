const cacheName = 'seraj-cache-v1';
const filesToCache = [
  '/',
  '/index.html',
  '/static/css/tailwind.css',
  '/static/js/main.js',
  '/static/logo/192.png',
  '/static/logo/512.png'
];

// نصب Service Worker و کش فایل‌ها
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(cacheName).then((cache) => cache.addAll(filesToCache))
  );
});

// فعال‌سازی و پاکسازی کش قدیمی
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((key) => {
        if (key !== cacheName) return caches.delete(key);
      }))
    )
  );
});

// پاسخ به درخواست‌ها از کش یا شبکه
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => response || fetch(event.request))
  );
});

event.respondWith(
  caches.match(event.request)
    .then((response) => response || fetch(event.request))
    .catch(() => caches.match('/offline.html'))
);
