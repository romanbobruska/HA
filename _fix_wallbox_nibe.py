#!/usr/bin/env python3
"""
URGENT FIX: Wallbox stále nabíjí když NIBE běží.
Root cause: cerpadlo_topi závisí na pumpState ("Vytápění") — NIBE potřebuje ~7 min po zapnutí.
Během tohoto okna cerpadlo_topi=false → manager spustí wallbox.

Fix 1: Manager - přidat check na switch.nibe_topeni (proaktivní, okamžitý)
Fix 2: Korekční smyčka - přidat check na switch.nibe_topeni
Fix 3: Manager takeover - přidat nibeOn guard
"""
import json, sys

MGR_FILE = r"d:\Programy\Programování\Node Red\HA\node-red\flows\manager-nabijeni-auta.json"
SOLAR_FILE = r"d:\Programy\Programování\Node Red\HA\node-red\flows\nabijeni-auta-slunce.json"

# ============================================================
# FIX 1: Manager - přidat nibeOn check
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

# Add nibeOn check right after cerpadloTopi MUTEX
old_mutex = """// 3. MUTEX: NIBE topí → auto NESMÍ nabíjet (nikdy současně!)
var ultraLevna = global.get("ultra_levna_energie") || false;
var cerpadloTopi = global.get("cerpadlo_topi") || false;
if (cerpadloTopi && !ultraLevna) {
    node.status({fill:"red", shape:"ring", text:"⚠️MUTEX: NIBE topí → auto STOP"});
    return [[msg], null, null];
}"""

new_mutex = """// 3. MUTEX: NIBE topí → auto NESMÍ nabíjet (nikdy současně!)
var ultraLevna = global.get("ultra_levna_energie") || false;
var cerpadloTopi = global.get("cerpadlo_topi") || false;
// v20: Proaktivní check — switch.nibe_topeni (okamžitý, nečeká na pumpState)
var nibeOn = getBool("switch.nibe_topeni");
if ((cerpadloTopi || nibeOn) && !ultraLevna) {
    node.status({fill:"red", shape:"ring", text:"⚠️MUTEX: NIBE " + (nibeOn ? "ON" : "topí") + " → auto STOP"});
    return [[msg], null, null];
}"""

if old_mutex in func:
    func = func.replace(old_mutex, new_mutex)
    print("OK: Manager MUTEX - added nibeOn check")
else:
    print("ERROR: Manager MUTEX pattern not found")
    sys.exit(1)

# Add nibeOn guard to takeover logic (line 82-89)
old_takeover = """// v19.4: Car already charging + solar production → take over with solar cycle
// Surplus is negative because car consumes, but solar IS available
var currentSolarW = getFloat("sensor.vyroba_fve", 0);
var chargerIsCharging = (chargerState === "2");
if (chargerIsCharging && currentSolarW > MIN_SOLAR_W && !solarCyklusBezi) {
    node.status({fill:"green", shape:"dot", text:"☀️ Takeover | solar:" + Math.round(currentSolarW) + "W charger active → slunce"});
    return [null, [msg], null];
}"""

new_takeover = """// v19.4: Car already charging + solar production → take over with solar cycle
// Surplus is negative because car consumes, but solar IS available
var currentSolarW = getFloat("sensor.vyroba_fve", 0);
var chargerIsCharging = (chargerState === "2");
// v20: nibeOn guard — nikdy takeover když NIBE běží
if (chargerIsCharging && currentSolarW > MIN_SOLAR_W && !solarCyklusBezi && !nibeOn) {
    node.status({fill:"green", shape:"dot", text:"☀️ Takeover | solar:" + Math.round(currentSolarW) + "W charger active → slunce"});
    return [null, [msg], null];
}"""

if old_takeover in func:
    func = func.replace(old_takeover, new_takeover)
    print("OK: Manager takeover - added nibeOn guard")
else:
    print("WARN: Manager takeover pattern not found")

mgr_node["func"] = func

with open(MGR_FILE, "w", encoding="utf-8") as f:
    json.dump(mgr_nodes, f, ensure_ascii=False, indent=4)

print("Manager saved.")

# ============================================================
# FIX 2: Korekční smyčka - přidat nibeOn check
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

# Add nibeOn check right after cerpadloTopi check
old_cerpadlo = """// === OCHRANA 1b: NIBE MUTEX — čerpadlo topí → auto STOP (v19.4) ===
var cerpadloTopi = global.get("cerpadlo_topi") || false;
if (cerpadloTopi) {
    node.status({fill:'red', shape:'ring', text:'NIBE topí → 0A STOP'});
    msg.payload = 0;
    return msg;
}"""

new_cerpadlo = """// === OCHRANA 1b: NIBE MUTEX — čerpadlo topí → auto STOP (v19.4) ===
var cerpadloTopi = global.get("cerpadlo_topi") || false;
// v20: Proaktivní check — switch.nibe_topeni (okamžitý, nečeká na pumpState ~7min)
var nibeStates = global.get("homeassistant.homeAssistant.states['switch.nibe_topeni']") || {};
var nibeOn = nibeStates.state === "on";
if (cerpadloTopi || nibeOn) {
    node.status({fill:'red', shape:'ring', text:'NIBE ' + (nibeOn ? 'ON' : 'topí') + ' → 0A STOP'});
    msg.payload = 0;
    return msg;
}"""

if old_cerpadlo in sfunc:
    sfunc = sfunc.replace(old_cerpadlo, new_cerpadlo)
    print("OK: Solar correction - added nibeOn check")
else:
    print("ERROR: Solar correction pattern not found")
    sys.exit(1)

solar_node["func"] = sfunc

with open(SOLAR_FILE, "w", encoding="utf-8") as f:
    json.dump(solar_nodes, f, ensure_ascii=False, indent=4)

print("Solar correction saved.")
print("\nDone! Both files updated.")
