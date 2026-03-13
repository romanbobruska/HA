// [3/3] Topení — bezpečnostní pojistky + výstup
var h=msg.h,a=h.actions.slice(),reason=h.reason;
// OCHRANA: nibe_off nelze pokud pracuje
if(a.indexOf("nibe_off")>-1&&!h.canOffNibe){a=a.filter(function(x){return x!=="nibe_off";});reason+=" ⚠️NIBE_PROT";}
// OCHRANA: nibe_on + nibe_off
if(a.indexOf("nibe_on")>-1&&a.indexOf("nibe_off")>-1){a=a.filter(function(x){return x!=="nibe_on"&&x!=="nibe_off";});reason+=" ⚠️KONFL";}
// COOLDOWN
var hasOn=a.indexOf("nibe_on")>-1,hasOff=a.indexOf("nibe_off")>-1;
if((hasOn&&!h.nibeOn)||(hasOff&&h.nibeOn&&h.canOffNibe)){
if(!h.nibeCdOk&&!h.fS){a=a.filter(function(x){return x!=="nibe_on"&&x!=="nibe_off";});reason+=" ⏳CD";}
else flow.set("last_nibe_switch",h.now);}
// MUTEX: NIBE + patrony
hasOn=a.indexOf("nibe_on")>-1;hasOff=a.indexOf("nibe_off")>-1;
var hasPOn=a.indexOf("p1_on")>-1||a.indexOf("p2_on")>-1||a.indexOf("p3_on")>-1;
var patRun=h.p1||h.p2||h.p3;
if(hasOn&&(hasPOn||patRun)){a=a.filter(function(x){return x!=="nibe_on";});reason+=" ⚠️MX:NIBE";}
if(hasPOn&&h.nibeOn&&!hasOff){a=a.filter(function(x){return x!=="p1_on"&&x!=="p2_on"&&x!=="p3_on";});reason+=" ⚠️MX:PAT";}
if(hasPOn&&hasOff){var ni=a.indexOf("nibe_off");var pi2=Math.min(a.indexOf("p1_on")>-1?a.indexOf("p1_on"):999,a.indexOf("p2_on")>-1?a.indexOf("p2_on"):999,a.indexOf("p3_on")>-1?a.indexOf("p3_on"):999);
if(ni>pi2){a=a.filter(function(x){return x!=="nibe_off";});a.unshift("nibe_off");}}
// Topení mod global
var fMod=(typeof flow.get("topeni_mod_active")!=="undefined")?flow.get("topeni_mod_active"):(global.get("topeni_mod")||"Vypnuto");
global.set("topeni_mod",fMod);
// cerpadlo_topi
var isHtg=h.pumpSt.indexOf("Vytápění")>-1,isTUV=h.pumpSt.indexOf("Ohřev vody")>-1||h.pumpSt.indexOf("TUV")>-1;
var nBD=flow.get("nibe_block_discharge")!==false;
global.set("cerpadlo_topi",(isHtg||isTUV)&&nBD);
// Status
var st=[h.auto?(h.letni?"LÉTO":"ZIMA"):"OFF",h.inT.toFixed(1)+"/"+h.effTgt.toFixed(1)+"°C","T:"+h.tankT.toFixed(0),"Lv"+h.lvl];
if(a.length>0)st.push("→"+a.join(","));
var col="green";if(!h.auto)col="grey";else if(h.inT<h.nouzT)col="red";else if(h.isDraha||h.patTgt>0)col="yellow";
node.status({fill:col,shape:"dot",text:st.join("|")});
var aM=null;if(a.length>0)aM=a.map(function(x){return{action:x};});
return[aM,{payload:{auto:h.auto,letni:h.letni,inT:h.inT,tgtT:h.effTgt,tankT:h.tankT,
lvl:h.lvl,isDraha:h.isDraha,nibeOn:h.nibeOn,obehOn:h.obehOn,patrony:h.actPat,patTgt:h.patTgt,
krb:h.krb,soc:h.soc,prebytek:h.prebytek,actions:a,reason:reason}}];