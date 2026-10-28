"""Build the standalone, installable (PWA) version of the log into site/."""
import json, re, pathlib
from PIL import Image, ImageDraw

root = pathlib.Path(__file__).parent
site = root / 'site'
data = (pathlib.Path('/tmp/claude-0/-home-user/ecbf8b6e-7ca9-5914-9c80-7faf3519b587/scratchpad/data.json')).read_text()
(root / 'programme-data.json').write_text(data)
s = (root / 'template.html').read_text().replace('__DATA__', data)

def sub(old, new):
    global s
    assert old in s, old[:60]
    s = s.replace(old, new)

# storage: device only, no Claude account sync
sub('<span class="save local" id="saveState">Saved on this device</span>', '<span class="save" id="saveState">Saved on this phone</span>')
s = re.sub(r"async function initStore\(\)\{.*?\n\}\n", "async function initStore(){ try { await navigator.storage?.persist?.(); } catch {} }\n", s, flags=re.S)
sub("""${store.mode === 'account' ? 'Your log syncs to your Claude account, so it follows you to any device where you open this page. It is private to you.' : 'Your log is saved in this browser. Export a backup now and then so you never lose a block.'}""",
    "Your log is saved on this device only. Export a backup now and then, and use Import backup to move it to a new phone.")
s = re.sub(r"async function save\(filename, data, type\)\{.*?\n\}\n", """async function save(filename, data, type){
  const file = new File([data], filename, {type});
  try { if (navigator.canShare?.({files:[file]})) { await navigator.share({files:[file], title:filename}); return; } } catch (e) { if (e?.name === 'AbortError') return; }
  const a = document.createElement('a'); a.href = URL.createObjectURL(file); a.download = filename;
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  toast('Saved ' + filename);
}
""", s, flags=re.S)

head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#171B20" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="S&amp;C Log">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
"""
s = s.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
title_end = s.index('</style>') + len('</style>')
s = head + s[:title_end] + '\n</head>\n<body>\n' + s[title_end:]
s = s.replace('</script>\n', """</script>
<script>if ('serviceWorker' in navigator) addEventListener('load', () => navigator.serviceWorker.register('sw.js'));</script>
</body>
</html>
""", 1) if s.count('</script>') == 1 else s
assert s.rstrip().endswith('</html>')
(site / 'index.html').write_text(s)

(site / 'manifest.webmanifest').write_text(json.dumps({
  "name": "8 Week S&C Log", "short_name": "S&C Log", "start_url": "./", "scope": "./",
  "display": "standalone", "background_color": "#ECEEF1", "theme_color": "#1E4FC2",
  "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}, indent=1))

(site / 'sw.js').write_text("""// Offline cache: app shell is cache-first, fonts are cached on first use.
const CACHE = 'sc-log-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin === location.origin) {
    // network first for the page so updates arrive, cache when offline
    e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return r; })
      .catch(() => caches.match(e.request, {ignoreSearch: true}).then(r => r || caches.match('index.html'))));
  } else if (/fonts\\.(googleapis|gstatic)\\.com$/.test(url.hostname)) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => { const c = res.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return res; })));
  }
});
""")

def icon(size, path, pad=0.0):
    im = Image.new('RGB', (size, size), '#1E4FC2'); d = ImageDraw.Draw(im); u = size / 100
    c = lambda *xy: [v * u for v in xy]
    # barbell: bar, two plates per side, collars
    d.rounded_rectangle(c(14, 47, 86, 53), radius=1.5*u, fill='white')
    for x, w, h in [(22, 7, 40), (30, 6, 30)]:
        d.rounded_rectangle(c(x, 50-h/2, x+w, 50+h/2), radius=2*u, fill='white')
        d.rounded_rectangle(c(100-x-w, 50-h/2, 100-x, 50+h/2), radius=2*u, fill='white')
    im.save(site / path)
icon(192, 'icon-192.png'); icon(512, 'icon-512.png'); icon(180, 'apple-touch-icon.png')
print('built', [p.name for p in site.iterdir()])
