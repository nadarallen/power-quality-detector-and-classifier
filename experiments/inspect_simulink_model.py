import zipfile
import xml.etree.ElementTree as ET
import re

slx_path = 'IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx'
print(f"Inspecting {slx_path}...")

with zipfile.ZipFile(slx_path, 'r') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8', errors='ignore')
            # Look for streamer, Vabc, Iabc, Bus 5, VI Measurement
            matches = re.findall(r'(\b\w*(?:streamer|Vabc|Iabc|VI\s*Measurement|Three-Phase VI|PQD_V|PQD_I)\w*\b)', content, re.IGNORECASE)
            if matches:
                print(f"File {name}: found {set(matches)}")
                # Search for blocks connecting to pqd_live_streamer
                if 'pqd_live_streamer' in content:
                    print(f"  pqd_live_streamer found in {name}!")
                    # Extract surrounding lines
                    lines = content.split('\n')
                    for i, l in enumerate(lines):
                        if 'pqd_live_streamer' in l or 'Vabc_5' in l or 'Iabc_5' in l:
                            start = max(0, i - 10)
                            end = min(len(lines), i + 15)
                            print(f"--- Context around line {i} ---")
                            print('\n'.join(lines[start:end]))
                            break
