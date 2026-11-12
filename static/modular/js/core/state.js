/**
 * HERMES AI • CENTRAL STATE STORE (SINGLE SOURCE OF TRUTH)
 * Ponytail Standard: All components read and subscribe from here.
 * Editing any component never affects the data integrity.
 */

import { bus } from './event_bus.js';

class StateStore {
  constructor() {
    this.activeView = 'dashboard'; // 'dashboard' | 'watchlist' | 'chart' | 'positions'
    this.activeSymbol = 'BTCUSDT';
    this.activeTf = '1h';
    this.chartOrientation = 'portrait'; // 'portrait' | 'landscape'

    // Clean Capital & Account State (Restored from Persistent Cache: Zero $500.00 Flash!)
    this.account = this.loadAccount();

    // Clean Positions: Load persistent positions or default to empty (Zero Ghost Trades!)
    this.positions = this.loadPositions();

    // The Official 22 Champion Coins + Custom Additions
    this.watchlist = this.loadWatchlist();

    // Live Prices Map
    this.prices = new Map();
    this.watchlist.forEach(item => {
      this.prices.set(item.symbol, {
        price: item.price,
        changeAbs: item.changeAbs,
        changePct: item.changePct
      });
    });

    // Bar Replay State
    this.replay = {
      active: false,
      playing: false,
      currentIndex: 0,
      totalBars: 0,
      speed: 800,
      timerId: null
    };
  }

  // Persistent Account Cache (Guarantees instant true balance on cold/warm start)
  loadAccount() {
    try {
      const saved = localStorage.getItem('nexuspro_modular_account');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && typeof parsed.baseCapital === 'number' && parsed.baseCapital > 0) {
          return parsed;
        }
      }
    } catch (e) {}
    return {
      baseCapital: 1000.00,
      equity: 1000.00,
      unrealizedPnl: 0.00,
      pnlPct: 0.00,
      totalPnl: 0.00,
      totalPnlPct: 0.00,
      usedMargin: 0.00,
      freeMargin: 1000.00,
      marginRatio: 0.00,
      winRate: 0.0,
      sentries: {
        btcMacro: { status: 'safe', label: 'BTC Macro Safe', value: 'Stable' },
        instFloor: { status: 'safe', label: 'Floor Clean', value: 'Active' },
        idmSweep: { status: 'safe', label: 'IDM Swept', value: 'Active' },
        freshGuard: { status: 'safe', label: 'First Tap', value: '100% Fresh' }
      }
    };
  }

  saveAccount() {
    try {
      localStorage.setItem('nexuspro_modular_account', JSON.stringify(this.account));
    } catch (e) {}
  }

  // Persistent Positions Storage (Eliminates Ghost Trades)
  loadPositions() {
    try {
      const saved = localStorage.getItem('nexuspro_active_positions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) {}
    return []; // Default: Zero open positions
  }

  savePositions() {
    try {
      localStorage.setItem('nexuspro_active_positions', JSON.stringify(this.positions));
    } catch (e) {}
  }

  // Live Server Positions & Account Balance Synchronization (Auto-sync with Hermes SMC Engine)
  async syncPositionsFromServer() {
    try {
      const fetchOpts = {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      };
      const [posRes, accRes] = await Promise.all([
        fetch('/api/paper/positions?t=' + Date.now(), fetchOpts).catch(() => null),
        fetch('/api/paper/account?t=' + Date.now(), fetchOpts).catch(() => null)
      ]);

      if (!posRes.ok) return;
      const data = await posRes.json();
      const rawPositions = data.positions || [];

      // Update base capital & total stats if account response is valid
      if (accRes && accRes.ok) {
        try {
          const accData = await accRes.json();
          const serverBal = Number(accData.current_balance || accData.balance || accData.total_current_balance);
          if (serverBal && !isNaN(serverBal) && serverBal > 0) {
            this.account.baseCapital = serverBal;
          }
          if (accData.win_rate !== undefined) {
            this.account.winRate = Number(accData.win_rate || 0);
          }
          if (accData.total_pnl !== undefined) {
            this.account.totalPnl = Number(accData.total_pnl || 0);
          }
          const comb = accData.combined_10x || accData.portfolio_10x || {};
          if (comb.total_pnl_pct !== undefined) {
            this.account.totalPnlPct = Number(comb.total_pnl_pct || 0);
          } else if (comb.initial_balance && comb.initial_balance > 0) {
            this.account.totalPnlPct = Number(((this.account.totalPnl / comb.initial_balance) * 100).toFixed(2));
          }
          this.saveAccount();
        } catch (e) {
          console.warn('Account parse error:', e);
        }
      }

      // Map backend positions to StateStore format
      this.positions = rawPositions.map(p => {
        const sideUpper = String(p.side || '').toUpperCase();
        const isLong = sideUpper === 'BUY' || sideUpper === 'LONG' || String(p.side_raw || '').toUpperCase() === 'LONG';
        const entryPrice = Number(p.entry_price || 0);
        const markPrice = Number(p.mark_price || p.current_price || entryPrice);
        const sizeUsd = Number(p.size_usdt || p.position_size_usdt || 250);
        const leverage = parseInt(p.leverage) || 5;
        const marginUsdt = Number(p.margin_usdt || (sizeUsd / leverage));
        const pnlUsdt = Number(p.unrealized_pnl || 0);
        const pnlPct = Number(p.roi_pct !== undefined ? p.roi_pct : (p.pnl_pct || 0));

        // Format entry timestamp
        const entryTimeMs = p.entry_time ? Number(p.entry_time) : Date.now();
        const d = new Date(entryTimeMs);
        const hours = d.getHours();
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const formattedHours = String(hours % 12 || 12).padStart(2, '0');
        const entryTimeStr = `${formattedHours}:${minutes}:${seconds} ${ampm}`;

        const coinName = p.coin_name || p.symbol.replace('USDT', '');
        const coinQty = p.size_coin ? `${p.size_coin} ${coinName}` : `${(sizeUsd / (entryPrice || 1)).toFixed(1)} ${coinName}`;

        // Institutional High-Watermark Ratchet: Never let MFE or MAE slip/reset on server poll
        const prevPos = (this.positions || []).find(oldP => oldP.id === p.id);
        const prevMfe = prevPos ? Number(prevPos.mfe || 0) : 0;
        const prevMae = prevPos ? Number(prevPos.mae || 0) : 0;
        const serverMfe = Number(p.mfe_pct !== undefined ? p.mfe_pct : (p.mfe || 0));
        const serverMae = Number(p.mae_pct !== undefined ? p.mae_pct : (p.mae || 0));

        const lockedMfe = Math.max(prevMfe, serverMfe, pnlPct > 0 ? pnlPct : 0);
        const lockedMae = Math.max(prevMae, serverMae, pnlPct < 0 ? Math.abs(pnlPct) : 0);

        return {
          id: p.id,
          symbol: p.symbol,
          displaySymbol: p.symbol,
          coinName: coinName,
          coinQty: coinQty,
          side: isLong ? 'LONG' : 'SHORT',
          leverage: leverage,
          timeframe: (p.timeframe || '15M').toUpperCase(),
          sizeUsd: sizeUsd,
          marginUsdt: marginUsdt,
          entryPrice: entryPrice,
          markPrice: markPrice,
          liquidationPrice: Number(p.liq_price || 0),
          tpPrice: Number(p.tp_price || (isLong ? entryPrice * 1.03 : entryPrice * 0.97)),
          tp1Price: Number(p.tp_price || p.tp2_price || (isLong ? entryPrice * 1.03 : entryPrice * 0.97)),
          tp2Price: Number(p.tp_price || p.tp2_price || (isLong ? entryPrice * 1.03 : entryPrice * 0.97)),
          slPrice: Number(p.sl_price || 0),
          hardSlPrice: Number(p.hard_sl_price || (isLong ? entryPrice * 0.97 : entryPrice * 1.03)),
          entryTime: entryTimeMs,
          entryTimeStr: entryTimeStr,
          unrealizedPnl: pnlUsdt,
          pnlPct: pnlPct,
          mae: Number(lockedMae.toFixed(2)),
          mfe: Number(lockedMfe.toFixed(2)),
          duration: p.duration || p.duration_str || 'Live',
          armor: {
            beShield: Boolean(p.be_locked || (p.trailing_step && p.trailing_step >= 1)),
            trailing: Boolean(p.trailing_step && p.trailing_step >= 2),
            takeProfit: Boolean(p.partial_booked || (p.trailing_step && p.trailing_step >= 1))
          }
        };
      });

      // Update account metrics
      const totalUnPnl = this.positions.reduce((acc, pos) => acc + pos.unrealizedPnl, 0);
      const totalMargin = this.positions.reduce((acc, pos) => acc + pos.marginUsdt, 0);
      this.account.unrealizedPnl = totalUnPnl;
      this.account.usedMargin = totalMargin;
      this.account.freeMargin = Math.max(0, this.account.baseCapital - totalMargin);
      this.account.equity = this.account.baseCapital + totalUnPnl;
      this.account.pnlPct = this.account.baseCapital > 0 ? (totalUnPnl / this.account.baseCapital) * 100 : 0;

      this.savePositions();
      this.saveAccount();
      bus.emit('position:updated');
      bus.emit('account:updated', this.account);
    } catch (e) {
      console.warn('Error syncing positions:', e);
    }
  }

  // Load Watchlist (Default: 22 Champion Coins)
  loadWatchlist() {
    const default22 = [
      { symbol: 'BTCUSDT', name: 'BTCUSD', subName: 'Bitcoin / U.S. Dollar', icon: '₿', iconBg: '#f7931a', price: 77500.0, changeAbs: 890.0, changePct: 1.15, hasRedFlag: false, precision: 1 },
      { symbol: 'PAXGUSDT', name: 'PAXGUSDT', subName: 'Gold Tokenized / TetherUS', icon: '🥇', iconBg: '#d97706', price: 2920.0, changeAbs: 18.0, changePct: 0.62, hasRedFlag: false, precision: 2 },
      { symbol: 'ETHUSDT', name: 'ETHUSDT', subName: 'Ethereum / TetherUS', icon: 'Ξ', iconBg: '#627eea', price: 2310.0, changeAbs: 42.0, changePct: 1.85, hasRedFlag: false, precision: 2 },
      { symbol: 'ARBUSDT', name: 'ARBUSDT', subName: 'Arbitrum / TetherUS', icon: '◈', iconBg: '#2563eb', price: 0.42, changeAbs: 0.01, changePct: 2.10, hasRedFlag: false, precision: 4 },
      { symbol: 'SOLUSDT', name: 'SOLUSDT', subName: 'Solana / TetherUS', icon: '◎', iconBg: '#14f195', price: 142.50, changeAbs: 3.20, changePct: 2.30, hasRedFlag: false, precision: 2 },
      { symbol: 'BNBUSDT', name: 'BNBUSDT', subName: 'BNB / TetherUS', icon: '🔶', iconBg: '#f3ba2f', price: 585.0, changeAbs: 5.50, changePct: 0.95, hasRedFlag: false, precision: 2 },
      { symbol: 'DOGEUSDT', name: 'DOGEUSDT', subName: 'Dogecoin / TetherUS', icon: 'Ð', iconBg: '#c2a633', price: 0.1625, changeAbs: 0.0042, changePct: 2.65, hasRedFlag: false, precision: 4 },
      { symbol: 'AVAXUSDT', name: 'AVAXUSDT', subName: 'Avalanche / TetherUS', icon: '▲', iconBg: '#e84142', price: 8.54, changeAbs: 0.15, changePct: 1.78, hasRedFlag: false, precision: 3 },
      { symbol: 'ATOMUSDT', name: 'ATOMUSDT.P', subName: 'Cosmos / TetherUS PERPETUAL CON...', icon: '⚛', iconBg: '#2e3148', price: 1.417, changeAbs: -0.015, changePct: -1.05, hasRedFlag: true, precision: 3 },
      { symbol: 'LQTYUSDT', name: 'LQTYUSDT.P', subName: 'LQTY / TetherUS PERPETUAL CONT...', icon: '💧', iconBg: '#2962ff', price: 0.1910, changeAbs: 0.0024, changePct: 1.27, hasRedFlag: false, precision: 4 },
      { symbol: 'AXSUSDT', name: 'AXSUSDT', subName: 'Axie Infinity / TetherUS', icon: '∞', iconBg: '#0055d5', price: 0.847, changeAbs: 0.013, changePct: 1.56, hasRedFlag: false, precision: 3 },
      { symbol: 'DYDXUSDT', name: 'DYDXUSDT.P', subName: 'DYDX / TetherUS PERPETUAL CONT...', icon: '✕', iconBg: '#1f2430', price: 0.1037, changeAbs: 0.0024, changePct: 2.37, hasRedFlag: false, precision: 4 },
      { symbol: 'AAVEUSDT', name: 'AAVEUSDT.P', subName: 'AAVE / TetherUS PERPETUAL CONTRA...', icon: '👻', iconBg: '#8a649d', price: 128.50, changeAbs: 1.90, changePct: 1.50, hasRedFlag: false, precision: 2 },
      { symbol: 'FETUSDT', name: 'FETUSDT.P', subName: 'Fetch.AI / TetherUS PERPETUAL CO...', icon: ':::', iconBg: '#1b2c4e', price: 0.1557, changeAbs: 0.0003, changePct: 0.19, hasRedFlag: false, precision: 4 },
      { symbol: 'FILUSDT', name: 'FILUSDT', subName: 'Filecoin / TetherUS', icon: 'ƒ', iconBg: '#0090ff', price: 0.879, changeAbs: 0.0048, changePct: 0.55, hasRedFlag: false, precision: 4 },
      { symbol: 'INJUSDT', name: 'INJUSDT.P', subName: 'Injective / TetherUS PERPETUAL...', icon: '🌀', iconBg: '#00f2fe', price: 7.306, changeAbs: 0.325, changePct: 4.66, hasRedFlag: false, precision: 3 },
      { symbol: 'SUIUSDT', name: 'SUIUSDT', subName: 'Sui / TetherUS', icon: '💧', iconBg: '#4da2ff', price: 1.825, changeAbs: 0.052, changePct: 2.93, hasRedFlag: false, precision: 3 },
      { symbol: 'NEARUSDT', name: 'NEARUSDT', subName: 'Near Protocol / TetherUS', icon: 'Ⓝ', iconBg: '#000000', price: 3.42, changeAbs: 0.08, changePct: 2.40, hasRedFlag: false, precision: 3 },
      { symbol: 'APTUSDT', name: 'APTUSDT', subName: 'Aptos / TetherUS', icon: '⍋', iconBg: '#212529', price: 7.15, changeAbs: 0.12, changePct: 1.71, hasRedFlag: false, precision: 3 },
      { symbol: 'UNIUSDT', name: 'UNIUSDT', subName: 'Uniswap / TetherUS', icon: '🦄', iconBg: '#ff007a', price: 7.18, changeAbs: 0.22, changePct: 3.16, hasRedFlag: false, precision: 3 },
      { symbol: 'RENDERUSDT', name: 'RENDERUSDT', subName: 'Render / TetherUS', icon: '⟁', iconBg: '#e53e3e', price: 4.65, changeAbs: 0.14, changePct: 3.10, hasRedFlag: false, precision: 3 },
      { symbol: 'OPUSDT', name: 'OPUSDT', subName: 'Optimism / TetherUS', icon: '🔴', iconBg: '#ff0420', price: 1.18, changeAbs: -0.02, changePct: -1.67, hasRedFlag: false, precision: 3 },
      { symbol: 'TIAUSDT', name: 'TIAUSDT', subName: 'Celestia / TetherUS', icon: '⊛', iconBg: '#7b2cbf', price: 4.12, changeAbs: 0.06, changePct: 1.48, hasRedFlag: false, precision: 3 },
      { symbol: 'SEIUSDT', name: 'SEIUSDT', subName: 'Sei Network / TetherUS', icon: '⛵', iconBg: '#9013fe', price: 0.285, changeAbs: 0.008, changePct: 2.88, hasRedFlag: false, precision: 4 }
    ];

    try {
      const saved = localStorage.getItem('nexuspro_custom_watchlist');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          // Merge defaults ensuring all 22 champions exist
          const map = new Map();
          parsed.forEach(c => map.set(c.symbol, c));
          default22.forEach(c => {
            if (!map.has(c.symbol)) map.set(c.symbol, c);
          });
          return Array.from(map.values());
        }
      }
    } catch (e) {}

    return default22;
  }

  saveWatchlist() {
    try {
      localStorage.setItem('nexuspro_custom_watchlist', JSON.stringify(this.watchlist));
    } catch (e) {}
  }

  // Dynamic Add Coin from Search
  addWatchlistCoin(symbolInput) {
    if (!symbolInput) return false;
    let clean = symbolInput.toUpperCase().replace('.P', '').trim();
    if (!clean) return false;
    if (!clean.endsWith('USDT')) clean = `${clean}USDT`;

    const existing = this.watchlist.find(w => w.symbol === clean);
    if (existing) {
      this.selectSymbol(clean);
      this.setView('chart');
      return true;
    }

    const shortName = clean.replace('USDT', '');
    const newCoin = {
      symbol: clean,
      name: `${shortName}USDT`,
      subName: `${shortName} / TetherUS PERPETUAL`,
      icon: shortName.slice(0, 3),
      iconBg: '#1e293b',
      price: 1.0,
      changeAbs: 0.0,
      changePct: 0.0,
      hasRedFlag: false,
      precision: 2
    };

    this.watchlist.unshift(newCoin);
    this.prices.set(clean, { price: 1.0, changeAbs: 0.0, changePct: 0.0 });
    this.saveWatchlist();

    bus.emit('watchlist:updated', this.watchlist);
    bus.emit('watchlist:coin_added', clean);

    this.selectSymbol(clean);
    this.setView('chart');
    return true;
  }

  // Set Active View
  setView(viewName) {
    if (['dashboard', 'watchlist', 'chart', 'positions', 'assets'].includes(viewName)) {
      this.activeView = viewName;
      if (viewName === 'positions' || viewName === 'dashboard' || viewName === 'assets') {
        this.syncPositionsFromServer();
      }
      bus.emit('view:changed', viewName);
    }
  }

  // Select Coin for Chart
  selectSymbol(symbol) {
    const cleanSym = symbol.replace('.P', '').toUpperCase();
    this.activeSymbol = cleanSym;
    bus.emit('symbol:changed', cleanSym);
  }

  // Set Timeframe
  setTimeframe(tf) {
    this.activeTf = tf;
    bus.emit('tf:changed', tf);
  }

  // Toggle Portrait / Landscape
  toggleOrientation() {
    this.chartOrientation = this.chartOrientation === 'portrait' ? 'landscape' : 'portrait';
    bus.emit('orientation:changed', this.chartOrientation);
  }

  // Update Live Ticker
  updatePrice(symbol, price, changeAbs, changePct) {
    const cleanSym = symbol.replace('.P', '').toUpperCase();
    const prev = this.prices.get(cleanSym);
    const direction = prev ? (price >= prev.price ? 'up' : 'down') : 'up';

    const updated = {
      price,
      changeAbs: changeAbs !== undefined ? changeAbs : (prev ? price - prev.price : 0),
      changePct: changePct !== undefined ? changePct : (prev ? ((price - prev.price) / prev.price) * 100 : 0),
      direction
    };
    this.prices.set(cleanSym, updated);

    // Also update in watchlist if exists
    const wlItem = this.watchlist.find(w => w.symbol === cleanSym);
    if (wlItem) {
      wlItem.price = price;
      if (changeAbs !== undefined) wlItem.changeAbs = changeAbs;
      if (changePct !== undefined) wlItem.changePct = changePct;
    }

    // Check if open position matches this symbol and update PnL
    const openPos = this.positions.find(p => p.symbol === cleanSym);
    if (openPos) {
      openPos.markPrice = price;
      const rawDiff = openPos.side === 'LONG' ? (price - openPos.entryPrice) : (openPos.entryPrice - price);
      const priceChangePct = openPos.entryPrice > 0 ? (rawDiff / openPos.entryPrice) : 0;
      openPos.pnlPct = priceChangePct * openPos.leverage * 100;
      // Precision PnL on Isolated Margin ($50 margin -> 5% ROI = $2.50, zero 5x double jitter)
      openPos.unrealizedPnl = (openPos.marginUsdt * openPos.pnlPct) / 100;

      // Monotonic Ratchet Lock on live price ticks
      if (openPos.pnlPct > 0) {
        openPos.mfe = Math.max(Number(openPos.mfe || 0), Number(openPos.pnlPct.toFixed(2)));
      } else if (openPos.pnlPct < 0) {
        openPos.mae = Math.max(Number(openPos.mae || 0), Math.abs(Number(openPos.pnlPct.toFixed(2))));
      }

      bus.emit('position:updated', openPos);
    }

    bus.emit('price:updated', { symbol: cleanSym, data: updated });
  }

  // Close Position Permanently
  closePosition(id) {
    const idx = this.positions.findIndex(p => p.id === id);
    if (idx !== -1) {
      const closed = this.positions.splice(idx, 1)[0];
      this.savePositions();

      // Recalculate remaining positions accurately instead of zeroing!
      const totalUnPnl = this.positions.reduce((acc, pos) => acc + (pos.unrealizedPnl || 0), 0);
      const totalMargin = this.positions.reduce((acc, pos) => acc + (pos.marginUsdt || 0), 0);
      this.account.unrealizedPnl = totalUnPnl;
      this.account.usedMargin = totalMargin;
      this.account.freeMargin = Math.max(0, this.account.baseCapital - totalMargin);
      this.account.equity = this.account.baseCapital + totalUnPnl;
      this.account.pnlPct = this.account.baseCapital > 0 ? (totalUnPnl / this.account.baseCapital) * 100 : 0;

      bus.emit('position:closed', closed);
      bus.emit('account:updated', this.account);

      // Immediately sync with server to credit realized PnL to baseCapital
      setTimeout(() => this.syncPositionsFromServer(), 300);
    }
  }

  // Fast Breakeven Move
  moveToBe(id) {
    const pos = this.positions.find(p => p.id === id);
    if (pos) {
      pos.armor.beShield = true;
      this.savePositions();
      bus.emit('position:updated', pos);
    }
  }
}

export const state = new StateStore();
