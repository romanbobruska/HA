#!/usr/bin/env python3
"""Fix escaped quotes in main_logic_func on server flows.json"""
import json
import sys

path = sys.argv[1]
f = json.load(open(path))
for n in f:
    if n.get('id') == 'main_logic_func':
        func = n['func']
        idx = func.find('_zapNak')
        end = func.find('if(solCyklus)', idx)
        block = func[idx:end]
        # Replace \\" (escaped backslash-quote) with just "
        fixed = block.replace('\\"', '"')
        func = func[:idx] + fixed + func[end:]
        n['func'] = func
        lines = func.split('\n')
        for i in range(48, 53):
            if i < len(lines):
                print(f'{i+1}: {lines[i]}')
        break

with open(path, 'w') as out:
    json.dump(f, out, ensure_ascii=False)
print('OK saved')
