"""
NEXUSPRO DATABASE ENGINE (SQLITE)
=================================
Manages:
- 10 Deca Compounding Sections ($50 each = $500 initial capital)
- Live Paper Positions & Orders
- Completed Trade Audit Logs
- System Performance Metrics
"""

import sqlite3
import json
import time
from typing import Dict, List, Any, Optional
from config import (
    DB_PATH,
    TOTAL_DECA_SECTIONS,
    STARTING_BALANCE_PER_SECTION,
    PAIR_MAPPING
)

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds 10 Deca Compounding sections."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    c = conn.cursor()

    # 1. Deca Compounding Sections (1 to 10)
    c.execute("""
        CREATE TABLE IF NOT EXISTS deca_sections (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            assigned_coins TEXT NOT NULL,
            initial_balance REAL NOT NULL,
            current_balance REAL NOT NULL,
            vault_balance REAL DEFAULT 0.0,
            equity REAL NOT NULL,
            total_pnl REAL DEFAULT 0.0,
            pnl_pct REAL DEFAULT 0.0,
            win_count INTEGER DEFAULT 0,
            loss_count INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            status TEXT DEFAULT 'IDLE',
            active_symbol TEXT,
            updated_at REAL
        )
    """)

    # 2. Live Positions
    c.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            entry_price REAL NOT NULL,
            mark_price REAL NOT NULL,
            position_size_usdt REAL NOT NULL,
            margin_usdt REAL NOT NULL,
            leverage INTEGER DEFAULT 5,
            sl_price REAL NOT NULL,
            tp_price REAL NOT NULL,
            trailing_sl_price REAL DEFAULT 0.0,
            trailing_stage INTEGER DEFAULT 0,
            unrealized_pnl REAL DEFAULT 0.0,
            pnl_pct REAL DEFAULT 0.0,
            liquidation_price REAL,
            order_type TEXT DEFAULT 'LIMIT',
            status TEXT DEFAULT 'OPEN',
            open_time REAL NOT NULL,
            updated_at REAL
        )
    """)

    # 3. Trade History
    c.execute("""
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            margin_usdt REAL NOT NULL,
            position_size_usdt REAL NOT NULL,
            leverage INTEGER DEFAULT 5,
            realized_pnl REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            exit_reason TEXT NOT NULL,
            open_time REAL NOT NULL,
            close_time REAL NOT NULL,
            duration_minutes REAL
        )
    """)

    # 4. Settings
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Safe column migration for positions and trade_history (zero data loss)
    pos_cols = [d[1] for d in c.execute("PRAGMA table_info(positions)").fetchall()]
    for col, ctype in [("mae_pct", "REAL DEFAULT 0.0"), ("mfe_pct", "REAL DEFAULT 0.0"), ("size_usdt", "REAL DEFAULT 0.0")]:
        if col not in pos_cols:
            c.execute(f"ALTER TABLE positions ADD COLUMN {col} {ctype}")

    hist_cols = [d[1] for d in c.execute("PRAGMA table_info(trade_history)").fetchall()]
    for col, ctype in [
        ("roi_pct", "REAL DEFAULT 0.0"),
        ("entry_time_str", "TEXT"),
        ("exit_time_str", "TEXT"),
        ("duration_str", "TEXT"),
        ("be_status_str", "TEXT"),
        ("mae_pct", "TEXT DEFAULT '0.00%'"),
        ("mfe_pct", "TEXT DEFAULT '0.00%'")
    ]:
        if col not in hist_cols:
            c.execute(f"ALTER TABLE trade_history ADD COLUMN {col} {ctype}")

    conn.commit()

    # Seed 10 Deca sections if not already seeded
    c.execute("SELECT COUNT(*) FROM deca_sections")
    count = c.fetchone()[0]
    if count == 0:
        now = time.time()
        for sec_id in range(1, TOTAL_DECA_SECTIONS + 1):
            coins = [sym for sym, sid in PAIR_MAPPING.items() if sid == sec_id]
            coins_str = ", ".join(coins)
            sec_name = f"Section {sec_id} ({coins_str})"
            c.execute("""
                INSERT INTO deca_sections (
                    id, name, assigned_coins, initial_balance, current_balance,
                    equity, total_pnl, pnl_pct, win_count, loss_count, win_rate, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 0, 0, 0.0, 'IDLE', ?)
            """, (sec_id, sec_name, coins_str, STARTING_BALANCE_PER_SECTION, STARTING_BALANCE_PER_SECTION, STARTING_BALANCE_PER_SECTION, now))
        conn.commit()

    conn.close()

# ----------------- SECTION OPERATIONS -----------------

def get_all_sections() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM deca_sections ORDER BY id ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_section(section_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM deca_sections WHERE id = ?", (section_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_section_balance(section_id: int, new_balance: float, pnl: float, is_win: bool):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT initial_balance, win_count, loss_count FROM deca_sections WHERE id = ?", (section_id,))
    row = c.fetchone()
    if row:
        init_bal = row["initial_balance"]
        wins = row["win_count"] + (1 if is_win else 0)
        losses = row["loss_count"] + (0 if is_win else 1)
        tot_trades = wins + losses
        win_rate = round((wins / tot_trades) * 100.0, 1) if tot_trades > 0 else 0.0
        tot_pnl = round(new_balance - init_bal, 2)
        pnl_pct = round((tot_pnl / init_bal) * 100.0, 2) if init_bal > 0 else 0.0

        c.execute("""
            UPDATE deca_sections SET
                current_balance = ?,
                equity = ?,
                total_pnl = ?,
                pnl_pct = ?,
                win_count = ?,
                loss_count = ?,
                win_rate = ?,
                status = 'IDLE',
                active_symbol = NULL,
                updated_at = ?
            WHERE id = ?
        """, (round(new_balance, 2), round(new_balance, 2), tot_pnl, pnl_pct, wins, losses, win_rate, time.time(), section_id))
        conn.commit()
    conn.close()

def set_section_status(section_id: int, status: str, symbol: Optional[str] = None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE deca_sections SET status = ?, active_symbol = ?, updated_at = ? WHERE id = ?
    """, (status, symbol, time.time(), section_id))
    conn.commit()
    conn.close()

# ----------------- POSITIONS OPERATIONS -----------------

def get_open_positions() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM positions WHERE status = 'OPEN' ORDER BY open_time DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def open_position(pos_data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    c = conn.cursor()
    now = time.time()
    c.execute("""
        INSERT INTO positions (
            section_id, symbol, side, entry_price, mark_price, position_size_usdt,
            margin_usdt, leverage, sl_price, tp_price, trailing_sl_price, trailing_stage,
            unrealized_pnl, pnl_pct, liquidation_price, order_type, status, open_time, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
    """, (
        pos_data["section_id"],
        pos_data["symbol"],
        pos_data["side"],
        pos_data["entry_price"],
        pos_data.get("mark_price", pos_data["entry_price"]),
        pos_data["position_size_usdt"],
        pos_data["margin_usdt"],
        pos_data.get("leverage", 5),
        pos_data["sl_price"],
        pos_data["tp_price"],
        pos_data.get("trailing_sl_price", 0.0),
        pos_data.get("trailing_stage", 0),
        0.0,
        0.0,
        pos_data.get("liquidation_price", 0.0),
        pos_data.get("order_type", "LIMIT"),
        now,
        now
    ))
    pos_id = c.lastrowid
    conn.commit()
    conn.close()
    set_section_status(pos_data["section_id"], "IN_TRADE", pos_data["symbol"])
    return pos_id

def update_position_mark_price(pos_id: int, mark_price: float, u_pnl: float, pnl_pct: float, trailing_sl: float = 0.0, stage: int = 0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE positions SET
            mark_price = ?,
            unrealized_pnl = ?,
            pnl_pct = ?,
            trailing_sl_price = CASE WHEN ? > 0 THEN ? ELSE trailing_sl_price END,
            trailing_stage = CASE WHEN ? > 0 THEN ? ELSE trailing_stage END,
            updated_at = ?
        WHERE id = ?
    """, (mark_price, u_pnl, pnl_pct, trailing_sl, trailing_sl, stage, stage, time.time(), pos_id))
    conn.commit()
    conn.close()

def close_position_in_db(pos_id: int, exit_price: float, realized_pnl: float, exit_reason: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM positions WHERE id = ?", (pos_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return

    pos = dict(row)
    now = time.time()
    dur_min = round((now - pos["open_time"]) / 60.0, 1)
    pnl_pct = round((realized_pnl / pos["margin_usdt"]) * 100.0, 2) if pos["margin_usdt"] > 0 else 0.0

    # Mark position closed
    c.execute("UPDATE positions SET status = 'CLOSED', mark_price = ?, updated_at = ? WHERE id = ?", (exit_price, now, pos_id))

    # Insert into trade_history
    c.execute("""
        INSERT INTO trade_history (
            section_id, symbol, side, entry_price, exit_price, margin_usdt,
            position_size_usdt, leverage, realized_pnl, pnl_pct, exit_reason,
            open_time, close_time, duration_minutes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pos["section_id"], pos["symbol"], pos["side"], pos["entry_price"],
        exit_price, pos["margin_usdt"], pos["position_size_usdt"], pos["leverage"],
        round(realized_pnl, 2), pnl_pct, exit_reason, pos["open_time"], now, dur_min
    ))
    conn.commit()
    conn.close()

    # Update section balance
    sec = get_section(pos["section_id"])
    if sec:
        new_bal = max(1.0, sec["current_balance"] + realized_pnl)
        is_win = realized_pnl > 0
        update_section_balance(pos["section_id"], new_bal, realized_pnl, is_win)

# ----------------- TRADE HISTORY & SUMMARY -----------------

def get_trade_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM trade_history ORDER BY close_time DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_portfolio_summary() -> Dict[str, Any]:
    sections = get_all_sections()
    open_positions = get_open_positions()

    tot_initial = sum(s["initial_balance"] for s in sections)
    tot_balance = sum(s["current_balance"] for s in sections)
    unrealized = sum(p["unrealized_pnl"] for p in open_positions)
    tot_equity = tot_balance + unrealized
    tot_pnl = tot_equity - tot_initial
    pnl_pct = round((tot_pnl / tot_initial) * 100.0, 2) if tot_initial > 0 else 0.0

    tot_wins = sum(s["win_count"] for s in sections)
    tot_losses = sum(s["loss_count"] for s in sections)
    tot_trades = tot_wins + tot_losses
    win_rate = round((tot_wins / tot_trades) * 100.0, 1) if tot_trades > 0 else 0.0

    return {
        "mode": "BB 3.0 (STEPPED TRAILING SL)",
        "starting_capital": tot_initial,
        "total_balance": round(tot_balance, 2),
        "total_equity": round(tot_equity, 2),
        "unrealized_pnl": round(unrealized, 2),
        "total_pnl": round(tot_pnl, 2),
        "pnl_pct": pnl_pct,
        "total_trades": tot_trades,
        "total_wins": tot_wins,
        "total_losses": tot_losses,
        "win_rate": win_rate,
        "active_positions_count": len(open_positions),
        "sections_count": len(sections),
        "target_capital": 47389.77,
        "progress_pct": round((tot_equity / 47389.77) * 100.0, 2)
    }

# ----------------- REAL-TIME SYNC BRIDGE (BB 3.0 SNIPER & TELEGRAM) -----------------

def sync_external_trade_open(trade_data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    c = conn.cursor()
    now = time.time()
    sym = trade_data["symbol"]
    # Check if symbol already has OPEN position
    c.execute("SELECT id FROM positions WHERE symbol = ? AND status = 'OPEN'", (sym,))
    existing = c.fetchone()
    if existing:
        conn.close()
        return existing["id"]

    sec_id = int(trade_data.get("section_id", 1))
    side = trade_data["side"]
    entry = float(trade_data.get("entry_price", trade_data.get("mt_entry", 0.0)))
    sl = float(trade_data.get("sl_price", trade_data.get("sl", 0.0)))
    tp = float(trade_data.get("tp_price", trade_data.get("target_1r", 0.0)))
    margin = float(trade_data.get("margin_usdt", 50.0))
    pos_size = float(trade_data.get("position_size_usdt", margin * 5))
    lev = int(trade_data.get("leverage", 5))

    c.execute("""
        INSERT INTO positions (
            section_id, symbol, side, entry_price, mark_price, position_size_usdt,
            margin_usdt, leverage, sl_price, tp_price, trailing_sl_price, trailing_stage,
            unrealized_pnl, pnl_pct, liquidation_price, order_type, status, open_time, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 'LIMIT', 'OPEN', ?, ?)
    """, (
        sec_id, sym, side, entry, entry, pos_size, margin, lev, sl, tp, sl, 0, now, now
    ))
    pos_id = c.lastrowid
    conn.commit()
    conn.close()
    set_section_status(sec_id, "IN_TRADE", sym)
    return pos_id

def sync_external_trailing_update(sym: str, new_sl: float, stage: int, highest_r: float = 0.0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE positions SET
            trailing_sl_price = ?,
            trailing_stage = ?,
            updated_at = ?
        WHERE symbol = ? AND status = 'OPEN'
    """, (new_sl, stage, time.time(), sym))
    conn.commit()
    conn.close()

def sync_external_trade_close(trade_data: Dict[str, Any]):
    conn = get_db_connection()
    c = conn.cursor()
    now = time.time()
    sym = trade_data["symbol"]
    sec_id = int(trade_data.get("section_id", 1))
    side = trade_data.get("side", "LONG")
    entry = float(trade_data.get("entry_price", trade_data.get("mt_entry", 0.0)))
    exit_p = float(trade_data.get("exit_price", entry))
    margin = float(trade_data.get("margin_usdt", 50.0))
    pos_size = float(trade_data.get("position_size_usdt", margin * 5))
    lev = int(trade_data.get("leverage", 5))
    pnl = float(trade_data.get("dollar_pnl", trade_data.get("realized_pnl", 0.0)))
    pnl_pct = float(trade_data.get("pnl_pct", round((pnl / margin) * 100.0, 2) if margin > 0 else 0.0))
    reason = trade_data.get("outcome", trade_data.get("exit_reason", "TP Hit"))
    
    # Parse open/close timestamps if ISO string or int ms
    open_val = trade_data.get("open_time") or trade_data.get("filled_at") or trade_data.get("entry_time") or (now - 300)
    close_val = trade_data.get("close_time") or trade_data.get("closed_at") or trade_data.get("exit_time") or now
    
    open_t = open_val if isinstance(open_val, (int, float)) else now - 300
    close_t = close_val if isinstance(close_val, (int, float)) else now
    if open_t > 1e11: open_t /= 1000.0
    if close_t > 1e11: close_t /= 1000.0
    
    dur_min = round((close_t - open_t) / 60.0, 1)

    # 1. Close any open position in positions table
    c.execute("UPDATE positions SET status = 'CLOSED', mark_price = ?, updated_at = ? WHERE symbol = ? AND status = 'OPEN'", (exit_p, close_t, sym))

    # 2. Check if already recorded in trade_history to prevent duplicates
    c.execute("SELECT id FROM trade_history WHERE symbol = ? AND ABS(close_time - ?) < 60", (sym, close_t))
    existing = c.fetchone()
    if not existing:
        c.execute("""
            INSERT INTO trade_history (
                section_id, symbol, side, entry_price, exit_price, margin_usdt,
                position_size_usdt, leverage, realized_pnl, pnl_pct, exit_reason,
                open_time, close_time, duration_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sec_id, sym, side, entry, exit_p, margin, pos_size, lev, round(pnl, 2), pnl_pct, reason, open_t, close_t, dur_min
        ))

    conn.commit()

    # 3. Update section balance
    sec = get_section(sec_id)
    if sec:
        new_balance = float(trade_data.get("section_new_balance", sec["current_balance"] + pnl))
        is_win = pnl > 0
        update_section_balance(sec_id, new_balance, pnl, is_win)

    conn.close()

# Run initialization immediately on import
init_db()
