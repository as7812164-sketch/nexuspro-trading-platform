from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / 'app.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = '''@app.get("/download/apk")
@app.get("/apk")
async def download_apk():
    apk_path = os.path.join(STATIC_DIR, "NexusPro_BB_Mobile_Terminal.apk")
    if os.path.exists(apk_path):
        return FileResponse(apk_path, media_type="application/vnd.android.package-archive", filename="NexusPro_BB_Mobile_Terminal.apk")
    raise HTTPException(status_code=404, detail="APK file not found")'''

replacement = '''@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/json")

@app.get("/download/apk")
@app.get("/apk")
async def download_apk():
    apk_path = os.path.join(STATIC_DIR, "NexusPro_Trading_Terminal.apk")
    if not os.path.exists(apk_path):
        apk_path = os.path.join(STATIC_DIR, "NexusPro_BB_Mobile_Terminal.apk")
    if os.path.exists(apk_path):
        return FileResponse(apk_path, media_type="application/vnd.android.package-archive", filename="NexusPro_Trading_Terminal.apk")
    raise HTTPException(status_code=404, detail="APK file not found")'''

c = c.replace('\r\n', '\n')
target = target.replace('\r\n', '\n')
replacement = replacement.replace('\r\n', '\n')

c = c.replace(target, replacement)
with open(BASE_DIR / 'app.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("[OK] app.py manifest & apk routes updated!")
