#!/usr/bin/env python3
"""URGENT FIX: NIBE se vypnulo protože mode=Patrony ale patrony nemůžou běžet (SOC < MIN_SOC_PAT).
Fix: přidat patronyMohou do podmínky pro přepnutí na Patrony mod."""
import json, sys

HTG_FILE = r"d:\Programy\Programování\Node Red\HA\node-red\flows\fve-heating.json"
NODE_ID = "htg_main_func"

with open(HTG_FILE, "r", encoding="utf-8") as f:
    nodes = json.load(f)

node = None
for n in nodes:
    if n.get("id") == NODE_ID:
        node = n
        break

if not node:
    print("ERROR: Node not found")
    sys.exit(1)

func = node["func"]

# Fix: Add patronyMohou check to Patrony mode condition
# Without this, mode switches to "Patrony" (blocking NIBE) even when patrony can't run
old = "if (isSolarHour && tempGap <= PATRON_TEMP_MARGIN && needsHeat && patronyRealisticke) {"
new = "if (isSolarHour && tempGap <= PATRON_TEMP_MARGIN && needsHeat && patronyRealisticke && patronyMohou) {"

if old in func:
    func = func.replace(old, new)
    print("OK: Added patronyMohou check to Patrony mode condition")
else:
    print("ERROR: Pattern not found")
    sys.exit(1)

node["func"] = func

with open(HTG_FILE, "w", encoding="utf-8") as f:
    json.dump(nodes, f, ensure_ascii=False, indent=4)

print("Done! NIBE should turn on after deploy.")
