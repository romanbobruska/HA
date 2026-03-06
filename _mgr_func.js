// Manager nabíjení auta v2.5
// v2.4: Pokud solární cyklus už běží, NEZASTAVOVAT kvůli poklesu přebytku.
// v2.5: Kontrola charger_state přímo - pokud charger hlásí "charged" (3), STOP okamžitě.
//   auto_ma_hlad má 60s delay z HA automatizace - nelze na něj spoléhat pro okamžitý stop.
// Výstupy: [1] stop → grid+solar OFF, [2] nabíjení ze slunce, [3] nabíjení ze sítě
function getState(id) {
    var e = global.get("homeassistant.homeAssistant.states['" + id + "']") || {};
    return e.state;
}
function getBool(id) { return getState(id) === "on"; }
function getFloat(id, def) {
    var v = parseFloat(getState(id));
    return isNaN(v) ? (def || 0) : v;
}

var config = global.get("fve_config") || {};

var autoHlad     = getBool("input_boolean.auto_ma_hlad");
var automatizace = getBool("input_boolean.automatizovat_nabijeni_auta");
var solarniRezim = getBool("input_boolean.solarni_rezim_nabijeni_auta");
var letniRezim   = getBool("input_boolean.letni_rezim");
var solarCyklusBezi = getBool("input_boolean.nastavuj_amperaci_chargeru_solar");

// v2.5: Přímá kontrola charger_state - "2" = Charging, "3" = Charged, jinak = idle
var chargerState = getState("sensor.charger_state_garage") || "0";
var chargerCharged = (chargerState === "3" || chargerState === "4");  // 3=Charged, 4=Error/Done

// v19.5: Solar forecast source z configu (VICTRON / OPEN_METEO)
var solarSource = (config.solar_forecast_source || "VICTRON").toUpperCase();
var entityDnes = (solarSource === "OPEN_METEO") ? "sensor.energy_production_today_3" : "input_number.predpoved_solarni_vyroby_dnes";
var entityZitra = (solarSource === "OPEN_METEO") ? "sensor.energy_production_tomorrow_3" : "input_number.predpoved_solarni_vyroby_zitra";
var vyrobaDnes   = getFloat(entityDnes, 0);
var vyrobaZitra  = getFloat(entityZitra, 0);
var batSoc       = getFloat("sensor.battery_percent", 0);
var rozdiVyroby  = getFloat("sensor.rozdil_vyroby_a_spotreby", 0);

var FORECAST_KWH = config.nabijeni_auta_forecast_kwh || 40;
var MIN_SOC      = config.nabijeni_auta_min_soc      || 95;
var MIN_SOLAR_W  = config.nabijeni_auta_solar_w      || 4000;
var MIN_SOC_SLUNCE = config.nabijeni_auta_min_soc_slunce || 85;

// v22: Clear balancing_solar_car on all non-balancing-solar exits
// Set BEFORE routing to SLUNCE during balancing — correction loop reads this

// 1. Auto nemá hlad → stop (grid+solar OFF)
if (!autoHlad) {
    global.set("balancing_solar_car", false);
    node.status({fill:"grey", shape:"ring", text:"Nemá hlad → stop"});
    return [[msg], null, null];
}

// 1b. v2.5: Charger hlásí "charged" → stop okamžitě (bez čekání na auto_ma_hlad delay)
if (chargerCharged) {
    global.set("balancing_solar_car", false);
    node.status({fill:"grey", shape:"ring", text:"Charger state=" + chargerState + " (nabito) → stop"});
    return [[msg], null, null];
}

// 2. Automatizace vypnuta → stop
if (!automatizace) {
    global.set("balancing_solar_car", false);
    node.status({fill:"grey", shape:"ring", text:"Automatizace OFF → stop"});
    return [[msg], null, null];
}

// 3. MUTEX: NIBE topí → auto NESMÍ nabíjet (nikdy současně!)
var ultraLevna = global.get("ultra_levna_energie") || false;
var cerpadloTopi = global.get("cerpadlo_topi") || false;
if (cerpadloTopi && !ultraLevna) {
    global.set("balancing_solar_car", false);
    node.status({fill:"red", shape:"ring", text:"⚠️MUTEX: NIBE topí → auto STOP"});
    return [[msg], null, null];
}

// 3b. v22: Balancování — řízené nabíjení auta
// Čteme z HA entity (přežije restart NR) i z globalu (nastaví orchestrátor)
var fvePlanAttrs = (global.get("homeassistant.homeAssistant.states['sensor.fve_plan']") || {}).attributes || {};
var balancingActive = fvePlanAttrs.current_mode === "Balancování" || global.get("balancing_active") || false;
if (balancingActive) {
    if (batSoc < 99) {
        // SOC nízký — baterie potřebuje veškerý solár na balancing
        global.set("balancing_solar_car", false);
        node.status({fill:"yellow", shape:"ring", text:"⚡ Balancování (SOC:" + batSoc + "%) → auto STOP"});
        return [[msg], null, null];
    }
    // SOC ≥ 99% — přebytek využij na auto, ale baterie se NESMÍ vybíjet
    if (solarCyklusBezi) {
        // Solární cyklus už běží → nechat (korekční smyčka řídí ampéráž s reserve)
        global.set("balancing_solar_car", true);
        node.status({fill:"green", shape:"dot", text:"⚡☀ Bal+cyklus | SOC:" + batSoc + "% přebytek:" + Math.round(rozdiVyroby) + "W"});
        return [null, [msg], null];
    }
    if (rozdiVyroby > MIN_SOLAR_W) {
        // Dostatek přebytku → spusť solární nabíjení auta
        global.set("balancing_solar_car", true);
        node.status({fill:"green", shape:"dot", text:"⚡☀ Bal+start | SOC:" + batSoc + "% přebytek:" + Math.round(rozdiVyroby) + "W → slunce"});
        return [null, [msg], null];
    }
    // Žádný přebytek → STOP (při balancingu nenabíjet ze sítě)
    global.set("balancing_solar_car", false);
    node.status({fill:"yellow", shape:"ring", text:"⚡ Bal+SOC≥99 žádný přebytek (" + Math.round(rozdiVyroby) + "W) → STOP"});
    return [[msg], null, null];
}

// Non-balancing paths: clear flag
global.set("balancing_solar_car", false);

// 3c. SOC pod prahem pro solární nabíjení → stop solární cyklus
if (batSoc < MIN_SOC_SLUNCE) {
    node.status({fill:"orange", shape:"ring", text:"SOC " + batSoc + "% < " + MIN_SOC_SLUNCE + "% → stop"});
    return [[msg], null, null];
}

// === v2.4: Pokud solární cyklus UŽ BĚŽÍ, nechat ho běžet ===
// Cyklus si sám řídí ampéráž a zastaví se když target < 6A
// Manager ho nezastavuje kvůli poklesu přebytku
if (solarCyklusBezi) {
    node.status({fill:"green", shape:"dot", text:"☀️ Cyklus běží | SOC:" + batSoc + "% přebytek:" + Math.round(rozdiVyroby) + "W charger:" + chargerState});
    return [null, [msg], null];
}

// v19.4: Car already charging + solar production → take over with solar cycle
// Surplus is negative because car consumes, but solar IS available
var currentSolarW = getFloat("sensor.vyroba_fve", 0);
var chargerIsCharging = (chargerState === "2");
if (chargerIsCharging && currentSolarW > MIN_SOLAR_W && !solarCyklusBezi) {
    node.status({fill:"green", shape:"dot", text:"☀️ Takeover | solar:" + Math.round(currentSolarW) + "W charger active → slunce"});
    return [null, [msg], null];
}

// === v19.12: Balancing solar dump → start solar cycle even without surplus ===
// During balancing + negative sell price, MPPT is curtailed → surplus=0 even though solar IS producing.
// Use raw solar production (sensor.vyroba_fve) instead of surplus to decide.
var balancingSolarDump = global.get("balancing_solar_dump") || false;
if (balancingSolarDump && currentSolarW > MIN_SOLAR_W) {
    node.status({fill:"yellow", shape:"dot", text:"⚡ Solar dump | solar:" + Math.round(currentSolarW) + "W → slunce"});
    return [null, [msg], null];
}

// === Nový start solárního nabíjení ===
var maPrebytek = rozdiVyroby > MIN_SOLAR_W;

// 4. Solární režim ON → slunce (jen pokud je přebytek)
if (solarniRezim && maPrebytek) {
    node.status({fill:"green", shape:"dot", text:"Solar ON | přebytek=" + Math.round(rozdiVyroby) + "W → slunce"});
    return [null, [msg], null];
}

// 5. Letní režim + přebytek → slunce
if (letniRezim && maPrebytek) {
    node.status({fill:"green", shape:"dot", text:"Letní + přebytek=" + Math.round(rozdiVyroby) + "W → slunce"});
    return [null, [msg], null];
}

// 6. Výroba dnes > FORECAST + přebytek → slunce
if (vyrobaDnes > FORECAST_KWH && maPrebytek) {
    node.status({fill:"green", shape:"dot", text:"Dnes " + Math.round(vyrobaDnes) + "kWh + přebytek → slunce"});
    return [null, [msg], null];
}

// 7. Baterie > MIN_SOC + přebytek → slunce
if (batSoc > MIN_SOC && maPrebytek) {
    node.status({fill:"green", shape:"dot", text:"Bat " + batSoc + "% + přebytek=" + Math.round(rozdiVyroby) + "W → slunce"});
    return [null, [msg], null];
}

// 8. Zítra dobrý forecast + přebytek → slunce
if (vyrobaZitra > FORECAST_KWH && maPrebytek) {
    node.status({fill:"green", shape:"dot", text:"Zítra " + Math.round(vyrobaZitra) + "kWh + přebytek → slunce"});
    return [null, [msg], null];
}

// 9. Žádný přebytek nebo forecast nesplněn
if (vyrobaZitra > FORECAST_KWH || vyrobaDnes > FORECAST_KWH) {
    node.status({fill:"orange", shape:"ring", text:"Čeká na přebytek | dnes:" + Math.round(vyrobaDnes) + " zítra:" + Math.round(vyrobaZitra) + " přebytek=" + Math.round(rozdiVyroby) + "W"});
    return [[msg], null, null];
}

// 10. Forecast špatný, přebytek není → nabíjení ze sítě
node.status({fill:"blue", shape:"dot", text:"Síť | dnes:" + Math.round(vyrobaDnes) + " zítra:" + Math.round(vyrobaZitra) + " bat:" + batSoc + "%"});
return [null, null, [msg]];