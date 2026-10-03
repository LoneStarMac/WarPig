# Octagon Float Frame

Structural model of a bolted perforated-square-steel-tube frame for an 8 × 8 × 8 ft octagonal parade float
(the pig), replacing a rotting 15-year-old wood frame. Space-frame analysis in [PyNite](https://github.com/JWock82/Pynite),
with an interactive 3D viewer, cut list, joint schedule and caster loads.

**Live page:** https://lonestarmac.github.io/WarPig/Beer-Bike-Float/ (after Pages is enabled, see *Setup* below)

> Not a stamped design. It is a parametric model built so the team can change dimensions, loads and tube sizes and
> see the consequences. If people ride on it, have a qualified engineer look at the rider load cases before you build.

## Current design (v3)

| | |
|---|---|
| Body | 96 × 96 × 96 in octagon, 55 in flats, top open. 36 in snout to a 30 × 18 in panel; 24 in tail to a 48 × 40 in panel. |
| Chassis | 2½" × 14 ga ladder at the lower-deck level: two rails at ±24", a spine, four cross-members at the ribs (Y = 0, 32, 64, 96). Casters under the rails at 12" from each end. |
| Lower deck | ¾" ply on the chassis, 19" above the road (was 38"). |
| Sides | 1¾" posts only, three 32 × 55 in door bays per side. No diagonals in the body. |
| Upper deck | 2" perimeter and cross beams, two 1½" joists, 48 × 32 in hatch in the middle, 57" above the road. |
| Rim | 1½" handrail ring 20.5" above the upper deck, on 1½" chamfer stubs. Top of frame 93" above the road (was 115"). |
| Bracing | 1½" 45° X in the nose and tail walls. The deck plywood and the nose/tail pyramids do the rest. |
| Skirt | 1½" skin framing below the chassis, 6" off the road, 73½" wide belly. |
| Steel | ≈ 409 ft, ≈ 604 lb, all 14 ga: 27 ten-ft sticks of 1½", 6 of 1¾", 6 of 2", 7 of 2½". (v2 at 12 ga was 1,016 lb.) |
| Weight | ≈ 3,080 lb parked with 6 aboard; ≈ 2,230 lb moving with 2. |
| Casters | 800 lb each parked, 1,540 lb with one wheel in a pothole. Spec 16" wheels ≥ 1,200 lb. |
| Worst member | Chassis rail, 74% of allowable, one wheel lifted. Target is 85%; nothing else over 60%. |
| Flex | 0.5" sag at the hatch edge with someone sitting on it. Front-to-back racking under a rope snatch: 2.1" with every joint a pin, 0.24" with brackets at the 16 post ends. |

### Sizing philosophy

The frame is skinned in plywood, so flex is acceptable; what is not acceptable is a yielded tube or a sheared
bolt. So members are sized for **strength only**: `python model/frame_model.py --optimize` picks, for each member
family, the lightest tube from the allowed list that stays under 85% of capacity (yield or buckling) in every load
case, and deflection is reported rather than limited. That took the frame from 1,016 lb of 12 ga to 604 lb of 14 ga.
The 14 ga section properties are derived from the 12 ga Telespar datasheet by the gross-section ratio; **confirm the
yield grade of the 14 ga tube you buy**, since some generic perforated tube is 33–36 ksi rather than 50, which would
push the chassis back to 12 ga.

Rigidity then comes from three things that weigh nothing: the deck plywood screwed to the frame, the nose and tail
pyramids, and brackets at the post ends (which the model does not count on, but which cut racking nine-fold).

### Joint philosophy, because that is what makes it buildable

Two perforated tubes crossing at 90° share exactly one bolt, so every T and corner in this frame is modelled as a
pin and the frame is sized so that is enough. Nothing relies on a bolted corner carrying moment. Moment exists
only inside continuous sticks (sleeve-spliced with a 12" stub of the next size down) and in the chassis ladder,
which we recommend having a shop weld from plain 2½" tube and paint (about an hour of welding); bolting it with
the rails stacked on the cross-members also works, the deck ply holds it square.

Brackets make it stiff. Every diagonal in the body is 45°, so the whole frame needs two bracket patterns, counted
from the model on the viewer's Joints tab: **A, a 90° saddle** (~110: a U-channel wrapping the host tube, two bolts
through it, a tab along the ending tube with two bolts) and **B, the same saddle with the tab bent to 45°** (~50:
X-brace ends, chamfer stubs, skirt stubs). Nose and tail stringers need none: flatten 2" of the end in a vise and
use one bolt. A cut-and-brake "cap" on the tube end does the same job as pattern A if you would rather make than
order. Both patterns are simple enough to have laser-cut and bent (SendCutSend or similar) from 12 ga.

Racking is resisted by the ¾" deck plywood acting as shear diaphragms (screw it to the steel every 6–8" along
every panel edge; this is the one place fastener spacing matters) and by the nose and tail pyramids, which are
rigid in every direction. The 3/8" skin on the two upper chamfer faces is also counted as a light shear panel;
without it the rim sways 2" under a tow snatch, so fasten that skin along all its edges or add one hidden diagonal
per bay up there.

The busiest joint has five sticks (the four lower corners of the end ribs): cross-member end, edge stringer on top
of it, post beside the stringer, skirt stub underneath, cone stringer on the stringer end. Each is a separate
one-bolt lap to its neighbour.

Bolts: ⅜" Grade 5 zinc-plated, flange nuts or nylocks, snug-tight only. These are bearing joints; clamp force
adds nothing and over-tightening dimples the 0.105" wall. Where a bolt passes through a single tube with nothing
inside it, a 1¾" sleeve stub inside the 2" tube lets you tighten harder.

## Reviewing and changing the design

Everything is driven by the `PARAMETERS` block at the top of [`model/frame_model.py`](model/frame_model.py):
dimensions, rib stations, cone sizes, people counts, dynamic factors, tube size per member group, plywood
stiffness. Change a value, push to `main`, and the GitHub Action re-runs the model, rebuilds the page and the
export files, and redeploys. Open a pull request instead and the Action runs the model and attaches the exports
to the run without deploying, so you can review a change before it goes live.

To run locally, from this directory:

```bash
pip install -r requirements.txt
python model/frame_model.py            # prints worst members, writes docs/exports/*
python model/build_viewer.py --standalone   # writes docs/index.html
```

Open `docs/index.html` in a browser. It loads three.js and fonts from CDNs, so it needs a network connection.

## Files

| Path | What |
|---|---|
| `model/frame_model.py` | The model: geometry, loads, load cases, checks, exports. Edit this. |
| `model/build_viewer.py` | Turns `results.json` into the viewer page. |
| `model/viewer_template.html` | The viewer (three.js scene, tabs, cross-section drawing). |
| `model/v1/` | The first, fully-triangulated design, kept for reference. |
| `docs/index.html` | Built viewer, served by GitHub Pages. |
| `docs/exports/frame.FCMacro` | FreeCAD macro: Macro → Macros… → Execute. One Part object per member group, inches, plus a compound of all members. |
| `docs/exports/frame.dxf` | Same wireframe as 3D lines, one layer per member group. |
| `docs/exports/cutlist.csv` | Model segments by group, section and length. The viewer's Cut list tab merges them into physical sticks. |
| `docs/exports/results.json` | Everything the viewer shows: member forces per load case, displacements, reactions, joint schedule. |

Units: inches and pounds. X across, Y along the length (rear body rib = 0, snout forward), Z up; Z = 0 is the
chassis centreline. The road is at Z = −17.25 (16" caster + half a 2½" tube).

## What the model does and does not do

* 1D beam elements, linear static. Five load cases: parked with 6 aboard; moving with 2 aboard × 2.0 road shock;
  parked + 0.3 g sideways; moving + rope snatch at the front rail ends; parked with the right-rear wheel off the ground.
* Member checks: yield (P/A + M/S) and AISC E3 column buckling over the node-to-node length. Shock is checked
  against nominal strength (it already carries a 2× factor); the other cases against ASD allowables (÷1.67).
* 12 ga section properties are the perforated net values from the Unistrut Telespar datasheet; 14 ga is scaled from
  them. F<sub>y</sub> = 50 ksi (ASTM A1011 Gr 50; Unistrut quotes 60 ksi average after forming).
* `--optimize` re-sizes every family from scratch; a plain run uses the sizes baked into `GROUP_SEC`.
* Plywood decks modelled as shear panels at an effective G·t of 15,000 lb/in (APA gives 60–80k for ¾" sheathing
  before fastener slip). This is the assumption most worth an engineer's eye.
* Not modelled: local wall dimpling under a bolt, hole slop, skin on the sides, belly and cones, wind.

## Setup (once)

1. Repo Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. Push to `main` (or run the *Run models and publish site* workflow by hand). The site URL appears on the
   workflow's deploy step; this design is at `/Beer-Bike-Float/`.

## Sources

* [Telespar datasheet: section properties, material](https://unistrut.biz/content/Resources/General/Telespar-DataSheet.pdf)
* [Telespar 2 × 2 × 12 ga 10 ft post, street price](https://squarefittings.com/store/telspar-2-x-2-square-sign-post-with-holes-10-tall-12-gauge-pre-galv-plus-g90.html)
* [PyNite](https://github.com/JWock82/Pynite), [ezdxf](https://github.com/mozman/ezdxf), [three.js](https://threejs.org/)
