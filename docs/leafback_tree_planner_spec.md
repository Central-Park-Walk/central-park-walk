# Leaf-Back London Plane Crown Skeleton — Planner Spec

Spec version: v4 (2026-07-07)

> **Role 1 (Tree Planner) artifact.** This is the authoritative, versioned statement of *what a
> correct London plane (Platanus × acerifolia) "leaf-back" crown skeleton must exhibit*. The Critic
> (Role 2) checks renders + metrics against this document, point by point. The Engineer (Role 3)
> implements against it. This document owns **design intent only** — it contains no code and does not
> reference generator internals. It is a living spec: revise it (bump the version, add a changelog
> line) only on an escalated **design** question, never to paper over a defect the Engineer can fix.
>
> Fits the machine in `docs/leafback_pipeline.md` (§"The artifact flow"). Consolidates the accumulated
> knowledge of lines A (`leafback_topology_redesign_plan.md`), B
> (`leafback_spacecolonization_prototype.md`), and C (`leafback_trunkscaffold_prototype.md`).

## Changelog
- **v4 (2026-07-07)** — **production skinning path adopted.** The trunk-scaffold (line C)
  space-colonization skeleton has **no Mtree path** — the production mesher
  `m_tree.ManifoldMesher().mesh_tree()` only accepts an opaque Mtree `Tree` object, not a
  `(pos,parent,radius,strand)` node graph — so the leaf-back line is skinned by a **custom
  per-strand tube skinner, now promoted to `scripts/leafback_skinner.py`**. Validated on the
  m tier REF at production RING=24: rendered mesh = **1 connected component**, full Mtree
  attribute contract written (radius, stem_id, hierarchy_depth, branch_extent, direction), 0
  degenerate faces (`docs/leafback_meshdisconnect_diagnosis.md`). Three spec effects: **(1)**
  AC-5(iv)'s connected-component check is now verified on *that* skinner's output, and the old
  per-EDGE preview skinner `edge_tubes` is **demoted to preview/visualization only** (the earlier
  "62 / 3 disconnected components" was a wrong-skinner artifact, not a skeleton defect). **(2)**
  AC-8 integration is now concretely defined as skinner → attribute contract → london_plane GLB →
  `scripts/perf_gate.sh`. **(3)** a new known-acceptable residual **AC-15** (fork-junction
  interpenetration, ~6.5 % self-intersecting faces at preview RING) is recorded. This changes
  *how AC-5(iv)/AC-8 are verified and what ships* — **not *what a correct tree is*.**
- **v3 (2026-07-07)** — AC-5 hardened after a Critic-process failure (iteration 2 PASSed a render with a
  visible near-closed loop + a disconnected branch; see `docs/leafback_critic_protocol.md`). AC-5 loop/
  disconnection is now a **trace-first hard gate**; the acyclic-graph metric is marked **necessary-but-
  insufficient** (a near-loop is acyclic; a mesh-stage disconnection leaves the graph connected), replaced
  by **post-mesh** connected-component + near-loop checks; and the R3/R4 diagnostic renders
  (component-colored + top-down orthographic) are **required before any PASS** when a loop/disconnection is
  suspected. No change to *what a correct tree is* — this tightens *how AC-5 is verified*.
- **v2 (2026-07-07)** — added AC-14 (primary-limb caliber / bold hierarchy, blocking) + Growth-model
  subsection, per owner guidance that limb thickness is a life-stage/age property grounded in DBH +
  bucket data. Resolves the iteration-1 escalation (Critic marginal-PASS: line C read as *a tree* but
  the scaffold/primaries read as thin wire, not bold structural limbs; no AC captured primary caliber).
- **v1 (2026-07-07)** — initial consolidation. Establishes AC-1…AC-13, the PASS rule, the reference
  specimen, and the blocking-vs-tuning classification of line C's honest-shortfall list.

---

## Reference specimen & data (everyone judges the same tree)
All criteria are stated against one canonical specimen so the Planner, Critic, and Engineer are never
arguing about different trees.

- **m tier REF** — the prototype crown bucket (`docs/crown_type_buckets.md` +
  `tmp/leafback_bucket_validation.json`):
  - Total height **H = 14.4 m**
  - Crown base / fork height **CB = 4.32 m** (⇒ crown height CH = H − CB ≈ 10.08 m)
  - Crown radius **RX = 5.04 m** (max horizontal extent)
  - **DBH = 0.381 m** (trunk base radius = DBH/2 = 0.19 m)
  - **Primary count N = 4** (the bucket's `primaries` datum — the count of scaffold origins)
- **Attractor cloud:** the **781-sprig** m-tier shell from `leafback_graph.build_graph()`,
  **seed 20260706**. Measured character: crown y ∈ [4.32, 14.38], max radius 5.03 m, mean radius
  3.55 m, nearest-neighbour spacing ~0.65 m. **Critical known property: the cloud is a pure SHELL —
  0 % of sprigs lie in the crown interior (ρ<0.6·RX); 99.4 % sit on the outer shell.** The chosen
  skeleton model must be one that a shell of foliage targets *matches* (a trunk-plus-radial-scaffold
  model does; a single-point cage does not).
- **Standard render framings** the Critic judges against (from
  `tmp/leafback_trunkscaffold_render.py`): full-crown ×3 at azimuth [0°, 60°, 120°]; trunk→scaffold
  transition close-up ×2; two near-trunk "from the trunk looking out" shots; one "look straight up"
  money shot. Reference photos = Chris's mature London plane crowns shot from near the trunk.

---

## What PASS means
The Critic issues **PASS only when every *blocking* AC (below) is visually satisfied against the
reference photos.** Metric agreement alone is **NOT** sufficient — the metric proxies are early-warning
instruments, not the verdict. **Visual judgment overrides metrics**: this is how the project has
actually made progress (line A passed every local metric yet never read as a tree; line B's valence
distribution *diagnosed* the hollow lantern that metrics alone would have called "clean"). A render may
satisfy every metric and still FAIL on a blocking AC if it does not *look* right against the photos; a
render may miss a metric target and still PASS if the Critic judges the visual intent met and names the
metric as a known-acceptable residual. Known-acceptable tuning targets (AC-9…AC-13) do **not** block
PASS; the Critic notes them as residuals for the next tuning pass.

Convergence additionally requires the **performance gate** (AC-8) — a visual PASS that busts the fps
floor is not converged (see `docs/leafback_pipeline.md` §"Performance gate").

---

## Acceptance criteria (numbered checklist)

Each AC gives: **(a)** intent, **(b)** how the Critic judges it visually, **(c)** the metric proxy (the
named check from `leafback_trunkscaffold_measure.py`) if one exists, **(d)** blocking vs known-acceptable.

### AC-1 — Persistent central trunk / leader
- **(a) Intent:** A real tapering central axis runs from ground level *well up into the canopy* and
  then dissolves into codominant limbs — it does **NOT** terminate at a single low fork point. (Lines A
  and B both collapsed to one pinned point at crown-base; this is the defect AC-1 rules out.)
- **(b) Visual:** In the trunk→scaffold transition close-ups and the crown views, a single dominant
  central mass is legible continuing upward past the lowest branches, thinning as limbs peel off, and
  fading into the upper crown (no hard stop, no starburst hub). Reference target: leader persists to
  ~70–75 % of tree height before dissolving.
- **(c) Metric proxy:** trunk taper monotonicity (base→top radius must step *down* monotonically along
  the spine); `spine_top` height ≥ ~0.6·CH above CB. No single node at crown-base with all scaffolds
  attached (see AC-5 single-point convergence).
- **(d) BLOCKING.**

### AC-2 — N scaffolds at well-separated heights
- **(a) Intent:** N (= the crown bucket's primary-count datum; N=4 for m tier REF) scaffold
  branches break off the trunk at **meaningfully different, well-separated heights** — distributed
  across a substantial fraction of the trunk's in-crown height, not bunched in a narrow band near one
  point.
- **(b) Visual:** In crown + transition views the primary limbs clearly leave the trunk at *different*
  vertical positions spread over roughly the lower ¾ of the crown; no cluster of primaries emerging
  within a small height window.
- **(c) Metric proxy:** count of distinct scaffold attachment heights = N; spread of attachment
  heights spans ≥ ~0.5·CH; min vertical separation between adjacent attachment heights is non-trivial
  (not near-zero). Azimuthal separation of scaffolds ≥ θ_min (35°) — no two primaries at nearly the
  same angle AND nearly the same height.
- **(d) BLOCKING.**

### AC-3 — Near-trunk sparseness ("stand inside the tree")
- **(a) Intent:** Standing at the trunk looking up/out, the viewer sees a **handful of thick, legible,
  widely-spaced limbs with real visible sky gaps** — the "walk up and stand inside the tree"
  experience. NOT a tangle (line A's failure), NOT a single-point radiating cage (line B's failure).
- **(b) Visual:** The two near-trunk "from the trunk" shots and the "look up" money shot show a small
  number of clearly-separated proximal limbs with open sky visible between them near the trunk;
  ramification is visibly sparse close in.
- **(c) Metric proxy:** near-trunk density profile (leaf-tip / branch count vs radial distance ρ) must
  show few tips in the innermost ρ band (ρ < ~0.2·RX); the proximal limbs should be a small count
  (order N, not dozens).
- **(d) BLOCKING.**
- **Note:** the near-trunk *heft* half of this experience is delivered by **AC-14** — a handful of
  clearly-separated proximal limbs only reads as "standing inside the tree" if those limbs are **bold
  boughs**, not wires. AC-3 (few, spaced) and AC-14 (thick) together make the near-trunk view.

### AC-4 — Distance-scaled branching density (monotone outward)
- **(a) Intent:** Branching density increases monotonically from trunk to shell: sparse/simple near
  the trunk, progressively denser and finer toward the canopy shell.
- **(b) Visual:** Across the crown views, ramification is coarse and open near the axis and visibly
  finer/denser toward the outer envelope; no inversion (dense core, sparse shell) and no uniform
  density throughout.
- **(c) Metric proxy:** near-trunk density profile is **monotone increasing** in tips-per-band from the
  innermost ρ band out to the shell band (line C achieved 4 → 10 → 30 → 110 → 85; monotone through the
  shell peak is the target, a slight apex/outermost fall-off is acceptable — see AC-12).
- **(d) BLOCKING.**

### AC-5 — No structural artifacts
- **(a) Intent:** None of the named structural defects the project has already fought: **(i)** no
  trunk-elbow (sharp direction reversal at a fork, on a *thick* limb); **(ii)** no long unsubdivided
  straight edge spanning much of the crown; **(iii)** no node-collapse (multiple distinct nodes at
  coincident points / zero-length edges); **(iv)** no unnatural loops or branches curving back to
  rejoin themselves or the trunk; **(v)** no single-point convergence of all scaffolds (the pinned-fork
  hub).
- **(b) Visual — TRACE FIRST (hard gate, before any aesthetic AC):** The Critic must trace every visibly
  thick limb from the trunk to its tip and confirm, with image locations: no thick down-then-up chevron at
  the trunk transition; no rod running straight across the crown without taper/curve/re-fork; no
  star-of-rods hub; **no branch that curves back to close or nearly-close a loop; no branch that stops
  mid-air with a free end and geometry resuming across a gap; no disconnected/orphan segment; no rejoin of
  two limbs;** scaffolds originate at *different* points, not one. Judged on the **component-colored** and
  **top-down orthographic** diagnostic renders (see AC-5 render requirement), not only the perspective
  beauty shots. **Any such finding is a FAIL** (or AMBIGUOUS pending the diagnostic renders) — do not
  proceed to grade AC-14 or other aesthetic ACs. Governed by `docs/leafback_critic_protocol.md` R1–R6.
- **(c) Metric proxy:**
  - (i) elbow: worst *thick-limb* fork bend — thick limbs (radius above the twig threshold) must have
    **no** bend > ~60° that is a direction reversal. Bends > 150° are permitted **only** on the
    thinnest terminal twigs (that is AC-13 tip-jitter, cosmetic), not on scaffolds.
  - (ii) long-edge: **0** edges > 3 m other than the vertical trunk itself.
  - (iii) node-collapse: min non-trunk edge length ≥ ~0.05 m; **0** zero-length edges; **0** coincident
    thick-node pairs.
  - (iv) loops / disconnection — **run on the FINAL post-mesh/post-stitch geometry that is rendered, NOT
    the skeleton graph.** The skeleton graph is acyclic-and-connected *by construction* (single root, every
    node has one parent), so a graph-only check is **necessary-but-insufficient**: it cannot see a
    **near-loop** (a branch curving back without actually rejoining is still acyclic) or a **mesh-stage
    disconnection** (thin-twig culling / degenerate-edge cleanup breaks the mesh while the graph stays
    connected). **The rendered mesh is the output of the production per-strand skinner
    `scripts/leafback_skinner.py`** (the leaf-back line's production skinning path — the trunk-scaffold
    skeleton has no Mtree path, so this custom per-strand tube skinner is what ships; see the v4 changelog).
    The connected-component check is run on **that** skinner's output — feeding the trunk-scaffold skeleton —
    **NOT** on the preview `edge_tubes` mesher. Required checks (`tmp/leafback_integrity_diag.py`, R7):
    **connected-component count of the rendered mesh = 1** (any orphan piece = FAIL), and **near-loop
    proximity = 0** flagged limbs (no non-twig node within ε of a topologically-distant node). **`edge_tubes`
    is a fast preview/visualization skinner ONLY (one independent tube per edge, no shared vertices) and must
    NEVER be used as the connectivity source of truth** — a future session must reach for the production
    skinner `scripts/leafback_skinner.py` or the fixed `tmp/leafback_integrity_diag.py` (which must carry the
    `radius`/`stem_id` vertex attributes to report honestly). A passing metric may only FAIL a render — it
    can **never clear a defect the Critic can see** (visual overrides metrics; protocol R2).
  - (v) single-point convergence: number of scaffolds sharing one origin node = 0 (they attach at N
    distinct trunk points; see AC-2).
- **Required diagnostic renders (R3/R4):** every submission ships a **component-colored** render (each
  connected mesh piece a distinct color — orphans pop) and a **top-down orthographic** wireframe (removes
  the projection ambiguity of perspective shots — a real loop reads as a ring from directly above). **No
  PASS may be issued while a Critic-requested diagnostic render is outstanding.**
- **(d) BLOCKING** (all five sub-checks; (iv) is a trace-first hard gate).

### AC-6 — Emergent regularity, not hard caps
- **(a) Intent:** Valence, sibling angle, and taper should **emerge from the growth mechanism** rather
  than needing hard post-hoc caps. The space-colonization line proved emergent low valence / clean
  taper / clean sibling spacing is achievable without caps, and that this is *preferred* over the merge
  line's patch-after-patch (whack-a-mole) pattern. This AC exists to rule out, by design, the anti-
  pattern where every fix chases one named artifact.
- **(b) Visual:** The crown reads as a coherent grown structure, not a capped/clamped one — no
  witch's-broom (dozens of near-parallel twigs from one node), no artificially fanned forks.
- **(c) Metric proxy:** valence distribution with **max valence ≤ ~4 emerging without a hard valence
  cap in the code** (bifurcation-dominant, as line B's `{1:470,2:192,3:12}` and line C's
  `{1:576,2:198,3:20,4:1}`); sibling angle min > 0 and not clustered at ~0° (no coincident twigs);
  taper emerges from the pipe model, not a profile table. **Note for the Critic:** this AC is partly a
  *mechanism* property the Critic cannot see in a single render — judge it via the emergent signatures
  (clean valence distribution, no broom, no fanned regularity) and defer to the Engineer's submission
  note on whether a hard cap was introduced. A render that only looks clean *because* a cap was bolted
  on does not satisfy AC-6's intent.
- **(d) BLOCKING** on the *visible* signatures (no broom, no coincident-twig fan, emergent taper).
  Whether the code literally contains a cap is a design-review item escalated to the Planner, not a
  render FAIL.

### AC-7 — Reuse of validated data/components
- **(a) Intent:** Reuse the existing validated components **without modification unless a specific
  deficiency is found and noted**: the crown-envelope / sprig-cloud generation (per-bucket fork height,
  primary count N, sprig density — `build_graph`'s attractor cloud) and the pipe-model taper logic
  (`PIPE_POWER=2.3`, tip seed `R0=0.004`).
- **(b) Visual:** N/A directly — verified via the Engineer's submission note and by the specimen data
  matching the Reference section (same 781-sprig cloud, seed 20260706; same DBH-scaled root radius).
- **(c) Metric proxy:** attractor count = 781, seed = 20260706, root radius = DBH/2 = 0.19 m hit by the
  pipe model; any deviation from these must be accompanied by a stated, specific deficiency.
- **(d) BLOCKING** as a discipline check (unexplained modification of a protected/shared component is a
  FAIL); satisfied by default when the protected components are used unchanged.

### AC-8 — Performance ceiling (convergence gate)
- **(a) Intent:** The final generator, wired into tree generation at CPW's full target scale (real
  park, ~6808 trees in dense woodland), must hold the game's **> 45 fps** floor on the reference GPU
  (RTX 3060 Ti) at the established woodland benchmark positions.
- **(b) Visual:** N/A — measured, not judged.
- **(c) Metric proxy:** **integration is concretely defined as:** feed the trunk-scaffold skeleton
  through the production per-strand skinner `scripts/leafback_skinner.py` (which **must emit the full
  Mtree attribute contract — `radius`, `stem_id`, `hierarchy_depth`, `branch_extent`, `direction` — so
  the three shared cleaners, foliage/card placement, and the wind bake all work unchanged**), export the
  **london_plane GLB**, then run `scripts/perf_gate.sh` (real-park `--park --all-london-plane`) reading
  median FPS at both **ramble** and **north_woods** — both must be **> 45**. Node/edge count vs the
  current committed skeleton is unchanged as the cheap per-iteration early-warning proxy (skinning
  geometry ∝ node count; line C ≈ 1037 nodes / m tier). Run at/near convergence, not every iteration.
- **(d) BLOCKING for convergence** (a visual-PASS skeleton that busts the floor is not converged — it
  returns to the Engineer to simplify, and to the Planner if simplification changes design intent).

### Growth model (design intent behind AC-14)
Primary-limb caliber is **not a free knob** — it is the emergent consequence of how the tree grew, and
it is fully grounded in data already in the pipeline. The Engineer is directed to model the *cause*, so
that AC-14 is satisfied by construction rather than by bolting a thickness multiplier onto a wiry
skeleton (an arbitrary multiplier would violate the spirit of AC-6). The four data-grounded facts:

1. **Life stage = the crown bucket.** `docs/crown_type_buckets.md` defines the three buckets as an
   explicit age progression: bucket 1 (s tier) is *young* — high fork, thinner and more uniform
   limbs; bucket 2 (m tier, our REF) is *mature*; bucket 3 (l tier) is *old/veteran*,
   explicitly "heavy near-horizontal low primaries." **Which bucket a specimen is sets how heavy its
   low primaries read.** The model must render the caliber appropriate to the specimen's life stage —
   the caliber gradient is *shallow* for a young ovoid and *steep* for a veteran.
2. **DBH is the measured caliber budget.** DBH = 0.381 m (trunk base radius r₀ = DBH/2 = 0.19 m, the
   AC-7 anchor). Trunk base cross-section A₀ = π·r₀² is the *total* caliber budget. By da Vinci's rule /
   the pipe model (AC-7's `PIPE_POWER=2.3`), cross-section is ~conserved across each branch point, so
   A₀ is *partitioned* up the tree rather than invented per limb. Sum of the primary calibers is bounded
   by what the trunk carries — a thick primary necessarily means fewer/thinner siblings, not free mass.
3. **Age gradient — lower = thicker — from acropetal growth order.** Scaffolds form acropetally: the
   lowest formed first (when the tree was a sapling) and has thickened by cambial growth every season
   since → it is the **oldest, thickest** primary and commands the **largest, most-ramified** sub-crown.
   Each higher scaffold formed later → younger, thinner, smaller sub-crown. So primary caliber and
   sub-crown size both **decrease with attachment height** as a direct read-out of growth order. (This
   corrects line C's inverted partition, where the *lowest* primary got the *fewest* attractors.)
4. **Propagation — thick primary → thick secondaries.** A primary's base caliber flows *down* its own
   sub-crown by the same pipe model: a heavy low primary's secondaries and twigs scale to its base, so
   the whole sub-crown reads proportionally bold. Caliber hierarchy is therefore one continuous
   pipe-model field seeded by the DBH budget and the growth-ordered partition — not three independent
   gauge choices.

The Engineer implements the *cause* (growth-ordered crown partition so lower/older primaries command
larger sub-crowns, plus a DBH-anchored caliber budget weighted toward lower attachments), from which the
visible thick→medium→fine hierarchy of AC-14 emerges — consistent with AC-6's "emergent, not capped."

### AC-14 — Primary-limb caliber / bold structural hierarchy
- **(a) Intent:** The crown reads as a **majestic London plane**, not merely *a tree*: primaries are
  **bold structural limbs**, visibly heavier than secondaries, which are visibly heavier than twigs — a
  legible thick→medium→fine gauge hierarchy, **not one wire gauge throughout** (the iteration-1 defect).
  Additionally the **lower primaries are visibly thicker than the higher primaries** (the acropetal age
  gradient of the Growth model). Caliber is tied to **life stage**: for the m tier REF (mature) the
  low primaries read clearly bold but *not* as extreme as a veteran (bucket 3); a young s tier
  (bucket 1) reads lighter and more uniform. This AC is what separates a wiry meridian-cage from a tree
  with real trunk-to-limb heft.
- **(b) Visual:** Judged against the reference **uplooking / branch-structure** photo (Chris's
  near-trunk crown shots) and the mature full-tree photos. In the trunk→scaffold transition close-ups
  and the "look up" money shot, the proximal primaries must read as **substantial boughs** you could not
  mistake for the fine outer twigs; the eye should be able to trace a clear caliber step-down from trunk
  → primary → secondary → twig. In the crown views the **lowest** primaries are the most massive limbs
  in the tree and the caliber of primaries **diminishes with height** up the trunk. No render where all
  limbs share a single apparent thickness can PASS.
- **(c) Metric proxy** (all provisional/tunable — early-warning, not the verdict, per the PASS rule):
  - **Lowest-primary base caliber vs trunk.** Lowest primary base radius ≥ **~0.55·r₀** of the trunk
    base radius (r₀ = DBH/2 = 0.19 m ⇒ ≥ ~0.10 m), targeting a **~0.55–0.70·r₀ band** for the mature
    m tier REF. (Provisional: this is the mature-bucket target; a veteran would sit higher, a young
    ovoid lower.)
  - **Age gradient (monotone-ish).** Primary base radius **decreases with attachment height** — the
    highest primary's base radius should be materially smaller than the lowest's (proxy: highest primary
    ≤ ~0.6× the lowest primary's base radius for the REF). No inversion where an upper primary out-calibers a lower one.
  - **Gauge separation (thick→medium→fine).** The three gauges read as distinct populations, not a
    continuum of hairs: median primary base radius ≥ **~2×** median secondary base radius, and median
    secondary ≥ **~2×** median twig base radius (provisional ratios; the point is a clear step, not the
    exact factor).
  - **Pipe-model / da Vinci conservation at the first scaffold region.** At each scaffold fork the sum
    of downstream calibers (continuing leader + departing primary) ≈ the upstream trunk caliber under
    the pipe exponent (Σ r_childᵖ ≈ r_parentᵖ, p = `PIPE_POWER` = 2.3), within ~±20 %. This is the check
    that the bold primaries are *paid for* out of the DBH budget rather than fabricated (ties AC-14 to
    AC-7's protected pipe-model taper).
- **(d) BLOCKING.** The *visible* bold hierarchy (thick→medium→fine, lower-thicker-than-higher) is the
  gate; the metric bands are the early-warning proxies and are tunable per bucket. Whether the caliber
  emerges from the growth model vs. a bolted-on multiplier is an AC-6-style mechanism concern — a render
  that reads bold only because a flat thickness multiplier was applied does not satisfy AC-14's intent
  and is escalated to the Planner.

---

## Line C honest-shortfall list — blocking vs known-acceptable classification
Line C (the current best) reported five residual shortfalls (§8 of `leafback_trunkscaffold_prototype.md`).
Each is classified explicitly so the Critic knows what blocks PASS versus what is cosmetic. **None of
these are structural regressions** — all project structural checks stay clean; they are the natural next
tuning targets.

### AC-9 — Scaffold emergence variety
- **Shortfall:** all N primaries leave the trunk at the same ~60° angle and arc similarly; real limbs
  vary branch angle and curvature.
- **(b) Visual:** the primaries look mechanically uniform in their departure angle/curve.
- **(c) Metric proxy:** spread (variance) of per-scaffold emergence elevation angle — currently ~0.
- **(d) KNOWN-ACCEPTABLE tuning target** (does not block PASS). Fix = per-scaffold jitter on emergence
  elevation + mild gravity/light tropism in the core-crossing phase.

### AC-10 — Wedge-boundary reachability gaps
- **Shortfall:** ~7 % of attractors unreached, in thin azimuthal seams between the N golden-angle
  wedges.
- **(b) Visual:** faint gaps in the shell foliage along the seams between primaries.
- **(c) Metric proxy:** **reachability %.** Currently 93.3 % (line B ran ~97 %). **Threshold for
  known-acceptable: reachability ≥ ~90 %.** If reachability drops below ~90 %, it is promoted to
  BLOCKING (the crown reads visibly holed). At/above ~90 % it is a tuning residual.
- **(d) KNOWN-ACCEPTABLE tuning target above ~90 %; BLOCKING below ~90 %.** Fix = more primaries for
  larger buckets (the datum allows it) or a light cross-wedge attractor-sharing pass.

### AC-11 — "Arcy" frontal read
- **Shortfall:** from some head-on azimuths the primaries' arcs echo line B's meridians; side/among-
  the-limbs views read markedly more tree-like than head-on ones.
- **(b) Visual:** head-on crown view (az 0°) looks slightly meridian-arced rather than fully
  volumetric.
- **(c) Metric proxy:** none direct (a gestalt read). Judged from the az-[0,60,120]° set — if only the
  head-on frame is affected and the 60°/120° frames read tree-like, it is cosmetic.
- **(d) KNOWN-ACCEPTABLE tuning target.** Does not block PASS provided AC-1…AC-5 hold. Fix overlaps with
  AC-9 (emergence variety) and AC-12. **Note:** the arcy/meridian read partly resolves once **AC-14**
  holds — bold, caliber-graded low primaries break the thin-meridian silhouette that makes the head-on
  arcs echo line B; a wiry primary reads as a meridian, a bold bough does not.

### AC-12 — Apex density
- **Shortfall:** the top scaffold both continues the leader and fills the apex, leaving the crown top a
  little thin.
- **(b) Visual:** the very top of the crown reads slightly sparse in the crown views / look-up shot.
- **(c) Metric proxy:** near-trunk density profile's outermost/topmost band (a mild fall-off after the
  shell peak is acceptable, e.g. line C's 110 → 85). A *severe* apex void would be visible and promote
  this toward blocking.
- **(d) KNOWN-ACCEPTABLE tuning target.** Fix = a dedicated short leader-continuation origin at
  `spine_top`.

### AC-13 — Twig tip-jitter
- **Shortfall:** a handful of hair-twig direction reversals (line C: 9 bends >150°, all on the thinnest
  ~17 mm terminal twigs out at the shell).
- **(b) Visual:** cosmetically harmless; not visible as a structural kink at normal viewing distance.
- **(c) Metric proxy:** count of >150° bends **restricted to the thinnest terminal twigs** — these are
  explicitly NOT AC-5(i) elbows (AC-5(i) covers thick limbs only). Any >150° bend on a *thick* limb is
  an AC-5 FAIL, not tip-jitter.
- **(d) KNOWN-ACCEPTABLE tuning target.** Fix = apply the same directional blend used on the core-
  crossing leader to the shell twig tips.

### AC-15 — Fork-junction interpenetration (skinner residual)
- **(a) Intent:** Forks read as **organic, smooth branch collars** — a child limb merges into its
  parent with a filleted junction, as ManifoldMesher produces, not as a raw tube driven through another
  tube's wall.
- **Shortfall:** the production per-strand skinner `scripts/leafback_skinner.py` produces **raw tube
  interpenetration** at forks (child tube pierces the parent surface with no smooth collar), measured at
  **~6.5 % self-intersecting faces** at the preview RING resolution — worst at the thickest low scaffold,
  milder mid/upper crown (`docs/leafback_meshdisconnect_diagnosis.md`).
- **(b) Visual:** at close range a fork looks like interpenetrating cylinders rather than a fused bough;
  not distinguishable as a defect at s/m-tier viewing distance.
- **(c) Metric proxy:** self-intersecting face-pair fraction of the skinned mesh (~6.5 % at preview
  RING). This is a **mesh-quality** residual of the skinner, **NOT** an AC-5 structural artifact — the
  mesh is a single connected component (AC-5(iv) holds); it does not create orphans, loops, or
  disconnection.
- **(d) KNOWN-ACCEPTABLE tuning target** (does not block PASS at s/m-tier viewing distance; owner-
  accepted 2026-07-07). Intended fix = production **RING ≈ 24 + smoothing iterations** at bake time
  (already logged in the skinner module header so it is not rediscovered as a "new" bug).

---

## Summary table

| AC | Title | Blocking? |
|----|-------|-----------|
| AC-1 | Persistent central trunk/leader | **Blocking** |
| AC-2 | N scaffolds at separated heights | **Blocking** |
| AC-3 | Near-trunk sparseness | **Blocking** |
| AC-4 | Distance-scaled density (monotone) | **Blocking** |
| AC-5 | No structural artifacts (elbow/long-edge/collapse/loop/single-point) | **Blocking** |
| AC-6 | Emergent regularity, not hard caps | **Blocking** (visible signatures) |
| AC-7 | Reuse validated data/components | **Blocking** (discipline) |
| AC-8 | Performance ceiling >45 fps | **Blocking** (convergence gate) |
| AC-14 | Primary-limb caliber / bold structural hierarchy | **Blocking** |
| AC-9 | Scaffold emergence variety | Known-acceptable tuning |
| AC-10 | Wedge-boundary reachability | Known-acceptable ≥~90 %; blocking below |
| AC-11 | "Arcy" frontal read | Known-acceptable tuning |
| AC-12 | Apex density | Known-acceptable tuning |
| AC-13 | Twig tip-jitter | Known-acceptable tuning |
| AC-15 | Fork-junction interpenetration (skinner residual) | Known-acceptable tuning |
