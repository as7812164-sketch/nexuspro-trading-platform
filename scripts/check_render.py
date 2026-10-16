import urllib.request
import json
import time

url = "https://nexuspro-terminal.onrender.com"
print(f"Checking Render live deployment at {url}...")

endpoints = [
    "/trade",
    "/nexus/trade",
    "/markets",
    "/nexus/markets",
    "/assets",
    "/nexus/assets",
    "/api/ticker/BTCUSDT",
    "/api/klines/BTCUSDT?interval=15m&limit=5",
    "/api/orderbook/BTCUSDT?depth=5"
]

for ep in endpoints:
    full_url = f"{url}{ep}"
    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            content = resp.read()
            if "api" in ep:
                data = json.loads(content)
                if "ticker" in ep:
                    print(f"  [PASS] {ep} -> {code} | Price: ${data.get('last_price')} | 24h: {data.get('price_change_pct')}%")
                elif "klines" in ep:
                    print(f"  [PASS] {ep} -> {code} | Candles count: {len(data.get('candles', []))}")
                elif "orderbook" in ep:
                    print(f"  [PASS] {ep} -> {code} | Best Ask: {data.get('asks', [[]])[0]}")
            else:
                print(f"  [PASS] {ep} -> {code} (HTML length: {len(content)} bytes)")
    except Exception as e:
        print(f"  [RETRYING] {ep} -> {e}")
