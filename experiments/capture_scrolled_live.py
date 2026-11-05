import asyncio, base64, json, os, subprocess, time, urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9226
ARTIFACTS_DIR = r"C:\Users\Allen\.gemini\antigravity\brain\bf881e96-0014-4e27-93c0-da9fc42df4ac"
PROFILE_DIR = r"C:\Users\Allen\AppData\Local\Temp\chrome_scroll_profile"

chrome_proc = subprocess.Popen([
    CHROME_PATH,
    "--headless=new",
    f"--remote-debugging-port={CDP_PORT}",
    f"--user-data-dir={PROFILE_DIR}",
    "--window-size=1640,1100",
    "--disable-gpu",
    "--hide-scrollbars",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(2.0)

async def capture():
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json").read()
        tabs = json.loads(resp)
        ws_url = tabs[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            msg_id = 0
            async def call(method, params=None):
                nonlocal msg_id
                msg_id += 1
                cid = msg_id
                await ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("id") == cid:
                        return r.get("result", {})

            await call("Page.enable")
            await call("Page.navigate", {"url": "http://127.0.0.1:8500/#live-simulink"})
            await asyncio.sleep(2.5)

            # Scroll down to display Current Oscilloscope and FFT spectrum clearly
            await call("Runtime.evaluate", {"expression": "window.scrollTo(0, 680);"})
            await asyncio.sleep(1.0)

            res = await call("Page.captureScreenshot", {"format": "png"})
            png_bytes = base64.b64decode(res["data"])

            for path in [
                "experiments/live_simulink_scrolled_current_fft.png",
                os.path.join(ARTIFACTS_DIR, "live_simulink_scrolled_current_fft.png")
            ]:
                with open(path, "wb") as f:
                    f.write(png_bytes)
            print("Successfully captured live_simulink_scrolled_current_fft.png")
    finally:
        chrome_proc.terminate()

asyncio.run(capture())
