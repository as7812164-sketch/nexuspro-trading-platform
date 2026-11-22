import urllib.request
import json

url = 'https://nexuspro-terminal.onrender.com/api/trade/history?limit=30'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("Data type:", type(data))
        if isinstance(data, dict):
            print("Keys:", data.keys())
            trades = data.get("trades") or data.get("history") or []
        else:
            trades = data
        print(f"Total trades: {len(trades)}")
        for t in trades[:20]:
            print(t)
except Exception as e:
    print("Error:", e)
