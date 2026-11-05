import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            xml_bytes = z.read(name)
            if b'GotoTag' in xml_bytes:
                root = ET.fromstring(xml_bytes)
                for b in root.findall('.//Block'):
                    btype = b.get('BlockType', '')
                    if btype in ['Goto', 'From']:
                        gt = b.find('./P[@Name="GotoTag"]')
                        if gt is not None:
                            print(f"{name}: Type={btype}, Name={b.get('Name')}, Tag={gt.text}")
