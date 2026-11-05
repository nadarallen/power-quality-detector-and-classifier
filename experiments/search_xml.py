import xml.etree.ElementTree as ET
import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    for filename in z.namelist():
        if filename.startswith('simulink/systems/'):
            with z.open(filename) as f:
                content = f.read().decode('utf-8', errors='ignore')
                for match in ['PQD_', 'Fault', 'Breaker', 'Capacitor', 'Notch']:
                    if match in content:
                        print(f"Found '{match}' in {filename}")
