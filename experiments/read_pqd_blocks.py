import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    for fname in ['simulink/systems/system_root.xml', 'simulink/systems/system_152.xml']:
        with z.open(fname) as f:
            tree = ET.parse(f)
            root = tree.getroot()
            print(f"=== {fname} ===")
            for b in root.iter('Block'):
                name = b.get('Name', '')
                if 'PQD_' in name:
                    sid = b.get('SID', '')
                    btype = b.get('BlockType', '')
                    print(f"  SID={sid} Type={btype} Name={name}")
                    for p in b.findall('P'):
                        if p.get('Name') in ['SourceBlock', 'SourceType', 'External', 'SwitchTimes', 'FaultResistance', 'GotoTag', 'Value']:
                            print(f"     {p.get('Name')} = {p.text}")
