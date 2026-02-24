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

# Kopíruj adresáře (themes, atd.)
dirs = ['themes']
for d in dirs:
    src_dir = os.path.join(repo, d)
    dst_dir = os.path.join(dst, d)
    if os.path.exists(src_dir):
        os.makedirs(dst_dir, exist_ok=True)
        for fname in os.listdir(src_dir):
            shutil.copy2(os.path.join(src_dir, fname), os.path.join(dst_dir, fname))
            print('   OK ' + d + '/' + fname)
    else:
        print('   SKIP ' + d + '/ (nenalezen v repo)')
