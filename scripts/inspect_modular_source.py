import urllib.request
import os

base_url = "https://trdzone.duckdns.org"
html = urllib.request.urlopen(f"{base_url}/mobile", timeout=15).read().decode("utf-8", "ignore")
print("=== LIVE /mobile HTML ===")
print(html)

local_mod = r"C:\Users\power\.gemini\antigravity\scratch\smc_v17_trading_system\static\modular"
for rel in [
    "js/app.js",
    "js/core/state.js",
    "js/core/websocket.js",
    "js/components/hud_header.js",
    "js/components/navigation.js",
    "js/components/wallet_summary.js",
    "js/components/watchlist.js",
    "js/components/position_card.js",
    "js/components/chart_terminal.js",
    "js/components/ticker_carousel.js",
]:
    live_sz = -1
    try:
        r = urllib.request.urlopen(f"{base_url}/{rel}", timeout=10).read()
        live_sz = len(r)
    except Exception as e:
        live_sz = f"ERR:{e}"
    loc_p = os.path.join(local_mod, rel.replace("/", os.sep))
    loc_sz = os.path.getsize(loc_p) if os.path.exists(loc_p) else -1
    print(f"File: {rel:38s} | Local: {loc_sz} | Live VPS: {live_sz}")
