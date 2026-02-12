# FVE Automatizace — Kompletní shrnutí projektu

> Tento dokument slouží jako kontext pro pokračování práce na jiném OS/stroji.
> Poslední aktualizace: 2026-02-12

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
| **Normal** | 0 | ne | povoleno | Solar hodiny, drahé hodiny (vybíjení) |
| **Šetřit** | 0 | ne | 0 (zakázáno) | Výchozí mód, šetří baterii |
| **Nabíjet ze sítě** | dynamický | dynamický | 0 | Velmi levná energie |
| **Prodávat** | +maxFeedIn | ne | povoleno | Velmi drahá energie, prodej |
| **Zákaz přetoků** | 0 | ne | povoleno | Dobrá prodejní cena |

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

---

## 11. Známé limitace a budoucí práce

1. ~~**Hardcoded konstanty**~~: ✅ Vyřešeno v Session 4 (refaktoring)
2. ~~**Duplikátní kód**~~: ✅ Částečně vyřešeno (přejmenování, centralizace configu)
3. **Predikce spotřeby**: `dailyConsumptionKwh=20` je statická, fve-history-learning.json zatím učí vzory ale nepoužívá je aktivně
4. **Bazénový ohřev**: Registr 47041 připraven ale neintegrován do automatizace
5. **Round-trip loss**: 81% (90% × 90%) — zohledněno ve finanční kalkulaci ale ne ve vizualizaci
6. **Vytápění**: Logika v `fve-heating.json` závisí na `letni_rezim` a cenových levelech — potřeba ověřit runtime chování
