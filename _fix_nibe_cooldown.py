"""Fix NIBE cooldown default from 3 to 1 minute (user confirmed 1 min is correct)"""
import json

with open('_server_flows.json', encoding='utf-8') as f:
    data = json.load(f)

changes = []
for n in data:
    if n.get('id') == 'htg_main_func' and 'func' in n:
        old = 'config.nibe_cooldown_min || 3'
        new = 'config.nibe_cooldown_min || 1'
        if old in n['func']:
            n['func'] = n['func'].replace(old, new)
            changes.append("htg_main_func: NIBE cooldown default 3→1 min")
        else:
            print("WARN: nenalezen nibe_cooldown_min || 3")

# Save server flows
with open('_server_flows.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Sync to local
with open('node-red/flows/fve-heating.json', encoding='utf-8') as f:
    local = json.load(f)
for ln in local:
    if ln.get('id') == 'htg_main_func':
        for sn in data:
            if sn.get('id') == 'htg_main_func':
                ln['func'] = sn['func']
                changes.append("fve-heating.json synced")
                break
with open('node-red/flows/fve-heating.json', 'w', encoding='utf-8') as f:
    json.dump(local, f, indent=4, ensure_ascii=False)

# Validate
for fp in ['_server_flows.json', 'node-red/flows/fve-heating.json']:
    json.load(open(fp, encoding='utf-8'))
    print(f"✅ {fp} valid JSON")

for c in changes:
    print(f"  ✅ {c}")
