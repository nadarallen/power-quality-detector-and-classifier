import asyncio
import json
import subprocess
import tempfile
import urllib.request
import time
import base64
import websockets

CDP_PORT = 9341

async def verify_scope():
    profile = tempfile.mkdtemp()
    cmd = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        '--headless=new',
        f'--remote-debugging-port={CDP_PORT}',
        f'--user-data-dir={profile}',
        'http://127.0.0.1:8500/#live-simulink'
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    ws = None
    try:
        tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list').read().decode('utf-8'))
        matching = [t for t in tabs if '8500' in t.get('url', '')]
        tab_ws = matching[0]['webSocketDebuggerUrl'] if matching else tabs[0]['webSocketDebuggerUrl']
        ws = await websockets.connect(tab_ws, max_size=100*1024*1024)
        msg_id = 1

        async def cdp_call(method, params=None):
            nonlocal msg_id
            curr = msg_id
            msg_id += 1
            await ws.send(json.dumps({'id': curr, 'method': method, 'params': params or {}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == curr:
                    return r.get('result', {})

        async def eval_js(expr):
            res = await cdp_call('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
            return res.get('result', {}).get('value')

        await cdp_call('Page.enable')
        await cdp_call('Runtime.enable')
        await cdp_call('Emulation.setDeviceMetricsOverride', {'width': 1400, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})

        await asyncio.sleep(2.5)

        badge_text = await eval_js("document.getElementById('scope-v-live-badge').textContent")
        sim_time = await eval_js("document.getElementById('scope-v-sim-time').textContent")
        v_rms = await eval_js("document.getElementById('leg-v-l1').textContent")
        print(f"Scope Badge: {badge_text} | Sim Time: {sim_time} | Legend: {v_rms}")

        res = await cdp_call('Page.captureScreenshot', {'format': 'png'})
        data = base64.b64decode(res['data'])
        out_path = r'C:\Users\Allen\.gemini\antigravity\brain\bf881e96-0014-4e27-93c0-da9fc42df4ac\live_oscilloscope_sweep_verified.png'
        with open(out_path, 'wb') as f:
            f.write(data)
        print('Screenshot saved successfully:', out_path)
    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(verify_scope())
