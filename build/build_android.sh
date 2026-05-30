#!/usr/bin/env bash
# Build an Android APK that wraps the Immortal-Zip PWA via Bubblewrap (TWA).
# Runs on an Ubuntu CI runner with JDK 17 + Android SDK installed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PAGES_HOST="${PAGES_HOST:-socrtwo.github.io/Immortal-Zip}"
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

# Provide the keystore passwords through the environment so `bubblewrap
# build` never stops to prompt for them.
export BUBBLEWRAP_KEYSTORE_PASSWORD="$KEYSTORE_PASS"
export BUBBLEWRAP_KEY_PASSWORD="$KEYSTORE_PASS"

# IMPORTANT: do NOT run the interactive `bubblewrap init`. Its first prompt
# is the free-text Application ID, and piping `yes` into it answered "y" —
# an invalid packageId with no "." — so Bubblewrap looped forever on
#   ">> packageId must have at least 2 sections separated by '.'"
# (flooding the log with "y"s) until the job timed out. Instead we drop in
# our own complete, pre-validated twa-manifest.json (valid packageId +
# signingKey) and generate the project from it non-interactively.
cp "$ROOT/build/twa-manifest.json" ./twa-manifest.json
sed -i "s|REPLACE_WITH_YOUR_PAGES_HOST|${PAGES_HOST}|g" twa-manifest.json

# Scaffold/refresh the Android project from the manifest, then build + sign.
# Bubblewrap's `update`/`build` still emit an interactive prompt:
#   "versionName for the new App version"
# It REJECTS an empty answer ("Minimum length is 1 but input is 0"), so
# feeding blank lines just loops until it aborts (exit 130). Feed the actual
# version (from the manifest) as the first answer, followed by a few blank
# lines for any later prompts that DO have valid defaults. A finite feeder
# means the producer exits 0, so the pipeline stays pipefail-safe.
APP_VERSION=$(python3 -c "import json;print(json.load(open('twa-manifest.json')).get('appVersionName','1.0.0'))" 2>/dev/null || echo 1.0.0)
answers() { printf '%s\n' "$APP_VERSION"; printf '\n%.0s' {1..20}; }
answers | npx bubblewrap update
answers | npx bubblewrap build --skipPwaValidation

APK_OUT="$ROOT/dist/Immortal-Zip-1.0.0.apk"
mkdir -p "$(dirname "$APK_OUT")"
cp app-release-signed.apk "$APK_OUT" 2>/dev/null \
  || cp app/build/outputs/apk/release/app-release.apk "$APK_OUT" 2>/dev/null \
  || {
       echo "ERROR: Bubblewrap did not produce an APK. Searched:" >&2
       echo "  app-release-signed.apk" >&2
       echo "  app/build/outputs/apk/release/app-release.apk" >&2
       find . -name '*.apk' -print >&2 || true
       exit 1
     }

echo ">>> Done."
ls -lh "$APK_OUT"
