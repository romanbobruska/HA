# FVE Automatizace — Kontext projektu

> **Living document** — aktuální stav systému. Po každé změně PŘEPSAT relevantní sekci (ne přidávat na konec).
> Poslední aktualizace: 2026-02-27 (03:05)
>
> **Provozní pravidla pro AI:**
> - Aktualizovat tento soubor po každém **úspěšném** nasazení (deploy)
> - Uživatel nevyžaduje potvrzení každého kroku — vše provádět bez čekání na Accept v IDE
> - Pokud je otázka nutná, položit max. 1× po kompletní analýze — ideálně více otázek v jednom promptu
> - **Každých 5 promptů projít HA Core logy a opravit co se dá**
> - **NIKDY nečíst HA entitu přes `api-current-state` pokud je dostupná v `fve_config` nebo `homeassistant.homeAssistant.states` globálu** — ale pouze pokud nepotřebuješ aktuální hodnotu přímo v daný okamžik; pokud ano, číst přes `api-current-state`
> - Nodes/skupiny v Node-RED se nesmí překrývat v canvasu — groups řadit vertikálně, mezera ~18px, x=14
> - **Design pattern pro NR flows:** každý node MUSÍ být v group (`g` property). Nové nody vždy přidat do existující nebo nové group. Vzor layoutu: `fve-config.json`
> - **Deploy = stop + start** (ne restart) — NR načte flows čistě bez banneru "modified externally"
> - **Před každým deploym** `deploy_sync_server.py` automaticky zachytí ruční změny z NR UI do git verzí flows
> - **KRITICKÉ: Flows které vytvořil uživatel** (`nabijeni-auta-sit.json`, `nabijeni-auta-slunce.json`, `manager-nabijeni-auta.json` — původní spaghetti logika) **NESMÍM měnit bez explicitního souhlasu uživatele.** Před jakoukoliv změnou logiky v těchto flows se ZEPTAT.

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

## Node-RED Design Patterns (POVINNÉ DODRŽOVAT)

### Layout pravidla
- **Každý node MUSÍ mít `g` property** → přiřazen do group. Žádné volné nody na canvasu.
- **Groups se nesmí překrývat** — řadit vertikálně nebo vedle sebe
- **Groupy musí být vizuálně u sebe** — žádné velké mezery, rozesety po stránce
- **Mezera mezi groups ~100px vertikálně** (přibližně, ne přesná hodnota)
- **Uživatel si layout upravuje ručně** — při programatických změnách zachovat jeho pozice x,y,w,h

### Wiring pravidla — KLÍČOVÉ
- **Žádné crossing wires** — pokud flow vyžaduje sdílené cíle z více zdrojů, MUSÍ se použít **link-out / link-in** nody
- **link-out/link-in** = neviditelné propojení mezi grupami (žádné drátky přes canvas)
- **Přímé wiry jen UVNITŘ skupiny** — nikdy mezi skupinami (výjimka: trivální 1 wire k sousední grupě)
- **Sdílená logika** (service calls, log) = vlastní grupa s link-in sbírající ze všech zdrojů
- **Inject nody** volají pouze nody ve **své vlastní skupině**
- **Žádné duplicitní triggery** na stejný cílový node
- **Orphan nody** (bez vstupu, mimo trigger types) = přesunout do skupiny nebo odstranit

### Group struktura
- Každá logická funkce = jedna group
- Group `style.label = true`
- Barvy: zelená=#d3f3d3 (Normal), žlutá=#f3f3d3 (Šetřit/upozornění), modrá=#d3d3f3 (Nabíjet), červená=#f3d3d3 (Prodávat), fialová=#e3d3f3 (Zákaz), žluto-krém=#fffacd (Solar), světle modrá=#dce6f0 (sdílené), šedá=#e8e8e8 (Log/pomocné)

### Vzor pro multi-mode flow (fve-modes.json v3)
```
Každý mód = malá grupa: [link-in] → [Logic func] → [link-out → Victron] + [link-out → Log]
Sdílená grupa = [link-in ← všechny módy] → [Fan-out func] → [service calls + feed-in switch]
Log grupa = [link-in ← všechny módy] → [Log Prep] → [File] + [rotace]

→ 0 viditelných wirů mezi grupami = čistý, přehledný layout
```

### Příklady správného layoutu
```
# fve-modes.json v3 (uživatelem schválený layout)
# Módové grupy vlevo vertikálně, sdílené vpravo
Group "Mód: NORMAL"             x=24  y=6    w=442  h=108  (link-in + Logic + 2× link-out)
Group "Mód: ŠETŘIT"             x=24  y=106  w=442  h=108
Group "Mód: NABÍJET ZE SÍTĚ"   x=24  y=206  w=442  h=108
Group "Mód: PRODÁVAT"           x=24  y=306  w=442  h=108
Group "Mód: ZÁKAZ PŘETOKŮ"     x=24  y=406  w=442  h=108
Group "Mód: SOLÁRNÍ NABÍJENÍ"  x=24  y=506  w=442  h=108
Group "Victron Actions"         x=34  y=639  w=932  h=442  (pod módy, link-in + fan-out + service calls)
Group "Log"                     x=494 y=159  w=662  h=182  (vpravo vedle módů, link-in + log prep + file + rotace)
```

### Pravidlo synchronizace před úpravou
- **VŽDY nejdřív načíst aktuální stav ze serveru** (`cat /addon_configs/a0d7b954_nodered/flows.json`)
- Uživatel může kdykoli provést ruční deploy v Node-RED nebo změnu v HA
- Před jakoukoliv programatickou úpravou flow: stáhnout ze serveru → porovnat s git → mergovat změny
- **NIKDY nepřepisovat uživatelovy ruční změny** — vždy je zachovat jako základ

---

## 3. Struktura Node-RED flows

| Soubor | Co dělá |
|--------|---------|
| `fve-orchestrator.json` | Plánovač módů na 12h (spotové ceny + solar forecast + SOC simulace) |
| `fve-modes.json` | Implementace 6 módů (refaktor v2, 2026-02-27): každý mód = link-in + Logic func, sdílená grupa "Victron Actions" (32 nodů místo 65) |
| `fve-config.json` | Konfigurace + čtení HA stavů do globálů |
| `fve-heating.json` | Řízení topení: NIBE + oběhové čerpadlo + patrony + chlazení |
| `fve-history-learning.json` | Historická predikce solární výroby per hodina |
| `init-set-victron.json` | Inicializace dat z Victron VRM API |
| `vypocitej-ceny.json` | Spotové ceny z API → SQLite → globál `fve_prices_forecast` |
| `manager-nabijeni-auta.json` | Rozhodnutí grid vs. solar nabíjení auta v2.3 — prioritní logika níže |
| `nabijeni-auta-sit.json` | Nabíjení auta ze sítě (headroom výpočet); cenové prahy z `fve_config` (`nabijeni_auta_cena_prah_vyssi/nizsi`) |
| `nabijeni-auta-slunce.json` | Nabíjení auta ze solaru; SOC práh z `fve_config`; damping ±2A/cyklus, delay 20s; **SOC>95% drain mód** (+300W z baterie) |
| `boiler.json` | Automatizace bojleru (Meross termostat) — solar forecast zítra, NIBE guard, Meross unavailable guard |
| `filtrace-bazenu.json` | Časové řízení filtrace bazénu |
| `ostatni.json` | Drobné automatizace |

### Bojler (boiler.json) — rozhodovací logika (v2, 2026-02-26)

**Meross termostat** `climate.smart_socket_thermostat_24090276694597600801c4e7ae0a2e53`, cyklus 2 min.

Rozhodovací pořadí (první splněná podmínka vyhraje):

1. **Nejsme doma** → MIN (20°C)
2. **Rychle teplá voda** (override) → MAX (69°C)
3. **Povinný čas 17:00–19:30** + voda < 58°C:
   - Zítra velký solár (`forecast_vyroba_zitra > FORECAST_THRESHOLD`) → jen **40°C** (`TEPLOTA_POVINNY_SOLAR`), zbytek dohřeje solár
   - Zítra malý solár → VYSOKA (60°C)
4. **NIBE topí** (`cerpadlo_topi`) + přebytek nestačí → MIN (bojler čeká, NIBE má přednost)
5. **Baterie > 96%** + solární přebytek → MAX/VYSOKA dle velikosti přebytku
6. **Baterie < 96%** + velký přebytek (`> PRAH_MAX`) → **MAX (69°C)**; střední přebytek (`> PRAH_VYSOKA`) → VYSOKA (60°C)
7. **Levná elektřina** (ne v letním režimu) → STREDNI (58°C)
8. Jinak → MIN

**Guardy**:
- Meross **unavailable** → přeskočit zápis (zabránit chybám)
- Cílová teplota === aktuální nastavená → přeskočit zápis (zbytečné volání Meross API)
- Ochrana přetížení sítě: `celkova_spotreba + SPOTREBA_BOJLER > SAFE_LIMIT` → neohřívat

**Config** (flow proměnné): `TEPLOTA_MAX=69, VYSOKA=60, STREDNI=58, MIN=20, POVINNY_SOLAR=40, FORECAST_THRESHOLD=35000Wh, PRICE_LEVEL_LEVNY=6, CENA_KWH_LEVNA=2.6`

### Manager nabíjení auta v2.4 — prioritní logika (oprava 2026-02-27)

**Implementace**: 1 `function` node (`main_logic_func`), 3 výstupy: [stop, slunce, síť].
**DŮLEŽITÉ**: čte `vyrobaDnes`/`vyrobaZitra` **přímo z `homeassistant.homeAssistant.states`** (HA websocket store) — NE z `fve_config`, protože `fve_config.forecast_vyroba_dnes` je po restartu NR = 0.

**KLÍČOVÁ OCHRANA (v2.4)**: Všechny cesty na SLUNCE vyžadují **reálný přebytek** (`rozdiVyroby > MIN_SOLAR_W = 4000W`). Bez přebytku auto NESMÍ nabíjet ze slunce (vybíjelo by baterii). Forecast/režim pouze POVOLUJÍ solární nabíjení, ale fyzický přebytek musí existovat.

**Stop path fyzicky zastavuje wallbox** (`switch.wallbox_garaz_start_stop = OFF`) — oprava 2026-02-27.

Rozhodovací pořadí (první splněná podmínka vyhraje):

1. Auto nemá hlad → **STOP** (wallbox OFF)
2. Automatizace OFF → **STOP** (wallbox OFF)
3. NIBE topí (mutex) → **STOP** (wallbox OFF)
4. `solarni_rezim ON` + **přebytek** → **SLUNCE**; bez přebytku → **STOP**
5. `letni_rezim ON` + **přebytek** → **SLUNCE**; bez přebytku → falls through
6. `vyrobaDnes > 40 kWh` + **přebytek** → **SLUNCE**
7. `batSoc > 95%` + **přebytek** → **SLUNCE**
8. `vyrobaZitra > 40 kWh` + **přebytek** → **SLUNCE**
9. Forecast OK ale přebytek chybí → **STOP** (čeká na přebytek, nevybíjí baterii)
10. Forecast špatný → **SÍŤ**

**Config parametry** (`fve_config`) — kompletní seznam pro nabíjení auta:
- `nabijeni_auta_forecast_kwh: 40` — threshold pro celkovou výrobu dne (manager)
- `nabijeni_auta_min_soc: 95` — min SOC baterie pro solární větev s přebytkem (manager)
- `nabijeni_auta_solar_w: 4000` — min aktuální přebytek W pro solární nabíjení (manager)
- `nabijeni_auta_cena_prah_vyssi: 4.3` — max cena kWh pro nabíjení ze sítě, vyšší práh (nabijeni-sit)
- `nabijeni_auta_cena_prah_nizsi: 3.0` — max cena kWh pro nabíjení ze sítě, nižší práh (nabijeni-sit)
- `nabijeni_auta_min_soc_slunce: 85` — min SOC baterie pro povolení solárního nabíjení (nabijeni-slunce)
- `nabijeni_auta_pretizeni_w: 18000` — práh přetížení sítě při nabíjení auta W (nabijeni-sit)
- `nabijeni_auta_soc_drain_prah: 95` — SOC práh pro drain mód solárního nabíjení (%)
- `nabijeni_auta_soc_drain_w: 300` — cílový odběr z baterie v drain módu (W, doporučeno 100-500)

**Odkud čte data**:
- `vyrobaDnes` = `getFloat("input_number.predpoved_solarni_vyroby_dnes")` → přes HA websocket (vždy aktuální)
- `vyrobaZitra` = `getFloat("input_number.predpoved_solarni_vyroby_zitra")` → přes HA websocket
- `letniRezim` = `getBool("input_boolean.letni_rezim")` → přes HA websocket

---

## 4. Klíčové globální proměnné Node-RED

| Proměnná | Popis |
|----------|-------|
| `fve_config` | Kompletní konfigurace (prahy, kapacita, parametry topení...) |
| `fve_prices_forecast` | Tabulka cen. `day`=`"hoursToday"`/`"hoursTomorrow"`, 4 záznamy/hod. Klíč: `levelCheapestHourBuy` |
| `fve_plan` | Aktuální plán na 12h (mód per hodina, SOC simulace) |
| `fve_current_mode` | Aktuální mód FVE |
| `energy_arbiter` | Stav blokace vybíjení, aktivní spotřebiče |
| `cerpadlo_topi` | Flag: NIBE topí (Vytápění/TUV)? Blokuje vybíjení baterie + blokuje nabíjení auta. **Neplatí pro chlazení.** |
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
| **Zákaz přetoků** | Záporné prodejní ceny | Normální ESS, feed-in OFF |
| **Solární nabíjení** | Levné solární hodiny | Může nabíjet ze solaru, nevybíjí |

**Blokace vybíjení**: při aktivním NIBE topení (jen ze sítě, solar<500W), nabíjení auta ze sítě nebo sauně → `blockMinSoc = currentSoc+1` (baterie se nevybíjí pod aktuální SOC), `MaxDischargePower=-1`. Solární nabíjení auta a NIBE ze solaru NEBLOKUJÍ.

**Feed-in control** (oprava 2026-02-26):
- Zákaz přetoků: `switch.overvoltage_feed_in = OFF` + `number.max_feed_in_power = 0` + `power_set_point = 100W` + **`PreventFeedback = 1` přes MQTT** (`victron/W/c0619ab69c71/settings/0/Settings/CGwacs/PreventFeedback`)
- `PreventFeedback` je klíčový — omezuje MPPT výkon na firmware úrovni Victronu, zabraňuje exportu i na úrovni jednotlivých fází
- `power_set_point = 100W` (ne 0) — ESS cílí na mírný odběr ze sítě, absorbuje regulační oscilaci
- Všechny ostatní módy: obnovují `overvoltage_feed_in = ON` + `max_feed_in_power = 7600` + `PreventFeedback = 0`
- Výsledek: **export = 0W** (ověřeno 12/12 vzorků minutového monitoringu)

**Po vypnutí sauny / zastavení nabíjení auta** (cf3302d, 3326bb6):
- `sauna_set_global` (sauna OFF) / `Kontrola nabíjení auta` (auto STOP) resetují `config.min_soc = 20` v globálu
- Zapíší `number.min_soc = 20` do HA entity (Victron) přes nové nody `sauna_reset_minsoc` / `auto_reset_minsoc`
- Okamžitě triggerují přepočet plánu (→ `Sbírka dat`) přes `sauna_trigger_plan` / `auto_trigger_plan`
- **Bez toho**: plánovač viděl `minSoc=currentSoc+1` (74%/64%) a generoval plán "Šetřit (Ochrana baterie)" i po deaktivaci
- **Pravidlo**: každý blokátor (sauna, auto, cerpadlo) musí po deaktivaci resetovat `number.min_soc = 20` a retriggerovat plán

---

## 7. Řízení topení domu (`fve-heating.json`)

**Architektura**: inject 60s + trigger na změnu automatizace → `Řízení topení v2.0` → actions array → switch router → service calls

### Topení MOD (klíčový koncept)
`input_select.topeni_mod` v HA zobrazuje aktuální mód. `flow.set("topeni_mod_active")` řídí blokaci.

| Mód | Podmínka | Blokace |
|-----|----------|--------|
| **NIBE** | `tempGap > 0.2°C` (teplota domu je víc než 0.2°C pod cílem) | Patrony zakázány |
| **Patrony** | `tempGap ≤ 0.2°C` + solární přebytek ≥ 3kW + SOC ≥ 95% | NIBE zakázáno |
| **Vypnuto** | teplota OK + žádný přebytek | obojí vypnuto |

**PRIORITA**: Patrony = **POSLEDNÍ** v prioritě. Berou přebytky co nemám kam dát (auto, NIBE, baterie uspokojeny). Patrony běží jen pokud teplota domu je max 0.2°C pod cílem (`PATRON_TEMP_MARGIN`). Větší rozdíl → NIBE.

**BEZPEČNOST**: NIBE a patrony NIKDY současně (přetížení jističe). Trojvrstvá ochrana:
1. Patrony: `!nibeBlockedByMod` podmínka
2. NIBE: `nibeBlockedByPatrony = nibeBlockedByMod`
3. Finální mutex v actions array

**PRIORITA TOPENÍ > NABÍJENÍ AUTA** (oprava 2026-02-26):
- Platí POUZE pro topení (Vytápění/TUV), **NE pro chlazení** (letní režim)
- Pokud NIBE potřebuje topit a auto nabíjí → akce `stop_auto_nabijeni` vypne `input_boolean.nastavuj_amperaci_chargeru_solar` + `input_boolean.nastavuj_amperaci_chargeru_grid`
- `global.cerpadlo_topi` = `(isHeating || isTUV) && nibeBlkDisch` → blokuje auto v `manager-nabijeni-auta.json`
- Manager (krok 3): kontroluje `cerpadlo_topi` → pokud true, auto STOP

**NIBE** (`switch.nibe_topeni`, reg 47371) — rozhodovací strom (v2.1, 2026-02-27):
1. **Bezpečnostní kontroly** (vždy první): Grid Lost, Krb, Nádrž > MAX_TANK, Patrony blokují → NIBE OFF
2. **needsHeat && !isDraha** (levná/střední hodina + potřeba topit):
   - `bigSolarTomorrow && indoorTemp >= safeTemp && !(isSolarHour && SOC > 90%)` → NIBE OFF (šetříme pro solární hodiny; výjimka: v solárních hodinách při SOC > 90% topit)
   - `cheaperAhead && indoorTemp >= safeTemp && !(isSolarHour && SOC > 90%)` → NIBE OFF (počkáme; výjimka: v solárních hodinách při SOC > 90% topit hned)
   - `prebytek >= SOLAR_OVERRIDE_W (8kW, config)` → NIBE ON, `nibeBlockDischarge = false`
   - jinak → NIBE ON, `nibeBlockDischarge = (batSoc <= 90)` — SOC > 90%: topit ze soláru + baterie; SOC ≤ 90%: šetřit baterii
3. **needsHeat && isDraha && nibeOn** (drahá hodina + NIBE už běží):
   - NIBE **pokračuje**, `nibeBlockDischarge = false`
4. **needsHeat && isDraha && !nibeOn** (drahá hodina + NIBE neběží):
   - `prebytek >= SOLAR_OVERRIDE_W` → NIBE ON bez blokace
   - `indoorTemp < safeTemp` → NIBE ON nouzově
   - Jinak: **čekat**
5. **!needsHeat** → NIBE OFF

**Noční režim** (oprava v2.1): `effTarget = isNight ? (targetTemp - NOCNI_SNIZ) : targetTemp` — noční snížení platí **vždy** v noci (22:00–6:00), ne jen v drahých hodinách.
**Price fallback** (oprava v2.1): pokud `lvl === 99` (hodina nenalezena v `fve_prices_forecast`), čte se z `input_number.levelcheapesthourbuy`.
- Config: `topeni_solar_override_w = 8000` (W), `topeni_solar_forecast_kwh = 30` (kWh)
- COOLDOWN: min. 10 minut mezi přepnutími
- OCHRANA: nevypnout pokud kompresor běží nebo čerpadlo není v Klidovém stavu

**Oběhové čerpadlo** (`switch.horousany_termostat_prizemi_kote`):
- ON: `tankTemp >= MIN_TANK (32°C)` — **bez horního limitu** (horní limit platí jen pro patrony)
- Noční omezení (22:00–6:00): spustí jen pokud `indoorTemp < targetTemp - 0.5°C`
- Nezávislé na NIBE, čerpá teplo z nádrže kdykoli je k dispozici
- OFF: nádrž < 32°C nebo krb aktivní

**Patrony** (3 fáze × 3 kW, `switch.patrona_faze_1/3_2/3`):
- **Priorita nejnižší** — zapnou se pouze pokud už není kam dát solární energii
- Podmínky (`patronyMohou`): SOC ≥ 95% + auto nenabíjí + `auto_ma_hlad=OFF` + nádrž < 50°C + solární přebytek
  - `auto_nabijeni_aktivni` (global) = wallbox fyzicky nabíjí (`Charging`) — blokuje patrony i při solárním nabíjení auta
  - `auto_ma_hlad` = ránní rychlé síťové nabíjení auta
- **Konzervativní start**: hlavní loop (60s) vždy zapne jen **1 fázi**, korekční smyčka (5s) přidá další
- **Hlavní loop vs korekce**: hlavní loop jen startuje (actPat=0→1) nebo stopuje patrony. Jakmile patrony běží, počet fází řídí korekční smyčka (5s).
- **MOD_PATRONY** se aktivuje pokud:
  - `isSolarHour` AND `tempGap ≤ PATRON_TEMP_MARGIN (0.3°C)` AND `needsHeat` — solární hodiny, dům blízko cíle
  - nebo `!needsHeat` AND patrony fyzicky běží — teplota dosažena, patrony dál ohřívají nádrž
- MOD_PATRONY = NIBE blokováno. Patrony fyzicky čekají na SOC ≥ 95%.
- `PATRON_TEMP_MARGIN = 0.3°C` — max rozdíl indoor vs target pro přepnutí na patrony v solárních hodinách
- **Korekce fází** (`pat_korekce_func`, 5s cyklus) — **reaktivní logika** (bez predikce availPat):
  - **Snížení**: `battMinus > DISCHARGE_LIMIT` musí trvat **3 po sobě jdoucí cykly** (15s) → sníží o 1 fázi
  - **Zvýšení**: `battMinus === 0` musí trvat **6 po sobě jdoucích cyklů** (30s stability) → přidá 1 fázi
  - **Minimum 1 fáze**: korekce nikdy nesníží pod 1 fázi. Pod 1 fázi může vypnout jen hlavní loop (patronyMohou = false).
  - **Cooldown**: po každé změně fáze 30s pauza (6 cyklů × 5s) — zamezuje oscilaci
  - **Startup cooldown**: hlavní loop při zapnutí patrony (actPat=0→1) nastaví cooldown 30s pro korekci
  - `DISCHARGE_LIMIT = 200W` (config: `topeni_patron_discharge_limit_w`)
  - `DISCHARGE_HYST = 3` (config: `topeni_patron_discharge_hyst`)
  - `STABLE_CYCLES = 6` (config: `topeni_patron_stable_cycles`)
  - `CHANGE_COOLDOWN = 6` (config: `topeni_patron_change_cooldown`)
  - Korekce kontroluje SOC ≥ 95% (resp. ultraSocPrah) — pod prahem vypne všechny fáze
  - Platí pro automatický i manuální mód

**Ultra levná energie** (v2.2, 2026-02-27):
- **Podmínka aktivace**: `priceBuy < prah_ultra_levna_nakup (1.0 Kč)` AND `priceSell ≤ 0` AND `isSolarHour`
- **Kde**: detekce v `fve-modes.json` (Zákaz přetoků Logic), global flag `ultra_levna_energie`
- **Deaktivované blokace**:
  - Patrony SOC práh: 95% → `min_soc` (20%)
  - Patrony nepotřebují solární přebytek (mohou čerpat ze sítě)
  - Patrony neblokované autem (`!autoHlad`, `!autoNabiji` padá)
  - NIBE nezastavuje auto nabíjení (`stop_auto_nabijeni` se neprovede)
  - `cerpadlo_topi` neblokuje auto v `manager-nabijeni-auta.json`
- **Zachované blokace** (bezpečnost):
  - ⚡ NIBE + Patrony nikdy současně (jistič: 14kW + 9kW = 23kW > 22kW)
  - `max_spotreba_sit_w` (22kW) stále respektováno
  - Normální teplotní podmínky (`needsHeat`, `tankTemp`, `autoHlad`)
  - Bezpečnostní kontroly (Krb, Grid Lost, tank > MAX, NIBE cooldown)
- **Chování**: spotřebiče se nezapnou všechny naráz — jen se uvolní vzájemné blokace, zapnou se přirozeně pokud to dává smysl
- Config: `prah_ultra_levna_nakup = 1.0` (Kč/kWh)

**Cílová teplota**: `input_number.nastavena_teplota_v_dome`
Noční snížení (`0.5°C`) platí **vždy v noci** (22:00–6:00) pro oběhové čerpadlo.

**Automatizace OFF** (`input_boolean.automatizovat_topeni` → OFF) = manuální mód:
- Flow čte `input_select.topeni_mod` — nastavíš ho ručně v HA dashboardu
- Flow **NEPŘEPISUJE** mod, jen provádí příkazy dle něj
- `Vypnuto` → **žádné zásahy** — plně manuální ovládání, flow nic nemění
- `NIBE` → topit jen z NIBE dle pravidel (teplota vs. target), patrony blokované
- `Patrony` → topit jen z patron dle solárního přebytku, NIBE blokované
- `Obehove` → jen oběhové čerpadlo, NIBE i patrony off

---

## 8. FVE Logging (`/homeassistant/fve_log.jsonl`)

- Každý cyklus módů (Normal/Šetřit/Nabíjet/Prodávat/Solární/Zákaz) zapisuje JSON řádek
- Pole: `ts, mode, soc, prebytek_w, block_discharge, block_min_soc, nibe, topeni_mod, consumers`
- Rotace 1× denně ve 04:00 — zachovají se záznamy max 3 dny dozadu (max 10000 řádků)
- Soubor: `/homeassistant/fve_log.jsonl`
- Čtení: `tail -20 /homeassistant/fve_log.jsonl | python3 -c "import sys,json; [print(json.dumps(json.loads(l))) for l in sys.stdin]"`

---

## 9. Aktuální stav integrací

**Blokace vybíjení baterie** (oprava 2026-02-25):
- **CHYBA**: `MaxDischargePower=0` škrtilo celý DC→AC tok invertoru včetně průchodu solární energie → solar výkon klesl na ~2kW
- **OPRAVA**: `MaxDischargePower=-1` vždy (bez limitu), blokace vybíjení baterie přes `number.min_soc = currentSoc+1`
- Při uvolnění blokace: `min_soc` se resetuje zpět na `config.min_soc` (20%)
- Dotčené módy: Normal Logic, Solární nabíjení Logic, Šetřit, Nabíjet

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

**Victron ESS** (MQTT + HA entities):
- MaxChargePower: `number.max_charge_power` / `Settings/CGwacs/MaxChargePower`
- MaxDischargePower: `number.max_discharge_power` / `hub4/0/Overrides/MaxDischargePower`
- Power Setpoint: `number.power_set_point` / `Settings/CGwacs/AcPowerSetPoint`
- Feed-in excess solar: `switch.overvoltage_feed_in` / `Settings/CGwacs/OvervoltageFeedIn`
- Max feed-in power: `number.max_feed_in_power` / `Settings/CGwacs/MaxFeedInPower`

**Wallbox ampérace** (oprava 2026-02-26, commit 7c641cf+e34050c):
- `select.wallboxu_garaz_amperace` vrací string "16A" — parsovat přes `parseInt(rawCharger.replace(/[^0-9]/g, ''), 10)`
- Damping: max ±2A změna za cyklus, delay 20s mezi cykly
- Bez opravy: ampérace oscilovala 6→16→6 každou 1-2s

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
