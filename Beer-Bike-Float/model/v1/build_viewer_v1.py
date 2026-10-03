"""Builds viewer.html (self-contained 3D results viewer) from results.json."""
import json, math, re
from collections import defaultdict

d = json.load(open('results.json'))
P = d['params']

# ---------- physical stick list: merge collinear segments of the same group
def line_key(m):
    (x1,y1,z1), (x2,y2,z2) = d['nodes'][m['i']], d['nodes'][m['j']]
    v = (x2-x1, y2-y1, z2-z1); L = math.sqrt(sum(c*c for c in v)); u = [c/L for c in v]
    # canonical direction sign
    for c in u:
        if abs(c) > 1e-9:
            if c < 0: u = [-c for c in u]
            break
    # foot of perpendicular from origin
    t = x1*u[0] + y1*u[1] + z1*u[2]
    foot = (round(x1 - t*u[0], 2), round(y1 - t*u[1], 2), round(z1 - t*u[2], 2))
    return (m['group'], m['sec'], tuple(round(c, 4) for c in u), foot)

# union-find: merge members of the same group that are collinear AND share an end node (a continuous stick)
parent = {m['name']: m['name'] for m in d['members']}
def find(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
by_node = defaultdict(list)
for m in d['members']:
    by_node[m['i']].append(m); by_node[m['j']].append(m)
for n, ms in by_node.items():
    for a in ms:
        for b in ms:
            if a is not b and line_key(a) == line_key(b):
                parent[find(a['name'])] = find(b['name'])
sticks = defaultdict(float); stick_meta = {}
for m in d['members']:
    r = find(m['name']); sticks[r] += m['L']; stick_meta[r] = (m['group'], m['sec'])
stick_rows = defaultdict(int)
for r, L in sticks.items():
    g, s = stick_meta[r]; stick_rows[(g, s, round(L, 1))] += 1
stick_list = [dict(group=g, sec=s, L=L, qty=q) for (g, s, L), q in sorted(stick_rows.items())]

# 10-ft stick count by first-fit packing (0.25" kerf)
def pack(lengths, stock=120.0, kerf=0.25):
    bins = []
    for L in sorted(lengths, reverse=True):
        for b in bins:
            if b + L + kerf <= stock:
                bins[bins.index(b)] = b + L + kerf; break
        else:
            bins.append(L)
    return len(bins)
by_sec = defaultdict(list)
for r in stick_list:
    by_sec[r['sec']] += [r['L']] * r['qty']
stock = {s: dict(sticks10=pack(Ls), ft=round(sum(Ls)/12, 1), lb=round(sum(Ls)/12*P['sections'][s]['wpf'], 0)) for s, Ls in by_sec.items()}

# ---------- summary
summary = {}
for c in d['combos']:
    worst = max(d['members'], key=lambda m: d['results'][m['name']][c]['u'])
    r = d['results'][worst['name']][c]
    mxd = max((math.hypot(*v[c]), n) for n, v in d['disp'].items())
    cast = max(abs(v[c]['FZ']) for v in d['reactions'].values())
    summary[c] = dict(u=r['u'], member=worst['name'], group=worst['group'], sig=r['sig_ksi'], defl=round(mxd[0], 2), caster=round(cast))

payload = dict(params=P, nodes=d['nodes'], members=d['members'], results=d['results'], reactions=d['reactions'],
               disp=d['disp'], combos=d['combos'], sticks=stick_list, stock=stock, summary=summary)

html = open('viewer_template_v1.html').read()
html = html.replace('/*__DATA__*/', json.dumps(payload))
open('viewer.html', 'w').write(html)
print('viewer.html', len(html)//1024, 'KB')
print(json.dumps(stock, indent=1)); print(json.dumps(summary, indent=1))
