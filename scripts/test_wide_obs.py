import urllib.request
import json

url = "https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval=1h&limit=250"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

candles = []
for k in data:
    candles.append({
        "time": int(k[0]) // 1000,
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
        "volume": float(k[5])
    })

# ATR
trs = []
for i in range(1, len(candles)):
    trs.append(max(candles[i]["high"] - candles[i]["low"], 
                   abs(candles[i]["high"] - candles[i-1]["close"]), 
                   abs(candles[i]["low"] - candles[i-1]["close"])))
atr = sum(trs[-14:]) / 14.0

print(f"Total Candles: {len(candles)}, ATR: {atr:.2f}")

obs = []
last_ob_idx = -999

# Scan across 180 bars with min 12-16 bars separation between major structural OBs
scan_start = max(10, len(candles) - 180)

for i in range(scan_start, len(candles) - 1):
    c1 = candles[i - 2]
    c2 = candles[i - 1]
    c3 = candles[i]
    
    # Distance filter: at least 14 bars separation between major structural OBs
    if (i - last_ob_idx) < 14:
        continue
        
    # Multi-bar swing pivot checks
    win = 5
    high_win = [candles[x]["high"] for x in range(max(0, i-win-2), i-2)]
    low_win = [candles[x]["low"] for x in range(max(0, i-win-2), i-2)]
    is_swing_high = c1["high"] >= max(high_win) and c2["high"] < c1["high"]
    is_swing_low = c1["low"] <= min(low_win) and c2["low"] > c1["low"]
    
    disp_bull = (c2["close"] - c2["open"]) >= (atr * 0.9) or (c3["close"] - c3["open"]) >= (atr * 0.9)
    disp_bear = (c2["open"] - c2["close"]) >= (atr * 0.9) or (c3["open"] - c3["close"]) >= (atr * 0.9)
    sweep_low = c2["low"] < c1["low"]
    sweep_high = c2["high"] > c1["high"]
    
    if (disp_bull and (is_swing_low or sweep_low)) or (sweep_low and (c2["close"] > c1["high"])):
        ob_top = c1["high"]
        ob_bottom = min(c1["low"], c2["low"])
        if ob_top - ob_bottom < atr * 0.25:
            ob_bottom = ob_top - (atr * 0.40)
        ob_mid = (ob_top + ob_bottom) / 2.0
        
        if sweep_low and (c2["close"] > c1["high"]):
            theme = "COND"
            title = "COND-OB"
            model = "Type 6: Sweep+BOS Leg OB"
        elif c1["close"] < c1["open"]:
            theme = "STRONG_BULL"
            title = "STRONG-OB"
            model = "Type 2: Classic Opposite-Color OB"
        else:
            theme = "WEAK"
            title = "WEAK-OB (SWEEP REQ)"
            model = "Type 1: Momentum Same-Color OB"
            
        mit_time = None
        for k in range(i + 1, len(candles)):
            if candles[k]["low"] <= ob_top:
                mit_time = candles[k]["time"]
                break
                
        obs.append({
            "theme": theme, "title": title, "model": model,
            "top": round(ob_top, 2), "bottom": round(ob_bottom, 2),
            "bar": i, "mitigated": mit_time is not None
        })
        last_ob_idx = i
        
    elif (disp_bear and (is_swing_high or sweep_high)) or (sweep_high and (c2["close"] < c1["low"])):
        ob_top = max(c1["high"], c2["high"])
        ob_bottom = c1["low"]
        if ob_top - ob_bottom < atr * 0.25:
            ob_top = ob_bottom + (atr * 0.40)
        ob_mid = (ob_top + ob_bottom) / 2.0
        
        if is_swing_high and c1["close"] > c1["open"]:
            theme = "STRONG_BEAR"
            title = "STRONG-OB"
            model = "Type 2: Classic Opposite-Color OB"
        elif sweep_high:
            theme = "COND"
            title = "COND-OB"
            model = "Type 6: Sweep+BOS Leg OB"
        else:
            theme = "WEAK"
            title = "WEAK-OB (SWEEP REQ)"
            model = "Type 1: Momentum Same-Color OB"
            
        mit_time = None
        for k in range(i + 1, len(candles)):
            if candles[k]["high"] >= ob_bottom:
                mit_time = candles[k]["time"]
                break
                
        obs.append({
            "theme": theme, "title": title, "model": model,
            "top": round(ob_top, 2), "bottom": round(ob_bottom, 2),
            "bar": i, "mitigated": mit_time is not None
        })
        last_ob_idx = i

print(f"Detected {len(obs)} OBs spaced across 180 bars:")
for o in obs[-7:]:
    st = "MIT" if o["mitigated"] else "ACT"
    print(f"  Bar {o['bar']}: [{o['theme']}] {o['title']} ({o['model']}) Top: {o['top']} - Bot: {o['bottom']} [{st}]")
