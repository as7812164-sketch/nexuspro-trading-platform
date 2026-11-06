"""
HERMES MS ORDER BLOCK INSTITUTIONAL EXECUTION ENGINE v2.0
=========================================================
- 7-Model Order Block Architecture (Shoaib Khan / MS Trading Masterclass)
- Strong OB, Weak OB (Wick Swept), Conditional Type 6 & 7
- 1st Tap Entry Protocol (Sentry 4)
- 0.5% Buffer Beyond OB Boundary Stop Loss
- Dynamic Armor: +1.0% Breakeven, +1.8% Trailing SL, +2.8% Take Profit
- 5% Margin Allocation ($50 USDT on $1,000 Capital), 5x Isolated
- Concurrency: Max 8 Simultaneous Trades
- Markets: Crypto on 1H & 4H | Gold (PAXGUSDT) on 15m, 1H & 4H
"""

import time
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from pathlib import Path
from config import DEFAULT_LEVERAGE, CHAMPIONS, PAIR_MAPPING
from database.db import (
    get_open_positions,
    open_position,
    update_position_mark_price,
    close_position_in_db,
    sync_external_setup,
    remove_external_setup,
    get_all_sections,
    update_section_balance
)

class HermesMSOBEngine:
    def __init__(self):
        self.portfolio_capital = 1000.0   # $1,000 Base Portfolio
        self.margin_per_trade = 50.0      # 5% = $50 USDT
        self.max_concurrent_trades = 8     # Max 8 concurrent positions
        self.leverage = DEFAULT_LEVERAGE  # 5x Isolated
        self.sl_buffer_pct = 0.005         # 0.5% beyond OB boundary
        self.target_tp_pct = 2.8           # Take Profit +2.8%
        self.breakeven_trigger = 1.0       # Breakeven fee shield at +1.0%
        self.trailing_trigger = 1.8        # Trailing profit lock at +1.8%
        
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
        """
        if len(candles) < 25:
            return []
            
        atr = self.calculate_atr(candles, 14)
        if atr <= 0:
            return []
            
        curr_price = candles[-1]["close"]
        curr_low = candles[-1]["low"]
        curr_high = candles[-1]["high"]
        
        lookback = min(len(candles) - 4, 30)
        recent_swing_high = max(c["high"] for c in candles[-lookback:-3])
        recent_swing_low = min(c["low"] for c in candles[-lookback:-3])
        
        valid_setups = []
        scan_start = max(2, len(candles) - 15)
        
        for i in range(scan_start, len(candles) - 1):
            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]
            
            # --- Bullish OB ---
            fvg_bull = c3["low"] > c1["high"] and (c3["low"] - c1["high"]) >= (atr * 0.15)
            disp_bull = (c2["close"] - c2["open"]) >= (atr * 1.2)
            
            if fvg_bull and disp_bull:
                c1_bull = c1["close"] > c1["open"]
                c1_bear = c1["close"] < c1["open"]
                c2_breach = c2["low"] < c1["low"]
                is_swing_origin = abs(c1["low"] - recent_swing_low) < (atr * 0.5)
                
                cat_name = "STRONG" if (c1_bear or is_swing_origin) else "WEAK"
                model_desc = "Type 2: Classic Opposite OB" if c1_bear else ("Type 4: Swing Origin OB" if is_swing_origin else "Type 1: Momentum OB")
                
                ob_top = c1["high"]
                ob_bottom = c2["low"] if c2_breach else c1["low"]
                ob_mid = (ob_top + ob_bottom) / 2.0
                
                # Check mitigation / invalidation in bars after formation
                is_invalidated = False
                is_mitigated = False
                for post_idx in range(i + 1, len(candles) - 1):
                    post_c = candles[post_idx]
                    if post_c["close"] < ob_bottom:
                        is_invalidated = True
                        break
                    if post_c["low"] <= ob_top:
                        is_mitigated = True
                        
                if not is_invalidated and not is_mitigated:
                    # SL with 0.5% buffer below OB bottom
                    sl_p = ob_bottom * (1.0 - self.sl_buffer_pct)
                    tp_p = ob_top * (1.0 + self.target_tp_pct / 100.0)
                    
                    # Proximity check
                    dist_pct = ((curr_price - ob_top) / curr_price) * 100.0 if curr_price > ob_top else 0.0
                    is_tap = curr_low <= ob_top and curr_price >= ob_bottom
                    
                    valid_setups.append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "side": "LONG",
                        "model": model_desc,
                        "category": cat_name,
                        "ob_top": round(ob_top, 4),
                        "ob_bottom": round(ob_bottom, 4),
                        "ob_mid": round(ob_mid, 4),
                        "entry_price": round(ob_top, 4),
                        "sl_price": round(sl_p, 4),
                        "tp_price": round(tp_p, 4),
                        "proximity_pct": round(dist_pct, 2),
                        "is_first_tap": is_tap,
                        "current_price": round(curr_price, 4),
                        "status": "IMMINENT_FIRST_TAP" if is_tap else "WAITING_1ST_TAP"
                    })

            # --- Bearish OB ---
            fvg_bear = c3["high"] < c1["low"] and (c1["low"] - c3["high"]) >= (atr * 0.15)
            disp_bear = (c2["open"] - c2["close"]) >= (atr * 1.2)
            
            if fvg_bear and disp_bear:
                c1_bull = c1["close"] > c1["open"]
                c1_bear = c1["close"] < c1["open"]
                c2_breach = c2["high"] > c1["high"]
                is_swing_origin = abs(c1["high"] - recent_swing_high) < (atr * 0.5)
                
                cat_name = "STRONG" if (c1_bull or is_swing_origin) else "WEAK"
                model_desc = "Type 2: Classic Opposite OB" if c1_bull else ("Type 4: Swing Origin OB" if is_swing_origin else "Type 1: Momentum OB")
                
                ob_top = c2["high"] if c2_breach else c1["high"]
                ob_bottom = c1["low"]
                ob_mid = (ob_top + ob_bottom) / 2.0
                
                # Check mitigation / invalidation
                is_invalidated = False
                is_mitigated = False
                for post_idx in range(i + 1, len(candles) - 1):
                    post_c = candles[post_idx]
                    if post_c["close"] > ob_top:
                        is_invalidated = True
                        break
                    if post_c["high"] >= ob_bottom:
                        is_mitigated = True
                        
                if not is_invalidated and not is_mitigated:
                    # SL with 0.5% buffer above OB top
                    sl_p = ob_top * (1.0 + self.sl_buffer_pct)
                    tp_p = ob_bottom * (1.0 - self.target_tp_pct / 100.0)
                    
                    dist_pct = ((ob_bottom - curr_price) / curr_price) * 100.0 if curr_price < ob_bottom else 0.0
                    is_tap = curr_high >= ob_bottom and curr_price <= ob_top
                    
                    valid_setups.append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "side": "SHORT",
                        "model": model_desc,
                        "category": cat_name,
                        "ob_top": round(ob_top, 4),
                        "ob_bottom": round(ob_bottom, 4),
                        "ob_mid": round(ob_mid, 4),
                        "entry_price": round(ob_bottom, 4),
                        "sl_price": round(sl_p, 4),
                        "tp_price": round(tp_p, 4),
                        "proximity_pct": round(dist_pct, 2),
                        "is_first_tap": is_tap,
                        "current_price": round(curr_price, 4),
                        "status": "IMMINENT_FIRST_TAP" if is_tap else "WAITING_1ST_TAP"
                    })
                    
        return valid_setups

    async def run_scan_cycle(self):
        """
        Executes scanning cycle across Crypto & Gold timeframes.
        Executes First Tap triggers up to max 8 concurrent trades.
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
                        
                        # Check First Tap Execution if under concurrency limit
                        if len(open_pos) < self.max_concurrent_trades and sym not in active_symbols:
                            tap_setup = next((s for s in setups if s["is_first_tap"]), None)
                            if tap_setup:
                                now = time.time()
                                cd_key = f"{sym}_{tap_setup['side']}"
                                if now - self._cooldowns.get(cd_key, 0) > 300: # 5 min cooldown
                                    await self.execute_trade_trigger(tap_setup)
                                    active_symbols.add(sym)
                                    open_pos = get_open_positions()
                                    
        self.scanned_setups = all_setups[:25]

    async def execute_trade_trigger(self, setup: Dict[str, Any]):
        """
        Opens a live position on 1st Tap of Order Block.
        Allocates exact 5% of Portfolio ($50 USDT) with 5x leverage.
        """
        sym = setup["symbol"]
        side = setup["side"]
        entry_p = setup["entry_price"]
        sl_p = setup["sl_price"]
        tp_p = setup["tp_price"]
        tf = setup["timeframe"]
        
        pos_size = self.margin_per_trade * self.leverage # $250 USDT
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
            print(f"🟢 [HERMES MS-OB] 1st Tap Executed: #{pos_id} {side} {sym} @ {entry_p} | SL: {sl_p} (0.5% Buffer) | Margin: ${self.margin_per_trade} (5%)")
        except Exception as e:
            print(f"❌ Trade execution error for {sym}: {e}")

    async def update_open_positions(self):
        """
        Monitors active positions against live mark price.
        Applies Dynamic Profit Armor:
        - Breakeven shift (+1.0%)
        - Trailing stop (+1.8%)
        - SL hit (0.5% buffer)
        - TP hit (+2.8%)
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
                            
                            side = pos["side"].upper()
                            entry_p = float(pos["entry_price"])
                            sl_p = float(pos.get("trailing_sl_price") or pos.get("sl_price") or 0.0)
                            tp_p = float(pos.get("tp_price") or 0.0)
                            margin = float(pos.get("margin_usdt") or self.margin_per_trade)
                            lev = int(pos.get("leverage") or self.leverage)
                            
                            # Calculate PnL and ROE
                            if side == "LONG" or side == "BUY":
                                gain_pct = ((curr_price - entry_p) / entry_p) * 100.0
                                roe_pct = gain_pct * lev
                                u_pnl = margin * (roe_pct / 100.0)
                                
                                # Dynamic Armor
                                new_sl = sl_p
                                stage = int(pos.get("trailing_stage") or 0)
                                
                                if roe_pct >= self.breakeven_trigger * lev and stage == 0:
                                    new_sl = entry_p * 1.0005 # Breakeven fee shield
                                    stage = 1
                                elif roe_pct >= self.trailing_trigger * lev and stage <= 1:
                                    trail_candidate = curr_price * (1.0 - 0.005)
                                    if trail_candidate > new_sl:
                                        new_sl = trail_candidate
                                        stage = 2
                                        
                                # Check Exit Triggers
                                if curr_price <= sl_p:
                                    realized = margin * (((sl_p - entry_p) / entry_p) * lev)
                                    close_position_in_db(pos["id"], sl_p, realized, "STOP_LOSS_HIT")
                                    print(f"🛑 [HERMES MS-OB] Long SL Hit: {sym} @ {sl_p}")
                                    continue
                                elif tp_p > 0 and curr_price >= tp_p:
                                    realized = margin * (((tp_p - entry_p) / entry_p) * lev)
                                    close_position_in_db(pos["id"], tp_p, realized, "TAKE_PROFIT_HIT")
                                    print(f"🎯 [HERMES MS-OB] Long TP Hit: {sym} @ {tp_p}")
                                    continue
                                    
                            else: # SHORT / SELL
                                gain_pct = ((entry_p - curr_price) / entry_p) * 100.0
                                roe_pct = gain_pct * lev
                                u_pnl = margin * (roe_pct / 100.0)
                                
                                new_sl = sl_p
                                stage = int(pos.get("trailing_stage") or 0)
                                
                                if roe_pct >= self.breakeven_trigger * lev and stage == 0:
                                    new_sl = entry_p * 0.9995
                                    stage = 1
                                elif roe_pct >= self.trailing_trigger * lev and stage <= 1:
                                    trail_candidate = curr_price * (1.0 + 0.005)
                                    if trail_candidate < new_sl:
                                        new_sl = trail_candidate
                                        stage = 2
                                        
                                if curr_price >= sl_p:
                                    realized = margin * (((entry_p - sl_p) / entry_p) * lev)
                                    close_position_in_db(pos["id"], sl_p, realized, "STOP_LOSS_HIT")
                                    print(f"🛑 [HERMES MS-OB] Short SL Hit: {sym} @ {sl_p}")
                                    continue
                                elif tp_p > 0 and curr_price <= tp_p:
                                    realized = margin * (((entry_p - tp_p) / entry_p) * lev)
                                    close_position_in_db(pos["id"], tp_p, realized, "TAKE_PROFIT_HIT")
                                    print(f"🎯 [HERMES MS-OB] Short TP Hit: {sym} @ {tp_p}")
                                    continue
                                    
                            # Update mark price & trailing SL in DB
                            update_position_mark_price(pos["id"], curr_price, u_pnl, round(roe_pct, 2), new_sl, stage)
                except Exception:
                    pass

    async def start_loop(self):
        """Active background execution loop for Hermes MS-OB Engine."""
        self._is_running = True
        print(f"🏛️ [HERMES MS-OB] Autonomous Engine Active: Portfolio ${self.portfolio_capital} | Margin ${self.margin_per_trade} (5%) | Max 8 Trades")
        while self._is_running:
            try:
                await self.update_open_positions()
                await self.run_scan_cycle()
            except Exception as e:
                print(f"[MS-OB Engine Loop Error]: {e}")
            await asyncio.sleep(10) # 10s Evaluation Cycle

    def stop_loop(self):
        self._is_running = False

hermes_ms_ob_engine = HermesMSOBEngine()
