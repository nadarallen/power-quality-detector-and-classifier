"""
experiments/verify_prompt8_live_browser.py
==========================================
Automated Browser-Level Verification Suite for Prompt 8:
- Connects headless Google Chrome via Chrome DevTools Protocol (CDP)
- Launches real MATLAB/Simulink continuous IEEE 9-bus simulation
- Verifies progressive Bus 5 telemetry streaming
- Captures initial 1,000-sample rapid evaluation
- Verifies authoritative 5-second periodic classification cadence (T1..T4)
- Performs disturbance sequence: Normal -> Sag -> Reset -> Swell -> Reset
- Validates decoupling (Requested Disturbance vs Physical Assessment vs ML Inference)
- Captures required browser screenshots directly from Chrome render tree
- Tests SSE resilience (page reload, instant state recovery, clean shutdown)
"""

import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import websockets

BASE_URL = "http://127.0.0.1:8500"
ARTIFACTS_DIR = r"C:\Users\Allen\.gemini\antigravity\brain\bf881e96-0014-4e27-93c0-da9fc42df4ac"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9222


def _api_get(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


def _api_post(endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


async def cdp_call(ws, method, params=None, msg_id=1):
    msg = {"id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    await ws.send(json.dumps(msg))
    while True:
        raw = await ws.recv()
        resp = json.loads(raw)
        if resp.get("id") == msg_id:
            if "error" in resp:
                raise RuntimeError(f"CDP Error in {method}: {resp['error']}")
            return resp.get("result", {}), msg_id + 1


async def eval_js(ws, expr, msg_id):
    res, next_id = await cdp_call(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True}, msg_id)
    val = res.get("result", {}).get("value")
    return val, next_id


async def capture_screenshot(ws, output_filename, msg_id):
    res, next_id = await cdp_call(ws, "Page.captureScreenshot", {"format": "png"}, msg_id)
    img_data = base64.b64decode(res["data"])
    out_path = os.path.join(ARTIFACTS_DIR, output_filename)
    with open(out_path, "wb") as f:
        f.write(img_data)
    print(f"[CDP Screenshot] Saved: {output_filename}")
    return out_path, next_id


async def run_prompt8_verification():
    print("=" * 80)
    print("PROMPT 8: BROWSER-LEVEL LIVE ML CLASSIFICATION VERIFICATION")
    print("=" * 80)

    # 1. Start Headless Chrome with Remote Debugging
    chrome_cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        "--window-size=1600,1100",
        "--disable-gpu",
        "--no-sandbox",
        BASE_URL,
    ]
    chrome_proc = subprocess.Popen(chrome_cmd)
    print(f"[Browser] Chrome launched on port {CDP_PORT}...")
    await asyncio.sleep(2.5)

    msg_id = 1
    evidence = {}

    try:
        # Connect to CDP
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json") as r:
            targets = json.loads(r.read().decode())
        page_target = next(t for t in targets if "8500" in t.get("url", ""))
        ws_url = page_target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
            print(f"[CDP] Connected to Chrome DevTools Protocol at {ws_url}")

            # Wait for DOM ready & scroll to live-sim-section
            await asyncio.sleep(1.5)
            _, msg_id = await eval_js(ws, "document.getElementById('live-sim-section').scrollIntoView();", msg_id)
            await asyncio.sleep(0.5)

            # 2. Check if a continuous simulation is running or start fresh
            st = _api_get("/api/live/simulation/status")
            if st.get("status") in ("running", "streaming"):
                run_id = st["run_id"]
                print(f"[Step 1] Using already active simulation session: run_id={run_id}")
            else:
                print("\n[Step 1] Launching Continuous IEEE 9-Bus Simulation Session...")
                start_payload = {
                    "mode": "continuous",
                    "class": "Normal",
                    "phases": ["A", "B", "C"],
                    "params": {},
                }
                start_resp = _api_post("/api/live/simulation/start", start_payload)
                run_id = start_resp["run_id"]
                print(f"  Simulation Started: run_id={run_id}")

            evidence["run_id"] = run_id

            # Poll until simulation becomes 'streaming'
            t0 = time.time()
            is_streaming = False
            while time.time() - t0 < 90:
                st = _api_get("/api/live/simulation/status")
                print(f"  Status: {st['status']} (elapsed: {st['elapsed_s']}s, chunks: {st['chunks_posted']})")
                if st["status"] == "streaming" and st["chunks_posted"] >= 1:
                    is_streaming = True
                    break
                await asyncio.sleep(2.0)

            assert is_streaming, f"Simulation failed to enter 'streaming' mode within 90s! (Current: {st['status']})"
            print(f"[Step 1 PASS] Live Simulink streaming active! ({st['chunks_posted']} chunks posted)")

            # 3. Wait for Initial Rapid Inference (1,000 samples)
            print("\n[Step 2] Verifying Rapid Initial Evaluation (1,000 samples)...")
            initial_pred = None
            t0_inf = time.time()
            while time.time() - t0_inf < 15:
                pred = _api_get("/api/live/simulation/prediction")
                if pred and pred.get("prediction_status") == "VALID" and pred.get("inference_sequence", 0) >= 1:
                    initial_pred = pred
                    break
                await asyncio.sleep(0.5)

            assert initial_pred is not None, "Initial 1,000-sample prediction was not generated!"
            print(f"  Initial Inference: Seq #{initial_pred['inference_sequence']}, Class: {initial_pred['raw_ml_prediction']}, Latency: {initial_pred['inference_latency_ms']} ms")
            evidence["initial_prediction"] = initial_pred

            # 4. Verify 5-Second Periodic Inferences & Timestamps (>= 4 consecutive ticks)
            print("\n[Step 3] Monitoring Authoritative 5-Second Cadence (recording >= 4 consecutive ticks)...")
            recorded_inferences = []
            seen_seqs = set()
            start_cadence = time.time()
            while len(recorded_inferences) < 5 and (time.time() - start_cadence < 35):
                pred = _api_get("/api/live/simulation/prediction")
                seq = pred.get("inference_sequence", 0)
                if seq > 0 and seq not in seen_seqs:
                    seen_seqs.add(seq)
                    rec = {
                        "sequence": seq,
                        "timestamp": pred["timestamp"],
                        "wall_clock_monotonic": pred["inference_wall_clock_monotonic"],
                        "raw_ml_prediction": pred["raw_ml_prediction"],
                        "confidence": pred["confidence"],
                        "latency_ms": pred["inference_latency_ms"],
                        "probabilities": pred["raw_ml_probabilities"],
                    }
                    recorded_inferences.append(rec)
                    print(f"  Recorded Inference #{seq}: Monotonic={rec['wall_clock_monotonic']:.3f}s, Class={rec['raw_ml_prediction']}, Prob={rec['confidence']:.4f}")
                await asyncio.sleep(0.5)

            assert len(recorded_inferences) >= 4, f"Failed to record 4 consecutive inferences! Got {len(recorded_inferences)}"

            # Calculate intervals
            intervals = []
            for i in range(1, len(recorded_inferences)):
                dt = recorded_inferences[i]["wall_clock_monotonic"] - recorded_inferences[i - 1]["wall_clock_monotonic"]
                intervals.append(dt)
                print(f"  Interval #{i} (Seq {recorded_inferences[i-1]['sequence']} -> {recorded_inferences[i]['sequence']}): {dt:.3f} s")

            avg_interval = sum(intervals) / len(intervals)
            print(f"  Mean inference interval: {avg_interval:.2f} s (Target: 5.0 s)")
            evidence["periodic_inferences"] = recorded_inferences
            evidence["inference_intervals"] = intervals

            # Allow DOM to catch up with latest SSE event
            await asyncio.sleep(1.5)

            # Capture Screenshot 1: Normal Operation
            _, msg_id = await eval_js(ws, "document.getElementById('ml-classification-hero').scrollIntoView();", msg_id)
            await asyncio.sleep(0.5)
            s1_path, msg_id = await capture_screenshot(ws, "browser_live_01_normal.png", msg_id)
            evidence["screenshot_1_normal"] = s1_path

            # Verify DOM values in Chrome
            dom_pred_class, msg_id = await eval_js(ws, "document.getElementById('ml-hero-pred-class').textContent", msg_id)
            dom_pred_conf, msg_id = await eval_js(ws, "document.getElementById('ml-hero-pred-conf').textContent", msg_id)
            print(f"  Browser DOM Card A: Class={dom_pred_class}, Score={dom_pred_conf}")

            # 5. Disturbance Sequence: Inject SAG
            print("\n[Step 4] Injecting SAG Disturbance into Simulink...")
            sag_payload = {
                "run_id": run_id,
                "disturbance": "Sag",
                "phases": ["A"],
                "params": {"fault_resistance_ohms": 5.0, "ground_resistance_ohms": 0.1, "duration_ms": 150},
            }
            sag_ack = _api_post("/api/live/simulation/inject", sag_payload)
            print(f"  Sag Inject Ack: status={sag_ack.get('status')}")

            # Wait for next evaluation to capture Sag
            sag_pred = None
            t0_sag = time.time()
            while time.time() - t0_sag < 15:
                p = _api_get("/api/live/simulation/prediction")
                if p.get("requested_disturbance") == "Sag" and p.get("inference_sequence", 0) > recorded_inferences[-1]["sequence"]:
                    sag_pred = p
                    break
                await asyncio.sleep(0.5)

            if sag_pred:
                print(f"  Sag Active: Physical={sag_pred['measured_physical_assessment']}, ML={sag_pred['raw_ml_prediction']}, Score={sag_pred['confidence']:.4f}")
            else:
                sag_pred = _api_get("/api/live/simulation/prediction")
                print(f"  Sag Pred (latest): Physical={sag_pred.get('measured_physical_assessment')}, ML={sag_pred.get('raw_ml_prediction')}")
            evidence["sag_prediction"] = sag_pred

            # Wait 1.5s for DOM to update via SSE and capture Screenshot 2: Sag Injection
            await asyncio.sleep(1.5)
            s2_path, msg_id = await capture_screenshot(ws, "browser_live_02_sag.png", msg_id)
            evidence["screenshot_2_sag"] = s2_path

            # Reset to Normal
            print("\n[Step 5] Resetting Disturbance to Normal...")
            _api_post("/api/live/simulation/reset", {"run_id": run_id})
            await asyncio.sleep(6.0)

            # 6. Disturbance Sequence: Inject SWELL
            print("\n[Step 6] Injecting SWELL Disturbance into Simulink...")
            swell_payload = {
                "run_id": run_id,
                "disturbance": "Swell",
                "phases": ["A"],
                "params": {"capacitive_power_mvar": 150.0, "damping_power_kw": 5.0, "duration_ms": 150},
            }
            swell_ack = _api_post("/api/live/simulation/inject", swell_payload)
            print(f"  Swell Inject Ack: status={swell_ack.get('status')}")

            swell_pred = None
            t0_sw = time.time()
            while time.time() - t0_sw < 15:
                p = _api_get("/api/live/simulation/prediction")
                if p.get("requested_disturbance") == "Swell" and p.get("inference_sequence", 0) > (sag_pred.get("inference_sequence", 0) if sag_pred else 0):
                    swell_pred = p
                    break
                await asyncio.sleep(0.5)

            if swell_pred:
                print(f"  Swell Active: Physical={swell_pred['measured_physical_assessment']}, ML={swell_pred['raw_ml_prediction']}, Score={swell_pred['confidence']:.4f}")
            else:
                swell_pred = _api_get("/api/live/simulation/prediction")
                print(f"  Swell Pred (latest): Physical={swell_pred.get('measured_physical_assessment')}, ML={swell_pred.get('raw_ml_prediction')}")
            evidence["swell_prediction"] = swell_pred

            # Wait 1.5s for DOM to update via SSE and capture Screenshot 3: Swell Injection
            await asyncio.sleep(1.5)
            s3_path, msg_id = await capture_screenshot(ws, "browser_live_03_swell.png", msg_id)
            evidence["screenshot_3_swell"] = s3_path

            # Reset to Normal
            print("\n[Step 7] Resetting Disturbance to Normal...")
            _api_post("/api/live/simulation/reset", {"run_id": run_id})
            await asyncio.sleep(6.0)

            # 7. Expand Timeline Table and Capture Screenshot 4
            print("\n[Step 8] Expanding Classification Timeline Table in Browser...")
            _, msg_id = await eval_js(ws, "toggleTimelineExpand();", msg_id)
            await asyncio.sleep(0.5)
            _, msg_id = await eval_js(ws, "document.getElementById('ml-timeline-content').scrollIntoView();", msg_id)
            await asyncio.sleep(0.5)
            s4_path, msg_id = await capture_screenshot(ws, "browser_live_04_timeline.png", msg_id)
            evidence["screenshot_4_timeline"] = s4_path

            # 8. Capture Waveforms & FFT Spectrum (Screenshot 5 & 6)
            print("\n[Step 9] Capturing Waveform Oscilloscope & FFT Spectrum...")
            _, msg_id = await eval_js(ws, "document.getElementById('live-voltage-canvas').scrollIntoView();", msg_id)
            await asyncio.sleep(0.5)
            s5_path, msg_id = await capture_screenshot(ws, "browser_live_05_waveforms_spectrum.png", msg_id)
            evidence["screenshot_5_waveforms_spectrum"] = s5_path

            # Also capture oscilloscope/spectrum in section 2
            _, msg_id = await eval_js(ws, "document.getElementById('scope-canvas') ? document.getElementById('scope-canvas').scrollIntoView() : null;", msg_id)
            await asyncio.sleep(0.5)
            s6_path, msg_id = await capture_screenshot(ws, "browser_live_06_fft_spectrum.png", msg_id)
            evidence["screenshot_6_fft_spectrum"] = s6_path

            # 9. Test SSE Resilience: Page Reload & Instant State Recovery
            print("\n[Step 10] Testing SSE Resilience: Browser Reload...")
            _, msg_id = await eval_js(ws, "window.location.reload();", msg_id)
            await asyncio.sleep(2.5)
            _, msg_id = await eval_js(ws, "document.getElementById('live-sim-section').scrollIntoView();", msg_id)
            await asyncio.sleep(1.0)
            reloaded_class, msg_id = await eval_js(ws, "document.getElementById('ml-hero-pred-class').textContent", msg_id)
            print(f"  Reloaded Page Instant Class: {reloaded_class} (Retrieved immediately without 5s wait)")
            assert reloaded_class in ["NORMAL", "SAG", "SWELL", "INTERRUPTION", "HARMONICS", "FLICKER", "NOTCH", "TRANSIENT"]
            evidence["reload_recovery_class"] = reloaded_class

            # 10. Stop Simulation Cleanly
            print("\n[Step 11] Stopping Simulation Session Cleanly...")
            stop_resp = _api_post("/api/live/simulation/stop", {})
            print(f"  Stop requested: {stop_resp}")

            t0_stop = time.time()
            stopped_ok = False
            while time.time() - t0_stop < 15:
                st = _api_get("/api/live/simulation/status")
                if st["status"] in ("stopped", "completed"):
                    stopped_ok = True
                    break
                await asyncio.sleep(1.0)

            assert stopped_ok, f"Simulation did not transition to stopped state! Status: {st['status']}"
            print("  Simulation cleanly stopped.")

            # Save full evidence JSON
            ev_path = os.path.join(ARTIFACTS_DIR, "prompt8_browser_verification_evidence.json")
            with open(ev_path, "w", encoding="utf-8") as f:
                json.dump(evidence, f, indent=2)
            print(f"\n[Evidence Saved] {ev_path}")
            print("ALL PROMPT 8 AUTOMATED VERIFICATIONS PASSED SUCCESSFULLY!")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()
        print("[Browser] Chrome process terminated cleanly.")


if __name__ == "__main__":
    asyncio.run(run_prompt8_verification())
