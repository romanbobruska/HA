#!/usr/bin/env python3
"""Fix: Read charger amperage directly from HA global state instead of broken node chain.
The HA node converts "14A" to NaN (state_type: num), causing chargeramp_a=0,
which breaks both availableW calculation and ±2A damping."""

import json, sys

f = r'node-red\flows\nabijeni-auta-slunce.json'
data = json.load(open(f, 'r', encoding='utf-8'))

node = None
for n in data:
    if n.get('id') == '788e188fae8d1fca':
        node = n
        break

if not node:
    print("ERROR: node 788e188fae8d1fca not found")
    sys.exit(1)

old_func = node['func']

# What we're replacing
old_code = "// Entity 'select.wallboxu_garaz_amperace' vraci '16A' - parsuj cislo\nlet rawCharger = String(msg.payload_charger || '0');\nlet chargeramp_a = parseInt(rawCharger.replace(/[^0-9]/g, ''), 10) || 0;"

# New code: read directly from HA global state
new_code = "// v22: Read amperage directly from HA global state (node chain converts '14A' to NaN)\nvar ampState = global.get(\"homeassistant.homeAssistant.states['select.wallboxu_garaz_amperace']\") || {};\nlet rawCharger = String(ampState.state || '0');\nlet chargeramp_a = parseInt(rawCharger.replace(/[^0-9]/g, ''), 10) || 0;"

if old_code not in old_func:
    print("ERROR: old code pattern not found in func")
    print("First 400 chars:", repr(old_func[:400]))
    sys.exit(1)

node['func'] = old_func.replace(old_code, new_code)
print("OK: Replaced charger reading with direct HA state access")

# Verify damping code is present
if 'DAMPING: max +-2A' in node['func']:
    print("OK: Damping code confirmed present")
else:
    print("WARNING: Damping code not found!")

json.dump(data, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
print("File saved successfully")
