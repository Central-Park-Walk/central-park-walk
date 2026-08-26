# STATE — cpw / tree-sculptor · updated 2026-08-25 (W-42, advisory)

**Target:** Blender sculptor → game-ready London-plane GLBs.

## What just changed (W-42, advisory — no build)
Chris canonized the **from-scratch principle** (`CLAUDE.md` §Taste, `01a6fec`):
the mtree/SpeedTree ⛔ = never BUY someone else's solution to a creative
problem; study prior art, build our own; showing off is the point. Grass and
sky are **NOT done** (index corrected). Representation call: **mesh models
stay ≥1 yr**; splats deferred (capture-not-author, no relight/wind/instancing);
watch item = splat-baked mid-range LOD vs card-confetti, revisit ~6 mo.
New endorsed lane: open **TLS scan of a real London plane + from-scratch QSM
skeleton-fitter** as sculpt armature — verify a usable open scan EXISTS first.

## Where we are (from W-41)
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. Overlay instrument
REPAIRED (W-41): cyan silhouette registered to photo envelope (crown-height
scale + bole pin; width free); tripwire fails build at >4% height / >2% bole.
Verified ≤1px/≤2px all stages; all three overlays looked at.
**Awaiting Chris verdict on the repaired instrument.**
Honest `spread_ratio` (sculpt/photo crown width): young **1.03** ·
mature **1.625 (lower bound — sculpt render clips its 512 frame; widen
review-rig camera first)** · veteran **1.328**. K6 naked mast + K7
menorah/streamers now show honestly.
⚠ scipy restored to user-site (numpy 2.5.2); tip-host counts frozen
(288/1920/1260).

## Budget (post W-39 bare / cards / tip_hosts)
young **62388** / **3720** / 155 · mature **126108** / **15864** / 661 ·
veteran **141768** / **17040** / 710.

## Open work
- `TS-1` habit · instrument repaired (W-41), awaiting verdict. Then habit
  faults: K6 mast, K7 menorah/streamers, mature/veteran over-spread
  (1.625/1.328 → ~1.0). Widen mature review camera first.
- `TS-10` TLS ground truth (NEW, W-42) · verify an open London-plane TLS
  scan exists; if yes, from-scratch QSM skeleton-fitter → sculpt armature.
- `KB-1` exam assembly · queued after TS-1 verdict (exemplars +
  fault-injection + Chris fault lists + Qwen-VL; roster Fable 5/Opus 5/Qwen-VL).
- `TS-7` crotches PASS · `TS-6` garden shipped · `TS-9` elbows deferred ·
  `TS-5` bark dial · `TS-3` impostors · `TS-4` species

## ★ ONE NEXT HYPOTHESIS (unchanged by W-42)
> With the instrument honest, the dominant mature/veteran habit fault is
> structural: primaries fan near-horizontally from one attach band (menorah)
> instead of forking into ascending leaders at ~¼ height — fixing fork
> topology (not angle polish) should pull spread toward 1.0 and kill K6/K7
> together.

## Look at
`tmp/tree_sculpt/habit_refs/overlay_contact_sheet.png` (all three, repaired) ·
`tmp/tree_sculpt/habit_refs/habit_refs.json` (registration numbers).
