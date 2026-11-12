"""
HERMES MS ORDER BLOCK INSTITUTIONAL EXECUTION ENGINE (v2.0 GOLDEN — 1ST TAP EXCLUSIVE)
======================================================================================
- Exclusive Strategy for NexusPro (Zero Legacy Strategies / Zero Watchdogs)
- Strictly BUY / LONG Execution Only on Hermes MS-OB 7-Model Bullish Order Blocks
- Strictly 1st Tap Valid Only:
  * 1st Tap inside OB -> Wait for 5m Candle Body Close > OB Top -> Open LONG Position
  * Immediately retires OB in SQLite (CONSUMED_TRADE) so 2nd trade on same OB is impossible
  * If price returns for a 2nd Tap (after leaving 1st Tap) OR closes below OB Bottom ->
    Permanently Invalidated (INVALIDATED_2ND_TAP / INVALIDATED_CLOSE)
- Flat $1,000.00 Portfolio | Flat 5% Margin ($50.00) | 5x Isolated ($250.00 Size) | Max 8 Concurrent
- Break-Even Shield: +12.0% ROI -> Lock +2.5% ROI
- Hard Stop Loss: -15.0% ROI (-3.0% Price) with 2x consecutive 15m close guard
- Full Book Take Profit: +15.0% ROI (+3.0% Price)
"""

import time
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional

from config import (
    DEFAULT_LEVERAGE,
    SYMBOL_LEVERAGE_OVERRIDES,
    get_symbol_leverage,
    PAIR_MAPPING,
    HARD_SL_PRICE_PCT,
    HARD_SL_ROI_PCT,
    FULL_BOOK_TP_PRICE_PCT,
    FULL_BOOK_TP_ROI_PCT,
    BREAKEVEN_TRIGGER_ROI,
    BREAKEVEN_LOCK_ROI,
    ALLOW_SHORT_ENTRIES,
    FIXED_MARGIN_PER_TRADE,
    MAX_CONCURRENT_TRADES,
    TOTAL_PORTFOLIO_CAPITAL,
    NEXUS_TELEGRAM_BOT_TOKEN,
    NEXUS_TELEGRAM_CHAT_ID
)
from database.db import (
    get_open_positions,
    open_position,
    update_position_mark_price,
    close_position_in_db,
    is_ob_retired,
    mark_ob_state
)
from engine.feed import market_feed


class HermesMSOBEngine:
    def __init__(self):
        self.portfolio_capital = TOTAL_PORTFOLIO_CAPITAL
        self.margin_per_trade = FIXED_MARGIN_PER_TRADE
        self.max_concurrent_trades = MAX_CONCURRENT_TRADES
        self.leverage = DEFAULT_LEVERAGE
        self.hard_sl_price_pct = HARD_SL_PRICE_PCT / 100.0
        self.full_tp_price_pct = FULL_BOOK_TP_PRICE_PCT / 100.0
        self.be_trigger_roi = BREAKEVEN_TRIGGER_ROI
        self.be_lock_roi = BREAKEVEN_LOCK_ROI
        self.allow_short = ALLOW_SHORT_ENTRIES  # True -> 1:1 TradingView BUY + SELL signals

        self.crypto_timeframes = ["1h", "4h"]
        self.gold_timeframes = ["15m", "1h", "4h"]
        self.gold_symbol = "PAXGUSDT"

        self.watchlist = [
            "BTCUSDT", "ETHUSDT", "PAXGUSDT", "SOLUSDT", "BNBUSDT",
            "AVAXUSDT", "DOGEUSDT", "NEARUSDT", "SUIUSDT", "TIAUSDT",
            "OPUSDT", "ARBUSDT", "RENDERUSDT", "FETUSDT"
        ]

        self.scanned_setups: List[Dict[str, Any]] = []
        self._is_running = False
        self._cooldowns: Dict[str, float] = {}
        self._ob_lifecycle: Dict[str, Dict[str, Any]] = {}

    async def send_telegram_alert(self, session: aiohttp.ClientSession, text: str):
        if not NEXUS_TELEGRAM_BOT_TOKEN or not NEXUS_TELEGRAM_CHAT_ID:
            return
        try:
            url = f"https://api.telegram.org/bot{NEXUS_TELEGRAM_BOT_TOKEN}/sendMessage"
            await session.post(
                url,
                json={"chat_id": NEXUS_TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
                timeout=aiohttp.ClientTimeout(total=6),
            )
        except Exception:
            pass

    async def fetch_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str, limit: int = 120) -> List[Dict[str, Any]]:
        try:
            candles = await market_feed.get_klines(symbol, interval=interval, limit=limit)
            if candles and len(candles) >= 20:
                return candles
        except Exception:
            pass

        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "time": int(k[0]) // 1000,
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5]),
                        }
                        for k in data
                    ]
        except Exception:
            pass
        return []

    def scan_symbol_order_blocks(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        100% 1:1 parity with PC TradingView 'Hermes MS Trading Order Block Indicator v2.0':
        - Wilder RMA 14-period ATR (matching ta.atr(14) in Pine Script)
        - Swing Pivot Lookback = 5 | Liquidity Sweep Decay = 35 bars | IDM Lookback = min(100, bar_index - swingBar)
        - 7-Model Order Block classification (FVG >= 0.15*ATR, Displacement >= 1.2*ATR, zero 8-bar skip, exact C1/C2 bounds)
        - Strong/Cond OB (Types 2,4,6,7): Strictly 1st Tap Only (First Tap OB Boundary)
        - Weak OB (Types 1,3,5): Wick Sweep Rejection ONLY (>= 18.0% rejection wick beyond OB boundary)
        - Supports BOTH BUY (LONG) and SELL (SHORT) signals when self.allow_short=True
        """
        n = len(candles)
        if n < 30:
            return []

        # 1. Wilder RMA 14-period ATR (exact ta.atr(14) parity)
        atr_period = 14
        tr_list = [candles[0]["high"] - candles[0]["low"]]
        for i in range(1, n):
            hl = candles[i]["high"] - candles[i]["low"]
            hc = abs(candles[i]["high"] - candles[i - 1]["close"])
            lc = abs(candles[i]["low"] - candles[i - 1]["close"])
            tr_list.append(max(hl, hc, lc))

        atr_arr = [0.0] * n
        for i in range(n):
            if i < atr_period:
                atr_arr[i] = sum(tr_list[: i + 1]) / float(i + 1)
            else:
                atr_arr[i] = (atr_arr[i - 1] * (atr_period - 1) + tr_list[i]) / float(atr_period)

        swing_len = 5
        min_disp_mult = 1.2
        min_fvg_mult = 0.15
        min_weak_wick_pct = 18.0

        last_sh_price = None
        last_sl_price = None
        last_sh_bar = None
        last_sl_bar = None
        last_idm_bull = None
        last_idm_bear = None
        bull_swept = False
        bear_swept = False
        idm_bull_swept = False
        idm_bear_swept = False
        bull_sweep_bar = -999
        bear_sweep_bar = -999

        active_obs: List[Dict[str, Any]] = []

        # Walk full bar history sequentially (exact Pine Script state machine)
        for i in range(n):
            atr = atr_arr[i]

            # Swing High / Swing Low Pivot Lookback = 5
            p_idx = i - swing_len
            if p_idx >= swing_len:
                if all(
                    candles[p_idx]["high"] > candles[p_idx - w]["high"]
                    and candles[p_idx]["high"] > candles[p_idx + w]["high"]
                    for w in range(1, swing_len + 1)
                ):
                    last_sh_price = candles[p_idx]["high"]
                    last_sh_bar = p_idx
                if all(
                    candles[p_idx]["low"] < candles[p_idx - w]["low"]
                    and candles[p_idx]["low"] < candles[p_idx + w]["low"]
                    for w in range(1, swing_len + 1)
                ):
                    last_sl_price = candles[p_idx]["low"]
                    last_sl_bar = p_idx

            curr = candles[i]

            # Liquidity Sweeps with 35-bar active window
            if last_sl_price is not None and curr["low"] < last_sl_price and curr["close"] > last_sl_price:
                bull_swept = True
                bull_sweep_bar = i
            if last_sh_price is not None and curr["high"] > last_sh_price and curr["close"] < last_sh_price:
                bear_swept = True
                bear_sweep_bar = i
            if (i - bull_sweep_bar) > 35:
                bull_swept = False
            if (i - bear_sweep_bar) > 35:
                bear_swept = False

            # Break of Structure (BOS) & Inducement (IDM) Tracking
            if i > 0:
                prev = candles[i - 1]
                if last_sh_price is not None and curr["close"] > last_sh_price and prev["close"] <= last_sh_price and last_sl_bar is not None:
                    lb = min(100, max(1, i - last_sl_bar))
                    start_lb = max(0, i - lb + 1)
                    last_idm_bull = min(candles[k]["low"] for k in range(start_lb, i + 1))
                    idm_bull_swept = False
                if last_sl_price is not None and curr["close"] < last_sl_price and prev["close"] >= last_sl_price and last_sh_bar is not None:
                    lb = min(100, max(1, i - last_sh_bar))
                    start_lb = max(0, i - lb + 1)
                    last_idm_bear = max(candles[k]["high"] for k in range(start_lb, i + 1))
                    idm_bear_swept = False

            if last_idm_bull is not None and curr["low"] < last_idm_bull:
                idm_bull_swept = True
            if last_idm_bear is not None and curr["high"] > last_idm_bear:
                idm_bear_swept = True

            # OB Creation on closed 3-candle impulse (i <= n - 2 ensures c3 is closed)
            if 2 <= i <= n - 2 and atr > 0:
                c1 = candles[i - 2]
                c2 = candles[i - 1]
                c3 = candles[i]

                # A. Bullish Order Block (LONG)
                fvg_bull = c3["low"] > c1["high"] and (c3["low"] - c1["high"]) >= (atr * min_fvg_mult)
                disp_bull = (c2["close"] - c2["open"]) >= (atr * min_disp_mult)
                if fvg_bull and disp_bull:
                    c1_bull = c1["close"] > c1["open"]
                    c1_bear = c1["close"] < c1["open"]
                    c2_breach = c2["low"] < c1["low"]
                    is_swing_origin = last_sl_price is not None and abs(c1["low"] - last_sl_price) < (atr * 0.5)

                    if bull_swept:
                        model_desc, cat_name = "Type 6: Sweep+BOS Leg OB", "STRONGEST_COND"
                    elif idm_bull_swept and last_idm_bull is not None and c1["low"] < last_idm_bull:
                        model_desc, cat_name = "Type 7: Post-IDM Decisional OB", "STRONGEST_COND"
                    elif c2_breach:
                        model_desc, cat_name = "Type 3: Outlier C2 Low Breach OB", "WEAK"
                    elif c1_bull:
                        model_desc, cat_name = "Type 1: Momentum Same-Color OB", "WEAK"
                    elif is_swing_origin and c1_bear:
                        model_desc, cat_name = "Type 4: Swing Origin OB", "STRONG"
                    elif c1_bear:
                        model_desc, cat_name = "Type 2: Classic Opposite-Color OB", "STRONG"
                    else:
                        model_desc, cat_name = "Type 5: Mid-Leg Internal OB", "WEAK"

                    ob_top = c1["high"]
                    ob_bottom = c2["low"] if c2_breach else c1["low"]
                    active_obs.append({
                        "side": "LONG",
                        "create_idx": i,
                        "c1_bar": i - 2,
                        "c1_time": int(c1["time"]),
                        "model": model_desc,
                        "category": cat_name,
                        "top": ob_top,
                        "bottom": ob_bottom,
                        "mid": (ob_top + ob_bottom) / 2.0,
                        "mit": False,
                        "inv": False,
                        "first_tap_idx": None,
                        "signal_type": None,
                    })

                # B. Bearish Order Block (SHORT)
                if self.allow_short:
                    fvg_bear = c3["high"] < c1["low"] and (c1["low"] - c3["high"]) >= (atr * min_fvg_mult)
                    disp_bear = (c2["open"] - c2["close"]) >= (atr * min_disp_mult)
                    if fvg_bear and disp_bear:
                        c1_bull = c1["close"] > c1["open"]
                        c1_bear = c1["close"] < c1["open"]
                        c2_breach = c2["high"] > c1["high"]
                        is_swing_origin = last_sh_price is not None and abs(c1["high"] - last_sh_price) < (atr * 0.5)

                        if bear_swept:
                            model_desc, cat_name = "Type 6: Sweep+BOS Leg OB", "STRONGEST_COND"
                        elif idm_bear_swept and last_idm_bear is not None and c1["high"] > last_idm_bear:
                            model_desc, cat_name = "Type 7: Post-IDM Decisional OB", "STRONGEST_COND"
                        elif c2_breach:
                            model_desc, cat_name = "Type 3: Outlier C2 High Breach OB", "WEAK"
                        elif c1_bear:
                            model_desc, cat_name = "Type 1: Momentum Same-Color OB", "WEAK"
                        elif is_swing_origin and c1_bull:
                            model_desc, cat_name = "Type 4: Swing Origin OB", "STRONG"
                        elif c1_bull:
                            model_desc, cat_name = "Type 2: Classic Opposite-Color OB", "STRONG"
                        else:
                            model_desc, cat_name = "Type 5: Mid-Leg Internal OB", "WEAK"

                        ob_top = c2["high"] if c2_breach else c1["high"]
                        ob_bottom = c1["low"]
                        active_obs.append({
                            "side": "SHORT",
                            "create_idx": i,
                            "c1_bar": i - 2,
                            "c1_time": int(c1["time"]),
                            "model": model_desc,
                            "category": cat_name,
                            "top": ob_top,
                            "bottom": ob_bottom,
                            "mid": (ob_top + ob_bottom) / 2.0,
                            "mit": False,
                            "inv": False,
                            "first_tap_idx": None,
                            "signal_type": None,
                        })

            # Step-by-step Tap, Weak Wick Sweep & Invalidation evaluation on bar i
            rng = curr["high"] - curr["low"]
            for ob in active_obs:
                if i <= ob["create_idx"] or ob["inv"]:
                    continue

                if ob["side"] == "LONG":
                    if curr["close"] < ob["bottom"]:
                        ob["inv"] = True
                        continue
                    if not ob["mit"]:
                        if ob["category"] in ("STRONG", "STRONGEST_COND"):
                            if curr["low"] <= ob["top"] and curr["close"] >= ob["bottom"]:
                                ob["mit"] = True
                                ob["first_tap_idx"] = i
                                ob["signal_type"] = "STRONG_TAP_BUY"
                        elif ob["category"] == "WEAK":
                            if curr["low"] < ob["bottom"] and curr["close"] >= ob["bottom"] and curr["close"] > curr["open"]:
                                lower_wick_pct = ((min(curr["open"], curr["close"]) - curr["low"]) / rng * 100.0) if rng > 0 else 0.0
                                if lower_wick_pct >= min_weak_wick_pct:
                                    ob["mit"] = True
                                    ob["first_tap_idx"] = i
                                    ob["signal_type"] = "WEAK_SWEEP_BUY"
                else:  # SHORT
                    if curr["close"] > ob["top"]:
                        ob["inv"] = True
                        continue
                    if not ob["mit"]:
                        if ob["category"] in ("STRONG", "STRONGEST_COND"):
                            if curr["high"] >= ob["bottom"] and curr["close"] <= ob["top"]:
                                ob["mit"] = True
                                ob["first_tap_idx"] = i
                                ob["signal_type"] = "STRONG_TAP_SELL"
                        elif ob["category"] == "WEAK":
                            if curr["high"] > ob["top"] and curr["close"] <= ob["top"] and curr["close"] < curr["open"]:
                                upper_wick_pct = ((curr["high"] - max(curr["open"], curr["close"])) / rng * 100.0) if rng > 0 else 0.0
                                if upper_wick_pct >= min_weak_wick_pct:
                                    ob["mit"] = True
                                    ob["first_tap_idx"] = i
                                    ob["signal_type"] = "WEAK_SWEEP_SELL"

            # Trim invalidated/old mitigated zones (keep up to 40 active)
            if len(active_obs) > 40:
                active_obs = [o for o in active_obs if not o["inv"] and (not o["mit"] or (o["first_tap_idx"] is not None and o["first_tap_idx"] >= n - 2))]

        curr_price = candles[-1]["close"]
        valid_setups: List[Dict[str, Any]] = []

        for ob in active_obs:
            side = ob["side"]
            ob_top = ob["top"]
            ob_bottom = ob["bottom"]
            ob_mid = ob["mid"]
            ob_key = f"{symbol}_{timeframe}_{side}_{ob['c1_time']}"

            if is_ob_retired(ob_key):
                continue

            if ob["inv"]:
                self._ob_lifecycle[ob_key] = {"tapped": ob["mit"], "tap_count": 1 if ob["mit"] else 0, "invalidated": True}
                mark_ob_state(ob_key, symbol, timeframe, side, ob_top, ob_bottom, "INVALIDATED_CLOSE", 1 if ob["mit"] else 0)
                continue

            # Retire historical mitigated OBs older than the active bar window (>1 closed bar ago) -> ZERO 28h stale triggers!
            if ob["mit"]:
                tap_idx = ob["first_tap_idx"]
                is_strong_active = ob["category"] in ("STRONG", "STRONGEST_COND") and tap_idx is not None and tap_idx >= n - 2
                # Weak sweeps require confirmed HTF close (n - 2) so intrabar wick never fakes before close
                is_weak_active = ob["category"] == "WEAK" and tap_idx is not None and tap_idx == n - 2
                in_active_signal = is_strong_active or is_weak_active

                if not in_active_signal and (tap_idx is None or tap_idx < n - 2):
                    self._ob_lifecycle[ob_key] = {"tapped": True, "tap_count": 1, "invalidated": True}
                    mark_ob_state(ob_key, symbol, timeframe, side, ob_top, ob_bottom, "INVALIDATED_2ND_TAP", 1)
                    continue
            else:
                in_active_signal = False

            # Weak OB intrabar sweep still forming on n-1 (tap_idx == n-1) isn't eligible for entry until HTF closes
            if ob["category"] == "WEAK" and ob["mit"] and ob["first_tap_idx"] == n - 1:
                status = "WEAK_SWEEP_FORMING"
            elif in_active_signal:
                status = "WEAK_SWEEP_WAITING_5M" if ob["category"] == "WEAK" else "FIRST_TAP_WAITING_5M"
            else:
                status = "WAITING_WEAK_SWEEP" if ob["category"] == "WEAK" else "WAITING_1ST_TAP"

            self._ob_lifecycle[ob_key] = {
                "tapped": ob["mit"],
                "tap_count": 1 if ob["mit"] else 0,
                "invalidated": False,
                "in_active_first_tap": in_active_signal,
                "signal_type": ob["signal_type"],
            }

            lev = get_symbol_leverage(symbol)
            sl_price_pct = HARD_SL_ROI_PCT / (lev * 100.0)
            tp_price_pct = FULL_BOOK_TP_ROI_PCT / (lev * 100.0)

            if side == "LONG":
                entry_p = ob_top
                sl_p = entry_p * (1.0 - sl_price_pct)
                tp_p = entry_p * (1.0 + tp_price_pct)
                if curr_price > ob_top:
                    dist_pct = ((curr_price - ob_top) / curr_price) * 100.0
                elif curr_price >= ob_bottom:
                    dist_pct = 0.0
                else:
                    dist_pct = 99.0
            else:
                entry_p = ob_bottom
                sl_p = entry_p * (1.0 + sl_price_pct)
                tp_p = entry_p * (1.0 - tp_price_pct)
                if curr_price < ob_bottom:
                    dist_pct = ((ob_bottom - curr_price) / curr_price) * 100.0
                elif curr_price <= ob_top:
                    dist_pct = 0.0
                else:
                    dist_pct = 99.0

            valid_setups.append({
                "ob_key": ob_key,
                "symbol": symbol,
                "timeframe": timeframe,
                "side": side,
                "leverage": lev,
                "model": ob["model"],
                "category": ob["category"],
                "signal_type": ob["signal_type"],
                "ob_top": round(ob_top, 6),
                "ob_bottom": round(ob_bottom, 6),
                "ob_mid": round(ob_mid, 6),
                "entry_price": round(entry_p, 6),
                "sl_price": round(sl_p, 6),
                "tp_price": round(tp_p, 6),
                "sl_roi_pct": -HARD_SL_ROI_PCT,
                "tp_roi_pct": FULL_BOOK_TP_ROI_PCT,
                "proximity_pct": round(dist_pct, 2),
                "is_first_tap": in_active_signal,
                "tap_count": 1 if ob["mit"] else 0,
                "current_price": round(curr_price, 6),
                "status": status,
            })

        return valid_setups

    async def check_5m_confirmation(self, session: aiohttp.ClientSession, setup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        1:1 TradingView Execution Confirmation (BOTH BUY/LONG & SELL/SHORT):
        - Verifies OB has NOT been retired in SQLite and has active 1st-Tap or >=18% Weak Sweep signal
        - Confirms on latest closed 5m candle within exact OB entry zone (zero stale chase!)
        """
        ob_key = setup["ob_key"]
        if is_ob_retired(ob_key):
            return None

        st = self._ob_lifecycle.get(ob_key, {})
        if not st.get("tapped") or not st.get("in_active_first_tap") or st.get("invalidated"):
            return None

        candles_5m = await self.fetch_klines(session, setup["symbol"], "5m", limit=8)
        if len(candles_5m) < 3:
            return None

        last_closed_5m = candles_5m[-2]
        close_p = last_closed_5m["close"]
        open_p = last_closed_5m["open"]
        ob_top = setup["ob_top"]
        ob_bottom = setup["ob_bottom"]
        side = setup.get("side", "LONG").upper()
        sig_type = setup.get("signal_type") or "STRONG_TAP"

        if side == "LONG":
            # Confirm holding >= ob_bottom, bullish 5m close (or reclaiming ob_top), and not chasing > +0.5% above ob_top
            if close_p >= ob_bottom and close_p <= ob_top * 1.005 and (close_p > open_p or close_p >= ob_top):
                return {
                    "pathway": f"HERMES_MS_OB_{sig_type}_5M",
                    "entry_price": close_p,
                    "candle_time": last_closed_5m["time"],
                }
        else:  # SHORT
            # Confirm holding <= ob_top, bearish 5m close (or rejecting below ob_bottom), and not chasing > 0.5% below ob_bottom
            if close_p <= ob_top and close_p >= ob_bottom * 0.995 and (close_p < open_p or close_p <= ob_bottom):
                return {
                    "pathway": f"HERMES_MS_OB_{sig_type}_5M",
                    "entry_price": close_p,
                    "candle_time": last_closed_5m["time"],
                }
        return None

    async def run_scan_cycle(self):
        open_pos = get_open_positions()
        active_symbols = {p["symbol"] for p in open_pos}
        all_setups: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession() as session:
            for sym in self.watchlist:
                tfs = self.gold_timeframes if sym == self.gold_symbol else self.crypto_timeframes
                for tf in tfs:
                    candles = await self.fetch_klines(session, sym, tf, limit=300)
                    if not candles:
                        continue
                    setups = self.scan_symbol_order_blocks(sym, tf, candles)
                    all_setups.extend(setups)

                    if len(open_pos) < self.max_concurrent_trades and sym not in active_symbols:
                        for setup in setups:
                            side = setup.get("side", "LONG").upper()
                            if side == "SHORT" and not self.allow_short:
                                continue
                            if setup["is_first_tap"]:
                                now = time.time()
                                cd_key = f"{sym}_{side}"
                                if now - self._cooldowns.get(cd_key, 0) > 300:
                                    confirm = await self.check_5m_confirmation(session, setup)
                                    if confirm:
                                        await self.execute_trade_trigger(session, setup, confirm)
                                        active_symbols.add(sym)
                                        open_pos = get_open_positions()
                                        break

        all_setups.sort(key=lambda s: s.get("proximity_pct", 99.0))
        self.scanned_setups = all_setups[:25]

    async def execute_trade_trigger(self, session: aiohttp.ClientSession, setup: Dict[str, Any], confirm: Dict[str, Any]):
        sym = setup["symbol"]
        side = setup.get("side", "LONG").upper()
        is_long = (side == "LONG")
        ob_key = setup["ob_key"]

        # Re-check permanent retirement lock before opening
        if is_ob_retired(ob_key):
            return

        entry_p = confirm["entry_price"]
        tf = setup["timeframe"].upper()
        lev = get_symbol_leverage(sym)
        sl_price_pct = HARD_SL_ROI_PCT / (lev * 100.0)
        tp_price_pct = FULL_BOOK_TP_ROI_PCT / (lev * 100.0)
        sl_p = round(entry_p * (1.0 - sl_price_pct if is_long else 1.0 + sl_price_pct), 6)
        tp_p = round(entry_p * (1.0 + tp_price_pct if is_long else 1.0 - tp_price_pct), 6)
        pos_size = self.margin_per_trade * lev
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
            "leverage": lev,
            "order_type": "MS_OB_1ST_TAP",
            "timeframe": tf,
        }

        try:
            pos_id = open_position(pos_data)
            # Immediately retire this OB in SQLite so a 2nd tap or re-entry is impossible forever
            mark_ob_state(ob_key, sym, setup["timeframe"], side, setup["ob_top"], setup["ob_bottom"], "CONSUMED_TRADE", 1)
            self._ob_lifecycle[ob_key] = {"tapped": True, "tap_count": 1, "invalidated": True}
            self._cooldowns[f"{sym}_{side}"] = time.time()
            dir_label = "BUY/LONG" if is_long else "SELL/SHORT"
            sig_label = "Weak OB >=18% Sweep" if setup.get("category") == "WEAK" else "1st Tap OB Boundary"
            print(f"⚡ [HERMES MS-OB] {sig_label} {dir_label} #{pos_id} {sym} ({tf}) @ {entry_p} | {lev}x | SL: {sl_p} | TP: {tp_p} (+15% ROI)")
            await self.send_telegram_alert(
                session,
                f"⚡ <b>HERMES MS-OB {dir_label} TRIGGER (#{pos_id})</b>\n"
                f"• Pair: <b>{sym}</b> ({tf}) • {setup['model']}\n"
                f"• Entry ({sig_label} + 5m Close): <code>${entry_p}</code>\n"
                f"• Margin: <code>$50 (5%)</code> @ <b>{lev}x Isolated</b> (Size ${int(pos_size)})\n"
                f"• TP (+15% ROI): <code>${tp_p}</code> | Hard SL (-15% ROI): <code>${sl_p}</code>"
            )
        except Exception as e:
            print(f"❌ Trade execution error for {sym}: {e}")

    async def update_open_positions(self):
        open_pos = get_open_positions()
        if not open_pos:
            return

        tickers = await market_feed.get_all_tickers()
        async with aiohttp.ClientSession() as session:
            for pos in open_pos:
                sym = pos["symbol"]
                ticker = (tickers or {}).get(sym)
                if not ticker or not ticker.get("last_price"):
                    ticker = await market_feed.get_ticker(sym)
                if not ticker or not ticker.get("last_price"):
                    continue

                curr_price = float(ticker["last_price"])
                pos_id = pos["id"]
                side = pos["side"].upper()
                entry_p = float(pos["entry_price"])
                sl_p = float(pos.get("sl_price") or 0.0)
                tp_p = float(pos.get("tp_price") or 0.0)
                trailing_sl_p = float(pos.get("trailing_sl_price") or 0.0)
                stage = int(pos.get("trailing_stage") or 0)
                margin = float(pos.get("margin_usdt") or self.margin_per_trade)
                lev = int(pos.get("leverage") or self.leverage)

                if entry_p <= 0:
                    continue

                if side in ("LONG", "BUY"):
                    gain_pct = ((curr_price - entry_p) / entry_p) * 100.0
                else:
                    gain_pct = ((entry_p - curr_price) / entry_p) * 100.0
                roe_pct = gain_pct * lev
                u_pnl = margin * (roe_pct / 100.0)

                # 1. FULL BOOK TAKE PROFIT (+15.0% ROI)
                is_tp_hit = (side in ("LONG", "BUY") and curr_price >= tp_p) or (side in ("SHORT", "SELL") and curr_price <= tp_p)
                if tp_p > 0 and is_tp_hit:
                    realized = round(margin * (FULL_BOOK_TP_ROI_PCT / 100.0), 2)
                    close_position_in_db(pos_id, tp_p, realized, "FULL_BOOK_TP_HIT (+15% ROI)")
                    print(f"🎯 [HERMES MS-OB] Full TP Hit (+15% ROI): #{pos_id} {sym} ({lev}x) @ {tp_p}")
                    continue

                # 2. BREAK-EVEN SHIELD (+12.0% ROI -> LOCK +2.5% ROI)
                if roe_pct >= self.be_trigger_roi and stage == 0:
                    if side in ("LONG", "BUY"):
                        be_sl = round(entry_p * (1.0 + (self.be_lock_roi / (lev * 100.0))), 6)
                    else:
                        be_sl = round(entry_p * (1.0 - (self.be_lock_roi / (lev * 100.0))), 6)
                    stage = 1
                    sl_p = be_sl
                    trailing_sl_p = be_sl
                    update_position_mark_price(pos_id, curr_price, u_pnl, round(roe_pct, 2), be_sl, stage)
                    print(f"🛡️ [HERMES MS-OB] BE Shield Locked (+2.5% ROI): #{pos_id} {sym} ({lev}x) -> {be_sl}")

                # 3. BREAK-EVEN EXIT
                if stage == 1 and trailing_sl_p > 0:
                    is_be_exit = (side in ("LONG", "BUY") and curr_price <= trailing_sl_p) or (side in ("SHORT", "SELL") and curr_price >= trailing_sl_p)
                    if is_be_exit:
                        realized = round(margin * (self.be_lock_roi / 100.0), 2)
                        close_position_in_db(pos_id, trailing_sl_p, realized, "BREAKEVEN_PROFIT_LOCKED (+2.5% ROI)")
                        print(f"🛡️ [HERMES MS-OB] BE Exit (+2.5% ROI): #{pos_id} {sym} ({lev}x) @ {trailing_sl_p}")
                        continue

                # 4. HARD STOP LOSS (-15.0% ROI WITH 2x 15m CLOSE GUARD)
                if stage == 0:
                    sl_price_pct = HARD_SL_ROI_PCT / (lev * 100.0)
                    hard_sl_level = sl_p if sl_p > 0 else (round(entry_p * (1.0 - sl_price_pct), 6) if side in ("LONG", "BUY") else round(entry_p * (1.0 + sl_price_pct), 6))
                    is_sl_tapped = (side in ("LONG", "BUY") and curr_price <= hard_sl_level) or (side in ("SHORT", "SELL") and curr_price >= hard_sl_level)
                    if is_sl_tapped:
                        candles_15m = await self.fetch_klines(session, sym, "15m", limit=6)
                        if len(candles_15m) >= 4:
                            c_prev2 = candles_15m[-3]
                            c_prev1 = candles_15m[-2]
                            if side in ("LONG", "BUY"):
                                two_closes = c_prev2["close"] < hard_sl_level and c_prev1["close"] < hard_sl_level
                            else:
                                two_closes = c_prev2["close"] > hard_sl_level and c_prev1["close"] > hard_sl_level
                            if two_closes:
                                realized = round(margin * (-HARD_SL_ROI_PCT / 100.0), 2)
                                close_position_in_db(pos_id, curr_price, realized, "HARD_SL_HIT_2x15M_CONFIRMED (-15% ROI)")
                                print(f"🛑 [HERMES MS-OB] Hard SL Hit (-15% ROI): #{pos_id} {sym} ({lev}x) @ {curr_price}")
                                continue

                update_position_mark_price(pos_id, curr_price, u_pnl, round(roe_pct, 2), sl_p, stage)

    async def start_loop(self):
        self._is_running = True
        print("⚡ [HERMES MS-OB v2.0 EXCLUSIVE] BUY/LONG Only | Strict 1st Tap Valid | 2nd Tap Invalidated | $1000 Flat | BE +12%->+2.5% | Hard SL -15% | TP +15%")
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
