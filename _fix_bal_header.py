import json, sys

f = open(sys.argv[1], 'r', encoding='utf-8')
d = json.load(f)
f.close()

changes = 0

for n in d:
    nid = n.get('id', '')

    # 1) Fix opp_bal_check: ALWAYS send datetime + boolean to HA
    if nid == 'opp_bal_check':
        n['func'] = (
            '// Check for pending opportunistic balancing result\n'
            'var p=global.get("opp_bal_pending");\n'
            'if(!p)return[null,null];\n'
            'global.set("opp_bal_pending",null);\n'
            'var _cfg=global.get("fve_config")||{};\n'
            'var _fsh=_cfg.balancing_force_stop_hours||3;\n'
            '// Law 12.5: ALWAYS store latest passive bal info for plan header\n'
            'var _qual=p.durationH>=_fsh;\n'
            'global.set("bal_header_info",{datetime:p.datetime,ok:p.ok,passive:true,durationH:p.durationH,maxIdleMin:p.maxIdleMin,qualifying:_qual});\n'
            '// Law 12.5: ALWAYS update datetime entity (for header display)\n'
            'var dtMsg={payload:{action:"input_datetime.set_datetime",target:{entity_id:"input_datetime.last_pylontech_balanced"},data:{datetime:p.datetime}}};\n'
            '// Law 12.5: ALWAYS update boolean entity (for header OK/NOK)\n'
            'var bMsg={payload:{action:"input_boolean."+(p.ok?"turn_on":"turn_off"),target:{entity_id:"input_boolean.pylontech_balancing_ok"},data:{}}};\n'
            'if(_qual){\n'
            '  global.set("last_qualifying_balance_ts",Date.now());\n'
            '  node.warn("Opp bal: "+p.durationH.toFixed(1)+"h >= "+_fsh+"h, qualifying (pushes next planned)");\n'
            '}else{\n'
            '  node.warn("Opp bal: "+p.durationH.toFixed(1)+"h < "+_fsh+"h, non-qualifying (header updated, no push)");\n'
            '}\n'
            'node.warn("Opp bal result: "+(p.ok?"OK":"NOK")+" "+p.datetime+" dur:"+p.durationH.toFixed(1)+"h idle:"+p.maxIdleMin+"min");\n'
            'node.status({fill:p.ok?"green":"red",shape:"dot",text:(p.ok?"OK":"NOK")+" "+p.datetime+" "+p.durationH.toFixed(1)+"h"});\n'
            'return[dtMsg,bMsg];'
        )
        print('FIXED opp_bal_check: ALWAYS update datetime+boolean')
        changes += 1

    # 2) Fix planner: distinguish qualifying vs non-qualifying opp balance
    if n.get('name', '') == '4. Generování plánu' or nid == 'rf_gen_plan_':
        func = n.get('func', '')
        old_line = 'var lB=(ha["input_datetime.last_pylontech_balanced"]||{}).state||"";'
        if old_line in func:
            new_block = (
                'var lB=(ha["input_datetime.last_pylontech_balanced"]||{}).state||"";\n'
                '// Law 12.5: if last bal was non-qualifying passive, use qualifying ts for planner\n'
                'var _bhdr=global.get("bal_header_info");\n'
                'var _nonQual=(_bhdr&&_bhdr.passive&&!_bhdr.qualifying);\n'
                'var _lBforPlan=lB;\n'
                'if(_nonQual&&_bhdr&&_bhdr.datetime){\n'
                '  var _qualTs=global.get("last_qualifying_balance_ts")||0;\n'
                '  if(_qualTs>0){_lBforPlan=new Date(_qualTs).toISOString().replace("T"," ").substring(0,19);}\n'
                '  else{_lBforPlan="";}\n'
                '}'
            )
            func = func.replace(old_line, new_block)
            # Fix dB calculation to use _lBforPlan instead of lB
            lines = func.split('\n')
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('var dB=') and 'lB' in stripped and '_lBforPlan' not in stripped:
                    new_lines.append(line.replace('lB', '_lBforPlan', 1))
                    print('  Fixed dB calculation to use _lBforPlan')
                else:
                    new_lines.append(line)
            n['func'] = '\n'.join(new_lines)
            print('FIXED planner: qualifying check added')
            changes += 1
        else:
            print('Planner: old_line not found')

    # 3) Fix plan output: remove debug warn line
    if nid == 'rf_plan_output_05':
        func = n.get('func', '')
        lines = func.split('\n')
        new_lines = [l for l in lines if 'DBG hdr' not in l]
        if len(new_lines) != len(lines):
            print('FIXED plan output: removed debug warn')
            changes += 1
        n['func'] = '\n'.join(new_lines)

print('Total changes:', changes)

with open(sys.argv[2], 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print('Written to', sys.argv[2])
