var config = global.get("fve_config") || {};
var plan = global.get("fve_plan") || {};
// FIX: Read planned mode from plan object (immutable, set by planner only)
// Previously read from fve_current_mode which was overwritten by override logic
var planMode = (plan && plan.currentMode) ? plan.currentMode : "normal";
var manualMod = config.manual_mod || "auto";

var currentMode = planMode;
if (manualMod !== "auto") {
    currentMode = manualMod;
}

// DIAGNOSTIKA: loguj manuální mód
if (manualMod !== "auto") {
    node.warn("KP MANUAL: config.manual_mod=" + manualMod + " planMode=" + planMode + " → currentMode=" + currentMode);
}

var wasEnabled = flow.get("automatizace_was_enabled") || false;
if (config.automatizace_enabled === false) {
    if (wasEnabled) {
        // Právě vypnuta automatizace → přejdi do NORMAL (safe state) JEDNOU
        flow.set("automatizace_was_enabled", false);
        flow.set("auto_off_normal_sent", false);  // reset flag pro příští cyklus
        global.set("fve_current_mode", "normal");
        msg.currentMode = "normal";
        msg.autoNabijeniAktivni = false;
        msg.cerpadloTopi = global.get("cerpadlo_topi") || false;
        msg.saunaAktivni = global.get("sauna_aktivni") || false;
        node.status({fill:"yellow", shape:"dot", text:"AUTO OFF → NORMAL mód (reset Victronu)"});
        return msg;  // POŠLI jednou do NORMAL módu
    }
    var normalSent = flow.get("auto_off_normal_sent") || false;
    if (!normalSent) {
        // Automatizace zůstává vypnuta, ale ještě jsme neposlali NORMAL → pošli jednou
        flow.set("auto_off_normal_sent", true);
        global.set("fve_current_mode", "normal");
        msg.currentMode = "normal";
        msg.autoNabijeniAktivni = false;
        msg.cerpadloTopi = global.get("cerpadlo_topi") || false;
        msg.saunaAktivni = global.get("sauna_aktivni") || false;
        node.status({fill:"grey", shape:"ring", text:"Automatizace vypnuta (NORMAL reset)"});
        return msg;
    }
    node.status({fill:"grey", shape:"ring", text:"Automatizace vypnuta"});
    return null;
}
flow.set("automatizace_was_enabled", true);
flow.set("auto_off_normal_sent", false);  // reset při zapnutí

var autoNabijeni = global.get("auto_nabijeni_aktivni") || false;

// Grid Lost ochrana
var gridLostState = global.get("homeassistant.homeAssistant.states['sensor.grid_lost_ciselny']") || {};
var gridLost = parseInt(gridLostState.state || "0") >= 2;
var cerpadloTopi = global.get("cerpadlo_topi") || false;
var saunaAktivni = global.get("sauna_aktivni") || false;

// FIX: Removed override normal->setrit when heat pump/car active.
// Root cause of battery charging in Normal mode:
//   Override switched to Setrit which set max_discharge_power=0 and
//   scheduled_soc=currentSoc, causing solar->battery and grid->consumption.
// The planner already assigns correct modes. Individual modes (e.g. Nabijet)
// already adjust power_set_point for high-priority consumers.

// Update display mode
// Grid Lost: přepnout na šetřit (žádné nabíjení ze sítě, baterie se nevybíjí)
if (gridLost && currentMode === "nabijet_ze_site") {
    currentMode = "setrit";
    node.status({fill:"red", shape:"dot", text:"GRID LOST → Šetřit (blokace nabíjení)"});
}
global.set("fve_current_mode", currentMode);

// v18.2: Blokace text pro dashboard
var blokaceItems = [];
if (gridLost) blokaceItems.push("GRID LOST");
if (cerpadloTopi) blokaceItems.push("topení");
if (autoNabijeni) blokaceItems.push("auto");
if (saunaAktivni) blokaceItems.push("sauna");
var blokaceText = blokaceItems.length > 0 ? "ANO - " + blokaceItems.join(", ") : "NE";

// Update blokaceText in global fve_plan for real-time file updates
var currentPlan = global.get("fve_plan") || {};
if (!currentPlan.status) currentPlan.status = {};
currentPlan.status.blokaceText = blokaceText;
global.set("fve_plan", currentPlan);

msg.blokaceText = blokaceText;
msg.autoNabijeniAktivni = autoNabijeni;
msg.cerpadloTopi = cerpadloTopi;
msg.gridLost = gridLost;
msg.saunaAktivni = saunaAktivni;
msg.config = config;
msg.plan = plan;

var modeSource = manualMod !== "auto" ? "(manualni)" : "(auto)";
var infoText = "";
if (gridLost) infoText += " | ⚡GRID LOST";
if (cerpadloTopi) infoText += " | Cerpadlo topi";
if (saunaAktivni) infoText += " | Sauna";
if (autoNabijeni) infoText += " | Auto nabiji";
node.status({fill: manualMod !== "auto" ? "blue" : "green", shape:"dot", text: "Mod: " + currentMode + " " + modeSource + infoText});

// v2.1: Přepnout z nabíjení na šetřit jakmile SOC dosáhne cíle
if (currentMode === "nabijet_ze_site" && manualMod === "auto") {
    var targetSoc = (plan && plan.smartCharging) ? plan.smartCharging.targetSocFromGrid : 0;
    var currentSoc = (global.get("fve_status") || {}).battery_soc || 0;
    if (targetSoc > 0 && currentSoc >= targetSoc) {
        currentMode = "setrit";
        global.set("fve_current_mode", currentMode);
        node.status({fill:"yellow", shape:"dot", text:"SOC " + Math.round(currentSoc) + "% >= cíl " + targetSoc + "% → Šetřit"});
    }
}

// v25.5: Přepnout z prodeje jakmile SOC klesne na cíl (zákon 4.5)
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

return msg;
