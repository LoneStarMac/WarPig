# Brake: notes for later

Status: **to do, not designed in.** Nothing in the frame model depends on this. The numbers below come from the
model's Stop case (`STOP_G`, rear tyres braked, crowd moving) and some hand arithmetic; revisit them if the
casters, the CG or the crowd change.

## What the physics says

* The body is tall and the crowd sits high, so a stop is a pitch problem before it is a strength problem. The
  frame is at 47% in the Stop case; the rear wheels are the limit. At 0.3 g braking the rear pair keeps 455 of its
  1,015 lb, so the rear lifts at about **0.54 g**. Sideways tipping starts at about 0.43 g with 6 aboard.
* **Any brake goes on the rear wheels only**, and then it cannot overdo it: every bit of braking unloads the rear
  tyres, and they can only hold μ × load. Even a locked rear wheel on dry asphalt (μ 0.8) manages about **0.22 g**,
  a quarter of the way to lifting the rear. So size the brake to lock the wheel and let the tyre do the limiting.
* 3 mph (parade pace) is ~900 ft·lb with 3,000 lb aboard. At 0.22 g that stops in about 1.4 ft; at 0.14 g about
  2.2 ft. Ordinary-car braking, nothing dramatic for people sitting down.
* A dragging panel does nothing: friction is μ × load and a dropped sheet only drags its own weight. A skid only
  brakes if it lifts a wheel, which is a chock with extra steps.

## Layout

* **Rigid casters at the rear, swivels at the front.** Then the rear tyre path is fixed, the shoes know where the
  tyre is, and the float tracks straight when pushed from behind.
* **One shoe per rear tyre on a hinged arm.** There is no room above the tyre (the 16" wheel top meets the rail
  underside), so the arm hangs from a bracket on the chassis rail behind the tyre, shoe at axle height, pressed
  forward into the tread. Pivot an inch or two aft of straight-above-the-shoe so the tyre's rotation drags the shoe
  in harder (leading-shoe effect, ×2–3). Since the tyre caps the stop, a self-energizing shoe that locks is fine.
  Shoe face: a slab of conveyor belt or truck mudflap on a steel backer, rubber on rubber μ ≈ 0.6 dry, ~0.4 wet.
* **Not drawer slides.** The braking friction is a side load across a slide, which is the loading ball slides are
  worst at, and they pack with grit. One bolt pivot does the job.
* **Equalizer.** One cable from the lever to a balance bar (handbrake "compensator"), two cables to the arms.
  Without it the strong shoe locks and the weak one idles, and the pig yaws as it stops. Barrel adjusters or a
  turnbuckle in each cable: shoes and tyres wear.

## Lever: over-centre handbrake with gas-strut assist

The preferred version. Pull back = brake, push forward flat = released. It is a car handbrake with an
over-centre strut, so the instinctive panic motion (yank back) is the right one.

* A gas strut on the lever whose line of action crosses the pivot ~20° into the pull. Forward of centre it holds
  the lever released; past centre it pulls the lever on. Its torque is force × offset from the pivot, zero at
  centre and growing with angle, so the brake comes on over the second half of the travel: that is the slow stop.
* Put dead centre early so any deliberate pull passes it; a lever stalled at dead centre is in neutral equilibrium.
  Keep the released hold-off weak, 10–15 lb at the handle, so a trip cord can pull it through (below) but bumps
  and vibration cannot.
* **Ratchet sector and pawl, not a single parking pin.** Holds any position (half-applied on a slope during a
  halt), and parks without relying on the strut, which loses force in the cold and over the years. Golf-cart and
  UTV hand-brake lever assemblies have the ratchet, the release button and the cable fitting built in, $30–60;
  buy that rather than make it.
* Release: pull back a notch to unload the pawl, press the button, push forward over centre until flat. A stop
  defines "flat" with the shoes a finger's width off the tyres.
* Numbers that land where we want: 100 lb strut at 4" from the pivot = 400 in·lb; cable off the lever at 2",
  handle at 20" (10:1 for the operator) → 200 lb of cable, 100 lb per shoe, ×2.5 leading-shoe → ~250 lb on each
  tread → about 0.14 g, two-thirds of what the tyres will give. The operator's extra 50 lb at the handle adds
  500 lb of cable and locks the wheels; the tyre caps it there.
* **Caveat: this fails released.** If nobody is at the handle nothing happens. Keep a no-operator layer: a trip
  cord from the handle along the lower deck so any rider can yank it through centre, and/or the drop chocks.

## Alternative: spring-applied shoe, pin-released (fails braked)

* Same arms and shoes, but a spring (two 100 lb gas struts per shoe, or a garage-door extension spring on a 2:1
  lever) pulls the shoe on. The arm is held off by a short cable to a **pelican hook** (sailing hardware, releases
  a loaded line with a small tug on its ring); lanyard on the ring to the rider, light zip tie through the ring as
  the vibration keeper. Fails braked if the lanyard, hook or cable goes; fails unbraked only if the spring breaks.
* Do not hold a 300 lb spring with a plain pin: a pin loaded in shear binds, and pulling it takes a 50–60 lb yank
  at the moment it must not stick.
* Re-cocking compresses a 200–300 lb spring: build in a 4:1 lever on the arm or use a small ratchet strap to the
  rail, so nobody does it with fingers next to the tyre.

## Stage two: drop chocks

* Rubber wheel chocks (5–6" high, ~35° face) hung by a strap from the rail just ahead of each rear tyre, held in
  a cradle by a pin on a rope to the rider. Pull the pin, the chock lands on its tether in the wheel path within
  one revolution; the tether keeps it aligned.
* A positive stop at walking pace: a 5" chock absorbs ~600 ft·lb lifting the rear, which at 2 mph stops the float
  in the length of the ramp at ~0.25 g. At 3 mph it is marginal (900 ft·lb to absorb, and the pitch unloads the rear
  wheels exactly as they climb), so it may hop the chock. A backstop for the shoes, not the brake.
* Chocks ahead of the rear wheels only stop forward motion. Houston is flat; one direction is probably enough.

## Guarding and loads into the frame

* The shoe arm snaps into a 16" tyre at parade speed; the tyre does not care, a hand does. Sheet-metal cover over
  the arm; the hoof skin can do double duty.
* Shoe normal force (~250–700 lb) goes into the rail bracket and the caster fork as a horizontal push at axle
  height; a 16" caster rated 1,200 lb shrugs that off (a kerb is worse). The braking force reaches the chassis
  through the caster plate: at 0.22 g that is ~230 lb per wheel × 17" of caster = 3,900 in·lb on the 4" plate,
  ~1,000 lb on the outer bolt pair, well inside a ⅜" Grade 5 with the crush sleeves.

## Open questions

* Shoe μ wet; try it on the actual tyres before trusting the 0.14 g figure.
* Strut sizing against the real lever and cable losses: expect to change the strut once.
* Whether the rear casters' forks have anywhere to mount the arm brackets, or everything hangs from the rail.
* If the design goes ahead, add the brackets and the cable run to the model and the cut list, and the arms to the
  hardware schedule.
