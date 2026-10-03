"""
Parade float frame, v2  -  chassis at deck level, open sides, skirt, hatch, tail
=================================================================================
Units: inches, pounds, psi.   Axes: X across, Y along the length (rear body rib = 0, nose forward), Z up.
Z = 0 is the centreline of the 2.5" chassis = the lower deck ring. Ground is 16" (caster) + 1.25" below that.

Edit the PARAMETERS block, then from the repo root:   python model/frame_model.py   [out_dir]
Writes results.json, cutlist.csv, frame.dxf, frame.FCMacro into out_dir (default docs/exports).
Then  python model/build_viewer.py --standalone  rebuilds docs/index.html. CI does both on every push.
"""
import json, math, csv, itertools, os, sys
from Pynite import FEModel3D

# ----------------------------------------------------------------- PARAMETERS
W, H_OCT, L = 96.0, 96.0, 96.0      # octagon width/height (skin outline) and body length
FLAT   = 55.0                       # octagon flats (top opening width)
RIBS   = [0.0, 32.0, 64.0, 96.0]    # rib stations (posts, cross-members)
C      = (W - FLAT) / 2             # 20.5 chamfer
Z_HI   = H_OCT - 2*C                # 55: upper deck ring, above the chassis
Z_RIM  = H_OCT - C                  # 75.5: top rim
CASTER_H, CHASSIS_SZ = 16.0, 2.5    # caster height, chassis tube
GROUND_CLEAR = 6.0                  # skirt bottom above the road (UNDERBODY='skirt')
BELLY_CLEAR  = 10.0                 # belly above the road (UNDERBODY='chamfer'); every inch of belly is an inch less leg showing
UNDERBODY = 'chamfer'               # 'skirt'  : octagon chamfer skirt hanging to GROUND_CLEAR, casters inside it (v2/v3)
                                    # 'legs'   : belly flat at the chassis, each caster in a steel-framed leg box (v4)
                                    # 'chamfer': octagon taper back on the belly down to BELLY_CLEAR; casters in coroplast legs, no steel (v5)
ENTRY     = 'tail'                  # 'side': open side bays for doors, X-braced end walls (v3)
                                    # 'tail': door through the tail, side walls diagonal-braced and hard-skinned
Z_GROUND = -(CASTER_H + CHASSIS_SZ/2)          # -17.25
Z_SKIRT  = {'skirt': Z_GROUND + GROUND_CLEAR, 'chamfer': Z_GROUND + BELLY_CLEAR, 'legs': 0.0}[UNDERBODY]   # belly height; full octagon bottom would be -20.5
X_SKIRT  = W/2 - (0 - Z_SKIRT)                 # 36.75 : chamfer line hits the skirt bottom here; 48 with legs
RAIL_X   = 24.0                     # chassis rails (casters bolt under these)
CASTER_Y = (12.0, 84.0) if UNDERBODY == 'skirt' else (11.0, 83.0)   # caster stations along the rails
LEG_CLEAR = 4.0                     # leg box bottom above the road
Z_LEG    = Z_GROUND + LEG_CLEAR     # -13.25
LEGS = {                            # legs in plan. 'legs': steel boxes (x half-width, y0..y1). 'chamfer': coroplast cylinders of radius r at the caster.
    'rear':  dict(halfw=6.0,  y0=0.0,  y1=22.0, r=11.0),    # rigid caster: 22" round leg
    'front': dict(halfw=13.0, y0=70.0, y1=96.0, r=13.0),    # 16" swivel caster, ~10" swivel radius: 26" round leg
}
LEG_SKIN_LB = 4.0                   # per coroplast leg incl. the rubber hoof seal (4 mm coroplast is ~0.2 psf)
DOOR_HALF = 15.0                    # tail door half-width (ENTRY='tail'): jambs at +/-15, 30" clear
HATCH    = (32.0, 64.0)             # upper-deck hatch between these ribs, X between the joists at +/-24
JOIST_X  = 24.0
L_NOSE, NOSE_W, NOSE_H, NOSE_ZC = 36.0, 30.0, 18.0, (Z_RIM + (-C)) / 2    # snout panel, centred on the octagon (z = 27.5)
L_TAIL, TAIL_W, TAIL_H, TAIL_ZC = (24.0, 48.0, 40.0, (Z_RIM + (-C)) / 2 + 6) if ENTRY == 'side' else (24.0, 40.0, Z_HI, Z_HI / 2)
# tail panel: blunt and a little high with side entry; with tail entry it is a 40 x 55 flap from the chassis to the upper deck, i.e. the door
LIFT_CASTER = (RAIL_X, CASTER_Y[0])             # right-rear wheel off the ground in the Lifted case

PEOPLE_LOWER_PARKED = 4;  PERSON_LB = 200.0    # parked: 4 standing below + one 250 lb person at each hatch edge
EDGE_PERSON = 250.0
MOVING = dict(lower_center=200.0, hatch_edge=250.0)   # in motion: 1 below, 1 sitting at the hatch edge (you said 1; this is 2)
SKIN_PSF, DECK_PSF = 3.0, 2.3
SHOCK, SWAY_G, TOW_FRACTION = 2.0, 0.30, 0.15
PLY_GT_EFF = 15_000.0               # lb/in effective shear rigidity of a 3/4" ply deck screwed ~8" o.c. (APA ~60-80k, cut for fastener slip)
SKIN_GT_EFF = 4_000.0               # lb/in for the 3/8" skin on the upper chamfers, nutserts/bolts ~12" o.c. along every panel edge

FY, FU, E, G = 50_000.0, 65_000.0, 29.0e6, 11.2e6
# 12 ga (0.105") perforated: A, I, S, r, lb/ft from the Unistrut Telespar datasheet (net section at a hole).
SECTIONS = {
    '1.50x12': dict(A=0.380, I=0.129, S=0.172, r=0.582, J=0.19, wpf=1.702, size=1.50, t=0.105),
    '1.75x12': dict(A=0.485, I=0.231, S=0.264, r=0.690, J=0.35, wpf=2.060, size=1.75, t=0.105),
    '2.00x12': dict(A=0.590, I=0.372, S=0.372, r=0.794, J=0.56, wpf=2.416, size=2.00, t=0.105),
    '2.25x12': dict(A=0.695, I=0.561, S=0.499, r=0.898, J=0.84, wpf=2.773, size=2.25, t=0.105),
    '2.50x12': dict(A=0.803, I=0.804, S=0.643, r=1.001, J=1.21, wpf=3.141, size=2.50, t=0.105),
}
def _derive_14ga():
    """14 ga (0.075") perforated tube is sold by the same suppliers but not in that datasheet. Scale each 12 ga entry by
    the gross-section ratio (same holes, thinner wall), which keeps the datasheet's perforation knock-down."""
    out = {}
    for k, s12 in list(SECTIONS.items()):
        b = s12['size']; t12, t14 = 0.105, 0.075
        g = lambda t: (b*b - (b-2*t)**2, (b**4 - (b-2*t)**4)/12)
        A12, I12 = g(t12); A14, I14 = g(t14)
        A = s12['A']*A14/A12; I = s12['I']*I14/I12
        out[f'{b:.2f}x14'] = dict(A=round(A, 3), I=round(I, 3), S=round(s12['S']*I14/I12, 3), r=round(math.sqrt(I/A), 3),
                                 J=round(s12['J']*t14/t12, 2), wpf=round(s12['wpf']*A14/A12, 3), size=b, t=t14)
    SECTIONS.update(out)
_derive_14ga()
SECTIONS_BY_WEIGHT = sorted(SECTIONS, key=lambda k: SECTIONS[k]['wpf'])
# Member families share one tube size so there are few sizes to buy and few joint patterns. The auto-sizer
# (python frame_model.py --optimize) picks the lightest allowed section per family that keeps every member under
# U_TARGET in every load case (strength only: yield and buckling; deflection is reported, not limited).
FAMILIES = {
    'chassis':   dict(groups=['chassis_rail', 'chassis_spine', 'chassis_cross'], min='2.00x14'),
    'upper':     dict(groups=['deck_hi_rail', 'deck_hi_end', 'deck_hi_cross'], min='1.75x14'),
    'posts':     dict(groups=['post', 'deck_lo_edge', 'door_jamb'], min='1.75x14'),
    'rim':       dict(groups=['chamfer_hi', 'rim_cross', 'rim_stringer'], min='1.50x14'),   # handrail: 1.5" minimum for feel
    'joists':    dict(groups=['joist_hi'], min='1.50x14'),
    'brace':     dict(groups=['xbrace_end', 'side_diag'], min='1.50x14'),
    'legs':      dict(groups=['leg_top', 'leg_drop', 'leg_ring'], min='1.50x14'),
    'skirt':     dict(groups=['skirt_stub', 'skirt_bottom', 'skirt_drop', 'skirt_stringer'], min='1.50x14'),
    'cones':     dict(groups=['nose_stringer', 'nose_rim', 'tail_stringer', 'tail_rim'], min='1.50x14'),
}
U_TARGET = 0.85
# v3 sizes, from --optimize with U_TARGET = 0.85. (v2 was 2.5"/2"/1.75" x 12 ga everywhere: 1,016 lb.)
GROUP_SEC = {
    'chassis_rail': '2.50x14', 'chassis_spine': '2.50x14', 'chassis_cross': '2.50x14',
    'deck_hi_rail': '2.00x14', 'deck_hi_end': '2.00x14', 'deck_hi_cross': '2.00x14', 'xbrace_end': '1.50x14',
    'deck_lo_edge': '1.75x14', 'post': '1.75x14', 'chamfer_hi': '1.50x14', 'rim_cross': '1.50x14', 'rim_stringer': '1.50x14',
    'joist_hi': '1.50x14',
    'skirt_stub': '1.50x14', 'skirt_bottom': '1.50x14', 'skirt_drop': '1.50x14', 'skirt_stringer': '1.50x14',
    'leg_top': '1.50x14', 'leg_drop': '1.50x14', 'leg_ring': '1.50x14', 'side_diag': '1.50x14', 'door_jamb': '1.75x14',
    'nose_stringer': '1.50x14', 'nose_rim': '1.50x14', 'tail_stringer': '1.50x14', 'tail_rim': '1.50x14',
}
GROUP_LABEL = {
    'chassis_rail': 'Chassis rail (casters bolt under)', 'chassis_spine': 'Chassis spine', 'chassis_cross': 'Chassis cross-member',
    'deck_lo_edge': 'Lower deck edge stringer', 'post': 'Side post (door jamb)', 'deck_hi_rail': 'Upper deck side rail',
    'deck_hi_end': 'Upper deck end beam', 'deck_hi_cross': 'Upper deck cross beam (hatch edge)', 'joist_hi': 'Upper deck joist',
    'xbrace_end': 'X-brace, nose & tail wall', 'chamfer_hi': 'Upper chamfer stub',
    'rim_cross': 'Top rim cross', 'rim_stringer': 'Top rim stringer', 'skirt_stub': 'Skirt chamfer stub', 'skirt_bottom': 'Skirt bottom cross',
    'skirt_drop': 'Skirt dropper', 'skirt_stringer': 'Skirt stringer', 'nose_stringer': 'Nose stringer', 'nose_rim': 'Snout frame',
    'leg_top': 'Leg box, top ring', 'leg_drop': 'Leg box, corner post', 'leg_ring': 'Leg box, bottom ring',
    'side_diag': 'Side wall diagonal (under skin)', 'door_jamb': 'Tail door jamb',
    'tail_stringer': 'Tail stringer', 'tail_rim': 'Tail frame',
}
ROLE = {
    'chassis_rail': 'Chassis', 'chassis_spine': 'Chassis', 'chassis_cross': 'Chassis', 'deck_lo_edge': 'Chassis',
    'post': 'Posts & rim', 'chamfer_hi': 'Posts & rim', 'rim_cross': 'Posts & rim', 'rim_stringer': 'Posts & rim',
    'deck_hi_rail': 'Upper deck', 'deck_hi_end': 'Upper deck', 'deck_hi_cross': 'Upper deck', 'joist_hi': 'Upper deck',
    'xbrace_end': 'Bracing',
    'skirt_stub': 'Skirt', 'skirt_bottom': 'Skirt', 'skirt_drop': 'Skirt', 'skirt_stringer': 'Skirt',
    'leg_top': 'Legs', 'leg_drop': 'Legs', 'leg_ring': 'Legs', 'side_diag': 'Bracing', 'door_jamb': 'Posts & rim',
    'nose_stringer': 'Nose & tail', 'nose_rim': 'Nose & tail', 'tail_stringer': 'Nose & tail', 'tail_rim': 'Nose & tail',
}
ROLE_ORDER = ['Chassis', 'Posts & rim', 'Upper deck', 'Bracing', 'Legs' if UNDERBODY == 'legs' else 'Skirt', 'Nose & tail']
# Joint model, matched to what perforated tube can actually do: two members crossing at 90 degrees share ONE bolt, so every
# such joint is a pin. Moment exists only inside continuous sticks (and their sleeve splices) and in the chassis grillage,
# which is either welded or squared by the deck ply. Posts are pinned top and bottom; the deck diaphragms and the nose/tail
# pyramids do the racking work. The X-braces are continuous through their crossing (one stick + two halves). Nose/tail
# tip frames are left rigid (4 short pieces, bracketed); everything else, skirt included, is pinned.
PIN_BOTH       = {'post', 'chamfer_hi', 'nose_stringer', 'tail_stringer', 'skirt_stub', 'skirt_drop', 'side_diag', 'door_jamb'}   # leg corner posts stay rigid: the leg box is skinned on 4 sides
PIN_CHAIN_ENDS = {'deck_hi_cross', 'deck_hi_end', 'deck_hi_rail', 'joist_hi', 'rim_stringer', 'rim_cross', 'skirt_stringer', 'skirt_bottom', 'deck_lo_edge', 'xbrace_end', 'leg_top'}


class Frame:
    def __init__(self):
        self.m = FEModel3D()
        self.m.add_material('steel', E, G, 0.3, 0.0, FY)
        self.m.add_material('ply', 1.5e6, 0.6e6, 0.3, 0.0)
        for name, s in SECTIONS.items():
            self.m.add_section(name, s['A'], s['I'], s['I'], s['J'])
        self.nodes, self.members, self.proxies = {}, [], []
        self._mid = itertools.count(1)

    def node(self, x, y, z):
        key = f"N_{x:+.2f}_{y:+.2f}_{z:+.2f}"
        if key not in self.nodes:
            self.m.add_node(key, x, y, z); self.nodes[key] = (x, y, z)
        return key

    def member(self, a, b, group, sec=None):
        sec = sec or GROUP_SEC[group]
        name = f"M{next(self._mid):03d}_{group}"
        self.m.add_member(name, a, b, 'steel', sec)
        if group in PIN_BOTH:
            self.m.def_releases(name, Ryi=True, Rzi=True, Ryj=True, Rzj=True)
        Lm = math.dist(self.nodes[a], self.nodes[b])
        self.members.append(dict(name=name, i=a, j=b, group=group, sec=sec, L=Lm))
        w = SECTIONS[sec]['wpf'] / 12.0
        self.dist(name, w, 'D')
        return name

    def chain(self, pts, group, sec=None):
        ns = [self.node(*p) for p in pts]
        names = [self.member(a, b, group, sec) for a, b in zip(ns[:-1], ns[1:])]
        if group in PIN_CHAIN_ENDS:
            self.m.def_releases(names[0], Ryi=True, Rzi=True)
            self.m.def_releases(names[-1], Ryj=True, Rzj=True)
        return names

    def diaphragm(self, p1, p2, p3, p4, a_len, b_dep, Gt=None):
        """Plywood panel between corners p1..p4 (p1-p2 and p3-p4 across, p1-p4 along Y), modelled as an X of pinned ply-stiffness bars."""
        Ld = math.dist(p1, p3); cos2 = 1 - ((p3[1]-p1[1]) / Ld) ** 2      # component across the panel (perpendicular to Y)
        k = (Gt or PLY_GT_EFF) * b_dep / a_len
        A = k * Ld / (2 * cos2) / 1.5e6
        sec = f'ply_{A:.3f}'
        if sec not in self.m.sections: self.m.add_section(sec, A, 1e-4, 1e-4, 1e-4)
        for (p, q) in ((p1, p3), (p2, p4)):
            name = f"P{next(self._mid):03d}_diaphragm"
            self.m.add_member(name, self.node(*p), self.node(*q), 'ply', sec)
            self.m.def_releases(name, Ryi=True, Rzi=True, Ryj=True, Rzj=True)
            self.proxies.append(dict(name=name, i=self.node(*p), j=self.node(*q)))

    def dist(self, name, w, case):
        self.m.add_member_dist_load(name, 'FZ', -w, -w, case=case)
        self.m.add_member_dist_load(name, 'FX', SWAY_G*w, SWAY_G*w, case='EX_'+case)
        self.m.add_member_dist_load(name, 'FY', -SWAY_G*w, -SWAY_G*w, case='EY_'+case)

    def pt(self, node, P, case):
        self.m.add_node_load(node, 'FZ', -P, case=case)
        self.m.add_node_load(node, 'FX', SWAY_G*P, case='EX_'+case)
        self.m.add_node_load(node, 'FY', -SWAY_G*P, case='EY_'+case)


def build(lift_caster=None):
    F = Frame()
    f = FLAT/2; hw = W/2; rx = RAIL_X; jx = JOIST_X
    xs5 = [-hw, -rx, 0.0, rx, hw]
    cham_hi_len = math.hypot(hw - f, Z_RIM - Z_HI)
    tail_rib, nose_rib = RIBS[0], RIBS[-1]
    rail_ys = sorted(set(RIBS) | set(CASTER_Y) | {L/2})

    # ----- CHASSIS (z = 0): rails, spine, cross-members, deck-edge stringers
    for sx in (-1, 1):
        F.chain([(sx*rx, y, 0.0) for y in rail_ys], 'chassis_rail')
        F.chain([(sx*hw, y, 0.0) for y in RIBS], 'deck_lo_edge')
    F.chain([(0.0, y, 0.0) for y in rail_ys], 'chassis_spine')
    for y in RIBS:
        extra = [x for leg in LEGS.values() if UNDERBODY == 'legs' and y in (leg['y0'], leg['y1']) for sx in (-1, 1) for x in (sx*rx - leg['halfw'], sx*rx + leg['halfw'])]
        if ENTRY == 'tail' and y == tail_rib: extra += [-DOOR_HALF, DOOR_HALF]
        F.chain([(x, y, 0.0) for x in sorted(set(xs5 + extra))], 'chassis_cross')

    # ----- POSTS, UPPER DECK FRAME, HATCH JOISTS
    for y in RIBS:
        for sx in (-1, 1):
            F.chain([(sx*hw, y, 0.0), (sx*hw, y, Z_HI)], 'post')
        end = y in (RIBS[0], RIBS[-1])
        xs_hi = list(xs5)
        if end and not (ENTRY == 'tail' and y == tail_rib): xs_hi += [-(Z_HI - rx), Z_HI - rx]
        if ENTRY == 'tail' and y == tail_rib: xs_hi += [-DOOR_HALF, DOOR_HALF]
        F.chain([(x, y, Z_HI) for x in sorted(set(xs_hi))], 'deck_hi_end' if end else 'deck_hi_cross')
        if end and not (ENTRY == 'tail' and y == tail_rib):
            # 45-degree X-brace: rail crossing at the chassis up to the end beam, rise = run = Z_HI, so the braces cross at 90
            xt = Z_HI - rx          # 31": where the brace lands on the end beam
            F.chain([(-rx, y, 0.0), (0.0, y, rx), (xt, y, Z_HI)], 'xbrace_end')
            F.chain([(rx, y, 0.0), (0.0, y, rx), (-xt, y, Z_HI)], 'xbrace_end')
        if ENTRY == 'tail' and y == tail_rib:   # door jambs from the chassis to the upper deck beam; the beam is the header
            for sx in (-1, 1):
                F.chain([(sx*DOOR_HALF, y, 0.0), (sx*DOOR_HALF, y, Z_HI)], 'door_jamb')
    for sx in (-1, 1):
        F.chain([(sx*hw, y, Z_HI) for y in RIBS], 'deck_hi_rail')
        F.chain([(sx*jx, y, Z_HI) for y in RIBS], 'joist_hi')
    F.chain([(0.0, y, Z_HI) for y in RIBS if y <= HATCH[0]], 'joist_hi')
    F.chain([(0.0, y, Z_HI) for y in RIBS if y >= HATCH[1]], 'joist_hi')

    # ----- SIDE WALL DIAGONALS (tail entry: sides are braced and hard-skinned; one 45-ish diagonal per bay, alternating)
    if ENTRY == 'tail':
        for sx in (-1, 1):
            for bi, (y1, y2) in enumerate(zip(RIBS[:-1], RIBS[1:])):
                a, b = ((y1, 0.0), (y2, Z_HI)) if (bi + (sx > 0)) % 2 == 0 else ((y2, 0.0), (y1, Z_HI))
                F.chain([(sx*hw, a[0], a[1]), (sx*hw, b[0], b[1])], 'side_diag')

    # ----- UPPER CHAMFERS + RIM (handrail level)
    for y in RIBS:
        for sx in (-1, 1):
            F.chain([(sx*hw, y, Z_HI), (sx*f, y, Z_RIM)], 'chamfer_hi')
        F.chain([(-f, y, Z_RIM), (f, y, Z_RIM)], 'rim_cross')
    for sx in (-1, 1):
        F.chain([(sx*f, y, Z_RIM) for y in RIBS], 'rim_stringer')

    # ----- UNDERBODY: skirt (skin framing hanging below the chassis) or legs (a box round each caster)
    if UNDERBODY in ('skirt', 'chamfer'):
        full = UNDERBODY == 'skirt'          # skirt: droppers + centre stringer; chamfer: belly ply spans rib to rib on the crosses alone
        xsk = [-X_SKIRT, -rx, 0.0, rx, X_SKIRT] if full else [-X_SKIRT, X_SKIRT]
        for y in RIBS:
            for sx in (-1, 1):
                F.chain([(sx*hw, y, 0.0), (sx*X_SKIRT, y, Z_SKIRT)], 'skirt_stub')
            F.chain([(x, y, Z_SKIRT) for x in xsk], 'skirt_bottom')
            if full:
                for x in (-rx, 0.0, rx):
                    F.chain([(x, y, 0.0), (x, y, Z_SKIRT)], 'skirt_drop')
        for x in ([-X_SKIRT, 0.0, X_SKIRT] if full else [-X_SKIRT, X_SKIRT]):
            F.chain([(x, y, Z_SKIRT) for y in RIBS], 'skirt_stringer')
        if not full:   # coroplast legs: no steel, just their weight on the rail at the caster
            for y in CASTER_Y:
                for sx in (-1, 1): F.pt(F.node(sx*rx, y, 0.0), LEG_SKIN_LB, 'D')
    else:
        for leg in LEGS.values():
            for sx in (-1, 1):
                xa, xb = sx*rx - leg['halfw'], sx*rx + leg['halfw']; y0, y1 = leg['y0'], leg['y1']
                for y in (y0, y1):            # top ring: cross pieces through the rail (a rib's cross-member already does it)
                    if y not in RIBS: F.chain([(xa, y, 0.0), (sx*rx, y, 0.0), (xb, y, 0.0)], 'leg_top')
                for x in (xa, xb): F.chain([(x, y0, 0.0), (x, y1, 0.0)], 'leg_top')
                for (x, y) in ((xa, y0), (xb, y0), (xa, y1), (xb, y1)): F.chain([(x, y, 0.0), (x, y, Z_LEG)], 'leg_drop')
                F.chain([(xa, y0, Z_LEG), (xb, y0, Z_LEG), (xb, y1, Z_LEG), (xa, y1, Z_LEG), (xa, y0, Z_LEG)], 'leg_ring')

    # ----- NOSE and TAIL cones
    def cone(y0, ytip, wid, hgt, zc, grp):
        nw, nh = wid/2, hgt/2
        T = [(-nw, ytip, zc-nh), (nw, ytip, zc-nh), (nw, ytip, zc+nh), (-nw, ytip, zc+nh)]
        F.chain(T + [T[0]], grp + '_rim')
        lo = [((-X_SKIRT, Z_SKIRT), 0), ((X_SKIRT, Z_SKIRT), 1)] if UNDERBODY != 'legs' else [((-rx, 0.0), 0), ((rx, 0.0), 1)]
        base = lo + [((hw, 0.0), 1), ((hw, Z_HI), 2), ((f, Z_RIM), 2), ((-f, Z_RIM), 3), ((-hw, Z_HI), 3), ((-hw, 0.0), 0)]
        for (x, z), ti in base:
            F.chain([(x, y0, z), T[ti]], grp + '_stringer')
        return T
    NOSE = cone(RIBS[-1], L + L_NOSE, NOSE_W, NOSE_H, NOSE_ZC, 'nose')
    TAIL = cone(RIBS[0], -L_TAIL, TAIL_W, TAIL_H, TAIL_ZC, 'tail')

    # ----- DECK DIAPHRAGMS (plywood, modelled)  lower: full width per bay; upper: full width in end bays, side strips beside the hatch
    for y1, y2 in zip(RIBS[:-1], RIBS[1:]):
        F.diaphragm((-hw, y1, 0.0), (hw, y1, 0.0), (hw, y2, 0.0), (-hw, y2, 0.0), y2-y1, W)
        if y1 >= HATCH[0] and y2 <= HATCH[1]:
            for sx in (-1, 1):
                F.diaphragm((sx*jx, y1, Z_HI), (sx*hw, y1, Z_HI), (sx*hw, y2, Z_HI), (sx*jx, y2, Z_HI), y2-y1, hw-jx)
        else:
            F.diaphragm((-hw, y1, Z_HI), (hw, y1, Z_HI), (hw, y2, Z_HI), (-hw, y2, Z_HI), y2-y1, W)

    # upper chamfer skin panels (3/8" ply on the sloped faces either side of the top opening): light shear panels
    for y1, y2 in zip(RIBS[:-1], RIBS[1:]):
        for sx in (-1, 1):
            F.diaphragm((sx*hw, y1, Z_HI), (sx*f, y1, Z_RIM), (sx*f, y2, Z_RIM), (sx*hw, y2, Z_HI), y2-y1, cham_hi_len, Gt=SKIN_GT_EFF)

    if ENTRY == 'tail':
        for sx in (-1, 1):
            F.diaphragm((sx*DOOR_HALF, tail_rib, 0.0), (sx*hw, tail_rib, 0.0), (sx*hw, tail_rib, Z_HI), (sx*DOOR_HALF, tail_rib, Z_HI), Z_HI, hw - DOOR_HALF, Gt=SKIN_GT_EFF)

    # ----- SUPPORTS: casters under the rails
    for y in CASTER_Y:
        for sx in (-1, 1):
            if lift_caster and abs(sx*rx - lift_caster[0]) < 1e-6 and abs(y - lift_caster[1]) < 1e-6: continue
            F.m.def_support(F.node(sx*rx, y, 0.0), True, True, True, False, False, False)

    # ----- LOADS
    def by_group_name(group):
        return [mm['name'] for mm in F.members if mm['group'] == group]
    def along(group, x, z, ybays=None):
        out = []
        for mm in F.members:
            if mm['group'] != group: continue
            (x1, y1, z1), (x2, y2, z2) = F.nodes[mm['i']], F.nodes[mm['j']]
            if abs(x1-x) < 1e-6 and abs(z1-z) < 1e-6 and abs(x2-x) < 1e-6 and abs(z2-z) < 1e-6:
                if ybays is None or any(min(y1, y2) >= a-1e-6 and max(y1, y2) <= b+1e-6 for a, b in ybays): out.append(mm['name'])
        return out
    # skin on the body: tributary strip widths per lengthwise stringer (true face widths)
    skirt_ch = math.hypot(hw - X_SKIRT, -Z_SKIRT); cham_hi = math.hypot(hw - f, Z_RIM - Z_HI)
    trib = [('deck_lo_edge', -hw, 0.0, skirt_ch/2 + Z_HI/2), ('deck_lo_edge', hw, 0.0, skirt_ch/2 + Z_HI/2),
            ('deck_hi_rail', -hw, Z_HI, Z_HI/2 + cham_hi/2), ('deck_hi_rail', hw, Z_HI, Z_HI/2 + cham_hi/2),
            ('rim_stringer', -f, Z_RIM, cham_hi/2), ('rim_stringer', f, Z_RIM, cham_hi/2)]
    if UNDERBODY == 'skirt':
        trib += [('skirt_stringer', -X_SKIRT, Z_SKIRT, X_SKIRT/2 + skirt_ch/2), ('skirt_stringer', X_SKIRT, Z_SKIRT, X_SKIRT/2 + skirt_ch/2), ('skirt_stringer', 0.0, Z_SKIRT, X_SKIRT)]
    elif UNDERBODY == 'chamfer':   # belly ply spans between the bottom crosses; edge stringers take the chamfer skin
        trib += [('skirt_stringer', -X_SKIRT, Z_SKIRT, skirt_ch/2), ('skirt_stringer', X_SKIRT, Z_SKIRT, skirt_ch/2)]
        for mm in by_group_name('skirt_bottom'):
            F.dist(mm, SKIN_PSF * (RIBS[1]-RIBS[0]) / 144 * (0.5 if F.nodes[F.members[[m['name'] for m in F.members].index(mm)]['i']][1] in (RIBS[0], RIBS[-1]) else 1.0), 'D')
    else:   # belly skin on the chassis underside, plus the leg boxes' sides hung from their corner posts
        trib += [('chassis_rail', -rx, 0.0, rx), ('chassis_rail', rx, 0.0, rx), ('chassis_spine', 0.0, 0.0, rx)]
        for leg in LEGS.values():
            area = 2*(2*leg['halfw'] + leg['y1'] - leg['y0']) * (0 - Z_LEG) / 144
            for sx in (-1, 1):
                for (x, y) in ((sx*rx - leg['halfw'], leg['y0']), (sx*rx + leg['halfw'], leg['y0']), (sx*rx - leg['halfw'], leg['y1']), (sx*rx + leg['halfw'], leg['y1'])):
                    F.pt(F.node(x, y, 0.0), SKIN_PSF*area/4, 'D')
    for g, x, z, t in trib:
        for nm in along(g, x, z): F.dist(nm, SKIN_PSF*t/144, 'D')
    # nose / tail skin: frustum lateral area ~ mean perimeter x slant, 2/3 to the base ring, 1/3 to the tip
    base_per = 2*X_SKIRT + 2*skirt_ch + 2*Z_HI + 2*cham_hi + FLAT
    for (Lc, wd, ht, zc, T, y0) in ((L_NOSE, NOSE_W, NOSE_H, NOSE_ZC, NOSE, RIBS[-1]), (L_TAIL, TAIL_W, TAIL_H, TAIL_ZC, TAIL, RIBS[0])):
        slant = math.hypot(Lc, (hw - wd/2 + Z_HI/2 - ht/2) / 2)
        area = (base_per + 2*(wd+ht)) / 2 * slant / 144
        lo = ((-X_SKIRT, Z_SKIRT), (X_SKIRT, Z_SKIRT)) if UNDERBODY != 'legs' else ((-rx, 0), (rx, 0))
        for (x, z) in lo + ((hw, 0), (hw, Z_HI), (f, Z_RIM), (-f, Z_RIM), (-hw, Z_HI), (-hw, 0)):
            F.pt(F.node(x, y0, z), SKIN_PSF*area*2/3/8, 'D')
        for p in T: F.pt(F.node(*p), SKIN_PSF*area/3/4, 'D')
    # decks: ply + people
    jt = rx
    lo_area = W*L/144; lo_live = PEOPLE_LOWER_PARKED*PERSON_LB/lo_area
    for g, x in (('chassis_rail', -rx), ('chassis_rail', rx), ('chassis_spine', 0.0)):
        for nm in along(g, x, 0.0): F.dist(nm, DECK_PSF*jt/144, 'D'); F.dist(nm, lo_live*jt/144, 'L')
    for x in (-hw, hw):
        for nm in along('deck_lo_edge', x, 0.0): F.dist(nm, DECK_PSF*(jt/2)/144, 'D'); F.dist(nm, lo_live*(jt/2)/144, 'L')
    for x in (-jx, jx):
        for nm in along('joist_hi', x, Z_HI): F.dist(nm, DECK_PSF*jt/144, 'D')
    for nm in along('joist_hi', 0.0, Z_HI): F.dist(nm, DECK_PSF*jt/144, 'D')
    for x in (-hw, hw):
        for nm in along('deck_hi_rail', x, Z_HI): F.dist(nm, DECK_PSF*(jt/2)/144, 'D')
    # parked: one person sitting at the centre of each hatch edge; moving: one below at mid-deck + one at a hatch edge
    for y in HATCH: F.pt(F.node(0.0, y, Z_HI), EDGE_PERSON, 'L')
    F.pt(F.node(0.0, L/2, 0.0), MOVING['lower_center'], 'LM'); F.pt(F.node(0.0, HATCH[0], Z_HI), MOVING['hatch_edge'], 'LM')

    tot_w = total_gravity(F, ('D', 'L')); tot_move = total_gravity(F, ('D', 'LM'))
    T = TOW_FRACTION * tot_move
    for sx in (-1, 1):
        n = F.node(sx*rx, RIBS[-1], 0.0)
        F.m.add_node_load(n, 'FY', T*math.cos(math.radians(20)), case='T'); F.m.add_node_load(n, 'FZ', T*math.sin(math.radians(20)), case='T')

    F.m.add_load_combo('Static', {'D': 1, 'L': 1})
    F.m.add_load_combo('Shock',  {'D': SHOCK, 'LM': SHOCK})
    F.m.add_load_combo('Sway',   {'D': 1, 'L': 1, 'EX_D': 1, 'EX_L': 1})
    F.m.add_load_combo('Tow',    {'D': 1, 'LM': 1, 'EY_D': 1, 'EY_LM': 1, 'T': 1})
    F.m.add_load_combo('DeadOnly', {'D': 1})
    F.total_weight, F.total_moving = tot_w, tot_move
    return F


def total_gravity(F, cases):
    tot = 0.0
    for mem in F.m.members.values():
        for dl in mem.DistLoads:
            direction, w1, w2, x1, x2, case = dl[:6]
            if direction == 'FZ' and case in cases:
                a = 0.0 if x1 is None else x1; b = mem.L() if x2 is None else x2
                tot += -(w1 + w2)/2 * (b - a)
    for nd in F.m.nodes.values():
        for (direction, Pn, case) in nd.NodeLoads:
            if direction == 'FZ' and case in cases: tot += -Pn
    return tot


# ----------------------------------------------------------------- CHECKS (same as v1)
def aisc_fcr(KL_r):
    Fe = math.pi**2 * E / KL_r**2
    return (0.658 ** (FY/Fe)) * FY if KL_r <= 4.71*math.sqrt(E/FY) else 0.877*Fe

def check(F, combos):
    res = {}
    for mm in F.members:
        mem = F.m.members[mm['name']]; s = SECTIONS[mm['sec']]
        KL_r = mm['L']/s['r']; Fcr = aisc_fcr(KL_r); r = {}
        for cb in combos:
            Pmax, Pmin = mem.max_axial(cb), mem.min_axial(cb)
            P_c, P_t = max(0.0, -Pmin), max(0.0, Pmax)
            Mz = max(abs(mem.max_moment('Mz', cb)), abs(mem.min_moment('Mz', cb)))
            My = max(abs(mem.max_moment('My', cb)), abs(mem.min_moment('My', cb)))
            Vy = max(abs(mem.max_shear('Fy', cb)), abs(mem.min_shear('Fy', cb)))
            Vz = max(abs(mem.max_shear('Fz', cb)), abs(mem.min_shear('Fz', cb)))
            sig_b = (Mz + My)/s['S']; sig_a = max(P_c, P_t)/s['A']
            omega = 1.0 if cb == 'Shock' else 1.67
            u_yield = (sig_a + sig_b)/(FY/omega)
            u_buck = P_c/(Fcr*s['A']/omega) + sig_b/(FY/omega)
            d = max(abs(mem.max_deflection(k, cb)) for k in ('dy', 'dz')) if True else 0
            d = max(d, max(abs(mem.min_deflection(k, cb)) for k in ('dy', 'dz')))
            V_end = math.hypot(Vy, Vz)
            r[cb] = dict(P=round(Pmax if P_t >= P_c else Pmin, 1), M=round(Mz+My, 1), sig_ksi=round((sig_a+sig_b)/1000, 2),
                         u_yield=round(u_yield, 3), u_buck=round(u_buck, 3), u=round(max(u_yield, u_buck), 3),
                         defl=round(d, 3), joint_lb=round(math.hypot(V_end, max(P_c, P_t)), 1), V=round(V_end, 1))
        r['KL_r'] = round(KL_r, 1); r['Fcr_ksi'] = round(Fcr/1000, 1)
        res[mm['name']] = r
    return res

def reactions(F, combos):
    return {n: {cb: dict(FX=round(nd.RxnFX[cb], 1), FY=round(nd.RxnFY[cb], 1), FZ=round(nd.RxnFZ[cb], 1)) for cb in combos}
            for n, nd in F.m.nodes.items() if nd.support_DZ}

def node_disp(F, combos):
    return {n: {cb: (round(nd.DX[cb], 3), round(nd.DY[cb], 3), round(nd.DZ[cb], 3)) for cb in combos} for n, nd in F.m.nodes.items()}


# ----------------------------------------------------------------- EXPORTS
def write_dxf(F, path):
    import ezdxf
    doc = ezdxf.new('R2010'); msp = doc.modelspace()
    for i, g in enumerate(sorted({m['group'] for m in F.members})): doc.layers.add(g, color=(i % 7) + 1)
    for mm in F.members: msp.add_line(F.nodes[mm['i']], F.nodes[mm['j']], dxfattribs={'layer': mm['group']})
    doc.saveas(path)

def write_fcmacro(F, path):
    lines = ['import FreeCAD, Part', 'doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("FloatFrame")', 'groups = {}']
    for mm in F.members:
        (x1, y1, z1), (x2, y2, z2) = F.nodes[mm['i']], F.nodes[mm['j']]
        lines.append(f'groups.setdefault("{mm["group"]}", []).append(Part.LineSegment(FreeCAD.Vector({x1},{y1},{z1}), FreeCAD.Vector({x2},{y2},{z2})).toShape())')
    lines += ['allshapes = []', 'for g, shapes in groups.items():', '    obj = doc.addObject("Part::Feature", g)', '    obj.Shape = Part.makeCompound(shapes)', '    allshapes += shapes',
              'frame = doc.addObject("Part::Feature", "Frame_all_members")', 'frame.Shape = Part.makeCompound(allshapes)', 'doc.recompute()',
              'FreeCAD.Console.PrintMessage("Float frame v2 imported: %d members (inches)\\n" % len(allshapes))']
    open(path, 'w').write('\n'.join(lines))

def write_cutlist(F, path):
    rows = {}
    for mm in F.members:
        key = (mm['group'], mm['sec'], round(mm['L'], 1)); rows[key] = rows.get(key, 0) + 1
    tot_ft = tot_lb = 0
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['group', 'section', 'length_in', 'qty', 'total_ft', 'total_lb'])
        for (g, s, Lm), q in sorted(rows.items()):
            ft = Lm*q/12; lb = ft*SECTIONS[s]['wpf']; tot_ft += ft; tot_lb += lb
            w.writerow([g, s, Lm, q, round(ft, 1), round(lb, 1)])
        w.writerow(['TOTAL', '', '', sum(rows.values()), round(tot_ft, 1), round(tot_lb, 1)])
    return tot_ft, tot_lb


def run_all():
    combos = ['Static', 'Shock', 'Sway', 'Tow']
    F = build(); F.m.analyze(check_statics=False)
    res = check(F, combos)
    F2 = build(lift_caster=LIFT_CASTER); F2.m.analyze(check_statics=False)
    res2 = check(F2, ['Static'])
    for mm in F.members: res[mm['name']]['Lifted'] = res2[mm['name']]['Static']
    return F, F2, res

def optimize(max_rounds=8):
    """Lightest allowed section per family with every member of the family under U_TARGET in every case.
    Start light, upsize whatever fails, repeat (self-weight and load sharing shift a little each round)."""
    for fam in FAMILIES.values():
        for g in fam['groups']: GROUP_SEC[g] = fam['min']
    for rnd in range(max_rounds):
        F, F2, res = run_all()
        changed = False
        for name, fam in FAMILIES.items():
            u = max(res[m['name']][c]['u'] for m in F.members if m['group'] in fam['groups'] for c in ['Static', 'Shock', 'Sway', 'Tow', 'Lifted'])
            cur = GROUP_SEC[fam['groups'][0]]
            if u > U_TARGET:
                heavier = [k for k in SECTIONS_BY_WEIGHT if SECTIONS[k]['wpf'] > SECTIONS[cur]['wpf']]
                if not heavier: continue
                nxt = heavier[0]
                for g in fam['groups']: GROUP_SEC[g] = nxt
                changed = True
                print(f"  round {rnd}: {name:8s} {cur} u={u:.2f} -> {nxt}")
        if not changed:
            print(f"  converged after {rnd+1} rounds"); break
    return GROUP_SEC

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out_dir = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'exports')
    if '--optimize' in sys.argv:
        print('Auto-sizing (strength only, U_TARGET=%.2f):' % U_TARGET); optimize()
        print('GROUP_SEC = ' + json.dumps(GROUP_SEC, indent=4))
    os.makedirs(out_dir, exist_ok=True); os.chdir(out_dir)
    combos = ['Static', 'Shock', 'Sway', 'Tow']
    F = build(); F.m.analyze(check_statics=True)
    res, rx, disp = check(F, combos), reactions(F, combos), node_disp(F, combos)
    F2 = build(lift_caster=LIFT_CASTER); F2.m.analyze(check_statics=True)
    res2, rx2, disp2 = check(F2, ['Static']), reactions(F2, ['Static']), node_disp(F2, ['Static'])
    for mm in F.members: res[mm['name']]['Lifted'] = res2[mm['name']]['Static']
    for n in disp: disp[n]['Lifted'] = disp2[n]['Static']
    for n in rx: rx[n]['Lifted'] = rx2.get(n, {}).get('Static', dict(FX=0, FY=0, FZ=0))
    combos_all = combos + ['Lifted']
    # sensitivity: the same frame with T-90 brackets at post tops and bottoms (post ends carry moment)
    def racking(disp_, cb):
        return max(abs(v[cb][1]) for n, v in disp_.items() if abs(F.nodes[n][2] - Z_HI) < 1e-6)
    PIN_BOTH.discard('post')
    FB = build(); FB.m.analyze(check_statics=False); dispB = node_disp(FB, combos)
    FB2 = build(lift_caster=LIFT_CASTER); FB2.m.analyze(check_statics=False); dispB2 = node_disp(FB2, ['Static'])
    PIN_BOTH.add('post')
    stiffness = dict(
        tow_rack_pinned=round(racking(disp, 'Tow'), 2), tow_rack_bracketed=round(racking(dispB, 'Tow'), 2),
        lifted_twist_pinned=round(max(math.hypot(*v['Lifted']) for v in disp.values()), 2),
        lifted_twist_bracketed=round(max(math.hypot(*v['Static']) for v in dispB2.values()), 2),
        hatch_sag_static=round(-disp[F.node(0.0, HATCH[0], Z_HI)]['Static'][2], 2))
    print('\nStiffness: ' + json.dumps(stiffness))
    tot_ft, tot_lb = write_cutlist(F, 'cutlist.csv'); write_dxf(F, 'frame.dxf'); write_fcmacro(F, 'frame.FCMacro')
    # joint schedule: how many sticks meet at each node, and which
    joints = {}
    for mm in F.members:
        for n in (mm['i'], mm['j']): joints.setdefault(n, []).append(mm['group'])
    joint_rows = sorted(({'node': n, 'xyz': F.nodes[n], 'n': len(g), 'groups': sorted(g)} for n, g in joints.items()), key=lambda r: -r['n'])
    out = dict(version=2, joints=joint_rows,
               params=dict(W=W, H=H_OCT, L=L, FLAT=FLAT, RIBS=RIBS, L_NOSE=L_NOSE, NOSE_W=NOSE_W, NOSE_H=NOSE_H, NOSE_ZC=NOSE_ZC,
                           L_TAIL=L_TAIL, TAIL_W=TAIL_W, TAIL_H=TAIL_H, TAIL_ZC=TAIL_ZC, Z_LO=0.0, Z_HI=Z_HI, Z_RIM=Z_RIM, Z_SKIRT=Z_SKIRT, X_SKIRT=X_SKIRT,
                           UNDERBODY=UNDERBODY, ENTRY=ENTRY, LEGS=LEGS, Z_LEG=Z_LEG, LEG_CLEAR=LEG_CLEAR, BELLY_CLEAR=BELLY_CLEAR, DOOR_HALF=DOOR_HALF,
                           Z_GROUND=Z_GROUND, RAIL_X=RAIL_X, CASTER_Y=CASTER_Y, HATCH=HATCH, JOIST_X=JOIST_X, C=C,
                           PEOPLE_LOWER=PEOPLE_LOWER_PARKED, EDGE_PERSON=EDGE_PERSON, MOVING=MOVING, PERSON_LB=PERSON_LB, SKIN_PSF=SKIN_PSF, DECK_PSF=DECK_PSF,
                           SHOCK=SHOCK, SWAY_G=SWAY_G, TOW_FRACTION=TOW_FRACTION, PLY_GT_EFF=PLY_GT_EFF, SKIN_GT_EFF=SKIN_GT_EFF, FY=FY,
                           total_weight_lb=round(F.total_weight), total_moving_lb=round(F.total_moving), steel_ft=round(tot_ft), steel_lb=round(tot_lb),
                           sections=SECTIONS, group_sec=GROUP_SEC, families={k: v['groups'] for k, v in FAMILIES.items()}, u_target=U_TARGET, stiffness=stiffness,
                           weight_by_role={r: round(sum(m['L']/12*SECTIONS[m['sec']]['wpf'] for m in F.members if ROLE[m['group']] == r)) for r in ROLE_ORDER}),
               labels=GROUP_LABEL, roles=ROLE, role_order=ROLE_ORDER,
               nodes=F.nodes, members=F.members, proxies=F.proxies, results=res, reactions=rx, disp=disp, combos=combos_all)
    json.dump(out, open('results.json', 'w'))

    print(f"\nParked D+L {F.total_weight:,.0f} lb   moving D+LM {F.total_moving:,.0f} lb   steel {tot_ft:.0f} ft / {tot_lb:.0f} lb   members {len(F.members)}  nodes {len(F.nodes)}")
    for cb in combos_all:
        worst = sorted(res.items(), key=lambda kv: -kv[1][cb]['u'])[:5]
        print(f"\n== {cb}")
        for name, r in worst:
            print(f"  {name:26s} u={r[cb]['u']:5.2f} sig={r[cb]['sig_ksi']:5.1f} ksi P={r[cb]['P']:7.0f} M={r[cb]['M']:7.0f} defl={r[cb]['defl']:.3f} KL/r={r['KL_r']}")
    print("\n== Casters FZ (lb)")
    for n, r in rx.items(): print(f"  {n:26s} " + "  ".join(f"{cb}:{r[cb]['FZ']:6.0f}" for cb in combos_all))
    print("\n== by group: max u (any case) / max joint lb")
    for g in sorted({m['group'] for m in F.members}):
        ms = [m for m in F.members if m['group'] == g]
        u = max(res[m['name']][c]['u'] for m in ms for c in combos_all); j = max(res[m['name']][c]['joint_lb'] for m in ms for c in combos_all)
        print(f"  {g:16s} {GROUP_SEC[g]}  u={u:.2f}  joint={j:6.0f}")
    import math as _m
    for cb in combos_all:
        mx = max((_m.hypot(*v[cb]), n) for n, v in disp.items())
        print(f"max displacement {cb:7s} {mx[0]:.3f} in at {mx[1]}")
