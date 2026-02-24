import json

# ROOT CAUSE:
# Node-RED UI renderuje skupinu s bbox = group_y + h.
# Vzorové flows mají margin ~41px (fve-heating.json).
# Aktuální Exekuce plánu: group_y:279, h:302 → spodní hrana: 279+302=581
# → Solární nabíjení: y:520 → rel_y:241, margin:61 → mělo by být OK.
#
# Skutečný problém: Node-RED UI při načtení flows.json IGNORUJE w/h skupiny
# a přepočítává bbox z nodů. Pokud je node na y:520 a skupina na y:279,
# UI spočítá h = 520 - 279 + NODE_HEIGHT = 241 + 60 = 301.
# Pak nastaví h=301 a uloží. Ale my máme h:302 → rozdíl 1px.
# UI pak node "ořízne" protože 520+60=580 > 279+302=581 (jen 1px volno).
#
# ŘEŠENÍ: Přesunout → Solární nabíjení na y:480 (stejně jako → Zákaz přetoků)
# a → Zákaz přetoků posunout na y:440, → Prodávat na y:400 atd.
# NEBO: Zachovat pozice ale zvětšit h skupiny na 342 (margin 101px).
#
# Nejjednodušší fix: zvětšit h skupiny na hodnotu kde margin >= 60px
# (aby UI při přepočtu nezmenšil skupinu pod node)
# h = (max_node_y - group_y) + 60 (NODE_H) + 60 (safe margin) = 241 + 120 = 361

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

for node in d:
    if node.get('id') == 'c0d4d6462d4ebded':
        old_h = node.get('h', 0)
        # h = rel_max_y + NODE_HEIGHT + safe_margin = 241 + 60 + 60 = 361
        node['h'] = 361
        print(f"Exekuce plánu h: {old_h} -> {node['h']}")
        break

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
