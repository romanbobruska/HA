import json

# ROOT CAUSE ANALÝZA:
# Node-RED UI počítá výšku nodu jako 60px (ne 30px).
# Proto bbox skupiny musí mít h >= (max_rel_y + 60 + padding).
# Při výpočtu: rel_y = node_abs_y - group_y
# → Solární nabíjení: rel_y = 520 - 279 = 241
# → potřebné h = 241 + 60 (výška nodu) + 20 (padding) = 321
#
# PRAVIDLO PRO PŘÍŠTĚ:
# NODE_H = 60px (skutečná výška nodu v Node-RED UI)
# PADDING = 20px
# h = (max_node_y - group_y) + NODE_H + PADDING

NODE_H = 60   # skutečná výška nodu v Node-RED UI
PADDING = 20  # padding pod posledním nodem

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

for gid, g in groups.items():
    gnodes = nodes_by_group.get(gid, [])
    if not gnodes:
        continue

    min_x = min(n.get('x', 0) for n in gnodes)
    min_y = min(n.get('y', 0) for n in gnodes)
    max_x = max(n.get('x', 0) for n in gnodes)
    max_y = max(n.get('y', 0) for n in gnodes)

    # x, y skupiny zachovat (jsou správné z HA)
    # Přepočítej pouze w a h s NODE_H=60
    new_w = (max_x - g['x']) + NODE_H*3 + PADDING   # šířka: od levého okraje skupiny po pravý node + node šířka
    new_h = (max_y - g['y']) + NODE_H + PADDING       # výška: od horního okraje skupiny po spodní node + výška nodu

    # Zachovej x a y z HA (jsou správné), uprav jen w a h
    old_w, old_h = g.get('w', 0), g.get('h', 0)
    g['w'] = new_w
    g['h'] = new_h
    print(f"Skupina '{g['name']}': w:{old_w}->{new_w} h:{old_h}->{new_h}")
    print(f"  max_node: abs_x:{max_x} abs_y:{max_y} | rel_x:{max_x-g['x']} rel_y:{max_y-g['y']}")
    print(f"  → Solární nabíjení fit: rel_y:{max_y-g['y']} + NODE_H:{NODE_H} + PAD:{PADDING} = {max_y-g['y']+NODE_H+PADDING} <= h:{new_h}")

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
