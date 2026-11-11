"""
HERMES MS-OB RESET PORTFOLIO SCRIPT
===================================
Resets database to $1,000.00 USDT starting portfolio across 10 sections ($100 each).
Margin per trade: $50 USDT (5% of total portfolio).
Positions: Cleared.
Trade History: Cleared for fresh start.
Cloud Vault: Synchronized with version 2.0-hermes-msob.
"""

import sys
import os
import time
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DB_PATH
from database.db import init_db, reset_fresh_portfolio_db
from database.cloud_vault import push_vault_state

def reset_portfolio():
    print(f"Resetting NexusPro database cleanly at: {DB_PATH}")
    init_db()
    summary = reset_fresh_portfolio_db()
    print(f"[OK] Reset complete! Sections: {summary['sections_count']} | Total Balance: ${summary['total_balance']:.2f} | Trades: {summary['total_trades']} | Open: {summary['active_positions_count']}")

    # Push clean reset snapshot (version 3.0-hermes-msob-clean) to GitHub data-vault branch
    pushed = push_vault_state(force_reset=True)
    if pushed:
        print("[OK] Cloud Vault successfully reset to $1,000.00 portfolio (0 trades) on GitHub data-vault branch!")
    else:
        print("[NOTE] Local vault saved, GitHub push note: check network or credentials.")

if __name__ == "__main__":
    reset_portfolio()
