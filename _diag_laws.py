#!/usr/bin/env python3
"""
Kompletni diagnostika dle ZAKONY.TXT §2.4 + §1.3:
Proc je grid draw, kdyz mame SOC > min a nejsme v rezimu, ktery by to vyzadoval?

Zjisti:
1. Aktualni mod (real + planovany)
2. Automatizace on/off
3. SOC, solar, spotreba, baterie tok, grid tok
4. Victron PSP, max_discharge_power, max_charge_power
5. Blokace flags (NIBE, sauna, nabijeni auta)
6. Poslední log radky z fve_log.jsonl
7. Vyhodnoceni - je to v souladu se zakony?
"""
import urllib.request, json, sys, subprocess, os
sys.stdout.reconfigure(encoding='utf-8')

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyYzg3OGM0MGM4MzU0MzI1OGZiZDcxODFhM2ZlZTQyZiIsImlhdCI6MTc3MTg4NzE0MywiZXhwIjoyMDg3MjQ3MTQzfQ.y2NTKxC9b67IlReCS6e-S2TVNCiv1mc1-RGSFUcnwuc"

def s(eid):
    req = urllib.request.Request(f"http://localhost:8123/api/states/{eid}",
                                  headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
            return d.get("state")
    except Exception as e:
        return None

def f(eid, default=0.0):
    v = s(eid)
    try: return float(v)
    except: return default

print("=" * 80)
print("  1) FVE MOD / AUTOMATIZACE / PLAN")
print("=" * 80)
print(f"  input_select.fve_manual_mod        = {s('input_select.fve_manual_mod')}")
print(f"  sensor.fve_aktualni_mod            = {s('sensor.fve_aktualni_mod')}")
print(f"  sensor.fve_plan (current_mode attr)= ", end="")
req = urllib.request.Request(f"http://localhost:8123/api/states/sensor.fve_plan",
                              headers={"Authorization": f"Bearer {TOKEN}"})
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        d = json.loads(r.read())
        a = d.get("attributes", {})
        print(f"{a.get('current_mode','?')}  (plan header: {a.get('blokace_text','-')})")
except Exception as e:
    print(f"ERR: {e}")
print(f"  input_boolean.fve_automatizace     = {s('input_boolean.fve_automatizace')}")
print(f"  input_boolean.automatizovat_topeni = {s('input_boolean.automatizovat_topeni')}")

print()
print("=" * 80)
print("  2) ENERGIE TOKY")
print("=" * 80)
soc = f("sensor.battery_percent")
solar = f("sensor.pv_power_fve") + f("sensor.pv_power_garaz")
spotr = f("sensor.celkova_spotreba")
batP = f("sensor.battery_power_plus")  # +nabiji / -vybiji ?
batM = f("sensor.nabijeni_baterii_plus")
battery_flow = f("sensor.system_battery_power")
grid_net_in = f("sensor.fve_net_odber_ze_site")
grid_net_out = f("sensor.fve_net_dodavka_do_site")
print(f"  SOC baterie:         {soc} %")
print(f"  Solar vyroba (FVE+garaz):      {solar:>8.0f} W")
print(f"  Celkova spotreba domu:         {spotr:>8.0f} W")
print(f"  Baterie tok (system_battery):  {battery_flow:>+8.0f} W  (+ = nabiji, - = vybiji)")
print(f"  nabijeni_baterii_plus:         {batM:>8.0f} W")
print(f"  Grid NET import:               {grid_net_in:>8.0f} W")
print(f"  Grid NET export:               {grid_net_out:>8.0f} W")

print()
print("=" * 80)
print("  3) VICTRON ESS PARAMETRY")
print("=" * 80)
psp = f("number.power_set_point")
mdp = f("number.max_discharge_power")
mcp = f("number.max_charge_power")
feedin = s("switch.overvoltage_feed_in")
print(f"  power_set_point (PSP):       {psp:>+8.0f} W  (>0 import / <0 export)")
print(f"  max_discharge_power:         {mdp:>+8.0f}    (-1 = unlimited, 0 = blokace)")
print(f"  max_charge_power:            {mcp:>+8.0f}    (-1 = unlimited, 0 = blokace)")
print(f"  switch.overvoltage_feed_in:  {feedin}")

print()
print("=" * 80)
print("  4) BLOKACE FLAGS (§4.8 blokace vybijeni)")
print("=" * 80)
print(f"  binary_sensor.nibe_kompresory_aktivni_binarni = {s('binary_sensor.nibe_kompresory_aktivni_binarni')}")
print(f"  switch.nibe_topeni                            = {s('switch.nibe_topeni')}")
print(f"  input_boolean.virivka                         = {s('input_boolean.virivka')}")
print(f"  input_boolean.auto_ma_hlad                    = {s('input_boolean.auto_ma_hlad')}")
print(f"  sensor.charger_state_garage                   = {s('sensor.charger_state_garage')}")
print(f"  sauna_aktivni (nema entitu - kontroluje NR)")

print()
print("=" * 80)
print("  5) POSLEDNI LOG RADKY (fve_log.jsonl)")
print("=" * 80)
r = subprocess.run(["tail", "-5", "/homeassistant/fve_log.jsonl"],
                    capture_output=True, text=True, timeout=5)
for line in r.stdout.strip().split("\n"):
    try:
        e = json.loads(line)
        print(f"  {e.get('ts','?')[:19]} mode={e.get('mode','?'):20s} soc={e.get('soc','?')} "
              f"prebytek={e.get('prebytek_w',0)} blockDisch={e.get('block_discharge','?')} "
              f"nibe={e.get('nibe','?')} topeni_mod={e.get('topeni_mod','?')}")
    except: pass

print()
print("=" * 80)
print("  6) VYHODNOCENI PROTI ZAKONUM")
print("=" * 80)
# get current mode
cur_mode = s('sensor.fve_aktualni_mod') or s('input_select.fve_manual_mod')
auto_on = s('input_boolean.fve_automatizace') == 'on'

print(f"  Mod: {cur_mode}")
print(f"  Automatizace: {'ON' if auto_on else 'OFF'}")
print(f"  SOC: {soc} % (min_soc = 20)")
print(f"  Grid net: {grid_net_in - grid_net_out:+.0f} W")
print()

net_flow = grid_net_in - grid_net_out
violations = []
ok = []

if not auto_on:
    violations.append("Automatizace OFF - Fan-out blokuje Victron zapisy, cokoliv se deje je MIMO NR ovladani")
else:
    # Normal mode check
    if cur_mode in ("normal", "Normal"):
        if net_flow > 200 and soc > 25 and s('binary_sensor.nibe_kompresory_aktivni_binarni') != 'on':
            violations.append(f"§4.2 NORMAL mod + SOC {soc}% + NIBE off + grid import {net_flow:.0f} W -> "
                              f"baterie MA vybijet, nema brat ze site")
        else:
            ok.append(f"§4.2 NORMAL - grid {net_flow:+.0f} W odpovida situaci (NIBE/sauna/SOC)")
    elif cur_mode in ("setrit", "Šetřit", "Setrit"):
        if net_flow < 0 and soc > 20:
            violations.append(f"§4.3 SETRIT + solar prebytek -> export {-net_flow:.0f} W - mozne, pokud PSP=0")
        ok.append(f"§4.3 SETRIT - baterie se nevybiji, grid kryje deficit {net_flow:+.0f} W (povoleno)")
    elif cur_mode in ("zakaz_pretoku", "Zákaz přetoků"):
        if net_flow > 200:
            violations.append(f"§4.6 ZAKAZ PRETOKU - grid import {net_flow:.0f} W > 150W povoleno")
        if net_flow < -100:
            violations.append(f"§4.6 ZAKAZ PRETOKU - export {-net_flow:.0f} W porusuje feedin_off")

if psp > 500 and cur_mode in ("normal", "Normal"):
    violations.append(f"NORMAL mod + PSP = {psp} W - v NORMAL by PSP mel byt ~0 (battery discharge target)")

if solar > 100 and mdp == 0:
    violations.append(f"Solar bezi {solar} W, ale max_discharge_power=0 -> solar throttling bug")

if ok:
    print("  OK dle zakonu:")
    for o in ok: print(f"    - {o}")
if violations:
    print("  PORUSENI ZAKONU:")
    for v in violations: print(f"    !!! {v}")
else:
    print("  Zadna zjevna porusovani zakonu nenalezena.")
