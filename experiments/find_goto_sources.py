import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    for fname in z.namelist():
        if fname.startswith('simulink/systems/'):
            with z.open(fname) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for b in root.iter('Block'):
                    for p in b.findall('P'):
                        if p.get('Name') == 'GotoTag' and ('Vabc' in str(p.text) or 'Iabc' in str(p.text)):
                            print(f"{fname} -> Block: {b.get('Name')} (SID={b.get('SID')}), GotoTag={p.text}")
