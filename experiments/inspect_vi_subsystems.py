import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for name in ['simulink/systems/system_51.xml', 'simulink/systems/system_17.xml', 'simulink/systems/system_34.xml']:
        print(f"\n==================== {name} ====================")
        xml_bytes = z.read(name)
        root = ET.fromstring(xml_bytes)
        for b in root.findall('.//Block'):
            sid = b.get('SID', '')
            name_attr = b.get('Name', '')
            btype = b.get('BlockType', '')
            print(f"SID={sid}, Type={btype}, Name={name_attr}")
            for p in b.findall('./P'):
                if p.get('Name') in ['GotoTag', 'VariableName', 'SourceBlock', 'Ports']:
                    print(f"   {p.get('Name')} = {p.text}")
