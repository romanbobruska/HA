import os, shutil, sys

repo = '/tmp/HA/homeassistant'
dst = '/config'
files = [
    'configuration.yaml', 'automations.yaml', 'scripts.yaml', 'scenes.yaml',
    'mqtt.yaml', 'modbus.yaml', 'input_numbers.yaml',
    'template_sensors.yaml', 'template_switches.yaml'
]
for f in files:
    src = os.path.join(repo, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(dst, f))
        print('   OK ' + f)
    else:
        print('   SKIP ' + f + ' (nenalezen v repo)')
