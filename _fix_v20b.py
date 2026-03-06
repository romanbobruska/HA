#!/usr/bin/env python3
"""Fix v20b: Balancování NIKDY v hodině se zápornou prodejní cenou"""
import json, sys

ORCH_FILE = r"d:\Programy\Programování\Node Red\HA\node-red\flows\fve-orchestrator.json"
NODE_ID = "9e0b46a9dfedea33"

with open(ORCH_FILE, "r", encoding="utf-8") as f:
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

# Fix: Add priceSell > 0 to solar balancing condition
old = "if (solarOffsets[offset] && simulatedSoc >= balancingMinSoc) {"
new = "if (solarOffsets[offset] && simulatedSoc >= balancingMinSoc && priceSell > 0) {"

if old in func:
    func = func.replace(old, new)
    print("OK: Added priceSell > 0 condition to solar balancing")
else:
    print("ERROR: Pattern not found")
    sys.exit(1)

# Also remove the "(zákaz přetoků)" suffix since it can never happen now
old2 = '            if (priceSell <= 0) balReason += " (zákaz přetoků)";\n'
if old2 in func:
    func = func.replace(old2, "")
    print("OK: Removed dead code (zákaz přetoků suffix)")

node["func"] = func

with open(ORCH_FILE, "w", encoding="utf-8") as f:
    json.dump(nodes, f, ensure_ascii=False, indent=4)

print("Done!")
