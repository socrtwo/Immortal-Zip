# Immortal Unzip — iOS

iOS native app wrapping the Immortal Unzip web engine in a full-screen **WKWebView**. Supports iPhone and iPad.

## Requirements

- Xcode 15+
- iOS 16.0+ deployment target
- macOS with Xcode for building

## Quick Start

1. Open `ImmortalUnzip.xcodeproj` in Xcode.
2. Select your development team under **Signing & Capabilities**.
3. Connect a device or choose a simulator.
4. Press **Run** (⌘R).

## Features

- Opens `.zip`, `.docx`, `.xlsx`, `.pptx`, `.epub` files from the Files app or share sheet
- Native save/share dialog for extracted files
- Supports iPad multitasking (all orientations)
- Dark background matching the web UI

## Project Structure

```
ios/
├── ImmortalUnzip.xcodeproj/
│   └── project.pbxproj
├── ImmortalUnzip/
│   ├── AppDelegate.swift         # App lifecycle
│   ├── SceneDelegate.swift       # Scene/URL routing
│   ├── ViewController.swift      # WKWebView host + JS bridges
│   ├── immortal-unzip.html       # Full app UI (bundled resource)
│   ├── LaunchScreen.storyboard   # Launch screen
│   └── Info.plist                # Bundle config + file associations
└── README.md
```

## JavaScript Bridges

The iOS app exposes the following `webkit.messageHandlers` to the HTML page:

| Handler | Body type | Purpose |
|---------|-----------|---------|
| `pickFile` | — | Open system file picker |
| `saveFile` | `{fileName, data}` (base64) | Save extracted file via Files |
| `shareFile` | `{fileName, data}` (base64) | Share extracted file |
| `showToast` | string | Show a brief message |

The web page calls these via:
```js
window.webkit.messageHandlers.pickFile.postMessage(null);
window.webkit.messageHandlers.saveFile.postMessage({ fileName: 'out.txt', data: '<base64>' });
```

## App Store Distribution

1. Archive the app: **Product → Archive**.
2. Distribute through App Store Connect.
3. Bundle ID: `com.socrtwo.immortalunzip` (update to match your team).
