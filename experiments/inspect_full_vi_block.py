import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    content = z.read('simulink/systems/system_root.xml').decode('utf-8', errors='ignore')
    idx = content.find('Vabc_5')
    if idx != -1:
        # Find opening <Block before idx
        b_start = content.rfind('<Block ', 0, idx)
        b_end = content.find('</Block>', idx) + len('</Block>')
        print(content[b_start:b_end])
