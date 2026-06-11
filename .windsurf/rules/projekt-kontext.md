---
trigger: always_on
---

# POVINNÁ PRAVIDLA (vždy dodržet)

## 1. KONTEXT — číst zákony PO KAŽDÉM PROMPTU
- Pokud NEJSEM plně v kontextu, na začátku KAŽDÉHO promptu PŘEČTI:
  - `User inputs/ZAKONY.TXT` — **CELÝ soubor, všechny zákony, ne jen část**
  - `User inputs/problemy.txt` — aktuální požadavky uživatele
  - `docs/PROJEKT_SHRNUTI.md` — technický kontext systému
- Teprve POTOM analyzuj nebo nasazuj. Bez kontextu NEZAČÍNEJ.

## 2. NEOTEVÍRAT ZBYTEČNĚ SOUBORY V IDE
- Uživatele VELMI obtěžuje, když se mu v IDE otevírají soubory, které řeším — musí je pak ručně zavírat.
- Minimalizuj počet otevřených souborů:
  - Preferuj `grep_search` / cílené skripty (Python) pro extrakci obsahu místo `read_file`.
  - Velké soubory (flows.json, dlouhé funkce) NEČTI celé přes `read_file` — vypiš si potřebnou část skriptem do TEMP mimo repo.
  - Dávkuj čtení, nečti soubory „pro jistotu".
- Drž projekt čistý (zákon 2.0): žádné dočasné soubory v repu, vždy uklidit.
