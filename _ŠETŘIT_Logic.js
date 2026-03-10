// === ŠETŘIT mód ===
// Baterie se NEVYBÍJÍ - max_discharge_power=0
// min_soc zůstává na hodnotě nastavené uživatelem
var patBlockCharge = global.get("pat_block_charge") || false;
var config = global.get("fve_config") || {};
var status = global.get("fve_status") || {};
var currentSoc = status.battery_soc || 50;
var minSoc = config.min_soc || 20;

// Přebytky solaru stále jdou do sítě (feed-in ON)
// Dynamic: MaxDischargePower = aktuální solar (DC bus passthrough)
var pvEntity = global.get("homeassistant.homeAssistant.states['sensor.vyroba_fve']") || {};
var rawSolar = Math.round(parseFloat(pvEntity.state) || 0);
// v19.3: Když solar=0 (noc), MaxDischargePower=0 blokuje DC bus standby loss
// Victron transfer relay zajistí grid passthrough i s MaxDischargePower=0
var currentSolar = rawSolar > 10 ? Math.max(50, rawSolar) : 0;

// v19.3: Grid bias kompenzuje inverter standby (~130W) aby baterie nevybijela
var gridBias = config.setrit_grid_bias_w || 150;
msg.victron = {
    power_set_point:           gridBias,
    min_soc:                   minSoc,
    schedule_soc:              0,
    schedule_charge_duration:  0,
    schedule_charge_day:       -7,
    max_discharge_power:       currentSolar,
    max_charge_power:          patBlockCharge ? 0 : -1,
    feedin_on:                 true,
    max_feed_in_power:         config.max_feed_in_w || 7600,
    prevent_feedback:          0
};
msg.mode = "setrit";
msg.blockDischarge = true;

node.status({fill:"yellow", shape:"dot", text:"SETRIT | SOC:" + currentSoc + "% | minSOC:" + minSoc + "% | PSP:" + gridBias + "W | max_disch:" + currentSolar});

global.set("energy_arbiter", {
    mode: "setrit",
    battery_charging: false,
    battery_charge_rate_w: 0,
    power_set_point: 0,
    consumers_active: [],
    max_discharge_allowed: false,
    timestamp: Date.now()
});

return msg;
