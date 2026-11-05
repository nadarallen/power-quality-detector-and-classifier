import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    with z.open('simulink/blockdiagram.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

print("--- BLOCKS MATCHING PQD ---")
for b in root.iter('Block'):
    name = b.get('Name', '')
    if 'PQD_' in name:
        print(f"Block: {name} (SID={b.get('SID')}, Type={b.get('BlockType')})")
        for p in b.findall('P'):
            if p.get('Name') in ['SourceBlock', 'SourceType', 'External', 'SwitchTimes', 'FaultResistance']:
                print(f"   {p.get('Name')} = {p.text}")

print("\n--- LINES CONNECTED TO PQD ---")
for line in root.iter('Line'):
    src = line.find("P[@Name='Src']")
    dst = line.find("P[@Name='Dst']")
    src_t = src.text if src is not None else ''
    dst_t = dst.text if dst is not None else ''
    branch = line.find('Branch')

    # check if any PQD block is mentioned
    line_str = ET.tostring(line, encoding='unicode')
    if 'PQD_' in line_str:
        print(f"Line: {src_t} -> {dst_t}")
        if branch is not None:
            for b_dst in branch.iter('P'):
                if b_dst.get('Name') == 'Dst':
                    print(f"   Branch Dst: {b_dst.text}")
