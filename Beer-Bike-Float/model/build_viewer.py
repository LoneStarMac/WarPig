"""Builds the 3D results viewer from docs/exports/results.json.
   python model/build_viewer.py               -> docs/viewer_fragment.html (artifact-style fragment, no <html> skeleton)
   python model/build_viewer.py --standalone  -> docs/index.html (full page for GitHub Pages, with a downloads bar)
"""
import json, math, re, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
EXPORTS = os.path.join(ROOT, 'docs', 'exports')
d = json.load(open(os.path.join(EXPORTS, 'results.json')))
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

# ---------- joints: distinct sticks per node (a continuous stick passing through counts once)
stick_of = {m['name']: find(m['name']) for m in d['members']}
node_sticks = defaultdict(set)
for m in d['members']:
    for n in (m['i'], m['j']): node_sticks[n].add((stick_of[m['name']], m['group']))
joints = []
for n, st in node_sticks.items():
    groups = sorted(g for _, g in st)
    joints.append(dict(node=n, xyz=d['nodes'][n], n=len(st), groups=groups))
joints.sort(key=lambda r: (-r['n'], r['xyz'][1], r['xyz'][0]))
valence_hist = defaultdict(int)
for r in joints: valence_hist[r['n']] += 1

# ---------- summary
summary = {}
for c in d['combos']:
    worst = max(d['members'], key=lambda m: d['results'][m['name']][c]['u'])
    r = d['results'][worst['name']][c]
    mxd = max((math.hypot(*v[c]), n) for n, v in d['disp'].items())
    cast = max(abs(v[c]['FZ']) for v in d['reactions'].values())
    summary[c] = dict(u=r['u'], member=worst['name'], group=worst['group'], sig=r['sig_ksi'], defl=round(mxd[0], 2), caster=round(cast))

payload = dict(params=P, labels=d['labels'], roles=d['roles'], role_order=d['role_order'], nodes=d['nodes'], members=d['members'], results=d['results'], reactions=d['reactions'],
               disp=d['disp'], combos=d['combos'], sticks=stick_list, stock=stock, summary=summary, joints=joints, valence_hist=dict(valence_hist))

html = open(os.path.join(HERE, 'viewer_template.html')).read()
html = html.replace('/*__DATA__*/', json.dumps(payload))
if '--standalone' in sys.argv:
    downloads = '''
  <nav class="downloads" aria-label="Downloads"><span class="eyebrow">Files</span>
    <a href="exports/frame.FCMacro" download>FreeCAD macro</a><a href="exports/frame.dxf" download>DXF wireframe</a>
    <a href="exports/cutlist.csv" download>Cut list CSV</a><a href="exports/results.json" download>Results JSON</a>
    <a href="https://github.com/__REPO__/blob/main/__DESIGN__/model/frame_model.py">Edit the model on GitHub</a></nav>'''
    html = html.replace('<main class="wrap">\n  <section class="stats" id="stats" aria-label="Summary"></section>',
                        '<main class="wrap">\n  <section class="stats" id="stats" aria-label="Summary"></section>' + downloads)
    html = html.replace('</style>', '''.downloads { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; font-size: 13px; }
.downloads a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; }
.downloads a:hover, .downloads a:focus-visible { border-bottom-color: var(--accent); outline: none; }
</style>''', 1)
    repo = os.environ.get('GITHUB_REPOSITORY', 'LoneStarMac/WarPig')
    html = html.replace('__REPO__', repo).replace('__DESIGN__', os.path.basename(ROOT))
    head, body = html.split('<header class="top">', 1)      # title, font links and <style> go in <head>; the rest is the body
    page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<meta name="description" content="Structural check of a perforated-steel-tube parade float frame: 3D viewer, cut list, joints, assumptions.">\n'
            + head + '</head>\n<body>\n<header class="top">' + body + '\n</body>\n</html>\n')
    out = os.path.join(ROOT, 'docs', 'index.html'); open(out, 'w').write(page)
else:
    out = os.path.join(ROOT, 'docs', 'viewer_fragment.html'); open(out, 'w').write(html)
print(os.path.relpath(out, ROOT), len(html)//1024, 'KB')
print(json.dumps(stock, indent=1)); print(json.dumps(summary, indent=1))
