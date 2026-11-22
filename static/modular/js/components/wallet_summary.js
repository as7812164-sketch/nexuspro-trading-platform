/**
 * HERMES AI • WALLET SUMMARY COMPONENT (ISOLATED)
 * Displays 2-Row Institutional Matrix for NexusPro:
 * Fresh Start Portfolio Scale: $500.00 Starting Base (10 Deca Sections @ $50 each)
 * Monotonic High-Watermark (ATH) & Low-Watermark (ATL) Ratchet:
 * - When equity moves 500 -> 510: ATH ratchets to $510.00.
 * - When trade loses 510 -> 505: ATH DOES NOT DROP! Remains $510.00.
 * - When subsequent trade hits 525: ATH ratchets to $525.00.
 * - ATL records lowest equity ever reached (starts at $500.00).
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

  getMetrics(baseCap, currentBal, equity) {
    const acc = state.account || {};
    let savedAth = baseCap;
    let savedAtl = baseCap;
    try {
      const lsAth = localStorage.getItem('nexuspro_ath');
      const lsAtl = localStorage.getItem('nexuspro_atl');
      savedAth = lsAth ? Number(lsAth) : Number(acc.all_time_high || baseCap);
      savedAtl = lsAtl ? Number(lsAtl) : Number(acc.all_time_low || baseCap);
    } catch(e) {}

    const ath = Math.max(savedAth, equity, currentBal, baseCap);
    const atl = Math.min(savedAtl, equity, currentBal, baseCap);
    const peakProfit = Math.max(0.0, ath - baseCap);

    try {
      localStorage.setItem('nexuspro_ath', String(ath));
      localStorage.setItem('nexuspro_atl', String(atl));
    } catch(e) {}

    return { ath, atl, peakProfit };
  }

  updateDynamicValues() {
    let unPnl = 0;
    let usedMargin = 0;
    state.positions.forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const baseCap = 500.00; // Fresh 10-Section Base Capital ($50 x 10)
    const currentBal = Number(state.account.baseCapital || 500.00);
    const equity = currentBal + unPnl;
    const pnlPct = baseCap > 0 ? ((equity - baseCap) / baseCap) * 100 : 0;
    const freeMargin = Math.max(0, currentBal - usedMargin);
    const { ath, atl, peakProfit } = this.getMetrics(baseCap, currentBal, equity);

    const eqEl = this.el?.querySelector('.wallet-balance');
    const pillEl = this.el?.querySelector('.wallet-pill');
    const usedEl = this.el?.querySelector('#wallet-used-margin');
    const freeEl = this.el?.querySelector('#wallet-free-margin');
    const athEl = this.el?.querySelector('#wallet-ath-val');
    const atlEl = this.el?.querySelector('#wallet-atl-val');
    const peakPnlEl = this.el?.querySelector('#wallet-peak-profit');

    if (eqEl) eqEl.textContent = `$${equity.toFixed(2)}`;
    if (athEl) athEl.textContent = `$${ath.toFixed(2)}`;
    if (atlEl) atlEl.textContent = `$${atl.toFixed(2)}`;
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
    const acc = state.account || {};
    let unPnl = 0;
    let usedMargin = 0;
    state.positions.forEach(p => {
      unPnl += (p.unrealizedPnl || 0);
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const baseCap = 500.00; // Fresh 10-Section Base Capital ($50 x 10)
    const currentBal = Number(acc.baseCapital || 500.00);
    const equity = currentBal + unPnl;
    const pnlPct = baseCap > 0 ? ((equity - baseCap) / baseCap) * 100 : 0;
    const freeMargin = Math.max(0, currentBal - usedMargin);
    const hasOpen = state.positions.length > 0;
    const pillLabel = hasOpen ? 'Active' : 'Return';

    const { ath, atl, peakProfit } = this.getMetrics(baseCap, currentBal, equity);

    if (!this.el) return;
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
            <span class="stat-val mono text-primary" id="wallet-ath-val" style="color:#FFFFFF; font-weight:800;">$${ath.toFixed(2)}</span>
          </div>
          <div class="wallet-stat-item">
            <span class="stat-name text-cyan" style="color:#38BDF8; font-weight:700;"><i class="fa-solid fa-shield-halved"></i> ATL (FLOOR)</span>
            <span class="stat-val mono text-primary" id="wallet-atl-val" style="color:#FFFFFF; font-weight:800;">$${atl.toFixed(2)}</span>
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

