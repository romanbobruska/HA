# Přehledy pro uživatele (AI výstupy)

Tento soubor slouží k **přehledným tabulkám** a shrnutím z práce s AI.  
**Vstupní poznámky** píš do `User inputs/problemy.txt` — ten soubor AI **nemění**.

---

## 1. Řez „stabilní verze“ v gitu

| Položka | Hodnota |
|--------|---------|
| Datum / čas řezu | čtvrtek **26. 3. 2026, 02:00** |
| Přibližný commit | `75d56bb` (poslední commit před tímto okamžikem na `main`) |
| Commity poté | první změny až **27. 3. 2026** (mezi řezem a půlnocí 27. 3. nebyl commit) |
| Seznam změn | `git log 75d56bb..HEAD --oneline` v adresáři `HA` |

---

## 2. Hlavní změny oproti stabilní verzi (témata)

| Oblast | Stručně |
|--------|---------|
| Šetření / PSP (§ 4.3) | PSP ve Šetřit nečerpá ze sítě při solárním přebytku; dynamika dle zákonů; dočasná instrumentace odstraněna |
| highSolDay × patrony | Doplnění `patMohou`; blok výběje pro NIBE jen když PV pod `topeni_solar_override_w` |
| NORMAL + NIBE | Výběj baterie při NIBE, grid-support, úpravy PSP; plán: agresivní NORMAL při vysoké solární predikci (živá HA) |
| Victron / FVE vypnuto | Fan-out neposílá nic na Victron při `fve_automatizace` OFF; hard-stop korekcí patronů |
| Plán / balance | `dnuOdBalance` z `last_pylontech` + `Date.parse` — konec falešných „999 dní“ |
| DRAIN / EV | Úpravy výběje u auta a patronů (včetně vzorců a ochran) |
| Úklid | DIAG komentáře, debug ingest u Šetřit, deploy diags |

---

## 3. Soulad se zákony (`User inputs/POZADAVKY.TXT`) — stručně

| Téma | Stav | Poznámka |
|------|------|----------|
| § 4.3 Šetřit + solar | OK | Dynamický PSP; v dokumentu doplněná tvrdá věta o „ani 1 kWh“ ze sítě při nabíjení z PV |
| § 4.2 NORMAL / NIBE výjimka | OK | Blok výběje jen u NIBE s PV pod prahem override; obdobně zákaz přetoku / solár nabíjení |
| § 4.9 plán — „agresivní NORMAL“ | Interpretace | Není doslova v tabulce 4.9.2; sedí s úvodem § 4.9 (nekupovat draze po levném) + živá predikce |
| § 1.2 NIBE × patrony | OK | Úpravy směřují k mutexu a deferrálům |
| min_soc | OK | Entitu neměníme; ve Šetřit jen efektivní podlaha v logice |
| § 5.0 / § 7.0.2 manager auta | Po opravě OK | Viz řádek níže |

---

## 4. Nalezené konflikty vs stabilní git a provedené opravy

| Problém | Závažnost | Oprava (stav v repozitáři) |
|---------|-----------|----------------------------|
| `manager-nabijeni-auta.json` na v24.1: chyběl `probe_active`, § 5.0 až po „nemá hlad“ | Vysoká | Obnovena logika **v24.2** ze stabilního `75d56bb` |
| `nabijeni-auta-slunce.json`: u `curA ≥ 6` chyběla priorita snížení A při překročení odběru ze sítě | Vysoká | Znovu **grid větev (2 cykly)** před větví DRAIN; DRAIN **vzorec** zachován → označení **v5.1** |
| § 3.4 uživatelské flow | Procesní | Změny jen po tvém srozumění / jako oprava regrese |

---

## 5. Jak to používat

| Kdo | Co |
|-----|-----|
| Ty | Pišeš zadání / otázky do **`User inputs/problemy.txt`** |
| AI | Odpovídá v chatu a **doplňuje / aktualizuje tabulky v tomto souboru**, pokud jde o shrnutí k projektu |
| Git | `HA` repo — po ověření na HA commit + push dle tvého workflow |

*Poslední aktualizace tabulek: souhrn stavu po opravách manager + solární korekce (v24.2 / v5.1).*

---

## 6. Odpověď na: „Jsme v konfliktu se zákony? Je tam bug?“

Kontrola: **statický rozbor kódu** oproti `User inputs/POZADAVKY.TXT` + stav flow po návratu manageru **v24.2** a korekce slunce **v5.1** (grid priorita + DRAIN vzorec). **Nejde o logy z běhu na HA.**

| Otázka | Závěr |
|--------|--------|
| Je v kódu **známý rozpor** se zákony (jako u v24.1 / chybějící grid větev)? | **Ne** — tyto dvě regrese jsou v aktuálních souborech **opravené**. |
| Je **jistota 100 %**, že na reálné instalaci nic neporuší zákony? | **Ne** — to by vyžadovalo provozní měření (odběr ze sítě, PSP, probe, NIBE×patrony v čase). Zákony někde vyžadují „nikdy ze sítě“ u auta — smyčka je k tomu navržená, ale senzor/zpoždění Victronu může občas ukázat jinak než fyzika. |
| „Agresivní NORMAL“ v plánu vs § 4.9.2 | **Ne konflikt, ale rozšíření**: doslova v tabulce 4.9.2 není; odpovídá **úvodnímu pravidlu § 4.9** (nekupovat draze po levném) a používá **živou** solární predikci z HA. |

### Zbývající **nízká** rizika (nejsou „prokázaný bug“, spíš hlídat)

| Oblast | Proč |
|--------|------|
| NORMAL + `gridSupport` + `max_charge_power` | Teoreticky může ovlivnit, jak rychle se baterie nabíjí z PV při NIBE + velkém soláru — sledovat v provozu. |
| Složitost flow | § 1.3 chce jednoduchost; orchestrátor a módy jsou velké — není to rozpor, ale údržba je náročnější. |

### Git

Změny **manager** + **nabijeni-auta-slunce** + **docs** mohou být jen **lokálně necommitnuté** — po ověření na HA je vhodné commitnout a pushnout dle tvého workflow.

---

## 7. Solární nabíjení auta vs patrony — stejná konfigurace Victronu?

**Ne — záměrně ani náhodou nejsou „stejný stav“**, i když obě smyčky regulují podobně (W, odběr ze sítě).

| Vrstva | Co se děje |
|--------|------------|
| **Režim FVE z plánu** | Uzel „Kontrola podmínek“ **nepřepíná** mód na `solar_charging` jen proto, že nabíjíš auto. `msg.currentMode` = plán (`plan.currentMode`), typicky ve dne **`setrit`** nebo **`normal`**, ne nutně **`solar_charging`**. |
| **ŠETŘIT vs SOLÁRNÍ NABÍJENÍ** (logika ve `fve-modes`) | **ŠETŘIT**: dynamický **PSP** z `sensor.rozdil_vyroby_a_spotreby`, **min_soc** = `max(config, liveSoc+2)`, **max_discharge** podle soláru. **SOLÁRNÍ NABÍJENÍ**: **PSP=0**, **min_soc** základní z configu, **max_discharge** jinak (často `-1` bez blokace). To jsou **různé příkazy** do Victronu. |
| **Wallbox** | Dle zákonů je **na síti mimo ESS** — jeho odběr **nemusí být** v „rozdílu“ Victronu. Smyčka auta snižuje A; Victron mezitím může podle PSP **táhnout ze sítě** za jiným účelem. |
| **Patrony** | Korekce patronů každých ~20 s posílá **`max_charge_power`** (`pat_max_charge_svc`) a nastavuje **`pat_block_charge`** podle SOC (≥ práh drain → blok nabíjení). Totéž **globální** `pat_block_charge` čtou i módy (Šetřit, Normal, …). Když patrony **jedou**, zátěž je uvnitř ESS — změní se bilance PV vs spotřeba a často i **subjektivní** „už netahám ze sítě“ (jiný mix než wallbox + ESS). |

**Závěr:** Spíš než „chyba v jedné proměnné“ jde o **jiný aktivní FVE mód** (často Šetřit) oproti profilu **Solární nabíjení**, plus **wallbox mimo Victron**. Chování po zapnutí patronů je tedy **očekávatelně jiné**, ne že by korekční smyčky byly identické vůči Victronu.

**Možné zpřesnění (návrh, ne implementováno):** při aktivním solárním nabíjení auta buď v „Kontrola podmínek“ **vynutit** `solar_charging`, nebo ve Šetřit při `auto_nabijeni_aktivni` sladit PSP/min_soc s režimem solárního nabíjení — to už je změna pravidel, ne jen bugfix.
