# AI výstupy (jen když v chatu požádáš)

**Jediný soubor v `docs/`, kam AI cíleně doplňuje** krátké shrnutí nebo tabulku podle tvého zadání v `problemy.txt`.  
**Pravda o pravidlech a provozu:** `User inputs/POZADAVKY.TXT` a kód v `node-red/flows/` — ne tento soubor.  
**AI nemění** `User inputs/problemy.txt`.

---

## Co AI vždy bere v potaz (bez dlouhých tabulek zde)

| Téma | Kde to je |
|------|-----------|
| Zákony projektu | `User inputs/POZADAVKY.TXT` |
| Technický kontext, SSH, workflow | `docs/PROJEKT_SHRNUTI.md` |
| Ovládání z pohledu uživatele | `docs/UZIVATELSKA_PRIRUCKA.md` |
| Starší poznámky (nízká priorita) | `docs/KONVERZACE_KONTEXT.md` |

**Stabilní baseline v gitu:** `75d56bb` (25. 3. 2026 13:00:09 +0100). Porovnání: `git log 75d56bb..HEAD --oneline` v `HA/`.

**Deploy na HA:** jen po tvém výslovném souhlasu v chatu; příkaz § 2.1 v POZADAVKY.

**Zadání v rozporu s POZADAVKY:** AI neimplementuje ani nenasazuje — popíše konflikt (§) a počká na rozhodnutí / úpravu zákonů.

---

## Záznamy (doplňuje AI podle požadavku)

*(Níže krátké vstupy s datem — jen pokud o ně v chatu požádáš.)*
