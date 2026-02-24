import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

for node in d:
    # --- Oprava 1: Sbírka dat - pouzit Solcast jako prioritni zdroj ---
    if node.get('name', '').startswith('Sbírka dat'):
        old = 'var zbyvajiciSolar = global.get("zbyvajici_solar_dnes") || 0;'
        new = (
            '// v18.20: Solcast forecast jako primární zdroj zbývající výroby dnes\n'
            '// Fallback na VRM API (zbyvajici_solar_dnes) pokud Solcast není dostupný\n'
            'var solcastZbytek = global.get("homeassistant.homeAssistant.states[\'sensor.energy_production_today_remaining_2\']");\n'
            'var solcastZbytekKwh = (solcastZbytek && solcastZbytek.state && !isNaN(parseFloat(solcastZbytek.state)))\n'
            '    ? parseFloat(solcastZbytek.state)\n'
            '    : 0;\n'
            'var zbyvajiciSolar = (solcastZbytekKwh > 0) ? solcastZbytekKwh : (global.get("zbyvajici_solar_dnes") || 0);'
        )
        if old in node['func']:
            node['func'] = node['func'].replace(old, new)
            print('OK: Sbírka dat opravena - Solcast jako primární zdroj')
        else:
            print('WARN: Sbírka dat - old string not found')
            print('Looking for:', repr(old[:80]))

    # --- Oprava 2: Výpočet plánu - sanity check limity ---
    if node.get('name', '').startswith('Výpočet plánu'):
        old = 'var monthMaxSolarKwh = [8, 15, 30, 50, 65, 75, 70, 60, 40, 25, 10, 6];'
        new = (
            '// v18.20: Realistická maxima pro 17kWp, az190, sklon45, 50N (Horoušany)\n'
            'var monthMaxSolarKwh = [15, 35, 60, 90, 110, 120, 115, 105, 75, 50, 20, 12];'
        )
        if old in node['func']:
            node['func'] = node['func'].replace(old, new)
            print('OK: Sanity check limity opraveny (únor: 15→35 kWh)')
        else:
            print('WARN: Sanity check - old string not found')
            print('Looking for:', repr(old[:80]))

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: fve-orchestrator.json')
