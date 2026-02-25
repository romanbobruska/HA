import json, glob, os, sys

flows_dir = os.environ.get('FLOWS_DIR', '/tmp/HA/node-red/flows')
output_file = os.environ.get('OUTPUT_FILE', '/addon_configs/a0d7b954_nodered/flows.json')

# Klíče které přebíráme z gitu (logika) — pozice ze serveru zachováme
LOGIC_KEYS = {'func', 'wires', 'rules', 'sql', 'links', 'cases', 'outputs',
              'property', 'propertyType', 'repeat', 'crontab', 'once', 'onceDelay',
              'payload', 'payloadType', 'topic', 'name', 'active', 'disabled',
              'entity_id', 'entities', 'outputProperties', 'server', 'mydb',
              'sqlquery', 'halt_if', 'halt_if_type', 'halt_if_compare',
              'outputInitially', 'outputOnlyOnStateChange', 'stateType',
              'nodes', 'style', 'label', 'info', 'env', 'mode', 'complete',
              'targetType', 'statusVal', 'statusType', 'tosidebar', 'console',
              'tostatus'}

# Klíče pozic — VŽDY zachovat ze serveru pokud server node existuje
LAYOUT_KEYS = {'x', 'y', 'w', 'h'}

# 1. Načti aktuální server flows jako základ
server_by_id = {}
if os.path.exists(output_file):
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            server_nodes = json.load(f)
        for n in server_nodes:
            nid = n.get('id')
            if nid:
                server_by_id[nid] = n
        print('   Server flows loaded: ' + str(len(server_by_id)) + ' nodes')
    except Exception as e:
        print('   WARN: Nelze nacist server flows: ' + str(e), file=sys.stderr)

# 2. Načti git flows
git_by_id = {}
files_merged = 0
for fpath in sorted(glob.glob(os.path.join(flows_dir, '*.json'))):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            nodes = json.loads(f.read().rstrip().rstrip('.'))
        added = 0
        for node in nodes:
            nid = node.get('id', '')
            if nid and nid not in git_by_id:
                git_by_id[nid] = node
                added += 1
        files_merged += 1
        print('   OK ' + fname + ' (' + str(added) + ' nodes)')
    except Exception as e:
        print('   ERR ' + fname + ': ' + str(e), file=sys.stderr)

# 3. Merge: git je základ logiky, server zachovává pozice
all_nodes = []
seen_ids = set()

for nid, git_node in git_by_id.items():
    if nid in seen_ids:
        continue
    seen_ids.add(nid)

    merged = dict(git_node)  # začni s git verzí (logika)

    # Pokud node existuje na serveru, zachovej jeho pozice
    if nid in server_by_id:
        srv = server_by_id[nid]
        for key in LAYOUT_KEYS:
            if key in srv:
                merged[key] = srv[key]

    all_nodes.append(merged)

# Přidej server nody které nejsou v gitu (config nody, server references apod.)
for nid, srv_node in server_by_id.items():
    if nid not in seen_ids:
        # Zachovat pouze config/server/credentials nody, ne flow nody
        ntype = srv_node.get('type', '')
        if ntype in ('server', 'sqlitedb', 'global-config', 'credentials') or \
           nid.startswith('c7421fe') or '.' in nid:  # starší ID formát s tečkou = config
            all_nodes.append(srv_node)
            seen_ids.add(nid)
            print('   Zachovan server-only node: ' + ntype + ' ' + nid[:16])

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_nodes, f, ensure_ascii=False, indent=4)

print('')
print('   Celkem: ' + str(files_merged) + ' flows, ' + str(len(all_nodes)) + ' nodes')
print('   Ulozeno: ' + output_file)
