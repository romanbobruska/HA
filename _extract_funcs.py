import json

with open('_server_flows.json', encoding='utf-8') as f:
    data = json.load(f)

targets = {
    '9e0b46a9dfedea33': '_orch_func.js',
}

for n in data:
    nid = n.get('id')
    if nid in targets and 'func' in n:
        with open(targets[nid], 'w', encoding='utf-8') as f:
            f.write(n['func'])
        print(f"Extracted {nid} → {targets[nid]} ({len(n['func'])} chars, {len(n['func'].splitlines())} lines)")
