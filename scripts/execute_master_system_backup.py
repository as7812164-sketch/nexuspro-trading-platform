import os
import shutil
import zipfile
import json
from datetime import datetime

# Define source directories
VAULT_DIR = r"C:\Users\power\.gemini\antigravity\scratch\smc_v17_trading_system\institutional_video_learning_vault"
MS_OB_DIR = r"C:\Users\power\.gemini\antigravity\scratch\smc_v17_trading_system\pine_script_vault\09_HERMES_MS_TRADING_ORDER_BLOCK_SYSTEM"
NEXUSPRO_DIR = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform"
HERMES_APP_DATA = r"C:\Users\power\AppData\Local\hermes"

# Target backup locations
DESKTOP_BACKUP_DIR = r"C:\Users\power\Desktop\HERMES_SYSTEM_MASTER_BACKUP_20261108"
SCRATCH_BACKUP_DIR = r"C:\Users\power\.gemini\antigravity\scratch\smc_v17_trading_system\MASTER_BACKUP_ARCHIVE_20261108"
DESKTOP_ZIP = r"C:\Users\power\Desktop\HERMES_SYSTEM_MASTER_BACKUP_20261108.zip"

print(f"[*] Starting Hermes Master System Backup at {datetime.now().isoformat()}...")

# Clean or create target folders
for target_root in [DESKTOP_BACKUP_DIR, SCRATCH_BACKUP_DIR]:
    if os.path.exists(target_root):
        shutil.rmtree(target_root)
    os.makedirs(target_root, exist_ok=True)
    os.makedirs(os.path.join(target_root, "01_VIDEO_CURRICULUM_INDICATORS"), exist_ok=True)
    os.makedirs(os.path.join(target_root, "02_HERMES_MS_OB_SYSTEMS"), exist_ok=True)
    os.makedirs(os.path.join(target_root, "03_NEXUSPRO_PRODUCTION_TERMINAL"), exist_ok=True)
    os.makedirs(os.path.join(target_root, "04_HERMES_AI_BRAIN_AND_MEMORIES"), exist_ok=True)

# 1. BUCKET 1: Video Curriculum & Indicators
print("[1] Backing up 15-Video Curriculum & Indicators...")
vault_sources = [
    os.path.join(VAULT_DIR, "05_final_unified_engine", "HERMES_15_PILLAR_MASTER_INDICATOR.pine"),
    os.path.join(VAULT_DIR, "05_final_unified_engine", "HERMES_15_PILLAR_UNIFIED_MASTER_STRATEGY.pine"),
    os.path.join(VAULT_DIR, "03_logic_and_entry_modules", "HERMES_15_PILLAR_MASTER_STRATEGY_BLUEPRINT.md"),
    os.path.join(VAULT_DIR, "MASTER_14_VIDEO_VISUAL_VERIFICATION_REPORT.md"),
    os.path.join(VAULT_DIR, "MASTER_CURRICULUM_LEDGER.md"),
]
for src in vault_sources:
    if os.path.exists(src):
        fname = os.path.basename(src)
        shutil.copy2(src, os.path.join(DESKTOP_BACKUP_DIR, "01_VIDEO_CURRICULUM_INDICATORS", fname))
        shutil.copy2(src, os.path.join(SCRATCH_BACKUP_DIR, "01_VIDEO_CURRICULUM_INDICATORS", fname))
        print(f"    -> Copied {fname}")

# Copy all living engines v01 to v15
engines_dir = os.path.join(VAULT_DIR, "04_pine_prototypes_and_synthesizer")
if os.path.exists(engines_dir):
    prototypes_dest_desktop = os.path.join(DESKTOP_BACKUP_DIR, "01_VIDEO_CURRICULUM_INDICATORS", "prototypes_v01_to_v15")
    prototypes_dest_scratch = os.path.join(SCRATCH_BACKUP_DIR, "01_VIDEO_CURRICULUM_INDICATORS", "prototypes_v01_to_v15")
    os.makedirs(prototypes_dest_desktop, exist_ok=True)
    os.makedirs(prototypes_dest_scratch, exist_ok=True)
    for f in os.listdir(engines_dir):
        if f.endswith(".pine"):
            src_f = os.path.join(engines_dir, f)
            shutil.copy2(src_f, os.path.join(prototypes_dest_desktop, f))
            shutil.copy2(src_f, os.path.join(prototypes_dest_scratch, f))
    print("    -> Copied living_engine_v01 to living_engine_v15 prototypes")

# 2. BUCKET 2: Hermes MS-OB Systems
print("[2] Backing up Hermes MS-OB Systems...")
msob_sources = [
    os.path.join(MS_OB_DIR, "HERMES_MS_OB_INDICATOR_OFFICIAL.pine"),
    os.path.join(MS_OB_DIR, "backups", "HERMES_MS_TRADING_ORDER_BLOCK_INDICATOR_v2.0_GOLDEN_VERIFIED_20261107.pine"),
    os.path.join(MS_OB_DIR, "backups", "HERMES_MS_TRADING_ORDER_BLOCK_SYSTEM_v2.0_GOLDEN_VERIFIED_20261107.pine"),
    os.path.join(MS_OB_DIR, "HERMES_MS_TRADING_ORDER_BLOCK_INDICATOR.pine"),
    os.path.join(MS_OB_DIR, "HERMES_MS_TRADING_ORDER_BLOCK_SYSTEM.pine"),
    os.path.join(MS_OB_DIR, "README.md"),
]
for src in msob_sources:
    if os.path.exists(src):
        fname = os.path.basename(src)
        shutil.copy2(src, os.path.join(DESKTOP_BACKUP_DIR, "02_HERMES_MS_OB_SYSTEMS", fname))
        shutil.copy2(src, os.path.join(SCRATCH_BACKUP_DIR, "02_HERMES_MS_OB_SYSTEMS", fname))
        print(f"    -> Copied {fname}")

# 3. BUCKET 3: NexusPro Production Terminal
print("[3] Backing up NexusPro Production Platform...")
nexus_files = [
    "app.py", "config.py", "requirements.txt", "start_nexuspro.bat", "test_system.py"
]
for f in nexus_files:
    src = os.path.join(NEXUSPRO_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(DESKTOP_BACKUP_DIR, "03_NEXUSPRO_PRODUCTION_TERMINAL", f))
        shutil.copy2(src, os.path.join(SCRATCH_BACKUP_DIR, "03_NEXUSPRO_PRODUCTION_TERMINAL", f))

# Subdirectories for NexusPro
for sub in ["engine", "database", "static", "scripts"]:
    sub_src = os.path.join(NEXUSPRO_DIR, sub)
    if os.path.exists(sub_src):
        shutil.copytree(sub_src, os.path.join(DESKTOP_BACKUP_DIR, "03_NEXUSPRO_PRODUCTION_TERMINAL", sub), dirs_exist_ok=True)
        shutil.copytree(sub_src, os.path.join(SCRATCH_BACKUP_DIR, "03_NEXUSPRO_PRODUCTION_TERMINAL", sub), dirs_exist_ok=True)
        print(f"    -> Copied nexuspro/{sub}/")

# Also copy Desktop APK if present
desktop_apk = r"C:\Users\power\Desktop\NexusPro_Trading_Terminal.apk"
if os.path.exists(desktop_apk):
    shutil.copy2(desktop_apk, os.path.join(DESKTOP_BACKUP_DIR, "03_NEXUSPRO_PRODUCTION_TERMINAL", "NexusPro_Trading_Terminal.apk"))
    shutil.copy2(desktop_apk, os.path.join(SCRATCH_BACKUP_DIR, "03_NEXUSPRO_PRODUCTION_TERMINAL", "NexusPro_Trading_Terminal.apk"))
    print("    -> Copied NexusPro_Trading_Terminal.apk")

# 4. BUCKET 4: Hermes Brain & Memories
print("[4] Backing up Hermes AI Brain & Memories...")
brain_files = [
    (os.path.join(HERMES_APP_DATA, "SOUL.md"), "SOUL.md"),
    (os.path.join(HERMES_APP_DATA, "memories", "MEMORY.md"), "MEMORY.md"),
    (os.path.join(HERMES_APP_DATA, "memories", "USER.md"), "USER.md"),
]
for src, name in brain_files:
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(DESKTOP_BACKUP_DIR, "04_HERMES_AI_BRAIN_AND_MEMORIES", name))
        shutil.copy2(src, os.path.join(SCRATCH_BACKUP_DIR, "04_HERMES_AI_BRAIN_AND_MEMORIES", name))
        print(f"    -> Copied {name}")

# 5. CREATE MASTER KNOWLEDGE INDEX (Searchable Ledger)
master_index_content = """# 🏛️ HERMES MASTER KNOWLEDGE & SYSTEM BACKUP LEDGER
**Archive Date:** 2026-11-08 | **Author:** Hermes AI Quant Division (Akash Bhai Partnership)
**Archive Location:** `C:\\Users\\power\\Desktop\\HERMES_SYSTEM_MASTER_BACKUP_20261108`

---

## ⚡ Quick Scan & Retrieval Index
Whenever Akash bhai starts a new session or asks for any component, reference this index to instantly retrieve:

### 1. 01_VIDEO_CURRICULUM_INDICATORS (15-Video Curriculum Synthesis)
- **`HERMES_15_PILLAR_MASTER_INDICATOR.pine`:** Complete visual study indicator synthesizing all 15 Shoaib Khan / MS Trading lessons.
  - *Pillars Included:* Valid Pullback, BOS/CHoCH, IDM, Institutional OB, FVG (C.E. 50%), Trendline/EQH Traps, LRLR/HRLR, HTF POI to 5m Sniper, Premium/Discount, OTE (0.618-0.786), Asian Judas, London/NY Killzones, Multi-Timeframe Bias, CBDR Day H/L, 7-Condition OB Taxonomy.
  - *Visual Clarity:* 100% transparent label panels, zero candlestick occlusion.
- **`HERMES_15_PILLAR_UNIFIED_MASTER_STRATEGY.pine`:** Full TradingView automated strategy engine for backtesting with Dynamic Profit Armor (+1.0% Breakeven, +1.8% Trail, +2.8% TP, -2.8% SL).
- **`HERMES_15_PILLAR_MASTER_STRATEGY_BLUEPRINT.md`:** Complete forensic mathematical blueprint.
- **`prototypes_v01_to_v15/`:** Step-by-step evolutionary Pine scripts (`living_engine_v01.pine` to `living_engine_v15.pine`).

### 2. 02_HERMES_MS_OB_SYSTEMS (Order Block Core Engine)
- **`HERMES_MS_OB_INDICATOR_OFFICIAL.pine`:** Upgraded TradingView Pine Script with interior dashed 50% Mean Threshold midline, rectangular boxes, and 7-model classification.
- **`HERMES_MS_TRADING_ORDER_BLOCK_INDICATOR_v2.0_GOLDEN_VERIFIED_20261107.pine`:** Golden verified backup archived on 07 November 2026.
- **`HERMES_MS_TRADING_ORDER_BLOCK_SYSTEM_v2.0_GOLDEN_VERIFIED_20261107.pine`:** Strategy backtesting engine matching the verified golden baseline.
- **`README.md`:** Full documentation of the 7 Order Block models, Shoaib Khan body close invalidation, and weak OB sweep execution rules.

### 3. 03_NEXUSPRO_PRODUCTION_TERMINAL (Live Cloud Trading Platform)
- **Live URL:** `https://nexuspro-terminal.onrender.com/trade`
- **Trading Rules Confirmed:**
  - Zero Compounding (Normal futures mode only).
  - Portfolio Base: Flat **$1,000.00 USDT**.
  - Margin Per Position: Flat **5% ($50.00)**.
  - Leverage: **Strictly 5x Isolated Margin** ($250.00 position size).
  - Hard SL: **-3.0% Price Move = -15% ROI** (-$7.50 max loss).
  - Full Book TP: **+3.0% Price Move = +15% ROI** (+$7.50 profit).
  - Dynamic Profit Armor: Breakeven shift at +1.0% ($0.00 risk).
- **Files:** `app.py`, `config.py`, `engine/ms_ob_engine.py`, `database/db.py`, `static/trade.html`, `static/js/app.js`, `NexusPro_Trading_Terminal.apk`.

### 4. 04_HERMES_AI_BRAIN_AND_MEMORIES (Persistent Brain Files)
- **`MEMORY.md`:** 43 comprehensive forensic chapters spanning every autopsy, benchmark, rule refinement, and architectural decision.
- **`SOUL.md`:** Hermes AI autonomous quant framework and disciplined trading persona.
- **`USER.md`:** User profile, rules, and communication protocol.

---

## 🛡️ Strict Operational Safety Boundaries
- **`trdzone.duckdns.org` & Oracle VPS (`130.210.4.45`):** 100% Locked & Frozen in Read-Only production mode. Never edit without explicit user permission.
- **Zero Retail Indicators:** RSI, MACD, EMA, Bollinger Bands are permanently banned across all indicators and platforms.
"""

for target_root in [DESKTOP_BACKUP_DIR, SCRATCH_BACKUP_DIR]:
    index_file = os.path.join(target_root, "00_HERMES_MASTER_KNOWLEDGE_INDEX.md")
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(master_index_content)
    print(f"[*] Generated Master Knowledge Index at {index_file}")

# 6. CREATE DESKTOP ZIP ARCHIVE
print(f"[*] Creating ZIP archive at {DESKTOP_ZIP}...")
with zipfile.ZipFile(DESKTOP_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(DESKTOP_BACKUP_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, DESKTOP_BACKUP_DIR)
            zipf.write(file_path, arcname)

zip_size_mb = os.path.getsize(DESKTOP_ZIP) / (1024 * 1024)
print(f"[SUCCESS] Master Backup Completed! ZIP size: {zip_size_mb:.2f} MB")
