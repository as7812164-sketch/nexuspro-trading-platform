import re

app_js_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\js\app.js"
trade_html_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\trade.html"

# ----------------- 1. PATCH APP.JS -----------------
with open(app_js_path, "r", encoding="utf-8") as f:
    code = f.read()

# Make Strategy HUD hidden by default so chart and watermark are 100% visible
code = code.replace("let isHudManuallyHidden = false;", "let isHudManuallyHidden = true;")

# In drawStrategyOnChart, respect isHudManuallyHidden so it does not auto-pop open over the watermark
old_hud_show = """    // Update HUD DOM Elements
    const hud = document.getElementById("chartStrategyHUD");
    const toggleBtn = document.getElementById("chartStrategyToggleBtn");
    if (toggleBtn) toggleBtn.style.display = "inline-flex";

    const sideBadge = document.getElementById("hudSideBadge");"""

new_hud_show = """    // Update HUD DOM Elements
    const hud = document.getElementById("chartStrategyHUD");
    const toggleBtn = document.getElementById("chartStrategyToggleBtn");
    if (toggleBtn) toggleBtn.style.display = "inline-flex";
    if (hud && isHudManuallyHidden) {
        hud.style.display = "none";
    }

    const sideBadge = document.getElementById("hudSideBadge");"""

code = code.replace(old_hud_show, new_hud_show)

# Replace computeHermesOrderBlocks with the refined swing-pivot & displacement engine
old_compute_func_regex = r"function computeHermesOrderBlocks\(candles\) \{[\s\S]*?detectedHermesOrderBlocks = obList\.slice\(-8\);\s*drawHermesOrderBlocks\(\);\s*\}"

new_compute_func = """function computeHermesOrderBlocks(candles) {
    if (currentSmcPriceLines && currentSmcPriceLines.length > 0) {
        currentSmcPriceLines.forEach(l => {
            try { candleSeries.removePriceLine(l); } catch(e) {}
        });
        currentSmcPriceLines = [];
    }

    if (!candles || candles.length < 20) {
        detectedHermesOrderBlocks = [];
        drawHermesOrderBlocks();
        return;
    }

    // 1. Calculate 14-period True Range / ATR
    const trList = [];
    for (let i = 1; i < candles.length; i++) {
        const cHigh = candles[i].high;
        const cLow = candles[i].low;
        const pClose = candles[i - 1].close;
        const tr = Math.max(cHigh - cLow, Math.abs(cHigh - pClose), Math.abs(cLow - pClose));
        trList.push(tr);
    }
    const atrPeriod = 14;
    const atr = trList.slice(-atrPeriod).reduce((a, b) => a + b, 0) / atrPeriod || 1.0;
    if (atr <= 0) return;

    const obList = [];
    const scanLookback = Math.min(candles.length - 3, 90);
    const startIdx = Math.max(5, candles.length - scanLookback);
    let lastObIndex = -999;

    for (let i = startIdx; i < candles.length - 1; i++) {
        const c1 = candles[i - 2];
        const c2 = candles[i - 1];
        const c3 = candles[i];

        // Separation filter: ensure at least 3-4 bars between consecutive OBs to prevent badge overlap
        if ((i - lastObIndex) < 3) continue;

        // Swing Pivots
        const isSwingHigh = c1.high > (candles[i-3]?.high || 0) && c1.high > (candles[i-4]?.high || 0) && c2.high < c1.high;
        const isSwingLow = c1.low < (candles[i-3]?.low || 999999) && c1.low < (candles[i-4]?.low || 999999) && c2.low > c1.low;

        // ---------------- BULLISH / DEMAND CANDLE EVALUATION ----------------
        const dispBull = (c2.close - c2.open) >= (atr * 0.75) || (c3.close - c3.open) >= (atr * 0.75);
        const sweepLow = c2.low < c1.low || c1.low < (candles[i-3]?.low || c1.low);
        const fvgBull = c3.low > c1.high && (c3.low - c1.high) >= (atr * 0.10);

        if (dispBull && (sweepLow || isSwingLow || fvgBull)) {
            const isC1Bear = c1.close < c1.open;
            let obTop = c1.high;
            let obBottom = sweepLow ? Math.min(c1.low, c2.low) : c1.low;
            if (obTop - obBottom < atr * 0.20) {
                obBottom = obTop - (atr * 0.30);
            }
            const obMid = (obTop + obBottom) / 2.0;

            let theme = "COND";
            let badgeTitle = "⚡ COND-OB";
            let modelSubtitle = "Type 6: Sweep+BOS Leg OB";

            if (sweepLow && (c2.close > c1.high)) {
                theme = "COND";
                badgeTitle = "⚡ COND-OB";
                modelSubtitle = "Type 6: Sweep+BOS Leg OB";
            } else if (isC1Bear) {
                theme = "STRONG_BULL";
                badgeTitle = "🟢 STRONG-OB";
                modelSubtitle = "Type 2: Classic Opposite-Color OB";
            } else {
                theme = "WEAK";
                badgeTitle = "🟠 WEAK-OB (SWEEP REQ)";
                modelSubtitle = "Type 1: Momentum Same-Color OB";
            }

            let isMitigated = false;
            let mitIdx = null;
            let mitTime = null;

            for (let k = i + 1; k < candles.length; k++) {
                if (candles[k].low <= obTop) {
                    isMitigated = true;
                    mitIdx = k;
                    mitTime = candles[k].time;
                    break;
                }
            }

            obList.push({
                side: "BULLISH",
                theme: theme,
                badgeTitle: badgeTitle,
                modelSubtitle: modelSubtitle,
                startIdx: i - 2,
                startTime: c1.time,
                top: obTop,
                bottom: obBottom,
                mid: obMid,
                isMitigated: isMitigated,
                mitIdx: mitIdx,
                mitTime: mitTime
            });
            lastObIndex = i;
            continue;
        }

        // ---------------- BEARISH / SUPPLY CANDLE EVALUATION ----------------
        const dispBear = (c2.open - c2.close) >= (atr * 0.75) || (c3.open - c3.close) >= (atr * 0.75);
        const sweepHigh = c2.high > c1.high || c1.high > (candles[i-3]?.high || c1.high);
        const fvgBear = c1.low > c3.high && (c1.low - c3.high) >= (atr * 0.10);

        if (dispBear && (sweepHigh || isSwingHigh || fvgBear)) {
            const isC1Bull = c1.close > c1.open;
            let obTop = sweepHigh ? Math.max(c1.high, c2.high) : c1.high;
            let obBottom = c1.low;
            if (obTop - obBottom < atr * 0.20) {
                obTop = obBottom + (atr * 0.30);
            }
            const obMid = (obTop + obBottom) / 2.0;

            let theme = "STRONG_BEAR";
            let badgeTitle = "🔴 STRONG-OB";
            let modelSubtitle = "Type 2: Classic Opposite-Color OB";

            if (isSwingHigh && isC1Bull) {
                theme = "STRONG_BEAR";
                badgeTitle = "🔴 STRONG-OB";
                modelSubtitle = "Type 2: Classic Opposite-Color OB";
            } else if (sweepHigh) {
                theme = "COND";
                badgeTitle = "⚡ COND-OB";
                modelSubtitle = "Type 6: Sweep+BOS Leg OB";
            } else {
                theme = "WEAK";
                badgeTitle = "🟠 WEAK-OB (SWEEP REQ)";
                modelSubtitle = "Type 1: Momentum Same-Color OB";
            }

            let isMitigated = false;
            let mitIdx = null;
            let mitTime = null;

            for (let k = i + 1; k < candles.length; k++) {
                if (candles[k].high >= obBottom) {
                    isMitigated = true;
                    mitIdx = k;
                    mitTime = candles[k].time;
                    break;
                }
            }

            obList.push({
                side: "BEARISH",
                theme: theme,
                badgeTitle: badgeTitle,
                modelSubtitle: modelSubtitle,
                startIdx: i - 2,
                startTime: c1.time,
                top: obTop,
                bottom: obBottom,
                mid: obMid,
                isMitigated: isMitigated,
                mitIdx: mitIdx,
                mitTime: mitTime
            });
            lastObIndex = i;
        }
    }

    detectedHermesOrderBlocks = obList.slice(-7);
    drawHermesOrderBlocks();
}"""

code = re.sub(old_compute_func_regex, new_compute_func, code)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(code)
print("[OK] app.js updated with refined detection and HUD minimization")

# ----------------- 2. PATCH TRADE.HTML -----------------
with open(trade_html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Make 1H the default active button instead of 15m
html = html.replace(
    '<button class="tf-btn active" onclick="setTimeframe(\'15m\', this)">15m</button>\n                    <button class="tf-btn" onclick="setTimeframe(\'1h\', this)">1H</button>',
    '<button class="tf-btn" onclick="setTimeframe(\'15m\', this)">15m</button>\n                    <button class="tf-btn active" onclick="setTimeframe(\'1h\', this)">1H</button>'
)

# Bump cache buster
html = re.sub(r'app\.js\?v=[^"]+', 'app.js?v=hermes_msob_boxes_v6', html)

with open(trade_html_path, "w", encoding="utf-8") as f:
    f.write(html)
print("[OK] trade.html updated with 1H default and v6 cache buster")
