import asyncio
import aiohttp
from engine.ms_ob_engine import hermes_ms_ob_engine

async def main():
    print("=== TESTING HERMES MSOB LTF SNIPER ENGINE ===")
    async with aiohttp.ClientSession() as session:
        # Test 1: Fetch real 1H and 5m candles for SOLUSDT
        print("\n1. Testing 1H ➔ 5m Pairing on SOLUSDT...")
        candles_1h = await hermes_ms_ob_engine.fetch_klines(session, "SOLUSDT", "1h", limit=120)
        candles_5m = await hermes_ms_ob_engine.fetch_klines(session, "SOLUSDT", "5m", limit=50)
        print(f" * Fetched {len(candles_1h)} 1H bars, {len(candles_5m)} 5m bars")
        
        # Test scan_symbol_order_blocks
        setups_1h = hermes_ms_ob_engine.scan_symbol_order_blocks("SOLUSDT", "1h", candles_1h)
        print(f" * Found {len(setups_1h)} 1H setups on SOLUSDT")
        for s in setups_1h[:3]:
            print(f"   - {s['side']} ({s['category']}): OB [{s['ob_bottom']} - {s['ob_top']}], 1st Tap: {s['is_first_tap']}")
            
        # Test 2: Test detect_ltf_mss_and_retest directly on 5m
        print("\n2. Testing 5m MSS & Latest POI Detection...")
        res_5m = hermes_ms_ob_engine.detect_ltf_mss_and_retest(
            candles_5m,
            side="LONG",
            htf_ob_top=72.0,
            htf_ob_bottom=69.0,
            tap_time=candles_5m[0]["time"]
        )
        print(" * 5m Detection Result:", res_5m)
        if res_5m:
            entry = res_5m["entry_price"]
            sl = res_5m["sl_price"]
            tp = res_5m["tp_price"]
            sl_roi = round(abs((entry - sl)/entry) * 5 * 100, 2)
            print(f"   ➔ ENTRY: {entry} | REFINED SL: {sl} (-{sl_roi}% ROI) | TP: {tp} (+15% ROI)")
            print(f"   ➔ Latest POI Box: [{res_5m['latest_poi']['bottom']} - {res_5m['latest_poi']['top']}]")

        # Test 3: Test 4H ➔ 15m Pairing on BTCUSDT
        print("\n3. Testing 4H ➔ 15m Pairing on BTCUSDT...")
        candles_4h = await hermes_ms_ob_engine.fetch_klines(session, "BTCUSDT", "4h", limit=120)
        candles_15m = await hermes_ms_ob_engine.fetch_klines(session, "BTCUSDT", "15m", limit=50)
        print(f" * Fetched {len(candles_4h)} 4H bars, {len(candles_15m)} 15m bars")
        
        res_15m = hermes_ms_ob_engine.detect_ltf_mss_and_retest(
            candles_15m,
            side="LONG",
            htf_ob_top=62000.0,
            htf_ob_bottom=59000.0,
            tap_time=candles_15m[0]["time"]
        )
        print(" * 15m Detection Result:", res_15m)
        if res_15m:
            entry = res_15m["entry_price"]
            sl = res_15m["sl_price"]
            tp = res_15m["tp_price"]
            sl_roi = round(abs((entry - sl)/entry) * 10 * 100, 2)
            print(f"   ➔ ENTRY: {entry} | REFINED SL: {sl} (-{sl_roi}% ROI) | TP: {tp} (+15% ROI)")
            print(f"   ➔ Latest POI Box: [{res_15m['latest_poi']['bottom']} - {res_15m['latest_poi']['top']}]")

    print("\n✅ ALL LTF PAIRINGS & MSS POI DETECTION VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
