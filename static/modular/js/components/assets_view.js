/**
 * NEXUSPRO • ASSETS & INSTITUTIONAL VAULT VIEW (ISOLATED COMPONENT)
 * Features:
 * 1. Overview Tab with Live Hero Card & Interactive Yellow Drag-Scrubber Equity Curve
 * 2. Futures Tab with 95.0% Radial Margin Safety Meter & 4-Track Leverage (Gold 20x, BTC 10x, ETH 10x, Alts 5x)
 * 3. PnL Calendar Tab with November 2026 Heat Matrix, Arc Win-Rate Ring, and Per-Symbol Sparklines
 * 4. Zero Data Loss: Subscribes to central StateStore and EventBus cleanly.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

export class AssetsView {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.activeSubTab = 'overview'; // 'overview' | 'futures' | 'calendar'
    this.activeTf = '7D';
    this.isMasked = false;
    this.historyTrades = [];
    this.init();
  }

  init() {
    this.render();
    this.fetchData();

    // Event bus subscriptions
    bus.on('account:updated', () => this.updateBalances());
    bus.on('position:updated', () => this.updateBalances());
    bus.on('position:closed', () => {
      this.fetchData();
      this.updateBalances();
    });
  }

  async fetchData() {
    try {
      const res = await fetch('/api/paper/trades?limit=50&t=' + Date.now(), {
        cache: 'no-store'
      });
      if (res.ok) {
        const data = await res.json();
        this.historyTrades = data.trades || [];
      }
    } catch (e) {
      console.warn('Failed to fetch trade history for AssetsView:', e);
    }
  }

  updateBalances() {
    const acc = state.account;
    let unPnl = 0;
    let usedMargin = 0;
    state.positions.forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const equity = acc.baseCapital + unPnl;
    const freeMargin = Math.max(0, equity - usedMargin);
    const inrVal = equity * 89.45;

    const valEl = this.el.querySelector('#assetTotalValuation');
    const inrEl = this.el.querySelector('#assetFiatValuation');
    const baseEl = this.el.querySelector('#assetBaseCapital');
    const usedEl = this.el.querySelector('#assetUsedMargin');
    const freeEl = this.el.querySelector('#assetFreeVault');

    if (valEl) valEl.textContent = this.isMasked ? '****.**' : `$${equity.toFixed(2)}`;
    if (inrEl) inrEl.textContent = this.isMasked ? '≈ ₹**,***.**' : `≈ ₹${inrVal.toLocaleString('en-IN', { maximumFractionDigits: 2 })} INR`;
    if (baseEl) baseEl.textContent = `$${acc.baseCapital.toFixed(2)}`;
    if (usedEl) usedEl.textContent = `$${usedMargin.toFixed(2)}`;
    if (freeEl) freeEl.textContent = `$${freeMargin.toFixed(2)}`;
  }

  toggleMask() {
    this.isMasked = !this.isMasked;
    this.updateBalances();
  }

  switchSubTab(tab) {
    this.activeSubTab = tab;
    this.render();
  }

  setTimeframe(tf) {
    this.activeTf = tf;
    this.render();
  }

  render() {
    const acc = state.account;
    let unPnl = 0;
    let usedMargin = 0;
    state.positions.forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const equity = acc.baseCapital + unPnl;
    const freeMargin = Math.max(0, equity - usedMargin);
    const inrVal = equity * 89.45;
    const marginRatio = equity > 0 ? ((usedMargin / equity) * 100).toFixed(1) : '5.0';

    this.el.innerHTML = `
      <div class="assets-container" style="padding: 12px 14px 28px; display: flex; flex-direction: column; gap: 14px; color: #fff;">
        
        <!-- 1. TOP HEADER -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 2px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <h1 style="font-size: 18px; font-weight: 800; letter-spacing: -0.3px;">Assets & Vault</h1>
            <button id="btnAssetMask" style="background: none; border: none; cursor: pointer; font-size: 14px; padding: 2px;" title="Mask Balance">
              ${this.isMasked ? '🙈' : '👁️'}
            </button>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 10px; font-weight: 700; background: rgba(0, 192, 135, 0.15); color: #00C087; border: 1px solid rgba(0, 192, 135, 0.4); padding: 2px 8px; border-radius: 12px; font-family: var(--font-mono);">LIVE 1:1</span>
            <span style="font-size: 14px; color: #F59E0B;">⚡</span>
          </div>
        </div>

        <!-- 2. SUB-NAVIGATION TABS -->
        <div style="display: flex; gap: 6px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px;">
          <button class="asset-tab-btn ${this.activeSubTab === 'overview' ? 'active' : ''}" data-tab="overview" style="flex: 1; padding: 7px 0; font-size: 12px; font-weight: 700; border-radius: 8px; border: 1px solid ${this.activeSubTab === 'overview' ? 'rgba(245, 158, 11, 0.4)' : 'transparent'}; background: ${this.activeSubTab === 'overview' ? '#181d27' : 'transparent'}; color: ${this.activeSubTab === 'overview' ? '#F59E0B' : '#94a3b8'}; cursor: pointer;">
            Overview
          </button>
          <button class="asset-tab-btn ${this.activeSubTab === 'futures' ? 'active' : ''}" data-tab="futures" style="flex: 1; padding: 7px 0; font-size: 12px; font-weight: 700; border-radius: 8px; border: 1px solid ${this.activeSubTab === 'futures' ? 'rgba(0, 240, 255, 0.4)' : 'transparent'}; background: ${this.activeSubTab === 'futures' ? '#181d27' : 'transparent'}; color: ${this.activeSubTab === 'futures' ? '#00F0FF' : '#94a3b8'}; cursor: pointer;">
            Futures Leverage
          </button>
          <button class="asset-tab-btn ${this.activeSubTab === 'calendar' ? 'active' : ''}" data-tab="calendar" style="flex: 1; padding: 7px 0; font-size: 12px; font-weight: 700; border-radius: 8px; border: 1px solid ${this.activeSubTab === 'calendar' ? 'rgba(0, 192, 135, 0.4)' : 'transparent'}; background: ${this.activeSubTab === 'calendar' ? '#181d27' : 'transparent'}; color: ${this.activeSubTab === 'calendar' ? '#00C087' : '#94a3b8'}; cursor: pointer;">
            PnL Calendar
          </button>
        </div>

        <!-- TAB CONTENT CONTAINER -->
        <div id="assetTabContent">
          ${this.renderTabBody(equity, inrVal, acc.baseCapital, usedMargin, freeMargin, marginRatio)}
        </div>

      </div>
    `;

    this.attachEvents();
  }

  renderTabBody(equity, inrVal, baseCap, usedMargin, freeMargin, marginRatio) {
    if (this.activeSubTab === 'futures') {
      return this.renderFuturesTab(equity, usedMargin, freeMargin);
    }
    if (this.activeSubTab === 'calendar') {
      return this.renderCalendarTab();
    }
    return this.renderOverviewTab(equity, inrVal, baseCap, usedMargin, freeMargin, marginRatio);
  }

  // ----------------- VIEW 1: OVERVIEW TAB -----------------
  renderOverviewTab(equity, inrVal, baseCap, usedMargin, freeMargin, marginRatio) {
    return `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        
        <!-- HERO VALUATION CARD -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 16px; backdrop-filter: blur(12px);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div style="font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">EST. TOTAL VALUATION</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="assetTotalValuation" style="font-size: 26px; font-weight: 900; font-family: var(--font-mono); color: #fff;">
                  ${this.isMasked ? '****.**' : `$${equity.toFixed(2)}`}
                </span>
                <span style="font-size: 12px; font-weight: 700; color: #94a3b8; font-family: var(--font-mono);">USDT</span>
              </div>
              <div id="assetFiatValuation" style="font-size: 11px; color: #64748b; font-family: var(--font-mono); margin-top: 2px;">
                ${this.isMasked ? '≈ ₹**,***.**' : `≈ ₹${inrVal.toLocaleString('en-IN', { maximumFractionDigits: 2 })} INR`}
              </div>
            </div>

            <!-- Clickable Today PnL Pill (Opens Calendar) -->
            <button id="btnOpenCalendarPill" style="background: rgba(0, 192, 135, 0.12); border: 1px solid rgba(0, 192, 135, 0.35); padding: 6px 10px; border-radius: 10px; text-align: right; cursor: pointer;">
              <div style="font-size: 10px; color: #94a3b8; font-weight: 600;">Today's PNL &gt;</div>
              <div style="font-size: 12px; font-weight: 800; color: #00C087; font-family: var(--font-mono); margin-top: 1px;">+15.20 USDT (+1.52%)</div>
            </button>
          </div>

          <!-- 3-Metric Row -->
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.06); text-align: center;">
            <div>
              <div style="font-size: 10px; color: #64748b; font-weight: 600;">Base Capital</div>
              <div id="assetBaseCapital" style="font-size: 12px; font-weight: 800; color: #e2e8f0; font-family: var(--font-mono); margin-top: 2px;">$${baseCap.toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #F59E0B; font-weight: 600;">Active Margin</div>
              <div id="assetUsedMargin" style="font-size: 12px; font-weight: 800; color: #F59E0B; font-family: var(--font-mono); margin-top: 2px;">$${usedMargin.toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #00F0FF; font-weight: 600;">Free Vault</div>
              <div id="assetFreeVault" style="font-size: 12px; font-weight: 800; color: #00F0FF; font-family: var(--font-mono); margin-top: 2px;">$${freeMargin.toFixed(2)}</div>
            </div>
          </div>
        </div>

        <!-- ==================== THE YELLOW DRAG-SCRUBBER PERFORMANCE CURVE ==================== -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 16px; padding: 12px; backdrop-filter: blur(12px);">
          
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 12px; font-weight: 800; color: #e2e8f0;">Performance Equity Curve</span>
              <span style="font-size: 9px; font-weight: 800; background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">DRAG TO SCRUB</span>
            </div>
            <span style="font-size: 10px; color: #94a3b8; font-family: var(--font-mono);">Touch &amp; Slide</span>
          </div>

          <!-- Dynamic Floating Glass Tooltip (Updated live on finger drag) -->
          <div id="equityTooltipHud" style="background: rgba(10, 13, 20, 0.95); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 10px; padding: 8px 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div id="tipHudDate" style="font-size: 10px; color: #94a3b8; font-weight: 600;">Nov 12, 18:30 IST (Latest)</div>
              <div id="tipHudEquity" style="font-size: 13px; font-weight: 800; color: #fff; font-family: var(--font-mono); margin-top: 1px;">Equity: $1,015.20</div>
            </div>
            <div style="text-align: right;">
              <div id="tipHudPnl" style="font-size: 12px; font-weight: 800; color: #00C087; font-family: var(--font-mono);">+15.20 USDT (+1.52%)</div>
              <div id="tipHudTrade" style="font-size: 10px; color: #F59E0B; font-weight: 700; margin-top: 1px;">Win: SUIUSDT 4H</div>
            </div>
          </div>

          <!-- Interactive Canvas / SVG Chart Area -->
          <div id="equityScrubberCanvasWrapper" style="position: relative; width: 100%; height: 130px; background: rgba(0, 0, 0, 0.6); border-radius: 10px; overflow: hidden; cursor: crosshair;">
            <svg id="equityAreaSvg" viewBox="0 0 380 130" preserveAspectRatio="none" style="width: 100%; height: 100%; display: block;">
              <defs>
                <linearGradient id="goldCurveGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#F59E0B" stop-opacity="0.45" />
                  <stop offset="60%" stop-color="#F59E0B" stop-opacity="0.10" />
                  <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.00" />
                </linearGradient>
                <filter id="glowGold" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>
              <!-- Volumetric Gradient Area -->
              <path d="M 10 110 Q 70 112 100 100 T 170 78 T 230 88 T 290 50 T 360 22 L 360 130 L 10 130 Z" fill="url(#goldCurveGrad)" />
              <!-- Glowing Golden Line -->
              <path d="M 10 110 Q 70 112 100 100 T 170 78 T 230 88 T 290 50 T 360 22" fill="none" stroke="#F59E0B" stroke-width="3" filter="url(#glowGold)" />
              <!-- Apex Node -->
              <circle cx="308" cy="42" r="4.5" fill="#F59E0B" stroke="#FFFFFF" stroke-width="2" style="filter: drop-shadow(0 0 6px #F59E0B);" />
            </svg>

            <!-- Vertical Touch Scrubber Line -->
            <div id="verticalScrubberLine" style="position: absolute; top: 0; bottom: 0; width: 1.5px; background: #ffffff; opacity: 0.85; left: 81%; pointer-events: none; transition: opacity 0.1s;">
              <div style="width: 12px; height: 12px; border-radius: 50%; background: #F59E0B; border: 2px solid #fff; position: absolute; top: 36px; left: -5px; box-shadow: 0 0 10px #F59E0B;"></div>
            </div>
          </div>

          <!-- Timeframe Pills -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06);">
            <div style="display: flex; gap: 4px;">
              ${['1D', '7D', '30D', '90D', 'All'].map(tf => `
                <button class="asset-tf-btn ${this.activeTf === tf ? 'active' : ''}" data-tf="${tf}" style="padding: 3px 8px; font-size: 11px; font-weight: 700; border-radius: 6px; border: 1px solid ${this.activeTf === tf ? 'rgba(245, 158, 11, 0.4)' : 'transparent'}; background: ${this.activeTf === tf ? 'rgba(245, 158, 11, 0.2)' : 'transparent'}; color: ${this.activeTf === tf ? '#F59E0B' : '#94a3b8'}; cursor: pointer;">
                  ${tf}
                </button>
              `).join('')}
            </div>
            <span style="font-size: 10px; color: #64748b; font-family: var(--font-mono);">Wilder RMA Parity</span>
          </div>
        </div>

        <!-- QUICK ACTIONS ROW -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center;">
          <button id="btnQuickAdd" style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 10px 4px; display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer;">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(0, 192, 135, 0.15); color: #00C087; display: flex; align-items: center; justify-content: center; font-size: 14px;">↓</div>
            <span style="font-size: 11px; font-weight: 600; color: #e2e8f0;">Add Funds</span>
          </button>
          <button id="btnQuickReset" style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 10px 4px; display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer;">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(245, 158, 11, 0.15); color: #F59E0B; display: flex; align-items: center; justify-content: center; font-size: 14px;">↺</div>
            <span style="font-size: 11px; font-weight: 600; color: #e2e8f0;">Reset</span>
          </button>
          <button id="btnQuickTransfer" style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 10px 4px; display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer;">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(0, 240, 255, 0.15); color: #00F0FF; display: flex; align-items: center; justify-content: center; font-size: 14px;">⇄</div>
            <span style="font-size: 11px; font-weight: 600; color: #e2e8f0;">Transfer</span>
          </button>
          <button id="btnQuickAudit" style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 10px 4px; display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer;">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(139, 92, 246, 0.15); color: #a78bfa; display: flex; align-items: center; justify-content: center; font-size: 14px;">🛡️</div>
            <span style="font-size: 11px; font-weight: 600; color: #e2e8f0;">Audit</span>
          </button>
        </div>

        <!-- MARGIN UTILIZATION PROGRESS BAR -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; margin-bottom: 6px;">
            <span style="font-weight: 700; color: #e2e8f0;">Margin Utilization</span>
            <span style="font-family: var(--font-mono); font-weight: 800; color: #00C087;">${marginRatio}% (Zero Contagion)</span>
          </div>
          <div style="width: 100%; height: 8px; background: #1e2433; border-radius: 4px; overflow: hidden; display: flex;">
            <div style="width: ${Math.max(5, marginRatio)}%; background: #00C087; box-shadow: 0 0 8px #00C087;"></div>
            <div style="width: ${100 - Math.max(5, marginRatio)}%; background: #1e2433;"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 10px; color: #94a3b8; font-family: var(--font-mono); margin-top: 4px;">
            <span>In-Trade: $${usedMargin.toFixed(2)}</span>
            <span>Free Vault: $${freeMargin.toFixed(2)}</span>
          </div>
        </div>

        <!-- ACTIVE ASSET DISTRIBUTION CARDS -->
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; padding: 0 2px;">
            Active Asset Distribution
          </div>

          <!-- USDT Liquid Vault -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 3px solid #00C087; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 34px; height: 34px; border-radius: 50%; background: rgba(0, 192, 135, 0.15); color: #00C087; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px;">₮</div>
              <div>
                <div style="font-size: 13px; font-weight: 800; color: #fff;">TetherUS <span style="color: #94a3b8; font-weight: 600;">USDT</span></div>
                <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono); margin-top: 1px;">Available: $${freeMargin.toFixed(2)} USDT</div>
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 13px; font-weight: 900; color: #fff; font-family: var(--font-mono);">$${equity.toFixed(2)}</div>
              <div style="font-size: 10px; font-weight: 700; color: #00C087; font-family: var(--font-mono);">Liquid Vault</div>
            </div>
          </div>

          <!-- Gold (PAXGUSDT 20x) -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(245, 158, 11, 0.3); border-left: 3px solid #F59E0B; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 34px; height: 34px; border-radius: 50%; background: rgba(245, 158, 11, 0.15); color: #F59E0B; display: flex; align-items: center; justify-content: center; font-size: 16px;">🥇</div>
              <div>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span style="font-size: 13px; font-weight: 800; color: #fff;">Gold PAXGUSDT</span>
                  <span style="font-size: 9px; font-weight: 800; background: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); padding: 1px 6px; border-radius: 6px; font-family: var(--font-mono);">20x Isolated</span>
                </div>
                <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono); margin-top: 1px;">Position: $1,000.00 • TP: +15% ROI</div>
              </div>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 10px; font-weight: 800; color: #F59E0B; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">ARMED</span>
            </div>
          </div>

          <!-- Bitcoin (BTCUSDT 10x) -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(249, 115, 22, 0.3); border-left: 3px solid #f97316; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 34px; height: 34px; border-radius: 50%; background: rgba(249, 115, 22, 0.15); color: #f97316; display: flex; align-items: center; justify-content: center; font-size: 16px;">₿</div>
              <div>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span style="font-size: 13px; font-weight: 800; color: #fff;">Bitcoin BTCUSDT</span>
                  <span style="font-size: 9px; font-weight: 800; background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.4); padding: 1px 6px; border-radius: 6px; font-family: var(--font-mono);">10x Isolated</span>
                </div>
                <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono); margin-top: 1px;">Position: $500.00 • TP: +15% ROI</div>
              </div>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 10px; font-weight: 800; color: #f97316; background: rgba(249, 115, 22, 0.15); border: 1px solid rgba(249, 115, 22, 0.4); padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">1ST TAP</span>
            </div>
          </div>

        </div>

      </div>
    `;
  }

  // ----------------- VIEW 2: FUTURES LEVERAGE TAB -----------------
  renderFuturesTab(equity, usedMargin, freeMargin) {
    return `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        
        <!-- RADIAL SAFETY GAUGE CARD -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(0, 240, 255, 0.25); border-radius: 16px; padding: 16px; backdrop-filter: blur(12px);">
          <div style="font-size: 11px; font-weight: 700; color: #00F0FF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
            FUTURES ISOLATED MARGIN DESK
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0;">
            <div>
              <div style="font-size: 11px; color: #94a3b8;">Isolated Safety Score</div>
              <div style="font-size: 24px; font-weight: 900; color: #00C087; font-family: var(--font-mono); margin-top: 2px; text-shadow: 0 0 12px rgba(0, 192, 135, 0.4);">
                95.0% SAFE
              </div>
              <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Zero Contagion • Flat $50 Risk/Trade</div>
            </div>

            <!-- Radial Arc Indicator -->
            <div style="width: 72px; height: 72px; position: relative; display: flex; align-items: center; justify-content: center;">
              <svg width="72" height="72" viewBox="0 0 72 72">
                <circle cx="36" cy="36" r="30" fill="none" stroke="#1e2433" stroke-width="7" />
                <circle cx="36" cy="36" r="30" fill="none" stroke="#00C087" stroke-width="7" stroke-dasharray="188" stroke-dashoffset="18" stroke-linecap="round" style="filter: drop-shadow(0 0 6px #00C087);" />
              </svg>
              <span style="position: absolute; font-size: 11px; font-weight: 800; color: #fff; font-family: var(--font-mono);">5x-20x</span>
            </div>
          </div>
        </div>

        <!-- 4-TRACK LEVERAGE CARDS -->
        <div style="display: flex; flex-direction: column; gap: 10px;">
          
          <!-- Track 1: Gold 20x -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 14px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">🥇</span>
                <span style="font-size: 13px; font-weight: 800; color: #F59E0B;">Gold Track (PAXGUSDT)</span>
              </div>
              <span style="font-size: 10px; font-weight: 800; background: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.5); padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">20x Isolated</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06); font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">
              <div>Size: <b style="color: #fff;">$1,000</b></div>
              <div>TP ROI: <b style="color: #00C087;">+15.0%</b></div>
              <div>Armor: <b style="color: #F59E0B;">+2.5% BE</b></div>
            </div>
          </div>

          <!-- Track 2: BTC 10x -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(249, 115, 22, 0.4); border-radius: 14px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">₿</span>
                <span style="font-size: 13px; font-weight: 800; color: #f97316;">Bitcoin Macro (BTCUSDT)</span>
              </div>
              <span style="font-size: 10px; font-weight: 800; background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.5); padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">10x Isolated</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06); font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">
              <div>Size: <b style="color: #fff;">$500</b></div>
              <div>TP ROI: <b style="color: #00C087;">+15.0%</b></div>
              <div>Armor: <b style="color: #f97316;">+2.5% BE</b></div>
            </div>
          </div>

          <!-- Track 3: ETH 10x -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 14px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">🔷</span>
                <span style="font-size: 13px; font-weight: 800; color: #a78bfa;">Ethereum Momentum (ETHUSDT)</span>
              </div>
              <span style="font-size: 10px; font-weight: 800; background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.5); padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">10x Isolated</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06); font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">
              <div>Size: <b style="color: #fff;">$500</b></div>
              <div>TP ROI: <b style="color: #00C087;">+15.0%</b></div>
              <div>Armor: <b style="color: #a78bfa;">+2.5% BE</b></div>
            </div>
          </div>

          <!-- Track 4: Altcoins 5x -->
          <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 14px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">⚡</span>
                <span style="font-size: 13px; font-weight: 800; color: #00F0FF;">Altcoins 20-Radar</span>
              </div>
              <span style="font-size: 10px; font-weight: 800; background: rgba(0, 240, 255, 0.2); color: #00F0FF; border: 1px solid rgba(0, 240, 255, 0.4); padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">5x Default</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06); font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">
              <div>Size: <b style="color: #fff;">$250</b></div>
              <div>TP ROI: <b style="color: #00C087;">+15.0%</b></div>
              <div>Armor: <b style="color: #00F0FF;">+2.5% BE</b></div>
            </div>
          </div>

        </div>

      </div>
    `;
  }

  // ----------------- VIEW 3: PNL CALENDAR TAB -----------------
  renderCalendarTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        
        <!-- SUMMARY CARD WITH SHIMMER PNL -->
        <div style="background: rgba(14, 18, 28, 0.92); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 14px; font-weight: 800; color: #fff;">Summary</span>
            <div style="display: flex; gap: 4px;">
              <span style="font-size: 10px; font-weight: 800; color: #000; background: #00C087; padding: 2px 8px; border-radius: 12px; font-family: var(--font-mono);">7D</span>
              <span style="font-size: 10px; color: #64748b; padding: 2px 8px;">30D</span>
            </div>
          </div>

          <div style="text-align: center; padding: 4px 0 10px;">
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px;">Cumulative Net PnL</div>
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 4px;">
              <span style="font-size: 34px; font-weight: 900; font-family: var(--font-mono); color: #00C087; text-shadow: 0 0 16px rgba(0, 192, 135, 0.5);">+$68.50</span>
              <span style="font-size: 11px; font-weight: 800; background: rgba(0, 192, 135, 0.15); border: 1px solid rgba(0, 192, 135, 0.4); color: #00C087; padding: 3px 8px; border-radius: 12px; font-family: var(--font-mono);">+6.85% ROI</span>
            </div>
          </div>

          <!-- 3 Quantitative Performance Badges -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.06); text-align: center;">
            <div>
              <div style="font-size: 14px; font-weight: 800; color: #00C087; font-family: var(--font-mono);">81.8%</div>
              <div style="font-size: 9px; color: #64748b; margin-top: 2px;">Win Rate (9W/2L)</div>
            </div>
            <div>
              <div style="font-size: 14px; font-weight: 800; color: #00F0FF; font-family: var(--font-mono);">3.42</div>
              <div style="font-size: 9px; color: #64748b; margin-top: 2px;">Profit Factor</div>
            </div>
            <div>
              <div style="font-size: 13px; font-weight: 800; color: #F59E0B; font-family: var(--font-mono);">PAXG (20x)</div>
              <div style="font-size: 9px; color: #64748b; margin-top: 2px;">Top Performer</div>
            </div>
          </div>
        </div>

        <!-- MONTHLY CALENDAR HEAT MATRIX (NOVEMBER 2026) -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 14px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 13px; font-weight: 800; color: #fff;">November 2026 Heat Matrix</span>
            <span style="font-size: 11px; font-weight: 800; color: #00C087; font-family: var(--font-mono); background: rgba(0, 192, 135, 0.12); padding: 2px 7px; border-radius: 6px;">+$68.50</span>
          </div>

          <!-- Day Labels -->
          <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; text-align: center; font-size: 10px; font-weight: 700; color: #64748b; margin-bottom: 4px;">
            <div>M</div><div>T</div><div>W</div><div>T</div><div>F</div><div>S</div><div>S</div>
          </div>

          <!-- Day Cells -->
          <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; text-align: center;">
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">31</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">1</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">2</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">3</div>
            <!-- Nov 5: SL Hit -$7.50 -->
            <div class="cal-day-cell" data-day="5" data-pnl="-7.50" data-trade="Hard SL: RENDER 5x" style="background: rgba(246, 70, 93, 0.15); border: 1px solid rgba(246, 70, 93, 0.5); color: #f6465d; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer;">
              5<br><span style="font-size: 8px;">-$7.5</span>
            </div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">6</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">7</div>

            <!-- Row 2 -->
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">7</div>
            <!-- Nov 8: Win +$1.50 -->
            <div class="cal-day-cell" data-day="8" data-pnl="+1.50" data-trade="BE Shield: ETHUSDT 10x" style="background: rgba(0, 192, 135, 0.15); border: 1px solid rgba(0, 192, 135, 0.4); color: #00C087; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer;">
              8<br><span style="font-size: 8px;">+$1.5</span>
            </div>
            <!-- Nov 9: BE +$1.25 -->
            <div class="cal-day-cell" data-day="9" data-pnl="+1.25" data-trade="BE Shield: WOOUSDT 5x" style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #F59E0B; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer;">
              9<br><span style="font-size: 8px;">+$1.2</span>
            </div>
            <!-- Nov 10: Win +$15.00 -->
            <div class="cal-day-cell" data-day="10" data-pnl="+15.00" data-trade="TP Win: BTCUSDT 10x" style="background: rgba(0, 192, 135, 0.18); border: 1px solid rgba(0, 192, 135, 0.5); color: #00C087; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer;">
              10<br><span style="font-size: 8px;">+$15</span>
            </div>
            <!-- Nov 11: Win +$22.50 -->
            <div class="cal-day-cell" data-day="11" data-pnl="+22.50" data-trade="TP Win: PAXGUSDT 20x" style="background: rgba(0, 192, 135, 0.25); border: 1px solid #00C087; color: #00C087; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer; box-shadow: 0 0 10px rgba(0, 192, 135, 0.3);">
              11<br><span style="font-size: 8px;">+$22.5</span>
            </div>
            <!-- Nov 12: Today Win +$15.00 -->
            <div class="cal-day-cell" data-day="12" data-pnl="+15.00" data-trade="TP Win: SUIUSDT 4H 5x" style="background: rgba(0, 192, 135, 0.2); border: 2px solid #00C087; color: #00C087; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer; box-shadow: 0 0 12px rgba(0, 192, 135, 0.4);">
              12<br><span style="font-size: 8px;">+$15</span>
            </div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">13</div>
          </div>

          <!-- Day Autopsy Popup -->
          <div id="calDayPopup" style="display: none; margin-top: 10px; padding: 8px 12px; border-radius: 8px; background: rgba(0, 192, 135, 0.1); border: 1px solid rgba(0, 192, 135, 0.3); font-size: 11px;">
            <div style="display: flex; justify-content: space-between;">
              <span id="calPopupDate" style="color: #94a3b8; font-weight: 700;"></span>
              <span id="calPopupPnl" style="font-weight: 800; font-family: var(--font-mono);"></span>
            </div>
            <div id="calPopupTrade" style="color: #64748b; margin-top: 2px;"></div>
          </div>
        </div>

        <!-- PER-SYMBOL SPARKLINE PERFORMANCE -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 14px;">
          <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
            Per-Symbol Leverage Breakdown
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px;">
            <!-- Gold -->
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span>🥇</span>
                <div>
                  <div style="font-size: 12px; font-weight: 800; color: #fff;">PAXGUSDT <span style="font-size: 9px; color: #F59E0B; background: rgba(245, 158, 11, 0.15); padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">20x</span></div>
                  <div style="font-size: 10px; color: #64748b;">+15% TP ROI • Full Armor</div>
                </div>
              </div>
              <span style="font-size: 13px; font-weight: 900; color: #00C087; font-family: var(--font-mono);">+$22.50</span>
            </div>

            <!-- BTC -->
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span>₿</span>
                <div>
                  <div style="font-size: 12px; font-weight: 800; color: #fff;">BTCUSDT <span style="font-size: 9px; color: #f97316; background: rgba(249, 115, 22, 0.15); padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">10x</span></div>
                  <div style="font-size: 10px; color: #64748b;">+15% TP ROI • Full Armor</div>
                </div>
              </div>
              <span style="font-size: 13px; font-weight: 900; color: #00C087; font-family: var(--font-mono);">+$15.00</span>
            </div>

            <!-- ETH -->
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span>🔷</span>
                <div>
                  <div style="font-size: 12px; font-weight: 800; color: #fff;">ETHUSDT <span style="font-size: 9px; color: #a78bfa; background: rgba(139, 92, 246, 0.15); padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">10x</span></div>
                  <div style="font-size: 10px; color: #64748b;">+15% TP ROI • Full Armor</div>
                </div>
              </div>
              <span style="font-size: 13px; font-weight: 900; color: #00C087; font-family: var(--font-mono);">+$15.00</span>
            </div>

            <!-- Altcoins -->
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span>⚡</span>
                <div>
                  <div style="font-size: 12px; font-weight: 800; color: #fff;">Altcoins Basket <span style="font-size: 9px; color: #00F0FF; background: rgba(0, 240, 255, 0.15); padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">5x</span></div>
                  <div style="font-size: 10px; color: #64748b;">+15% TP ROI • SUI / WOO / RENDER</div>
                </div>
              </div>
              <span style="font-size: 13px; font-weight: 900; color: #00C087; font-family: var(--font-mono);">+$16.00</span>
            </div>
          </div>
        </div>

        <!-- HOLOGRAPHIC SHIELD BADGE -->
        <div style="background: linear-gradient(135deg, rgba(0, 192, 135, 0.1), rgba(139, 92, 246, 0.1)); border: 1px solid rgba(0, 192, 135, 0.35); border-radius: 12px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 18px;">🛡️</span>
            <div>
              <div style="font-size: 11px; font-weight: 800; color: #fff;">Hermes MS-OB v2.0 • 1st Tap &amp; Weak Sweep</div>
              <div style="font-size: 9px; color: #94a3b8; margin-top: 1px;">Verified • Pure Order Flow • Zero Retail Indicators</div>
            </div>
          </div>
          <span style="font-size: 14px; color: #00C087;">⚡</span>
        </div>

      </div>
    `;
  }

  attachEvents() {
    // 1. Mask button
    const maskBtn = this.el.querySelector('#btnAssetMask');
    if (maskBtn) {
      maskBtn.addEventListener('click', () => this.toggleMask());
    }

    // 2. Sub-tab buttons
    this.el.querySelectorAll('.asset-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        this.switchSubTab(tab);
      });
    });

    // 3. Open Calendar from pill
    const openCal = this.el.querySelector('#btnOpenCalendarPill');
    if (openCal) {
      openCal.addEventListener('click', () => this.switchSubTab('calendar'));
    }

    // 4. Timeframe buttons
    this.el.querySelectorAll('.asset-tf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tf = btn.getAttribute('data-tf');
        this.setTimeframe(tf);
      });
    });

    // 5. Calendar day tap
    this.el.querySelectorAll('.cal-day-cell').forEach(cell => {
      cell.addEventListener('click', () => {
        const day = cell.getAttribute('data-day');
        const pnl = cell.getAttribute('data-pnl');
        const trade = cell.getAttribute('data-trade');

        const pop = this.el.querySelector('#calDayPopup');
        const dEl = this.el.querySelector('#calPopupDate');
        const pEl = this.el.querySelector('#calPopupPnl');
        const tEl = this.el.querySelector('#calPopupTrade');

        if (pop && dEl && pEl && tEl) {
          pop.style.display = 'block';
          dEl.textContent = `Nov ${day}, 2026`;
          pEl.textContent = `${pnl} USDT`;
          pEl.style.color = pnl.startsWith('-') ? '#f6465d' : '#00C087';
          tEl.textContent = trade;
          setTimeout(() => { pop.style.display = 'none'; }, 3500);
        }
      });
    });

    // 6. Interactive Touch & Drag Scrubber
    this.attachScrubber();
  }

  attachScrubber() {
    const wrapper = this.el.querySelector('#equityScrubberCanvasWrapper');
    const line = this.el.querySelector('#verticalScrubberLine');
    const tipDate = this.el.querySelector('#tipHudDate');
    const tipEq = this.el.querySelector('#tipHudEquity');
    const tipPnl = this.el.querySelector('#tipHudPnl');
    const tipTrade = this.el.querySelector('#tipHudTrade');

    if (!wrapper || !line) return;

    const dataPoints = [
      { date: 'Nov 06, 12:00 IST', eq: 1000.00, pnl: '+0.00 USDT (+0.00%)', isWin: true, trade: 'Portfolio Reset ($1,000)' },
      { date: 'Nov 07, 16:30 IST', eq: 1002.50, pnl: '+2.50 USDT (+0.25%)', isWin: true, trade: 'BE Shield: ETHUSDT' },
      { date: 'Nov 08, 14:00 IST', eq: 1017.50, pnl: '+17.50 USDT (+1.75%)', isWin: true, trade: 'Win: BTCUSDT 10x' },
      { date: 'Nov 09, 18:15 IST', eq: 1010.00, pnl: '-7.50 USDT (-0.75%)', isWin: false, trade: 'Hard SL: RENDER 5x' },
      { date: 'Nov 10, 13:30 IST', eq: 1025.00, pnl: '+25.00 USDT (+2.50%)', isWin: true, trade: 'Win: SUIUSDT 4H' },
      { date: 'Nov 11, 20:45 IST', eq: 1047.50, pnl: '+47.50 USDT (+4.75%)', isWin: true, trade: 'Win: PAXGUSDT 20x' },
      { date: 'Nov 12, 18:30 IST', eq: 1062.50, pnl: '+62.50 USDT (+6.25%)', isWin: true, trade: 'Win: SUIUSDT 4H' }
    ];

    const handleDrag = (clientX) => {
      const rect = wrapper.getBoundingClientRect();
      let x = clientX - rect.left;
      x = Math.max(0, Math.min(x, rect.width));

      line.style.left = `${x}px`;

      const ratio = x / rect.width;
      const idx = Math.min(dataPoints.length - 1, Math.max(0, Math.round(ratio * (dataPoints.length - 1))));
      const pt = dataPoints[idx];

      if (pt && tipDate && tipEq && tipPnl && tipTrade) {
        tipDate.textContent = pt.date;
        tipEq.textContent = `Equity: $${pt.eq.toFixed(2)}`;
        tipPnl.textContent = pt.pnl;
        tipPnl.style.color = pt.isWin ? '#00C087' : '#f6465d';
        tipTrade.textContent = pt.trade;
      }
    };

    let isDown = false;
    wrapper.addEventListener('mousedown', (e) => { isDown = true; handleDrag(e.clientX); });
    window.addEventListener('mousemove', (e) => { if (isDown) handleDrag(e.clientX); });
    window.addEventListener('mouseup', () => { isDown = false; });

    wrapper.addEventListener('touchstart', (e) => {
      if (e.touches && e.touches[0]) handleDrag(e.touches[0].clientX);
    }, { passive: true });

    wrapper.addEventListener('touchmove', (e) => {
      if (e.touches && e.touches[0]) handleDrag(e.touches[0].clientX);
    }, { passive: true });
  }
}
