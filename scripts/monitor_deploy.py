import urllib.request
import json
import time

SERVICE_ID = "srv-db8s4uff3r2c73f7lgb0"
API_KEY = "rnd_IZZkLTzrsSOolykJGGflmGovOuZN"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def monitor():
    for i in range(30):
        try:
            req = urllib.request.Request(f"https://api.render.com/v1/services/{SERVICE_ID}/deploys?limit=2", headers=HEADERS)
            data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
            latest = data[0]['deploy']
            status = latest.get('status')
            commit = latest.get('commit', {}).get('id', '')[:7]
            print(f"[{i+1}] Latest Deploy {latest['id']} ({commit}) -> {status}")
            if status == "live":
                print("[SUCCESS] Commit is LIVE on Render!")
                return True
            elif status in ["build_failed", "update_failed", "canceled"]:
                print(f"[FAIL] Deploy {status}")
                return False
        except Exception as e:
            print(f"Error checking: {e}")
        time.sleep(10)
    return False

if __name__ == "__main__":
    monitor()
