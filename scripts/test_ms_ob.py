import sys
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import asyncio
import aiohttp
from engine.ms_ob_engine import hermes_ms_ob_engine
from database.db import get_portfolio_summary, get_open_positions

async def main():
    print("--- Testing Hermes MS-OB Engine & Portfolio ---")
    summary = get_portfolio_summary()
    print("Portfolio Summary:", summary)
    assert summary["starting_capital"] == 1000.0
    assert summary["total_equity"] == 1000.0
    assert hermes_ms_ob_engine.margin_per_trade == 50.0
    assert hermes_ms_ob_engine.max_concurrent_trades == 8
    assert hermes_ms_ob_engine.sl_buffer_pct == 0.005

    print("\n--- Running 1 Scan Cycle across Crypto (1H/4H) & Gold (15m/1H/4H) ---")
    await hermes_ms_ob_engine.run_scan_cycle()
    print(f"Scanned Setups Found: {len(hermes_ms_ob_engine.scanned_setups)}")
    for s in hermes_ms_ob_engine.scanned_setups[:5]:
        print(f"  [{s['symbol']} {s['timeframe']}] {s['side']} | {s['category']} ({s['model']}) | Entry: {s['entry_price']} | SL: {s['sl_price']} | Status: {s['status']}")

    print("\n[OK] HERMES MS-OB ENGINE VERIFICATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
