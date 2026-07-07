# Leaf-Back Skeleton — Space-Colonization / Attractor-Growth Prototype

> **Purpose.** A *comparison line* against the merge-based `build_graph_v2`
> (`docs/leafback_topology_redesign_plan.md`, paused 2026-07-06). That line kept needing
> local patches (trunk elbow → long cross-crown edges → node-collapse) because it has **no
> explicit growth model** — it agglomerates the sprig cloud inward by proximity/mass and
> *derives* directions from lerps and caps, so every fix chases an individual symptom. This
> prototype uses an **explicit, well-established growth model** — space colonization
> (Runions, Lane & Prusinkiewicz, *Modeling Trees with a Space Colonization Algorithm*,
> Eurographics NPH 2007; same family as Runions et al. leaf-venation 2005) — where a
> skeleton **grows outward from the trunk base toward attractor points** under a local
> competition rule. The question this answers: are the merge line's residual artifacts
> **inherent to the crown data**, or an artifact of the *merge mechanism*?
>
> **Isolation discipline (identical to the merge line).** New standalone file
> `tmp/leafback_spacecol.py`. It does **not** import, edit, or run `leafback_graph_v2.py`
> or `leafback_graph.py::build_graph`'s *merge* body — it only calls `build_graph()` to get
> the **same 781-sprig attractor cloud** (reused unchanged) and re-uses the crown constants.
> The three shared mesh functions (`clean_degenerate_geometry` / `enforce_min_twig_diameter`
> / `stitch_bark_islands` in `scripts/generate_trees_mtree.py`) are **called read-only** by
> the render script and **never modified**. Nothing here is committed; nothing in the merge
> line is touched. **Date:** 2026-07-06 · **By:** Opus 4.8 (1M).
>
> **This is the design writeup, written BEFORE the code** (per the project's think-first rule).
> Results + honest comparison are appended after the run.

## What is reused unchanged (apples-to-apples)
- **The 781-sprig attractor cloud** — `leafback_graph.build_graph()` default output
  (`seed=20260706`), positions `nodes[0..n_sprigs-1]`. Same crown envelope (Broad Dome,
  widest ~mid), same density (Poisson `SPRIG_SPACE=0.65 m`), same seed. **No changes to that
  stage.** Measured: 781 points, crown `y ∈ [4.32, 14.38]`, max radius **5.03 m**, mean
  radius 3.55 m, nearest-neighbour spacing min **0.65** / median 0.675 m.
- **Trunk base** `(0,0,0)`, **crown base** `CB = 4.32 m`, **height** `H = 14.4 m`,
  **DBH** 0.381 m — the same specimen constants.
- **Pipe-model thickness** (`r0 = 0.004` tip seed, `r_parent^p = Σ r_child^p`, `p = 2.3`,
  scale so root radius = DBH/2) and **strand decomposition** (thickest child continues the
  stem_id) — copied *verbatim* from `leafback_graph.py` lines 72–100 so taper and
  scaffold-vs-twig are computed identically to the merge line. The only thing that differs
  between the two lines is **how the nodes/edges are generated**.
- **Render path** — the same `edge_tubes()` + camera rig from `tmp/leafback_2c_render.py`
  (1100², EEVEE-Next, same bark material/sun/sky, same crown azimuths `[0,60,120]°` at
  `dist=H·1.15`, same transition close-ups at the fork). Output dict has the **identical
  shape** (`nodes` w/ `pos`/`parent`/`radius`, `children`, `root`, `fork`, `strand`), so the
  renderer runs unchanged.

## The algorithm (standard space colonization)
Canonical Runions form. State: a growing set of tree **nodes** (each `pos`, `parent`) and a
shrinking set of **attractors** `S` (the 781 sprigs).

0. **Clear bole (pre-grow).** There are **zero attractors below `CB=4.32 m`** — every real
   tree has a branch-free bole there. Grow a straight vertical leader from `(0,0,0)` up to
   the fork `(0, CB, 0)` in `D`-length segments. The top of the bole is the seed node for
   colonization. *Why pre-grow rather than let colonization make the bole:* it is
   botanically real (clear bole), it hands the growth a clean central leader, and it
   **structurally forecloses the merge line's elbow** (that elbow came from *placing the
   fork below its own children*; here the fork is the leader tip and growth only continues
   upward from it). This is a modelling choice of the prototype, reported honestly, not a
   post-hoc patch.
1. **Associate.** Each surviving attractor `a ∈ S` finds its single **nearest tree node**
   `n(a)` within the **influence radius `di`**. Attractors with no node inside `di` simply
   wait (they pull nothing this step).
2. **Grow.** Every node `v` selected by ≥1 attractor grows **one** new child at fixed step
   `D` in the **normalized average** of the unit directions to its selectors:
   `dir(v) = normalize( Σ_{a: n(a)=v} normalize(a − v) )`; new node at `v + D·dir(v)`.
   (Start with **no tropism**; an upward/gravity bias is an available lever, noted, not used
   in the base run.)
3. **Kill.** Any attractor within the **kill radius `dk`** of *any* node is removed from `S`.
   This is what terminates twigs *at* leaf positions rather than overgrowing.
4. Repeat 1–3 until `S` is empty or no node grew this step (then stop; report leftovers).

**Forking is emergent, with no valence rule and no cap.** A node stays the nearest node to
attractors on more than one side across iterations, so on later steps it grows a *second*
(or third) child → a fork appears exactly where attractor clusters separate. The task's
"split the tip when attractors pull in divergent directions" is precisely this mechanism;
the canonical nearest-node association is the cleaner, well-established way to get it, so
that is what is implemented. **Whether valence stays low is therefore a measured result,
not an imposed constraint** — the key comparison against the merge line's hard `K=3` cap.

**Tapering is emergent** from the same pipe model: tips (childless nodes, where attractors
were killed) seed `r0`; thickness accumulates trunk-ward by subtree mass. Scaffold vs twig
falls out of the tree structure, no post-hoc classification.

## Parameter choices (grounded in the measured crown), before tuning
All three scale off the **sprig spacing `s ≈ 0.65 m`** (the natural length scale of the
cloud) and the classic Runions guidance (`dk ≈ 2D`, `di` a several-× multiple of `D`).

| Param | Symbol | Chosen start | Why (from the measured crown) |
|---|---|---|---|
| **Step length** | `D` | **0.35 m** (≈ 0.54·s) | Every edge is length `D` by construction, so **long-straight-edges are structurally impossible** (the merge line's 6.6 m rods cannot occur). `D` sets granularity/curvature: small enough that re-averaging each step yields **curved** limbs, not sticks; large enough that a ~10 m crown path is ~28 segments (node count stays in the low thousands). Reported after run. |
| **Kill radius** | `dk` | **0.50 m** (≈ 0.77·s, ≈ 1.43·D) | A tip must grow essentially *onto* a sprig before removing it, so twigs terminate **at** the crown shell. Must satisfy `dk ≳ D` (else a tip can step *past* an attractor without ever entering `dk` → the attractor is never killed → runaway); `1.43·D` gives margin. `dk < s` so one tip doesn't wipe a whole neighbourhood of sprigs at once. |
| **Influence radius** | `di` | **sweep {1.5, 2.2, 3.0} m**, land one | Governs character: **large `di`** → each node averages many attractors → few, smooth, centralized limbs (sparse scaffold); **small `di`** → nodes see only local attractors → bushier, more independent twigs. `2.2 m ≈ 3.4·s ≈ 6.3·D` sits in the classic 4–20·D band and is the expected sweet spot for a legible scaffold→twig read; the sweep confirms/relocates it. **Landed value reported.** |

Guards: iteration cap (safety), and if `S` stalls (no growth but attractors remain) stop and
report the leftover count as **unreached foliage** (the space-col analogue of the merge line's
reachability check).

## What will be measured (same checks as the merge line)
1. **Valence distribution** (children per internal node) + **max** — merge line was
   `{1:1, 2:268, 3:256}`, max 3 **by cap**. Ours is **uncapped** → does it stay low naturally?
2. **Sibling angle** min / median — merge line enforced `θ_min = 35.1°`. Ours emergent.
3. **Hop count sprig→root.** Ours uses tiny `D` segments, so raw segment-hops are *not*
   comparable to the merge line's few large hops. Report **both**: raw segment-hops **and**
   **branch-order depth** (number of *forks* root→tip) as the apples-to-apples hierarchy
   measure (merge line branch-orders were the median-10 hop figure's real content).
4. **Long-straight-edge / elbow checks** — same as 2b/2c: longest non-bole edge (expect ≈`D`),
   count of edges > 3 m (expect 0 by construction), and the fork→dominant-limb bend angle.
5. **Emergence check** — does forking + taper appear **without** any cap or `θ_min` rule?
6. **Cost** — node/edge count vs the merge line's 1377 (for the Stage-3 skinning note).

## Renders (identical framing to the merge line)
Same as `leafback_v2_crown_2c_view{0,1,2}.png` + `leafback_v2_transition_2c_{0,1}.png`:
full-crown at azimuths `[0,60,120]°`, plus the trunk→scaffold transition close-up — so the
output drops directly next to everything already reviewed. Files:
`tmp/leafback_spacecol_crown_view{0,1,2}.png`, `tmp/leafback_spacecol_transition_{0,1}.png`.

---

## Results (seed 20260706, same 781-sprig cloud — NOT committed, prototype only)

**Landed parameters:** `D = 0.35 m`, `dk = 0.55 m`, `di = 2.2 m`, `θ_spawn = 25°`
(now the generator defaults in `tmp/leafback_spacecol.py`).

### Tuning path (honest — this is where the one real space-col artifact showed up)
The **naive** algorithm (no spawn guard, `dk = 0.50`) produced a characteristic
space-colonization failure: a **"witch's-broom"** — chokepoint nodes just above the bole kept
being the nearest node across dozens of iterations and each spawned a near-parallel child, so
**valence ran to 42** with **sibling angle ≈ 0°** (dozens of coincident twigs from one point).
Two levers were examined:
- **Kill radius alone.** Raising `dk` to 1.0 m (> sprig spacing) removed the broom (valence
  max 3, sib-min 72°) but over-claimed the cloud — only **50 tips**, a bare scaffold. `dk`
  trades broom against crown density and cannot fix both at once. *Finding:* `dk` must be
  ≳ attractor spacing to avoid lingering pullers, but pushing it there sparsifies the crown.
- **Spawn-angle guard (adopted).** A node spawns a *new* child only when the pull direction
  diverges > `θ_spawn` from its existing children; a near-parallel pull continues the existing
  frontier child instead of stacking a parallel twig. This **decouples** broom-suppression from
  density: at `dk = 0.55` (dense crown) the broom is gone. `θ = 15/25/35°` gave *identical*
  clean results — the broom children were ~0° apart (caught by any θ) while real forks are
  naturally ≥ 40° apart (untouched). This is emergent forking, **not a hard valence cap.**

### Topology checks (tree-wide) — vs the merge line's Stage-2c numbers
| check | space-col (this line) | merge `build_graph_v2` (2c) |
|---|---|---|
| **Valence distribution** | `{1:470, 2:192, 3:12}` — **max 3, ZERO >3, emergent** (no cap) | `{1:1, 2:268, 3:256}` — max 3 **by hard `K=3` cap** |
| **Sibling angle** min / median | **40° / 87°** — emergent (no θ rule on the tree) | 35.1° / 75.5° — **enforced** θ_min=35° |
| **Fork → dominant-limb bend (elbow)** | **7.3°** — clean, no fix needed | 22.9° (after the dedicated 2b elbow fix; was 113° before) |
| **Longest non-bole edge** | **0.35 m** (= step `D`, structural) | 1.50 m (after the 2c subdivision fix; was 6.64 m before) |
| **Edges > 3 m** | **0** (structurally impossible) | 1 (the trunk only, after 2c) |
| **Branch-order depth** (forks root→tip) min/med/max | 2 / 12 / 26 | (merge hop-count median 10) |
| **Segment hops** sprig→root min/med/max | 14 / 37 / 52 | median 6 raw (few large hops) — *not* comparable* |
| **Foliage reached** | **759 / 781 (97.2%)** — 22 unreachable corridor/pocket attractors | 781 / 781 (100%, by construction) |
| **Node count** | 891 | 1377 |

\* Hop counts are *not* directly comparable: space-col uses many uniform `D≈0.35 m` segments
(so raw hops are high), the merge line uses a few large hops. The apples-to-apples hierarchy
measure is **branch-order depth** (number of forks root→tip): median **12** — a deep, orderly
trunk→scaffold→branch→twig hierarchy.

### Emergence check (the point of the comparison)
- **Forking emerged from geometry, capped at valence 3, with NO hard valence rule** — the
  spawn-angle guard is a "don't stack coincident twigs" rule, not a "≤3 children" rule; the
  distribution is bifurcation-dominant (192 forks of 2, 12 of 3) *because that is what the
  attractor competition produces*, not because 3 was imposed.
- **Sibling separation emerged** (min 40° > the merge line's enforced 35°) with no θ_min pass.
- **Taper emerged** from the identical pipe model (root 190.5 mm → 3.8 mm tips, DBH target
  190 mm hit exactly): scaffold-vs-twig falls out of subtree mass, same as the merge line.
- **The two artifacts the merge line spent Stages 2b/2c fixing — the trunk elbow and the long
  straight cross-crown edge — cannot occur here by construction** (clear-bole start; every edge
  is length `D`). No fix cycles were needed for either.

### The one cost that is real
**22 of 781 attractors (2.8%) are unreached** — corridor/pocket sprigs that sit just beyond a
passing branch's `dk` and never get claimed. The merge line reaches 100% by construction (it
connects every sprig inward). This is the honest trade: space colonization *grows toward* the
cloud and can leave sparse pockets, where the merge line *starts from* every sprig. 2.8% is a
handful of missing outer-shell twigs, tunable via `dk`/`di`, but non-zero and worth stating.

### Renders
Framed identically to the merge line, so they overlay directly on everything reviewed:
- `tmp/leafback_spacecol_crown_view{0,1,2}.png` — full crown, azimuths [0,60,120]°.
- `tmp/leafback_spacecol_transition_{0,1}.png` — trunk→scaffold close-up (55°, 90°).
- Side-by-side montages: `tmp/_cmp_crown.png` (space-col top row / merge-2c bottom row),
  `tmp/_cmp_transition.png`.

**Pipeline note (why the render is a two-step):** `import scipy` **hangs inside Blender's
bundled Python** (BLAS/OpenMP conflict) — this is what silently hung the first render attempt.
Fixed by generating the skeleton in **system Python** (`leafback_spacecol.py` → saved to
`tmp/leafback_spacecol_graph.npz`) and having the Blender script **load the arrays** (pure
numpy, no scipy). The 3 shared mesh functions are still called read-only, unchanged.

## Honest comparison — does it read as a tree?

**Decisive win: the trunk→scaffold transition.** The close-up (`_cmp_transition.png`) is the
clearest result. Space-col: the bole enters and splits into **smooth, tapering, curved limbs**
— a legible branch junction with real pipe-model taper and organic curvature. This is *exactly*
the thing the merge line spent two whole fix-cycles (2b elbow, 2c straight-rod/collapse)
chasing, and here it is **clean for free**, because (a) the clear bole hands growth a straight
central leader and (b) per-step re-averaging makes limbs *curve* instead of snapping. The
merge-2c close-up beside it is a thicket of **straight sticks** at sharp angles with an
unreadable junction and visible tube-overlap.

**Clear structural win: legibility + curvature.** The whole space-col crown has a readable
**trunk → primary rib → branch → twig** hierarchy of smooth continuous limbs. The merge-2c
crown is denser but reads as a **chaotic bramble of straight spikes** — the "fine-twig clutter /
full-crown gestalt" the merge line flagged as unresolved is, on direct comparison, its dominant
visual character. Space-col simply does not have that tangle.

**Where space-col falls short — the "paper-lantern / cage" effect (sharpened by visual review).**
Honestly, the full crown does *not yet* read as a dense, classic broad-dome canopy. The renders
show a **small number of long, nearly meridian-spanning primary ribs** sweeping apex→base, hung
with only **sparse short twigs** — it reads as a **wireframe "paper lantern" / cage**, open
enough to see straight through, rather than a volume-filling crown.

**The valence distribution corroborates this, and is the key diagnostic.** `{1:470, 2:192,
3:12}` — **the large majority of nodes (470 of 674 branching-or-pass-through nodes) are
valence-1 pass-through points**, i.e. straight continuations, not branch points. Only 204 nodes
branch at all. That is the signature of **a few dominant ribs racing outward and claiming
attractors *along their path*** (each claimed attractor just extends the rib by one pass-through
segment) rather than **branching repeatedly to fill interior volume**. The mechanism is sound —
the ribs are clean, curved, tapered — but it is currently *under-branching*. The thin envelope
**shell** of attractors + isotropic uniform-`di` growth compounds it (limbs hug the shell in
evenly-spaced meridians). Plus 22 unreached pocket attractors (2.8%) thin the outer twigs. Both
lines share a residual short perpendicular **twig-spike** layer, milder in space-col.

**Verdict (the comparison the fork was run to make).** Neither line is a finished tree, but
**they fail in different classes, and space-col's failure is the more tree-shaped and the more
tractable one.** The merge line's residual is an *inherent tangle of straight sticks* whose bones
are not a tree; every fix chased one named artifact (whack-a-mole, as the plan doc predicted).
Space-col's residual is *"under-branched / too sparse"* — its bones **are** a tree (clean trunk,
tapered curved limbs, correct hierarchy, no elbow, no long edges, emergent low valence). The gap
is **denser interior branching**, and — crucially — this is a **parameter-tuning** target on a
*validated mechanism*, not another structural fix.

## Next session — the concrete step (do NOT do a structural fix)
**Hypothesis:** the current **influence radius `di = 2.2 m` is too large relative to the crown**
(radius ~5 m). A tip within 2.2 m of a far attractor is pulled straight toward that *single*
attractor and extends its rib (a valence-1 pass-through), instead of seeing several *nearby
sub-clusters* and branching toward them. Large `di` → long ribs; branching needs the tip to be
influenced by a *tight local cluster* whose members then separate into forks.

**Next step = a parameter sweep aimed at denser branching** (the mechanism is validated; this is
tuning, not redesign):
- **Smaller `di`** (sweep ~0.8–1.6 m, i.e. ~1.2–2.5·sprig-spacing) so tips respond to local
  sub-clusters and fork more, rather than chasing one distant attractor.
- **More permissive branch-spawn** — lower `θ_spawn` and/or relax the spawn guard so genuine
  nearby divergences spawn a new child instead of being folded into the frontier rib. Watch the
  witch's-broom does not return (it was ~0° children; a floor around 12–18° should stay safe).
- Re-measure the **valence distribution as the primary success metric**: the target is a *much*
  larger valence-2/3 share (more branch points, fewer valence-1 pass-throughs) and a fuller,
  volume-filling crown in the renders — while **holding** the structural wins (no elbow, no
  long edges, emergent valence ≤3-ish).
- Secondary levers if the sweep alone isn't enough: **tropism** (already a parameter, set to 0),
  and lower **`dk`** to recover the 22 unreached pockets. **Interior/jittered attractors** would
  break the shell→meridian regularity but that is an *attractor-stage* change, prototyped
  separately — not part of this generator's sweep.

This **confirms the plan doc's hypothesis**: an explicit growth model yields a cleaner, more
tree-shaped artifact class than proximity-merge, and its residual is a coherent *tuning* target
(denser branching) rather than a sequence of unrelated geometric patches. **Space colonization
is the confirmed direction to carry forward** over the merge line.

## Status
Prototype only — **not committed except this doc**, nothing in the merge line touched, the 3
shared mesh functions unmodified. Committed: `docs/leafback_spacecolonization_prototype.md` (this
file). Uncommitted working artifacts (all in gitignored `tmp/`): `leafback_spacecol.py`
(generator), `leafback_spacecol_measure.py` (metrics/sweep), `leafback_spacecol_render.py`
(Blender render), `leafback_spacecol_graph.npz` (saved skeleton), and the `leafback_spacecol_*` /
`_cmp_*` PNGs. **Paused for the night — next session runs the `di`/`θ_spawn` sweep above.**
