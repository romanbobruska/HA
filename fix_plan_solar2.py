import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))

for node in d:
    if node.get('name', '').startswith('Sbírka dat'):
        # Oprav zdroj zbyvajiciSolar - pouzit input_number entity pres HA states
        old = (
            '// v18.20: Solcast forecast jako primární zdroj zbývající výroby dnes\n'
            '// Fallback na VRM API (zbyvajici_solar_dnes) pokud Solcast není dostupný\n'
            'var solcastZbytek = global.get("homeassistant.homeAssistant.states[\'sensor.energy_production_today_remaining_2\']");\n'
            'var solcastZbytekKwh = (solcastZbytek && solcastZbytek.state && !isNaN(parseFloat(solcastZbytek.state)))\n'
            '    ? parseFloat(solcastZbytek.state)\n'
            '    : 0;\n'
            'var zbyvajiciSolar = (solcastZbytekKwh > 0) ? solcastZbytekKwh : (global.get("zbyvajici_solar_dnes") || 0);'
        )
        new = 'var zbyvajiciSolar = global.get("zbyvajici_solar_dnes") || 0;'
        if old in node['func']:
            node['func'] = node['func'].replace(old, new)
            print('OK: Sbírka dat - vráceno na zbyvajici_solar_dnes')
        else:
            print('WARN: Sbírka dat - old Solcast string not found, hledám alternativu')
            # Zkus najít jinou variantu
            idx = node['func'].find('zbyvajiciSolar')
            if idx >= 0:
                print('  Context:', repr(node['func'][max(0,idx-100):idx+200]))

        # Oprav forecastZitra - pouzit input_number.predpoved_solarni_vyroby_zitra
        old2 = 'var forecastZitra = global.get("forecast_vyroba_zitra") || 0;'
        new2 = (
            '// v18.21: Forecast z input_number entit (primární zdroj)\n'
            'var forecastZitraIN = global.get("homeassistant.homeAssistant.states[\'input_number.predpoved_solarni_vyroby_zitra\']");\n'
            'var forecastZitraKwh = (forecastZitraIN && forecastZitraIN.state && !isNaN(parseFloat(forecastZitraIN.state)))\n'
            '    ? parseFloat(forecastZitraIN.state) : 0;\n'
            'var forecastZitra = (forecastZitraKwh > 0) ? forecastZitraKwh : (global.get("forecast_vyroba_zitra") || 0);'
        )
        if old2 in node['func']:
            node['func'] = node['func'].replace(old2, new2)
            print('OK: forecastZitra - pouzit input_number.predpoved_solarni_vyroby_zitra')
        else:
            print('WARN: forecastZitra - old string not found')

        # Oprav zbyvajiciSolar - pouzit input_number.zbyvajici_solarni_vyroba_dnes
        old3 = 'var zbyvajiciSolar = global.get("zbyvajici_solar_dnes") || 0;'
        new3 = (
            '// v18.21: Zbývající výroba z input_number entity (primární zdroj)\n'
            'var zbyvajiciIN = global.get("homeassistant.homeAssistant.states[\'input_number.zbyvajici_solarni_vyroba_dnes\']");\n'
            'var zbyvajiciKwh = (zbyvajiciIN && zbyvajiciIN.state && !isNaN(parseFloat(zbyvajiciIN.state)))\n'
            '    ? parseFloat(zbyvajiciIN.state) : 0;\n'
            'var zbyvajiciSolar = (zbyvajiciKwh > 0) ? zbyvajiciKwh : (global.get("zbyvajici_solar_dnes") || 0);'
        )
        if old3 in node['func']:
            node['func'] = node['func'].replace(old3, new3)
            print('OK: zbyvajiciSolar - pouzit input_number.zbyvajici_solarni_vyroba_dnes')
        else:
            print('WARN: zbyvajiciSolar - old string not found')

        # Oprav forecastDnes - pouzit input_number.predpoved_solarni_vyroby_dnes
        old4 = "dnes: global.get(\"forecast_vyroba_dnes\") || 0"
        new4 = (
            "dnes: (function() {\n"
            "    var dnesIN = global.get(\"homeassistant.homeAssistant.states['input_number.predpoved_solarni_vyroby_dnes']\");\n"
            "    var dnesKwh = (dnesIN && dnesIN.state && !isNaN(parseFloat(dnesIN.state))) ? parseFloat(dnesIN.state) : 0;\n"
            "    return (dnesKwh > 0) ? dnesKwh : (global.get(\"forecast_vyroba_dnes\") || 0);\n"
            "})()"
        )
        if old4 in node['func']:
            node['func'] = node['func'].replace(old4, new4)
            print('OK: forecastDnes - pouzit input_number.predpoved_solarni_vyroby_dnes')
        else:
            print('WARN: forecastDnes - old string not found')
            idx = node['func'].find('forecast_vyroba_dnes')
            if idx >= 0:
                print('  Context:', repr(node['func'][max(0,idx-50):idx+150]))

json.dump(d, open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: fve-orchestrator.json')
