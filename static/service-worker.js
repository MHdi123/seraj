importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyCu9ruK0nzFXl7cj2U81pu2Ku-SiCk9iOw",
  authDomain: "seraj-app.firebaseapp.com",
  projectId: "seraj-app",
  storageBucket: "seraj-app.firebasestorage.app",
  messagingSenderId: "651768016947",
  appId: "1:651768016947:web:68632e505ad4c1c7bd3346",
  measurementId: "G-KN3B5SW162"
});

const messaging = firebase.messaging();


const CACHE_NAME = 'seraj-cache-v2';
const DYNAMIC_CACHE = 'seraj-dynamic-v2';
const API_CACHE = 'seraj-api-v2';

// فایل‌های ایستا که همیشه کش می‌شوند
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/css/tailwind.css',
  '/static/js/main.js',
  '/static/logo/192.png',
  '/static/logo/512.png',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2'
];

// APIهایی که می‌توانند آفلاین کار کنند
const CACHED_API_ENDPOINTS = [
  '/api/events/upcoming',
  '/api/user/stats'
];

// نصب Service Worker
self.addEventListener('install', event => {
  console.log('✅ Service Worker در حال نصب...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('📦 در حال کش فایل‌های ایستا...');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// فعال‌سازی و پاکسازی کش‌های قدیمی
self.addEventListener('activate', event => {
  console.log('✅ Service Worker فعال شد');
  
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME && key !== DYNAMIC_CACHE && key !== API_CACHE)
          .map(key => {
            console.log('🗑️ پاکسازی کش قدیمی:', key);
            return caches.delete(key);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// استراتژی: Cache First, then Network
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // درخواست‌های API
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(event.request));
    return;
  }
  
  // درخواست‌های فایل‌های ایستا
  if (isStaticAsset(event.request.url)) {
    event.respondWith(handleStaticAsset(event.request));
    return;
  }
  
  // درخواست‌های صفحات HTML
  if (event.request.mode === 'navigate') {
    event.respondWith(handlePageRequest(event.request));
    return;
  }
  
  // سایر درخواست‌ها
  event.respondWith(handleOtherRequests(event.request));
});

// بررسی فایل ایستا
function isStaticAsset(url) {
  const staticPatterns = [
    '/static/',
    '.css',
    '.js',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.woff',
    '.woff2',
    '.ttf'
  ];
  
  return staticPatterns.some(pattern => url.includes(pattern));
}

// مدیریت درخواست‌های API
async function handleApiRequest(request) {
  try {
    // ابتدا تلاش می‌کنیم از شبکه بگیریم
    const networkResponse = await fetch(request);
    
    // اگر موفق بود، در کش ذخیره می‌کنیم
    if (networkResponse.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
    
    // اگر شبکه خطا داد، از کش استفاده می‌کنیم
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(JSON.stringify({ 
      error: 'آفلاین هستید و اطلاعات در کش موجود نیست' 
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    // آفلاین هستیم، از کش استفاده می‌کنیم
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(JSON.stringify({ 
      error: 'شما آفلاین هستید' 
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// مدیریت فایل‌های ایستا
async function handleStaticAsset(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
    
  } catch (error) {
    return new Response('فایل در کش موجود نیست', { status: 404 });
  }
}

// مدیریت صفحات HTML
async function handlePageRequest(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
    
  } catch (error) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // اگر صفحه درخواستی در کش نبود، صفحه آفلاین را نمایش بده
    return caches.match('/offline');
  }
}

// مدیریت سایر درخواست‌ها
async function handleOtherRequests(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    return await fetch(request);
  } catch (error) {
    return new Response('درخواست ناموفق', { status: 404 });
  }
}

// دریافت پیام‌ها از صفحه اصلی
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});