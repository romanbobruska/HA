#!/usr/bin/env python3
"""
deploy_sync_server.py
Spustí se NA SERVERU před deployem.
Načte aktuální flows.json ze serveru, porovná s git verzí a přepíše
git soubory serverovými pozicemi/obsahem — zachová ruční změny uživatele.
"""
import json, os, sys

SKIP_TYPES = {'server', 'global-config', 'sqlitedb', 'config-vrm-api',
              'modbus-client', 'credentials'}

NODERED_FLOWS = '/addon_configs/a0d7b954_nodered/flows.json'
FLOWS_DIR = '/tmp/HA/node-red/flows'

if not os.path.exists(NODERED_FLOWS):
    print('   INFO: ' + NODERED_FLOWS + ' nenalezen, preskakuji sync')
    sys.exit(0)

with open(NODERED_FLOWS, 'r', encoding='utf-8') as f:
    server_all = json.load(f)

srv_tabs = {n['id']: n['label'] for n in server_all if n.get('type') == 'tab'}
srv_by_tab = {}
for n in server_all:
    z = n.get('z', '')
    if z and z in srv_tabs:
        srv_by_tab.setdefault(srv_tabs[z], []).append(n)

updated = 0
for fname in sorted(os.listdir(FLOWS_DIR)):
    if not fname.endswith('.json') or 'server_current' in fname:
        continue
    fpath = os.path.join(FLOWS_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        git_nodes = json.load(f)

    tab = next((n for n in git_nodes if n.get('type') == 'tab'), None)
    if not tab:
        continue
    label = tab['label']

    srv_list = srv_by_tab.get(label, [])
    if not srv_list:
        continue

    # Index server nodu podle jmena+type
    srv_by_key = {}
    for n in srv_list:
        k = n.get('name', n.get('label', '')) + '|' + n.get('type', '')
        srv_by_key[k] = n

    changed = 0
    new_git_nodes = []
    for gn in git_nodes:
        if gn.get('type') in SKIP_TYPES or gn.get('type') == 'tab':
            new_git_nodes.append(gn)
            continue
        k = gn.get('name', gn.get('label', '')) + '|' + gn.get('type', '')
        sn = srv_by_key.get(k)
        if not sn:
            new_git_nodes.append(gn)
            continue

        # Přepiš pozici, rozměry a obsah ze serveru do git verze
        for field in ['x', 'y', 'w', 'h', 'func', 'wires', 'outputs',
                      'entityId', 'entity_id', 'ifState', 'ifStateOperator',
                      'halt_if', 'halt_if_compare', 'halt_if_type',
                      'action', 'payload', 'repeat', 'disabled', 'rules',
                      'outputProperties', 'type']:
            sv = sn.get(field)
            gv = gn.get(field)
            if sv is not None and sv != gv:
                gn[field] = sv
                changed += 1
        new_git_nodes.append(gn)

    # Přidej nové nody které uživatel přidal v NR UI (nejsou v git)
    git_keys = {n.get('name', n.get('label', '')) + '|' + n.get('type', '')
                for n in git_nodes}
    for sn in srv_list:
        if sn.get('type') in SKIP_TYPES:
            continue
        k = sn.get('name', sn.get('label', '')) + '|' + sn.get('type', '')
        if k not in git_keys:
            sn_copy = dict(sn)
            sn_copy['z'] = tab['id']
            new_git_nodes.append(sn_copy)
            changed += 1
            print('   + NOVY NODE v ' + fname + ': ' + sn.get('type','?') + ' \'' + sn.get('name','') + '\'')

    if changed > 0:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(new_git_nodes, f, ensure_ascii=False, indent=4)
        print('   SYNC ' + fname + ': ' + str(changed) + ' zmen ze serveru')
        updated += 1

print('   Sync hotov: ' + str(updated) + ' souboru aktualizovano')
