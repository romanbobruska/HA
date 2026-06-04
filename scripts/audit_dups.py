# -*- coding: utf-8 -*-
import json, io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
flows_dir = r"d:\Programy\Programování\Node Red\HA\node-red\flows"

# id -> list of (file, node)
occ = {}
for fn in sorted(os.listdir(flows_dir)):
    if not fn.endswith(".json"): continue
    nodes = json.load(open(os.path.join(flows_dir, fn), encoding="utf-8"))
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            occ.setdefault(n["id"], []).append((fn, n))

print("=== DUPLICATE node IDs across git flow files ===")
dups = {k: v for k, v in occ.items() if len(v) > 1}
if not dups:
    print("  (none)")
for nid, lst in dups.items():
    files = [f for f, _ in lst]
    # winner = alphabetically first file (deploy_merge_flows sorted glob)
    winner = sorted(files)[0]
    # check if funcs/content differ
    contents = [json.dumps({k: v for k, v in n.items() if k not in ("x","y","w","h","z","g")}, sort_keys=True, ensure_ascii=False) for _, n in lst]
    differ = len(set(contents)) > 1
    print("  %s  files=%s  winner=%s  CONTENT_DIFFERS=%s" % (nid, files, winner, differ))

# detailed overlap of the two history files
print("\n=== fve-history.json vs fve-history-learning.json overlap ===")
def ids(fn):
    return {n["id"] for n in json.load(open(os.path.join(flows_dir, fn), encoding="utf-8")) if isinstance(n, dict) and n.get("id")}
a = ids("fve-history.json"); b = ids("fve-history-learning.json")
print("  history ids=%d  learning ids=%d  overlap=%d" % (len(a), len(b), len(a & b)))
print("  overlap ids:", sorted(a & b))
print("  learning-only ids:", sorted(b - a))
