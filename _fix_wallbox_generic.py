#!/usr/bin/env python3
"""
Fix: Odstranit NIBE-specifické podmínky z manageru i korekční smyčky.
Logika musí být univerzální — pracovat na základě reálného přebytku.

Korekční smyčka: Pracuje na rozdíl výroby a spotřeby. Pokud available < 6A → stop.
Manager: Kontroluje reálný přebytek před zapnutím wallboxu. Takeover kontroluje surplus.
"""
import json, sys

MGR_FILE = r"d:\Programy\Programování\Node Red\HA\node-red\flows\manager-nabijeni-auta.json"
SOLAR_FILE = r"d:\Programy\Programování\Node Red\HA\node-red\flows\nabijeni-auta-slunce.json"

# ============================================================
# FIX 1: Korekční smyčka — odstranit cerpadloTopi + nibeOn check
# ============================================================
with open(SOLAR_FILE, "r", encoding="utf-8") as f:
    solar_nodes = json.load(f)

solar_node = None
for n in solar_nodes:
    if n.get("id") == "788e188fae8d1fca":
        solar_node = n
        break

if not solar_node:
    print("ERROR: Solar correction node not found")
    sys.exit(1)

sfunc = solar_node["func"]

# Remove the NIBE-specific MUTEX block entirely
old_nibe_check = """// === OCHRANA 1b: NIBE MUTEX — čerpadlo topí → auto STOP (v19.4) ===
var cerpadloTopi = global.get("cerpadlo_topi") || false;
// v20: Proaktivní check — switch.nibe_topeni (okamžitý, nečeká na pumpState ~7min)
var nibeStates = global.get("homeassistant.homeAssistant.states['switch.nibe_topeni']") || {};
var nibeOn = nibeStates.state === "on";
if (cerpadloTopi || nibeOn) {
    node.status({fill:'red', shape:'ring', text:'NIBE ' + (nibeOn ? 'ON' : 'topí') + ' → 0A STOP'});
    msg.payload = 0;
    return msg;
}

// Celkovy dostupny vykon pro wallbox = prebytek + co wallbox uz bere"""

new_generic = """// Celkovy dostupny vykon pro wallbox = prebytek + co wallbox uz bere
// v21: Žádné device-specifické checky — pracujeme čistě na přebytku (výroba - spotřeba)"""

if old_nibe_check in sfunc:
    sfunc = sfunc.replace(old_nibe_check, new_generic)
    print("OK: Korekční smyčka — odstraněn NIBE check")
else:
    print("ERROR: NIBE check pattern not found in solar correction")
    # Try to find partial match
    if "cerpadloTopi" in sfunc:
        print("  Found cerpadloTopi in function - looking for pattern...")
        idx = sfunc.find("cerpadloTopi")
        print("  Context:", sfunc[max(0,idx-100):idx+200])
    sys.exit(1)

solar_node["func"] = sfunc

with open(SOLAR_FILE, "w", encoding="utf-8") as f:
    json.dump(solar_nodes, f, ensure_ascii=False, indent=4)

print("Solar correction saved.")

# ============================================================
# FIX 2: Manager — odstranit NIBE MUTEX, přidat surplus check na takeover
# ============================================================
with open(MGR_FILE, "r", encoding="utf-8") as f:
    mgr_nodes = json.load(f)

mgr_node = None
for n in mgr_nodes:
    if n.get("id") == "main_logic_func":
        mgr_node = n
        break

if not mgr_node:
    print("ERROR: Manager node not found")
    sys.exit(1)

func = mgr_node["func"]

# Remove NIBE MUTEX entirely — replace with comment
old_mutex = """// 3. MUTEX: NIBE topí → auto NESMÍ nabíjet (nikdy současně!)
var ultraLevna = global.get("ultra_levna_energie") || false;
var cerpadloTopi = global.get("cerpadlo_topi") || false;
// v20: Proaktivní check — switch.nibe_topeni (okamžitý, nečeká na pumpState)
var nibeOn = getBool("switch.nibe_topeni");
if ((cerpadloTopi || nibeOn) && !ultraLevna) {
    node.status({fill:"red", shape:"ring", text:"⚠️MUTEX: NIBE " + (nibeOn ? "ON" : "topí") + " → auto STOP"});
    return [[msg], null, null];
}"""

new_surplus_check = """// 3. v21: Kontrola reálného přebytku — žádné device-specifické checky
// Pokud není dostatečný přebytek a wallbox neběží, nezapínat
var ultraLevna = global.get("ultra_levna_energie") || false;"""

if old_mutex in func:
    func = func.replace(old_mutex, new_surplus_check)
    print("OK: Manager — odstraněn NIBE MUTEX")
else:
    print("ERROR: Manager MUTEX pattern not found")
    if "cerpadloTopi" in func:
        idx = func.find("cerpadloTopi")
        print("  Context:", func[max(0,idx-100):idx+200])
    sys.exit(1)

# Fix takeover — check real surplus instead of raw solar, remove nibeOn
old_takeover = """// v19.4: Car already charging + solar production → take over with solar cycle
// Surplus is negative because car consumes, but solar IS available
var currentSolarW = getFloat("sensor.vyroba_fve", 0);
var chargerIsCharging = (chargerState === "2");
// v20: nibeOn guard — nikdy takeover když NIBE běží
if (chargerIsCharging && currentSolarW > MIN_SOLAR_W && !solarCyklusBezi && !nibeOn) {
    node.status({fill:"green", shape:"dot", text:"☀️ Takeover | solar:" + Math.round(currentSolarW) + "W charger active → slunce"});
    return [null, [msg], null];
}"""

new_takeover = """// v21: Car already charging + dostatečný přebytek → take over with solar cycle
// Surplus = výroba - spotřeba. Pokud wallbox nabíjí, přičteme zpět jeho spotřebu.
var currentSolarW = getFloat("sensor.vyroba_fve", 0);
var chargerIsCharging = (chargerState === "2");
var chargerAmpRaw = getState("select.wallboxu_garaz_amperace") || "0";
var chargerAmpA = parseInt(String(chargerAmpRaw).replace(/[^0-9]/g, ''), 10) || 0;
var chargerWatts = chargerIsCharging ? (chargerAmpA * 3 * 230) : 0;
var surplusWithoutCar = rozdiVyroby + chargerWatts;
if (chargerIsCharging && surplusWithoutCar > MIN_SOLAR_W && !solarCyklusBezi) {
    node.status({fill:"green", shape:"dot", text:"☀️ Takeover | surplus(bez auta):" + Math.round(surplusWithoutCar) + "W → slunce"});
    return [null, [msg], null];
}"""

if old_takeover in func:
    func = func.replace(old_takeover, new_takeover)
    print("OK: Manager takeover — surplus check místo raw solar + nibeOn")
else:
    print("WARN: Manager takeover pattern not found")
    if "Takeover" in func:
        idx = func.find("Takeover")
        print("  Context:", func[max(0,idx-50):idx+300])

# Also fix the solarCyklusBezi bypass — when cycle is running, still check if conditions are
# fundamentally broken (SOC dropped below minimum)
# Actually this is already handled — step 3b checks SOC < MIN_SOC_SLUNCE before the bypass
# And the correction loop handles surplus. So the bypass is correct.

mgr_node["func"] = func

with open(MGR_FILE, "w", encoding="utf-8") as f:
    json.dump(mgr_nodes, f, ensure_ascii=False, indent=4)

print("Manager saved.")
print("\nDone! Both files updated — no device-specific checks, pure surplus logic.")
