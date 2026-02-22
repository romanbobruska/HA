# Automatizace topení domu — Požadavky a architektura

## 1. Přehled systému

Kompletní řízení teploty v domě přes Node-RED. Systém má plnou odpovědnost za teplotu v domě a za odběr elektřiny tepelným čerpadlem.

### Komponenty:
- **NIBE F1345** — tepelné čerpadlo, hřeje směšovací nádrž (odběr peak ~14 kW)
- **Oběhové čerpadlo** — tlačí teplou vodu z nádrže do domu (~300 W)
- **Patrony** (3-fázové) — elektrické nahřívání nádrže z přebytků solaru (3× 3 kW = 9 kW)
- **Bazénový ventil** — přepíná teplou vodu mezi domem a bazénem

### Princip:
1. NIBE autonomně hřeje nádrž na základě stupňů minut (DM). My pouze povolujeme/blokujeme (reg 47371).
2. Oběhové čerpadlo řídíme nezávisle — odebíráme teplo z nádrže do domu, kdy chceme.
3. Odběr tepla z nádrže → pokles DM → NIBE začne hřát → spotřeba elektřiny.
4. Klíčová strategie: **odebírat teplo (oběhové čerpadlo) v levných hodinách**, aby NIBE hřálo nádrž za levnou elektřinu.

---

## 2. Vstupy (HA entity)

| Entity | Popis |
|---|---|
| `input_number.nastavena_teplota_v_dome` | Cílová teplota v domě |
| `sensor.hp2551ae_pro_v2_1_0_indoor_temperature` | Skutečná teplota v domě |
| `sensor.teplota_smesovac_teplota` | Teplota ve směšovací nádrži |
| `sensor.hp2551ae_pro_v2_1_0_outdoor_temperature` | Venkovní teplota |
| `sensor.nibe_degree_minutes` | Stupně minuty NIBE (rozsah +100 až -30) |
| `switch.horousany_termostat_prizemi_kote` | Oběhové čerpadlo domu |
| `switch.patrona_faze_1` | Patrona fáze 1 (3 kW) |
| `switch.patrona_faze_3_2` | Patrona fáze 2 (3 kW) |
| `switch.patrona_faze_3` | Patrona fáze 3 (3 kW) |
| `switch.bazen_ventil_smesovac` | Ventil směšovač → bazén |
| `input_boolean.topi_se_v_krbu` | Topí se v krbu? |
| `input_boolean.chlazeni` | Chlazení povoleno? |
| `input_boolean.automatizovat_topeni` | Celá automatizace ON/OFF |
| `input_boolean.letni_rezim` | Letní/zimní režim |
| `input_boolean.auto_ma_hlad` | Auto potřebuje nabíjení? |
| `sensor.battery_percent` | SOC baterie (%) |
| `sensor.solar_power` | Solární výkon (W) |
| `sensor.fve_dostupny_prebytek` | Dostupný přebytek solaru (W) |
| `binary_sensor.nibe_kompresory_aktivni_binarni` | Kompresor NIBE běží? |
| `sensor.nibe_aktualni_realny_stav` | Textový stav čerpadla |

---

## 3. Výstupy (aktuátory)

| Aktuátor | Ovládání | Popis |
|---|---|---|
| NIBE topení | Modbus reg 47371 (0/1) | Povolení/zákaz hřát nádrž |
| Oběhové čerpadlo | `switch.horousany_termostat_prizemi_kote` | ON/OFF |
| Patrona fáze 1 | `switch.patrona_faze_1` | ON/OFF |
| Patrona fáze 2 | `switch.patrona_faze_3_2` | ON/OFF |
| Patrona fáze 3 | `switch.patrona_faze_3` | ON/OFF |
| Bazénový ventil | `switch.bazen_ventil_smesovac` | Kontrola (OFF při topení domu) |

---

## 4. Konfigurovatelné parametry (fve_config)

| Parametr | Výchozí | Popis |
|---|---|---|
| `topeni_min_teplota_nadrze` | 30 | Min. teplota nádrže pro oběhové čerpadlo (°C) |
| `topeni_max_teplota_nadrze` | 50 | Max. teplota nádrže pro topení domu (°C) |
| `topeni_nocni_snizeni` | 0.5 | Noční snížení cílové teploty (°C) |
| `topeni_nocni_od` | 22 | Začátek nočního režimu (hodina) |
| `topeni_nocni_do` | 6 | Konec nočního režimu (hodina) |
| `topeni_nouzova_teplota` | 18 | Nouzová teplota — topit i v drahých hodinách (°C) |
| `topeni_min_pretok_patron_w` | 3000 | Min. přebytek pro zapnutí 1. patrony (W) |
| `topeni_patron_faze_w` | 3000 | Výkon jedné fáze patrony (W) |
| `topeni_min_soc_patron` | 95 | Min. SOC baterie pro patron ohřev (%) |
| `topeni_max_teplota_patron` | 60 | Max. teplota nádrže při patron ohřevu (°C) |
| `prah_draha_energie` | 12 | Level >= prah = drahá energie (existující) |

---

## 5. Pravidla rozhodování

### 5.1 Automatizace OFF (`automatizovat_topeni` = OFF)
Jednorázová akce:
- NIBE: nastavit na topení (47371=1), **pokud** kompresor neběží. Pokud běží, nechat být.
- Oběhové čerpadlo: OFF
- Patrony: všechny OFF
- Bazénový ventil: nechat jak je
- Poté **žádné další zásahy** dokud se automatizace nezapne.

### 5.2 Letní režim
- Topení: OFF (oběhové čerpadlo OFF, NIBE allow pro TUV)
- Patrony: OFF (nebo overflow logika pokud implementována)
- Chlazení: řízeno cílovou teplotou (`nastavena_teplota_v_dome`)

### 5.3 Zimní režim — NIBE (47371)

**Blokace v drahých hodinách:**
- `levelBuy >= prah_draha_energie` → BLOKOVAT (47371=0)
  - Výjimka: nouzová teplota (indoor < `topeni_nouzova_teplota`) → POVOLIT i v drahých
- `levelBuy < prah_draha_energie` → POVOLIT (47371=1)
  - V nejlevnějších hodinách vždy povolit — lepší než riskovat topení v drahých

**Vzájemná exkluzivita:** Pokud patrony aktivní → NIBE MUSÍ být OFF (47371=0)

**Ochrana:** NIKDY nevypínat (47371=0) pokud kompresor běží!

### 5.4 Zimní režim — Oběhové čerpadlo

**Zapnout** pokud VŠECHNY podmínky splněny:
- Teplota v domě < cílová teplota (s nočním snížením)
- Teplota v nádrži >= `topeni_min_teplota_nadrze` (30°C)
- Teplota v nádrži <= `topeni_max_teplota_nadrze` (50°C)
- Krb neaktivní (pokud topí krb, čerpadlo nepotřebné)
- Automatizace ON

**Vypnout** pokud:
- Teplota v domě >= cílová teplota
- Teplota v nádrži mimo rozsah 30-50°C
- Krb aktivní

**Strategie odběru tepla dle ceny:**
- Levné hodiny: agresivněji odebírat (i mírně pod cílem)
- Drahé hodiny: šetřit (odebírat jen pokud nutné)
- Noční hodiny s levnou energií: neblokovat odběr kvůli nočnímu snížení 0.5°C — lepší nahřát nádrž v levných hodinách

### 5.5 Noční režim (22:00–6:00)
- Cílová teplota = `nastavena_teplota_v_dome` - `topeni_nocni_snizeni` (0.5°C)
- ALE: v levných nočních hodinách je výhodné nechat oběhové čerpadlo běžet
  - NIBE pak nahřeje nádrž za levnou energii → zásobárna tepla na den

### 5.6 Patrony — Přetokové vytápění

**Podmínky aktivace:**
1. Baterie SOC >= `topeni_min_soc_patron` (95%)
2. Auto nemá hlad (`auto_ma_hlad` = OFF)
3. Teplota v nádrži < `topeni_max_teplota_patron` (60°C)
4. Přebytek solaru dostatečný

**Výpočet přebytku:**
```
přebytek = sensor.fve_dostupny_prebytek + aktuální_výkon_patron
```
(Patron spotřeba je součástí AC loads, proto ji přičítáme zpět)

**Stupňování:**
| Přebytek | Fáze | Výkon |
|---|---|---|
| < 3 kW | 0 | 0 W |
| 3–5.9 kW | 1 | 3 kW |
| 6–8.9 kW | 1+2 | 6 kW |
| ≥ 9 kW | 1+2+3 | 9 kW |

**Vzájemná exkluzivita:** Patrony aktivní → NIBE OFF (47371=0). Buď patrony, nebo NIBE.
**Oběhové čerpadlo:** Při patron ohřevu NIBE blokováno (pokud neběží kompresor).

### 5.7 Bazénový ventil
- Při topení domu: zkontrolovat že `switch.bazen_ventil_smesovac` je OFF
- Pokud je ON → vypnout (teplo musí jít do domu, ne do bazénu)
- Jinak na ventil nesahat

### 5.8 Chlazení (letní režim)
- Řízeno stejnou cílovou teplotou (`nastavena_teplota_v_dome`)
- Hystereze: zapnout nad cílem, vypnout pod cílem
- Max přepnutí za den: 4
- Ochrana: nevypínat pokud kompresor běží

### 5.9 Ochrana čerpadla
- **NIKDY** nevypínat NIBE (47371=0) pokud kompresor běží
- Kontrola přes `binary_sensor.nibe_kompresory_aktivni_binarni` a `sensor.nibe_aktualni_realny_stav`

---

## 6. Informace o spotřebě tepla

- Venkovní teplota ~0°C → nádrž nahřát 2-3× denně
- Venkovní teplota ~10°C → nádrž nahřát ~1× denně
- NIBE peak odběr: ~14 kW
- Oběhové čerpadlo: ~300 W
- Patrona: 3× 3 kW = 9 kW max

---

## 7. Architektura flow

**Soubor:** `fve-heating.json`

**Struktura:**
1. **Trigger:** Inject každých 60s + trigger na změnu klíčových stavů
2. **Hlavní funkce:** Čte všechny stavy z HA global context, rozhoduje
3. **Výstupy:** Akce pro každý aktuátor (NIBE, oběhové, patrony, ventil)
4. **Ochrana:** Detekce stavu čerpadla → global `cerpadlo_topi` pro FVE battery blokaci
