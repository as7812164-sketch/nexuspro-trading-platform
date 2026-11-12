/**
 * NEXUSPRO • MAIN BOOTSTRAP (PONYTAIL STANDARD)
 * Assembles all isolated components into the DOM.
 * Keeps canonical ES module paths (single shared StateStore/EventBus instance).
 */

import { state } from './core/state.js';
import { bus } from './core/event_bus.js';
import { connector } from './core/websocket.js';

// Modular Components
import { HudHeader } from './components/hud_header.js';
import { WalletSummary } from './components/wallet_summary.js';
import { TickerCarousel } from './components/ticker_carousel.js';
import { PositionCard } from './components/position_card.js';
import { Watchlist } from './components/watchlist.js';
import { ChartTerminal } from './components/chart_terminal.js?v=tv_1to1_v5';
import { Navigation } from './components/navigation.js';

document.addEventListener('DOMContentLoaded', () => {
  console.log('🏛️ Initializing NexusPro Modular Quant Architecture...');

  // Pre-seed URL parameters BEFORE mounting components to avoid triple kline fetches
  const urlParams = new URLSearchParams(window.location.search);
  const initialView = urlParams.get('view') || 'dashboard';
  const initialSym = urlParams.get('symbol');
  const initialTf = urlParams.get('tf');

  if (initialSym) state.activeSymbol = initialSym.replace('.P', '').toUpperCase();
  if (initialTf) state.activeTf = initialTf.toLowerCase();

  // 1. Mount Persistent HUD & Navigation
  const hud = new HudHeader('#mount-hud');
  const nav = new Navigation('#mount-bottom-nav');

  // 2. Mount Dashboard Components
  const wallet = new WalletSummary('#mount-dashboard-wallet');
  const carousel = new TickerCarousel('#mount-dashboard-carousel');
  const dashboardPos = new PositionCard('#mount-dashboard-position');
  const embeddedWl = new Watchlist('#mount-dashboard-watchlist');

  // 3. Mount Dedicated Watchlist View
  const mainWl = new Watchlist('#mount-watchlist-view');

  // 4. Mount Dedicated Positions View
  const positionsView = new PositionCard('#mount-positions-view');

  // 5. Mount Dedicated Chart Terminal View
  const chartTerminal = new ChartTerminal('#mount-chart-view');

  // 6. Connect Real Data WebSocket Feeds
  connector.init();

  // 7. Live Server Positions Synchronization (Every 3 seconds)
  const triggerInstantResync = () => {
    state.syncPositionsFromServer();
    if (positionsView && typeof positionsView.fetchTradeHistory === 'function') {
      positionsView.fetchTradeHistory();
    }
    if (dashboardPos && typeof dashboardPos.fetchTradeHistory === 'function') {
      dashboardPos.fetchTradeHistory();
    }
  };

  // Immediate eager initial sync
  triggerInstantResync();
  setTimeout(triggerInstantResync, 120);

  // Background interval
  setInterval(triggerInstantResync, 3000);

  // Instant Lifecycle Foreground & Resume Synchronizer (Fixes Android WebView sleep/pause)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      triggerInstantResync();
    }
  });
  window.addEventListener('focus', triggerInstantResync);
  window.addEventListener('pageshow', triggerInstantResync);

  // Mobile Pull-to-refresh swipe gesture
  let touchStartY = 0;
  window.addEventListener('touchstart', (e) => {
    if (e.touches && e.touches[0]) touchStartY = e.touches[0].clientY;
  }, { passive: true });
  window.addEventListener('touchend', (e) => {
    if (e.changedTouches && e.changedTouches[0]) {
      const touchEndY = e.changedTouches[0].clientY;
      if (window.scrollY <= 10 && (touchEndY - touchStartY > 100)) {
        triggerInstantResync();
      }
    }
  }, { passive: true });

  bus.on('request:refresh_all', triggerInstantResync);

  state.setView(initialView);

  const initialReplay = urlParams.get('replay');
  if (initialReplay === '1' || initialReplay === 'true') {
    setTimeout(() => {
      chartTerminal.toggleReplayMode(true);
    }, 250);
  }

  console.log(`⚡ NexusPro System Active on view: ${initialView}`);
});
