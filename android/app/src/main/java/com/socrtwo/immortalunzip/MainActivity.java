package com.socrtwo.immortalunzip;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends AppCompatActivity {
    private static final String TAG = "ImmortalUnzip";

    private WebView webView;
    private ValueCallback<Uri[]> filePathCallback;
    private String pendingFileName;
    private byte[] pendingFileData;

    private final ActivityResultLauncher<Intent> filePickerLauncher =
        registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
            if (result.getResultCode() == Activity.RESULT_OK && result.getData() != null) {
                Uri uri = result.getData().getData();
                if (uri != null) handleSelectedFile(uri);
            }
            if (filePathCallback != null) { filePathCallback.onReceiveValue(null); filePathCallback = null; }
        });

    private final ActivityResultLauncher<Intent> saveFileLauncher =
        registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
            if (result.getResultCode() == Activity.RESULT_OK && result.getData() != null) {
                Uri uri = result.getData().getData();
                if (uri != null && pendingFileData != null) saveFileToUri(uri, pendingFileData);
            }
            pendingFileData = null;
            pendingFileName = null;
        });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webView);
        setupWebView();
        webView.loadUrl("file:///android_asset/immortal-unzip.html");
        handleIncomingIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleIncomingIntent(intent);
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_VIEW.equals(intent.getAction())) return;
        Uri uri = intent.getData();
        if (uri == null) return;
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                handleSelectedFile(uri);
            }
        });
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        webView.addJavascriptInterface(new WebAppInterface(), "Android");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView wv, ValueCallback<Uri[]> callback, FileChooserParams params) {
                filePathCallback = callback;
                openFilePicker();
                return true;
            }
        });
    }

    private void openFilePicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{
            "application/zip",
            "application/java-archive",
            "application/vnd.android.package-archive",
            "application/epub+zip",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        });
        filePickerLauncher.launch(intent);
    }

    private void handleSelectedFile(Uri uri) {
        try {
            String fileName = getFileName(uri);
            byte[] fileData = readFileBytes(uri);
            if (fileData == null || fileData.length == 0) return;
            String b64 = Base64.encodeToString(fileData, Base64.NO_WRAP);
            String js = String.format("javascript:loadFileFromAndroid('%s','%s');",
                    escapeJs(fileName), b64);
            webView.evaluateJavascript(js, null);
        } catch (Exception e) {
            Log.e(TAG, "Error reading file", e);
            Toast.makeText(this, "Error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private String getFileName(Uri uri) {
        String result = "unknown.zip";
        if ("content".equals(uri.getScheme())) {
            try (Cursor c = getContentResolver().query(uri, null, null, null, null)) {
                if (c != null && c.moveToFirst()) {
                    int idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                    if (idx >= 0) result = c.getString(idx);
                }
            }
        }
        if (result == null) {
            result = uri.getLastPathSegment();
            if (result == null) result = "file.zip";
        }
        return result;
    }

    private byte[] readFileBytes(Uri uri) throws IOException {
        try (InputStream in = getContentResolver().openInputStream(uri);
             ByteArrayOutputStream buf = new ByteArrayOutputStream()) {
            if (in == null) return null;
            byte[] tmp = new byte[8192]; int n;
            while ((n = in.read(tmp)) != -1) buf.write(tmp, 0, n);
            return buf.toByteArray();
        }
    }

    private String escapeJs(String s) {
        return s.replace("\\","\\\\").replace("'","\\'").replace("\n","\\n").replace("\r","\\r");
    }

    public class WebAppInterface {
        @JavascriptInterface
        public void saveFile(String fileName, String base64Data) {
            try {
                pendingFileName = fileName;
                pendingFileData = Base64.decode(base64Data, Base64.DEFAULT);
                runOnUiThread(() -> {
                    Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType(getMimeType(fileName));
                    intent.putExtra(Intent.EXTRA_TITLE, fileName);
                    saveFileLauncher.launch(intent);
                });
            } catch (Exception e) {
                Log.e(TAG, "saveFile error", e);
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "Save error: " + e.getMessage(), Toast.LENGTH_SHORT).show());
            }
        }

        @JavascriptInterface
        public void shareFile(String fileName, String base64Data) {
            try {
                byte[] data = Base64.decode(base64Data, Base64.DEFAULT);
                File cacheDir = new File(getCacheDir(), "shared");
                if (!cacheDir.exists()) cacheDir.mkdirs();
                File file = new File(cacheDir, fileName);
                try (FileOutputStream fos = new FileOutputStream(file)) { fos.write(data); }
                Uri uri = FileProvider.getUriForFile(MainActivity.this,
                        getPackageName() + ".fileprovider", file);
                runOnUiThread(() -> {
                    Intent share = new Intent(Intent.ACTION_SEND);
                    share.setType(getMimeType(fileName));
                    share.putExtra(Intent.EXTRA_STREAM, uri);
                    share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(Intent.createChooser(share, "Share file"));
                });
            } catch (Exception e) {
                Log.e(TAG, "shareFile error", e);
            }
        }

        @JavascriptInterface
        public void showToast(String message) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show());
        }
    }

    private void saveFileToUri(Uri uri, byte[] data) {
        try (OutputStream out = getContentResolver().openOutputStream(uri)) {
            if (out != null) { out.write(data); Toast.makeText(this, "File saved!", Toast.LENGTH_SHORT).show(); }
        } catch (IOException e) {
            Log.e(TAG, "saveFileToUri", e);
            Toast.makeText(this, "Save error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private String getMimeType(String fileName) {
        String ext = fileName.contains(".") ? fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase() : "";
        switch (ext) {
            case "zip":  return "application/zip";
            case "docx": return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "xlsx": return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            case "pptx": return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
            case "epub": return "application/epub+zip";
            default:     return "application/octet-stream";
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
