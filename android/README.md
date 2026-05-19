# Immortal Unzip — Android

Android app wrapping the Immortal Unzip HTML engine in a full-screen **WebView**. Supports Android 7.0+ (API 24+).

## Requirements

- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34
- Gradle 8.2+

## Quick Start

1. Open the `android/` folder as a project in Android Studio.
2. Let Gradle sync complete.
3. Connect a device (USB debugging enabled) or start an emulator.
4. Click **Run** (▶).

## Build Release APK

```bash
cd android
./gradlew assembleRelease
```

Output: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

Sign with your keystore before distributing to the Play Store.

## Features

- Opens `.zip`, `.epub`, `.docx`, `.xlsx`, `.pptx` files from other apps
- Native Save dialog using Android Storage Access Framework
- Native Share sheet for extracted files
- Works offline — HTML engine is bundled as an asset

## Project Structure

```
android/
├── app/
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── assets/
│   │   │   └── immortal-unzip.html       ← App UI (bundled)
│   │   ├── java/com/socrtwo/immortalunzip/
│   │   │   └── MainActivity.java         ← WebView host + JS interface
│   │   └── res/
│   │       ├── layout/activity_main.xml
│   │       ├── values/{strings,colors,themes}.xml
│   │       └── xml/file_paths.xml        ← FileProvider paths
│   └── build.gradle
├── build.gradle
├── settings.gradle
├── gradle.properties
└── README.md
```

## JavaScript Interface (Android)

The `Android` object is exposed to the HTML page:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `saveFile` | `(fileName: string, base64: string)` | Save via SAF |
| `shareFile` | `(fileName: string, base64: string)` | Share via Android share sheet |
| `showToast` | `(message: string)` | Show a brief Toast |

Usage from HTML:
```js
Android.saveFile('output.zip', base64data);
Android.showToast('Extraction complete');
```

## Play Store Distribution

1. Set `applicationId` in `app/build.gradle` to your unique ID.
2. Generate a signed APK/AAB in Android Studio: **Build → Generate Signed Bundle/APK**.
3. Upload to Google Play Console.
