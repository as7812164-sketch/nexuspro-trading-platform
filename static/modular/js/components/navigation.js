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

        <button class="nav-tab ${state.activeView === 'assets' ? 'active' : ''}" data-view="assets">
          <span class="nav-icon" style="filter: drop-shadow(0 0 6px rgba(245, 158, 11, 0.4));">💼</span>
          <span class="nav-label" style="${state.activeView === 'assets' ? 'color:#f59e0b; font-weight:800;' : ''}">Assets</span>
        </button>
      </nav>
    `;

    // Attach click events
    this.el.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const view = tab.getAttribute('data-view');
        state.setView(view);
      });
    });
  }
}
