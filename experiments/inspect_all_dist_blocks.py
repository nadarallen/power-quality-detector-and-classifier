import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'r') as z:
    xml_bytes = z.read('simulink/systems/system_root.xml')
    root = ET.fromstring(xml_bytes)

    dist_blocks = [
        'PQD_Fault_Sag', 'PQD_Breaker_Swell', 'PQD_Cap_Swell',
        'PQD_Breaker_Interruption', 'PQD_Breaker_Transient', 'PQD_RLC_Transient',
        'PQD_Harm_Enable', 'PQD_Harm_FromWS', 'PQD_Harm_Switch',
        'PQD_Flicker_Enable', 'PQD_Flicker_FromWS', 'PQD_Flicker_Switch',
        'PQD_Notch_Bus5', 'PQD_Notch_Enable', 'PQD_Notch_FromWS'
    ]

    for b in root.findall('.//Block'):
        name = b.get('Name', '')
        if any(d == name for d in dist_blocks):
            print(f"\n==================== {name} (Type={b.get('BlockType')}) ====================")
            for p in b.findall('./P'):
                print(f"  {p.get('Name')} = {p.text}")
            inst = b.find('./InstanceData')
            if inst is not None:
                print("  --- InstanceData ---")
                for p in inst.findall('./P'):
                    print(f"    {p.get('Name')} = {p.text}")
