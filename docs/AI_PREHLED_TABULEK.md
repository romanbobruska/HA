# Přehledy pro uživatele (AI výstupy)

Tento soubor slouží k **přehledným tabulkám** a shrnutím z práce s AI.  
**Vstupní poznámky** píš do `User inputs/problemy.txt` — ten soubor AI **nemění**.  
**Orientace v repu:** tabulka odkazů je v **`docs/KDE_CO_NAJDES.md`** (ne v `README.md`).

---

## 1. Řez „stabilní verze“ v gitu (**svatý grál**)

Při problémech se vracet k tomuto stavu (`git checkout 75d56bb` / diff / cherry-pick dle potřeby) a porovnávat `main`.

| Položka | Hodnota |
|--------|---------|
| **Git commit (plný)** | `75d56bbc0e04f9fb17431379d70df6d1f1f2d4c3` |
| **Datum / čas v gitu** (Author i Commit) | **středa 25. 3. 2026, 13:00:09** (časové pásmo **+0100** CET) |
| Zpráva commitu | `fix: repair CP852 encoding corruption in fve-orchestrator.json (228 nodes)` |
| Referenční okamžik řezu (projekt) | čtvrtek **26. 3. 2026, 02:00** — „poslední commit před tímto okamžikem na `main`“ = výše uvedený `75d56bb` |
| Commity poté | první změny až **27. 3. 2026** (mezi řezem a půlnocí 27. 3. nebyl commit) |
| Seznam změn od stabilní | `git log 75d56bb..HEAD --oneline` v adresáři `HA` |

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
| Zastaralý `pat_block_charge` při manuálu topení / FVE OFF / NIBE boost | Střední | **v24.85:** Patrony korekce v2.1 — vždy sync globálu před časným returnem |

---

## 5. Jak to používat

| Kdo | Co |
|-----|-----|
| Ty | Pišeš zadání / otázky do **`User inputs/problemy.txt`** |
| AI | Odpovídá v chatu a **doplňuje / aktualizuje tabulky v tomto souboru**, pokud jde o shrnutí k projektu |
| Git | `HA` repo — po ověření na HA commit + push dle tvého workflow |

### Pravidlo nasazení na Home Assistant (odsouhlasení)

1. AI **nejprve vypíše**, co by se nasadilo (rozsah / commity / stručný důvod vůči zákonům).  
2. **Deploy přes SSH** podle `User inputs/POZADAVKY.TXT` § 2.1 AI **nespouští**, dokud ty **výslovně neodsouhlasíš** („nasadit“, „spusť deploy“, apod.).  
3. Pokud najde **zásadní rozpor se zákony**, **neposouvá nasazení** — nejdřív popis a návrh, čeká na tvé rozhodnutí.

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

**Aktualizace:** změny z relace (v24.84+) jsou na `main` commitnuté a pushnuté, dokud nevzniknou nové lokální úpravy.

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

---

## 8. Kompletní analýza změn od stabilní verze (`75d56bb`, 26. 3. 2026 02:00)

### Dává to smysl?

**Ano v rámci cíle:** levná energie, solár, zákon 4.3 (Šetřit bez zbytečného čerpání při přebytku), bezpečnost NIBE×patrony, plán 4.9, auto § 5.x, vypnutá FVE automatizace → žádné zápisy Victron. Řada commitů je **úzce provázaná** (DRAIN větev u auta, pak návrat grid priority) — finální stav po **v24.84** je konzistentní se zákony z diskuse.

**Riziko:** složitost (§ 1.3) roste; každá další větev v plánu nebo módu zvyšuje náklad na testování na HA.

### Seznam commitů `75d56bb..HEAD` (chronologicky od nejstaršího po nejnovější)

| Commit | Zkratka obsahu |
|--------|----------------|
| `466afc7` | Šetřit: PSP při solárním přebytku nečerpá ze sítě |
| `f783e25` | Šetřit PSP dle § 4.3 |
| `2b89a31` | Dočasná instrumentace (později pryč) |
| `6745012` | NIBE × highSolDay × `patMohou` |
| `1340562` | Blok výběje NIBE jen při PV pod override |
| `ff0c21f` | Odstranění debug ingest |
| `1928828` | Korekce auta při high solar |
| `25676b5`–`3e0a4ba` | Agresivní NORMAL, § 4.9, NORMAL+NIBE |
| `6558403`–`746b9be` | EV smyčka: grid senzor, grid priorita, clamp |
| `365904b`–`6b592ed` | NORMAL: výběj při NIBE, grid-support |
| `3ee09d3` | Victron OFF při vypnuté FVE auto |
| `c6207c7`–`2705d77` | EV / hunger / SOC>95 iterace |
| `4b70326` | Obnova stabilních hunger + EV větví |
| `a110388`–`3c6452d` | DRAIN u auta: cíl, no-grid, vzorec |
| `1e37aea` | Hard-stop korekcí patronů při FVE OFF |
| `ffb6bd7`–`d5b1848` | Plán: `dnuOdBalance` / `last_pylontech`, Date.parse |
| `3561bec`–`1848e8f` | Úklid deploy diag, DIAG fan-out |
| `0110890` | v24.84: manager v24.2, solar v5.1, docs, problemy přesun |
| `cc0a578` | v24.85: Patrony korekce v2.1 — synchronizace `pat_block_charge` při časných návratech |

### Inkrementální oprava v24.85 (bez změny hlavní logiky smyčky)

**Patrony korekce v2.1** (`fve-orchestrator.json` + `fve-heating.json`, stejný uzel):

- Při **FVE automatizace OFF** → `global.set("pat_block_charge", false)` před návratem (jinak mohla zůstat **zastaralá** hodnota z minulého cyklu a Šetřit/Normal by špatně nastavovaly `max_charge_power`).
- Při **automatizovat topení OFF** (manuál) → ihned `pat_block_charge = false` (dříve se hlavní synchronizační řádek neprovedl).
- Při **NIBE boost → patrony OFF** → stejná synchronizace `pat_block_charge` a `chgMsg(_pN)` jako při normálním výpočtu (místo slepého `chgMsg(-1)`).

Tím se Victron konfigurace z globálu **nesplituje** s tím, co posílá druhý výstup korekce.

---

## 9. Terminologie + rozhodnutí o změně (příklad: odběr ze sítě v NORMAL)

### 9.1 „Zákony“ v tomto projektu

| Co si pod tím představit | Co to **není** |
|--------------------------|----------------|
| Soubor **`User inputs/POZADAVKY.TXT`** = tvá **závazná pravidla** pro kód, módy, deploy a prioritu zařízení | **Ne** jsou to paragrafy zákonů ČR ani obecná „legal“ interpretace — při rozporu s fyzikou nebo Victronem se řeší **technicky** a případně **úpravou tvých pravidel v tom souboru** (edituješ ty). |

### 9.2 Požadavek (test): „zařídit braní ze sítě i v NORMAL módu“

Rozlišují se **dva významy** stejné věty:

| Varianta změny | Udělám / neudělám | Proč (podle **tvých** pravidel v POZADAVKY) |
|----------------|-------------------|---------------------------------------------|
| **A)** Spotřeba domu > to, co pokryje výběj baterie → **doplnění deficitu ze sítě** (pasivně, „zbytek ze sítě“) | **Ne jako nová funkce** — § **4.2 NORMAL** už říká, že baterie se vybíjí podle spotřeby a **zbytek se bere ze sítě**. Pokud to na krabičce nevidíš, jde o **bug / nastavení Victronu (PSP, limity)**, ne o chybějící „dovolení“ v pravidlech. | Úprava kódu jen **po důkazu z běhu** (senzory, log), ne „protože legal“. |
| **B)** Ve **drahé** hodině v NORMALu **záměrně zvyšovat nákup ze sítě** (např. aktivně nabíjet baterii z DS v tom samém módu, který má být „vybíjí baterii“) | **Neudělám bez tvé změny POZADAVKY** | Odporuje smyslu módu v § **4.1** (Normal = drahé hodiny, vybíjí baterii) a cíli § **1.0** / § **4.9** (nekupovat zbytečně draze). Nabíjení z DS patří do **„Nabíjet ze sítě“** § **4.4** za podmínek plánu. |
| **C)** Nasadit cokoli, co **nesedí** s aktuálním textem POZADAVKY | **Ne** | Nejdřív **vysvětlím rozpor**; nasazení až po tvém rozhodnutí / úpravě pravidel (viz § **5** výše — deploy po odsouhlasení). |

*Poslední doplněk sekce 9: reakce na upřesnění „zákony = jen moje pravidla, ne legal“.*

---

## 10. Šablona odpovědi AI, když zadání **odporuje** POZADAVKY

*(Včetně záměrného testu — stejná struktura; Cursor to má i v `.cursor/rules/ha-problemy.mdc`.)*

| Krok | Obsah odpovědi |
|------|----------------|
| 1 | **Přepis požadavku** — co přesně má být uděláno (1 věta). |
| 2 | **Konflikt** — odkaz na **konkrétní § / odstavec** v `User inputs/POZADAVKY.TXT` a proč je to v rozporu. |
| 3 | **Zákaz akce** — **ne** změna flow / konfigurace / **deploy**, dokud se pravidla neupraví v POZADAVKY nebo nedáš výslovnou výjimku. |
| 4 | **Možnosti pro tebe** — upravit POZADAVKY sám; přeformulovat zadání v souladu s pravidly; nebo požádat o návrh nového odstavce do POZADAVKY. |
| 5 | *(Test)* Krátké potvrzení, že šlo o kontrolu chování AI — při reálném konfliktu platí 1–4. |
