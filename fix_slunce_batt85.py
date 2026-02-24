import json

d = json.load(open('node-red/flows/nabijeni-auta-slunce.json', encoding='utf-8'))

changes = 0

for n in d:
    # 'Baterky jsou > 85%?' (d027326abd49e85d)
    # out1 (YES, >85%) meni: b007af166f6ef45c (Nastavuj amperaci ON) → 04485a466ad52c1e (Baterie minus → vypocet prebytku)
    if n['id'] == 'd027326abd49e85d':
        print('PRED:', n['wires'])
        if n['wires'][0] == ['b007af166f6ef45c']:
            n['wires'][0] = ['04485a466ad52c1e']
            print('PO:  ', n['wires'])
            changes += 1
        else:
            print('WARN: out1 neni ocekavany', n['wires'][0])

print(f'Celkem zmen: {changes}')

json.dump(d, open('node-red/flows/nabijeni-auta-slunce.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
