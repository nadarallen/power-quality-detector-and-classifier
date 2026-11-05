import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    xml_bytes = z.read('simulink/systems/system_152.xml')
    root = ET.fromstring(xml_bytes)
    print("=== BLOCKS in system_152 ===")
    for b in root.findall('.//Block'):
        print(f"SID={b.get('SID')}, Type={b.get('BlockType')}, Name={b.get('Name')}")
        for p in b.findall('./P'):
            print(f"    {p.get('Name')} = {p.text}")
    print("\n=== LINES in system_152 ===")
    for l in root.findall('.//Line'):
        src = l.find('./P[@Name="Src"]')
        dst = l.find('./P[@Name="Dst"]')
        print(f"Line Src={src.text if src is not None else ''} -> Dst={dst.text if dst is not None else ''}")
        for br in l.findall('.//Branch'):
            bdst = br.find('./P[@Name="Dst"]')
            print(f"    Branch Dst={bdst.text if bdst is not None else ''}")
