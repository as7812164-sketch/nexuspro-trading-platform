"""
NEXUSPRO PLATFORM CONFIGURATION
===============================
Brand: NexusPro (Institutional Futures & Deca Compounding Terminal)
Format: 100% Bitget Pro Layout & UI System
Engine: BB 3.0 ($47,389.77 USDT Historic Compounding Model)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Branding
BRAND_NAME = "NexusPro"
BRAND_SUBTITLE = "INSTITUTIONAL FUTURES & DECA TERMINAL"
BRAND_ACCENT = "#00DFC0"  # Bitget Signature Teal/Cyan
THEME_BG = "#080B11"

# Deca Compounding ($500.00 Starting Capital)
TOTAL_DECA_SECTIONS = 10
INITIAL_CAPITAL_TOTAL = 500.0  # USDT
STARTING_BALANCE_PER_SECTION = 50.0  # $50 each * 10 sections = $500
SECTION_RISK_FRACTION = 0.05  # 5% Aggressive Section Compounding ($47k model)
DEFAULT_LEVERAGE = 5  # 5x Isolated Leverage

# BB 3.0 Strategy Parameters (Model 2: Infinite Stepped Trailing SL Rider)
STRATEGY_NAME = "BB 3.0"
STRATEGY_VERSION = "3.0"
STRATEGY_MODEL = "BB 3.0 INFINITE TRAILING RIDER"
SL_ANTI_HUNT_BUFFER = 0.0015  # 0.15% Buffer beyond extreme sweep wick
MEAN_THRESHOLD_RATIO = 0.50   # 50% Mean Threshold of Extreme Order Block
FEE_FRICTION_R = 0.06         # 0.06 R Taker fee + slippage deduction
MAX_LIMIT_WAIT_BARS = 32      # Bars to wait for 50% MT retest fill
INFINITE_TRAILING_ENABLED = True

# Infinite Stepped Trailing SL Ladder (BB 3.0 Continuous ROI Model)
# User Defined Trailing Ladder (5x Leverage):
# Tier 1: At +4.80% ROI -> Move SL to +1.00% ROI (Fee Shield / Risk Free)
# Tier 2: At +9.80% ROI -> Move SL to +5.10% ROI
# Tier 3: At +14.80% ROI -> Move SL to +10.10% ROI
# Tier 4: At +19.80% ROI -> Move SL to +15.10% ROI
# Tier 5: At +24.80% ROI -> Move SL to +20.10% ROI
# Tier 6: At +29.80% ROI -> Move SL to +25.10% ROI
# Tier 7: At +34.80% ROI -> Move SL to +30.10% ROI
# Continuous: Every +5.00% additional ROI peak shifts SL forward by +5.00% ROI indefinitely!
TRAILING_TIER_1_TRIGGER_ROI = 4.80
TRAILING_TIER_1_LOCK_ROI = 1.00
TRAILING_STEP_ROI = 5.00
TRAILING_BUFFER_ROI = 4.70
DEFAULT_RRR = 3.0


# Top-30 Champions mapped across 10 Isolated Deca Sections (3 Proven Champions per Section)
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
