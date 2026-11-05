import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    with z.open('simulink/systems/system_root.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

for b in root.iter('Block'):
    sid = b.get('SID', '')
    if sid in ['154', '155', '157']:
        print(f"=== Block SID={sid} Name={b.get('Name')} ===")
        print(ET.tostring(b, encoding='unicode'))
