# ⚡ NEXUSPRO — Institutional Futures & Deca Compounding Terminal

A high-performance crypto trading platform featuring **100% Bitget Pro layout, format, and UI**, integrated with the **BB 2.0 ($47,389.77 USDT)** Deca Compounding Engine.

---

## 🏛️ Platform Highlights

1. **Brand**: **NexusPro** (Bitget Pro Dark Obsidian Theme `#080B11`, Bitget Teal `#00DFC0`).
2. **Paper Trading Capital**: **$500.00 USDT** distributed equally across **10 Isolated Deca Sections** ($50.00 each).
3. **Target Compounding Milestone**: **$47,389.77 USDT (+9,378%)** based on the verified 6-month Out-Of-Sample test.
4. **Strategy Core**: **BB 2.0 (Booming Bulls Liquidity Masterclass)**:
   - Previous Day High (PDH) & Previous Day Low (PDL) sweeps.
   - 15m Extreme Order Block + Fair Value Gap (FVG) confirmation.
   - 50% Mean Threshold (MT) limit entry fills.
   - 0.15% Anti-Hunt Stop Loss buffer.
   - Stepped Trailing SL Ladder (+1.0R ➔ +0.2R BE Lock, +1.5R ➔ +1.0R Lock).
5. **Deca Compounding Isolation**:
   - 20 Champions paired across 10 sections (e.g. Sec 1: BTC/ETH, Sec 9: 1000PEPE/APT, Sec 10: ARB/FET).
   - Zero cross-section contamination: if one coin hits a stop loss, other sections keep compounding smoothly.

---

## 📱 Page Format (Bitget Pro UX)

| Route | Page | Description |
| :--- | :--- | :--- |
| `/` or `/trade` | **Futures Trading Terminal** | TradingView Lightweight Candlestick chart (1m to 1D), real-time Order Book depth ladder, 5x-100x Isolated Leverage Desk, and Bottom Positions & Trade History dock. |
| `/markets` | **Markets Overview** | 24h Ticker Carousel (BTC, ETH, SOL, XRP), category filter pills (Top-20 Champions, Gainers, Losers, Volume), and live searchable table with 1-click "Trade" action. |
| `/deca` | **BB 2.0 Deca Compounding Hub** | Live tracking of all 10 sections ($50 initial each), real-time BB 2.0 scanner radar, milestone meter toward $47k, and simulation reset tools. |
| `/assets` | **Assets & Wallet** | Total equity valuation, available margin, section balance breakdown, and paper trading tools. |

---

## 🚀 How to Run

Double-click `start_nexuspro.bat` or run:

```bash
cd C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform
python -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

Open your browser at:
`http://localhost:8080` (or `http://localhost:8080/trade`)
