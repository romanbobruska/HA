# HA - Automatizace FVE a tepelného čerpadla

Kompletní řešení pro automatizaci fotovoltaické elektrárny (Victron), tepelného čerpadla (Nibe) a nabíjení elektromobilů v Home Assistant s Node-RED.

## Architektura

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐
│  Victron    │◄───►│   MQTT   │◄───►│ Home         │
│  GX/Cerbo   │     │  Broker  │     │ Assistant    │
└─────────────┘     └──────────┘     └──────┬───────┘
                                            │
┌─────────────┐     ┌──────────┐            │
│  Nibe TČ    │◄───►│  Modbus  │◄───────────┤
└─────────────┘     └──────────┘            │
                                            │
┌─────────────┐                    ┌────────┴───────┐
│ Spotová     │◄──── HTTP ────────►│   Node-RED     │
│ elektřina   │                    │   (flows)      │
└─────────────┘                    └────────────────┘
```

## Struktura repozitáře

```
HA/
├── node-red/flows/          # Node-RED flow soubory (import do Node-RED)
│   ├── fve-config.json          # Konfigurace FVE + cenové prahy
│   ├── fve-orchestrator.json    # Plánování a rozhodování o módech
│   ├── fve-modes.json           # Implementace módů (MQTT příkazy)
│   ├── fve-heating.json         # Řízení topení/chlazení
│   ├── fve-history-learning.json # Historické učení
│   ├── init-set-victron.json    # Inicializace dat z Victron VRM API
│   ├── vypocitej-ceny.json      # Výpočet cen elektřiny
│   ├── manager-nabijeni-auta.json # Manager nabíjení auta
│   ├── nabijeni-auta-sit.json   # Nabíjení auta ze sítě
│   ├── nabijeni-auta-slunce.json # Nabíjení auta ze slunce
│   ├── nibe-control.json        # Ovládání Nibe TČ
│   ├── boiler.json              # Automatizace bojleru (hystereze, solar)
│   ├── boiler-altan.json        # Ohřívač v altánu
│   ├── horni-zebrik.json        # Horní žebřík (topný)
│   └── filtrace-bazenu.json     # Filtrace bazénu
├── homeassistant/           # Home Assistant konfigurace
│   ├── configuration.yaml       # Hlavní konfigurace HA
│   ├── automations.yaml         # HA automatizace
│   ├── mqtt.yaml                # MQTT entity (Victron, wallboxy)
│   ├── input_numbers.yaml       # Nastavitelné parametry
│   ├── template_sensors.yaml    # Template senzory
│   └── template_switches.yaml   # Template přepínače (Nibe)
├── database/                # Databázové schéma
│   └── schema.sql               # Tabulka spotových cen
└── docs/                    # Dokumentace
    └── UZIVATELSKA_PRIRUCKA.md  # Uživatelská příručka
```

## Globální proměnné Node-RED

Všechna data se po načtení ukládají do globálních proměnných. Ostatní flows čtou z globálů — žádné opakované dotazy do DB nebo API.

### Cenová data (zdroj: `vypocitej-ceny.json`)
| Proměnná | Popis |
|----------|-------|
| `fve_prices_forecast` | Kompletní tabulka cen s levely |
| `fve_current_price` | Aktuální cena (buy, sell, levelBuy, levelSell) |
| `fve_price_level` | Aktuální cenový level (1-10) |

### Konfigurace (zdroj: `fve-config.json`)
| Proměnná | Popis |
|----------|-------|
| `fve_config` | Kompletní konfigurace (prahy, kapacita, min SOC...) |

### Victron statistiky (zdroj: `init-set-victron.json`)
| Proměnná | Popis |
|----------|-------|
| `forecast_vyroba_dnes` | Předpověď solární výroby dnes (Wh) |
| `forecast_vyroba_zitra` | Předpověď solární výroby zítra (Wh) |
| `forecast_zbytek_vyroba_dnes` | Zbývající výroba dnes (Wh) |
| `grid_direct_use` | Spotřeba ze sítě (Wh) |
| `grid_to_battery` | Nabíjení baterie ze sítě (Wh) |
| `ev_consumption` | Spotřeba EV (Wh) |
| `solar_consumption` | Spotřeba ze solaru (Wh) |
| `solar_to_battery` | Nabíjení baterie ze solaru (Wh) |
| `battery_consumption` | Spotřeba z baterie (Wh) |
| `battery_to_grid` | Vybíjení baterie do sítě (Wh) |
| `total_solar_yield` | Celková solární výroba (Wh) |

### Vypočtené hodnoty (zdroj: `init-set-victron.json`)
| Proměnná | Popis |
|----------|-------|
| `fve_spotreba_sit_kwh` | Spotřeba ze sítě (kWh) |
| `fve_spotreba_ev_kwh` | Spotřeba EV (kWh) |
| `fve_vyroba_solar_kwh` | Solární výroba (kWh) |
| `fve_nabijeni_bat_kwh` | Nabíjení baterie (kWh) |
| `fve_vybijeni_bat_kwh` | Vybíjení baterie (kWh) |
| `fve_prodej_sit_kwh` | Prodej do sítě (kWh) |

## Módy FVE

| Mód | Popis | Kdy |
|-----|-------|-----|
| **NORMAL** | Standardní provoz, baterie se nabíjí/vybíjí | Výchozí |
| **ŠETŘIT** | Blokace vybíjení baterie | Drahá energie, čekáme na levnější |
| **NABÍJET ZE SÍTĚ** | Aktivní nabíjení z gridu | Velmi levná energie (level ≤ 2) |
| **PRODÁVAT** | Prodej z baterie do sítě | Velmi drahá energie (level ≥ 9) |
| **ZÁKAZ PŘETOKŮ** | Solar přebytek do sítě místo baterie | Dobrá prodejní cena |

## Instalace

### 1. Home Assistant
Zkopírujte soubory z `homeassistant/` do `/config/` na vašem HA:
```bash
cp homeassistant/*.yaml /config/
```

### 2. Node-RED
V Node-RED importujte všechny flow soubory z `node-red/flows/`:
- Menu → Import → vyberte soubor → Import

### 3. Databáze
Vytvořte tabulku cen v SQLite:
```bash
sqlite3 /homeassistant/home-assistant_v2.db < database/schema.sql
```

### 4. MQTT
Ujistěte se, že Victron GX/Cerbo publikuje data přes MQTT s prefixem `victron/`.

## Požadavky

- Home Assistant s addony: Node-RED, MQTT Broker
- Victron GX/Cerbo s MQTT
- Nibe tepelné čerpadlo (Modbus)
- Victron VRM API přístup (pro předpověď výroby)

## Licence

Soukromý projekt.
