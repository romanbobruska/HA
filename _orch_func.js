// FVE Smart Plan v19.11 - cenová arbitráž + PRODÁVAT mód
// v17.0 Opravy:
//   1. targetSocFromGrid: nabíjet JEN pokud currentSoc nestačí na drahé hodiny před solarem
//      - Starý projectedEndSoc byl špatně (počítal drain i v Šetřit kde SOC zůstává)
//      - Nový: realDrain = POUZE drahé hodiny * socDropNormal
//   2. solar_start/end_hour z HA entit (sensor.sun_next_rising/setting)
//   3. Maintenance charge: 20 dní, pouze v zimě (říjen-březen)
// Pravidla:
//   - Solární nabíjení má VŽDY přednost před nabíjením ze sítě
//   - Nabíjet ze sítě POUZE pokud baterie nestačí do solaru
//   - Baterie by měla být často blízko minSoc před solárním nabíjením
//   - NORMAL = vybíjení baterie (drahé + střední hodiny dle kapacity)
//   - ŠETŘIT = baterie zamčená (SOC se nemění)

var data = msg.planData;
var config = data.config || {};
var status = data.status || {};
var forecast = data.forecast || {};

var prices = data.prices || global.get("fve_prices_forecast") || [];

var MODY = {
    NORMAL: "normal",
    SETRIT: "setrit",
    NABIJET_ZE_SITE: "nabijet_ze_site",
    PRODAVAT: "prodavat",
    ZAKAZ_PRETOKU: "zakaz_pretoku",
    SOLAR_CHARGING: "solar_charging",
    BALANCOVANI: "Balancování"
};

// === PARAMETRY Z CONFIGU ===
var kapacitaBaterie = config.kapacita_baterie_kwh || 28;
var minSoc = config.min_soc || 20;
var maxDailySoc = config.max_daily_soc || 80;
var amortizace = config.amortizace_baterie_czk_kwh || 1.5;
var chargeEfficiency = config.charge_efficiency || 0.90;
var dischargeEfficiency = config.discharge_efficiency || 0.90;
var roundTripEfficiency = chargeEfficiency * dischargeEfficiency;
var chargeRateKwh = config.charge_rate_kwh || 5;
var socDropNormal = config.soc_drop_normal_pct || 5;
var dailyConsumptionKwh = config.daily_consumption_kwh || 20;
var PRAH_LEVNA = config.prah_levna_energie || 4;
var PRAH_DRAHA = config.prah_draha_energie || 12;
var horizont = config.plan_horizon_hours || 12;
var maxGridW = config.max_spotreba_sit_w || 22000;
var maxFeedInW = config.max_feed_in_w || 7600;
var prodejZBaterieEnabled = config.prodej_z_baterie_enabled === true;
var blokaceVybijeni = config.blokace_vybijeni === true;
var manualMod = config.manual_mod || "auto";
var letniRezim = config.letni_rezim === true;
var socDropSetrit = config.soc_drop_setrit_pct || 1;
var minDischargeBlokaceW = config.min_vybijeni_blokace_w || 1300;
// v18.8: SOC drop při blokaci (1.3kW povinná spotřeba domu)
var socDropBlokace = (minDischargeBlokaceW / 1000 / kapacitaBaterie) * 100;

// v19: Cenová arbitráž
var MIN_ARBITRAGE_PROFIT = config.min_arbitrage_profit_czk || 2;
var MIN_SELL_PROFIT = config.min_sell_profit_czk || 2;
var NIGHT_RESERVE_KWH = config.night_reserve_kwh || 10;
var nightReservePct = (NIGHT_RESERVE_KWH / kapacitaBaterie) * 100;

// v17: Dynamické solární hodiny z HA (předané z Sbírka dat)
var solarStartHour = data.solarStartHour || config.solar_start_hour || 9;
var solarEndHour = data.solarEndHour || config.solar_end_hour || 17;

// === AKTUÁLNÍ STAV ===
var currentSoc = status.battery_soc || 50;

// v18.2: Blokace info pro dashboard
var cerpadloTopi = global.get("cerpadlo_topi") || false;

// v19.12: Dynamický odhad spotřeby NIBE v solárních hodinách
var haStatesNibe = global.get("homeassistant.homeAssistant.states") || {};
var indoorTemp = parseFloat((haStatesNibe["sensor.hp2551ae_pro_v2_1_0_indoor_temperature"] || {}).state) || 22;
var targetTemp = parseFloat((haStatesNibe["input_number.nastavena_teplota_v_dome"] || {}).state) || 23;
var tempGapPlan = targetTemp - indoorTemp;
// NIBE topí ~2kW průměrně. Pokud dům potřebuje topení nebo je blízko cíle (±0.5°C), NIBE poběží v solárních hodinách.
var nibeEstKwh = (tempGapPlan > -0.5 && targetTemp > 18) ? (config.nibe_est_consumption_kwh || 2.0) : 0;
var autoNabijeni = global.get("auto_nabijeni_aktivni") || false;
var saunaAktivni = global.get("sauna_aktivni") || false;
var blokaceItems = [];
if (cerpadloTopi) blokaceItems.push("topení");
if (autoNabijeni) blokaceItems.push("auto");
if (saunaAktivni) blokaceItems.push("sauna");
var blokaceText = blokaceItems.length > 0 ? "ANO - " + blokaceItems.join(", ") : "NE";
var forecastZitra = forecast.zitra || 0;
var forecastPerHour = data.forecastPerHour || {};
// v19.5: Merge tomorrow's per-hour forecast for hours that fall into "next day" in the plan
var fphTomorrow = data.forecastPerHourTomorrow || {};
var hoursToMidnight = (24 - currentHour) % 24;
if (hoursToMidnight === 0) hoursToMidnight = 24;
for (var mergeH = 0; mergeH < 24; mergeH++) {
    // Hours after midnight in the plan → use tomorrow's data
    var offsetForHour = (mergeH - currentHour + 24) % 24;
    if (offsetForHour >= hoursToMidnight && fphTomorrow[mergeH] !== undefined) {
        forecastPerHour[mergeH] = fphTomorrow[mergeH];
    }
}
var remainingSolarKwh = data.zbyvajiciSolar || 0;

// v18.13: Sanity check - max denní výroba dle měsíce pro 17kWp, az190, sklon45, 50N
// Hodnoty odpovídají realistickému maximu pro daný měsíc
// v18.20: Realistická maxima pro 17kWp, az190, sklon45, 50N (Horoušany)
var monthMaxSolarKwh = [15, 35, 60, 90, 110, 120, 115, 105, 75, 50, 20, 12];
var currentMonth = new Date().getMonth(); // 0-11
var maxSolarToday = monthMaxSolarKwh[currentMonth];
if (remainingSolarKwh > maxSolarToday) {
    remainingSolarKwh = maxSolarToday;
}
// v18.22: Cap forecastZitra stejně jako remainingSolar
// VRM API může vracet nerealisticky vysoké hodnoty (56 kWh v únoru)
// Zítřek: pokud jsme posledních 3 dny v měsíci, použít max(aktuální, příští měsíc)
var dayOfMonth = new Date().getDate();
var daysInMonth = new Date(new Date().getFullYear(), currentMonth + 1, 0).getDate();
var maxSolarForTomorrow = maxSolarToday;
if (dayOfMonth >= daysInMonth - 2) {
    var nextMonthMax = monthMaxSolarKwh[(currentMonth + 1) % 12];
    maxSolarForTomorrow = Math.max(maxSolarToday, nextMonthMax);
}
if (forecastZitra > maxSolarForTomorrow) {
    forecastZitra = maxSolarForTomorrow;
}

// v18: Predikce výroby a spotřeby per hodinu z historie
var consumptionPredictions = data.consumptionPredictions || [];

// v18: Pomocná funkce - získej predikci pro danou hodinu
function getPredictionForHour(hour) {
    for (var pi = 0; pi < consumptionPredictions.length; pi++) {
        if (consumptionPredictions[pi].hour === hour) {
            return consumptionPredictions[pi];
        }
    }
    return null;
}

// v18: Výpočet solárního přírůstku per hodinu
// v18.22: Měsíční solární křivky pro Horoušany (50.105N, 14.741E)
// Azimut 190° (JZ), sklon 45°, 17 kWp
// Každý měsíc má vlastní distribuci výroby per hodina (normalizováno na 1.0)
// Zima: krátký den, výroba soustředěna kolem poledne
// Léto: dlouhý den, výroba rozprostřena, dřívější start
var monthlySolarCurves = {
    // Leden (index 0): východ ~7:50, západ ~16:20, krátký den
    0:  {8: 0.02, 9: 0.08, 10: 0.14, 11: 0.18, 12: 0.20, 13: 0.18, 14: 0.12, 15: 0.06, 16: 0.02},
    // Únor: východ ~6:50, západ ~17:15
    1:  {7: 0.01, 8: 0.04, 9: 0.09, 10: 0.14, 11: 0.17, 12: 0.19, 13: 0.17, 14: 0.11, 15: 0.06, 16: 0.02},
    // Březen: východ ~6:00, západ ~18:00
    2:  {6: 0.01, 7: 0.02, 8: 0.06, 9: 0.10, 10: 0.13, 11: 0.15, 12: 0.16, 13: 0.14, 14: 0.11, 15: 0.07, 16: 0.04, 17: 0.01},
    // Duben: východ ~5:20, západ ~19:30
    3:  {5: 0.01, 6: 0.02, 7: 0.04, 8: 0.07, 9: 0.10, 10: 0.12, 11: 0.14, 12: 0.14, 13: 0.13, 14: 0.10, 15: 0.07, 16: 0.04, 17: 0.02},
    // Květen: východ ~4:30, západ ~20:20
    4:  {5: 0.01, 6: 0.03, 7: 0.05, 8: 0.08, 9: 0.10, 10: 0.12, 11: 0.13, 12: 0.13, 13: 0.12, 14: 0.10, 15: 0.07, 16: 0.04, 17: 0.02},
    // Červen: východ ~4:10, západ ~20:50 (nejdelší den)
    5:  {5: 0.02, 6: 0.03, 7: 0.05, 8: 0.08, 9: 0.10, 10: 0.12, 11: 0.13, 12: 0.13, 13: 0.12, 14: 0.10, 15: 0.07, 16: 0.04, 17: 0.01},
    // Červenec: podobný červnu
    6:  {5: 0.02, 6: 0.03, 7: 0.05, 8: 0.08, 9: 0.10, 10: 0.12, 11: 0.13, 12: 0.13, 13: 0.12, 14: 0.10, 15: 0.07, 16: 0.04, 17: 0.01},
    // Srpen: východ ~5:00, západ ~20:00
    7:  {5: 0.01, 6: 0.02, 7: 0.05, 8: 0.08, 9: 0.10, 10: 0.12, 11: 0.14, 12: 0.14, 13: 0.12, 14: 0.10, 15: 0.07, 16: 0.04, 17: 0.01},
    // Září: východ ~5:50, západ ~18:50
    8:  {6: 0.01, 7: 0.03, 8: 0.07, 9: 0.10, 10: 0.13, 11: 0.15, 12: 0.15, 13: 0.14, 14: 0.11, 15: 0.07, 16: 0.03, 17: 0.01},
    // Říjen: východ ~6:40, západ ~17:30
    9:  {7: 0.02, 8: 0.05, 9: 0.10, 10: 0.14, 11: 0.16, 12: 0.17, 13: 0.16, 14: 0.11, 15: 0.06, 16: 0.03},
    // Listopad: východ ~7:10, západ ~16:20
    10: {8: 0.03, 9: 0.08, 10: 0.14, 11: 0.18, 12: 0.20, 13: 0.18, 14: 0.12, 15: 0.06, 16: 0.01},
    // Prosinec: východ ~7:50, západ ~16:00 (nejkratší den)
    11: {8: 0.02, 9: 0.07, 10: 0.14, 11: 0.19, 12: 0.22, 13: 0.19, 14: 0.12, 15: 0.05}
};
// Vyber křivku pro aktuální měsíc
var solarCurveWeights = monthlySolarCurves[currentMonth] || monthlySolarCurves[5];

// Spočítej celkovou váhu pro aktivní solární hodiny v plánu
var totalCurveWeight = 0;
for (var cwh = solarStartHour; cwh < solarEndHour; cwh++) {
    totalCurveWeight += solarCurveWeights[cwh] || 0;
}
if (totalCurveWeight === 0) totalCurveWeight = 1; // safety

function getSolarCurveShare(hour) {
    // Vrátí podíl hodiny na celkové výrobě (0-1) v rámci aktivních solárních hodin
    var weight = solarCurveWeights[hour] || 0;
    return weight / totalCurveWeight;
}

function getSolarGainForHour(hour, remainingSolar, solarHours, hFraction) {
    var frac = (hFraction !== undefined) ? hFraction : 1.0;
    var curveShare = getSolarCurveShare(hour);

    // v18.6: Historická spotřeba per hodina (přesnější než denní průměr)
    var pred = getPredictionForHour(hour);
    var hourlyConsumption = (pred && pred.avgConsumptionKwh > 0)
        ? pred.avgConsumptionKwh
        : (config.daily_consumption_kwh || 20) / 24;
    // v19.12: Přičíst odhad NIBE spotřeby jen v hodinách s dostatečným solárem
    // NIBE topí jen když solární výroba pokryje domácnost + má přebytek (~3kWh+)
    var isSolarForNibe = hour >= solarStartHour && hour < solarEndHour;
    var solarThisHour = (forecastPerHour[hour] !== undefined) ? forecastPerHour[hour] : 0;
    var nibeBoost = (isSolarForNibe && nibeEstKwh > 0 && solarThisHour > 3.0) ? nibeEstKwh : 0;
    hourlyConsumption += nibeBoost;

    // v19.5: Per-hour forecast má NEJVYŠŠÍ prioritu (reálná data z API)
    // forecastPerHour je sloučený z today + tomorrow (merge v init sekci)
    if (forecastPerHour[hour] !== undefined) {
        var fpKwh = forecastPerHour[hour];
        var fpNet = fpKwh - hourlyConsumption * frac;
        return (fpNet * frac * chargeEfficiency / kapacitaBaterie) * 100;
    }

    if (pred && pred.sampleCount >= 3 && pred.avgSolarKwh > 0) {
        // Historická data: čistý přebytek solaru (výroba - spotřeba)
        var netGain = pred.netSolarGainKwh || 0;
        // v18.5: Sanity check - omezit historický gain křivkou
        if (remainingSolar > 0 && solarHours > 0) {
            var maxFromCurve = remainingSolar * curveShare;
            var maxNetKwh = maxFromCurve - hourlyConsumption;
            if (netGain > maxNetKwh * 2 && maxNetKwh > 0) {
                netGain = maxNetKwh;
            }
        }
        // v18.6: Aplikovat zlomek hodiny
        return (netGain * frac * chargeEfficiency / kapacitaBaterie) * 100;
    }
    // Fallback: rozdělení zbývajícího solaru podle křivky
    if (solarHours > 0 && remainingSolar > 0) {
        var hourKwh = remainingSolar * curveShare;
        // v18.13: Záporný netKwh = spotřeba > výroba, baterie dodá rozdíl
        var netKwh = hourKwh - hourlyConsumption * frac;
        return (netKwh * frac * chargeEfficiency / kapacitaBaterie) * 100;
    }
    // Plán v noci pro zítřek - použít forecast
    if (forecastZitra > 0 && curveShare > 0) {
        var hourKwhForecast = (forecastPerHour[hour] !== undefined) ? forecastPerHour[hour] : forecastZitra * curveShare;
        // v18.13: Záporný = spotřeba > forecast výroba
        var netKwhForecast = hourKwhForecast - hourlyConsumption * frac;
        return (netKwhForecast * frac * chargeEfficiency / kapacitaBaterie) * 100;
    }
    return 0;
}

// v17: Maintenance charge - 20 dní, pouze v zimě (říjen-březen)
var lastFullCharge = global.get("fve_last_full_charge") || null;
if (!lastFullCharge) {
    global.set("fve_last_full_charge", new Date().toISOString());
    lastFullCharge = global.get("fve_last_full_charge");
}
var daysSinceFullCharge = lastFullCharge
    ? Math.floor((Date.now() - new Date(lastFullCharge).getTime()) / (1000 * 60 * 60 * 24))
    : 999;
if (currentSoc >= 99) {
    global.set("fve_last_full_charge", new Date().toISOString());
}

var now = new Date();
var currentHour = now.getHours();
var currentMinute = now.getMinutes();
var firstHourFraction = (60 - currentMinute) / 60; // v18.6: zlomek zbývající první hodiny
var currentMonth = now.getMonth() + 1; // 1-12
var isWinter = (currentMonth >= 10 || currentMonth <= 3); // říjen-březen

// === POMOCNÁ FUNKCE: NAJDI CENOVÝ ZÁZNAM ===
function findPriceEntry(hour, offset) {
    var isNextDay = (currentHour + (offset || 0)) >= 24;
    var preferDay = isNextDay ? "hoursTomorrow" : "hoursToday";
    var otherDay = isNextDay ? "hoursToday" : "hoursTomorrow";
    
    for (var i = 0; i < prices.length; i++) {
        if (prices[i].day === preferDay && prices[i].hour === hour && prices[i].minute === 0) {
            return { entry: prices[i], method: "exact_" + preferDay };
        }
    }
    for (var j = 0; j < prices.length; j++) {
        if (prices[j].day === preferDay && prices[j].hour === hour) {
            return { entry: prices[j], method: "dayHour_" + preferDay };
        }
    }
    for (var k = 0; k < prices.length; k++) {
        if (prices[k].day === otherDay && prices[k].hour === hour && prices[k].minute === 0) {
            return { entry: prices[k], method: "exact_" + otherDay };
        }
    }
    for (var m = 0; m < prices.length; m++) {
        if (prices[m].day === otherDay && prices[m].hour === hour) {
            return { entry: prices[m], method: "dayHour_" + otherDay };
        }
    }
    for (var n = 0; n < prices.length; n++) {
        if (prices[n].hour === hour) {
            return { entry: prices[n], method: "any_" + (prices[n].day || "noday") };
        }
    }
    return { entry: null, method: "none" };
}

// === KROK 1: CENOVÁ MAPA HORIZONTU ===
var hourPrices = [];
var debugMatches = [];
for (var hi = 0; hi < horizont; hi++) {
    var hh = (currentHour + hi) % 24;
    var found = findPriceEntry(hh, hi);
    var entry = found.entry;
    hourPrices.push({
        offset: hi,
        hour: hh,
        buy: entry ? (parseFloat(entry.priceCZKhourBuy) || 0) : 0,
        sell: entry ? (parseFloat(entry.priceCZKhourProd) || 0) : 0,
        levelBuy: entry ? (entry.levelCheapestHourBuy || 5) : 5,
        levelSell: entry ? (entry.levelMostExpensiveHourProd || 5) : 5
    });
    debugMatches.push({
        offset: hi, hour: hh, method: found.method,
        day: entry ? entry.day : null, min: entry ? entry.minute : null,
        buy: entry ? entry.priceCZKhourBuy : null, lvl: entry ? entry.levelCheapestHourBuy : null
    });
}

// === KROK 2: IDENTIFIKUJ SOLÁRNÍ HODINY (potřebuji je dříve pro výpočet nabíjení) ===
var solarOffsets = {};
var solarHoursCount = 0;
for (var sh = 0; sh < horizont; sh++) {
    var shh = (currentHour + sh) % 24;
    if (shh >= solarStartHour && shh < solarEndHour) {
        solarOffsets[sh] = true;
        solarHoursCount++;
    }
}

// === KROK 3: NAJDI DRAHÉ HODINY PŘED SOLAREM ===
// Klíčový výpočet: kolik drahých hodin je PŘED dalším solárním oknem?
// Tyto hodiny MUSÍ pokrýt baterie (vybíjením)
var expensiveBeforeSolar = [];
var firstSolarOffset = horizont;
for (var fso = 0; fso < horizont; fso++) {
    if (solarOffsets[fso]) {
        firstSolarOffset = fso;
        break;
    }
}

for (var eo = 0; eo < hourPrices.length; eo++) {
    var hp = hourPrices[eo];
    var isSolarHour = solarOffsets[eo];
    if (hp.levelBuy >= PRAH_DRAHA && !isSolarHour && eo < firstSolarOffset) {
        expensiveBeforeSolar.push(hp);
    }
}

// Všechny drahé hodiny (pro finanční kalkulaci)
var allExpensiveHours = hourPrices.filter(function(hp) {
    return hp.levelBuy >= PRAH_DRAHA && !solarOffsets[hp.offset];
});
var avgExpensivePrice = 0;
if (allExpensiveHours.length > 0) {
    var sum = 0;
    for (var ei = 0; ei < allExpensiveHours.length; ei++) {
        sum += allExpensiveHours[ei].buy;
    }
    avgExpensivePrice = sum / allExpensiveHours.length;
}

// === KROK 4: KOLIK ENERGIE POTŘEBUJI ZE SÍTĚ? ===
// v17: PŘESNÝ výpočet - nabíjet JEN pokud currentSoc nestačí
//
// Logika:
// 1. Spočítej reálný drain do solaru = drahé hodiny před solarem × socDropNormal
// 2. SOC po vybíjení = currentSoc - drain
// 3. Pokud SOC po vybíjení >= minSoc + safety → NENABÍJET (solár dobije)
// 4. Pokud SOC po vybíjení < minSoc + safety → nabít JEN deficit
//
// Příklad z problemy.txt:
//   currentSoc=42%, drahé hodiny před solarem=3 (06,07,08), drain=15%
//   SOC po vybíjení = 42% - 15% = 27%
//   minSoc + safety = 20% + 5% = 25%
//   27% > 25% → NENABÍJET ✓

var drainBeforeSolarPct = expensiveBeforeSolar.length * socDropNormal;
var socAfterDrain = currentSoc - drainBeforeSolarPct;

// Safety margin závisí na solární předpovědi
var safetyMargin = 5;
if (forecastZitra < dailyConsumptionKwh * 0.3) {
    safetyMargin = 10; // špatná předpověď
} else if (forecastZitra < dailyConsumptionKwh * 0.5) {
    safetyMargin = 7; // střední předpověď
}

var minRequiredSoc = minSoc + safetyMargin;
var gridChargeNeeded = 0;
var targetSocFromGrid = currentSoc; // default: nenabíjet

// Nabíjet ze sítě JEN pokud SOC po vybíjení drahých hodin nestačí
if (socAfterDrain < minRequiredSoc) {
    // Deficit: kolik % chybí?
    var deficitPct = minRequiredSoc - socAfterDrain;
    // Nabít tak, aby po vybíjení drahých hodin zůstalo minRequiredSoc
    targetSocFromGrid = Math.min(maxDailySoc, currentSoc + Math.ceil(deficitPct));
    gridChargeNeeded = Math.max(0, ((targetSocFromGrid - currentSoc) / 100) * kapacitaBaterie / chargeEfficiency);
}

// Pokud target je moc blízko currentSoc, nenabíjet
if (targetSocFromGrid <= currentSoc + 3) {
    gridChargeNeeded = 0;
    targetSocFromGrid = currentSoc;
}

// v17: Maintenance charge - 20 dní, pouze v zimě
var maintenanceCharge = false;
if (isWinter && daysSinceFullCharge >= 20 && targetSocFromGrid < 100) {
    targetSocFromGrid = 100;
    gridChargeNeeded = ((100 - currentSoc) / 100) * kapacitaBaterie / chargeEfficiency;
    maintenanceCharge = true;
}

// === KROK 4b: FINANČNÍ SMYSLUPLNOST NABÍJENÍ ===
var viableChargingHours = [];
if (gridChargeNeeded > 0) {
    for (var vi = 0; vi < hourPrices.length; vi++) {
        var chp = hourPrices[vi];
        if (chp.levelBuy > PRAH_LEVNA) continue;
        if (!solarOffsets[chp.offset]) { // nenabíjet v solárních hodinách ze sítě
            var effectiveCost = chp.buy / roundTripEfficiency + amortizace;
            if (effectiveCost < avgExpensivePrice || avgExpensivePrice === 0 || maintenanceCharge) {
                viableChargingHours.push(chp);
            }
        }
    }
    viableChargingHours.sort(function(a, b) { return a.buy - b.buy; });
}

var hoursNeeded = Math.ceil(gridChargeNeeded / chargeRateKwh);

// === KROK 5: PŘIŘAĎ NABÍJECÍ HODINY ===
var chargingOffsets = {};
var assignedHours = 0;

if (viableChargingHours.length > 0) {
    for (var ci = 0; ci < viableChargingHours.length && assignedHours < hoursNeeded; ci++) {
        chargingOffsets[viableChargingHours[ci].offset] = true;
        assignedHours++;
    }
}

// Fallback: pokud nestačí viable hours, hledej další levné
if (assignedHours < hoursNeeded) {
    var cheapestAvail = hourPrices.slice().filter(function(hp) {
        return !chargingOffsets[hp.offset] && hp.levelBuy <= PRAH_LEVNA && !solarOffsets[hp.offset];
    });
    cheapestAvail.sort(function(a, b) { return a.buy - b.buy; });
    for (var ca = 0; ca < cheapestAvail.length && assignedHours < hoursNeeded; ca++) {
        chargingOffsets[cheapestAvail[ca].offset] = true;
        assignedHours++;
    }
}

// Maintenance: pokud stále nestačí, použij i dražší hodiny
if (maintenanceCharge && assignedHours < hoursNeeded) {
    var remaining = hourPrices.filter(function(hp) {
        return !chargingOffsets[hp.offset] && hp.levelBuy < PRAH_DRAHA && !solarOffsets[hp.offset];
    });
    remaining.sort(function(a, b) { return a.buy - b.buy; });
    for (var ri = 0; ri < remaining.length && assignedHours < hoursNeeded; ri++) {
        chargingOffsets[remaining[ri].offset] = true;
        assignedHours++;
    }
}

// Upravit target pokud se nepodařilo přiřadit dost hodin
if (assignedHours < hoursNeeded && !maintenanceCharge) {
    var actualChargeKwh = assignedHours * chargeRateKwh * chargeEfficiency;
    targetSocFromGrid = Math.min(targetSocFromGrid,
        currentSoc + Math.round(actualChargeKwh / kapacitaBaterie * 100));
    gridChargeNeeded = actualChargeKwh;
}

// Odstraň solární hodiny z chargingOffsets (pro jistotu)
for (var cso in chargingOffsets) {
    if (solarOffsets[cso]) {
        delete chargingOffsets[cso];
    }
}

// === KROK 6: SOLÁRNÍ SOC GAIN ===
var solarSocGainTotal = 0;
if (solarHoursCount > 0 && remainingSolarKwh > 0) {
    solarSocGainTotal = (remainingSolarKwh * chargeEfficiency / kapacitaBaterie) * 100;
}

// === KROK 7: DYNAMICKÝ PRÁH VYBÍJENÍ ===
// v19.9: Pre-calculate low-gain solar hours (gain <= 0 = solar < consumption)
// These hours should compete for discharge budget alongside regular hours
var lowGainSolarOffsets = {};
for (var lgs in solarOffsets) {
    var lgsH = (currentHour + parseInt(lgs)) % 24;
    var lgsGain = getSolarGainForHour(lgsH, remainingSolarKwh, solarHoursCount, 1.0);
    if (lgsGain <= 0) {
        lowGainSolarOffsets[lgs] = true;
    }
}

var dischargeCandidate = [];
for (var dc = 0; dc < hourPrices.length; dc++) {
    if ((!solarOffsets[dc] || lowGainSolarOffsets[dc]) && !chargingOffsets[dc]) {
        dischargeCandidate.push({
            offset: dc,
            hour: hourPrices[dc].hour,
            levelBuy: hourPrices[dc].levelBuy,
            buy: hourPrices[dc].buy
        });
    }
}

// v19.7: Sort by absolute price (not per-day level) to fix midnight boundary
dischargeCandidate.sort(function(a, b) {
    return b.buy - a.buy;
});

var availableBatteryKwh = Math.max(0, (currentSoc - minSoc) / 100 * kapacitaBaterie * dischargeEfficiency);
var energyBudgetKwh = availableBatteryKwh;

var dischargeOffsets = {};
var effectiveThreshold = PRAH_DRAHA;
var usedEnergyKwh = 0;
var dischargeDebug = [];

for (var di = 0; di < dischargeCandidate.length; di++) {
    var cand = dischargeCandidate[di];
    var energyForThisHour = socDropNormal / 100 * kapacitaBaterie;
    
    if (usedEnergyKwh + energyForThisHour <= energyBudgetKwh) {
        dischargeOffsets[cand.offset] = true;
        usedEnergyKwh += energyForThisHour;
        effectiveThreshold = Math.min(effectiveThreshold, cand.levelBuy);
        dischargeDebug.push({
            offset: cand.offset, hour: cand.hour, level: cand.levelBuy,
            price: cand.buy, action: "NORMAL",
            usedKwh: Math.round(usedEnergyKwh * 10) / 10,
            budgetKwh: Math.round(energyBudgetKwh * 10) / 10
        });
    } else if (cand.levelBuy >= PRAH_DRAHA && usedEnergyKwh < energyBudgetKwh) {
        // v18.17: Budget nestačí na celou hodinu, ale levelBuy je drahý
        // Přidáme hodinu - baterie se vybije co může (až na minSoc)
        dischargeOffsets[cand.offset] = true;
        usedEnergyKwh = energyBudgetKwh; // vyčerpáme zbytek budgetu
        effectiveThreshold = Math.min(effectiveThreshold, cand.levelBuy);
        dischargeDebug.push({
            offset: cand.offset, hour: cand.hour, level: cand.levelBuy,
            price: cand.buy, action: "NORMAL (partial, budget limit)",
            usedKwh: Math.round(usedEnergyKwh * 10) / 10,
            budgetKwh: Math.round(energyBudgetKwh * 10) / 10
        });
    } else {
        dischargeDebug.push({
            offset: cand.offset, hour: cand.hour, level: cand.levelBuy,
            price: cand.buy, action: "SETRIT (budget exceeded)",
            usedKwh: Math.round(usedEnergyKwh * 10) / 10,
            budgetKwh: Math.round(energyBudgetKwh * 10) / 10
        });
    }
}

// v18.18b: Flag - existují drahé hodiny bez budgetu na vybíjení?
var budgetExhausted = false;
for (var be = 0; be < dischargeCandidate.length; be++) {
    if (!dischargeOffsets[dischargeCandidate[be].offset] && dischargeCandidate[be].levelBuy >= PRAH_DRAHA) {
        budgetExhausted = true;
        break;
    }
}

// === KROK 7b: CENOVÁ ARBITRÁŽ ===
// Hledáme ziskové páry: levná hodina (nabít) → drahá hodina (využít/prodat)
// Profit = drahá_nákup - (levná_nákup / roundTripEff + amortizace)
// Nabíjíme z gridu jen pokud solar nepokryje

var arbitrageChargeOffsets = {};
var arbitrageSellOffsets = {};
var arbitrageDebug = [];

// Extended price window (beyond 12h horizon) — využíváme ceny zítřka z DB
var extPrices = [];
for (var epi = 0; epi < 36; epi++) {
    var epH = (currentHour + epi) % 24;
    var epResult = findPriceEntry(epH, epi);
    if (epResult) {
        var epEntry = epResult.entry;
        extPrices.push({
            offset: epi,
            hour: epH,
            buy: epEntry.priceCZKhourBuy || 0,
            sell: epEntry.priceCZKhourProd || 0,
            levelBuy: epEntry.levelCheapestHourBuy || 99,
            isSolar: (epH >= solarStartHour && epH < solarEndHour)
        });
    }
}

// Peak SOC po solárním nabíjení (odhad)
var peakSocFromSolar = Math.min(100, currentSoc + solarSocGainTotal);

// Odhad SOC v budoucí hodině — krok po kroku včetně zítřejšího solaru
function estimateSocAtExpHour(expHour, expOffset) {
    var estSoc = currentSoc;
    for (var step = 1; step <= expOffset; step++) {
        var h = (currentHour + step) % 24;
        var isNextDay = (currentHour + step) >= 24;
        if (h >= solarStartHour && h < solarEndHour) {
            // Solární hodina — odhad čistého zisku z křivky
            var curveShare = getSolarCurveShare(h);
            var solarKwh;
            if (isNextDay && forecastPerHour[h] !== undefined) {
                solarKwh = forecastPerHour[h];
            } else if (isNextDay) {
                solarKwh = forecastZitra * curveShare;
            } else {
                solarKwh = remainingSolarKwh * curveShare;
            }
            var consumption = dailyConsumptionKwh / 24;
            var netKwh = solarKwh - consumption;
            estSoc += (netKwh * chargeEfficiency / kapacitaBaterie) * 100;
        } else {
            estSoc -= socDropNormal;
        }
    }
    return Math.min(100, Math.max(minSoc, estSoc));
}

// Drahé hodiny v rozšířeném okně (od nejdražší)
var extExpensive = extPrices.filter(function(h) { return h.buy > 0; })
    .sort(function(a, b) { return b.buy - a.buy; });

// Levné hodiny v 12h plánu (od nejlevnější), jen ne-solární a ne-charging
var cheapInPlan = hourPrices.slice()
    .filter(function(h) {
        return !solarOffsets[h.offset] && !chargingOffsets[h.offset];
    })
    .sort(function(a, b) { return a.buy - b.buy; });

var matchedExp = {};
var totalArbChargeKwh = 0;
var maxArbChargeKwh = Math.max(0, ((100 - nightReservePct) - currentSoc) / 100 * kapacitaBaterie);

for (var arbi = 0; arbi < cheapInPlan.length && totalArbChargeKwh < maxArbChargeKwh; arbi++) {
    var cheapH = cheapInPlan[arbi];
    var effCost = cheapH.buy / roundTripEfficiency + amortizace;

    for (var expi = 0; expi < extExpensive.length; expi++) {
        var expH = extExpensive[expi];
        if (matchedExp[expH.offset]) continue;
        if (expH.offset <= cheapH.offset) continue;

        var rawSpread = expH.buy - cheapH.buy;
        var arbProfit = expH.buy - effCost;
        if (rawSpread < MIN_ARBITRAGE_PROFIT || arbProfit <= 0) continue;

        // Solar coverage: pokud solar naplní baterii dost, nechargovat z gridu
        var socAtExp = estimateSocAtExpHour(expH.hour, expH.offset);
        if (socAtExp > minSoc + nightReservePct) {
            arbitrageDebug.push({
                cheapHour: cheapH.hour, expHour: expH.hour,
                rawSpread: Math.round(rawSpread * 10) / 10,
                estSoc: Math.round(socAtExp),
                action: "SKIP_SOLAR"
            });
            matchedExp[expH.offset] = true;
            continue;
        }

        // Profitable + solar nepokryje → CHARGE
        arbitrageChargeOffsets[cheapH.offset] = {
            targetHour: expH.hour,
            rawSpread: Math.round(rawSpread * 100) / 100,
            effProfit: Math.round(arbProfit * 100) / 100
        };
        matchedExp[expH.offset] = true;
        totalArbChargeKwh += chargeRateKwh;

        arbitrageDebug.push({
            cheapHour: cheapH.hour, cheapPrice: cheapH.buy,
            expHour: expH.hour, expPrice: expH.buy,
            rawSpread: Math.round(rawSpread * 100) / 100,
            effProfit: Math.round(arbProfit * 100) / 100,
            action: "CHARGE"
        });

        // Sell check: raw spread = sellPrice - buyPrice
        if (expH.offset < horizont && prodejZBaterieEnabled) {
            var sellSpread = expH.sell - cheapH.buy;
            var sellEffProfit = expH.sell * dischargeEfficiency - effCost;
            if (sellSpread >= MIN_SELL_PROFIT && sellEffProfit > 0) {
                arbitrageSellOffsets[expH.offset] = {
                    rawSpread: Math.round(sellSpread * 100) / 100,
                    effProfit: Math.round(sellEffProfit * 100) / 100
                };
            }
        }
        break;
    }
}

// Update targetSocFromGrid pro SOC simulaci (arbitráž + deficit)
// targetSocFromGrid update moved after KROK 7c

// === KROK 7c: OPTIMALIZACE — target end SOC 25% ===
// 1) Sloučí discharge z KROK 7 + P5b hodiny (levelBuy >= PRAH_DRAHA)
// 2) Ořízne nejlevnější discharge hodiny pokud by SOC kleslo pod target
// 3) Ořízne arb nabíjení na minimum potřebné
// 4) Oříznuté hodiny jdou do arbSaveOffsets → P5b je nepřepíše
var arbSaveOffsets = {};
if (Object.keys(arbitrageChargeOffsets).length > 0) {
    var targetEndSoc = minSoc + 5;

    // Odstraň arb charge offsety z discharge (nemohou být obojí)
    for (var ari in arbitrageChargeOffsets) {
        delete dischargeOffsets[ari];
    }

    // Přidej P5b hodiny (levelBuy >= PRAH_DRAHA) které nejsou v discharge ani arb
    for (var p5i = 0; p5i < hourPrices.length; p5i++) {
        var p5h = hourPrices[p5i];
        if (p5h.levelBuy >= PRAH_DRAHA && !dischargeOffsets[p5h.offset] &&
            !solarOffsets[p5h.offset] && !chargingOffsets[p5h.offset] &&
            !arbitrageChargeOffsets[p5h.offset]) {
            dischargeOffsets[p5h.offset] = true;
        }
    }

    // Seřaď všechny discharge hodiny od nejlevnější (pro trimming)
    var dischKeys = Object.keys(dischargeOffsets).map(Number);
    dischKeys.sort(function(a, b) {
        var prA = 0, prB = 0;
        for (var pp = 0; pp < hourPrices.length; pp++) {
            if (hourPrices[pp].offset === a) prA = hourPrices[pp].buy;
            if (hourPrices[pp].offset === b) prB = hourPrices[pp].buy;
        }
        return prA - prB;
    });

    // Ořízni nejlevnější discharge hodiny pokud by SOC kleslo pod target
    var totalDischSoc = dischKeys.length * socDropNormal;
    var projEndSoc = currentSoc - totalDischSoc;
    while (projEndSoc < targetEndSoc && dischKeys.length > 0) {
        var trimOff = dischKeys.shift();
        delete dischargeOffsets[trimOff];
        arbSaveOffsets[trimOff] = true;
        totalDischSoc -= socDropNormal;
        projEndSoc = currentSoc - totalDischSoc;
    }

    // Doplň discharge hodiny pokud je SOC stále nad target (nejdražší první)
    // Kandidáti: ne-solar, ne-charge, ne-arb, ne-discharge, ne v arbSaveOffsets
    var fillCand = [];
    for (var fci = 0; fci < hourPrices.length; fci++) {
        var fch = hourPrices[fci];
        if (!dischargeOffsets[fch.offset] && !solarOffsets[fch.offset] &&
            !chargingOffsets[fch.offset] && !arbitrageChargeOffsets[fch.offset] &&
            !arbSaveOffsets[fch.offset]) {
            fillCand.push(fch);
        }
    }
    fillCand.sort(function(a, b) { return b.buy - a.buy; });
    for (var ffi = 0; ffi < fillCand.length; ffi++) {
        if (projEndSoc - socDropNormal >= targetEndSoc) {
            dischargeOffsets[fillCand[ffi].offset] = true;
            totalDischSoc += socDropNormal;
            projEndSoc = currentSoc - totalDischSoc;
        }
    }

    // Potřebný SOC po nabití = target + drain
    var neededChargeKwh = Math.max(0, (targetEndSoc + totalDischSoc - currentSoc) / 100 * kapacitaBaterie / chargeEfficiency);

    // Ořízni arb charge hodiny na minimum (keep cheapest)
    var arbOffsetKeys = Object.keys(arbitrageChargeOffsets).map(Number);
    arbOffsetKeys.sort(function(a, b) {
        var priceA = 0, priceB = 0;
        for (var pp = 0; pp < hourPrices.length; pp++) {
            if (hourPrices[pp].offset === a) priceA = hourPrices[pp].buy;
            if (hourPrices[pp].offset === b) priceB = hourPrices[pp].buy;
        }
        return priceA - priceB;
    });
    var keptChargeKwh = 0;
    var newArbChargeOffsets = {};
    for (var aci = 0; aci < arbOffsetKeys.length; aci++) {
        if (keptChargeKwh < neededChargeKwh) {
            newArbChargeOffsets[arbOffsetKeys[aci]] = arbitrageChargeOffsets[arbOffsetKeys[aci]];
            keptChargeKwh += chargeRateKwh;
        }
    }
    arbitrageChargeOffsets = newArbChargeOffsets;
    totalArbChargeKwh = keptChargeKwh;
    // Oříznuté arb charge hodiny → arbSaveOffsets (P5b je nesmí přepsat na discharge)
    for (var sai = 0; sai < arbOffsetKeys.length; sai++) {
        if (!newArbChargeOffsets[arbOffsetKeys[sai]]) {
            arbSaveOffsets[arbOffsetKeys[sai]] = true;
        }
    }
}

// Update targetSocFromGrid s oříznutým nabíjením
if (Object.keys(arbitrageChargeOffsets).length > 0) {
    var arbTargetSoc = Math.min(100, currentSoc + ((totalArbChargeKwh * chargeEfficiency) / kapacitaBaterie * 100));
    targetSocFromGrid = Math.max(targetSocFromGrid, arbTargetSoc);
}


// === KROK 8: VÝPOČET MÓDU PRO KAŽDOU HODINU ===
function calculateModeForHour(offset, priceData, simulatedSoc, hFraction) {
    var frac = (hFraction !== undefined) ? hFraction : 1.0;
    if (manualMod !== "auto") {
        return { mode: manualMod, reason: "Manuální mód" };
    }

    var priceSell = priceData.sell;
    var levelSell = priceData.levelSell;
    var levelBuy = priceData.levelBuy;

    // === PRE-COMPUTE: Balancing need ===
    var haStates_bal = global.get("homeassistant.homeAssistant.states") || {};
    var lastBalStr_pre = (haStates_bal["input_datetime.last_pylontech_balanced"] || {}).state || "";
    var lastBalMs_pre = 0;
    if (lastBalStr_pre && lastBalStr_pre !== "unknown" && lastBalStr_pre !== "unavailable") {
        lastBalMs_pre = new Date(lastBalStr_pre).getTime();
    }
    var daysSinceBal = lastBalMs_pre > 0 ? (Date.now() - lastBalMs_pre) / (1000 * 60 * 60 * 24) : 999;
    var balancingIntervalDays = config.balancing_interval_days || 30;
    var balancingNeeded = daysSinceBal >= balancingIntervalDays;

    // PRIORITA 0: Záporná prodejní cena
    // Pokud balancing potřebný + solární hodina → BALANCOVANI (ne zákaz přetoků)
    var _balCanAssign = balancingNeeded && balancingHoursUsed < balancingForceStopHours && (offset === 0 ? _balElapsedHours < balancingForceStopHours : true);
    if (priceSell <= 0 && !(_balCanAssign && solarOffsets[offset])) {
        return { mode: MODY.ZAKAZ_PRETOKU, reason: "Záporná prodejní cena" };
    }

    // PRIORITA 0.5: Balancování baterie (1x/30 dní)
    // v23: Přes více hodin — pouze v hodinách s dostatečným solárním výkonem
    var BAL_MIN_SOLAR_KWH = config.balancing_min_solar_kwh || 2;
    if (_balCanAssign) {
        if (solarOffsets[offset]) {
            // v23: Check per-hour solar forecast — skip hours with too little solar
            var balHour = (currentHour + offset) % 24;
            var balSolarKwh = (forecastPerHour[balHour] !== undefined) ? forecastPerHour[balHour] : 0;
            if (balSolarKwh <= 0) {
                // Fallback to curve estimate
                var balCurveShare = getSolarCurveShare(balHour);
                balSolarKwh = (forecastZitra > 0 ? forecastZitra : remainingSolarKwh) * balCurveShare;
            }
            if (balSolarKwh >= BAL_MIN_SOLAR_KWH) {
                balancingHoursUsed++;
                var balReason = "☀ solár " + balSolarKwh.toFixed(1) + "kWh, " + Math.round(daysSinceBal) + " dní, SOC " + Math.round(simulatedSoc) + "% → cíl 100%";
                if (priceSell <= 0) balReason += " (zákaz přetoků)";
                return { mode: MODY.BALANCOVANI, reason: balReason };
            }
            // Solar hour but too little yield — fall through to normal decisions
        } else if (priceSell <= 0) {
            // Nesolar + záporná cena: ZAKAZ_PRETOKU (grid nabíjení nemá smysl)
            return { mode: MODY.ZAKAZ_PRETOKU, reason: "Záporná cena, čekám na solár pro balancing" };
        } else if (levelBuy <= PRAH_LEVNA) {
            // Levná hodina + kladná cena: grid nabíjení jen bez solaru
            var hasSolarAhead = false;
            for (var soff in solarOffsets) {
                if (parseInt(soff) > offset) { hasSolarAhead = true; break; }
            }
            if (!hasSolarAhead) {
                balancingHoursUsed++;
                return { mode: MODY.BALANCOVANI, reason: "levná Lv" + levelBuy + ", žádný solár, SOC " + Math.round(simulatedSoc) + "% → cíl 100%" };
            }
        }
        // Drahé/střední hodiny: normální provoz (fall-through)
    }

    // PRIORITA 1: Nabíjení ze sítě
    if (chargingOffsets[offset] && simulatedSoc < targetSocFromGrid) {
        return {
            mode: MODY.NABIJET_ZE_SITE,
            reason: "Nabíjení na cíl " + Math.round(targetSocFromGrid) + "% (nyní " + Math.round(simulatedSoc) + "%)"
        };
    }

    // PRIORITA 1b: Arbitrážní nabíjení (levná hodina → nabít pro budoucí drahou)
    if (arbitrageChargeOffsets[offset]) {
        var arbInfo = arbitrageChargeOffsets[offset];
        return {
            mode: MODY.NABIJET_ZE_SITE,
            reason: "Arbitráž: nabít na " + Math.round(targetSocFromGrid) + "% pro h" + arbInfo.targetHour + " (úspora " + arbInfo.rawSpread + " CZK/kWh)"
        };
    }

    // PRIORITA 2: Prodej z baterie při výhodné ceně (v19: cenová arbitráž)
    if (prodejZBaterieEnabled && simulatedSoc > minSoc + nightReservePct) {
        var sellRevenue = priceSell * dischargeEfficiency;
        // Cost basis: solar = jen amortizace, grid = avg charge cost + amortizace
        var costBasis = amortizace;
        if (viableChargingHours.length > 0) {
            var sc = 0;
            for (var sci = 0; sci < viableChargingHours.length; sci++) {
                sc += viableChargingHours[sci].buy;
            }
            costBasis = (sc / viableChargingHours.length) / roundTripEfficiency + amortizace;
        }
        var sellProfit = sellRevenue - costBasis;
        if (sellProfit >= MIN_SELL_PROFIT || arbitrageSellOffsets[offset]) {
            // v19.4: Defer sell if >20% better sell price within next 3h
            var deferSell = false;
            if (!arbitrageSellOffsets[offset]) {
                for (var bsa = 1; bsa <= 3; bsa++) {
                    var bsaOff = offset + bsa;
                    if (bsaOff >= horizont) break;
                    var bsaResult = findPriceEntry((currentHour + bsaOff) % 24, bsaOff);
                    if (bsaResult && (bsaResult.entry.priceCZKhourProd || 0) > priceSell * 1.2) {
                        deferSell = true;
                        break;
                    }
                }
            }
            if (!deferSell) {
                // v19.4: Use frac for partial hours — prevents premature sell stop mid-hour
                var dischRateKwh = maxFeedInW / 1000 * frac;
                var socAfterSell = Math.max(minSoc,
                    simulatedSoc - (dischRateKwh / dischargeEfficiency / kapacitaBaterie * 100));
                if (socAfterSell >= minSoc + nightReservePct) {
                    return {
                        mode: MODY.PRODAVAT,
                        reason: "Prodej (zisk " + Math.round(sellProfit * 10) / 10 + " CZK/kWh), SOC " + Math.round(simulatedSoc) + "% → ~" + Math.round(socAfterSell) + "%"
                    };
                }
            }
        }
    }

    // PRIORITA 3: Ochrana baterie - příliš nízký SOC
    if (simulatedSoc <= minSoc) {
        return {
            mode: MODY.SETRIT,
            reason: "Ochrana baterie (SOC " + Math.round(simulatedSoc) + "% ≤ " + minSoc + "%)"
        };
    }

    // PRIORITA 4: Solární hodiny - v18.18: ŠETŘIT při nízkém zisku, NORMAL při vysokém
    if (solarOffsets[offset]) {
        var planHourForSolar = (currentHour + offset) % 24;
        var solarGainPct = getSolarGainForHour(planHourForSolar, remainingSolarKwh, solarHoursCount, frac);
        var solarGainEst = Math.round(solarGainPct * 10) / 10;
        var expectedSocSolar = Math.min(100, simulatedSoc + solarGainEst);

        // v19.9: Low-gain solar hour selected for discharge -> treat as regular discharge hour
        // Solar doesn't cover consumption -> battery should discharge here if budget allows
        if (solarGainEst <= 0 && dischargeOffsets[offset] && simulatedSoc > minSoc) {
            var expectedSocLowSolar = Math.max(minSoc, simulatedSoc + solarGainEst);
            return {
                mode: MODY.NORMAL,
                reason: "Sol\u00e1rn\u00ed (low gain " + solarGainEst + "%), vyb\u00edjen\u00ed SOC " + Math.round(simulatedSoc) + "% \u2192 ~" + Math.round(expectedSocLowSolar) + "%"
            };
        }

        // v18.18: Pokud solární zisk výrazně nabíjí baterii, vždy NORMAL
        if (solarGainEst > socDropNormal) {
            return {
                mode: MODY.NORMAL,
                reason: "Solární hodina, SOC " + Math.round(simulatedSoc) + "% → ~" + Math.round(expectedSocSolar) + "%"
            };
        }

        // Nízký solární zisk - rozhodnutí dle ceny (viz v18.19 výše)

        // v19.8: Drahá solární hodina — NORMAL pokud je dostatek SOC, jinak ŠETŘIT
        if (levelBuy >= PRAH_DRAHA && simulatedSoc > minSoc) {
            // v19.8: Pokud solární zisk je záporný a SOC by kleslo blízko k minSoc, chránit baterii
            if (solarGainEst < 0 && expectedSocSolar <= minSoc + 3) {
                return {
                    mode: MODY.SETRIT,
                    reason: "Solární+drahá ale nízký SOC (Lv" + levelBuy + ", zisk " + solarGainEst + "%), SOC " + Math.round(simulatedSoc) + "%"
                };
            }
            return {
                mode: MODY.NORMAL,
                reason: "Solární+drahá (Lv" + levelBuy + "≥" + PRAH_DRAHA + "), SOC " + Math.round(simulatedSoc) + "% → ~" + Math.round(expectedSocSolar) + "%"
            };
        }

        // Nízký zisk a levná hodina - ŠETŘIT pouze pokud budget nestačí
        if (budgetExhausted) {
            return {
                mode: MODY.SETRIT,
                reason: "Solární (nízký zisk +" + solarGainEst + "%), šetřím na dražší hodiny, SOC " + Math.round(simulatedSoc) + "%"
            };
        }
        // Budget stačí - NORMAL
        return {
            mode: MODY.NORMAL,
            reason: "Solární hodina, SOC " + Math.round(simulatedSoc) + "% → ~" + Math.round(expectedSocSolar) + "%"
        };
    }

    // PRIORITA 5: NORMAL pro hodiny vybrané dynamickým prahem (vybíjení)
    if (dischargeOffsets[offset] && simulatedSoc > minSoc) {
        var expectedSocDischarge = Math.max(minSoc, simulatedSoc - socDropNormal * frac);
        var priceInfo = levelBuy >= PRAH_DRAHA ? "drahá" : (levelBuy <= PRAH_LEVNA ? "levná" : "střední");
        return {
            mode: MODY.NORMAL,
            reason: priceInfo + " (Lv" + levelBuy + "≥eff" + effectiveThreshold + "), vybíjení SOC " + Math.round(simulatedSoc) + "% → ~" + Math.round(expectedSocDischarge) + "%"
        };
    }

    // PRIORITA 5b: v18.19 - Drahé hodiny VŽDY vybíjet (i bez budgetu)
    if (levelBuy >= PRAH_DRAHA && simulatedSoc > minSoc && !arbSaveOffsets[offset]) {
        var expectedSocForced = Math.max(minSoc, simulatedSoc - socDropNormal * frac);
        return {
            mode: MODY.NORMAL,
            reason: "drahá (Lv" + levelBuy + "≥" + PRAH_DRAHA + "), vybíjení SOC " + Math.round(simulatedSoc) + "% → ~" + Math.round(expectedSocForced) + "%"
        };
    }

    // PRIORITA 6: ŠETŘIT (výchozí mód) - pouze levné hodiny (levelBuy < PRAH_DRAHA)
    return {
        mode: MODY.SETRIT,
        reason: "Šetřím (Lv" + levelBuy + "<" + PRAH_DRAHA + "), SOC " + Math.round(simulatedSoc) + "%"
    };
}

// === SIMULACE SOC ===
function simulateSocChange(mode, hour, soc, hFraction, chargeTarget) {
    var frac = (hFraction !== undefined) ? hFraction : 1.0;
    var isSolar = hour >= solarStartHour && hour < solarEndHour;
    switch (mode) {
        case MODY.NABIJET_ZE_SITE:
            var maxChargeSoc = (chargeTarget && chargeTarget > 0) ? chargeTarget : 100;
            return Math.min(maxChargeSoc, soc + (chargeRateKwh * frac * chargeEfficiency / kapacitaBaterie * 100));
        case MODY.PRODAVAT:
            var dischRateKwh = maxFeedInW / 1000;
            return Math.max(minSoc, soc - (dischRateKwh * frac / dischargeEfficiency / kapacitaBaterie * 100));
        case MODY.SETRIT:
            return soc;
        case MODY.ZAKAZ_PRETOKU:
            return Math.max(minSoc, soc - socDropSetrit * frac);
        case MODY.NORMAL:
            if (isSolar) {
                var solarGainSim = getSolarGainForHour(hour, remainingSolarKwh, solarHoursCount, frac);
                // v18.13: Záporný gain = spotřeba > výroba, SOC klesá
                return Math.min(100, Math.max(minSoc, soc + solarGainSim));
            }
            return Math.max(minSoc, soc - socDropNormal * frac);
        case MODY.BALANCOVANI:
            // Solar/cheap hours: charge like NABIJET, expensive: hold like SETRIT
            var balIsSolar = hour >= solarStartHour && hour < solarEndHour;
            if (balIsSolar) {
                return Math.min(100, soc + (chargeRateKwh * frac * chargeEfficiency / kapacitaBaterie * 100));
            }
            return soc; // hold during non-solar (may charge from cheap grid but conservatively simulate hold)
        default:
            return soc;
    }
}

// === GENEROVÁNÍ PLÁNU ===
var modeNamesCZ = {
    normal: "Normální provoz",
    setrit: "Šetřit baterii",
    nabijet_ze_site: "Nabíjet ze sítě",
    prodavat: "Prodávat do sítě",
    zakaz_pretoku: "Zákaz přetoků",
    "Balancování": "Balancování baterie"
};

// v22: Multi-hour balancing
var balancingForceStopHours = config.balancing_force_stop_hours || 2;
var balancingHoursUsed = 0;
// Check how many hours already elapsed (if balancing is running)
var _balStartedAt = global.get("balancing_started_at") || 0;
var _balElapsedHours = _balStartedAt > 0 ? (Date.now() - _balStartedAt) / (1000 * 3600) : 0;
var balancingHoursRemaining = Math.max(0, balancingForceStopHours - _balElapsedHours);

var plan = [];
var simulatedSoc = currentSoc;

for (var pi = 0; pi < horizont; pi++) {
    var planHour = (currentHour + pi) % 24;
    var isNextDay = (currentHour + pi) >= 24;
    var priceData = hourPrices[pi];
    var hFrac = (pi === 0) ? firstHourFraction : 1.0;
    var result = calculateModeForHour(pi, priceData, simulatedSoc, hFrac);
    simulatedSoc = simulateSocChange(result.mode, planHour, simulatedSoc, hFrac, targetSocFromGrid);
    plan.push({
        hour: planHour,
        offset: pi,
        mode: result.mode,
        modeCZ: modeNamesCZ[result.mode] || result.mode,
        reason: result.reason,
        priceLevel: priceData.levelBuy,
        priceBuy: priceData.buy,
        priceSell: priceData.sell,
        simulatedSoc: Math.round(simulatedSoc),
        isNextDay: isNextDay,
        isChargingHour: chargingOffsets[pi] || false,
        isSolarHour: solarOffsets[pi] || false,
        isDischargeHour: dischargeOffsets[pi] || false,
        isArbitrageCharge: !!arbitrageChargeOffsets[pi],
        isArbitrageSell: !!arbitrageSellOffsets[pi],
        isBalancovani: result.mode === MODY.BALANCOVANI
    });
}

// === LOGOVÁNÍ ===
var countSetrit = 0, countNormal = 0, countNabijet = 0, countProdavat = 0, countBalancovani = 0;
for (var cs = 0; cs < plan.length; cs++) {
    if (plan[cs].mode === MODY.SETRIT) countSetrit++;
    else if (plan[cs].mode === MODY.NORMAL) countNormal++;
    else if (plan[cs].mode === MODY.NABIJET_ZE_SITE) countNabijet++;
    else if (plan[cs].mode === MODY.PRODAVAT) countProdavat++;
    else if (plan[cs].mode === MODY.BALANCOVANI) countBalancovani++;
}

// === VÝSTUP ===
var currentMode = plan.length > 0 ? plan[0].mode : MODY.NORMAL;
var currentReason = plan.length > 0 ? plan[0].reason : "";

msg.payload = {
    currentMode: currentMode,
    currentReason: currentReason,
    currentHour: currentHour,
    plan: plan,
    dischargeDebug: dischargeDebug,
    arbitrage: {
        chargeHours: Object.keys(arbitrageChargeOffsets).length,
        sellHours: Object.keys(arbitrageSellOffsets).length,
        totalChargeKwh: Math.round(totalArbChargeKwh * 10) / 10,
        debug: arbitrageDebug,
        peakSocFromSolar: Math.round(peakSocFromSolar),
        nightReservePct: Math.round(nightReservePct)
    },
    config: { 
        prah_levna: PRAH_LEVNA,
        prah_draha: PRAH_DRAHA,
        effective_threshold: effectiveThreshold,
        solarStartHour: solarStartHour,
        solarEndHour: solarEndHour
    },
    proteus: {
        firstSolarOffset: firstSolarOffset,
        dischargeHoursCount: Object.keys(dischargeOffsets).length,
        solarHoursCount: Object.keys(solarOffsets).length,
        energyBudgetKwh: Math.round(energyBudgetKwh * 10) / 10,
        usedEnergyKwh: Math.round(usedEnergyKwh * 10) / 10,
        effectiveThreshold: effectiveThreshold,
        peakSoc: Math.round(currentSoc + solarSocGainTotal),
        totalSolarAvailable: Math.round((remainingSolarKwh + forecastZitra) * 10) / 10,
        forecastZitra: forecastZitra,
        drainBeforeSolarPct: drainBeforeSolarPct,
        socAfterDrain: Math.round(socAfterDrain),
        minRequiredSoc: minRequiredSoc
    },
    smartCharging: {
        targetSocFromGrid: Math.round(targetSocFromGrid),
        gridChargeNeeded: Math.round(gridChargeNeeded * 10) / 10,
        hoursNeeded: hoursNeeded,
        assignedHours: assignedHours,
        viableHoursAvailable: viableChargingHours.length,
        remainingSolar: Math.round(remainingSolarKwh * 10) / 10,
        roundTripEfficiency: Math.round(roundTripEfficiency * 100),
        amortizace: amortizace,
        daysToFullCharge: daysSinceFullCharge,
        maintenanceCharge: maintenanceCharge,
        isWinter: isWinter,
        chargingReason: gridChargeNeeded > 0 
            ? (maintenanceCharge ? "maintenance (20d)" : "deficit " + Math.round(minRequiredSoc - socAfterDrain) + "%")
            : "nepotřeba (SOC " + Math.round(socAfterDrain) + "% > min " + minRequiredSoc + "%)"
    },
    planSummary: {
        setritHours: countSetrit,
        normalHours: countNormal,
        nabijetHours: countNabijet,
        prodavatHours: countProdavat,
        balancovaniHours: countBalancovani
    },
    status: {
        soc: currentSoc,
        remainingSolar: remainingSolarKwh,
        forecastZitra: forecastZitra,
        forecastDnes: forecast.dnes || 0,
        prodejEnabled: prodejZBaterieEnabled,
        blokaceVybijeni: blokaceVybijeni,
        blokaceText: blokaceText
    },
    generatedAt: now.toISOString()
};

var modeColors = {
    normal: "green",
    setrit: "yellow",
    nabijet_ze_site: "blue",
    prodavat: "red",
    zakaz_pretoku: "purple",
    "Balancování": "cyan"
};
node.status({
    fill: modeColors[currentMode] || "grey",
    shape: "dot",
    text: "v19 " + currentMode
        + " | Š:" + countSetrit + " N:" + countNormal + " Nab:" + countNabijet + " Prod:" + countProdavat + " Bal:" + countBalancovani
        + " | effThr:" + effectiveThreshold
        + " | SOC:" + currentSoc + "% drn:" + drainBeforeSolarPct + "% →" + Math.round(socAfterDrain) + "%"
        + " | ☀" + solarStartHour + "-" + solarEndHour + "h"
        + (gridChargeNeeded > 0 ? " | ⚡" + Math.round(targetSocFromGrid) + "%" : "")
});

return msg;
