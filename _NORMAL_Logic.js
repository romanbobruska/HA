var patBlockCharge = global.get("pat_block_charge") || false;
var config = global.get("fve_config") || {};
var status = global.get("fve_status") || {};
var minSoc = config.min_soc || 20;
var currentSoc = status.battery_soc || 50;
var cerpadloTopi = msg.cerpadloTopi || false;
var autoCharging = msg.autoNabijeniAktivni || false;
// v19.4: Read charger state directly — global may be stale after NR restart
var chargerEntity = global.get("homeassistant.homeAssistant.states['sensor.charger_state_garage']") || {};
if (chargerEntity.state === "2") autoCharging = true;
var saunaAktivni = msg.saunaAktivni || false;
var minDischargeBlokaceW = config.min_vybijeni_blokace_w || 1300;

// v19: Aktualni PV vykon pro rozhodovani o blokaci
var pvFveEntity = global.get("homeassistant.homeAssistant.states['sensor.vyroba_fve']") || {};
var currentPvPower = parseFloat(pvFveEntity.state) || 0;
var dynamicDischargeW = Math.max(0, Math.round(minDischargeBlokaceW - currentPvPower));
// v19.3: Proven pattern from ŠETŘIT — solar<=10W → MaxDischargePower=0
// Eliminates ~130W DC bus standby loss. Victron transfer relay handles grid passthrough.
var solarPassthrough = currentPvPower > 10 ? Math.max(50, Math.round(currentPvPower)) : 0;

// v19: Blokace vybijeni: POUZE pri nabijeni ze site, NIBE bez solaru, nebo saune

var nibeFromGrid = cerpadloTopi;  // NIBE topí → vždy blokovat vybíjení baterie
// v19.4: Hard block discharge when car charges and SOC < threshold (battery priority)
var autoSocThreshold = config.nabijeni_auta_min_soc || 95;
// v24.10: blockDischargeHard removed — car charges from grid (not Victron), battery must power house
var blockDischargeHard = false;
var blockDischargeSoft = nibeFromGrid || saunaAktivni;
var blockDischarge = blockDischargeHard || blockDischargeSoft;

msg.victron = {
    power_set_point: 0,
    min_soc: minSoc,
    schedule_soc: 0,
    schedule_charge_duration: 0,
    schedule_charge_day: -7,
    max_discharge_power: (blockDischargeHard || blockDischargeSoft) ? solarPassthrough : -1,
    max_charge_power: (patBlockCharge || blockDischargeSoft) ? 0 : -1,
    feedin_on: true,
    max_feed_in_power: 7600,
    prevent_feedback: 0
};
msg.mode = "normal";
msg.blockDischarge = blockDischarge;
msg.maxDischargePower = blockDischarge ? 0 : -1;
msg.maxChargePower = blockDischarge ? 0 : -1;

var consumers = [];
if (cerpadloTopi) consumers.push("Topeni");
if (autoCharging) consumers.push("Auto");
if (saunaAktivni) consumers.push("Sauna");
var consText = consumers.length > 0 ? " | " + consumers.join("+") : "";
var dischText = blockDischarge ? " | BLOK_DISCH:0W" : "";
node.status({fill: blockDischarge ? "yellow" : "green", shape:"dot", text:"NORMAL | SOC:" + currentSoc + "%" + consText + dischText});

global.set("energy_arbiter", {
    mode: "normal",
    battery_charging: false,
    battery_charge_rate_w: 0,
    power_set_point: 0,
    consumers_active: consumers,
    max_discharge_allowed: !blockDischarge,
    timestamp: Date.now()
});

return msg;
