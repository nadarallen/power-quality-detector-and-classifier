import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    with z.open('simulink/systems/system_root.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

def get_lines_for(keywords):
    lines = []
    for line in root.iter('Line'):
        s = ET.tostring(line, encoding='unicode')
        if any(k in s for k in keywords):
            lines.append(line)
    return lines

for kw in ['154', '155', '156', '157', 'PQD_Fault_Sag', 'PQD_Breaker_Swell', 'PQD_Breaker_Interruption']:
    lines = get_lines_for([kw])
    print(f"\nLines mentioning {kw}: count={len(lines)}")
    for l in lines:
        src = l.find("P[@Name='Src']")
        dst = l.find("P[@Name='Dst']")
        src_t = src.text if src is not None else ''
        dst_t = dst.text if dst is not None else ''
        print(f"  {src_t} -> {dst_t}")
        for b in l.iter('Branch'):
            bdst = b.find("P[@Name='Dst']")
            if bdst is not None:
                print(f"     branch -> {bdst.text}")
