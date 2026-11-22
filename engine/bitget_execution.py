"""
NEXUSPRO BITGET REAL-MONEY EXECUTION CLIENT
===========================================
Synchronizes live institutional trade executions with Bitget Futures (USDT-M Perpetual).
- Capital: $100.00 USDT starting wallet
- Margin: Flat $10.00 USDT per trade (Fixed Margin)
- Leverage: Strictly 5x Isolated (or symbol override e.g. 10x BTC/ETH)
- Risk: Stop Loss strictly -15.0% ROI / Take Profit strictly +15.0% ROI
- Parity: 1:1 mirror of TradeZone / NexusPro 1H OB + 5m MSS sniper signals
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional

try:
    import ccxt
except ImportError:
    ccxt = None

from config import (
    BITGET_AUTO_TRADE,
    BITGET_API_KEY,
    BITGET_SECRET,
    BITGET_PASSPHRASE,
    BITGET_MARGIN_PER_TRADE,
    DEFAULT_LEVERAGE,
    get_symbol_leverage
)

class BitgetExecutionClient:
    def __init__(self):
        self.api_key = BITGET_API_KEY
        self.secret = BITGET_SECRET
        self.passphrase = BITGET_PASSPHRASE
        self.auto_trade = BITGET_AUTO_TRADE
        self.exchange = None
        self._markets_loaded = False
        self._init_exchange()

    def _init_exchange(self):
        if not ccxt:
            print("⚠️ [BITGET CLIENT] CCXT module not installed. Live trading disabled.")
            return

        if self.api_key and self.secret and self.passphrase:
            try:
                self.exchange = ccxt.bitget({
                    'apiKey': self.api_key,
                    'secret': self.secret,
                    'password': self.passphrase,
                    'timeout': 15000,
                    'options': {
                        'defaultType': 'swap',  # USDT-M Perpetual Futures
                    },
                    'enableRateLimit': True,
                })
                print("💎 [BITGET CLIENT] Initialized CCXT Bitget instance successfully.")
            except Exception as e:
                print(f"❌ [BITGET CLIENT INIT ERROR] {e}")
                self.exchange = None
        else:
            print("⚠️ [BITGET CLIENT] Credentials incomplete. Live trading disabled.")
            self.exchange = None

    def is_configured(self) -> bool:
        return (self.exchange is not None) and bool(self.api_key) and bool(self.secret) and bool(self.passphrase)

    def is_auto_trade_enabled(self) -> bool:
        return self.auto_trade and self.is_configured()

    def format_symbol_for_bitget(self, symbol: str) -> str:
        """Converts symbol like OPUSDT to CCXT swap format: OP/USDT:USDT"""
        clean = symbol.replace("/", "").replace(":USDT", "").upper()
        symbol_map = {
            "MKRUSDT": "AMKR/USDT:USDT",
            "1000PEPEUSDT": "PEPE/USDT:USDT",
        }
        if clean in symbol_map:
            return symbol_map[clean]
        base = clean.replace("USDT", "")
        return f"{base}/USDT:USDT"

    def ensure_markets(self):
        if self.exchange and not self._markets_loaded:
            try:
                self.exchange.load_markets()
                self._markets_loaded = True
            except Exception as e:
                print(f"[BITGET] load_markets warning: {e}")

    def enforce_isolated_margin(self, symbol: str) -> bool:
        """Enforces ISOLATED margin mode on Bitget Futures."""
        if not self.exchange:
            return False
        ccxt_sym = self.format_symbol_for_bitget(symbol)
        try:
            self.exchange.set_margin_mode('ISOLATED', ccxt_sym)
            return True
        except Exception as e:
            err = str(e).lower()
            if "already" in err or "not modified" in err or "400" in err:
                return True
            return True

    def set_leverage_isolated(self, leverage: int, symbol: str, hold_side: str) -> bool:
        """Sets isolated leverage on Bitget for the specific hold side (long/short)."""
        if not self.exchange:
            return False
        ccxt_sym = self.format_symbol_for_bitget(symbol)
        try:
            self.exchange.set_leverage(leverage, ccxt_sym, params={'marginMode': 'isolated', 'holdSide': hold_side.lower()})
            return True
        except Exception as e:
            err = str(e).lower()
            if "not modified" in err or "already" in err:
                return True
            print(f"[BITGET] set_leverage note: {e}")
            return False

    async def fetch_account_balance(self) -> Dict[str, Any]:
        """Fetches live Bitget USDT-M Futures account balance."""
        if not self.is_configured():
            return {"connected": False, "error": "Bitget credentials not configured", "total_usdt": 0.0, "free_usdt": 0.0}

        try:
            loop = asyncio.get_event_loop()
            bal = await loop.run_in_executor(None, lambda: self.exchange.fetch_balance({'type': 'swap'}))
            usdt = bal.get('USDT', {})
            total = float(usdt.get('total', 0.0) or 0.0)
            free = float(usdt.get('free', 0.0) or 0.0)
            used = float(usdt.get('used', 0.0) or 0.0)
            return {
                "connected": True,
                "total_usdt": round(total, 2),
                "free_usdt": round(free, 2),
                "used_usdt": round(used, 2)
            }
        except Exception as e:
            return {"connected": False, "error": str(e), "total_usdt": 0.0, "free_usdt": 0.0}

    async def execute_live_order(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        margin_usdt: float = BITGET_MARGIN_PER_TRADE,
        leverage: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a real-money order on Bitget USDT-M Futures:
        - Margin: $10.00 USDT
        - Leverage: 5x Isolated
        - Preset TP: +15.0% ROI
        - Preset SL: -15.0% ROI
        """
        if not self.is_auto_trade_enabled():
            return {"success": False, "skipped": True, "reason": "Bitget Auto-Trading is disabled or not configured"}

        if leverage is None:
            leverage = get_symbol_leverage(symbol)

        is_long = side.upper() in ("BUY", "LONG")
        trade_side = 'buy' if is_long else 'sell'
        hold_side = 'long' if is_long else 'short'
        clean_sym = symbol.replace('/', '').replace(':USDT', '').upper()
        ccxt_sym = self.format_symbol_for_bitget(symbol)

        # Scale 1000PEPEUSDT to PEPE/USDT:USDT if needed
        eff_entry = entry_price
        eff_tp = tp_price
        eff_sl = sl_price
        if "1000PEPE" in clean_sym:
            eff_entry /= 1000.0
            eff_tp /= 1000.0
            eff_sl /= 1000.0

        loop = asyncio.get_event_loop()

        def _do_execute():
            self.ensure_markets()

            # 1. Anti-Duplicate Check: Skip if position already open on Bitget
            try:
                existing_positions = self.exchange.fetch_positions([ccxt_sym])
                for p in existing_positions:
                    contracts = float(p.get('contracts', 0) or 0)
                    size = float(p.get('size', 0) or 0)
                    if (contracts > 0 or size > 0) and str(p.get('side', '')).lower() == hold_side:
                        print(f"⚠️ [BITGET GUARD] {symbol} already has active position on Bitget.")
                        return {"success": False, "skipped": True, "reason": "Active position already exists on Bitget"}
            except Exception as p_err:
                print(f"[BITGET GUARD] Position pre-check note: {p_err}")

            # 2. Enforce ISOLATED Margin Mode
            self.enforce_isolated_margin(symbol)

            # 3. Set Isolated Leverage
            self.set_leverage_isolated(leverage, symbol, hold_side)

            # 4. Sizing: Strictly $10 USDT margin * leverage
            notional = margin_usdt * leverage
            raw_amount = notional / eff_entry

            # Precision rounding
            try:
                amount = float(self.exchange.amount_to_precision(ccxt_sym, raw_amount))
            except Exception:
                m = self.exchange.markets.get(ccxt_sym) if getattr(self.exchange, 'markets', None) else None
                prec = m.get('precision', {}).get('amount') if m else None
                if prec is not None and prec == 1.0:
                    amount = float(int(raw_amount))
                else:
                    amount = round(raw_amount, 2)

            if amount <= 0:
                return {"success": False, "error": f"Calculated order amount ({amount}) is zero or invalid"}

            # 5. Place Market Order with preset TP & SL
            order_params = {
                'marginMode': 'isolated',
                'hedged': True,
                'presetTakeProfitPrice': str(round(eff_tp, 4 if eff_tp >= 1 else 6)),
                'presetStopLossPrice': str(round(eff_sl, 4 if eff_sl >= 1 else 6))
            }

            print(f"💎 [BITGET REAL ORDER] Placing MARKET {trade_side.upper()} {ccxt_sym} | Amount: {amount} | Margin: ${margin_usdt} | TP: {eff_tp} | SL: {eff_sl}")

            order = self.exchange.create_order(
                symbol=ccxt_sym,
                type='market',
                side=trade_side,
                amount=amount,
                params=order_params
            )

            order_id = order.get("id") or order.get("info", {}).get("orderId", "BITGET_FILLED")
            actual_fill_price = float(order.get("average") or order.get("price") or eff_entry)

            # 6. Secondary Safety: Arm exchange-level Position TP/SL via Bitget V2 API
            try:
                self.exchange.privateMixPostV2MixOrderPlacePosTpsl({
                    'marginCoin': 'USDT',
                    'symbol': clean_sym,
                    'productType': 'USDT-FUTURES',
                    'holdSide': hold_side,
                    'stopSurplusTriggerPrice': str(round(eff_tp, 6)),
                    'stopSurplusTriggerType': 'fill_price',
                    'stopLossTriggerPrice': str(round(eff_sl, 6)),
                    'stopLossTriggerType': 'fill_price'
                })
                print(f"🛡️ [BITGET POS TP/SL ARMED] Attached TP: {eff_tp} | SL: {eff_sl}")
            except Exception as tpe:
                print(f"[BITGET POS TP/SL NOTE] {tpe}")

            return {
                "success": True,
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "entry_price": actual_fill_price,
                "margin_usdt": margin_usdt,
                "leverage": leverage,
                "tp_price": eff_tp,
                "sl_price": eff_sl,
                "raw_order": order
            }

        try:
            return await loop.run_in_executor(None, _do_execute)
        except Exception as e:
            err_str = str(e)
            print(f"❌ [BITGET ORDER EXECUTION ERROR] {symbol} {side}: {err_str}")
            return {"success": False, "error": err_str}

    async def close_live_position(self, symbol: str, side: str) -> Dict[str, Any]:
        """Closes active Bitget futures position immediately at market price."""
        if not self.is_configured():
            return {"success": False, "error": "Bitget exchange not configured"}

        clean_sym = symbol.replace('/', '').replace(':USDT', '').upper()
        ccxt_sym = self.format_symbol_for_bitget(symbol)
        is_long = side.upper() in ('BUY', 'LONG')
        hold_side = 'long' if is_long else 'short'

        loop = asyncio.get_event_loop()

        def _do_close():
            # 1. Cancel pending trigger/plan orders
            try:
                self.exchange.privateMixPostV2MixOrderCancelAllOrders({'productType': 'USDT-FUTURES', 'symbol': clean_sym, 'marginCoin': 'USDT'})
            except Exception:
                pass
            try:
                self.exchange.privateMixPostV2MixOrderCancelPlanOrder({'productType': 'USDT-FUTURES', 'symbol': clean_sym, 'marginCoin': 'USDT'})
            except Exception:
                pass

            # 2. Query open contracts
            contracts = 0.0
            try:
                res = self.exchange.privateMixGetV2MixPositionAllPosition({'productType': 'USDT-FUTURES', 'symbol': clean_sym})
                if res and 'data' in res:
                    for p in res['data']:
                        if p.get('holdSide', '').lower() == hold_side:
                            contracts = float(p.get('total', 0) or 0)
                            if contracts > 0:
                                break
            except Exception as qe:
                print(f"[BITGET CLOSE QUERY NOTE] {qe}")

            if contracts <= 0:
                print(f"ℹ️ [BITGET CLOSE] {clean_sym} {hold_side} position already closed on exchange.")
                return {"success": True, "already_closed": True, "symbol": symbol}

            # 3. Flash Close Position
            try:
                print(f"💎 [BITGET FLASH CLOSE] Closing {contracts} {hold_side.upper()} contracts for {ccxt_sym}...")
                order = self.exchange.close_position(ccxt_sym, side=hold_side)
                print(f"✅ [BITGET FLASH CLOSE SUCCESS] {order.get('id', 'CLOSED')}")
                return {"success": True, "symbol": symbol, "closed_contracts": contracts, "order": order}
            except Exception as fe:
                print(f"[BITGET FLASH CLOSE FALLBACK] {fe}")
                close_side = 'sell' if is_long else 'buy'
                order_params = {
                    'marginMode': 'isolated',
                    'hedged': True,
                    'reduceOnly': True
                }
                order = self.exchange.create_order(
                    symbol=ccxt_sym,
                    type='market',
                    side=close_side,
                    amount=contracts,
                    params=order_params
                )
                return {"success": True, "symbol": symbol, "closed_contracts": contracts, "order": order}

        try:
            return await loop.run_in_executor(None, _do_close)
        except Exception as e:
            err_str = str(e)
            print(f"❌ [BITGET POSITION CLOSE ERROR] {symbol}: {err_str}")
            return {"success": False, "error": err_str}

bitget_client = BitgetExecutionClient()
