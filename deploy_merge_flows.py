import json, glob, os, sys

flows_dir = os.environ.get('FLOWS_DIR', '/tmp/HA/node-red/flows')
output_file = os.environ.get('OUTPUT_FILE', '/addon_configs/a0d7b954_nodered/flows.json')

all_nodes = []
seen_ids = set()
files_merged = 0

for fpath in sorted(glob.glob(os.path.join(flows_dir, '*.json'))):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            nodes = json.loads(f.read().rstrip().rstrip('.'))
        added = 0
        for node in nodes:
            nid = node.get('id', '')
            if nid in seen_ids:
                continue
            seen_ids.add(nid)
            all_nodes.append(node)
            added += 1
        files_merged += 1
        print('   OK ' + fname + ' (' + str(added) + ' nodes)')
    except Exception as e:
        print('   ERR ' + fname + ': ' + str(e), file=sys.stderr)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_nodes, f, ensure_ascii=False, indent=4)

print('')
print('   Celkem: ' + str(files_merged) + ' flows, ' + str(len(all_nodes)) + ' nodes')
print('   Ulozeno: ' + output_file)
