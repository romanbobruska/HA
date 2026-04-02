---
description: Jak správně provést deploy změn do HA/Node-RED
---

## Povinný workflow pro KAŽDÝ prompt

### 1. Na začátku KAŽDÉHO promptu
- Přečíst `User inputs/ZAKONY.TXT` (zákony projektu)
- Přečíst `problemy.txt` (uživatelovy aktuální problémy/požadavky)
- Přečíst `docs/PROJEKT_SHRNUTI.md` (kontext systému)

### 2. Před úpravou JAKÉHOKOLIV flow souboru (ABSOLUTNÍ ZÁKON 1.2 + 2.3)
**VŽDY má přednost stav Node-RED na serveru HA před lokální verzí. NIKDY nepřepisovat stav v HA lokální verzí.**
// turbo
- Stáhnout aktuální flows ze serveru:
```
ssh -i "$env:USERPROFILE\.ssh\id_ha" -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 "cat /addon_configs/a0d7b954_nodered/flows.json" > "$env:TEMP\_server_flows.json"
```
- **Serverová verze = PRAVDA** — zahrnuje VŠECHNO: flows, nody, layout (x,y,w,h), parametry, config hodnoty
- Aplikovat POUZE cílené změny na serverovou verzi
- NIKDY nepřepisovat uživatelovy ruční změny — uživatel mění parametry přímo v NR UI na serveru
- Deploy.sh nahrazuje CELÉ taby z gitu → git MUSÍ obsahovat aktuální serverovou verzi + moje změny

### 3. Deploy
```
ssh -i "$env:USERPROFILE\.ssh\id_ha" -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 "rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh 2>&1"
```

### 4. Po deployi (VŽDY)
- Zkontrolovat NR logy: `ssh ... "sudo docker logs addon_a0d7b954_nodered --since 2m 2>&1 | grep -i -E 'error|warn|exception' | tail -10"`
- Ověřit HA stavy (filtrace, baterie, grid draw, wallbox)
- Ověřit soulad se zákony z ZAKONY.TXT
- Aktualizovat `docs/PROJEKT_SHRNUTI.md`
- Git commit + push

### 5. Úklid (VŽDY)
- Smazat VŠECHNY temp soubory lokálně: `_fix_*`, `_check_*`, `_apply_*`, `_revert_*`, `_htg_*`
- Smazat temp soubory na serveru: `rm -f /tmp/_*.py /tmp/_*.sh /tmp/_*.js /tmp/_*.txt`
- Smazat `/tmp/HA` na serveru (deploy.sh to dělá, ale ověřit)

### KRITICKÉ PRAVIDLO
**Deploy.sh nahrazuje CELÉ taby z gitu.** Pokud git verze tabu je starší než serverová (uživatel mezitím změnil parametr v NR UI), deploy PŘEPÍŠE uživatelovu změnu. Proto je POVINNÉ vždy stáhnout server flows PŘED jakoukoli úpravou a použít je jako základ.
