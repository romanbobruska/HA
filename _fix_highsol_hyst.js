// Fix: High solar day daytime hysteresis changed from nocSniz(0.5) to new config param (0.2)
// Law change: POZADAVKY.TXT 8.2 — "hystereze teploty domu se timto zvysuje na -0.2 stupnu"
// Affects: rf_htg_read_001 (add param) + rf_htg_decide2 (use new param)
const fs = require('fs');

function patchRead(flows) {
    var fn = flows.find(x => x.id === 'rf_htg_read_001');
    if (!fn) { console.error('FAIL: rf_htg_read_001 not found'); return false; }

    // Add highSolSniz config param after nocSniz line
    var old = 'nocSniz:cfg.topeni_nocni_snizeni||0.5,nocOd:cfg.topeni_nocni_od||22,nocDo:cfg.topeni_nocni_do||6,';
    var fix = 'nocSniz:cfg.topeni_nocni_snizeni||0.5,highSolSniz:cfg.topeni_high_sol_snizeni||0.2,nocOd:cfg.topeni_nocni_od||22,nocDo:cfg.topeni_nocni_do||6,';

    if (fn.func.includes(fix)) { console.log('  SKIP: already patched'); return false; }
    if (!fn.func.includes(old)) { console.error('  FAIL: old string not found'); return false; }

    fn.func = fn.func.replace(old, fix);
    console.log('  OK: highSolSniz param added');

    try { new Function('msg,flow,global,node', fn.func); console.log('  SYNTAX OK'); return true; }
    catch(e) { console.error('  SYNTAX ERROR:', e.message); return false; }
}

function patchDecide(flows) {
    var fn = flows.find(x => x.id === 'rf_htg_decide2');
    if (!fn) { console.error('FAIL: rf_htg_decide2 not found'); return false; }

    // Change effTgt calculation: use highSolSniz instead of nocSniz for daytime high solar day
    var old = 'h.effTgt=h.isNight?(h.tgtT-h.nocSniz):(h.highSolDay&&h.isSol&&!h.autoHlad&&!h.autoNabiji?(h.tgtT-h.nocSniz):h.tgtT);';
    var fix = 'h.effTgt=h.isNight?(h.tgtT-h.nocSniz):(h.highSolDay&&h.isSol&&!h.autoHlad&&!h.autoNabiji?(h.tgtT-h.highSolSniz):h.tgtT);';

    if (fn.func.includes(fix)) { console.log('  SKIP: already patched'); return false; }
    if (!fn.func.includes(old)) { console.error('  FAIL: old string not found'); return false; }

    fn.func = fn.func.replace(old, fix);
    console.log('  OK: effTgt uses highSolSniz for daytime high solar day');

    try { new Function('msg,flow,global,node', fn.func); console.log('  SYNTAX OK'); return true; }
    catch(e) { console.error('  SYNTAX ERROR:', e.message); return false; }
}

// Server
var sPath = process.env.TEMP + '/_server_flows_v3.json';
var s = JSON.parse(fs.readFileSync(sPath, 'utf8'));
console.log('=== SERVER rf_htg_read_001 ===');
var r1 = patchRead(s);
console.log('=== SERVER rf_htg_decide2 ===');
var r2 = patchDecide(s);
if (r1 || r2) { fs.writeFileSync(sPath, JSON.stringify(s, null, 2), 'utf8'); console.log('Server flows saved.'); }

// Git
var gPath = './node-red/flows/fve-heating.json';
var g = JSON.parse(fs.readFileSync(gPath, 'utf8'));
console.log('=== GIT rf_htg_read_001 ===');
var g1 = patchRead(g);
console.log('=== GIT rf_htg_decide2 ===');
var g2 = patchDecide(g);
if (g1 || g2) { fs.writeFileSync(gPath, JSON.stringify(g, null, 4), 'utf8'); console.log('Git flows saved.'); }

console.log('\nDONE. Changes:', (r1||r2)?'SERVER':'none(srv)', (g1||g2)?'GIT':'none(git)');
