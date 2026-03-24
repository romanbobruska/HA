// Fix: sim() uses consumption predictions for non-solar hours instead of flat socN
// Also adds liveCons + autoK context to prep node
var fs = require('fs');
var path = 'd:/Programy/Programování/Node Red/HA/node-red/flows/fve-orchestrator.json';
var d = JSON.parse(fs.readFileSync(path, 'utf8'));
var changes = 0;

// === FIX 1: Prep node — add liveCons and autoK to context ===
var prep = d.find(function(n) { return n.id === 'rf_prep_params_01'; });
if (!prep) { console.error('PREP NODE NOT FOUND'); process.exit(1); }

// Add liveCons + autoK before msg.ctx
var anchor1 = 'msg.ctx={MODY:MODY,C:C,';
if (prep.func.indexOf('liveCons') >= 0) {
    console.log('PREP: liveCons already present, skipping');
} else {
    // Insert live consumption reading before msg.ctx
    var liveBlock = 'var liveConsE=ha["sensor.celkova_spotreba"]||{};var liveCons=(parseFloat(liveConsE.state)||0)/1000;\n' +
        'var autoHlad=((ha["input_boolean.auto_ma_hlad"]||{}).state)==="on";var autoK=autoHlad?(cfg.nabijeni_auta_sit_max_amperage||16)*230/1000:0;\n';
    prep.func = prep.func.replace(anchor1, liveBlock + anchor1);
    
    // Add liveCons,autoK to context object
    var ctxEnd = ',dF:dF,cw:cw,tW:tW,fc:fc};';
    prep.func = prep.func.replace(ctxEnd, ',dF:dF,cw:cw,tW:tW,fc:fc,liveCons:liveCons,autoK:autoK};');
    
    if (prep.func.indexOf('liveCons') >= 0 && prep.func.indexOf('autoK') >= 0) {
        changes++;
        console.log('PREP: Added liveCons + autoK ✓');
    } else {
        console.error('PREP: Replacement failed!');
        process.exit(1);
    }
}

// === FIX 2: Plan node — add cN() function and use it in sim() + cM() ===
var plan = d.find(function(n) { return n.id === 'rf_gen_plan_0004'; });
if (!plan) { console.error('PLAN NODE NOT FOUND'); process.exit(1); }

// Insert cN function after sG function (before sim function)
var simAnchor = 'return 0;}\nfunction sim(';
if (plan.func.indexOf('function cN(') >= 0) {
    console.log('PLAN: cN() already present, skipping insert');
} else {
    var cNFunc = 'return 0;}\n' +
        '// cN: consumption-based SOC% drop for non-solar hours (replaces flat socN)\n' +
        'function cN(h,f){f=f||1;var p=gP(h),c;' +
        'if(p&&p.avgConsumptionKwh>0&&p.sampleCount>=3)c=p.avgConsumptionKwh;' +
        'else c=x.liveCons||(C.dayCons/24);' +
        'c=Math.max(0.3,Math.min(c,C.dayCons/4));' +
        'if((!p||p.sampleCount<3)&&x.nibeK>0)c+=x.nibeK;' +
        'if((!p||p.sampleCount<3)&&x.autoK>0)c+=x.autoK;' +
        'return(c*f/C.kap)*100;}\n' +
        'function sim(';
    plan.func = plan.func.replace(simAnchor, cNFunc);
    if (plan.func.indexOf('function cN(') >= 0) {
        changes++;
        console.log('PLAN: Added cN() function ✓');
    } else {
        console.error('PLAN: cN insertion failed!');
        process.exit(1);
    }
}

// Fix sim() NORMAL mode: socN*f → cN(h,f)
var simOld = 'if(m===M.NORMAL)return iS?Math.min(100,Math.max(C.minSoc,s+sG(h,f))):Math.max(C.minSoc,s-C.socN*f);';
var simNew = 'if(m===M.NORMAL)return iS?Math.min(100,Math.max(C.minSoc,s+sG(h,f))):Math.max(C.minSoc,s-cN(h,f));';
if (plan.func.indexOf(simOld) >= 0) {
    plan.func = plan.func.replace(simOld, simNew);
    changes++;
    console.log('PLAN: sim() NORMAL fixed ✓');
} else if (plan.func.indexOf('s-cN(h,f)') >= 0) {
    console.log('PLAN: sim() NORMAL already fixed');
} else {
    console.error('PLAN: sim() NORMAL pattern not found!');
    process.exit(1);
}

// Fix cM() line 60: discharge threshold — use cN for SOC estimate
var cm60old = 'if(x.dO[off]&&R(soc-C.socN*f)>=C.minSoc+C.socN){var eD=clamp(soc-C.socN*f);';
var cm60new = 'var _cn=cN((x.cH+off)%24,f);if(x.dO[off]&&R(soc-_cn)>=C.minSoc+C.socN){var eD=clamp(soc-_cn);';
if (plan.func.indexOf(cm60old) >= 0) {
    plan.func = plan.func.replace(cm60old, cm60new);
    changes++;
    console.log('PLAN: cM() line 60 fixed ✓');
} else {
    console.log('PLAN: cM() line 60 pattern not found (may already be fixed)');
}

// Fix cM() line 63: drahá hour discharge
var cm63old = 'if(lv>=C.DRAHA&&R(soc-C.socN*f)>=C.minSoc+C.socN){var eD2=clamp(soc-C.socN*f);';
var cm63new = 'if(lv>=C.DRAHA&&R(soc-_cn)>=C.minSoc+C.socN){var eD2=clamp(soc-_cn);';
if (plan.func.indexOf(cm63old) >= 0) {
    plan.func = plan.func.replace(cm63old, cm63new);
    changes++;
    console.log('PLAN: cM() line 63 fixed ✓');
} else {
    console.log('PLAN: cM() line 63 pattern not found (may already be fixed)');
}

if (changes > 0) {
    fs.writeFileSync(path, JSON.stringify(d, null, 4), 'utf8');
    console.log('\nTotal changes: ' + changes + ' — saved to ' + path);
} else {
    console.log('\nNo changes needed');
}
