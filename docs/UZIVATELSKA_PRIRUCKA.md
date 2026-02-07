# FVE Automatizace - Uživatelská příručka

Tato příručka vás provede nastavením a používáním automatizace pro váš FVE systém s Victron střídačem.

---

## Obsah

1. [Co automatizace dělá](#co-automatizace-dělá)
2. [Kde sledovat aktuální stav](#kde-sledovat-aktuální-stav)
3. [Kde vidět plán na 12 hodin](#kde-vidět-plán-na-12-hodin)
4. [Jak nastavit parametry](#jak-nastavit-parametry)
5. [Popis módů](#popis-módů)
6. [Časté problémy a řešení](#časté-problémy-a-řešení)
7. [Příklady použití](#příklady-použití)

---

## Co automatizace dělá

Automatizace řídí váš FVE systém tak, aby:
- **Šetřila peníze** - nakupuje elektřinu, když je levná, prodává když je drahá
- **Chránila baterii** - minimalizuje zbytečné cykly nabíjení/vybíjení
- **Prioritizovala nabíjení auta** - auto má vždy přednost před baterií
- **Plánovala dopředu** - vytváří plán na 12 hodin podle předpovědi cen a solární výroby

---

## Kde sledovat aktuální stav

### V Home Assistant

Otevřete Home Assistant a najděte tyto sensory:

| Sensor | Co zobrazuje |
|--------|--------------|
| `sensor.fve_aktualni_mod` | Aktuální mód (normal, setrit, nabijet_ze_site...) |
| `sensor.fve_planovany_mod` | Mód naplánovaný pro tuto hodinu |
| `sensor.fve_plan` | Kompletní plán na 12 hodin |
| `sensor.fve_energie_v_baterii` | Kolik energie je v baterii (kWh) |
| `sensor.fve_dostupna_energie_v_baterii` | Kolik energie můžete použít (nad min. SOC) |
| `sensor.fve_volna_kapacita_baterie` | Kolik místa zbývá v baterii |
| `sensor.fve_rozdil_vyroby_a_spotreby` | Aktuální přebytek/nedostatek (W) |

### Jak vytvořit přehledovou kartu

V Home Assistant přidejte tuto kartu do vašeho dashboardu:

```yaml
type: entities
title: FVE Automatizace
entities:
  - entity: sensor.fve_aktualni_mod
    name: Aktuální mód
  - entity: sensor.fve_planovany_mod
    name: Plánovaný mód
  - entity: sensor.battery_percent
    name: Stav baterie
  - entity: sensor.fve_energie_v_baterii
    name: Energie v baterii
  - entity: sensor.fve_dostupna_energie_v_baterii
    name: Dostupná energie
  - entity: sensor.fve_rozdil_vyroby_a_spotreby
    name: Přebytek/nedostatek
  - entity: input_boolean.fve_automatizace
    name: Automatizace zapnuta
```

---

## Kde vidět plán na 12 hodin

### Možnost 1: Sensor v Home Assistant

Sensor `sensor.fve_plan` obsahuje kompletní plán. Klikněte na něj a v atributech uvidíte:
- `current_mode` - aktuální mód
- `current_hour` - aktuální hodina
- `plan` - seznam plánovaných módů pro každou hodinu
- `last_update` - kdy byl plán naposledy aktualizován

### Možnost 2: Karta s plánem

Přidejte tuto kartu pro zobrazení plánu:

```yaml
type: markdown
title: Plán FVE na 12 hodin
content: |
  **Aktuální mód:** {{ states('sensor.fve_aktualni_mod') }}
  **Aktualizováno:** {{ state_attr('sensor.fve_plan', 'last_update') }}
  
  {% set plan_str = state_attr('sensor.fve_plan', 'plan') %}
  {% if plan_str and plan_str != '[]' %}
  {% set plan = plan_str | from_json %}
  | Hodina | Mód | Důvod |
  |--------|-----|-------|
  {% for item in plan %}
  | {{ item.hour }}:00 | {{ item.mode }} | {{ item.reason }} |
  {% endfor %}
  {% else %}
  Plán není k dispozici
  {% endif %}
```

### Možnost 3: Node-RED debug

1. Otevřete Node-RED
2. Najděte flow "FVE Orchestrator"
3. Zapněte debug node "Plan Debug"
4. V debug panelu uvidíte kompletní plán při každé aktualizaci (každých 15 minut)

---

## Jak nastavit parametry

### Základní nastavení v Home Assistant

Všechny parametry najdete v Home Assistant pod "Nastavení" → "Zařízení a služby" → "Pomocníci" nebo přímo v dashboardu.

#### Hlavní přepínače (zapnout/vypnout)

| Entita | Popis | Doporučení |
|--------|-------|------------|
| `input_boolean.fve_automatizace` | **Hlavní vypínač** - zapíná/vypíná celou automatizaci | Nechte zapnuté |
| `input_boolean.fve_prodej_z_baterie` | Povolí prodej energie z baterie do sítě | Zapněte pouze pokud chcete prodávat |
| `input_boolean.fve_blokace_vybijeni` | Zablokuje vybíjení baterie (např. pro tepelné čerpadlo) | Vypnuto, zapněte při potřebě |
| `input_boolean.letni_rezim` | Letní režim - jiné chování automatizace | Dle sezóny |

#### Číselné parametry

| Entita | Popis | Výchozí | Rozsah |
|--------|-------|---------|--------|
| `input_number.fve_kapacita_baterie` | Kapacita vaší baterie v kWh | 28 | 1-100 |
| `input_number.fve_min_soc` | Minimální stav nabití baterie v % | 20 | 5-50 |
| `input_number.fve_amortizace_baterie` | Cena za opotřebení baterie v Kč/kWh | 1.0 | 0-5 |
| `input_number.fve_max_feed_in` | Maximální výkon do sítě v W | 7600 | 0-15000 |
| `input_number.fve_max_spotreba_sit` | Maximální odběr ze sítě v W | 22000 | 0-50000 |
| `input_number.fve_jistic` | Hodnota jističe v A | 32 | 16-63 |

#### Výběrové parametry

| Entita | Popis | Možnosti |
|--------|-------|----------|
| `input_select.fve_rezim_casu` | Rozlišení plánování | `hodina`, `ctvrthodina` |
| `input_select.fve_manual_mod` | Ruční přepis módu | `auto`, `normal`, `setrit`, `nabijet_ze_site`, `prodavat`, `prodavat_misto_nabijeni` |

### Jak změnit parametr

1. **V Home Assistant UI:**
   - Jděte do "Nastavení" → "Zařízení a služby" → "Pomocníci"
   - Najděte požadovaný parametr
   - Klikněte a změňte hodnotu

2. **Přes dashboard:**
   - Přidejte entitu na dashboard
   - Klikněte na ni a změňte hodnotu

3. **Přes službu:**
   - Jděte do "Nástroje pro vývojáře" → "Služby"
   - Vyberte `input_number.set_value` nebo `input_boolean.turn_on/off`
   - Zadejte entitu a hodnotu

---

## Popis módů

### NORMAL (Normální)
**Co dělá:** Standardní provoz - baterie se nabíjí ze solaru a vybíjí do spotřeby domu.

**Kdy se aktivuje:** Výchozí stav, když není důvod pro jiný mód.

**Victron nastavení:**
- ESS mód: Optimized (with BatteryLife)
- Grid Set Point: 0 W

---

### ŠETŘIT (Setrit)
**Co dělá:** Minimalizuje vybíjení baterie, spotřeba jde ze sítě.

**Kdy se aktivuje:** 
- Energie je drahá (cenový level ≥ 7)
- Baterie je málo nabitá
- Očekává se levnější energie později

**Victron nastavení:**
- Max Discharge Power: 0 W (baterie se nevybíjí)
- Grid Set Point: 0 W

---

### NABÍJET ZE SÍTĚ (Nabijet ze site)
**Co dělá:** Aktivně nabíjí baterii ze sítě.

**Kdy se aktivuje:**
- Energie je velmi levná (cenový level ≤ 2)
- Baterie není plná
- Vyplatí se nakoupit levnou energii

**Victron nastavení:**
- Grid Set Point: záporná hodnota (např. -5000 W = nabíjení 5 kW)
- Schedule Charge: zapnuto

---

### PRODÁVAT (Prodavat)
**Co dělá:** Prodává energii z baterie do sítě.

**Kdy se aktivuje:**
- Energie je velmi drahá (cenový level ≥ 9)
- Baterie je dostatečně nabitá
- Prodej je povolen (`input_boolean.fve_prodej_z_baterie` = ON)

**Victron nastavení:**
- Grid Set Point: kladná hodnota (např. 5000 W = prodej 5 kW)
- Max Feed In: nastaveno na maximum

---

### PRODÁVAT MÍSTO NABÍJENÍ (Prodavat misto nabijeni)
**Co dělá:** Solární přebytek jde do sítě místo do baterie.

**Kdy se aktivuje:**
- Dobrá prodejní cena
- Baterie je dostatečně nabitá
- Očekává se dostatek solaru i později

**Victron nastavení:**
- Max Charge Power: omezeno
- Přebytek jde do sítě

---

## Časté problémy a řešení

### Automatizace nereaguje

**Příznaky:** Mód se nemění, baterie se chová jinak než by měla.

**Řešení:**
1. Zkontrolujte, že `input_boolean.fve_automatizace` je **zapnuté**
2. V Node-RED zkontrolujte, že flow "FVE Orchestrator" běží (zelené tečky u nodů)
3. Zkontrolujte MQTT spojení - v HA jděte do "Nastavení" → "Zařízení a služby" → "MQTT"
4. Restartujte Node-RED: v menu vyberte "Deploy"

### Plán se nezobrazuje

**Příznaky:** Sensor `sensor.fve_plan` je prázdný nebo ukazuje "unavailable".

**Řešení:**
1. Počkejte 15 minut - plán se aktualizuje každých 15 minut
2. V Node-RED ručně spusťte inject node "Každých 15 min" v flow "FVE Orchestrator"
3. Zkontrolujte debug node pro chyby

### Špatné cenové úrovně

**Příznaky:** Automatizace nakupuje/prodává v nesprávný čas.

**Řešení:**
1. Zkontrolujte databázi `own_energy_prices_total` - obsahuje aktuální ceny?
2. Ověřte flow "vypocitej ceny.json" v Node-RED
3. Zkontrolujte, že máte správně nastavené cenové prahy

### Baterie se nenabíjí ze sítě

**Příznaky:** I při levné energii se baterie nenabíjí.

**Řešení:**
1. Zkontrolujte, že cenový level je ≤ 2 (velmi levná energie)
2. Ověřte, že baterie není plná
3. Zkontrolujte MQTT komunikaci s Victron

### Auto má vždy přednost

**Toto je záměrné chování!** Když wallbox hlásí stav "Charging", FVE automatizace nepřepisuje nastavení baterie, aby auto dostalo maximum energie.

### Mód se neustále mění

**Příznaky:** Mód se mění každou minutu tam a zpět.

**Řešení:**
1. Zkontrolujte hysterezi v konfiguraci
2. Možná jsou cenové úrovně na hranici prahů - upravte `prah_levna_energie` nebo `prah_draha_energie`

---

## Příklady použití

### Příklad 1: Chci maximálně šetřit

Nastavení:
- `input_boolean.fve_prodej_z_baterie`: **VYPNUTO** (neprodávat z baterie)
- `input_number.fve_min_soc`: **30%** (vyšší rezerva)
- `input_number.fve_amortizace_baterie`: **2.0 Kč/kWh** (vyšší cena = méně cyklů)

### Příklad 2: Chci maximálně vydělat

Nastavení:
- `input_boolean.fve_prodej_z_baterie`: **ZAPNUTO**
- `input_number.fve_min_soc`: **15%** (nižší rezerva = více k prodeji)
- `input_number.fve_amortizace_baterie`: **0.5 Kč/kWh** (nižší cena = více cyklů)

### Příklad 3: Mám tepelné čerpadlo

Když běží tepelné čerpadlo a nechcete vybíjet baterii:
- Zapněte `input_boolean.fve_blokace_vybijeni`
- Nebo vytvořte automatizaci, která to zapne při běhu TČ

### Příklad 4: Ruční přepis módu

Pokud chcete dočasně přepsat automatiku:
1. Nastavte `input_select.fve_manual_mod` na požadovaný mód (např. "normal")
2. Automatizace bude používat tento mód místo vypočítaného
3. Pro návrat k automatice nastavte zpět na "auto"

---

## Slovníček pojmů

| Pojem | Význam |
|-------|--------|
| **SOC** | State of Charge - stav nabití baterie v procentech |
| **Feed In** | Dodávka energie do sítě (prodej) |
| **Grid Set Point** | Cílový odběr/dodávka ze/do sítě |
| **ESS** | Energy Storage System - systém ukládání energie |
| **Cenový level** | Úroveň ceny 1-10, kde 1 = nejlevnější, 10 = nejdražší |
| **Přebytek** | Rozdíl mezi výrobou a spotřebou (kladný = vyrábíme více) |
| **Amortizace** | Opotřebení baterie vyjádřené v Kč za každou kWh cyklu |

---

## Kontakt a podpora

Pokud máte problémy:
1. Zkontrolujte logy v Home Assistant (Nastavení → Systém → Logy)
2. Zkontrolujte debug výstupy v Node-RED
3. Ověřte MQTT komunikaci s Victron systémem

---

*Verze příručky: 1.0*
*Poslední aktualizace: 2026-01-24*
