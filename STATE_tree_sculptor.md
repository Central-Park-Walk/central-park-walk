# STATE — cpw / tree-sculptor · updated 2026-08-25 (W-41)

**Target:** Blender sculptor → game-ready London-plane GLBs.

## Where we are
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. **W-41: overlay
instrument REPAIRED.** Cyan silhouette is now registered to the photo's
measured tree envelope (uniform scale on crown height + bole→bole pin,
derived from `segment_tree`/`measure_envelope` both sides; width free so
spread mismatch stays readable). Invariant tripwire fails the build at
>4% height / >2% bole error; speckle consolidated (sub-limb components
dropped). Verified: heights ≤1px, boles ≤2px, all stages; looked at all
three overlays. Awaiting Chris verdict on the repaired instrument.

**Habit through the honest instrument (new baseline `spread_ratio`,
sculpt/photo crown width at matched height):** young **1.03** ·
mature **1.625 (lower bound — see caveat)** · veteran **1.328**.
K6 naked mast + K7 menorah/streamers now show honestly on mature.

⚠ Caveats: (1) mature sculpt render clips at its own 512 frame — review-rig
camera too tight; widen before trusting mature spread. (2) scipy had vanished
from system python since July; restored to user-site (numpy 2.5.2 came with
it). Tip-host shell counts stay frozen (288/1920/1260).

## Budget (post W-39 bare / cards / tip_hosts)
young **62388** / **3720** / 155 · mature **126108** / **15864** / 661 ·
veteran **141768** / **17040** / 710.

## Open work
- `TS-1` habit · instrument repaired (W-41, awaiting verdict). Next: habit
  faults themselves — K6 mast, K7 menorah/streamers, mature/veteran
  over-spread (1.625/1.328 → ~1.0). Widen mature review camera first.
- `KB-1` exam assembly · queued after TS-1 verdict — exemplar meshes +
  fault-injection rig + Chris fault lists + Qwen-VL pull; roster
  Fable 5 vs Opus 5 vs Qwen-VL.
- `TS-7` crotches **PASS** · `TS-6` garden layout shipped (W-30)
- `TS-9` elbows deferred · `TS-5` bark dial · `TS-3` impostors · `TS-4` species

## ★ ONE NEXT HYPOTHESIS
> With the instrument honest, the dominant mature/veteran habit fault is
> structural: primaries fan near-horizontally from one attach band (menorah)
> instead of forking into ascending leaders at ~¼ height — fixing fork
> topology (not angles polish) should pull spread toward 1.0 and kill K6/K7
> together.

## Look at
`tmp/tree_sculpt/habit_refs/overlay_contact_sheet.png` (all three, repaired) ·
`tmp/tree_sculpt/habit_refs/habit_refs.json` (registration numbers).
