# FVE Automatizace — Kontext projektu

> **Living document** — aktuální stav systému. Po každé změně PŘEPSAT relevantní sekci.
> Poslední aktualizace: 2026-03-11 (v25.1 REFACTORING: Všechny funkce ≤100L, hardcoded hodnoty nahrazeny config parametry, velké funkce rozděleny)
>
> **⚠️ VŠECHNY požadavky, zákony a pravidla jsou v `User inputs/POZADAVKY.TXT`.**
> Tento soubor obsahuje pouze technický kontext a stav systému — NE požadavky.
>
> **Pravidla pro AI:**
> - **VŽDY komunikovat v ČEŠTINĚ** — základní pravidlo
> - Před každou prací PŘEČÍST `User inputs/POZADAVKY.TXT` (ZÁKONY)
> - Před deploymentem ověřit soulad se VŠEMI zákony
> - Po deploymentu ověřit HA stavy, logy, grid draw
> - `User inputs/POZADAVKY.TXT` NESMÍ AI MĚNIT — edituje výhradně uživatel
> - Aktualizovat tento soubor po každém úspěšném nasazení
> - Po sobě VŽDY uklidit dočasné soubory (`_*.py`, `_*.js`, `fix_*.py`)

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
| `fve-orchestrator.json` | Plánovač módů na 12h — 5 funkcí: Příprava→Cena→Arbitráž→Plán→Výstup (v25.1 split z 1239L) |
| `fve-modes.json` | Implementace 7 FVE módů (Normal, Šetřit, Nabíjet, Prodávat, Zákaz, Solární, Balancování) |
| `fve-config.json` | Centrální konfigurace (47L) + čtení HA stavů do globálů (30L) |
| `fve-heating.json` | Řízení topení — 3 funkce: Čtení stavu→Rozhodování→Pojistky+výstup (v25.1 split z 541L) |
| `fve-history-learning.json` | Historická predikce solární výroby per hodina |
| `init-set-victron.json` | Inicializace dat z Victron VRM API |
| `vypocitej-ceny.json` | Spotové ceny z API → SQLite → globál |
| `manager-nabijeni-auta.json` | Rozhodnutí grid vs. solar nabíjení auta |
| `nabijeni-auta-sit.json` | Nabíjení auta ze sítě (cenové prahy, headroom) |
| `nabijeni-auta-slunce.json` | Nabíjení auta ze solaru (closed-loop amperage) |
| `boiler.json` | Automatizace bojleru (Meross termostat) |
| `filtrace-bazenu.json` | Časové řízení filtrace bazénu |
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

### Entity názvy patron fází
| Fáze | Entity ID |
|------|-----------|
| 1 | `switch.patrona_faze_1` |
| 2 | `switch.patrona_faze_3_2` |
| 3 | `switch.patrona_faze_3` |

---

## 9. Solární instalace

- **Výkon**: 17 kWp, **Lokace**: Horoušany (50.10°N, 14.74°E)
- **Azimut**: 190° (JZ), **Sklon**: 45°
- **Solární křivka**: 5:00–18:00, max 12:00, silnější odpoledne (JZ)
