/**
 * HERMES AI • WATCHLIST COMPONENT (1:1 IMAGE 3 TRADINGVIEW PARITY)
 * Pure OLED #000000 black, authentic coin badges, red flag indicator,
 * live price ticks, dynamic coin search & add, and 1-tap seamless navigation to chart.
 * Editing this file NEVER affects the chart or position card.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

export class Watchlist {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.searchQuery = '';
    this.init();
  }

  init() {
    this.render();
    bus.on('price:updated', (payload) => this.onPriceUpdate(payload));
    bus.on('watchlist:updated', () => this.render());
  }

  formatPrice(price, precision = 2) {
    if (!price || isNaN(price)) return '0.00';
    if (precision === 0 || price >= 1000) {
      return Math.round(price).toLocaleString('en-US');
    }
    return price.toLocaleString('en-US', {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision
    });
  }

  onPriceUpdate({ symbol, data }) {
    const row = this.el.querySelector(`[data-row="${symbol}"]`);
    if (!row) return;

    const priceEl = row.querySelector('.coin-price');
    const changeAbsEl = row.querySelector('.coin-change-abs');
    const changePctEl = row.querySelector('.coin-change-pct');
    const item = state.watchlist.find(w => w.symbol === symbol);
    const precision = item ? item.precision : (data.price < 1 ? 4 : 2);

    if (priceEl) {
      priceEl.textContent = this.formatPrice(data.price, precision);
      priceEl.classList.remove('flash-up', 'flash-down');
      void priceEl.offsetWidth;
      priceEl.classList.add(data.direction === 'up' ? 'flash-up' : 'flash-down');
    }

    if (changeAbsEl && data.changeAbs !== undefined) {
      const isPos = data.changeAbs >= 0;
      const absFormatted = this.formatPrice(Math.abs(data.changeAbs), precision);
      changeAbsEl.textContent = `${isPos ? '+' : '-'}${absFormatted}`;
      changeAbsEl.className = `coin-change-abs mono ${isPos ? 'text-green' : 'text-red'}`;
    }

    if (changePctEl && data.changePct !== undefined) {
      const isPos = data.changePct >= 0;
      changePctEl.textContent = `${isPos ? '+' : ''}${data.changePct.toFixed(2)}%`;
      changePctEl.className = `coin-change-pct mono ${isPos ? 'text-green' : 'text-red'}`;
    }
  }

  render() {
    const filteredCoins = state.watchlist.filter(c => {
      if (!this.searchQuery) return true;
      const q = this.searchQuery.toLowerCase();
      return c.symbol.toLowerCase().includes(q) || c.name.toLowerCase().includes(q) || c.subName.toLowerCase().includes(q);
    });

    this.el.innerHTML = `
      <div class="watchlist-container">
        <!-- Header -->
        <div class="watchlist-header">
          <span class="watchlist-title">WATCHLIST</span>
          <span class="watchlist-count mono">${state.watchlist.length} PAIRS</span>
        </div>

        <!-- Search Bar with Add Option -->
        <div class="watchlist-search-box">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input 
              type="text" 
              class="wl-search-input mono" 
              placeholder="Search or type new coin (e.g. XRP, PEPE)..." 
              value="${this.searchQuery}" 
            />
          </div>
          <button class="wl-add-btn" id="btn-add-searched-coin" title="Add coin to Watchlist">+ ADD</button>
        </div>

        <!-- List -->
        <div class="watchlist-list">
          ${filteredCoins.length === 0 ? `
            <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 12px;">
              <div>No coins matched "${this.searchQuery}"</div>
              <div style="margin-top: 8px;">
                <button class="wl-inline-add-btn" id="btn-inline-add">Add "${this.searchQuery.toUpperCase()}" to Watchlist</button>
              </div>
            </div>
          ` : filteredCoins.map(coin => {
            const isPos = coin.changePct >= 0;
            const priceStr = this.formatPrice(coin.price, coin.precision);
            const absStr = this.formatPrice(Math.abs(coin.changeAbs), coin.precision);

            return `
              <div class="coin-row" data-row="${coin.symbol}">
                ${coin.hasRedFlag ? '<div class="coin-red-flag"></div>' : ''}
                
                <div class="coin-logo-wrap">
                  <div class="coin-logo" style="background: ${coin.iconBg};">
                    ${coin.icon}
                  </div>
                </div>

                <div class="coin-info">
                  <div class="coin-name-row">
                    <span class="coin-symbol">${coin.name}</span>
                  </div>
                  <div class="coin-full-name">${coin.subName}</div>
                </div>

                <div class="coin-pricing">
                  <div class="coin-price mono">${priceStr}</div>
                  <div class="coin-change-row">
                    <span class="coin-change-abs mono ${isPos ? 'text-green' : 'text-red'}">
                      ${isPos ? '+' : '-'}${absStr}
                    </span>
                    <span class="coin-change-pct mono ${isPos ? 'text-green' : 'text-red'}">
                      ${isPos ? '+' : ''}${coin.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;

    // Attach Search Handlers
    const input = this.el.querySelector('.wl-search-input');
    if (input) {
      input.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim();
        this.renderFilteredList();
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          this.handleAddCoin(input.value);
        }
      });
    }

    const btnAdd = this.el.querySelector('#btn-add-searched-coin');
    if (btnAdd && input) {
      btnAdd.addEventListener('click', () => {
        this.handleAddCoin(input.value);
      });
    }

    const btnInline = this.el.querySelector('#btn-inline-add');
    if (btnInline && input) {
      btnInline.addEventListener('click', () => {
        this.handleAddCoin(this.searchQuery);
      });
    }

    this.attachRowClicks();
  }

  renderFilteredList() {
    const listEl = this.el.querySelector('.watchlist-list');
    if (!listEl) return;

    const filtered = state.watchlist.filter(c => {
      if (!this.searchQuery) return true;
      const q = this.searchQuery.toLowerCase();
      return c.symbol.toLowerCase().includes(q) || c.name.toLowerCase().includes(q) || c.subName.toLowerCase().includes(q);
    });

    if (filtered.length === 0) {
      listEl.innerHTML = `
        <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 12px;">
          <div>No coins matched "${this.searchQuery}"</div>
          <div style="margin-top: 8px;">
            <button class="wl-inline-add-btn" id="btn-inline-add-dyn">Add "${this.searchQuery.toUpperCase()}" to Watchlist</button>
          </div>
        </div>
      `;
      const dynBtn = listEl.querySelector('#btn-inline-add-dyn');
      if (dynBtn) {
        dynBtn.addEventListener('click', () => this.handleAddCoin(this.searchQuery));
      }
      return;
    }

    listEl.innerHTML = filtered.map(coin => {
      const isPos = coin.changePct >= 0;
      const priceStr = this.formatPrice(coin.price, coin.precision);
      const absStr = this.formatPrice(Math.abs(coin.changeAbs), coin.precision);

      return `
        <div class="coin-row" data-row="${coin.symbol}">
          ${coin.hasRedFlag ? '<div class="coin-red-flag"></div>' : ''}
          <div class="coin-logo-wrap">
            <div class="coin-logo" style="background: ${coin.iconBg};">${coin.icon}</div>
          </div>
          <div class="coin-info">
            <div class="coin-name-row">
              <span class="coin-symbol">${coin.name}</span>
            </div>
            <div class="coin-full-name">${coin.subName}</div>
          </div>
          <div class="coin-pricing">
            <div class="coin-price mono">${priceStr}</div>
            <div class="coin-change-row">
              <span class="coin-change-abs mono ${isPos ? 'text-green' : 'text-red'}">
                ${isPos ? '+' : '-'}${absStr}
              </span>
              <span class="coin-change-pct mono ${isPos ? 'text-green' : 'text-red'}">
                ${isPos ? '+' : ''}${coin.changePct.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    this.attachRowClicks();
  }

  handleAddCoin(text) {
    if (!text || !text.trim()) return;
    const added = state.addWatchlistCoin(text.trim());
    if (added) {
      this.searchQuery = '';
      this.render();
    }
  }

  attachRowClicks() {
    this.el.querySelectorAll('.coin-row').forEach(row => {
      row.addEventListener('click', () => {
        const symbol = row.getAttribute('data-row');
        state.selectSymbol(symbol);
        state.setView('chart');
      });
    });
  }
}
