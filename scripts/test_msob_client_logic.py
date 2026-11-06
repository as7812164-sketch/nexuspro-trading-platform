import urllib.request
import json

def test_symbol(symbol="PAXGUSDT", interval="1h"):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit=120"
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
    
    # Calculate ATR
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i-1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs[-14:]) / 14.0 if trs else 1.0

    print(f"\n--- {symbol} {interval} (Last Price: {candles[-1]['close']}, ATR: {atr:.2f}) ---")
    
    obs = []
    start_idx = max(3, len(candles) - 80)
    for i in range(start_idx, len(candles) - 1):
        c1 = candles[i - 2]
        c2 = candles[i - 1]
        c3 = candles[i]
        
        # Bullish
        disp_bull = (c2["close"] - c2["open"]) >= (atr * 0.75)
        fvg_bull = c3["low"] > c1["high"] and (c3["low"] - c1["high"]) >= (atr * 0.10)
        if disp_bull and (fvg_bull or (c2["close"] - c2["open"]) >= atr * 1.1):
            is_c1_bear = c1["close"] < c1["open"]
            is_sweep = c2["low"] < c1["low"]
            ob_top = c1["high"]
            ob_bottom = c2["low"] if is_sweep else c1["low"]
            if ob_top - ob_bottom < atr * 0.15:
                ob_bottom = ob_top - (atr * 0.25)
            ob_mid = (ob_top + ob_bottom) / 2.0
            
            # Category
            if is_sweep:
                cat = "COND"
                title = "COND-OB"
                model = "Type 6: Sweep+BOS Leg OB"
                theme = "COND"
            elif is_c1_bear:
                cat = "STRONG"
                title = "STRONG-OB"
                model = "Type 2: Classic Opposite-Color OB"
                theme = "STRONG_BULL"
            else:
                cat = "WEAK"
                title = "WEAK-OB (SWEEP REQ)"
                model = "Type 1: Momentum Same-Color OB"
                theme = "WEAK"
                
            mit_idx = None
            for k in range(i + 1, len(candles)):
                if candles[k]["low"] <= ob_top:
                    mit_idx = k
                    break
            obs.append({
                "side": "BULL",
                "title": title,
                "model": model,
                "top": round(ob_top, 2),
                "bottom": round(ob_bottom, 2),
                "mid": round(ob_mid, 2),
                "mitigated": mit_idx is not None,
                "start_time": c1["time"]
            })

        # Bearish
        disp_bear = (c2["open"] - c2["close"]) >= (atr * 0.75)
        fvg_bear = c1["low"] > c3["high"] and (c1["low"] - c3["high"]) >= (atr * 0.10)
        if disp_bear and (fvg_bear or (c2["open"] - c2["close"]) >= atr * 1.1):
            is_c1_bull = c1["close"] > c1["open"]
            is_sweep = c2["high"] > c1["high"]
            ob_top = c2["high"] if is_sweep else c1["high"]
            ob_bottom = c1["low"]
            if ob_top - ob_bottom < atr * 0.15:
                ob_top = ob_bottom + (atr * 0.25)
            ob_mid = (ob_top + ob_bottom) / 2.0
            
            if is_sweep:
                cat = "COND"
                title = "COND-OB"
                model = "Type 6: Sweep+BOS Leg OB"
                theme = "COND"
            elif is_c1_bull:
                cat = "STRONG"
                title = "STRONG-OB"
                model = "Type 2: Classic Opposite-Color OB"
                theme = "STRONG_BEAR"
            else:
                cat = "WEAK"
                title = "WEAK-OB (SWEEP REQ)"
                model = "Type 1: Momentum Same-Color OB"
                theme = "WEAK"
                
            mit_idx = None
            for k in range(i + 1, len(candles)):
                if candles[k]["high"] >= ob_bottom:
                    mit_idx = k
                    break
            obs.append({
                "side": "BEAR",
                "title": title,
                "model": model,
                "top": round(ob_top, 2),
                "bottom": round(ob_bottom, 2),
                "mid": round(ob_mid, 2),
                "mitigated": mit_idx is not None,
                "start_time": c1["time"]
            })

    print(f"Detected {len(obs)} OBs (showing last 6):")
    for o in obs[-6:]:
        status = "MITIGATED" if o["mitigated"] else "UNMITIGATED (ACTIVE)"
        print(f"  [{o['side']}] {o['title']} ({o['model']}) | Top: {o['top']} - Bot: {o['bottom']} (MT: {o['mid']}) | {status}")

test_symbol("PAXGUSDT", "1h")
test_symbol("BTCUSDT", "1h")
