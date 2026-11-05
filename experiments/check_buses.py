import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    with z.open('simulink/systems/system_root.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

for b in root.iter('Block'):
    name = b.get('Name', '')
    sid = b.get('SID', '')
    if 'Bus' in name or 'VI' in name:
        print(f"SID={sid} Name='{name}' Type={b.get('BlockType')}")
