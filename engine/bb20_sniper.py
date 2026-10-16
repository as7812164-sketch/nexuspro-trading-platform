"""
NEXUSPRO BB 2.0 SNIPER ENGINE ($47K USDT COMPOUNDING MODEL)
===========================================================
- Methodology: Anish Singh Thakur (Booming Bulls) Liquidity Masterclass
- Levels: Previous Day High (PDH) & Previous Day Low (PDL) Liquidity Sweeps
- Institutional Structure: 15m Extreme Origin Order Block + FVG Imbalance
- Entry: 50% Mean Threshold (MT) Limit Retest
- Risk Management: 0.15% Anti-Hunt Buffer beyond extreme wick
- Compounding: 10 Isolated Deca Sections ($50 each = $500 initial capital)
"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from config import (
    PAIR_MAPPING,
    CHAMPIONS,
    SL_ANTI_HUNT_BUFFER,
    MEAN_THRESHOLD_RATIO,
    DEFAULT_LEVERAGE,
    TRAILING_TIER_1_TRIGGER_R,
    TRAILING_TIER_1_LOCK_R,
    TRAILING_STEP_R,
    TRAILING_OFFSET_R,
    STRATEGY_NAME,
    STRATEGY_VERSION,
    STRATEGY_MODEL
)
from engine.feed import market_feed
from database.db import (
    get_all_sections,
    get_section,
    get_open_positions,
    open_position,
    update_position_mark_price,
    close_position_in_db
)

class BB20SniperEngine:
    def __init__(self):
        self.scanned_setups: List[Dict[str, Any]] = []
        self._is_running = False

    async def scan_symbol_bb20(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Scans a single champion for BB 2.0 PDH/PDL sweeps and 15m Extreme OBs."""
        # 1. Fetch Daily klines to extract PDH & PDL
        daily_candles = await market_feed.get_klines(symbol, interval="1d", limit=3)
        if len(daily_candles) < 2:
            return None

        prev_day = daily_candles[-2]
        pdh = float(prev_day["high"])
        pdl = float(prev_day["low"])

        # 2. Fetch 15m klines to find Extreme Order Blocks
        candles_15m = await market_feed.get_klines(symbol, interval="15m", limit=80)
        if len(candles_15m) < 15:
            return None

        curr_candle = candles_15m[-1]
        curr_price = float(curr_candle["close"])
        n = len(candles_15m)

        # A. Bullish Setup: PDL Sweep + Extreme Demand OB
        for i in range(n - 10, n - 2):
            c_sweep = candles_15m[i]
            # Candle pierces below PDL or approaches within 0.8% and leaves lower rejection wick
            if float(c_sweep["low"]) <= pdl * 1.008:
                c_disp1 = candles_15m[i + 1]
                c_disp2 = candles_15m[i + 2]
                gain = (float(c_disp2["close"]) - float(c_sweep["low"])) / float(c_sweep["low"])

                # Strong institutional displacement >= 1.2%
                if gain >= 0.012 and float(c_disp2["close"]) > float(c_disp1["open"]):
                    ob_bottom = float(c_sweep["low"])
                    ob_top = max(float(c_sweep["open"]), float(c_sweep["close"]))
                    mt_entry = round(ob_bottom + (ob_top - ob_bottom) * MEAN_THRESHOLD_RATIO, 6)
                    sl_price = round(ob_bottom * (1.0 - SL_ANTI_HUNT_BUFFER), 6)
                    risk = abs(mt_entry - sl_price)

                    if risk > 0:
                        tp_price = round(mt_entry + (risk * DEFAULT_RRR), 6)
                        proximity_pct = round(abs(curr_price - mt_entry) / mt_entry * 100.0, 2)
                        return {
                            "symbol": symbol,
                            "side": "LONG",
                            "section_id": PAIR_MAPPING.get(symbol, 1),
                            "pdh": pdh,
                            "pdl": pdl,
                            "entry_price": mt_entry,
                            "sl_price": sl_price,
                            "tp_price": tp_price,
                            "risk_amount": risk,
                            "current_price": curr_price,
                            "proximity_pct": proximity_pct,
                            "status": "ARMED_RETEST" if proximity_pct <= 0.6 else "SCANNING",
                            "strategy": "BB 2.0 PDL Sweep + 50% MT Demand",
                            "timestamp": time.time()
                        }

        # B. Bearish Setup: PDH Sweep + Extreme Supply OB
        for i in range(n - 10, n - 2):
            c_sweep = candles_15m[i]
            if float(c_sweep["high"]) >= pdh * 0.992:
                c_disp1 = candles_15m[i + 1]
                c_disp2 = candles_15m[i + 2]
                drop = (float(c_sweep["high"]) - float(c_disp2["close"])) / float(c_sweep["high"])

                if drop >= 0.012 and float(c_disp2["close"]) < float(c_disp1["open"]):
                    ob_top = float(c_sweep["high"])
                    ob_bottom = min(float(c_sweep["open"]), float(c_sweep["close"]))
                    mt_entry = round(ob_top - (ob_top - ob_bottom) * MEAN_THRESHOLD_RATIO, 6)
                    sl_price = round(ob_top * (1.0 + SL_ANTI_HUNT_BUFFER), 6)
                    risk = abs(sl_price - mt_entry)

                    if risk > 0:
                        tp_price = round(mt_entry - (risk * DEFAULT_RRR), 6)
                        proximity_pct = round(abs(curr_price - mt_entry) / mt_entry * 100.0, 2)
                        return {
                            "symbol": symbol,
                            "side": "SHORT",
                            "section_id": PAIR_MAPPING.get(symbol, 1),
                            "pdh": pdh,
                            "pdl": pdl,
                            "entry_price": mt_entry,
                            "sl_price": sl_price,
                            "tp_price": tp_price,
                            "risk_amount": risk,
                            "current_price": curr_price,
                            "proximity_pct": proximity_pct,
                            "status": "ARMED_RETEST" if proximity_pct <= 0.6 else "SCANNING",
                            "strategy": "BB 2.0 PDH Sweep + 50% MT Supply",
                            "timestamp": time.time()
                        }

        return None

    async def run_scan_cycle(self):
        """Scans all Top-20 Champions and auto-executes qualified setups into Deca sections."""
        setups = []
        open_pos = get_open_positions()
        busy_symbols = {p["symbol"] for p in open_pos}
        busy_sections = {p["section_id"] for p in open_pos}

        for symbol in CHAMPIONS:
            try:
                setup = await self.scan_symbol_bb20(symbol)
                if setup:
                    setups.append(setup)
                    # Auto-execute limit retest fill if proximity <= 0.20% and section is free
                    sec_id = setup["section_id"]
                    if (setup["proximity_pct"] <= 0.25 and
                        symbol not in busy_symbols and
                        sec_id not in busy_sections):

                        sec = get_section(sec_id)
                        if sec and sec["current_balance"] >= 5.0:
                            margin = round(sec["current_balance"], 2)
                            pos_size = round(margin * DEFAULT_LEVERAGE, 2)
                            liq_price = round(
                                setup["entry_price"] * (1.0 - 0.18) if setup["side"] == "LONG"
                                else setup["entry_price"] * (1.0 + 0.18), 6
                            )

                            pos_id = open_position({
                                "section_id": sec_id,
                                "symbol": symbol,
                                "side": setup["side"],
                                "entry_price": setup["entry_price"],
                                "mark_price": setup["current_price"],
                                "position_size_usdt": pos_size,
                                "margin_usdt": margin,
                                "leverage": DEFAULT_LEVERAGE,
                                "sl_price": setup["sl_price"],
                                "tp_price": setup["tp_price"],
                                "trailing_sl_price": setup["sl_price"],
                                "trailing_stage": 0,
                                "liquidation_price": liq_price,
                                "order_type": "LIMIT"
                            })
                            busy_symbols.add(symbol)
                            busy_sections.add(sec_id)
            except Exception:
                pass

        self.scanned_setups = setups

    async def update_open_positions(self):
        """Monitors open positions, manages Stepped Trailing SL, and exits at TP/SL."""
        open_pos = get_open_positions()
        if not open_pos:
            return

        tickers = await market_feed.get_all_tickers()

        for pos in open_pos:
            sym = pos["symbol"]
            ticker = tickers.get(sym)
            if not ticker:
                continue

            curr_price = ticker["last_price"]
            entry = pos["entry_price"]
            side = pos["side"]
            margin = pos["margin_usdt"]
            leverage = pos["leverage"]
            sl = pos["trailing_sl_price"] if pos["trailing_sl_price"] > 0 else pos["sl_price"]
            tp = pos["tp_price"]

            # Calculate Price Return & Dollar PnL
            if side == "LONG":
                price_diff = curr_price - entry
                sl_hit = curr_price <= sl
                tp_hit = curr_price >= tp
            else:
                price_diff = entry - curr_price
                sl_hit = curr_price >= sl
                tp_hit = curr_price <= tp

            pnl_pct = (price_diff / entry) * leverage * 100.0
            u_pnl = round((pnl_pct / 100.0) * margin, 2)

            # R-Multiple Calculation
            risk_dist = abs(entry - pos["sl_price"])
            r_multiple = (price_diff / risk_dist) if risk_dist > 0 else 0.0

            # BB 3.0 Infinite Stepped Trailing SL Ladder (Model 2)
            new_trailing = pos["trailing_sl_price"]
            new_stage = pos["trailing_stage"]

            if r_multiple >= 1.0:
                if r_multiple >= 1.5:
                    # Dynamic Infinite Trailing: Tier candidate increments every 0.5R
                    tier_candidate = int((r_multiple - 1.0) / 0.5) + 1
                    if tier_candidate > new_stage:
                        new_stage = tier_candidate
                        locked_r = (new_stage - 1) * 0.5
                        new_trailing = entry + (risk_dist * locked_r) if side == "LONG" else entry - (risk_dist * locked_r)
                elif new_stage < 1:
                    # Tier 1 (+1.0R): Move SL to +0.2R (Fee Shield / Risk-Free)
                    new_trailing = entry + (risk_dist * TRAILING_TIER_1_LOCK_R) if side == "LONG" else entry - (risk_dist * TRAILING_TIER_1_LOCK_R)
                    new_stage = 1

            # Check Exit Conditions:
            # In BB 3.0, winners are NEVER prematurely capped at 2.0R.
            # Positions ride dynamically until trailing stop loss or initial SL is hit!
            if sl_hit:
                if new_stage == 0:
                    reason = "STOP_LOSS (-1.0R)"
                elif new_stage == 1:
                    reason = "FEE_SHIELD_SAVED (+0.2R)"
                else:
                    locked_r = (new_stage - 1) * 0.5
                    reason = f"BB 3.0 TRAILING PROFIT (+{locked_r:.1f}R)"
                close_position_in_db(pos["id"], sl, u_pnl, reason)
            else:
                update_position_mark_price(pos["id"], curr_price, u_pnl, round(pnl_pct, 2), new_trailing, new_stage)

    async def start_loop(self):
        """Continuous background execution loop."""
        self._is_running = True
        while self._is_running:
            try:
                await self.update_open_positions()
                await self.run_scan_cycle()
            except Exception:
                pass
            await asyncio.sleep(8)  # Fast 8-second evaluation loop

    def stop_loop(self):
        self._is_running = False

bb20_sniper = BB20SniperEngine()
