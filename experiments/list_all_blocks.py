import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    for name in z.namelist():
        print(name)
    with z.open('simulink/blockdiagram.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

print("\n--- ALL TOP-LEVEL BLOCKS ---")
for b in root.iter('Block'):
    name = b.get('Name', '')
    sid = b.get('SID', '')
    btype = b.get('BlockType', '')
    print(f"SID={sid} Type={btype} Name={name}")
