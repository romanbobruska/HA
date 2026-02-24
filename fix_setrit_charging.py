import json

d = json.load(open('node-red/flows/fve-modes.json', encoding='utf-8'))

changes = 0

for n in d:
    # 1. Normal Logic: maxChargePower ma byt vzdy -1 (nelimitovat nabijeni ze solaru)
    if n.get('name') == 'Normal Logic' and n.get('type') == 'function':
        old = 'msg.maxChargePower = blockDischarge ? 0 : -1;'
        new = 'msg.maxChargePower = -1; // Nabijeni ze solaru vzdy povoleno'
        if old in n['func']:
            n['func'] = n['func'].replace(old, new)
            print('OK: Normal Logic - maxChargePower vzdy -1')
            changes += 1
        else:
            print('WARN: Normal Logic - old string not found, hledam...')
            idx = n['func'].find('maxChargePower')
            if idx >= 0:
                print(repr(n['func'][idx-20:idx+80]))

    # 2. Setrit: MaxChargePower = 0 (setrit) -> -1 (povoleno nabijeni ze solaru)
    if n.get('id') == 'max_charge_b49b9676' and n.get('type') == 'api-call-service':
        old_data = '{"value": 0}'
        new_data = '{"value": -1}'
        if n.get('data') == old_data:
            n['data'] = new_data
            # Aktualizuj i action/service data
            print('OK: Setrit MaxChargePower 0 -> -1 (povoleno nabijeni ze solaru)')
            changes += 1
        else:
            print('WARN: max_charge_b49b9676 data:', repr(n.get('data')))

    # 3. Solarni nabijeni group - zkontroluj MaxChargePower
    if n.get('name') == 'MaxChargePower = 0 (šetřit)' or n.get('name') == 'MaxChargePower = 0 (setrit)':
        print('Found:', n['name'], 'id:', n['id'], 'data:', n.get('data'))

print(f'Celkem zmen: {changes}')

json.dump(d, open('node-red/flows/fve-modes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
