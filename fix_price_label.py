import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

for n in d:
    if n.get('id') == '9e0b46a9dfedea33':
        func = n['func']

        old = 'var priceInfo = levelBuy >= PRAH_DRAHA ? "drahá" : "střední";'
        new = 'var priceInfo = levelBuy >= PRAH_DRAHA ? "drahá" : (levelBuy <= PRAH_LEVNA ? "levná" : "střední");'

        if old in func:
            func = func.replace(old, new)
            print('OK: priceInfo - přidána kategorie "levná" pro levelBuy <= PRAH_LEVNA')
        else:
            print('WARN: old string not found')
            print(repr(func[func.find('priceInfo'):func.find('priceInfo')+100]))

        n['func'] = func
        break

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
