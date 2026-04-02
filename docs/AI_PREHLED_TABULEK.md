# AI výstupy (jen když v chatu požádáš)

**Jediný soubor v `docs/`, kam AI cíleně doplňuje** krátké shrnutí nebo tabulku podle tvého zadání v `problemy.txt`.  
**Pravda o pravidlech a provozu:** `User inputs/ZAKONY.TXT` a kód v `node-red/flows/` — ne tento soubor.  
**AI nemění** `User inputs/problemy.txt`.

---

## Co AI vždy bere v potaz (bez dlouhých tabulek zde)

| Téma | Kde to je |
|------|-----------|
| Zákony projektu | `User inputs/ZAKONY.TXT` |
| Technický kontext, SSH, workflow | `docs/PROJEKT_SHRNUTI.md` |
| Ovládání z pohledu uživatele | `docs/UZIVATELSKA_PRIRUCKA.md` |
| Starší poznámky (nízká priorita) | `docs/KONVERZACE_KONTEXT.md` |

**Stabilní baseline v gitu:** `75d56bb` (25. 3. 2026 13:00:09 +0100). Porovnání: `git log 75d56bb..HEAD --oneline` v `HA/`.

**Deploy na HA:** jen po tvém výslovném souhlasu v chatu; příkaz § 2.1 v `ZAKONY.TXT`.

**Zadání v rozporu se `ZAKONY.TXT`:** AI neimplementuje ani nenasazuje — popíše konflikt (§) a počká na rozhodnutí / úpravu zákonů.

---

## Záznamy (doplňuje AI podle požadavku)

*(Níže krátké vstupy s datem — jen pokud o ně v chatu požádáš.)*

### 2026-04-02 — shrnutí práce (chat, bez změn flow v gitu)

| Oblast | Co proběhlo | OK? |
|--------|----------------|-----|
| **Vysvětlení plánu** | `sensor.fve_plan` řádek „Střední cena (NIBE topí)“ = **simulace spotřeby/SOC**, ne příkaz k topení; §8.2/§8.3 platí hlavně pro **`fve-heating.json`**, orchestrátor v noci **nefiltruje** velký solar jako topení. | **OK** (srozumitelné vůči `ZAKONY.TXT`) |
| **Návrh úpravy kódu** | Návrh: při `predikce dnes ≥ topeni_solar_high_day_kwh` vypnout **noční** model NIBE v `rf_gen_plan_0004` + opravit **`planAgg`**: nepoužívat `x.fD` (dny od full charge), ale **`fc.dnes` / live forecast**. | **OK** jako návrh |
| **Implementace v repu** | Krátce **vloženo** do `fve-orchestrator.json`, po upřesnění „jen návrh, nic nenasazovat“ **vráceno** (stav flow = před úpravou). | **Proces: chyba** (implementace bez výslovného souhlasu s úpravou gitu); **náprava revertem: OK** |
| **Monitoring HA (MCP)** | Ověřeno: při plánu s „(NIBE topí)“ v noci byl **`switch.nibe_topeni` off**, **`topeni_mod` Vypnuto**, vysoká predikce dnes/zítra — **rozpor plán vs. realita**, ne nutně porušení §1.2 u fyzického NIBE. | **OK** (důkaz ze serveru) |
| **Deploy** | Nasazení na server **ne** (dle tvých pokynů). | **OK** |
| **Instrumentace debug** | V workspace **nebyla** trvalá `fetch`/ingest instrumentace v `HA/`; úklidy bez změn kódu. | **OK** |

**Celkový verdikt:** Obsahová práce (analýza, návrh, monitoring) **OK**. Jediná slabina workflow: jednou **úprava orchestrátoru bez jasného „chci patch v gitu“** — už **srovnáno revertem**; v gitu dnes zůstává jen tvoje úprava `problemy.txt`.
