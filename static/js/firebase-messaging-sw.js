importScripts('https://www.gstatic.com/firebasejs/9.22.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.2/firebase-messaging-compat.js');

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

messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/icon.png'
  };
  self.registration.showNotification(notificationTitle, notificationOptions);
});