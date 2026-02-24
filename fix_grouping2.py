import json

# Načti orchestrátor
d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

groups = {n['id']: n for n in d if n.get('type') == 'group'}
nodes_by_group = {}
for n in d:
    if n.get('type') in ('group', 'tab', 'server', 'sqlitedb', 'global-config'):
        continue
    gid = n.get('g', '')
    if gid not in nodes_by_group:
        nodes_by_group[gid] = []
    nodes_by_group[gid].append(n)

NODE_W = 160  # typická šířka nodu
NODE_H = 30   # typická výška nodu
PADDING = 20  # padding uvnitř skupiny

print('=== ANALÝZA SKUPIN ===')
for gid, g in groups.items():
    gnodes = nodes_by_group.get(gid, [])
    if not gnodes:
        print(f"SKUPINA '{g['name']}' - PRÁZDNÁ")
        continue

    # Spočítej skutečný bbox nodů
    min_x = min(n.get('x', 0) for n in gnodes)
    min_y = min(n.get('y', 0) for n in gnodes)
    max_x = max(n.get('x', 0) for n in gnodes)
    max_y = max(n.get('y', 0) for n in gnodes)

    # Potřebný bbox skupiny (s paddingem)
    need_x = min_x - PADDING
    need_y = min_y - PADDING
    need_w = (max_x - min_x) + NODE_W + PADDING * 2
    need_h = (max_y - min_y) + NODE_H + PADDING * 2

    # Aktuální bbox skupiny
    cur_x = g['x']
    cur_y = g['y']
    cur_w = g.get('w', 0)
    cur_h = g.get('h', 0)

    print(f"\nSKUPINA: '{g['name']}'")
    print(f"  Aktuální: x:{cur_x} y:{cur_y} w:{cur_w} h:{cur_h}")
    print(f"  Potřebný: x:{need_x} y:{need_y} w:{need_w} h:{need_h}")

    # Zkontroluj nody mimo bbox
    for n in gnodes:
        nx = n.get('x', 0)
        ny = n.get('y', 0)
        if not (cur_x <= nx <= cur_x + cur_w and cur_y <= ny <= cur_y + cur_h):
            print(f"  *** MIMO BBOX: '{n.get('name', n.get('type', ''))}' x:{nx} y:{ny}")

# Nody bez skupiny
ungrouped = nodes_by_group.get('', [])
if ungrouped:
    print(f"\n=== NODY BEZ SKUPINY ({len(ungrouped)}) ===")
    for n in ungrouped:
        print(f"  {n.get('type','')} | {n.get('name','')}")

print('\n=== OPRAVA ===')
print('Opravuji skupiny aby obsahovaly všechny nody...')

# Oprav každou skupinu - rozšiř bbox aby obsahoval všechny nody
changed = False
for gid, g in groups.items():
    gnodes = nodes_by_group.get(gid, [])
    if not gnodes:
        continue

    min_x = min(n.get('x', 0) for n in gnodes)
    min_y = min(n.get('y', 0) for n in gnodes)
    max_x = max(n.get('x', 0) for n in gnodes)
    max_y = max(n.get('y', 0) for n in gnodes)

    need_x = min_x - PADDING
    need_y = min_y - PADDING
    need_w = (max_x - min_x) + NODE_W + PADDING * 2
    need_h = (max_y - min_y) + NODE_H + PADDING * 2

    cur_x = g['x']
    cur_y = g['y']
    cur_w = g.get('w', 0)
    cur_h = g.get('h', 0)

    if cur_x != need_x or cur_y != need_y or cur_w != need_w or cur_h != need_h:
        print(f"  Opravuji '{g['name']}': x:{cur_x}->{need_x} y:{cur_y}->{need_y} w:{cur_w}->{need_w} h:{cur_h}->{need_h}")
        # Najdi node v d a uprav
        for node in d:
            if node.get('id') == gid:
                node['x'] = need_x
                node['y'] = need_y
                node['w'] = need_w
                node['h'] = need_h
                changed = True
                break

if changed:
    json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Saved: fve-orchestrator.json')
else:
    print('Žádné změny potřeba.')
