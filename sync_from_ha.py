import json

# Finální layout z HA (po úpravách uživatele) - toto je vzor
# Synchronizuj lokální fve-orchestrator.json s tímto stavem

# Pozice z HA flows.json
ha_positions = {
    # Skupiny
    '4580a451a0858d03': {'x': 14,  'y': 19,  'w': 1032, 'h': 242},  # Plánování
    'c0d4d6462d4ebded': {'x': 14,  'y': 279, 'w': 1092, 'h': 242},  # Exekuce plánu
    '66210c073baa5af0': {'x': 14,  'y': 539, 'w': 672,  'h': 142},  # Kontrola priorit

    # Nody - Plánování
    '22e7b3b8965c20db': {'x': 140, 'y': 60},   # Každou minutu
    'f037d87ec94c7da2': {'x': 55,  'y': 120},  # ← Manuální trigger
    '9333668b1d326a83': {'x': 370, 'y': 100},  # Sbírka dat pro plánování
    'aabb001122334455': {'x': 620, 'y': 100},  # Čti čerstvé ceny z DB
    'aabb001122334466': {'x': 880, 'y': 100},  # Aktualizuj ceny v planData
    '9e0b46a9dfedea33': {'x': 420, 'y': 180},  # Výpočet plánu na 12h
    'df085ac4da095340': {'x': 680, 'y': 160},  # Ulož plán
    '517215d5f730e80c': {'x': 860, 'y': 160},  # Aktualizuj HA sensor
    '39019d1a78677231': {'x': 690, 'y': 220},  # Plan Debug
    '701e94d82c3aead0': {'x': 920, 'y': 220},  # Zapiš plán do souboru

    # Nody - Exekuce plánu
    '44d31ff3c04741b7': {'x': 160,  'y': 320},  # Každých 15 sekund
    'c36915a8599c5282': {'x': 170,  'y': 400},  # Kontrola podmínek
    '8eef6d1d51c9c644': {'x': 450,  'y': 400},  # Rozhodnutí o akci
    '19a783a61de3519b': {'x': 690,  'y': 400},  # Směrování podle módu
    'f10a91fcb4de6bd3': {'x': 1065, 'y': 320},  # → Normal
    '7f051a6595e57c3e': {'x': 1065, 'y': 360},  # → Šetřit
    '185f95d7c56fe799': {'x': 1065, 'y': 400},  # → Nabíjet
    'a706b353f30c25d1': {'x': 1065, 'y': 440},  # → Prodávat
    'a86bc5233cfa0458': {'x': 1065, 'y': 480},  # → Zákaz přetoků
    'solar123456789abc': {'x': 1065, 'y': 520}, # → Solární nabíjení
    'blokace_file_update': {'x': 380, 'y': 480}, # Aktualizuj blokaci v souboru
    'blokace_file_write':  {'x': 630, 'y': 480}, # Zapiš blokaci

    # Nody - Kontrola priorit
    'fc848e97e2c781c1': {'x': 140, 'y': 580},  # Změna stavu wallboxu
    '376106d716756636': {'x': 360, 'y': 580},  # Kontrola nabíjení auta
    'dc8da09248ec1e29': {'x': 580, 'y': 580},  # Nastav global
    'sauna_state_changed': {'x': 140, 'y': 640}, # Změna stavu sauny
    'sauna_set_global':    {'x': 360, 'y': 640}, # Nastav global sauna
}

# Oprav bbox skupiny Exekuce plánu - solar nabijeni je na y:520, node výška ~30px
# bbox musí obsahovat y:520+30=550, skupina začíná na y:279
# h musí být >= 550-279+padding = 271+20 = 291 → zaokrouhlíme na 302
ha_positions['c0d4d6462d4ebded']['h'] = 302  # bylo 242, nestačilo pro y:520

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

changed = 0
for node in d:
    nid = node.get('id', '')
    if nid not in ha_positions:
        continue
    pos = ha_positions[nid]
    for key, val in pos.items():
        if node.get(key) != val:
            node[key] = val
            changed += 1

print(f'Změněno {changed} hodnot')

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: fve-orchestrator.json')

# Ověř
print()
print('=== OVĚŘENÍ ===')
d2 = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))
groups = {n['id']: n for n in d2 if n.get('type') == 'group'}
for gid, g in groups.items():
    gnodes = [n for n in d2 if n.get('g') == gid]
    print(f"Skupina '{g['name']}': x:{g['x']} y:{g['y']} w:{g['w']} h:{g['h']} | {len(gnodes)} nodů")
    for n in gnodes:
        nx, ny = n.get('x', 0), n.get('y', 0)
        in_bbox = (g['x'] <= nx <= g['x']+g['w']) and (g['y'] <= ny <= g['y']+g['h'])
        flag = '' if in_bbox else ' *** MIMO BBOX'
        print(f"  {n.get('name', n.get('type',''))}: x:{nx} y:{ny}{flag}")
