# WarPig

Design files for the parade float: a bolted perforated-square-steel-tube frame replacing the old wood one.
Each design lives in its own directory with its model, viewer and export files, and the site is rebuilt from all
of them on every push to `main`.

**Site:** https://lonestarmac.github.io/WarPig/

| Design | What | Page |
|---|---|---|
| [`Beer-Bike-Float/`](Beer-Bike-Float/) | Octagon body with snout and tail, 2½" chassis at deck level, open sides for doors, hatch in the upper deck. PyNite space-frame check with 3D viewer. | [/Beer-Bike-Float/](https://lonestarmac.github.io/WarPig/Beer-Bike-Float/) |

To add a design: copy a directory, edit its `model/frame_model.py`, add a row above. The workflow finds every
`*/model/frame_model.py`, runs it, builds that design's page and assembles the site.

One-time setup for the site: Settings → Pages → Build and deployment → Source: **GitHub Actions**.
