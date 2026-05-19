# Immortal Unzip — Web

Deploy `immortal-unzip.html` (from the repository root) as a standalone web app. No server-side code, no build step, and no external runtime dependencies — it runs entirely in the browser.

## Deployment Options

### Static hosting (GitHub Pages, Netlify, Vercel, etc.)

1. Copy `immortal-unzip.html` to your hosting root (or any subdirectory).
2. Access it at `https://yoursite.com/immortal-unzip.html`.

### Local / offline use

Simply open `immortal-unzip.html` directly in any modern browser:

```bash
open immortal-unzip.html          # macOS
xdg-open immortal-unzip.html      # Linux
start immortal-unzip.html         # Windows
```

No internet connection required after the file is saved.

### Progressive Web App (PWA)

Add a `manifest.webmanifest` alongside the HTML to enable "Add to Home Screen" / "Install App" on Chrome and Edge:

```json
{
  "name": "Immortal Unzip",
  "short_name": "Immortal Unzip",
  "start_url": "immortal-unzip.html",
  "display": "standalone",
  "background_color": "#121212",
  "theme_color": "#00e5ff",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

Then add to the `<head>` of `immortal-unzip.html`:

```html
<link rel="manifest" href="manifest.webmanifest">
```

## Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome / Edge 90+ | ✅ Full |
| Firefox 89+ | ✅ Full |
| Safari 16.4+ | ✅ Full |
| ChromeOS browser | ✅ Full |
| Safari iOS 16.4+ | ✅ Full |
| Samsung Internet 16+ | ✅ Full |

Features used: `FileReader`, `Blob`, `URL.createObjectURL`, `TextDecoder`, `DataView`, `Uint8Array` — all broadly supported.
