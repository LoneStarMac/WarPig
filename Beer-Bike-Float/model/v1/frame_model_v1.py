"""
Parade float space-frame model  -  perforated square steel tube (Telespar-style)
=================================================================================
Units: inches, pounds, psi.   Axes: X across (width), Y along length (rear=0 -> front), Z up.
Z = 0 is the top of the base rails (where the casters bolt on), ~16-19 in above the road.

Edit the PARAMETERS block, run:  python3 frame_model.py
Writes results.json (for the 3D viewer), cutlist.csv, frame.dxf, frame.FCMacro
"""
import json, math, csv, itertools, sys
from Pynite import FEModel3D

# ----------------------------------------------------------------- PARAMETERS
W      = 96.0      # overall width at the widest point
H      = 96.0      # overall height of the octagon
L      = 96.0      # body length (rear face to front rib)
FLAT   = 55.0      # width of the bottom flat / top opening / vertical sides
RIBS   = [0.0, 32.0, 64.0, 96.0]   # Y stations of the octagon ribs
L_NOSE = 36.0      # nose cone length beyond the front rib   (ASSUMED - not given)
NOSE_W, NOSE_H = 30.0, 18.0        # nose tip panel
NOSE_ZC = H/2                      # nose tip panel centred at mid-height   (ASSUMED)
DECK_LO_Y = (0, 96)                # lower deck covers the whole body
DECKS_HI  = [(0, 32), (64, 96)]    # two upper decks (rear, front); centre open
JOIST_X   = [-24.0, 0.0, 24.0]     # deck joist lines
DOOR_HALF = 12.0                   # rear door half-width (door between the jambs)
CASTER_Y  = (0.0, 96.0)            # casters under the base rails at these stations
LIFT_CASTER = ( FLAT/2, 0.0)       # (x, y) of caster removed in the "one wheel in a pothole" case

PEOPLE_LOWER = 6                   # people on the lower deck
PEOPLE_UPPER = 3                   # people on EACH upper deck
PERSON_LB    = 200.0
POINT_PERSON = 300.0               # one heavy person sitting at the worst spot (centre of the inner edge of a top deck)
SKIN_PSF     = 3.0                 # 3/8" ply + paint + decorations
DECK_PSF     = 2.3                 # 3/4" ply
SHOCK        = 2.0                 # road-shock dynamic factor on D+L
SWAY_G       = 0.30                # lateral acceleration (turning / crown of road / crowd leaning)
TOW_FRACTION = 0.15                # tow jerk per eye, as a fraction of total weight (2 eyes => 0.30 W total)

FY = 50_000.0      # psi, Telespar: ASTM A1011 Gr 50 (60 ksi avg after forming)
FU = 65_000.0
E, G = 29.0e6, 11.2e6

# Telespar perforated square tube, 12 ga (0.105").  A, I, S, r from the Unistrut datasheet; J estimated.
SECTIONS = {
    '1.75x12': dict(A=0.485, I=0.231, S=0.264, r=0.690, J=0.35, wpf=2.060, size=1.75),
    '2.00x12': dict(A=0.590, I=0.372, S=0.372, r=0.794, J=0.56, wpf=2.416, size=2.00),
    '2.25x12': dict(A=0.695, I=0.561, S=0.499, r=0.898, J=0.84, wpf=2.773, size=2.25),
    '2.50x12': dict(A=0.803, I=0.804, S=0.643, r=1.001, J=1.21, wpf=3.141, size=2.50),
}
DEFAULT_SEC = '2.00x12'
# Per-group section overrides (edit these after looking at the utilisation report)
GROUP_SEC = {
    # primary: 2" (ribs, stringers, deck beams)  - secondary: 1-3/4" (fits inside 2" for sleeve stubs)
    'face_diag': '1.75x12', 'vbrace_lo': '1.75x12', 'vbrace_hi': '1.75x12', 'door_diag': '1.75x12',
    'xbrace_front': '1.75x12', 'joist_lo': '1.75x12', 'joist_hi': '1.75x12',
    'nose_stringer': '1.75x12', 'nose_rim': '1.75x12', 'door_jamb': '1.75x12',
}
# Joint model. Bolted lap joints with 7/16" holes and 3/8" bolts rotate freely until the slop takes up, so nothing
# secondary is allowed to carry moment: braces, joists and nose stringers are pinned at both ends; continuous sticks
# (deck beams, stringers, lower joists) are pinned where they END on another member. Octagon rib corners stay rigid
# (the ribs are triangulated, so this only affects local bending, not stability). Front X-brace stays continuous.
PIN_BOTH       = {'face_diag', 'vbrace_lo', 'vbrace_hi', 'door_diag', 'joist_hi', 'nose_stringer'}
PIN_CHAIN_ENDS = {'deck_lo_chord', 'deck_hi_chord', 'stringer', 'joist_lo'}
UPPER_INNER_BEAM_SEC = '2.50x12'   # the two 96" beams on the inner edge of the top decks have no mid-span support

# ----------------------------------------------------------------- GEOMETRY HELPERS
C   = (W - FLAT) / 2          # chamfer = 20.5
Z_LO = C                      # lower deck ring  (vertex ring)
Z_HI = H - C                  # upper deck ring  (vertex ring)
Y_TIP = L + L_NOSE

def octagon_xz():
    """8 vertices (x, z) starting bottom-left, counter-clockwise looking from the rear."""
    f = FLAT/2
    return {
        'V0': (-f, 0.0), 'V1': (f, 0.0),
        'V2': (W/2, Z_LO), 'V3': (W/2, Z_HI),
        'V4': (f, H), 'V5': (-f, H),
        'V6': (-W/2, Z_HI), 'V7': (-W/2, Z_LO),
    }

class Frame:
    def __init__(self):
        self.m = FEModel3D()
        self.m.add_material('steel', E, G, 0.3, 0.0, FY)   # rho=0: self weight applied explicitly from lb/ft
        for name, s in SECTIONS.items():
            self.m.add_section(name, s['A'], s['I'], s['I'], s['J'])
        self.nodes = {}          # name -> (x,y,z)
        self.members = []        # dicts with metadata
        self._mid = itertools.count(1)

    # -- nodes
    def node(self, x, y, z):
        key = f"N_{x:+.2f}_{y:+.2f}_{z:+.2f}"
        if key not in self.nodes:
            self.m.add_node(key, x, y, z)
            self.nodes[key] = (x, y, z)
        return key

    # -- members (optionally split through intermediate nodes)
    def member(self, a, b, group, sec=None):
        sec = sec or GROUP_SEC.get(group, DEFAULT_SEC)
        name = f"M{next(self._mid):03d}_{group}"
        self.m.add_member(name, a, b, 'steel', sec)
        if group in PIN_BOTH:
            self.m.def_releases(name, Ryi=True, Rzi=True, Ryj=True, Rzj=True)
        (x1,y1,z1), (x2,y2,z2) = self.nodes[a], self.nodes[b]
        Lm = math.dist((x1,y1,z1), (x2,y2,z2))
        self.members.append(dict(name=name, i=a, j=b, group=group, sec=sec, L=Lm))
        # self weight, case D
        w = SECTIONS[sec]['wpf'] / 12.0
        self.m.add_member_dist_load(name, 'FZ', -w, -w, case='D')
        self._lateral_from_dist(name, w, 'D')
        return name

    def chain(self, pts, group, sec=None):
        """Members through a list of (x,y,z) points in order."""
        names = []
        ns = [self.node(*p) for p in pts]
        for a, b in zip(ns[:-1], ns[1:]):
            names.append(self.member(a, b, group, sec))
        if group in PIN_CHAIN_ENDS:
            self.m.def_releases(names[0], Ryi=True, Rzi=True)
            self.m.def_releases(names[-1], Ryj=True, Rzj=True)
        return names

    # -- loads: every gravity load also generates the matching lateral (sway/jerk) load cases
    def _lateral_from_dist(self, name, w, case):
        f = SWAY_G * w
        self.m.add_member_dist_load(name, 'FX', f, f, case='EX_' + case)
        self.m.add_member_dist_load(name, 'FY', -f, -f, case='EY_' + case)

    def dist(self, name, w_lb_per_in, case):
        self.m.add_member_dist_load(name, 'FZ', -w_lb_per_in, -w_lb_per_in, case=case)
        self._lateral_from_dist(name, w_lb_per_in, case)

    def pt(self, node, P, case):
        self.m.add_node_load(node, 'FZ', -P, case=case)
        self.m.add_node_load(node, 'FX', SWAY_G*P, case='EX_' + case)
        self.m.add_node_load(node, 'FY', -SWAY_G*P, case='EY_' + case)


def build(lift_caster=None):
    F = Frame()
    V = octagon_xz()
    f = FLAT/2
    joist_x_lo = [-W/2] + JOIST_X + [W/2]      # lower chord nodes: -48, -24, 0, 24, 48 (+/-12 at the rear for door jambs)

    # ----- RIBS
    for y in RIBS:
        p = lambda k: (V[k][0], y, V[k][1])
        rear  = (y == RIBS[0]);  front = (y == RIBS[-1]);  end = rear or front
        F.chain([p('V0'), p('V1')], 'rib_base')
        F.chain([p('V1'), p('V2')], 'rib_chamfer_lo'); F.chain([p('V7'), p('V0')], 'rib_chamfer_lo')
        F.chain([p('V2'), p('V3')], 'rib_post');       F.chain([p('V6'), p('V7')], 'rib_post')
        F.chain([p('V3'), p('V4')], 'rib_chamfer_hi'); F.chain([p('V5'), p('V6')], 'rib_chamfer_hi')
        F.chain([p('V4'), p('V5')], 'rib_rim')
        # lower deck chord through joist nodes (and door jamb nodes at the rear)
        xs = sorted(set(joist_x_lo + ([-DOOR_HALF, DOOR_HALF] if rear else [])))
        F.chain([(x, y, Z_LO) for x in xs], 'deck_lo_chord')
        F.chain([p('V0'), (0, y, Z_LO)], 'vbrace_lo'); F.chain([p('V1'), (0, y, Z_LO)], 'vbrace_lo')
        # upper deck chord
        xs_hi = sorted(set(joist_x_lo + ([-DOOR_HALF, DOOR_HALF] if rear else [])))
        F.chain([(x, y, Z_HI) for x in xs_hi], 'deck_hi_chord', sec=None if end else UPPER_INNER_BEAM_SEC)
        if end:
            F.chain([p('V4'), (0, y, Z_HI)], 'vbrace_hi'); F.chain([p('V5'), (0, y, Z_HI)], 'vbrace_hi')
        if rear:   # door jambs + diagonals outboard of the door
            for s in (-1, 1):
                F.chain([(s*DOOR_HALF, y, Z_LO), (s*DOOR_HALF, y, Z_HI)], 'door_jamb')
                F.chain([(s*W/2, y, Z_LO), (s*DOOR_HALF, y, Z_HI)], 'door_diag')
        if front:  # X-brace in the front wall (inside the nose)
            F.chain([p('V7'), (0, y, H/2), p('V3')], 'xbrace_front')
            F.chain([p('V2'), (0, y, H/2), p('V6')], 'xbrace_front')

    # ----- LONGITUDINAL STRINGERS at the 8 vertices
    for k, (x, z) in V.items():
        F.chain([(x, y, z) for y in RIBS], 'stringer')

    # ----- FACE DIAGONALS  (single diagonal per bay, alternating)  - top is open, no diagonals there
    faces = [('V0','V1'), ('V1','V2'), ('V2','V3'), ('V3','V4'), ('V5','V6'), ('V6','V7'), ('V7','V0')]
    for fi, (a, b) in enumerate(faces):
        for bi, (y1, y2) in enumerate(zip(RIBS[:-1], RIBS[1:])):
            if (fi + bi) % 2 == 0:
                F.chain([(V[a][0], y1, V[a][1]), (V[b][0], y2, V[b][1])], 'face_diag')
            else:
                F.chain([(V[b][0], y1, V[b][1]), (V[a][0], y2, V[a][1])], 'face_diag')

    # ----- DECK JOISTS
    for x in JOIST_X:
        F.chain([(x, y, Z_LO) for y in RIBS], 'joist_lo')
    for (ya, yb) in DECKS_HI:
        for x in JOIST_X:
            F.chain([(x, ya, Z_HI), (x, yb, Z_HI)], 'joist_hi')

    # ----- NOSE
    nw, nh = NOSE_W/2, NOSE_H/2
    N0 = (-nw, Y_TIP, NOSE_ZC-nh); N1 = (nw, Y_TIP, NOSE_ZC-nh); N2 = (nw, Y_TIP, NOSE_ZC+nh); N3 = (-nw, Y_TIP, NOSE_ZC+nh)
    F.chain([N0, N1, N2, N3, N0], 'nose_rim')
    yf = RIBS[-1]
    for k, n in [('V0',N0), ('V1',N1), ('V2',N1), ('V3',N2), ('V4',N2), ('V5',N3), ('V6',N3), ('V7',N0)]:
        F.chain([(V[k][0], yf, V[k][1]), n], 'nose_stringer')

    # ----- SUPPORTS (casters)  - pinned.  Horizontal restraint = caster friction / rolling resistance.
    casters = [(sx*f, y, 0.0) for y in CASTER_Y for sx in (-1, 1)]
    for (x, y, z) in casters:
        if lift_caster and abs(x-lift_caster[0]) < 1e-6 and abs(y-lift_caster[1]) < 1e-6:
            continue
        F.m.def_support(F.node(x, y, z), True, True, True, False, False, False)

    # ----- LOADS
    by_group = lambda g: [mm for mm in F.members if mm['group'] == g]
    def stringers_at(k, ybays=None):
        x, z = V[k]
        out = []
        for mm in by_group('stringer'):
            (x1,y1,z1), (x2,y2,z2) = F.nodes[mm['i']], F.nodes[mm['j']]
            if abs(x1-x) < 1e-6 and abs(z1-z) < 1e-6:
                if ybays is None or any(min(y1,y2) >= a-1e-6 and max(y1,y2) <= b+1e-6 for a, b in ybays):
                    out.append(mm['name'])
        return out

    # skin + decoration on the body faces -> tributary strips on the vertex stringers
    trib = {'V0': f + C/2, 'V1': f + C/2, 'V2': C/2 + (Z_HI-Z_LO)/2, 'V7': C/2 + (Z_HI-Z_LO)/2,
            'V3': (Z_HI-Z_LO)/2 + C/2, 'V6': (Z_HI-Z_LO)/2 + C/2, 'V4': C/2, 'V5': C/2}
    # chamfer faces are 29" long for a 20.5" rise; use true face widths
    cham = math.hypot(C, C)
    trib = {'V0': f/2 + cham/2, 'V1': f/2 + cham/2, 'V2': cham/2 + (Z_HI-Z_LO)/2, 'V7': cham/2 + (Z_HI-Z_LO)/2,
            'V3': (Z_HI-Z_LO)/2 + cham/2, 'V6': (Z_HI-Z_LO)/2 + cham/2, 'V4': cham/2, 'V5': cham/2}
    for k, t in trib.items():
        for nm in stringers_at(k):
            F.dist(nm, SKIN_PSF * t / 144.0, 'D')
    # rear face skin -> rear rib vertices;  nose skin -> nose corners + front rib vertices
    rear_area = (W*H - 2*C*C) / 144.0
    for k in V:
        F.pt(F.node(V[k][0], RIBS[0], V[k][1]), SKIN_PSF*rear_area/8, 'D')
    nose_area = 0.5 * (W*H - 2*C*C + NOSE_W*NOSE_H) / 144.0 * 1.15   # rough frustum surface
    for n in (N0, N1, N2, N3):
        F.pt(F.node(*n), SKIN_PSF*nose_area/12, 'D')
    for k in V:
        F.pt(F.node(V[k][0], RIBS[-1], V[k][1]), SKIN_PSF*nose_area/12, 'D')

    # decks: ply dead load + people, on joists (24" tributary) and deck-edge stringers (12")
    jt = (JOIST_X[1]-JOIST_X[0])          # 24"
    lo_area = W * L / 144.0
    lo_live_psf = PEOPLE_LOWER * PERSON_LB / lo_area
    for mm in by_group('joist_lo'):
        F.dist(mm['name'], DECK_PSF*jt/144, 'D'); F.dist(mm['name'], lo_live_psf*jt/144, 'L')
    for k in ('V2', 'V7'):
        for nm in stringers_at(k):
            F.dist(nm, DECK_PSF*(jt/2)/144, 'D'); F.dist(nm, lo_live_psf*(jt/2)/144, 'L')
    hi_area = W * (DECKS_HI[0][1]-DECKS_HI[0][0]) / 144.0
    hi_live_psf = PEOPLE_UPPER * PERSON_LB / hi_area
    for mm in by_group('joist_hi'):
        F.dist(mm['name'], DECK_PSF*jt/144, 'D'); F.dist(mm['name'], hi_live_psf*jt/144, 'L')
    for k in ('V3', 'V6'):
        for nm in stringers_at(k, DECKS_HI):
            F.dist(nm, DECK_PSF*(jt/2)/144, 'D'); F.dist(nm, hi_live_psf*(jt/2)/144, 'L')
    # one heavy person sitting at the centre of the inner edge of each upper deck
    F.pt(F.node(0, DECKS_HI[0][1], Z_HI), POINT_PERSON, 'L')
    F.pt(F.node(0, DECKS_HI[1][0], Z_HI), POINT_PERSON, 'L')

    # tow eyes at the two front base corners: rope ~20 deg up
    tot_w = total_gravity(F)
    T = TOW_FRACTION * tot_w
    for sx in (-1, 1):
        n = F.node(sx*f, RIBS[-1], 0.0)
        F.m.add_node_load(n, 'FY', T*math.cos(math.radians(20)), case='T')
        F.m.add_node_load(n, 'FZ', T*math.sin(math.radians(20)), case='T')

    # ----- COMBOS
    F.m.add_load_combo('Static', {'D': 1, 'L': 1})
    F.m.add_load_combo('Shock',  {'D': SHOCK, 'L': SHOCK})
    F.m.add_load_combo('Sway',   {'D': 1, 'L': 1, 'EX_D': 1, 'EX_L': 1})
    F.m.add_load_combo('Tow',    {'D': 1, 'L': 1, 'EY_D': 1, 'EY_L': 1, 'T': 1})
    F.m.add_load_combo('DeadOnly', {'D': 1})
    F.total_weight = tot_w
    return F


def total_gravity(F):
    """Sum of all -FZ loads in cases D and L (before T is added)."""
    tot = 0.0
    for mname, mem in F.m.members.items():
        for dl in mem.DistLoads:
            direction, w1, w2, x1, x2, case = dl[:6]
            if direction == 'FZ' and case in ('D', 'L'):
                Lm = mem.L()
                a = 0.0 if x1 is None else x1
                b = Lm if x2 is None else x2
                tot += -(w1 + w2)/2 * (b - a)
    for nname, nd in F.m.nodes.items():
        for (direction, P, case) in nd.NodeLoads:
            if direction == 'FZ' and case in ('D', 'L'):
                tot += -P
    return tot


# ----------------------------------------------------------------- CHECKS
def aisc_fcr(KL_r):
    Fe = math.pi**2 * E / KL_r**2
    lim = 4.71 * math.sqrt(E / FY)
    return (0.658 ** (FY/Fe)) * FY if KL_r <= lim else 0.877 * Fe

def check(F, combos, tag=''):
    """Per member, per combo: stresses, utilisation (yield + buckling interaction), end forces for joints."""
    res = {}
    for mm in F.members:
        mem = F.m.members[mm['name']]
        s = SECTIONS[mm['sec']]
        KL_r = mm['L'] / s['r']
        Fcr = aisc_fcr(KL_r)
        r = {}
        for cb in combos:
            Pmax, Pmin = mem.max_axial(cb), mem.min_axial(cb)
            P_c = max(0.0, -Pmin)                      # compression (PyNite: tension +)
            P_t = max(0.0, Pmax)
            Mz = max(abs(mem.max_moment('Mz', cb)), abs(mem.min_moment('Mz', cb)))
            My = max(abs(mem.max_moment('My', cb)), abs(mem.min_moment('My', cb)))
            Vy = max(abs(mem.max_shear('Fy', cb)), abs(mem.min_shear('Fy', cb)))
            Vz = max(abs(mem.max_shear('Fz', cb)), abs(mem.min_shear('Fz', cb)))
            sig_b = (Mz + My) / s['S']
            sig_a = max(P_c, P_t) / s['A']
            # capacities: Shock combo already carries a 2x factor -> compare to nominal; others -> ASD (/1.67)
            omega = 1.0 if cb == 'Shock' else 1.67
            u_yield = (sig_a + sig_b) / (FY / omega)
            u_buck  = P_c / (Fcr * s['A'] / omega) + sig_b / (FY / omega)
            # deflection relative to the member chord
            d = max(abs(mem.max_deflection('dy', cb)), abs(mem.min_deflection('dy', cb)),
                    abs(mem.max_deflection('dz', cb)), abs(mem.min_deflection('dz', cb)))
            # end forces for the joints
            V_end = math.hypot(Vy, Vz)
            joint = math.hypot(V_end, max(P_c, P_t))
            r[cb] = dict(P=round(Pmax if P_t >= P_c else Pmin, 1), M=round(Mz+My, 1), sig_ksi=round((sig_a+sig_b)/1000, 2),
                         u_yield=round(u_yield, 3), u_buck=round(u_buck, 3), u=round(max(u_yield, u_buck), 3),
                         defl=round(d, 3), joint_lb=round(joint, 1), V=round(V_end, 1))
        r['KL_r'] = round(KL_r, 1); r['Fcr_ksi'] = round(Fcr/1000, 1)
        res[mm['name']] = r
    return res


def reactions(F, combos):
    out = {}
    for nname, nd in F.m.nodes.items():
        if nd.support_DZ:
            out[nname] = {cb: dict(FX=round(nd.RxnFX[cb],1), FY=round(nd.RxnFY[cb],1), FZ=round(nd.RxnFZ[cb],1)) for cb in combos}
    return out


def node_disp(F, combos):
    out = {}
    for nname, nd in F.m.nodes.items():
        out[nname] = {cb: (round(nd.DX[cb],3), round(nd.DY[cb],3), round(nd.DZ[cb],3)) for cb in combos}
    return out


# ----------------------------------------------------------------- EXPORTS
def write_dxf(F, path):
    import ezdxf
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    colors = {}
    for i, g in enumerate(sorted({m['group'] for m in F.members})):
        doc.layers.add(g, color=(i % 7) + 1)
    for mm in F.members:
        msp.add_line(F.nodes[mm['i']], F.nodes[mm['j']], dxfattribs={'layer': mm['group']})
    doc.saveas(path)


def write_fcmacro(F, path):
    """FreeCAD macro: one Part::Line per member, grouped by member group, plus a compound 'Frame'."""
    lines = ['import FreeCAD, Part', 'doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("FloatFrame")', 'groups = {}']
    for mm in F.members:
        (x1,y1,z1), (x2,y2,z2) = F.nodes[mm['i']], F.nodes[mm['j']]
        # FreeCAD likes mm; keep inches here (set document units to inches) - multiply by 25.4 if you prefer mm
        lines.append(f'groups.setdefault("{mm["group"]}", []).append(Part.LineSegment(FreeCAD.Vector({x1},{y1},{z1}), FreeCAD.Vector({x2},{y2},{z2})).toShape())')
    lines += [
        'allshapes = []',
        'for g, shapes in groups.items():',
        '    obj = doc.addObject("Part::Feature", g)',
        '    obj.Shape = Part.makeCompound(shapes)',
        '    allshapes += shapes',
        'frame = doc.addObject("Part::Feature", "Frame_all_members")',
        'frame.Shape = Part.makeCompound(allshapes)',
        'doc.recompute()',
        'FreeCAD.Console.PrintMessage("Float frame imported: %d members (inches)\\n" % len(allshapes))',
    ]
    open(path, 'w').write('\n'.join(lines))


def write_cutlist(F, path):
    rows = {}
    for mm in F.members:
        key = (mm['group'], mm['sec'], round(mm['L'], 1))
        rows[key] = rows.get(key, 0) + 1
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['group', 'section', 'length_in', 'qty', 'total_ft', 'total_lb'])
        tot_ft = tot_lb = 0
        for (g, s, Lm), q in sorted(rows.items()):
            ft = Lm*q/12; lb = ft*SECTIONS[s]['wpf']
            tot_ft += ft; tot_lb += lb
            w.writerow([g, s, Lm, q, round(ft, 1), round(lb, 1)])
        w.writerow(['TOTAL', '', '', sum(rows.values()), round(tot_ft, 1), round(tot_lb, 1)])
    return tot_ft, tot_lb


# ----------------------------------------------------------------- MAIN
if __name__ == '__main__':
    combos = ['Static', 'Shock', 'Sway', 'Tow']
    F = build()
    F.m.analyze(check_statics=True)
    res = check(F, combos)
    rx = reactions(F, combos)
    disp = node_disp(F, combos)

    # one caster lifted (uneven ground): same loads, 3 supports
    F2 = build(lift_caster=LIFT_CASTER)
    F2.m.analyze(check_statics=True)
    res2 = check(F2, ['Static'])
    for mm in F.members:
        res[mm['name']]['Lifted'] = res2[mm['name']]['Static']
    rx2 = reactions(F2, ['Static'])
    disp2 = node_disp(F2, ['Static'])
    for n in disp: disp[n]['Lifted'] = disp2[n]['Static']
    for n in rx:
        rx[n]['Lifted'] = rx2.get(n, {}).get('Static', dict(FX=0, FY=0, FZ=0))
    combos_all = combos + ['Lifted']

    tot_ft, tot_lb = write_cutlist(F, 'cutlist.csv')
    write_dxf(F, 'frame.dxf')
    write_fcmacro(F, 'frame.FCMacro')

    out = dict(
        params=dict(W=W, H=H, L=L, FLAT=FLAT, RIBS=RIBS, L_NOSE=L_NOSE, NOSE_W=NOSE_W, NOSE_H=NOSE_H, Z_LO=Z_LO, Z_HI=Z_HI,
                    PEOPLE_LOWER=PEOPLE_LOWER, PEOPLE_UPPER=PEOPLE_UPPER, PERSON_LB=PERSON_LB, SKIN_PSF=SKIN_PSF, DECK_PSF=DECK_PSF,
                    SHOCK=SHOCK, SWAY_G=SWAY_G, TOW_FRACTION=TOW_FRACTION, FY=FY, total_weight_lb=round(F.total_weight, 0),
                    steel_ft=round(tot_ft, 0), steel_lb=round(tot_lb, 0), sections=SECTIONS, default_sec=DEFAULT_SEC, group_sec=GROUP_SEC),
        nodes=F.nodes, members=F.members, results=res, reactions=rx, disp=disp, combos=combos_all)
    json.dump(out, open('results.json', 'w'))

    # ---- console summary
    print(f"\nTotal gravity load (D+L): {F.total_weight:,.0f} lb   steel: {tot_ft:.0f} ft, {tot_lb:.0f} lb   members: {len(F.members)}  nodes: {len(F.nodes)}")
    for cb in combos_all:
        worst = sorted(res.items(), key=lambda kv: -kv[1][cb]['u'])[:6]
        print(f"\n== {cb}: worst members (u = max(yield, buckling) utilisation)")
        for name, r in worst:
            print(f"  {name:28s} {r[cb]['u']:5.2f}  sig={r[cb]['sig_ksi']:5.1f} ksi  P={r[cb]['P']:8.0f} lb  M={r[cb]['M']:8.0f} in-lb  defl={r[cb]['defl']:.3f} in  KL/r={r['KL_r']}")
    print("\n== Caster reactions (FZ, lb)")
    for n, r in rx.items():
        print(f"  {n:28s} " + "  ".join(f"{cb}:{r[cb]['FZ']:7.0f}" for cb in combos_all))
    print("\n== Max joint force (lb) by group, Shock combo")
    for g in sorted({m['group'] for m in F.members}):
        j = max(res[m['name']]['Shock']['joint_lb'] for m in F.members if m['group'] == g)
        u = max(res[m['name']]['Shock']['u'] for m in F.members if m['group'] == g)
        print(f"  {g:16s} joint={j:7.0f}   u_shock={u:.2f}")
