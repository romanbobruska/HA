# -*- coding: utf-8 -*-
import json, io, os, sys, difflib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
nid = sys.argv[1]
key = sys.argv[2] if len(sys.argv) > 2 else "func"

live_path = os.path.join(os.environ["TEMP"], "_live_flows.json")
flows_dir = r"d:\Programy\Programování\Node Red\HA\node-red\flows"

live = json.load(open(live_path, encoding="utf-8"))
ln = [n for n in live if n.get("id") == nid][0]

gn = None
for fn in os.listdir(flows_dir):
    if not fn.endswith(".json"): continue
    for n in json.load(open(os.path.join(flows_dir, fn), encoding="utf-8")):
        if isinstance(n, dict) and n.get("id") == nid:
            gn = n
gv = (gn.get(key) or "").split("\n")
lv = (ln.get(key) or "").split("\n")
print("git lines=%d  live lines=%d" % (len(gv), len(lv)))
diff = list(difflib.unified_diff(lv, gv, fromfile="LIVE(server)", tofile="GIT", lineterm=""))
if not diff:
    print("NO DIFF (identical)")
for l in diff[:120]:
    print(l)
