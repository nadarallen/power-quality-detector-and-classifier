import asyncio, json, urllib.request, base64
import websockets

async def capture_scrolled():
    resp = urllib.request.urlopen("http://127.0.0.1:9224/json").read()
    tabs = json.loads(resp)
    ws_url = tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        async def call(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cid = msg_id
            await ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get("id") == cid:
                    return r.get("result", {})

        msg_id = 0
        await call("Page.enable")

        # Navigate to live simulink
        await call("Page.navigate", {"url": "http://127.0.0.1:8500/#live-simulink"})
        await asyncio.sleep(2.0)

        # Scroll down to show Current Oscilloscope & FFT spectrum
        await call("Runtime.evaluate", {"expression": "window.scrollTo(0, 520);"})
        await asyncio.sleep(1.0)

        res = await call("Page.captureScreenshot", {"format": "png"})
        png_bytes = base64.b64decode(res["data"])
        with open("experiments/live_simulink_scrolled_current_fft.png", "wb") as f:
            f.write(png_bytes)
        print("Captured: experiments/live_simulink_scrolled_current_fft.png")

asyncio.run(capture_scrolled())
