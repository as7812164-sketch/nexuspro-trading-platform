/**
 * NEXUSPRO • BOTTOM NAVIGATION COMPONENT (ISOLATED)
 * Renders 5-Tab Sticky Bottom Bar (Watchlist, Chart, Citadel, Positions, Menu)
 * Decoupled: Emits view changes to StateStore.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

export class Navigation {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.init();
  }

  init() {
    this.render();
    bus.on('view:changed', (viewName) => this.onViewChanged(viewName));
  }

  onViewChanged(viewName) {
    this.el.querySelectorAll('.nav-tab').forEach(tab => {
      if (tab.getAttribute('data-view') === viewName) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    // Toggle view containers
    document.querySelectorAll('.view-panel').forEach(panel => {
      if (panel.id === `view-${viewName}`) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });
  }

  render() {
    this.el.innerHTML = `
      <nav class="bottom-nav">
        <button class="nav-tab ${state.activeView === 'watchlist' ? 'active' : ''}" data-view="watchlist">
          <span class="nav-icon">📑</span>
          <span class="nav-label">Watchlist</span>
        </button>

        <button class="nav-tab ${state.activeView === 'chart' ? 'active' : ''}" data-view="chart">
          <span class="nav-icon">📈</span>
          <span class="nav-label">Chart</span>
        </button>

        <button class="nav-tab ${state.activeView === 'dashboard' ? 'active' : ''}" data-view="dashboard">
          <span class="nav-icon">🏛️</span>
          <span class="nav-label">Citadel</span>
        </button>

        <button class="nav-tab ${state.activeView === 'positions' ? 'active' : ''}" data-view="positions">
          <span class="nav-icon">📊</span>
          <span class="nav-label">Positions</span>
        </button>

        <button class="nav-tab ${state.activeView === 'menu' ? 'active' : ''}" data-view="menu">
          <span class="nav-icon">⚙️</span>
          <span class="nav-label">Menu</span>
        </button>
      </nav>
    `;

    // Attach click events
    this.el.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const view = tab.getAttribute('data-view');
        if (view === 'menu') {
          alert('NexusPro Institutional Terminal v2.2\nStrategy: Hermes MS-OB v2.0 GOLDEN Exclusive\nMode: BUY / LONG Only • 1st Tap Valid | 2nd Tap Invalidated\nCapital: $1,000 Flat (Zero Compounding)\nMargin: Flat $50 (5%) • 5x Isolated\nArmor: BE Lock +12% -> +2.5% | Hard SL -15% (2x15m) | TP +15%');
          return;
        }
        state.setView(view);
      });
    });
  }
}
