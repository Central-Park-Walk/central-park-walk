# Leaf-Back Skeleton Connection — Redesign Plan (v2 merge)

> **⏸ STATUS — PAUSED 2026-07-06 (see [Closing summary](#closing-summary--why-this-line-is-paused-2026-07-06) at the bottom).**
> This document is the **standalone, chronological history** of the `build_graph_v2`
> merge-based skeleton line: Stages 1 → 1b → 2 → 2b → 2c (original diagnosis, every fix, every
> verification, every honest residual). The line is being **paused, not abandoned**, in favour
> of prototyping a **space-colonization / attractor-based growth** method as a comparison. The
> merge code (`tmp/leafback_graph_v2.py`) and all diagnostic/render scripts **stay in place,
> uncommitted in `tmp/`** — only this `.md` and the diagnosis `.md` are committed as the record.
>
> **Prototype discipline held throughout:** v2 is an isolated, swappable function; the old
> `leafback_graph.py::build_graph()` was left untouched, and the three shared mesh functions
> (`clean_degenerate_geometry` / `enforce_min_twig_diameter` / `stitch_bark_islands` in
> `scripts/generate_trees_mtree.py`) were **never modified across any stage** (verified: that
> file is unmodified in git). **Date:** 2026-07-06 · **By:** Opus 4.8 (1M).
> Follows [`leafback_skeleton_topology_diagnosis.md`](leafback_skeleton_topology_diagnosis.md).

> **Original design writeup, written BEFORE code** (per task). Proposes a replacement for the
> proximity grid-cell merge in `leafback_graph.py::build_graph()`.

## What's being replaced (and what's kept)
**Kept:** the leaf-back philosophy (fill crown envelope with sprigs → connect inward), the
graph data structure (parent index, `children` map, `strand`/stem_id, pipe-model radius),
and the funnel-to-fork-to-root termination. The diagnosis confirmed the data structure is
fine and reusable.

**Replaced:** only the **merge criteria + direction assignment.** Today: every active node
in a shared grid cell fuses to **one centroid parent** → valence 4-8 bursts, and each
segment direction is a raw `child → centroid` vector → no angle control. v2 replaces the
"all-in-a-cell → one centroid" step with a **valence-capped, dominant-continuation,
angle-aware greedy agglomeration.**

## v2 algorithm — "capped dominant-continuation merge"

Per active node, state carries `pos`, `axis` (unit vector pointing **leaf-ward** = the
direction its subtree extends), `mass` (accumulated sprig count ∝ pipe thickness), `strand`,
`id`, `parent`. Sprig leaves init `mass=1`, `axis = normalize(pos − fork)` (radially outward).

Merge loop over levels L, with a **neighbour radius** `R_L = R0·g^L` (a *search* radius, not
a bin — this is the key change from grid cells):

1. **Order active nodes by decreasing `mass`** so thick strands anchor first.
2. **Greedy grouping, hard valence cap K = 3, target 2:**
   - For each unclaimed anchor `A`: gather unclaimed neighbours within `R_L`, nearest first.
   - Add a neighbour `B` to the group only if it passes the **sibling angular-spacing test**
     (below) against every member already in the group, until the group hits `K`.
   - A group of size 1 = `A` had no admissible neighbour → it **carries forward unchanged**.
3. **Create the parent (the connection + direction logic):**
   - **Dominant continuation `D`** = the group member with the **highest `mass`** (tiebreak:
     best axis-continuation, i.e. the member whose `axis` is most anti-parallel to the
     trunk-ward direction). The parent **inherits `D`'s strand**; the other members become
     **laterals** whose strands terminate into the parent.
   - **Direction inheritance / curvature smoothing:** the parent's trunk-ward growth
     direction is `cont = normalize( lerp( −D.axis , trunk_dir , w_L ) )` where
     `trunk_dir = normalize(fork − centroid)` and `w_L` (trunk-pull weight) rises with level.
     This makes the dominant **strand flow smoothly** (inherits the child's heading, bent
     gently toward the trunk) instead of jumping to a raw centroid.
   - **Placement:** `parent.pos = D.pos + step · cont` (a step trunk-ward from the dominant
     child, *not* the centroid). `parent.mass = Σ member mass` (pipe accumulation).
   - Each member's `parent = parent.id` → **valence = group size ≤ 3** by construction.
4. Terminate when ≤3 active → wire to `fork` → `root`; then pipe-model radius + strand
   re-derivation (unchanged from v1).

### The four required rules, resolved
| Requirement | v2 rule | Value | Justification |
|---|---|---|---|
| **Valence cap** | group size hard-capped at K, most events bifurcate | **K=3, target 2** | Real forks are predominantly bifurcations, occasionally trifurcations; valence ≥4 reads as an artifact (diagnosis: median 4, up to 8). 3 admits the real trifurcation without allowing bursts. |
| **Dominant continuation** | highest-`mass` member continues the strand + sets direction; others are laterals | mass = Σ sprigs | See below. |
| **Sibling angular spacing** | a candidate child is rejected if `angle( child−A , member−A ) < θ_min` for any accepted member | **θ_min = 35°** | Below ~30° two branches overlap/read colinear (the "spray"); 35° gives visible separation without a forced fan. |
| **Curvature / direction** | parent direction = `lerp(−D.axis, trunk_dir, w_L)` (inherit + bend), placed along it | `w_L` ramps 0.15→0.6 | Inheriting the dominant's heading and bending gently toward the trunk removes the sharp centroid-jump "spray"; ramping trunk-pull guarantees funnel convergence. |

### Dominant-vs-lateral decision when 3+ compete — **cumulative thickness (`mass`)**, tiebreak direction
Chosen over "strand length so far" and "continuation-direction similarity" as the *primary*
metric because: (1) it matches the **pipe model already in use** (`r^p = Σ child r^p`) — the
thicker branch *is* the dominant limb by construction, so strand assignment and radius stay
consistent; (2) it is **botanically correct** — the main axis is the one carrying the most
downstream foliage/mass; (3) it is **monotonic and stable** — a strand only gains mass
trunk-ward, so the dominant never flip-flops. Direction-continuation is the **tiebreak**
(keeps strands straight when masses are near-equal, e.g. at the twig tips where every sprig
has mass 1).

## Why this fixes the three observed defects
- **Valence 8 bursts →** capped at 3, and θ_min further trims most events to 2. The
  proximity merge's "everything in the cell" is gone.
- **Scattered sibling angles →** θ_min guarantees separation; no two children overlap.
- **Sharp spray / straight sticks →** direction is inherited from the dominant and bent
  smoothly toward the trunk, so strands read as continuous curved limbs, and laterals leave
  at a controlled angle rather than pointing at a centroid.

## Isolation + validation plan
- v2 lives in a **new file `tmp/leafback_graph_v2.py`** (`build_graph_v2()` + helpers).
  `leafback_graph.py::build_graph()` is **not edited** — both paths run side by side.
- **Validate on a small subset only:** extract the leaf-descendants of the diagnosis's worst
  junctions (old nodes **1002 / 1005 / 814**, valence 8/8/7) and re-connect each *local*
  cloud with v2 (and, as a controlled A/B, with the old merge on the identical input).
  Report **before/after valence + branching-angle spread + a rendered close-up** comparable
  to the reviewed junction renders. **No full-tree run, no mesh-function edits, no commit.**

## Risks / open questions (for review, not resolved here)
- Convergence speed: capped merges reduce count slower than grid-cell bursts → more levels
  (more hops). That is *desirable* (finer hierarchy) but must still terminate — handled by
  the ramping trunk-pull `w_L` and the ≤3-active stop.
- `step` and `R0/g` need tuning; the subset validation is where those numbers get set.
- v2 changes hop counts vs the validated envelope work — envelope/aspect are unaffected
  (same sprig fill), but the depth-as-output numbers will differ; that's expected and
  re-measured when/if v2 is promoted.

---

## Validation results (small subset — NOT committed, prototype only)

Implemented in **`tmp/leafback_graph_v2.py`** (`build_graph_v2()` — isolated; the old
`build_graph()` is untouched). Validated on the three diagnosis junctions by extracting each
one's leaf-descendant cloud from the old graph and re-connecting it with v2.

### Before / after — valence + sibling angle
| junction | BEFORE (old grid-cell) | AFTER (v2 capped) |
|---|---|---|
| node 1002 | **valence 8**, min-sibling **5°**, 27 leaves | **max-valence 3**, mean 2.44, min-sib **31°**, median **87°** |
| node 1005 | **valence 8**, min-sibling **8°**, 26 leaves | **max-valence 3**, mean 2.67, min-sib **27°**, median **59°** |
| node 814 | **valence 7**, min-sibling **12°**, 7 leaves | **max-valence 3**, mean 2.20, min-sib **69°**, median **90°** |

Every burst collapsed to **valence ≤3** (mean ~2.2–2.7 — i.e. mostly bifurcations, the
target). Median sibling angle rose from 5–12° to **59–90°** (clear separation). The residual
min-sibling of 27–31° at nodes 1002/1005 is the **terminal fork-node wiring**, which bypasses
the θ_min drop-check — internal forks satisfy θ_min≥35° by construction; applying the same
rule at fork wiring is the one small gap left (noted, not a design flaw).

### Renders
- **`tmp/leafback_v2_junction_compare.png`** — wireframe, old subtree vs v2, coloured by
  strand with linewidth ∝ radius: OLD = all edges into one burst point; v2 = a bifurcating
  tree with a **thick dominant strand + thin laterals** at separated angles.
  ⚠ **Clarification (2026-07-06 verify):** each v2 panel plots the **whole** reconnected
  subtree (44/40/11 edges over 45/41/12 nodes), *not* one node's edges — so the 10+ coloured
  segments are the many strands, and "max-val 3" is the per-node max over all its internal
  nodes. Hard check confirmed **zero nodes with valence >3** in every reconstruction. For a
  strict at-a-glance count see **`tmp/leafback_v2_singlenode_stars.png`** (each node's parent
  edge + its ≤3 children only: OLD 1002/1005/814 = 8/8/7 children; v2 worst node = 3).
- **`tmp/leafback_v2_tube_OLD.png` / `_V2.png`** — tube renders (existing mesh steps reused
  read-only), directly comparable to the reviewed junction closeups. OLD = ~8 equal-thickness
  sticks radiating from one point (starburst); **v2 = a thick tapered dominant limb shedding
  thin laterals at controlled angles** — a branch, not a spray. (Residual tube-overlap at the
  forks is the *skinning* layer, out of scope for this skeleton-connection task, and far
  milder than the old burst.)

### Stage 1 — fork-node wiring gap (2026-07-06, uncommitted)
Applied θ_min at fork-node wiring: the trunk fork's remaining ≤3 actives now go through a
spacing pass that **merges any too-close pair into an intermediate sub-fork** (dominant
continues) instead of attaching both to the fork. Re-measured the 3 flagged nodes:

| node | min-sib BEFORE Stage 1 | min-sib AFTER Stage 1 | max valence (after) |
|---|---|---|---|
| 1002 | 31° | **38°** ✓ (was at the fork node) | 3 (0 violations) |
| 1005 | 27° | **30°** (fork node now ≥35°; residual moved to an *intermediate*) | 3 (0 violations) |
| 814 | 69° | 69° (already clean) | 3 (0 violations) |

Valence cap **not regressed** (max 3, zero nodes >3 in all three). Residual after the first
Stage-1 pass: 1005 still had a 30° pair at an intermediate whose two source branches are
near-parallel — resolved by the DROP policy below.

### Stage 1b — near-parallel DROP policy (2026-07-06, uncommitted)
**Decision: DROP (not Relocate).** When a too-close fork pair cannot be separated even by the
best intermediate placement (i.e. it is genuinely near-parallel), the **weaker branch — by
the SAME cumulative-mass dominance used for strand continuation everywhere else, so no second
"who wins" is introduced** — is dropped, and its downstream foliage is **absorbed onto the
dominant branch's subtree** at valence-safe, best-spaced host nodes. Chosen over Relocate
because the flagged 1005 case is a mass-24 dominant limb (already valence-3) beside a mass-2
twig: Relocate-fuse (union children → 5) and a naive Drop-graft onto the dominant (→4) both
**violate the K=3 cap**, whereas absorbing the weak twig's tips onto sub-nodes with room does
not; and Relocate would blend two headings into a synthetic centroid node, contrary to
"dominant keeps its heading". Implemented as a fallback *inside* the Stage-1 fork loop (try
intermediate first; drop only if it can't reach θ_min).

**Re-measured all 3 flagged nodes — every check passes:**
| node | min-sib (every internal node) | max valence / >3 | branches dropped | foliage (orig sprigs reachable) |
|---|---|---|---|---|
| 1002 | **37.5°** ✓ | 3 / none | 0 (intermediate sufficed) | 27/27 |
| 1005 | **30° → 37.9°** ✓ | 3 / none | 1 (near-parallel twig absorbed) | 26/26 |
| 814  | **69.2°** ✓ | 3 / none | 0 | 7/7 |

**θ_min ≥ 35° now holds at every internal node in all three; valence capped at 3 with zero
violations; no foliage lost.** (A first foliage check flagged 1005 as 24/26 leaves — that was
a leaf-*count* artifact: a dropped tip reattached onto another sprig, making it internal. The
correct test — all original sprig nodes reachable — confirms 26/26. A real reattach-into-the-
dropped-branch bug was also caught and fixed via the same verification.) Only `build_graph_v2`
was touched; the 3 shared mesh functions were not. **Stop for review before Stage 2.**

### Read (subset stage)
The redesign **works at the junction level** on the flagged cases: valence cap, dominant
continuation, sibling spacing, and direction inheritance together convert the proximity
bursts into hierarchical bifurcating forks. Full-crown promotion follows in Stage 2.

---

## Stage 2 — full-crown promotion (2026-07-06, uncommitted)
Ran `build_graph_v2()` on the **full Broad Dome crown: 781 sprigs** (the "809" on record was
the v1 placeholder dome; 781 is the v2 real-crown fill). **Tuned params → `R0=0.7, GROW=1.35,
step_frac=0.6`** (now the generator defaults): chosen over two other sweeps as the most
**bifurcation-dominant** (valence-2 the majority) with the **widest median sibling angle**.
The 3 sample nodes still pass under the new defaults (min-sib 38.6/37.9/69.2, valence ≤3,
foliage 27/27·26/26·7/7).

**Topology checks (tree-wide, 482 internal nodes):**
- **Valence:** distribution `{1:1, 2:268, 3:256}` — **max 3, ZERO nodes >3.** Bifurcation-
  leaning, as intended.
- **Sibling angle:** min **35.1°**, median 75.5°, max 171.7° → **θ_min ≥ 35° holds at every
  internal node**, not just samples.
- **Hop count (sprig→root):** min 3, **median 10**, max 11 (vs OLD grid-cell **median 6,
  range 2-6**). The increase is the **expected** consequence of valence-capping — ternary
  merging needs more levels than the old many-into-one burst, so the hierarchy is deeper
  (more branch orders). More realistic, but ~1306 nodes vs the old ~1048 (more skinning
  geometry — a note for Stage 3, not a blocker).

**Drop-policy checks (Stage-1b near-parallel absorb):**
- **Drop events: 0 / 482 merge events (0%)** with the tuned params (it fired once under a
  different sweep). The absorb-drop is a **fork-wiring-only last resort** for a near-parallel
  pair the intermediate can't separate; on the full crown that case didn't arise. **Internal
  θ_min is guaranteed by the main loop's carry-forward drop, a separate mechanism — so a 0
  absorb-drop count does *not* mean spacing was unenforced** (the min-sib 35.1° proves it was).
- **Sprig reachability: 781 / 781 original sprigs reach the root — ALL reachable, no foliage
  loss.** (Verified with the Stage-1b reachability test applied tree-wide.)

**Visual check** — `tmp/leafback_v2_crown_view{0,1,2}.png`, framed identically to the original
`leafback_bark_view0-2.png` starburst renders:
- **Major improvement:** a legible **trunk → thick primary scaffold → branch → twig
  hierarchy** with real taper is now present (the thick dominant limbs are clearly visible) —
  the old renders were a pom-pom of equal-thickness sticks radiating from one point, with no
  hierarchy. No single burst point remains.
- **Honest remaining issue:** the fine outer-twig layer is still **dense and fairly straight**,
  so the crown reads busy/tangled under projection. This is a *refinement* (curvature strength
  + twig density + 2-D superposition), **not** a topology-correctness issue — every node
  satisfies valence ≤3 and θ_min ≥35°.

**Stage 2 read (the decision point):** by the metrics the topology is **ready at full scale** —
valence, θ_min, and reachability all pass tree-wide, not just on the 3 samples, and the
intended trunk→limb→twig hierarchy visibly emerged. The one open item is fine-twig
**visual clutter**, which is a curvature/density polish separable from topology correctness.
**Open for Stage 3:** re-run the Phase-A skin spike on this full v2 skeleton to see if the
junction *mesh* quality lifts the original qualified NO-GO (skeleton now fixed; skinning was
proven mechanically in Phase A). **Stopping here for review — not committed, Stage 3 not
started.**

---

## Stage 2b — trunk-elbow diagnosis + fix (2026-07-06, uncommitted)
Visual review of the Stage 2 renders (`leafback_v2_crown_view0-2.png`) surfaced a sharp,
unnatural **elbow at the trunk→scaffold transition** (`problem_elbow_lp_v2.png`): the thick
dominant limb snapped direction at the fork instead of continuing the trunk.

### Diagnosis (read-only, `tmp/leafback_elbow_diag.py` — verified to reproduce the render graph node-for-node)
The elbow is a **placement overshoot**, NOT a dominance-by-mass or per-node curvature error
(both checked and ruled out — at the elbow merges the mass-winner *is* the best-continuation
pick, and the single-node curvature lerp contributes only ~5°):
- **Fork node `1304`** was pinned at the fixed crown-base point `(0, CB=4.32, 0)`. Its
  dominant child **`1302`** (mass 725 — the whole trunk continuation) was placed at **y=3.59,
  0.73 m *below* the fork**, heading down-and-out `(-0.48,-0.39,-0.78)` → **113° off the
  vertical trunk**. `1302` then had to climb back up (110.8° bend) → the visible down-then-up
  chevron.
- **Mechanism:** at the top levels (L=7–9) the trunk-pull weight `w` is at its 0.6 max, so
  `cont ≈ trunk_dir` aims steeply at the fixed low fork; `ppos = D.pos + step·cont` with the
  spread-scaled `step` then plants the parent below its own children and below the fork.
- **Prevalence:** 199/525 internal nodes exceed a 60° dominant-strand bend, but **152 are
  fine twigs (mass<5)** — the separate, known twig-clutter issue. Only **15 are thick
  (mass≥20)**, and of those **only 2 are true downward-dip elbows** (`1304`, `1300`), both at
  the trunk transition (hop 1–2). Localized in space, but **systemic in cause** (recurs on
  every crown's main scaffold).

### Fix (in `tmp/leafback_graph_v2.py::build_graph_v2`, isolated; shared mesh fns untouched)
Per the two-part brief — **float the fork + clamp the step**, no heading-reconciliation pass:
1. **Float the trunk target at merge time.** The merge-loop trunk-pull now aims horizontally
   at the central axis at the group's *own* height (`trunk_dir = axis@centroid_y − centroid`)
   instead of the pinned low fork, so strands converge inward while keeping elevation; the
   final fork y then floats to the dominant strand's convergence (`max(CB, min active y)`).
2. **Cap the placement step** at whichever boundary `cont` reaches first — the group centroid
   (don't leap past the merge point), the crown-base/lowest-member y-floor (no downward
   spike), and the central axis (no horizontal sign-flip). Capping the *single colinear step*
   (not overwriting y) was necessary: a y-only clamp merely relocated the reversal into the xz
   plane (empirically confirmed — a mass-324 limb reversed at 147° horizontally). Same cap
   applied in the fork-wiring intermediate placement.

### Verification (`tmp/leafback_elbow_verify.py`, before/after on the same seed-20260706 crown)
| metric | before | after |
|---|---|---|
| fork y | 4.32 (pinned) | **5.57 (floated)** |
| fork→dominant-limb bend | **113.1°** | **19.3°** (limb now continues the trunk) |
| dominant child vs fork y | 0.73 m **below** | 5.44 m **above** (no dip) |
| true downward-dip elbows (thick) | **2** | **0** |
| valence max / >3 | 3 / 0 | 3 / 0 (no regression) |
| θ_min (tree-wide) | 35.1° | 35.0° (≥35 holds) |
| sprig reachability | 781/781 | 781/781 |
| thick (>60°, mass≥20) bends | 15 | 15 (count unchanged; **max 145°→124°**) |

**Side effects (honest):** the thick-bend *set* shifts — most of these bends are a metric
artifact (6–8 of them have near-equal-mass top-2 children, so "dominant child = max-mass" is
an arbitrary pick and the *other* child continues smoothly; baseline had 12/15 such). The one
genuine **residual heading gap**: the fork's *second* limb (`~mass 341`) still leaves at ~90°
(a wide scaffold branch, not a reversal) — reported per brief, NOT papered over with a third
mechanism. Render `leafback_v2_crown_FIXED_view0-2.png` + `leafback_v2_transition_FIXED_0-1.png`
confirm the downward chevron is gone; the trunk now flows in as a central leader with an
upward-sweeping fork. **Fine-twig clutter untouched (out of scope). Not committed; Stage 3
still not started — stop for review.**

---

## Stage 2c — long straight cross-crown edges + node-collapse regression (2026-07-06, uncommitted)
Visual review of the post-elbow renders surfaced a separate artifact: a thick limb runs
almost perfectly straight across nearly the full crown diameter — no taper, curve, or
re-forking. Diagnosis (`tmp/leafback_straight_diag.py`, verified to reproduce the graph
node-for-node) found it is the **same region** as the Stage-2b residual (the fork's 2nd child,
node 1317, mass 341, 90°) — but the rod is a **long single *lateral* edge**, not 1317's
dominant chain (which actually collapses and bends). Two compounding causes:

- **① Pre-existing, systemic — oversized neighbour radius.** `R = 0.7·1.35^L` grows to
  **~7.7 m at L=8**, spanning the crown, so one top-level merge grabs a distant sprig as a
  lateral in a **single edge with zero intermediate vertices** → dead-straight, untapered,
  un-re-forked. A graph edge is straight by construction and the curvature lerp only acts
  when a node is *created*, so nothing subdivides or curves a 6.6 m one-hop edge. Baseline
  (pre-elbow-fix) already had an **8.0 m** edge and **9 edges >3 m** → not caused by the
  elbow fix. Seed-independent (R schedule is fixed); the seed only picks which sprigs.
- **② New regression from the Stage-2b step-cap — node collapse.** The scalar anti-overshoot
  cap drives `step→0` at top-level merges, stacking distinct nodes at coincident points:
  **1317/1315/1313/1311 all at (−1.55, 5.57, 0.06)**, and **235 / 1321 edges zero-length**
  (baseline **0**). The zero-length edges get cleaned by `clean_degenerate_geometry`, but the
  collapse concentrates the long lateral edges at **one hub** → the prominent star-of-rods.

**Named worst edges (before):** 387→1317 6.64 m (m1) · 1252→1315 4.23 m (m18) · 1312→1313
3.60 m (m128) · 1298→1311 3.21 m (m65). Long edges >3 m: **14** (baseline 9), thick (mass≥100)
**4**. **Prevalence:** clustered at the top scaffold hubs (nodes 1310–1321, y≈5.5–11), not
scattered through the twigs. **Systemic — recurs on every specimen.**

### Fix (three parts, in `tmp/leafback_graph_v2.py`; shared mesh fns untouched)
- **Fix B — hard-cap the merge radius** at `R_MAX` independent of level (`R = min(R0·GROW^L,
  R_MAX)`), so no single hop reaches across the crown. Chosen over a separate
  max-candidate-distance rule to avoid a second competing distance metric (per brief).
- **Fix A — subdivide long merge edges.** When wiring a member whose straight-line edge to the
  new parent exceeds `SUBDIV_LEN`, insert evenly-spaced intermediate vertices (with a gentle
  gravity sag) so the pipe-model taper and curvature act *along* the span instead of one raw
  segment. Threshold justified below.
- **Fix C — nudge, don't collapse.** Keep the scalar step cap (it also drives the descent that
  keeps the fork low) but floor the step at `MIN_STEP=0.35 m` so it can never scale to ~0, then
  add a per-coordinate safety clamp (y ≥ floor; x,z not crossing the axis). Over-reaching steps
  stop *at* the boundary while still moving — no coincident nodes.

### Chosen parameters + justification
- **`R_MAX = 4.5 m`** — below ~4.0 m convergence fails: too many top actives stay unmerged and
  the fork-wiring (which only splits *too-close* pairs) accepts them all → a **valence-4 fork**.
  Since Fix C removes the node-collapse that generated *this* seed's crown-spanners, R_MAX's
  real job is a **seed-independent safety bound** (< crown radius ~5 m) so no hop spans the
  crown on any seed; fixing the fork-wiring to allow a tighter cap would mean touching the
  delicate Stage-1/1b logic → deliberately out of scope.
- **`SUBDIV_LEN = 1.5 m`** — ≈2× the sprig spacing (0.65 m); a limb reads rod-straight only
  beyond roughly this, so edges longer than it get intermediate vertices.
- **`SAG_FRAC = 0.06`**, gravity-perpendicular — droops horizontal limbs, leaves the ~vertical
  trunk straight. The intermediate **adjacent to the branching parent is pinned to the chord**
  so that node's child-directions (θ_min, enforced at *exactly* 35°) are preserved bit-for-bit;
  without this pin the sag dropped θ_min to 30.9°.
- **`MIN_STEP = 0.35 m`** — the no-collapse nudge; side effect: the fork floats a little higher
  (5.57 → 6.78 m) because nodes descend slightly less. Acceptable (2.5 m into the crown).

### Verification (`tmp/leafback_2c_measure.py`, seed-20260706; before = Stage-2b state)
| metric | before (2b) | after (2c) |
|---|---|---|
| zero-length edges (collapse) | **235** | **0** |
| coincident thick-node pairs | 4 nodes stacked as 1 | **0** |
| edges > 3 m | **14** | **1** (the vertical trunk only) |
| thick (mass ≥ 100) edges > 3 m | **4** | **1** (trunk) |
| longest **non-trunk** edge | **6.64 m** | **1.50 m** |
| fork's 2nd-child longest lateral (the named rod) | **6.64 m** | **1.23 m** |
| fork → dominant-limb bend (elbow) | 19.3° | 22.9° (no dip) |
| thick downward-dip elbows (Stage-2b check) | 0 | **0** |
| valence max / >3 | 3 / 0 | **3 / 0** |
| θ_min (tree-wide) | 35.0° | **35.1° (≥35 holds)** |
| sprig reachability | 781/781 | **781/781** |
| node count | 1322 | 1377 (+55 subdivision vertices) |

The four named edges (387→1317 etc.) no longer exist — the region renumbered; the artifact is
gone (its longest lateral is now 1.23 m). **Fix attribution (verified separately):** Fix C alone
took collapse 235→0 *and* long-edges 14→5 (the collapse hubs were clustering most crown-spanners);
Fix B is a safety cap (largely inert post-C on this seed, valence-safe); Fix A subdivided the
residual long edges, taking longest-non-trunk 6.78→1.50 m and adding taper/curvature — with the
chord-pin keeping θ_min intact. Renders `leafback_v2_crown_2c_view0-2.png` +
`leafback_v2_transition_2c_0-1.png` confirm the star-of-rods is gone: a forking, tapering
scaffold with no coincident hub and no cross-crown rod. **Fine-twig clutter untouched (out of
scope). Not committed; Stage 3 not started — stop for review.**

---

## Closing summary — why this line is paused (2026-07-06)

The `build_graph_v2` merge line is being **paused in favour of prototyping a different
generation method (space-colonization / attractor-based growth) as a comparison.** This is a
deliberate architectural fork, **not a failure verdict** on the merge approach. The trigger is
a *pattern* across the work: three consecutive fix cycles — **elbow (2b)**, **long straight
cross-crown edges (2c)**, **node-collapse regression (2c)** — each resolved cleanly against its
own metrics, yet review kept surfacing a *new* named artifact each time. That "whack-a-mole"
cadence is itself the signal worth recording.

### What `build_graph_v2` achieves cleanly (measured tree-wide, seed 20260706)
- **Valence ≤ 3 everywhere** — 0 nodes over the cap, tree-wide (was median 4, up to 8 in the
  original grid-cell merge).
- **θ_min ≥ 35° everywhere** — no two siblings closer than the target, tree-wide (was 5–12° at
  the worst bursts).
- **Full sprig reachability** — 781/781 original sprigs reach the root; no foliage dropped.
- **No elbow / no node-collapse / no cross-crown rod at the specific nodes checked** — the
  trunk→scaffold transition continues upward (fork→dominant bend 22.9°, no dip below fork);
  0 coincident-node hubs (235 → 0 zero-length edges); longest non-trunk edge 6.64 m → 1.50 m.
- A legible **trunk → primary scaffold → branch → twig hierarchy with real taper** is present,
  which the original starburst had none of.

### What remains unresolved
- **Fine-twig-tier visual clutter.** The outer twig layer is still dense and fairly straight, so
  the crown reads busy/tangled under projection. Flagged since Stage 2 as a curvature/density
  polish, deliberately kept out of scope of every fix — but never actually addressed.
- **Full-crown gestalt.** Every *local* metric passes and every *named* artifact was fixed at
  the node level, but the crown at full scale still does not clearly read as a **classic,
  instantly-recognizable tree** (the project's stated bar). The failures we fixed were all
  ones review happened to *name*; the residual is the harder, unnamed "does the whole thing
  look right" judgment.

### Open hypothesis (the reason for the fork)
The merge-based method has **no explicit branching/growth model** — it agglomerates sprigs
inward by proximity/mass and *derives* directions from lerps and caps. So every fix necessarily
targets an **individual failure symptom** (this bend, this edge, this collapse) rather than an
underlying **"what a tree looks like"** target. That structurally invites whack-a-mole: patching
the mechanism's *texture* one artifact at a time, with no generative prior that would rule the
whole class out at once. **Space-colonization / attractor growth is worth comparing precisely
because it *is* an explicit growth model** — branches grow toward attractor points under a
competition rule — so its artifacts (if any) should be a different, hopefully more tree-shaped,
class. The comparison will tell us whether the merge line's residual is inherent or just
under-tuned.

### Status / where to resume
- **Committed (this pause):** `docs/leafback_topology_redesign_plan.md` (this file, Stages 1–2c
  + summary) and `docs/leafback_skeleton_topology_diagnosis.md` (the original branch-topology
  diagnosis).
- **Left in place, uncommitted in `tmp/` (gitignored working artifacts):** `leafback_graph_v2.py`
  (the merge generator with all Fix A/B/C changes) and the diagnostic/verify/render/sweep
  scripts (`leafback_elbow_{diag,verify}.py`, `leafback_elbow_sweep.py`, `leafback_straight_diag.py`,
  `leafback_2c_measure.py`, `leafback_{elbow,2c}_render.py`) + their PNG renders. **Nothing was
  deleted** — the whole line can be picked back up as-is.
- The three shared mesh functions (`clean_degenerate_geometry` / `enforce_min_twig_diameter` /
  `stitch_bark_islands`) were **never modified** across Stages 1–2c → zero regression risk to the
  committed s/m tree work regardless of what happens to this line.
- **Resume point (if we return):** Stage 3 = re-run the Phase-A skin spike on the 2c skeleton to
  see if junction *mesh* quality lifts the original qualified NO-GO — **not started**, held
  pending the growth-based comparison.
