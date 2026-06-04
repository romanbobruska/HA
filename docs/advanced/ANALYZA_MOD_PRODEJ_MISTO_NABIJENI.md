# Analýza: nový mód „Prodej do sítě místo nabíjení do baterie"

> **Status:** příprava / analýza. **NENASAZENO.** Drženo v gitu na branchi `advanced`.
> Datum: 2026-06-04. Vychází ze stavu `main` (commit po `53635ca`).

## 1. Co by mód dělal

V hodinách se **solárním přebytkem** (výroba > spotřeba) systém dnes přebytek primárně **ukládá do baterie** (dokud není plná / `max_daily_soc`). Nový mód by v definovaných situacích přebytek **neukládal, ale rovnou exportoval (prodal) do sítě**.

**Důležité odlišení od stávajícího módu `PRODAVAT`:**
- `PRODAVAT` (dnes) = prodej **Z baterie** (vybíjení do sítě ve drahé výkupní hodině).
- Nový mód = rozhodnutí v bodě **solárního přebytku**: *nabít baterii* vs. *exportovat přebytek teď*. Je to **opportunity-cost** rozhodnutí, ne vybíjení baterie.

## 2. Ekonomika — kdy se vyplatí

Rozhodovací bod: mám 1 kWh solárního přebytku. Dvě varianty:

**(B) Prodat teď** → výnos ≈ `sell_now` (přímý AC export, **bez round-trip ztrát, bez amortizace baterie**).

**(A) Nabít baterii** → 1 kWh přebytku se uloží s účinností `chEff` (0.90) a později se využije s `dchEff` (0.90), tj. round-trip `rtEff ≈ 0.81`. Budoucí hodnota uložené kWh:
- **Self-consumption later** (pokryje budoucí spotřebu místo nákupu): `rtEff × buy_future − amort` *(jen pokud v té hodině reálně bude deficit, který by se jinak kryl ze sítě)*.
- **Sell later z baterie** (drahá večerní výkupní hodina): `chEff × sell_future − amort` *(to už ale umí `PRODAVAT`)*.

→ **Hodnota uložení** `V_store = max(rtEff × buy_future_best − amort, chEff × sell_future_best − amort)`.

### Klíčová nerovnost

```
Prodej přebytek TEĎ místo nabíjení, když:
    sell_now  >  V_store
tj. zhruba:
    sell_now  >  rtEff × max(buy_future)  −  amort_per_kwh
```

Reálné parametry systému (z `fve_config`): `rtEff ≈ 0.81`, `amort = 1.5 Kč/kWh`, `kapacita = 28 kWh`, `chEff = dchEff = 0.90`, `max_feed_in = 7.6 kW`, `min_sell_profit = 3 Kč`.

**Příklad:** budoucí nejdražší nákup `buy_future = 3.0 Kč/kWh` → `V_store ≈ 0.81×3.0 − 1.5 = 0.93 Kč/kWh`. Pokud `sell_now > ~0.93 Kč/kWh`, je prodej přebytku výhodnější než ukládání (za předpokladu, že baterie není potřeba pro noční rezervu).

## 3. Kdy je to v PRAXI použitelné (scénáře)

### ✅ Vyplatí se
1. **Letní polední přetoky + plná baterie** — baterie naplněna do 100 % / `max_daily_soc` už dopoledne; odpolední přebytek by se jinak **zařízl curtailmentem** (mód `zakaz_pretoku`). Prodat ho i za nízkou cenu > nechat propadnout (alternativa je nulový výnos).
2. **Vysoká výkupní cena teď + levné budoucí nákupy** — `sell_now` vysoký a noční/budoucí spot levný → uložení má malou hodnotu.
3. **Baterie blízko `max_daily_soc`** a další solár dorazí → není kam ukládat.
4. **Silný solární den** — předpověď ukazuje, že baterie se naplní i bez tohoto přebytku před večerním peakem.

### ❌ Nevyplatí se (mód musí zůstat vypnutý)
1. **Slabý solární den + drahý večerní spot** — radši uložit pro večerní self-consumption/peak.
2. **Potřeba noční rezervy** (`night_reserve_kwh = 10 kWh`) — dokud není rezerva zajištěna, neprodávat přebytek.
3. **Před/během balancování** (Pylontech 1×/30 dní potřebuje 100 % SOC).
4. **SOC pod cílem pro drahé večerní hodiny** — uložení pokryje večerní peak.

## 4. Vztah ke stávající logice (důležité — možná duplicita)

Stávající **`replCost` invariant** (§1.0 v solveru `rf_cena_discharge2`) už částečně toto řeší: *„nikdy neprodávej/nešetři energii, kterou bys pak musel koupit dráž"*. A `PRODAVAT` + agresivní letní prahy (`minSellEff = 0.5 Kč` při `solarPokryvaVse`) už dnes umí prodávat přebytky v létě.

→ **Otázka k rozhodnutí:** je nový mód reálně potřeba jako *samostatný mód*, nebo stačí **rozšířit solver** o explicitní porovnání `sell_now` vs `V_store` v solárních hodinách (charge-gate)? Druhá varianta je čistší (jeden algoritmus, žádný další stavový mód → konzistence s architekturou „jeden solver rozhoduje vše").

## 5. Návrh implementace (NÁČRT — nenasazovat bez schválení)

**Varianta A (preferovaná): rozšíření solveru, ne nový mód**
- Nový config: `prodej_misto_nabijeni_enabled` (default `false`), `min_export_advantage_czk` (práh výhody, např. 0.3 Kč).
- V solveru (`rf_arb_trimming_3`, node 03) pro každou **solární hodinu s přebytkem**:
  1. spočítat `V_store` (nejlepší budoucí využití uložené kWh přes `replCost`/buy/sell mapu),
  2. pokud `sell_now − V_store ≥ min_export_advantage` **A** noční rezerva + balancování + cílový SOC jsou OK → označit hodinu `exportSurplus = true` (charge-gate: zakázat nabíjení, povolit feed-in do `max_feed_in`).
- Výstup do Victronu: `MaxChargePower = 0` pro přebytek, feed-in povolen (≤ 7.6 kW).

**Varianta B: samostatný mód `prodat_prebytek`** (modeIndex 8)
- Přidat do `Rozhodnutí o akci` switch + nový `mode_grp_*` v `fve-modes.json` s Victron logikou.
- Nevýhoda: další stavový mód, víc míst k údržbě, riziko nekonzistence s plánovačem.

## 6. Rizika a okrajové případy
- **Noční rezerva**: nesmí prodat přebytek, pokud by pak chyběla energie na večer/noc.
- **Balancování**: kolize s potřebou 100 % SOC.
- **NIBE/topení/bazén**: přebytek může být potřeba pro spotřebiče (topit „zadarmo" ze soláru) — export má nižší prioritu než lokální využití zdarma.
- **`max_feed_in` (7.6 kW)**: nepřekročit limit střídače/jističe.
- **Záporná výkupní cena**: při `sell ≤ 0` NIKDY neexportovat (řeší `zakaz_pretoku` / `zaporna_nakupni_cena`).

## 7. Doporučení před rozhodnutím (měření)
Než se mód postaví, vyplatí se **týden logovat**:
- kolik kWh/den končí v `zakaz_pretoku` (curtailment) = horní hranice potenciálního zisku,
- profil `sell_now` vs `max(buy_future)` v solárních hodinách.

Pokud je curtailmentu málo a spread `sell_now − V_store` málokdy kladný, **přínos bude malý** a nemusí stát za složitost.

## 8. Závěr (TL;DR)
- Mód dává smysl hlavně **v létě při plné baterii a poledních přetocích**, kde je alternativou nulový výnos (curtailment).
- Ekonomicky: prodávej přebytek teď, když `sell_now > rtEff × max(buy_future) − amort` a baterie není potřeba pro noční rezervu/balancování.
- **Doporučení:** realizovat jako **rozšíření solveru (charge-gate), ne samostatný mód**, a nejdřív změřit potenciál (curtailment kWh/den).

---

# 9. PRAKTICKÉ POUŽITÍ — kdy to reálně vydělá (analýza edge cases)

Systém: **17 kWp, baterie 28 kWh, Victron ESS, max_feed_in 7.6 kW, amort 1.5 Kč/kWh, rtEff ≈ 0.81** (chEff·dchEff 0.9×0.9).

## Klíčová myšlenka, kterou stávající logika plně neřeší
**Cyklus baterie NENÍ zadarmo.** Uložit 1 kWh a později ji vydat stojí: amortizace **1.5 Kč** + round-trip ztráta **~19 %**. Přímý export přebytku TEĎ se těmto nákladům vyhne. Proto v řadě situací **přímý prodej přebytku > ulož-teď-prodej-večer**, i když je večerní výkupní cena vyšší.

Práh (uložit pro večerní prodej vs. prodat teď):
```
prodej teď je lepší, když:  sell_now  >  rtEff × sell_vecer − amort
                            sell_now  >  0.81 × sell_vecer − 1.5
```
Příklad: večerní výkup 4.0 Kč → práh = 0.81×4 − 1.5 = **1.74 Kč**. Tj. když je denní výkup > 1.74 Kč, přímý export bije uskladnění pro večerní prodej (baterie se ušetří).

## Edge case A — KILLER: levná noc dopředu → prodej denní přebytek, dobij v noci
**Situace:** odpolední solární přebytek + výkupní cena dne ~2 Kč; **noc/příští okno má buy blízko 0 nebo záporné** (větrná noc, nízká poptávka).
- **Uložit přebytek:** budoucí hodnota = `rtEff × buy_future` ≈ 0.81 × ~0 ≈ **0 Kč** (energii pak koupíš skoro zadarmo, uskladnění nemá cenu).
- **Prodat přebytek teď:** **+2 Kč/kWh**, baterii dobiješ v noci z levné sítě (mód NABÍJET ZE SÍTĚ).
- **Zisk: ~2 Kč/kWh**, který by jinak propadl. Při 8–12 kWh přebytku = **16–24 Kč/den navíc**.
- Tohle je hlavní lukrativní scénář — nastává hlavně na jaře/podzim a o větrných dnech.

## Edge case B — plná baterie + polední přetoky (anti-curtailment)
Baterie 100 % už dopoledne, odpolední přebytek by se **zařízl** (`zakaz_pretoku`). Alternativa exportu = **0 Kč**. Takže prodat i za nízkou cenu (klidně 0.3–1 Kč) je čistý zisk. Léto, silné dny. Modest, ale „zadarmo".

## Edge case C — vzácná vysoká denní výkupní cena (volatilita trhu)
Občas spike výkupní ceny během dne (záporné ceny jinde v EU → volatilita). Když `sell_now` vyletí na 3–5 Kč v solární hodině, přímý export přebytku (bez cyklu baterie) je nejvýhodnější okamžitý monetizační kanál. Vzácné, ale vysoká hodnota/kWh.

## Edge case D — úspora cyklu baterie + delší životnost
Každá nevyužitá obrátka baterie = ušetřená amortizace **1.5 Kč/kWh** + delší životnost článků. Když denní výkup stojí za to, přímý export šetří baterii pro hodnotnější večerní arbitráž.

## Kvantifikace (hrubý odhad pro jejich systém)
- Dny typu A (levná noc + slušný denní výkup): odhad **15–30 dní/rok**, ~10 kWh × ~2 Kč = **~200–600 Kč/rok**.
- Anti-curtailment léto (typ B): dle množství zaříznuté energie, řádově **stovky Kč/rok**.
- Volatilní spiky (typ C): nárazově desítky Kč/den, pár dní/rok.
- **Souhrn: nízké stovky až ~1000 Kč/rok** — odpovídá „edge case, ale umí vydělat dost peněz". Přesnou hodnotu dá až měření (sekce 7).

## Návrh AUTOMATICKÉHO spínání (charge-gate v solveru — pro pozdější schválení)
V solární hodině s očekávaným přebytkem označit `exportSurplus = true`, když VŠECHNY platí:
1. `sell_now > 0` (nikdy neexportovat při záporné ceně),
2. `sell_now > rtEff × max(buy_future v horizontu) − amort` (uskladnění nemá hodnotu — typ A),
   **NEBO** `SOC ≥ max_daily_soc` / baterie se naplní i bez tohoto přebytku (typ B),
3. **noční rezerva** (`night_reserve_kwh` 10 kWh) je zajištěná levným nočním nákupem nebo zbývajícím solárem,
4. nekoliduje s **balancováním** (to chce 100 % SOC),
5. lokální spotřebiče zdarma (NIBE/bazén/ohřev) mají přednost před exportem.
→ Když splněno: `max_charge = 0`, feed-in do `max_feed_in`. (Přesně to dělá nový mód `prodat_prebytek` — jen by ho spínal solver místo ruky.)

## Jak používat MANUÁLNÍ mód teď (bez auto)
1. Večer/ráno mrkni na spotové ceny: je **dnešní výkup ≥ ~1.5–2 Kč** a **noc/zítra levný nákup**? → typ A.
2. Nebo je baterie plná a poledne přetéká? → typ B.
3. Přepni `input_select.fve_manual_mod = prodat_prebytek` na dobu solárního přebytku.
4. Večer dej zpět na `auto` (nebo NABÍJET ZE SÍTĚ pro levné noční dobití).

## Rizika v praxi
- Zapomenout přepnout zpět → baterie se přes den nenabije a večer chybí (proto je auto-spínání s pojistkou noční rezervy bezpečnější).
- Špatný odhad nočního nákupu → uskladnění by bylo lepší. Auto pravidlo to řeší daty z `fve_prices_forecast`.
