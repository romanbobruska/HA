import json

d = json.load(open('node-red/flows/fve-orchestrator.json', encoding='utf-8'))
groups = {n['id']: n for n in d if n.get('type') == 'group'}
nodes = [n for n in d if n.get('type') not in ('group', 'tab', 'server', 'sqlitedb', 'global-config')]

print('=== GROUPS ===')
for gid, g in groups.items():
    x1 = g['x']
    y1 = g['y']
    x2 = x1 + g.get('w', 0)
    y2 = y1 + g.get('h', 0)
    print(f"  {g['name']:30s} x:{x1}-{x2}, y:{y1}-{y2}")

print()
print('=== NODES ===')
for n in nodes:
    gname = groups.get(n.get('g', ''), {}).get('name', 'NO GROUP')
    nx = n.get('x', 0)
    ny = n.get('y', 0)
    # Check if node is inside its group bbox
    g = groups.get(n.get('g', ''), {})
    if g:
        gx1 = g['x']
        gy1 = g['y']
        gx2 = gx1 + g.get('w', 0)
        gy2 = gy1 + g.get('h', 0)
        inside = (gx1 <= nx <= gx2) and (gy1 <= ny <= gy2)
        flag = '' if inside else ' *** OUT OF BBOX ***'
    else:
        flag = ''
    print(f"  [{gname:25s}] {n.get('name', n.get('type', '')):35s} x:{nx:5d} y:{ny:4d}{flag}")
