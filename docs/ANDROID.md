# Building the Field Sales APK

The APK is a Capacitor 6 shell around the mobile web app in `salesperson-web/`.
There is no separate native codebase — the Android project only hosts the WebView
and the plugins.

## Prerequisites

| Tool | Version used here | Notes |
|---|---|---|
| Node | 20+ | 26.0.0 used |
| JDK | 17 | `brew install openjdk@17` (Gradle 8.2 + AGP 8.x) |
| Android SDK | platform **34**, build-tools **34.0.0** | `compileSdk`/`targetSdk` are 34, `minSdk` 22 |
| Android Studio | optional | only needed for the emulator or `cap open android` |

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17        # macOS / Homebrew
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$JAVA_HOME/bin:$PATH"
```

`salesperson-web/android/local.properties` must point at the SDK:

```properties
sdk.dir=/Users/<you>/Library/Android/sdk
```

## 1. Point the app at a reachable API

The bundle is built with `VITE_API_BASE_URL` baked in, so set it **before**
building:

```bash
cd salesperson-web
cp .env.example .env
```

| Target | Value |
|---|---|
| Android emulator against a local backend | `http://10.0.2.2:8000/api/v1` |
| Physical phone on the same Wi-Fi | `http://192.168.x.y:8000/api/v1` |
| Production | `https://api.yourdomain.com/api/v1` |

Cleartext HTTP is only allowed for `10.0.2.2`, `localhost` and `127.0.0.1`
(see `android/app/src/main/res/xml/network_security_config.xml`). **Any real
deployment must use HTTPS**; the base config already refuses everything else.

Also add the app's origin to the backend's CORS list when testing in a browser:

```
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

(The APK itself runs on the `https://localhost` Capacitor scheme and needs no
CORS entry.)

## 2. Debug APK (installable, for the team)

```bash
cd salesperson-web
npm install
npm run apk:debug        # build + cap sync + gradlew assembleDebug
```

Output:

```
salesperson-web/android/app/build/outputs/apk/debug/app-debug.apk
```

Install it:

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
# or copy the .apk to the phone and open it (allow "install unknown apps")
```

## 3. Release APK (signed)

Create a keystore once, keep it out of the repository:

```bash
keytool -genkey -v -keystore fieldsales-release.jks \
        -keyalg RSA -keysize 2048 -validity 10000 -alias fieldsales
```

Then either create `salesperson-web/android/keystore.properties`
(see `keystore.properties.example`):

```properties
storeFile=/absolute/path/to/fieldsales-release.jks
storePassword=…
keyAlias=fieldsales
keyPassword=…
```

…or export `ANDROID_KEYSTORE_FILE`, `ANDROID_KEYSTORE_PASSWORD`,
`ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. Then:

```bash
npm run apk:release
# → android/app/build/outputs/apk/release/app-release.apk
```

Without a keystore the same command still succeeds and produces
`app-release-unsigned.apk`, which Android will not install — sign it with
`apksigner` or configure the keystore above.

For Play Store distribution build a bundle instead:

```bash
cd android && ./gradlew bundleRelease   # → app/build/outputs/bundle/release/app-release.aab
```

## 4. Icon and splash screen

Source art lives in `salesperson-web/resources/` (`icon.png` 1024×1024,
`icon-foreground.png`, `icon-background.png`, `splash.png` 2732×2732). Regenerate
every density after changing it:

```bash
npx @capacitor/assets generate --android
```

## What the shell is configured to do

| Concern | Where | Behaviour |
|---|---|---|
| App id / name | `capacitor.config.ts` | `in.tradercrm.fieldsales`, "Field Sales" |
| Orientation | `AndroidManifest.xml` | portrait only |
| Splash | `capacitor.config.ts` + generated drawables | navy splash, hidden by the app once React mounts |
| External links | `src/lib/native.ts` → `window.open(url, '_blank')` | Google Maps / `tel:` / `wa.me` open in the native app via an Android intent; `<queries>` in the manifest covers Android 11+ package visibility |
| Hardware back | `src/lib/native.ts` + `App.tsx` | navigates back inside the app; from a tab root it asks before exiting, so a half-written report is not lost |
| Session | Capacitor Preferences (app-private storage) | survives app restarts; cleared on logout or a `401` |
| Backups | `backup_rules.xml`, `allowBackup=false` | the token is never included in device backups |
| Offline | `src/lib/offline.ts` | completion outbox, flushed on reconnect / resume |
| Network state | `@capacitor/network` | triggers the outbox flush |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Unable to locate a Java Runtime` | export `JAVA_HOME` as above |
| `SDK location not found` | create `android/local.properties` with `sdk.dir` |
| `Failed to resolve: com.android.tools.build` | install Android SDK platform 34 + build-tools 34.0.0 (`sdkmanager "platforms;android-34" "build-tools;34.0.0"`) |
| App shows "No internet connection" on a device | `VITE_API_BASE_URL` points at `localhost` — use the LAN IP or `10.0.2.2`, and rebuild (the URL is baked into the bundle) |
| Login says "This app is for field salespeople" | that account is ADMIN/USER; the APK only accepts `SALESPERSON` accounts |
| White screen after an update | `npm run build && npx cap sync android` before rebuilding; the APK serves the `dist/` snapshot |
