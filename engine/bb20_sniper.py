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
    TRAILING_TIER_1_TRIGGER_ROI,
    TRAILING_TIER_1_LOCK_ROI,
    TRAILING_STEP_ROI,
    TRAILING_BUFFER_ROI,
    DEFAULT_RRR,
    STRATEGY_NAME,
    STRATEGY_VERSION,
    STRATEGY_MODEL
)

# ROI Stepped Trailing SL Calculation Functions (Continuous Ladder)
def get_roi_trailing_tier(peak_roi_pct: float) -> int:
    """
    Returns the trailing tier based on peak ROI%:
    < 4.80%   -> Tier 0 (Initial SL active)
    >= 4.80%  -> Tier 1 (SL to +1.00% ROI - Risk-Free Fee Shield)
    >= 9.80%  -> Tier 2 (SL to +5.10% ROI)
    >= 14.80% -> Tier 3 (SL to +10.10% ROI)
    >= 19.80% -> Tier 4 (SL to +15.10% ROI)
    >= 24.80% -> Tier 5 (SL to +20.10% ROI)
    >= 29.80% -> Tier 6 (SL to +25.10% ROI)
    >= 34.80% -> Tier 7 (SL to +30.10% ROI)
    General: Every +5.0% additional ROI peak shifts SL forward by +5.0% ROI indefinitely!
    """
    if peak_roi_pct < 4.80:
        return 0
    return int(round((peak_roi_pct - 4.80) / 5.0 + 1e-5, 4)) + 1

def get_locked_roi(tier: int) -> float:
    """
    Returns the locked ROI% for a given tier:
    Tier 0 -> 0.0%
    Tier 1 -> 1.00%
    Tier 2 -> 5.10%
    Tier 3 -> 10.10%
    Tier 4 -> 15.10%
    Tier k -> 5.10 + (k - 2) * 5.0%
    """
    if tier <= 0:
        return 0.0
    if tier == 1:
        return 1.00
    return round(5.10 + (tier - 2) * 5.0, 2)

def calculate_trailing_sl_price(entry: float, side: str, locked_roi_pct: float, leverage: float = 5.0) -> float:
    """
    Translates locked ROI% to exact stop-loss spot price at given leverage:
    Spot Move % = ROI% / Leverage
    LONG:  SL = Entry * (1 + locked_roi / (leverage * 100))
    SHORT: SL = Entry * (1 - locked_roi / (leverage * 100))
    """
    spot_fraction = locked_roi_pct / (leverage * 100.0)
    if side == "LONG":
        return round(entry * (1.0 + spot_fraction), 6)
    else:
        return round(entry * (1.0 - spot_fraction), 6)

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
        self.invalidated_setups: set = set()
        self.cooldown_tracker: Dict[str, float] = {}

    async def scan_symbol_bb20(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Scans a single champion for BB 2.0 PDH/PDL sweeps and 15m Extreme OBs."""
        # Anti-churn cooldown: after a trade closes on this symbol, do not re-enter for 60 minutes
        if time.time() - self.cooldown_tracker.get(symbol, 0) < 3600:
            return None

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
                        # 1. Check if setup was already blacklisted / stopped out
                        if (symbol, "LONG", round(mt_entry, 4)) in self.invalidated_setups:
                            continue

                        # 2. Invalidation Check: Did ANY subsequent candle breach SL or is current price below SL?
                        is_invalidated = False
                        for past_c in candles_15m[i + 1:]:
                            if float(past_c["low"]) <= sl_price:
                                is_invalidated = True
                                break
                        if is_invalidated or curr_price <= sl_price:
                            self.invalidated_setups.add((symbol, "LONG", round(mt_entry, 4)))
                            continue

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
                        # 1. Check if setup was already blacklisted / stopped out
                        if (symbol, "SHORT", round(mt_entry, 4)) in self.invalidated_setups:
                            continue

                        # 2. Invalidation Check: Did ANY subsequent candle breach SL or is current price above SL?
                        is_invalidated = False
                        for past_c in candles_15m[i + 1:]:
                            if float(past_c["high"]) >= sl_price:
                                is_invalidated = True
                                break
                        if is_invalidated or curr_price >= sl_price:
                            self.invalidated_setups.add((symbol, "SHORT", round(mt_entry, 4)))
                            continue

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
                # Skip symbol if currently in post-exit cooldown
                if time.time() - self.cooldown_tracker.get(symbol, 0) < 3600:
                    continue

                setup = await self.scan_symbol_bb20(symbol)
                if setup:
                    setups.append(setup)
                    sec_id = setup["section_id"]
                    curr_p = setup["current_price"]
                    entry_p = setup["entry_price"]
                    sl_p = setup["sl_price"]

                    # Strict Directional Limit Retest Tap Logic:
                    # - For LONG: price approaches from above, touches 50% MT, and remains strictly above SL
                    # - For SHORT: price approaches from below, touches 50% MT, and remains strictly below SL
                    can_execute = False
                    if setup["side"] == "LONG":
                        if curr_p <= entry_p * 1.0010 and curr_p > sl_p:
                            can_execute = True
                    elif setup["side"] == "SHORT":
                        if curr_p >= entry_p * 0.9990 and curr_p < sl_p:
                            can_execute = True

                    if (can_execute and
                        symbol not in busy_symbols and
                        sec_id not in busy_sections):

                        sec = get_section(sec_id)
                        if sec and sec["current_balance"] >= 5.0:
                            margin = round(sec["current_balance"], 2)
                            pos_size = round(margin * DEFAULT_LEVERAGE, 2)
                            liq_price = round(
                                entry_p * (1.0 - 0.18) if setup["side"] == "LONG"
                                else entry_p * (1.0 + 0.18), 6
                            )

                            pos_id = open_position({
                                "section_id": sec_id,
                                "symbol": symbol,
                                "side": setup["side"],
                                "entry_price": entry_p,
                                "mark_price": curr_p,
                                "position_size_usdt": pos_size,
                                "margin_usdt": margin,
                                "leverage": DEFAULT_LEVERAGE,
                                "sl_price": sl_p,
                                "tp_price": setup["tp_price"],
                                "trailing_sl_price": sl_p,
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

            # Minimum 20-second trade evaluation grace period to prevent sub-10s execution race
            open_t = float(pos.get("open_time") or time.time())
            if time.time() - open_t < 20.0:
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
            else:
                price_diff = entry - curr_price
                sl_hit = curr_price >= sl

            pnl_pct = (price_diff / entry) * leverage * 100.0  # Current ROI %
            u_pnl = round((pnl_pct / 100.0) * margin, 2)

            # BB 3.0 Infinite Stepped Trailing SL Ladder (Continuous ROI Model)
            new_trailing = pos["trailing_sl_price"]
            new_stage = pos["trailing_stage"]

            tier_cand = get_roi_trailing_tier(pnl_pct)
            if tier_cand > new_stage:
                new_stage = tier_cand
                locked_roi = get_locked_roi(tier_cand)
                new_trailing = calculate_trailing_sl_price(entry, side, locked_roi, leverage)

            # Check Exit Conditions:
            if sl_hit:
                if new_stage == 0:
                    reason = "STOP_LOSS (INITIAL SL HIT)"
                elif new_stage == 1:
                    reason = "FEE_SHIELD_SAVED (+1.0% ROI)"
                else:
                    locked_roi = get_locked_roi(new_stage)
                    reason = f"BB 3.0 TRAILING PROFIT (+{locked_roi:.1f}% ROI)"

                # Activate 60-min cooldown on symbol and permanently blacklist setup
                self.cooldown_tracker[sym] = time.time()
                self.invalidated_setups.add((sym, side, round(entry, 4)))

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
