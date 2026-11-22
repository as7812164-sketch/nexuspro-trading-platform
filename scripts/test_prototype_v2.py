import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform")))

# Let's write a prototype of the new detect_ltf_mss_and_retest
def detect_ltf_mss_and_retest_v2(candles, side, htf_ob_top, htf_ob_bottom, tap_time=0):
    n = len(candles)
    if n < 10:
        return None

    curr_c = candles[-1]
    curr_price = curr_c["close"]
    lookback = min(30, n - 2)
    start_idx = n - lookback

    if side.upper() in ("LONG", "BUY"):
        # 1. Identify valid swing highs (Lower Highs)
        swing_highs = []
        for i in range(start_idx, n - 2):
            if candles[i]["high"] >= candles[i - 1]["high"] and candles[i]["high"] >= candles[i + 1]["high"]:
                swing_highs.append((i, candles[i]["high"]))
        
        if not swing_highs:
            max_c = max(candles[start_idx:n - 2], key=lambda c: c["high"])
            swing_highs.append((candles.index(max_c), max_c["high"]))

        # Check most recent Lower High
        for sh_idx, sh_val in reversed(swing_highs):
            # 2. Check for MSS: Any candle after sh_idx breaks recent LH by wick OR body
            for k in range(sh_idx + 1, n):
                c_k = candles[k]
                is_break = c_k["high"] > sh_val  # Wick OR Body!

                if is_break:
                    # MSS Confirmed!
                    # 3. Identify 5M Last POI (base candle of the breakout move)
                    base_idx = k - 1
                    while base_idx > sh_idx and candles[base_idx]["close"] > candles[base_idx]["open"]:
                        base_idx -= 1
                    base_c = candles[base_idx]

                    poi_top = max(base_c["open"], base_c["close"], (base_c["high"] + base_c["open"]) / 2.0)
                    poi_bottom = min(base_c["open"], base_c["close"], base_c["low"])

                    # 4. STRICT LIVE RETEST ONLY (Current / Live Candle)
                    # Invalidation: If live price is completely below poi_bottom, POI failed!
                    if curr_price < poi_bottom * 0.997:
                        return None  # Invalidated / Sliced

                    # Live Retest Check: Current candle wick taps poi_top or is inside POI
                    is_live_retest = (curr_c["low"] <= poi_top and curr_price >= poi_bottom * 0.998)
                    # Also check immediate previous candle if it just wicked in
                    prev_c = candles[-2]
                    is_prev_retest = (prev_c["low"] <= poi_top and prev_c["low"] >= poi_bottom * 0.998 and curr_price >= poi_bottom)

                    retested = is_live_retest or is_prev_retest

                    entry_p = min(poi_top, curr_price) if retested else poi_top

                    return {
                        "status": "CONFIRMED_RETEST" if retested else "WAITING_RETEST",
                        "pathway": "HERMES_MSOB_LTF_MSS_SNIPER",
                        "mss_level": round(sh_val, 6),
                        "mss_time": c_k["time"],
                        "latest_poi": {
                            "top": round(poi_top, 6),
                            "bottom": round(poi_bottom, 6),
                            "time": base_c["time"]
                        },
                        "entry_price": round(entry_p, 6),
                        "retested": retested,
                        "poi_top": round(poi_top, 6),
                        "poi_bot": round(poi_bottom, 6),
                    }

    else: # SHORT
        swing_lows = []
        for i in range(start_idx, n - 2):
            if candles[i]["low"] <= candles[i - 1]["low"] and candles[i]["low"] <= candles[i + 1]["low"]:
                swing_lows.append((i, candles[i]["low"]))
        
        if not swing_lows:
            min_c = min(candles[start_idx:n - 2], key=lambda c: c["low"])
            swing_lows.append((candles.index(min_c), min_c["low"]))

        for sl_idx, sl_val in reversed(swing_lows):
            for k in range(sl_idx + 1, n):
                c_k = candles[k]
                is_break = c_k["low"] < sl_val  # Wick OR Body!

                if is_break:
                    base_idx = k - 1
                    while base_idx > sl_idx and candles[base_idx]["close"] < candles[base_idx]["open"]:
                        base_idx -= 1
                    base_c = candles[base_idx]

                    poi_bottom = min(base_c["open"], base_c["close"], (base_c["low"] + base_c["open"]) / 2.0)
                    poi_top = max(base_c["open"], base_c["close"], base_c["high"])

                    if curr_price > poi_top * 1.003:
                        return None  # Sliced / Invalidated

                    is_live_retest = (curr_c["high"] >= poi_bottom and curr_price <= poi_top * 1.002)
                    prev_c = candles[-2]
                    is_prev_retest = (prev_c["high"] >= poi_bottom and prev_c["high"] <= poi_top * 1.002 and curr_price <= poi_top)

                    retested = is_live_retest or is_prev_retest
                    entry_p = max(poi_bottom, curr_price) if retested else poi_bottom

                    return {
                        "status": "CONFIRMED_RETEST" if retested else "WAITING_RETEST",
                        "pathway": "HERMES_MSOB_LTF_MSS_SNIPER",
                        "mss_level": round(sl_val, 6),
                        "mss_time": c_k["time"],
                        "latest_poi": {
                            "top": round(poi_top, 6),
                            "bottom": round(poi_bottom, 6),
                            "time": base_c["time"]
                        },
                        "entry_price": round(entry_p, 6),
                        "retested": retested,
                        "poi_top": round(poi_top, 6),
                        "poi_bot": round(poi_bottom, 6),
                    }
    return None

print("Prototype v2 defined successfully.")
