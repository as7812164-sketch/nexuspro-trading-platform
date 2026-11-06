"""
PATCH NO COMPOUNDING & HERMES MS-OB INDICATOR ON CHART
======================================================
1. Removes all compounding/Deca references from static/trade.html and static/js/app.js.
2. Updates static/js/app.js to draw HERMES_MS_OB (7-Model Order Blocks, 50% MT, Hard SL -15% ROI, Full Book TP +15% ROI) directly on the chart.
3. Updates app.py to return clean normal futures status and setups.
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Patch static/trade.html
html_path = BASE_DIR / "static" / "trade.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Nav link
html = html.replace(
    '<a href="/deca" class="nav-link"><i class="fa-solid fa-trophy" style="color:var(--gold)"></i> Deca $47k Hub</a>',
    '<a href="/positions" class="nav-link"><i class="fa-solid fa-crosshairs" style="color:var(--brand-teal)"></i> Positions & Radar</a>'
)

# Header stats
html = html.replace(
    '<span class="stat-label">Deca P&L</span>',
    '<span class="stat-label">Total P&L</span>'
)

# Ticker bar strategy
html = html.replace(
    'Standby (Strategy Decommissioned)',
    'Hermes MS-OB (Normal Futures • 5x • SL -15% ROI • TP +15% ROI)'
)
html = html.replace(
    'Strategy: Hermes MS-OB (7-Model 1st Tap | 5% Margin | Max 8 Concurrent)',
    'Strategy: Hermes MS-OB (Normal Futures • 5x • Hard SL -15% ROI • Full TP +15% ROI)'
)

# Dock tab
html = html.replace(
    '<i class="fa-solid fa-trophy"></i> Deca $47k Hub',
    '<i class="fa-solid fa-crosshairs"></i> Hermes MS-OB Setups'
)
html = html.replace(
    '<!-- TAB 2: BB 3.0 SETUPS RADAR -->',
    '<!-- TAB 2: HERMES MS-OB RADAR -->'
)

# Drawer menu
html = html.replace(
    '<span style="display:flex; align-items:center; gap:10px;"><i class="fa-solid fa-trophy" style="color:var(--gold); width:18px;"></i> Deca Compounding Hub</span>',
    '<span style="display:flex; align-items:center; gap:10px;"><i class="fa-solid fa-crosshairs" style="color:var(--brand-teal); width:18px;"></i> Hermes MS-OB Setups</span>'
)
html = html.replace(
    '<!-- SECTION 2: BB 3.0 INSTITUTIONAL MATRIX -->',
    '<!-- SECTION 2: HERMES MS-OB MATRIX -->'
)
html = html.replace(
    '<i class="fa-solid fa-arrow-trend-up" style="color:var(--gold); width:18px;"></i> Compounding Ladders',
    '<i class="fa-solid fa-crosshairs" style="color:var(--brand-teal); width:18px;"></i> MS-OB 7-Model Setups'
)
html = html.replace(
    '<span>Deca Capital:</span> <b style="color:var(--brand-teal);">$1,000.00 USDT</b>',
    '<span>Margin / Trade:</span> <b style="color:var(--brand-teal);">5% ($50.00 USDT)</b>'
)

# Mobile bottom bar
html = html.replace(
    '<a href="/deca" class="mobile-tab-btn">\n            <i class="fa-solid fa-trophy" style="font-size:16px; color:var(--gold);"></i>\n            <span>Deca 47k</span>\n        </a>',
    '<a href="/positions" class="mobile-tab-btn">\n            <i class="fa-solid fa-crosshairs" style="font-size:16px; color:var(--brand-teal);"></i>\n            <span>MS-OB Setups</span>\n        </a>'
)

# Cache buster
html = re.sub(r'app\.js\?v=[a-zA-Z0-9_\-]+', 'app.js?v=hermes_msob_v3_nocompounding', html)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print("[OK] static/trade.html patched cleanly!")

# 2. Patch static/js/app.js
js_path = BASE_DIR / "static" / "js" / "app.js"
with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

# Update updateSmcLevels to calculate 7-Model Order Blocks on current chart and render them
msob_chart_renderer = """function updateSmcLevels(candles) {
    if (currentSmcPriceLines && currentSmcPriceLines.length > 0) {
        currentSmcPriceLines.forEach(l => {
            try { candleSeries.removePriceLine(l); } catch(e) {}
        });
        currentSmcPriceLines = [];
    }
    if (!indicatorsState.smc || !candles || candles.length < 25) return;

    // --- HERMES MS-OB 7-MODEL CHART INDICATOR ---
    // Calculates unmitigated Order Blocks with 50% Mean Threshold on current timeframe
    const atrPeriod = 14;
    let trList = [];
    for (let i = 1; i < candles.length; i++) {
        const cHigh = candles[i].high;
        const cLow = candles[i].low;
        const pClose = candles[i - 1].close;
        const tr = Math.max(cHigh - cLow, Math.abs(cHigh - pClose), Math.abs(cLow - pClose));
        trList.push(tr);
    }
    const atr = trList.slice(-atrPeriod).reduce((a, b) => a + b, 0) / atrPeriod || 0.0;
    if (atr <= 0) return;

    const currPrice = candles[candles.length - 1].close;
    const scanStart = Math.max(2, candles.length - 20);

    for (let i = scanStart; i < candles.length - 1; i++) {
        const c1 = candles[i - 2];
        const c2 = candles[i - 1];
        const c3 = candles[i];

        // Bullish OB
        const fvgBull = c3.low > c1.high && (c3.low - c1.high) >= (atr * 0.15);
        const dispBull = (c2.close - c2.open) >= (atr * 1.2);
        if (fvgBull && dispBull) {
            const obTop = c1.high;
            const obBottom = (c2.low < c1.low) ? c2.low : c1.low;
            const obMid = (obTop + obBottom) / 2.0;

            let isMitigated = false;
            for (let k = i + 1; k < candles.length; k++) {
                if (candles[k].close < obBottom) { isMitigated = true; break; }
                if (candles[k].low <= obTop) { isMitigated = true; }
            }

            if (!isMitigated) {
                // Render Unmitigated Bullish Demand OB
                const topL = candleSeries.createPriceLine({
                    price: obTop,
                    color: '#00C087',
                    lineWidth: 2,
                    lineStyle: 0,
                    axisLabelVisible: true,
                    title: '🟢 BULLISH OB (DEMAND)'
                });
                const midL = candleSeries.createPriceLine({
                    price: obMid,
                    color: '#F59E0B',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: '⚡ 50% MT'
                });
                const botL = candleSeries.createPriceLine({
                    price: obBottom,
                    color: '#00C087',
                    lineWidth: 1,
                    lineStyle: 1,
                    axisLabelVisible: false,
                    title: ''
                });
                currentSmcPriceLines.push(topL, midL, botL);
            }
        }

        // Bearish OB
        const fvgBear = c3.high < c1.low && (c1.low - c3.high) >= (atr * 0.15);
        const dispBear = (c2.open - c2.close) >= (atr * 1.2);
        if (fvgBear && dispBear) {
            const obTop = (c2.high > c1.high) ? c2.high : c1.high;
            const obBottom = c1.low;
            const obMid = (obTop + obBottom) / 2.0;

            let isMitigated = false;
            for (let k = i + 1; k < candles.length; k++) {
                if (candles[k].close > obTop) { isMitigated = true; break; }
                if (candles[k].high >= obBottom) { isMitigated = true; }
            }

            if (!isMitigated) {
                // Render Unmitigated Bearish Supply OB
                const botL = candleSeries.createPriceLine({
                    price: obBottom,
                    color: '#FF4B55',
                    lineWidth: 2,
                    lineStyle: 0,
                    axisLabelVisible: true,
                    title: '🔴 BEARISH OB (SUPPLY)'
                });
                const midL = candleSeries.createPriceLine({
                    price: obMid,
                    color: '#F59E0B',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: '⚡ 50% MT'
                });
                const topL = candleSeries.createPriceLine({
                    price: obTop,
                    color: '#FF4B55',
                    lineWidth: 1,
                    lineStyle: 1,
                    axisLabelVisible: false,
                    title: ''
                });
                currentSmcPriceLines.push(botL, midL, topL);
            }
        }
    }
}"""

js = re.sub(
    r'function updateSmcLevels\(candles\) \{[\s\S]*?// Old strategy lines completely purged\s*\}',
    msob_chart_renderer,
    js
)

# Update drawStrategyOnChart to render exact 15% ROI Hard SL and 15% ROI Full Book TP
js = js.replace(
    "title: `${isTrailing ? '🛡️ TRAILING SL' : '⛔ STOP LOSS'}: $${slP.toFixed(4)}`",
    "title: `⛔ HARD SL (-15% ROI): $${slP.toFixed(4)}`"
)
js = js.replace(
    "title: `🎯 TARGET TP: $${tpP.toFixed(4)} (+3.0R)`",
    "title: `🎯 FULL BOOK TP (+15% ROI): $${tpP.toFixed(4)}`"
)

# Remove any EMA ribbon toggle default
js = js.replace(
    "indicatorsState = {\n    vol: true,\n    ema: true,",
    "indicatorsState = {\n    vol: true,\n    ema: false,"
)

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js)
print("[OK] static/js/app.js patched cleanly!")

# 3. Patch app.py /api/status
app_path = BASE_DIR / "app.py"
with open(app_path, "r", encoding="utf-8") as f:
    app_py = f.read()

app_py = app_py.replace(
    '"mode": "7-Model Order Block 1st Tap Protocol (1H/4H & Gold 15m/1H/4H)"',
    '"mode": "HERMES_MS_OB (Normal Futures • Zero Compounding • Hard SL -15% ROI • Full TP +15% ROI)"'
)
app_py = app_py.replace(
    '"breakeven_trigger": "+1.0% (Fee Shield)",\n            "trailing_trigger": "+1.8%",\n            "take_profit": "+2.8%"',
    '"hard_sl": "-15.0% ROI (-3.0% Price)",\n            "full_book_tp": "+15.0% ROI (+3.0% Price)",\n            "compounding": "DISABLED (Flat 5% Margin = $50)"'
)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(app_py)
print("[OK] app.py patched cleanly!")
