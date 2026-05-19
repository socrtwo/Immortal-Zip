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
# Pre-seed the Bubblewrap config so the CLI never asks the interactive
# "Do you want Bubblewrap to install the JDK?" question that hangs CI.
mkdir -p "$HOME/.bubblewrap"
cat > "$HOME/.bubblewrap/config.json" <<EOF
{
  "jdkPath": "${JAVA_HOME}",
  "androidSdkPath": "${ANDROID_HOME:-${ANDROID_SDK_ROOT}}"
}
EOF

npm install --no-fund --no-audit @bubblewrap/cli

# Sanity-check that the published manifest is reachable before bubblewrap
# tries to parse it — otherwise we get a confusing "<!DOCTYPE" JSON error.
MANIFEST_URL="https://${PAGES_HOST}/manifest.webmanifest"
echo ">>> Verifying ${MANIFEST_URL} is reachable"
if ! curl --fail --location --silent --show-error \
       --retry 5 --retry-delay 5 \
       "${MANIFEST_URL}" >/dev/null; then
  cat <<EOF >&2

ERROR: Could not fetch the PWA manifest at
  ${MANIFEST_URL}

Bubblewrap needs this to build the Android TWA. The most common cause is
that GitHub Pages has not been enabled for this repository yet. To fix:

  1. Open Settings → Pages on the repo.
  2. Under "Build and deployment", set Source to "GitHub Actions".
  3. Re-run the "Deploy Pages" workflow (Actions tab → Deploy Pages →
     Run workflow), and confirm \${MANIFEST_URL} returns JSON in a
     browser.
  4. Re-run this release workflow.

EOF
  exit 1
fi

# `init` may emit warnings; pipe a default "Y" answer for any prompts it
# adds in future versions, but DO NOT mask non-zero exit codes — if init
# fails we want the job to fail loudly rather than continue with a broken
# project skeleton.
yes | npx bubblewrap init --manifest "https://${PAGES_HOST}/manifest.webmanifest" --directory .

# Use the patched manifest (overrides whatever init produced).
cp "$ROOT/build/twa-manifest.json" ./twa-manifest.json
sed -i "s|REPLACE_WITH_YOUR_PAGES_HOST|${PAGES_HOST}|g" twa-manifest.json

# Bubblewrap detects the manifest mismatch and asks whether to regenerate
# the project. Answer "Y" so it rebuilds the Android skeleton against our
# patched manifest before producing the APK.
yes | npx bubblewrap build --skipPwaValidation

APK_OUT="$ROOT/dist/Immortal-Zip-1.0.0.apk"
mkdir -p "$(dirname "$APK_OUT")"
cp app-release-signed.apk "$APK_OUT" 2>/dev/null \
  || cp app/build/outputs/apk/release/app-release.apk "$APK_OUT" \
  || true

echo ">>> Done."
ls -lh "$APK_OUT" 2>/dev/null || echo "APK not produced — check Bubblewrap output above."
