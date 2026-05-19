#!/usr/bin/env bash
# Build a macOS .app bundle and wrap it in a DMG installer.
# Runs on macOS GitHub runners.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(python3 -c "import immortal_zip; print(immortal_zip.__version__)")"
DIST="$ROOT/dist"
rm -rf "$DIST"
mkdir -p "$DIST"

# Build an .icns from the source PNG if iconutil is available.
if [ ! -f build/immortal-zip.icns ] && command -v iconutil >/dev/null 2>&1; then
  ICONSET="$DIST/icon.iconset"
  mkdir -p "$ICONSET"
  for sz in 16 32 64 128 256 512; do
    sips -z "$sz" "$sz" build/immortal-zip-1024.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
    sips -z "$((sz*2))" "$((sz*2))" build/immortal-zip-1024.png --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o build/immortal-zip.icns
fi

echo ">>> PyInstaller bundle (.app)"
pyinstaller --noconfirm --clean --distpath "$DIST" --workpath "$DIST/work" build/immortal-zip.spec

APP_BUNDLE="$DIST/Immortal-Zip.app"
if [ ! -d "$APP_BUNDLE" ]; then
  echo "Expected app bundle at $APP_BUNDLE not found" >&2
  ls "$DIST"
  exit 1
fi

echo ">>> DMG creation"
DMG_PATH="$DIST/Immortal-Zip-${VERSION}.dmg"
STAGING="$DIST/dmg-staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP_BUNDLE" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

hdiutil create -volname "Immortal-Zip ${VERSION}" \
  -srcfolder "$STAGING" \
  -ov -format UDZO "$DMG_PATH"

echo ">>> Done."
ls -lh "$DMG_PATH"
