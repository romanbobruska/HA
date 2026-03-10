import json

with open('_server_flows.json', encoding='utf-8') as f:
    data = json.load(f)

targets = ['NORMAL Logic', 'ŠETŘIT Logic']
for n in data:
    if n.get('name') in targets and 'func' in n:
        print(f"=== {n['name']} ({n['id']}) ===")
        print(n['func'])
        print()
