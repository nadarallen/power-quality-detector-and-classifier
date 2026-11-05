import zipfile
import re

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    content = z.read('simulink/systems/system_root.xml').decode('utf-8', errors='ignore')
    idx = content.find('Vabc_5')
    if idx != -1:
        start = max(0, idx - 500)
        end = min(len(content), idx + 500)
        print(content[start:end])
