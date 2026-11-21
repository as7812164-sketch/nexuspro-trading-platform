import asyncio
import os, sys

# Set cwd to nexuspro_trading_platform
sys.path.insert(0, r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform")
os.chdir(r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform")

from engine.ms_ob_engine import hermes_ms_ob_engine

async def test_cycle():
    print("Testing 1 live scan cycle of hermes_ms_ob_engine...")
    # Restrict watchlist to top 5 coins for quick test
    original_wl = hermes_ms_ob_engine.watchlist
    hermes_ms_ob_engine.watchlist = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "NEARUSDT"]
    try:
        await hermes_ms_ob_engine.run_scan_cycle()
        print("Scan cycle completed! Total scanned setups:", len(hermes_ms_ob_engine.scanned_setups))
        print("Armed watchdogs count:", len(hermes_ms_ob_engine._armed_watchdogs))
        for s in hermes_ms_ob_engine.scanned_setups[:5]:
            print(f" * {s['symbol']} ({s['timeframe']}) {s['side']} | Status: {s['status']}")
    finally:
        hermes_ms_ob_engine.watchlist = original_wl

if __name__ == "__main__":
    asyncio.run(test_cycle())
