# FVE Automatizace — Kontext projektu

> **Living document** — aktuální stav systému. Po každé změně PŘEPSAT relevantní sekci.
> Poslední aktualizace: 2026-03-19 (v25.51: Config plain values, opp header global, conditional datetime)
>
> **⚠️ VŠECHNY požadavky, zákony a pravidla jsou v `User inputs/POZADAVKY.TXT`.**
> Tento soubor obsahuje pouze technický kontext a stav systému — NE požadavky.
>
> **Pravidla pro AI (POVINNÁ při KAŽDÉM promptu):**
> - **VŽDY komunikovat v ČEŠTINĚ** — základní pravidlo
> - **NA ZAČÁTKU každého promptu**: přečíst `User inputs/POZADAVKY.TXT` (ZÁKONY) + `problemy.txt` (aktuální problémy)
> - **ABSOLUTNÍ ZÁKON 1.2 + 2.3**: VŽDY má přednost stav NR na serveru HA před lokální verzí. NIKDY nepřepisovat stav v HA lokální verzí.
> - **PŘED úpravou flow**: stáhnout aktuální flows ze serveru (`ssh ... "cat flows.json"`) — SERVEROVÁ verze = PRAVDA (flows, nody, layout, parametry, config — VŠECHNO)
> - **Deploy.sh nahrazuje CELÉ taby z gitu** → git MUSÍ obsahovat aktuální serverovou verzi + moje cílené změny
> - Před deploymentem ověřit soulad se VŠEMI zákony
> - Po deploymentu: ověřit HA stavy, NR logy, grid draw
> - `User inputs/POZADAVKY.TXT` NESMÍ AI MĚNIT — edituje výhradně uživatel
> - Aktualizovat tento soubor po každém úspěšném nasazení
> - Po sobě VŽDY uklidit dočasné soubory (`_*.py`, `_*.js`, `_fix_*`, `_check_*`) lokálně i na serveru
>
> **Komunikační kanál:**
> - Uživatel píše problémy/požadavky do `problemy.txt` — AI ho čte na začátku každého promptu
> - AI odpovídá v chatu a provádí opravy — NIKDY nepíše do `problemy.txt`

---

## 1. Co tento systém dělá

Automatizuje FVE elektrárnu (17 kWp), tepelné čerpadlo NIBE, nabíjení elektroaut a dalších spotřebičů v Home Assistant + Node-RED na základě spotových cen elektřiny, solární výroby a aktuální spotřeby.

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
| **FVE Log** | `/homeassistant/fve_log.jsonl` |

### Deploy příkaz
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ha" -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 \
  "rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh 2>&1"
```

### Sync ručních změn z NR UI
1. Uživatel provede změny v NR UI → Deploy
2. AI stáhne server flows přes SSH, porovná s gitem, commitne
3. Pak deploy z gitu
- `deploy_sync_server.py` = samostatný nástroj, nespouští se automaticky při deployi
- **VŽDY stáhnout flows ze serveru PŘED jakoukoli úpravou** — jinak ztráta ručních změn
- Sync matchuje podle ID nodu, zachovává uživatelův layout

---

## 3. Struktura Node-RED flows

| Soubor | Co dělá |
|--------|---------|
| `fve-orchestrator.json` | Plánovač módů na 12h — 5 funkcí: Příprava→Cena→Arbitráž→Plán→Výstup + Kontrola podmínek + blokace |
| `fve-modes.json` | Implementace 7 FVE módů (Normal, Šetřit, Nabíjet, Prodávat, Zákaz, Solární, Balancování) |
| `fve-config.json` | Centrální konfigurace (~186L, komentovaná po sekcích) + čtení HA stavů do globálů |
| `fve-heating.json` | Řízení topení — 3 funkce: Čtení stavu→Rozhodování→Pojistky+výstup (v25.1 split z 541L) |
| `fve-history-learning.json` | Historická predikce solární výroby per hodina |
| `init-set-victron.json` | Inicializace dat z Victron VRM API |
| `vypocitej-ceny.json` | Spotové ceny z API → SQLite → globál |
| `manager-nabijeni-auta.json` | Rozhodnutí grid vs. solar nabíjení auta |
| `nabijeni-auta-sit.json` | Nabíjení auta ze sítě (cenové prahy, headroom) |
| `nabijeni-auta-slunce.json` | Nabíjení auta ze solaru (closed-loop amperage) |
| `boiler.json` | Automatizace bojleru (Meross termostat) |
| `filtrace-bazenu.json` | Časové řízení filtrace bazénu + NIBE kompresor priorita |
| `ostatni.json` | Drobné automatizace |

---

## 4. Klíčové globální proměnné Node-RED

| Proměnná | Popis |
|----------|-------|
| `fve_config` | Kompletní konfigurace (prahy, kapacita, parametry) |
| `fve_prices_forecast` | Tabulka spotových cen |
| `fve_plan` | Aktuální plán na 12h (mód per hodina) |
| `fve_current_mode` | Aktuální FVE mód |
| `cerpadlo_topi` | NIBE topí? (Vytápění/TUV, ne chlazení) |
| `auto_nabijeni_aktivni` | Nabíjí se auto? |
| `sauna_aktivni` | Zapnuta sauna? |

---

## 5. Technické detaily integrací

**Victron ESS** (MQTT + HA):
- MaxDischargePower: `number.max_discharge_power` / `hub4/0/Overrides/MaxDischargePower`
- Power Setpoint: `number.power_set_point` / `Settings/CGwacs/AcPowerSetPoint`
- Feed-in: `switch.overvoltage_feed_in`, `number.max_feed_in_power`, `PreventFeedback` (MQTT)

**NIBE** (MyUplink + Modbus):
- Topení: reg 47371, Chlazení: reg 47372, TUV: reg 47387
- Stav: `sensor.nibe_aktualni_realny_stav`

**Wallbox**:
- Ampérace: `select.wallboxu_garaz_amperace` (vrací "16A" — parsovat přes parseInt)
- Stav: `sensor.charger_state_garage` (0=Disc, 1=Conn, 2=Charg, 3=Charged, 6=WaitStart)

**Meross termostat**: `climate.smart_socket_thermostat_24090276694597600801c4e7ae0a2e53`

---

## 6. Node-RED Design Patterns

- Každý node MUSÍ mít `g` property (přiřazen do group)
- Groups se nesmí překrývat — řadit vertikálně
- Přímé wiry jen UVNITŘ skupiny — mezi skupinami link-out/link-in
- Deploy = stop + start (ne restart)
- Vzor: `fve-modes.json` — módové grupy vlevo, sdílené vpravo

---

## 7. v25.1 REFACTORING (branch: REFACTORING, 2026-03-11)

Všechny NR funkce zkráceny na ≤100 řádků. Hardcoded hodnoty nahrazeny config parametry.

| Funkce | Před | Po | Změna |
|--------|------|-----|-------|
| Výpočet plánu na 12h | 1239L | 5 funkcí (49+45+33+58+25L) | Split do řetězce msg passing |
| Řízení topení v2.0 | 541L | 3 funkce (61+70+35L) | Split: čtení→rozhodování→pojistky |
| Patrony korekce | 212L | 53L | Komprese, zachována logika |
| BALANCOVÁNÍ Logic | 229L | 51L | Komprese, zachována logika |
| Kontrola podmínek | 131L | 46L | Komprese |
| 🧠 Bojler logika | 214L | 47L | Komprese |
| Manager nabíjení auta | 176L | 42L | Komprese |
| Nastav konfiguraci | 168L | 47L | Komprese, removed comments |
| Vypočítej amperaci | 142L | 33L | Komprese |
| Sbírka dat | 124L | 35L | Komprese |
| Filtrace bazénu | 121L | 30L | Komprese |
| Zpracuj HA stavy | 103L | 30L | Komprese |

**R3**: Hardcoded `7600` → `config.max_feed_in_w || 7600` v 6 funkcích (fve-modes)
**R4**: Hardcoded `95` SOC → `config.topeni_patron_drain_soc_prah || 95` v 5 funkcích

**Pozn.**: Komprimované funkce v chráněných flows (manager-nabijeni-auta, nabijeni-auta-slunce) — logika nezměněna, jen formátování.

---

## 8. v25.6–25.8 Opravy korekčních smyček (2026-03-11)

### v25.6: Solární nabíjení auta — anti-oscilace
- **Problém**: Ampéráž oscilovala chaoticky (13→6→15→7→16→6 za minutu), grid draw 246–334W
- **Příčina**: Tři trigger zdroje (inject 20s + delay feedback 20s + state-change) vytvářely překrývající se řetězce
- **Fix** (`nabijeni-auta-slunce.json`, node `788e188fae8d1fca`):
  - Cooldown 15s (`solar_corr_last_run`) — duplicitní spuštění se přeskočí
  - Rate limit ±2A per cyklus (config `nabijeni_auta_max_step`)
  - Grid draw safety: pokud `spotreba_ze_site > nabijeni_auta_max_grid_w` (200W) → okamžitě snížit

### v25.7: Patrony korekce — dead band pro 3kW kroky
- **Problém**: Dead band 500W (z `nabijeni_auta_dead_band_w`) příliš úzký pro 3kW fáze patron → oscilace 1↔2 fáze
- **Příčina**: Kód četl config klíče pro auto (`nabijeni_auta_*`) místo patron (`topeni_patron_*`)
- **Fix** (`fve-heating.json`, node `pat_korekce_func`):
  - DB = max(`topeni_patron_dead_band_w`, `topeni_patron_faze_w / 2`) = min 1500W
  - Cooldown mezi změnami fází: `topeni_patron_change_cooldown × 5s` (default 30s)
  - Správné config klíče pro patron target a dead band

### v25.8: Patrony router — chybějící ON wiring (KRITICKÝ BUG)
- **Problém**: Korekční smyčka nemohla PŘIDÁVAT fáze — pouze odebírat
- **Příčina**: `pat_korekce_router` (switch node) měl 6 pravidel ale jen 3 výstupy
  - Rules 0–2 (p*_off) → napojeny na service nodes ✅
  - Rules 3–5 (p*_on) → žádné výstupy, tiše zahozeny ❌
- **Fix**: `outputs: 6`, wires pro p1_on→`htg_svc_p1_on`, p2_on→`htg_svc_p2_on`, p3_on→`htg_svc_p3_on`
- **Ověřeno**: 3 fáze stabilně běží, batt -528W, grid 82W

### v25.9: Patrony — sell price check (zákon 8.5)
- **Nový zákon**: Pokud prodejní cena > 2 CZK → patrony se nepoužijí (lepší prodat)
- **Config**: `topeni_patron_max_sell_price: 2` (CZK, konfigurovatelné)
- **Implementace**: check v `rf_htg_decide2` (`patSellOk`) + `pat_korekce_func` (SELL price guard)
- **Logika**: `sellPrice <= threshold || sellPrice >= 99` (99 = cena nedostupná → povoleno)

### Entity názvy patron fází
| Fáze | Entity ID |
|------|-----------|
| 1 | `switch.patrona_faze_1` |
| 2 | `switch.patrona_faze_3_2` |
| 3 | `switch.patrona_faze_3` |

---

## 9. v25.15 Discharge optimalizace + config (2026-03-13)

### v25.15.1–15.2: Prioritizace vybíjení dle zákonů 4.9
- **Problém**: hr=7 (drahá solární hodina, 4.68 CZK) v Šetřit místo Normal kvůli minSOC ochraně
- **Fix node 3** (`rf_arb_trimming_3`): Budget-limited fill, solar-aware SOC drop, second-pass DRAHA trim
- **Fix node 4** (`rf_gen_plan_0004`): Výjimka z minSOC ochrany pro solární discharge hodiny

### v25.15.3: Blokace text fix
- **Problém**: Dashboard zobrazoval "Blokace:top" místo "Topení"
- **Fix** (`Kontrola podmínek`): Zkratky → plné názvy ("Topení", "Nab. auta", "Výpadek sítě", "Sauna")

### v25.15.5: Config reformat
- Obnoveny komentáře a sekce v `fve-config.json` (186L)
- Přidány chybějící parametry: `topeni_patron_min_solar_w`, `nibe_est_consumption_kwh`, `topeni_solar_defer_margin`, `topeni_final_solar_kwh`, `topeni_final_hours`
- Fix: `topeni_min_soc_patron` 90→95 (dle POZADAVKY.TXT)

### v25.16: High solar day NIBE deferral (zákon 8.2)
- **Nové pravidlo**: Pokud denní solární forecast > 50kWh, NIBE se odloží na patrony během solárních hodin
- **Config**: `topeni_solar_high_day_kwh: 50` (konfigurovatelný práh)
- **Denní hystereze**: Na high-solar dnech v solárních hodinách `effTgt = tgtT - 0.5°C` (jako noční snížení)
- **Bezpečnost**: NIBE startne pokud teplota klesne pod `tgtT - 0.7°C`, nebo při mustHeatFinal/mustHeatByPrice

### v25.17: Opravy topení a filtrace (2026-03-13)

**Oběhové čerpadlo** (`fve-heating.json`):
- Čerpadlo používalo `h.effTgt` (22.8°C s highSolDay) místo `h.tgtT` (23.3°C) → nyní `h.tgtT` ve dne
- Zákon 8.4: "teplota domu < cíl" = nastavená teplota, ne efektivní

**effTgt deferral** (`fve-heating.json`):
- highSolDay snížení effTgt platí JEN když patrony mohou běžet (`!h.autoHlad && !h.autoNabiji`)
- Zákon 8.2: deferral "pokud je pravděpodobnost, že se natopí dům i z patron"

**Patrony mode selection** (`fve-heating.json`):
- Přidán `patMohou` check do první Patrony větve
- Přidán globální 3h override: `if(mod==="Patrony" && hToLastSol<=finalHrs) mod="NIBE"`
- `korekce` nyní respektuje `patBlkMod` — hlavní loop přebírá řízení fází od korekční smyčky
- Config: `topeni_final_hours: 3` (konfigurovatelný)

**Filtrace NIBE priorita** (`filtrace-bazenu.json`, zákon 10.5):
- Když NIBE kompresor pracuje (`binary_sensor.nibe_kompresory_aktivni_binarni=ON`) → filtrace pauza
- Kontroluje se stav kompresoru (pracuje), NE switch.nibe_topeni (zapnuto)
- Anti-cycling se nepřeskakuje pro kompresor override
- Zákon 10.5 aktualizován v POZADAVKY.TXT

**Zákon 8.5 — pravidlo 3 hodin** (nový zákon v POZADAVKY.TXT):
- Pokud aktuální hodina ≤ 3h před poslední solární hodinou → patrony se nespustí, NIBE preferováno
- Důvod: patrony nestihnou dostatečně natopil nádrž před koncem solární výroby

### v25.49: Oportunistický balancing monitoring (2026-03-19)

**Zákon 12.5**: Pokud SOC baterie dosáhne 100% i mimo plánovaný balancing, sledovat pasivně:
1. **Tracking SOC 100%**: Globál `opp_soc100_since` zaznamenává čas dosažení 100%
2. **Po 1 hodině na 100%**: Spustí se monitoring proudu baterie (`opp_bal_monitoring=true`)
3. **Sledování idle**: Pokud `|battery_dc_current| < 0.5A` po dobu 20 min → balanced OK
4. **Vyhodnocení**: Když SOC klesne pod 100%, vyhodnotí se OK/NOK → aktualizuje `input_datetime.last_pylontech_balanced` + `input_boolean.pylontech_balancing_ok`
5. **Nové nody**: `opp_bal_inject` (60s timer) + `opp_bal_check` (zpracování pending výsledku → service calls)
- Mód FVE se NEMĚNÍ — pouze pasivní sledování

**Plan header**: `balancingStatus.text` = "⚡ Poslední balancing: DD.MM. HH:MM ✅/❌" v plánu

**Fix contMin threshold**: BALANCOVÁNÍ Logic `contMin>=20` → `contMin>=80` (20 min při 15s/cyklus)

### v25.55: Fix filtrace anti-cycling + heating proactive tank (2026-03-21)

**Fix 1: Filtrace** (`filtrace-bazenu.json`, `filtrace_decision`):
- **Root cause**: Anti-cycling (10 min) blokoval vypnutí filtrace i po splnění denního minima. Když se filtrace zapnula při run=58 min, za 2 min met=true, ale anti-cycling blokoval "off" → filtrace běžela 68/60 min.
- **Zákon 10.1** (základní pravidlo, PRIORITA): „FILTRACE NESMÍ BĚŽET DÉLE, NEŽ JE POŽADOVÁNO"
- **Fix**: Anti-cycling nyní má podmínku `&& !met` — když je minimum splněno, vypnutí proběhne okamžitě bez čekání na anti-cycling.

**Fix 2: Topení** (`fve-heating.json`, `rf_htg_decide2`):
- **Root cause**: Proaktivní ohřev nádrže blokován `autoHlad` v L42. Zákon říká, že `autoHlad` blokuje jen patrony, ne NIBE.
- **Zákon 8.2**: „VŽDY JE DOBRÉ NATOPÍT NÁDRŽ I V PŘÍPADĚ, ŽE JE NATOPEN DŮM! A TO ZA CO NEJVÝHODNĚJŠÍCH PODMÍNEK"
- **Fix**: 
  - L42: odstraněn `autoHlad` (blokuje jen patrony, ne NIBE proaktivní ohřev)
  - Nový config parametr `topeni_chladna_nadrz: 40` (°C) — práh chladné nádrže pro proaktivní ohřev
  - L42 nyní porovnává `tankT < coldTank` (40°C) místo `maxTank` (50°C) — zákon: "chladnou nádrží se myslí teplota < 40°C"

### v25.55d: REVERT — SOC bypass na L38/L72/L73 odstraněn (2026-03-22)

**Root cause bugu**: V rámci v25.55b jsem přidal `soc>=60` bypass na L38, L72, L73 (highSolDay/bigSolTom deferraly). To způsobilo, že v noci (SOC je VŽDY nízké přes noc = normální stav) se ignorovaly solární deferraly a NIBE se zapnulo ve 4h ráno za drahých hodin, přestože dnešní solární forecast je vysoký.
- **Zákon 8.2**: „pokud je solární výroba na daný den vysoká (>50kWh), NIBE se NESPUSTÍ"  
- **Zákon 8.3.4**: „cheaperAhead/bigSolarTomorrow odklady platí"
- **Fix**: SOC bypass z L38, L72, L73 kompletně odstraněn. Deferraly `highSolDay`/`bigSolTom` nyní opět fungují správně i v noci.

**Fix 3: Filtrace — min continuous run po NR restartu** (`filtrace-bazenu.json`, `filtrace_decision`):
- **Root cause**: Po NR restartu se `contStart` (continuous run tracking) resetuje na `now` → `contRunMin=0` → `minRunOk=false`. L197 (`!minRunOk`) pak blokoval vypnutí i když `met=true` (denní minimum splněno). Stejný pattern jako anti-cycling bug.
- **Zákon 10.1** (PRIORITA): „FILTRACE NESMÍ BĚŽET DÉLE, NEŽ JE POŽADOVÁNO"
- **Fix**: L197 doplněno o `&& !met` — když je minimum splněno, min continuous run protection neblokuje vypnutí.

### v25.54: Fix Law 5.0 — auto=OFF nesmí ovlivňovat charger (2026-03-20)

**Root cause**: V `manager-nabijeni-auta.json` (`main_logic_func`) se kontrola `!hlad` (auto nemá hlad → STOP) prováděla PŘED kontrolou `!auto` (automatizace OFF → NIC). Když uživatel vypnul automatizaci a `auto_ma_hlad=OFF`, manager přesto zastavil wallbox.

**Zákon 5.0**: „PŘI VYPNUTÉ AUTOMATIZACI NABÍJENÍ AUTA SE NIC NEOVLIVŇUJE — ANI CHARGER, ANI AMPÉRÁŽ — NIC."

**Fix**: Přesunuta kontrola `if(!auto) return null;` na **první místo** v rozhodovací logice, před jakýkoli jiný check (hlad, SOC, balancování). Když auto=OFF, manager okamžitě vrátí `null` a nic neposílá.

### v25.53: Fix opp balancing header display (2026-03-19)

**Root cause**: `opp_bal_check` neaktualizoval `input_datetime.last_pylontech_balanced` při opp < 3h (jen `bal_header_info` global, který je volatilní). Navíc `bal_svc_set_boolean` měl prázdnou konfiguraci — service call do HA se neprováděl.

**Fix 1: `opp_bal_check` VŽDY aktualizuje HA entity** (`fve-modes.json`):
- `input_datetime.last_pylontech_balanced` — VŽDY (pro header display)
- `input_boolean.pylontech_balancing_ok` — VŽDY (pro OK/NOK ikonu)
- `bal_header_info` global — VŽDY (s `qualifying` flag pro planner)
- `last_qualifying_balance_ts` global — jen při opp >= `force_stop_hours` (pro planner)

**Fix 2: Planner qualifying check** (`fve-orchestrator.json`, `4. Generování plánu`):
- Pokud `bal_header_info.passive && !qualifying` → planner ignoruje aktualizovaný datetime a používá `last_qualifying_balance_ts` pro výpočet `daysSinceBalance`
- Tím se zabrání posunu dalšího plánovaného balancingu při krátkém opp balancingu

**Zákon 12.5**: Header VŽDY zobrazuje poslední balancing datetime + OK/NOK. Posun dalšího plánovaného balancingu JEN při opp >= 3h.

### v25.52: Fix CP852 encoding corruption (2026-03-19)

**Root cause**: PowerShell `>` redirect při SSH stahování flows interpretuje UTF-8 bajty jako CP852 (český OEM codepage). Patch skripty pak zkopírovaly poškozené komentáře do gitu a deploy je nahrál na server.

**Fix**: Python `line.encode('cp852').decode('utf-8')` na serveru — 102 řádků opraveno ve 2 nodech (`44025571f9d270fb` config, `rf_plan_output_05` plan output). Server + git synchronizovány.

**Prevence**: NIKDY nepoužívat `ssh ... "cat file" > local_file`. Vždy base64 přenos nebo zpracování přímo na serveru.

**Smazána HA entita**: `input_number.balancing_force_stop_hours` — odstraněna z entity registry přes WebSocket API. Hodnota je přímo v `fve-config.json` jako `3`.

### v25.50: Sync balancing laws (2026-03-19)

**Fix 1: `balancing_force_stop_hours` fallback 2→3** (`fve-orchestrator.json`, Rozhodnutí o akci):
- Zákon 12.5: config default = 3h (bylo hardcoded 2)

**Fix 2: opp_bal_check conditional datetime** (`fve-modes.json`, opp_bal_check):
- Zákon 12.5: datetime update (posun dalšího plánovaného balancingu) JEN pokud pasivní monitoring trval ≥ `force_stop_hours` (3h)
- Pokud < 3h: aktualizuje se JEN `pylontech_balancing_ok` (OK/NOK), datetime se NEMĚNÍ

### v25.51: Config plain values + header oddělení (2026-03-19)

**Fix 1: Config `balancing_force_stop_hours`** (`fve-config.json`):
- Bylo: `getHAFloat("input_number.balancing_force_stop_hours", 2)` — HA entita
- Nyní: `3` — přímá hodnota v configu (zákon: NE HA entity, konfig!)
- Také: `balancing_min_solar_kwh: 2` → `3` (zákon 12.5)

**Fix 2: Oddělení header info od planner datetime**:
- `global.set("bal_header_info", {...})` — VŽDY se uloží při opp balancingu (pro header)
- `input_datetime.last_pylontech_balanced` — aktualizuje se JEN pokud `durationH >= force_stop_hours` (pro planner)
- Plan output čte `bal_header_info` global (pokud novější než entita) → header vždy aktuální

### v25.48: 3 opravy topení (2026-03-19)

**BUG 1: Patrony SOC 95→90** (`fve-config.json`):
- `topeni_min_soc_patron: 95` → `90` (zákon 8.5: SOC ≥ 90%)

**BUG 2: Oběhové čerpadlo neběželo** (`fve-heating.json`, `rf_htg_decide2`):
- `oTgt = h.effTgt` → `oTgt = h.isNight ? h.effTgt : h.tgtT`
- Zákon 8.4: ve dne cíl = nastavená teplota (ne effTgt s highSolSniz)

**BUG 3: Auto OFF vypínalo patrony** (`fve-heating.json`, `rf_htg_decide2`):
- Blok `if(!h.auto)` dělal safety shutdown patron → odstraněn
- Zákon 8.2: "Automatizace OFF → ABSOLUTNĚ na nic nesahat"

### v25.32: Korekce nabíjení auta ze solaru — range-based + charger stop (2026-03-18)

**BUG 1: Deploy přepsal uživatelské timing změny** (`nabijeni-auta-slunce.json`):
- Uživatel změnil heartbeat a delay z 20s na 5s na serveru → deploy přepsal zpět na 20s
- FIX: git aktualizován na 5s (inject + delay), cooldown 15s→4s

**BUG 2: Oscilace amperáže 8↔9A** (target-based control):
- CHRG mode: bW=2325>TBW+DB=1500 → +1A → grid>200 → -1A → cyklus
- FIX: Range-based control (stejný princip jako patrony v25.31):
  - CHRG: `0 ≤ bW ≤ 2000W` → stable; increase jen pokud `gridW < gMax/2`
  - DRAIN: `bW > 300` → +1A; `bW < -2500` → -1A; jinak stable

**BUG 3: Korekce při tA<6 jen vypla boolean, nestopla charger**:
- Switch "Amperace<6?" output 1 → jen `input_boolean.nastavuj_amperaci_chargeru_solar = OFF`
- Charger běžel dál na 8A, grid 3.9kW (NIBE + auto)
- FIX: přidán wire na "Vypni nabíjení" (wallbox stop) do output 1

### v25.31: Drain mode range-based control — konec oscilace (2026-03-17)

**BUG: Patrony oscilují 2↔3 fáze v drain mode** (`fve-heating.json`, `pat_korekce_func`):
- Root cause: target-based control (dTgt=-1500W, DB=500W) s krokem 3kW nemůže trefit cíl
  - 2 fáze: bCh=-500W → err=1000>500 → přidej F3
  - 3 fáze: bCh=-3500W → err=-2000<-500 → odeber F3 → cyklus se opakuje
- FIX: **Range-based** logika místo target-based:
  - `bCh > 300W` (nabíjí) → charge bypass přidá fázi (bypass cooldown)
  - `bCh < -2500W` (příliš vybíjí) → odeber fázi
  - `-2500 ≤ bCh ≤ 300` → **STABILNÍ** (žádná akce)
- Monitoring: 2 fáze stabilní 60+s, baterie -1443W (vybíjí ~1.4kW), grid 33W ≈ 0 ✅

### v25.30: Charge bypass — okamžitá reakce na nabíjení (2026-03-17)

**BUG: SOC 99%, baterie +291W (nabíjí), korekce nereaguje** (`fve-heating.json`, `pat_korekce_func`):
- Root cause: cooldown 30s + dead band bránily okamžité reakci
- FIX: nový blok PŘED cooldown — `soc>=95% && bCh>300 && act>0` → okamžitě přidej fázi
- Drain target default 1000→1500W (zákon: 1-2kWh)

### v25.29: Patrony korekce drain — dead band fix (2026-03-17)

**BUG: Korekce nepřidávala fáze v drain mode** (`fve-heating.json`, `pat_korekce_func`):
- Zákon 8.5: "SOC >=95% → baterie se VYBÍJÍ ~1kWh" (drain mode, obdobně jako nabíjení auta ze solaru)
- Root cause: `DB = max(DB_CFG=500, FAZE_W/2=1500) = 1500W` — dead band 1500W příliš velký
- S dTgt=-1000W a bCh=+198W: err=1198 < DB=1500 → žádná akce → fáze se nepřidávaly
- FIX: `DB_DR = DB_CFG` (500W) pro drain mode — menší dead band umožňuje reakci
- Monitoring: 1→2→3 fáze přidány, baterie -2756W, tank 40→45°C, grid ≈0W ✅

### v25.28: Patrony korekce — sell default 3 + drainBypass (2026-03-17)

**BUG: Patrony oscilace — htg_decide2 zapne, pat_korekce_func za 20s vypne** (`fve-heating.json`, `pat_korekce_func`):
- Root cause: `topeni_patron_max_sell_price||2` v korekci (htg_decide2 měl ||3) + chyběl drainBypass
- Sell 2.48 CZK: htg_decide2 OK (≤3) → p1_on, korekce FAIL (>2) → p1_off → oscilace 60s
- FIX: sell default `||3` + `soc>=DRAIN_P` bypass v sell price check
- Monitoring: patrona fáze 1 ON stabilně, grid 0W, baterie +198W ✅

### v25.27: Zákon 8.5 — 3h pravidlo + sell price 3 CZK + PM 0.2 (2026-03-17)

**Opravy dle aktualizovaných zákonů** (`fve-heating.json`, `rf_htg_decide2`):
- **3h pravidlo:** podmínka `tankT < TANK_3H` (35°C, konfig.) — pokud nádrž je nad 35°C, 3h pravidlo NEplatí
- **Sell price default:** 2 → 3 CZK (zákon 8.5: "prodejni cena > 3 CZK → ne patrony")
- **PM (patrony margin):** 0.3 → 0.2 (zákon 8.5: "0.2 stupne pod stanovenou teplotou")

### v25.26: Patrony — drain bypass pro sell price check (2026-03-17)

**KONFLIKT v zákoně 8.5: sell price vs. "nikam dát energii"** (`fve-heating.json`, `rf_htg_decide2`):
- Zákon 8.5: "Uz nikam nemame dat solarni energii → patrony" vs. "prodejni cena > 2 CZK → ne patrony"
- Root cause: `patSellOk = (sellPrice <= 2)` blokoval patrony i při SOC 99% — baterie plná, auto neběží, tank 40°C → solár se prodával za 2.08 CZK místo ohřevu nádrže
- FIX: `drainBypass = h.soc >= DRAIN_P` (95%) — bypass sell price check když baterie plná
- `patMohou = (patSellOk || drainBypass) && patSolOk && ...`
- Výsledek: při SOC ≥ 95% patrony ohřejí nádrž místo prodeje za nízkou cenu

### v25.25: Solární nabíjení auta — odstranění GRID_DRAIN tolerance (2026-03-17)

**BUG: Korekční smyčka tolerovala 500W grid draw v drain módu** (`nabijeni-auta-slunce.json`, `788e188fae8d1fca`):
- Zákon 5.1: "NIKDY NESMI NASTAT, ZE SE BUDE BRAT ENERGIE ZE SITE!!! NIKDY!!!"
- Root cause: `GRID_DRAIN=500W` — když SOC ≥ 95%, `gMax=GRID_DRAIN` místo `GRID_MAX` (200W)
- Uživatel viděl ~500W grid draw při solárním nabíjení s SOC 99%
- FIX: `gMax=GRID_MAX` vždy — stejný threshold 200W pro všechny SOC režimy

### v25.24: Blokace vybíjení — odebrání "Nab. auta" z blokaceText (2026-03-17)

**BUG: Dashboard ukazoval "Blokace: ANO - Nab. auta" při solárním nabíjení** (`fve-orchestrator.json`, `c36915a8599c5282` Kontrola podmínek):
- Zákon 5.1: "Pri nabijeni auta ze solaru NIKDY NESMI BYT BLOKOVANE VYBIJENI BATERIE"
- Root cause: `if(autoN)bI.push("Nab. auta")` přidávalo auto do blokace textu, i když mode logika (NORMAL, SOLÁRNÍ NABÍJENÍ) vybíjení NEblokuje
- FIX: odstraněn `autoN` z `bI[]` pole — blokaceText nyní správně ukazuje "NE" při solárním nabíjení auta

### v25.23: Topení — oběhové effTgt + h.lvl cross-day + odstranění horní hystereze (2026-03-17)

**BUG 1: Oběhové čerpadlo běželo nad cílovou teplotou** (`fve-heating.json`, `rf_htg_decide2`):
- Zákon 8.4: "ON pokud teplota domu < cíl" — dům 23.4°C, cíl 23.3°C → mělo být OFF
- Root cause 1: `oTgt` používalo `h.tgtT` místo `h.effTgt` → ignorovalo highSolDay snížení
- Root cause 2: horní hystereze `nHO = obehOn ? (inT < oTgt + 0.2)` držela oběhové ON 0.2°C nad cílem
- FIX: `oTgt = h.effTgt` (respektuje highSolDay + noční snížení)
- FIX: `nHO = h.inT < oTgt` — přísná podmínka bez horní hystereze (zákon 8.4)

**BUG 2: h.lvl v topení používalo per-day levely** (`rf_htg_read_001`):
- Zákon 8.2: cross-day levely pro topení (analogie k šetření)
- FIX: `h.lvl` se počítá z plánu pomocí cross-day rankingu podle skutečné buy ceny
- Fallback na per-day levely pokud plán není k dispozici

**Filtrace: min nepřetržitý běh + odstranění priority auta** (`filtrace-bazenu.json`, `filtrace_decision`):
- Zákon 10.1 (nový): filtrace musí běžet v kuse min 15 min (`filtrace_min_run_min: 15` v configu)
- Zákon 10.5 (odebrán): blokace `auto_ma_hlad + SOC < 85%` zrušena
- FIX: `minRunOk` tracking — pokud filtrace běží < 15 min, žádná OFF akce (kromě pool freeze < 2°C)
- FIX: odstraněna proměnná `carP` a všech 5 `&& !carP` podmínek

### v25.22: FVE Plan — cross-day cenový ranking pro šetřit mód (2026-03-16)

**BUG: levelBuy je per-day rank (1-24), nesrovnatelný přes půlnoc** (`fve-orchestrator.json`, `rf_cena_discharge2`):
- Zákon 4.3: "VŽDY ŠETŘÍME ZA CO NEJNIŽŠÍ CENY, pozor na přechod přes půlnoc"
- Root cause: `levelBuy` = rank v rámci jednoho dne. Hodina 23 dnes (3.75 CZK, nejlevnější) měla level 13 (→ DRAHÁ), zatímco hodina 1 zítra (3.93 CZK, dražší) měla level 3 (→ LEVNÁ)
- 9 míst v kódu používalo `levelBuy` pro threshold porovnání (`>=DRAHA`, `<=LEVNA`)
- FIX: Po sestavení `hp[]` přepočet levelBuy jako cross-day rank seřazený podle skutečné buy ceny
- Originální per-day level uložen jako `origLevel` pro dashboard display
- `rf_gen_plan_0004`: `priceLevel: pd.origLevel || pd.levelBuy` pro zobrazení
- Výsledek: hodina 23 (3.75 CZK) správně → level 2 (LEVNÁ) → šetřit místo vybíjení

### v25.21: Topení — hystereze NIBE/oběhové, cooldown 3min (2026-03-16)

**BUG: NIBE a oběhové čerpadlo se zapínaly/vypínaly synchronně** (`fve-heating.json`):
- Root cause: oba závisí na `inT < tgtT` BEZ hystereze → toggle na přesně stejné teplotě
- FIX 1: `needH` hystereze — pokud NIBE topí (`h.nibeOn`), needH=true dokud `inT < effTgt + HYST` (0.2°C, konfigurovatelné `topeni_hystereze`)
- FIX 2: `nHO` hystereze — pokud oběhové běží (`h.obehOn`), nHO=true dokud `inT < oTgt + HYST`
- FIX 3: NIBE cooldown default 1→3 min (zákon 8.3: "min. 3 minut mezi přepnutími")
- FIX 4: Tank heating rozšířen z `lvl<=LEVNA` na `!isDraha` — cheaperAhead deferral optimalizuje na nejlevnější hodinu
- FIX 5: `mustHeatByPrice` a `mustHeatFinal` používaly raw `h.inT<h.tgtT` BEZ hystereze → NIBE se vypínalo hned po zapnutí oběhového (0.1°C nárůst stačil k flipu mustHeatByPrice=false → isDraha fallback → nibe_off)
- FIX 5: Obě proměnné nyní používají `needH` (s hysterezí) místo `h.inT<h.tgtT`
- Výsledek: NIBE a oběhové jsou nyní nezávislé (zákon 8.4) — každý má vlastní stav pro hysterezi

### v25.20: Topení — proaktivní ohřev nádrže za levnou cenu (2026-03-15)

**Nádrž se neohřívala, když dům byl natopen ale solar nízký** (`fve-heating.json`, `rf_htg_decide2`):
- Zákon 8.2+8.3.5: proaktivní ohřev nádrže za levnou cenu při nízkém solaru
- FIX: `!needH && tankT < maxTank && !isDraha && !highSolDay && !patMohou → mod="NIBE"`
- cheaperAhead deferral optimalizuje na nejlevnější dostupnou hodinu

**Plan reason: "(NIBE topí)" jen když NIBE skutečně topí** (`fve-orchestrator.json`, `rf_prep_params_01`):
- BUG: `nibeK` se počítal i když dům nepotřeboval topit (tgT-inT > -0.5 příliš široký)
- FIX: `nibeK` jen pokud `switch.nibe_topeni=on` OR `inT < tgT` (skutečná potřeba)

### v25.19: Filtrace — opravy logiky + persistance (2026-03-14)

**Filtrace: met → VŽDY OFF, bez výjimek** (`filtrace-bazenu.json`):
- Zákon: "FILTRACE NESMÍ BĚŽET DÉLE, NEŽ JE POŽADOVÁNO" (10.1)
- `if (met) { act = "off"; }` — po splnění minima = STOP, bez ohledu na přebytek
- Solar surplus ON podmínka přidán `!met` check: `if (gSurp && !carP && !met)` — surplus zapne filtraci POUZE pokud minimum NENÍ splněno

**Filtrace: filt_run persistance přes NR restart**:
- BUG: `flow.set("filt_run")` = in-memory, ztráta counteru při NR restartu → filtrace běžela znovu od 0
- FIX: counter se zapisuje do `/config/filt_persist.json` přes `global.get("fs").writeFileSync()`
- Na NR restart se načte z persist souboru → counter přežije restart
- Prerekvizita: `fs:require("fs")` přidáno do `functionGlobalContext` v NR `settings.js`

**Filtrace: pool freeze check** (zákon 10.1):
- Nový konfig parametr `filtrace_min_pool_temp` (výchozí 2°C)
- Pokud teplota bazénu < 2°C → filtrace se NESPUSTÍ / VYPNE
- Obě větve (ON/OFF) kontrolují freeze podmínku

**Dashboard status filtrace** (zákon 10.6):
- `filtrace_decision` exportuje `{run, minReq, met, remaining}` do `global.filtrace_status`
- Oba write paths v orchestratoru zahrnují `filtrace_status` v `fve_plan.json`
- `dashboard_fve_plan.md`: zobrazuje `Bazén: ✅ OK (XX/YY min)` nebo `Bazén: ❌ -ZZ min`

**History learning persistance** (`fve-history-learning.json`):
- BUG: `require("fs")` nefunguje v NR function nodes (není v scope)
- FIX: všechny 3 nody (`fve_history_store`, `fve_history_predict_calc`, `fve_history_analyze_calc`) přepsány na `global.get("fs")` — čte `fs` z `functionGlobalContext`
- Persist soubor: `/config/consumption_history.json`

**NR settings.js**:
- Přidáno `fs:require("fs")` do `functionGlobalContext` → dostupné ve všech function nodes jako `global.get("fs")`

---

## 10. Solární instalace

- **Výkon**: 17 kWp, **Lokace**: Horoušany (50.10°N, 14.74°E)
- **Azimut**: 190° (JZ), **Sklon**: 45°
- **Solární křivka**: 5:00–18:00, max 12:00, silnější odpoledne (JZ)
