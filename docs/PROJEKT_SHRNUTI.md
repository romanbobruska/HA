# FVE Automatizace — Kontext projektu

> **Living document** — aktuální stav systému. Po každé změně PŘEPSAT relevantní sekci (ne přidávat na konec).
> Poslední aktualizace: 2026-02-25 (18:20)
>
> **Provozní pravidla pro AI:**
> - Aktualizovat tento soubor po každém **úspěšném** nasazení (deploy)
> - Uživatel nevyžaduje potvrzení každého kroku — vše provádět bez čekání na Accept v IDE
> - Pokud je otázka nutná, položit max. 1× po kompletní analýze
> - **Každých 5 promptů projít HA Core logy a opravit co se dá**
> - **NIKDY nečíst HA entitu přes `api-current-state` pokud je dostupná v `fve_config` nebo `homeassistant.homeAssistant.states` globálu** — ale pouze pokud nepotřebuješ aktuální hodnotu přímo v daný okamžik; pokud ano, číst přes `api-current-state`
> - Nodes/skupiny v Node-RED se nesmí překrývat v canvasu — groups řadit vertikálně, mezera ~18px, x=14-24
> - **Před každým deploym** `deploy_sync_server.py` automaticky zachytí ruční změny z NR UI do git verzí flows

---

## 1. Co tento systém dělá

Automatizuje FVE elektrárnu (17 kWp), tepelné čerpadlo NIBE, nabíjení elektroaut a dalších spotřebičů v Home Assistant + Node-RED na základě spotových cen elektřiny, solární výroby a aktuální spotřeby.

**Klíčová logika:**
- V levných hodinách → nabíjet baterii ze sítě, topit
- V drahých hodinách → vybíjet baterii, blokovat velké spotřebiče
- V solárních hodinách → solar pokrývá spotřebu, přebytek do baterie nebo sítě
- Oběhové čerpadlo a NIBE jsou řízeny **nezávisle na sobě**

---

## 2. Infrastruktura

| Komponenta | Detail |
|------------|--------|
| **HA server** | `192.168.0.30:8123` |
| **SSH** | `ssh -i "$env:USERPROFILE\.ssh\id_ha" -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30` |
| **Git repo** | `https://github.com/romanbobruska/HA.git` (branch: main) |
| **Node-RED** | addon `a0d7b954_nodered`, flows: `/addon_configs/a0d7b954_nodered/flows.json` |
| **HA config** | `/config/` |
| **SQLite DB** | `/homeassistant/home-assistant_v2.db` (spotové ceny) |
| **Victron MQTT** | prefix `victron`, ID `c0619ab69c71` |

### Deploy příkaz (jediný správný způsob)
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ha" -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 \
  "rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh 2>&1"
```
- Deploy skript **automaticky** zastaví NR, nahraje flows, restartuje NR přes HA API
- HA konfigurační soubory se kopírují automaticky
- **POZOR**: `ha core check` v deploy.sh nesahat — visí, nahrazeno HA REST API

### Workflow pro zachycení ručních změn z NR UI
1. Provedeš změny v NR UI → klikneš **Deploy** v NR UI
2. Řekneš mi "hotovo"
3. Já stáhnu server flows přes SSH (base64), porovnám s gitem a commitnu změny
4. Pak teprve nasadím deploy z gitu
- `deploy_sync_server.py` = **samostatný nástroj**, nespouští se automaticky při deployi
- Deploy nikdy nespouští sync automaticky — jinak by přepsal git serverovou (potenciálně starou) verzí

### Kritická pravidla pro sync server→git
- **Sync matchuje vždy podle ID nodu** — nikdy nepřepisovat `rules`/`func`/`wires` z jednoho nodu na jiný
- **`rules`, `func`, `wires`, `links`** smí být synced jen pokud patří ke správnému ID
- Pozice (`x`,`y`,`w`,`h`) synced normálně podle ID
- **Zachovej layout uživatele**: pokud uživatel ručně přesunul nody, zachovat jejich `x`,`y` při dalších úpravách logiky
- Při opravě change nodů: vždy mapovat ID→ID z originálu, ne klíčovat podle pořadí nebo pozice

---

## 3. Struktura Node-RED flows

| Soubor | Co dělá |
|--------|---------|
| `fve-orchestrator.json` | Plánovač módů na 12h (spotové ceny + solar forecast + SOC simulace) |
| `fve-modes.json` | Implementace 6 módů (Victron příkazy přes HA service calls) |
| `fve-config.json` | Konfigurace + čtení HA stavů do globálů |
| `fve-heating.json` | Řízení topení: NIBE + oběhové čerpadlo + patrony + chlazení |
| `fve-history-learning.json` | Historická predikce solární výroby per hodina |
| `init-set-victron.json` | Inicializace dat z Victron VRM API |
| `vypocitej-ceny.json` | Spotové ceny z API → SQLite → globál `fve_prices_forecast` |
| `manager-nabijeni-auta.json` | Rozhodnutí grid vs. solar nabíjení auta — 1 function node čtoucí z globálů |
| `nabijeni-auta-sit.json` | Nabíjení auta ze sítě (headroom výpočet); cenové prahy z `fve_config` |
| `nabijeni-auta-slunce.json` | Nabíjení auta ze solaru; SOC práh z `fve_config` |
| `boiler.json` | Automatizace bojleru (Meross termostat) |
| `filtrace-bazenu.json` | Časové řízení filtrace bazénu |
| `ostatni.json` | Drobné automatizace |

---

## 4. Klíčové globální proměnné Node-RED

| Proměnná | Popis |
|----------|-------|
| `fve_config` | Kompletní konfigurace (prahy, kapacita, parametry topení...) |
| `fve_prices_forecast` | Tabulka cen. `day`=`"hoursToday"`/`"hoursTomorrow"`, 4 záznamy/hod. Klíč: `levelCheapestHourBuy` |
| `fve_plan` | Aktuální plán na 12h (mód per hodina, SOC simulace) |
| `fve_current_mode` | Aktuální mód FVE |
| `energy_arbiter` | Stav blokace vybíjení, aktivní spotřebiče |
| `cerpadlo_topi` | Flag: topí NIBE? (blokuje vybíjení baterie) |
| `auto_nabijeni_aktivni` | Flag: nabíjí se auto? |
| `sauna_aktivni` | Flag: zapnuta sauna? |

---

## 5. Klíčové konfigurační parametry (`fve_config`)

```
kapacita_baterie_kwh: 28      min_soc: 20 (čte z HA number.min_soc)
prah_levna_energie: 4         prah_draha_energie: 12
max_spotreba_sit_w: 22000     safety_margin_w: 2000
topeni_min_teplota_nadrze: 32 topeni_max_teplota_nadrze: 50
topeni_nouzova_teplota: 18    topeni_nocni_snizeni: 0.5 (vždy v noci 22-6h)
topeni_min_soc_patron: 95     topeni_max_teplota_patron: 50
topeni_patron_faze_w: 3000    topeni_min_pretok_patron_w: 3000
```

---

## 6. FVE módy

| Mód | Kdy | Baterie |
|-----|-----|---------|
| **Normal** | Drahé hodiny, vybíjení | Vybíjí |
| **Šetřit** | Výchozí, levné hodiny | Nečerpá |
| **Nabíjet ze sítě** | Nejlevnější hodiny | Nabíjí ze sítě |
| **Prodávat** | Velmi drahé + plná baterie | Prodej přebytků |
| **Zákaz přetoků** | Záporné prodejní ceny | Normální ESS |
| **Solární nabíjení** | Levné solární hodiny | Může nabíjet ze solaru, nevybíjí |

**Blokace vybíjení**: při aktivním NIBE topení, nabíjení auta nebo sauně → `MaxDischargePower=0`, `MaxChargePower=0`

---

## 7. Řízení topení domu (`fve-heating.json`)

**Architektura**: inject 60s + trigger na změnu automatizace → `Řízení topení v2.0` → actions array → switch router → service calls

### Topení MOD (klíčový koncept)
`input_select.topeni_mod` v HA zobrazuje aktuální mód. `flow.set("topeni_mod_active")` řídí blokaci.

| Mód | Podmínka | Blokace |
|-----|----------|---------|
| **Patrony** | solární přebytek ≥ 3kW + SOC ≥ 95% | NIBE zakázáno |
| **NIBE** | potřeba topit, žádný přebytek | Patrony zakázány |
| **Vypnuto** | teplota OK | obojí vypnuto |

**BEZPEČNOST**: NIBE a patrony NIKDY současně (přetížení jističe). Trojvrstvá ochrana:
1. Patrony: `!nibeBlockedByMod` podmínka
2. NIBE: `nibeBlockedByPatrony = nibeBlockedByMod`
3. Finální mutex v actions array

**NIBE** (`switch.nibe_topeni`, reg 47371):
- Levné/střední hodiny → ON (pokud MOD = NIBE)
- Drahé hodiny → OFF (výjimka: indoor < nouzová teplota 18°C)
- COOLDOWN: min. 10 minut mezi přepnutími
- OCHRANA: nevypnout pokud kompresor běží nebo čerpadlo není v Klidovém stavu

**Oběhové čerpadlo** (`switch.horousany_termostat_prizemi_kote`):
- ON: `tankTemp >= MIN_TANK (32°C)` — **bez horního limitu** (horní limit platí jen pro patrony)
- Noční omezení (22:00–6:00): spustí jen pokud `indoorTemp < targetTemp - 0.5°C`
- Nezávislé na NIBE, čerpá teplo z nádrže kdykoli je k dispozici
- OFF: nádrž < 32°C nebo krb aktivní

**Patrony** (3 fáze × 3 kW, `switch.patrona_faze_1/3_2/3`):
- Podmínky: SOC ≥ 95%, auto nemá hlad, nádrž < 50°C, solární přebytek
- Stupňování: přebytek ≥ 3kW=1f, ≥6kW=2f, ≥9kW=3f
- MOD_PATRONY → NIBE blokováno (bezpečnost jističe)

**Cílová teplota**: `input_number.nastavena_teplota_v_dome`
Noční snížení (`0.5°C`) platí **vždy v noci** (22:00–6:00) pro oběhové čerpadlo.

---

## 8. Aktuální stav integrací

**sensor.nabijeni_baterii_minus** (`unique_id: battery_power_minus`):
- MQTT topic: `victron/N/c0619ab69c71/system/0/Batteries`
- Vrací **kladnou hodnotu W** při vybíjení baterie (abs), 0 při nabíjení
- Používá se v `nabijeni-auta-slunce.json` vzorec: `11040 - spotreba_sit - batt_minus` (kladné = odečítáme)
- Oprava 2026-02-24: dříve vracelo záporné hodnoty, vzorec v flow opraven koordinovaně

**Meross termostat** (`climate.smart_socket_thermostat_24090276694597600801c4e7ae0a2e53`):
- MAC: `c4:e7:ae:0a:2e:53`, IP: `192.168.0.185`
- Meross LAN integrace v5.8.0 — nastaveno `protocol: auto`, `polling_period: 30`
- Dřívější problém (unavailable 4×/hod) vyřešen změnou z `protocol: http` na `auto`

**NIBE** (MyUplink + Modbus):
- Topení: reg 47371, Chlazení: reg 47372, TUV: reg 47387
- Sensor stavu: `sensor.nibe_aktualni_realny_stav` (Vytápění / Ohřev vody / Klidový / ...)
- Degree Minutes: `sensor.nibe_degree_minutes` (reg 43005)

**Victron ESS** (MQTT):
- MaxChargePower: `Settings/CGwacs/MaxChargePower`
- MaxDischargePower: `hub4/0/Overrides/MaxDischargePower`
- Power Setpoint: `Settings/CGwacs/AcPowerSetPoint`

---

## 9. Důležité implementační detaily

- **NIKDY hardcodovat hodnoty** — vše z `fve_config` nebo HA entit
- **"čerpadlo"** v kontextu topení = NIBE tepelné čerpadlo (ne oběhové čerpadlo)
- `fve_prices_forecast` — `levelCheapestHourBuy` je rank per den (1–24), ne absolutní cena
- Victron scheduled charging: aktivní jen pokud `duration > 0` — `duration: 0` = vypnuto
- Deploy skript zastaví NR přes `hassio/addon_stop` API, restartuje přes `hassio/addon_restart`
- `git status` před každým commitem — zahrnout i soubory které uživatel manuálně upravil

---

## 10. Solární instalace

- **Výkon**: 17 kWp, **Lokace**: Horoušany (50.10°N, 14.74°E)
- **Azimut**: 190° (mírně JZ), **Sklon**: 45°
- **Solární křivka** (v18.12): 5:00–18:00, maximum v 12:00 (13%), silnější odpoledne díky JZ orientaci
- **Sanity check výroby** (monthMaxSolarKwh): Leden 8, Únor 15, Březen 30, Červen 75 kWh/den
