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

### 3. VÝBĚR DEPLOY REŽIMU (§2.1.1) — POVINNÉ ROZHODNUTÍ PŘED DEPLOYEM
- **`scripts/deploy.sh --no-ha`** = VÝCHOZÍ VOLBA. Použít VŽDY, když se mění JEN `node-red/flows/*.json` a/nebo dokumentace.
- **`scripts/deploy.sh`** (restart HA Core) = JEN když se mění HA konfigurace: `template_*.yaml`, `input_*.yaml`, `automations.yaml`, `scripts.yaml`, `configuration.yaml`, `mqtt.yaml`, `modbus.yaml`, `themes/*.yaml`, `scenes.yaml`.
- **Restart HA Core je DESTRUKTIVNÍ (výpadek celého systému). Pokud si nejsem jistý → VŽDY `--no-ha`.**
- Pozn.: skript je v `scripts/deploy.sh` (NE v rootu repa).

### 4. POŘADÍ: nasadit → OVĚŘIT → AŽ POTOM push do main (§2.5)
**§2.5: `git push` do main provádět AŽ POTÉ, co ověřím, že nasazení je OK. DŘÍVE NE.**
Protože `deploy.sh` klonuje z gitu, verifikace před pushem do main se dělá přes feature branch:
1. `git commit` lokálně + `git push` na **feature branch** (NE main).
2. Deploy z branch:
```
ssh -i "$env:USERPROFILE\.ssh\id_ha" -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 "rm -rf /tmp/HA; cd /tmp && git clone -b <branch> https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash scripts/deploy.sh --no-ha 2>&1 | tail -20"
```
3. **OVĚŘIT**: NR logy (`sudo docker logs addon_a0d7b954_nodered --since 2m 2>&1 | grep -i -E 'error|warn|exception' | tail -10`), HA stavy (baterie, grid draw, wallbox), `sensor.fve_plan` bez NaN, soulad se ZAKONY.TXT.
4. **Až po čistém ověření**: merge branch → main + `git push origin main`.
5. Aktualizovat `docs/PROJEKT_SHRNUTI.md`.

### 5. Úklid (VŽDY)
- Smazat VŠECHNY temp soubory lokálně: `_fix_*`, `_check_*`, `_apply_*`, `_revert_*`, `_htg_*`
- Smazat temp soubory na serveru: `rm -f /tmp/_*.py /tmp/_*.sh /tmp/_*.js /tmp/_*.txt`
- Smazat `/tmp/HA` na serveru (deploy.sh to dělá, ale ověřit)

### KRITICKÁ PRAVIDLA
1. **Deploy.sh nahrazuje CELÉ taby z gitu.** Pokud git verze tabu je starší než serverová (uživatel mezitím změnil parametr v NR UI), deploy PŘEPÍŠE uživatelovu změnu. Proto je POVINNÉ vždy stáhnout server flows PŘED jakoukoli úpravou a použít je jako základ + ověřit `server == git + moje změny`.
2. **`--no-ha` je výchozí (§2.1.1).** NIKDY nerestartovat HA Core, pokud se nemění HA yaml konfigurace.
3. **Push do main až PO ověření nasazení (§2.5).** Nikdy ne dříve.
