"""
BUILD & SIGN NATIVE NEXUSPRO ANDROID APK
========================================
- Configures Android TWA package to https://nexuspro-terminal.onrender.com/trade
- Compiles via apktool.jar
- Signs via uber-apk-signer.jar
- Copies to Desktop and static folder
- Dispatches via Telegram to Akash bhai (Chat 752247227)
"""

import os
import sys
import shutil
import subprocess
import json
import urllib.request
import ssl

WORKSPACE = r"C:\Users\power\.gemini\antigravity\scratch\smc_v17_trading_system"
APK_SRC = os.path.join(WORKSPACE, "nexuspro_apk_src")
TOOLS_DIR = os.path.join(WORKSPACE, "tools")
JAVA_EXE = os.path.join(TOOLS_DIR, "jre", "bin", "java.exe")
APKTOOL_JAR = os.path.join(TOOLS_DIR, "apktool.jar")
SIGNER_JAR = os.path.join(TOOLS_DIR, "uber-apk-signer.jar")

DESKTOP_APK = r"C:\Users\power\Desktop\NexusPro_Trading_Terminal.apk"
STATIC_APK = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\NexusPro_Trading_Terminal.apk"
DIST_DIR = os.path.join(WORKSPACE, "nexuspro_dist")
UNSIGNED_APK = os.path.join(WORKSPACE, "nexuspro_render_unsigned.apk")

TELEGRAM_TOKEN = "8593127726:AAGdudgSBU_krN-g42Cq_5ovc5DW2c6A-yY"
TELEGRAM_CHAT_ID = "752247227"

def patch_apk_strings():
    print("[1] Patching strings.xml for NexusPro on Render...")
    strings_path = os.path.join(APK_SRC, "res", "values", "strings.xml")
    with open(strings_path, "r", encoding="utf-8") as f:
        c = f.read()

    # Replace host and launchUrl
    c = c.replace("trdzone.duckdns.org", "nexuspro-terminal.onrender.com")
    c = c.replace(
        '<string name="launchUrl">https://nexuspro-terminal.onrender.com/mobile?native=1&amp;v=104</string>',
        '<string name="launchUrl">https://nexuspro-terminal.onrender.com/trade?view=mobile&amp;native=1</string>'
    )
    c = c.replace(
        '<string name="webManifestUrl">https://nexuspro-terminal.onrender.com/static/nexus_manifest.json</string>',
        '<string name="webManifestUrl">https://nexuspro-terminal.onrender.com/manifest.json</string>'
    )
    c = c.replace(
        '<string name="appName">NexusPro APEX Trading Terminal</string>',
        '<string name="appName">NexusPro Futures Terminal</string>'
    )

    with open(strings_path, "w", encoding="utf-8") as f:
        f.write(c)
    print("strings.xml patched successfully.")

    # Bump apktool.yml
    yml_path = os.path.join(APK_SRC, "apktool.yml")
    with open(yml_path, "r", encoding="utf-8") as f:
        yml = f.read()
    yml = yml.replace("versionCode: 5", "versionCode: 6")
    yml = yml.replace("versionName: 1.0.4", "versionName: 1.0.5")
    yml = yml.replace("apkFileName: HERMES 2.5 APEX Trading Terminal.apk", "apkFileName: NexusPro_Trading_Terminal.apk")
    with open(yml_path, "w", encoding="utf-8") as f:
        f.write(yml)
    print("apktool.yml bumped to v1.0.5 (code 6).")

def compile_apk():
    print("[2] Compiling APK with apktool...")
    if os.path.exists(UNSIGNED_APK):
        try: os.remove(UNSIGNED_APK)
        except: pass

    cmd_build = [JAVA_EXE, "-jar", APKTOOL_JAR, "b", APK_SRC, "-o", UNSIGNED_APK]
    res = subprocess.run(cmd_build, cwd=WORKSPACE, stdin=subprocess.DEVNULL, timeout=75, capture_output=True, text=True)
    if res.returncode != 0:
        print("Apktool error:", res.stderr)
        raise RuntimeError("Apktool compilation failed!")
    print("Apktool compilation complete. Output:", UNSIGNED_APK)

def sign_apk():
    print("[3] Signing APK with uber-apk-signer...")
    os.makedirs(DIST_DIR, exist_ok=True)
    cmd_sign = [JAVA_EXE, "-jar", SIGNER_JAR, "-a", UNSIGNED_APK, "-o", DIST_DIR, "--overwrite"]
    res = subprocess.run(cmd_sign, cwd=WORKSPACE, stdin=subprocess.DEVNULL, timeout=60, capture_output=True, text=True)
    if res.returncode != 0:
        print("Signer error:", res.stderr)
        raise RuntimeError("Uber-apk-signer failed!")

    signed_candidate = os.path.join(DIST_DIR, "nexuspro_render_unsigned-aligned-debugSigned.apk")
    if not os.path.exists(signed_candidate):
        for f in os.listdir(DIST_DIR):
            if f.endswith("-aligned-debugSigned.apk"):
                signed_candidate = os.path.join(DIST_DIR, f)
                break

    if not os.path.exists(signed_candidate):
        raise FileNotFoundError(f"Signed APK not found in {DIST_DIR}")

    shutil.copy2(signed_candidate, DESKTOP_APK)
    shutil.copy2(signed_candidate, STATIC_APK)
    size_mb = os.path.getsize(DESKTOP_APK) / (1024 * 1024)
    print(f"[OK] Signed APK saved to Desktop: {DESKTOP_APK} ({size_mb:.2f} MB)")
    print(f"[OK] Signed APK saved to Static: {STATIC_APK}")
    return size_mb

def send_telegram(size_mb):
    print("[4] Dispatching APK to Telegram chat 752247227...")
    caption = (
        "🏛️ *NEXUSPRO INSTITUTIONAL FUTURES TERMINAL (NATIVE ANDROID APK)* 📱\n\n"
        "⚡ *Release Notes v1.0.5:*\n"
        "• 🎯 *Strategy:* HERMES_MS_OB (7-Model Order Block Architecture)\n"
        "• 🛡️ *Compounding:* Permanently Disabled (Normal Futures Trading)\n"
        "• 💰 *Portfolio:* $1,000.00 USDT Total Balance\n"
        "• 📊 *Margin:* Flat 5% ($50.00 USDT) Per Trade | 5x Leverage ($250 Size)\n"
        "• ⛔ *Hard SL:* -15.0% ROI (-3.0% Price Move)\n"
        "• 🎯 *Full Book TP:* +15.0% ROI (+3.0% Price Move)\n"
        "• ⚔️ *Execution:* Dual LONG & SHORT (Crypto 1H/4H & Gold 15m/1H/4H)\n"
        "• 🔒 *Direct Server:* https://nexuspro-terminal.onrender.com/trade\n\n"
        f"📦 *File:* `NexusPro_Trading_Terminal.apk` ({size_mb:.2f} MB)\n"
        "🟢 *Ready for Instant Installation on Android!*"
    )

    boundary = "----WebKitFormBoundaryNexusProUploadHermes"
    body = bytearray()

    def add_field(name, value):
        return f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")

    body.extend(add_field("chat_id", TELEGRAM_CHAT_ID))
    body.extend(add_field("caption", caption))
    body.extend(add_field("parse_mode", "Markdown"))
    body.extend(
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="NexusPro_Trading_Terminal.apk"\r\nContent-Type: application/vnd.android.package-archive\r\n\r\n'.encode(
            "utf-8"
        )
    )

    with open(DESKTOP_APK, "rb") as f:
        body.extend(f.read())
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            res = json.loads(resp.read().decode())
            if res.get("ok"):
                print("[OK] APK successfully delivered to Telegram!")
            else:
                print("Telegram API response:", res)
    except Exception as e:
        print("Telegram delivery error:", e)

if __name__ == "__main__":
    patch_apk_strings()
    compile_apk()
    size_mb = sign_apk()
    send_telegram(size_mb)
