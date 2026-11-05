import asyncio
import base64
import json
import subprocess
import tempfile
import urllib.request
import time
import websockets

CDP_PORT = 9337

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

async def test_form():
    profile = tempfile.mkdtemp()
    cmd = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        '--headless=new',
        f'--remote-debugging-port={CDP_PORT}',
        f'--user-data-dir={profile}',
        'http://127.0.0.1:8500/#overview'
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
        _, msg_id = await cdp_call(ws, "Emulation.setDeviceMetricsOverride", {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False}, msg_id)

        _, msg_id = await cdp_call(ws, "Page.navigate", {"url": "http://127.0.0.1:8500/#overview"}, msg_id)
        for _ in range(20):
            ready, msg_id = await eval_js(ws, "document.readyState", msg_id)
            if ready == "complete":
                break
            await asyncio.sleep(0.3)
        await asyncio.sleep(1.5)

        # Navigate to Disturbance Lab
        print("[Navigating to Disturbance Lab]")
        curr_url, msg_id = await eval_js(ws, "window.location.href", msg_id)
        doc_title, msg_id = await eval_js(ws, "document.title", msg_id)
        print(f"Current URL: {curr_url} | Title: {doc_title}")

        _, msg_id = await eval_js(ws, "switchPage('disturbance-lab')", msg_id)
        await asyncio.sleep(1.0)
        curr_page, msg_id = await eval_js(ws, "currentPage", msg_id)
        print(f"Current Page in app.js: {curr_page}")

        # 1. Swell initial check
        label_swell, msg_id = await eval_js(ws, "document.getElementById('lab-param-label').textContent", msg_id)
        unit_swell, msg_id = await eval_js(ws, "document.getElementById('lab-param-unit').textContent", msg_id)
        val_swell, msg_id = await eval_js(ws, "document.getElementById('lab-custom-mag').value", msg_id)
        btn_swell, msg_id = await eval_js(ws, "document.getElementById('btn-lab-custom-inject').textContent", msg_id)
        print(f"[TEST 1 SWELL] Label: {label_swell} | Unit: {unit_swell} | Val: {val_swell} | Btn: {btn_swell}")
        assert "Capacitor Qc" in label_swell, f"Expected Capacitor Qc, got {label_swell}"
        assert unit_swell == "MVAr", f"Expected MVAr, got {unit_swell}"
        assert val_swell == "120", f"Expected 120, got {val_swell}"

        # 2. Change to Sag
        _, msg_id = await eval_js(ws, "document.getElementById('lab-custom-class').value = 'Sag'; onCustomClassChange();", msg_id)
        label_sag, msg_id = await eval_js(ws, "document.getElementById('lab-param-label').textContent", msg_id)
        unit_sag, msg_id = await eval_js(ws, "document.getElementById('lab-param-unit').textContent", msg_id)
        val_sag, msg_id = await eval_js(ws, "document.getElementById('lab-custom-mag').value", msg_id)
        btn_sag, msg_id = await eval_js(ws, "document.getElementById('btn-lab-custom-inject').textContent", msg_id)
        print(f"[TEST 2 SAG] Label: {label_sag} | Unit: {unit_sag} | Val: {val_sag} | Btn: {btn_sag}")
        assert "Fault Resistance" in label_sag, f"Expected Fault Resistance, got {label_sag}"
        assert unit_sag == "Ω", f"Expected Ω, got {unit_sag}"
        assert val_sag == "4.5", f"Expected 4.5, got {val_sag}"

        # 3. Change to Harmonics
        _, msg_id = await eval_js(ws, "document.getElementById('lab-custom-class').value = 'Harmonics'; onCustomClassChange();", msg_id)
        label_harm, msg_id = await eval_js(ws, "document.getElementById('lab-param-label').textContent", msg_id)
        btn_harm, msg_id = await eval_js(ws, "document.getElementById('btn-lab-custom-inject').textContent", msg_id)
        print(f"[TEST 3 HARMONICS] Label: {label_harm} | Btn: {btn_harm}")
        assert "H5" in label_harm, f"Expected H5, got {label_harm}"

        # 4. Change to Flicker
        _, msg_id = await eval_js(ws, "document.getElementById('lab-custom-class').value = 'Flicker'; onCustomClassChange();", msg_id)
        label_flk, msg_id = await eval_js(ws, "document.getElementById('lab-param-label').textContent", msg_id)
        btn_flk, msg_id = await eval_js(ws, "document.getElementById('btn-lab-custom-inject').textContent", msg_id)
        print(f"[TEST 4 FLICKER] Label: {label_flk} | Btn: {btn_flk}")
        assert "Mod. Depth" in label_flk, f"Expected Mod. Depth, got {label_flk}"

        # 5. Change to Notch
        _, msg_id = await eval_js(ws, "document.getElementById('lab-custom-class').value = 'Notch'; onCustomClassChange();", msg_id)
        label_ntc, msg_id = await eval_js(ws, "document.getElementById('lab-param-label').textContent", msg_id)
        val_ntc, msg_id = await eval_js(ws, "document.getElementById('lab-custom-mag').value", msg_id)
        print(f"[TEST 5 NOTCH] Label: {label_ntc} | Val: {val_ntc}")
        assert "Commut" in label_ntc, f"Expected Commut, got {label_ntc}"
        assert val_ntc == "150", f"Expected 150, got {val_ntc}"

        # 6. Change back to Swell (matches user's screenshot) and capture screenshot
        _, msg_id = await eval_js(ws, "document.getElementById('lab-custom-class').value = 'Swell'; onCustomClassChange();", msg_id)
        await asyncio.sleep(0.5)

        res, msg_id = await cdp_call(ws, "Page.captureScreenshot", {"format": "png"}, msg_id)
        data = base64.b64decode(res["data"])
        out_path = r'C:\Users\Allen\.gemini\antigravity\brain\bf881e96-0014-4e27-93c0-da9fc42df4ac\form_updating_verified.png'
        with open(out_path, 'wb') as f:
            f.write(data)
        print('Screenshot saved successfully:', out_path)

        print("\n========================================================")
        print("ALL 6 FORM UPDATE TESTS PASSED CLEANLY AND FULLY VERIFIED!")
        print("========================================================")
    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(test_form())
