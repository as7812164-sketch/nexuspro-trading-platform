"""
BUILD & SIGN 100% NATIVE NEXUSPRO ANDROID WEBVIEW APK (v2.1.0)
================================================================
- Clones proven pure Native WebView template (LauncherActivity -> android.webkit.WebView)
- ZERO Chrome Custom Tab / TWA URL bar (No address bar, full native screen)
- Dark #080B11 Status & Navigation bars with fitsSystemWindows=true
- Loads https://nexuspro-terminal.onrender.com/mobile (1:1 TradeZone Modular OLED UI Clone)
- Uses authentic Neon Cyber NexusPro icons & splash assets
- Compiles via apktool.jar & signs via uber-apk-signer.jar
- Saves to Desktop, static/, and optionally dispatches to Akash bhai via Telegram
"""

import os
import sys
import re
import shutil
import subprocess
import json
import urllib.request
import ssl

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = r"C:\Users\power\.gemini\antigravity\scratch\smc_v17_trading_system"
TEMPLATE_SRC = os.path.join(WORKSPACE, "hermes35_apk_src")       # Proven pure native WebView source
ICON_SRC = os.path.join(WORKSPACE, "nexuspro_apk_src")           # Authentic NexusPro icons & splash
NATIVE_SRC = os.path.join(WORKSPACE, "nexuspro_native_apk_src")  # Isolated clean build dir

TOOLS_DIR = os.path.join(WORKSPACE, "tools")
JAVA_EXE = os.path.join(TOOLS_DIR, "jre", "bin", "java.exe")
APKTOOL_JAR = os.path.join(TOOLS_DIR, "apktool.jar")
SIGNER_JAR = os.path.join(TOOLS_DIR, "uber-apk-signer.jar")

DESKTOP_APK = r"C:\Users\power\Desktop\NexusPro_Trading_Terminal.apk"
STATIC_APK = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\NexusPro_Trading_Terminal.apk"
DIST_DIR = os.path.join(WORKSPACE, "nexuspro_native_dist")
UNSIGNED_APK = os.path.join(WORKSPACE, "nexuspro_native_unsigned.apk")

# Dedicated isolated NexusPro bot (@SMC_1H_Trigger_Bot), fallback to primary bot only if unreachable
NEXUS_BOT_TOKEN = "8685685362:AAFWkKvRIs6cJ70gegcJVFyKB5soDtEttbU"
FALLBACK_BOT_TOKEN = "8593127726:AAGdudgSBU_krN-g42Cq_5ovc5DW2c6A-yY"
TELEGRAM_CHAT_ID = "752247227"

TARGET_HOST = "nexuspro-terminal.onrender.com"
TARGET_URL = "https://nexuspro-terminal.onrender.com/mobile"
PKG_NAME = "com.nexuspro.trading.terminal"


def prepare_native_source():
    print("[1/5] Preparing isolated pure Native WebView source directory...")
    if os.path.exists(NATIVE_SRC):
        shutil.rmtree(NATIVE_SRC)
    shutil.copytree(TEMPLATE_SRC, NATIVE_SRC)

    # Clean leftover build cache & legacy hermes35 offline www bundle (keeps APK lightweight & 100% live Render synced)
    for rel in ["build", os.path.join("assets", "www")]:
        p = os.path.join(NATIVE_SRC, rel)
        if os.path.exists(p):
            shutil.rmtree(p)

    # Copy NexusPro custom icons, maskables, adaptive icon XML, and splash screens
    print("[2/5] Copying NexusPro Cyber N icons & dark splash assets...")
    res_folders = [
        "mipmap-mdpi", "mipmap-hdpi", "mipmap-xhdpi", "mipmap-xxhdpi", "mipmap-xxxhdpi",
        "mipmap-anydpi-v26",
        "drawable-mdpi", "drawable-hdpi", "drawable-xhdpi", "drawable-xxhdpi", "drawable-xxxhdpi"
    ]
    for folder in res_folders:
        src_f = os.path.join(ICON_SRC, "res", folder)
        dst_f = os.path.join(NATIVE_SRC, "res", folder)
        if os.path.exists(src_f):
            os.makedirs(dst_f, exist_ok=True)
            for fname in os.listdir(src_f):
                if fname.endswith((".png", ".xml")):
                    shutil.copy2(os.path.join(src_f, fname), os.path.join(dst_f, fname))

    # Write clean Native WebView AndroidManifest.xml (ZERO TWA / Chrome Custom Tab dependencies)
    manifest_xml = f"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    android:compileSdkVersion="36"
    android:compileSdkVersionCodename="16"
    package="{PKG_NAME}"
    platformBuildVersionCode="36"
    platformBuildVersionName="16">

    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>

    <application
        android:allowBackup="true"
        android:extractNativeLibs="false"
        android:hardwareAccelerated="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/appName"
        android:name="{PKG_NAME}.Application"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.NoTitleBar"
        android:usesCleartextTraffic="true">

        <activity
            android:alwaysRetainTaskState="true"
            android:configChanges="orientation|screenSize|keyboardHidden|screenLayout"
            android:exported="true"
            android:fitsSystemWindows="true"
            android:hardwareAccelerated="true"
            android:label="@string/launcherName"
            android:launchMode="singleTask"
            android:name="{PKG_NAME}.LauncherActivity"
            android:screenOrientation="portrait"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

    </application>
</manifest>
"""
    with open(os.path.join(NATIVE_SRC, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest_xml)

    # Update strings.xml cleanly
    strings_path = os.path.join(NATIVE_SRC, "res", "values", "strings.xml")
    with open(strings_path, "r", encoding="utf-8") as f:
        s = f.read()

    s = re.sub(r'<string name="appName">.*?</string>', '<string name="appName">NexusPro Futures Terminal</string>', s)
    s = re.sub(r'<string name="launcherName">.*?</string>', '<string name="launcherName">NexusPro</string>', s)
    s = re.sub(r'<string name="hostName">.*?</string>', f'<string name="hostName">{TARGET_HOST}</string>', s)
    s = re.sub(r'<string name="launchUrl">.*?</string>', f'<string name="launchUrl">{TARGET_URL}</string>', s)
    s = re.sub(r'<string name="webManifestUrl">.*?</string>', f'<string name="webManifestUrl">https://{TARGET_HOST}/manifest.json</string>', s)
    s = re.sub(r'<string name="providerAuthority">.*?</string>', f'<string name="providerAuthority">{PKG_NAME}.fileprovider</string>', s)
    s = s.replace("https://trdzone.duckdns.org", f"https://{TARGET_HOST}")
    s = s.replace("trdzone.duckdns.org", TARGET_HOST)
    s = s.replace("com.hermes35.radar.terminal", PKG_NAME)

    with open(strings_path, "w", encoding="utf-8") as f:
        f.write(s)

    # Bump version in apktool.yml -> v2.1.0 (versionCode: 11)
    yml_path = os.path.join(NATIVE_SRC, "apktool.yml")
    with open(yml_path, "r", encoding="utf-8") as f:
        yml = f.read()
    yml = re.sub(r'versionCode:\s*\d+', 'versionCode: 11', yml)
    yml = re.sub(r'versionName:\s*[^\r\n]+', 'versionName: 2.1.0', yml)
    yml = re.sub(r'apkFileName:\s*[^\r\n]+', 'apkFileName: NexusPro_Trading_Terminal.apk', yml)
    with open(yml_path, "w", encoding="utf-8") as f:
        f.write(yml)

    # Migrate Smali package (hermes35 -> nexuspro) & bind live Render /mobile URL (keep portrait lock = 1 matching sample APK CSS rotator)
    old_smali_dir = os.path.join(NATIVE_SRC, "smali", "com", "hermes35", "radar", "terminal")
    new_smali_dir = os.path.join(NATIVE_SRC, "smali", "com", "nexuspro", "trading", "terminal")
    os.makedirs(new_smali_dir, exist_ok=True)

    for fname in os.listdir(old_smali_dir):
        if not fname.endswith(".smali"):
            continue
        with open(os.path.join(old_smali_dir, fname), "r", encoding="utf-8") as f:
            code = f.read()

        code = code.replace("Lcom/hermes35/radar/terminal/", "Lcom/nexuspro/trading/terminal/")
        code = code.replace("com.hermes35.radar.terminal", PKG_NAME)
        code = code.replace("https://trdzone.duckdns.org/mobile", TARGET_URL)
        code = code.replace("https://trdzone.duckdns.org/static/mobile.html", TARGET_URL)
        code = code.replace("https://trdzone.duckdns.org", f"https://{TARGET_HOST}")
        code = code.replace("trdzone.duckdns.org", TARGET_HOST)

        with open(os.path.join(new_smali_dir, fname), "w", encoding="utf-8") as f:
            f.write(code)

    shutil.rmtree(os.path.join(NATIVE_SRC, "smali", "com", "hermes35"))
    print("    -> Smali package migrated & URLs bound to:", TARGET_URL)


def compile_and_sign():
    print("[3/5] Compiling Native APK with apktool...")
    if os.path.exists(UNSIGNED_APK):
        os.remove(UNSIGNED_APK)

    cmd_build = [JAVA_EXE, "-jar", APKTOOL_JAR, "b", NATIVE_SRC, "-o", UNSIGNED_APK]
    res = subprocess.run(cmd_build, cwd=WORKSPACE, stdin=subprocess.DEVNULL, timeout=90, capture_output=True, text=True)
    if res.returncode != 0:
        print("APKTOOL STDOUT:", res.stdout)
        print("APKTOOL STDERR:", res.stderr)
        raise RuntimeError("Apktool compilation failed!")

    print("[4/5] Signing Native APK with uber-apk-signer...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)

    cmd_sign = [JAVA_EXE, "-jar", SIGNER_JAR, "-a", UNSIGNED_APK, "-o", DIST_DIR]
    res_s = subprocess.run(cmd_sign, cwd=WORKSPACE, stdin=subprocess.DEVNULL, timeout=60, capture_output=True, text=True)
    if res_s.stdout:
        print(res_s.stdout.strip())
    if res_s.returncode != 0:
        print("SIGNER STDERR:", res_s.stderr)
        raise RuntimeError("Uber-apk-signer failed!")

    signed_apk = None
    for f in os.listdir(DIST_DIR):
        if f.endswith("-aligned-debugSigned.apk"):
            signed_apk = os.path.join(DIST_DIR, f)
            break

    if not signed_apk or not os.path.exists(signed_apk):
        raise FileNotFoundError(f"Signed APK missing in {DIST_DIR}")

    shutil.copy2(signed_apk, DESKTOP_APK)
    shutil.copy2(signed_apk, STATIC_APK)
    size_mb = os.path.getsize(DESKTOP_APK) / (1024 * 1024)
    print(f"    -> Saved Desktop APK: {DESKTOP_APK} ({size_mb:.2f} MB)")
    print(f"    -> Saved Static APK:  {STATIC_APK} ({size_mb:.2f} MB)")
    return size_mb


def send_telegram(size_mb):
    print("[5/5] Dispatching Native APK to Akash bhai via Telegram...")
    caption = (
        "🏛️ *NEXUSPRO • NATIVE CLONE TERMINAL APK (v2.1.0)* 📱⚡\n\n"
        "🎯 *Exact 1:1 Sample Shell & Modular OLED Architecture:*\n"
        "• 🛡️ *Zero Browser Bar:* Pure Android WebView Shell (Bilkul sample app jaisa OLED UI & layout!)\n"
        "• 🔗 *Live Render Endpoint:* `https://nexuspro-terminal.onrender.com/mobile`\n"
        "• 📊 *Chart Indicator:* Hermes MS-OB v2.0 GOLDEN (7-Model First Tap, 50% MT, Transparent Labels — Old Indicator & GEX Removed)\n"
        "• ⚖️ *Risk Engine:* $1,000 Flat | 5% Margin ($50) | 5x Isolated | +12%->+2.5% BE | -15% SL (2x15m) | +15% TP\n"
        "• 🔒 *Sample App Untouched:* Alag package (`com.nexuspro.trading.terminal`) — aapke sample app aur `trdzone` settings par ZERO impact.\n\n"
        f"📦 *Version:* `v2.1.0 (Build 11)` | *Size:* `{size_mb:.2f} MB`\n"
        "👉 *Tap karke install karein — sab live data, setups aur chart instant chalega!*"
    )

    for tok in [NEXUS_BOT_TOKEN, FALLBACK_BOT_TOKEN]:
        boundary = "----WebKitFormBoundaryNexusProNativeAPK"
        body = bytearray()

        def add_field(name, value):
            return f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")

        body.extend(add_field("chat_id", TELEGRAM_CHAT_ID))
        body.extend(add_field("caption", caption))
        body.extend(add_field("parse_mode", "Markdown"))
        body.extend(
            f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="NexusPro_Trading_Terminal.apk"\r\nContent-Type: application/vnd.android.package-archive\r\n\r\n'.encode("utf-8")
        )
        with open(DESKTOP_APK, "rb") as f:
            body.extend(f.read())
        body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendDocument", data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                res = json.loads(resp.read().decode())
                if res.get("ok"):
                    print(f"[OK] Native APK sent to Telegram cleanly via bot {tok[:10]}...!")
                    return True
        except Exception as e:
            print(f"[WARN] Telegram send failed via {tok[:10]}...: {e}")
    return False


if __name__ == "__main__":
    if "--send-only" in sys.argv:
        if not os.path.exists(DESKTOP_APK):
            raise FileNotFoundError(f"APK missing at {DESKTOP_APK}")
        sz = os.path.getsize(DESKTOP_APK) / (1024 * 1024)
        ok = send_telegram(sz)
        if not ok:
            sys.exit(1)
        print("\n[SUCCESS] Telegram APK dispatch complete!")
    else:
        prepare_native_source()
        sz = compile_and_sign()
        if "--no-telegram" not in sys.argv:
            send_telegram(sz)
        print("\n[SUCCESS] NexusPro Pure Native Android APK (v2.1.0) build complete!")
