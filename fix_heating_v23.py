import json

# PRAVIDLO:
# - targetTemp = input_number.nastavena_teplota_v_dome (např. 22°C)
# - hystereze = 0.7°C = BEZPECNY_POKLES
# - needsHeat = indoorTemp < targetTemp (potřeba tepla)
# - Pokud indoorTemp >= (targetTemp - 0.7) a existuje levnější hodina → počkat
# - Pokud indoorTemp < (targetTemp - 0.7) → topit teď (pod bezpečným prahem)
# - bigSolarTomorrow: zacházet jako s "levnější hodina existuje" → počkat na solar
#
# REVERT: Vrátit needsHeat na původní jednoduchou definici
# FIX: bigSolarTomorrow blokuje topení jen pokud indoorTemp >= safeTemp

d = json.load(open('node-red/flows/fve-heating.json', encoding='utf-8'))

for n in d:
    if n.get('id') == 'htg_main_func':
        func = n['func']

        # Revert needsHeat na původní (bez heatThreshold)
        old_needs = (
            '        // Podmínky pro topení (sdílené mezi NIBE a oběhovým čerpadlem)\n'
            '        var tankOk = tankTemp >= MIN_TANK;  // horní limit se netýká čerpadla (směšovač zajistí teplotu)\n'
            '        // v2.2: Termostatová hystereze 0.7°C\n'
            '        //   NIBE OFF → spustit jen pokud teplota klesla pod (effTarget - BEZPECNY_POKLES)\n'
            '        //   NIBE ON  → vypnout až pokud teplota dosáhla effTarget\n'
            '        var heatThreshold = nibeOn ? effTarget : (effTarget - BEZPECNY_POKLES);\n'
            '        var needsHeat = indoorTemp < heatThreshold;'
        )
        new_needs = (
            '        // Podmínky pro topení (sdílené mezi NIBE a oběhovým čerpadlem)\n'
            '        var tankOk = tankTemp >= MIN_TANK;  // horní limit se netýká čerpadla (směšovač zajistí teplotu)\n'
            '        var needsHeat = indoorTemp < effTarget;'
        )

        if old_needs in func:
            func = func.replace(old_needs, new_needs)
            print('OK: needsHeat reverted na original')
        else:
            print('WARN: needsHeat v2.2 string not found')

        n['func'] = func
        break

json.dump(d, open('node-red/flows/fve-heating.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
