# STATE — cpw / tree-sculptor · updated 2026-08-27 (post W-43)

**Target:** Blender sculptor → game-ready London-plane GLBs.

## What just changed
**2026-08-27 (W-43): TS-10(a) DONE — Gate 1 PASS. The TLS ground truth exists
and is IN HAND.** St Pancras Old Church TLS (Wilkes/Disney/Boni Vicari, UCL;
Zenodo 10.5281/zenodo.5070536, CC-BY 4.0): 97 segmented trees, predominantly
*Platanus × hispanica*, RIEGL VZ-400 leaf-on, 0.04 m voxel, binary PLY. Data:
`tmp/tree_sculpt/tls_stpancras/` (958 MB zip kept; T99/T27/T36 extracted;
viewer `preview_clouds.py` → `gate1_contact.png`). **T99 = presumptive armature
specimen** (6.5 M pts, 37.6 m spread × 28.9 m, trunk + primary scaffold sharply
readable, canonical LP habit incl. pendulous skirt). T36 = upright street form.
T27 = cleanup-only (outlier residue + neighbor-cut seam). Leaf-on occludes
upper-crown interior wood — acceptable: measured wood is needed only up to the
card layer. ⚠ Confirm T99 is not the dataset's one Hardy ash before fitting.

Earlier same day (maintenance): first `/distill` of this ledger — sculptor
canon now lives in **`docs/trees.md` §10; read it before any unit of work**
(replaces re-reading the ledger). Commit `d9993d6`, verdict PENDING Chris.

## Where we are
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. Overlay instrument
parked (repaired W-41, kept). Honest habit numbers stand: spread_ratio young
1.03 · mature 1.625 (lower bound) · veteran 1.328; K6 naked mast + K7
menorah/streamers confirmed real — TS-10 exists to fix these by construction.
⚠ scipy in user-site (numpy 2.5.2), PIL 10.2.0 available, NO matplotlib;
tip-host counts frozen (288/1920/1260).

## Budget (post W-39 bare / cards / tip_hosts)
young **62388** / **3720** / 155 · mature **126108** / **15864** / 661 ·
veteran **141768** / **17040** / 710.

## Open work
- `TS-10` **(b) is NEXT**: read TreeQSM (Raumonen et al. 2013) + AdTree
  (Du et al. 2019) — read, don't adopt — THEN design the from-scratch QSM
  skeleton-fitter; then (c) fitted skeleton → sculpt armature. First moves in
  (b): ash-check T99, strip T27-class outliers, wood/leaf separation call.
- `TS-1` habit · PARKED; resume differencing once a TS-10-armatured sculpt is
  within shouting distance of reference.
- `KB-1` exam assembly · queued (exemplars + fault-injection + Chris fault
  lists + Qwen-VL; roster Fable 5/Opus 5/Qwen-VL).
- `TS-7` crotches PASS · `TS-6` garden shipped · `TS-9` elbows deferred ·
  `TS-5` bark dial · `TS-3` impostors · `TS-4` species
- Attribution debt: CC-BY 4.0 — credit Wilkes/Disney/Boni Vicari (UCL)
  wherever the derived skeleton ships (README/docs), same commit as first use.

## ★ ONE NEXT HYPOTHESIS
> A branch skeleton fitted to the T99 St Pancras point cloud, used as the
> sculpt armature, fixes the habit faults (K6 mast, K7 menorah, over-spread)
> **by construction** — measured fork topology replaces invented topology.
> Gate 1 (existence) PASSED 2026-08-27. Gate 2 is the fitter design, and it
> opens with the papers, not with code.

## Look at
`tmp/tree_sculpt/tls_stpancras/gate1_contact.png` — the three scanned planes.
`docs/trees.md` §10 — sculptor canon, verdict still PENDING whether it reads
as YOUR canon. Also pending your side: interactive confirm of the ≥60 m
confetti (LEDGER ## 47).
