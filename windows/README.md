# Immortal Unzip — Windows

Windows desktop app built with **Electron**. Provides a native install experience for the Immortal Unzip fault-tolerant ZIP extractor.

## Features

- Native Windows Open / Save dialogs via Electron's `dialog` API
- File associations for `.zip`, `.jar`, `.apk`, `.docx`, `.xlsx`, `.pptx`, `.epub`
- Single-instance: opening a second file routes to the existing window
- Command-line: `immortal-unzip path/to/file.zip`
- NSIS installer and portable EXE build targets

## Quick Start (Development)

```bash
cd windows
npm install
npm start
```

## Build Distributable

```bash
# NSIS installer + portable EXE
npm run build

# Installer only
npm run build:nsis

# Portable EXE only
npm run build:portable
```

Output goes to `windows/dist/`.

## Project Structure

```
windows/
├── package.json          # Electron + electron-builder config
├── main.js               # Main process: window, IPC, file dialogs
├── preload.js            # Context bridge (electronAPI)
├── immortal-unzip.html   # Full app UI + Immortal Inflate/Unzip engine
└── README.md
```

## Icon

Place a 256×256 `icon.ico` file in this folder before building.
