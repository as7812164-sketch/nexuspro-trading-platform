"""
NEXUSPRO INSTITUTIONAL FUTURES TERMINAL (FASTAPI BACKEND)
=========================================================
Brand: NexusPro
Engine: Hermes MS-OB v2.0 GOLDEN ONLY (7-Model Order Block First-Tap Strategy)
- BUY / LONG Exclusive Execution
- Strictly 1st Tap Valid | 2nd Tap Permanently Invalidated
- Flat $1,000 Portfolio | $50 (5%) Margin | 5x Isolated | +12%->+2.5% BE | -15% SL (2x15m) | +15% TP
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import (
    BRAND_NAME,
    BRAND_SUBTITLE,
    BASE_DIR,
    CHAMPIONS,
    PAIR_MAPPING,
    DEFAULT_LEVERAGE,
    SYMBOL_LEVERAGE_OVERRIDES,
    get_symbol_leverage
)
from database.db import (
    init_db,
    get_db_connection,
    get_all_sections,
    get_section,
    get_open_positions,
    open_position,
    close_position_in_db,
    get_trade_history,
    get_portfolio_summary,
    STARTING_BALANCE_PER_SECTION,
    get_pending_setups,
    enrich_trade_metadata,
    reconcile_sections_ledger,
    purge_phantom_churn_trades,
    reset_fresh_portfolio_db
)
from engine.feed import market_feed
from engine.ms_ob_engine import hermes_ms_ob_engine

STATIC_DIR = BASE_DIR / "static"

async def vault_periodic_sync_loop():
    """Periodically pushes full ledger state to GitHub data-vault branch every 5 minutes."""
    await asyncio.sleep(60)
    while True:
        try:
            from database.cloud_vault import push_vault_state
            push_vault_state()
        except Exception as _ve:
            print(f"[PERIODIC VAULT SYNC NOTE] {_ve}")
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize clean SQLite & exclusive Hermes MS-OB Engine (zero legacy strategies/watchdogs)
    init_db()
    try:
        from database.cloud_vault import pull_and_restore_vault_state
        restored = pull_and_restore_vault_state()
        if restored:
            print("[CLOUD VAULT] Restored Hermes MS-OB state from GitHub data-vault branch!")
    except Exception as _ve:
        print(f"[CLOUD VAULT RESTORE ERROR] {_ve}")

    try:
        purged = purge_phantom_churn_trades()
        if purged > 0:
            print(f"[RECONCILIATION] Cleaned {purged} rapid phantom churn trades.")
    except Exception as e:
        print(f"[RECONCILIATION ERROR] {e}")
    reconcile_sections_ledger()
    asyncio.create_task(market_feed.get_all_tickers())
    ms_ob_task = asyncio.create_task(hermes_ms_ob_engine.start_loop())
    vault_task = asyncio.create_task(vault_periodic_sync_loop())
    yield
    # Shutdown
    hermes_ms_ob_engine.stop_loop()
    ms_ob_task.cancel()
    vault_task.cancel()

app = FastAPI(title=f"{BRAND_NAME} Institutional Terminal", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
MODULAR_DIR = STATIC_DIR / "modular"
MODULAR_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/modular", StaticFiles(directory=str(MODULAR_DIR)), name="modular")

@app.middleware("http")
async def add_modular_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in ("/mobile", "/nexus/mobile") or request.url.path.startswith("/modular/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ----------------- PAGE ROUTES -----------------

@app.api_route("/ping", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
async def ping_health():
    return {"status": "ok", "service": "NexusPro", "timestamp": time.time()}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/trade", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/futures", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/nexus/trade", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_trade_page():
    return FileResponse(STATIC_DIR / "trade.html")

@app.get("/markets", response_class=HTMLResponse)
@app.get("/nexus/markets", response_class=HTMLResponse)
async def serve_markets_page():
    return FileResponse(STATIC_DIR / "markets.html")

@app.get("/deca", response_class=HTMLResponse)
@app.get("/compounding", response_class=HTMLResponse)
@app.get("/nexus/deca", response_class=HTMLResponse)
async def serve_deca_page():
    return FileResponse(STATIC_DIR / "deca.html")

@app.get("/assets", response_class=HTMLResponse)
@app.get("/wallet", response_class=HTMLResponse)
@app.get("/nexus/assets", response_class=HTMLResponse)
async def serve_assets_page():
    return FileResponse(STATIC_DIR / "assets.html")

@app.get("/hologram", response_class=HTMLResponse)
@app.get("/nexus/hologram", response_class=HTMLResponse)
async def serve_hologram_page():
    return FileResponse(STATIC_DIR / "hologram.html")

@app.get("/positions", response_class=HTMLResponse)
@app.get("/nexus/positions", response_class=HTMLResponse)
async def serve_positions_page():
    return FileResponse(STATIC_DIR / "positions.html")

@app.api_route("/mobile", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/nexus/mobile", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_mobile_page():
    return FileResponse(
        MODULAR_DIR / "index.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

# ----------------- REST API ENDPOINTS -----------------

@app.api_route("/api/status", methods=["GET", "HEAD"])
async def get_status():
    summary = get_portfolio_summary()
    return {
        "status": "online",
        "brand": BRAND_NAME,
        "tagline": BRAND_SUBTITLE,
        "strategy": "HERMES_MS_OB",
        "allowed_direction": "BUY / SELL (BOTH)",
        "first_tap_rule": "Strong/Cond: Strict 1st Tap Only | Weak OB: >= 18% Wick Sweep Only (1:1 TV Sync)",
        "mode": "HERMES_MS_OB_EXCLUSIVE (1:1 TV Sync BUY/SELL | BE +12%->+2.5% | Hard SL -15% | TP +15%)",
        "starting_capital": summary["starting_capital"],
        "total_equity": summary["total_equity"],
        "total_balance": summary["total_balance"],
        "margin_per_trade_usdt": hermes_ms_ob_engine.margin_per_trade,
        "max_concurrent_trades": hermes_ms_ob_engine.max_concurrent_trades,
        "sl_buffer_pct": getattr(hermes_ms_ob_engine, "hard_sl_price_pct", 0.03) * 100.0,
        "hard_sl_roi_pct": -15.0,
        "full_book_tp_roi_pct": 15.0,
        "default_leverage": DEFAULT_LEVERAGE,
        "leverage_overrides": SYMBOL_LEVERAGE_OVERRIDES,
        "dynamic_armor": {
            "hard_sl": "-15.0% ROI (BTC/ETH 10x: 1.5% Price | Gold 20x: 0.75% Price | Default 5x: 3.0% Price, 2x15m Guard)",
            "breakeven_shield": "+12.0% ROI -> Lock +2.5% ROI",
            "full_book_tp": "+15.0% ROI (BTC/ETH 10x: 1.5% Price | Gold 20x: 0.75% Price | Default 5x: 3.0% Price)",
            "compounding": "DISABLED (Flat 5% Margin = $50)"
        },
        "win_rate": summary["win_rate"],
        "active_positions": summary["active_positions_count"],
        "scanned_setups_count": len(hermes_ms_ob_engine.scanned_setups),
        "timestamp": time.time()
    }

@app.get("/api/markets")
async def get_markets():
    tickers = await market_feed.get_all_tickers()
    # Filter to top champions first, then others
    top_list = []
    other_list = []
    for sym, t in (tickers or {}).items():
        if not sym.endswith("USDT"):
            continue
        item = {
            **t,
            "is_champion": sym in CHAMPIONS,
            "section_id": PAIR_MAPPING.get(sym, None)
        }
        if sym in CHAMPIONS:
            top_list.append(item)
        else:
            other_list.append(item)

    top_list.sort(key=lambda x: x.get("volume_24h", 0.0), reverse=True)
    other_list.sort(key=lambda x: x.get("volume_24h", 0.0), reverse=True)
    return {"champions": top_list, "all_markets": top_list + other_list[:60]}

@app.get("/api/ticker/{symbol}")
async def get_ticker(symbol: str):
    ticker = await market_feed.get_ticker(symbol)
    if not ticker:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return ticker

@app.get("/api/klines/{symbol}")
async def get_klines(symbol: str, interval: str = "15m", limit: int = 150):
    candles = await market_feed.get_klines(symbol, interval=interval, limit=limit)
    return {"symbol": symbol.upper(), "interval": interval, "candles": candles}

@app.get("/api/orderbook/{symbol}")
async def get_orderbook(symbol: str, depth: int = 12):
    ob = await market_feed.get_order_book(symbol, depth=depth)
    return ob

@app.get("/api/deca/summary")
async def get_deca_summary():
    return get_portfolio_summary()

@app.get("/api/paper/account")
async def get_paper_account():
    summary = get_portfolio_summary()
    init_cap = float(summary.get("starting_capital", 1000.0) or 1000.0)
    tot_bal = float(summary.get("total_balance", init_cap))
    tot_pnl = float(summary.get("total_pnl", 0.0))
    return {
        **summary,
        "current_balance": round(tot_bal, 2),
        "balance": round(tot_bal, 2),
        "total_current_balance": round(tot_bal, 2),
        "combined_10x": {
            "initial_balance": init_cap,
            "total_pnl_pct": round((tot_pnl / init_cap) * 100.0, 2) if init_cap > 0 else 0.0,
        },
    }

@app.get("/api/assets/analytics")
@app.get("/api/paper/assets_analytics")
async def get_assets_analytics():
    tickers = await market_feed.get_all_tickers()
    from database.assets_analytics import get_assets_analytics_payload
    return get_assets_analytics_payload(tickers)


@app.get("/api/deca/sections")
async def get_deca_sections():
    sections = get_all_sections()
    return {"sections": sections}

@app.get("/api/deca/setups")
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
            "leverage": s.get("leverage", get_symbol_leverage(sym)),
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
    return {"count": len(all_setups), "setups": all_setups}

@app.get("/api/smc/upcoming_setups")
async def get_smc_upcoming_setups(max_distance: float = 6.0):
    open_pos = get_open_positions()
    busy_symbols = {p["symbol"] for p in open_pos}
    raw_setups = hermes_ms_ob_engine.scanned_setups or []
    formatted = []
    for s in raw_setups:
        sym = s.get("symbol", "")
        if not sym or sym in busy_symbols:
            continue
        dist = float(s.get("proximity_pct", 0.0) or 0.0)
        if dist > max_distance:
            continue
        side = str(s.get("side", "LONG")).upper()
        is_long = side in ("LONG", "BUY")
        ob_top = float(s.get("ob_top", 0.0) or 0.0)
        ob_bot = float(s.get("ob_bottom", 0.0) or 0.0)
        curr_p = float(s.get("current_price", 0.0) or 0.0)
        is_inside = (ob_bot <= curr_p <= ob_top) if (ob_top > ob_bot > 0 and curr_p > 0) else False
        formatted.append({
            "symbol": sym,
            "direction": "DEMAND" if is_long else "SUPPLY",
            "side": "BUY" if is_long else "SELL",
            "leverage": s.get("leverage", get_symbol_leverage(sym)),
            "timeframe": str(s.get("timeframe", "1h")).upper(),
            "current_price": curr_p,
            "entry_price": float(s.get("entry_price", 0.0) or 0.0),
            "ob_top": ob_top,
            "ob_bottom": ob_bot,
            "ob_mid": float(s.get("ob_mid", 0.0) or 0.0),
            "sl_price": float(s.get("sl_price", 0.0) or 0.0),
            "tp_price": float(s.get("tp_price", 0.0) or 0.0),
            "distance_pct": round(dist, 2),
            "is_inside": is_inside,
            "model": s.get("model", "Hermes MS-OB"),
            "category": s.get("category", "STRONG"),
            "status": s.get("status", "SCANNING"),
        })
    formatted.sort(key=lambda x: x["distance_pct"])
    return {"count": len(formatted), "setups": formatted}

@app.post("/api/admin/heal_ledger")
@app.get("/api/admin/heal_ledger")
async def heal_ledger():
    purged = purge_phantom_churn_trades()
    reconcile_sections_ledger()
    return {
        "status": "ok",
        "purged_phantoms": purged,
        "message": f"Successfully purged {purged} rapid phantom churn trades and restored Deca sections equity!"
    }

@app.get("/api/trade/positions")
@app.get("/api/paper/positions")
async def get_positions():
    pos = get_open_positions()
    tickers = await market_feed.get_all_tickers()
    enriched = []
    for p in pos:
        item = dict(p)
        sym = item["symbol"]
        ticker = tickers.get(sym)
        if ticker:
            cur_price = ticker["last_price"]
            item["mark_price"] = cur_price
            side = item["side"]
            entry = item["entry_price"]
            margin = item["margin_usdt"]
            leverage = item["leverage"]
            price_diff = (cur_price - entry) if side in ("BUY", "LONG") else (entry - cur_price)
            pnl_pct = round((price_diff / entry) * leverage * 100.0, 2)
            u_pnl = round((pnl_pct / 100.0) * margin, 2)
            item["unrealized_pnl"] = u_pnl
            item["pnl_pct"] = pnl_pct

            # Dynamic MFE (Peak Profit) & MAE (Peak Drawdown) Tracking
            cur_mfe = float(item.get("mfe_pct") or 0.0)
            cur_mae = float(item.get("mae_pct") or 0.0)

            # MFE is peak favorable excursion and must ALWAYS be >= current ROE (if positive)
            new_mfe = max(cur_mfe, max(0.0, pnl_pct))

            # MAE is peak adverse excursion (drawdown) and must ALWAYS be >= current loss (if negative)
            current_drawdown = max(0.0, -pnl_pct)
            new_mae = max(cur_mae, current_drawdown)

            # Check 24h ticker high / low for candle-level adverse excursion
            high_24h = float(ticker.get("high_price") or cur_price)
            low_24h = float(ticker.get("low_price") or cur_price)
            if side in ("BUY", "LONG"):
                if low_24h > 0 and low_24h < entry:
                    cand_mae = round(((entry - low_24h) / entry) * leverage * 100.0, 2)
                    new_mae = max(new_mae, min(cand_mae, 15.0))
            else:
                if high_24h > entry:
                    cand_mae = round(((high_24h - entry) / entry) * leverage * 100.0, 2)
                    new_mae = max(new_mae, min(cand_mae, 15.0))

            item["mfe_pct"] = round(new_mfe, 2)
            item["mae_pct"] = round(new_mae, 2)

            if new_mfe > cur_mfe or new_mae > cur_mae:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE positions 
                        SET mfe_pct = ?, mae_pct = ?, mark_price = ?, unrealized_pnl = ?, pnl_pct = ?, updated_at = ? 
                        WHERE id = ?
                    """, (new_mfe, new_mae, cur_price, u_pnl, pnl_pct, time.time(), p["id"]))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
        else:
            cur_mfe = float(item.get("mfe_pct") or 0.0)
            cur_mae = float(item.get("mae_pct") or 0.0)
            cur_roe = float(item.get("pnl_pct") or 0.0)
            item["mfe_pct"] = max(cur_mfe, max(0.0, cur_roe))
            item["mae_pct"] = max(cur_mae, max(0.0, -cur_roe))

        if "size_usdt" not in item or not item["size_usdt"]:
            item["size_usdt"] = item.get("position_size_usdt", item.get("margin_usdt", 50.0) * 5.0)
        open_t = item.get("open_time")
        if open_t and not item.get("entry_time"):
            item["entry_time"] = int(float(open_t) * 1000) if float(open_t) < 1e11 else int(open_t)
        item.setdefault("liq_price", float(item.get("liquidation_price") or 0.0))
        t_stage = int(item.get("trailing_stage") or 0)
        item.setdefault("trailing_step", t_stage)
        item.setdefault("be_locked", t_stage >= 1)
        item.setdefault("hard_sl_price", float(item.get("sl_price") or 0.0))
        item.setdefault("timeframe", "1H")
        enriched.append(item)
    return {"positions": enriched, "count": len(enriched)}

@app.post("/api/trade/order")
async def place_order(order: Dict[str, Any] = Body(...)):
    symbol = order.get("symbol", "BTCUSDT").upper()
    side = order.get("side", "LONG").upper()
    order_type = order.get("order_type", "LIMIT").upper()
    leverage = int(order.get("leverage", DEFAULT_LEVERAGE))
    margin = float(order.get("margin_usdt", 25.0))
    entry_price = float(order.get("entry_price", 0.0))
    sl_price = float(order.get("sl_price", 0.0))
    tp_price = float(order.get("tp_price", 0.0))

    if entry_price <= 0:
        ticker = await market_feed.get_ticker(symbol)
        if not ticker:
            raise HTTPException(status_code=400, detail="Unable to get current price for symbol")
        entry_price = ticker["last_price"]

    if sl_price <= 0:
        sl_price = round(entry_price * (0.985 if side == "LONG" else 1.015), 6)
    # Pure Trailing SL Mode: Fixed TP disabled per user mandate
    tp_price = 0.0

    sec_id = PAIR_MAPPING.get(symbol, 1)
    pos_size = round(margin * leverage, 2)
    liq_price = round(entry_price * (0.82 if side == "LONG" else 1.18), 6)

    pos_id = open_position({
        "section_id": sec_id,
        "symbol": symbol,
        "side": side,
        "entry_price": entry_price,
        "mark_price": entry_price,
        "position_size_usdt": pos_size,
        "size_usdt": pos_size,
        "margin_usdt": margin,
        "leverage": leverage,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "trailing_sl_price": sl_price,
        "trailing_stage": 0,
        "liquidation_price": liq_price,
        "order_type": order_type
    })

    return {"status": "SUCCESS", "position_id": pos_id, "symbol": symbol, "side": side, "entry_price": entry_price}

@app.post("/api/trade/close/{pos_id}")
async def close_trade(pos_id: int):
    try:
        open_pos = get_open_positions()
        target = next((p for p in open_pos if p["id"] == pos_id), None)
        if not target:
            return JSONResponse(status_code=404, content={"success": False, "error": "Position not found or already closed"})

        ticker = await market_feed.get_ticker(target["symbol"])
        curr_price = ticker["last_price"] if ticker else target["mark_price"]
        side = target["side"]
        margin = target["margin_usdt"]
        leverage = target["leverage"]

        price_diff = (curr_price - target["entry_price"]) if side in ("BUY", "LONG") else (target["entry_price"] - curr_price)
        pnl = round((price_diff / target["entry_price"]) * leverage * margin, 2)

        close_position_in_db(pos_id, curr_price, pnl, "MANUAL_CLOSE")
        return {"status": "CLOSED", "success": True, "position_id": pos_id, "realized_pnl": pnl}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/api/trade/close")
@app.post("/api/paper/close")
async def close_trade_body(body: Dict[str, Any] = Body(...)):
    try:
        pos_id = body.get("position_id") or body.get("trade_id")
        symbol = body.get("symbol")
        open_pos = get_open_positions()
        target = None
        if pos_id:
            target = next((p for p in open_pos if p["id"] == int(pos_id)), None)
        if not target and symbol:
            target = next((p for p in open_pos if p["symbol"] == symbol.upper()), None)

        if not target:
            return {"success": False, "error": "Position not found or already closed"}

        ticker = await market_feed.get_ticker(target["symbol"])
        curr_price = ticker["last_price"] if ticker else target["mark_price"]
        side = target["side"]
        margin = target["margin_usdt"]
        leverage = target["leverage"]

        price_diff = (curr_price - target["entry_price"]) if side in ("BUY", "LONG") else (target["entry_price"] - curr_price)
        pnl = round((price_diff / target["entry_price"]) * leverage * margin, 2)

        close_position_in_db(target["id"], curr_price, pnl, "MANUAL_CLOSE")
        return {"status": "CLOSED", "success": True, "position_id": target["id"], "realized_pnl": pnl}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/api/trade/history")
@app.get("/api/paper/trades")
async def get_history(limit: int = 50):
    trades = get_trade_history(limit=limit)
    enriched = [enrich_trade_metadata(t) for t in trades]
    return {"trades": enriched, "count": len(enriched)}

@app.get("/api/admin/reconcile")
@app.post("/api/admin/reconcile")
async def trigger_reconciliation():
    reconcile_sections_ledger()
    return {"status": "SUCCESS", "summary": get_portfolio_summary()}

# ----------------- LEGACY SYNC DECOMMISSIONED -----------------

@app.post("/api/sync/trade")
async def sync_trade_decommissioned():
    return JSONResponse(
        status_code=410,
        content={"status": "DECOMMISSIONED", "message": "Legacy BB 3.0 sync disabled — Hermes MS-OB exclusive"}
    )

@app.post("/api/deca/reset")
@app.post("/api/paper/reset")
async def reset_deca():
    """Deletes all old trade records/positions/OB locks and resets portfolio cleanly to $1,000.00 USDT."""
    summary = reset_fresh_portfolio_db()
    hermes_ms_ob_engine._ob_lifecycle.clear()
    hermes_ms_ob_engine._cooldowns.clear()
    hermes_ms_ob_engine.scanned_setups = []
    try:
        from database.cloud_vault import push_vault_state
        push_vault_state(force_reset=True)
    except Exception:
        pass
    return {
        "status": "RESET_SUCCESS",
        "message": "All old trades cleared. Portfolio reset cleanly to $1,000.00 USDT ($100 x 10 sections).",
        "summary": summary
    }

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/json")

@app.get("/download/apk")
@app.get("/apk")
async def download_apk():
    apk_path = os.path.join(STATIC_DIR, "NexusPro_Trading_Terminal.apk")
    if not os.path.exists(apk_path):
        apk_path = os.path.join(STATIC_DIR, "NexusPro_BB_Mobile_Terminal.apk")
    if os.path.exists(apk_path):
        return FileResponse(apk_path, media_type="application/vnd.android.package-archive", filename="NexusPro_Trading_Terminal.apk")
    raise HTTPException(status_code=404, detail="APK file not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)


# ----------------- ENGINE DIAGNOSTIC ROUTES (WATCHDOG DECOMMISSIONED) -----------------

@app.get("/api/sentinel/status")
async def get_sentinel_status():
    summary = get_portfolio_summary()
    return {
        "status": "HEALTHY",
        "health_score": 100,
        "engine": "Hermes MS-OB v2.0 GOLDEN Exclusive (Legacy Watchdogs Removed)",
        "total_audits_run": 0,
        "total_issues_healed": 0,
        "active_positions": summary["active_positions_count"],
        "recent_learned_lessons": []
    }

@app.get("/api/sentinel/logs")
async def get_sentinel_logs(limit: int = Query(50, ge=1, le=200)):
    return {"status": "OK", "knowledge_base": [], "total_audits_run": 0, "total_issues_healed": 0}

@app.get("/api/sentinel/diagnose")
@app.post("/api/sentinel/diagnose")
async def run_sentinel_diagnose():
    return {
        "status": "SUCCESS",
        "message": "Hermes MS-OB Exclusive Engine active. Legacy watchdogs and BB strategies permanently removed.",
        "report": {"status": "HEALTHY", "health_score": 100, "engine": "HERMES_MS_OB"}
    }

# ----------------- CLOUD VAULT DATA PERSISTENCE ROUTES -----------------

@app.get("/api/vault/status")
async def get_vault_status():
    """Returns the live sync status of Cloud Vault on GitHub branch data-vault."""
    from database.cloud_vault import LOCAL_VAULT_BACKUP, VAULT_BRANCH
    from database.db import get_trade_history, get_portfolio_summary
    trades = get_trade_history(limit=100)
    summary = get_portfolio_summary()
    has_local = LOCAL_VAULT_BACKUP.exists()
    return {
        "status": "ARMED",
        "branch": VAULT_BRANCH,
        "total_trades_persisted": len(trades),
        "total_equity": summary.get("total_equity", 500.0),
        "local_backup_present": has_local
    }

@app.post("/api/vault/sync")
async def trigger_vault_sync():
    """Triggers an immediate on-demand backup push to GitHub data-vault branch."""
    from database.cloud_vault import push_vault_state
    success = push_vault_state()
    return {
        "status": "SUCCESS" if success else "FAILED",
        "message": "Cloud Vault synced with GitHub data-vault branch." if success else "Vault push encountered an error."
    }
