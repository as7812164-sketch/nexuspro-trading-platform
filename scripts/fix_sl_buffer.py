from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Update engine/ms_ob_engine.py
engine_path = BASE_DIR / "engine" / "ms_ob_engine.py"
with open(engine_path, "r", encoding="utf-8") as f:
    ec = f.read()

ec = ec.replace(
    "self.hard_sl_price_pct = 0.03",
    "self.hard_sl_price_pct = 0.03\n        self.sl_buffer_pct = 0.03"
)
with open(engine_path, "w", encoding="utf-8") as f:
    f.write(ec)

# 2. Update app.py
app_path = BASE_DIR / "app.py"
with open(app_path, "r", encoding="utf-8") as f:
    ac = f.read()

ac = ac.replace(
    '"sl_buffer_pct": hermes_ms_ob_engine.sl_buffer_pct * 100.0,',
    '"sl_buffer_pct": getattr(hermes_ms_ob_engine, "hard_sl_price_pct", 0.03) * 100.0,\n        "hard_sl_roi_pct": -15.0,\n        "full_book_tp_roi_pct": 15.0,'
)
with open(app_path, "w", encoding="utf-8") as f:
    f.write(ac)

print("[OK] Patched sl_buffer_pct in engine and app.py!")
