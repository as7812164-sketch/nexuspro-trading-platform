import urllib.request
import json
import ssl

ctx = ssl._create_unverified_context()
base = "https://nexuspro-terminal.onrender.com"

req = urllib.request.Request(base + "/api/status", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("=== LIVE STATUS ===")
    for k in ["strategy", "allowed_direction", "first_tap_rule", "mode", "default_leverage", "dynamic_armor", "active_positions", "scanned_setups_count"]:
        print(f" * {k}: {data.get(k)}")

req2 = urllib.request.Request(base + "/api/deca/setups", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req2, context=ctx, timeout=10) as resp:
    data2 = json.loads(resp.read().decode("utf-8"))
    print("\n=== LIVE SETUPS ===")
    setups = data2.get("setups", [])
    print(" * Total Setups:", len(setups))
    s1h = [s for s in setups if s.get("timeframe") == "1H"]
    s4h = [s for s in setups if s.get("timeframe") == "4H"]
    print(f" * 1H Setups Count: {len(s1h)} | 4H Setups Count: {len(s4h)}")
    print("\nSample 1H Setups:")
    for s in s1h[:3]:
        print(f"   - {s.get('symbol')} (1H) {s.get('side')} | Status: {s.get('status')} | Prox: {s.get('proximity_pct')}% | Anchor: {s.get('anchor_name')}")
    print("\nSample 4H Setups:")
    for s in s4h[:3]:
        print(f"   - {s.get('symbol')} (4H) {s.get('side')} | Status: {s.get('status')} | Prox: {s.get('proximity_pct')}% | Anchor: {s.get('anchor_name')}")
