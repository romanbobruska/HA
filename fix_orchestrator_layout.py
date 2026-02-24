import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

# ============================================================
# NOVÝ LAYOUT fve-orchestrator.json
# ============================================================
# Vzor z fve-modes.json / fve-heating.json:
#   - Skupiny začínají na x:14, y postupně roste
#   - Nody: absolutní souřadnice, skupina bbox = min/max nodů + padding
#   - Tok zleva doprava, přehledné řádky
#
# SKUPINA 1: Plánování (zelená #e3f3d3)
#   Řádek 1 (y=80):  [Každou minutu] [Manuální] → [Sbírka dat] → [Čti ceny DB] → [Aktualizuj ceny] → [Výpočet plánu] → [Plan Debug]
#   Řádek 2 (y=160): výstup z Výpočtu → [Ulož plán] → [Aktualizuj HA sensor] → [Zapiš plán do souboru]
#
# SKUPINA 2: Exekuce plánu (modrá #d3e8f3)
#   Řádek 1 (y=300): [Každých 15s] → [Kontrola podmínek] → [Rozhodnutí o akci] → [Směrování] → [link outy svisle]
#   Řádek 2 (y=380): [Aktualizuj blokaci] → [Zapiš blokaci]
#
# SKUPINA 3: Kontrola priorit (oranžová #f3e8d3)
#   Řádek 1 (y=540): [Wallbox změna] → [Kontrola nabíjení] → [Nastav global]
#   Řádek 2 (y=600): [Sauna změna] → [Nastav global sauna]
# ============================================================

new_positions = {
    # --- SKUPINA 1: Plánování ---
    # Řádek 1: triggery + hlavní tok
    '22e7b3b8965c20db': (140, 80),     # Každou minutu (inject)
    'f037d87ec94c7da2': (140, 120),    # ← Manuální trigger (link in)
    '9333668b1d326a83': (360, 80),     # Sbírka dat pro plánování
    'aabb001122334455': (580, 80),     # Čti čerstvé ceny z DB
    'aabb001122334466': (800, 80),     # Aktualizuj ceny v planData
    '9e0b46a9dfedea33': (1020, 80),    # Výpočet plánu na 12h
    '39019d1a78677231': (1260, 80),    # Plan Debug
    # Řádek 2: výstupní tok
    'df085ac4da095340': (1020, 160),   # Ulož plán
    '517215d5f730e80c': (1260, 160),   # Aktualizuj HA sensor
    '701e94d82c3aead0': (1500, 160),   # Zapiš plán do souboru

    # --- SKUPINA 2: Exekuce plánu ---
    # Řádek 1: hlavní tok + link outy
    '44d31ff3c04741b7': (140, 300),    # Každých 15 sekund
    'c36915a8599c5282': (360, 300),    # Kontrola podmínek
    '8eef6d1d51c9c644': (580, 300),    # Rozhodnutí o akci
    '19a783a61de3519b': (800, 300),    # Směrování podle módu
    # Link outy - svisle napravo od směrování
    'f10a91fcb4de6bd3': (1020, 260),   # → Normal
    '7f051a6595e57c3e': (1020, 300),   # → Šetřit
    '185f95d7c56fe799': (1020, 340),   # → Nabíjet
    'a706b353f30c25d1': (1020, 380),   # → Prodávat
    'a86bc5233cfa0458': (1020, 420),   # → Zákaz přetoků
    'solar123456789abc': (1020, 460),  # → Solární nabíjení
    # Řádek 2: blokace
    'blokace_file_update': (580, 520), # Aktualizuj blokaci v souboru
    'blokace_file_write':  (800, 520), # Zapiš blokaci

    # --- SKUPINA 3: Kontrola priorit ---
    # Řádek 1: wallbox
    'fc848e97e2c781c1': (140, 640),    # Změna stavu wallboxu
    '376106d716756636': (360, 640),    # Kontrola nabíjení auta
    'dc8da09248ec1e29': (580, 640),    # Nastav global
    # Řádek 2: sauna
    'sauna_state_changed': (140, 700), # Změna stavu sauny
    'sauna_set_global':    (360, 700), # Nastav global sauna
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
    old = f"x:{g['x']} y:{g['y']} w:{g.get('w',0)} h:{g.get('h',0)}"
    new = f"x:{new_x} y:{new_y} w:{new_w} h:{new_h}"
    print(f"Skupina '{g['name']}': {old} -> {new}")
    g['x'] = new_x
    g['y'] = new_y
    g['w'] = new_w
    g['h'] = new_h

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: fve-orchestrator.json')
