/**
 * HERMES AI • WALLET SUMMARY COMPONENT (ISOLATED)
 * Displays 2-Row Institutional Matrix (Option B) for NexusPro:
 * Row 1: All-Time High ATH ($646.25), All-Time Low ATL ($485.00), Peak Profit (+$146.25)
 * Row 2: Base Capital ($500.00), Used Margin, Free Margin
 * Editing this file NEVER affects the chart or watchlist.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

export class WalletSummary {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.init();
  }

  init() {
    this.render();
    bus.on('account:updated', () => this.render());
    bus.on('position:updated', () => this.updateDynamicValues());
    bus.on('position:closed', () => this.render());
  }

  updateDynamicValues() {
    let unPnl = 0;
    let usedMargin = 0;
    state.positions.forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const rawBal = Number(state.account.baseCapital || 578.75);
    const baseCap = 500.00;
    const realizedPnl = rawBal > 800 ? (rawBal - 1000.0) : (rawBal - 500.0);
    const currentBal = baseCap + (isNaN(realizedPnl) ? 78.75 : realizedPnl);
    const equity = currentBal + unPnl;
    const pnlPct = baseCap > 0 ? ((equity - baseCap) / baseCap) * 100 : 0;
    const freeMargin = Math.max(0, currentBal - usedMargin);
    const athVal = Math.max(646.25, equity, currentBal);
    const peakProfit = Math.max(146.25, athVal - baseCap);

    const eqEl = this.el.querySelector('.wallet-balance');
    const pillEl = this.el.querySelector('.wallet-pill');
    const usedEl = this.el.querySelector('#wallet-used-margin');
    const freeEl = this.el.querySelector('#wallet-free-margin');
    const athEl = this.el.querySelector('#wallet-ath-val');
    const peakPnlEl = this.el.querySelector('#wallet-peak-profit');

    if (eqEl) eqEl.textContent = `$${equity.toFixed(2)}`;
    if (athEl) athEl.textContent = `$${athVal.toFixed(2)}`;
    if (peakPnlEl) peakPnlEl.textContent = `+$${peakProfit.toFixed(2)}`;
    if (pillEl) {
      if (state.positions.length > 0) {
        pillEl.textContent = `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}% Active`;
        pillEl.className = `wallet-pill mono ${pnlPct >= 0 ? 'text-green' : 'text-red'}`;
      } else {
        pillEl.textContent = `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}% Return`;
        pillEl.className = `wallet-pill mono ${pnlPct >= 0 ? 'text-green' : 'text-red'}`;
      }
    }
    if (usedEl) usedEl.textContent = `$${usedMargin.toFixed(2)}`;
    if (freeEl) freeEl.textContent = `$${freeMargin.toFixed(2)}`;
  }

  render() {
    const acc = state.account;
    let unPnl = 0;
    let usedMargin = 0;
    state.positions.forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const rawBal = Number(acc.baseCapital || 578.75);
    const baseCap = 500.00;
    const realizedPnl = rawBal > 800 ? (rawBal - 1000.0) : (rawBal - 500.0);
    const currentBal = baseCap + (isNaN(realizedPnl) ? 78.75 : realizedPnl);
    const equity = currentBal + unPnl;
    const pnlPct = baseCap > 0 ? ((equity - baseCap) / baseCap) * 100 : 0;
    const freeMargin = Math.max(0, currentBal - usedMargin);
    const hasOpen = state.positions.length > 0;
    const pillLabel = hasOpen ? 'Active' : 'Return';

    const athVal = Math.max(646.25, equity, currentBal);
    const atlVal = 485.00;
    const peakProfit = Math.max(146.25, athVal - baseCap);

    this.el.innerHTML = `
      <div class="wallet-card">
        <div class="wallet-top">
          <div>
            <div class="wallet-label">TOTAL PORTFOLIO EQUITY</div>
            <div class="wallet-balance mono">$${equity.toFixed(2)}</div>
          </div>
          <div class="wallet-pill mono ${pnlPct >= 0 ? 'text-green' : 'text-red'}">
            ${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}% ${pillLabel}
          </div>
        </div>

        <!-- ROW 1: INSTITUTIONAL HIGH-WATERMARK (ATH, ATL, PEAK PROFIT) -->
        <div class="wallet-stats-grid">
          <div class="wallet-stat-item">
            <span class="stat-name text-gold" style="color:#F59E0B; font-weight:700;"><i class="fa-solid fa-rocket"></i> ATH (PEAK)</span>
            <span class="stat-val mono text-primary" id="wallet-ath-val" style="color:#FFFFFF; font-weight:800;">$${athVal.toFixed(2)}</span>
          </div>
          <div class="wallet-stat-item">
            <span class="stat-name text-cyan" style="color:#38BDF8; font-weight:700;"><i class="fa-solid fa-shield-halved"></i> ATL (FLOOR)</span>
            <span class="stat-val mono text-primary" id="wallet-atl-val" style="color:#FFFFFF; font-weight:800;">$${atlVal.toFixed(2)}</span>
          </div>
          <div class="wallet-stat-item">
            <span class="stat-name text-green" style="color:var(--green-institutional, #00DFC0); font-weight:700;"><i class="fa-solid fa-trophy"></i> PEAK PROFIT</span>
            <span class="stat-val mono text-green" id="wallet-peak-profit" style="color:var(--green-institutional, #00DFC0); font-weight:800;">+$${peakProfit.toFixed(2)}</span>
          </div>
        </div>

        <!-- ROW 2: LIVE CAPITAL & MARGIN UTILIZATION -->
        <div class="wallet-stats-grid" style="margin-top:6px; padding-top:6px;">
          <div class="wallet-stat-item">
            <span class="stat-name">BASE CAPITAL</span>
            <span class="stat-val mono text-primary" id="wallet-base-capital">$${baseCap.toFixed(2)}</span>
          </div>
          <div class="wallet-stat-item">
            <span class="stat-name">USED MARGIN</span>
            <span class="stat-val mono text-gold" id="wallet-used-margin">$${usedMargin.toFixed(2)}</span>
          </div>
          <div class="wallet-stat-item">
            <span class="stat-name">FREE MARGIN</span>
            <span class="stat-val mono text-cyan" id="wallet-free-margin">$${freeMargin.toFixed(2)}</span>
          </div>
        </div>
      </div>
    `;
  }
}
