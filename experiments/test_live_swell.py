import urllib.request
import json
import time

res = json.loads(urllib.request.urlopen("http://localhost:8500/api/live/simulation/status").read().decode())
run_id = res['run_id']
print(f"Active run_id: {run_id}")

# Inject Swell with 4.0s duration
data = {
    "run_id": run_id,
    "disturbance": "Swell",
    "phases": ["A", "B", "C"],
    "duration_s": 4.0
}
req = urllib.request.Request("http://localhost:8500/api/live/simulation/inject", json.dumps(data).encode(), {"Content-Type": "application/json"})
inj_res = json.loads(urllib.request.urlopen(req).read().decode())
print("Inject Swell:", inj_res)

for i in range(5):
    time.sleep(0.5)
    st = json.loads(urllib.request.urlopen("http://localhost:8500/api/live/simulation/status").read().decode())
    met = st.get('metrics', {}) or {}
    pred = st.get('prediction', {}) or {}
    print(f"t=+{(i+1)*0.5:.1f}s | state={st.get('active_physical_state')} | V_ieee_pu={met.get('v_ieee_pu')} | ML_pred={pred.get('predicted_class')}")

# Reset
req_reset = urllib.request.Request("http://localhost:8500/api/live/simulation/reset", json.dumps({"run_id": run_id}).encode(), {"Content-Type": "application/json"})
urllib.request.urlopen(req_reset)
print("Reset sent.")
