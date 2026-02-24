import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

# === NOVÝ LAYOUT ===
# Vzor z fve-modes.json a fve-heating.json:
#   - skupiny začínají na x:14, y postupně roste po 200px
#   - nody uvnitř skupiny: x začíná na 140, krok 200px; y = střed skupiny
#   - padding skupiny: 20px od prvního nodu

# --- SKUPINA 1: Plánování ---
# Tok: [inject Každou minutu] + [link in Manuální] → [Sbírka dat] → [Čti ceny z DB] → [Aktualizuj ceny] → [Výpočet plánu]
#       výstup Výpočet plánu → [Ulož plán] → [Aktualizuj HA sensor] → [Zapiš plán do souboru]
#                           → [Plan Debug]
# Řádek 1 (y=80): triggery + hlavní tok výpočtu
# Řádek 2 (y=160): výstupní tok

G1_Y1 = 80   # hlavní tok
G1_Y2 = 160  # výstupní tok

new_positions = {
    # Skupina Plánování - řádek 1
    '22e7b3b8965c20db': (140, G1_Y1),    # Každou minutu
    'f037d87ec94c7da2': (140, G1_Y1+40), # ← Manuální trigger (pod inject)
    '9333668b1d326a83': (360, G1_Y1),    # Sbírka dat pro plánování
    'aabb001122334455': (580, G1_Y1),    # Čti čerstvé ceny z DB
    'aabb001122334466': (800, G1_Y1),    # Aktualizuj ceny v planData
    '9e0b46a9dfedea33': (1020, G1_Y1),   # Výpočet plánu na 12h
    # Skupina Plánování - řádek 2 (výstup)
    'df085ac4da095340': (1020, G1_Y2),   # Ulož plán
    '517215d5f730e80c': (1240, G1_Y2),   # Aktualizuj HA sensor
    '701e94d82c3aead0': (1460, G1_Y2),   # Zapiš plán do souboru
    '39019d1a78677231': (1240, G1_Y1),   # Plan Debug (vedle Výpočet plánu)

    # Skupina Exekuce plánu
    # Řádek 1 (y=300): trigger → kontrola → rozhodnutí → směrování
    # Řádek 2 (y=380): link outy + blokace
    '44d31ff3c04741b7': (200, 300),      # Každých 15 sekund
    'c36915a8599c5282': (400, 300),      # Kontrola podmínek
    '8eef6d1d51c9c644': (600, 300),      # Rozhodnutí o akci
    '19a783a61de3519b': (800, 300),      # Směrování podle módu
    # Link outy - svisle za směrováním
    'f10a91fcb4de6bd3': (1000, 260),     # → Normal
    '7f051a6595e57c3e': (1000, 300),     # → Šetřit
    '185f95d7c56fe799': (1000, 340),     # → Nabíjet
    'a706b353f30c25d1': (1000, 380),     # → Prodávat
    'a86bc5233cfa0458': (1000, 420),     # → Zákaz přetoků
    'solar123456789abc': (1000, 460),    # → Solární nabíjení
    # Blokace - druhý řádek
    'blokace_file_update': (600, 380),   # Aktualizuj blokaci v souboru
    'blokace_file_write':  (800, 380),   # Zapiš blokaci

    # Skupina Kontrola priorit
    # Řádek 1 (y=580): wallbox
    # Řádek 2 (y=640): sauna
    'fc848e97e2c781c1': (200, 580),      # Změna stavu wallboxu
    '376106d716756636': (420, 580),      # Kontrola nabíjení auta
    'dc8da09248ec1e29': (640, 580),      # Nastav global
    'sauna_state_changed': (200, 640),   # Změna stavu sauny
    'sauna_set_global':    (420, 640),   # Nastav global sauna
}

# Aplikuj nové pozice
changed = 0
for node in d:
    nid = node.get('id', '')
    if nid in new_positions:
        nx, ny = new_positions[nid]
        if node.get('x') != nx or node.get('y') != ny:
            node['x'] = nx
            node['y'] = ny
            changed += 1

print(f'Přesunuto {changed} nodů')

# === OPRAV SKUPINY - bbox dle nových pozic ===
NODE_W = 160
NODE_H = 30
PADDING = 30

groups = {n['id']: n for n in d if n.get('type') == 'group'}
nodes_by_group = {}
for n in d:
    if n.get('type') in ('group', 'tab', 'server', 'sqlitedb', 'global-config'):
        continue
    gid = n.get('g', '')
    if gid not in nodes_by_group:
        nodes_by_group[gid] = []
    nodes_by_group[gid].append(n)

for gid, g in groups.items():
    gnodes = nodes_by_group.get(gid, [])
    if not gnodes:
        continue
    min_x = min(n.get('x', 0) for n in gnodes)
    min_y = min(n.get('y', 0) for n in gnodes)
    max_x = max(n.get('x', 0) for n in gnodes)
    max_y = max(n.get('y', 0) for n in gnodes)
    new_x = min_x - PADDING
    new_y = min_y - PADDING
    new_w = (max_x - min_x) + NODE_W + PADDING * 2
    new_h = (max_y - min_y) + NODE_H + PADDING * 2
    print(f"Skupina '{g['name']}': x:{g['x']}->{new_x} y:{g['y']}->{new_y} w:{g.get('w',0)}->{new_w} h:{g.get('h',0)}->{new_h}")
    g['x'] = new_x
    g['y'] = new_y
    g['w'] = new_w
    g['h'] = new_h

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: fve-orchestrator.json')
