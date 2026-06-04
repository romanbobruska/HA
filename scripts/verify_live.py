# -*- coding: utf-8 -*-
import json, io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

live_path = os.path.join(os.environ["TEMP"], "_live_flows.json")
flows_dir = r"d:\Programy\Programování\Node Red\HA\node-red\flows"

with open(live_path, encoding="utf-8") as f:
    live = json.load(f)
live_by_id = {n["id"]: n for n in live if isinstance(n, dict) and n.get("id")}

git_by_id = {}
git_src = {}
for fn in sorted(os.listdir(flows_dir)):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(flows_dir, fn), encoding="utf-8") as f:
        nodes = json.load(f)
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            git_by_id[n["id"]] = n
            git_src[n["id"]] = fn

# Compare every git node against live. Ignore purely-cosmetic keys that NR/merge/audit rewrite.
IGNORE = {"x", "y", "wires", "g", "z"}
mismatch = []
missing = []
for nid, gn in git_by_id.items():
    ln = live_by_id.get(nid)
    if ln is None:
        missing.append((nid, git_src[nid], gn.get("type"), gn.get("name")))
        continue
    diffs = []
    keys = (set(gn.keys()) | set(ln.keys())) - IGNORE
    for k in keys:
        if gn.get(k) != ln.get(k):
            diffs.append(k)
    if diffs:
        mismatch.append((nid, git_src[nid], gn.get("name"), diffs))

print("GIT nodes:", len(git_by_id), "| LIVE nodes:", len(live_by_id))
print("\n=== MISSING in LIVE (git node not deployed) ===")
if not missing:
    print("  (none)")
for nid, src, t, nm in missing:
    print("  %s  [%s]  type=%s name=%s" % (nid, src, t, nm))

print("\n=== MISMATCH (git != live, non-cosmetic) ===")
if not mismatch:
    print("  (none)")
for nid, src, nm, diffs in mismatch:
    print("  %s  [%s]  name=%s  diff-keys=%s" % (nid, src, nm, diffs))

# nodes present in live but NOT in git (e.g. groups added by audit, tabs)
extra = [nid for nid in live_by_id if nid not in git_by_id]
print("\n=== EXTRA in LIVE not in git (count=%d) ===" % len(extra))
types = {}
for nid in extra:
    t = live_by_id[nid].get("type", "?")
    types[t] = types.get(t, 0) + 1
print(" ", types)
