# FVE Automatizace — Kompletní shrnutí projektu

> Tento dokument slouží jako kontext pro pokračování práce na jiném OS/stroji.
> Poslední aktualizace: 2026-02-15

---

## 1. Přehled systému

Automatizace fotovoltaické elektrárny (Victron), tepelného čerpadla (Nibe), nabíjení elektromobilů a dalších spotřebičů v Home Assistant s Node-RED.

### Hardware
- **Victron GX/Cerbo** — střídač + baterie 28 kWh, komunikace přes MQTT
- **Nibe tepelné čerpadlo** — komunikace přes Modbus (registr 47371 topení, 47372 chlazení, 47387 TUV)
- **2× Wallbox** — garáž + venkovní, ovládání přes HA entity `select.wallboxu_garaz_amperace` / `select.wallbox_venek_amperace`
- **Bojler** — spínání přes HA
- **Bazénová filtrace** — časové řízení
- **Jistič** — 3×32A, max 22 kW ze sítě

### Komunikační vrstvy
```
Victron  ←→  MQTT Broker  ←→  Home Assistant  ←→  Node-RED (flows)
Nibe     ←→  Modbus       ←→  Home Assistant
Wallboxy ←→  WiFi/API     ←→  Home Assistant
Spotové ceny ←→ HTTP API  ←→  SQLite DB  ←→  Node-RED
```

---

## 2. Struktura repozitáře

```
HA/
├── node-red/flows/              # 14 flow souborů (import → merge do flows.json)
│   ├── fve-orchestrator.json        # Plánovač módů (581 řádků hlavní funkce!)
│   ├── fve-modes.json               # Implementace 5 módů (Victron příkazy)
│   ├── fve-config.json              # Konfigurace + cenové prahy + stav
│   ├── fve-heating.json             # Řízení topení/chlazení (Nibe)
│   ├── fve-history-learning.json    # Historické učení (predikce)
│   ├── init-set-victron.json        # Inicializace z Victron VRM API
│   ├── vypocitej-ceny.json          # Výpočet spotových cen (SQLite)
│   ├── manager-nabijeni-auta.json   # Manager nabíjení (rozhodnutí grid/solar)
│   ├── nabijeni-auta-sit.json       # Nabíjení auta ze sítě
│   ├── nabijeni-auta-slunce.json    # Nabíjení auta ze slunce
│   ├── nibe-control.json            # Ovládání Nibe TČ (Modbus)
│   ├── boiler.json                  # Automatizace bojleru
│   ├── filtrace-bazenu.json         # Filtrace bazénu
│   └── ostatni.json                 # Drobné automatizace
├── homeassistant/               # HA YAML konfigurace
│   ├── configuration.yaml
│   ├── automations.yaml
│   ├── mqtt.yaml                    # MQTT entity (Victron, wallboxy)
│   ├── input_numbers.yaml
│   ├── template_sensors.yaml
│   └── template_switches.yaml
├── database/
│   └── schema.sql                   # Tabulka spotových cen
├── docs/
│   ├── UZIVATELSKA_PRIRUCKA.md
│   └── PROJEKT_SHRNUTI.md           # ← TENTO SOUBOR
├── deploy.sh                    # Deploy skript (SSH na HA)
└── README.md
```

---

## 3. Globální proměnné Node-RED

| Proměnná | Zdroj | Popis |
|----------|-------|-------|
| `fve_config` | fve-config.json | Kompletní konfigurace (prahy, kapacita, min SOC, efektivita...) |
| `fve_status` | fve-config.json | Aktuální stav (SOC, ceny, flagy) |
| `fve_prices_forecast` | vypocitej-ceny.json | Tabulka cen z DB. Pole `day`=`"hoursToday"`/`"hoursTomorrow"`, 4 záznamy/hodina (0,15,30,45 min). Klíčová pole: `priceCZKhourBuy`, `levelCheapestHourBuy` |
| `fve_current_price` | vypocitej-ceny.json | Aktuální cena (buy, sell, levelBuy, levelSell) |
| `fve_price_level` | vypocitej-ceny.json | Aktuální cenový level (1–24, čím nižší tím levnější) |
| `fve_plan` | fve-orchestrator.json | Aktuální plán na 12h |
| `fve_current_mode` | fve-orchestrator.json | Aktuální mód |
| `fve_last_full_charge` | fve-orchestrator.json | Datum posledního plného nabití (pro maintenance) |
| `energy_arbiter` | fve-modes.json | Arbitráž energie (mód, spotřebiče, PSP, discharge flag) |
| `auto_nabijeni_aktivni` | manager-nabijeni-auta.json | Flag: nabíjí se auto? |
| `cerpadlo_topi` | fve-heating.json | Flag: topí čerpadlo? |
| `max_spotreba_sit_w` | fve-config.json / init | Max odběr ze sítě (22000 W) |

---

## 4. Klíčové konfigurační parametry (`fve_config`)

| Parametr | Default | Popis |
|----------|---------|-------|
| `kapacita_baterie_kwh` | 28 | Kapacita baterie |
| `min_soc` | 20 | Minimální SOC (%) |
| `max_daily_soc` | 80 | Max SOC pro denní nabíjení (%) |
| `charge_rate_kwh` | 5 | Rychlost nabíjení (kW) |
| `charge_efficiency` | 0.90 | Účinnost nabíjení |
| `discharge_efficiency` | 0.90 | Účinnost vybíjení |
| `amortizace_baterie_czk_kwh` | 1.5 | Amortizace baterie (Kč/kWh) |
| `prah_levna_energie` | 4 | Level pro levnou energii (≤ → nabíjet) |
| `prah_draha_energie` | 12 | Level pro drahou energii (≥ → vybíjet) |
| `max_spotreba_sit_w` | 22000 | Max odběr ze sítě (W) |
| `max_feed_in_w` | 7600 | Max dodávka do sítě (W) |
| `plan_horizon_hours` | 12 | Horizont plánování (h) |
| `soc_drop_normal_pct` | 5 | Pokles SOC za hodinu v Normal (%) |
| `daily_consumption_kwh` | 20 | Denní spotřeba domu (kWh) |

---

## 5. Módy FVE a prioritní systém

### Módy
| Mód | PSP | Scheduled Charge | MaxDischarge | Kdy |
|-----|-----|------------------|--------------|-----|
| **Normal** | 0 | ne | povoleno | Solar hodiny (drahé), drahé hodiny (vybíjení) |
| **Šetřit** | 0 | ne | 0 (zakázáno) | Výchozí mód, šetří baterii |
| **Nabíjet ze sítě** | dynamický | dynamický | 0 | Velmi levná energie |
| **Prodávat** | +maxFeedIn | ne | povoleno | Velmi drahá energie, prodej |
| **Zákaz přetoků** | 0 | ne | povoleno | Dobrá prodejní cena |
| **Solární nabíjení** | 0 | schedule_soc=current | 0 (zakázáno) | Levné solar hodiny (level≤4) |

### Prioritní systém spotřebičů
```
P1: Topení (nekontrolovatelné) — běží vždy
P2: Nabíjení auta — dostane co potřebuje ze sítě
P3: Bojler — dostane zbytek
P4: Baterie — dostane, co zbyde po všech ostatních
```

### Dynamický PSP v režimu Nabíjet
- **Bez high-priority spotřebiče**: scheduled charging zapnuto (SOC=100%, duration=86399s), PSP=-maxGridW → baterie nabíjí max rychlostí
- **S autem/topením**: scheduled charging VYPNUTO (SOC=0, duration=0, day=-7), PSP=+20000W (import). Baterie nabíjí jen z toho, co zbyde po AC zátěžích. Victron service call nody používají **Mustache šablony** (`{{victron.schedule_charge_soc}}` atd.)

---

## 6. Plánovací algoritmus (v13.1)

Soubor: `fve-orchestrator.json`, node `9e0b46a9dfedea33`

### Postup
1. **Načti ceny** z DB (preferuj `hoursToday`, fallback `hoursTomorrow`)
2. **Najdi drahé hodiny** (level ≥ PRAH_DRAHA, **vyloučeny solární hodiny 9–17**)
3. **Finanční smysluplnost** nabíjení (efektivní cena < průměr drahých hodin)
4. **Kolik energie potřebuji?** — safety margin (10–15%), drahé hodiny, maintenance charge (každých 10 dní)
5. **Přiřaď nabíjecí hodiny** — nejlevnější first
6. **Identifikuj solární hodiny** (9–17, pokud zbývá solar forecast)
7. **Identifikuj drahé hodiny** (level ≥ PRAH_DRAHA, mimo solar a charging)
8. **Večerní špička** před nabíjením (vybíjení na minSOC, jen pokud SOC > minSoc+15)
9. **Simulace SOC** pro celý horizont
10. **Výstup**: plán s módym pro každou hodinu + debug info

### Opravené bugy (v13.1)
- **Bug 1**: `expensiveHours` zahrnoval solární hodiny (9–17), kde se baterie NABÍJÍ, ne vybíjí → nadhodnocená potřeba energie
- **Bug 2**: `neededForExpensive = expensiveDrainKwh + totalDrainKwh` double-counting → opraveno na `totalDrainKwh + extraExpensiveDrain`
- **Důsledek**: systém zbytečně nabíjel baterii na 67% místo zachování ~50%

---

## 7. Flow soubory — detailní popis

### fve-orchestrator.json (29 nodes, 8 functions)
- **Trigger**: inject každých 15 min + HA state change
- **Sbírka dat**: čte config, status, ceny, solar forecast
- **Výpočet plánu**: 581 řádků JS → 12h plán s módy
- **Ulož plán**: do global + HA sensor `sensor.fve_plan`
- **Kontrola podmínek**: každých 15s kontroluje aktuální mód a spouští odpovídající mode flow
- **Předává `msg.autoNabijeniAktivni` a `msg.cerpadloTopi`** do mode flows

### fve-modes.json (45 nodes, 5 functions + 22 service calls)
- 5 módů, každý: link in → function → service calls (PSP, MinSOC, ScheduleSOC, MaxDischargePower...)
- Nabíjet Logic: dynamický PSP a scheduled charging dle priorit
- Šetřit Logic: consumer info v energy_arbiter
- Všech 5 módů nastavuje global `energy_arbiter`

### fve-config.json (25 nodes, 4 functions)
- Načítá konfiguraci z HA entit
- Zpracovává ceny z DB
- Aktualizuje `fve_status` global

### vypocitej-ceny.json (55 nodes, 10 functions)
- Stahuje spotové ceny z API
- Ukládá do SQLite (`own_energy_prices_total`)
- Počítá levely pomocí SQL `PARTITION BY day ORDER BY price`
- **Duplicity**: 2× "Sestav insert", 2× "Počkej, až skončí insert" (různý kód!)

### nabijeni-auta-sit.json (29 nodes)
- "Vypočítej max amperaci": `headroom = SAFE_LIMIT - celkova_spotreba`
- `SAFE_LIMIT = max_spotreba_sit_w - 2000` (safety margin)
- Ampéry: `Math.floor(headroom / 230 / 3 + charger_amps)`

### nabijeni-auta-slunce.json (26 nodes)
- Obdobná logika jako sit, ale pro solární nabíjení
- **Duplikát**: funkce "Vypočítej max amperaci" v obou souborech

### boiler.json (28 nodes)
- Rozhodovací logika: `volna_kapacita_site = max_spotreba_sit - celkova_spotreba`
- SAFETY_MARGIN = 2000 W (stejná konstanta jako v nabijeni-auta)

### fve-heating.json (25 nodes)
- Rozhodnutí topení/chlazení na základě teploty, cen, SOC
- Detekce topení vs chlazení (Nibe stavy)

### nibe-control.json (19 nodes)
- Modbus zápis: topení (47371), chlazení (47372), TUV (47387)
- **Poznámka**: Registr 47041 (Hot water comfort mode) je ve skutečnosti pro vytápění bazénu. Hodnoty: 0=Ekonomický (5°C), 1=Normální (6°C), 2=Luxusní (50°C), 4=Smart Control

### init-set-victron.json (42 nodes)
- Načítá data z Victron VRM API
- Nastavuje globální proměnné (spotřeba, výroba, SOC...)
- **Duplikát**: funkce "Má se spustit?" (stejná i ve vypocitej-ceny.json)

---

## 8. Identifikované duplicity a problémy

### Duplicitní názvy funkcí
| Název | Soubory | Poznámka |
|-------|---------|----------|
| "Vypočítej max amperaci" | nabijeni-auta-sit, nabijeni-auta-slunce | Podobná logika, mírně odlišná |
| "Má se spustit?" | init-set-victron, vypocitej-ceny | Obdobná guard logika |
| "Sestav insert" | 2× ve vypocitej-ceny | Různý kód (43 vs 21 řádků) |
| "Počkej, až skončí insert" | 2× ve vypocitej-ceny | Různý kód (9 vs 10 řádků) |

### Opakující se vzory
- `global.get("fve_config")` — ve **14 funkcích** napříč 8 flow soubory
- `global.get("fve_status")` — v **7 funkcích**
- `SAFETY_MARGIN = 2000` — hardcoded ve 3 funkcích (boiler, nabijeni-auta-sit, fve-modes)
- `max_spotreba_sit` — čteno v 7 funkcích, z configu i přímo z globálu

### Potenciální refaktoring
1. **SAFETY_MARGIN** → přesunout do `fve_config` jako konfigurační parametr
2. **"Vypočítej max amperaci"** → sdílená funkce (link in/out nebo subflow)
3. **"Má se spustit?"** → sjednotit guard logiku
4. **vypocitej-ceny.json** → odstranit duplicitní "Sestav insert" a "Počkej" nody
5. **energy_arbiter** boilerplate v 5 mode funkcích → standardizovat

---

## 9. Deploy postup

### Automatický (SSH na HA)
```bash
curl -sL https://raw.githubusercontent.com/romanbobruska/HA/main/deploy.sh | bash
# nebo s restartem HA:
curl -sL https://raw.githubusercontent.com/romanbobruska/HA/main/deploy.sh | bash -s -- --with-ha
# nebo z jiné branch:
curl -sL https://raw.githubusercontent.com/romanbobruska/HA/main/deploy.sh | bash -s -- --branch=refactoring
```

### Manuální
```bash
cd /tmp && git clone https://github.com/romanbobruska/HA.git
ha apps stop a0d7b954_nodered 2>/dev/null || ha addons stop a0d7b954_nodered
# Merge flows do jednoho flows.json (Python skript v deploy.sh)
cp /tmp/HA/homeassistant/*.yaml /config/
ha apps start a0d7b954_nodered 2>/dev/null || ha addons start a0d7b954_nodered
rm -rf /tmp/HA
```

### Klíčové cesty na HA
- Node-RED flows: `/addon_configs/a0d7b954_nodered/flows.json`
- HA config: `/config/`
- SQLite DB: `/homeassistant/home-assistant_v2.db`

---

## 10. Historie změn (sessionové opravy)

### Session 1: Grid overload protection
- **Problém**: Odběr 28 kW ze sítě, riziko pádu jističe
- **Oprava**: Přechod z `spotreba_ze_site` na `celkova_spotreba` (sensor.celkova_spotreba) + safety margin 2000 W
- **Soubory**: nabijeni-auta-sit.json, boiler.json

### Session 2: Priority system (auto > baterie)
- **Problém**: Baterie se nabíjela max rychlostí, auto omezeno na 8A
- **Příčina**: Scheduled charging v Victronu přepisuje PSP
- **Oprava**: V Nabíjet Logic — při aktivním autu/topení: vypnout scheduled charging, PSP=+20kW (import). Mustache šablony v service callech.
- **Soubory**: fve-modes.json

### Session 3: Plan SOC target
- **Problém**: Plán cílil na SOC 67% místo ~50%
- **Příčina 1**: `expensiveHours` zahrnoval solární hodiny (9–17) → nadhodnocený drain
- **Příčina 2**: `neededForExpensive` double-counting (expensiveDrain + totalDrain)
- **Oprava**: Vyloučit solární hodiny z expensive filtr + opravit výpočet na `totalDrainKwh + extraExpensiveDrain`
- **Soubory**: fve-orchestrator.json (v13.1)

### Session 4: Refaktoring (branch `refactoring` → merged do `main`)
- **Změny**:
  - `fve-config.json`: nové config parametry `safety_margin_w`, `solar_start_hour`, `solar_end_hour`, `soc_drop_setrit_pct`
  - `boiler.json`, `nabijeni-auta-sit.json`, `fve-modes.json`: SAFETY_MARGIN čte z configu místo hardcoded 2000
  - `nabijeni-auta-slunce.json`: přechod z `global.get("max_spotreba_sit")` na `fve_config.max_spotreba_sit_w`
  - `fve-orchestrator.json`: `solarStartHour`, `solarEndHour`, `socDropSetrit` čtou z configu
  - `vypocitej-ceny.json`: přejmenované duplicitní funkce ("Sestav insert" → "ceny_total"/"ceny_raw")
  - `fve-modes.json`: standardizovaný `energy_arbiter` se `consumers_active` ve všech 5 módech
- **Soubory**: 7 flow souborů

### Session 5: 2026-02-12
- **Merge refactoring** do main + push na GitHub
- **Baterie na 70%**: pravděpodobně starý kód na HA (v13.1 fix nebyl nasazen) — vyřeší deploy
- **Vytápění TČ**: analyzována logika fve-heating.json, čeká na runtime data
- **Refaktoring filtrace-bazenu.json**:
  - 30+ nodes (spaghetti z moment, time-range-switch, duplicitních service callů) → 19 nodes
  - 1 rozhodovací funkce "Rozhodnutí filtrace" (121 řádků, 4 výstupy)
  - Odstraněno: 4× duplicitní "Filtrace ON", 2× "Je letní režim?", 5× moment node, 2× "Rozdíl výroby > 3kW?"
  - Zachována identická logika: stejná časová okna, prahy, podmínky
  - Timezone-safe (Europe/Prague via Intl)
  - Nepotřebuje `node-red-contrib-moment` ani `node-red-contrib-time-range-switch`

### Session 6: 2026-02-14
- **Problém**: V režimu Normal solární výroba nabíjela baterii a spotřeba šla ze sítě
- **Příčina**: Sekvenční řetězení Victron service callů — pokud jeden selže, zbytek se neprovede.
  Po přechodu Šetřit→Normal zůstaly na Victronu staré nastavení (scheduled_soc, max_discharge_power=0).
- **Fix fve-modes.json** — paralelní service cally:
  - Všech 5 módů: Logic funkce → ALL service cally paralelně (ne řetězově)
  - Pokud jeden service call selže, ostatní se stále provedou
  - Při dalším 15s cyklu se neúspěšný call zopakuje
- **Fix Zákaz přetoků** — doplněny 3 chybějící service cally:
  - Schedule SOC = 0, Schedule Day = -7, MaxDischargePower = 0
  - Předtím měl jen 2 ze 5 potřebných nastavení
- **HA obnovena ze zálohy** (v9 → v13.1 přes deploy.sh)
- **Fix fve-orchestrator.json** — root cause nabíjení baterie v Normal režimu:
  - Bug 1: Override feedback loop — `Kontrola podmínek` přepisovala `fve_current_mode` overridnutým módem,
    další 15s cyklus četl "setrit" místo plánovaného "normal" (až 60s do resetu plánovačem)
  - Bug 2: Override Normal→Šetřit při běhu čerpadla/auta — Šetřit nastavil `max_discharge_power=0`
    a `scheduled_soc=currentSoc`, čímž solar nabíjel baterii a spotřeba šla ze sítě
  - Fix: planMode se čte z `plan.currentMode` (immutable), override odstraněn
  - Jednotlivé módy (Nabíjet) již interně řeší high-priority consumers
- **Fix fve-orchestrator.json** — SOC oscilace v plánovači (~5 min přerušení vybíjení):
  - Bug 3: PRIORITA 3 (`simulatedSoc <= minSoc + 3` → Šetřit) způsobovala oscilaci:
    Normal → baterie vybíjí → SOC klesne pod práh → Šetřit (max_discharge=0) →
    solar trochu nabije → SOC stoupne → Normal → opakuj (~5 min cyklus)
  - Bug 4: Solar offsets se vytvořily jen když `remainingSolarKwh > 0` —
    odpoledne s 0 zbývajícím forecastem → hodina NENÍ solární → default Šetřit
  - Fix KROK 6: Solar offsets vždy pro hodiny v solárním okně (9-17)
  - Fix PRIORITA 3: Během solárních hodin ochrana baterie jen při absolutním minSoc

### Session 7: 2026-02-15
- **Problém 1**: minSOC stále osciloval (19%), přestože předchozí fixy měly zamknout na 20%
- **Root cause minSOC**:
  - `fve-config.json` četl `input_number.fve_min_soc` z HA → `config.min_soc`
  - HA automatizace/skripty měnily input_number → config se aktualizoval
  - `fve-modes.json` Nabíjet Logic používal `config.min_soc` (dynamické čtení)
- **Fix minSOC** (2 commits):
  - `fve-config.json`: Odstraněn case pro `input_number.fve_min_soc` → config IGNORUJE HA změny
  - `fve-modes.json`: Nabíjet Logic používá lokální `var minSoc = config.min_soc || 20` (read once)
  - Výsledek: minSOC natvrdo 20%, ŽÁDNÉ externí změny možné
- **Problém 2**: Baterie se nenabíjela v nejlevnějších hodinách (12:00 level 2, 14:00 level 1)
- **Root cause nabíjení**:
  - KROK 4 ochranné nabíjení: `targetSocFromGrid = 27%` (jen 1 hodina)
  - KROK 5 opportunistická logika: `if (gridChargeNeeded === 0 && ...)` → přeskočeno (gridChargeNeeded=1.9)
  - KROK 7 PRIORITA 1: `if (simulatedSoc < targetSocFromGrid)` → 27 < 27 = false → mode=setrit
- **Fix opportunistické nabíjení**:
  - KROK 5: `if (currentSoc < optimalSoc && targetSocFromGrid < optimalSoc)` — funguje i s aktivním ochranným nabíjením
  - Zvyšuje `targetSocFromGrid` z 27% na 60-80%, přiřadí více levných hodin (~8 místo 1)
  - Výsledek: Baterie se nabije na optimální SOC v levných hodinách
- **Nový mód**: SOLAR_CHARGING (per user request)
  - **Účel**: Ochrana baterie během levných solárních hodin
  - **Aktivace**: `level <= prah_levna_energie` AND solární výroba (9-17h)
  - **Chování**: Baterie může nabíjet ze solaru, ale NEMŮŽE vybíjet. Pokud spotřeba > výroba → dovoz ze sítě
  - **Implementace**:
    - `fve-orchestrator.json`: Přidán `MODY.SOLAR_CHARGING`, KROK 7 PRIORITA 4 rozlišuje levné/drahé solární hodiny
    - `fve-orchestrator.json`: Switch node rozšířen na 6 výstupů (modeIndex=5)
    - `fve-modes.json`: Nová group "Solární nabíjení Logic" s Victron nastavením:
      - `schedule_soc: currentSoc` (zamkne SOC, zabrání vybíjení)
      - `power_set_point: 0` (ESS řídí, povolí nabíjení ze solaru)
      - `energy_arbiter`: `battery_discharging: false`
  - **Výsledek**: Během levných solárních hodin baterie chráněna, deficit ze sítě

### Session 8: 2026-02-16
- **Problém 1**: Baterie se vybíjela při topení čerpadlem (porušení historického požadavku)
- **Fix**: `fve-modes.json` Normal Logic — `blockDischarge = cerpadloTopi || autoNabijeniAktivni`
  - `max_discharge_allowed: !blockDischarge` v energy_arbiter
  - `msg.maxDischargePower = blockDischarge ? 0 : -1` → dynamický MaxDischargePower node
- **Problém 2**: Při drahých cenách (level > 12) se šetřila baterie při SOC 25%
- **Root cause**: Podmínka `simulatedSoc > minSoc + 5` → 25 > 25 = false → ŠETŘIT místo NORMAL
- **Fix**: Odstraněn margin `minSoc + 5`, nahrazen `minSoc` (vybíjení až do minSoc)
- **Problém 3**: minSoc hardcoded na 20%, ignorovalo se `number.min_soc` z HA
- **Fix**: `fve-config.json` Zpracuj HA stavy — odkomentován case pro `number.min_soc`
  - minSoc nyní dynamicky čte z HA entity

### Session 9: 2026-02-17 — Hloubková analýza + 4 kritické opravy
- **Hloubková analýza**: Kompletní audit PROJEKT_SHRNUTI.md + kódu všech relevantních flows
- **BUG 1 (KRITICKÝ)**: Baterie přestala nabíjet když se začalo nabíjet auto
  - **Root cause**: Nabíjet Logic vypínal scheduled charging při aktivním autu/čerpadle
    - `schedule_charge_soc: 0`, `duration: 0`, `day: -7` → Victron nenabíjí baterii z gridu
    - PSP = +20000W jen povolí import, ale bez scheduled charging baterie nic nedostane
    - Po skončení auta je levná hodina pryč → baterie se nikdy nenabije
  - **Fix**: `fve-modes.json` Nabíjet Logic — scheduled charging VŽDY zapnuté
    - Odstraněn if/else branch pro high-priority consumers
    - Baterie i auto se nabíjejí současně v rámci limitu sítě
  - **Fix**: `nabijeni-auta-sit.json` — headroom počítá s nabíjením baterie
    - Čte `energy_arbiter.battery_charging` a odečítá `charge_rate_kwh * 1000`
    - Zabraňuje přetížení sítě když se současně nabíjí auto i baterie
- **BUG 2 (KLARIFIKACE)**: Solar při topení/nabíjení auta
  - Implementace je SPRÁVNÁ (PSP=0, max_discharge=0)
  - Solar pokrývá spotřebu ✅, přebytek nabíjí baterii ✅, deficit ze sítě ✅
- **BUG 3 (REGRESE)**: cheapHours filter v KROK 5 nefungoval
  - `hp.day === "hoursToday"` ale hourPrices nemá field `day` → vždy undefined
  - cheapHours byl VŽDY prázdný → KROK 5 opportunistické nabíjení nikdy nefungovalo
  - **Fix**: Nahrazeno `(currentHour + hp.offset) < 24` (offset-based day check)
- **BUG 4 (DESIGN)**: optimalSoc byl statický (minSoc + 40 = 60%)
  - Nepočítal s počtem drahých hodin, spotřebou, solarem
  - Poslední 2 dny baterie došla dříve → drahá energie ze sítě
  - **Fix**: Dynamický výpočet: `minSoc + ceil(baseDrain + expensiveDrain - solarContrib) + safetyMargin`
    - Více drahých hodin = vyšší target SOC
    - Více solaru = nižší target SOC (šetří peníze)
- **Planner verze**: v13.1 → v14.0
- **Soubory**: fve-modes.json, nabijeni-auta-sit.json, fve-orchestrator.json

### Session 9 (pokračování): Přepis logiky topení v2 s debug logováním
- **Problém**: Předehřev čerpadla nefungoval - čerpadlo bylo blokované
- **Analýza**: Důkladná analýza celého flow řetězce (inject → 7x api-current-state → rozhodnutí → switch → akce)
  - Propojení nodů je správné
  - Logika rozhodování byla zjednodušena ale bez diagnostiky
  - Bez debug logování nelze identifikovat runtime příčinu blokování
- **Fix v2**: `fve-heating.json` Rozhodnuti topeni/chlazeni — kompletní přepis s debug logováním
  - **Strict boolean**: `config.letni_rezim === true` (místo `|| false` — truthy check)
  - **Default price level**: 99 (blokovat) pokud ceny nenalezeny, pak fallback na 1
  - **isDraha flag**: `currentPriceLevel >= PRAH_DRAHA` pro jasnou logiku
  - **node.warn()**: Každý cyklus loguje VŠECHNY rozhodovací proměnné do Node-RED debug sidebar:
    - action, reason, režim, temp, venku, level, PRAH_DRAHA, isDraha, switch stav, pump stav, kompresor, krb, priceFound, prices.length
  - **Logika** (zimní režim):
    - Nouzové (temp ≤ 22°C): VŽDY zapnout
    - Levné + střední (level < PRAH_DRAHA): VŽDY zapnout při temp < 23.5°C
    - Drahé (level ≥ PRAH_DRAHA): BLOKOVÁNO (jen nouzové)
  - **Každá větev** má explicitní reason text
- **Výsledek**: Po deployi bude v Node-RED debug sidebar vidět přesně proč je topení ON/OFF/BLOKOVÁNO
- **Fix v3** (po debug logu z runtime):
  - Debug log ukázal: `HEATING: none | Teplota OK (23.5°C >= 23.5°C) | Lv=9 (PRAH=12)`
  - **BUG 1**: `temp < TEMP_TARGET` → `23.5 < 23.5 = false` → topení se nezapne. Fix: `temp <= TEMP_TARGET`
  - **BUG 2**: `PRAH_DRAHA = config.prah_draha_energie || 12` — špatný práh!
    - `levelCheapestHourBuy` je rank per day (1-24), ne globální level
    - Uživatel: prah pro topení je 9 (9 nejlevnějších hodin = topení, 15 nejdražších = blokovat)
    - Fix: `PRAH_DRAHA = config.prah_draha_topeni || 9` — nový config parametr
  - Přidán `prah_draha_topeni: 9` do default configu v `fve-config.json`
- **Fix v4** (po dalším debug logu z runtime):
  - Debug log: `HEATING: none | Čekám na interval (180s) | Lv=9 (PRAH=9) | isDraha=true | switch=OFF`
  - **BUG KRITICKÝ**: Čerpadlo bylo vypnuto během provozu → může zničit kompresory!
    - Ochrana čerpadla kontrolovala stav, ale nebyla dostatečně přísná
    - Fix: **ABSOLUTNÍ ochrana** — NIKDY nevypnout pokud `pumpRealState` není "Klidový"
    - Kontroluje `pumpIsWorking = !pumpIsIdle && pumpRealState !== ""`
    - Loguje `node.warn()` při každém blokování
  - **BUG**: `isDraha = currentPriceLevel >= PRAH_DRAHA` → `9 >= 9 = true` → blokováno!
    - Fix: `isDraha = currentPriceLevel > PRAH_DRAHA` (level 9 při prahu 9 = povoleno)
  - **BUG**: Při topení čerpadlem se baterie nabíjela místo aby solár pokryl spotřebu
    - Root cause: `schedule_soc: currentSoc` v módech zamkne SOC → solár jde do baterie
    - Fix v `fve-modes.json` — všechny módy:
      - **Normal**: žádný `schedule_soc`, PSP=0, ESS řídí tok (solár→spotřeba→přebytek→baterie)
      - **Šetřit**: žádný `schedule_soc` lock při aktivním čerpadle/autu
      - **Solární nabíjení**: žádný `schedule_soc` lock při aktivním čerpadle/autu
      - **Nabíjet**: `safeImport = maxGrid - safetyMargin` při aktivním čerpadle/autu
    - Výsledek: solární energie se použije na spotřebu, přebytek do baterie, deficit ze sítě
- **Fix v6 (FINÁLNÍ)** — topení VŽDY ON při level < 12, baterie zamčená při topení:
  - **Topení** (`fve-heating.json`):
    - Používá existující `prah_draha_energie: 12` z configu (smazány vlastní prahy)
    - Level < 12: čerpadlo **VŽDY ON bez ohledu na teplotu**
    - Level >= 12: **BLOKOVÁNO** (jen nouzové pod 22°C)
    - Žádné teplotní kontroly pro levné/střední ceny
  - **Baterie** (`fve-modes.json`):
    - Problém: `schedule_soc = 0` v Normal mode → ESS normálně nabíjí baterii ze solaru
    - Fix: Při topení čerpadlem `schedule_soc = currentSoc` (zamknout baterii)
    - Opravena HA node "Schedule SOC" v Normal mode: hardcoded 0 → `{{victron.schedule_soc}}`
    - Solár → spotřeba (čerpadlo), přebytek → síť (prodej), deficit → síť (import)
    - Baterie se NENABÍJÍ ani NEVYBÍJÍ při topení
  - **Config** (`fve-config.json`): Smazány `prah_levna_topeni`, `prah_draha_topeni`
- **Fix v7** — Solární nabíjení mód neměl HA service nodes:
  - **Root cause**: Funkce nastavila `msg.victron.schedule_soc = currentSoc`, ale link out měl `links: []` → výstup šel **nikam** → ESS zůstával v předchozím stavu → baterie se nabíjela ze solaru
  - Fix: Přidáno 5 HA service nodes do skupiny Solární nabíjení:
    - `Set Power Point = 0`, `Schedule SOC = {{victron.schedule_soc}}` (lock)
    - `Schedule Duration = 0`, `Schedule Day = -7`, `Max Discharge Power = 0`
  - Výsledek: Solár → spotřeba, přebytek → síť (prodej), baterie zamčená
- **Fix v8** — plán vybíjí při levných cenách + baterie se stále nabíjí ze solaru:
  - **Plán** (`fve-orchestrator.json` v15.0):
    - `peakDischargeOffsets` vybíjel baterii na minSOC **bez ohledu na cenu** (i při 3.52 Kč)
    - Fix: peakDischarge POUZE při drahých cenách (`levelBuy >= PRAH_DRAHA`)
    - Levné/střední hodiny → Šetřit (výchozí mód)
  - **Baterie** (`fve-modes.json`):
    - **Root cause**: Victron ESS **IGNORUJE** `scheduled_soc` když `schedule_charge_duration=0`!
    - Fix: Při zamykání baterie aktivovat scheduled charging:
      - `schedule_charge_duration: 86399`, `schedule_charge_day: 7`, `scheduled_soc: currentSoc`
    - Při normálním provozu (bez topení): `duration: 0`, `day: -7`, `soc: 0`
    - Opraveny HA nodes v Normal/Šetřit/Solar: Schedule Duration a Day nyní **dynamické**
  - **Nový komunikační mód**: zakázáno měnit předchozí požadavky, max 1 dotaz po analýze
- **v16.0 — Dynamický práh vybíjení** (`fve-orchestrator.json`):
  - Uživatel explicitně změnil požadavek: baterie se má vybíjet i při středních cenách pokud kapacita stačí
  - Config prahy (`PRAH_LEVNA=4`, `PRAH_DRAHA=12`) **beze změny**
  - Nový algoritmus:
    1. Spočítá energetický budget: `(currentSoc - minSoc) * kapacita * efficiency`
    2. Seřadí ne-solární, ne-nabíjecí hodiny od **nejdražšího levelu dolů**
    3. Přidává hodiny do Normal (vybíjení) od nejdražších dolů
    4. Zastaví se když budget vyčerpán
    5. `effectiveThreshold` se automaticky snižuje (12 → 9 → 5...)
  - Odstraněn `peakDischargeOffsets` (nahrazen dynamickým prahem)
  - Výsledek: čím větší výroba/kapacita → nižší práh → více Normal → méně odběr ze sítě
  - Debug výstup: `dischargeDebug` s detaily pro každou hodinu
- **v16.1 — Solární nabíjení má VŽDY přednost** (`fve-orchestrator.json`):
  - **Problém**: targetSocFromGrid=71%, ale zítra ~20 kWh solární výroby → zbytečné nabíjení ze sítě
  - **Root cause**: `targetSocFromGrid` nezohledňoval zítřejší solární předpověď
  - Fix:
    - `solarCoversConsumption = forecastZitra >= 70% dailyConsumption`
    - Pokud solár pokryje: **žádné nabíjení ze sítě** (baterie se dobije solarem zadarmo)
    - Pokud SOC klesne pod `minMorningSoc`: nabít jen na minimum
    - Pokud solár nestačí: nabít ze sítě jen **deficit** (snížený o solární přebytek)
    - Opportunistické nabíjení **blokováno** při dobré solární předpovědi
    - Safety margin: 5% (dobrý solár), 10% (střední), 15% (špatný)
  - Nové proměnné: `solarChargePct`, `expensiveBeforeSolar`, `minMorningSoc`
- **v17.0 — Přesné nabíjení + dynamické solární hodiny** (`fve-orchestrator.json`):
  - **Problém 1**: Baterie se nabíjí ze sítě na 52%, ale SOC 42% stačí na 3 drahé hodiny (15% drain → 27% > 25%)
    - **Root cause**: `projectedEndSoc = currentSoc - horizont*socDropSetrit` je ŠPATNĚ — v Šetřit se SOC nemění!
    - Fix: `realDrain = drahé hodiny PŘED solarem × socDropNormal`
    - Nabíjet ze sítě JEN pokud `currentSoc - drain < minSoc + safety`
    - Výsledek: baterie často blízko minSoc před solárním nabíjením
  - **Problém 2**: Hardcoded `solar_start_hour=9`, `solar_end_hour=17`
    - Fix: Čtení z HA entit `sensor.sun_next_rising` / `sensor.sun_next_setting`
    - Parsování hodiny z ISO datetime, fallback na config
    - Přidáno do "Sbírka dat pro plánování" node
  - **Problém 3**: Maintenance charge příliš častý
    - Změna: 10 → **20 dní**, pouze v **zimě** (říjen-březen)
    - V létě solár udržuje baterii zdravou přirozeně
- **v18.0 — MaxChargePower + zamčení baterie při topení/nabíjení auta** (`fve-modes.json`, `mqtt.yaml`):
  - **Problém**: Baterie se nabíjela ze solaru i při topení/nabíjení auta (MaxDischargePower=0 nestačí)
  - **Root cause**: Chyběla MQTT entita `MaxChargePower` — bez ní Victron ESS nabíjí baterii ze solaru
  - Fix:
    - Přidána MQTT entita `number.max_charge_power` (`Settings/CGwacs/MaxChargePower`)
    - 6 nových HA service nodes v `fve-modes.json` (jeden pro každý mód)
    - Normal (topení/auto): `MaxChargePower=0` + `MaxDischargePower=0` → baterie zamčená
    - Normal (bez spotřebičů): `MaxChargePower=-1` + `MaxDischargePower=-1` → neomezeno
    - Šetřit: `MaxChargePower=0` + `MaxDischargePower=0` → baterie zamčená
    - Nabíjet ze sítě: `MaxChargePower=-1` + `MaxDischargePower=0` → nabíjení povoleno
    - Prodávat: `MaxChargePower=0` + `MaxDischargePower=-1` → jen vybíjení
    - Zákaz přetoků: `MaxChargePower=-1` + `MaxDischargePower=-1` → baterie neomezena (řídí se feed-in)
    - Solární nabíjení: `MaxChargePower=-1` + `MaxDischargePower=0` → solár nabíjí baterii, nevybíjí se
  - Výsledek: Solár → spotřeba (čerpadlo/auto), přebytek → baterie nebo síť dle módu
  - Odstraněny `node.warn` debugy z `fve-heating.json` (použít debug nodes místo toho)

### v18.1 — Dynamická solární predikce z historie
- Problém: Plánovač používal konstantní `solarGainEst = 3 kWh` pro každou solární hodinu
  - Výsledek: SOC +3% každou hodinu bez ohledu na reálnou výrobu a spotřebu
  - Plán ukazoval nerealistické SOC odhady (např. 29% → 56% za 9 solárních hodin)
- Fix:
  - **fve-history-learning.json**: Rozšířen sběr dat o hodinovou výrobu a spotřebu
    - `Sbírka aktuálních dat (v18)`: Počítá delta za hodinu z kumulativních Victron dat
    - `Uložit do historie (v18)`: Ukládá `avgSolarKwh`, `avgConsumptionKwh`, `avgSurplusKwh` per hodinu
    - `Výpočet predikce (v18)`: Generuje `netSolarGainKwh` per hodinu (výroba - spotřeba)
    - `Analýza vzorců (v18)`: Přidány `solarPattern`, `consumptionPattern`, `surplusPattern`
  - **fve-orchestrator.json**: Plánovač v18.0
    - Nová funkce `getSolarGainForHour(hour, remainingSolar, solarHours)`:
      - Pokud historie >= 3 vzorky: použije `netSolarGainKwh` z predikce
      - Fallback: rovnoměrné rozdělení `remainingSolarKwh / solarHoursCount - avgHourlyConsumption`
    - Odstraněn hardcoded `soc + 3` v `simulateSocChange()`
    - Odstraněn hardcoded `solarGainEst = 3` v `calculateModeForHour()`
  - **Modbus**: Přidán sensor `Nibe - Degree Minutes` (registr 43005, 16bit, scale 0.1)
    - Entita: `sensor.nibe_degree_minutes`
    - Template sensor: `sensor.nibe_degree_minutes_status` (červená ikona při záporných DM)
- Výsledek: SOC odhady v plánu odpovídají reálné výrobě a spotřebě
- Poznámka: Historie se musí nejdřív nasbírat (min. 3 vzorky per hodinu), do té doby fallback

---

## 11. Známé limitace a budoucí práce

1. ~~**Hardcoded konstanty**~~: ✅ Vyřešeno v Session 4 (refaktoring)
2. ~~**Duplikátní kód**~~: ✅ Částečně vyřešeno (přejmenování, centralizace configu)
3. ~~**Predikce spotřeby**~~: ✅ Vyřešeno v v18.1 (dynamická predikce z historie)
4. ~~**optimalSoc statický**~~: ✅ Vyřešeno v Session 9 (dynamický výpočet z reálné potřeby)
5. **Bazénový ohřev**: Registr 47041 připraven ale neintegrován do automatizace
6. **Round-trip loss**: 81% (90% × 90%) — zohledněno ve finanční kalkulaci ale ne ve vizualizaci
7. ~~**Vytápění**~~: ✅ Logika v `fve-heating.json` opravena v Session 8 (podmínka pro střední ceny)
