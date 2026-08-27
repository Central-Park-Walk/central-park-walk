# QSM fitter — design (TS-10b) · 2026-08-27

**Goal:** a from-scratch fitter that turns the T99 St Pancras TLS cloud into a sculpt
armature with **measured fork topology AND measured radii/taper**. Invented topology and
invented radii are the photo-confirmed defects (Chris FAIL 2026-08-27, `screenshots/
cpw_000..003.png`); anything this fitter derives instead of measures must be labeled so.

This doc is the compiled brief: it contains everything the implementation needs from
TreeQSM (Raumonen et al. 2013, Remote Sens. 5:491–520) and AdTree (Du et al. 2019,
Remote Sens. 11:2074) — both read in full, PDFs in `tmp/tree_sculpt/papers/`. **Read,
don't adopt** (from-scratch principle): we take the mechanisms, not the code.

## Input

`tmp/tree_sculpt/tls_stpancras/STP01_2017_T99.ply` — 6,545,385 pts, 37.6 m spread ×
28.9 m tall, leaf-on (2017-07-18), 0.04 m voxel downsample, binary PLY xyz, arbitrary
frame. CC-BY 4.0 (Wilkes/Disney/Boni Vicari, UCL) — **attribution debt rides the first
shipped derived skeleton** (README + docs, same commit).

Ash-check (2026-08-27): the record has no per-tree species table; morphology decides.
The Hardy ash was a modest churchyard tree (~10–15 m, gravestone ring); T99 is a
28.9 m × 37.6 m open-grown spreader with pendulous lower-skirt habit — plane, not ash.
**PASSED.** (Fallback dataset if St Pancras ever sours: TreeML-Data, Munich — W-43.)

## Prior-art digest — what we take, what we reject

| Mechanism | Source | Verdict |
| --- | --- | --- |
| Ball-count outlier filter (reject points whose r-ball holds < n pts) | TreeQSM §2.3 (1.5 cm/3 pts at 2–3 mm accuracy) | TAKE, rescaled to voxel grid |
| Cover sets + cut/study-region march; forks = connectivity splits of the study region | TreeQSM §2.8 + Appendix | REJECT as the spine — gap-fragile (AdTree Fig 15 shows it dropping limbs on imperfect clouds); leaf-on is the gap-rich case. Its **fork test** (connected components ahead of a moving front) survives inside our geodesic binning |
| Structure-tensor eigen-features per neighborhood (λ1≥λ2≥λ3 → elongated / planar / 3-D; branch direction from normals) | TreeQSM §2.6 | TAKE — this is the wood/leaf separator |
| Trunk = parallel + 2-D sets, grown from TBase; Ground removed by connectivity | TreeQSM §2.7 | TAKE, simplified (dataset is pre-segmented + cleaned; residue only) |
| Graph + shortest-path (Dijkstra/MST) skeleton — bridges occlusion gaps by construction | AdTree §3.1 | TAKE as the spine, on a kNN graph (Delaunay on 6.5 M pts is needless; gap-bridging recovered by explicit shortest inter-component links, TreeQSM §2.10 spirit) |
| Main-branch centralization (mean-shift) before skeletonizing — stops the MST wandering in wide crowns | AdTree §3.1 | TAKE — T99 is exactly the wide spreader this exists for |
| Vertex weight = subtree length (density-independent importance); merge indicator α, fixed σ=1.5 (robust 0.5–3); Douglas-Peucker on chains | AdTree §3.2 | TAKE for skeleton simplification |
| Cylinder fit: 7-param LSQ, init from region axis + median point-axis distance; second pass with outliers removed / distance weights w=1−d/dmax (Levenberg-Marquardt) | TreeQSM §2.9 + AdTree §3.3 | TAKE — this is the radius instrument |
| Radius priors: child ≤ ~parent, radius decreases away from base; used to *check* fits, not replace them | TreeQSM §2.9 | TAKE as sanity rails |
| Branch radii by allometry from trunk only, r ∝ subtree weight | AdTree Eq. 8 | REJECT for the measured region — derived radii are the defect. Allowed ONLY beyond the measured floor, labeled DERIVED |
| Gap filling: two explicit cases (parentless C near extensionless A → bridge cylinder; parentless C near fat transversal A → child stub) | TreeQSM §2.10 | TAKE, conservative ("only very clear cases" — their words) |

Accuracy facts that bound our trust (both papers):
- Trunk / large-scaffold radii: few-% error, robust to cover-scale choice (TreeQSM Tables 1–3, Fig 13).
- Branches < ~3 cm diameter: overestimated ~1 cm at 2–3 mm scan accuracy; foliage inflates
  diameters further (TreeQSM §3.3, §4). At our 0.04 m voxels this floor scales up — see D4.
- AdTree end-to-end mean cloud-to-model distance: 2.8–11.9 cm (their Table 1) — the
  realistic global-fit ceiling, not a target.

## Decisions (multi-position; the calls are made)

**D1 — skeleton spine: geodesic level-sets on a kNN graph** (not cover-set march, not
Delaunay-MST verbatim). Dijkstra geodesic distance from the base over a radius/kNN graph
of wood points; bin by distance; connected components per bin = nodes; component adjacency
across bins = edges and **forks — measured, not detected by heuristics**. Positions:
(a) TreeQSM cover-march — rejected above; (b) AdTree Delaunay-MST — right idea, wrong
cost/complexity at 6.5 M pts, and MST edges still need the level-set pass to become a
centered skeleton; (c) geodesic level-sets — same gap-robustness once inter-component
links are added, simplest honest from-scratch build, forks emerge from connectivity
(outputs, not parameters). **(c).**

**D2 — radii: fit where resolvable, derive-and-label beyond.** Per skeleton edge, collect
supporting points, LSQ cylinder (init: bin-centroid axis + median radial distance; pass 2:
drop >2.5σ radial outliers or distance-weight). Rails: child ≤ 1.1×parent, no radius
growth away from base (plateaus allowed — planes hold girth through scaffold runs).
Positions: AdTree allometry-only — rejected (derived = invented); TreeQSM fit-everywhere —
rejected (leaf-on inflation below the floor); hybrid — **chosen**. The rails may VETO a
fit (fall back to interpolation, flagged), never inflate one.

**D3 — wood/leaf separation: structure-tensor linearity + trunk-connected growth.**
Two scales (~0.15 m, ~0.30 m); wood = elongated (λ1-dominant) neighborhoods reachable
from the trunk seed through elongated territory; leaves = the rest. Leaf points are
EXCLUDED from radius fits, kept for a crown-envelope sanity overlay. The separator gets
its own visual gate (G1) before anything downstream trusts it.

**D4 — the measured floor is 3 voxels: diameter ≥ 0.12 m.** Below it a 0.04 m-voxel
cloud cannot resolve a radius (TreeQSM's <3 cm warning, scaled). Edges below the floor
get taper-continuation from their measured parent path, `source: DERIVED`. The sculptor
may use DERIVED radii but the ledger score counts only the MEASURED region. Trunk +
primary + most secondary scaffold of a mature plane sit well above 0.12 m — the K6/K7/
no-taper territory is fully covered by MEASURED wood.

**D5 — validation is deliverable-first, and the instrument gets a null.**
- **G0 (null, before T99):** run the fitter on a synthetic cloud sampled from a known
  cylinder-tree (generate from our own compiled sculpt, radii known exactly). Recovered
  radii within 2·SEM of truth on every segment ≥ floor, forks 1:1 — or the instrument is
  broken and T99 results are void. (Standing rule: confirm the null on a path you know.)
- **G1 (look):** skeleton + radii rendered over the cloud, same orthographic projections
  as `gate1_contact.png`, one contact sheet. Forks correspond; no leaf-mass routing.
- **G2 (numbers):** trunk taper profile monotone-ish; DBH in the mature-plane field range
  (~0.6–1.2 m). Metrics may FAIL the fit; they may never CLEAR a defect visible in G1.

## Pipeline (implementation order, TS-10c)

1. `qsm/load.py` — PLY read, ball-count outlier strip (r = 0.06 m, min 3), residue/seam
   crop. 2. `qsm/woodleaf.py` — D3 separator + G1a sheet. 3. `qsm/skeleton.py` — kNN
   graph (r ≈ 0.10 m), inter-component bridges, Dijkstra from base, bins ≈ 0.25 m
   (≥ local diameter, TreeQSM region rule), centroid nodes, AdTree simplification
   (σ = 1.5). 4. `qsm/radii.py` — D2 fits + rails + D4 floor. 5. `qsm/export.py` —
   JSON: `nodes[{id,xyz}], edges[{a,b,r_a,r_b,source,order}]` → Blender armature
   importer (the sculptor's `build_curve_bevel_bark` consumes radii as spline bevel
   inputs — joins stay topology, per docs/trees.md §10).

Scales rescale from the papers by one ratio — their d ≈ 1–3 cm at 2–3 mm accuracy, ours
×4 at 4 cm voxels. That one tuned ratio is the pipe-model transfer test: if a second
tree (T36) needs per-tree re-tuning beyond it, the design is wrong (generalizability
tell). numpy + scipy (cKDTree, sparse.csgraph, least_squares) + PIL — all in user-site;
no matplotlib, no new deps.

## Non-goals

Leaves/foliage geometry (cards remain the sculptor's job) · fine twigs (⛔ rail — wood
is measured only up to the card layer) · species stats, biomass, forestry metrics ·
multi-tree segmentation (dataset is pre-segmented).
