# Leaf-Back Trunk-Scaffold — Mesh-Disconnection Diagnosis (Engineer, read-only)

**Role:** Engineer (diagnosis) · Opus 4.8 (1M) · 2026-07-07 · **read-only** (no shared code, no
generator, no spec modified). Supersedes the high-level "one severed bridge" hypothesis carried into
this session. **Nothing fixed yet — reported for a Planner/Chris decision (design escalation).**

## TL;DR — the prior framing was wrong in a consequential way
- The **actually-rendered** trunk-scaffold mesh has **62 connected components**, not 3.
- The integrity diagnostic (`leafback_integrity_diag.py`) reported **3** only because its `edge_tubes`
  **omits the `radius` and `stem_id` vertex attributes** that the real render writes. Lacking `stem_id`,
  `stitch_bark_islands` falls back to island-keyed welding and fuses far more aggressively — so the
  diagnostic **under-reports the disconnection ~20×**. The tool is unfaithful.
- The disconnection is **not** a single bridging segment culled by one function. The mesh **is never
  connected at any stage**: `clean_degenerate_geometry` fuses the 973-tube soup down to only **250**
  components; `enforce_min_twig_diameter` is a **no-op** here; `stitch_bark_islands` then reaches
  **62** (real render, stem-keyed) or **3** (diagnostic, island-keyed).
- **Root cause (proven):** the prototype's throwaway preview skinner `edge_tubes` emits each skeleton
  edge as an independent tube framed in *its own* direction, so coincident-center rings at thick
  nodes/bends are offset **5–25 mm** — beyond the 5 mm weld tolerance. The junctions never fuse.

## Evidence

### Staged connected-component trace (`tmp/leafback_meshstage_diag.py`, Blender, reuses the 3 shared fns read-only)
Two builds of the **same** skeleton (`leafback_trunkscaffold_growth_graph.npz`, 974 nodes): one **WITH**
the `radius`+`stem_id` attributes (byte-for-byte what `leafback_trunkscaffold_render.py` renders), one
**WITHOUT** (what `leafback_integrity_diag.py` analyzes). Components after each stage:

| stage | WITH attrs (== real render) | WITHOUT attrs (== integrity diag) |
|---|---|---|
| raw tube soup | 973 | 973 |
| after `clean_degenerate_geometry` (5 mm weld) | **250** | 250 |
| after `enforce_min_twig_diameter` | 250 (no-op) | 250 (no-op, no `radius` attr) |
| after `stitch_bark_islands` | **62** ← FINAL RENDERED | **3** ← what the Critic was shown |

- `enforce_min_twig_diameter` is a **no-op**: the floor is 32 mm Ø = 16 mm radius, and the skeleton's
  **minimum** node radius is 18.1 mm — no vertex is below the floor. (In the diagnostic it also early-
  returns for lack of a `radius` attribute.) It cannot be the severing function.
- `stitch_bark_islands`, real render (stem-keyed): *"welded 1316 junction verts, deleted 551 strays,
  islands 250→~62, **61 large orphans KEPT+flagged**."* The render calls it with `verbose=False`, so
  those 61 kept orphans were logged **silently** — nobody saw them.
- `stitch_bark_islands`, diagnostic (island-keyed): *"welded 1756 junction verts, islands 250→~3."*
  Island keying welds same-position cross-island pairs regardless of strand, so it fuses ~440 more
  junctions than the stem-keyed path → only 3 components. Hence the 3-vs-62 discrepancy.
- The diagnostic's two orphans **exactly** match the critique's reported pieces: 190 v @(−1.83, 6.5,
  1.98) and 169 v @(3.0, 7.0, 1.53). Faithful reproduction of what the Critic saw; it just wasn't the
  whole story.

### Why `clean_degenerate_geometry` fuses only 250 (`tmp/leafback_ringweld_check.py`, numpy, read-only)
`edge_tubes` places each edge's 9-vertex ring in a frame built from *that edge's* direction (`u,v` from
`ref` ⟂ `t`), with independent angular phase. Two edges meeting at a node put two rings at the **same
center** `pos[n]` but in **different planes/phases**, so corresponding vertices are offset by
`~2·r·sin(Δ/2)` — **proportional to the node radius `r`**. Measured over the 748 multi-ring junctions:

- **107** junctions have a min inter-ring vertex gap **> 5 mm** (the weld tol) → cannot fuse. (A local
  proxy; the global union-find yields ~250 residual islands because a node can stay joined through one
  welded ring pair while another fails, and vice-versa — same cause, consistent direction.)
- Unweldable junctions' **median node radius = 33 mm vs 18 mm** for all nodes → **thick nodes are
  over-represented**, exactly as `gap ∝ r` predicts.
- Worst offenders are the **primary/trunk** nodes: gaps up to **25.4 mm** (5× the tolerance) at 77 mm
  and 114 mm radius nodes.

### Why the renders still look like a coherent tree
62 disconnected tubes that **geometrically overlap** at their junctions render as visually continuous
solid bark — the topological seams are invisible. The crown looked fine (and originally passed aesthetic
review) while being a shattered mesh. This is the same "separate tubes that only overlap" situation
`stitch_bark_islands` was written for — but that function's assumptions don't hold for this skinner (see
below).

## Why the shared functions can't rescue it here (semantic mismatch, not a bug in them)
The 3 shared mesh functions were tuned for **Mtree's ManifoldMesher**, whose consecutive tubes overlap
*within* the weld tolerance and whose `stem_id` marks genuinely distinct logical branches. This
prototype's `edge_tubes` violates both assumptions:
1. **Ring gaps exceed the 5 mm tol** (above) — Mtree's overlaps do not.
2. **`stitch_bark_islands`' `stem_id` "same-branch skip"** (which deliberately avoids welding within one
   branch, to preserve twig ring cross-sections) **declines to weld the same-strand junctions** that
   `clean_degenerate` missed — because along one strand every segment shares a `stem_id`. So exactly the
   junctions that most need rescuing are the ones stitch refuses to touch. (The island-keyed fallback in
   the diagnostic doesn't have this blind spot, which is why it reaches 3 not 62 — an accident, not a
   fix.)

## Production-skinning-path investigation (2026-07-07, read-only) — reconciles the above
A fan-out over `scripts/generate_trees_mtree.py` + runtime `.gd` established:
- **The production tree mesher is Mtree-internal ONLY:** `m_tree.ManifoldMesher().mesh_tree(tree)`
  (`generate_trees_mtree.py:2388-2391`) consumes an opaque `m_tree.Tree` C++ object. **It cannot skin a
  `(pos, parent, radius, strand)` node graph.** So the space-colonization skeleton has **no Mtree path** —
  shipping it *requires* a custom node-graph skinner promoted out of `tmp/`. The 3 shared cleaners are
  attribute-agnostic and carry over IF the skinner writes `radius`/`stem_id`/`hierarchy_depth`/`branch_extent`/
  `direction` (`mesh_utils.py:14-26`, read at `:2472-2475`,`:2792-2808`,`:4091-4094`,`:94-96`).
- **That custom skinner already has a Phase-A spike** (`docs/leafback_skin_spike_phaseA.md`,
  `tmp/leafback_skin_spike.py::build_tube_mesh`, 2026-07-06): a **per-STRAND** ring tube mesher that writes
  the "exact ManifoldMesher contract" (`radius`+`stem_id`+outward normals) and reuses the 3 shared steps. On
  the *old merge* skeleton it reached **~92 % connectivity (17 orphans)** via **surface-emergence base
  placement**. Its Go/No-Go: the blocker is **skeleton branch-topology, not skinning** → refine the skeleton
  (curved segments, valence cap, anti-crossing routing, enforced hierarchy), then re-spike. **Line C
  (trunk-scaffold) IS that refinement** (persistent leader, distributed scaffolds, growth-ordered caliber).

### ⇒ The 62-component result is largely a WRONG-SKINNER artifact
The trunk-scaffold render + Critic path skin with **`edge_tubes`** — one **independent** 18-vertex tube
**per edge**, no shared vertices — a naive **preview** skinner. The **production-candidate** skinner is the
per-**strand** `build_tube_mesh`, which shares ring vertices *along* a strand and is therefore far more
connected by construction (the spike's ~92 % on a worse skeleton vs `edge_tubes`' 62 pieces here). So
AC-5(iv) connectivity has been measured on the **wrong mesh in two independent ways**: (a) the diag omitted
attributes (now fixed → true 62 on `edge_tubes`), **and** (b) the entire review path uses the preview
`edge_tubes`, not the production-candidate `build_tube_mesh`. Connectivity should be judged on the per-strand
skinner, per Phase-A's own recommendation.

## The design-level questions this raises (→ Planner / Chris, per pipeline operating mode)
This is not a one-line "un-sever a bridge." Two escalations:

1. **What mesh does AC-5(iv) actually verify?** `edge_tubes` is a *throwaway preview skinner* living only
   in the tmp render/diag scripts. The trunk-scaffold **skeleton** is generated by
   `leafback_trunkscaffold.py` (space colonization) — **not** by Mtree. So how is this skeleton skinned
   *in production* (AC-8 integration)? If via Mtree's ManifoldMesher, the connectivity story is entirely
   different and "rendered mesh = 1 component" as currently measured tests a mesh that will never ship.
   If `edge_tubes` (or similar) *is* the intended skinner, it needs a **topology-aware weld** (share ring
   vertices across each parent/child edge, or scale the weld tol to node radius) rather than leaning on
   the Mtree-tuned shared functions. **This changes what/when AC-5(iv) verifies → a Planner spec (v4)
   decision, not an Engineer guess.**
2. **The AC-5(iv) tooling gave the Critic a wrong number.** Independently of the original Critic gestalt
   failure, `leafback_integrity_diag.py` itself was unfaithful (3 vs the true 62).
   **✅ FIXED 2026-07-07 (Engineer, diagnostic tool only — no shared/production code touched, uncommitted):**
   `leafback_integrity_diag.py`'s `edge_tubes` now attaches the same `radius`+`stem_id` vertex attributes
   the render writes (generic: `radius` always, `stem_id` when a `strand` array is present, so it stays
   honest for whatever skinner feeds it), and calls `stitch_bark_islands(..., verbose=True)` so the
   "N large orphans KEPT+flagged" line always surfaces. **Re-run against the iteration-2 growth render now
   reports connected components = 62** (matching the independent staged trace exactly: MAIN 2016 v +
   orphans 1096/853/847/579/523…), stitch runs stem-based, near-loop still = 0. Regenerated
   `..._growth_diag_components.png` / `..._diag_topdown.png` now visibly show the many islands (the trunk-
   spine is itself a separate piece). *Whether AC-5(iv) should be verified on `edge_tubes` output at all
   remains the open Planner question in (1) above — the tool is now honest about whatever it is pointed at.*
   Palette note (optional, non-blocking): the component render cycles a 7-colour palette, so with 62 pieces
   some non-adjacent orphans share a hue; a hashed/larger palette would make each orphan pop more distinctly
   for the Critic's R3 use.

## Re-spike: line-C skinned with the PRODUCTION-CANDIDATE per-strand skinner (2026-07-07, Chris-approved)
`tmp/leafback_trunkscaffold_skin.py` feeds line-C's skeleton to the verbatim Phase-A `build_tube_mesh`
(per-strand RMF tubes + `lbg.strand_polylines` surface-emergence base) + the 3 shared cleaners, and
measures all four asks. Result — **a qualified win, one bounded fix from clean:**

- **CONNECTIVITY: 2 components** (raw 225 → clean 144 → min-twig 144 [no-op] → **stitch 2**), vs the naive
  `edge_tubes`' 62. The **single orphan (1274 v)** is precisely diagnosed (`tmp/leafback_ts_orphan_diag.py`):
  it is **scaffold strand-1's entire sub-crown**, failing at ONE weld — node 25 (scaffold base, r 77mm) →
  node 24 (trunk-spine, r 122mm), both on the trunk axis (node 25 sits directly *above* node 24). The
  scaffold emerges **near-vertically**, so `strand_polylines`' surface-emergence offset (`0.9·r_parent·dir`)
  pushes the base *up the axis* not *radially to the trunk surface* → child base ring (77mm) sits concentric
  *inside* the trunk tube (122mm) → **45.3mm gap = (r_parent − r_child) > 32mm stitch tol** → no weld. Same
  class Phase-A fixed for *radial* branches; not yet handled for *axial* emergence. **Bounded front-end fix**
  (generalize the surface-emergence base to offset radially when emergence ∥ parent axis), not a structural
  failure of the skinner.
- **JUNCTION QUALITY: much improved** over the merge skeleton — skeleton max valence **4** (dist
  {0:225,1:544,2:188,3:15,4:2}), **0 degenerate faces**, every strand a clean chain (no dropped segments).
  Residual: **627 self-intersecting face-pairs (5.26%)** = raw tube-through-tube interpenetration at forks
  (child pierces parent surface, no smooth collar), worst at the thickest low scaffold, milder mid/upper
  (renders `leafback_ts_skin_junction{0..3}.png`). Acceptable-ish at tier review distance; a real quality gap
  vs ManifoldMesher's manifold forks. Faceting is RING=10 preview (prod would use ~24 + smoothing).
- **ATTRIBUTE CONTRACT:** `radius` (POINT/FLOAT, 18.1–190.5mm) + `stem_id` (POINT/INT) present → the 3
  cleaners' contract satisfied. **Still-missing for full AC-8 integration** (foliage placement + wind bake
  read these): `hierarchy_depth`, `branch_extent`, `direction`.

**Bottom line:** `edge_tubes` (per-edge) was the wrong artifact; the per-strand `build_tube_mesh` on line-C
gets essentially connected (2, one axial-emergence weld away from 1) with clean low-valence junctions — it is
the viable production skinning path. Remaining before promotion: (1) the axial-emergence base fix → re-verify
1 component; (2) provide the 3 missing attributes; (3) optional junction-collar/RING polish. **edge_tubes is
demoted to a fast preview tool — NOT a gating connectivity source (record in AC-5(iv)).**

## PROMOTED (2026-07-07, Chris-approved): `scripts/leafback_skinner.py`
The per-strand skinner + axial-emergence fix + full attribute contract are promoted out of `tmp/` into
**`scripts/leafback_skinner.py`** (the protected `tmp/leafback_graph.py` is intentionally NOT edited — a
corrected copy of `strand_polylines` lives in the new module; the two diverge deliberately). Verified on
line-C via `tmp/leafback_skinner_verify.py` at production **RING=24**:

- **Connected components = 1** (target 1) — **PASS**. The axial-emergence fix (offset the scaffold base
  RADIALLY onto the trunk surface when emergence ∥ axis) closed the 45.3mm orphan gap; stitch 72→1, 0 strays.
- **All 5 attributes present + type-correct:** radius [18–191mm], stem_id [0–224], **hierarchy_depth [0–4]**
  (trunk→quaternary), **branch_extent [0–24.6m]** (path length, monotone to tips), **direction** unit vectors
  (|dir| mean=1.000). So the wind bake + card placement contract is satisfied.
- **Junction quality:** 0 degenerate faces; self-intersecting face-pairs 6.51% = the **known, accepted,
  non-blocking** raw-interpenetration residual (Chris 2026-07-07) — intended remedy RING≈24 + smoothing at
  production time, logged in the module header so it is not rediscovered as a "new" bug.
- Component render `tmp/leafback_skinner_verify_components.png` = a single color island (vs the earlier 62).

Still ahead (NOT this session's scope): **AC-8 generator wiring** (feed line-C skeleton → `leafback_skinner`
→ london_plane GLB in `generate_trees_mtree.py`, regen, run `scripts/perf_gate.sh`) — a convergence gate; and
**Planner spec v4** (adopt per-strand skinner as the prod path; re-point AC-5(iv) to its output + a one-line
`edge_tubes`-is-preview-only demotion; define AC-8 = the attribute set + GLB export) — escalated now that
promotion has landed.

## Artifacts (all read-only, uncommitted, in gitignored `tmp/`)
- `tmp/leafback_meshstage_diag.py` — staged component trace (WITH vs WITHOUT attrs).
- `tmp/leafback_ringweld_check.py` — per-junction inter-ring gap vs node-radius analysis.
- No shared code, generator, or spec modified. No fix implemented (reported for decision).
