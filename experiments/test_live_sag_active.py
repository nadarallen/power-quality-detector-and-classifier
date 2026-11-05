import urllib.request
import json
import time

# 1. Check current status
res = json.loads(urllib.request.urlopen("http://localhost:8500/api/live/simulation/status").read().decode())
run_id = res['run_id']
print(f"Active run_id: {run_id}, status: {res['status']}")

# 2. Inject Sag with 10.0s duration
data = {
    "run_id": run_id,
    "disturbance": "Sag",
    "phases": ["A", "B", "C"],
    "duration_s": 10.0
}
req = urllib.request.Request("http://localhost:8500/api/live/simulation/inject", json.dumps(data).encode(), {"Content-Type": "application/json"})
inj_res = json.loads(urllib.request.urlopen(req).read().decode())
print("Inject Response:", inj_res)

# 3. Sample every 0.5s for 4 seconds
print("\n--- MONITORING 4 SECONDS OF INJECTION ---")
for i in range(8):
    time.sleep(0.5)
    st = json.loads(urllib.request.urlopen("http://localhost:8500/api/live/simulation/status").read().decode())
    met = st.get('metrics', {}) or {}
    pred = st.get('prediction', {}) or {}
    print(f"t=+{(i+1)*0.5:.1f}s | active_state={st.get('active_physical_state')} | V_rms={met.get('rms_voltage')} | V_ieee_pu={met.get('v_ieee_pu')} | ML_pred={pred.get('predicted_class')} ({pred.get('confidence')})")

# 4. Reset to normal
req_reset = urllib.request.Request("http://localhost:8500/api/live/simulation/reset", json.dumps({"run_id": run_id}).encode(), {"Content-Type": "application/json"})
reset_res = json.loads(urllib.request.urlopen(req_reset).read().decode())
print("\nReset Response:", reset_res)
time.sleep(1.0)
st_post = json.loads(urllib.request.urlopen("http://localhost:8500/api/live/simulation/status").read().decode())
met_post = st_post.get('metrics', {}) or {}
print(f"Post-Reset | active_state={st_post.get('active_physical_state')} | V_rms={met_post.get('rms_voltage')} | V_ieee_pu={met_post.get('v_ieee_pu')}")
