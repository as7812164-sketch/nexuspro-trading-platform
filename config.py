"""
NEXUSPRO PLATFORM CONFIGURATION
===============================
Brand: NexusPro (Institutional Futures & Deca Compounding Terminal)
Format: 100% Bitget Pro Layout & UI System
Engine: BB 2.0 ($47,389.77 USDT Historic Compounding Model)
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

# BB 2.0 Strategy Parameters
SL_ANTI_HUNT_BUFFER = 0.0015  # 0.15% Buffer beyond extreme sweep wick
MEAN_THRESHOLD_RATIO = 0.50   # 50% Mean Threshold of Extreme Order Block
FEE_FRICTION_R = 0.06         # 0.06 R Taker fee + slippage deduction
MAX_LIMIT_WAIT_BARS = 32      # Bars to wait for 50% MT retest fill
DEFAULT_RRR = 2.0             # Fixed 1:2.0 RRR Sweet Spot Target

# Stepped Trailing SL Ladder (BB 2.0 Model 3)
TRAILING_TIER_1_TRIGGER_R = 1.0  # At +1.0R profit -> move SL to +0.2R (Fee Shield)
TRAILING_TIER_1_LOCK_R = 0.2
TRAILING_TIER_2_TRIGGER_R = 1.5  # At +1.5R profit -> move SL to +1.0R (Profit Locked)
TRAILING_TIER_2_LOCK_R = 1.0
TRAILING_TIER_3_TRIGGER_R = 2.0  # At +2.0R profit -> move SL to +1.5R (Profit Locked)
TRAILING_TIER_3_LOCK_R = 1.5

# Top-20 Champions mapped across 10 Isolated Deca Sections (Zero Cross-Section Contamination)
PAIR_MAPPING = {
    "BTCUSDT": 1, "ETHUSDT": 1,
    "SOLUSDT": 2, "BNBUSDT": 2,
    "AVAXUSDT": 3, "DOGEUSDT": 3,
    "DOTUSDT": 4, "LINKUSDT": 4,
    "LTCUSDT": 5, "NEARUSDT": 5,
    "OPUSDT": 6, "RENDERUSDT": 6,
    "SUIUSDT": 7, "TIAUSDT": 7,
    "UNIUSDT": 8, "XRPUSDT": 8,
    "1000PEPEUSDT": 9, "APTUSDT": 9,
    "ARBUSDT": 10, "FETUSDT": 10
}

CHAMPIONS = list(PAIR_MAPPING.keys())

# Storage
DB_PATH = BASE_DIR / "database" / "nexuspro.db"
