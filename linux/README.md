# Immortal Unzip — Linux

Linux desktop app built with **Electron**. Produces an AppImage (runs on any distro), a `.deb` (Debian/Ubuntu), and an `.rpm` (Fedora/RHEL).

## Quick Start (Development)

```bash
cd linux
npm install
npm start
```

## Build Distributable

```bash
# AppImage + DEB + RPM
npm run build

# AppImage only
npm run build:appimage

# Debian package
npm run build:deb

# RPM package
npm run build:rpm
```

Output goes to `linux/dist/`.

## ChromeOS

The AppImage works on ChromeOS via the Linux development environment (Crostini). See `../chromeos/README.md` for a dedicated ChromeOS PWA/extension approach.

## Project Structure

```
linux/
├── package.json          # Electron + electron-builder config
├── main.js               # Main process
├── preload.js            # Context bridge
├── immortal-unzip.html   # App UI
└── README.md
```

## Icon

Place a 512×512 `icon.png` in this folder before building.
