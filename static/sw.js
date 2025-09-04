// sw.js

// Este é um Service Worker muito básico.
// Ele é necessário para que o navegador reconheça o site como um PWA instalável.

self.addEventListener('install', (event) => {
  console.log('Service worker: install event in progress.');
});

self.addEventListener('activate', (event) => {
  console.log('Service worker: activate event in progress.');
});

self.addEventListener('fetch', (event) => {
  // Apenas responde com o que a rede fornecer.
  // Para um PWA mais avançado, aqui você implementaria o cache offline.
  console.log('Service worker: fetch event in progress.');
  event.respondWith(fetch(event.request));
});
