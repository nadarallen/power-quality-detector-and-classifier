import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    for fname in z.namelist():
        if fname.startswith('simulink/systems/'):
            with z.open(fname) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for b in root.iter('Block'):
                    src = b.find("P[@Name='SourceBlock']")
                    srct = b.find("P[@Name='SourceType']")
                    if (src is not None and 'VI' in str(src.text)) or (srct is not None and 'VI' in str(srct.text)):
                        print(f"{fname} -> SID={b.get('SID')} Name='{b.get('Name')}'")
                        for p in b.findall('P'):
                            print(f"   {p.get('Name')} = {p.text}")
