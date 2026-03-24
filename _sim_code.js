// [4/5] Generování plánu (KROK 8 — calculateMode + simulateSoc)
var x=msg.ctx, C=x.C, hp=x.hp, M=x.MODY;
function gP(h){for(var i=0;i<x.cPred.length;i++)if(x.cPred[i].hour===h)return x.cPred[i];return null;}
function sS(h){return(x.cw[h]||0)/x.tW;}
function sG(h,f){f=f||1;var p=gP(h),c=(p&&p.avgConsumptionKwh>0)?p.avgConsumptionKwh:C.dayCons/24;
if(c>C.dayCons/6)c=C.dayCons/6;
var iS=h>=x.solS&&h<x.solE;if(iS&&x.nibeK>0&&(x.fPH[h]||0)>C.solOverKwh)c+=x.nibeK;
if(x.fPH[h]!==undefined)return((x.fPH[h]-c*f)*f*C.chEff/C.kap)*100;
if(p&&p.sampleCount>=3&&p.avgSolarKwh>0)return((p.netSolarGainKwh||0)*f*C.chEff/C.kap)*100;
if(x.sC>0&&x.rS>0){var hk=x.rS*sS(h);return((hk-c*f)*f*C.chEff/C.kap)*100;}
if(x.fZ>0&&sS(h)>0){var fk=x.fZ*sS(h);return((fk-c*f)*f*C.chEff/C.kap)*100;}return 0;}
function sim(m,h,s,f,t){f=f||1;var iS=h>=x.solS&&h<x.solE;
if(m===M.NABIJET)return Math.min(t||100,s+(C.chKwh*f*C.chEff/C.kap*100));
if(m===M.PRODAVAT)return Math.max(x.sellTarget||C.minSoc,s-(C.maxFeed/1000*f/C.dchEff/C.kap*100));
if(m===M.SETRIT)return iS?Math.min(100,s+Math.max(0,sG(h,f))):s;
if(m===M.ZAKAZ)return iS?Math.min(100,Math.max(C.minSoc,s+sG(h,f))):Math.max(C.minSoc,s-C.socS*f);
if(m===M.NORMAL)return iS?Math.min(100,Math.max(C.minSoc,s+sG(h,f))):Math.max(C.minSoc,s-C.socN*f);
if(m===M.BAL)return iS?Math.min(100,s+(C.chKwh*f*C.chEff/C.kap*100)):s;return s;}
var ha=global.get("homeassistant.homeAssistant.states")||{};
var lB=(ha["input_datetime.last_pylontech_balanced"]||{}).state||"";
// Law 12.5: if last bal was non-qualifying passive, use qualifying ts for planner
var _bhdr=global.get("bal_header_info");
var _nonQual=(_bhdr&&_bhdr.passive&&!_bhdr.qualifying);
var _lBforPlan=lB;
if(_nonQual&&_bhdr&&_bhdr.datetime){
  var _qualTs=global.get("last_qualifying_balance_ts")||0;
  if(_qualTs>0){_lBforPlan=new Date(_qualTs).toISOString().replace("T"," ").substring(0,19);}
  else{_lBforPlan="";}
}
var dB=(_lBforPlan&&lB!=="unknown")?(Date.now()-new Date(lB).getTime())/86400000:999;
var bNeed=dB>=C.balInt,bUsed=0,bSt=global.get("balancing_started_at")||0;
var bEl=bSt>0?(Date.now()-bSt)/3600000:0;
function R(s){return Math.round(s);}
function clamp(v){return Math.min(100,Math.max(C.minSoc,R(v)));}
function cM(off,pd,soc,f){f=f||1;var S=R(soc),lv=pd.levelBuy,sl=pd.sell;
if(C.manual!=="auto")return{mode:C.manual,reason:"Manuální režim, SOC "+S+"%"};
var canB=bNeed&&bUsed<C.balStop&&(off===0?bEl<C.balStop:true);
if(sl<=0&&!(canB&&x.sO[off]))return{mode:M.ZAKAZ,reason:"Záporná prodejní cena, SOC "+S+"%"};
if(canB&&x.sO[off]){var bh=(x.cH+off)%24,bk=x.fPH[bh]!==undefined?x.fPH[bh]:0;
if(bk<=0)bk=(x.fZ>0?x.fZ:x.rS)*sS(bh);if(bk>=C.balMinSol){bUsed++;
return{mode:M.BAL,reason:"Balancování baterie ("+bk.toFixed(1)+" kWh solární), SOC "+S+"%, "+R(dB)+" dní od posledního"};}}
if(x.cO[off]&&soc<x.tSoc){var eC=clamp(soc+(C.chKwh*f*C.chEff/C.kap*100));
return{mode:M.NABIJET,reason:"Nabíjení ze sítě na "+R(x.tSoc)+"%, SOC "+S+"→~"+eC+"%"};}
if(x.aCO[off]){var eA=clamp(soc+(C.chKwh*f*C.chEff/C.kap*100));
return{mode:M.NABIJET,reason:"Nabíjení (arbitráž pro hodinu "+x.aCO[off].targetHour+":00), SOC "+S+"→~"+eA+"%"};}
if(C.prodej&&soc>x.sellTarget){var rv=sl*C.dchEff,cb=C.amort;
if(x.viab.length>0){var s2=0;for(var i=0;i<x.viab.length;i++)s2+=x.viab[i].buy;cb=(s2/x.viab.length)/C.rtEff+C.amort;}
if(rv-cb>=C.minSell||x.aSO[off])
return{mode:M.PRODAVAT,reason:"Prodej do sítě (zisk "+R((rv-cb)*10)/10+" Kč/kWh), SOC "+S+"% (cíl "+x.sellTarget+"%)"};}
if(soc<=C.minSoc&&!x.sO[off])return{mode:M.SETRIT,reason:"Ochrana minimální SOC, SOC "+S+"% ≤ "+C.minSoc+"%"};
if(x.sO[off]){var hh=(x.cH+off)%24,sg=sG(hh,f),es=clamp(soc+sg);
var nibeN=(x.nibeK>0&&(x.fPH[hh]||0)>C.solOverKwh)?" (NIBE topí)":"";
if(sg<=0&&R(soc+sg)<C.minSoc+C.socN)return{mode:M.SETRIT,reason:"Solární hodina (nízký zisk), šetřím baterii"+nibeN+", SOC "+S+"%"};
if(sg<=0&&x.dO[off]&&soc>=C.minSoc){
return{mode:M.NORMAL,reason:"Solární (nízký zisk) + vybíjení"+nibeN+", SOC "+S+"→~"+es+"%"};}
if(sg>C.socN)return{mode:M.NORMAL,reason:"Solární hodina"+nibeN+", SOC "+S+"→~"+es+"%"};
if(lv>=C.DRAHA&&soc>=C.minSoc&&R(soc+sg)>=C.minSoc+C.socN)return{mode:M.NORMAL,reason:"Solární + drahá hodina (úroveň "+lv+")"+nibeN+", SOC "+S+"→~"+es+"%"};
if(x.bEx)return{mode:M.SETRIT,reason:"Solární (nízký zisk), šetřím baterii"+nibeN+", SOC "+S+"%"};
return{mode:M.NORMAL,reason:"Solární hodina"+nibeN+", SOC "+S+"→~"+es+"%"};}
if(x.dO[off]&&R(soc-C.socN*f)>=C.minSoc+C.socN){var eD=clamp(soc-C.socN*f);
var cn=lv>=C.DRAHA?"Drahá hodina":"Střední cena";
return{mode:M.NORMAL,reason:cn+" (úroveň "+lv+"), SOC "+S+"→~"+eD+"%"};}
if(lv>=C.DRAHA&&R(soc-C.socN*f)>=C.minSoc+C.socN){var eD2=clamp(soc-C.socN*f);
return{mode:M.NORMAL,reason:"Drahá hodina (úroveň "+lv+"), SOC "+S+"→~"+eD2+"%"};}
if(x.aS[off])return{mode:M.SETRIT,reason:"Šetřím pro dražší hodiny (úroveň "+lv+"), SOC "+S+"%"};
return{mode:M.SETRIT,reason:"Šetřím baterii (úroveň "+lv+"), SOC "+S+"%"};}
var nm={normal:"Normální provoz",setrit:"Šetřit baterii",nabijet_ze_site:"Nabíjet ze sítě",prodavat:"Prodávat do sítě",zakaz_pretoku:"Zákaz přetoků","Balancování":"Balancování baterie"};
var plan=[],sm=x.cSoc;
for(var pi=0;pi<C.hor;pi++){var ph=(x.cH+pi)%24,nd=(x.cH+pi)>=24,pd=hp[pi],hf=pi===0?x.fFrac:1;
var r=cM(pi,pd,sm,hf);sm=sim(r.mode,ph,sm,hf,x.tSoc);
plan.push({hour:ph,offset:pi,mode:r.mode,modeCZ:nm[r.mode]||r.mode,reason:r.reason,
priceLevel:pd.origLevel||pd.levelBuy,priceBuy:pd.buy,priceSell:pd.sell,simulatedSoc:Math.round(sm),isNextDay:nd,
isChargingHour:x.cO[pi]||false,isSolarHour:x.sO[pi]||false,isDischargeHour:x.dO[pi]||false,
isArbitrageCharge:!!x.aCO[pi],isArbitrageSell:!!x.aSO[pi],isBalancovani:r.mode===M.BAL});}
x.plan=plan;
node.status({fill:"green",shape:"dot",text:"Plan "+plan.length+"h SOC:"+x.cSoc+"→"+Math.round(sm)+"%"});
return msg;