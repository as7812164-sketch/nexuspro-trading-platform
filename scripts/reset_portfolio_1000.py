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

from config import DB_PATH, TOTAL_DECA_SECTIONS, STARTING_BALANCE_PER_SECTION, PAIR_MAPPING
from database.cloud_vault import push_vault_state

def reset_portfolio():
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # 1. Reset deca_sections to 10 sections of $100 each = $1,000.00
    now = time.time()
    c.execute("DELETE FROM deca_sections")
    for sec_id in range(1, TOTAL_DECA_SECTIONS + 1):
        coins = [sym for sym, sid in PAIR_MAPPING.items() if sid == sec_id]
        coins_str = ", ".join(coins)
        sec_name = f"Section {sec_id} ({coins_str})"
        c.execute("""
            INSERT INTO deca_sections (
                id, name, assigned_coins, initial_balance, current_balance,
                vault_balance, equity, total_pnl, pnl_pct, win_count, loss_count, win_rate, status, active_symbol, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0.0, ?, 0.0, 0.0, 0, 0, 0.0, 'IDLE', NULL, ?)
        """, (sec_id, sec_name, coins_str, STARTING_BALANCE_PER_SECTION, STARTING_BALANCE_PER_SECTION, STARTING_BALANCE_PER_SECTION, now))

    # 2. Clear positions
    c.execute("DELETE FROM positions")

    # 3. Clear trade history
    c.execute("DELETE FROM trade_history")

    # 4. Clear pending setups
    c.execute("DELETE FROM pending_setups")

    conn.commit()

    # Verify
    sections = c.execute("SELECT id, name, initial_balance, current_balance, equity FROM deca_sections").fetchall()
    tot_equity = sum(s[4] for s in sections)
    print(f"[OK] Successfully seeded {len(sections)} sections. Total Starting Portfolio: ${tot_equity:.2f} USDT")

    conn.close()

    # 5. Push clean reset snapshot to GitHub data-vault branch
    pushed = push_vault_state(force_reset=True)
    if pushed:
        print("[OK] Cloud Vault successfully reset to $1,000 portfolio on GitHub data-vault branch!")
    else:
        print("[NOTE] Local vault saved, GitHub push note: check network or credentials.")

if __name__ == "__main__":
    reset_portfolio()
