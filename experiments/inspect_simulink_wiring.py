import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for sys_name in ['simulink/systems/system_152.xml', 'simulink/systems/system_root.xml']:
        print(f"\n==================== {sys_name} ====================")
        xml_bytes = z.read(sys_name)
        root = ET.fromstring(xml_bytes)

        # Print blocks
        for block in root.findall('.//Block'):
            btype = block.get('BlockType', '')
            bname = block.get('Name', '')
            if any(k in bname.lower() or k in btype.lower() for k in ['vi', 'streamer', 'pqd', 'vabc', 'iabc', 'bus 5', '5']):
                print(f"Block: Type={btype}, Name={bname}")
                for p in block.findall('./P'):
                    pname = p.get('Name')
                    if pname in ['FunctionName', 'Parameters', 'Ports', 'Value', 'SourceName', 'SignalName', 'GotoTag']:
                        print(f"    P: {pname} = {p.text}")

        # Print lines/connections
        for line in root.findall('.//Line'):
            src = line.find('./P[@Name="Src"]')
            dst = line.find('./P[@Name="Dst"]')
            name = line.find('./P[@Name="Name"]')
            src_txt = src.text if src is not None else ''
            dst_txt = dst.text if dst is not None else ''
            name_txt = name.text if name is not None else ''

            if any(k in src_txt.lower() or k in dst_txt.lower() or k in name_txt.lower() for k in ['vabc', 'iabc', 'pqd', '5', 'stream']):
                print(f"Line: Name={name_txt}, Src={src_txt} -> Dst={dst_txt}")
                for branch in line.findall('.//Branch'):
                    bdst = branch.find('./P[@Name="Dst"]')
                    if bdst is not None:
                        print(f"    Branch Dst={bdst.text}")
