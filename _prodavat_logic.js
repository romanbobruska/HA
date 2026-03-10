var patBlockCharge = global.get("pat_block_charge") || false;
var saunaAktivni = msg.saunaAktivni || false;
var config = global.get("fve_config") || {};
var status = global.get("fve_status") || {};

if (msg.autoNabijeniAktivni) {
    node.status({fill:"yellow", shape:"ring", text:"Skip prodej - auto se nabíjí"});
    return null;
}

var currentSoc = status.battery_soc || 50;
var minSoc = config.min_soc || 20;
var maxFeedIn = config.max_feed_in_w || 7600;

// SOC check přesunut za effectiveMinSoc

// v25.5: Cílové SOC z plánu (zákon 4.5) — plán definuje floor předem
var nightReserveKwh = config.night_reserve_kwh || 10;
var kapacita = config.kapacita_baterie_kwh || 28;
var nightReservePct = (nightReserveKwh / kapacita) * 100;
var effectiveMinSoc = msg.sellTargetSoc || Math.max(minSoc, Math.round(minSoc + nightReservePct));

if (currentSoc <= effectiveMinSoc) {
    node.status({fill:"green", shape:"dot", text:"SOC " + currentSoc + "% ≤ cíl " + effectiveMinSoc + "% → prodej hotov"});
    return null;
}

// v19.4: PSP must be NEGATIVE to actively sell from battery to grid
// PSP=0 only feeds excess solar — at night with solar=0 nothing gets exported
var sellPowerW = maxFeedIn;  // max export power = max feed-in power
msg.victron = {
    power_set_point: -sellPowerW,
    min_soc: effectiveMinSoc,
    schedule_soc: 0,
    schedule_charge_duration: 0,
    schedule_charge_day: -7,
    max_discharge_power: -1,
    max_charge_power: patBlockCharge ? 0 : -1,
    feedin_on: true,
    max_feed_in_power: maxFeedIn,
    prevent_feedback: 0
};
msg.mode = "prodavat";
msg.feedInExcess = true;
node.status({fill:"red", shape:"dot", text:"PRODÁVAT -" + sellPowerW + "W | SOC: " + currentSoc + "% (min:" + effectiveMinSoc + "%)"});

var consumers = [];
if (msg.cerpadloTopi) consumers.push("Topeni");
if (msg.saunaAktivni) consumers.push("Sauna");
if (msg.autoNabijeniAktivni) consumers.push("Auto");

global.set("energy_arbiter", {
    mode: "prodavat",
    battery_charging: false,
    reserved_for_battery_w: 0,
    max_discharge_allowed: true,
    consumers_active: consumers,
    timestamp: Date.now()
});

return msg;
