import asyncio
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
import websockets

CDP_PORT = 9339
SCREENSHOT_PATH = r"C:\Users\Allen\.gemini\antigravity\brain\bf881e96-0014-4e27-93c0-da9fc42df4ac\live_swell_injection_verified.png"

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

async def run_test():
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
        await asyncio.sleep(2.0)

        # 1. Click SWELL button in UI
        click_script = """
        (function() {
            const btn = document.getElementById('btn-live-dist-Swell');
            if (btn) btn.click();
            return {
                selected: LIVE_SIM.selectedClass,
                feedback: document.getElementById('live-sidebar-feedback').textContent
            };
        })()
        """
        res, msg_id = await eval_js(ws, click_script, msg_id)
        print("Clicked SWELL via UI:", res)

        # Wait 1.0s for telemetry to ingest the swell waveform into streamBuffer
        await asyncio.sleep(1.0)

        # 2. Check stream buffer stats in browser
        buf_check = """
        (function() {
            const v = LIVE_SIM.streamBuffer.L1 || [];
            let maxVal = 0;
            for (let i = Math.max(0, v.length - 250); i < v.length; i++) {
                if (Math.abs(v[i]) > maxVal) maxVal = Math.abs(v[i]);
            }
            return {
                bufLen: v.length,
                maxPeakPu: maxVal,
                feedback: document.getElementById('live-sidebar-feedback').textContent
            };
        })()
        """
        stats, msg_id = await eval_js(ws, buf_check, msg_id)
        print("Buffer stats during Swell:", stats)

        # 3. Capture screenshot
        shot_res, msg_id = await cdp_call(ws, "Page.captureScreenshot", {
            "format": "png",
            "clip": {"x": 0, "y": 0, "width": 1400, "height": 900, "scale": 1}
        }, msg_id)

        img_bytes = base64.b64decode(shot_res.get("data", ""))
        with open(SCREENSHOT_PATH, "wb") as f:
            f.write(img_bytes)
        print(f"Captured swell screenshot: {SCREENSHOT_PATH} ({len(img_bytes)} bytes)")

        # 4. Reset to normal
        await eval_js(ws, "resetLiveDisturbance()", msg_id)
        print("Reset to normal completed.")

    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(run_test())
