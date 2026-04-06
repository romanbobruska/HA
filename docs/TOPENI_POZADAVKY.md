# Topení — reference entit a `fve_config` (ne zákony)

> **⚠️ Tento soubor není zdroj pravidel.**  
> Všechna závazná pravidla chování (NIBE × patrony, drahé hodiny, ochrana kompresoru, `auto_ma_hlad`, bazén, …) jsou **výhradně** v **`User inputs/ZAKONY.TXT`**.  
> Při jakémkoli rozporu nebo pochybnosti platí **`ZAKONY.TXT`** — ne tento soubor.

**Účel tohoto souboru:** rychlý přehled **HA entit**, **aktuátorů** a **jmenných klíčů** v `fve_config` souvisejících s topením.  
**Implementace:** `node-red/flows/fve-heating.json`.

---

## 1. Komponenty (stručně)

- **NIBE F1345** — nádrž (~14 kW peak), řízení allow přes Modbus 47371  
- **Oběhové čerpadlo** — tlačí teplo z nádrže do domu  
- **Patrony** (3× ~3 kW) — přetok do nádrže dle logiky ve flow a **`ZAKONY.TXT`**  
- **Bazénový ventil** — přepínání okruhu  

---

## 2. Vstupy (HA entity)

| Entity | Popis |
|--------|--------|
| `input_number.nastavena_teplota_v_dome` | Cílová teplota v domě |
| `sensor.hp2551ae_pro_v2_1_0_indoor_temperature` | Skutečná teplota v domě |
| `sensor.teplota_smesovac_teplota` | Teplota ve směšovací nádrži |
| `sensor.hp2551ae_pro_v2_1_0_outdoor_temperature` | Venkovní teplota |
| `sensor.nibe_degree_minutes` | Stupně minuty NIBE (+100 až -30) |
| `switch.teplota_smesovac` | Oběhové čerpadlo domu |
| `switch.patrona_faze_1` | Patrona fáze 1 (~3 kW) |
| `switch.patrona_faze_3_2` | Patrona fáze 2 (~3 kW) |
| `switch.patrona_faze_3` | Patrona fáze 3 (~3 kW) |
| `switch.bazen_ventil_smesovac` | Ventil směšovač → bazén |
| `input_boolean.topi_se_v_krbu` | Topí se v krbu? |
| `input_boolean.chlazeni` | Chlazení povoleno? |
| `input_boolean.automatizovat_topeni` | Automatizace topení ON/OFF |
| `input_boolean.letni_rezim` | Letní / zimní režim |
| `input_boolean.auto_ma_hlad` | Auto potřebuje nabíjení? |
| `sensor.battery_percent` | SOC baterie (%) |
| `sensor.solar_power` | Solární výkon (W) |
| `sensor.fve_dostupny_prebytek` | Dostupný přebytek (W) |
| `binary_sensor.nibe_kompresory_aktivni_binarni` | Kompresor NIBE běží? |
| `sensor.nibe_aktualni_realny_stav` | Textový stav čerpadla |

---

## 3. Výstupy (aktuátory)

| Aktuátor | Ovládání | Popis |
|----------|----------|--------|
| NIBE topení | Modbus reg 47371 (0/1) | Povolení / zákaz hřát nádrž |
| NIBE TUV luxusní teplota | `switch.nibe_prepinac_tuv_luxusni_teplota` (template) | ON = komfort TUV Luxusní (47041=2), OFF = Normální (47041=1), přes `input_select.nibe_tuv_komfort` |
| Oběhové čerpadlo | `switch.teplota_smesovac` | ON/OFF |
| Patrony | `switch.patrona_faze_*` | ON/OFF |
| Bazénový ventil | `switch.bazen_ventil_smesovac` | Kontrola |

---

## 4. Klíče `fve_config` (topení)

| Parametr | Výchozí | Popis |
|----------|---------|--------|
| `topeni_min_teplota_nadrze` | 30 | Min. °C nádrže pro oběh |
| `topeni_max_teplota_nadrze` | 50 | Max. °C nádrže pro topení domu |
| `topeni_nocni_snizeni` | 0.5 | Noční snížení cíle °C |
| `topeni_nocni_od` / `topeni_nocni_do` | 22 / 6 | Noční okno (hodina) |
| `topeni_nouzova_teplota` | 18 | Nouzová teplota °C |
| `topeni_min_pretok_patron_w` | 3000 | Min. přebytek W pro 1. patronu |
| `topeni_patron_faze_w` | 3000 | Výkon fáze W |
| `topeni_min_soc_patron` | 95 | Min. SOC % pro patrony |
| `topeni_max_teplota_patron` | 60 | Max. °C nádrže při patronách |
| `prah_draha_energie` | 12 | Level drahé energie (sdíleno s FVE) |

*(Další klíče pro patrony / NIBE / solar override jsou v `fve_config` ve flow — pravda o významu a limitech v **`ZAKONY.TXT`** a v kódu `fve-heating.json`.)*
