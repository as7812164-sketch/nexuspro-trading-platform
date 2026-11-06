import urllib.request
import json
import time

api_key = "rnd_IZZkLTzrsSOolykJGGflmGovOuZN"
srv_id = "srv-db8s4uff3r2c73f7lgb0"

for attempt in range(25):
    try:
        url = f"https://api.render.com/v1/services/{srv_id}/deploys?limit=2"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        if data:
            latest = data[0].get("deploy", {})
            status = latest.get("status")
            commit_id = latest.get("commit", {}).get("id", "")[:7]
            print(f"[{attempt+1}] Deploy {latest.get('id')} ({commit_id}): {status}")
            if status == "live":
                print("[SUCCESS] Service is LIVE with latest commit!")
                break
            elif status in ["build_failed", "update_failed", "canceled"]:
                print(f"[FAILED] Deploy ended in state: {status}")
                break
    except Exception as e:
        print(f"Error checking deploy: {e}")
    time.sleep(6)
