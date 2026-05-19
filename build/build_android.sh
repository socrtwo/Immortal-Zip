#!/usr/bin/env bash
# Build an Android APK that wraps the Immortal-Zip PWA via Bubblewrap (TWA).
# Runs on an Ubuntu CI runner with JDK 17 + Android SDK installed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PAGES_HOST="${PAGES_HOST:-socrtwo.github.io/immortal-zip}"
KEYSTORE_PASS="${KEYSTORE_PASS:-immortal-zip}"

WORK="$ROOT/dist/android"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# Patch the manifest with the actual host.
sed "s|REPLACE_WITH_YOUR_PAGES_HOST|${PAGES_HOST}|g" "$ROOT/build/twa-manifest.json" > twa-manifest.json

# Generate a release keystore (self-signed) if one isn't provided.
if [ ! -f "$ROOT/android.keystore" ]; then
  keytool -genkeypair -v \
    -keystore android.keystore \
    -alias android \
    -keyalg RSA -keysize 2048 -validity 36500 \
    -storepass "$KEYSTORE_PASS" -keypass "$KEYSTORE_PASS" \
    -dname "CN=Immortal-Zip, OU=Releases, O=Immortal-Zip, L=, S=, C=US"
else
  cp "$ROOT/android.keystore" android.keystore
fi

# Bubblewrap workflow.
npm install --no-fund --no-audit @bubblewrap/cli
npx bubblewrap init --manifest "https://${PAGES_HOST}/manifest.webmanifest" --directory . || true
cp twa-manifest.json twa-manifest.json.gen 2>/dev/null || true

# Use the patched manifest.
cp "$ROOT/build/twa-manifest.json" ./twa-manifest.json
sed -i "s|REPLACE_WITH_YOUR_PAGES_HOST|${PAGES_HOST}|g" twa-manifest.json

# Build the signed APK.
npx bubblewrap build --skipPwaValidation

APK_OUT="$ROOT/dist/Immortal-Zip-1.0.0.apk"
mkdir -p "$(dirname "$APK_OUT")"
cp app-release-signed.apk "$APK_OUT" 2>/dev/null \
  || cp app/build/outputs/apk/release/app-release.apk "$APK_OUT" \
  || true

echo ">>> Done."
ls -lh "$APK_OUT" 2>/dev/null || echo "APK not produced — check Bubblewrap output above."
