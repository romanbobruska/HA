import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))
groups = {n['id']: n for n in d if n.get('type') == 'group'}

print('Skupiny v orchestratoru:')
for gid, g in groups.items():
    cnt = sum(1 for n in d if n.get('g') == gid)
    fill = g.get('style', {}).get('fill', 'CHYBI')
    label = g.get('style', {}).get('label', 'CHYBI')
    print(f"  [{cnt} nodu] {g['name']} | fill: {fill} | label: {label}")

ungrouped = [n for n in d if not n.get('g') and n.get('type') not in ('group','tab','server','sqlitedb','global-config','comment')]
print()
print('Nody BEZ skupiny:', len(ungrouped))
for n in ungrouped:
    print(f"  {n.get('type','')} | {n.get('name','')} | x:{n.get('x',0)} y:{n.get('y',0)}")
