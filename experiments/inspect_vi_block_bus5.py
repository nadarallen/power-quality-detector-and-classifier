import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    xml_bytes = z.read('simulink/systems/system_root.xml')
    root = ET.fromstring(xml_bytes)
    for b in root.findall('.//Block'):
        for p in b.findall('./P'):
            if p.text in ['Vabc_5', 'Iabc_5']:
                print(f"Block SID={b.get('SID')}, Name={b.get('Name')}, Type={b.get('BlockType')}")
                for p2 in b.findall('./P'):
                    print(f"    {p2.get('Name')} = {p2.text}")
                break
