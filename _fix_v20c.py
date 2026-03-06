#!/usr/bin/env python3
"""
Fix v20c: Balancování - neplánovat pokud nestihne dobít a příští hodina je zákaz přetoků.
Logika:
  1. Spočítej expected gain v aktuální partial hodině
  2. Pokud SOC + gain < 99% → potřebujeme pokračovat v další hodině
  3. Zkontroluj jestli další hodina má priceSell > 0
  4. Pokud ne → skip balancing, najdi lepší hodinu
"""
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
original = func

# ============================================================
# FIX: Add next-hour negative price check to balancing
# ============================================================
# Current code (after v20b):
old_bal = '''        if (solarOffsets[offset] && simulatedSoc >= balancingMinSoc && priceSell > 0) {
            balancingAssigned = true;
            var balReason = "☀ solár, " + Math.round(daysSinceBal) + " dní, SOC " + Math.round(simulatedSoc) + "% → cíl 100%";'''

new_bal = '''        if (solarOffsets[offset] && simulatedSoc >= balancingMinSoc && priceSell > 0) {
            // v20c: Pokud nestihne dobít v této hodině, zkontroluj další hodiny
            var balGainThisHour = chargeRateKwh * frac * chargeEfficiency / kapacitaBaterie * 100;
            var canCompleteThisHour = (simulatedSoc + balGainThisHour) >= 99;
            if (!canCompleteThisHour) {
                // Potřebujeme pokračovat v další hodině — zkontroluj ceny
                var balBlocked = false;
                for (var nbi = offset + 1; nbi < Math.min(offset + 3, horizont); nbi++) {
                    if (hourPrices[nbi] && hourPrices[nbi].sell <= 0) {
                        balBlocked = true;
                        break;
                    }
                }
                if (balBlocked) {
                    // Skip — další hodina(y) mají zápornou cenu, balancování by nefungovalo
                    // Fall through to normal mode, zkusí se později
                } else {
                    balancingAssigned = true;
                    var balReason = "☀ solár, " + Math.round(daysSinceBal) + " dní, SOC " + Math.round(simulatedSoc) + "% → cíl 100%";'''

# We also need the closing part
old_bal_end = '''            return { mode: MODY.BALANCOVANI, reason: balReason };
        }'''

# New: add closing braces for the if/else + the canComplete fast path
new_bal_end = '''            return { mode: MODY.BALANCOVANI, reason: balReason };
                }
            } else {
                // Stihne dobít v této hodině — OK
                balancingAssigned = true;
                var balReason = "☀ solár, " + Math.round(daysSinceBal) + " dní, SOC " + Math.round(simulatedSoc) + "% → cíl 100%";
                return { mode: MODY.BALANCOVANI, reason: balReason };
            }
        }'''

if old_bal in func:
    func = func.replace(old_bal, new_bal)
    print("OK: Added next-hour check to balancing (part 1)")
else:
    print("ERROR: Could not find balancing pattern (part 1)")
    # Debug
    idx = func.find("simulatedSoc >= balancingMinSoc")
    if idx >= 0:
        print("  Found at:", idx, "context:", func[idx-50:idx+200])
    sys.exit(1)

# Now fix the end part — need to be careful, there might be multiple matches
# Find the FIRST occurrence after our new code
if old_bal_end in func:
    # Replace only the first occurrence
    func = func.replace(old_bal_end, new_bal_end, 1)
    print("OK: Added canComplete fast path (part 2)")
else:
    print("ERROR: Could not find balancing end pattern")
    sys.exit(1)

if func == original:
    print("\nNo changes made!")
    sys.exit(1)

node["func"] = func

with open(ORCH_FILE, "w", encoding="utf-8") as f:
    json.dump(nodes, f, ensure_ascii=False, indent=4)

print(f"\nDone! Changes applied.")
