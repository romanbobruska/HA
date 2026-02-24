# -*- coding: utf-8 -*-
"""Sjednotit Setrit a Normal+blokace:
- Setrit: min_soc = minSoc (ne Math.max(minSoc, currentSoc))
- Normal blokace: MaxDischargePower = 0 (ne dynamicDischargeW)
"""
import json

path = 'node-red/flows/fve-modes.json'
nodes = json.load(open(path, 'r', encoding='utf-8'))

# 1. Setrit Logic
setrit = [n for n in nodes if n.get('name') == '\u0160et\u0159it Logic'][0]
func = setrit['func']

old = 'min_soc: Math.max(minSoc, currentSoc),'
new = 'min_soc: minSoc,'
if old in func:
    func = func.replace(old, new)
    print('OK: Setrit Logic - min_soc: Math.max -> minSoc')
else:
    print('WARN: Setrit Logic - pattern min_soc nenalezen')

old2 = '"% | minSOC:" + Math.max(minSoc, currentSoc) + "% (NO SCHED)"'
new2 = '"% | minSOC:" + minSoc + "% (NO SCHED)"'
if old2 in func:
    func = func.replace(old2, new2)
    print('OK: Setrit Logic - status text opraven')
else:
    print('INFO: Setrit status text - pattern nenalezen (mozna jiz OK)')

setrit['func'] = func

# 2. Normal Logic - blokace: dynamicDischargeW -> 0
normal = [n for n in nodes if n.get('name') == 'Normal Logic'][0]
nfunc = normal['func']

old3 = 'msg.maxDischargePower = blockDischarge ? dynamicDischargeW : -1;'
new3 = 'msg.maxDischargePower = blockDischarge ? 0 : -1;'
if old3 in nfunc:
    nfunc = nfunc.replace(old3, new3)
    print('OK: Normal Logic - blokace MaxDischargePower=0')
else:
    # Zkus najit co tam je
    idx = nfunc.find('maxDischargePower')
    if idx >= 0:
        print('WARN: Normal Logic - nalezeno maxDischargePower ale jiny pattern:')
        print(repr(nfunc[max(0, idx-20):idx+80]))
    else:
        print('WARN: Normal Logic - maxDischargePower nenalezeno vubec')

normal['func'] = nfunc

with open(path, 'w', encoding='utf-8', newline='\n') as out:
    json.dump(nodes, out, indent=4, ensure_ascii=False)
print('Ulozeno.')

# Overeni
setrit2 = [n for n in nodes if n.get('name') == '\u0160et\u0159it Logic'][0]
normal2 = [n for n in nodes if n.get('name') == 'Normal Logic'][0]
print('\n=== OVERENI ===')
for line in setrit2['func'].split('\n'):
    if 'min_soc' in line:
        print('Setrit min_soc:', line.strip())
for line in normal2['func'].split('\n'):
    if 'maxDischargePower' in line and 'blockDischarge' in line:
        print('Normal blokace:', line.strip())
