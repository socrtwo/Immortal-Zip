# Immortal-Zip

A conventional zip / unzip tool that can also **repair** corrupted archives by
salvaging every readable member and rebuilding a fresh central directory —
useful even when other tools refuse to open the file.

This repository contains **two complementary implementations**:

1. **Immortal-Zip** (Python) — CLI, GUI, and PWA with installers for
   Windows, macOS, Linux, Android, iOS, and ChromeOS.
2. **Immortal Unzip** (JavaScript / Electron) — standalone JS libraries
   (`immortal-inflate.js`, `immortal-unzip.js`) plus per-platform
   Electron / native shells under `windows/`, `macos/`, `linux/`,
   `chromeos/`, `ios/`, `android/`, and `web/`.

Both implementations share the same recovery strategy (scan for
`PK\x03\x04` local file headers, inflate each entry independently, skip
unrecoverable members) and are interoperable on the same archives.

---

## Part 1 — Immortal-Zip (Python)

* CLI and GUI on Windows, macOS, Linux, and ChromeOS (Linux container)
* Web / PWA that installs as an app on iOS, Android, ChromeOS, and any
  desktop browser
* Wraps the PWA as a native APK for Android and, with Apple signing
  credentials, as an IPA for iOS

### Installable releases

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

### Building from source

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

### iOS notes

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

### Repair strategy

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

---

## Part 2 — Immortal Unzip (JavaScript / Electron)

**Fault-tolerant ZIP extractor with repair mode** — a full unzip tool and JavaScript library built on the **Immortal Inflater** from the [Universal File Repair Tool](https://github.com/socrtwo/Universal-File-Repair-Tool).

Even severely damaged or truncated ZIP archives are parsed and extracted as completely as possible.

### Libraries

| File | Description |
|------|-------------|
| `lib/immortal-inflate.js` | Standalone UMD library — fault-tolerant DEFLATE decoder |
| `lib/immortal-unzip.js`   | Full ZIP parser + extractor with repair mode, built on ImmortalInflate |

#### immortal-inflate.js — Usage

```html
<script src="lib/immortal-inflate.js"></script>
<script>
  // result.data      — Uint8Array of decompressed bytes
  // result.isCorrupt — true if stream was damaged but partial data was recovered
  const result = ImmortalInflate(compressedUint8Array);
</script>
```

```js
// Node.js
const ImmortalInflate = require('./lib/immortal-inflate');
const result = ImmortalInflate(compressedUint8Array);
```

#### immortal-unzip.js — Usage

```html
<script src="lib/immortal-inflate.js"></script>
<script src="lib/immortal-unzip.js"></script>
<script>
  const uz = new ImmortalUnzip(zipUint8Array);
  console.log(uz.entries);           // ZipEntry[]
  const { data, isCorrupt } = uz.extract(uz.entries[0]);

  // Repair a damaged ZIP (always uses raw scan)
  const repaired = ImmortalUnzip.repair(zipUint8Array);
  repaired.entries.forEach(e => {
    const { data } = repaired.extract(e);
  });
</script>
```

### App UI

`immortal-unzip.html` — fully self-contained single-file web app with:
- Drag-and-drop or click-to-browse ZIP loading
- File listing with sizes, compression ratio, and method
- Per-file and Extract-All buttons
- Repair Mode: one-click deep scan for damaged archives
- Built-in ZIP builder (STORE method) for output bundle — no external dependencies

### Platform Distributions

| Platform | Folder | Installer format |
|----------|--------|-----------------|
| **Windows** | `windows/` | NSIS installer + portable EXE (via Electron) |
| **macOS** | `macos/` | DMG + ZIP (Intel + Apple Silicon universal binary) |
| **Linux** | `linux/` | AppImage + DEB + RPM |
| **ChromeOS** | `chromeos/` | Chrome Extension (MV3) + PWA |
| **iOS** | `ios/` | Xcode project → IPA / App Store |
| **Android** | `android/` | Gradle project → APK / AAB / Play Store |
| **Web** | `web/` | Static HTML — deploy anywhere, no server needed |

#### Desktop (Windows / macOS / Linux) Quick Start

```bash
# Windows
cd windows && npm install && npm start

# macOS
cd macos && npm install && npm start

# Linux
cd linux && npm install && npm start
```

Build distributables with `npm run build` in each folder. Output goes to `dist/`.

#### Web

Open `immortal-unzip.html` directly in any browser — no server required.

#### ChromeOS

Load `chromeos/` as an unpacked extension via `chrome://extensions` → **Load unpacked**.

#### iOS

Open `ios/ImmortalUnzip.xcodeproj` in Xcode 15+, select a team, and run.

#### Android

Open `android/` in Android Studio, sync Gradle, and run.

### Repair Mode

When a ZIP's central directory is missing, truncated, or unreadable, Immortal Unzip automatically falls back to **raw byte scanning** — searching for local file headers (`PK\x03\x04`) and attempting to decompress every entry using the Immortal Inflater. The inflater tolerates bit errors, truncation, and corrupt Huffman trees, recovering as much data as possible.

You can also trigger repair mode manually by clicking the **🔧 Re-scan (Repair Mode)** button in the UI.

### Supported Formats

Any ZIP-based container:

| Extension | Type |
|-----------|------|
| `.zip` | Standard ZIP archive |
| `.jar` | Java Archive |
| `.apk` | Android Package |
| `.docx` | Word document |
| `.xlsx` | Excel workbook |
| `.pptx` | PowerPoint presentation |
| `.epub` | eBook |
| `.odt/.ods/.odp` | OpenDocument formats |

### Origin

The Immortal Inflater was extracted from the [Universal File Repair Tool](https://github.com/socrtwo/Universal-File-Repair-Tool) — a complete file repair suite for DOCX, XLSX, PPTX, ZIP, PDF, JPG, PNG, and MP3 files.
