import urllib.request
import json
import time

SERVICE_ID = "srv-db8s4uff3r2c73f7lgb0"
API_KEY = "rnd_IZZkLTzrsSOolykJGGflmGovOuZN"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def trigger_deploy():
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys"
    req = urllib.request.Request(url, headers=HEADERS, data=json.dumps({}).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            deploy_id = data.get("id")
            print(f"[TRIGGERED] Deploy ID: {deploy_id} | Status: {data.get('status')}")
            return deploy_id
    except Exception as e:
        print(f"[ERROR TRIGGERING DEPLOY] {e}")
        return None

def wait_for_deploy(deploy_id):
    if not deploy_id:
        return
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys/{deploy_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    for _ in range(40):
        time.sleep(10)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                status = data.get("status")
                print(f"[POLL] Deploy status: {status}")
                if status == "live":
                    print("[LIVE] Deployment is live on Render!")
                    return True
                elif status in ["build_failed", "update_failed", "canceled"]:
                    print(f"[FAILED] Deployment status: {status}")
                    return False
        except Exception as e:
            print(f"[NOTE] Polling note: {e}")
    return False

if __name__ == "__main__":
    dep_id = trigger_deploy()
    wait_for_deploy(dep_id)
