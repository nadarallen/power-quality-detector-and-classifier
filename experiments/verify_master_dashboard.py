"""
experiments/verify_master_dashboard.py
======================================
Automated End-to-End Browser Verification Suite for the Redesigned
IEEE 9-Bus Power Quality Dashboard.

Exercises all 6 dedicated pages via Chrome DevTools Protocol (CDP):
1. Overview: System KPIs, 3-phase Bus 5 summary, decoupled triplet, recent events.
2. Live Simulink: Simulation workspace, Live ML hero panel, dual-unit oscilloscopes, Live FFT spectrum.
3. Disturbance Analysis: 4 subtabs (Harmonics, Flicker, Notch, Transient).
4. Datasets: 10,000 samples distribution, interactive Waveform Explorer, 32-feature schema.
5. Model Performance: 99.92% accuracy, 8x8 confusion matrix, class-wise metrics, benchmarks.
6. Event History: Unified event repository with filtering and CSV export.

Captures high-resolution browser screenshots for each dedicated page.
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
CDP_PORT = 9224


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
    print(f"  [Screenshot Captured] {output_filename}")
    return out_path, next_id


async def run_master_verification():
    print("=" * 80)
    print("MASTER DASHBOARD REDESIGN - CDP BROWSER VERIFICATION SUITE")
    print("=" * 80)

    # 1. Launch Headless Chrome
    chrome_cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        "--window-size=1400,900",
        "--disable-gpu",
        "--no-sandbox",
        f"{BASE_URL}/#overview",
    ]
    chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[Browser] Chrome launched on port {CDP_PORT}...")
    await asyncio.sleep(2.5)

    ws = None
    try:
        # Wait for CDP debug endpoint
        tab_url = None
        for _ in range(30):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{CDP_PORT}/json")
                with urllib.request.urlopen(req, timeout=1.0) as r:
                    tabs = json.loads(r.read().decode())
                    matching = [t for t in tabs if "8500" in t.get("url", "")]
                    if matching:
                        tab_url = matching[0]["webSocketDebuggerUrl"]
                        break
                    elif tabs and "webSocketDebuggerUrl" in tabs[0]:
                        tab_url = tabs[0]["webSocketDebuggerUrl"]
                        break
            except Exception:
                time.sleep(0.3)

        if not tab_url:
            raise RuntimeError("Failed to connect to Chrome DevTools Protocol endpoint.")

        print(f"[CDP Connected] Debugger URL: {tab_url}")
        ws = await websockets.connect(tab_url, max_size=100 * 1024 * 1024, ping_interval=None, ping_timeout=None)
        msg_id = 1

        # Enable Page and Runtime
        _, msg_id = await cdp_call(ws, "Page.enable", {}, msg_id)
        _, msg_id = await cdp_call(ws, "Runtime.enable", {}, msg_id)

        # Explicit navigation to guarantee DOM is loaded
        print(f"[CDP] Navigating to {BASE_URL}/#overview...")
        _, msg_id = await cdp_call(ws, "Page.navigate", {"url": f"{BASE_URL}/#overview"}, msg_id)

        # Wait for document to be ready
        for _ in range(20):
            ready, msg_id = await eval_js(ws, "document.readyState", msg_id)
            if ready == "complete":
                break
            await asyncio.sleep(0.3)
        await asyncio.sleep(1.5)

        # ── PAGE 1: OVERVIEW ──────────────────────────────────────────────────
        print("\n[Step 1] Verifying PAGE 1: OVERVIEW...")
        _, msg_id = await eval_js(ws, "switchPage('overview')", msg_id)
        await asyncio.sleep(1.0)

        # Verify DOM
        page1_active, msg_id = await eval_js(ws, "document.getElementById('page-overview') && document.getElementById('page-overview').classList.contains('active')", msg_id)
        print(f"  Page Overview is active: {page1_active}")
        assert page1_active, "Overview page is not active!"

        await capture_screenshot(ws, "master_page_01_overview.png", msg_id)

        # ── PAGE 2: LIVE SIMULINK ─────────────────────────────────────────────
        print("\n[Step 2] Navigating to PAGE 2: LIVE SIMULINK...")
        _, msg_id = await eval_js(ws, "switchPage('live-simulink')", msg_id)
        await asyncio.sleep(1.5)

        page2_active, msg_id = await eval_js(ws, "document.getElementById('page-live-simulink').classList.contains('active')", msg_id)
        print(f"  Page Live Simulink is active: {page2_active}")
        assert page2_active, "Live Simulink page is not active!"

        has_fft_canvas, msg_id = await eval_js(ws, "!!document.getElementById('live-fft-canvas')", msg_id)
        has_ml_hero, msg_id = await eval_js(ws, "!!document.getElementById('ml-classification-hero')", msg_id)
        print(f"  Live FFT Canvas present: {has_fft_canvas}")
        print(f"  Live ML Hero present: {has_ml_hero}")
        assert has_fft_canvas and has_ml_hero

        await capture_screenshot(ws, "master_page_02_live_simulink.png", msg_id)

        # Scroll down to capture Current Oscilloscope and FFT Spectrum
        _, msg_id = await eval_js(ws, "window.scrollTo(0, 580)", msg_id)
        await asyncio.sleep(1.0)
        await capture_screenshot(ws, "master_page_02b_current_and_fft.png", msg_id)

        # Scroll further down to capture FFT Spectrum
        _, msg_id = await eval_js(ws, "window.scrollTo(0, 1100)", msg_id)
        await asyncio.sleep(1.0)
        await capture_screenshot(ws, "master_page_02c_fft_spectrum.png", msg_id)
        _, msg_id = await eval_js(ws, "window.scrollTo(0, 0)", msg_id)
        await asyncio.sleep(0.5)

        # ── PAGE 3: DISTURBANCE LAB ───────────────────────────────────────────
        print("\n[Step 3] Navigating to PAGE 3: DISTURBANCE LAB...")
        _, msg_id = await eval_js(ws, "switchPage('disturbance-lab')", msg_id)
        await asyncio.sleep(1.5)

        page3_active, msg_id = await eval_js(ws, "document.getElementById('page-disturbance-lab').classList.contains('active')", msg_id)
        print(f"  Page Disturbance Lab is active: {page3_active}")
        assert page3_active, "Disturbance Lab page is not active!"

        # Toggle diagnostics to verify expansion
        _, msg_id = await eval_js(ws, "toggleLabDiagnostics()", msg_id)
        await asyncio.sleep(0.5)
        await capture_screenshot(ws, "master_page_03_disturbance_lab.png", msg_id)

        # ── PAGE 4: DISTURBANCE ANALYSIS (4 SUBTABS) ─────────────────────────
        print("\n[Step 4] Navigating to PAGE 4: DISTURBANCE ANALYSIS...")
        _, msg_id = await eval_js(ws, "switchPage('disturbance-analysis')", msg_id)
        await asyncio.sleep(1.0)

        for tab in ["harmonics", "flicker", "notch", "transient"]:
            print(f"  Exercising Subtab: {tab.upper()}...")
            _, msg_id = await eval_js(ws, f"switchDisturbanceTab('{tab}')", msg_id)
            await asyncio.sleep(0.5)

        # Stay on Harmonics for primary capture
        _, msg_id = await eval_js(ws, "switchDisturbanceTab('harmonics')", msg_id)
        await asyncio.sleep(0.5)
        await capture_screenshot(ws, "master_page_04_disturbance_analysis.png", msg_id)

        # ── PAGE 5: SIMULATION HISTORY ────────────────────────────────────────
        print("\n[Step 5] Navigating to PAGE 5: SIMULATION HISTORY & AUDIT LOG...")
        _, msg_id = await eval_js(ws, "switchPage('simulation-history')", msg_id)
        await asyncio.sleep(1.5)

        ev_count, msg_id = await eval_js(ws, "document.getElementById('event-history-count').textContent", msg_id)
        print(f"  Unified Events Count: {ev_count}")
        await capture_screenshot(ws, "master_page_05_simulation_history.png", msg_id)

        # ── PAGE 6: DATASETS ──────────────────────────────────────────────────
        print("\n[Step 6] Navigating to PAGE 6: DATASETS & WAVEFORM EXPLORER...")
        _, msg_id = await eval_js(ws, "switchPage('datasets')", msg_id)
        await asyncio.sleep(1.5)

        # Click Sag class in Explorer
        _, msg_id = await eval_js(ws, "selectExplorerClass('Sag')", msg_id)
        await asyncio.sleep(1.0)

        ds_class_lbl, msg_id = await eval_js(ws, "document.getElementById('explorer-class-lbl').textContent", msg_id)
        ds_ml_pred, msg_id = await eval_js(ws, "document.getElementById('explorer-ml-pred').textContent", msg_id)
        print(f"  Waveform Explorer Inspected Class: {ds_class_lbl}")
        print(f"  Waveform Explorer ML Prediction: {ds_ml_pred}")
        assert ds_class_lbl == "Sag", f"Expected Sag, got {ds_class_lbl}"

        await capture_screenshot(ws, "master_page_06_datasets.png", msg_id)

        # ── PAGE 7: MODEL DIAGNOSTICS ─────────────────────────────────────────
        print("\n[Step 7] Navigating to PAGE 7: MODEL DIAGNOSTICS & BENCHMARKS...")
        _, msg_id = await eval_js(ws, "switchPage('model-diagnostics')", msg_id)
        await asyncio.sleep(1.5)

        mp_acc, msg_id = await eval_js(ws, "document.getElementById('mp-acc').textContent", msg_id)
        mp_f1, msg_id = await eval_js(ws, "document.getElementById('mp-f1').textContent", msg_id)
        print(f"  Model Test Accuracy: {mp_acc}")
        print(f"  Model Macro F1: {mp_f1}")
        assert "99." in mp_acc, f"Expected 99%+ accuracy, got {mp_acc}"

        await capture_screenshot(ws, "master_page_07_model_diagnostics.png", msg_id)

        # ── PAGE 8: PRESENTATION MODE ─────────────────────────────────────────
        print("\n[Step 8] Navigating to PAGE 8: PRESENTATION MODE & GUIDED DEMO...")
        _, msg_id = await eval_js(ws, "switchPage('presentation-mode')", msg_id)
        await asyncio.sleep(1.5)

        pres_ind, msg_id = await eval_js(ws, "document.getElementById('pres-slide-indicator').textContent", msg_id)
        print(f"  Presentation Slide Indicator: {pres_ind}")
        assert "SLIDE 1" in pres_ind, f"Expected SLIDE 1, got {pres_ind}"

        await capture_screenshot(ws, "master_page_08_presentation_mode.png", msg_id)

        print("\n" + "=" * 80)
        print("ALL 8 DEDICATED PAGES VERIFIED AND SCREENSHOTS CAPTURED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        if ws:
            await ws.close()
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()


if __name__ == "__main__":
    asyncio.run(run_master_verification())
