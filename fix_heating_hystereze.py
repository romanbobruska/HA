import json

# ANALÝZA PROBLÉMU:
# Aktuální: needsHeat = indoorTemp < effTarget
#   → NIBE topí kdykoliv teplota klesne pod 22°C (bez hystereze)
#   → Způsobuje krátké cykly a přetápění
#
# Správná termostatová hystereze:
#   - Spustit topení: indoorTemp < (effTarget - BEZPECNY_POKLES) = < 21.3°C
#   - Zastavit topení: indoorTemp >= effTarget = >= 22°C
#
# Implementace: needsHeat závisí na aktuálním stavu NIBE (hystereze)
#   - Pokud NIBE OFF: spustit jen pokud < safeTemp (21.3°C)
#   - Pokud NIBE ON:  vypnout až pokud >= effTarget (22°C)
#
# ZÁROVEŇ: bigSolarTomorrow logika v needsHeat větvi je nyní správná
# (používá safeTemp jako práh = 21.3°C) - to je OK

d = json.load(open('node-red/flows/fve-heating.json', encoding='utf-8'))

for n in d:
    if n.get('id') == 'htg_main_func':
        func = n['func']

        # Oprav needsHeat definici - přidej hysterezi
        old_needs = (
            '        // Podmínky pro topení (sdílené mezi NIBE a oběhovým čerpadlem)\n'
            '        var tankOk = tankTemp >= MIN_TANK;  // horní limit se netýká čerpadla (směšovač zajistí teplotu)\n'
            '        var needsHeat = indoorTemp < effTarget;'
        )
        new_needs = (
            '        // Podmínky pro topení (sdílené mezi NIBE a oběhovým čerpadlem)\n'
            '        var tankOk = tankTemp >= MIN_TANK;  // horní limit se netýká čerpadla (směšovač zajistí teplotu)\n'
            '        // v2.2: Termostatová hystereze 0.7°C\n'
            '        //   NIBE OFF → spustit jen pokud teplota klesla pod (effTarget - BEZPECNY_POKLES)\n'
            '        //   NIBE ON  → vypnout až pokud teplota dosáhla effTarget\n'
            '        var heatThreshold = nibeOn ? effTarget : (effTarget - BEZPECNY_POKLES);\n'
            '        var needsHeat = indoorTemp < heatThreshold;'
        )

        if old_needs in func:
            func = func.replace(old_needs, new_needs)
            print('OK: needsHeat - hystereze 0.7°C přidána')
        else:
            print('WARN: needsHeat old string not found')
            idx = func.find('var needsHeat')
            if idx >= 0:
                print(repr(func[idx-200:idx+100]))

        n['func'] = func
        break

json.dump(d, open('node-red/flows/fve-heating.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
