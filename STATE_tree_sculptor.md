# STATE — cpw / tree-sculptor · updated 2026-08-27 (post W-44)

**Target:** Blender sculptor → game-ready London-plane GLBs. Sculpt stages FAILED Chris's
field look 2026-08-27 (not tree-shaped: K6 mast, K7 menorah, NO-TAPER sausages) — invented
topology + invented radii. TS-10 (TLS → QSM armature) is structural necessity, not polish.

## What just changed
**W-44: TS-10(b) DONE.** TreeQSM + AdTree read in full (PDFs `tmp/tree_sculpt/papers/`);
**`docs/qsm_fitter.md` is the binding fitter design** — the compiled brief; implementation
sessions must NOT re-read the papers. Core calls: geodesic level-set skeleton on kNN graph
(forks measured as bin-component adjacency) · cylinder-LSQ radii, rails child≤1.1×parent /
no growth away from base · wood/leaf via structure-tensor linearity from trunk seed ·
**measured floor Ø ≥ 0.12 m** — below it radii are DERIVED and labeled · gates G0 synthetic
null BEFORE T99, G1 contact-sheet look, G2 taper/DBH. Ash-check T99 PASS (morphology:
28.9 m × 37.6 m spreader ≠ the ~10–15 m Hardy ash; Zenodo has no species table).

## Where we are
Armature specimen = T99 (6.5 M pts, leaf-on, 0.04 m voxel) in `tmp/tree_sculpt/
tls_stpancras/`. Compile = `build_curve_bevel_bark` (consumes radii as bevel inputs).
scipy + PIL in user-site, NO matplotlib. tip-hosts frozen (288/1920/1260). Budget (W-39):
young 62388/3720/155 · mature 126108/15864/661 · veteran 141768/17040/710.

## Open work
- `TS-10` **(c) NEXT**: implement `qsm/` stages 1–3 (load+strip, wood/leaf, skeleton) per
  `docs/qsm_fitter.md` §Pipeline; pass **G0 (synthetic null) then G1 (look)** before any
  radius work. Then stages 4–5 (radii + export) → sculpt armature.
- Chris PENDING: `docs/trees.md` §10 reads as HIS canon?
- Attribution debt: CC-BY 4.0 (Wilkes/Disney/Boni Vicari, UCL) in README/docs, same commit
  as first shipped use of the derived skeleton.
- `TS-1` habit PARKED · `KB-1` exam queued · `TS-5` bark dial · `TS-3` impostors · `TS-4` species

## ★ ONE NEXT HYPOTHESIS
> The G0 null passes and the T99 skeleton's G1 contact sheet shows forks that correspond
> to the cloud with no leaf-mass routing — i.e., the fitter design survives contact with
> the data at the topology stage, before any radius is trusted.

## Look at
`docs/qsm_fitter.md` — the design (10-min read). `screenshots/cpw_000..003.png` — the FAIL
this exists to fix. `tmp/tree_sculpt/tls_stpancras/gate1_contact.png` — T99.
