import re

app_js_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace computeHermesOrderBlocks with wide multi-bar swing pivot engine
old_compute_regex = r"function computeHermesOrderBlocks\(candles\) \{[\s\S]*?detectedHermesOrderBlocks = obList\.slice\(-7\);\s*drawHermesOrderBlocks\(\);\s*\}"

new_compute = """function computeHermesOrderBlocks(candles) {
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
    // Scan across the wider visible chart history (up to 180 bars)
    const scanLookback = Math.min(candles.length - 4, 180);
    const startIdx = Math.max(6, candles.length - scanLookback);
    let lastObIndex = -999;

    for (let i = startIdx; i < candles.length - 1; i++) {
        const c1 = candles[i - 2];
        const c2 = candles[i - 1];
        const c3 = candles[i];

        // Wide separation filter: at least 12 bars between structural OBs across the chart
        if ((i - lastObIndex) < 12) continue;

        // Swing Pivot Windows
        const win = 4;
        let isSwingHigh = true;
        let isSwingLow = true;
        for (let w = 1; w <= win; w++) {
            if ((i - 2 - w) >= 0) {
                if (candles[i - 2 - w].high > c1.high) isSwingHigh = false;
                if (candles[i - 2 - w].low < c1.low) isSwingLow = false;
            }
        }
        if (c2.high > c1.high) isSwingHigh = false;
        if (c2.low < c1.low) isSwingLow = false;

        const dispBull = (c2.close - c2.open) >= (atr * 0.85) || (c3.close - c3.open) >= (atr * 0.85);
        const dispBear = (c2.open - c2.close) >= (atr * 0.85) || (c3.open - c3.close) >= (atr * 0.85);
        const sweepLow = c2.low < c1.low;
        const sweepHigh = c2.high > c1.high;

        // ---------------- BULLISH / DEMAND CANDLE EVALUATION ----------------
        if ((dispBull && (isSwingLow || sweepLow)) || (sweepLow && (c2.close > c1.high))) {
            const isC1Bear = c1.close < c1.open;
            let obTop = c1.high;
            let obBottom = sweepLow ? Math.min(c1.low, c2.low) : c1.low;
            if (obTop - obBottom < atr * 0.25) {
                obBottom = obTop - (atr * 0.40);
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
        if ((dispBear && (isSwingHigh || sweepHigh)) || (sweepHigh && (c2.close < c1.low))) {
            const isC1Bull = c1.close > c1.open;
            let obTop = sweepHigh ? Math.max(c1.high, c2.high) : c1.high;
            let obBottom = c1.low;
            if (obTop - obBottom < atr * 0.25) {
                obTop = obBottom + (atr * 0.40);
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

code = re.sub(old_compute_regex, new_compute, code)

# Ensure cache-buster updated in trade.html
trade_html_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\trade.html"
with open(trade_html_path, "r", encoding="utf-8") as f:
    html = f.read()

html = re.sub(r'app\.js\?v=[^"]+', 'app.js?v=hermes_msob_boxes_v7', html)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(code)
with open(trade_html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("[OK] Successfully updated app.js with wide swing-pivot detection and trade.html to v7")
