# Kontext konverzace — FVE řízení

> **⚠️ ZASTARALÝ SOUBOR** — Historický log sessions. Aktuální stav systému je v `docs/PROJEKT_SHRNUTI.md`.
> Požadavky a zákony jsou výhradně v `User inputs/ZAKONY.TXT`.

## Aktuální stav (v19.3, 2026-03-04)

### Nasazené fixy
Všechny fixy jsou nasazeny a ověřeny.

#### v19.3 ŠETŘIT battery discharge fix (2026-03-04)
- **Problém**: Baterie vybíjela ~130W v ŠETŘIT módu při solar=0 (inverter DC bus standby loss)
- **Fix**: `MaxDischargePower = 0` když solar ≤ 10W + `PSP = 150W` (grid bias). Victron transfer relay zajišťuje grid passthrough.
- **Výsledek**: Baterie 0W (dříve -118W)

#### v19.3 Per-hour solar forecast (2026-03-04)
- **Problém**: `forecastPerHour` byla jen ve fallback path, historická data (path 1) běžela první
- **Fix**: `forecastPerHour[hour]` jako PATH 0 (nejvyšší priorita) v `getSolarGainForHour`
- **Výsledek**: h7→h10 SOC realistické (+11% vs starých +29%)

#### v19.3 NIBE heating fix (2026-03-04)
- **Problém**: NIBE nenatápělo nádrž v nejlevnějších hodinách (`isDraha` a `cheaperAhead` blokovali)
- **Fix**: `isDraha` respektuje `planCurrentMode === "setrit"`. `cheaperAhead`/`bigSolarTomorrow` skippovány když plan je `setrit`.

### Deploy pravidla (historický zápis — aktuální stav v `docs/PROJEKT_SHRNUTI.md`)
- Dříve platilo „jen Node-RED“; **`deploy.sh` na `main` nyní výchozí restartuje i Home Assistant Core** (šablony, `input_select`, …). Pro nasazení jen flow bez restartu Core: **`bash deploy.sh --no-ha`**.
- Deploy se spouští klonem do `/tmp/HA` podle § 2.1 v `ZAKONY.TXT`.

---

## Architektura FVE řízení

### Klíčové soubory
| Soubor | Účel |
|---|---|
| `fve-orchestrator.json` | Plánovač (1min) + Exekutor (15s) |
| `fve-modes.json` | 6 módů: Normal, Šetřit, Nabíjet, Prodávat, Zákaz přetoků, Solární nabíjení |
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

### Victron nastavení podle módů (v19.3)
| Parametr | Normal | Šetřit | Nabíjet | Prodávat | Zákaz přetoků | Solární |
|---|---|---|---|---|---|---|
| power_set_point | 0 | gridBias (150W) | dynamic | dynamic | 100 | 0 |
| min_soc | minSoc | minSoc | minSoc | minSoc | minSoc | minSoc |
| schedule_soc | 0 | 0 | targetSoc | 0 | 0 | 0 |
| schedule_charge_duration | 0 | 0 | 86399 | 0 | 0 | 0 |
| schedule_charge_day | -7 | -7 | 7 | -7 | -7 | -7 |
| max_discharge_power | blockDisch? solarPT : -1 | solar>10?max(50,s):0 | 0 | -1 | -1 | blockDisch? solarPT : -1 |
| max_charge_power | blockDisch? 0 : -1 | patBlock? 0 : -1 | -1 | 0 | -1 | patBlock? 0 : -1 |
| feedin_on | true | true | true | true | false | true |

### Normal režim: co SPRÁVNĚ dělá PSP=0
- Solar → spotřeba domácnosti (priorita)
- Solar přebytek → nabíjení baterie (NORMÁLNÍ, ne bug)
- Solar < spotřeba → baterie vybíjí (pokrývá deficit)
- blockDischarge (NIBE/auto/sauna) → `max_discharge_power = solarPassthrough` (0 při solar≤10W)

---

## Historie sessions

### Session 1-4: Refaktoring, konfigurace, plánování
- Centralizace hardcoded konstant do fve_config
- Opravy plánovače (v13.1): fix expensiveHours solar overlap, double-count

### Session 5: 2026-02-12
- Refaktoring filtrace-bazenu.json (30+ nodes → 19 nodes)
- Fix boiler.json: config → config_fve typo
- Deploy troubleshooting (divergent branches, missing YAML files)

### Session 6: 2026-02-14
- Fix 1: paralelní Victron service cally (fve-modes.json)
- Fix 2: override Normal→Šetřit odstraněn (fve-orchestrator.json)
- Fix 3: SOC oscilace v plánovači

### Session 7-9: 2026-02-24 – 2026-03-03
- Wallbox amperáže damping, boiler guard, NIBE v2.3, cenová arbitráž v19.0, feed-in control

### Session 10: 2026-03-04 (aktuální)
- ŠETŘIT MaxDischargePower=0 fix (eliminuje 130W DC bus standby)
- Per-hour solar forecast (forecastPerHour jako PATH 0)
- NIBE heating fix (isDraha respektuje plan setrit)
- Konzistence blokace vybíjení přes všechny módy

---

## Ověřená fakta
- Victron řídící entity (`number.power_set_point` atd.) se nastavují **výhradně** v `fve-modes.json`
- `init-set-victron.json` (1s repeat) zapisuje jen do `input_number.*` (statistiky), ne do Victron řízení
- Žádný jiný flow nemění Victron ESS nastavení
- Všechny módy používají sdílenou grupu "Victron Actions" s fan-out + Mustache templates
- Výchozí mód plánovače je ŠETŘIT (PRIORITA 7), NORMAL jen pro solar/expensive/peak hodiny
- **MaxDischargePower=0 je bezpečné při solar≤10W** — Victron transfer relay zajišťuje grid passthrough
- **PSP > 0** (grid bias) v ŠETŘIT kompenzuje inverter standby (~130W DC bus loss)

## Vyřešené problémy
1. PSP=0 správné pro Normal režim? → ANO, self-consumption
2. scheduled_soc=0 + duration=0? → Scheduling vypnutý
3. MaxDischargePower=0 bezpečné? → ANO při solar≤10W (ověřeno 2026-03-04)
