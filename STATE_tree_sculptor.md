# STATE — cpw / tree-sculptor · updated 2026-08-27 (post W-43b)

**Target:** Blender sculptor → game-ready London-plane GLBs.

## What just changed
**W-43 (2026-08-27): TS-10(a) DONE — Gate 1 PASS.** Real London-plane TLS in
hand: St Pancras Old Church (Wilkes/Disney/Boni Vicari, UCL; Zenodo
10.5281/zenodo.5070536, CC-BY 4.0), 97 segmented trees, RIEGL VZ-400 leaf-on,
0.04 m voxel. Data: `tmp/tree_sculpt/tls_stpancras/` (zip kept; T99/T27/T36
extracted; viewer `preview_clouds.py` → `gate1_contact.png`). **T99 =
presumptive armature specimen** (6.5 M pts, 37.6 m spread, scaffold sharply
readable, canonical habit). T36 = upright street form; T27 = cleanup-only.
Leaf-on occludes upper interior wood — acceptable (measured wood needed only
to the card layer). ⚠ Confirm T99 is not the dataset's one Hardy ash.
**W-43b:** docs' `godot4` symlink was a lie — real binary is
`"/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64"` (CLAUDE.md fixed,
`3af0b49`, unpushed). Earlier: ledger distilled → `docs/trees.md` §10
(read §10 before any unit of work; verdict PENDING Chris), commit `d9993d6`.

## Where we are
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. Overlay instrument
parked (W-41, kept). Honest habit numbers: spread_ratio young 1.03 · mature
1.625 (lower bound) · veteran 1.328; K6 naked mast + K7 menorah confirmed real
— TS-10 exists to fix these by construction. ⚠ scipy + PIL 10.2.0 in
user-site (numpy 2.5.2), NO matplotlib; tip-hosts frozen (288/1920/1260).
Budget (post W-39, bare/cards/tip_hosts): young 62388/3720/155 · mature
126108/15864/661 · veteran 141768/17040/710.

## Open work
- `TS-10` **(b) NEXT**: read TreeQSM (Raumonen 2013) + AdTree (Du 2019) —
  read, don't adopt — then design the from-scratch QSM fitter; then (c)
  skeleton → sculpt armature. First moves: ash-check T99, outlier strip,
  wood/leaf separation call.
- Chris confirms (both PENDING): ≥60 m confetti interactive check
  (wash-out → `TS-3` promoted; solid → headless rig flagged) · `docs/trees.md`
  §10 reads as HIS canon.
- `TS-1` habit PARKED · `KB-1` exam queued · `TS-7` crotches PASS · `TS-6`
  shipped · `TS-9` deferred · `TS-5` bark dial · `TS-3` impostors · `TS-4` species
- Attribution debt: CC-BY 4.0 credit (Wilkes/Disney/Boni Vicari, UCL) in
  README/docs, same commit as first shipped use of the derived skeleton.

## ★ ONE NEXT HYPOTHESIS
> A branch skeleton fitted to the T99 St Pancras point cloud, used as the
> sculpt armature, fixes the habit faults (K6 mast, K7 menorah, over-spread)
> **by construction** — measured fork topology replaces invented topology.
> Gate 1 (existence) PASSED. Gate 2 = the fitter design; it opens with the
> papers, not with code.

## Look at
`tmp/tree_sculpt/tls_stpancras/gate1_contact.png` — the three scanned planes.
Confetti check: `"$GODOT" --path . -- --eval-plot=london_plane_sculpt`,
walk back 40/60/100 m from mature + veteran.
