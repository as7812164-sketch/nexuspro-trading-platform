import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

print("--- Testing Routes ---")
routes_to_test = [
    '/trade', '/nexus/trade',
    '/markets', '/nexus/markets',
    '/deca', '/nexus/deca',
    '/assets', '/nexus/assets',
    '/hologram', '/nexus/hologram',
    '/positions', '/nexus/positions'
]

for r in routes_to_test:
    res = client.get(r)
    assert res.status_code == 200, f"Route {r} failed with {res.status_code}"
    print(f"  [PASS] {r} -> 200 OK")

print("\n--- Testing APIs ---")
res = client.get('/api/ticker/BTCUSDT')
assert res.status_code == 200, f"Ticker status: {res.status_code}"
data = res.json()
print(f"  [PASS] BTC Ticker: Last Price=${data['last_price']:.2f}, 24h Change={data['price_change_pct']:.2f}%, High=${data['high_24h']:.2f}, Low=${data['low_24h']:.2f}")
assert data['last_price'] > 50000, f"BTC price {data['last_price']} too low!"

res = client.get('/api/klines/BTCUSDT?interval=15m&limit=10')
assert res.status_code == 200
klines = res.json().get('candles', [])
print(f"  [PASS] BTC Klines count: {len(klines)}")
assert len(klines) > 0, "No klines returned!"
print(f"  First candle: {klines[0]}")
print(f"  Last candle: {klines[-1]}")

res = client.get('/api/orderbook/BTCUSDT?depth=5')
assert res.status_code == 200
ob = res.json()
print(f"  [PASS] BTC Orderbook bids: {len(ob['bids'])}, asks: {len(ob['asks'])}")
print(f"  Best Ask: {ob['asks'][0]}, Best Bid: {ob['bids'][0]}")
assert ob['asks'][0][0] > 50000, f"Ask price {ob['asks'][0][0]} is not realistic!"

res = client.get('/api/markets')
assert res.status_code == 200
m_data = res.json()
print(f"  [PASS] Champions count: {len(m_data.get('champions', []))}, All markets: {len(m_data.get('all_markets', []))}")

print("\nALL SYSTEM VERIFICATIONS PASSED 100%!")
