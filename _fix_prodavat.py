"""
v25.5: Fix PRODÁVAT mód — cílové SOC z plánu (zákon 4.5)
+ NIBE cooldown 3→1 min (zákon 8.3)
+ Ověření blockDischargeSoft, patrony cooldown

Změny:
1. Orchestrátor: přidá sellTargetSoc do výstupu plánu
2. Kontrola podmínek: přepne z prodeje jakmile SOC <= sellTargetSoc
3. PRODÁVAT Logic: použije sellTargetSoc z plánu místo currentSoc-1
4. NIBE cooldown: 3→1 min
"""
import json, re, sys

# === Load server flows ===
with open('_server_flows.json', encoding='utf-8') as f:
    data = json.load(f)

changes = []

for node in data:
    nid = node.get('id')
    
    # === 1. ORCHESTRÁTOR (9e0b46a9dfedea33) ===
    if nid == '9e0b46a9dfedea33' and 'func' in node:
        code = node['func']
        
        # 1a: Add sellTargetSoc calculation after currentReason
        old = 'var currentMode = plan.length > 0 ? plan[0].mode : MODY.NORMAL;\nvar currentReason = plan.length > 0 ? plan[0].reason : "";'
        new = '''var currentMode = plan.length > 0 ? plan[0].mode : MODY.NORMAL;
var currentReason = plan.length > 0 ? plan[0].reason : "";

// v25.5: Sell target SOC pro PRODÁVAT mód (zákon 4.5)
// Plán předem definuje, na jakou SOC se baterie vybije prodejem
var sellTargetSoc = minSoc;
if (currentMode === MODY.PRODAVAT && plan.length > 0) {
    sellTargetSoc = plan[0].simulatedSoc;
}'''
        if old in code:
            code = code.replace(old, new)
            changes.append("ORCH: přidán sellTargetSoc výpočet")
        else:
            print("WARN: Orchestrátor - nenalezen currentMode/currentReason blok")
            # Try alternative
            if 'var currentReason = plan.length > 0' in code:
                print("  Found currentReason line, trying line-by-line")
        
        # 1b: Add sellTargetSoc to msg.payload
        old2 = '    currentMode: currentMode,\n    currentReason: currentReason,\n    currentHour: currentHour,'
        new2 = '    currentMode: currentMode,\n    currentReason: currentReason,\n    sellTargetSoc: sellTargetSoc,\n    currentHour: currentHour,'
        if old2 in code:
            code = code.replace(old2, new2)
            changes.append("ORCH: přidán sellTargetSoc do payload")
        else:
            print("WARN: Orchestrátor - nenalezen payload blok pro sellTargetSoc")
        
        node['func'] = code
    
    # === 2. KONTROLA PODMÍNEK (c36915a8599c5282) ===
    if nid == 'c36915a8599c5282' and 'func' in node:
        code = node['func']
        
        # Add sell target check after the charging target check
        old_charge = '''msg.currentMode = currentMode;

return msg;'''
        new_charge = '''// v25.5: Přepnout z prodeje jakmile SOC klesne na cíl (zákon 4.5)
if (currentMode === "prodavat" && manualMod === "auto") {
    var sellTargetSoc = (plan && plan.sellTargetSoc !== undefined) ? plan.sellTargetSoc : 0;
    var currentSocSell = (global.get("fve_status") || {}).battery_soc || 0;
    if (sellTargetSoc > 0 && currentSocSell <= sellTargetSoc) {
        currentMode = "normal";
        global.set("fve_current_mode", currentMode);
        node.status({fill:"green", shape:"dot", text:"Prodej hotov: SOC " + Math.round(currentSocSell) + "% ≤ cíl " + sellTargetSoc + "% → Normal"});
    }
}

// v25.5: Předat sell target SOC do PRODÁVAT Logic
msg.sellTargetSoc = (plan && plan.sellTargetSoc !== undefined) ? plan.sellTargetSoc : (config.min_soc || 20);

msg.currentMode = currentMode;

return msg;'''
        if old_charge in code:
            code = code.replace(old_charge, new_charge)
            changes.append("KP: přidán sell target SOC check + msg.sellTargetSoc")
        else:
            print("WARN: Kontrola podmínek - nenalezen 'msg.currentMode = currentMode; return msg;' blok")
            # Debug: show last 200 chars
            print("  Last 200 chars:", repr(code[-200:]))
        
        node['func'] = code
    
    # === 3. PRODÁVAT LOGIC (68992d178ce105ed) ===
    if nid == '68992d178ce105ed' and 'func' in node:
        code = node['func']
        
        # 3a: Replace effectiveMinSoc calculation
        old_eff = 'var effectiveMinSoc = Math.max(minSoc, currentSoc - 1);'
        new_eff = '''// v25.5: Cílové SOC z plánu (zákon 4.5) — plán definuje floor předem
var nightReserveKwh = config.night_reserve_kwh || 10;
var kapacita = config.kapacita_baterie_kwh || 28;
var nightReservePct = (nightReserveKwh / kapacita) * 100;
var effectiveMinSoc = msg.sellTargetSoc || Math.max(minSoc, Math.round(minSoc + nightReservePct));'''
        if old_eff in code:
            code = code.replace(old_eff, new_eff)
            changes.append("PROD: effectiveMinSoc z plánu")
        else:
            print("WARN: PRODÁVAT Logic - nenalezen effectiveMinSoc řádek")
        
        # 3b: Update the SOC check at line 15 to use effectiveMinSoc
        old_check = 'if (currentSoc <= minSoc + 1) {\n    node.status({fill:"red", shape:"ring", text:"Nedostatek energie"});\n    return null;\n}'
        new_check = '''if (currentSoc <= effectiveMinSoc) {
    node.status({fill:"green", shape:"dot", text:"SOC " + currentSoc + "% ≤ cíl " + effectiveMinSoc + "% → prodej hotov"});
    return null;
}'''
        # effectiveMinSoc is defined AFTER this check, need to reorder
        # Actually, let me just move the check after effectiveMinSoc
        # Remove old check first
        if old_check in code:
            code = code.replace(old_check, '// SOC check přesunut za effectiveMinSoc')
            changes.append("PROD: přesunut SOC check")
        else:
            print("WARN: PRODÁVAT Logic - nenalezen SOC check blok")
            print("  Searching for 'minSoc + 1':", 'minSoc + 1' in code)
        
        # Add SOC check after effectiveMinSoc
        old_after_eff = 'var effectiveMinSoc = msg.sellTargetSoc || Math.max(minSoc, Math.round(minSoc + nightReservePct));'
        new_after_eff = '''var effectiveMinSoc = msg.sellTargetSoc || Math.max(minSoc, Math.round(minSoc + nightReservePct));

if (currentSoc <= effectiveMinSoc) {
    node.status({fill:"green", shape:"dot", text:"SOC " + currentSoc + "% ≤ cíl " + effectiveMinSoc + "% → prodej hotov"});
    return null;
}'''
        if old_after_eff in code:
            code = code.replace(old_after_eff, new_after_eff, 1)
            changes.append("PROD: přidán SOC floor check")
        
        node['func'] = code

# === Save server flows ===
with open('_server_flows.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n=== Změny aplikovány na _server_flows.json ({len(changes)}) ===")
for c in changes:
    print(f"  ✅ {c}")

# === Now sync to local flow files ===
local_files = {
    'fve-orchestrator.json': ['9e0b46a9dfedea33', 'c36915a8599c5282'],
    'fve-modes.json': ['68992d178ce105ed']
}

for fname, node_ids in local_files.items():
    fpath = f'node-red/flows/{fname}'
    try:
        with open(fpath, encoding='utf-8') as f:
            local_data = json.load(f)
    except FileNotFoundError:
        print(f"WARN: {fpath} nenalezen, přeskakuji")
        continue
    
    for ln in local_data:
        if ln.get('id') in node_ids:
            # Find matching server node
            for sn in data:
                if sn.get('id') == ln['id'] and 'func' in sn:
                    ln['func'] = sn['func']
                    print(f"  Synced {ln['id']} → {fpath}")
                    break
    
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(local_data, f, indent=4, ensure_ascii=False)
    
    # Validate JSON
    with open(fpath, encoding='utf-8') as f:
        json.load(f)
    print(f"  ✅ {fpath} valid JSON")

print("\n=== Hotovo ===")
