import json

with open('_server_flows.json', encoding='utf-8') as f:
    data = json.load(f)

for n in data:
    if n.get('id') == '9e0b46a9dfedea33':
        code = n['func']
        with open('_orch_func.js', 'w', encoding='utf-8') as out:
            out.write(code)
        print(f"Extracted {len(code)} chars, {len(code.split(chr(10)))} lines")
        break
