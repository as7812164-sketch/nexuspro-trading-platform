/**
 * HERMES AI • WALLET SUMMARY COMPONENT (ISOLATED)
 * Displays Base Capital ($500.00), Total Equity ($500.00), Margin utilization ($0.00), and Net return.
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
      unPnl += p.unrealizedPnl;
      usedMargin += (p.sizeUsd / p.leverage);
    });

    const equity = state.account.baseCapital + unPnl;
    const pnlPct = state.account.baseCapital > 0 ? (unPnl / state.account.baseCapital) * 100 : 0;
    const freeMargin = Math.max(0, equity - usedMargin);

    const eqEl = this.el.querySelector('.wallet-balance');
    const pillEl = this.el.querySelector('.wallet-pill');
    const usedEl = this.el.querySelector('#wallet-used-margin');
    const freeEl = this.el.querySelector('#wallet-free-margin');

    if (eqEl) eqEl.textContent = `$${equity.toFixed(2)}`;
    const baseEl = this.el.querySelector('#wallet-base-capital');
    if (baseEl) baseEl.textContent = `$${state.account.baseCapital.toFixed(2)}`;
    if (pillEl) {
      if (state.positions.length > 0) {
        pillEl.textContent = `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}% Active`;
        pillEl.className = `wallet-pill mono ${pnlPct >= 0 ? 'text-green' : 'text-red'}`;
      } else {
        const totPct = Number(state.account.totalPnlPct || 0);
        pillEl.textContent = `${totPct >= 0 ? '+' : ''}${totPct.toFixed(2)}% Return`;
        pillEl.className = `wallet-pill mono ${totPct >= 0 ? 'text-green' : 'text-red'}`;
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

    const equity = acc.baseCapital + unPnl;
    const pnlPct = acc.baseCapital > 0 ? (unPnl / acc.baseCapital) * 100 : 0;
    const freeMargin = Math.max(0, equity - usedMargin);
    const hasOpen = state.positions.length > 0;
    const displayPct = hasOpen ? pnlPct : Number(acc.totalPnlPct || 0);
    const pillLabel = hasOpen ? 'Active' : 'Return';

    this.el.innerHTML = `
      <div class="wallet-card">
        <div class="wallet-top">
          <div>
            <div class="wallet-label">TOTAL PORTFOLIO EQUITY</div>
            <div class="wallet-balance mono">$${equity.toFixed(2)}</div>
          </div>
          <div class="wallet-pill mono ${displayPct >= 0 ? 'text-green' : 'text-red'}">
            ${displayPct >= 0 ? '+' : ''}${displayPct.toFixed(2)}% ${pillLabel}
          </div>
        </div>

        <div class="wallet-stats-grid">
          <div class="wallet-stat-item">
            <span class="stat-name">BASE CAPITAL</span>
            <span class="stat-val mono text-primary" id="wallet-base-capital">$${acc.baseCapital.toFixed(2)}</span>
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
