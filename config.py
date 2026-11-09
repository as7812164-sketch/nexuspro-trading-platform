"""
NEXUSPRO PLATFORM CONFIGURATION
===============================
Brand: NexusPro (Institutional Futures Terminal)
Format: 100% Bitget Pro Layout and UI System
Engine: Hermes MS-OB 7-Model Order Block Execution Engine (v2.0 Golden Final)
- Entry: 5m Candle Close outside OB (Pathway 1: Respect Reversal | Pathway 2: 2h Sweep Reclaim)
- Break-Even: Trigger at +12.0% ROI -> Shift & Lock SL to +2.5% ROI (Guaranteed Profit + Fee Shield)
- Hard Stop Loss: -15.0% ROI (Requires 2 Consecutive 15m Candle Closes Beyond SL)
- Full Book Take Profit: +15.0% ROI (Instant Fill)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Branding
BRAND_NAME = "NexusPro"
BRAND_SUBTITLE = "INSTITUTIONAL FUTURES TERMINAL"
BRAND_ACCENT = "#00DFC0"  # Bitget Signature Teal/Cyan
THEME_BG = "#080B11"

# Standard Futures Trading ($1,000.00 Portfolio - Zero Compounding)
COMPOUNDING_ENABLED = False  # Compounding permanently disabled per user mandate
TOTAL_PORTFOLIO_CAPITAL = 1000.0  # USDT Total Portfolio
FIXED_MARGIN_PER_TRADE = 50.0     # Flat 5% of Whole Portfolio ($50 USDT per trade)
DEFAULT_LEVERAGE = 5              # 5x Isolated Leverage
POSITION_SIZE_USDT = 250.0        # $50 * 5x = $250 USDT per trade

TOTAL_DECA_SECTIONS = 10
INITIAL_CAPITAL_TOTAL = 1000.0
STARTING_BALANCE_PER_SECTION = 100.0
SECTION_RISK_FRACTION = 0.50

# Strategy Parameters: Hermes MS-OB 7-Model Order Block Engine (v2.0 Golden Final)
STRATEGY_NAME = "HERMES_MS_OB"
STRATEGY_VERSION = "2.0_FINAL"
STRATEGY_MODEL = "7_MODEL_OB_5M_CONFIRM_SWEEP_RECLAIM"

# Risk & Return Architecture (15% ROI SL / 15% ROI Full Book TP)
HARD_SL_PRICE_PCT = 3.0           # 3.0% Price Move
HARD_SL_ROI_PCT = 15.0            # 3.0% * 5x = -15.0% ROI Hard SL
FULL_BOOK_TP_PRICE_PCT = 3.0      # 3.0% Price Move
FULL_BOOK_TP_ROI_PCT = 15.0       # 3.0% * 5x = +15.0% ROI Full Book TP
SL_BUFFER_PCT = 0.03              # 3% Price Distance for SL
MAX_CONCURRENT_TRADES = 8         # Max 8 concurrent active positions

# Break-Even & Anti-Hunt Confirmation Protocols
BREAKEVEN_TRIGGER_ROI = 12.0          # Trigger Break-Even at +12.0% ROI
BREAKEVEN_LOCK_ROI = 2.5              # Lock Stop Loss at +2.5% ROI (Guaranteed Profit + Fee Shield)
SL_CONFIRMATION_TIMEFRAME = "15m"     # Timeframe for Hard SL candle closes
SL_CONSECUTIVE_15M_CANDLES = 2        # Require 2 consecutive 15m candle closes beyond SL to exit
ENTRY_CONFIRMATION_TIMEFRAME = "5m"   # Timeframe for entry confirmation close
SWEEP_RECLAIM_TIMEBOX_MINUTES = 120   # 2-Hour window (120 minutes) for liquidity sweep reclamation

# Dedicated Telegram Bot Integration
BB20_TELEGRAM_BOT_TOKEN = "8685685362:AAFWkKvRIs6cJ70gegcJVFyKB5soDtEttbU"
BB20_TELEGRAM_CHAT_ID = "752247227"

PAIR_MAPPING = {
    "BTCUSDT": 1, "ETHUSDT": 1, "PAXGUSDT": 1,
    "SOLUSDT": 2, "BNBUSDT": 2, "SEIUSDT": 2,
    "AVAXUSDT": 3, "DOGEUSDT": 3, "KAVAUSDT": 3,
    "DOTUSDT": 4, "LINKUSDT": 4, "ENSUSDT": 4,
    "LTCUSDT": 5, "NEARUSDT": 5, "DYDXUSDT": 5,
    "OPUSDT": 6, "RENDERUSDT": 6, "WLDUSDT": 6,
    "SUIUSDT": 7, "TIAUSDT": 7, "TRBUSDT": 7,
    "UNIUSDT": 8, "XRPUSDT": 8, "SNXUSDT": 8,
    "1000PEPEUSDT": 9, "APTUSDT": 9, "ARKMUSDT": 9,
    "ARBUSDT": 10, "FETUSDT": 10, "ONDOUSDT": 10
}

CHAMPIONS = list(PAIR_MAPPING.keys())

# Storage
DB_PATH = BASE_DIR / "database" / "nexuspro.db"

# Legacy compatibility
SL_ANTI_HUNT_BUFFER = 0.0
MEAN_THRESHOLD_RATIO = 0.0
FEE_FRICTION_R = 0.0
MAX_LIMIT_WAIT_BARS = 0
INFINITE_TRAILING_ENABLED = False
TRAILING_TIER_1_TRIGGER_ROI = 12.0
TRAILING_TIER_1_LOCK_ROI = 2.5
TRAILING_STEP_ROI = 0.0
TRAILING_BUFFER_ROI = 0.0
DEFAULT_RRR = 1.0
