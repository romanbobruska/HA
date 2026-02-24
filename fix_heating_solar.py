import json

d = json.load(open('node-red/flows/fve-heating.json', encoding='utf-8'))

for n in d:
    if n.get('id') == 'htg_main_func':
        func = n['func']

        # === FIX 1: NIBE - při bigSolarTomorrow netopit za střední ceny ===
        old_nibe = (
            '} else if (needsHeat) {\n'
            '            // Levné/střední hodiny + potřeba topit\n'
            '            if (cheaperAhead && indoorTemp >= safeTemp) {\n'
            '                // Teplota bezpečná + levnější hodiny existují → POČKAT\n'
            '                if (nibeOn && canOffNibe) actions.push("nibe_off");\n'
            '            } else {\n'
            '                // Potřeba topit a nemá smysl čekat\n'
            '                if (!nibeOn) actions.push("nibe_on");\n'
            '            }'
        )
        new_nibe = (
            '} else if (needsHeat) {\n'
            '            // Levné/střední hodiny + potřeba topit\n'
            '            // v2.1: Při velkém solárním forecastu šetříme energii\n'
            '            // → topíme jen pokud teplota klesne pod bezpečný práh (safeTemp)\n'
            '            if (bigSolarTomorrow && indoorTemp >= safeTemp) {\n'
            '                // Velký solar zítra + teplota bezpečná → NIBE OFF, šetříme\n'
            '                if (nibeOn && canOffNibe) actions.push("nibe_off");\n'
            '            } else if (cheaperAhead && indoorTemp >= safeTemp) {\n'
            '                // Teplota bezpečná + levnější hodiny existují → POČKAT\n'
            '                if (nibeOn && canOffNibe) actions.push("nibe_off");\n'
            '            } else {\n'
            '                // Potřeba topit a nemá smysl čekat (nebo teplota pod safeTemp)\n'
            '                if (!nibeOn) actions.push("nibe_on");\n'
            '            }'
        )

        if old_nibe in func:
            func = func.replace(old_nibe, new_nibe)
            print('OK: NIBE - bigSolarTomorrow blokuje topení za střední ceny pokud teplota >= safeTemp')
        else:
            print('WARN: NIBE old string not found')
            # Debug
            idx = func.find('} else if (needsHeat)')
            if idx >= 0:
                print('Found at:', idx)
                print(repr(func[idx:idx+400]))

        # === FIX 2: Oběhové čerpadlo - při bigSolarTomorrow zapnout jen pokud teplota pod safeTemp ===
        old_obeh = (
            'if (tankOk && needsHeat) {\n'
            '                actions.push("obehove_on");\n'
            '            } else {\n'
            '                if (obehOn) {\n'
            '                    actions.push("obehove_off");\n'
            '                }\n'
            '            }'
        )
        new_obeh = (
            'if (tankOk && needsHeat) {\n'
            '                // v2.1: Při velkém solárním forecastu čerpadlo jen pokud teplota pod safeTemp\n'
            '                if (bigSolarTomorrow && indoorTemp >= safeTemp && !isSolarHour) {\n'
            '                    if (obehOn) actions.push("obehove_off");\n'
            '                } else {\n'
            '                    actions.push("obehove_on");\n'
            '                }\n'
            '            } else {\n'
            '                if (obehOn) {\n'
            '                    actions.push("obehove_off");\n'
            '                }\n'
            '            }'
        )

        if old_obeh in func:
            func = func.replace(old_obeh, new_obeh)
            print('OK: Oběhové čerpadlo - bigSolarTomorrow omezuje běh při teplota >= safeTemp')
        else:
            print('WARN: Obehove old string not found')
            idx = func.find('tankOk && needsHeat')
            if idx >= 0:
                print('Found at:', idx)
                print(repr(func[idx:idx+300]))

        n['func'] = func
        break

json.dump(d, open('node-red/flows/fve-heating.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved.')
