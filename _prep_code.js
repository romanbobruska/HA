// [1/5] Příprava parametrů — config, stav, forecast, solární křivky
var d = msg.planData, cfg = d.config || {}, st = d.status || {}, fc = d.forecast || {};
var prices = d.prices || global.get("fve_prices_forecast") || [];
var MODY = {NORMAL:"normal",SETRIT:"setrit",NABIJET:"nabijet_ze_site",PRODAVAT:"prodavat",ZAKAZ:"zakaz_pretoku",SOLAR:"solar_charging",BAL:"Balancování"};
var C = {
    kap:cfg.kapacita_baterie_kwh||28, minSoc:cfg.min_soc||20, maxDaily:cfg.max_daily_soc||80,
    amort:cfg.amortizace_baterie_czk_kwh||1.5, chEff:cfg.charge_efficiency||0.90, dchEff:cfg.discharge_efficiency||0.90,
    chKwh:cfg.charge_rate_kwh||5, socN:cfg.soc_drop_normal_pct||5, socS:cfg.soc_drop_setrit_pct||1,
    dayCons:cfg.daily_consumption_kwh||20, LEVNA:cfg.prah_levna_energie||4, DRAHA:cfg.prah_draha_energie||12,
    hor:cfg.plan_horizon_hours||12, maxGrid:cfg.max_spotreba_sit_w||22000, maxFeed:cfg.max_feed_in_w||7600,
    prodej:cfg.prodej_z_baterie_enabled===true, blokace:cfg.blokace_vybijeni===true,
    manual:cfg.manual_mod||"auto", letni:cfg.letni_rezim===true,
    minArb:cfg.min_arbitrage_profit_czk||3, minSell:cfg.min_sell_profit_czk||3,
    nResKwh:cfg.night_reserve_kwh||10, nMargin:cfg.night_target_soc_margin||5,
    nibeKwh:cfg.nibe_est_consumption_kwh||2.0, balInt:cfg.balancing_interval_days||30,
    balStop:cfg.balancing_force_stop_hours||2, balMinSol:cfg.balancing_min_solar_kwh||2,
    solOverKwh:(cfg.topeni_solar_override_w||8000)/1000
};
C.rtEff=C.chEff*C.dchEff; C.nResPct=(C.nResKwh/C.kap)*100;
var solS=d.solarStartHour||cfg.solar_start_hour||9, solE=d.solarEndHour||cfg.solar_end_hour||17;
var now=new Date(), cH=now.getHours(), cMin=now.getMinutes(), fFrac=(60-cMin)/60;
var cM=now.getMonth(), isW=(cM>=9||cM<=2), cSoc=st.battery_soc||50;
var fZ=fc.zitra||0, fPH=d.forecastPerHour||{}, fPHT=d.forecastPerHourTomorrow||{};
var hMid=(24-cH)%24; if(hMid===0)hMid=24;
for(var m=0;m<24;m++){var o=(m-cH+24)%24;if(o>=hMid&&fPHT[m]!==undefined)fPH[m]=fPHT[m];}
var rS=d.zbyvajiciSolar||0;
var mMax=cfg.month_max_solar_kwh||[15,35,60,90,110,120,115,105,75,50,20,12];
if(rS>mMax[cM])rS=mMax[cM];
var mxT=mMax[cM]; var dom=now.getDate(),dim=new Date(now.getFullYear(),cM+1,0).getDate();
if(dom>=dim-2)mxT=Math.max(mxT,mMax[(cM+1)%12]||100);
if(fZ>mxT)fZ=mxT;
// Solární křivky (kompaktní — 12 měsíců)
var SC=cfg.solar_curves||{0:{8:.02,9:.08,10:.14,11:.18,12:.2,13:.18,14:.12,15:.06,16:.02},1:{7:.01,8:.04,9:.09,10:.14,11:.17,12:.19,13:.17,14:.11,15:.06,16:.02},2:{6:.01,7:.02,8:.06,9:.1,10:.13,11:.15,12:.16,13:.14,14:.11,15:.07,16:.04,17:.01},3:{5:.01,6:.02,7:.04,8:.07,9:.1,10:.12,11:.14,12:.14,13:.13,14:.1,15:.07,16:.04,17:.02},4:{5:.01,6:.03,7:.05,8:.08,9:.1,10:.12,11:.13,12:.13,13:.12,14:.1,15:.07,16:.04,17:.02},5:{5:.02,6:.03,7:.05,8:.08,9:.1,10:.12,11:.13,12:.13,13:.12,14:.1,15:.07,16:.04,17:.01},6:{5:.02,6:.03,7:.05,8:.08,9:.1,10:.12,11:.13,12:.13,13:.12,14:.1,15:.07,16:.04,17:.01},7:{5:.01,6:.02,7:.05,8:.08,9:.1,10:.12,11:.14,12:.14,13:.12,14:.1,15:.07,16:.04,17:.01},8:{6:.01,7:.03,8:.07,9:.1,10:.13,11:.15,12:.15,13:.14,14:.11,15:.07,16:.03,17:.01},9:{7:.02,8:.05,9:.1,10:.14,11:.16,12:.17,13:.16,14:.11,15:.06,16:.03},10:{8:.03,9:.08,10:.14,11:.18,12:.2,13:.18,14:.12,15:.06,16:.01},11:{8:.02,9:.07,10:.14,11:.19,12:.22,13:.19,14:.12,15:.05}};
var cw=SC[cM]||SC[5], tW=0;
for(var h=solS;h<solE;h++)tW+=cw[h]||0;
if(tW===0)tW=1;
// NIBE + blokace
var ha=global.get("homeassistant.homeAssistant.states")||{};
var inT=parseFloat((ha["sensor.hp2551ae_pro_v2_1_0_indoor_temperature"]||{}).state)||22;
var tgT=parseFloat((ha["input_number.nastavena_teplota_v_dome"]||{}).state)||23;
var nibeOn=((ha["switch.nibe_topeni"]||{}).state)==="on";var nibeK=(nibeOn||(inT<tgT&&tgT>18))?C.nibeKwh:0;
var cerp=global.get("cerpadlo_topi")||false,autoN=global.get("auto_nabijeni_aktivni")||false,sauna=global.get("sauna_aktivni")||false;
var bI=[];if(cerp)bI.push("topení");if(autoN)bI.push("auto");if(sauna)bI.push("sauna");
var lF=global.get("fve_last_full_charge")||null;
if(!lF){global.set("fve_last_full_charge",now.toISOString());lF=now.toISOString();}
var dF=Math.floor((Date.now()-new Date(lF).getTime())/86400000);
if(cSoc>=99)global.set("fve_last_full_charge",now.toISOString());
msg.ctx={MODY:MODY,C:C,prices:prices,cfg:cfg,solS:solS,solE:solE,cH:cH,cM:cM,fFrac:fFrac,isW:isW,cSoc:cSoc,now:now,fZ:fZ,fPH:fPH,rS:rS,cPred:d.consumptionPredictions||[],nibeK:nibeK,bTxt:bI.length>0?"ANO - "+bI.join(", "):"NE",dF:dF,cw:cw,tW:tW,fc:fc};
node.status({fill:"blue",shape:"dot",text:"Prep SOC:"+cSoc+"% ☀"+solS+"-"+solE});
return msg;