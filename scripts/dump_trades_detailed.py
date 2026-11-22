import urllib.request
import json

url = 'https://nexuspro-terminal.onrender.com/api/trade/history?limit=15'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    trades = json.loads(resp.read().decode('utf-8')).get('trades', [])
    for t in trades[:10]:
        sym = t['symbol']
        side = t['side']
        entry = float(t['entry_price'])
        exit_p = float(t['exit_price'])
        sl = t.get('sl_price')
        dur = t.get('duration_str')
        reason = t.get('exit_reason')
        diff_pct = ((exit_p - entry) / entry) * 100.0 if side == "LONG" else ((entry - exit_p) / entry) * 100.0
        print(f"{sym} {side}: Entry={entry}, Exit={exit_p}, SL={sl}, Price Diff={diff_pct:.2f}%, Dur={dur}")
        print(f"  Reason: {reason}\n")
