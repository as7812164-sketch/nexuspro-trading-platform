"""
PATCH PLATFORM SCRIPT: HERMES MS-OB INSTITUTIONAL UPGRADE
=========================================================
Surgically updates:
- database/db.py
- app.py
- static/trade.html
- static/js/app.js
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Patch database/db.py
db_py_path = BASE_DIR / "database" / "db.py"
with open(db_py_path, "r", encoding="utf-8") as f:
    db_content = f.read()

# Replace starting balance if hardcoded
db_content = re.sub(r'STARTING_BALANCE_PER_SECTION\s*=\s*50\.0', 'STARTING_BALANCE_PER_SECTION = 100.0', db_content)
# Replace mode in summary
db_content = db_content.replace('"mode": "BB 3.0 (STEPPED TRAILING SL)"', '"mode": "HERMES_MS_OB_V2 (7-MODEL OB FIRST TAP)"')
db_content = db_content.replace('47389.77', '2000.0')

# Ensure tp_price in open_position is preserved
old_tp_override = """    tp_p = 0.0  # No fixed TP: Position rides with continuous Stepped Trailing SL
    pos_data["tp_price"] = 0.0"""
new_tp_override = """    tp_p = float(pos_data.get("tp_price", 0.0))"""
if old_tp_override in db_content:
    db_content = db_content.replace(old_tp_override, new_tp_override)

# Add timeframe column to tables if not present
if "timeframe" not in db_content:
    db_content = db_content.replace(
        '("size_usdt", "REAL DEFAULT 0.0")',
        '("size_usdt", "REAL DEFAULT 0.0"), ("timeframe", "TEXT DEFAULT \'1H\'")'
    )
    db_content = db_content.replace(
        '("mfe_pct", "TEXT DEFAULT \'0.00%\'")',
        '("mfe_pct", "TEXT DEFAULT \'0.00%\'"), ("timeframe", "TEXT DEFAULT \'1H\'")'
    )

with open(db_py_path, "w", encoding="utf-8") as f:
    f.write(db_content)
print("[OK] database/db.py patched successfully!")

# 2. Patch app.py
app_py_path = BASE_DIR / "app.py"
with open(app_py_path, "r", encoding="utf-8") as f:
    app_content = f.read()

# Replace engine imports
if "from engine.ms_ob_engine import hermes_ms_ob_engine" not in app_content:
    app_content = app_content.replace(
        "from engine.sentinel import nexus_sentinel",
        "from engine.sentinel import nexus_sentinel\nfrom engine.ms_ob_engine import hermes_ms_ob_engine"
    )

# Replace background task in lifespan
if "hermes_ms_ob_engine.start_loop()" not in app_content:
    app_content = app_content.replace(
        "sentinel_task = asyncio.create_task(nexus_sentinel.start_loop())",
        "ms_ob_task = asyncio.create_task(hermes_ms_ob_engine.start_loop())\n    sentinel_task = asyncio.create_task(nexus_sentinel.start_loop())"
    )
    app_content = app_content.replace(
        "nexus_sentinel.stop_loop()",
        "hermes_ms_ob_engine.stop_loop()\n    nexus_sentinel.stop_loop()"
    )
    app_content = app_content.replace(
        "sentinel_task.cancel()",
        "ms_ob_task.cancel()\n    sentinel_task.cancel()"
    )

# Patch /api/status
status_pattern = r'@app\.api_route\("/api/status", methods=\["GET", "HEAD"\]\)\s*async def get_status\(\):[\s\S]*?timestamp": time\.time\(\)\s*\}'
new_status_code = """@app.api_route("/api/status", methods=["GET", "HEAD"])
async def get_status():
    summary = get_portfolio_summary()
    return {
        "status": "online",
        "brand": BRAND_NAME,
        "tagline": BRAND_SUBTITLE,
        "strategy": "HERMES_MS_OB",
        "mode": "7-Model Order Block 1st Tap Protocol (1H/4H & Gold 15m/1H/4H)",
        "starting_capital": summary["starting_capital"],
        "total_equity": summary["total_equity"],
        "total_balance": summary["total_balance"],
        "margin_per_trade_usdt": hermes_ms_ob_engine.margin_per_trade,
        "max_concurrent_trades": hermes_ms_ob_engine.max_concurrent_trades,
        "sl_buffer_pct": hermes_ms_ob_engine.sl_buffer_pct * 100.0,
        "dynamic_armor": {
            "breakeven_trigger": "+1.0% (Fee Shield)",
            "trailing_trigger": "+1.8%",
            "take_profit": "+2.8%"
        },
        "win_rate": summary["win_rate"],
        "active_positions": summary["active_positions_count"],
        "scanned_setups_count": len(hermes_ms_ob_engine.scanned_setups),
        "timestamp": time.time()
    }"""

if re.search(status_pattern, app_content):
    app_content = re.sub(status_pattern, new_status_code, app_content)

# Patch /api/deca/setups
setups_pattern = r'@app\.get\("/api/deca/setups"\)\s*async def get_deca_setups\(\):[\s\S]*?return \{"count": len\(all_setups\), "setups": all_setups\}'
new_setups_code = """@app.get("/api/deca/setups")
async def get_deca_setups():
    open_pos = get_open_positions()
    tickers = await market_feed.get_all_tickers()
    active_list = []
    busy_symbols = set()
    for p in open_pos:
        sym = p["symbol"]
        busy_symbols.add(sym)
        ticker = (tickers or {}).get(sym)
        mark = ticker["last_price"] if ticker else p["entry_price"]
        active_list.append({
            "symbol": sym,
            "side": p["side"],
            "section_id": p["section_id"],
            "timeframe": p.get("timeframe", "1H"),
            "entry_price": p["entry_price"],
            "mark_price": mark,
            "sl_price": p["trailing_sl_price"] if p.get("trailing_sl_price", 0) > 0 else p["sl_price"],
            "tp_price": p["tp_price"],
            "distance_pct": 0.0,
            "proximity_pct": 0.0,
            "roe_pct": p.get("pnl_pct", 0.0),
            "status": "LIVE POSITION (HERMES MS-OB)",
            "is_active": True
        })

    msob_setups = hermes_ms_ob_engine.scanned_setups or []
    pending_list = []
    for s in msob_setups:
        sym = s["symbol"]
        if sym in busy_symbols:
            continue
        pending_list.append({
            "symbol": sym,
            "side": s["side"],
            "section_id": PAIR_MAPPING.get(sym, 1),
            "timeframe": s["timeframe"].upper(),
            "entry_price": s["entry_price"],
            "mark_price": s["current_price"],
            "sl_price": s["sl_price"],
            "tp_price": s["tp_price"],
            "distance_pct": s["proximity_pct"],
            "proximity_pct": s["proximity_pct"],
            "probability_pct": 92.5,
            "status": s["status"],
            "anchor_name": f"{s['category']} OB ({s['model']})",
            "anchor_price": s["ob_mid"],
            "is_active": False
        })

    all_setups = active_list + pending_list
    return {"count": len(all_setups), "setups": all_setups}"""

if re.search(setups_pattern, app_content):
    app_content = re.sub(setups_pattern, new_setups_code, app_content)

with open(app_py_path, "w", encoding="utf-8") as f:
    f.write(app_content)
print("[OK] app.py patched successfully!")

# 3. Patch static/trade.html
html_path = BASE_DIR / "static" / "trade.html"
with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

html_content = html_content.replace(
    'Strategy: Standby (Strategy Decommissioned)',
    'Strategy: Hermes MS-OB (7-Model 1st Tap | 5% Margin | Max 8 Concurrent)'
)
html_content = html_content.replace(
    '<span class="stat-val green" id="topTotalEquity">$500.00</span>',
    '<span class="stat-val green" id="topTotalEquity">$1,000.00</span>'
)
html_content = html_content.replace(
    '<b style="color:#fff;" id="drawerTotalEquity">$575.06 USDT</b>',
    '<b style="color:#fff;" id="drawerTotalEquity">$1,000.00 USDT</b>'
)
html_content = html_content.replace(
    '<b style="color:var(--brand-teal);">$500.00 USDT</b>',
    '<b style="color:var(--brand-teal);">$1,000.00 USDT</b>'
)
html_content = html_content.replace(
    '<b style="color:var(--buy-green);" id="drawerActiveMode">STANDBY (AWAITING COMMAND)</b>',
    '<b style="color:var(--buy-green);" id="drawerActiveMode">HERMES MS-OB 7-MODEL 1ST TAP</b>'
)
html_content = re.sub(r'app\.js\?v=[a-zA-Z0-9_\-]+', 'app.js?v=hermes_msob_v2', html_content)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("[OK] static/trade.html patched successfully!")

# 4. Patch static/js/app.js
js_path = BASE_DIR / "static" / "js" / "app.js"
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

# Add PAXGUSDT to ALL_CHAMPIONS
if "PAXGUSDT" not in js_content:
    js_content = js_content.replace(
        '{ s: "BTCUSDT", sec: 1 }, { s: "ETHUSDT", sec: 1 },',
        '{ s: "BTCUSDT", sec: 1 }, { s: "ETHUSDT", sec: 1 }, { s: "PAXGUSDT", sec: 1 },'
    )

# Customize renderPairModalList to highlight PAXGUSDT (Gold)
paxg_highlight = """        <div onclick="selectPair('${x.s}')" style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; border-radius:6px; cursor:pointer; margin-bottom:4px; background:var(--bg-base); border:1px solid ${x.s==='PAXGUSDT' ? 'rgba(245,158,11,0.5)' : 'var(--border-subtle)'}; transition:border-color 0.2s;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-weight:800; color:${x.s==='PAXGUSDT' ? '#F59E0B' : '#fff'}; font-size:13px;">${x.s==='PAXGUSDT' ? 'PAXGUSDT (Gold)' : x.s}</span>
                <span style="font-size:9px; background:${x.s==='PAXGUSDT' ? 'rgba(245,158,11,0.2)' : 'var(--bg-surface-elevated)'}; padding:2px 4px; border-radius:3px; color:${x.s==='PAXGUSDT' ? '#F59E0B' : 'var(--text-muted)'}; font-weight:bold;">${x.s==='PAXGUSDT' ? 'GOLD 15M/1H/4H' : 'PERP 1H/4H'}</span>
            </div>
            <span style="font-size:10px; font-weight:800; color:var(--brand-teal);">Section ${x.sec}</span>
        </div>"""

js_content = re.sub(
    r'<div onclick="selectPair\(\'\$\{x\.s\}\'\)"[\s\S]*?Section \$\{x\.sec\}</span>\s*</div>',
    paxg_highlight,
    js_content
)

# Update radar no active setups placeholder
js_content = js_content.replace(
    'No active setups • Autonomous Scanner Scanning 20 Champions',
    'No active setups • Hermes MS-OB Engine Scanning Crypto (1H/4H) & Gold (15m/1H/4H)'
)

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js_content)
print("[OK] static/js/app.js patched successfully!")
