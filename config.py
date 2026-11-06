"""
NEXUSPRO PLATFORM CONFIGURATION
===============================
Brand: NexusPro (Institutional Futures and Deca Compounding Terminal)
Format: 100% Bitget Pro Layout and UI System
Engine: Standby (Old Strategy Decommissioned and Completely Removed)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Branding
BRAND_NAME = "NexusPro"
BRAND_SUBTITLE = "INSTITUTIONAL FUTURES TERMINAL"
BRAND_ACCENT = "#00DFC0"  # Bitget Signature Teal/Cyan
THEME_BG = "#080B11"

# Deca Compounding ($500.00 Starting Capital)
TOTAL_DECA_SECTIONS = 10
INITIAL_CAPITAL_TOTAL = 500.0  # USDT
STARTING_BALANCE_PER_SECTION = 50.0  # $50 each * 10 sections = $500
SECTION_RISK_FRACTION = 0.05
DEFAULT_LEVERAGE = 5  # 5x Isolated Leverage

# Strategy Parameters: Old BB 3.0 strategy permanently removed per user directive
STRATEGY_NAME = "STANDBY"
STRATEGY_VERSION = "0.0"
STRATEGY_MODEL = "DECOMMISSIONED_STANDBY"
SL_ANTI_HUNT_BUFFER = 0.0
MEAN_THRESHOLD_RATIO = 0.0
FEE_FRICTION_R = 0.0
MAX_LIMIT_WAIT_BARS = 0
INFINITE_TRAILING_ENABLED = False

# Strategy execution flags strictly disabled (Zero execution)
TRAILING_TIER_1_TRIGGER_ROI = 0.0
TRAILING_TIER_1_LOCK_ROI = 0.0
TRAILING_STEP_ROI = 0.0
TRAILING_BUFFER_ROI = 0.0
FIXED_TP_ENABLED = False
DEFAULT_RRR = 0.0

# Dedicated Telegram Bot Integration
BB20_TELEGRAM_BOT_TOKEN = "8685685362:AAFWkKvRIs6cJ70gegcJVFyKB5soDtEttbU"
BB20_TELEGRAM_CHAT_ID = "752247227"


PAIR_MAPPING = {
    "BTCUSDT": 1, "ETHUSDT": 1, "BCHUSDT": 1,
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
