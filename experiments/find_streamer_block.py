import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8', errors='ignore')
            if 'pqd_live_streamer' in content:
                print(f"File {name} contains pqd_live_streamer!")
                idx = content.find('pqd_live_streamer')
                b_start = content.rfind('<Block ', 0, idx)
                b_end = content.find('</Block>', idx) + len('</Block>')
                print(content[b_start:b_end])
