/**
 * NEXUSPRO • TICKER CAROUSEL COMPONENT (ISOLATED)
 * Renders quick horizontal scrollable coin chips.
 * Tapping any chip opens the chart for that coin.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

export class TickerCarousel {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.keyCoins = ['BTCUSDT', 'ETHUSDT', 'PAXGUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOGEUSDT', 'NEARUSDT', 'SUIUSDT', 'RENDERUSDT'];
    this.init();
  }

  init() {
    this.render();
    bus.on('price:updated', (payload) => this.onPriceUpdate(payload));
  }

  onPriceUpdate({ symbol, data }) {
    const chip = this.el.querySelector(`[data-chip="${symbol}"]`);
    if (!chip) return;

    const priceEl = chip.querySelector('.chip-price');
    const changeEl = chip.querySelector('.chip-change');

    if (priceEl) {
      priceEl.textContent = data.price < 1 ? data.price.toFixed(4) : data.price.toFixed(2);
      priceEl.classList.remove('flash-up', 'flash-down');
      void priceEl.offsetWidth; // trigger reflow
      priceEl.classList.add(data.direction === 'up' ? 'flash-up' : 'flash-down');
    }

    if (changeEl && data.changePct !== undefined) {
      const isPos = data.changePct >= 0;
      changeEl.textContent = `${isPos ? '+' : ''}${data.changePct.toFixed(2)}%`;
      changeEl.className = `chip-change mono ${isPos ? 'text-green' : 'text-red'}`;
    }
  }

  render() {
    this.el.innerHTML = `
      <div class="carousel-container">
        ${this.keyCoins.map(sym => {
          const item = state.watchlist.find(w => w.symbol === sym) || { name: sym, price: 0, changePct: 0 };
          const isPos = item.changePct >= 0;
          return `
            <div class="ticker-chip" data-chip="${sym}">
              <div class="chip-top">
                <span class="chip-symbol">${item.name || sym}</span>
                <span class="chip-change mono ${isPos ? 'text-green' : 'text-red'}">
                  ${isPos ? '+' : ''}${item.changePct.toFixed(2)}%
                </span>
              </div>
              <div class="chip-price mono">
                ${item.price < 1 ? item.price.toFixed(4) : item.price.toFixed(2)}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    // Attach Click Handlers
    this.el.querySelectorAll('.ticker-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const sym = chip.getAttribute('data-chip');
        state.selectSymbol(sym);
        state.setView('chart');
      });
    });
  }
}
