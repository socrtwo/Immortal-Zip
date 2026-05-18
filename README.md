# Immortal-Zip

A conventional zip / unzip tool that can also **repair** corrupted archives by
salvaging every readable member and rebuilding a fresh central directory —
useful even when other tools refuse to open the file.

* CLI and GUI on Windows, macOS, Linux, and ChromeOS (Linux container)
* Web / PWA that installs as an app on iOS, Android, ChromeOS, and any
  desktop browser
* Wraps the PWA as a native APK for Android and, with Apple signing
  credentials, as an IPA for iOS

## Installable releases

Every release built by `.github/workflows/release.yml` ships these
installable artifacts:

| Platform   | Artifact                                  | How users install                                                                       |
| ---------- | ----------------------------------------- | --------------------------------------------------------------------------------------- |
| Windows    | `Immortal-Zip-<ver>-Setup.exe`            | Double-click; conventional installer with Start Menu / Desktop shortcuts and uninstaller |
| macOS      | `Immortal-Zip-<ver>.dmg`                  | Open and drag `Immortal-Zip.app` to Applications                                        |
| Linux      | `immortal-zip_<ver>_amd64.deb`            | `sudo apt install ./immortal-zip_<ver>_amd64.deb`                                       |
| Linux      | `Immortal-Zip-<ver>-x86_64.AppImage`      | `chmod +x` and run; no install step required                                            |
| Android    | `Immortal-Zip-<ver>.apk`                  | Open the file and accept "Install"; signed with a release keystore                       |
| iOS        | `Immortal-Zip-<ver>.ipa`                  | Requires Apple Developer signing; see [iOS notes](#ios-notes)                            |
| Web        | Live PWA at `https://socrtwo.github.io/immortal-zip/` | Open the site → "Install app" / "Add to Home Screen"                          |
| ChromeOS   | The Web PWA, or the `.deb` inside Crostini | "Install app" from the browser, or `sudo apt install ./immortal-zip_<ver>_amd64.deb`    |

## Building from source

```bash
pip install -e .
immortal-zip --help          # CLI
immortal-zip gui             # GUI
pytest                       # tests
```

Per-platform installer builds:

```bash
bash build/build_linux.sh    # → .AppImage and .deb
bash build/build_macos.sh    # → .dmg (run on macOS)
pwsh  build/build_windows.ps1 # → Setup.exe (run on Windows with NSIS)
bash build/build_android.sh  # → .apk (Bubblewrap + Android SDK)
bash build/build_ios.sh      # → .ipa (macOS + Apple signing identity)
```

Tag a commit `vX.Y.Z` and push to trigger the cross-platform release
workflow that produces every artifact and attaches them to a GitHub
release.

## iOS notes

iOS does not allow installable third-party apps without an Apple
Developer Program membership and code signing. There are two practical
install paths:

1. **PWA (no fee, no review).** Visit the hosted page in Safari and
   choose *Share → Add to Home Screen*. The app launches in standalone
   mode and works offline thanks to the service worker.
2. **Signed IPA.** Set the GitHub repository variable `IOS_ENABLED=true`
   and the secrets `APPLE_TEAM_ID`, `IOS_P12_BASE64`, `IOS_P12_PASSWORD`.
   The `ios` job in the release workflow then produces an ad-hoc IPA
   that installs through Apple Configurator, MDM, or TestFlight.

## Repair strategy

A standard ZIP ends with an *End-Of-Central-Directory* record that
points at a *Central Directory* describing each member. Most archive
tools fail when either is missing or corrupted, even though the raw
per-file Local File Headers (the `PK\x03\x04` blocks) usually survive.

The repairer:

1. Scans the file byte-by-byte for `PK\x03\x04` signatures.
2. For each header, reads the compressed payload either by its declared
   size, or by scanning ahead to the next signature when the size is
   missing (data-descriptor entries).
3. Inflates each payload independently — corrupted members fail
   gracefully and are skipped rather than aborting the run.
4. Writes a brand-new, well-formed archive with a fresh central
   directory.

The same algorithm is implemented in `immortal_zip/core.py` (Python)
and `web/app.js` (browser).
