// [2/3] Topení — rozhodovací logika
var h=msg.h,cfg=h.cfg;
h.isDraha=(h.lvl>=h.DRAHA)&&(h.planMode!=="setrit");
h.isNight=(h.hr>=h.nocOd||h.hr<h.nocDo);
h.effTgt=h.isNight?(h.tgtT-h.nocSniz):(h.highSolDay&&h.isSol?(h.tgtT-h.nocSniz):h.tgtT);
h.actPat=(h.p1?1:0)+(h.p2?1:0)+(h.p3?1:0);
h.availPat=h.prebytek+h.actPat*h.patW;
h.pumpWork=h.pumpSt.indexOf("Klidový")===-1&&h.pumpSt!=="";
h.canOffNibe=!h.comp&&!h.pumpWork;
var a=[],reason="",patTgt=0,shutD=flow.get("shutdown_done")||false;
if(!h.auto){if(!shutD){if(h.p1)a.push("p1_off");if(h.p2)a.push("p2_off");if(h.p3)a.push("p3_off");flow.set("shutdown_done",true);reason="Auto OFF→STOP";}
else reason="Auto OFF";flow.set("topeni_mod_active","Vypnuto");global.set("topeni_mod","Vypnuto");}
else{var fS=flow.get("shutdown_done")===true;flow.set("shutdown_done",false);
if(h.letni){var sDone=flow.get("summer_setup_done")||false;
if(!sDone){if(h.canOffNibe)a.push("nibe_on");if(h.obehOn)a.push("obehove_off");if(h.p1)a.push("p1_off");if(h.p2)a.push("p2_off");if(h.p3)a.push("p3_off");
flow.set("summer_setup_done",true);reason="Léto init";}
if(h.coolEn){if(!h.coolOn&&h.inT>h.effTgt+h.hystChlaz)a.push("cool_on");else if(h.coolOn&&h.inT<h.effTgt)a.push("cool_off");
reason="Léto "+(h.coolOn?"chlaz":"");}else{if(h.coolOn)a.push("cool_off");reason="Léto";}
}else{flow.set("summer_setup_done",false);if(h.ventil)a.push("ventil_off");if(h.coolOn)a.push("cool_off");
var mod=flow.get("topeni_mod_active")||"Vypnuto";
var tankOk=h.tankT>=h.minTank,needH=h.inT<h.effTgt;
var dumpR=h.ultraL||h.cantExport;
var MSP=cfg.topeni_patron_min_solar_w||5000,fveM=(global.get("homeassistant.homeAssistant.states['sensor.fve_plan']")||{}).attributes;
fveM=(fveM&&fveM.current_mode)||h.planMode;
var DRAIN_P=cfg.topeni_patron_drain_soc_prah||95;
var patSolOk=h.solW>=MSP||fveM==="zakaz_pretoku"||h.soc>=DRAIN_P;
var PMSP=cfg.topeni_patron_max_sell_price||2,patSellOk=h.sellPrice<=PMSP||h.sellPrice>=99;
var patMohou=patSellOk&&patSolOk&&(!h.balActive||h.balSolDump)&&h.soc>=h.minSocPat&&!h.autoHlad&&!h.autoNabiji&&h.tankT<h.maxTankPat&&(!h.gridLost||h.solW>0);
if(patMohou&&h.actPat===0){if(h.availPat>=h.minPretok){patTgt=1;flow.set("pat_change_cooldown",0);}}
else if(patMohou&&h.actPat>0){patTgt=h.availPat<h.minPretok?0:h.actPat;}
var PM=0.3,tGap=h.effTgt-h.inT;
var patSocR=h.soc>=(h.minSocPat-15),bNeedWh=Math.max(0,(h.minSocPat-h.soc)/100*h.kapBat);
var consEst=h.solLeft*1500,patReal=dumpR||(patSocR&&h.zbSolar>(bNeedWh+consEst)*1.5);
if(h.isSol&&tGap<=PM&&needH&&patReal)mod="Patrony";
else if(tGap>PM&&needH)mod="NIBE";else if(!needH&&patMohou)mod="Patrony";
else if(!needH&&dumpR&&h.tankT<h.maxTank&&h.soc>=(cfg.topeni_dump_solar_soc||85))mod="NIBE";
else if(!needH)mod="Vypnuto";else mod="NIBE";
flow.set("topeni_mod_active",mod);
var nibeBlkMod=mod==="Patrony"||mod==="Vypnuto",patBlkMod=mod==="NIBE";
var korekce=h.actPat>0&&patMohou;
if(!korekce){var pw=[patTgt>=1&&!patBlkMod,patTgt>=2&&!patBlkMod,patTgt>=3&&!patBlkMod];
if(pw[0]!==h.p1)a.push(pw[0]?"p1_on":"p1_off");if(pw[1]!==h.p2)a.push(pw[1]?"p2_on":"p2_off");if(pw[2]!==h.p3)a.push(pw[2]?"p3_on":"p3_off");}
// NIBE
var safeT=h.effTgt-h.bezpPokles,canDefer=h.inT>=safeT,solDM=cfg.topeni_solar_defer_margin||0.2,canDeferSol=h.inT>=(h.effTgt-solDM),nibeBlkDch=true;
var hToLastSol=h.lastSolarHour>=0?(h.lastSolarHour-h.hr):99,finalSolWh=(cfg.topeni_final_solar_kwh||20)*1000,finalHrs=cfg.topeni_final_hours||3,hasSolRes=h.zbSolar>finalSolWh;
var mustHeatByPrice=!h.letni&&h.isSol&&hToLastSol>0&&hToLastSol<=finalHrs&&h.inT<h.tgtT;
var mustHeatFinal=!h.letni&&h.isSol&&h.lastSolarHour>=0&&h.inT<h.tgtT&&hToLastSol<=0;
var gridOk=!h.gridLost||(h.gridLost&&h.solW>=h.nibePeak);
function cheaperAhead(){for(var i=0;i<(global.get("fve_prices_forecast")||[]).length;i++){var p=(global.get("fve_prices_forecast")||[])[i];if(p.minute!==0)continue;if(p.hour<=h.hr)continue;if((p.levelCheapestHourBuy||99)<h.lvl)return true;}return false;}
function cheaperBeforeSol(){for(var i=0;i<(global.get("fve_prices_forecast")||[]).length;i++){var p=(global.get("fve_prices_forecast")||[])[i];if(p.minute!==0)continue;if(p.hour<=h.hr)continue;if(p.hour>=h.lastSolarHour)continue;if((p.levelCheapestHourBuy||99)<h.lvl)return true;}return false;}
var chAhead=cheaperAhead(),chBeforeSol=cheaperBeforeSol(),solCovers=h.isSol&&h.prebytek>=h.solOverride;
var nibeWant=needH||(!h.isDraha&&h.tankT<h.maxTank);
if(!h.ultraL&&h.autoNabiji&&nibeWant&&!nibeBlkMod)a.push("stop_auto_nabijeni");
if(!gridOk){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(h.krb){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(h.tankT>h.maxTank){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(nibeBlkMod){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(h.balActive&&!needH){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(h.isDraha){if(h.prebytek>=h.solOverride){if(!h.nibeOn)a.push("nibe_on");nibeBlkDch=false;}else if(mustHeatFinal){if(!h.nibeOn)a.push("nibe_on");reason+=" ⚡FINAL";}else if(mustHeatByPrice&&!chBeforeSol){if(!h.nibeOn)a.push("nibe_on");reason+=" ⚡PRICE";}else{if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}}
else if(nibeWant){var dumpF=dumpR&&!needH&&h.soc>=(cfg.topeni_dump_solar_soc||85)&&h.tankT<h.maxTank;
if(dumpF){if(!h.nibeOn)a.push("nibe_on");nibeBlkDch=false;}
else{var planCh=h.planMode==="setrit"&&h.lvl<=h.LEVNA;
if(!planCh&&!solCovers&&h.bigSolTom&&(!needH||canDeferSol)&&!mustHeatFinal&&!mustHeatByPrice){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(!planCh&&!solCovers&&h.highSolDay&&h.isSol&&(!needH||canDeferSol)&&!mustHeatFinal&&!mustHeatByPrice){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(!planCh&&!solCovers&&(mustHeatByPrice?chBeforeSol:chAhead)&&(!needH||canDefer)&&!mustHeatFinal){if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
else if(h.prebytek>=h.solOverride){if(!h.nibeOn)a.push("nibe_on");nibeBlkDch=false;}
else{if(!h.nibeOn)a.push("nibe_on");nibeBlkDch=h.soc<=90;}}}
else{if(h.nibeOn&&h.canOffNibe)a.push("nibe_off");}
if(dumpR&&!needH&&h.tankT<h.maxTank)nibeBlkDch=false;
flow.set("nibe_block_discharge",nibeBlkDch);
// Oběhové
if(!h.krb){var oTgt=h.isNight?(h.tgtT-h.nocSniz):h.effTgt,nHO=h.inT<oTgt;
if(h.balBlockPump){if(h.obehOn)a.push("obehove_off");}
else if(tankOk&&nHO)a.push("obehove_on");else{if(h.obehOn)a.push("obehove_off");}}
reason=[h.isDraha?"DRAHÁ(Lv"+h.lvl+")":"Lv"+h.lvl,"In:"+h.inT.toFixed(1)+"/"+h.effTgt.toFixed(1),"Tnk:"+h.tankT.toFixed(0)].join("|");
if(patTgt>0)reason+="|PAT:"+patTgt;if(h.isSol)reason+="|☀"+h.solLeft+"h";
}}
h.actions=a;h.reason=reason;h.patTgt=patTgt;h.fS=flow.get("shutdown_done")===false&&h.auto;
msg.h=h;
return msg;