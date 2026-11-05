import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    with z.open('simulink/systems/system_root.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

blocks = {b.get('SID'): b.get('Name') for b in root.iter('Block')}

for line in root.iter('Line'):
    src = line.find("P[@Name='Src']")
    dst = line.find("P[@Name='Dst']")
    src_t = src.text if src is not None else ''
    dst_t = dst.text if dst is not None else ''

    # check if any connection connects to 154, 155, 156, 157, 158, 160, 162, 169, 171, 173, 180, 185, 186
    dist_sids = ['154', '155', '157', '158', '160', '162', '169', '171', '173', '180', '185', '186']
    line_str = ET.tostring(line, encoding='unicode')
    if any(f"{sid}#" in line_str for sid in dist_sids):
        def format_port(p_str):
            if not p_str or '#' not in p_str: return p_str
            sid, port = p_str.split('#')
            name = blocks.get(sid, sid).replace('\n', ' ')
            return f"{name} ({sid}) #{port}"

        out_str = f"Line: {format_port(src_t)} -> {format_port(dst_t)}"
        for br in line.iter('Branch'):
            bdst = br.find("P[@Name='Dst']")
            if bdst is not None:
                out_str += f" | Branch -> {format_port(bdst.text)}"
        print(out_str)
