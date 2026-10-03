"""
Flat connection plates for the perforated-tube frame, as DXF for laser cutting (SendCutSend etc.).
Run from the repo root:  python model/make_plates.py   -> docs/exports/plates/*.dxf + plates.json

Every plate is flat, 10 ga (0.135") mild steel, zinc plated. Bolt holes are SLOTS so the plate lands on the
tube's 1"-pitch holes whatever the phase of the cut. Each leg gets two bolts. The plate goes on both faces of
the joint; one 3/8" bolt passes plate - tube - plate at each slot.

  TP-90   T plate: a tube ending square on a continuous tube (posts to rails, beams to rails, columns to chassis)
  TL-90   L plate: two tube ends meeting at a corner (tip frames, rim corners, deck-frame corners)
  TP-45   45-degree plate: a chamfer stub, X-brace end or 45-degree tail stringer landing on a tube
Units: inches.
"""
import json, math, os
import ezdxf
from ezdxf import units

T = 0.135                 # 10 ga
LEG_W = 1.25              # leg width: fits inside the 1.5" tube face with a little margin
SLOT_W = 0.406            # 13/32 for a 3/8 bolt
SLOT_L = 1.30             # slot length along the tube: covers any 1" hole phase with margin
RAD = 0.25                # corner radius on the outline

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'exports', 'plates')
os.makedirs(OUT, exist_ok=True)


def slot(msp, cx, cy, length, width, angle_deg=0.0, layer='CUT'):
    """Obround slot centred at (cx, cy), long axis along angle."""
    a = math.radians(angle_deg); ca, sa = math.cos(a), math.sin(a)
    r = width / 2; h = (length - width) / 2
    pts = []
    # two straight edges + two semicircles, as a closed polyline with bulges
    p1 = (cx + h*ca - r*sa, cy + h*sa + r*ca); p2 = (cx - h*ca - r*sa, cy - h*sa + r*ca)
    p3 = (cx - h*ca + r*sa, cy - h*sa - r*ca); p4 = (cx + h*ca + r*sa, cy + h*sa - r*ca)
    pl = msp.add_lwpolyline([(p1[0], p1[1], 0, 0, 0), (p2[0], p2[1], 0, 0, 1), (p3[0], p3[1], 0, 0, 0), (p4[0], p4[1], 0, 0, 1)],
                            format='xyseb', close=True, dxfattribs={'layer': layer})
    return pl


def outline(msp, pts, layer='CUT'):
    """Closed polyline with rounded corners (radius RAD) through the given corner points."""
    n = len(pts); out = []
    for i in range(n):
        p0, p1, p2 = pts[i-1], pts[i], pts[(i+1) % n]
        v1 = (p0[0]-p1[0], p0[1]-p1[1]); v2 = (p2[0]-p1[0], p2[1]-p1[1])
        l1 = math.hypot(*v1); l2 = math.hypot(*v2)
        u1 = (v1[0]/l1, v1[1]/l1); u2 = (v2[0]/l2, v2[1]/l2)
        ang = math.acos(max(-1, min(1, u1[0]*u2[0] + u1[1]*u2[1])))
        d = RAD / math.tan(ang/2) if ang > 1e-6 else 0
        d = min(d, l1/2 - 1e-3, l2/2 - 1e-3)
        a = (p1[0] + u1[0]*d, p1[1] + u1[1]*d); b = (p1[0] + u2[0]*d, p1[1] + u2[1]*d)
        cross = u1[0]*u2[1] - u1[1]*u2[0]
        bulge = math.tan((math.pi - ang) / 4) * (1 if cross < 0 else -1)
        out.append((a[0], a[1], 0, 0, bulge)); out.append((b[0], b[1], 0, 0, 0))
    msp.add_lwpolyline(out, format='xyseb', close=True, dxfattribs={'layer': layer})


def new_doc():
    doc = ezdxf.new('R2010'); doc.units = units.IN
    doc.layers.add('CUT', color=7); doc.layers.add('NOTES', color=3)
    return doc, doc.modelspace()


def tp90():
    """T plate. Bar along the host tube (6" x 1.25"), stem down the ending tube (1.25" x 4")."""
    doc, msp = new_doc()
    bar_l, stem_l, w = 6.0, 4.0, LEG_W
    pts = [(-bar_l/2, 0), (bar_l/2, 0), (bar_l/2, w), (w/2, w), (w/2, w + stem_l), (-w/2, w + stem_l), (-w/2, w), (-bar_l/2, w)]
    outline(msp, pts)
    for cx in (-1.9, 1.9): slot(msp, cx, w/2, SLOT_L, SLOT_W, 0)           # two bolts in the host, either side of the stem
    for cy in (w + 1.0, w + 2.6): slot(msp, 0, cy, SLOT_L, SLOT_W, 90)      # two bolts down the ending tube
    return doc, dict(name='TP-90', desc='T plate, tube ending square on a continuous tube', w=bar_l, h=w + stem_l, bolts=4)


def tl90():
    """L plate for a corner where two tube ends meet. Legs 4.5" x 1.25"."""
    doc, msp = new_doc()
    leg, w = 4.5, LEG_W
    pts = [(0, 0), (leg, 0), (leg, w), (w, w), (w, leg), (0, leg)]
    outline(msp, pts)
    for cx in (w + 0.9, w + 2.5): slot(msp, cx, w/2, SLOT_L, SLOT_W, 0)
    for cy in (w + 0.9, w + 2.5): slot(msp, w/2, cy, SLOT_L, SLOT_W, 90)
    return doc, dict(name='TL-90', desc='L plate, two tube ends meeting at a corner', w=leg, h=leg, bolts=4)


def tp45():
    """45-degree plate: bar along the host (6" x 1.25"), leg at 45 degrees (1.25" x 4.5") from the bar's centre."""
    doc, msp = new_doc()
    bar_l, leg_l, w = 6.0, 4.5, LEG_W
    c, s = math.cos(math.radians(45)), math.sin(math.radians(45))
    # leg axis starts at the bar's top edge centre and goes up-right at 45 degrees
    ax, ay = 0.0, w
    hw = w/2
    # leg corners (perpendicular offset to the axis)
    n = (-s, c)   # perpendicular to the 45-degree axis
    tip = (ax + leg_l*c, ay + leg_l*s)
    legA = (ax + n[0]*hw, ay + n[1]*hw); legB = (ax - n[0]*hw, ay - n[1]*hw)
    tipA = (tip[0] + n[0]*hw, tip[1] + n[1]*hw); tipB = (tip[0] - n[0]*hw, tip[1] - n[1]*hw)
    # where the leg's edges meet the bar's top edge (y = w)
    def meet(p):  # move along the axis direction back to y = w
        t = (w - p[1]) / s
        return (p[0] + t*c, w)
    mA, mB = meet(legA), meet(legB)
    pts = [(-bar_l/2, 0), (bar_l/2, 0), (bar_l/2, w), mB, tipB, tipA, mA, (-bar_l/2, w)]
    outline(msp, pts)
    for cx in (-1.9, 2.3): slot(msp, cx, w/2, SLOT_L, SLOT_W, 0)
    for d in (1.6, 3.2): slot(msp, ax + d*c, ay + d*s, SLOT_L, SLOT_W, 45)
    return doc, dict(name='TP-45', desc='45-degree plate, chamfer stub / brace landing on a tube', w=bar_l, h=w + leg_l*s + hw*c, bolts=4)


specs = []
for fn in (tp90, tl90, tp45):
    doc, meta = fn()
    path = os.path.join(OUT, meta['name'] + '.dxf'); doc.saveas(path)
    meta.update(file=os.path.basename(path), thickness=T, material='10 ga (0.135") mild steel, zinc plated',
                slot=f'{SLOT_W:.3f} x {SLOT_L:.2f} in', leg_width=LEG_W)
    specs.append(meta)
json.dump(specs, open(os.path.join(OUT, 'plates.json'), 'w'), indent=1)
print(json.dumps(specs, indent=1))
