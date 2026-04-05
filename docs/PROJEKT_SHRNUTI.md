# FVE Automatizace — Kontext projektu

> **Living document** — aktuální stav systému. Po každé změně PŘEPSAT relevantní sekci.
> Poslední aktualizace: 2026-04-05 (v25.80 implementace módu záporná nákupní cena §4.9.2 bod 7; v25.79 fix hladu auta + ultra levná vybíjení; v25.78 auto nabíjení při zákazu přetoků; v25.77 přejmenování POZADAVKY → ZAKONY.TXT; v25.76 filtrace)
>
> **⚠️ VŠECHNY požadavky, zákony a pravidla jsou v `User inputs/ZAKONY.TXT`.**
> Tento soubor obsahuje pouze technický kontext a stav systému — NE požadavky.
>
> **Dokumentace v `docs/` (účel — bez zbytečných tabulek):**
> - **`PROJEKT_SHRNUTI.md`** (tento soubor) — hlavní technický kontext pro AI a vývoj.
> - **`UZIVATELSKA_PRIRUCKA.md`** — pohled uživatele (senzory, módy).
> - **`KONVERZACE_KONTEXT.md`** — starší poznámky; **nízká priorita**, při rozporu platí zákony (`ZAKONY.TXT`) + tento soubor.
> - **`AI_PREHLED_TABULEK.md`** — **jediný** soubor, kam AI **na tvé vyžádání v chatu** doplní krátký výstup; neobsahuje „pravdu“ o zákonech (ta je v `ZAKONY.TXT`).
> - **`TOPENI_POZADAVKY.md`** — jen **entity + `fve_config` klíče**; žádná duplicitní pravidla — zákony výhradně v **`ZAKONY.TXT`**.
>
> **Pravidla pro AI (POVINNÁ při KAŽDÉM promptu):**
> - **VŽDY komunikovat v ČEŠTINĚ** — základní pravidlo
> - **Trvalá pravidla v Cursoru** jsou v `.cursor/rules/ha-problemy.mdc` (`alwaysApply`) — soulad se **`ZAKONY.TXT`**, **žádné nasazování v rozporu** (nejprve vysvětlit konflikt).
> - **NA ZAČÁTKU úkolu**: `User inputs/ZAKONY.TXT` + `User inputs/problemy.txt` + **tento soubor**; `UZIVATELSKA_PRIRUCKA.md` dle tématu; `AI_PREHLED_TABULEK.md` jen pokud jde o doplnění výstupu, který tam má skončit.
> - **ABSOLUTNÍ ZÁKON 1.2 + 2.3**: VŽDY má přednost stav NR na serveru HA před lokální verzí. NIKDY nepřepisovat stav v HA lokální verzí.
> - **PŘED úpravou flow**: stáhnout aktuální flows ze serveru (`ssh ... "cat flows.json"`) — SERVEROVÁ verze = PRAVDA (flows, nody, layout, parametry, config — VŠECHNO)
> - **Deploy.sh nahrazuje CELÉ taby z gitu** → git MUSÍ obsahovat aktuální serverovou verzi + moje cílené změny
> - Před deploymentem ověřit soulad se VŠEMI zákony
> - Po deploymentu: ověřit HA stavy, NR logy, grid draw
> - **⚠️ DEPLOY WORKFLOW (§ 2.5 — ABSOLUTNÍ ZÁKON):**
>   1. Sync VŠECH tabů server→git (stáhnout flows ze serveru, uložit do lokálních JSON)
>   2. Aplikovat fixy LOKÁLNĚ na git soubory
>   3. `git commit` lokálně (BEZ push!)
>   4. `git push` na GitHub
>   5. Deploy přes SSH (`deploy.sh --no-ha`) — VŽDY `--no-ha` pokud měním jen NR flows!
>   6. **OVĚŘIT** nasazení (plán, stavy, logy, kódování)
>   7. Teprve po potvrzení úspěchu → hotovo
>   **NIKDY nepushovat PŘED ověřením nasazení!**
>   **deploy.sh přepínače:** `--no-ha` (jen NR, BEZ HA restartu — PREFEROVAT!), `--with-ha` (default), `--force`, `--branch=xyz`
> - `User inputs/ZAKONY.TXT` NESMÍ AI MĚNIT — edituje výhradně uživatel
> - Aktualizovat tento soubor po každém úspěšném nasazení
> - Po sobě VŽDY uklidit dočasné soubory (`_*.py`, `_*.js`, `_fix_*`, `_check_*`) lokálně i na serveru
>
> **Příkazy — pravidla (POVINNÁ, prevence zaseknutí):**
> - NIKDY `Start-Sleep` — uživatel nevidí nic. Použít non-blocking command + command_status s WaitDurationSeconds.
> - NIKDY `python3 -c "..."` přes SSH — escapování se zasekne. VŽDY heredoc: `<< 'PYEOF' ... PYEOF`
> - **POZOR na velké heredoc skripty** — pokud Python skript obsahuje assert, speciální znaky, uvozovky nebo `\n`:
>   1. NEJPRVE zapsat skript na server: `ssh ... "sudo tee /tmp/skript.py > /dev/null << 'PYEOF' ... PYEOF"`
>   2. POTOM spustit: `ssh ... "sudo python3 /tmp/skript.py"`
>   3. NAKONEC smazat: `ssh ... "sudo rm -f /tmp/skript.py"`
>   - Důvod: velké heredoc s inline `python3 <<` se zasekne kvůli escape problémům v PowerShell → uživatel musí ručně cancelovat
> - NIKDY `2>/dev/null` — skrývá chyby, uživatel nevidí co se děje.
> - NIKDY dlouhé pipe chains `ssh ... | node -e "..."` — PS opakuje command, vypadá zmateně. Zpracovat na serveru, stáhnout výsledek.
> - `sudo docker restart` vždy NON-BLOCKING — trvá 30s. Spustit non-blocking, pak check status.
> - NR restart: `sudo bash -c 'source /etc/profile.d/homeassistant.sh 2>/dev/null; ha apps restart a0d7b954_nodered'` (ne `ha addons` — deprecated)
> - File transfer: base64 encode na serveru → `ssh cat` → lokální soubor. Ne `Get-Content | ssh`. SCP nefunguje (subsystem error).
> - Dlouhé SSH příkazy rozdělit na víc kroků s echo progress markers.
> - Být samostatný — dokončit práci BEZ nutnosti interakce (cancel, klikání). Uživatel nehlídá terminál.
>
> **Komunikační kanál:**
> - Ruční vstup uživatele do repa: **`User inputs/problemy.txt`** (zadání) a **`User inputs/ZAKONY.TXT`** (zákony — edituje výhradně uživatel). Nic dalšího v projektu kvůli běžné práci vyplňovat nemusíš.
> - AI čte `problemy.txt` na začátku úkolu; odpovídá v chatu a provádí opravy — **NIKDY nepíše do `problemy.txt`**

---

## 1. Co tento systém dělá

Automatizuje FVE elektrárnu (17 kWp), tepelné čerpadlo NIBE, nabíjení elektroaut a dalších spotřebičů v Home Assistant + Node-RED na základě spotových cen elektřiny, solární výroby a aktuální spotřeby.

### 1.1 SOC baterie ve „solárních hodinách“ — právo vs. ZAKONY.TXT

- Soubor `User inputs/ZAKONY.TXT` jsou **pravidla a cíle tohoto projektu** (prioritizace spotřebičů, módy Victronu, plán 12 h, ekonomika). **Neobsahují odkaz na konkrétní paragrafy zákonů ČR**; u „zákonů“ v názvu jde o závazná pravidla *pro kód a provoz automatiky*.
- **Úroveň státní regulace** (obecně): u domácí FVE s akumulací typicky rozhoduje **připojení k distribuční soustavě** (dovolený výkon / odkup / měření), **technické normy** (bezpečné připojení zařízení) a **smlouva s operátorem distribuce**. **Samotná výška nabití baterie ve dne** obvykle **není** předmětem zákazu ve stylu „nesmíte mít v poledne vysoký SOC“. Pro jistotu u konkrétního případech platí jen **text připojení / obchodní podmínky** u vašeho DS a typ měření (např. limity přetoku, případné požadavky na řízení výkonu).
- **Uvnitř projektu** (`ZAKONY.TXT` § 4.9): cíl **cca 25 % SOC před první solární hodinou** je **strategická rezerva** (místo v akumulátoru na dopolední výrobu), ne požadavek „ve dne musí být baterie prázdná“. V § 4.9.1 mají **solární hodiny SOC v simulaci růst** — tedy **vysoký SOC ve dne při dobré výrobě je konzistentní** s pravidly plánu, pokud nedochází k nežádoucímu přetoku přes limity systému (to řeší mód **Zákaz přetoků** a konfigurace `max_feed_in` atd., ne „limit SOC“).
- **Závěr pro vývoj**: žádná oprava flow **jen proto, že je SOC ve dne vysoký**, z dokumentovaných pravidel neplyne. Pokud by něco odporovalo **připojovacím podmínkám**, je třeba je mít konkrétně vyjmenované (např. limit příkonu / exportu), ne odhad z SOC.
- **Častý omyl — „25 % na konci první solární hodiny“**: V § 4.9 je text **„před první solární hodinou“** (vstup do solárního okna), ne „po první solární hodině“. **Během** solárních hodin má simulace SOC podle § 4.9.1 **růst** — tedy po začátku slunce je **normální**, že SOC už není ~25 %, ale vyšší.
- **Co z toho dělá kód** (`fve-orchestrator.json`, node „4. Generování plánu“, `cM`): proměnná `C.socN` (z noční rezervy / marginu) se v kombinaci s `min_soc` používá jako práh typu **`minSoc + socN`** (typicky 20 %+5 % → **cca 25 %**) pro rozhodování **solární hodina vs. šetřit / vybíjet** — jde o **ochranný práh v plánovači**, ne o tvrdý požadavek „vždy vybit na 25 % před východem slunce“. Plán začíná od **aktuálního SOC** a dál ekonomikou (NORMAL / ŠETŘIT / …); žádná samostatná optimalizace „vynuť přesně 25 % v hodině před `solS`“ v tomto node není.

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
`deploy.sh` **výchozí chování (§ 2.1):** zkopíruje HA YAML (`configuration`, šablony, …), sloučí NR flows, restartuje Node-RED **a restartuje Home Assistant Core** — aby se projevily nové `template` senzory, volby `input_select`, atd.

Rychlý deploy **jen Node-RED** bez restartu Core: `bash deploy.sh --no-ha` (potom případně ručně *Vývojářské nástroje → YAML → Znovu načíst šablony*).

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
- Fix: `topeni_min_soc_patron` 90→95 (dle ZAKONY.TXT)

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
- Zákon 10.5 aktualizován v ZAKONY.TXT

**Zákon 8.5 — pravidlo 3 hodin** (nový zákon v ZAKONY.TXT):
- Pokud aktuální hodina ≤ 3h před poslední solární hodinou → patrony se nespustí, NIBE preferováno
- Důvod: patrony nestihnou dostatečně natopil nádrž před koncem solární výroby

### v25.61–63: PRODÁVAT — stabilní cílové SOC (2026-03-23)

**Problém 1: Baterie se drainovala na minSOC při prodeji**
- Trim (KROK 7c) počítal rovnoměrně 5% drain/hodina, ale PRODÁVAT drainuje ~21%/hodina
- Výsledek: baterie na 20% místo zachování rezervy na noc

**Problém 2: Cílové SOC v plánu driftovalo**
- Každých 15s přepočet dal jiný cíl → nestabilní plán

**Problém 3: Oscilace PRODÁVAT ↔ NORMAL**
- `eP` check projektoval SOC pro celý zbytek hodiny → při 30+ min selhával → flip na NORMAL

**Fix v25.61** (node "2. Cenová mapa + discharge"):
- Nový KROK 7.5: výpočet `sellTarget` = stabilní SOC pod které se nikdy neprodá
- Vychází z noční spotřeby domu do solárního startu + marže
- `sellTarget = max(minSoc + nResPct, minSoc + nightNeedSoc + nMargin)`

**Fix v25.61** (node "3. Arbitráž + trim"):
- Trim používá `sellTarget` jako efektivní start místo `cSoc`
- Nejlevnější noční hodiny se ořežou na ŠETŘIT

**Fix v25.61** (node "4. Generování plánu"):
- `cM()`: `soc > sellTarget` místo `soc > minSoc + nResPct`
- `sim()`: floor na `sellTarget` místo `minSoc` pro PRODÁVAT
- Reason: `"SOC XX% (cíl YY%)"` — stabilní zobrazení

**Fix v25.63** (node "4. Generování plánu"):
- Odstraněn redundantní `eP >= sellTarget` check — způsoboval oscilaci
- Stačí vstupní `soc > sellTarget` + `sim()` floor

**Zákon 4.5 aktualizován** v ZAKONY.TXT — business-user-friendly popis sell target logiky.

### v25.64–65: Solar guard + heating fixes (2026-03-24)

**v25.64 — Orchestrátor: Solar guard SOC check**
- `cM()` line 52: solar guard kontroluje výsledné SOC `R(soc+sg)` místo aktuálního `soc`
- `cM()` line 56: solar+drahá kontroluje `R(soc+sg)>=minSoc+socN`
- `cM()` lines 59,62: non-solar discharge kontroluje `R(soc-socN*f)>=minSoc+socN`
- Prevence zbytečného vybíjení když by SOC kleslo pod 25%

**v25.64 — Topení: highSolDay defer i v noci**
- BUG: `fve-heating.json` line 95 + 205 vyžadovaly `h.isSol` pro highSolDay defer
- Ve 4 ráno `isSol=false` → NIBE topila ze sítě za 3.9 Kč/kWh přes forecast 65 kWh
- FIX: odstraněn `h.isSol` z obou podmínek — defer funguje i v noci
- Bezpečnost: `_canDeferHSD` (inT >= safeT) zajistí NIBE start při poklesu teploty

**v25.65 — Patrony: pravidlo poslední solární hodiny**
- Nové pravidlo (zákon 8.5): poslední solární hodina + zbývající solar < 4 kWh + bez zákazu přetoků → patrony OFF
- Důvod: lepší nechat baterii nabít na 100% SOC pro noc než vybíjet přes patrony
- Config: `topeni_patron_last_sol_min_kwh` (default 4)
- Přepisuje i NIBE+Patrony mód (NIBE pokračuje, patrony stop)

### Incidenty a poučení z 2026-03-31

**INCIDENT 1: Deploy přepsal "Automatizuj ostatní"**
- Příčina: Git měl starou verzi ostatni.json (0 nodů). Uživatel měl 29 nodů JEN na serveru.
  Deploy.sh nahradil serverové nody starými z gitu → 9 nodů zmizelo + broken encoding (Světla → Sv─Ťtla).
- Náprava: Obnoveno ze zálohy `.flows.json.backup`, synced VŠECH 13 tabů server→git.
- **Poučení**: VŽDY sync server→git PŘED úpravou. Git MUSÍ být aktuální kopie serveru.

**INCIDENT 2: Zbytečný HA restart**
- Příčina: `deploy.sh` bez `--no-ha` → vždy restartuje HA Core (default `RESTART_HA=true`).
  Pro NR-only změny stačí `deploy.sh --no-ha` — restartuje jen NR addon.
- **Poučení**: VŽDY `--no-ha` pokud měním jen NR flows.

**INCIDENT 3: Git push před ověřením**
- Příčina: Porušení §2.5 — pushoval jsem do gitu PŘED ověřením, že nasazení je OK.
- **Poučení**: Push AŽ PO ověření (NR logy, HA stavy, kódování).

**v25.77 — Přejmenování zákonů: `POZADAVKY.TXT` → `ZAKONY.TXT` (2026-04-02)**
- Jediný soubor zákonů projektu je nyní **`User inputs/ZAKONY.TXT`** (obsah beze změny názvu uvnitř souboru).
- Aktualizovány odkazy: `.cursor/rules/ha-problemy.mdc`, `docs/*`, `README.md`, `.windsurf/workflows/deploy.md`.
- Git: odstraněn track `POZADAVKY.TXT`, přidán `ZAKONY.TXT`.

**v25.78 — Auto nabíjení při zákazu přetoků + vysokém SOC (2026-04-03)**
- **Problém**: Při `zakaz_pretoku` (záporná prodejní cena), SOC≥95 % a solární výrobě manager nabíjení auta nespouštěl solární nabíjení — vyžadoval `fve_dostupny_prebytek > 4000W`, ale při zákazu přetoků přebytek nízký (baterie plná, export blokovaný).
- **Zákon**: §4.6 — při SOC≥95 % a nemožnosti exportu → energii do spotřebičů dle priorit; §5.1 — solární nabíjení auta; §1 — auto priorita 2.
- **Fix** (`manager-nabijeni-auta.json`, `main_logic_func`): nový blok před `solCyklus` check:
  `zakaz_pretoku + SOC≥drain_prah(95%) + solar>1kW + gridDraw<200W → SLUNCE`
- Grid draw kontrola (`_gridW < nabijeni_auta_max_grid_w`) zabraňuje spuštění když dům už bere hodně ze sítě (prevence oscilace zapnout/vypnout).
- Deploy: `--no-ha`, commity `44d6839` + `25498b4`.

**v25.76 — Filtrace: měření času i při vypnuté automatizaci (2026-04-02)**
- **Problém**: Gate „Automatizovat filtraci?“ posílal zprávu při OFF automatizace na prázdný výstup → `filtrace_decision` se nespouštěla → `filt_run` / `global.filtrace_status` neodpovídaly ručnímu běhu čerpadla (dashboard „Bazén: XX/YY min“).
- **Zákon**: `ZAKONY.TXT` § 10 — do celkového času se započítá veškerá filtrace včetně ručního spuštění.
- **Fix** (`filtrace-bazenu.json`): oba výstupy gate vedou na `filtrace_st_state`; do zprávy `automatizovatFiltrace`; v `filtrace_decision` při `autoOn === false` se nevolají služby ON/OFF, jen se pokračuje v inkrementu `filt_run`, persist `filt_persist` a export `filtrace_status`.
- **Deploy**: `deploy.sh --no-ha`; git `main` commit `08302fe`. Post-deploy ověření: `flows.json` na serveru obsahuje `autoOn` / `automatizovatFiltrace` (grep).
- **Poznámka**: `ha apps logs …` z běžné SSH session bez tokenu může vracet 401 — logy NR ověřit v UI doplňku nebo přes API s tokenem.
- **Monitoring (2026-04-02, po nasazení)**: Home Assistant API — `sensor.fve_plan_data` → `filtrace_status` platné (např. `run`/`minReq`/`met`); SSH `ha apps info a0d7b954_nodered` → `state: started`; na serveru smazány dočasné `/tmp/check*.py` dle § 2.4.

**v25.75 — NIBE spotřeba v nočních hodinách simulace plánu (2026-04-01)**
- BUG: spotrebovaZtrataProc (nesluneční hodiny) nepřičítala NIBE spotřebu. Plán ukazoval pokles
  SOC jen ~5%/h (spotřeba domu), ale NIBE v levné noční hodině přidává 7 kWh (→ dalších ~25% SOC).
- FIX v rf_gen_plan_0004:
  1. spotrebovaZtrataProc přijímá level parametr, přičítá NIBE v levných hodinách (level<DRAHA)
  2. nibeVNoci flag + "(NIBE topí)" reason v nočních hodinách
  3. Consumption cap zvýšen z dayCons/4 na dayCons/2 (umožňuje NIBE peak 7 kWh + spotřeba)
- Pravidla: §4.9.1 ř.255-262 — NIBE jen v levných hodinách (§8.3: v drahých NIBE netopí)
- NIBE se nepřičítá pokud historický log má data (už obsahuje NIBE v průměru)
- Soubor: fve-orchestrator.json (node rf_gen_plan_0004)

**v25.74 — Fix trim logiky — zbytečné Šetřit místo vybíjení baterie (2026-04-01)**
- BUG: Trim v rf_arb_trimming_3 používal `sellTarget` (§4.5 cíl pro PRODEJ) jako základ pro projected
  end SOC. Tím odebíral levné hodiny z discharge plánu → Šetřit (kupuje ze sítě za 4+ Kč) místo
  NORMAL (baterie pokryje spotřebu zadarmo). Porušení §4.9.
- FIX: `(x.sellTarget||x.cSoc)` → `x.cSoc` (4 výskyty). sellTarget zůstává pro PRODEJ v kroku 4.
- DOPAD: Plán vybíjí baterii ve všech hodinách kde je to ekonomicky výhodné. Solar další den dobije.
- Soubor: fve-orchestrator.json (node rf_arb_trimming_3)

**v25.73 — Fix fve_dostupny_prebytek ukazoval výrobu místo přebytku (2026-04-01)**
- BUG: `template_sensors.yaml` sensor `fve_rozdil_vyroby_a_spotreby` četl neexistující entity:
  - `sensor.ac_loads_L1/L2/L3` → neexistují, float(0)=0 → spotřeba=0
  - `sensor.battery_power_plus` → neexistuje, float(0)=0 → nabíjení=0
  - Výsledek: přebytek = výroba (4973W místo reálných ~293W)
- DOPAD: manager nabíjení auta spouštěl solární nabíjení i když výroba nestačila na 6A + spotřebu domu
- FIX: opraveny entity IDs na `sensor.ac_loads/ac_loads_2/ac_loads_3` + `sensor.nabijeni_baterii_plus`
- Deploy: s HA restartem (template sensor změna), ověřeno — sensor teď ukazuje reálný přebytek

**v25.72 — Pravidlo posledních solárních hodin pro auto + patrony (2026-04-01)**
- NOVÝ §5.2 v zákonech: v posledních N solárních hodinách (config `posledni_solarni_hodiny: 2`)
  se auto NENABÍJÍ ze solaru a patrony se NEVYPUSTÍ — přednost má nabití baterie na 100% SOC
- FIX 1: `fve-config.json` — nový parametr `posledni_solarni_hodiny: 2`
- FIX 2: `rf_htg_decide2` ř.118 — `hToLastSol <= 0` → `hToLastSol < LAST_SOL_HRS` (patrony)
- FIX 3: `main_logic_func` (manager nabíjení auta) — nový blok po SOC check:
  pokud isSol && hToLastSol < 2 && zbSolar < 4kWh && !zákazPřetoků → STOP (nenabíjet auto)
- Podmínka: pravidlo se NEaplikuje při zákazu přetoků (záporná prodejní cena)
- Deploy: `--no-ha`, server flows synced předem

**v25.71 — Fix NIBE topí nádrž ze sítě při velkém solaru (2026-04-01)**
- BUG: `rf_htg_decide2` řádek 100: `!needH && tankT < coldTank && cheapestTankHour()` → `mod = "NIBE"`
  - Chyběla kontrola `!h.highSolDay` — NIBE topila nádrž ze sítě (4.53 Kč/kWh × 7 kWh = ~32 Kč)
    i když solar forecast dnes = 53 kWh → patrony/NIBE by natopily zadarmo v solárních hodinách
  - Zákon §8.2: "DOTOPI SE NADRZ ZA CO NEJNIZSI CENU, POKUD NENI SOLARNI VYROBA DOSTATECNA"
- FIX: přidáno `!h.highSolDay` na řádky 100 a 102 (obecná + noční větev)
  - Pokud `highSolDay` (dnes ≥ 50 kWh): NIBE NETOPÍ nádrž ze sítě, čeká na solární hodiny
- Deploy: `--no-ha` (jen NR restart), server flows synced předem

**v25.70 — Fix dashboard "Bazén: ❌ -0 min" po NR restartu**
- BUG 1: `filtrace_decision` early returns (NIBE komp, freeze lock) přeskočily export `filtrace_status`
  - Dashboard zobrazoval `{run:0, minReq:0, met:false}` protože globál se nikdy nenastavil
  - FIX: přidán `global.set("filtrace_status", ...)` před každý early return
- BUG 2: `fs` persistence nefunguje — `global.get("fs")` vrací `undefined` v NR function nodes
  - `filt_persist.json` se nikdy nezapsal/nepřečetl → run counter ztracen po NR restartu
  - FIX: nahrazeno za `global.set/get("filt_persist")` (přežije NR restart)
- BUG 3: `minReq` použito na řádku 66 před definicí na řádku 97 → `undefined`
  - FIX: `minReq` přesunuto před inicializační blok

**v25.69 — Fix proaktivní ohřev nádrže na noc + coldTank + cheapestTankHour**
- BUG 1 (KRITICKÝ): `h.coldTank` chybělo v `rf_htg_read_001` → `undefined` → `h.tankT < undefined` = vždy false
  - Proaktivní ohřev nádrže se NIKDY nespustil
  - FIX: přidáno `coldTank:cfg.topeni_chladna_nadrz||40` do h objektu
- BUG 2: `!h.isDraha` blokoval noční ohřev nádrže — v noci mohou být všechny hodiny drahé
  - FIX: nahrazeno za `cheapestTankHour()` — najde nejlevnější hodinu před solarem
  - Zákon §8.2: "topíme za co nejvýhodnějších podmínek"
- FIX 3: nová noční větev — pokud je noc, nádrž < coldTank, zítra nízký solar → NIBE ON v nejlevnější hodině
- INCIDENT: deploy přepsal "Automatizuj ostatní" (9 chybějících nodů + broken encoding)
  - Obnoveno ze zálohy `.flows.json.backup`, synced VŠECH 13 tabů server→git

**v25.68 — Fix NIBE nezapíná: off-by-one chyba v needH a tGap hranicích**
- BUG: `rf_htg_decide2` řádek 53: `needH = h.inT < h.effTgt - HYST` (strict `<`)
  - Při inT=23.1°C, effTgt=23.3°C, HYST=0.2 → 23.1 < 23.1 = **false** → NIBE se nezapne
  - FIX: `<` → `<=` (zapnout i na hranici hystereze)
- BUG: řádek 96: `tGap > PM` (strict `>`, PM=0.2)
  - Při tGap=0.2 → 0.2 > 0.2 = **false** → NIBE mód se nenastaví
  - FIX: `>` → `>=`
- Zákon §8.2: "dům musí být natopen na požadovanou teplotu (stejnou nebo vyšší)"
- Po opravě: `switch.nibe_topeni = ON`, `topení mód = NIBE`

**v25.66 — Realistická simulace plánu: dynamická spotřeba místo plochého socN**
- BUG: `sim()` pro NORMAL mód v noci používala plochý `socN=5%/h` (1.4 kWh/h)
- Skutečná noční spotřeba domu bez NIBE: ~1.0 kWh/h (3.5%/h) — přeceňování o 40-70%
- FIX: nová funkce `cN(h,f)` — dynamický výpočet spotřeby per hodina:
  1. Historie (`avgConsumptionKwh`, `sampleCount≥3`) → skutečná data
  2. Live spotřeba (`sensor.celkova_spotreba`) → reálný proxy
  3. Fallback: `dayCons/24` (0.83 kWh/h)
- `sim()` NORMAL non-solar: `cN(h,f)` místo `C.socN*f`
- `cM()` discharge thresholds: `cN()` pro SOC odhady (safety margin `C.socN` zachován)
- Prep node: přidán `liveCons` + `autoK` do plánovacího kontextu
- Výsledek: noc 23→5h SOC 66→46% (nový) vs 67→39% (starý) — rozdíl +7%

**v25.67 — Fix history learning: restart corruption + sanity checks**
- BUG 1: `fve_history_collect` — po NR restartu `prev_hourly_values` prázdný → delta = kumulativní denní hodnota (24.92 kWh místo ~1 kWh)
  - FIX: skip první run po restartu (`prevValues.hour === undefined`) — uloží baseline, čeká na další cyklus
  - Sanity check: reject `solarKwh > 20` nebo `consumptionKwh > 15` per hodina
- BUG 2: `fve_history_store` — po restartu `flow.get("consumption_history")` prázdný → přepíše validní persist file vadným vzorkem
  - FIX: na startu načte z `/homeassistant/fve_consumption_history.json` pokud flow context prázdný
- Reset korumpovaného `consumption_history.json` na `{}`

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

### v25.55e: Fix ŠETŘIT mód — baterie se nesmí vybíjet (2026-03-22)

**Root cause**: V Šetřit módu se baterie vybíjela (~10A) přestože zákon 4.3 říká „baterie se nesmí vybíjet". 
Původní kód nastavoval `PSP = 150W` (statický grid bias) a `max_discharge_power = currentSolar`. 
Victron ESS control loop nestíhal reagovat a baterie pokrývala deficit.

**Fix** (`fve-modes.json`, ŠETŘIT Logic `139cd450edbbde37`):
1. **Dynamic PSP** = `max(gridBias, deficit + gridBias)` — grid aktivně pokrývá vše co solar nestíhá
2. **effectiveMinSoc** = `max(minSoc, liveSoc)` — BMS zabrání vybíjení pod aktuální SOC
3. **max_discharge_power = currentSolar** (solar DC passthrough, nelze 0 — blokuje solar)

**Testováno**: `max_discharge_power=0` NEFUNGUJE na tomto Victron systému — solar jde celý do baterie, grid import skoční na 8.4kW.

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

### v25.79: Fix hladu auta + ultra levná vybíjení při zákazu přetoků (2026-04-03)

**Problém 1: `auto_ma_hlad = OFF` i když auto mělo hlad**
- Root cause: `probe_decision_func` neošetřoval stav 6 (WaitStart). Když manager zastavil wallbox (stav přešel na 6), probe nereagoval a `garage_hunger` zůstal na poslední hodnotě. Pokud se mezitím ztratil (ručně/jiný mechanismus), nikdo probe znovu nespustil.
- Fix: přidáno ošetření `newState === 6` — pokud auto dosud nebylo probeováno (`garage_probed = false`), spustí se probe. Jinak se zachová aktuální `garage_hunger`.
- Nový flag `garage_probed` (flow context): nastaví se na `true` po dokončení probe (`probe_result_func`), na `false` při startu nového probe.

**Problém 2: Baterie se nevybíjela při ultra levné ceně + SOC ≥ 95%**
- Root cause: `zakaz_pretoku` logika (`75d1f9e77bc15e0a`) při ultra levné ceně (buy < 1.0 Kč) blokovala vybíjení baterie (`max_discharge_power = solarPassthrough`). Ale zákon §4.6 říká: při SOC ≥ 95% energie MUSÍ jít do spotřebičů dle priorit, aby se neomezovala solární výroba.
- Fix: nová proměnná `ultraLevnaBlokuj = ultraLevna && currentSoc < DRAIN_PRAH (95%)`. Při SOC ≥ 95% se vybíjení NEblokuje i při ultra levné ceně.
- Výsledek: `max_discharge_power = -1` (neomezeno), grid draw klesl z 1094 W na ~37 W.

**Problém 3: Manager nespouštěl nabíjení auta při ultra levné ceně**
- Root cause: podmínka `_zakazOk` v `main_logic_func` vyžadovala `_gridW < 200W`. Při ultra levné ceně grid draw byl vysoký (protože baterie nevybíjela), takže podmínka nebyla splněna.
- Fix: uvolněna podmínka: `_gridW < 200 || _ultraLevna` — při ultra levné ceně grid draw je očekávaný a po spuštění nabíjení auta se sníží (baterie začne vybíjet).

**Nasazeno**: deploy.sh (s HA restartem), commit `91e1a66`.
**Ověřeno**: auto_ma_hlad=ON, wallbox=ON, charger_state=2 (nabíjí), grid=17W, solár=5285W.

### v25.78: Probe lock proti race condition (2026-04-02)

**Fix konfliktu probe vs. solární smyčka** (`manager-nabijeni-auta.json`, `nabijeni-auta-slunce.json`):
- Root cause: Smart Probe (20s diagnostika) a solární korekční smyčka řídily ve stejný čas stejný wallbox start/stop.
- Důsledek: oscilace a konflikt příkazů, které vedly k nestabilnímu chování nabíjení auta.
- Fix:
  - `manager-nabijeni-auta.json`: během probe se nastavuje globální lock `garage_probe_active=true`, po ukončení/rušení probe se vrací na `false`.
  - `nabijeni-auta-slunce.json`: při `garage_probe_active=true` se korekční smyčka okamžitě pozastaví (`return null`) a na wallbox nesahá.
- Deploy: `deploy.sh --no-ha`, Node-RED start HTTP 200, audit groups OK.

---

## 10. Solární instalace

- **Výkon**: 17 kWp, **Lokace**: Horoušany (50.10°N, 14.74°E)
- **Azimut**: 190° (JZ), **Sklon**: 45°
- **Solární křivka**: 5:00–18:00, max 12:00, silnější odpoledne (JZ)
