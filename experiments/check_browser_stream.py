import asyncio
import json
import subprocess
import tempfile
import urllib.request
import time
import websockets

CDP_PORT = 9339

async def test_stream():
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
                raw = await ws.recv()
                r = json.loads(raw)
                if r.get('id') == curr:
                    return r.get('result', {})

        async def eval_js(expr):
            res = await cdp_call('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
            return res.get('result', {}).get('value')

        await cdp_call('Page.enable')
        await cdp_call('Runtime.enable')

        await asyncio.sleep(3.0)

        run_id = await eval_js('LIVE_SIM.activeRunId')
        v_len = await eval_js('LIVE_SIM.streamBuffer && LIVE_SIM.streamBuffer.L1 ? LIVE_SIM.streamBuffer.L1.length : 0')
        v_is_array = await eval_js('Array.isArray(LIVE_SIM.streamBuffer.L1)')
        first_5 = await eval_js('LIVE_SIM.streamBuffer.L1.slice(0, 5)')
        last_5 = await eval_js('LIVE_SIM.streamBuffer.L1.slice(-5)')

        print(f'Active Run ID in Browser: {run_id}')
        print(f'StreamBuffer L1 length: {v_len}')
        print(f'StreamBuffer L1 isArray: {v_is_array}')
        print(f'First 5 samples: {first_5}')
        print(f'Last 5 samples: {last_5}')

        # Wait 2 seconds and check if last 5 samples changed
        await asyncio.sleep(2.0)
        last_5_after = await eval_js('LIVE_SIM.streamBuffer.L1.slice(-5)')
        print(f'Last 5 samples 2s later: {last_5_after}')
        print(f'Did buffer update? {last_5 != last_5_after}')

    finally:
        if ws:
            await ws.close()
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(test_stream())
