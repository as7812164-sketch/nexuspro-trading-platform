import re

file_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\trade.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update SMC button to active Hermes MS-OB
old_btn = '''<button id="btnToggleSmc" class="chart-tool-btn" onclick="toggleSmcLevels()" title="Toggle SMC Levels">
                        <i class="fa-solid fa-crosshairs" style="color:var(--gold);"></i> SMC
                    </button>'''

new_btn = '''<button id="btnToggleSmc" class="chart-tool-btn active" onclick="toggleSmcLevels()" title="Toggle Hermes MS-OB Order Block Indicator">
                        <i class="fa-solid fa-bolt" style="color:var(--gold);"></i> Hermes MS-OB
                    </button>'''

if old_btn in content:
    content = content.replace(old_btn, new_btn)
    print("[OK] Replaced SMC button with Hermes MS-OB button")
else:
    print("[WARN] SMC button pattern not found directly, checking regex")
    content = re.sub(
        r'<button id="btnToggleSmc" class="chart-tool-btn"[^>]*onclick="toggleSmcLevels\(\)"[^>]*>[\s\S]*?<\/button>',
        new_btn,
        content
    )
    print("[OK] Replaced via regex")

# 2. Add Hermes MS-OB Overlay container inside tradingview_chart
overlay_html = '''            <div id="tradingview_chart" onclick="onChartAreaClick(event)" style="position:relative;">
                <!-- HERMES MS-OB 7-MODEL ORDER BLOCK OVERLAY -->
                <div id="hermesObOverlayContainer" class="hermes-ob-overlay-container" style="position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:3; overflow:hidden;">
                    <!-- Top-Left Indicator Watermark (Matching TradingView Image 2) -->
                    <div id="hermesIndicatorWatermark" style="position:absolute; top:8px; left:12px; display:flex; align-items:center; gap:6px; background:rgba(18, 22, 34, 0.90); backdrop-filter:blur(6px); padding:4px 10px; border-radius:5px; border:1px solid rgba(255,255,255,0.12); z-index:10; pointer-events:none; box-shadow:0 2px 8px rgba(0,0,0,0.5);">
                        <span style="color:#F59E0B; font-size:12px;"><i class="fa-solid fa-bolt"></i></span>
                        <span style="color:#F1F5F9; font-size:11px; font-weight:800; letter-spacing:0.4px;">Hermes MS-OB Indicator</span>
                    </div>
                    <!-- SVG Layer for Order Block Rectangles and 50% MT dashed lines -->
                    <svg id="hermesObOverlaySvg" style="width:100%; height:100%; position:absolute; top:0; left:0; pointer-events:none;"></svg>
                    <!-- Badges Container for stylized multi-line pills -->
                    <div id="hermesObBadgesContainer" style="position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none;"></div>
                </div>'''

target_chart = '<div id="tradingview_chart" onclick="onChartAreaClick(event)" style="position:relative;">'
if 'id="hermesObOverlayContainer"' not in content:
    if target_chart in content:
        content = content.replace(target_chart, overlay_html, 1)
        print("[OK] Inserted hermesObOverlayContainer")
    else:
        print("[WARN] tradingview_chart tag not matched")
else:
    print("[INFO] hermesObOverlayContainer already present")

# 3. Update app.js script version cache-buster
content = re.sub(r'app\.js\?v=[^"]+', 'app.js?v=hermes_msob_boxes_v5', content)
print("[OK] Updated app.js cache-buster to hermes_msob_boxes_v5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[SUCCESS] static/trade.html patched cleanly")
