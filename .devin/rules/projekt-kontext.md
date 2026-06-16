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

## 1b. PŘÍKAZ „POKRACUJ" / „NEXT" (ABSOLUTNÍ)
- Když uživatel napíše **POKRACUJ**, **pokracuj** nebo **NEXT**, znamená to: **POKRAČUJ V ŘEŠENÍ PROBLÉMŮ Z `User inputs/problemy.txt`**.
- Pracuj autonomně přes VŠECHNY problémy v tom souboru — analyzuj, oprav, nasaď, ověř (git==server, `node --check`, deploy `--no-ha`, verifikace na živém systému).
- NEPTEJ SE zbytečně na potvrzení. Ptej se JEN při tvrdém konfliktu se zákony nebo bezpečnostním riziku (§1.3). Jinak prostě řeš dál.

## 2. NIKDY NEOTEVÍRAT SOUBORY V IDE (ABSOLUTNÍ — i při analýze)
- Uživatel chce mít v IDE otevřené JEN soubory, které si sám otevře. Cokoliv otevřu já = chyba.
- **NEPOUŽÍVAT `read_file`** k analýze obsahu — `read_file` soubor v IDE otevře. To je zakázané.
- Místo toho VŽDY:
  - `grep_search` (MatchPerLine) — výsledky se zobrazí v chatu, soubor se NEOTEVŘE.
  - `python -c "..."` — vypsat potřebný obsah přímo do terminálu (žádné otevření).
  - Když potřebuju delší výpis, skript zapíše výstup do TEMP MIMO repo a čtu odtud — ne přes otevření zdrojového souboru v IDE.
- Editace souborů: měň cíleně (edit/transform skript), neotevírej je „na koukání".
- Drž projekt čistý (zákon 2.0): žádné dočasné soubory v repu, vždy uklidit.
