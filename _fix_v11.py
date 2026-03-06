#!/usr/bin/env python3
"""
Fix v11: Balancování SOC threshold + Solar gain formula fix
1. Balancování jen když simulatedSoc >= balancingMinSoc (~84%)
2. Fix frac² bug v getSolarGainForHour (consumption podhodnocená v partial hours)
3. Minimální podlaha pro hourlyConsumption (daily/24)
"""
import json, re, sys

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
    print(f"ERROR: Node {NODE_ID} not found")
    sys.exit(1)

func = node["func"]
original = func

# ============================================================
# FIX 1: Add balancingAssigned flag and balancingMinSoc before plan loop
# ============================================================
# Find: var plan = [];
# Add before it: var balancingAssigned = false; var balancingMinSoc = ...
old_plan_init = "var plan = [];\nvar simulatedSoc = currentSoc;"
new_plan_init = """// v20: Balancování jen když SOC reálně umožňuje dosáhnout 100%
var balancingAssigned = false;
var balancingMinSoc = 100 - Math.round(chargeRateKwh * chargeEfficiency / kapacitaBaterie * 100); // ~84%

var plan = [];
var simulatedSoc = currentSoc;"""

if old_plan_init in func:
    func = func.replace(old_plan_init, new_plan_init)
    print("OK: Added balancingAssigned + balancingMinSoc")
else:
    print("WARN: Could not find plan init block")

# ============================================================
# FIX 2: Replace PRIORITA 0 + 0.5 in calculateModeForHour
# ============================================================
# Old: PRIORITA 0 with offset===0 exception, then PRIORITA 0.5 with offset===0
old_p0_p05 = """    // PRIORITA 0: Záporná prodejní cena
    // Pokud balancing potřebný → NE zákaz přetoků, ale BALANCOVANI (solární hodiny)
    if (priceSell <= 0 && !(balancingNeeded && offset === 0)) {
        return { mode: MODY.ZAKAZ_PRETOKU, reason: "Záporná prodejní cena" };
    }

    // PRIORITA 0.5: Balancování baterie (1x/30 dní)
    // Pouze aktuální hodina (offset 0) — budoucí hodiny plánují normálně
    // Při záporné ceně + solární hodina: BALANCOVANI s ochranou proti přetokům
    if (balancingNeeded && offset === 0) {
        if (solarOffsets[offset]) {
            var balReason = "☀ solár, " + Math.round(daysSinceBal) + " dní, cíl 100%";
            if (priceSell <= 0) balReason += " (zákaz přetoků)";
            return { mode: MODY.BALANCOVANI, reason: balReason };
        } else if (priceSell <= 0) {
            // Nesolar + záporná cena: ZAKAZ_PRETOKU (grid nabíjení nemá smysl)
            return { mode: MODY.ZAKAZ_PRETOKU, reason: "Záporná cena, čekám na solár pro balancing" };
        } else if (levelBuy <= PRAH_LEVNA) {
            // Levná hodina + kladná cena: grid nabíjení jen bez solaru
            var hasSolarAhead = false;
            for (var soff in solarOffsets) {
                if (parseInt(soff) >= offset) { hasSolarAhead = true; break; }
            }
            if (!hasSolarAhead) {
                return { mode: MODY.BALANCOVANI, reason: "levná Lv" + levelBuy + ", žádný solár, cíl 100%" };
            }
        }
        // Drahé/střední hodiny: normální provoz (fall-through)
    }"""

new_p0_p05 = """    // PRIORITA 0.5: Balancování baterie (1x/30 dní)
    // v20: Aktivní jen v hodině kdy simulatedSoc >= balancingMinSoc (~84%)
    // Zajistí, že balancování se zobrazí až v hodině kdy je reálně dosažitelné 100%
    if (balancingNeeded && !balancingAssigned) {
        if (solarOffsets[offset] && simulatedSoc >= balancingMinSoc) {
            balancingAssigned = true;
            var balReason = "☀ solár, " + Math.round(daysSinceBal) + " dní, SOC " + Math.round(simulatedSoc) + "% → cíl 100%";
            if (priceSell <= 0) balReason += " (zákaz přetoků)";
            return { mode: MODY.BALANCOVANI, reason: balReason };
        }
        if (!solarOffsets[offset] && priceSell > 0 && levelBuy <= PRAH_LEVNA && simulatedSoc >= balancingMinSoc) {
            var hasSolarAhead = false;
            for (var soff in solarOffsets) {
                if (parseInt(soff) > offset) { hasSolarAhead = true; break; }
            }
            if (!hasSolarAhead) {
                balancingAssigned = true;
                return { mode: MODY.BALANCOVANI, reason: "levná Lv" + levelBuy + ", žádný solár, SOC " + Math.round(simulatedSoc) + "% → cíl 100%" };
            }
        }
    }

    // PRIORITA 0: Záporná prodejní cena
    if (priceSell <= 0) {
        return { mode: MODY.ZAKAZ_PRETOKU, reason: "Záporná prodejní cena" };
    }"""

if old_p0_p05 in func:
    func = func.replace(old_p0_p05, new_p0_p05)
    print("OK: Replaced PRIORITA 0 + 0.5 with SOC threshold logic")
else:
    print("ERROR: Could not find PRIORITA 0 + 0.5 block")
    print("Looking for partial match...")
    # Try to find just the start
    if "balancingNeeded && offset === 0" in func:
        print("  Found 'offset === 0' pattern - needs manual fix")
    sys.exit(1)

# ============================================================
# FIX 3: Fix frac² bug in getSolarGainForHour - forecastPerHour path
# ============================================================
old_fph = """        var fpNet = fpKwh - hourlyConsumption * frac;
        return (fpNet * frac * chargeEfficiency / kapacitaBaterie) * 100;"""
new_fph = """        // v20: Fix frac² bug — správně: (výroba - spotřeba) * frac
        var fpNet = (fpKwh - hourlyConsumption) * frac;
        return (fpNet * chargeEfficiency / kapacitaBaterie) * 100;"""

if old_fph in func:
    func = func.replace(old_fph, new_fph)
    print("OK: Fixed frac² bug in forecastPerHour path")
else:
    print("WARN: Could not find forecastPerHour frac² pattern")

# ============================================================
# FIX 4: Fix frac² bug in fallback (remainingSolar) path
# ============================================================
old_fallback = """        var netKwh = hourKwh - hourlyConsumption * frac;
        return (netKwh * frac * chargeEfficiency / kapacitaBaterie) * 100;"""
new_fallback = """        // v20: Fix frac² bug
        var netKwh = (hourKwh - hourlyConsumption) * frac;
        return (netKwh * chargeEfficiency / kapacitaBaterie) * 100;"""

if old_fallback in func:
    func = func.replace(old_fallback, new_fallback)
    print("OK: Fixed frac² bug in remainingSolar fallback path")
else:
    print("WARN: Could not find remainingSolar frac² pattern")

# ============================================================
# FIX 5: Fix frac² bug in forecastZitra fallback path
# ============================================================
old_fz = """        var netKwhForecast = hourKwhForecast - hourlyConsumption * frac;
        return (netKwhForecast * frac * chargeEfficiency / kapacitaBaterie) * 100;"""
new_fz = """        // v20: Fix frac² bug
        var netKwhForecast = (hourKwhForecast - hourlyConsumption) * frac;
        return (netKwhForecast * chargeEfficiency / kapacitaBaterie) * 100;"""

if old_fz in func:
    func = func.replace(old_fz, new_fz)
    print("OK: Fixed frac² bug in forecastZitra fallback path")
else:
    print("WARN: Could not find forecastZitra frac² pattern")

# ============================================================
# FIX 6: Add minimum floor for hourlyConsumption
# ============================================================
old_consumption = """    var hourlyConsumption = (pred && pred.avgConsumptionKwh > 0)
        ? pred.avgConsumptionKwh
        : (config.daily_consumption_kwh || 20) / 24;"""
new_consumption = """    var hourlyConsumption = (pred && pred.avgConsumptionKwh > 0)
        ? pred.avgConsumptionKwh
        : (config.daily_consumption_kwh || 20) / 24;
    // v20: Floor — spotřeba nikdy pod denní průměr/24 (historická data mohou být nízká)
    var minHourlyConsumption = (config.daily_consumption_kwh || 20) / 24;
    if (hourlyConsumption < minHourlyConsumption) hourlyConsumption = minHourlyConsumption;"""

if old_consumption in func:
    func = func.replace(old_consumption, new_consumption)
    print("OK: Added hourlyConsumption floor")
else:
    print("WARN: Could not find hourlyConsumption pattern")

# ============================================================
# Apply changes
# ============================================================
if func == original:
    print("\nNo changes made!")
    sys.exit(1)

node["func"] = func

with open(ORCH_FILE, "w", encoding="utf-8") as f:
    json.dump(nodes, f, ensure_ascii=False, indent=4)

print(f"\nDone! Changes applied to {ORCH_FILE}")
print(f"Function length: {len(original)} → {len(func)} chars")
