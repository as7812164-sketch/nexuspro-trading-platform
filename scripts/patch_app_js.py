import re

file_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\js\app.js"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update indicatorsState to smc: true, and declare detectedHermesOrderBlocks
code = code.replace(
    "let indicatorsState = { ema: false, vol: true, smc: false };",
    "let indicatorsState = { ema: false, vol: true, smc: true };\nlet detectedHermesOrderBlocks = [];"
)

# 2. Hook drawHermesOrderBlocks to timescale changes in initChart()
old_timescale_sync = """    chart.timeScale().subscribeVisibleLogicalRangeChange(repositionMeasureOverlay);
    chart.timeScale().subscribeVisibleTimeRangeChange(repositionMeasureOverlay);"""

new_timescale_sync = """    chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
        repositionMeasureOverlay();
        drawHermesOrderBlocks();
    });
    chart.timeScale().subscribeVisibleTimeRangeChange(() => {
        repositionMeasureOverlay();
        drawHermesOrderBlocks();
    });"""

code = code.replace(old_timescale_sync, new_timescale_sync)

# 3. Hook drawHermesOrderBlocks to handleChartResize()
old_resize = """        repositionMeasureOverlay();
    }
}"""

new_resize = """        repositionMeasureOverlay();
        drawHermesOrderBlocks();
    }
}"""

code = code.replace(old_resize, new_resize, 1)

# 4. In renderIndicators, replace updateSmcLevels with computeHermesOrderBlocks
code = code.replace(
    "updateSmcLevels(candles);",
    "computeHermesOrderBlocks(candles);"
)

# 5. Replace updateSmcLevels function and toggleSmcLevels with true TradingView SVG Box Engine
old_smc_block = """function updateSmcLevels(candles) {
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

new_smc_block = """// ============================================================================
// HERMES MS-OB 7-MODEL CANDLE-ANCHORED RECTANGULAR BOX ENGINE (MATCHING TRADINGVIEW)
// ============================================================================

function computeHermesOrderBlocks(candles) {
    // Purge any lingering price lines
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
    // Scan up to 120 most recent bars
    const scanLookback = Math.min(candles.length - 3, 100);
    const startIdx = Math.max(3, candles.length - scanLookback);

    for (let i = startIdx; i < candles.length - 1; i++) {
        const c1 = candles[i - 2];
        const c2 = candles[i - 1];
        const c3 = candles[i];

        // ---------------- BULLISH / DEMAND CANDLE EVALUATION ----------------
        const dispBull = (c2.close - c2.open) >= (atr * 0.75);
        const fvgBull = c3.low > c1.high && (c3.low - c1.high) >= (atr * 0.10);

        if (dispBull && (fvgBull || (c2.close - c2.open) >= (atr * 1.15))) {
            const isC1Bear = c1.close < c1.open;
            const isSweep = c2.low < c1.low;
            const isOutsideBar = (c1.high >= (candles[i - 3]?.high || 0)) && (c1.low <= (candles[i - 3]?.low || 0));

            let obTop = c1.high;
            let obBottom = isSweep ? c2.low : c1.low;
            if (obTop - obBottom < atr * 0.15) {
                obBottom = obTop - (atr * 0.25);
            }
            const obMid = (obTop + obBottom) / 2.0;

            let theme = "COND";
            let badgeTitle = "⚡ COND-OB";
            let modelSubtitle = "Type 6: Sweep+BOS Leg OB";

            if (isSweep) {
                theme = "COND";
                badgeTitle = "⚡ COND-OB";
                modelSubtitle = "Type 6: Sweep+BOS Leg OB";
            } else if (isC1Bear) {
                theme = "STRONG_BULL";
                badgeTitle = "🟢 STRONG-OB";
                modelSubtitle = "Type 2: Classic Opposite-Color OB";
            } else if (isOutsideBar) {
                theme = "WEAK";
                badgeTitle = "🟠 WEAK-OB (SWEEP REQ)";
                modelSubtitle = "Type 3: Outside Bar OB";
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
        }

        // ---------------- BEARISH / SUPPLY CANDLE EVALUATION ----------------
        const dispBear = (c2.open - c2.close) >= (atr * 0.75);
        const fvgBear = c1.low > c3.high && (c1.low - c3.high) >= (atr * 0.10);

        if (dispBear && (fvgBear || (c2.open - c2.close) >= (atr * 1.15))) {
            const isC1Bull = c1.close > c1.open;
            const isSweep = c2.high > c1.high;
            const isOutsideBar = (c1.high >= (candles[i - 3]?.high || 0)) && (c1.low <= (candles[i - 3]?.low || 0));

            let obTop = isSweep ? c2.high : c1.high;
            let obBottom = c1.low;
            if (obTop - obBottom < atr * 0.15) {
                obTop = obBottom + (atr * 0.25);
            }
            const obMid = (obTop + obBottom) / 2.0;

            let theme = "STRONG_BEAR";
            let badgeTitle = "🔴 STRONG-OB";
            let modelSubtitle = "Type 2: Classic Opposite-Color OB";

            if (isSweep) {
                theme = "COND";
                badgeTitle = "⚡ COND-OB";
                modelSubtitle = "Type 6: Sweep+BOS Leg OB";
            } else if (isC1Bull) {
                theme = "STRONG_BEAR";
                badgeTitle = "🔴 STRONG-OB";
                modelSubtitle = "Type 2: Classic Opposite-Color OB";
            } else if (isOutsideBar) {
                theme = "WEAK";
                badgeTitle = "🟠 WEAK-OB (SWEEP REQ)";
                modelSubtitle = "Type 3: Outside Bar OB";
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
        }
    }

    // Keep up to 8 of the cleanest recent Order Blocks (both active & mitigated)
    detectedHermesOrderBlocks = obList.slice(-8);
    drawHermesOrderBlocks();
}

function drawHermesOrderBlocks() {
    const svg = document.getElementById("hermesObOverlaySvg");
    const badgesContainer = document.getElementById("hermesObBadgesContainer");
    const watermark = document.getElementById("hermesIndicatorWatermark");
    if (!svg || !badgesContainer) return;

    if (!indicatorsState.smc) {
        svg.innerHTML = "";
        badgesContainer.innerHTML = "";
        if (watermark) watermark.style.display = "none";
        return;
    }
    if (watermark) watermark.style.display = "flex";

    if (!chart || !candleSeries || !detectedHermesOrderBlocks || detectedHermesOrderBlocks.length === 0) {
        svg.innerHTML = "";
        badgesContainer.innerHTML = "";
        return;
    }

    const container = document.getElementById("tradingview_chart");
    const containerW = container ? container.clientWidth : (window.innerWidth || 800);
    const containerH = container ? container.clientHeight : 340;
    const priceScaleWidth = 65; // standard right price axis margin

    let svgHtml = "";
    let badgesHtml = "";

    const lastCandle = currentFullCandles && currentFullCandles.length > 0 ? currentFullCandles[currentFullCandles.length - 1] : null;
    let lastX = null;
    if (lastCandle) {
        try { lastX = chart.timeScale().timeToCoordinate(lastCandle.time); } catch(e) {}
        if (lastX === null || lastX === undefined) {
            try { lastX = chart.timeScale().logicalToCoordinate(currentFullCandles.length - 1); } catch(e) {}
        }
    }
    if (lastX === null || lastX === undefined) lastX = containerW - 100;

    for (let i = 0; i < detectedHermesOrderBlocks.length; i++) {
        const ob = detectedHermesOrderBlocks[i];

        // 1. Convert Prices to Y Coordinates
        let yTop = null, yBottom = null, yMid = null;
        try {
            yTop = candleSeries.priceToCoordinate(ob.top);
            yBottom = candleSeries.priceToCoordinate(ob.bottom);
            yMid = candleSeries.priceToCoordinate(ob.mid);
        } catch(e) {}

        if (yTop === null || yBottom === null || yTop === undefined || yBottom === undefined) continue;

        const boxY = Math.min(yTop, yBottom);
        const boxHeight = Math.max(5, Math.abs(yBottom - yTop));
        const midY = (yMid !== null && yMid !== undefined) ? yMid : (boxY + boxHeight / 2);

        if (boxY + boxHeight < -50 || boxY > containerH + 50) continue;

        // 2. Convert Time to X Start
        let xStart = null;
        if (ob.startTime) {
            try { xStart = chart.timeScale().timeToCoordinate(ob.startTime); } catch(e) {}
        }
        if ((xStart === null || xStart === undefined) && ob.startIdx !== undefined) {
            try { xStart = chart.timeScale().logicalToCoordinate(ob.startIdx); } catch(e) {}
        }
        if (xStart === null || xStart === undefined) {
            xStart = -100;
        }

        // 3. Convert Time to X End
        let xEnd = null;
        if (ob.isMitigated && ob.mitTime) {
            try { xEnd = chart.timeScale().timeToCoordinate(ob.mitTime); } catch(e) {}
            if ((xEnd === null || xEnd === undefined) && ob.mitIdx !== undefined) {
                try { xEnd = chart.timeScale().logicalToCoordinate(ob.mitIdx); } catch(e) {}
            }
        }
        if (xEnd === null || xEnd === undefined) {
            xEnd = Math.max(lastX + 45, containerW - priceScaleWidth);
        }

        const maxRight = containerW - priceScaleWidth;
        const renderXStart = Math.max(-10, xStart);
        const renderXEnd = Math.min(maxRight, Math.max(renderXStart + 10, xEnd));
        const boxWidth = renderXEnd - renderXStart;

        if (boxWidth <= 2 || renderXEnd < 0 || renderXStart > maxRight) continue;

        // 4. Color theme matching TradingView Image 2
        let strokeColor = "#2979FF";
        let fillColor = "rgba(41, 121, 255, 0.20)";
        let badgeBg = "#2979FF";
        let badgeBorder = "#1E40AF";
        let badgeIcon = "⚡";

        if (ob.theme === "STRONG_BEAR") {
            strokeColor = "#EF5350";
            fillColor = "rgba(239, 83, 80, 0.22)";
            badgeBg = "#EF5350";
            badgeBorder = "#B91C1C";
            badgeIcon = "🔴";
        } else if (ob.theme === "STRONG_BULL") {
            strokeColor = "#00E676";
            fillColor = "rgba(0, 230, 118, 0.20)";
            badgeBg = "#00C853";
            badgeBorder = "#047857";
            badgeIcon = "🟢";
        } else if (ob.theme === "WEAK") {
            strokeColor = "#FF9100";
            fillColor = "rgba(255, 145, 0, 0.18)";
            badgeBg = "#FF9100";
            badgeBorder = "#D97706";
            badgeIcon = "🟠";
        }

        // 5. SVG Rectangle & 50% MT Line
        svgHtml += `
            <g class="hermes-ob-group" data-id="${i}">
                <rect x="${renderXStart.toFixed(1)}" y="${boxY.toFixed(1)}" width="${boxWidth.toFixed(1)}" height="${boxHeight.toFixed(1)}"
                      fill="${fillColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2" />
                <line x1="${renderXStart.toFixed(1)}" y1="${midY.toFixed(1)}" x2="${renderXEnd.toFixed(1)}" y2="${midY.toFixed(1)}"
                      stroke="${strokeColor}" stroke-width="1.2" stroke-dasharray="4,3" opacity="0.85" />
            </g>
        `;

        // 6. Floating Badge anchored to top-left of box
        const badgeX = Math.max(10, Math.min(renderXStart + 4, maxRight - 150));
        const badgeY = (boxY > 32) ? (boxY - 18) : (boxY + 3);

        badgesHtml += `
            <div style="position:absolute; left:${badgeX.toFixed(1)}px; top:${badgeY.toFixed(1)}px; background:${badgeBg}; border:1px solid ${badgeBorder}; border-radius:3px; padding:2px 7px; box-shadow:0 2px 7px rgba(0,0,0,0.6); pointer-events:none; z-index:4; white-space:nowrap;">
                <div style="font-size:10px; font-weight:800; color:#FFFFFF; line-height:1.2; display:flex; align-items:center; gap:4px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                    <span>${badgeIcon}</span>
                    <span>${ob.badgeTitle}</span>
                </div>
                <div style="font-size:8.5px; font-weight:600; color:rgba(255,255,255,0.92); line-height:1.15; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                    ${ob.modelSubtitle}
                </div>
            </div>
        `;
    }

    svg.innerHTML = svgHtml;
    badgesContainer.innerHTML = badgesHtml;
}"""

if old_smc_block in code:
    code = code.replace(old_smc_block, new_smc_block)
    print("[OK] Replaced updateSmcLevels with computeHermesOrderBlocks and drawHermesOrderBlocks")
else:
    print("[ERROR] old_smc_block not matched directly!")

# 6. Update toggleSmcLevels to trigger drawHermesOrderBlocks
old_toggle_smc = """function toggleSmcLevels() {
    indicatorsState.smc = !indicatorsState.smc;
    const btn = document.getElementById("btnToggleSmc");
    if (btn) btn.classList.toggle("active", indicatorsState.smc);
    renderIndicators(isReplayMode ? replayCandles.slice(0, replayIndex) : currentFullCandles);
}"""

new_toggle_smc = """function toggleSmcLevels() {
    indicatorsState.smc = !indicatorsState.smc;
    const btn = document.getElementById("btnToggleSmc");
    if (btn) btn.classList.toggle("active", indicatorsState.smc);
    const watermark = document.getElementById("hermesIndicatorWatermark");
    if (watermark) watermark.style.display = indicatorsState.smc ? "flex" : "none";
    drawHermesOrderBlocks();
}"""

if old_toggle_smc in code:
    code = code.replace(old_toggle_smc, new_toggle_smc)
    print("[OK] Updated toggleSmcLevels")
else:
    print("[WARN] old_toggle_smc not found directly")

# 7. Remove redundant Mean Threshold line from drawStrategyOnChart
old_mt_draw = """    // 4. Mean Threshold Line (if setup / OB)
    const mt = Number(item.mean_threshold || item.mt || 0);
    if (mt > 0) {
        const mtLine = candleSeries.createPriceLine({
            price: mt,
            color: '#F59E0B',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            axisLabelVisible: true,
            title: `⚡ 50% MT: $${mt.toFixed(4)}`
        });
        currentChartPriceLines.push(mtLine);
    }"""

if old_mt_draw in code:
    code = code.replace(old_mt_draw, "    // 50% Mean Threshold line is now rendered cleanly inside the Hermes Order Block box")
    print("[OK] Removed redundant 50% MT price line from drawStrategyOnChart")
else:
    print("[WARN] old_mt_draw not found directly")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("[SUCCESS] static/js/app.js patched successfully")
