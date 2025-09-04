// sw.js

/**
 * @description Adiciona um ouvinte para o evento 'install'.
 * Este evento é disparado quando o Service Worker é instalado pela primeira vez.
 * É um bom lugar para preparar caches.
 */
self.addEventListener('install', (event) => {
  console.log('Service Worker: Evento de instalação em progresso.');
  // self.skipWaiting() força o novo service worker a se tornar ativo imediatamente.
  self.skipWaiting();
});

/**
 * @description Adiciona um ouvinte para o evento 'activate'.
 * Este evento é disparado quando o Service Worker é ativado.
 * É um bom lugar para limpar caches antigos.
 */
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Evento de ativação em progresso.');
});

/**
 * @description Adiciona um ouvinte para o evento 'fetch'.
 * Este evento é disparado para cada requisição de rede feita pela página.
 * É o que permite que o aplicativo funcione offline, interceptando requisições.
 * Nesta versão básica, ele simplesmente repassa a requisição para a rede.
 */
self.addEventListener('fetch', (event) => {
  console.log('Service Worker: Buscando recurso:', event.request.url);
  event.respondWith(fetch(event.request));
});
