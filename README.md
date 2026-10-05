# War Pig Beer Bike Float Frame

There have been many war pigs since the mascot was logingly adopted, including a couple iterations of the wooden Beer Bike float. The current woden float has suffered repeated buckling of the 4x4 frame, which is now split beyond repair and prompts us to reimagine the base of the pig again.

A warning lives in the nose of the current wooden pig:
> Hello    
> If you   
> decide to rebuild  
> this pig, do NOT  
> just copy each piece.  
> They are not equal.  
> It is a nightmare.  
> Good luck.  
> ♡ Loryn H. '21  


Sounds like a good idea then.

In this repository you will find structural models of a bolted perforated-square-steel-tube frame for an 8 × 8 × 8 ft octagonal War Pig, replacing the rotting 5-year-old wood frame. Space-frame analysis in [PyNite](https://github.com/JWock82/Pynite), with an interactive 3D viewer, cut list, joint schedule and caster loads.

> These are parametric models built so the team can change dimensions, loads and tube sizes and see the consequences. Before we ride on it, have an engineer review and/or test it well.

**Site:** https://wiess-college.github.io/WarPig/

| Design | What | Page |
|---|---|---|
| [`Beer-Bike-Float/`](Beer-Bike-Float/) | Octagon body with snout and tail, 2½" chassis at deck level, open sides for doors, hatch in the upper deck. PyNite space-frame check with 3D viewer. | ([/WarPig/Beer-Bike-Float/](https://wiess-college.github.io/WarPig/)) | 

## Instructions
To add a design: copy a directory, edit its `model/frame_model.py`, add a row above. The workflow finds every
`*/model/frame_model.py`, runs it, builds that design's page and assembles the site.

One-time setup for the site: Settings → Pages → Build and deployment → Source: **GitHub Actions**.
