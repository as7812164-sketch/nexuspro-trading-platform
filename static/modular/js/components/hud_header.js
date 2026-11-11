/**
 * NEXUSPRO • HUD HEADER COMPONENT (ISOLATED)
 * Renders Top Institutional Header & Sentry Network Status.
 * Editing this file NEVER affects the chart or watchlist.
 */

import { bus } from '../core/event_bus.js';
import { state } from '../core/state.js';

export class HudHeader {
  constructor(mountSelector) {
    this.el = document.querySelector(mountSelector);
    this.init();
  }

  init() {
    this.render();
    bus.on('ws:status', (status) => this.updateLatency(status.connected));

    const refreshBtn = this.el.querySelector('#btn-hud-refresh');
    const refreshIcon = this.el.querySelector('#hud-refresh-icon');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        if (refreshIcon) {
          refreshIcon.style.transition = 'transform 0.5s ease';
          refreshIcon.style.transform = 'rotate(360deg)';
          setTimeout(() => {
            refreshIcon.style.transition = 'none';
            refreshIcon.style.transform = 'rotate(0deg)';
          }, 500);
        }
        state.syncPositionsFromServer();
        bus.emit('request:refresh_all');
      });
    }
  }

  updateLatency(connected) {
    const pill = this.el.querySelector('.latency-pill');
    if (pill) {
      if (connected) {
        pill.textContent = '24ms';
        pill.classList.remove('text-red');
        pill.classList.add('text-green');
      } else {
        pill.textContent = 'OFFLINE';
        pill.classList.remove('text-green');
        pill.classList.add('text-red');
      }
    }
  }

  render() {
    this.el.innerHTML = `
      <header class="hud-header">
        <div class="hud-brand">
          <span class="hud-logo">🏛️</span>
          <div class="hud-title">
            <span>NEXUSPRO</span>
            <span class="hud-badge">HERMES MS-OB</span>
          </div>
        </div>

        <div class="hud-status-group">
          <button id="btn-hud-refresh" title="Instant Refresh Balance & Positions" style="background: rgba(37, 99, 235, 0.12); border: 1px solid rgba(37, 99, 235, 0.3); color: #60a5fa; width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.3s ease;">
            <span id="hud-refresh-icon" style="font-size: 13px; display: inline-block;">🔄</span>
          </button>
          <div class="sentry-pill" title="Hermes MS-OB 7-Model First Tap Active">
            <span class="sentry-dot"></span>
            <span>MS-OB v2</span>
          </div>
          <div class="latency-pill mono">24ms</div>
        </div>
      </header>
    `;
  }
}
