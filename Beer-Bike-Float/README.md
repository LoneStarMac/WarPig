# War Pig Beer Bike Float Frame

There have been many war pigs since the mascot was logingly adopted, including a couple iterations of the wooden Beer Bike float. The current woden float has suffered repeated buckling of the 4x4 frame, which is now split beyond repair and prompts us to reimagine the base of the pig again.

A warning lives in the nose of the current wooden pig:
> Hello
>
> If you 
>
> decide to rebuild
>
> this pig, do NOT
>
> just copy each piece.
>
> They are not equal..
>
> It is a nightmare.
>
> Good luck.
>
> ♡ Loryn H. '21


Sounds like a good idea then.

In this repository you will find a structural model of a bolted perforated-square-steel-tube frame for an 8 × 8 × 8 ft octagonal War Pig, replacing the rotting 5-year-old wood frame. Space-frame analysis in [PyNite](https://github.com/JWock82/Pynite), with an interactive 3D viewer, cut list, joint schedule and caster loads.

**Live page:** https://lonestarmac.github.io/WarPig/Beer-Bike-Float/ 

> This is a parametric model built so the team can change dimensions, loads and tube sizes and see the consequences. Before we ride on it, have an engineer review and/or test it well.


## Current design

| | |
|---|---|
| Body | 96 × 96 × 96 in octagon, 55 in flats, top open. 36 in snout to a 30 × 18 in panel; 20.5 in tail to a 55 × 55 in flap (the door is in it), so every tail face is a 45° cut. |
| Chassis | Two 2.5" × 14 ga rails at ±26" on the octagon's 55" bottom flat, four 2" × 52" cross-members at the ribs (Y = 0, 32, 64, 96), no spine. 16" casters under the rails at 11" from each end, entirely below the body: the feet. |
| Lower deck | 20.5" above the chassis: at each rib a V of 1.5" diagonals from the rail ends up to a 2" deck spine, a 1.5" beam across the apex, and 45° chamfer stubs out to the deck-ring corners. No joists or columns. 0.75" ply spanning 32" between the beams, 40" above the road, i.e. where it is now. |
| Sides | Three 1.75" posts per side at Y = 0, 48, 96: one on each body corner (a nailer for both ply sheets that meet there) and one mid-side. Hard-skinned, two 48 × 55 pieces per side; the panels are the side bracing (fastened along every edge). Optional cable X per side (`CABLES`) as a backstop if the ply ever slips. Entry is through the tail. |
| Upper deck | 1.75" side rails, end beams and two hatch-edge cross beams, 1.5" hatch sides; ply spans 32" between the beams. 48 × 32 in hatch, 97" above the road. |
| Rim | 1.5" handrail stringers 20.5" above the upper deck on 1.5" chamfer stubs at Y = 0, 24, 72, 96 (off the hatch-beam stations, so those rail joints are plain T's), cross pieces at the nose and tail only (nothing to sit on across the opening). Top of frame 113" above the road. |
| Bracing | 1.5" 45° X in the nose wall; four 1.5" long braces from the deck-ring corners of the end ribs up to the hatch-edge beams (front pair to ±12" on the Y=64 beam, rear pair to ±24" on the Y=32 beam); the V's under the deck at every rib; skinned tail-wall panels beside the door; deck, belly, chamfer and side plywood. |
| Underbody | The full octagon: 20.5" lower chamfer to the 55" bottom flat, 17" off the road, with the casters below it. Optional coroplast sleeves with a rubber-seal hoof round each caster, no steel. Rigid casters at the rear, swivels at the front. |
| Steel | ≈ 384 ft, ≈ 532 lb, all 14 ga: 28 ten-ft sticks of 1.5", 12 of 1.75", 3 of 2", 2 of 2.5". (v2 at 12 ga was 1,016 lb.) |
| Weight | ≈ 2,980 lb parked with 6 aboard; ≈ 2,130 lb moving with 2. |
| Casters | 810 lb each parked, 1,490 lb with one wheel in a pothole, 1,420 lb on the downhill side at 0.3 g sideways. Spec 16" wheels ≥ 1,200 lb. Tipping starts at about 0.43 g sideways with 6 aboard; braking lifts the rear wheels at about 0.54 g. A rear-wheel brake is self-limiting: even locked, the rear tires can only hold about 0.22 g, because braking unloads them. So the brake is a spring-applied shoe on each rear tire, pin-released, as strong as you like. |
| Worst member | Chassis rail, 85% of allowable at 0.3 g sideways, now that the caster's 17" lever is in the model (73% with one wheel lifted). The rails were checked at 2": over 100%, so they stay 2.5"; 12 ga rails buy margin for 14 lb. Target is 85%; nothing else over 47% (the hatch-edge beams, braking). Cross-members 34%. |
| Flex | 0.08" sag at the hatch edge with someone sitting on it (the long braces prop it). Front-to-back racking under a rope snatch: 0.09" with every joint a pin. Pothole twist 0.28". |

### Sizing philosophy

The frame is skinned in plywood, and flex is acceptable; what is not acceptable is a yielded tube or a sheared bolt, so members are sized for **strength**: `python model/frame_model.py --optimize` picks, for each member family, the lightest tube from the allowed list that stays under 85% of capacity (yield or buckling) in every load case, and deflection is reported rather than limited. That took the frame from 1,016 lb of 12 ga to 604 lb of 14 ga.
The 14 ga section properties are derived from the 12 ga Telespar datasheet by the gross-section ratio; the actual tube we buy needs to be chcked since some generic perforated tube is 33–36 ksi rather than 50, which would push the chassis back to 12 ga.

Rigidity then comes from the four long braces (34 lb), the deck, belly, chamfer and side plywood screwed to the frame, and the nose and tail pyramids. The body is a closed tube and post brackets no longer matter for stiffness; they are still worth having for consistency of construction.

### Joint philosophy

Two perforated tubes crossing at 90° share exactly one bolt, so every T and corner in this frame is modelled as a pin and the frame is sized so that is enough. Nothing relies on a bolted corner carrying moment. Moment exists only inside continuous sticks (sleeve-spliced with a 12" stub of the next size down) and in the chassis ladder, which we recommend having a shop weld from plain 2.5" tube and paint (about an hour of welding); bolting it with the rails stacked on the cross-members also works, the deck ply holds it square.

Pre-fabicated plates standardise the connections. Verticals lap past their horizontals instead of butting them, so the two tubes share a flat face and a laser-cut flat plate bolts across it, two bolts per leg, no bends. The goal is to design every diagonal in the body at 45°, so there are only two plate patterns: **A, a flat T or L plate** (~90) and **B, a flat 45° plate** (~45: chamfer stubs, X-brace ends, tail stringers). Cone stringers, long braces, lower-box diagonals and V-braces are flattened-end one-bolt pins and need none. Both patterns are a SendCutSend order from 12 ga.

Racking is resisted by the .75" deck plywood acting as shear diaphragms (screw it to the steel every 6–8" along every panel edge; this is the one place fastener spacing matters) and by the nose and tail pyramids, which are rigid in every direction. The 3/8" skin on the two upper chamfer faces is also counted as a light shear panel; without it the rim sways 2" under a tow snatch, so fasten that skin along all its edges or add one hidden diagonal per bay up there.

The busiest joint has five sticks (the four lower corners of the end ribs): cross-member end, edge stringer on top of it, post beside the stringer, skirt stub underneath, cone stringer on the stringer end. Each is a separate one-bolt lap to its neighbour.

Bolts: ⅜" Grade 5 zinc-plated, flange nuts or nylocks, snug-tight only. These are bearing joints; clamp force adds nothing and over-tightening dimples the 0.105" wall. Where a bolt passes through a single tube with nothing inside it, a 1.75" sleeve stub inside the 2" tube lets you tighten harder.

## Building it

The viewer's **Build** tab has the full sequence; the short version:

1. Cut and label every stick; flatten the ends of the cone stringers, long braces, lower-box diagonals and V-braces.
2. Chassis upside down on sawhorses: rails on cross-members, corner plates, caster plates with crush sleeves, belly ply. Flip it onto its wheels.
3. Lower box: at each rib a V from the rail ends to the deck centre, the deck beam across it, chamfer stubs to the corners; then the deck spine and edge stringers. Square and level it.
4. Lower deck ply (two 4 × 8 sheets from above).
5. Posts, side rails, end and hatch-edge beams, hatch sides, nose X-brace, tail-door jambs; then the four long braces, standing on the deck-ring corners of the end ribs and rising to the hatch-edge beams.
6. Upper deck ply from above (a 48" sheet fits the 55" top opening), rim, nose and tail frames, door.
7. Skin bottom up and outside in, every panel fastened along all four edges; paint; decorations; hooves.

**Plates** (`docs/exports/plates/`, DXF for laser cutting, 10 ga zinc-plated steel, slotted so they land on the tube's 1" hole pitch): TP-90 T plate, TL-90 L plate, TP-45 45° plate. Two per joint, one each face; quantities and the bolt schedule (≈620 ⅜"-16 Grade 5 bolts by length, 20 crush sleeves, fender washers) are computed from the model on the Build tab. Torque with threadlocker throughout: 12 ft·lb where there are plates both sides, 8 ft·lb on a bare tube with fender washers, 25 ft·lb at the caster and tow bolts, which have sleeves.
**Plates** (`docs/exports/plates/`, DXF for laser cutting, 10ga zinc-plated steel, slotted so they land on the tube's 1" hole pitch): TP-90 T plate, TL-90 L plate, TP-45 45° plate. Two per joint, one each face; quantities and the bolt schedule (≈620 .375"-16 Grade 5 bolts by length, 20 crush sleeves, fender washers) are computed from the model on the Build tab. Torque with threadlocker throughout: 12 ft·lb where there are plates both sides, 8 ft·lb on a bare tube with fender washers, 25 ft·lb at the caster and tow bolts, which have sleeves.

## Reviewing and changing the design

Everything is driven by the `PARAMETERS` block at the top of [`model/frame_model.py`](model/frame_model.py): dimensions, rib stations, cone sizes, people counts, dynamic factors, tube size per member group, plywood stiffness. Change a value, push to `main`, and the GitHub Action re-runs the model, rebuilds the page and the export files, and redeploys. Open a pull request instead and the Action runs the model and attaches the exports to the run without deploying, so you can review a change before it goes live.

* `docs/index.html` is the page: title, headings, the prose in every tab, the build steps. A number that comes from the model is a `<span data-v="…">` whose attribute is a small expression over the model data (`P` is the parameter block, `S` the per-case summary, `D` everything; `fmt()` formats). A table or figure the script draws is a `<div data-fill="name">`.
* `docs/viewer.css` is the style. `docs/viewer.js` is the script: the 3D scene, the table renderers (the `FILLS` map) and the helpers the `data-v` expressions can use.
* `docs/data.js` is written by `model/build_viewer.py` from the model run. Do not edit it; it is overwritten.
* three.js and its OrbitControls load from jsDelivr, pinned to r128 (the last release with the plain-script build).

To run locally, from this directory:

```bash
pip install -r requirements.txt
python model/frame_model.py            # prints worst members, writes docs/exports/*
python model/make_plates.py            # plate DXFs
python model/build_viewer.py            # writes docs/data.js for the page
```

Open `docs/index.html` in a browser. It loads three.js and fonts from CDNs, so it needs a network connection.

## Files

| Path | What |
|---|---|
| `model/frame_model.py` | The model: geometry, loads, load cases, checks, exports. |
| `model/build_viewer.py` | Turns `results.json` into `docs/data.js`: merged sticks, stock packing, joint census, plate counts, bolt schedule. |
| `model/make_plates.py` | Writes the plate DXFs and their spec to `docs/exports/plates/`. |
| `model/v1/` | Archived absurd first version. Never forget who you are. |
| `docs/index.html`, `viewer.css`, `viewer.js` | The page, its style and its script. |
| `docs/data.js` | Generated model data the page reads. |
| `docs/exports/frame.FCMacro` | FreeCAD macro: Macro → Macros… → Execute. One Part object per member group, inches, plus a compound of all members. |
| `docs/exports/frame.dxf` | Same wireframe as 3D lines, one layer per member group. |
| `docs/exports/cutlist.csv` | Model segments by group, section and length. The viewer's Cut list tab merges them into physical sticks. |
| `notes/` | Design notes for things not yet in the model (the brake). |
| `docs/exports/results.json` | Everything the viewer shows: member forces per load case, displacements, reactions, joint schedule. |

Units: inches and pounds. X across, Y along the length (rear body rib = 0, snout forward), Z up; Z = 0 is the chassis centreline. The road is at Z = −17.25 (16" caster + half a 2.5" tube).
Units: inches and pounds. X across, Y along the length (rear body rib = 0, snout forward), Z up; Z = 0 is the chassis centreline. The road is at Z = −17.25 (16" caster + half a 2.5" tube).

## What the model does and does not do

* 1D beam elements, linear static. Six load cases: parked with 6 aboard; moving with 2 aboard × 2.0 road shock; parked + 0.3 g sideways; moving + rope snatch at the front rail ends; parked with the right-rear wheel off the ground;moving + 0.3 g stop held at the rear wheels only. Casters are stiff legs from the rails to the road, pinned at the tire,so sideways and braking forces overturn about the road and the caster's lever loads the rail and cross-members.
* Member checks: yield (P/A + M/S) and AISC E3 column buckling over the node-to-node length. Shock is checked against nominal strength (it already carries a 2× factor); the other cases against ASD allowables (÷1.67).
* 12ga section properties are the perforated net values from the Unistrut Telespar datasheet; 14ga is scaled from them. F<sub>y</sub> = 50 ksi (ASTM A1011 Gr 50; Unistrut quotes 60 ksi average after forming).
* `--optimize` re-sizes every family from scratch; a plain run uses the sizes baked into `GROUP_SEC`.
* Plywood decks modelled as shear panels at an effective G·t of 15,000 lb/in (APA gives 60–80k for .75" sheathing before fastener slip). This is the assumption most worth an engineer's eye.
* `UNDERBODY` ('octagon', 'chamfer', 'legs' or 'skirt'), `ENTRY` ('tail' or 'side'), `LONG_BRACES`, `SIDE_BRACING` ('skin', 'diagonals', 'none'), `POST_Y`, `CHAMFER_Y`, `UPPER_JOISTS`, `RIM_CROSS`, `LOWER_WEB` ('vee': V to a deck spine at every rib; 'vee_ends': V's at the end ribs only, needs a 2.5" spine; 'pratt': side trusses with columns and diagonals), `CABLES` (tension-only cable X's: 'sides', 'nose'; `CABLE_D` picks ⅛", 3/16" or 1 4" 7×19 cable, checked at breaking/5) and `SPINE` switch between the v8 to v3 layouts. 'octagon' puts the chassis on the bottom flat with the casters below it; the other three keep the chassis at the lower deck with the casters inside the body, which rides 20" lower.
* Not modelled: local wall dimpling under a bolt, hole slop, skin on the sides, belly, legs and cones, wind.

## To do

* **Brake.** Not designed in. A rear-wheel-only tread-shoe brake, over-centre handbrake lever with a gas-strut assist and a ratchet, drop chocks as the no-operator backstop; the physics (rear lifts at ~0.54 g, a locked rear tire can only give ~0.22 g, so the brake cannot be too strong) and the mechanism are written up in [`notes/brake.md`](notes/brake.md) for when the design moves forward.
* **Brake.** Not designed in. A rear-wheel-only tread-shoe brake, over-centre handbrake lever with a gas-strut assist and a ratchet, drop chocks as the no-operator backstop; the physics (rear lifts at ~0.54 g, a locked rear tire can only give ~0.22 g, so the brake cannot be too strong) and the mechanism are written up in [`notes/brake.md`](notes/brake.md) for when the design moves forward.

## Sources

* [Telespar datasheet: section properties, material](https://unistrut.biz/content/Resources/General/Telespar-DataSheet.pdf)
* [Telespar 2 × 2 × 12ga 10 ft post, street price](https://squarefittings.com/store/telspar-2-x-2-square-sign-post-with-holes-10-tall-12-gauge-pre-galv-plus-g90.html)
* [PyNite](https://github.com/JWock82/Pynite), [ezdxf](https://github.com/mozman/ezdxf), [three.js](https://threejs.org/)
