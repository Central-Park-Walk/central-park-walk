# STATE — cpw / tree-sculptor · updated 2026-08-27 (post Chris field verdict)

**Target:** Blender sculptor → game-ready London-plane GLBs.

## What just changed
**CHRIS FIELD VERDICT (2026-08-27, interactive, `screenshots/cpw_000..003.png`):
the sculpt stages are NOT tree-shaped — FAIL at basic silhouette level.**
Veteran = untapered balloon-sausage limbs, parallel up-curled blunt stubs (K7
extreme), no crown subdivision, no taper. Young = bare kinked pole (K6) + a
sparse noodle-tangle. This FALSIFIES W-47's "mature credible at 20–40 m" —
the headless contact sheet flattered the forms; field observation supersedes.
Confetti question MOOT while the near view fails. Faults = invented topology
+ invented radii — exactly the TS-10 target: the QSM must deliver measured
forks AND measured taper from the scan, or TS-10 has failed.

**W-43 (same day): TS-10(a) Gate 1 PASS.** St Pancras Old Church TLS (UCL,
Zenodo 10.5281/zenodo.5070536, CC-BY 4.0), 97 segmented planes, leaf-on,
0.04 m voxel → `tmp/tree_sculpt/tls_stpancras/` (T99/T27/T36 extracted;
`preview_clouds.py` → `gate1_contact.png`). **T99 = presumptive armature
specimen** (6.5 M pts, 37.6 m spread). ⚠ Confirm T99 isn't the one Hardy ash.
Leaf-on occludes upper interior wood — acceptable (wood needed only to card
layer). W-43b: real Godot = `"/home/chris/godot 4/Godot_v4.6.1..."` (quoted —
spaced dir); F12 screenshots → `screenshots/cpw_NNN.png`, counter resets/run.

## Where we are
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. Overlay parked
(W-41, kept). K6 + K7 now photo-confirmed interactively, joined by NO-TAPER
(radius profile) as a first-class fault. spread_ratio young 1.03 · mature
1.625 (LB) · veteran 1.328. ⚠ scipy + PIL in user-site, NO matplotlib;
tip-hosts frozen (288/1920/1260). Budget (W-39 bare/cards/tip_hosts): young
62388/3720/155 · mature 126108/15864/661 · veteran 141768/17040/710.

## Open work
- `TS-10` **(b) NEXT**: read TreeQSM (Raumonen 2013) + AdTree (Du 2019) —
  read, don't adopt — then design the from-scratch QSM fitter (must output
  radii/taper, not just topology); then (c) skeleton → sculpt armature.
  First moves: ash-check T99, outlier strip, wood/leaf separation call.
- Chris PENDING: `docs/trees.md` §10 reads as HIS canon? (Confetti check
  superseded by the FAIL verdict above.)
- `TS-1` habit PARKED · `KB-1` exam queued · `TS-7` crotches PASS · `TS-6`
  shipped · `TS-9` deferred · `TS-5` bark dial · `TS-3` impostors · `TS-4` species
- Attribution debt: CC-BY 4.0 credit (Wilkes/Disney/Boni Vicari, UCL) in
  README/docs, same commit as first shipped use of the derived skeleton.

## ★ ONE NEXT HYPOTHESIS
> A skeleton fitted to the T99 St Pancras cloud, used as the sculpt armature,
> fixes K6 mast, K7 menorah, over-spread AND the no-taper sausages **by
> construction** — measured forks and measured radii replace invented ones.
> Gate 1 (existence) PASSED; Chris's FAIL verdict makes this structural
> necessity, not polish. Gate 2 = fitter design; opens with the papers.

## Look at
`screenshots/cpw_000..003.png` — Chris's FAIL evidence (veteran + young).
`tmp/tree_sculpt/tls_stpancras/gate1_contact.png` — the real trees we now own.
