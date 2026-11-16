/* Amber's MSC Hub - offline helper (v2).
   The app page opens from the saved copy instantly, then checks for a newer one in the background.
   Import helpers (lib/) are saved the first time they are used. Everything else is network first. */
const CACHE='msc-hub-v2';
const CORE=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
const ver=r=>r&&(r.headers.get('etag')||r.headers.get('last-modified'));
const notify=()=>self.clients.matchAll().then(cs=>cs.forEach(c=>c.postMessage('msc-update')));
self.addEventListener('fetch',e=>{
 const r=e.request;if(r.method!=='GET')return;
 const u=new URL(r.url);
 if(/^fonts\.(googleapis|gstatic)\.com$/.test(u.hostname)){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{if(res&&(res.ok||res.type==='opaque')){const copy=res.clone();caches.open(CACHE).then(c=>c.put(r,copy))}return res})));return}
 if(u.origin!==location.origin)return;
 const page=r.mode==='navigate'||/\/(index\.html)?$/.test(u.pathname);
 if(page){
  e.respondWith(caches.match('index.html',{ignoreSearch:true}).then(cached=>{
   let changed=false;const net=fetch(u.href,{cache:'no-cache'}).then(res=>{if(res&&res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put('index.html',copy));const a=ver(cached),b=ver(res);if(cached&&a&&b&&a!==b)changed=true}return res}).catch(()=>null);
   if(cached){e.waitUntil(net.then(()=>changed?new Promise(r=>setTimeout(r,1500)).then(notify):0));return cached}
   return net.then(x=>x||new Response('Offline',{status:503}))}));
  return}
 if(/\/lib\//.test(u.pathname)){
  e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{if(res&&res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put(r,copy))}return res})));
  return}
 e.respondWith(fetch(r).then(res=>{if(res&&res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put(r,copy))}return res}).catch(()=>caches.match(r).then(m=>m||caches.match('index.html'))))});
