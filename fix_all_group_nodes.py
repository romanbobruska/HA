import json, os

flows_dir = 'node-red/flows'
total_fixed = 0

for fname in sorted(os.listdir(flows_dir)):
    if not fname.endswith('.json'):
        continue
    fpath = os.path.join(flows_dir, fname)
    d = json.load(open(fpath, encoding='utf-8'))

    groups = {n['id']: n for n in d if n.get('type') == 'group'}
    if not groups:
        continue

    nodes_for_group = {}
    for n in d:
        if n.get('type') in ('group', 'tab', 'server', 'sqlitedb', 'global-config'):
            continue
        gid = n.get('g', '')
        if gid:
            if gid not in nodes_for_group:
                nodes_for_group[gid] = []
            nodes_for_group[gid].append(n['id'])

    file_changed = False
    for gid, g in groups.items():
        current_nodes = g.get('nodes', [])
        correct_nodes = nodes_for_group.get(gid, [])
        missing = [nid for nid in correct_nodes if nid not in current_nodes]
        extra = [nid for nid in current_nodes if nid not in correct_nodes]

        if missing or extra:
            print(f"{fname} | '{g['name']}':")
            if missing:
                print(f"  CHYBÍ: {missing}")
            if extra:
                print(f"  NAVÍC: {extra}")
            g['nodes'] = correct_nodes
            file_changed = True
            total_fixed += len(missing) + len(extra)

    if file_changed:
        json.dump(d, open(fpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"  -> Saved: {fname}")

print(f"\nCelkem opraveno: {total_fixed} nesrovnalostí")
