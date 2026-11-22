import asyncio
import aiohttp
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform")))
from engine.ms_ob_engine import HermesMSOBEngine

async def inspect_avax():
    engine = HermesMSOBEngine()
    async with aiohttp.ClientSession() as s:
        candles_5m = await engine.fetch_klines(s, "AVAXUSDT", "5m", limit=300)
        # Find candle closest to 1795301537 (04:22:17 IST)
        target_ts = 1795301537
        print("AVAX 5m candles around 04:22 IST:")
        for c in candles_5m:
            dt = datetime.fromtimestamp(c["time"], timezone(timedelta(hours=5, minutes=30)))
            if abs(c["time"] - target_ts) < 3600:
                print(f"  {dt.strftime('%H:%M:%S')}: Open={c['open']}, High={c['high']}, Low={c['low']}, Close={c['close']}")

asyncio.run(inspect_avax())
