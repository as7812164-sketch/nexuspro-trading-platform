/**
 * NEXUSPRO • TRADINGVIEW CHART TERMINAL COMPONENT (ISOLATED)
 * 1:1 Parity with Sample Mobile Architecture + HERMES MS-OB v2.0 GOLDEN Indicator
 * Features:
 *  - LightweightCharts v4 Candlestick Rendering
 *  - 1000 Deep Candlestick History Loading (Proxy + Global Feeds)
 *  - Live Candle Countdown Timer on Price Pill
 *  - Dynamic Top Bar (Title & Coin Logo updates on any symbol tap)
 *  - HERMES MS-OB v2.0 GOLDEN Indicator (Canvas Primitive Attached to Candles):
 *      * 7-Model Order Block Architecture (Types 1-7: Strong, Conditional & Weak)
 *      * Body-Close Invalidation & First Tap Tracking
 *      * Solid (Strong/Cond) & Dashed (Weak) OB Zones + 50% MT Dashed Midline
 *      * 100% Transparent Floating Labels (Zero Candle Obstruction Protocol)
 *      * Watermark: ⚡ Hermes MS-OB v2.0 GOLDEN
 *  - Bar Replay Simulator & Orientation Switcher
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';
import { connector } from '../core/websocket.js';

// IST (Indian Standard Time, UTC+5:30) 24-Hour Formatter Functions
const MONTH_NAMES_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function parseToUnixSec(time) {
  if (time === null || time === undefined) return null;
  if (typeof time === 'number') {
    if (isNaN(time) || !isFinite(time)) return null;
    return time > 1e11 ? Math.floor(time / 1000) : Math.floor(time);
  }
  if (time instanceof Date) {
    const ms = time.getTime();
    return isNaN(ms) ? null : Math.floor(ms / 1000);
  }
  if (typeof time === 'object' && time.year) {
    const d = new Date(Date.UTC(time.year, (time.month || 1) - 1, time.day || 1));
    return isNaN(d.getTime()) ? null : Math.floor(d.getTime() / 1000);
  }
  const parsed = new Date(time).getTime();
  return isNaN(parsed) ? null : Math.floor(parsed / 1000);
}

function formatISTTime(time) {
  const sec = parseToUnixSec(time);
  if (sec === null) return '';

  // India Standard Time: strictly UTC + 5 hours 30 minutes (+19800s)
  const istDate = new Date((sec + 19800) * 1000);
  const day = String(istDate.getUTCDate()).padStart(2, '0');
  const month = MONTH_NAMES_SHORT[istDate.getUTCMonth()];
  const year = String(istDate.getUTCFullYear()).slice(-2);
  const hours = String(istDate.getUTCHours()).padStart(2, '0');
  const minutes = String(istDate.getUTCMinutes()).padStart(2, '0');

  // Format: "05 Nov '26  21:40" (24-hour institutional format)
  return `${day} ${month} '${year}  ${hours}:${minutes}`;
}

function formatISTTickMark(time, tickMarkType) {
  const sec = parseToUnixSec(time);
  if (sec === null) return null;

  const istDate = new Date((sec + 19800) * 1000);
  const hours = String(istDate.getUTCHours()).padStart(2, '0');
  const minutes = String(istDate.getUTCMinutes()).padStart(2, '0');
  const seconds = String(istDate.getUTCSeconds()).padStart(2, '0');
  const day = istDate.getUTCDate();
  const month = MONTH_NAMES_SHORT[istDate.getUTCMonth()];
  const year = istDate.getUTCFullYear();

  switch (tickMarkType) {
    case 0: // Year
      return String(year);
    case 1: // Month
      return month;
    case 2: // DayOfMonth
      return String(day);
    case 3: // Time (24h)
      return `${hours}:${minutes}`;
    case 4: // TimeWithSeconds (24h)
      return `${hours}:${minutes}:${seconds}`;
    default:
      return `${hours}:${minutes}`;
  }
}

export class ChartTerminal {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.chart = null;
    this.candleSeries = null;
    this.volumeSeries = null;
    this.rawCandles = [];
    this.replayIndex = 0;
    this.countdownTimer = null;
    this.activeIndicatorLines = []; // Legacy line tracking (purged)
    this.tradePriceLines = []; // Active Trade Execution Lines (Entry, TP1, TP2, Hard SL)
    this.smcCanvas = null;
    this.smcCtx = null;
    this.currentOrderBlocks = [];
    this.smcIndicatorEnabled = (localStorage.getItem('nexuspro_msob_enabled') !== 'false');
    this.init();
  }

  init() {
    this.renderShell();
    this.bindEvents();
  }

  bindEvents() {
    bus.on('symbol:changed', (sym) => {
      this.updateHeaderInfo(sym);
      this.loadDataForCurrent();
    });

    bus.on('tf:changed', (tf) => {
      this.updateTfUI(tf);
      this.loadDataForCurrent();
    });

    bus.on('kline:live_candle', (candle) => this.onLiveCandle(candle));
    bus.on('orientation:changed', (mode) => this.applyOrientation(mode));
    bus.on('position:updated', () => {
      if (this.rawCandles && this.rawCandles.length > 0) {
        this.renderTradeExecutionHighlight(this.rawCandles);
      }
    });
    bus.on('view:changed', (view) => {
      if (view === 'chart') {
        setTimeout(() => {
          const container = this.el.querySelector('#tv-chart-box');
          if (this.chart && container) {
            const w = container.clientWidth || window.innerWidth || 390;
            const h = container.clientHeight || (window.innerHeight - 160) || 500;
            if (w > 0 && h > 0) {
              this.chart.resize(w, h);
            }
            if (this.rawCandles && this.rawCandles.length > 0) {
              this.candleSeries.setData(this.rawCandles);
              this.chart.timeScale().fitContent();
              this.chart.priceScale('right').applyOptions({ autoScale: true });
            } else {
              this.loadDataForCurrent();
            }
            this.resizeSmcCanvas();
            this.drawSmcOverlay();
            if (this.rawCandles && this.rawCandles.length > 0) {
              this.renderTradeExecutionHighlight(this.rawCandles);
            }
          }
        }, 50);
      }
    });
  }

  updateHeaderInfo(symbol) {
    const item = state.watchlist.find(w => w.symbol === symbol) || { icon: symbol.slice(0, 3), iconBg: '#1e293b' };
    const titleEl = this.el.querySelector('.chart-symbol-title');
    const logoEl = this.el.querySelector('.coin-logo-mini');

    if (titleEl) {
      titleEl.textContent = `${symbol.replace('USDT', '')} / TetherUS`;
    }
    if (logoEl) {
      logoEl.textContent = item.icon;
      logoEl.style.background = item.iconBg;
    }

    // Update Quick Pair buttons active state
    this.el.querySelectorAll('.quick-pair-item').forEach(qp => {
      const qpSym = qp.getAttribute('data-quick-sym');
      if (qpSym === symbol) {
        qp.classList.add('active');
      } else {
        qp.classList.remove('active');
      }
    });

    // Update price scale precision based on coin price
    if (this.candleSeries) {
      const priceData = state.prices.get(symbol);
      const curPrice = priceData ? priceData.price : (item ? item.price : 100);
      const precision = curPrice < 0.01 ? 6 : (curPrice < 1.0 ? 4 : 2);
      const minMove = curPrice < 0.01 ? 0.000001 : (curPrice < 1.0 ? 0.0001 : 0.01);

      this.candleSeries.applyOptions({
        priceFormat: {
          type: 'price',
          precision: precision,
          minMove: minMove
        }
      });

      if (this.chart) {
        this.chart.priceScale('right').applyOptions({ autoScale: true });
      }
    }
  }

  updateTfUI(tf) {
    this.el.querySelectorAll('.tf-btn').forEach(b => {
      if (b.getAttribute('data-tf') === tf) {
        b.classList.add('active');
      } else {
        b.classList.remove('active');
      }
    });
  }

  renderShell() {
    const symbol = state.activeSymbol;
    const tf = state.activeTf;
    const item = state.watchlist.find(w => w.symbol === symbol) || { icon: '₿', iconBg: '#f7931a' };

    this.el.innerHTML = `
      <div class="chart-view-wrapper">
        <!-- Top Ticker Bar -->
        <div class="chart-top-bar">
          <div class="chart-symbol-badge" id="btn-chart-symbol-select" style="cursor: pointer;" title="Tap to switch coin">
            <div class="coin-logo-mini" style="background: ${item.iconBg};">${item.icon}</div>
            <span class="chart-symbol-title">${symbol.replace('USDT', '')} / TetherUS</span>
            <span class="chart-perp-badge">PERP</span>
          </div>

          <div class="chart-top-actions">
            <button class="chart-mode-pill ${this.smcIndicatorEnabled ? 'text-green active-smc' : ''}" id="btn-toggle-smc" title="Toggle Hermes MS-OB v2.0 GOLDEN (7-Model Order Blocks)" style="border: 1px solid ${this.smcIndicatorEnabled ? '#00e676' : 'rgba(255, 255, 255, 0.15)'}; color: ${this.smcIndicatorEnabled ? '#00e676' : '#94a3b8'}; font-weight: 700; background: ${this.smcIndicatorEnabled ? 'rgba(0, 230, 118, 0.22)' : 'rgba(255, 255, 255, 0.05)'};">
              ⚡ MS-OB: <span id="modular-smc-text">${this.smcIndicatorEnabled ? 'ON' : 'OFF'}</span>
            </button>
            <button class="chart-mode-pill" id="btn-toggle-rotate" title="Toggle Landscape/Portrait">
              🔄 ROTATE
            </button>
            <button class="chart-mode-pill ${state.replay.active ? 'text-cyan' : ''}" id="btn-toggle-replay">
              ⏮ REPLAY
            </button>
          </div>
        </div>

        <!-- OHLC Details Bar -->
        <div class="chart-ohlc-bar mono">
          <span>O <span class="ohlc-val" id="ohlc-o">0.00</span></span>
          <span>H <span class="ohlc-val" id="ohlc-h">0.00</span></span>
          <span>L <span class="ohlc-val" id="ohlc-l">0.00</span></span>
          <span>C <span class="ohlc-val" id="ohlc-c">0.00</span></span>
          <span id="ohlc-change" class="text-green">+0.00%</span>
        </div>

        <!-- Timeframe Toolbar -->
        <div class="tf-bar">
          ${['15m', '1h', '4h', '1d', '1w'].map(t => `
            <button class="tf-btn ${t === tf ? 'active' : ''}" data-tf="${t}">
              ${t.toUpperCase()}
            </button>
          `).join('')}
        </div>

        <!-- Canvas Container -->
        <div class="chart-canvas-container" id="tv-chart-box">
          <!-- Canvas Overlay for 100% Candle-Attached Hermes MS-OB v2.0 GOLDEN Order Blocks -->
          <canvas id="smc-canvas-overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 5;"></canvas>

          <!-- Price & Countdown Badge -->
          <div id="chart-live-badge" style="position: absolute; right: 0; top: 55%; transform: translateY(-50%); z-index: 20; display: flex; flex-direction: column; align-items: flex-end; background: #00c087; color: #000000; padding: 3px 6px; font-weight: 800; border-radius: 4px 0 0 4px; font-family: var(--font-mono); box-shadow: -2px 0 8px rgba(0, 192, 135, 0.4);">
            <div id="badge-price" style="font-size: 11px; line-height: 1.1;">0.00</div>
            <div id="badge-timer" style="font-size: 9px; line-height: 1.1; font-weight: 700; opacity: 0.9;">02:40</div>
          </div>
        </div>

        <!-- Floating Replay Controls -->
        <div class="chart-replay-dock" id="replay-dock" style="display: ${state.replay.active ? 'flex' : 'none'};">
          <button class="replay-btn" id="btn-replay-prev" title="Step Back">⏮</button>
          <button class="replay-btn" id="btn-replay-play" title="Play/Pause">▶</button>
          <button class="replay-btn" id="btn-replay-next" title="Step Forward">⏭</button>
          <span class="replay-step-info mono" id="replay-progress">BAR 0/0</span>
          <button class="replay-btn" id="btn-replay-exit" style="color: #ef4444;" title="Exit Replay">✕</button>
        </div>

        <!-- Drawing Tools Drawer -->
        <div class="tools-drawer" id="tools-drawer">
          <button class="tool-drawer-item" data-tool="demand_zone">
            <span>🔲</span> Demand Zone (OB Box)
          </button>
          <button class="tool-drawer-item" data-tool="trendline">
            <span>📏</span> Trendline
          </button>
          <button class="tool-drawer-item" data-tool="horiz_ray">
            <span>➖</span> Horizontal Ray (MS-OB Level)
          </button>
          <button class="tool-drawer-item" data-tool="fib">
            <span>📶</span> Fibonacci 50% MT
          </button>
          <button class="tool-drawer-item" data-tool="risk_reward">
            <span>⚖️</span> Long/Short Position Tool
          </button>
        </div>

        <!-- Bottom Quick Switcher Bar -->
        <div class="chart-bottom-quickbar">
          <div class="quick-pairs">
            <div class="quick-pair-item ${symbol === 'BTCUSDT' ? 'active' : ''}" data-quick-sym="BTCUSDT" data-quick-tf="1h">
              <span>BTCUSD</span>
              <span class="quick-pair-tf">1h</span>
            </div>
            <div class="quick-pair-item ${symbol === 'PAXGUSDT' ? 'active' : ''}" data-quick-sym="PAXGUSDT" data-quick-tf="15m">
              <span>GOLD</span>
              <span class="quick-pair-tf">15m</span>
            </div>
            <div class="quick-pair-item ${symbol === 'ETHUSDT' ? 'active' : ''}" data-quick-sym="ETHUSDT" data-quick-tf="1h">
              <span>ETHUSD</span>
              <span class="quick-pair-tf">1h</span>
            </div>
            <div class="quick-pair-item ${symbol === 'SOLUSDT' ? 'active' : ''}" data-quick-sym="SOLUSDT" data-quick-tf="1h">
              <span>SOLUSD</span>
              <span class="quick-pair-tf">1h</span>
            </div>
          </div>

          <div class="chart-tools-actions">
            <button class="tool-icon-btn" id="btn-open-tools" title="Drawing Tools">✏️</button>
            <button class="tool-icon-btn ${this.smcIndicatorEnabled ? 'active-smc' : ''}" id="btn-toggle-smc-bottom" title="Toggle Hermes MS-OB v2.0 GOLDEN" style="color: ${this.smcIndicatorEnabled ? '#00e676' : '#94a3b8'}; font-weight: 800; font-size: 11px; border: 1px solid ${this.smcIndicatorEnabled ? '#00e676' : '#232c3e'}; border-radius: 4px; padding: 2px 7px; background: ${this.smcIndicatorEnabled ? 'rgba(0, 230, 118, 0.22)' : '#121622'};"><span id="bottom-smc-label">⚡ MS-OB: ${this.smcIndicatorEnabled ? 'ON' : 'OFF'}</span></button>
            <button class="tool-icon-btn" id="btn-chart-fullscreen" title="Full Screen">⛶</button>
          </div>
        </div>
      </div>
    `;

    this.attachDomHandlers();
    this.createLightweightChart();
    this.startCountdownLoop();
  }

  attachDomHandlers() {
    // Timeframe Buttons
    this.el.querySelectorAll('.tf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tf = btn.getAttribute('data-tf');
        state.setTimeframe(tf);
        this.updateTfUI(tf);
      });
    });

    // Quick Pair Switcher
    this.el.querySelectorAll('.quick-pair-item').forEach(item => {
      item.addEventListener('click', () => {
        const sym = item.getAttribute('data-quick-sym');
        const tf = item.getAttribute('data-quick-tf');
        state.setTimeframe(tf);
        state.selectSymbol(sym);
      });
    });

    // Toggle Replay Button
    const btnReplay = this.el.querySelector('#btn-toggle-replay');
    if (btnReplay) {
      btnReplay.addEventListener('click', () => this.toggleReplayMode());
    }

    // Replay Controls
    const btnPlay = this.el.querySelector('#btn-replay-play');
    if (btnPlay) btnPlay.addEventListener('click', () => this.toggleReplayPlay());
    const btnNext = this.el.querySelector('#btn-replay-next');
    if (btnNext) btnNext.addEventListener('click', () => this.stepReplay(1));
    const btnPrev = this.el.querySelector('#btn-replay-prev');
    if (btnPrev) btnPrev.addEventListener('click', () => this.stepReplay(-1));
    const btnExit = this.el.querySelector('#btn-replay-exit');
    if (btnExit) btnExit.addEventListener('click', () => this.toggleReplayMode(false));

    // SMC Engine v1.0 Toggle Buttons (Top & Bottom Sync)
    const btnSmcTop = this.el.querySelector('#btn-toggle-smc');
    if (btnSmcTop) {
      btnSmcTop.addEventListener('click', () => this.toggleSmcMode());
    }
    const btnSmcBottom = this.el.querySelector('#btn-toggle-smc-bottom');
    if (btnSmcBottom) {
      btnSmcBottom.addEventListener('click', () => this.toggleSmcMode());
    }

    // Tools Drawer Toggle
    const btnTools = this.el.querySelector('#btn-open-tools');
    const drawer = this.el.querySelector('#tools-drawer');
    if (btnTools && drawer) {
      btnTools.addEventListener('click', () => {
        drawer.classList.toggle('open');
      });
    }

    // Tool item click
    this.el.querySelectorAll('.tool-drawer-item').forEach(item => {
      item.addEventListener('click', () => {
        const tool = item.getAttribute('data-tool');
        if (drawer) drawer.classList.remove('open');
        this.applyDrawingTool(tool);
      });
    });

    // Orientation Rotate
    const btnRotate = this.el.querySelector('#btn-toggle-rotate');
    if (btnRotate) {
      btnRotate.addEventListener('click', () => state.toggleOrientation());
    }

    // Symbol Back to Watchlist
    const btnSymbol = this.el.querySelector('#btn-chart-symbol-select');
    if (btnSymbol) {
      btnSymbol.addEventListener('click', () => state.setView('watchlist'));
    }

    // Fullscreen Toggle
    const btnFs = this.el.querySelector('#btn-chart-fullscreen');
    if (btnFs) {
      btnFs.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen().catch(() => {});
        }
      });
    }
  }

  createLightweightChart() {
    const container = this.el.querySelector('#tv-chart-box');
    if (!container) return;

    if (!window.LightweightCharts) {
      setTimeout(() => this.createLightweightChart(), 200);
      return;
    }

    const { createChart, ColorType } = window.LightweightCharts;

    this.chart = createChart(container, {
      width: container.clientWidth || 390,
      height: container.clientHeight || 500,
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#848e9c',
        fontFamily: 'JetBrains Mono, -apple-system, sans-serif',
        fontSize: 11
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)', style: 1 },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)', style: 1 }
      },
      crosshair: {
        mode: 0, // CrosshairMode.Normal: 100% Free-floating cursor (ZERO MAGNET SNAPPING)
        vertLine: {
          color: 'rgba(255, 255, 255, 0.3)',
          width: 1,
          style: 3,
          labelBackgroundColor: '#1e2538'
        },
        horzLine: {
          color: 'rgba(255, 255, 255, 0.3)',
          width: 1,
          style: 3,
          labelBackgroundColor: '#1e2538'
        }
      },
      rightPriceScale: {
        borderColor: '#1e222d',
        autoScale: true,
        scaleMargins: { top: 0.1, bottom: 0.2 }
      },
      localization: {
        locale: 'en-IN',
        dateFormat: "dd MMM 'yy",
        timeFormatter: (time) => formatISTTime(time)
      },
      timeScale: {
        borderColor: '#1e222d',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time, tickMarkType) => formatISTTickMark(time, tickMarkType)
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
      kineticScroll: { touch: true, mouse: false }
    });

    const priceData = state.prices.get(state.activeSymbol);
    const curPrice = priceData ? priceData.price : 100;
    const precision = curPrice < 0.01 ? 6 : (curPrice < 1.0 ? 4 : 2);
    const minMove = curPrice < 0.01 ? 0.000001 : (curPrice < 1.0 ? 0.0001 : 0.01);

    this.candleSeries = this.chart.addCandlestickSeries({
      upColor: '#00c087',
      downColor: '#f6465d',
      borderVisible: false,
      wickUpColor: '#00c087',
      wickDownColor: '#f6465d',
      priceFormat: {
        type: 'price',
        precision: precision,
        minMove: minMove
      }
    });

    this.chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !param.seriesData) return;
      const data = param.seriesData.get(this.candleSeries);
      if (data) {
        this.updateOhlcBar(data);
      }
    });

    // SMC Overlay Canvas setup
    this.smcCanvas = this.el.querySelector('#smc-canvas-overlay');
    if (this.smcCanvas) {
      this.smcCtx = this.smcCanvas.getContext('2d');
    }
    this.resizeSmcCanvas();

    // Redraw overlay synchronously whenever chart scrolls, zooms, pans, or resizes
    this.chart.timeScale().subscribeVisibleLogicalRangeChange(() => this.drawSmcOverlay());
    this.chart.timeScale().subscribeVisibleTimeRangeChange(() => this.drawSmcOverlay());

    window.addEventListener('resize', () => {
      if (this.chart && container) {
        const w = container.clientWidth || window.innerWidth || 390;
        const h = container.clientHeight || (window.innerHeight - 160) || 500;
        if (w > 0 && h > 0) {
          this.chart.resize(w, h);
        }
        this.resizeSmcCanvas();
        this.drawSmcOverlay();
      }
    });

    if (window.ResizeObserver) {
      const ro = new ResizeObserver((entries) => {
        for (let entry of entries) {
          const cr = entry.contentRect;
          if (cr.width > 0 && cr.height > 0 && this.chart) {
            this.chart.resize(cr.width, cr.height);
            this.resizeSmcCanvas();
            this.drawSmcOverlay();
          }
        }
      });
      ro.observe(container);
    }

    this.loadDataForCurrent();
  }

  resizeSmcCanvas() {
    if (!this.smcCanvas) return;
    const container = this.el.querySelector('#tv-chart-box');
    if (!container) return;
    const dpr = window.devicePixelRatio || 1;
    const width = container.clientWidth || 390;
    const height = container.clientHeight || 500;
    this.smcCanvas.width = width * dpr;
    this.smcCanvas.height = height * dpr;
    this.smcCanvas.style.width = width + 'px';
    this.smcCanvas.style.height = height + 'px';
    this.smcCtx = this.smcCanvas.getContext('2d');
    this.smcCtx.scale(dpr, dpr);
  }

  async loadDataForCurrent() {
    this._loadSeq = (this._loadSeq || 0) + 1;
    const reqId = this._loadSeq;
    const symbol = state.activeSymbol;
    const tf = state.activeTf;

    this.updateHeaderInfo(symbol);

    // 1. Immediately purge any legacy price lines so they NEVER lock the price scale
    if (this.activeIndicatorLines && this.candleSeries) {
      this.activeIndicatorLines.forEach(line => {
        try { this.candleSeries.removePriceLine(line); } catch (e) {}
      });
      this.activeIndicatorLines = [];
    }

    if (this.tradePriceLines && this.candleSeries) {
      this.tradePriceLines.forEach(line => {
        try { this.candleSeries.removePriceLine(line); } catch (e) {}
      });
      this.tradePriceLines = [];
    }
    if (this.candleSeries) {
      try { this.candleSeries.setMarkers([]); } catch (e) {}
    }

    // Reset overlay state during coin switch
    this.currentOrderBlocks = [];
    this.drawSmcOverlay();

    // 2. Fetch real klines (Direct VPS proxy first, fast ~200ms response)
    try {
      const liveCandles = await connector.fetchHistoricalKlines(symbol, tf, 1000);
      if (reqId !== this._loadSeq) return;
      if (liveCandles && liveCandles.length > 0 && !state.replay.active) {
        this.rawCandles = liveCandles;
        this.replayIndex = liveCandles.length;
        this.candleSeries.setData(liveCandles);
        if (liveCandles.length > 130) {
          this.chart.timeScale().setVisibleLogicalRange({
            from: liveCandles.length - 125,
            to: liveCandles.length + 6
          });
        } else {
          this.chart.timeScale().fitContent();
        }
        this.chart.priceScale('right').applyOptions({ autoScale: true });

        const last = liveCandles[liveCandles.length - 1];
        const cp = last ? last.close : 100;
        const prec = cp < 0.01 ? 6 : (cp < 1.0 ? 4 : 2);
        const mm = cp < 0.01 ? 0.000001 : (cp < 1.0 ? 0.0001 : 0.01);
        try {
          this.candleSeries.applyOptions({
            priceFormat: { type: 'price', precision: prec, minMove: mm }
          });
        } catch (e) {}
        this.updateOhlcBar(last);
        state.updatePrice(symbol, last.close);

        // Compute and render Hermes MS-OB v2.0 GOLDEN Order Blocks Overlay
        this.renderHermesSmcOverlay(liveCandles);
        return;
      }
    } catch (err) {
      console.warn('[ChartTerminal] Failed to fetch live klines, using fallback:', err);
    }

    // 3. Fallback only if network completely unavailable
    const fallbackCandles = connector.generateFallbackKlines(symbol, 200);
    this.rawCandles = fallbackCandles;
    this.replayIndex = fallbackCandles.length;

    if (this.candleSeries) {
      this.candleSeries.setData(fallbackCandles);
      this.chart.timeScale().fitContent();
      this.chart.priceScale('right').applyOptions({ autoScale: true });

      if (fallbackCandles.length > 0) {
        const last = fallbackCandles[fallbackCandles.length - 1];
        this.updateOhlcBar(last);
        state.updatePrice(symbol, last.close);
        this.renderHermesSmcOverlay(fallbackCandles);
      }
    }
  }

  onLiveCandle(candle) {
    if (state.replay.active) return;
    if (!candle) return;
    // CRITICAL: Reject candle if it belongs to a different coin!
    if (candle.symbol && candle.symbol !== state.activeSymbol) return;

    // Safety guard: reject extreme price anomalies from stale websockets
    if (this.rawCandles && this.rawCandles.length > 0) {
      const lastPrice = this.rawCandles[this.rawCandles.length - 1].close;
      if (lastPrice > 0) {
        const ratio = candle.close / lastPrice;
        if (ratio > 5.0 || ratio < 0.2) return;
      }
    }

    if (this.candleSeries) {
      this.candleSeries.update(candle);
      this.updateOhlcBar(candle);
      this.drawSmcOverlay();
    }
  }

  updateOhlcBar(c) {
    const elO = this.el.querySelector('#ohlc-o');
    const elH = this.el.querySelector('#ohlc-h');
    const elL = this.el.querySelector('#ohlc-l');
    const elC = this.el.querySelector('#ohlc-c');
    const elChg = this.el.querySelector('#ohlc-change');

    const curPrice = c.close;
    const p = curPrice < 0.01 ? 6 : (curPrice < 1.0 ? 4 : 2);

    if (elO) elO.textContent = c.open.toFixed(p);
    if (elH) elH.textContent = c.high.toFixed(p);
    if (elL) elL.textContent = c.low.toFixed(p);
    if (elC) elC.textContent = c.close.toFixed(p);

    if (elChg) {
      const diff = c.close - c.open;
      const pct = (diff / c.open) * 100;
      const isPos = pct >= 0;
      elChg.textContent = `${isPos ? '+' : ''}${pct.toFixed(2)}%`;
      elChg.className = isPos ? 'text-green' : 'text-red';
    }

    const badgePrice = this.el.querySelector('#badge-price');
    if (badgePrice) badgePrice.textContent = c.close.toFixed(p);
  }

  startCountdownLoop() {
    clearInterval(this.countdownTimer);
    this.countdownTimer = setInterval(() => {
      const tf = state.activeTf;
      let intervalSec = 3600;
      if (tf === '15m') intervalSec = 900;
      if (tf === '4h') intervalSec = 14400;
      if (tf === '1d') intervalSec = 86400;

      const nowSec = Math.floor(Date.now() / 1000);
      const remaining = intervalSec - (nowSec % intervalSec);
      const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
      const ss = String(remaining % 60).padStart(2, '0');

      const timerEl = this.el.querySelector('#badge-timer');
      if (timerEl) {
        timerEl.textContent = `${mm}:${ss}`;
      }
    }, 1000);
  }

  renderHermesSmcOverlay(candles) {
    // 1. Purge all legacy horizontal lines completely
    this.activeIndicatorLines.forEach(line => {
      try { this.candleSeries.removePriceLine(line); } catch (e) {}
    });
    this.activeIndicatorLines = [];

    // 2. Compute Hermes MS-OB v2.0 GOLDEN (7-Model Order Blocks)
    if (this.smcIndicatorEnabled) {
      this.currentOrderBlocks = this.calculateHermesSmcOrderBlocks(candles);
    } else {
      this.currentOrderBlocks = [];
    }

    // 3. Draw On-Chart Overlay
    this.drawSmcOverlay();

    // 4. Highlight Active Trade Execution (Entry Arrow, TP, BE Lock, Hard SL)
    this.renderTradeExecutionHighlight(candles);
  }

  /* ------------------------------------------------------------------------
     HERMES MS-OB v2.0 GOLDEN — 7-MODEL INSTITUTIONAL ORDER BLOCK DETECTOR
     - Zero Retail Indicators (No EMA, RSI, MACD, Bollinger Bands)
     - 7 Models: Type 6 Sweep+BOS, Type 7 Post-IDM, Type 4 Swing Origin,
       Type 2 Classic Opposite-Color, Type 3 C2 Breach, Type 1 Momentum,
       Type 5 Mid-Leg Internal
     - Body-Close Invalidation Rule & First Tap Freeze Tracking
     - 100% Transparent Floating Labels (Zero Candle Obstruction)
     ------------------------------------------------------------------------ */
  calculateHermesSmcOrderBlocks(candles) {
    if (!candles || candles.length < 30) {
      this.currentSmcSignals = [];
      this.currentFvgs = [];
      return [];
    }

    const n = candles.length;

    // 1. Wilder RMA 14-Period ATR (exact ta.atr(14) parity)
    const atrPeriod = 14;
    const trList = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      if (i === 0) {
        trList[i] = candles[i].high - candles[i].low;
      } else {
        const hl = candles[i].high - candles[i].low;
        const hc = Math.abs(candles[i].high - candles[i - 1].close);
        const lc = Math.abs(candles[i].low - candles[i - 1].close);
        trList[i] = Math.max(hl, hc, lc);
      }
    }

    const atrArr = new Float64Array(n);
    let initSum = 0;
    for (let i = 0; i < n; i++) {
      if (i < atrPeriod) {
        initSum += trList[i];
        atrArr[i] = initSum / (i + 1);
      } else {
        atrArr[i] = (atrArr[i - 1] * (atrPeriod - 1) + trList[i]) / atrPeriod;
      }
    }

    // 2. Track Swings (swingLen = 5), Liquidity Sweeps (35-bar), BOS & Inducement (IDM)
    const swingLen = 5;
    const minDispMult = 1.2;
    const minFvgMult = 0.15;
    const minWeakWickPct = 18.0;

    let lastShPrice = null;
    let lastSlPrice = null;
    let lastShBar = null;
    let lastSlBar = null;
    let lastIdmBull = null;
    let lastIdmBear = null;
    let bullSwept = false;
    let bearSwept = false;
    let idmBullSwept = false;
    let idmBearSwept = false;
    let bullSweepBar = -999;
    let bearSweepBar = -999;

    const rawObList = [];
    const signals = [];
    const fvgs = [];

    for (let i = 0; i < n; i++) {
      const atr = atrArr[i] || 0;

      // Swing pivot evaluation (swingLen = 5)
      const pIdx = i - swingLen;
      if (pIdx >= swingLen) {
        let isSh = true;
        let isSl = true;
        for (let w = 1; w <= swingLen; w++) {
          if (candles[pIdx - w].high >= candles[pIdx].high || candles[pIdx + w].high >= candles[pIdx].high) isSh = false;
          if (candles[pIdx - w].low <= candles[pIdx].low || candles[pIdx + w].low <= candles[pIdx].low) isSl = false;
        }
        if (isSh) { lastShPrice = candles[pIdx].high; lastShBar = pIdx; }
        if (isSl) { lastSlPrice = candles[pIdx].low; lastSlBar = pIdx; }
      }

      const curr = candles[i];

      // Liquidity Sweeps (35-bar window)
      if (lastSlPrice !== null && curr.low < lastSlPrice && curr.close > lastSlPrice) {
        bullSwept = true;
        bullSweepBar = i;
      }
      if (lastShPrice !== null && curr.high > lastShPrice && curr.close < lastShPrice) {
        bearSwept = true;
        bearSweepBar = i;
      }
      if (i - bullSweepBar > 35) bullSwept = false;
      if (i - bearSweepBar > 35) bearSwept = false;

      // Break of Structure (BOS) & Inducement (IDM)
      if (i > 0) {
        const prev = candles[i - 1];
        if (lastShPrice !== null && curr.close > lastShPrice && prev.close <= lastShPrice && lastSlBar !== null) {
          const lb = Math.min(100, Math.max(1, i - lastSlBar));
          let lowestLow = curr.low;
          for (let k = Math.max(0, i - lb + 1); k <= i; k++) {
            if (candles[k].low < lowestLow) lowestLow = candles[k].low;
          }
          lastIdmBull = lowestLow;
          idmBullSwept = false;
        }
        if (lastSlPrice !== null && curr.close < lastSlPrice && prev.close >= lastSlPrice && lastShBar !== null) {
          const lb = Math.min(100, Math.max(1, i - lastShBar));
          let highestHigh = curr.high;
          for (let k = Math.max(0, i - lb + 1); k <= i; k++) {
            if (candles[k].high > highestHigh) highestHigh = candles[k].high;
          }
          lastIdmBear = highestHigh;
          idmBearSwept = false;
        }
      }

      if (lastIdmBull !== null && curr.low < lastIdmBull) idmBullSwept = true;
      if (lastIdmBear !== null && curr.high > lastIdmBear) idmBearSwept = true;

      // 3-Candle Pattern on closed impulse (i <= n - 2)
      if (i >= 2 && i <= n - 2 && atr > 0) {
        const c1 = candles[i - 2];
        const c2 = candles[i - 1];
        const c3 = candles[i];

        // 3. BULLISH ORDER BLOCK CLASSIFICATION (Shoaib Khan 7 Models)
        const fvgBull = c3.low > c1.high && (c3.low - c1.high) >= (atr * minFvgMult);
        const dispBull = (c2.close - c2.open) >= (atr * minDispMult);

        if (fvgBull && dispBull) {
          const c1Bull = c1.close > c1.open;
          const c1Bear = c1.close < c1.open;
          const c2BreachLow = c2.low < c1.low;
          const isSwingOrigin = lastSlPrice !== null && Math.abs(c1.low - lastSlPrice) < (atr * 0.5);

          let modelNum = 1;
          let catName = 'WEAK';
          let badgeTitle = 'WEAK-OB (SWEEP REQ)';
          let modelSubtitle = 'Type 1: Momentum Same-Color OB';
          let borderCol = '#FF9100';
          let bgCol = 'rgba(255, 145, 0, 0.12)';
          let badgeIcon = '⚠️';

          if (bullSwept) {
            modelNum = 6;
            catName = 'STRONGEST_COND';
            badgeTitle = 'COND-OB';
            modelSubtitle = 'Type 6: Sweep+BOS Leg OB';
            borderCol = '#2979FF';
            bgCol = 'rgba(41, 121, 255, 0.18)';
            badgeIcon = '⚡';
          } else if (idmBullSwept && lastIdmBull !== null && c1.low < lastIdmBull) {
            modelNum = 7;
            catName = 'STRONGEST_COND';
            badgeTitle = 'COND-OB';
            modelSubtitle = 'Type 7: Post-IDM Decisional OB';
            borderCol = '#2979FF';
            bgCol = 'rgba(41, 121, 255, 0.18)';
            badgeIcon = '⚡';
          } else if (c2BreachLow) {
            modelNum = 3;
            catName = 'WEAK';
            badgeTitle = 'WEAK-OB (SWEEP REQ)';
            modelSubtitle = 'Type 3: Outlier C2 Low Breach';
            borderCol = '#FF9100';
            bgCol = 'rgba(255, 145, 0, 0.10)';
            badgeIcon = '⚠️';
          } else if (c1Bull) {
            modelNum = 1;
            catName = 'WEAK';
            badgeTitle = 'WEAK-OB (SWEEP REQ)';
            modelSubtitle = 'Type 1: Momentum Same-Color OB';
            borderCol = '#FF9100';
            bgCol = 'rgba(255, 145, 0, 0.10)';
            badgeIcon = '⚠️';
          } else if (c1Bear && isSwingOrigin) {
            modelNum = 4;
            catName = 'STRONG';
            badgeTitle = 'STRONG-OB';
            modelSubtitle = 'Type 4: Swing Origin OB';
            borderCol = '#00E676';
            bgCol = 'rgba(0, 230, 118, 0.16)';
            badgeIcon = '🛡️';
          } else if (c1Bear) {
            modelNum = 2;
            catName = 'STRONG';
            badgeTitle = 'STRONG-OB';
            modelSubtitle = 'Type 2: Classic Opposite-Color OB';
            borderCol = '#00E676';
            bgCol = 'rgba(0, 230, 118, 0.16)';
            badgeIcon = '🛡️';
          } else {
            modelNum = 5;
            catName = 'WEAK';
            badgeTitle = 'WEAK-OB (SWEEP REQ)';
            modelSubtitle = 'Type 5: Mid-Leg Internal OB';
            borderCol = '#FF9100';
            bgCol = 'rgba(255, 145, 0, 0.10)';
            badgeIcon = '⚠️';
          }

          const obTop = c1.high;
          const obBottom = c2BreachLow ? c2.low : c1.low;
          rawObList.push({
            side: 'BULLISH',
            createIdx: i,
            modelNum,
            catName,
            badgeTitle,
            modelSubtitle,
            badgeIcon,
            borderCol,
            bgCol,
            startIdx: i - 2,
            startTime: c1.time,
            top: obTop,
            bottom: obBottom,
            mid: (obTop + obBottom) / 2.0,
            isMitigated: false,
            isInvalidated: false,
            mitIdx: null,
            mitTime: null
          });
          fvgs.push({ startIdx: i - 2, startTime: c1.time, top: c3.low, bottom: c1.high, filledIdx: null, filledTime: null, bull: true });
        }

        // 4. BEARISH ORDER BLOCK CLASSIFICATION (Shoaib Khan 7 Models)
        const fvgBear = c3.high < c1.low && (c1.low - c3.high) >= (atr * minFvgMult);
        const dispBear = (c2.open - c2.close) >= (atr * minDispMult);

        if (fvgBear && dispBear) {
          const c1Bull = c1.close > c1.open;
          const c1Bear = c1.close < c1.open;
          const c2BreachHigh = c2.high > c1.high;
          const isSwingOrigin = lastShPrice !== null && Math.abs(c1.high - lastShPrice) < (atr * 0.5);

          let modelNum = 1;
          let catName = 'WEAK';
          let badgeTitle = 'WEAK-OB (SWEEP REQ)';
          let modelSubtitle = 'Type 1: Momentum Same-Color OB';
          let borderCol = '#FF5252';
          let bgCol = 'rgba(255, 82, 82, 0.12)';
          let badgeIcon = '⚠️';

          if (bearSwept) {
            modelNum = 6;
            catName = 'STRONGEST_COND';
            badgeTitle = 'COND-OB';
            modelSubtitle = 'Type 6: Sweep+BOS Leg OB';
            borderCol = '#D500F9';
            bgCol = 'rgba(213, 0, 249, 0.18)';
            badgeIcon = '⚡';
          } else if (idmBearSwept && lastIdmBear !== null && c1.high > lastIdmBear) {
            modelNum = 7;
            catName = 'STRONGEST_COND';
            badgeTitle = 'COND-OB';
            modelSubtitle = 'Type 7: Post-IDM Decisional OB';
            borderCol = '#D500F9';
            bgCol = 'rgba(213, 0, 249, 0.18)';
            badgeIcon = '⚡';
          } else if (c2BreachHigh) {
            modelNum = 3;
            catName = 'WEAK';
            badgeTitle = 'WEAK-OB (SWEEP REQ)';
            modelSubtitle = 'Type 3: Outlier C2 High Breach';
            borderCol = '#FF5252';
            bgCol = 'rgba(255, 82, 82, 0.10)';
            badgeIcon = '⚠️';
          } else if (c1Bear) {
            modelNum = 1;
            catName = 'WEAK';
            badgeTitle = 'WEAK-OB (SWEEP REQ)';
            modelSubtitle = 'Type 1: Momentum Same-Color OB';
            borderCol = '#FF5252';
            bgCol = 'rgba(255, 82, 82, 0.10)';
            badgeIcon = '⚠️';
          } else if (c1Bull && isSwingOrigin) {
            modelNum = 4;
            catName = 'STRONG';
            badgeTitle = 'STRONG-OB';
            modelSubtitle = 'Type 4: Swing Origin OB';
            borderCol = '#FF1744';
            bgCol = 'rgba(255, 23, 68, 0.16)';
            badgeIcon = '🛡️';
          } else if (c1Bull) {
            modelNum = 2;
            catName = 'STRONG';
            badgeTitle = 'STRONG-OB';
            modelSubtitle = 'Type 2: Classic Opposite-Color OB';
            borderCol = '#FF1744';
            bgCol = 'rgba(255, 23, 68, 0.16)';
            badgeIcon = '🛡️';
          } else {
            modelNum = 5;
            catName = 'WEAK';
            badgeTitle = 'WEAK-OB (SWEEP REQ)';
            modelSubtitle = 'Type 5: Mid-Leg Internal OB';
            borderCol = '#FF5252';
            bgCol = 'rgba(255, 82, 82, 0.10)';
            badgeIcon = '⚠️';
          }

          const obTop = c2BreachHigh ? c2.high : c1.high;
          const obBottom = c1.low;
          rawObList.push({
            side: 'BEARISH',
            createIdx: i,
            modelNum,
            catName,
            badgeTitle,
            modelSubtitle,
            badgeIcon,
            borderCol,
            bgCol,
            startIdx: i - 2,
            startTime: c1.time,
            top: obTop,
            bottom: obBottom,
            mid: (obTop + obBottom) / 2.0,
            isMitigated: false,
            isInvalidated: false,
            mitIdx: null,
            mitTime: null
          });
          fvgs.push({ startIdx: i - 2, startTime: c1.time, top: c1.low, bottom: c3.high, filledIdx: null, filledTime: null, bull: false });
        }
      }

      // 5. Evaluate Tap / Weak Wick Sweep >=18% / Body-Close Invalidation at bar i
      const rng = curr.high - curr.low;
      for (const ob of rawObList) {
        if (i <= ob.createIdx || ob.isInvalidated || ob.isMitigated) continue;
        if (ob.side === 'BULLISH') {
          if (curr.close < ob.bottom) {
            ob.isInvalidated = true;
            continue;
          }
          if (ob.catName === 'STRONG' || ob.catName === 'STRONGEST_COND') {
            if (curr.low <= ob.top && curr.close >= ob.bottom) {
              ob.isMitigated = true;
              ob.mitIdx = i;
              ob.mitTime = curr.time;
              signals.push({ idx: i, time: curr.time, price: curr.low, kind: 'STRONG_BUY' });
            }
          } else if (ob.catName === 'WEAK') {
            if (curr.low < ob.bottom && curr.close >= ob.bottom && curr.close > curr.open) {
              const wickPct = rng > 0 ? ((Math.min(curr.open, curr.close) - curr.low) / rng) * 100.0 : 0;
              if (wickPct >= minWeakWickPct) {
                ob.isMitigated = true;
                ob.mitIdx = i;
                ob.mitTime = curr.time;
                signals.push({ idx: i, time: curr.time, price: curr.low, kind: 'WEAK_BUY' });
              }
            }
          }
        } else {
          if (curr.close > ob.top) {
            ob.isInvalidated = true;
            continue;
          }
          if (ob.catName === 'STRONG' || ob.catName === 'STRONGEST_COND') {
            if (curr.high >= ob.bottom && curr.close <= ob.top) {
              ob.isMitigated = true;
              ob.mitIdx = i;
              ob.mitTime = curr.time;
              signals.push({ idx: i, time: curr.time, price: curr.high, kind: 'STRONG_SELL' });
            }
          } else if (ob.catName === 'WEAK') {
            if (curr.high > ob.top && curr.close <= ob.top && curr.close < curr.open) {
              const wickPct = rng > 0 ? ((curr.high - Math.max(curr.open, curr.close)) / rng) * 100.0 : 0;
              if (wickPct >= minWeakWickPct) {
                ob.isMitigated = true;
                ob.mitIdx = i;
                ob.mitTime = curr.time;
                signals.push({ idx: i, time: curr.time, price: curr.high, kind: 'WEAK_SELL' });
              }
            }
          }
        }
      }

      // Check FVG fill
      for (const f of fvgs) {
        if (i <= f.startIdx + 2 || f.filledIdx !== null) continue;
        if (f.bull && curr.low <= f.bottom) { f.filledIdx = i; f.filledTime = curr.time; }
        else if (!f.bull && curr.high >= f.top) { f.filledIdx = i; f.filledTime = curr.time; }
      }
    }

    this.currentSmcSignals = signals.slice(-30);
    this.currentFvgs = fvgs.filter(f => f.filledIdx === null || f.filledIdx >= n - 25).slice(-14);
    const validObs = rawObList.filter(ob => !ob.isInvalidated);
    return validObs.slice(-18);
  }

  /* ------------------------------------------------------------------------
     HERMES MS-OB v2.0 ON/OFF TOGGLE SWITCH CONTROLLER
     ------------------------------------------------------------------------ */
  toggleSmcMode() {
    this.smcIndicatorEnabled = !this.smcIndicatorEnabled;
    localStorage.setItem('nexuspro_msob_enabled', this.smcIndicatorEnabled ? 'true' : 'false');
    this.updateSmcUI();

    if (this.smcIndicatorEnabled) {
      const candles = (state.replay.active && this.rawCandles)
        ? this.rawCandles.slice(0, this.replayIndex)
        : this.rawCandles;
      if (candles && candles.length > 0) {
        this.currentOrderBlocks = this.calculateHermesSmcOrderBlocks(candles);
      }
    } else {
      this.currentOrderBlocks = [];
    }

    this.drawSmcOverlay();
  }

  updateSmcUI() {
    const topBtn = this.el.querySelector('#btn-toggle-smc');
    const topText = this.el.querySelector('#modular-smc-text');
    const btmBtn = this.el.querySelector('#btn-toggle-smc-bottom');
    const btmLabel = this.el.querySelector('#bottom-smc-label');

    if (topBtn) {
      if (this.smcIndicatorEnabled) {
        topBtn.classList.add('text-green', 'active-smc');
        topBtn.style.borderColor = '#00e676';
        topBtn.style.color = '#00e676';
        topBtn.style.background = 'rgba(0, 230, 118, 0.22)';
      } else {
        topBtn.classList.remove('text-green', 'active-smc');
        topBtn.style.borderColor = 'rgba(255, 255, 255, 0.15)';
        topBtn.style.color = '#94a3b8';
        topBtn.style.background = 'rgba(255, 255, 255, 0.05)';
      }
    }
    if (topText) topText.textContent = this.smcIndicatorEnabled ? 'ON' : 'OFF';

    if (btmBtn) {
      if (this.smcIndicatorEnabled) {
        btmBtn.classList.add('active-smc');
        btmBtn.style.borderColor = '#00e676';
        btmBtn.style.color = '#00e676';
        btmBtn.style.background = 'rgba(0, 230, 118, 0.22)';
      } else {
        btmBtn.classList.remove('active-smc');
        btmBtn.style.borderColor = '#232c3e';
        btmBtn.style.color = '#94a3b8';
        btmBtn.style.background = '#121622';
      }
    }
    if (btmLabel) btmLabel.textContent = `⚡ MS-OB: ${this.smcIndicatorEnabled ? 'ON' : 'OFF'}`;
  }

  /* ------------------------------------------------------------------------
     CANVAS OVERLAY DRAWING (HERMES MS-OB v2.0 GOLDEN • TRANSPARENT LABELS)
     ------------------------------------------------------------------------ */
  drawSmcOverlay() {
    if (!this.smcCtx || !this.chart || !this.candleSeries || !this.smcCanvas) return;
    const container = this.el.querySelector('#tv-chart-box');
    if (!container) return;
    const width = container.clientWidth || 390;
    const height = container.clientHeight || 500;

    this.smcCtx.clearRect(0, 0, width, height);
    if (!this.smcIndicatorEnabled) return;
    if ((!this.currentOrderBlocks || this.currentOrderBlocks.length === 0) && (!this.currentSmcSignals || this.currentSmcSignals.length === 0)) return;

    const timeScale = this.chart.timeScale();
    const ctx = this.smcCtx;
    const lastCandle = this.rawCandles && this.rawCandles.length > 0 ? this.rawCandles[this.rawCandles.length - 1] : null;
    const lastCoord = lastCandle ? timeScale.timeToCoordinate(lastCandle.time) : null;
    const rightChartEdge = (width > 65) ? (width - 65) : width;
    const placedLabels = [];

    for (const ob of this.currentOrderBlocks) {
      let xStart = ob.startTime ? timeScale.timeToCoordinate(ob.startTime) : null;
      if ((xStart === null || xStart === undefined) && ob.startIdx !== undefined) {
        try { xStart = timeScale.logicalToCoordinate(ob.startIdx); } catch (e) {}
      }
      if (xStart === null || xStart === undefined) xStart = -80;

      let xEnd = null;
      if (ob.isMitigated && ob.mitTime) {
        xEnd = timeScale.timeToCoordinate(ob.mitTime);
        if ((xEnd === null || xEnd === undefined) && ob.mitIdx !== undefined) {
          try { xEnd = timeScale.logicalToCoordinate(ob.mitIdx); } catch (e) {}
        }
      }
      if (xEnd === null || xEnd === undefined) {
        xEnd = lastCoord !== null ? Math.min(lastCoord + 45, rightChartEdge) : rightChartEdge;
      }

      const renderXStart = Math.max(-10, xStart);
      const renderXEnd = Math.min(rightChartEdge, Math.max(renderXStart + 10, xEnd));
      const boxW = renderXEnd - renderXStart;
      if (boxW <= 2 || renderXEnd < 0 || renderXStart > rightChartEdge) continue;

      const yTop = this.candleSeries.priceToCoordinate(ob.top);
      const yBot = this.candleSeries.priceToCoordinate(ob.bottom);
      const yMt = this.candleSeries.priceToCoordinate(ob.mid);
      if (yTop === null || yBot === null || yMt === null) continue;

      const boxTopY = Math.min(yTop, yBot);
      const boxBotY = Math.max(yTop, yBot);
      const boxH = Math.max(boxBotY - boxTopY, 5);
      if (boxBotY < -60 || boxTopY > height + 60) continue;

      const isWeak = ob.catName === 'WEAK';

      ctx.save();
      ctx.globalAlpha = ob.isMitigated ? 0.65 : 1.0;

      // 1. Order Block Zone Box (Solid for Strong/Cond, Dashed for Weak)
      ctx.fillStyle = ob.bgCol;
      ctx.strokeStyle = ob.borderCol;
      ctx.lineWidth = isWeak ? 1.2 : 1.6;
      ctx.setLineDash(isWeak ? [5, 4] : []);
      ctx.fillRect(renderXStart, boxTopY, boxW, boxH);
      ctx.strokeRect(renderXStart, boxTopY, boxW, boxH);

      // 2. 50% Mean Threshold (MT) Dashed Midline
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.strokeStyle = ob.borderCol;
      ctx.lineWidth = 1.1;
      ctx.moveTo(renderXStart, yMt);
      ctx.lineTo(renderXEnd, yMt);
      ctx.stroke();

      // 3. White Vertical Freeze Pin at First Tap Bar
      if (ob.isMitigated && ob.mitTime) {
        ctx.setLineDash([]);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(renderXEnd - 2, boxTopY - 2, 2.5, boxH + 4);
      }

      // 4. 100% Transparent Floating Label (Zero Candle Obstruction Protocol)
      const badgeX = Math.max(6, Math.min(renderXStart + 4, rightChartEdge - 165));
      const line1Y = ob.side === 'BULLISH'
        ? Math.max(14, boxTopY - 14)
        : Math.min(height - 24, boxBotY + 12);
      const line2Y = line1Y + 10;

      const overlaps = placedLabels.some(lbl => Math.abs(lbl.x - badgeX) < 135 && Math.abs(lbl.y - line1Y) < 22);
      if (!overlaps) {
        placedLabels.push({ x: badgeX, y: line1Y });
        ctx.setLineDash([]);
        ctx.globalAlpha = ob.isMitigated ? 0.85 : 1.0;

        const statusStr = ob.isMitigated ? '[TAPPED]' : '[1ST TAP]';
        const titleText = `${ob.badgeIcon} ${ob.badgeTitle} ${statusStr}`;
        ctx.font = '800 9.5px "JetBrains Mono", -apple-system, sans-serif';
        ctx.lineWidth = 3;
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.92)';
        ctx.strokeText(titleText, badgeX, line1Y);
        ctx.fillStyle = ob.borderCol;
        ctx.fillText(titleText, badgeX, line1Y);

        ctx.font = '600 8px "JetBrains Mono", -apple-system, sans-serif';
        ctx.strokeText(ob.modelSubtitle, badgeX, line2Y);
        ctx.fillStyle = ob.borderCol;
        ctx.fillText(ob.modelSubtitle, badgeX, line2Y);
      }

      ctx.restore();
    }

    // Render FVG zones (TradingView 1:1 parity)
    if (this.currentFvgs && this.currentFvgs.length > 0) {
      for (const f of this.currentFvgs) {
        let fxStart = f.startTime ? timeScale.timeToCoordinate(f.startTime) : null;
        if ((fxStart === null || fxStart === undefined) && f.startIdx !== undefined) {
          try { fxStart = timeScale.logicalToCoordinate(f.startIdx); } catch (e) {}
        }
        if (fxStart === null || fxStart === undefined) continue;
        let fxEnd = f.filledTime ? timeScale.timeToCoordinate(f.filledTime) : null;
        if (fxEnd === null || fxEnd === undefined) {
          fxEnd = lastCoord !== null ? Math.min(lastCoord + 18, rightChartEdge) : rightChartEdge;
        }
        const fW = Math.max(8, Math.min(rightChartEdge, fxEnd) - Math.max(-10, fxStart));
        const fyTop = this.candleSeries.priceToCoordinate(f.top);
        const fyBot = this.candleSeries.priceToCoordinate(f.bottom);
        if (fyTop === null || fyBot === null) continue;
        const fTopY = Math.min(fyTop, fyBot);
        const fH = Math.max(3, Math.abs(fyBot - fyTop));
        ctx.save();
        ctx.fillStyle = 'rgba(255, 213, 79, 0.08)';
        ctx.strokeStyle = 'rgba(255, 213, 79, 0.45)';
        ctx.lineWidth = 1;
        ctx.fillRect(Math.max(-10, fxStart), fTopY, fW, fH);
        ctx.strokeRect(Math.max(-10, fxStart), fTopY, fW, fH);
        ctx.restore();
      }
    }

    // Render 1:1 TradingView Signal Markers (▲ Green, ▼ Red, ◆ Blue, ◆ Magenta)
    if (this.currentSmcSignals && this.currentSmcSignals.length > 0) {
      for (const sig of this.currentSmcSignals) {
        const sx = sig.time ? timeScale.timeToCoordinate(sig.time) : null;
        const sy = this.candleSeries.priceToCoordinate(sig.price);
        if (sx === null || sx === undefined || sy === null || sy === undefined) continue;
        if (sx < 0 || sx > rightChartEdge) continue;
        ctx.save();
        if (sig.kind === 'STRONG_BUY') {
          ctx.fillStyle = '#00E676';
          ctx.beginPath();
          ctx.moveTo(sx, sy + 7);
          ctx.lineTo(sx - 5.5, sy + 17);
          ctx.lineTo(sx + 5.5, sy + 17);
          ctx.closePath();
          ctx.fill();
        } else if (sig.kind === 'STRONG_SELL') {
          ctx.fillStyle = '#FF1744';
          ctx.beginPath();
          ctx.moveTo(sx, sy - 7);
          ctx.lineTo(sx - 5.5, sy - 17);
          ctx.lineTo(sx + 5.5, sy - 17);
          ctx.closePath();
          ctx.fill();
        } else if (sig.kind === 'WEAK_BUY') {
          ctx.fillStyle = '#2979FF';
          ctx.beginPath();
          ctx.moveTo(sx, sy + 6);
          ctx.lineTo(sx + 5, sy + 12);
          ctx.lineTo(sx, sy + 18);
          ctx.lineTo(sx - 5, sy + 12);
          ctx.closePath();
          ctx.fill();
        } else if (sig.kind === 'WEAK_SELL') {
          ctx.fillStyle = '#D500F9';
          ctx.beginPath();
          ctx.moveTo(sx, sy - 6);
          ctx.lineTo(sx + 5, sy - 12);
          ctx.lineTo(sx, sy - 18);
          ctx.lineTo(sx - 5, sy - 12);
          ctx.closePath();
          ctx.fill();
        }
        ctx.restore();
      }
    }

    // Watermark Diagnostic Badge
    ctx.save();
    ctx.font = '700 10px "JetBrains Mono", monospace';
    const wmText = '⚡ Hermes MS-OB v2.0 • BUY & SELL (1.2× ATR)';
    const wmMetrics = ctx.measureText(wmText);
    const wmX = rightChartEdge - wmMetrics.width - 16;
    const wmY = height - 18;
    ctx.fillStyle = 'rgba(11, 15, 25, 0.82)';
    ctx.fillRect(wmX - 6, wmY - 12, wmMetrics.width + 12, 17);
    ctx.strokeStyle = 'rgba(245, 158, 11, 0.45)';
    ctx.strokeRect(wmX - 6, wmY - 12, wmMetrics.width + 12, 17);
    ctx.fillStyle = '#f59e0b';
    ctx.fillText(wmText, wmX, wmY);
    ctx.restore();
  }

  /* ------------------------------------------------------------------------
     TRADE EXECUTION HIGHLIGHT ON CHART
     Plots:
      - ⬆ LONG or ⬇ SHORT Entry Arrow Marker attached to candle
      - 🎯 TP HIT marker if profit target reached
      - Solid White Entry Line @ Entry Price
      - Green Dashed TP 1 Line (+10% ROI) & TP 2 Line (+15% ROI)
      - Red Dashed Hard SL Line (-15% ROI)
     ------------------------------------------------------------------------ */
  renderTradeExecutionHighlight(candles) {
    if (!this.candleSeries) return;

    // 1. Clear existing trade execution lines
    if (this.tradePriceLines && this.tradePriceLines.length > 0) {
      this.tradePriceLines.forEach(line => {
        try { this.candleSeries.removePriceLine(line); } catch (e) {}
      });
      this.tradePriceLines = [];
    }

    // 2. Find active position for the current symbol
    const activeSymbol = state.activeSymbol;
    const positions = state.positions || [];
    const pos = positions.find(p => p.symbol === activeSymbol);

    if (!pos || !candles || candles.length === 0) {
      try { this.candleSeries.setMarkers([]); } catch (e) {}
      return;
    }

    const isLong = pos.side === 'LONG';
    const entryPrice = Number(pos.entryPrice || 0);
    const markPrice = Number(pos.markPrice || entryPrice);
    const p = entryPrice < 0.01 ? 6 : (entryPrice < 1.0 ? 4 : 2);

    // 3. Determine Entry Candle Timestamp
    const entrySec = pos.entryTime > 1e11 ? Math.floor(pos.entryTime / 1000) : Number(pos.entryTime || Date.now() / 1000);
    let markerTime = candles[0].time;
    let minDiff = Math.abs(candles[0].time - entrySec);
    for (let i = 1; i < candles.length; i++) {
      const diff = Math.abs(candles[i].time - entrySec);
      if (diff < minDiff) {
        minDiff = diff;
        markerTime = candles[i].time;
      } else if (candles[i].time > entrySec) {
        break;
      }
    }

    // 4. Create Candlestick Markers
    const markers = [];
    markers.push({
      time: markerTime,
      position: isLong ? 'belowBar' : 'aboveBar',
      color: isLong ? '#00e676' : '#ff3358',
      shape: isLong ? 'arrowUp' : 'arrowDown',
      text: '',
      size: 1
    });

    const targetTp = Number(pos.tpPrice || pos.tp2Price || pos.tp1Price || 0);
    const isTpHit = Boolean(pos.armor && pos.armor.takeProfit) || (isLong ? (targetTp > 0 && markPrice >= targetTp) : (targetTp > 0 && markPrice <= targetTp));
    const lastCandle = candles[candles.length - 1];
    if (isTpHit && lastCandle && lastCandle.time !== markerTime) {
      markers.push({
        time: lastCandle.time,
        position: isLong ? 'aboveBar' : 'belowBar',
        color: '#00e676',
        shape: 'circle',
        text: '',
        size: 1
      });
    }

    markers.sort((a, b) => a.time - b.time);
    try {
      this.candleSeries.setMarkers(markers);
    } catch (e) {
      console.warn('[ChartTerminal] Error setting markers:', e);
    }

    // 5. Draw Price Lines on CandleSeries
    // A. Solid White Entry Line (Clean 1:1 match to Image 2, price on right axis)
    if (entryPrice > 0) {
      const lineEntry = this.candleSeries.createPriceLine({
        price: entryPrice,
        color: '#ffffff',
        lineWidth: 1.5,
        lineStyle: 0, // Solid
        axisLabelVisible: true,
        title: 'ENTRY'
      });
      this.tradePriceLines.push(lineEntry);
    }

    // B. Single Take Profit Line (+15% ROI - Full Book TP)
    const tpPrice = Number(pos.tpPrice || pos.tp2Price || pos.tp1Price || 0);
    if (tpPrice > 0) {
      const lineTp = this.candleSeries.createPriceLine({
        price: tpPrice,
        color: '#00e676',
        lineWidth: 1.2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: 'TP (+15%)'
      });
      this.tradePriceLines.push(lineTp);
    }

    // C. Break-Even Shield Lock Line (+2.5% ROI locked after +12% ROI hit)
    if (pos.armor && pos.armor.beShield && entryPrice > 0) {
      const bePrice = isLong ? entryPrice * 1.005 : entryPrice * 0.995;
      const lineBe = this.candleSeries.createPriceLine({
        price: bePrice,
        color: '#ffd600',
        lineWidth: 1.2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'BE LOCK (+2.5%)'
      });
      this.tradePriceLines.push(lineBe);
    }

    // D. Hard SL Line (Red Dashed -15% ROI / 2x 15m close guard)
    const slP = Number(pos.hardSlPrice || pos.slPrice || 0);
    if (slP > 0) {
      const lineSl = this.candleSeries.createPriceLine({
        price: slP,
        color: '#ff3358',
        lineWidth: 1,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: 'HARD SL (-15%)'
      });
      this.tradePriceLines.push(lineSl);
    }
  }

  /* ------------------------------------------------------------------------
     BAR REPLAY SIMULATOR
     ------------------------------------------------------------------------ */
  toggleReplayMode(forceState) {
    state.replay.active = forceState !== undefined ? forceState : !state.replay.active;
    const dock = this.el.querySelector('#replay-dock');
    const btnReplay = this.el.querySelector('#btn-toggle-replay');

    if (state.replay.active) {
      if (dock) dock.style.display = 'flex';
      if (btnReplay) btnReplay.classList.add('text-cyan');
      this.replayIndex = Math.max(10, this.rawCandles.length - 30);
      this.applyReplaySlice();
    } else {
      if (dock) dock.style.display = 'none';
      if (btnReplay) btnReplay.classList.remove('text-cyan');
      this.stopReplayTimer();
      this.replayIndex = this.rawCandles.length;
      if (this.candleSeries) this.candleSeries.setData(this.rawCandles);
      this.renderHermesSmcOverlay(this.rawCandles);
    }
  }

  applyReplaySlice() {
    if (!this.candleSeries || this.rawCandles.length === 0) return;
    const sliced = this.rawCandles.slice(0, this.replayIndex);
    this.candleSeries.setData(sliced);
    this.renderHermesSmcOverlay(sliced);

    const progress = this.el.querySelector('#replay-progress');
    if (progress) {
      progress.textContent = `BAR ${this.replayIndex}/${this.rawCandles.length}`;
    }

    if (sliced.length > 0) {
      const cur = sliced[sliced.length - 1];
      this.updateOhlcBar(cur);
      state.updatePrice(state.activeSymbol, cur.close);
    }
  }

  stepReplay(delta) {
    this.replayIndex = Math.max(5, Math.min(this.rawCandles.length, this.replayIndex + delta));
    this.applyReplaySlice();
  }

  toggleReplayPlay() {
    state.replay.playing = !state.replay.playing;
    const btnPlay = this.el.querySelector('#btn-replay-play');

    if (state.replay.playing) {
      if (btnPlay) btnPlay.textContent = '⏸';
      this.replayTimerId = setInterval(() => {
        if (this.replayIndex < this.rawCandles.length) {
          this.stepReplay(1);
        } else {
          this.toggleReplayPlay();
        }
      }, state.replay.speed);
    } else {
      this.stopReplayTimer();
    }
  }

  stopReplayTimer() {
    state.replay.playing = false;
    clearInterval(this.replayTimerId);
    const btnPlay = this.el.querySelector('#btn-replay-play');
    if (btnPlay) btnPlay.textContent = '▶';
  }

  /* ------------------------------------------------------------------------
     DRAWING TOOLS APPLICATION
     ------------------------------------------------------------------------ */
  applyDrawingTool(tool) {
    if (!this.candleSeries) return;
    const lastPrice = state.prices.get(state.activeSymbol)?.price || 100.0;

    if (tool === 'demand_zone') {
      this.candleSeries.createPriceLine({
        price: lastPrice * 0.985,
        color: '#00c087',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: 'MANUAL DEMAND ZONE'
      });
    } else if (tool === 'horiz_ray') {
      this.candleSeries.createPriceLine({
        price: lastPrice,
        color: '#38bdf8',
        lineWidth: 1,
        lineStyle: 1,
        axisLabelVisible: true,
        title: 'SMC HORIZONTAL RAY'
      });
    } else if (tool === 'fib') {
      this.candleSeries.createPriceLine({
        price: lastPrice * 1.01,
        color: '#a855f7',
        lineWidth: 1,
        lineStyle: 2,
        title: 'FIB 0.50 (MT)'
      });
    }
  }

  /* ------------------------------------------------------------------------
     ORIENTATION TOGGLE (PORTRAIT / LANDSCAPE)
     ------------------------------------------------------------------------ */
  applyOrientation(mode) {
    const wrap = this.el.querySelector('.chart-view-wrapper');
    if (!wrap) return;

    if (mode === 'landscape') {
      wrap.style.transform = 'rotate(90deg)';
      wrap.style.transformOrigin = 'bottom left';
      wrap.style.width = '100vh';
      wrap.style.height = '100vw';
      wrap.style.position = 'absolute';
      wrap.style.top = '-100vw';
      wrap.style.left = '0';
    } else {
      wrap.style.transform = 'none';
      wrap.style.width = '100%';
      wrap.style.height = '100%';
      wrap.style.position = 'relative';
      wrap.style.top = '0';
      wrap.style.left = '0';
    }

    setTimeout(() => {
      const container = this.el.querySelector('#tv-chart-box');
      if (this.chart && container) {
        this.chart.applyOptions({
          width: container.clientWidth,
          height: container.clientHeight
        });
        this.resizeSmcCanvas();
        this.drawSmcOverlay();
      }
    }, 150);
  }

}
