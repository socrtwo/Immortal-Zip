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
if [ -d "$DIST/immortal-zip" ]; then
  cp -r "$DIST/immortal-zip/." "$APPDIR/usr/bin/"
else
  cp "$DIST/immortal-zip" "$APPDIR/usr/bin/immortal-zip"
fi
chmod +x "$APPDIR/usr/bin/immortal-zip"
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
  # Don't swallow failures: if appimagetool is present it must succeed,
  # otherwise we'd silently ship a release missing the AppImage.
  ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$DIST/Immortal-Zip-${VERSION}-x86_64.AppImage"
else
  echo "appimagetool not found — skipping AppImage build."
fi

echo ">>> .deb package"
mkdir -p "$DEB_ROOT/DEBIAN" \
         "$DEB_ROOT/opt/immortal-zip" \
         "$DEB_ROOT/usr/bin" \
         "$DEB_ROOT/usr/share/applications" \
         "$DEB_ROOT/usr/share/icons/hicolor/512x512/apps"

# The spec builds a one-file binary (dist/immortal-zip); older one-dir
# builds produce dist/immortal-zip/ instead. Handle both.
if [ -d "$DIST/immortal-zip" ]; then
  cp -r "$DIST/immortal-zip/." "$DEB_ROOT/opt/immortal-zip/"
else
  cp "$DIST/immortal-zip" "$DEB_ROOT/opt/immortal-zip/immortal-zip"
fi
chmod +x "$DEB_ROOT/opt/immortal-zip/immortal-zip"

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

echo ">>> portable tar.gz (for distros without dpkg / AppImage support)"
# A self-contained tarball: the binary, a desktop file, an icon, an
# install.sh that drops a launcher + menu entry into the user's profile,
# and a README. This is the "installable" fallback deliverable.
TARROOT="$DIST/immortal-zip-${VERSION}-linux-x86_64"
rm -rf "$TARROOT"
mkdir -p "$TARROOT"
cp "$DEB_ROOT/opt/immortal-zip/immortal-zip" "$TARROOT/immortal-zip"
chmod +x "$TARROOT/immortal-zip"
cp build/immortal-zip-1024.png "$TARROOT/immortal-zip.png"
cp "$APPDIR/usr/share/applications/immortal-zip.desktop" "$TARROOT/immortal-zip.desktop"

cat > "$TARROOT/install.sh" <<'EOF'
#!/usr/bin/env bash
# Per-user installer for the portable Immortal-Zip build.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
install -Dm755 "$HERE/immortal-zip" "$PREFIX/bin/immortal-zip"
install -Dm644 "$HERE/immortal-zip.png" \
  "$PREFIX/share/icons/hicolor/512x512/apps/immortal-zip.png"
install -Dm644 "$HERE/immortal-zip.desktop" \
  "$PREFIX/share/applications/immortal-zip.desktop"
echo "Installed to $PREFIX. Ensure $PREFIX/bin is on your PATH."
echo "Run with: immortal-zip   (or 'immortal-zip gui' for the GUI)"
EOF
chmod +x "$TARROOT/install.sh"

cat > "$TARROOT/README.txt" <<EOF
Immortal-Zip ${VERSION} — portable Linux build (x86_64)

Contents:
  immortal-zip            Self-contained executable (CLI + GUI).
  immortal-zip.desktop    Application menu entry.
  immortal-zip.png        Application icon.
  install.sh              Per-user installer (~/.local by default).

Quick start (no install):
  ./immortal-zip --help        Command-line usage
  ./immortal-zip gui           Launch the graphical interface

Install for the current user:
  ./install.sh                 Installs to ~/.local (override with PREFIX=)

The GUI requires Tk. On most distros: sudo apt install python3-tk
(the binary is self-contained otherwise).

For a system package, prefer the .deb (Debian/Ubuntu) or the .AppImage.
EOF

tar -C "$DIST" -czf "$DIST/immortal-zip-${VERSION}-linux-x86_64.tar.gz" \
  "immortal-zip-${VERSION}-linux-x86_64"

echo ">>> Done. Artifacts:"
ls -lh "$DIST"/*.AppImage "$DIST"/*.deb "$DIST"/*.tar.gz 2>/dev/null || true
