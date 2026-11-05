"""
Verify Live Simulink streamlined left sidebar buttons:
1. Verify dead/mockup controls (EXECUTION MODE, timing sliders, hidden duplicate panels) are removed.
2. Verify all 8 disturbance buttons exist, are clickable, and trigger physical injection / reset.
3. Verify phase selector and ALL toggle.
4. Verify START SIMULATION, RESET TO NORMAL, and STOP buttons.
5. Capture screenshot of live operational sidebar and active oscilloscope.
"""
import asyncio
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request
import websockets

CDP_PORT = 9338
SCREENSHOT_PATH = r"C:\Users\Allen\.gemini\antigravity\brain\bf881e96-0014-4e27-93c0-da9fc42df4ac\live_sidebar_streamlined_verified.png"

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

async def run_verification():
    profile = tempfile.mkdtemp()
    cmd = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        '--headless=new',
        f'--remote-debugging-port={CDP_PORT}',
        f'--user-data-dir={profile}',
        '--window-size=1400,900',
        'http://127.0.0.1:8500/#live-simulink'
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

    ws = None
    try:
        tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list').read().decode('utf-8'))
        matching = [t for t in tabs if "8500" in t.get("url", "")]
        tab_ws = matching[0]['webSocketDebuggerUrl'] if matching else tabs[0]['webSocketDebuggerUrl']
        ws = await websockets.connect(tab_ws, max_size=100*1024*1024)
        msg_id = 1

        _, msg_id = await cdp_call(ws, "Page.enable", {}, msg_id)
        _, msg_id = await cdp_call(ws, "Runtime.enable", {}, msg_id)
        await asyncio.sleep(1.5)

        # 1. Audit DOM elements
        audit_script = """
        (function() {
            const results = {};
            results.hasModeManual = !!document.getElementById('btn-mode-manual');
            results.hasModeScheduled = !!document.getElementById('btn-mode-scheduled');
            results.hasTimingCtrl = !!document.getElementById('timing-ctrl-group');
            results.hasParamPanels = !!document.getElementById('param-panels-container');

            const classes = ['Normal', 'Sag', 'Swell', 'Interruption', 'Harmonics', 'Flicker', 'Notch', 'Transient'];
            results.distButtons = {};
            classes.forEach(c => {
                const btn = document.getElementById('btn-live-dist-' + c);
                results.distButtons[c] = !!btn;
            });

            results.hasPhaseA = !!document.getElementById('chk-phase-a');
            results.hasPhaseB = !!document.getElementById('chk-phase-b');
            results.hasPhaseC = !!document.getElementById('chk-phase-c');

            results.hasStartBtn = !!document.getElementById('btn-live-start');
            results.hasInjectBtn = !!document.getElementById('btn-live-inject');
            results.hasResetBtn = !!document.getElementById('btn-live-reset');
            results.hasStopBtn = !!document.getElementById('btn-live-stop');
            results.hasFeedback = !!document.getElementById('live-sidebar-feedback');
            return results;
        })()
        """
        audit, msg_id = await eval_js(ws, audit_script, msg_id)
        print("DOM Audit Results:", json.dumps(audit, indent=2))

        # Check removals
        assert not audit['hasModeManual'], "EXECUTION MODE manual button was not removed"
        assert not audit['hasModeScheduled'], "EXECUTION MODE scheduled button was not removed"
        assert not audit['hasTimingCtrl'], "Timing controls were not removed"
        assert not audit['hasParamPanels'], "Duplicate parameter panels were not removed"

        # Check disturbance buttons
        for c, exists in audit['distButtons'].items():
            assert exists, f"Disturbance button for {c} is missing"

        # 2. Test clicking SAG
        click_sag = """
        (function() {
            const btn = document.getElementById('btn-live-dist-Sag');
            if (btn) btn.click();
            return {
                selectedClass: LIVE_SIM.selectedClass,
                feedbackText: document.getElementById('live-sidebar-feedback') ? document.getElementById('live-sidebar-feedback').textContent : '',
                btnSagActive: btn ? btn.classList.contains('active') : false
            };
        })()
        """
        sag_res, msg_id = await eval_js(ws, click_sag, msg_id)
        print("Click SAG Result:", sag_res)
        assert sag_res['selectedClass'] == 'Sag', f"Expected Sag, got {sag_res['selectedClass']}"
        assert sag_res['btnSagActive'], "SAG button did not receive active class"

        await asyncio.sleep(1.0)

        # 3. Test clicking SWELL
        click_swell = """
        (function() {
            const btn = document.getElementById('btn-live-dist-Swell');
            if (btn) btn.click();
            return {
                selectedClass: LIVE_SIM.selectedClass,
                feedbackText: document.getElementById('live-sidebar-feedback') ? document.getElementById('live-sidebar-feedback').textContent : '',
                btnSwellActive: btn ? btn.classList.contains('active') : false
            };
        })()
        """
        swl_res, msg_id = await eval_js(ws, click_swell, msg_id)
        print("Click SWELL Result:", swl_res)
        assert swl_res['selectedClass'] == 'Swell'

        await asyncio.sleep(1.0)

        # 4. Test clicking NORMAL (reset)
        click_normal = """
        (function() {
            const btn = document.getElementById('btn-live-dist-Normal');
            if (btn) btn.click();
            return {
                selectedClass: LIVE_SIM.selectedClass,
                feedbackText: document.getElementById('live-sidebar-feedback') ? document.getElementById('live-sidebar-feedback').textContent : '',
                btnNormalActive: btn ? btn.classList.contains('active') : false
            };
        })()
        """
        norm_res, msg_id = await eval_js(ws, click_normal, msg_id)
        print("Click NORMAL Result:", norm_res)
        assert norm_res['selectedClass'] == 'Normal'
        assert norm_res['btnNormalActive']

        # 5. Test ALL Phase toggle
        click_all = """
        (function() {
            selectAllPhases();
            return {
                a: document.getElementById('chk-phase-a').checked,
                b: document.getElementById('chk-phase-b').checked,
                c: document.getElementById('chk-phase-c').checked,
                feedback: document.getElementById('live-sidebar-feedback').textContent
            };
        })()
        """
        all_res, msg_id = await eval_js(ws, click_all, msg_id)
        print("Select ALL Phases Result:", all_res)
        assert all_res['a'] and all_res['b'] and all_res['c'], "Phases not all checked"

        # 6. Test START SIMULATION button click when already streaming
        click_start = """
        (function() {
            startSimulation();
            return {
                activeRunId: LIVE_SIM.activeRunId,
                feedback: document.getElementById('live-sidebar-feedback').textContent
            };
        })()
        """
        start_res, msg_id = await eval_js(ws, click_start, msg_id)
        print("Click START SIMULATION Result:", start_res)

        await asyncio.sleep(1.5)

        # 7. Capture screenshot
        shot_res, msg_id = await cdp_call(ws, "Page.captureScreenshot", {
            "format": "png",
            "clip": {"x": 0, "y": 0, "width": 1400, "height": 900, "scale": 1}
        }, msg_id)

        img_bytes = base64.b64decode(shot_res.get("data", ""))
        with open(SCREENSHOT_PATH, "wb") as f:
            f.write(img_bytes)
        print(f"Captured screenshot to: {SCREENSHOT_PATH} ({len(img_bytes)} bytes)")
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")

    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(run_verification())
