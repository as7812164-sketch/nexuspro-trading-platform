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
    PAIR_MAPPING,
    HARD_SL_PRICE_PCT,
    FULL_BOOK_TP_PRICE_PCT,
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
        self.allow_short = ALLOW_SHORT_ENTRIES  # False -> Strictly BUY / LONG only

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
        1:1 parity with Hermes MS-OB v2.0 GOLDEN Chart Indicator:
        - Rolling 14-period True Range ATR
        - 7-Model Order Block classification
        - Strict 1st-Tap Valid Only (2nd Tap or Body Close below OB permanently invalidates & persists to SQLite)
        - Strictly BUY / LONG Order Blocks when allow_short=False
        """
        n = len(candles)
        if n < 24:
            return []

        # 1. Rolling 14-period ATR
        tr_list = []
        for i in range(n):
            if i == 0:
                tr = candles[0]["high"] - candles[0]["low"]
            else:
                hl = candles[i]["high"] - candles[i]["low"]
                hc = abs(candles[i]["high"] - candles[i - 1]["close"])
                lc = abs(candles[i]["low"] - candles[i - 1]["close"])
                tr = max(hl, hc, lc)
            tr_list.append(tr)

        atr_arr = []
        tr_sum = 0.0
        for i in range(n):
            tr_sum += tr_list[i]
            if i >= 14:
                tr_sum -= tr_list[i - 14]
                atr_arr.append(tr_sum / 14.0)
            else:
                atr_arr.append(tr_sum / float(i + 1))

        swing_len = 3
        last_sh_price = None
        last_sl_price = None
        last_idm_bull = None
        bull_swept = False
        idm_bull_swept = False
        bull_sweep_bar = -999

        scan_lookback = min(n - 4, 100)
        start_idx = max(swing_len * 2, n - scan_lookback)
        last_ob_index = -999

        curr_price = candles[-1]["close"]
        valid_setups: List[Dict[str, Any]] = []

        for i in range(start_idx, n - 1):
            atr = atr_arr[i]
            if atr <= 0:
                continue

            # Swing pivots
            p_idx = i - swing_len
            if p_idx >= swing_len:
                is_sh = True
                is_sl = True
                for w in range(1, swing_len + 1):
                    if candles[p_idx - w]["high"] >= candles[p_idx]["high"] or candles[p_idx + w]["high"] >= candles[p_idx]["high"]:
                        is_sh = False
                    if candles[p_idx - w]["low"] <= candles[p_idx]["low"] or candles[p_idx + w]["low"] <= candles[p_idx]["low"]:
                        is_sl = False
                if is_sh:
                    last_sh_price = candles[p_idx]["high"]
                if is_sl:
                    last_sl_price = candles[p_idx]["low"]

            curr = candles[i]
            prev = candles[i - 1]

            if last_sl_price is not None and curr["low"] < last_sl_price and curr["close"] > last_sl_price:
                bull_swept = True
                bull_sweep_bar = i
            if (i - bull_sweep_bar) > 35:
                bull_swept = False

            if last_sh_price is not None and curr["close"] > last_sh_price and prev["close"] <= last_sh_price:
                lowest_low = min(candles[k]["low"] for k in range(max(0, i - 15), i + 1))
                last_idm_bull = lowest_low
                idm_bull_swept = False

            if last_idm_bull is not None and curr["low"] < last_idm_bull:
                idm_bull_swept = True

            if (i - last_ob_index) < 8:
                continue

            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]

            # Bullish Order Block (BUY / LONG)
            fvg_bull = c3["low"] > c1["high"] and (c3["low"] - c1["high"]) >= (atr * 0.12)
            disp_bull = (c2["close"] - c2["open"]) >= (atr * 0.70)

            if not (fvg_bull and disp_bull):
                continue

            c1_bull = c1["close"] > c1["open"]
            c1_bear = c1["close"] < c1["open"]
            c2_breach = c2["low"] < c1["low"]
            is_swing_origin = last_sl_price is not None and abs(c1["low"] - last_sl_price) < (atr * 0.5)

            if bull_swept:
                model_desc = "Type 6: Sweep+BOS Leg OB"
                cat_name = "STRONGEST_COND"
            elif idm_bull_swept and last_idm_bull is not None and c1["low"] < last_idm_bull:
                model_desc = "Type 7: Post-IDM Decisional OB"
                cat_name = "STRONGEST_COND"
            elif c2_breach:
                model_desc = "Type 3: Outlier C2 Low Breach OB"
                cat_name = "WEAK"
            elif c1_bull:
                model_desc = "Type 1: Momentum Same-Color OB"
                cat_name = "WEAK"
            elif is_swing_origin and c1_bear:
                model_desc = "Type 4: Swing Origin OB"
                cat_name = "STRONG"
            elif c1_bear:
                model_desc = "Type 2: Classic Opposite-Color OB"
                cat_name = "STRONG"
            else:
                model_desc = "Type 5: Mid-Leg Internal OB"
                cat_name = "WEAK"

            ob_top = c1["high"]
            ob_bottom = min(c1["low"], c2["low"]) if c2_breach else c1["low"]
            if ob_top - ob_bottom < atr * 0.20:
                ob_bottom = ob_top - (atr * 0.35)
            ob_mid = (ob_top + ob_bottom) / 2.0

            ob_key = f"{symbol}_{timeframe}_LONG_{int(c1['time'])}"
            last_ob_index = i

            # Check permanent SQLite retirement first (CONSUMED_TRADE / INVALIDATED_2ND_TAP / INVALIDATED_CLOSE)
            if is_ob_retired(ob_key):
                continue

            # Strict 1st-Tap Valid Only & 2nd-Tap Permanent Invalidation Walk
            tap_count = 0
            left_after_tap1 = False
            is_invalidated = False
            invalid_reason = None
            first_tap_idx = None

            for k in range(i + 1, n):
                post_c = candles[k]
                if post_c["close"] < ob_bottom:
                    is_invalidated = True
                    invalid_reason = "INVALIDATED_CLOSE"
                    break

                if tap_count == 0:
                    if post_c["low"] <= ob_top:
                        tap_count = 1
                        first_tap_idx = k
                else:
                    if post_c["low"] > ob_top:
                        left_after_tap1 = True
                    elif left_after_tap1 and post_c["low"] <= ob_top:
                        tap_count = 2
                        is_invalidated = True
                        invalid_reason = "INVALIDATED_2ND_TAP"
                        break

            if is_invalidated and invalid_reason:
                self._ob_lifecycle[ob_key] = {"tapped": tap_count > 0, "tap_count": tap_count, "invalidated": True}
                mark_ob_state(ob_key, symbol, timeframe, "LONG", ob_top, ob_bottom, invalid_reason, tap_count)
                continue

            # If price ALREADY completed a historical tap & bounced out long ago (>2 bars ago),
            # waiting for next touch would be a 2nd tap -> mark invalidated permanently so ZERO 2nd tap entry can happen!
            in_active_first_tap = (tap_count == 1 and first_tap_idx is not None and (not left_after_tap1 or first_tap_idx >= n - 2))
            if tap_count == 1 and left_after_tap1 and first_tap_idx is not None and first_tap_idx < n - 2:
                self._ob_lifecycle[ob_key] = {"tapped": True, "tap_count": 1, "invalidated": True}
                mark_ob_state(ob_key, symbol, timeframe, "LONG", ob_top, ob_bottom, "INVALIDATED_2ND_TAP", 1)
                continue

            self._ob_lifecycle[ob_key] = {
                "tapped": tap_count == 1,
                "tap_count": tap_count,
                "invalidated": False,
                "in_active_first_tap": in_active_first_tap,
            }

            entry_p = ob_top
            sl_p = entry_p * (1.0 - self.hard_sl_price_pct)
            tp_p = entry_p * (1.0 + self.full_tp_price_pct)
            dist_pct = ((curr_price - entry_p) / curr_price) * 100.0 if curr_price > entry_p else 0.0

            status = "FIRST_TAP_WAITING_5M" if in_active_first_tap else "WAITING_1ST_TAP"
            valid_setups.append({
                "ob_key": ob_key,
                "symbol": symbol,
                "timeframe": timeframe,
                "side": "LONG",
                "model": model_desc,
                "category": cat_name,
                "ob_top": round(ob_top, 6),
                "ob_bottom": round(ob_bottom, 6),
                "ob_mid": round(ob_mid, 6),
                "entry_price": round(entry_p, 6),
                "sl_price": round(sl_p, 6),
                "tp_price": round(tp_p, 6),
                "sl_roi_pct": -15.0,
                "tp_roi_pct": 15.0,
                "proximity_pct": round(dist_pct, 2),
                "is_first_tap": in_active_first_tap,
                "tap_count": tap_count,
                "current_price": round(curr_price, 6),
                "status": status,
            })

        return valid_setups

    async def check_5m_confirmation(self, session: aiohttp.ClientSession, setup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Strict 1st-Tap Confirmation (BUY / LONG ONLY):
        - Verifies OB has NOT been retired or 2nd-tapped in SQLite
        - Waits for completed 5m candle body close > ob_top above ob_bottom
        """
        ob_key = setup["ob_key"]
        if is_ob_retired(ob_key):
            return None

        st = self._ob_lifecycle.get(ob_key, {})
        if not st.get("tapped") or st.get("invalidated") or st.get("tap_count", 0) >= 2:
            return None

        candles_5m = await self.fetch_klines(session, setup["symbol"], "5m", limit=8)
        if len(candles_5m) < 3:
            return None

        last_closed_5m = candles_5m[-2]
        close_p = last_closed_5m["close"]
        ob_top = setup["ob_top"]
        ob_bottom = setup["ob_bottom"]

        if close_p > ob_top and last_closed_5m["low"] >= ob_bottom * 0.995:
            return {
                "pathway": "HERMES_MS_OB_1ST_TAP_5M_BUY",
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
                    candles = await self.fetch_klines(session, sym, tf, limit=120)
                    if not candles:
                        continue
                    setups = self.scan_symbol_order_blocks(sym, tf, candles)
                    all_setups.extend(setups)

                    if len(open_pos) < self.max_concurrent_trades and sym not in active_symbols:
                        for setup in setups:
                            if setup["side"] == "LONG" and setup["is_first_tap"]:
                                now = time.time()
                                cd_key = f"{sym}_LONG"
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
        side = "LONG"
        ob_key = setup["ob_key"]

        # Re-check permanent 1st-tap lock before opening
        if is_ob_retired(ob_key):
            return

        entry_p = confirm["entry_price"]
        tf = setup["timeframe"].upper()
        sl_p = round(entry_p * (1.0 - self.hard_sl_price_pct), 6)
        tp_p = round(entry_p * (1.0 + self.full_tp_price_pct), 6)
        pos_size = self.margin_per_trade * self.leverage
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
            "order_type": "MS_OB_1ST_TAP",
            "timeframe": tf,
        }

        try:
            pos_id = open_position(pos_data)
            # Immediately retire this OB in SQLite so a 2nd tap or re-entry is impossible forever
            mark_ob_state(ob_key, sym, setup["timeframe"], side, setup["ob_top"], setup["ob_bottom"], "CONSUMED_TRADE", 1)
            self._ob_lifecycle[ob_key] = {"tapped": True, "tap_count": 1, "invalidated": True}
            self._cooldowns[f"{sym}_LONG"] = time.time()
            print(f"⚡ [HERMES MS-OB] 1st-Tap BUY/LONG #{pos_id} {sym} ({tf}) @ {entry_p} | SL: {sl_p} | TP: {tp_p} (+15% ROI)")
            await self.send_telegram_alert(
                session,
                f"⚡ <b>HERMES MS-OB BUY/LONG TRIGGER (#{pos_id})</b>\n"
                f"• Pair: <b>{sym}</b> ({tf}) • {setup['model']}\n"
                f"• Entry (1st Tap + 5m Close): <code>${entry_p}</code>\n"
                f"• Margin: <code>$50 (5%)</code> @ <b>5x Isolated</b> (Size $250)\n"
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
                    realized = round(margin * (self.full_tp_price_pct * lev), 2)
                    close_position_in_db(pos_id, tp_p, realized, "FULL_BOOK_TP_HIT (+15% ROI)")
                    print(f"🎯 [HERMES MS-OB] Full TP Hit (+15% ROI): #{pos_id} {sym} @ {tp_p}")
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
                    print(f"🛡️ [HERMES MS-OB] BE Shield Locked (+2.5% ROI): #{pos_id} {sym} -> {be_sl}")

                # 3. BREAK-EVEN EXIT
                if stage == 1 and trailing_sl_p > 0:
                    is_be_exit = (side in ("LONG", "BUY") and curr_price <= trailing_sl_p) or (side in ("SHORT", "SELL") and curr_price >= trailing_sl_p)
                    if is_be_exit:
                        realized = round(margin * (self.be_lock_roi / 100.0), 2)
                        close_position_in_db(pos_id, trailing_sl_p, realized, "BREAKEVEN_PROFIT_LOCKED (+2.5% ROI)")
                        print(f"🛡️ [HERMES MS-OB] BE Exit (+2.5% ROI): #{pos_id} {sym} @ {trailing_sl_p}")
                        continue

                # 4. HARD STOP LOSS (-15.0% ROI WITH 2x 15m CLOSE GUARD)
                if stage == 0:
                    hard_sl_level = round(entry_p * (1.0 - self.hard_sl_price_pct), 6) if side in ("LONG", "BUY") else round(entry_p * (1.0 + self.hard_sl_price_pct), 6)
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
                                realized = round(margin * (-self.hard_sl_price_pct * lev), 2)
                                close_position_in_db(pos_id, curr_price, realized, "HARD_SL_HIT_2x15M_CONFIRMED (-15% ROI)")
                                print(f"🛑 [HERMES MS-OB] Hard SL Hit (-15% ROI): #{pos_id} {sym} @ {curr_price}")
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
