import asyncio
import aiohttp
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_TELEGRAM_BOT_TOKEN, NEXUS_TELEGRAM_CHAT_ID
from engine.chart_image_generator import render_smc_chart_image
from engine.ms_ob_engine import format_price

async def test_send():
    async with aiohttp.ClientSession() as session:
        # Fetch live Binance candles for ETH
        url = "https://data-api.binance.vision/api/v3/klines?symbol=ETHUSDT&interval=1h&limit=100"
        async with session.get(url) as r:
            raw = await r.json()
            candles = [
                {
                    "time": int(k[0]) // 1000,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                }
                for k in raw
            ]

        sym = "ETHUSDT"
        tf = "1H"
        dir_label = "BUY/LONG"
        pos_id = 60
        entry_p = 1779.57
        tp_p = 1806.26
        sl_p = 1752.88
        sig_label = "1st Tap + 5m"
        icon = "🟢"

        caption = (
            f"<pre>{icon} {sym} ({tf}) • {dir_label} (#{pos_id})\n"
            f"─────────────────────────────────\n"
            f"ENTRY : ${format_price(entry_p)} ({sig_label})\n"
            f"TP 🎯 : ${format_price(tp_p)} (+15.0% ROI)\n"
            f"SL 🛑 : ${format_price(sl_p)} (-15.0% ROI)</pre>"
        )

        chart_zone = {
            "side": "LONG",
            "entry_price": entry_p,
            "tp_price": tp_p,
            "hard_sl_price": sl_p,
            "ob_top": 1779.57,
            "ob_bottom": 1765.0,
            "leverage": 10,
        }

        chart_bytes = render_smc_chart_image(sym, candles, chart_zone, timeframe=tf)

        url = f"https://api.telegram.org/bot{NEXUS_TELEGRAM_BOT_TOKEN}/sendPhoto"
        form = aiohttp.FormData()
        form.add_field("chat_id", str(NEXUS_TELEGRAM_CHAT_ID))
        form.add_field("photo", chart_bytes, filename="trade_chart.png", content_type="image/png")
        form.add_field("caption", caption)
        form.add_field("parse_mode", "HTML")

        async with session.post(url, data=form) as resp:
            data = await resp.json()
            print("Status:", resp.status)
            print("Response:", data)

if __name__ == "__main__":
    asyncio.run(test_send())
