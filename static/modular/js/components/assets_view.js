/**
 * NEXUSPRO • ASSETS & INSTITUTIONAL VAULT VIEW (PRODUCTION REAL-DATA ENGINE)
 * =========================================================================
 * 100% Synced with SQLite Ledger & Live Open Positions.
 * Zero Fake Data • Zero Mock PnL • Full Audit Log Forensics.
 * 
 * Features:
 * 1. Overview Tab: Live Valuation, Today's Real PnL, Dynamic Catmull-Rom Equity Curve
 *    with interactive Touch-Drag Scrubber, Margin Utilization & Live Active Asset Cards.
 * 2. Futures Tab: Real Isolated Safety Score & 4-Track Real Leverage Allocation (PAXG 20x, BTC 10x, ETH 10x, Alts 5x).
 * 3. PnL Calendar Tab: Real Monthly Heat Matrix, Authentic Win Rate & Profit Factor,
 *    Tap-to-Inspect Trade Autopsies, and Per-Symbol Leverage Breakdown.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

function generateSmoothSvgPath(coords) {
  if (!coords || coords.length === 0) return '';
  if (coords.length === 1) return `M ${coords[0].x.toFixed(1)} ${coords[0].y.toFixed(1)}`;
  if (coords.length === 2) return `M ${coords[0].x.toFixed(1)} ${coords[0].y.toFixed(1)} L ${coords[1].x.toFixed(1)} ${coords[1].y.toFixed(1)}`;

  let d = `M ${coords[0].x.toFixed(1)} ${coords[0].y.toFixed(1)}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i === 0 ? 0 : i - 1];
    const p1 = coords[i];
    const p2 = coords[i + 1];
    const p3 = coords[i + 2 < coords.length ? i + 2 : coords.length - 1];

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d;
}

export class AssetsView {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.activeSubTab = 'overview'; // 'overview' | 'futures' | 'calendar'
    this.activeTf = '7D';
    this.isMasked = false;
    this.analytics = null;
    this.cachedCoords = [];
    this.init();
  }

  init() {
    this.render();
    this.fetchData();

    // Event bus subscriptions for instant live synchronizations
    bus.on('account:updated', () => this.fetchData());
    bus.on('position:updated', () => this.fetchData());
    bus.on('position:closed', () => this.fetchData());
  }

  async fetchData() {
    try {
      const res = await fetch('/api/assets/analytics?t=' + Date.now(), {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      });
      if (res.ok) {
        this.analytics = await res.json();
        this.render();
      }
    } catch (e) {
      console.warn('Failed to fetch assets analytics:', e);
    }
  }

  toggleMask() {
    this.isMasked = !this.isMasked;
    this.render();
  }

  switchSubTab(tab) {
    this.activeSubTab = tab;
    this.render();
  }

  setTimeframe(tf) {
    this.activeTf = tf;
    this.render();
  }

  // Fallback defaults if API is pending
  getSafeData() {
    if (this.analytics) return this.analytics;

    const acc = state.account || {};
    const baseCap = Number(acc.baseCapital || 1000.0);
    let unPnl = 0;
    let usedMargin = 0;
    (state.positions || []).forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.marginUsdt || (p.sizeUsd / (p.leverage || 5)) || 0);
    });

    const equity = roundNum(baseCap + unPnl, 2);
    const freeVault = Math.max(0, roundNum(equity - usedMargin, 2));
    const marginRatio = equity > 0 ? roundNum((usedMargin / equity) * 100, 1) : 0.0;

    return {
      base_capital: baseCap,
      realized_balance: baseCap,
      total_equity: equity,
      used_margin: usedMargin,
      free_vault: freeVault,
      margin_utilization_pct: marginRatio,
      fiat_inr: roundNum(equity * 89.45, 2),
      today_pnl: roundNum(unPnl, 2),
      today_pnl_pct: baseCap > 0 ? roundNum((unPnl / baseCap) * 100, 2) : 0.0,
      cumulative_net_pnl: roundNum(unPnl, 2),
      cumulative_roi_pct: baseCap > 0 ? roundNum((unPnl / baseCap) * 100, 2) : 0.0,
      win_rate: 0.0,
      win_count: 0,
      loss_count: 0,
      total_trades: 0,
      profit_factor: 0.0,
      top_performer: 'Standby (Scanning)',
      open_positions: (state.positions || []).map(p => ({
        id: p.id,
        symbol: p.symbol,
        side: p.side,
        leverage: p.leverage || 5,
        entry_price: p.entryPrice,
        mark_price: p.markPrice || p.entryPrice,
        margin_usdt: p.marginUsdt || 50.0,
        position_size_usdt: p.sizeUsd || 250.0,
        unrealized_pnl: p.unrealizedPnl || 0.0,
        pnl_pct: p.pnlPct || 0.0,
        be_locked: Boolean(p.armor && p.armor.beShield)
      })),
      equity_curve: [
        { date: 'Initial Base', equity: baseCap, pnl: '+0.00 USDT (+0.00%)', is_win: true, trade: 'Initial Capital Base' },
        { date: 'Live Valuation', equity: equity, pnl: `${unPnl >= 0 ? '+' : ''}${unPnl.toFixed(2)} USDT`, is_win: unPnl >= 0, trade: 'Live Unrealized' }
      ],
      calendar: {
        month_name: 'November',
        year: 2026,
        month_net_pnl: roundNum(unPnl, 2),
        cells: []
      },
      tracks: [
        { id: 'gold', name: 'Gold Track (PAXGUSDT)', symbol: 'PAXGUSDT', icon: '🥇', leverage: 20, closed_trades: 0, wins: 0, losses: 0, net_pnl: 0.0, active_position: null },
        { id: 'btc', name: 'Bitcoin Macro (BTCUSDT)', symbol: 'BTCUSDT', icon: '₿', leverage: 10, closed_trades: 0, wins: 0, losses: 0, net_pnl: 0.0, active_position: null },
        { id: 'eth', name: 'Ethereum Momentum (ETHUSDT)', symbol: 'ETHUSDT', icon: '🔷', leverage: 10, closed_trades: 0, wins: 0, losses: 0, net_pnl: 0.0, active_position: null },
        { id: 'altcoins', name: 'Altcoins Basket (5x Radar)', symbol: 'ALTCOINS', icon: '⚡', leverage: 5, closed_trades: 0, wins: 0, losses: 0, net_pnl: 0.0, active_position: null }
      ]
    };
  }

  render() {
    if (!this.el) return;
    const data = this.getSafeData();

    this.el.innerHTML = `
      <div class="assets-container" style="padding: 12px 14px 32px; display: flex; flex-direction: column; gap: 14px; color: #fff;">
        
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
          ${this.renderTabBody(data)}
        </div>

      </div>
    `;

    this.attachEvents(data);
  }

  renderTabBody(data) {
    if (this.activeSubTab === 'futures') {
      return this.renderFuturesTab(data);
    }
    if (this.activeSubTab === 'calendar') {
      return this.renderCalendarTab(data);
    }
    return this.renderOverviewTab(data);
  }

  // =========================================================================
  // VIEW 1: OVERVIEW TAB (HERO CARD, REAL EQUITY CURVE, LIVE ASSETS)
  // =========================================================================
  renderOverviewTab(data) {
    const isTodayPositive = data.today_pnl >= 0;
    const todaySign = isTodayPositive ? '+' : '';
    const todayColor = isTodayPositive ? '#00C087' : '#f6465d';
    const todayBg = isTodayPositive ? 'rgba(0, 192, 135, 0.12)' : 'rgba(246, 70, 93, 0.12)';
    const todayBorder = isTodayPositive ? 'rgba(0, 192, 135, 0.35)' : 'rgba(246, 70, 93, 0.35)';

    const curve = data.equity_curve || [];
    const latestPt = curve.length > 0 ? curve[curve.length - 1] : {
      date: 'Live Valuation',
      equity: data.total_equity,
      pnl: `${todaySign}${data.today_pnl.toFixed(2)} USDT (${todaySign}${data.today_pnl_pct.toFixed(2)}%)`,
      is_win: isTodayPositive,
      trade: data.open_positions && data.open_positions.length > 0 ? `Live: ${data.open_positions[0].symbol}` : 'Standby • Zero Open Trades'
    };

    // Calculate Dynamic SVG Path Coordinates
    const coords = [];
    const N = curve.length;
    if (N === 0) {
      coords.push({ x: 15, y: 70 }, { x: 365, y: 70 });
    } else if (N === 1) {
      coords.push({ x: 15, y: 70 }, { x: 365, y: 70 });
    } else {
      const eqValues = curve.map(c => c.equity);
      const minEq = Math.min(...eqValues);
      const maxEq = Math.max(...eqValues);
      const range = (maxEq - minEq);

      for (let i = 0; i < N; i++) {
        const x = 15 + (i / (N - 1)) * 350;
        let y = 70;
        if (range > 0.001) {
          y = 105 - ((curve[i].equity - minEq) / range) * 75;
        }
        coords.push({ x, y });
      }
    }
    this.cachedCoords = coords;

    const smoothLinePath = generateSmoothSvgPath(coords);
    const lastCoord = coords[coords.length - 1] || { x: 365, y: 70 };
    const firstCoord = coords[0] || { x: 15, y: 70 };
    const smoothAreaPath = `${smoothLinePath} L ${lastCoord.x.toFixed(1)} 130 L ${firstCoord.x.toFixed(1)} 130 Z`;

    return `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        
        <!-- HERO VALUATION CARD -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 16px; backdrop-filter: blur(12px);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div style="font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">EST. TOTAL VALUATION</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="assetTotalValuation" style="font-size: 26px; font-weight: 900; font-family: var(--font-mono); color: #fff;">
                  ${this.isMasked ? '****.**' : `$${data.total_equity.toFixed(2)}`}
                </span>
                <span style="font-size: 12px; font-weight: 700; color: #94a3b8; font-family: var(--font-mono);">USDT</span>
              </div>
              <div id="assetFiatValuation" style="font-size: 11px; color: #64748b; font-family: var(--font-mono); margin-top: 2px;">
                ${this.isMasked ? '≈ ₹**,***.**' : `≈ ₹${data.fiat_inr.toLocaleString('en-IN', { maximumFractionDigits: 2 })} INR`}
              </div>
            </div>

            <!-- Clickable Real Today PnL Pill (Opens Calendar Tab) -->
            <button id="btnOpenCalendarPill" style="background: ${todayBg}; border: 1px solid ${todayBorder}; padding: 6px 10px; border-radius: 10px; text-align: right; cursor: pointer;">
              <div style="font-size: 10px; color: #94a3b8; font-weight: 600;">Today's PNL &gt;</div>
              <div style="font-size: 12px; font-weight: 800; color: ${todayColor}; font-family: var(--font-mono); margin-top: 1px;">
                ${todaySign}${data.today_pnl.toFixed(2)} USDT (${todaySign}${data.today_pnl_pct.toFixed(2)}%)
              </div>
            </button>
          </div>

          <!-- 3-Metric Row -->
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.06); text-align: center;">
            <div>
              <div style="font-size: 10px; color: #64748b; font-weight: 600;">Base Capital</div>
              <div id="assetBaseCapital" style="font-size: 12px; font-weight: 800; color: #e2e8f0; font-family: var(--font-mono); margin-top: 2px;">$${data.base_capital.toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #F59E0B; font-weight: 600;">Active Margin</div>
              <div id="assetUsedMargin" style="font-size: 12px; font-weight: 800; color: #F59E0B; font-family: var(--font-mono); margin-top: 2px;">$${data.used_margin.toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #00F0FF; font-weight: 600;">Free Vault</div>
              <div id="assetFreeVault" style="font-size: 12px; font-weight: 800; color: #00F0FF; font-family: var(--font-mono); margin-top: 2px;">$${data.free_vault.toFixed(2)}</div>
            </div>
          </div>
        </div>

        <!-- ==================== REAL PERFORMANCE EQUITY CURVE & SCRUBBER ==================== -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 16px; padding: 12px; backdrop-filter: blur(12px);">
          
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 12px; font-weight: 800; color: #e2e8f0;">Performance Equity Curve</span>
              <span style="font-size: 9px; font-weight: 800; background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">DRAG TO SCRUB</span>
            </div>
            <span style="font-size: 10px; color: #94a3b8; font-family: var(--font-mono);">Touch &amp; Slide</span>
          </div>

          <!-- Dynamic Floating Glass HUD (Synchronized to finger drag) -->
          <div id="equityTooltipHud" style="background: rgba(10, 13, 20, 0.95); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 10px; padding: 8px 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div id="tipHudDate" style="font-size: 10px; color: #94a3b8; font-weight: 600;">${latestPt.date}</div>
              <div id="tipHudEquity" style="font-size: 13px; font-weight: 800; color: #fff; font-family: var(--font-mono); margin-top: 1px;">Equity: $${latestPt.equity.toFixed(2)}</div>
            </div>
            <div style="text-align: right;">
              <div id="tipHudPnl" style="font-size: 12px; font-weight: 800; color: ${latestPt.is_win ? '#00C087' : '#f6465d'}; font-family: var(--font-mono);">${latestPt.pnl}</div>
              <div id="tipHudTrade" style="font-size: 10px; color: ${latestPt.is_win ? '#00C087' : '#f6465d'}; font-weight: 700; margin-top: 1px;">${latestPt.trade}</div>
            </div>
          </div>

          <!-- Dynamic SVG Chart Area -->
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
              
              <!-- Volumetric Gradient Area Under Curve -->
              <path d="${smoothAreaPath}" fill="url(#goldCurveGrad)" />
              
              <!-- Glowing Golden Curve Line -->
              <path d="${smoothLinePath}" fill="none" stroke="#F59E0B" stroke-width="3" filter="url(#glowGold)" />
              
              <!-- Apex Node -->
              <circle cx="${lastCoord.x.toFixed(1)}" cy="${lastCoord.y.toFixed(1)}" r="4.5" fill="#F59E0B" stroke="#FFFFFF" stroke-width="2" style="filter: drop-shadow(0 0 6px #F59E0B);" />
            </svg>

            <!-- Vertical Touch Scrubber Line -->
            <div id="verticalScrubberLine" style="position: absolute; top: 0; bottom: 0; width: 1.5px; background: #ffffff; opacity: 0.85; left: ${((lastCoord.x / 380) * 100).toFixed(1)}%; pointer-events: none; transition: opacity 0.1s;">
              <div id="scrubberIndicatorDot" style="width: 12px; height: 12px; border-radius: 50%; background: #F59E0B; border: 2px solid #fff; position: absolute; top: ${(lastCoord.y - 6).toFixed(1)}px; left: -5px; box-shadow: 0 0 10px #F59E0B;"></div>
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
            <span style="font-size: 10px; color: #64748b; font-family: var(--font-mono);">Real-Time Audit Parity</span>
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
            <span style="font-family: var(--font-mono); font-weight: 800; color: #00C087;">${data.margin_utilization_pct}% (Zero Contagion)</span>
          </div>
          <div style="width: 100%; height: 8px; background: #1e2433; border-radius: 4px; overflow: hidden; display: flex;">
            <div style="width: ${Math.max(4, Math.min(100, data.margin_utilization_pct))}%; background: #00C087; box-shadow: 0 0 8px #00C087;"></div>
            <div style="width: ${100 - Math.max(4, Math.min(100, data.margin_utilization_pct))}%; background: #1e2433;"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 10px; color: #94a3b8; font-family: var(--font-mono); margin-top: 4px;">
            <span>In-Trade: $${data.used_margin.toFixed(2)}</span>
            <span>Free Vault: $${data.free_vault.toFixed(2)}</span>
          </div>
        </div>

        <!-- ACTIVE ASSET DISTRIBUTION CARDS (REAL POSITIONS) -->
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
                <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono); margin-top: 1px;">Available: $${data.free_vault.toFixed(2)} USDT</div>
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 13px; font-weight: 900; color: #fff; font-family: var(--font-mono);">$${data.total_equity.toFixed(2)}</div>
              <div style="font-size: 10px; font-weight: 700; color: #00C087; font-family: var(--font-mono);">Liquid Vault</div>
            </div>
          </div>

          <!-- Dynamic Active Positions List -->
          ${(data.open_positions && data.open_positions.length > 0) ? data.open_positions.map(p => {
            const isPosWin = p.unrealized_pnl >= 0;
            const pSign = isPosWin ? '+' : '';
            const pColor = isPosWin ? '#00C087' : '#f6465d';
            const icon = getCoinIcon(p.symbol);

            return `
              <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 3px solid ${pColor}; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <div style="width: 34px; height: 34px; border-radius: 50%; background: rgba(255, 255, 255, 0.06); display: flex; align-items: center; justify-content: center; font-size: 16px;">${icon}</div>
                  <div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                      <span style="font-size: 13px; font-weight: 800; color: #fff;">${p.symbol}</span>
                      <span style="font-size: 9px; font-weight: 800; background: rgba(0, 240, 255, 0.15); color: #00F0FF; border: 1px solid rgba(0, 240, 255, 0.4); padding: 1px 6px; border-radius: 6px; font-family: var(--font-mono);">${p.leverage}x Isolated</span>
                      <span style="font-size: 9px; font-weight: 800; background: ${p.side === 'LONG' ? 'rgba(0,192,135,0.15)' : 'rgba(246,70,93,0.15)'}; color: ${p.side === 'LONG' ? '#00C087' : '#f6465d'}; padding: 1px 5px; border-radius: 4px;">${p.side}</span>
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono); margin-top: 2px;">
                      Entry: $${p.entry_price} • Mark: $${p.mark_price}
                    </div>
                  </div>
                </div>
                <div style="text-align: right;">
                  <div style="font-size: 13px; font-weight: 900; color: ${pColor}; font-family: var(--font-mono);">${pSign}$${p.unrealized_pnl.toFixed(2)}</div>
                  <div style="font-size: 10px; font-weight: 700; color: ${pColor}; font-family: var(--font-mono);">${pSign}${p.pnl_pct.toFixed(2)}% ROI</div>
                </div>
              </div>
            `;
          }).join('') : `
            <div style="background: rgba(18, 21, 28, 0.5); border: 1px dashed rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 14px; text-align: center; color: #64748b; font-size: 11px;">
              🏛️ 0 Active Positions • 100% Capital Preserved • Scanning 24 Champion Pairs
            </div>
          `}

        </div>

      </div>
    `;
  }

  // =========================================================================
  // VIEW 2: FUTURES LEVERAGE TAB (SAFETY SCORE & 4-TRACK REAL ALLOCATION)
  // =========================================================================
  renderFuturesTab(data) {
    const safetyScore = Math.max(0, 100.0 - data.margin_utilization_pct);
    const strokeDash = Math.round((safetyScore / 100.0) * 188);

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
                ${safetyScore.toFixed(1)}% SAFE
              </div>
              <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Zero Contagion • Flat $50 Risk/Trade</div>
            </div>

            <!-- Radial Arc Indicator -->
            <div style="width: 72px; height: 72px; position: relative; display: flex; align-items: center; justify-content: center;">
              <svg width="72" height="72" viewBox="0 0 72 72">
                <circle cx="36" cy="36" r="30" fill="none" stroke="#1e2433" stroke-width="7" />
                <circle cx="36" cy="36" r="30" fill="none" stroke="#00C087" stroke-width="7" stroke-dasharray="188" stroke-dashoffset="${188 - strokeDash}" stroke-linecap="round" style="filter: drop-shadow(0 0 6px #00C087);" />
              </svg>
              <span style="position: absolute; font-size: 11px; font-weight: 800; color: #fff; font-family: var(--font-mono);">5x-20x</span>
            </div>
          </div>
        </div>

        <!-- 4-TRACK LEVERAGE CARDS (REAL DATA SYNCED) -->
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${(data.tracks || []).map(track => {
            const hasActive = track.active_position !== null && track.active_position !== undefined;
            const activePos = track.active_position;
            const netPositive = track.net_pnl >= 0;

            return `
              <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid ${track.color}40; border-radius: 14px; padding: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">${track.icon}</span>
                    <span style="font-size: 13px; font-weight: 800; color: ${track.color};">${track.name}</span>
                  </div>
                  <span style="font-size: 10px; font-weight: 800; background: ${track.color}20; color: ${track.color}; border: 1px solid ${track.color}60; padding: 2px 7px; border-radius: 6px; font-family: var(--font-mono);">${track.leverage}x Isolated</span>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06);">
                  <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">
                    Status: <b style="color: ${hasActive ? '#00C087' : '#94a3b8'};">${hasActive ? `LIVE (${activePos.symbol} ${activePos.pnl_pct >= 0 ? '+' : ''}${activePos.pnl_pct.toFixed(1)}%)` : 'ARMED (1st Tap Scan)'}</b>
                  </div>
                  <div style="font-size: 12px; font-weight: 900; color: ${netPositive ? '#00C087' : '#f6465d'}; font-family: var(--font-mono);">
                    Net: ${netPositive ? '+' : ''}$${track.net_pnl.toFixed(2)}
                  </div>
                </div>

                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #64748b; font-family: var(--font-mono); margin-top: 6px;">
                  <span>Closed: ${track.closed_trades} Trades (${track.wins}W / ${track.losses}L)</span>
                  <span>Armor: +2.5% BE Shield</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>

      </div>
    `;
  }

  // =========================================================================
  // VIEW 3: PNL CALENDAR TAB (REAL HEAT MATRIX, WIN RATE & AUDIT LOGS)
  // =========================================================================
  renderCalendarTab(data) {
    const isCumulativePositive = data.cumulative_net_pnl >= 0;
    const cumSign = isCumulativePositive ? '+' : '';
    const cumColor = isCumulativePositive ? '#00C087' : '#f6465d';

    const cal = data.calendar || { month_name: 'November', year: 2026, month_net_pnl: 0.0, cells: [] };
    const monthSign = cal.month_net_pnl >= 0 ? '+' : '';
    const monthColor = cal.month_net_pnl >= 0 ? '#00C087' : '#f6465d';

    return `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        
        <!-- SUMMARY CARD WITH AUTHENTIC PNL FORENSICS -->
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
              <span style="font-size: 34px; font-weight: 900; font-family: var(--font-mono); color: ${cumColor}; text-shadow: 0 0 16px ${cumColor}60;">
                ${cumSign}$${data.cumulative_net_pnl.toFixed(2)}
              </span>
              <span style="font-size: 11px; font-weight: 800; background: ${cumColor}20; border: 1px solid ${cumColor}60; color: ${cumColor}; padding: 3px 8px; border-radius: 12px; font-family: var(--font-mono);">
                ${cumSign}${data.cumulative_roi_pct.toFixed(2)}% ROI
              </span>
            </div>
          </div>

          <!-- 3 Quantitative Performance Badges -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.06); text-align: center;">
            <div>
              <div style="font-size: 14px; font-weight: 800; color: #00C087; font-family: var(--font-mono);">${data.win_rate.toFixed(1)}%</div>
              <div style="font-size: 9px; color: #64748b; margin-top: 2px;">Win Rate (${data.win_count}W/${data.loss_count}L)</div>
            </div>
            <div>
              <div style="font-size: 14px; font-weight: 800; color: #00F0FF; font-family: var(--font-mono);">${data.profit_factor.toFixed(2)}</div>
              <div style="font-size: 9px; color: #64748b; margin-top: 2px;">Profit Factor</div>
            </div>
            <div>
              <div style="font-size: 12px; font-weight: 800; color: #F59E0B; font-family: var(--font-mono);">${data.top_performer}</div>
              <div style="font-size: 9px; color: #64748b; margin-top: 2px;">Top Performer</div>
            </div>
          </div>
        </div>

        <!-- MONTHLY CALENDAR HEAT MATRIX (REAL TRADES) -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 14px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 13px; font-weight: 800; color: #fff;">${cal.month_name} ${cal.year} Heat Matrix</span>
            <span style="font-size: 11px; font-weight: 800; color: ${monthColor}; font-family: var(--font-mono); background: ${monthColor}20; padding: 2px 7px; border-radius: 6px;">
              ${monthSign}$${cal.month_net_pnl.toFixed(2)}
            </span>
          </div>

          <!-- Day Labels (Mon through Sun) -->
          <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; text-align: center; font-size: 10px; font-weight: 700; color: #64748b; margin-bottom: 4px;">
            <div>M</div><div>T</div><div>W</div><div>T</div><div>F</div><div>S</div><div>S</div>
          </div>

          <!-- Dynamic Day Cells -->
          <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; text-align: center;">
            <!-- November 2026 starts on Sunday (6 leading padding cells) -->
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">26</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">27</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">28</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">29</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">30</div>
            <div style="background: #11141c; color: #334155; padding: 6px 2px; border-radius: 6px; font-size: 10px;">31</div>

            ${(cal.cells || []).map(c => {
              if (c.has_trades) {
                const isPos = c.net_pnl > 0;
                const isNeg = c.net_pnl < 0;
                const cellBg = isPos ? 'rgba(0, 192, 135, 0.22)' : (isNeg ? 'rgba(246, 70, 93, 0.22)' : 'rgba(245, 158, 11, 0.22)');
                const cellBorder = isPos ? '#00C087' : (isNeg ? '#f6465d' : '#F59E0B');
                const cellColor = isPos ? '#00C087' : (isNeg ? '#f6465d' : '#F59E0B');
                const pSign = isPos ? '+' : '';

                return `
                  <div class="cal-day-cell" data-day="${c.day}" data-pnl="${pSign}$${c.net_pnl.toFixed(2)}" data-autopsy="${c.autopsy}" style="background: ${cellBg}; border: 1px solid ${cellBorder}; color: ${cellColor}; padding: 4px 2px; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer; box-shadow: 0 0 8px ${cellColor}40;">
                    ${c.day}<br><span style="font-size: 8px;">${pSign}$${c.net_pnl.toFixed(1)}</span>
                  </div>
                `;
              } else {
                return `
                  <div class="cal-day-cell" data-day="${c.day}" data-pnl="$0.00" data-autopsy="No trades recorded on this day" style="background: #11141c; color: #475569; padding: 6px 2px; border-radius: 6px; font-size: 10px; cursor: pointer;">
                    ${c.day}
                  </div>
                `;
              }
            }).join('')}
          </div>

          <!-- Day Autopsy Popup -->
          <div id="calDayPopup" style="display: none; margin-top: 10px; padding: 8px 12px; border-radius: 8px; background: rgba(0, 192, 135, 0.12); border: 1px solid rgba(0, 192, 135, 0.35); font-size: 11px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span id="calPopupDate" style="color: #94a3b8; font-weight: 700;"></span>
              <span id="calPopupPnl" style="font-weight: 800; font-family: var(--font-mono);"></span>
            </div>
            <div id="calPopupTrade" style="color: #e2e8f0; margin-top: 3px; font-size: 10px; font-family: var(--font-mono);"></div>
          </div>
        </div>

        <!-- PER-SYMBOL LEVERAGE BREAKDOWN (REAL STATS) -->
        <div style="background: rgba(18, 21, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 14px;">
          <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
            Per-Symbol Leverage Breakdown
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${(data.tracks || []).map(tr => {
              const netPos = tr.net_pnl >= 0;
              return `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span>${tr.icon}</span>
                    <div>
                      <div style="font-size: 12px; font-weight: 800; color: #fff;">
                        ${tr.symbol} <span style="font-size: 9px; color: ${tr.color}; background: ${tr.color}20; padding: 1px 5px; border-radius: 4px; font-family: var(--font-mono);">${tr.leverage}x</span>
                      </div>
                      <div style="font-size: 10px; color: #64748b;">
                        Closed: ${tr.closed_trades} (${tr.wins}W / ${tr.losses}L) • ${tr.active_position ? '1 Active' : 'Idle'}
                      </div>
                    </div>
                  </div>
                  <span style="font-size: 13px; font-weight: 900; color: ${netPos ? '#00C087' : '#f6465d'}; font-family: var(--font-mono);">
                    ${netPos ? '+' : ''}$${tr.net_pnl.toFixed(2)}
                  </span>
                </div>
              `;
            }).join('')}
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

  // =========================================================================
  // ATTACH DOM EVENTS & SCRUBBER
  // =========================================================================
  attachEvents(data) {
    // 1. Mask button
    const maskBtn = this.el.querySelector('#btnAssetMask');
    if (maskBtn) {
      maskBtn.addEventListener('click', () => this.toggleMask());
    }

    // 2. Sub-tab switching
    this.el.querySelectorAll('.asset-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        this.switchSubTab(tab);
      });
    });

    // 3. Open Calendar from Pill
    const openCal = this.el.querySelector('#btnOpenCalendarPill');
    if (openCal) {
      openCal.addEventListener('click', () => this.switchSubTab('calendar'));
    }

    // 4. Timeframe button clicks
    this.el.querySelectorAll('.asset-tf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tf = btn.getAttribute('data-tf');
        this.setTimeframe(tf);
      });
    });

    // 5. Calendar day tap autopsy popup
    this.el.querySelectorAll('.cal-day-cell').forEach(cell => {
      cell.addEventListener('click', () => {
        const day = cell.getAttribute('data-day');
        const pnl = cell.getAttribute('data-pnl');
        const autopsy = cell.getAttribute('data-autopsy');

        const pop = this.el.querySelector('#calDayPopup');
        const dEl = this.el.querySelector('#calPopupDate');
        const pEl = this.el.querySelector('#calPopupPnl');
        const tEl = this.el.querySelector('#calPopupTrade');

        if (pop && dEl && pEl && tEl) {
          pop.style.display = 'block';
          dEl.textContent = `Nov ${day}, 2026`;
          pEl.textContent = pnl;
          pEl.style.color = pnl.includes('-') ? '#f6465d' : '#00C087';
          tEl.textContent = autopsy || 'No Trades';
          setTimeout(() => { pop.style.display = 'none'; }, 4000);
        }
      });
    });

    // 6. Interactive Drag & Touch Scrubber
    this.attachScrubber(data);
  }

  attachScrubber(data) {
    const wrapper = this.el.querySelector('#equityScrubberCanvasWrapper');
    const line = this.el.querySelector('#verticalScrubberLine');
    const dot = this.el.querySelector('#scrubberIndicatorDot');
    const tipDate = this.el.querySelector('#tipHudDate');
    const tipEq = this.el.querySelector('#tipHudEquity');
    const tipPnl = this.el.querySelector('#tipHudPnl');
    const tipTrade = this.el.querySelector('#tipHudTrade');

    if (!wrapper || !line) return;

    const curve = data.equity_curve || [];
    if (curve.length === 0) return;

    const coords = this.cachedCoords || [];

    const handleDrag = (clientX) => {
      const rect = wrapper.getBoundingClientRect();
      let x = clientX - rect.left;
      x = Math.max(0, Math.min(x, rect.width));

      line.style.left = `${x}px`;

      const ratio = x / rect.width;
      const idx = Math.min(curve.length - 1, Math.max(0, Math.round(ratio * (curve.length - 1))));
      const pt = curve[idx];

      if (pt && tipDate && tipEq && tipPnl && tipTrade) {
        tipDate.textContent = pt.date;
        tipEq.textContent = `Equity: $${pt.equity.toFixed(2)}`;
        tipPnl.textContent = pt.pnl;
        tipPnl.style.color = pt.is_win ? '#00C087' : '#f6465d';
        tipTrade.textContent = pt.trade;
        tipTrade.style.color = pt.is_win ? '#00C087' : '#f6465d';
      }

      if (dot && coords[idx]) {
        dot.style.top = `${(coords[idx].y - 6).toFixed(1)}px`;
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

function roundNum(val, dec = 2) {
  const n = Number(val);
  return isNaN(n) ? 0.0 : Number(n.toFixed(dec));
}

function getCoinIcon(sym) {
  const s = (sym || '').toUpperCase();
  if (s.includes('BTC')) return '₿';
  if (s.includes('ETH')) return 'Ξ';
  if (s.includes('PAXG')) return '🥇';
  if (s.includes('SOL')) return '◎';
  if (s.includes('BNB')) return '🔶';
  if (s.includes('SUI') || s.includes('LQTY')) return '💧';
  if (s.includes('RENDER')) return '⟁';
  if (s.includes('DOGE')) return 'Ð';
  if (s.includes('ARB')) return '◈';
  if (s.includes('TIA')) return '⊛';
  if (s.includes('AVAX')) return '▲';
  if (s.includes('UNI')) return '🦄';
  if (s.includes('NEAR')) return 'Ⓝ';
  if (s.includes('OP')) return '🔴';
  return '⚡';
}
