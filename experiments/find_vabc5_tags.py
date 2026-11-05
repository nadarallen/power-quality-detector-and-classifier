import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8', errors='ignore')
            if 'Vabc_5' in content or 'Iabc_5' in content:
                print(f"File {name} contains Vabc_5 or Iabc_5!")
                # Search where it appears
                for line in content.split('\n'):
                    if 'Vabc_5' in line or 'Iabc_5' in line:
                        print("   ", line.strip()[:150])
