import json

# Analyzuj vzorove flows - jak Node-RED uklada h skupin
for fname in ['fve-modes.json', 'fve-heating.json']:
    d = json.load(open('node-red/flows/' + fname, encoding='utf-8'))
    groups = {n['id']: n for n in d if n.get('type') == 'group'}
    print('=== ' + fname + ' ===')
    for gid, g in groups.items():
        gnodes = [n for n in d if n.get('g') == gid]
        if not gnodes:
            continue
        max_y = max(n.get('y', 0) for n in gnodes)
        min_y = g['y']
        rel_max_y = max_y - min_y
        margin = g['h'] - rel_max_y
        print(f"  {g['name']}: group_y:{min_y} h:{g['h']} | max_node_y:{max_y} rel:{rel_max_y} | margin:{margin}")

print()
print('=== fve-orchestrator.json (aktualni) ===')
d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))
groups = {n['id']: n for n in d if n.get('type') == 'group'}
for gid, g in groups.items():
    gnodes = [n for n in d if n.get('g') == gid]
    if not gnodes:
        continue
    max_y = max(n.get('y', 0) for n in gnodes)
    min_y = g['y']
    rel_max_y = max_y - min_y
    margin = g['h'] - rel_max_y
    print(f"  {g['name']}: group_y:{min_y} h:{g['h']} | max_node_y:{max_y} rel:{rel_max_y} | margin:{margin}")
