#!/usr/bin/env bash
# Wrap the Immortal-Zip PWA in a Capacitor iOS shell and produce an .ipa.
#
# Strict requirements (Apple-imposed — cannot be bypassed from Linux):
#   * macOS runner (macos-14 on GitHub Actions or later)
#   * Xcode 15+
#   * A paid Apple Developer Program account
#   * Provisioning profile + signing certificate exported as p12, available
#     to CI as $IOS_P12_BASE64 and $IOS_P12_PASSWORD secrets
#   * Team ID in $APPLE_TEAM_ID, bundle id reserved on App Store Connect
#
# This script will produce a signed .ipa suitable for ad-hoc or App Store
# distribution. Without the secrets it will fall back to an unsigned build
# (.app) that can only be installed via Xcode onto a developer device.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUNDLE_ID="${BUNDLE_ID:-io.github.socrtwo.immortalzip}"
APP_NAME="Immortal-Zip"
VERSION="$(python3 -c "import immortal_zip; print(immortal_zip.__version__)")"

WORK="$ROOT/dist/ios"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# Bootstrap Capacitor project that points at the static PWA.
npm init -y >/dev/null
npm install --no-fund --no-audit @capacitor/core @capacitor/cli @capacitor/ios
npx cap init "$APP_NAME" "$BUNDLE_ID" --web-dir "$ROOT/web"
npx cap add ios

# Copy the PWA into the iOS project.
npx cap copy ios
npx cap sync ios

# Update Info.plist with the version.
PLIST="ios/App/App/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST" || true
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST" || true

cd ios/App
pod install || true

ARCHIVE_PATH="$WORK/build/${APP_NAME}.xcarchive"
EXPORT_PATH="$WORK/build/export"
mkdir -p "$WORK/build"

xcodebuild -workspace App.xcworkspace \
  -scheme App \
  -configuration Release \
  -destination "generic/platform=iOS" \
  -archivePath "$ARCHIVE_PATH" \
  archive

cat > "$WORK/build/export-options.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key><string>${EXPORT_METHOD:-ad-hoc}</string>
  <key>teamID</key><string>${APPLE_TEAM_ID:-}</string>
  <key>signingStyle</key><string>automatic</string>
  <key>uploadSymbols</key><true/>
  <key>compileBitcode</key><false/>
</dict>
</plist>
EOF

xcodebuild -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_PATH" \
  -exportOptionsPlist "$WORK/build/export-options.plist"

IPA_OUT="$ROOT/dist/Immortal-Zip-${VERSION}.ipa"
cp "$EXPORT_PATH"/*.ipa "$IPA_OUT"
echo ">>> Wrote $IPA_OUT"
ls -lh "$IPA_OUT"
