import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for name in z.namelist():
        if name.startswith('simulink/'):
            xml_bytes = z.read(name)
            content = xml_bytes.decode('utf-8', errors='ignore')
            if 'Vabc_5' in content or 'Iabc_5' in content:
                root = ET.fromstring(xml_bytes)
                for block in root.findall('.//Block'):
                    bname = block.get('Name', '')
                    btype = block.get('BlockType', '')
                    sid = block.get('SID', '')
                    for p in block.findall('./P'):
                        pname = p.get('Name')
                        ptext = p.text or ''
                        if ptext in ['Vabc_5', 'Iabc_5']:
                            print(f"File {name}: Block SID={sid}, Type={btype}, Name={bname} -> P Name={pname}, Value={ptext}")
