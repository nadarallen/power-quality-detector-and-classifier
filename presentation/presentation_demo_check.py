"""
presentation/presentation_demo_check.py
---------------------------------------
Verifies active presentation and simulation health:
1. Backend HTTP responsiveness on port 8500
2. Live simulation status and TCP streamer ingestion
3. Real-time ML inference pipeline
4. Preset catalog readiness
"""

import os
import sys
import json
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def fetch_json(url: str, timeout: float = 3.0) -> tuple[bool, dict, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PQD-Presentation-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
            return True, data, "OK"
    except urllib.error.URLError as err:
        return False, {}, str(err)
    except Exception as ex:
        return False, {}, str(ex)

def run_demo_check():
    print("=" * 80)
    print("   IEEE 9-BUS LIVE PRESENTATION & DEMONSTRATION DIAGNOSTIC")
    print("=" * 80)

    base_url = "http://127.0.0.1:8500"

    # 1. Health Endpoint
    ok_h, data_h, msg_h = fetch_json(f"{base_url}/api/health")
    b_badge = "[  OK  ]" if ok_h else "[ FAIL ]"
    print(f" {b_badge} Backend Service Health       : {msg_h if not ok_h else 'Healthy (HTTP 200)'}")

    # 2. Live Simulation Status
    ok_s, data_s, msg_s = fetch_json(f"{base_url}/api/live/simulation/status")
    if ok_s:
        sim_status = data_s.get("status", "UNKNOWN")
        run_id = data_s.get("run_id", "NONE")
        t_sim = data_s.get("simulation_time", 0.0)
        chunks = data_s.get("chunks_posted", 0)
        dist = data_s.get("active_disturbance", "Normal")

        sim_badge = "[  OK  ]" if sim_status in ("STREAMING", "RUNNING") else "[ INFO ]"
        print(f" {sim_badge} Simulink Telemetry State   : Status={sim_status}, RunID={run_id}")
        print(f"        -> Time: {t_sim:.2f}s | Chunks: {chunks} | Active Disturbance: {dist}")

        # ML Prediction status
        pred = data_s.get("prediction", {})
        if pred:
            p_cls = pred.get("predicted_class", "N/A")
            p_conf = pred.get("confidence", 0.0) * 100.0
            p_dom = pred.get("model_domain_status", "N/A")
            print(f"        -> Live ML Output: {p_cls} ({p_conf:.1f}%) | Domain: {p_dom}")
    else:
        print(f" [ WARN ] Simulink Telemetry State   : Failed to query status ({msg_s})")

    # 3. Model Classes and Schema
    ok_c, data_c, msg_c = fetch_json(f"{base_url}/api/classes")
    c_badge = "[  OK  ]" if ok_c else "[ FAIL ]"
    num_classes = len(data_c.get("classes", [])) if ok_c else 0
    print(f" {c_badge} Feature & Class Schema       : {num_classes} Classes Configured")

    # 4. Presets Validation
    cfg_p = os.path.join(PROJECT_ROOT, "presentation", "presentation_config.json")
    if os.path.exists(cfg_p):
        with open(cfg_p, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        presets = cfg.get("approved_demonstration_presets", [])
        print(f" [  OK  ] Presentation Presets Catalog: {len(presets)} Verified Presets Configured")
    else:
        print(" [ WARN ] Presentation Presets Catalog: presentation_config.json missing")

    print("-" * 80)
    overall_ok = ok_h and ok_c
    print(f" DEMONSTRATION BACKEND READINESS: {'READY' if overall_ok else 'NOT READY'}")
    print("=" * 80)
    return overall_ok

if __name__ == "__main__":
    ready = run_demo_check()
    sys.exit(0 if ready else 1)
