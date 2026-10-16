"""
NEXUSPRO FUTURES & DECA COMPOUNDING TERMINAL (FASTAPI BACKEND)
============================================================
Brand: NexusPro
Format: 100% Bitget Pro Layout & UI
Engine: BB 2.0 ($47,389.77 USDT Historic Compounding Model)
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
    DEFAULT_LEVERAGE
)
from database.db import (
    init_db,
    get_all_sections,
    get_section,
    get_open_positions,
    open_position,
    close_position_in_db,
    get_trade_history,
    get_portfolio_summary,
    STARTING_BALANCE_PER_SECTION
)
from engine.feed import market_feed
from engine.bb20_sniper import bb20_sniper

STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background BB 2.0 scanner and position monitor
    init_db()
    sniper_task = asyncio.create_task(bb20_sniper.start_loop())
    yield
    # Shutdown
    bb20_sniper.stop_loop()
    sniper_task.cancel()

app = FastAPI(title=f"{BRAND_NAME} Institutional Terminal", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ----------------- PAGE ROUTES -----------------

@app.get("/", response_class=HTMLResponse)
@app.get("/trade", response_class=HTMLResponse)
@app.get("/futures", response_class=HTMLResponse)
async def serve_trade_page():
    return FileResponse(STATIC_DIR / "trade.html")

@app.get("/markets", response_class=HTMLResponse)
async def serve_markets_page():
    return FileResponse(STATIC_DIR / "markets.html")

@app.get("/deca", response_class=HTMLResponse)
@app.get("/compounding", response_class=HTMLResponse)
async def serve_deca_page():
    return FileResponse(STATIC_DIR / "deca.html")

@app.get("/assets", response_class=HTMLResponse)
@app.get("/wallet", response_class=HTMLResponse)
async def serve_assets_page():
    return FileResponse(STATIC_DIR / "assets.html")

@app.get("/hologram", response_class=HTMLResponse)
async def serve_hologram_page():
    return FileResponse(STATIC_DIR / "hologram.html")

# ----------------- REST API ENDPOINTS -----------------

@app.get("/api/status")
async def get_status():
    summary = get_portfolio_summary()
    return {
        "status": "online",
        "brand": BRAND_NAME,
        "tagline": BRAND_SUBTITLE,
        "mode": "BB_2.0_DECA_COMPOUNDING",
        "starting_capital": summary["starting_capital"],
        "total_equity": summary["total_equity"],
        "win_rate": summary["win_rate"],
        "active_positions": summary["active_positions_count"],
        "timestamp": time.time()
    }

@app.get("/api/markets")
async def get_markets():
    tickers = await market_feed.get_all_tickers()
    # Filter to top champions first, then others
    top_list = []
    other_list = []
    for sym, t in tickers.items():
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

    top_list.sort(key=lambda x: x["volume_24h"], reverse=True)
    other_list.sort(key=lambda x: x["volume_24h"], reverse=True)
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

@app.get("/api/deca/sections")
async def get_deca_sections():
    sections = get_all_sections()
    return {"sections": sections}

@app.get("/api/deca/setups")
async def get_deca_setups():
    return {"count": len(bb20_sniper.scanned_setups), "setups": bb20_sniper.scanned_setups}

@app.get("/api/trade/positions")
async def get_positions():
    pos = get_open_positions()
    return {"positions": pos, "count": len(pos)}

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
    if tp_price <= 0:
        risk = abs(entry_price - sl_price)
        tp_price = round(entry_price + (risk * 2.0) if side == "LONG" else entry_price - (risk * 2.0), 6)

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
    open_pos = get_open_positions()
    target = next((p for p in open_pos if p["id"] == pos_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Position not found or already closed")

    ticker = await market_feed.get_ticker(target["symbol"])
    curr_price = ticker["last_price"] if ticker else target["mark_price"]
    side = target["side"]
    margin = target["margin_usdt"]
    leverage = target["leverage"]

    price_diff = (curr_price - target["entry_price"]) if side == "LONG" else (target["entry_price"] - curr_price)
    pnl = round((price_diff / target["entry_price"]) * leverage * margin, 2)

    close_position_in_db(pos_id, curr_price, pnl, "MANUAL_CLOSE")
    return {"status": "CLOSED", "position_id": pos_id, "realized_pnl": pnl}

@app.get("/api/trade/history")
async def get_history(limit: int = 50):
    trades = get_trade_history(limit=limit)
    return {"trades": trades, "count": len(trades)}

@app.post("/api/deca/reset")
async def reset_deca():
    """Resets paper accounts back to $50.00 each = $500.00 initial capital."""
    from database.db import get_db_connection
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM positions")
    c.execute("DELETE FROM trade_history")
    now = time.time()
    c.execute("""
        UPDATE deca_sections SET
            current_balance = ?,
            equity = ?,
            total_pnl = 0.0,
            pnl_pct = 0.0,
            win_count = 0,
            loss_count = 0,
            win_rate = 0.0,
            status = 'IDLE',
            active_symbol = NULL,
            updated_at = ?
    """, (STARTING_BALANCE_PER_SECTION, STARTING_BALANCE_PER_SECTION, now))
    conn.commit()
    conn.close()
    return {"status": "RESET_SUCCESS", "message": "All 10 Deca sections reset to $50.00 ($500.00 total equity)."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)
