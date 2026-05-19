# Immortal Unzip — ChromeOS

ChromeOS distribution of Immortal Unzip as a **Chrome Extension (MV3)** with file handler support.

## Installation

### From source (Developer Mode)

1. Open `chrome://extensions` in the Chrome browser on ChromeOS.
2. Enable **Developer mode** (toggle in top-right corner).
3. Click **Load unpacked** and select this `chromeos/` folder.
4. The extension icon will appear in the toolbar.

### Usage

- Click the toolbar icon to open the ZIP extractor in a new tab.
- Or right-click a `.zip` / `.docx` / `.xlsx` / `.epub` file in the Files app and choose **Open with → Immortal Unzip**.

## Building a CRX for Distribution

```bash
# Pack from Chrome: More Tools → Extensions → Pack Extension
# Point at the chromeos/ directory.
```

## Web App Alternative

The same `immortal-unzip.html` can be deployed as a Progressive Web App (PWA). See `../web/README.md`.

## Linux App on ChromeOS (Crostini)

ChromeOS also runs Linux apps. Use the AppImage from `../linux/dist/` inside the Linux terminal:

```bash
chmod +x ImmortalUnzip-1.0.0.AppImage
./ImmortalUnzip-1.0.0.AppImage
```

## File Handler Support

The extension registers as a file handler for:
- `.zip`, `.jar`, `.apk`, `.epub`
- `.docx`, `.xlsx`, `.pptx`

## Project Structure

```
chromeos/
├── manifest.json         # MV3 Chrome Extension manifest
├── background.js         # Service worker
├── immortal-unzip.html   # Full app UI (self-contained)
├── icons/                # Place icon PNG files here (16/32/48/128px)
└── README.md
```
