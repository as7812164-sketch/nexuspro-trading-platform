import subprocess
import time
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
output_path = r"C:\Users\power\.gemini\antigravity\brain\dcc51f2a-4d4e-4c0e-9f17-414b6ff083d5\nexuspro_hermes_msob_chart.png"
url = "https://nexuspro-terminal.onrender.com/trade?symbol=PAXGUSDT"

cmd = [
    chrome_path,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-size=1280,850",
    "--virtual-time-budget=10000",
    f"--screenshot={output_path}",
    url
]

print(f"Launching Chrome to capture: {url}")
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"Chrome return code: {result.returncode}")
if os.path.exists(output_path):
    size = os.path.getsize(output_path)
    print(f"[SUCCESS] Screenshot captured successfully! Size: {size} bytes at {output_path}")
else:
    print("[ERROR] Screenshot file was not created.")
