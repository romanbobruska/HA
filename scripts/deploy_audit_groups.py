"""
Deploy audit: opraví neshody mezi g property nodu a nodes[] array skupiny.
Spouštěn automaticky z deploy.sh po deploy_merge_flows.py.
"""
import json, os, sys

output_file = os.environ.get('OUTPUT_FILE', '/addon_configs/a0d7b954_nodered/flows.json')

if not os.path.exists(output_file):
    print('   WARN: flows.json neexistuje, audit přeskočen')
    sys.exit(0)

with open(output_file, 'r', encoding='utf-8') as f:
    nodes = json.load(f)

by_id = {n['id']: n for n in nodes}

# Nody s g property -> jejich skutečné group ID
node_by_group = {}
for n in nodes:
    if n.get('type') in ('group', 'tab'):
        continue
    g = n.get('g')
    if g:
        node_by_group.setdefault(g, []).append(n['id'])

groups = [n for n in nodes if n.get('type') == 'group']
fixes = 0

for g in groups:
    gid = g['id']
    declared = set(g.get('nodes', []))
    actual = set(node_by_group.get(gid, []))

    missing = actual - declared
    for nid in missing:
        n = by_id.get(nid, {})
        print(f'   FIX: přidávám "{n.get("name", nid)}" do nodes[] skupiny "{g["name"]}"')
        g.setdefault('nodes', []).append(nid)
        fixes += 1

if fixes > 0:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False, indent=4)
    print(f'   ✅ Audit opravil {fixes} neshod v nodes[]')
else:
    print('   ✅ Audit OK - žádné neshody v nodes[]')
