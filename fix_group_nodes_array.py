import json

# ROOT CAUSE:
# Node-RED skupiny mají DVĚ místa kde se definuje příslušnost nodu:
# 1. "g" field na nodu (máme správně)
# 2. "nodes" array na skupině (TOTO CHYBÍ pro nody přidané programaticky)
# UI používá "nodes" array pro vizuální renderování skupiny.
# Proto → Solární nabíjení (solar123456789abc) není vizuálně v skupině.
#
# FIX: Pro každou skupinu synchronizuj "nodes" array s nody které mají g == group_id
# PRAVIDLO PRO PŘÍŠTĚ: Při přidání nodu do skupiny vždy aktualizovat OBOJÍ:
#   - node["g"] = group_id
#   - group["nodes"].append(node_id)

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

# Najdi všechny skupiny
groups = {n['id']: n for n in d if n.get('type') == 'group'}

# Pro každou skupinu sesbírej nody které mají g == group_id
nodes_for_group = {}
for n in d:
    if n.get('type') in ('group', 'tab', 'server', 'sqlitedb', 'global-config'):
        continue
    gid = n.get('g', '')
    if gid:
        if gid not in nodes_for_group:
            nodes_for_group[gid] = []
        nodes_for_group[gid].append(n['id'])

# Aktualizuj "nodes" array na každé skupině
for gid, g in groups.items():
    current_nodes = g.get('nodes', [])
    correct_nodes = nodes_for_group.get(gid, [])
    missing = [nid for nid in correct_nodes if nid not in current_nodes]
    extra = [nid for nid in current_nodes if nid not in correct_nodes]

    if missing or extra:
        print(f"Skupina '{g['name']}':")
        if missing:
            print(f"  CHYBÍ v nodes[]: {missing}")
        if extra:
            print(f"  NAVÍC v nodes[]: {extra}")
        g['nodes'] = correct_nodes
        print(f"  -> Opraveno: {len(correct_nodes)} nodů")
    else:
        print(f"Skupina '{g['name']}': OK ({len(correct_nodes)} nodů)")

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
