# Immortal Unzip — macOS

macOS desktop app built with **Electron**. Supports both Intel (x64) and Apple Silicon (arm64) via universal binary.

## Features

- Native macOS Open / Save dialogs
- `.app` bundle with DMG installer
- File associations for common ZIP-based formats
- Apple Silicon & Intel universal binary support
- Hardened Runtime for notarization-ready signing

## Quick Start (Development)

```bash
cd macos
npm install
npm start
```

## Build Distributable

```bash
# DMG + ZIP for current arch
npm run build

# Universal binary (Intel + Apple Silicon)
npm run build:universal

# DMG only
npm run build:dmg
```

Output goes to `macos/dist/`.

## Signing & Notarization

Set the following environment variables before building:

```
CSC_LINK=path/to/certificate.p12
CSC_KEY_PASSWORD=your_password
APPLE_ID=your@apple.id
APPLE_APP_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx
APPLE_TEAM_ID=YOURTEAMID
```

## Project Structure

```
macos/
├── package.json              # Electron + electron-builder config
├── main.js                   # Main process
├── preload.js                # Context bridge
├── immortal-unzip.html       # App UI
├── entitlements.mac.plist    # Hardened Runtime entitlements
└── README.md
```
