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
