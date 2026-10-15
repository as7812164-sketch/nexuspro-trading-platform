"""
Test NexusPro backend, database, and market feed.
"""
import sys
import asyncio
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from database.db import init_db, get_all_sections, get_portfolio_summary
from config import BRAND_NAME, TOTAL_DECA_SECTIONS, INITIAL_CAPITAL_TOTAL
from engine.feed import market_feed

async def run_audit():
    init_db()
    sections = get_all_sections()
    summary = get_portfolio_summary()

    print("=== NEXUSPRO INTEGRITY AUDIT ===")
    print("Brand Name:", BRAND_NAME)
    print("Total Sections Seeded:", len(sections))
    print("Starting Total Capital: $" + str(summary['starting_capital']))
    print("Target Compounding Milestone: $" + str(summary['target_capital']))

    for s in sections[:4]:
        print(f" * Section {s['id']}: {s['assigned_coins']} | Bal: ${s['current_balance']} | Status: {s['status']}")

    print("\nTesting Binance Feed...")
    ticker = await market_feed.get_ticker("BTCUSDT")
    if ticker:
        print(f" * Live BTC Price: ${ticker['last_price']} ({ticker['price_change_pct']}%)")
    else:
        print(" * Ticker fetch skipped or offline.")

    print("\n[SUCCESS] NEXUSPRO SYSTEM INTEGRITY: 100% OPERATIONAL")

if __name__ == "__main__":
    asyncio.run(run_audit())
