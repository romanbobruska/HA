"""
v25.6: Fix orchestrátor — zákon 4.9.1 + 4.9.2
1. simulateSocChange pro ŠETŘIT: odečítat socDropSetrit (ne return soc)
2. KROK 7c: účtovat pasivní drain Šetřit hodin v projekci
"""
import json

with open('_server_flows.json', encoding='utf-8') as f:
    data = json.load(f)

changes = []

for node in data:
    if node.get('id') != '9e0b46a9dfedea33' or 'func' not in node:
        continue
    
    code = node['func']
    
    # === FIX 1: simulateSocChange pro ŠETŘIT ===
    old1 = '        case MODY.SETRIT:\n            return soc;'
    new1 = '        case MODY.SETRIT:\n            // v25.6: Šetřit má standby spotřebu domu (zákon 4.9.1)\n            return Math.max(minSoc, soc - socDropSetrit * frac);'
    if old1 in code:
        code = code.replace(old1, new1)
        changes.append("FIX1: simulateSocChange ŠETŘIT — odečítat socDropSetrit")
    else:
        print("WARN: nenalezen SETRIT case v simulateSocChange")
    
    # === FIX 2: KROK 7c — pasivní drain ===
    old2 = '// Ořízni nejlevnější discharge hodiny pokud by SOC kleslo pod target\nvar totalDischSoc = dischKeys.length * socDropNormal;\nvar projEndSoc = currentSoc - totalDischSoc;'
    new2 = '''// Ořízni nejlevnější discharge hodiny pokud by SOC kleslo pod target
var totalDischSoc = dischKeys.length * socDropNormal;
// v25.6: Účtovat pasivní drain Šetřit hodin (zákon 4.9.1)
var solarCount = Object.keys(solarOffsets).length;
var chargeCount = Object.keys(chargingOffsets).length + Object.keys(arbitrageChargeOffsets).length;
var setritHours = Math.max(0, horizont - dischKeys.length - solarCount - chargeCount);
var passiveDrainSoc = setritHours * socDropSetrit;
var projEndSoc = currentSoc - totalDischSoc - passiveDrainSoc;'''
    if old2 in code:
        code = code.replace(old2, new2)
        changes.append("FIX2: KROK 7c — pasivní drain Šetřit hodin")
    else:
        print("WARN: nenalezen KROK 7c blok")
    
    # === FIX 2b: Trim loop — aktualizovat passiveDrain při trimování ===
    old2b = '    totalDischSoc -= socDropNormal;\n    projEndSoc = currentSoc - totalDischSoc;'
    new2b = '    totalDischSoc -= socDropNormal;\n    passiveDrainSoc += socDropSetrit;  // oříznutá hodina se stává Šetřit\n    projEndSoc = currentSoc - totalDischSoc - passiveDrainSoc;'
    if old2b in code:
        code = code.replace(old2b, new2b, 1)  # only first occurrence (trim loop)
        changes.append("FIX2b: trim loop — passiveDrain update")
    else:
        print("WARN: nenalezen trim loop projEndSoc")
    
    # === FIX 2c: Fill loop — aktualizovat passiveDrain při doplňování ===
    old2c = '        dischargeOffsets[fillCand[ffi].offset] = true;\n        totalDischSoc += socDropNormal;\n        projEndSoc = currentSoc - totalDischSoc;'
    new2c = '        dischargeOffsets[fillCand[ffi].offset] = true;\n        totalDischSoc += socDropNormal;\n        passiveDrainSoc -= socDropSetrit;  // přidaná hodina přestává být Šetřit\n        projEndSoc = currentSoc - totalDischSoc - passiveDrainSoc;'
    if old2c in code:
        code = code.replace(old2c, new2c, 1)
        changes.append("FIX2c: fill loop — passiveDrain update")
    else:
        print("WARN: nenalezen fill loop projEndSoc")
    
    # === FIX 2d: Fill condition — passiveDrain in check ===
    old2d = '    if (projEndSoc - socDropNormal >= targetEndSoc) {'
    new2d = '    if (projEndSoc - socDropNormal + socDropSetrit >= targetEndSoc) {  // nová discharge hodina nahrazuje Šetřit'
    if old2d in code:
        code = code.replace(old2d, new2d)
        changes.append("FIX2d: fill condition — net effect check")
    else:
        print("WARN: nenalezen fill condition")
    
    node['func'] = code
    break

# Save
with open('_server_flows.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Sync to local
with open('node-red/flows/fve-orchestrator.json', encoding='utf-8') as f:
    local = json.load(f)
for ln in local:
    if ln.get('id') == '9e0b46a9dfedea33':
        for sn in data:
            if sn.get('id') == '9e0b46a9dfedea33':
                ln['func'] = sn['func']
                changes.append("Synced → fve-orchestrator.json")
                break
with open('node-red/flows/fve-orchestrator.json', 'w', encoding='utf-8') as f:
    json.dump(local, f, indent=4, ensure_ascii=False)

# Validate
for fp in ['_server_flows.json', 'node-red/flows/fve-orchestrator.json']:
    json.load(open(fp, encoding='utf-8'))
    print(f"✅ {fp} valid JSON")

print(f"\n=== {len(changes)} změn ===")
for c in changes:
    print(f"  ✅ {c}")
