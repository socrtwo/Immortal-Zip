#!/usr/bin/env bash
# Build a Linux AppImage and a .deb package.
# Designed to run on an Ubuntu CI runner.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-/usr/bin/python3.12}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python3"

VERSION="$("$PYTHON" -c "import immortal_zip; print(immortal_zip.__version__)")"
DIST="$ROOT/dist"
APPDIR="$DIST/AppDir"
DEB_ROOT="$DIST/deb"

rm -rf "$DIST"
mkdir -p "$DIST"

echo ">>> PyInstaller bundle"
"$PYTHON" -m PyInstaller --noconfirm --clean --distpath "$DIST" --workpath "$DIST/work" build/immortal-zip.spec

echo ">>> AppImage layout"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -r "$DIST/immortal-zip/." "$APPDIR/usr/bin/" 2>/dev/null || cp "$DIST/immortal-zip" "$APPDIR/usr/bin/immortal-zip"
chmod +x "$APPDIR/usr/bin/immortal-zip" || true
cp build/immortal-zip-1024.png "$APPDIR/usr/share/icons/hicolor/512x512/apps/immortal-zip.png"
cp build/immortal-zip-1024.png "$APPDIR/immortal-zip.png"

cat > "$APPDIR/usr/share/applications/immortal-zip.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Immortal-Zip
GenericName=Archive Tool
Comment=Zip, unzip, and repair archives
Exec=immortal-zip
Icon=immortal-zip
Categories=Utility;Archiving;
Terminal=false
EOF
cp "$APPDIR/usr/share/applications/immortal-zip.desktop" "$APPDIR/immortal-zip.desktop"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/immortal-zip" "$@"
EOF
chmod +x "$APPDIR/AppRun"

APPIMAGETOOL=""
if [ -x /opt/appimagetool/AppRun ]; then
  APPIMAGETOOL=/opt/appimagetool/AppRun
elif command -v appimagetool >/dev/null 2>&1; then
  APPIMAGETOOL=appimagetool
fi
if [ -n "$APPIMAGETOOL" ]; then
  ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$DIST/Immortal-Zip-${VERSION}-x86_64.AppImage" || true
else
  echo "appimagetool not found — skipping AppImage build."
fi

echo ">>> .deb package"
mkdir -p "$DEB_ROOT/DEBIAN" \
         "$DEB_ROOT/opt/immortal-zip" \
         "$DEB_ROOT/usr/bin" \
         "$DEB_ROOT/usr/share/applications" \
         "$DEB_ROOT/usr/share/icons/hicolor/512x512/apps"

cp -r "$DIST/immortal-zip/." "$DEB_ROOT/opt/immortal-zip/" 2>/dev/null \
  || cp "$DIST/immortal-zip" "$DEB_ROOT/opt/immortal-zip/immortal-zip"

ln -sf /opt/immortal-zip/immortal-zip "$DEB_ROOT/usr/bin/immortal-zip"
cp build/immortal-zip-1024.png "$DEB_ROOT/usr/share/icons/hicolor/512x512/apps/immortal-zip.png"
cp "$APPDIR/usr/share/applications/immortal-zip.desktop" "$DEB_ROOT/usr/share/applications/"

cat > "$DEB_ROOT/DEBIAN/control" <<EOF
Package: immortal-zip
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Immortal-Zip contributors <noreply@example.com>
Description: Zip, unzip, and repair archives
 Immortal-Zip is a cross-platform tool that creates and extracts ZIP
 archives and can repair corrupted ones by rebuilding the central
 directory from salvaged local file headers.
EOF

dpkg-deb --build --root-owner-group "$DEB_ROOT" "$DIST/immortal-zip_${VERSION}_amd64.deb"

echo ">>> Done. Artifacts:"
ls -lh "$DIST"/*.AppImage "$DIST"/*.deb 2>/dev/null || true
