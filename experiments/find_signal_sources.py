import zipfile
import xml.etree.ElementTree as ET
import re

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for name in z.namelist():
        if name.startswith('simulink/systems/system_'):
            xml_bytes = z.read(name)
            content = xml_bytes.decode('utf-8', errors='ignore')
            if any(k in content for k in ['Vabc_5', 'Iabc_5', 'pqd_live_streamer', 'PQD_Vabc', 'PQD_Iabc']):
                print(f"\n==================== Found in {name} ====================")
                root = ET.fromstring(xml_bytes)
                for block in root.findall('.//Block'):
                    bname = block.get('Name', '')
                    btype = block.get('BlockType', '')
                    sid = block.get('SID', '')
                    for p in block.findall('./P'):
                        pname = p.get('Name')
                        ptext = p.text or ''
                        if any(k in ptext for k in ['Vabc_5', 'Iabc_5', 'pqd_live_streamer', 'PQD_Vabc', 'PQD_Iabc']):
                            print(f"Block SID={sid}, Type={btype}, Name={bname} -> P Name={pname}, Value={ptext}")
                    if any(k in bname for k in ['Vabc_5', 'Iabc_5', 'pqd_live_streamer', 'PQD_Vabc', 'PQD_Iabc']):
                        print(f"Block SID={sid}, Type={btype}, Name={bname}")
