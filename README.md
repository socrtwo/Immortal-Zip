# Immortal Unzip

**Fault-tolerant ZIP extractor with repair mode** — a full unzip tool and JavaScript library built on the **Immortal Inflater** from the [Universal File Repair Tool](https://github.com/socrtwo/Universal-File-Repair-Tool).

Even severely damaged or truncated ZIP archives are parsed and extracted as completely as possible.

---

## Libraries

| File | Description |
|------|-------------|
| `lib/immortal-inflate.js` | Standalone UMD library — fault-tolerant DEFLATE decoder |
| `lib/immortal-unzip.js`   | Full ZIP parser + extractor with repair mode, built on ImmortalInflate |

### immortal-inflate.js — Usage

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

### immortal-unzip.js — Usage

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

---

## App UI

`immortal-unzip.html` — fully self-contained single-file web app with:
- Drag-and-drop or click-to-browse ZIP loading
- File listing with sizes, compression ratio, and method
- Per-file and Extract-All buttons
- Repair Mode: one-click deep scan for damaged archives
- Built-in ZIP builder (STORE method) for output bundle — no external dependencies

---

## Platform Distributions

| Platform | Folder | Installer format |
|----------|--------|-----------------|
| **Windows** | `windows/` | NSIS installer + portable EXE (via Electron) |
| **macOS** | `macos/` | DMG + ZIP (Intel + Apple Silicon universal binary) |
| **Linux** | `linux/` | AppImage + DEB + RPM |
| **ChromeOS** | `chromeos/` | Chrome Extension (MV3) + PWA |
| **iOS** | `ios/` | Xcode project → IPA / App Store |
| **Android** | `android/` | Gradle project → APK / AAB / Play Store |
| **Web** | `web/` | Static HTML — deploy anywhere, no server needed |

### Desktop (Windows / macOS / Linux) Quick Start

```bash
# Windows
cd windows && npm install && npm start

# macOS
cd macos && npm install && npm start

# Linux
cd linux && npm install && npm start
```

Build distributables with `npm run build` in each folder. Output goes to `dist/`.

### Web

Open `immortal-unzip.html` directly in any browser — no server required.

### ChromeOS

Load `chromeos/` as an unpacked extension via `chrome://extensions` → **Load unpacked**.

### iOS

Open `ios/ImmortalUnzip.xcodeproj` in Xcode 15+, select a team, and run.

### Android

Open `android/` in Android Studio, sync Gradle, and run.

---

## Repair Mode

When a ZIP's central directory is missing, truncated, or unreadable, Immortal Unzip automatically falls back to **raw byte scanning** — searching for local file headers (`PK\x03\x04`) and attempting to decompress every entry using the Immortal Inflater. The inflater tolerates bit errors, truncation, and corrupt Huffman trees, recovering as much data as possible.

You can also trigger repair mode manually by clicking the **🔧 Re-scan (Repair Mode)** button in the UI.

---

## Supported Formats

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

---

## Origin

The Immortal Inflater was extracted from the [Universal File Repair Tool](https://github.com/socrtwo/Universal-File-Repair-Tool) — a complete file repair suite for DOCX, XLSX, PPTX, ZIP, PDF, JPG, PNG, and MP3 files.
