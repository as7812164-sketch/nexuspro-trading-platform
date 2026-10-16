import sqlite3
import time

def setup_and_seed_nexuspro():
    conn = sqlite3.connect('database/nexuspro.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Add extra columns to positions if missing
    existing_pos_cols = [d[1] for d in c.execute("PRAGMA table_info(positions)").fetchall()]
    for col, col_type in [
        ("mae_pct", "REAL DEFAULT 0.0"),
        ("mfe_pct", "REAL DEFAULT 0.0"),
        ("size_usdt", "REAL DEFAULT 0.0"),
    ]:
        if col not in existing_pos_cols:
            c.execute(f"ALTER TABLE positions ADD COLUMN {col} {col_type}")

    # 2. Add extra columns to trade_history if missing
    existing_hist_cols = [d[1] for d in c.execute("PRAGMA table_info(trade_history)").fetchall()]
    for col, col_type in [
        ("entry_time_str", "TEXT"),
        ("exit_time_str", "TEXT"),
        ("duration_str", "TEXT"),
        ("be_status_str", "TEXT"),
        ("mae_pct", "TEXT DEFAULT '0.00%'"),
        ("mfe_pct", "TEXT DEFAULT '0.00%'"),
        ("roi_pct", "REAL DEFAULT 0.0")
    ]:
        if col not in existing_hist_cols:
            c.execute(f"ALTER TABLE trade_history ADD COLUMN {col} {col_type}")

    # 3. Clear old test positions and history to avoid duplicates
    c.execute("DELETE FROM positions")
    c.execute("DELETE FROM trade_history")

    now = time.time()

    # 4. Insert Active Positions matching user screenshot
    positions_to_seed = [
        {
            "section_id": 6,
            "symbol": "RENDERUSDT",
            "side": "SELL",
            "entry_price": 1.9625,
            "mark_price": 1.9520,
            "position_size_usdt": 247.3,
            "size_usdt": 247.3,
            "margin_usdt": 49.45,
            "leverage": 5,
            "sl_price": 2.0210,
            "tp_price": 1.8440,
            "trailing_sl_price": 1.9625,
            "trailing_stage": 1,
            "unrealized_pnl": 1.32,
            "pnl_pct": 2.68,
            "mae_pct": 0.00,
            "mfe_pct": 6.75,
            "liquidation_price": 2.3150,
            "order_type": "LIMIT",
            "status": "OPEN",
            "open_time": now - 3600 * 2,
            "updated_at": now
        },
        {
            "section_id": 1,
            "symbol": "ETHUSDT",
            "side": "SELL",
            "entry_price": 2469.8250,
            "mark_price": 2460.0000,
            "position_size_usdt": 250.0,
            "size_usdt": 250.0,
            "margin_usdt": 50.00,
            "leverage": 5,
            "sl_price": 2544.0,
            "tp_price": 2321.0,
            "trailing_sl_price": 2469.8250,
            "trailing_stage": 1,
            "unrealized_pnl": 0.99,
            "pnl_pct": 1.99,
            "mae_pct": 0.00,
            "mfe_pct": 9.88,
            "liquidation_price": 2914.0,
            "order_type": "LIMIT",
            "status": "OPEN",
            "open_time": now - 3600 * 3,
            "updated_at": now
        }
    ]

    for p in positions_to_seed:
        c.execute("""
            INSERT INTO positions (
                section_id, symbol, side, entry_price, mark_price, position_size_usdt, size_usdt,
                margin_usdt, leverage, sl_price, tp_price, trailing_sl_price, trailing_stage,
                unrealized_pnl, pnl_pct, mae_pct, mfe_pct, liquidation_price, order_type, status, open_time, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["section_id"], p["symbol"], p["side"], p["entry_price"], p["mark_price"],
            p["position_size_usdt"], p["size_usdt"], p["margin_usdt"], p["leverage"],
            p["sl_price"], p["tp_price"], p["trailing_sl_price"], p["trailing_stage"],
            p["unrealized_pnl"], p["pnl_pct"], p["mae_pct"], p["mfe_pct"],
            p["liquidation_price"], p["order_type"], p["status"], p["open_time"], p["updated_at"]
        ))

    # 5. Insert Executed Trade History matching user screenshot
    history_to_seed = [
        {
            "section_id": 10,
            "symbol": "ATOMUSDT",
            "side": "BUY",
            "entry_price": 1.7180,
            "exit_price": 1.7695,
            "margin_usdt": 47.30,
            "position_size_usdt": 236.50,
            "leverage": 5,
            "realized_pnl": 7.10,
            "pnl_pct": 15.01,
            "roi_pct": 15.01,
            "exit_reason": "TP Hit",
            "open_time": now - 3600 * 5,
            "close_time": now - 3600 * 2,
            "duration_minutes": 221.0,
            "entry_time_str": "16 Oct, 09:18:10 IST",
            "exit_time_str": "16 Oct, 12:59:43 IST",
            "duration_str": "3h 41m",
            "be_status_str": "🛡️ BE Locked @ $1.7356",
            "mae_pct": "-0.65%",
            "mfe_pct": "+15.13%"
        },
        {
            "section_id": 6,
            "symbol": "FETUSDT",
            "side": "SELL",
            "entry_price": 0.2073,
            "exit_price": 0.2052,
            "margin_usdt": 39.80,
            "position_size_usdt": 199.00,
            "leverage": 5,
            "realized_pnl": 1.99,
            "pnl_pct": 5.00,
            "roi_pct": 5.00,
            "exit_reason": "TP Hit",
            "open_time": now - 3600 * 18,
            "close_time": now - 3600 * 2.5,
            "duration_minutes": 926.0,
            "entry_time_str": "15 Oct, 20:38:24 IST",
            "exit_time_str": "16 Oct, 12:04:31 IST",
            "duration_str": "15h 26m",
            "be_status_str": "🛡️ BE Locked @ $0.2073",
            "mae_pct": "-11.58%",
            "mfe_pct": "+16.67%"
        },
        {
            "section_id": 6,
            "symbol": "OPUSDT",
            "side": "SELL",
            "entry_price": 0.1409,
            "exit_price": 0.1367,
            "margin_usdt": 113.20,
            "position_size_usdt": 566.00,
            "leverage": 5,
            "realized_pnl": 16.98,
            "pnl_pct": 15.00,
            "roi_pct": 15.00,
            "exit_reason": "TP Hit",
            "open_time": now - 3600 * 17,
            "close_time": now - 3600 * 3.5,
            "duration_minutes": 818.0,
            "entry_time_str": "15 Oct, 21:37:53 IST",
            "exit_time_str": "16 Oct, 11:16:49 IST",
            "duration_str": "13h 38m",
            "be_status_str": "BE Armor Inactive",
            "mae_pct": "-3.19%",
            "mfe_pct": "+19.87%"
        },
        {
            "section_id": 2,
            "symbol": "CRVUSDT",
            "side": "SELL",
            "entry_price": 0.3640,
            "exit_price": 0.3531,
            "margin_usdt": 52.20,
            "position_size_usdt": 261.00,
            "leverage": 5,
            "realized_pnl": 7.83,
            "pnl_pct": 15.00,
            "roi_pct": 15.00,
            "exit_reason": "TP Hit",
            "open_time": now - 3600 * 16.5,
            "close_time": now - 3600 * 3.5,
            "duration_minutes": 801.0,
            "entry_time_str": "15 Oct, 21:54:47 IST",
            "exit_time_str": "16 Oct, 11:16:38 IST",
            "duration_str": "13h 21m",
            "be_status_str": "BE Armor Inactive",
            "mae_pct": "-0.27%",
            "mfe_pct": "+21.29%"
        },
        {
            "section_id": 8,
            "symbol": "TAOUSDT",
            "side": "SELL",
            "entry_price": 295.50,
            "exit_price": 285.50,
            "margin_usdt": 47.67,
            "position_size_usdt": 238.35,
            "leverage": 5,
            "realized_pnl": -7.15,
            "pnl_pct": -15.00,
            "roi_pct": -15.00,
            "exit_reason": "SL Hit",
            "open_time": now - 3600 * 15.5,
            "close_time": now - 3600 * 3.5,
            "duration_minutes": 736.0,
            "entry_time_str": "15 Oct, 22:59:57 IST",
            "exit_time_str": "16 Oct, 11:16:39 IST",
            "duration_str": "12h 16m",
            "be_status_str": "BE Armor Inactive",
            "mae_pct": "-15.00%",
            "mfe_pct": "+0.50%"
        }
    ]

    for h in history_to_seed:
        c.execute("""
            INSERT INTO trade_history (
                section_id, symbol, side, entry_price, exit_price, margin_usdt,
                position_size_usdt, leverage, realized_pnl, pnl_pct, roi_pct, exit_reason,
                open_time, close_time, duration_minutes, entry_time_str, exit_time_str,
                duration_str, be_status_str, mae_pct, mfe_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            h["section_id"], h["symbol"], h["side"], h["entry_price"], h["exit_price"],
            h["margin_usdt"], h["position_size_usdt"], h["leverage"], h["realized_pnl"],
            h["pnl_pct"], h["roi_pct"], h["exit_reason"], h["open_time"], h["close_time"],
            h["duration_minutes"], h["entry_time_str"], h["exit_time_str"], h["duration_str"],
            h["be_status_str"], h["mae_pct"], h["mfe_pct"]
        ))

    # Update section balances to match exact trade history:
    # Starting Capital: 10 * $50 = $500.00
    # Sec 2 (CRVUSDT win +$7.83): balance = $57.83, 1W 0L
    # Sec 6 (OPUSDT +$16.98, FETUSDT +$1.99): balance = $68.97, 2W 0L, in trade RENDERUSDT
    # Sec 8 (TAOUSDT loss -$7.15): balance = $42.85, 0W 1L
    # Sec 10 (ATOMUSDT win +$7.10): balance = $57.10, 1W 0L
    # Sec 1 (ETHUSDT in trade): balance = $50.00
    c.execute("UPDATE deca_sections SET status = 'IN_TRADE', active_symbol = 'RENDERUSDT', current_balance = 68.97, equity = 68.97, total_pnl = 18.97, win_count = 2, loss_count = 0, win_rate = 100.0 WHERE id = 6")
    c.execute("UPDATE deca_sections SET status = 'IN_TRADE', active_symbol = 'ETHUSDT', current_balance = 50.00, equity = 50.00, total_pnl = 0.0, win_count = 0, loss_count = 0 WHERE id = 1")
    c.execute("UPDATE deca_sections SET current_balance = 57.83, equity = 57.83, total_pnl = 7.83, win_count = 1, loss_count = 0, win_rate = 100.0 WHERE id = 2")
    c.execute("UPDATE deca_sections SET current_balance = 57.10, equity = 57.10, total_pnl = 7.10, win_count = 1, loss_count = 0, win_rate = 100.0 WHERE id = 10")
    c.execute("UPDATE deca_sections SET current_balance = 42.85, equity = 42.85, total_pnl = -7.15, win_count = 0, loss_count = 1, win_rate = 0.0 WHERE id = 8")

    conn.commit()
    conn.close()
    print("NexusPro database successfully seeded with BB 2.0 active positions and trade history!")

if __name__ == "__main__":
    setup_and_seed_nexuspro()
