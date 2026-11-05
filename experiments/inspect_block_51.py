import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    xml_bytes = z.read('simulink/systems/system_root.xml')
    root = ET.fromstring(xml_bytes)
    for b in root.findall('.//Block'):
        if b.get('SID') in ['51', '152']:
            print(f"Block SID={b.get('SID')}, Name={b.get('Name')}, Type={b.get('BlockType')}")
            for p in b.findall('./P'):
                print(f"   {p.get('Name')} = {p.text}")
