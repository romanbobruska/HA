# FVE Automatizace — Kontext projektu

> **Living document** — aktuální stav systému. Po každé změně PŘEPSAT relevantní sekci.
> Poslední aktualizace: 2026-03-10 (v25.7: Drahé hodiny VŽDY Normal — KROK 7c ochrana + P5b bez arbSaveOffsets, 2× deploy OK)
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
| `fve-orchestrator.json` | Plánovač módů na 12h (cenová arbitráž, solar-first, balancing) |
| `fve-modes.json` | Implementace 7 FVE módů (Normal, Šetřit, Nabíjet, Prodávat, Zákaz, Solární, Balancování) |
| `fve-config.json` | Centrální konfigurace + čtení HA stavů do globálů |
| `fve-heating.json` | Řízení topení (NIBE, oběhové čerpadlo, patrony, chlazení) |
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

## 7. Solární instalace

- **Výkon**: 17 kWp, **Lokace**: Horoušany (50.10°N, 14.74°E)
- **Azimut**: 190° (JZ), **Sklon**: 45°
- **Solární křivka**: 5:00–18:00, max 12:00, silnější odpoledne (JZ)
