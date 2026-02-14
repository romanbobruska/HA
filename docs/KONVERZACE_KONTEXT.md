# Kontext konverzace — FVE řízení

## Aktuální stav (Session 6, 2026-02-14)

### Hlavní problém
V Normal režimu se občas nabíjí baterie ze solaru a spotřeba jde ze sítě místo z baterie.

### Co bylo opraveno (v kódu, čeká na deploy)

#### Fix 1: fve-modes.json — paralelní Victron service cally
- **Problém**: 5 service callů řetězově (A→B→C→D→E). Pokud jeden selže, zbytek se neprovede.
- **Fix**: Všech 5 módů → Logic funkce posílá na všechny service cally paralelně.
- **Zákaz přetoků**: doplněny 3 chybějící cally (Schedule SOC=0, Schedule Day=-7, MaxDischargePower=0).

#### Fix 2: fve-orchestrator.json — override Normal→Šetřit
- **Problém**: `Kontrola podmínek` (běží každých 15s) overridovala Normal→Šetřit při `cerpadloTopi || autoNabijeni`.
  - Šetřit nastavuje `max_discharge_power=0` + `scheduled_soc=currentSoc` → baterie se nabíjí, spotřeba ze sítě.
  - Feedback loop: override zapisoval "setrit" zpět do `fve_current_mode`, takže i po skončení podmínky zůstalo "setrit" (až 60s).
- **Fix**: `planMode` se čte z `plan.currentMode` (immutable, nastavuje plánovač). Override odstraněn.

### Co ještě NEBYLO nasazeno na HA
**Žádný z fixů nebyl nasazen!** HA stále běží na starém kódu. Uživatel obnovil HA ze zálohy (v9).

### Deploy pravidla
- **NIKDY nerestartovat HA** (`deploy.sh` BEZ `--with-ha`)
- Restartuje se pouze Node-RED
- Cesta k repozitáři na HA: nutno detekovat (`/config/HA` nebo `/homeassistant/HA` nebo `/tmp/HA`)

---

## Architektura FVE řízení

### Klíčové soubory
| Soubor | Účel |
|---|---|
| `fve-orchestrator.json` | Plánovač (1min) + Exekutor (15s) |
| `fve-modes.json` | 5 módů: Normal, Šetřit, Nabíjet, Prodávat, Zákaz přetoků |
| `fve-config.json` | Globální konfigurace (prahy, kapacity, SOC limity) |
| `init-set-victron.json` | VRM API čtení + statistiky (nenastavuje Victron řízení) |
| `fve-heating.json` | Řízení topení/chlazení TČ |
| `filtrace-bazenu.json` | Řízení filtrace bazénu |
| `boiler.json` | Řízení bojleru |

### Flow: Jak se mění Victron nastavení
```
Plánovač (1 min) → fve_plan.currentMode (global)
   ↓
Exekutor (15s) → Kontrola podmínek → Rozhodnutí o akci → Směrování → Link Out
   ↓
FVE Modes → Link In → Logic funkce → 5× paralelní service cally:
   - number.power_set_point
   - number.schedule_charge_duration
   - number.scheduled_soc
   - number.schedule_charge_day
   - number.max_discharge_power
```

### Victron nastavení podle módů
| Parametr | Normal | Šetřit | Nabíjet | Prodávat | Zákaz přetoků |
|---|---|---|---|---|---|
| power_set_point | 0 | 0 | dynamic | dynamic | 0 |
| scheduled_soc | 0 | currentSoc | targetSoc | 0 | 0 |
| schedule_charge_duration | 0 | 86399 | 86399 | 0 | 0 |
| schedule_charge_day | -7 | 7 | 7 | -7 | -7 |
| max_discharge_power | -1 | 0 | 0 | -1 | 0 |

### Normal režim: co SPRÁVNĚ dělá PSP=0
- Solar → spotřeba domácnosti (priorita)
- Solar přebytek → nabíjení baterie (NORMÁLNÍ, ne bug)
- Solar < spotřeba → baterie vybíjí (pokrývá deficit)
- **BUG byl**: override přepnul na Šetřit → baterie se nabíjela na currentSoc, vybíjení zakázáno

---

## Historie sessions

### Session 1-4: Refaktoring, konfigurace, plánování
- Centralizace hardcoded konstant do fve_config
- Opravy plánovače (v13.1): fix expensiveHours solar overlap, double-count

### Session 5: 2026-02-12
- Refaktoring filtrace-bazenu.json (30+ nodes → 19 nodes)
- Fix boiler.json: config → config_fve typo
- Deploy troubleshooting (divergent branches, missing YAML files)

### Session 6: 2026-02-14 (aktuální)
- Fix: paralelní Victron service cally
- Fix: override Normal→Šetřit (root cause nabíjení baterie)
- Fix: deploy_from_scratch.sh bez --with-ha
- TODO: nasadit fixy na HA

---

## Otevřené otázky
1. Je PSP=0 správné chování pro Normal režim? (Solar přebytek nabíjí baterii — je to žádoucí?)
2. Měl by Normal režim umožnit přebytek solaru do sítě místo baterie?
3. Jak se chová Victron ESS když scheduled_soc=0 a schedule_charge_duration=0?
