import zipfile

with zipfile.ZipFile('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx') as z:
    with z.open('simulink/systems/system_152.xml') as f:
        print(f.read().decode('utf-8'))
