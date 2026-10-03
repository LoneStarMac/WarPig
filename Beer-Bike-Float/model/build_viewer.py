"""Turns docs/exports/results.json into docs/data.js for the viewer page.
   python model/build_viewer.py            -> docs/data.js  (merged sticks, stock packing, joint census, hardware schedule)
   python model/build_viewer.py <dir>      -> <dir>/data.js from <dir>/results.json (for variant runs)
The page (docs/index.html), its style (docs/viewer.css) and script (docs/viewer.js) are static and hand-edited.
"""
import json, math, re, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
_args = [a for a in sys.argv[1:] if not a.startswith('--')]
EXPORTS = os.path.abspath(_args[0]) if _args else os.path.join(ROOT, 'docs', 'exports')   # optional: an exports dir from a variant run
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

# stock-length packing (0.25" kerf): first-fit and best-fit decreasing, keep the better. Returns the cut pattern per stock piece.
def pack(lengths, stock=120.0, kerf=0.25):
    def run(best_fit):
        bins = []
        for L in sorted(lengths, reverse=True):
            fits = [b for b in bins if sum(b) + kerf*len(b) + L <= stock]
            if fits:
                (min(fits, key=lambda b: stock - sum(b) - kerf*len(b) - L) if best_fit else fits[0]).append(L)
            else: bins.append([L])
        return bins
    bins = min((run(False), run(True)), key=len)
    return [dict(cuts=b, drop=round(stock - sum(b) - kerf*(len(b)-1), 1)) for b in bins]
by_sec = defaultdict(list)
for r in stick_list:
    if r['sec'] != 'cable': by_sec[r['sec']] += [r['L']] * r['qty']
stock = {}
for s, Ls in by_sec.items():
    p10, p20 = pack(Ls, 120.0), pack(Ls, 240.0)
    stock[s] = dict(sticks10=len(p10), sticks20=len(p20), scrap10=round(sum(b['drop'] for b in p10)/12, 1), scrap20=round(sum(b['drop'] for b in p20)/12, 1),
                    pattern10=p10, pattern20=p20, ft=round(sum(Ls)/12, 1), lb=round(sum(Ls)/12*P['sections'][s]['wpf'], 0))
stock = dict(sorted(stock.items(), key=lambda kv: P['sections'][kv[0]]['size']))
cables = [r for r in stick_list if r['sec'] == 'cable']

# ---------- joints: distinct sticks per node (a continuous stick passing through counts once)
stick_of = {m['name']: find(m['name']) for m in d['members']}
node_sticks = defaultdict(set)
for m in d['members']:
    for n in (m['i'], m['j']): node_sticks[n].add((stick_of[m['name']], m['group']))
# per stick: which nodes it passes through vs ends at
stick_nodes = defaultdict(lambda: defaultdict(int))
stick_dir = {}
for m in d['members']:
    sid = stick_of[m['name']]
    stick_nodes[sid][m['i']] += 1; stick_nodes[sid][m['j']] += 1
    (x1, y1, z1), (x2, y2, z2) = d['nodes'][m['i']], d['nodes'][m['j']]
    v = (x2-x1, y2-y1, z2-z1); L = math.sqrt(sum(c*c for c in v)); stick_dir[sid] = tuple(c/L for c in v)
def angle(u, v):
    c = abs(sum(a*b for a, b in zip(u, v))); c = min(1.0, c)
    return math.degrees(math.acos(c))
CONE = lambda g: g in ('nose_stringer', 'tail_stringer', 'side_diag', 'long_brace', 'web_diag', 'vbrace_lo', 'cable')   # flattened-end one-bolt pins, no bracket
joints = []
for n, st in node_sticks.items():
    through = [sid for sid, g in st if stick_nodes[sid][n] >= 2]
    ends = [(sid, g) for sid, g in st if stick_nodes[sid][n] < 2]
    body_ends = [(sid, g) for sid, g in ends if not CONE(g)]
    cone_ends = [(sid, g) for sid, g in ends if CONE(g)]
    groups = sorted(g for _, g in st)
    through.sort(); body_ends.sort(); cone_ends.sort()     # deterministic: node_sticks is a set
    def fit(sid, hsid):
        """(angle to 5 deg, flush?) of ending stick sid against host stick hsid. Flush: the ending member's perpendicular
        component lies along one global axis, so it sits on a face of the host; otherwise it meets an edge (45 degrees
        between two axes, e.g. the chamfer stub on the deck rail)."""
        v, u = stick_dir[sid], stick_dir[hsid]
        a = round(angle(v, u) / 5) * 5
        dot = sum(p*q for p, q in zip(v, u)); w = [p - dot*q for p, q in zip(v, u)]; wl = math.sqrt(sum(c*c for c in w)) or 1
        return a, max(abs(c)/wl for c in w) > 0.95
    rank = lambda af: 0 if af == (90, True) else 1 if af[0] == 45 else 2 if af[0] == 90 else 3
    needs = []                      # one bracket per ending body stick, typed by its angle to its host
    for sid, g in body_ends:
        hosted = bool(through)
        cands = through if hosted else [h for h, _ in body_ends if h != sid]
        if not cands: continue
        best = min(cands, key=lambda h: (rank(fit(sid, h)), h))   # the plainest fit available: flush 90 > 45 > edge 90
        a, flush = fit(sid, best)
        if a == 90: needs.append(('T90' if flush else 'T90e') if hosted else ('C90' if flush else 'C90e'))
        elif a == 45: needs.append('T45' if hosted else 'C45')
        else: needs.append(f'odd{a}')
    needs += ['pin'] * len(cone_ends)
    if len(through) >= 2: needs.append('X90')
    joints.append(dict(node=n, xyz=d['nodes'][n], n=len(st), groups=groups, through=len(through), ends=len(ends), needs=sorted(needs)))
joints.sort(key=lambda r: (-r['n'], r['xyz'][1], r['xyz'][0]))
kinds = defaultdict(int)
for r in joints:
    for k in r['needs']: kinds[k] += 1
patterns = defaultdict(lambda: dict(count=0, examples=set()))
for r in joints:
    if not r['needs']: continue
    key = ' + '.join(f"{r['needs'].count(k)}×{k}" if r['needs'].count(k) > 1 else k for k in dict.fromkeys(r['needs']))
    p = patterns[key]; p['count'] += 1; p['examples'].add(', '.join(dict.fromkeys(r['groups'])))
patterns = sorted((dict(sig=k, count=v['count'], examples=sorted(v['examples'])[:2]) for k, v in patterns.items()), key=lambda r: -r['count'])
valence_hist = defaultdict(int)
for r in joints: valence_hist[r['n']] += 1
# where each valence occurs: the distinct sets of member types, most common first
where_by_n = defaultdict(lambda: defaultdict(int))
for r in joints:
    where_by_n[r['n']][', '.join(dict.fromkeys(d['labels'].get(g, g).split(' (')[0].lower() for g in r['groups']))] += 1
valence_where = {n: [dict(desc=k, count=v) for k, v in sorted(ws.items(), key=lambda kv: -kv[1])] for n, ws in where_by_n.items()}

# ---------- hardware schedule from the census
SIZE = {k: v['size'] for k, v in P['sections'].items()}
sec_of_group = P['group_sec']
def bolt_len(grip):
    return math.ceil((grip + 0.33 + 0.125) / 0.25) * 0.25
plate_bolts = defaultdict(int); pin_bolts = defaultdict(int); cross_bolts = defaultdict(int)
plate_count = defaultdict(int)
T_PLATE = 0.135
for r in joints:
    sizes = [SIZE[sec_of_group[g]] for g in r['groups']]
    host = max(sizes)
    for k in r['needs']:
        if k in ('T90', 'C90'):
            plate_count['TP-90' if k == 'T90' else 'TL-90'] += 2
            for sz in (host, min(sizes)): plate_bolts[bolt_len(sz + 2*T_PLATE)] += 2
        elif k in ('T45', 'C45', 'T90e', 'C90e'):
            plate_count['TP-45'] += 2
            for sz in (host, min(sizes)): plate_bolts[bolt_len(sz + 2*T_PLATE)] += 2
        elif k == 'pin':
            pin_bolts[bolt_len(host + 0.15 + 0.16)] += 1
        elif k == 'X90':
            cross_bolts[bolt_len(sum(sorted(sizes)[-2:]))] += 1
caster_bolts = 4 * len(d['reactions']); tow_bolts = 4
rail_inside = SIZE['2.50x14'] - 2 * 0.075
hardware = dict(plates=dict(plate_count), plate_bolts=dict(plate_bolts), pin_bolts=dict(pin_bolts), cross_bolts=dict(cross_bolts),
                caster_bolts=caster_bolts, tow_bolts=tow_bolts, sleeve_len=round(rail_inside, 2), sleeves=caster_bolts + tow_bolts,
                total_bolts=sum(plate_bolts.values()) + sum(pin_bolts.values()) + sum(cross_bolts.values()) + caster_bolts + tow_bolts,
                cables=sum(r['qty'] for r in cables), cable_ft=round(sum(r['L']*r['qty'] for r in cables)/12 + 1.5*sum(r['qty'] for r in cables), 0))
try:
    plates_spec = json.load(open(os.path.join(EXPORTS, 'plates', 'plates.json')))
except Exception:
    plates_spec = []

# ---------- summary
summary = {}
for c in d['combos']:
    worst = max(d['members'], key=lambda m: d['results'][m['name']][c]['u'])
    r = d['results'][worst['name']][c]
    mxd = max((math.hypot(*v[c]), n) for n, v in d['disp'].items())
    cast = max(abs(v[c]['FZ']) for v in d['reactions'].values())
    summary[c] = dict(u=r['u'], member=worst['name'], group=worst['group'], sig=r['sig_ksi'], defl=round(mxd[0], 2), caster=round(cast))

payload = dict(params=P, labels=d['labels'], roles=d['roles'], role_order=d['role_order'], nodes=d['nodes'], members=d['members'], results=d['results'], reactions=d['reactions'],
               disp=d['disp'], combos=d['combos'], sticks=stick_list, stock=stock, summary=summary, joints=joints, valence_hist=dict(valence_hist), valence_where=valence_where, patterns=patterns, kinds=dict(kinds), hardware=hardware, plates=plates_spec)

# The page itself (docs/index.html), its style (viewer.css) and its script (viewer.js) are static files, edited by hand.
# This script only writes the data they read: docs/data.js, one global.
out = os.path.join(EXPORTS, 'data.js') if _args else os.path.join(ROOT, 'docs', 'data.js')
open(out, 'w').write('window.FLOAT_DATA = ' + json.dumps(payload, separators=(',', ':')) + ';\n')
print(os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, 'KB')
print(json.dumps({s: {k: x[k] for k in ('sticks10', 'sticks20', 'scrap10', 'scrap20', 'ft', 'lb')} for s, x in stock.items()}, indent=1)); print(json.dumps(summary, indent=1))
