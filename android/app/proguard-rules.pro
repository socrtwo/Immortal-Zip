# Add project specific ProGuard rules here.
-keep class com.socrtwo.immortalunzip.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
