# Leaf-Back London Plane — LOD0 Density Escalation (Planner proposal)

> **Role 1 (Tree Planner) artifact — DESIGN INTENT ONLY, no code.** Produced 2026-07-08,
> Opus 4.8 (1M), on escalation from the Engineer after the **AC-8 performance convergence
> gate FAILED** during AC-8 wiring (`tmp/AC8_wiring_progress.md`). This is a proposal: it
> analyses the failure, proposes a corrected perf bar, ranks the density levers against the
> blocking ACs, sets per-tier vertex budgets, and **drafts** a spec revision. It does **not**
> rewrite `docs/leafback_tree_planner_spec.md` — the canonical spec change is the owner's
> (Chris's) sign-off, per the project's ADR convention.
>
> Consumes: `leafback_tree_planner_spec.md` (v4), `leafback_pipeline.md`, `docs/rendering.md`,
> `docs/vision.md`, `docs/crown_type_buckets.md`, `tmp/AC8_wiring_progress.md`, and the
> woodland-perf record (`project_woodland_perf_investigation.md`, closed `640b2c2`).

---

## 1. Framing — what failed (and what did NOT)

**Integrity passed; performance failed.** The line-C trunk-scaffold skeleton →
`scripts/leafback_skinner.py` → london_plane GLB path is now **structurally correct** on all
three buckets: connected-component count = 1, 0 degenerate faces, the full 5-attribute Mtree
contract, and the l-tier thick-trunk weld defect diagnosed (RING=24 azimuthal spacing on the
356 mm trunk exceeded the weld tol) and fixed with a geometry-derived weld tol. **No blocking
structural AC (AC-1..AC-7, AC-14) or AC-5(iv) regressed.** This is **not** a mesh defect.

**The sole failure is LOD0 geometric density.** Measured per-tier build:

| tier (bucket) | skeleton nodes | verts | faces | leaf clusters | GLB |
|---|---|---|---|---|---|
| s (s tier, H10) | 238 | 4,559 | 5,430 | 115 | 1.2 MB |
| m (m tier, H14.4 — **REF**) | 974 | 18,401 | 22,475 | 273 | 3.9 MB |
| l (l tier, H22) | 4,585 | **71,353** | 87,561 | 1,032 | 14.25 MB |

The old Mtree london_plane was ~4 k verts (m) and ~1.48 MB (l) — so leaf-back is **~5× heavier
on m and ~10× on l**. The driver is **bark geometry**: bark verts ≈ `skeleton_nodes × RING(24)`,
so l's 4,585 nodes × 24 ≈ 110 k pre-weld rings dominate the mesh. Leaf-cluster counts rose only
modestly (Mtree m ~190 → 273 clusters, l ~774 → 1,032; ≈1.3–1.4×), so **cluster/overdraw is not
the marginal driver of this regression — bark vertex/primitive load is.** The AC-8 gate
(`scripts/perf_gate.sh`, real park `--park --all-london-plane`, 6808 trees, RTX 3060 Ti):

| location | leaf-back | Mtree LP baseline (2026-07-05) | vision target |
|---|---|---|---|
| literary_walk (open) | **13** (78 ms) | 72 | 60 |
| bethesda (open) | **13** | 83 | 60 |
| ramble (woodland) | **11** (95 ms) | 31 | 45 floor |
| great_lawn (open) | **14** | 97 | 60 |
| north_woods (woodland) | **9** (109 ms) | 26 | 45 floor |

Every position collapsed ~5×; frame cost 15 ms → 78 ms open, up to 109 ms at north_woods. This
was **anticipated**: the bucket-validation carry-forward already flagged *"scale card-thinning
for the big bucket's large sprig cloud … the big bucket needs thinning to sane LOD0"*
(`crown_type_buckets.md` §4, `project_london_plane_crown_mould.md`). The prediction was
correct; this proposal executes that anticipated thinning as a design task, not a surprise fix.

The woodland regime is **vertex-bound** (`vpgpu`/`vistri` are the truth-metrics;
`project_woodland_perf_investigation.md`), which is exactly the regime a 5–10× bark-vertex
increase punishes hardest — the leaf-back tree lands its worst multiplier where the frame can
least afford it.

---

## 2. The perf-bar question — what AC-8 *should* require

AC-8 as written in spec v4 says: real-park `--all-london-plane`, **both ramble and north_woods
> 45 fps**. The complication the Engineer correctly surfaced: **the incumbent Mtree LP does not
meet that bar either** — ramble 31, north_woods 26, both already sub-floor. The woodland 45 fps
floor is a **known, separately-managed, structural shortfall** (`project_woodland_perf_investigation.md`,
CLOSED `640b2c2`: dense photoreal woodland is ~26–32 fps, GPU vertex-bound, *not* a fixable
waste; splits2 + fade025 adopted on merit, best north_woods 32, still ~13 fps short — accepted
as "the price of 6808-tree photoreal woodland"). Holding the leaf-back tree to an absolute bar
its predecessor fails would make it un-shippable for reasons **unrelated to leaf-back**.

### Positions considered

- **Position A — keep AC-8 as written (absolute >45 both woodland spots).**
  *Rejected.* The incumbent fails it; enforcing it blocks the leaf-back tree on a floor the
  project has already accepted it cannot hit with *any* tree. It measures the woodland subsystem,
  not the leaf-back tree.

- **Position B — non-regression vs the Mtree LP baseline at every gate position (RECOMMENDED).**
  The leaf-back tree replaces a specific incumbent with known per-position numbers
  (72 / 83 / 31 / 97 / 26). The fair, testable question is: *does swapping in the leaf-back tree
  make the park slower?* Bar = **leaf-back median fps ≥ Mtree LP baseline at each of the 5
  positions, within measurement noise (~5%)**. This is concrete, already-measured, and isolates
  the tree's own cost from the separately-managed woodland floor.

- **Position C — parity only at the two woodland (vision-floor) positions, ignore open.**
  *Rejected.* The open positions collapsed 72/83/97 → 13/13/14 too. A tree that tanks the open
  park (where the 60 fps floor *is* met today) is unacceptable even if woodland held. The gate
  must cover all 5.

- **Position D — the absolute vision floor (60 open / 45 woodland) as the bar.**
  *Partially adopted.* The **open 60 fps floor is real and must hold** — but non-regression
  (Position B) already guarantees it, because the incumbent meets 60 at all three open spots
  (72/83/97). The **woodland 45** cannot be a *blocking* leaf-back bar (Position A's problem);
  it stays the project-level aspiration owned by the woodland-perf track.

### Recommendation — the concrete AC-8 bar

**Blocking (Position B + D's open floor):** at the 5 real-park gate positions, leaf-back median
fps must **not regress** vs the 2026-07-05 Mtree LP baseline within ~5%:

| position | baseline | blocking floor (≈baseline − 5%) |
|---|---|---|
| literary_walk | 72 | ≥ 68 |
| bethesda | 83 | ≥ 79 |
| ramble | 31 | ≥ 29 |
| great_lawn | 97 | ≥ 92 |
| north_woods | 26 | ≥ 25 |

Additionally the three **open** positions must independently clear the vision **60 fps** floor
(non-regression already implies this). **Aspiration (tracked, non-blocking):** the 45 fps
woodland floor remains the project target managed by the woodland-perf track — leaf-back is
required not to *worsen* it, not to *solve* what Mtree hasn't.

Rationale note for the owner: non-regression is a *hard, honest* bar — the current result
(13/13/11/14/9) fails it decisively at every position, so nothing about this framing "lets the
leaf-back tree off". It simply refuses to charge leaf-back for a pre-existing woodland deficit.

---

## 3. Density levers vs the blocking ACs

The regression driver is **bark verts (`nodes × RING`)**, secondarily leaf-card overdraw.
Levers, ranked by *recovery ÷ AC-risk*. **★ Ordering REVISED 2026-07-08 after the Half-1
measurement (§"Half-1 measurement — lever 1")** overturned the original forecast: radius-scaled
RING realizes only **~1.5×**, not the forecast 2.5–3× (the shared `clean_degenerate` weld already
sheds most high-ring redundancy — ring scaling and the cleaner are largely redundant). So the
**primary recovery path is NODE-COUNT reduction (Lever 1 below), which the cleaner cannot eat**
(fewer nodes → fewer verts, unconditionally); radius-scaled RING is **demoted to a kept ~1.5×
v/node multiplier (Lever 2)** — kept, and *load-bearing on lantern risk* (see its entry), but it
cannot carry the budget.

### Lever 1 — Node-count reduction (twig decimation + the AC-7 coarser cloud)  *(PRIMARY recovery — cleaner-independent)*
The dominant, cleaner-independent lever: fewer skeleton nodes → fewer verts one-for-one, and the
weld cannot claw it back. Two sub-mechanisms:
- **(1a) Twig / interior-node decimation for LOD0** — curve-simplify each strand before skinning:
  collapse **collinear valence-1 pass-through** nodes (the skinner tubes straight along a strand —
  intermediate collinear rings add no silhouette) and merge sub-threshold terminal segments
  (Douglas-Peucker-style per strand). Cuts node count directly.
- **(1b) Coarser l attractor cloud (the AC-7 change)** — the larger, structural lever for l:
  generate *fewer nodes born* by coarsening the attractor cloud at the skeleton stage
  (SPRIG_SPACE). Now **expected**, not a remote fallback (§7 — post-Half-1, l needs **~1,030
  nodes** and RING alone lands ~24–28 k → node reduction is mandatory). Fully pre-scoped in §7.
- **Sequencing guard:** 1a decimates *existing* nodes; 1b generates *fewer* nodes. **Sequence
  against the measured residual — do not stack blind** (coarsen the cloud toward the §7 target,
  *then* apply only as much twig decimation as the residual needs, so the two do not compound into
  over-thinning that breaks AC-4/AC-10).
- **AC-4** (monotone outward density): decimate/coarsen **uniformly**; keep **frontier branch
  (fork) nodes** so the shell ramification *count* and the density gradient survive. Coarser-but-
  uniform preserves the monotone shape (§7). **Risk if over-pulled / seam-biased.**
- **AC-10** (reachability ≥ ~90%): 3.3-pt margin today; **re-measure after coarsening** — below
  90% promotes to blocking. **Moderate risk.**
- **AC-14 / AC-1** (caliber, leader): caliber is a **ratio** property (√attractors-above,
  re-anchored on unchanged DBH) — uniform scaling preserves the lower>higher gradient and gauge
  separations; keep all thick-limb + trunk-spine nodes. **Structurally survives** (§7); only
  fine-twig *density* thins (a visual cost, acceptable at l's distance).
- **AC-6** (emergent valence): the **top risk** — a coarser cloud without co-scaled influence/kill
  distances reverts to the line-B "lantern" (valence-1 ribs). Bounded by the coupled
  {SPRIG_SPACE, di, dk} retune + l-only confirmation sweep (§7).
- Risk summary: **AC-4 / AC-10 / AC-6 — all bounded (§7); AC-6 is the one to guard via the
  coupled retune.** This is the lever that actually reaches the budget.

### Lever 2 — Radius-scaled RING  *(KEPT ~1.5× multiplier — load-bearing on lantern risk, NOT primary)*
Today RING = 24 uniformly. Replace with a per-**strand** ring count scaled by radius (per-strand,
NOT per-node — Half-1 confirmed per-node barely beats per-strand and risks intra-strand-transition
cracks): thick ≥90 mm → 24, ≥35 mm → 12, twig → 8. **Realized ~1.5× on l (67 k→45 k), ~1.56× on m,
~1.8× on s** — measured, not forecast; the cleaner already ate the rest.
- **★ KEEP IT — it is load-bearing, not demotable.** A 1.5× lever that "can't carry the budget"
  looks droppable, but it is what holds Lever 1b's node target **above the AC-6 lantern floor**:
  WITH ring scaling the l cloud needs **~1,030 nodes**; WITHOUT it, **~680** (14.7 v/node) — a
  ~350-node gap that is the margin between a coarse-but-viable crown and a **probable lantern
  reversion**. Dropping ring scaling to "simplify" would silently lower the AC-7 target into the
  danger zone. This dependency must travel with the number (Chris's explicit ask).
- **AC-15** (fork interpenetration): remedy is *"RING ≈ 24 + smoothing"* — thick low scaffolds
  keep 24 where interpenetration is worst/visible; only thin distant twigs drop, where faceting is
  invisible at l's viewing distance. **Net neutral.**
- **AC-5(iv)** (weld): tol is radius-derived; thick nodes keep 24, so the l weld fix is preserved.
  Half-1 measured **non-manifold edges DROP** under scaling (no ring-transition cracks). **No risk.**
- **AC-1/2/3/14** (thick limbs): untouched — bold silhouette lives at RING=24. **No risk.**
- **⚠ PROVISIONAL default:** `radius_scaled=True` is set as a skinner default but the coarser twigs
  (ring 8 vs 24) are an **aesthetic** change with no Critic review yet — flagged for an explicit
  Critic look at twig legibility before it is treated as settled (§"Half-1 measurement"). Do not
  bank it as final look.
- Risk summary: **AC-15 only (accepted); load-bearing on AC-6 via Lever 1's target — keep.**

### Lever 3 — Leaf-card thinning per bucket  *(overdraw/fragment ONLY — DROPPED from the vert-budget path)*
The carry-forward's named lever: `card_rule_depth_keep` / `card_rule_spacing` /
`cards_per_cluster`, tuned **per bucket**. **★ DROPPED from the vertex-budget recovery path (Chris,
post-review):** it cuts *leaf* geometry, but the budget is vertex-denominated and the driver is
*bark* — so it contributes ~nothing to the vert budget. Keep it **only** as a fragment/overdraw
lever (historically the #1 tree cost), tuned to the fps residual *after* the bark/node levers land,
judged separately from the vertex budget.
- **AC-4** (shell density) and canopy opacity (`reference_tree_canopy_data`): over-thinning holes
  the crown. **Bounded — judge visually against the reference canopy fullness.**
- Risk summary: **AC-4 + canopy-fullness look — tune to the perf residual, Critic-judged. Not a
  vert-budget lever.**

### Lever 4 — Global RING reduction (24 → lower, uniform)  *(NOT recommended)*
Cheaper to implement than the per-strand radius-scaled RING (Lever 2) but facets the **thick
trunk** in the near lod0 band (0–60 m solid, close viewing) and re-breaks the radius-derived weld
tol. Rejected in favour of Lever 2, which gets the same bulk recovery without touching thick limbs.

### Lever 5 — A genuine near/far LOD split  *(NOT recommended as the first move)*
The runtime chain is **lod0 → impostor only, no mid tier** (`docs/trees.md` canonical banner
2026-07-03). The old `_lod1` mid tier was **deliberately retired** because stale lod1 GLBs
shape-drifted from lod0 across octahedral impostor angles ("l keeps changing shape"). Re-adding a
mid tier is a whole subsystem with a *known failure mode*. **Recommendation: make the single lod0
model itself hit budget via Levers 1–3**, and let the existing openness-class lod0 cull (dense
chunks already cull lod0 at ~63 m) + impostor do the distance work. If, after 1–3, l still busts
budget, the lighter fallback is a **per-openness decimated lod0 variant for dense-forest chunks**
(not a new distance tier) — a follow-up, not the first move.

---

## 4. Recommended per-tier LOD0 vertex/face budget

Targets the Engineer can build to and measure. Anchored on **near-parity with the Mtree LP the
leaf-back tree replaces** (m ~4 k verts, l ~1.48 MB ≈ ~7 k verts), with a **modest allowance**
for the richer, genuinely-more-structured leaf-back crown. Face ≈ verts × 1.22 (from the measured
build ratios); GLB scales ~linearly with verts.

| tier | current verts | current GLB | **target verts** | **target faces** | **target GLB** | reduction |
|---|---|---|---|---|---|---|
| s | 4,559 | 1.2 MB | **≤ ~3,000** | ~3,700 | ~0.8 MB | ~1.5× |
| m (REF) | 18,401 | 3.9 MB | **≤ ~6,000** | ~7,300 | ~1.5 MB | ~3× |
| l | 71,353 | 14.25 MB | **≤ ~10,000** | ~12,200 | ~2.2 MB | ~7× |

These are the *"must approach"* design targets — parity-plus-a-little, not a guess. **Lever order
to hit them (REVISED post-Half-1 measurement):** (1) **node-count reduction** — twig/collinear
decimation + the **AC-7 coarser l cloud** (§7) — is the **primary, cleaner-independent** recovery,
the only lever that actually reaches the l budget; (2) **radius-scaled RING** — a KEPT ~1.5×
v/node multiplier (measured, not the forecast 2.5–3×), **load-bearing on lantern risk** (it holds
the AC-7 node target at ~1,030 vs the ~680 danger zone — do NOT demote it despite the modest
multiplier); (3) **card thinning** — DROPPED from the vert budget (it cuts leaf, not bark), kept
only for the fragment/overdraw residual. Measure verts/faces after each lever (cheap), run the
full fps gate only at/near budget. The l tier's 4,585 nodes are the outlier — node reduction is
where the l recovery is won.

**Honest caveat for the owner (feeds §6):** the leaf-back tree's *reason for existing* is the
structural richness (persistent leader, N scaffolds at separated heights, monotone shell density,
bold caliber hierarchy). Whether a **10× reduction on l** is reachable *while keeping the blocking
ACs* is not certain — there may be an irreducible node floor below which AC-1/2/4/14 start to
break. Levers 1–3 should be pulled and re-measured; **if l cannot reach non-regression distance
without losing a blocking AC, that is an escalation** (§6), not something to force by
over-decimating the crown.

---

## 5. Proposed spec change (PROPOSED — pending owner sign-off)

**Do not apply to `leafback_tree_planner_spec.md` yet.** Drafted here for Chris's review. Two
edits to AC-8:

### 5a. Revise AC-8(a)/(c) — perf target = non-regression, not absolute floor
Replace the "both ramble and north_woods > 45 fps" bar with:

> **(a) Intent:** The wired generator, at CPW's full target scale (real park, 6808 trees), must
> **not regress frame rate versus the incumbent Mtree london_plane** at any benchmark position,
> and must independently hold the **60 fps open-area floor** (`vision.md`). The **45 fps woodland
> floor** remains the project aspiration owned by the woodland-perf track (a floor the incumbent
> Mtree LP also does not meet — `project_woodland_perf_investigation.md`); leaf-back must not
> *worsen* it, and is not required to *solve* it.
>
> **(c) Metric proxy:** wire skeleton → `scripts/leafback_skinner.py` (full 5-attr contract) →
> london_plane GLB → `scripts/perf_gate.sh` (`--park --all-london-plane`). **Blocking:** median
> fps ≥ the recorded Mtree LP baseline − 5% at **all five** positions (literary_walk ≥ 68,
> bethesda ≥ 79, ramble ≥ 29, great_lawn ≥ 92, north_woods ≥ 25 against the 2026-07-05 gate), and
> the three open positions ≥ 60. Re-baseline if the incumbent numbers are re-measured.

### 5b. Add AC-8b (or fold into AC-8 metric proxy) — per-tier LOD0 density budget as early-warning
Upgrade the existing "node/edge count is the cheap early-warning proxy" line to a **concrete,
per-tier vertex/face/GLB budget**, checked every iteration (cheap; no forest run needed):

> **Density budget (early-warning proxy, checked per build):** LOD0 mesh must land within the
> per-tier budget — **s ≤ ~3,000 v / ~0.8 MB; m ≤ ~6,000 v / ~1.5 MB; l ≤ ~10,000 v / ~2.2 MB**
> (near-parity with the Mtree LP + a modest structural allowance; validated scene-wide at 0.78×
> Mtree, §"Engineer verification"). Busting a tier budget is an **early FAIL** that predicts the
> fps gate will fail — fix before spending a forest-scale run. This proxy is
> *necessary-but-insufficient*: passing the budget does not guarantee the fps gate
> (fragment/overdraw is separate), but failing it reliably predicts a perf FAIL.
>
> **How the budget is reached (recovery-path note, so the reader does not mis-pull levers):** the
> budget is hit **primarily by NODE-COUNT reduction** (twig decimation + the AC-7 coarser l cloud,
> §7) — radius-scaled RING realizes only ~1.5× (measured, Half-1), because the shared cleaner
> already sheds most high-ring redundancy. **RING scaling is nonetheless load-bearing and must NOT
> be dropped:** it holds the AC-7 node target at ~1,030 (l) rather than the ~680 that risks the
> AC-6 lantern reversion. Leaf-card thinning is NOT a vert-budget lever (it cuts leaf, not bark).

### 5c. Add a ring-transition manifold check to the AC-8 integration verify (NEW)
Radius-scaled RING creates junctions where a 24-ring trunk segment meets an 8-ring twig.
`components==1` will **not** catch cracks / T-junction non-manifoldness at the ring-count boundary.
The AC-8 integration verify must therefore **add a targeted non-manifold-edge count + visual trace
at trunk↔twig ring transitions**, not only re-run the 5-attribute + single-component contract.
(Half-1 measured this empirically **clean** for the per-strand implementation — non-manifold edges
*dropped* under scaling — so the per-strand approach is the correct one; the check stays a standing
requirement because a future per-node RING variant would reintroduce the risk.)

Edits 5a/5b/5c change **how AC-8 is measured**, not *what a correct tree is* — consistent with the
v2/v3/v4 changelog discipline. If adopted, they become spec v5 with a changelog line.

---

## 6. Open questions for the owner (values / scope calls)

1. **Is a 5–10× density tree ever viable at 6808-tree scale, or must leaf-back target a lower
   crown-node count from the skeleton stage?** Levers 1–3 are skinner/generator knobs. If l cannot
   reach non-regression without breaking a blocking AC, the real fix is **fewer crown nodes from
   the start** — a coarser attractor cloud (the 781-sprig m tier shell scales to ~2,865 on l,
   ~4,556 at the ceiling) or a coarser merge/ramification target at the *skeleton* stage. That is a
   **Planner/skeleton-stage design change** touching the protected `leafback_graph` cloud and AC-7,
   not a skinner tuning. Does the owner want that path pre-authorised as the fallback, or held as a
   separate escalation?

2. **Is the non-regression bar (Position B) the right contract, or does the owner want the leaf-back
   tree to *improve* woodland perf** (i.e. come in *lighter* than Mtree, buying back some of the
   woodland-floor deficit)? A leaf-back tree that is genuinely cheaper than Mtree is possible in
   principle (bark-only geometry, no Mtree leaf-plane overdraw) and would be a project win beyond
   parity — but it raises the reduction target further.

3. **Budget allowance size.** §4 sets targets at *parity + a modest allowance*. Is the owner
   comfortable trading some structural fidelity (e.g. l capped nearer ~8 k v) for headroom, or is
   the structural richness the priority even at parity-only (~7 k v, tighter)?

4. **The l bucket specifically.** l (l tier, the veteran "hero" silhouette) is both the
   **most visually valuable** form (§`crown_type_buckets.md`: distinctive out of proportion to its
   ~25% share) and the **worst perf offender** (10×). Is it acceptable for l to carry a *higher*
   vertex budget than a strict non-regression allows (because the hero tree earns it), offset by
   its lower population share — or does every bucket hold the same parity discipline?

---

## 7. Pre-scoped AC-7 fallback: coarser l attractor cloud  *(PROPOSED / pending Chris)*

**Why this is now EXPECTED, not a remote fallback — and the target is now MEASURED, not forecast.**
Owner arithmetic on §3, confirmed by the Half-1 measurement: **card thinning cuts LEAF geometry,
but the budget is vertex-denominated and the driver is BARK verts** — so it is dropped from the
*budget-recovery* path. Radius-scaled RING then realized only **~1.5×** on l (67 k→45 k, measured
— NOT the forecast 2.5–3×; the shared cleaner already ate the rest). That leaves **node-count
reduction to carry the l budget**, and RING alone cannot — so the AC-7 cloud coarsening is not a
fallback, it is the **primary l lever**. The forecast in the earlier draft of this section
(~1,700 nodes, SPRIG_SPACE ≈ 1.0 m) **assumed the fuller RING recovery and is superseded by the
measured numbers below.**

### The arithmetic — target node count, sprig count, SPRIG_SPACE  *(RESET by the Half-1 measurement)*
- **Measured verts/node at radius-scaled RING:** l = 44,610 v / 4,585 nodes = **9.7 v/node** (the
  actual Half-1 result — bark + shared leaf-card verts, post-weld, post-cleaner).
- **Node target for ≤ 10 k v:** 10,000 ÷ 9.7 ≈ **~1,030 l-nodes** (band ~1,000–1,050). That is a
  **~4.5× node reduction** from 4,585 — *deeper* than the earlier ~1,700 forecast, precisely
  because RING under-delivered. This is the reduction the cloud change must produce at the
  skeleton stage.
- **Sprig target:** current l = 2,865 sprigs → 4,585 nodes (~1.6 nodes/sprig; the graph adds
  intermediate/fork nodes). Node count scales ~linearly with sprig count, so ~1,030 nodes ⇐
  **~650 sprigs** (from 2,865, a ~4.4× cut).
- **SPRIG_SPACE:** the cloud is a **shell** (2-D surface), so sprig count ∝ 1/spacing². A 4.4×
  count cut needs spacing × √4.4 ≈ **×2.10** → SPRIG_SPACE **0.65 → ~1.35–1.40 m for the l bucket
  only.** (Check: (0.65/1.37)² × 2,865 ≈ 645 sprigs → ~1,030 nodes → ×9.7 ≈ ~10.0 k v. Round
  target: **SPRIG_SPACE_l ≈ 1.35–1.40 m.**)

### ★ Lever-2 (radius-scaled RING) is load-bearing on the lantern floor — carry the DEPENDENCY, not just the number
The ~1,030-node target **exists only because RING scaling is kept.** Run the same arithmetic
*without* Lever 2: l would be **14.7 v/node**, so ≤ 10 k ⇒ only **~680 nodes** ⇐ ~425 sprigs ⇐
SPRIG_SPACE ≈ **1.69 m**. That ~350-node gap (1,030 vs 680) — equivalently SPRIG_SPACE 1.37 m vs
1.69 m — is **the margin between a coarse-but-viable crown and a probable AC-6 lantern reversion.**
A coarser cloud also drives the coupled influence distance *up* (see below); the denser 1.37 m
target keeps di lower and the cloud further from the lantern regime than the 1.69 m target would.
So **do not "simplify" by dropping the modest 1.5× RING lever** — it silently lowers this target
into the danger zone. Lever 2 is kept for exactly this reason (Chris's explicit instruction).

### Coupled parameter — di/dk must scale with SPRIG_SPACE (do NOT change spacing alone)
The space-colonization influence distance **di = 1.9** and kill distance **dk** were tuned for
SPRIG_SPACE = 0.65 (line-B sweep). Coarsening the cloud without scaling these reverts to the
**line-B "paper-lantern" failure mode** — tips chase a single far attractor as valence-1 ribs
instead of forking to fill (`project_london_plane_crown_mould.md`: *"di too large vs spacing →
valence-1 rib"*). To preserve the emergent branching character, **di and dk scale with
SPRIG_SPACE** (at the revised SPRIG_SPACE_l ≈ 1.37 m: di ≈ 1.9 × 1.37/0.65 ≈ **~4.0** at l),
keeping the di/spacing ratio constant. The cloud coarsening is therefore a **coordinated
{SPRIG_SPACE, di, dk} retune for l**, not a one-knob edit. **Note the compounding hazard:** the
deeper 4.4× coarsening (vs the earlier 2.6× forecast) drives di up toward ~4 m — closer to l's
crown radius, i.e. *toward* the lantern regime — which is exactly why Lever 2 (holding the target
at 1.37 m, not the RING-less 1.69 m) matters. A short l-only sweep (as line B did) confirms the
retuned trio holds the valence distribution; if it does not at 1.37 m, that is the signal that l's
irreducible-node floor has been hit (§6 Q1 escalation), not a knob to force.

### Cost to the blocking ACs
- **AC-4 (monotone density gradient) — LOW risk.** Uniform shell coarsening lowers the *absolute*
  shell peak (line-C profile ~4→10→30→110→85 scales toward roughly ~1→2→7→25→19 at the 4.4× cut)
  but **preserves the monotone-increasing shape** — it is a uniform density scaling, not a
  re-profiling. AC-4's blocking property (monotone outward) survives as long as the coarsening is
  uniform, not seam-biased. (The deeper 4.4× cut leaves the near-trunk bands very sparse — watch
  that the innermost bands do not collapse to zero and break the *gradient* read; the frontier
  fork nodes carrying the shell peak are the ones to protect.)
- **AC-10 (reachability ≥ 90%) — MODERATE risk (the one to re-measure).** Fewer, better-spaced
  attractors are individually *easier* to reach, but each missed sprig is a larger *fraction* of
  a smaller cloud, so the current 93.3% (3.3-pt margin) could dip. The wedge-seam gaps are a
  function of the N-wedge partition, not density, so no first-order worsening — but **re-measure
  reachability on the coarsened cloud**; below 90% it promotes to blocking (per AC-10).
- **AC-14 (caliber hierarchy) — SURVIVES; it is a RATIO property.** Chris's specific concern —
  *fewer twigs, does the gradient survive?* Caliber comes from the growth-order partition (each
  primary's base radius ∝ √(attractors-above-attachment)) re-anchored on the unchanged DBH
  (r₀ = 0.19 m, protected). **Scaling the whole cloud down ~4.4× scales every primary's
  attractor-count by the same factor — the RATIOS between primaries (lower-thicker-than-higher)
  and the gauge separations (primary ≥ 2× secondary ≥ 2× twig, ratios of medians) are
  preserved.** The thick→medium→fine hierarchy and the lower>higher gradient survive. What thins
  is the *fine ramification density* (fewer twigs), which is a **visual**, not a structural,
  cost — acceptable at l's viewing distance (see below).
- **AC-6 (emergent valence) — MODERATE, and the TOP risk.** This is the real exposure: not the
  density drop itself but the **retune requirement** — if SPRIG_SPACE moves without di/dk, the
  emergent valence distribution regresses to the line-B lantern (valence-1 ribs). Mitigated by
  the coupled {SPRIG_SPACE, di, dk} scaling + an l-only confirmation sweep. This is why the
  section above insists the cloud change is a *coordinated retune*, not a one-knob edit.

**Viewing-distance acceptability.** l is the **l tier veteran — the largest tree,
seen from farthest**, and its lod0 holds only to ~63 m in dense chunks before the impostor takes
over. A coarser shell (fewer, coarser twigs) is the *cheapest* place in the whole species to
spend a fidelity cut: the fine outer-twig layer is exactly what is least resolvable at the
veteran's characteristic distance. The bold caliber hierarchy (AC-14), the near-trunk heft, and
the low-forked silhouette — the things that make l the "hero" form — all live on the thick limbs
that the coarsening does **not** touch.

### Per-bucket-only, and the AC-7 discipline note
- **l-only; it does NOT force m.** SPRIG_SPACE becomes a **per-bucket parameter** (l ≈ 1.35–1.40,
  m = 0.65, s = 0.65). m (974 nodes / 18 k v → ≤ 6 k target) is expected to reach budget on the
  node + RING levers alone (radius-scaled RING ~1.56× measured on m + modest twig decimation on a
  974-node skeleton) and is **not** flagged for cloud coarsening. Scope the parameter as per-bucket
  so m *could* take it later without re-plumbing — but the first move is l alone.
- **AC-7 is satisfied, not violated — and this is precisely why it must be l-only.** AC-7's
  literal protected anchor is the **m tier REF = the m tier** (attractor count = 781, seed
  20260706, r₀ = 0.19 m). **m must stay 0.65 / 781 to keep AC-7's REF anchor green.** l is a
  *different* bucket (l tier, 2,865 sprigs) — not the REF anchor — so coarsening l's
  cloud does not touch AC-7's literal check. AC-7 permits changing a protected component *"unless
  a specific deficiency is found and noted"* — **the AC-8 perf failure IS that noted specific
  deficiency, and this document is the note.** The l coarsening is an AC-7-compliant, noted
  divergence; the m REF is untouched.
- **Copy-diverge discipline (already established).** This edits cloud density — the protected
  `leafback_graph` component. The promoted copy `scripts/leafback_graph.py` already diverges from
  the tmp original and already took a new `profile=(T,P)` param; it can take a **per-bucket
  SPRIG_SPACE (+ coupled di/dk)** without touching the tmp `leafback_graph.py` original. No
  protected-original edit; the change lives in the promoted generator copy, l-branch only.

**Status: PROPOSED / pending Chris.** Pre-scope only. **The conditional in the earlier draft is
now resolved:** the Half-1 measurement put l at 44.6 k v with RING scaling alone (4.5× over
budget), so this cloud change is **confirmed as the required l lever, not a maybe.** What remains
gated on Chris is the go-ahead to implement it (it touches the promoted `leafback_graph` copy's
cloud density — an AC-7-noted divergence) and the l-only confirmation sweep that verifies the
coarsened {SPRIG_SPACE, di, dk} trio does not trip the AC-6 lantern.

---

## Summary

- **What failed:** perf, not integrity. LOD0 bark-vertex density 5–10× Mtree (`nodes × RING`),
  worst on l (71 k v). Anticipated by the bucket-validation carry-forward.
- **Perf bar (recommended):** **non-regression vs the Mtree LP baseline at all 5 positions
  (−5% tolerance)** + the open 60 fps floor held; the 45 fps woodland floor stays a tracked
  aspiration (the incumbent misses it too — do not charge leaf-back for it).
- **Per-tier LOD0 budget:** s ≤ ~3 k v / 0.8 MB · m ≤ ~6 k v / 1.5 MB · l ≤ ~10 k v / 2.2 MB.
- **Lever order (REVISED post-Half-1 measurement — RING under-delivered, ordering inverted):**
  (1) **node-count reduction** — twig/collinear decimation + the **AC-7 coarser l cloud** — is the
  **primary, cleaner-independent** lever, the only one that reaches the l budget (AC-6 lantern is
  the top risk, bounded by a coupled {SPRIG_SPACE, di, dk} retune); (2) **radius-scaled RING** — a
  KEPT ~1.5× multiplier (measured, not the forecast 2.5–3×) that is **load-bearing on lantern
  risk** (it holds the AC-7 node target at ~1,030 vs the ~680 danger zone — do NOT demote it); (3)
  **card thinning DROPPED** from the vert budget (cuts leaf, not bark), kept only for fragment
  cost. Do **not** re-introduce a mid LOD tier; do **not** globally cut RING.
- **AC-7 coarser-l cloud (now EXPECTED, §7):** measured target **~1,030 l-nodes** (from 4,585) via
  **SPRIG_SPACE_l ≈ 1.35–1.40 m** (from 0.65) + coupled di/dk retune. Ring-transition manifold
  check added to the AC-8 verify (§5c; Half-1 measured it empirically clean for the per-strand impl).
- **Open for owner:** whether the ~4.5× l node reduction is reachable without an AC-6 lantern
  reversion (§6 Q1) — the l-only confirmation sweep is the test; failure means l's irreducible-node
  floor is hit, an escalation not a knob to force.
- **Spec:** AC-8 revision DRAFTED (§5a/b/c), marked **PROPOSED / pending Chris** — not applied to
  the canonical spec.

---

## Engineer verification — owner review round (2026-07-08)
Chris reviewed the proposal and raised 4 points; the Engineer resolved the checkable ones before any
density build. Results:

- **Issue 2 — scene-arithmetic check (the gate on the budgets): PASSES.** Measured tier distribution
  under `--all-london-plane` (temp `CPW_TIER_TALLY`, reverted): **s 1044 · m 2521 · l 3243** (park is
  **l-dominant**, not m-dominant). Mtree per-tier verts (single variant, rebuilt via `CPW_FORCE_MTREE`):
  **s 13,314 · m 3,282 · l 13,165**. Scene-wide vert sums:
  - Mtree = **64.87 M**; **budget = 50.69 M = 0.78× (22 % UNDER Mtree)** → budgets CLEAR non-regression
    scene-wide; current leaf-back = 282.5 M = **4.36× Mtree** (matches the ~5× frame-cost fail).
  - Per-tier Δ/tree: s **−10,314** (×1044 = −10.8 M), l **−3,165** (×3243 = −10.3 M), m **+2,718**
    (×2521 = +6.85 M). The one over-Mtree tier (m, 1.8× Mtree) is more than offset because the park is
    l-dominant and Mtree's s tier is unexpectedly heavy (13.3 k).
  - **Caveat (state honestly):** this is a *total-scene-vert* proxy; FPS is dominated by the *visible*
    near-field. m is the sole over-Mtree tier, so a dense **m-heavy** benchmark view could still regress
    locally even though the scene-wide sum clears. The 22 % headroom gives margin, but the **per-position
    re-gate at ramble/north_woods is the real confirmation** after the density build.
  - **Verdict:** the Planner's budgets are self-consistent with the recommended bar → **budget condition
    MET.** (They could even be loosened slightly given the 22 % headroom, but tighter budgets better
    preserve the crown — keep as-is.)
- **Lever 3 (card thinning) DEMOTED from the budget-recovery path** (per Chris): it cuts *leaf* geometry,
  but the vertex-denominated driver is *bark*. Keep it only as an overdraw/fragment lever, not a vert-budget
  lever. l≤10 k therefore rests on **levers 1+2**, and (per §7 pre-scope) most likely **needs the AC-7
  coarser-l cloud** (RING-scaling alone lands ~24–28 k; §7 targets ~1,700 nodes via SPRIG_SPACE_l≈1.0 +
  coordinated di/dk retune). Treat AC-7 as *expected*, not a remote fallback.
- **Issue 3 — ring-transition verify (NEW REQUIREMENT for the density pass):** radius-scaled RING creates
  junctions where a 24-ring trunk segment meets a 6–8-ring twig. `components==1` will NOT catch cracks /
  T-junction non-manifoldness at the ring-count boundary. **The density-pass Engineer verify MUST add a
  targeted manifold/edge inspection at trunk↔twig ring transitions** (non-manifold-edge count + a visual
  trace at ring-count boundaries), not just re-run the 5-attribute + component contract.
- **−5 % tolerance = a measurement-noise band, not a regression license.** Project's own run-to-run
  characterization is **±1–1.5 ms** at the woodland positions (north_woods the clean metric, ramble
  noisier) — i.e. ~4 % (NW) to ~4.7 % (ramble) of frame time. So −5 % ≈ observed noise. Fine as-is;
  optionally tighten **north_woods (the clean metric) to ~3 %** since its variance is lower.
- **Mtree baseline GLBs REBUILT + restored** (park playable again): the LP GLBs are gitignored build
  outputs (not a `git checkout` restore), so they were regenerated via `CPW_FORCE_MTREE=1` — which also
  supplied the Mtree per-tier vert counts above. Leaf-back GLBs are regenerable anytime from the committed
  `.npz` + skinner.

## Half-1 measurement — lever 1 (radius-scaled RING) — 2026-07-08 — ⚠ OVERTURNS THE FORECAST
Implemented per-STRAND radius-scaled ring in `scripts/leafback_skinner.py::_ring_for_radius` (thick ≥90mm→24,
≥35mm→12, twig→8; per-strand so NO intra-strand transitions), A/B'd via `tmp/leafback_allbucket_verify.py`
(RADIUS_SCALED=0/1), tol matched to the generator (l 51mm).

| tier | ring24 final v | radius-scaled final v | reduction | non-manifold edges (24→scaled) |
|---|---|---|---|---|
| s tier | 4,100 | 2,266 | 1.81× | 172 → **84** |
| m tier | 17,335 | 11,110 | 1.56× | 751 → **433** |
| l tier | 67,238 | **44,610** | 1.51× | 2,884 → **1,768** |

- **Integrity: clean.** All tiers components=1, degenerate=0, 5-attr contract intact. **Non-manifold edges DROP**
  (not rise) — the per-strand approach introduces **no ring-transition cracks** (Issue-3 concern empirically
  absent; the safe no-intra-strand-transition implementation was correct). Ring-transition verify = PASS.
- **★ RING is a WEAK realized lever (~1.5×), NOT the forecast 2.5–3×.** Root cause (measured, `_ring_for_radius`
  ring-sum analysis): the forecast reasoned on RAW ring counts, but the shared `clean_degenerate` weld already
  removes most high-ring redundancy — **uniform-24 sheds 49% of raw verts in cleaning; ring-scaled sheds only 24%.**
  Ring scaling and the cleaner are largely redundant. Per-NODE scaling barely beats per-strand (raw 2.44× vs 2.18×;
  after cleaning, marginal) — so the risky intra-strand-transition path is NOT worth it.
- **★ Lever ordering FLIPS.** The dominant recovery must be **NODE-COUNT reduction** (lever 2 twig decimation +
  AC-7 coarser cloud), which the cleaner does NOT eat (fewer nodes → fewer verts, cleaner-independent). RING stays
  worth keeping as a ~1.5× v/node multiplier that EASES AC-7's burden, but cannot carry the budget.
- **AC-7 target RESET by measurement:** l with lever-1 = 44,610 v / 4,585 nodes = **9.7 v/node**. For ≤10k budget →
  **~1,030 l-nodes** (more aggressive than the §7 pre-scoped ~1,700, which assumed the fuller RING recovery).
- **★ LEVER-1 IS LOAD-BEARING ON LANTERN RISK — record the DEPENDENCY, not just the number.** A 1.5× lever that
  "can't carry the budget" looks demotable, but it is what keeps AC-7's node target ABOVE the lantern floor: WITH ring
  scaling AC-7 needs **~1,030** nodes; WITHOUT it, **~680** (14.7 v/node). That ~350-node gap is the margin between a
  coarse-but-viable crown and a probable AC-6 lantern reversion. **Dropping ring scaling to "simplify" would silently
  lower the AC-7 target into the danger zone.** Lever 1 is therefore KEPT — not as a minor multiplier, but as the thing
  that holds AC-7 off the lantern floor.
- **Scene arithmetic with lever-1-actual:** 175M verts = **2.70× Mtree** (down from 4.36×). Node reduction is the
  path from 2.70× to ≤1.0×. **Half-1 stops here (no fps gate, per owner).** Lever 2 + AC-7 (node-count, the real
  lever) held for a fresh session — now with a measured target and a corrected ordering.
- **`radius_scaled=True` is a PROVISIONAL default, pending Critic sign-off on twig legibility.** The ~1.5× win is real
  and cleaner-independent, but the coarser twigs (ring 8 vs 24) are an *aesthetic* change that has NOT had aesthetic
  review — leaving it default risks an aesthetic change riding in as an engineering default ahead of the Critic (the
  exact anti-pattern the 3-role split exists to prevent). Plausibly fine or even desirable (coarse near-trunk twigs suit
  the "near-trunk sparseness" design principle), but the call must be made ON PURPOSE. Flag for an explicit Critic look
  before it becomes permanent by inertia.
