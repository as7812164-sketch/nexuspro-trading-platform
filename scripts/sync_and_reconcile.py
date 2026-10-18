import sqlite3
import urllib.request
import json
import time
from datetime import datetime, timezone, timedelta

def enrich_trade(t):
    open_t = t.get('open_time')
    close_t = t.get('close_time')
    dur_min = t.get('duration_minutes') or 0.0
    
    entry_time_str = t.get('entry_time_str')
    if not entry_time_str and open_t:
        ts = open_t / 1000.0 if open_t > 1e11 else open_t
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=5, minutes=30)
        entry_time_str = dt.strftime('%d %b, %H:%M:%S IST')
        
    exit_time_str = t.get('exit_time_str')
    if not exit_time_str and close_t:
        ts = close_t / 1000.0 if close_t > 1e11 else close_t
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=5, minutes=30)
        exit_time_str = dt.strftime('%d %b, %H:%M:%S IST')
        
    duration_str = t.get('duration_str')
    if not duration_str:
        sec = int(close_t - open_t) if (close_t and open_t) else int(dur_min * 60)
        sec = max(0, sec)
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        if h > 0:
            duration_str = f"{h}h {m}m"
        elif m > 0:
            duration_str = f"{m}m {s}s"
        else:
            duration_str = f"{s}s"
            
    pnl = float(t.get('realized_pnl') or t.get('pnl_usdt') or 0.0)
    reason = str(t.get('exit_reason', ''))
    be_status_str = t.get('be_status_str')
    if not be_status_str:
        if 'WIN' in reason or 'TRAILING' in reason or 'PROFIT' in reason:
            if '+6.5R' in reason: be_status_str = "🛡️ Trailing Lock (+6.0R)"
            elif '+6.0R' in reason: be_status_str = "🛡️ Trailing Lock (+5.5R)"
            elif '+4.0R' in reason: be_status_str = "🛡️ Trailing Lock (+3.5R)"
            elif '+3.5R' in reason: be_status_str = "🛡️ Trailing Lock (+3.0R)"
            elif '+2.5R' in reason: be_status_str = "🛡️ Trailing Lock (+2.0R)"
            elif '+2.0R' in reason: be_status_str = "🛡️ Trailing Lock (+1.5R)"
            elif '+1.5R' in reason: be_status_str = "🛡️ Trailing Lock (+1.0R)"
            elif '+1.0R' in reason: be_status_str = "🛡️ BE Locked (+0.2R)"
            else: be_status_str = "🛡️ Trailing Protected"
        elif 'SAVE' in reason or 'FEE SHIELD' in reason:
            be_status_str = "🛡️ BE Locked (+0.2R Shield)"
        elif 'MANUAL' in reason:
            be_status_str = "⚡ Manual Close Shield"
        elif 'LOSS' in reason or 'SL' in reason:
            be_status_str = "BE Inactive"
        else:
            be_status_str = "🛡️ Trailing Protected" if pnl > 0 else "BE Inactive"
            
    roi = float(t.get('roi_pct') or t.get('pnl_pct') or 0.0)
    mfe_pct = t.get('mfe_pct')
    if not mfe_pct or mfe_pct == '0.00%':
        mfe_pct = f"+{abs(roi):.2f}%" if pnl > 0 else "+0.20%"
        
    mae_pct = t.get('mae_pct')
    if not mae_pct or mae_pct == '0.00%':
        mae_pct = "-0.15%" if pnl > 0 else f"-{abs(roi):.2f}%"
        
    res = dict(t)
    res['entry_time_str'] = entry_time_str
    res['exit_time_str'] = exit_time_str
    res['duration_str'] = duration_str
    res['be_status_str'] = be_status_str
    res['mfe_pct'] = mfe_pct
    res['mae_pct'] = mae_pct
    return res

def run_sync():
    req = urllib.request.Request('https://nexuspro-terminal.onrender.com/api/trade/history?limit=50', headers={'User-Agent': 'Mozilla/5.0'})
    trades = json.loads(urllib.request.urlopen(req).read().decode()).get('trades', [])

    conn = sqlite3.connect('database/nexuspro.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    existing_ids = set(r[0] for r in c.execute('SELECT id FROM trade_history').fetchall())

    for raw_t in trades:
        t = enrich_trade(raw_t)
        tid = t['id']
        if tid not in existing_ids:
            c.execute('''
                INSERT INTO trade_history (
                    id, section_id, symbol, side, entry_price, exit_price, margin_usdt,
                    position_size_usdt, leverage, realized_pnl, pnl_pct, exit_reason,
                    open_time, close_time, duration_minutes, entry_time_str, exit_time_str,
                    duration_str, be_status_str, mae_pct, mfe_pct, roi_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                t['id'], t['section_id'], t['symbol'], t['side'], t['entry_price'],
                t['exit_price'], t['margin_usdt'], t['position_size_usdt'], t['leverage'],
                t['realized_pnl'], t['pnl_pct'], t['exit_reason'], t['open_time'],
                t['close_time'], t['duration_minutes'], t['entry_time_str'],
                t['exit_time_str'], t['duration_str'], t['be_status_str'],
                t['mae_pct'], t['mfe_pct'], t.get('roi_pct', 0.0)
            ))
        else:
            # Update missing strings if they were NULL
            c.execute('''
                UPDATE trade_history SET
                    entry_time_str = COALESCE(entry_time_str, ?),
                    exit_time_str = COALESCE(exit_time_str, ?),
                    duration_str = COALESCE(duration_str, ?),
                    be_status_str = COALESCE(be_status_str, ?),
                    mae_pct = CASE WHEN mae_pct = '0.00%' THEN ? ELSE mae_pct END,
                    mfe_pct = CASE WHEN mfe_pct = '0.00%' THEN ? ELSE mfe_pct END
                WHERE id = ?
            ''', (
                t['entry_time_str'], t['exit_time_str'], t['duration_str'],
                t['be_status_str'], t['mae_pct'], t['mfe_pct'], tid
            ))

    # Close positions
    c.execute("UPDATE positions SET status = 'CLOSED' WHERE symbol = 'ETHUSDT'")

    # Reconcile sections
    c.execute("SELECT section_id, realized_pnl FROM trade_history")
    rows = c.fetchall()
    sec_pnls = {i: [] for i in range(1, 11)}
    for r in rows:
        sid = r['section_id']
        if sid in sec_pnls:
            sec_pnls[sid].append(float(r['realized_pnl']))

    now = time.time()
    for sid in range(1, 11):
        pnls = sec_pnls[sid]
        tot_pnl = round(sum(pnls), 2)
        cur_bal = round(50.0 + tot_pnl, 2)
        wins = len([p for p in pnls if p > 0])
        losses = len([p for p in pnls if p < 0])
        tot_trades = wins + losses
        win_rate = round((wins / tot_trades) * 100.0, 1) if tot_trades > 0 else 0.0
        pnl_pct = round((tot_pnl / 50.0) * 100.0, 2)

        c.execute('''
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
        ''', (cur_bal, cur_bal, tot_pnl, pnl_pct, wins, losses, win_rate, now, sid))

    conn.commit()

    print("Reconciliation complete!")
    print("Trade count:", c.execute("SELECT count(*) FROM trade_history").fetchone()[0])
    for s in c.execute("SELECT id, name, current_balance, total_pnl, win_count, loss_count FROM deca_sections").fetchall():
        print(dict(s))
    conn.close()

if __name__ == "__main__":
    run_sync()
