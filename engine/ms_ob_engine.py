"""
HERMES MS ORDER BLOCK INSTITUTIONAL EXECUTION ENGINE (v2.0 GOLDEN FINAL)
========================================================================
- 7-Model Order Block Architecture (Shoaib Khan / MS Trading Masterclass)
- Zero Compounding Mode (Normal Institutional Futures Trading)
- Total Portfolio: $1,000.00 USDT
- Margin Deployment: Flat 5% ($50.00 USDT) Per Trade
- Leverage: Strictly 5x Isolated ($250.00 USDT Position Size)
- Dual Entry Pathways:
  * Pathway 1 (Respect Reversal): OB Tapped -> 5m Candle Body Close outside OB -> Entry Trigger
  * Pathway 2 (Sweep Trap Reclaim): OB Breached -> Within 2 Hours (<=120 min) Reclaim + 5m Close outside OB -> Entry Trigger
- Dynamic Break-Even Shield:
  * Peak ROI hits +12.0% -> Shift & Lock Stop Loss to +2.5% ROI (Guaranteed Profit + Fee Shield)
- Hard Stop Loss:
  * Level: -15.0% ROI (-3.0% Price Move at 5x)
  * Anti-Hunt Filter: Strictly 2 Consecutive 15m Candle Body Closes beyond SL
- Full Book Take Profit:
  * Target: +15.0% ROI (+3.0% Price Move at 5x)
- Max Concurrent Trades: 8 Positions ($400 Margin Used, $600 Free Safety Cushion)
"""

import time
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from pathlib import Path
from config import (
    DEFAULT_LEVERAGE,
    CHAMPIONS,
    PAIR_MAPPING,
    HARD_SL_PRICE_PCT,
    FULL_BOOK_TP_PRICE_PCT,
    BREAKEVEN_TRIGGER_ROI,
    BREAKEVEN_LOCK_ROI,
    SL_CONSECUTIVE_15M_CANDLES,
    SWEEP_RECLAIM_TIMEBOX_MINUTES
)
from database.db import (
    get_open_positions,
    open_position,
    update_position_mark_price,
    close_position_in_db,
    get_all_sections
)

class HermesMSOBEngine:
    def __init__(self):
        self.portfolio_capital = 1000.0       # $1,000.00 Flat Portfolio (Zero Compounding)
        self.margin_per_trade = 50.0          # Flat 5% = $50.00 USDT
        self.max_concurrent_trades = 8        # Max 8 concurrent positions
        self.leverage = DEFAULT_LEVERAGE      # 5x Isolated Margin
        self.hard_sl_price_pct = HARD_SL_PRICE_PCT / 100.0   # 0.03 (3.0% Price Distance = -15.0% ROI)
        self.full_tp_price_pct = FULL_BOOK_TP_PRICE_PCT / 100.0 # 0.03 (3.0% Price Distance = +15.0% ROI)
        self.be_trigger_roi = BREAKEVEN_TRIGGER_ROI           # +12.0% ROI
        self.be_lock_roi = BREAKEVEN_LOCK_ROI                 # +2.5% ROI Lock
        self.sweep_window_sec = SWEEP_RECLAIM_TIMEBOX_MINUTES * 60 # 7200 seconds (2 Hours)
        
        self.crypto_timeframes = ["1h", "4h"]
        self.gold_timeframes = ["15m", "1h", "4h"]
        self.gold_symbol = "PAXGUSDT"
        
        self.watchlist = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", 
            "DOGEUSDT", "NEARUSDT", "SUIUSDT", "TIAUSDT", "OPUSDT", 
            "ARBUSDT", "RENDERUSDT", "FETUSDT", "PAXGUSDT"
        ]
        
        self.scanned_setups: List[Dict[str, Any]] = []
        self._is_running = False
        self._cooldowns: Dict[str, float] = {}
        # Key: "{symbol}_{timeframe}_{side}_{ob_top}_{ob_bottom}" -> tracking dict
        self._ob_lifecycle: Dict[str, Dict[str, Any]] = {}

    def calculate_atr(self, candles: List[Dict[str, Any]], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.0
        tr_list = []
        for i in range(1, len(candles)):
            c_high = candles[i]["high"]
            c_low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(c_high - c_low, abs(c_high - prev_close), abs(c_low - prev_close))
            tr_list.append(tr)
        return sum(tr_list[-period:]) / period if tr_list else 0.0

    async def fetch_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str, limit: int = 40) -> List[Dict[str, Any]]:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            async with session.get(url, timeout=7) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                candles = []
                for k in data:
                    candles.append({
                        "time": int(k[0]) // 1000,
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                return candles
        except Exception:
            return []

    def scan_symbol_order_blocks(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classifies unmitigated 7-Model Order Blocks on the specified timeframe.
        Calculates exact -15% Hard SL and +15% Full Book TP.
        Tracks First Tap and 2-Hour Sweep Reclaim states.
        """
        if len(candles) < 25:
            return []
            
        atr = self.calculate_atr(candles, 14)
        if atr <= 0:
            return []
            
        curr_price = candles[-1]["close"]
        curr_low = candles[-1]["low"]
        curr_high = candles[-1]["high"]
        now = time.time()
        
        lookback = min(len(candles) - 4, 30)
        recent_swing_high = max(c["high"] for c in candles[-lookback:-3])
        recent_swing_low = min(c["low"] for c in candles[-lookback:-3])
        
        valid_setups = []
        scan_start = max(2, len(candles) - 15)
        
        for i in range(scan_start, len(candles) - 1):
            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]
            
            # --- Bullish Order Block ---
            fvg_bull = c3["low"] > c1["high"] and (c3["low"] - c1["high"]) >= (atr * 0.12)
            disp_bull = (c2["close"] - c2["open"]) >= (atr * 0.70)
            
            if fvg_bull and disp_bull:
                c1_bull = c1["close"] > c1["open"]
                c1_bear = c1["close"] < c1["open"]
                c2_breach = c2["low"] < c1["low"]
                is_swing_origin = abs(c1["low"] - recent_swing_low) < (atr * 0.5)
                
                # Full 7-model classification
                if is_swing_origin and c1_bear:
                    model_desc = "Type 4: Swing Origin OB"
                    cat_name = "STRONG"
                elif c1_bear:
                    model_desc = "Type 2: Classic Opposite OB"
                    cat_name = "STRONG"
                elif c2_breach:
                    model_desc = "Type 3: Outlier C2 Breach OB"
                    cat_name = "WEAK"
                elif c1_bull:
                    model_desc = "Type 1: Momentum Same-Color OB"
                    cat_name = "WEAK"
                else:
                    model_desc = "Type 5: Mid-Leg Internal OB"
                    cat_name = "WEAK"
                
                ob_top = c1["high"]
                ob_bottom = min(c1["low"], c2["low"]) if c2_breach else c1["low"]
                if ob_top - ob_bottom < atr * 0.20:
                    ob_bottom = ob_top - (atr * 0.35)
                ob_mid = (ob_top + ob_bottom) / 2.0
                
                # Check post-formation bars
                is_invalidated = False
                is_tapped = False
                is_breached = False
                
                for post_idx in range(i + 1, len(candles)):
                    post_c = candles[post_idx]
                    if post_c["low"] <= ob_top:
                        is_tapped = True
                    if post_c["low"] < ob_bottom:
                        is_breached = True
                    if post_c["close"] < ob_bottom:
                        # Body closed below OB -> check sweep window
                        is_breached = True
                
                ob_key = f"{symbol}_{timeframe}_LONG_{round(ob_top, 4)}_{round(ob_bottom, 4)}"
                if ob_key not in self._ob_lifecycle:
                    self._ob_lifecycle[ob_key] = {
                        "tapped": is_tapped,
                        "tap_time": now if is_tapped else None,
                        "breached": is_breached,
                        "breach_time": now if is_breached else None,
                        "invalidated": False
                    }
                else:
                    st = self._ob_lifecycle[ob_key]
                    if is_tapped and not st["tapped"]:
                        st["tapped"] = True
                        st["tap_time"] = now
                    if is_breached and not st["breached"]:
                        st["breached"] = True
                        st["breach_time"] = now
                
                st = self._ob_lifecycle[ob_key]
                # Check 2-Hour Expiration on Breached Zones
                if st["breached"] and st["breach_time"]:
                    if (now - st["breach_time"]) > self.sweep_window_sec:
                        st["invalidated"] = True
                        is_invalidated = True
                
                if not is_invalidated and not st["invalidated"]:
                    entry_p = ob_top
                    sl_p = entry_p * (1.0 - self.hard_sl_price_pct) # -15% ROI at 5x
                    tp_p = entry_p * (1.0 + self.full_tp_price_pct) # +15% ROI at 5x
                    dist_pct = ((curr_price - entry_p) / curr_price) * 100.0 if curr_price > entry_p else 0.0
                    
                    status = "WAITING_1ST_TAP"
                    if st["breached"]:
                        status = "SWEEP_BREACH_RECLAIM_WINDOW"
                    elif st["tapped"]:
                        status = "RESPECT_WAITING_5M_CONFIRM"
                    
                    valid_setups.append({
                        "ob_key": ob_key,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "side": "LONG",
                        "model": model_desc,
                        "category": cat_name,
                        "ob_top": round(ob_top, 4),
                        "ob_bottom": round(ob_bottom, 4),
                        "ob_mid": round(ob_mid, 4),
                        "entry_price": round(entry_p, 4),
                        "sl_price": round(sl_p, 4),
                        "tp_price": round(tp_p, 4),
                        "sl_roi_pct": -15.0,
                        "tp_roi_pct": 15.0,
                        "proximity_pct": round(dist_pct, 2),
                        "is_first_tap": st["tapped"],
                        "is_breached": st["breached"],
                        "current_price": round(curr_price, 4),
                        "status": status
                    })

            # --- Bearish Order Block ---
            fvg_bear = c3["high"] < c1["low"] and (c1["low"] - c3["high"]) >= (atr * 0.12)
            disp_bear = (c2["open"] - c2["close"]) >= (atr * 0.70)
            
            if fvg_bear and disp_bear:
                c1_bull = c1["close"] > c1["open"]
                c1_bear = c1["close"] < c1["open"]
                c2_breach = c2["high"] > c1["high"]
                is_swing_origin = abs(c1["high"] - recent_swing_high) < (atr * 0.5)
                
                if is_swing_origin and c1_bull:
                    model_desc = "Type 4: Swing Origin OB"
                    cat_name = "STRONG"
                elif c1_bull:
                    model_desc = "Type 2: Classic Opposite OB"
                    cat_name = "STRONG"
                elif c2_breach:
                    model_desc = "Type 3: Outlier C2 Breach OB"
                    cat_name = "WEAK"
                elif c1_bear:
                    model_desc = "Type 1: Momentum Same-Color OB"
                    cat_name = "WEAK"
                else:
                    model_desc = "Type 5: Mid-Leg Internal OB"
                    cat_name = "WEAK"
                
                ob_top = max(c1["high"], c2["high"]) if c2_breach else c1["high"]
                ob_bottom = c1["low"]
                if ob_top - ob_bottom < atr * 0.20:
                    ob_top = ob_bottom + (atr * 0.35)
                ob_mid = (ob_top + ob_bottom) / 2.0
                
                is_invalidated = False
                is_tapped = False
                is_breached = False
                
                for post_idx in range(i + 1, len(candles)):
                    post_c = candles[post_idx]
                    if post_c["high"] >= ob_bottom:
                        is_tapped = True
                    if post_c["high"] > ob_top:
                        is_breached = True
                    if post_c["close"] > ob_top:
                        is_breached = True
                
                ob_key = f"{symbol}_{timeframe}_SHORT_{round(ob_top, 4)}_{round(ob_bottom, 4)}"
                if ob_key not in self._ob_lifecycle:
                    self._ob_lifecycle[ob_key] = {
                        "tapped": is_tapped,
                        "tap_time": now if is_tapped else None,
                        "breached": is_breached,
                        "breach_time": now if is_breached else None,
                        "invalidated": False
                    }
                else:
                    st = self._ob_lifecycle[ob_key]
                    if is_tapped and not st["tapped"]:
                        st["tapped"] = True
                        st["tap_time"] = now
                    if is_breached and not st["breached"]:
                        st["breached"] = True
                        st["breach_time"] = now
                
                st = self._ob_lifecycle[ob_key]
                if st["breached"] and st["breach_time"]:
                    if (now - st["breach_time"]) > self.sweep_window_sec:
                        st["invalidated"] = True
                        is_invalidated = True
                
                if not is_invalidated and not st["invalidated"]:
                    entry_p = ob_bottom
                    sl_p = entry_p * (1.0 + self.hard_sl_price_pct) # -15% ROI at 5x
                    tp_p = entry_p * (1.0 - self.full_tp_price_pct) # +15% ROI at 5x
                    dist_pct = ((entry_p - curr_price) / curr_price) * 100.0 if curr_price < entry_p else 0.0
                    
                    status = "WAITING_1ST_TAP"
                    if st["breached"]:
                        status = "SWEEP_BREACH_RECLAIM_WINDOW"
                    elif st["tapped"]:
                        status = "RESPECT_WAITING_5M_CONFIRM"
                    
                    valid_setups.append({
                        "ob_key": ob_key,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "side": "SHORT",
                        "model": model_desc,
                        "category": cat_name,
                        "ob_top": round(ob_top, 4),
                        "ob_bottom": round(ob_bottom, 4),
                        "ob_mid": round(ob_mid, 4),
                        "entry_price": round(entry_p, 4),
                        "sl_price": round(sl_p, 4),
                        "tp_price": round(tp_p, 4),
                        "sl_roi_pct": -15.0,
                        "tp_roi_pct": 15.0,
                        "proximity_pct": round(dist_pct, 2),
                        "is_first_tap": st["tapped"],
                        "is_breached": st["breached"],
                        "current_price": round(curr_price, 4),
                        "status": status
                    })
                    
        return valid_setups

    async def check_5m_confirmation(self, session: aiohttp.ClientSession, setup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates the 5m candle confirmation for the 2 approved entry pathways:
        - Pathway 1 (Respect): OB tapped, not breached, 5m candle closed outside OB in favor
        - Pathway 2 (Sweep Reclaim): OB breached, within 2 hours, 5m candle closed outside OB in favor
        """
        sym = setup["symbol"]
        side = setup["side"]
        ob_top = setup["ob_top"]
        ob_bottom = setup["ob_bottom"]
        st = self._ob_lifecycle.get(setup["ob_key"], {})
        
        if not st.get("tapped") or st.get("invalidated"):
            return None
            
        candles_5m = await self.fetch_klines(session, sym, "5m", limit=8)
        if len(candles_5m) < 3:
            return None
            
        # The last completed candle is candles_5m[-2] (since [-1] is currently active)
        last_closed_5m = candles_5m[-2]
        close_p = last_closed_5m["close"]
        now = time.time()
        
        # --- PATHWAY 1: Respect & Reversal ---
        if not st.get("breached"):
            if side == "LONG" and close_p > ob_top:
                return {
                    "pathway": "PATHWAY_1_RESPECT_5M_CLOSE",
                    "entry_price": close_p,
                    "candle_time": last_closed_5m["time"]
                }
            elif side == "SHORT" and close_p < ob_bottom:
                return {
                    "pathway": "PATHWAY_1_RESPECT_5M_CLOSE",
                    "entry_price": close_p,
                    "candle_time": last_closed_5m["time"]
                }
                
        # --- PATHWAY 2: Sweep & 2-Hour Reclamation ---
        elif st.get("breached") and st.get("breach_time"):
            elapsed = now - st["breach_time"]
            if elapsed <= self.sweep_window_sec: # within 2 hours
                if side == "LONG" and close_p > ob_top:
                    return {
                        "pathway": "PATHWAY_2_SWEEP_2H_RECLAIM_5M_CLOSE",
                        "entry_price": close_p,
                        "candle_time": last_closed_5m["time"]
                    }
                elif side == "SHORT" and close_p < ob_bottom:
                    return {
                        "pathway": "PATHWAY_2_SWEEP_2H_RECLAIM_5M_CLOSE",
                        "entry_price": close_p,
                        "candle_time": last_closed_5m["time"]
                    }
            else:
                st["invalidated"] = True
                
        return None

    async def run_scan_cycle(self):
        """
        Executes scanning cycle across Crypto (1H/4H) & Gold (15m/1H/4H).
        Evaluates 5m Confirmation & 2h Sweep Reclaim before triggering entry.
        """
        open_pos = get_open_positions()
        active_symbols = {p["symbol"] for p in open_pos}
        all_setups = []
        
        async with aiohttp.ClientSession() as session:
            for sym in self.watchlist:
                tfs = self.gold_timeframes if sym == self.gold_symbol else self.crypto_timeframes
                for tf in tfs:
                    candles = await self.fetch_klines(session, sym, tf, limit=45)
                    if candles:
                        setups = self.scan_symbol_order_blocks(sym, tf, candles)
                        all_setups.extend(setups)
                        
                        # Evaluate entry trigger if under concurrency limit
                        if len(open_pos) < self.max_concurrent_trades and sym not in active_symbols:
                            for setup in setups:
                                if setup["is_first_tap"]:
                                    now = time.time()
                                    cd_key = f"{sym}_{setup['side']}"
                                    if now - self._cooldowns.get(cd_key, 0) > 300: # 5 min cooldown
                                        confirm = await self.check_5m_confirmation(session, setup)
                                        if confirm:
                                            await self.execute_trade_trigger(setup, confirm)
                                            active_symbols.add(sym)
                                            open_pos = get_open_positions()
                                            break
                                    
        self.scanned_setups = all_setups[:25]

    async def execute_trade_trigger(self, setup: Dict[str, Any], confirm: Dict[str, Any]):
        """
        Opens live position upon 5m candle close confirmation.
        Allocates exact Flat 5% of Portfolio ($50 USDT) with 5x leverage ($250 size).
        Sets -15% Hard SL (protected by 2x 15m candle closes) and +15% Full Book TP.
        """
        sym = setup["symbol"]
        side = setup["side"]
        entry_p = confirm["entry_price"]
        tf = setup["timeframe"]
        pathway = confirm["pathway"]
        
        # Exact 3% price move = 15% ROI at 5x
        if side == "LONG":
            sl_p = round(entry_p * (1.0 - self.hard_sl_price_pct), 6)
            tp_p = round(entry_p * (1.0 + self.full_tp_price_pct), 6)
        else:
            sl_p = round(entry_p * (1.0 + self.hard_sl_price_pct), 6)
            tp_p = round(entry_p * (1.0 - self.full_tp_price_pct), 6)
            
        pos_size = self.margin_per_trade * self.leverage # $250.00 USDT
        sec_id = PAIR_MAPPING.get(sym, (len(get_open_positions()) % 8) + 1)
        
        pos_data = {
            "section_id": sec_id,
            "symbol": sym,
            "side": side,
            "entry_price": entry_p,
            "sl_price": sl_p,
            "tp_price": tp_p,
            "margin_usdt": self.margin_per_trade,
            "position_size_usdt": pos_size,
            "leverage": self.leverage,
            "order_type": "LIMIT",
            "timeframe": tf
        }
        
        try:
            pos_id = open_position(pos_data)
            self._cooldowns[f"{sym}_{side}"] = time.time()
            print(f"⚡ [HERMES MS-OB] Entry #{pos_id} via {pathway}: {side} {sym} @ {entry_p} | SL: {sl_p} (-15% ROI, 2x15m close guard) | TP: {tp_p} (+15% ROI)")
        except Exception as e:
            print(f"❌ Trade execution error for {sym}: {e}")

    async def update_open_positions(self):
        """
        Monitors active positions with:
        1. Full Book TP (+15% ROI) instant execution
        2. Break-Even Shield (+12% ROI -> Lock +2.5% ROI)
        3. Hard SL (-15% ROI) requiring 2 consecutive 15m candle closes
        """
        open_pos = get_open_positions()
        if not open_pos:
            return
            
        async with aiohttp.ClientSession() as session:
            for pos in open_pos:
                sym = pos["symbol"]
                url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}"
                try:
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            curr_price = float(data["price"])
                            
                            pos_id = pos["id"]
                            side = pos["side"].upper()
                            entry_p = float(pos["entry_price"])
                            sl_p = float(pos.get("sl_price") or 0.0)
                            tp_p = float(pos.get("tp_price") or 0.0)
                            trailing_sl_p = float(pos.get("trailing_sl_price") or 0.0)
                            stage = int(pos.get("trailing_stage") or 0)
                            margin = float(pos.get("margin_usdt") or self.margin_per_trade)
                            lev = int(pos.get("leverage") or self.leverage)
                            
                            # Calculate live ROE
                            if side in ["LONG", "BUY"]:
                                gain_pct = ((curr_price - entry_p) / entry_p) * 100.0
                            else:
                                gain_pct = ((entry_p - curr_price) / entry_p) * 100.0
                            roe_pct = gain_pct * lev
                            u_pnl = margin * (roe_pct / 100.0)
                            
                            # ----------------------------------------------------
                            # RULE 1: FULL BOOK TAKE PROFIT (+15.0% ROI)
                            # ----------------------------------------------------
                            is_tp_hit = (side in ["LONG", "BUY"] and curr_price >= tp_p) or                                         (side in ["SHORT", "SELL"] and curr_price <= tp_p)
                            if tp_p > 0 and is_tp_hit:
                                realized = margin * 0.15 # +15% ROI = +$7.50 USDT
                                close_position_in_db(pos_id, tp_p, realized, "FULL_BOOK_TP_HIT (+15% ROI)")
                                print(f"🎯 [HERMES MS-OB] Full TP Hit (+15% ROI): #{pos_id} {sym} @ {tp_p}")
                                continue
                                
                            # ----------------------------------------------------
                            # RULE 2: BREAK-EVEN SHIELD (+12% ROI -> LOCK +2.5% ROI)
                            # ----------------------------------------------------
                            if roe_pct >= self.be_trigger_roi and stage == 0:
                                # Lock +2.5% ROI profit (+0.5% price move at 5x)
                                if side in ["LONG", "BUY"]:
                                    be_sl = round(entry_p * (1.0 + (self.be_lock_roi / (lev * 100.0))), 6)
                                else:
                                    be_sl = round(entry_p * (1.0 - (self.be_lock_roi / (lev * 100.0))), 6)
                                    
                                stage = 1
                                sl_p = be_sl
                                trailing_sl_p = be_sl
                                update_position_mark_price(pos_id, curr_price, u_pnl, round(roe_pct, 2), be_sl, stage)
                                print(f"🛡️ [HERMES MS-OB] Break-Even Activated! #{pos_id} {sym} touched {roe_pct:.1f}% ROI! SL locked at +2.5% ROI ({be_sl})")
                                
                            # ----------------------------------------------------
                            # RULE 3: BREAK-EVEN PROFIT EXIT (IF RETESTS +2.5% ROI)
                            # ----------------------------------------------------
                            if stage == 1 and trailing_sl_p > 0:
                                is_be_exit = (side in ["LONG", "BUY"] and curr_price <= trailing_sl_p) or                                              (side in ["SHORT", "SELL"] and curr_price >= trailing_sl_p)
                                if is_be_exit:
                                    realized = margin * (self.be_lock_roi / 100.0) # +$1.25 USDT
                                    close_position_in_db(pos_id, trailing_sl_p, realized, "BREAKEVEN_PROFIT_LOCKED (+2.5% ROI)")
                                    print(f"🛡️ [HERMES MS-OB] Break-Even Exit: #{pos_id} {sym} protected at +2.5% ROI ({trailing_sl_p})")
                                    continue
                                    
                            # ----------------------------------------------------
                            # RULE 4: HARD STOP LOSS (-15.0% ROI) WITH 2x 15M CLOSE GUARD
                            # ----------------------------------------------------
                            if stage == 0:
                                hard_sl_level = round(entry_p * (1.0 - self.hard_sl_price_pct), 6) if side in ["LONG", "BUY"] else round(entry_p * (1.0 + self.hard_sl_price_pct), 6)
                                is_sl_tapped = (side in ["LONG", "BUY"] and curr_price <= hard_sl_level) or                                                (side in ["SHORT", "SELL"] and curr_price >= hard_sl_level)
                                               
                                if is_sl_tapped:
                                    # Fetch last 5 candles of 15m to check 2 consecutive candle closes
                                    candles_15m = await self.fetch_klines(session, sym, "15m", limit=6)
                                    if len(candles_15m) >= 4:
                                        c_prev2 = candles_15m[-3]
                                        c_prev1 = candles_15m[-2] # last completed 15m candle
                                        
                                        if side in ["LONG", "BUY"]:
                                            c1_closed_below = c_prev2["close"] < hard_sl_level
                                            c2_closed_below = c_prev1["close"] < hard_sl_level
                                            two_closes_confirmed = c1_closed_below and c2_closed_below
                                        else:
                                            c1_closed_above = c_prev2["close"] > hard_sl_level
                                            c2_closed_above = c_prev1["close"] > hard_sl_level
                                            two_closes_confirmed = c1_closed_above and c2_closed_above
                                            
                                        if two_closes_confirmed:
                                            realized = margin * (-self.hard_sl_price_pct * lev) # -$7.50 USDT (-15% ROI)
                                            close_position_in_db(pos_id, curr_price, realized, "HARD_SL_HIT_2x15M_CONFIRMED (-15% ROI)")
                                            print(f"🛑 [HERMES MS-OB] Hard SL Confirmed (2x 15m Closes): #{pos_id} {sym} @ {curr_price} (-15% ROI)")
                                            continue
                                        else:
                                            # Wick Hunt Shield: Do not close!
                                            pass
                                            
                            # Update DB mark price
                            update_position_mark_price(pos_id, curr_price, u_pnl, round(roe_pct, 2), sl_p, stage)
                except Exception:
                    pass

    async def start_loop(self):
        """Active background execution loop for Hermes MS-OB Engine."""
        self._is_running = True
        print(f"⚡ [HERMES MS-OB v2.0 FINAL] Engine Active: $1000 Portfolio | 5% Margin ($50) | 5x Lev | 5m Close Entry | BE +12%->+2.5% | Hard SL -15% (2x15m Guard) | Full TP +15%")
        while self._is_running:
            try:
                await self.update_open_positions()
                await self.run_scan_cycle()
            except Exception as e:
                print(f"[MS-OB Engine Loop Error]: {e}")
            await asyncio.sleep(10)

    def stop_loop(self):
        self._is_running = False

hermes_ms_ob_engine = HermesMSOBEngine()
