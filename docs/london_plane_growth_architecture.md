# London Plane — Connection Grammar & Target-Directed Growth (Planner study + proposal)

**Role:** Planner — *research and PROPOSE only*. Nothing built, no protected file edited, nothing
committed. · Opus 4.8 (1M) · 2026-07-08
**Deliverable of:** "London plane connection grammar — growth-to-target, reusing leaf-back's envelope."
**Status:** connection-grammar study (cited) + target-directed-growth design **PROPOSAL** (clearly
marked) + leader-continuity verify-gap note + explicit reuse confirmation.
**Prior art grounded in PRIMARY sources** (read in full, not snippets): Runions, Lane & Prusinkiewicz
2007 and Palubicki et al. 2009 (Algorithmic Botany, U. Calgary) — see §0.5. *Honest process note: an
earlier draft of §2–§4 was written from secondary summaries and then re-grounded in these primary papers
at Chris's instruction; the papers materially sharpened the mechanism (they did not merely decorate it),
which is exactly why prior-art-first is the rule. See [[feedback_check_prior_art_first]].*

---

## 0. The reframe, and a sharper diagnosis than "arc-interpolation"

The task's reframe is correct and I adopt it: **keep the envelope target, replace the connection
method.** The crown envelope per tier (Upright Ovoid / Broad Dome / Low-Forked Spread), fit from the
iNaturalist silhouette data, is *where* each tree must end up; what's broken is *how* branches get from
trunk to that shell.

But I must correct one premise on a point that changes the fix, per investigation-first: **the current
production skeleton (`scripts/leafback_skeleton.py`, "line C") is already a target-directed grower, not a
pure arc-interpolator.** Reading the code, it has:

- a persistent pipe-model-tapered central **spine** (ground → `spine_frac·CH`, `leafback_skeleton.py:218`);
- **N scaffold origins** breaking off at distributed heights × golden-angle azimuths (`:231`);
- a **directed structural leader** (Phase A) growing *forward* from the trunk surface toward the running
  centroid of live attractors (`grow_scaffold` Phase A, `:122`);
- **space-colonization ramification** (Phase B) at the shell (`:146`);
- a **growth-order capacity partition** — lowest primary = oldest = largest sub-crown, target tips
  `∝ w^(p/2)` where `w` = attractors above attachment (da Vinci "area-above", `:264`);
- **pipe-model taper** already applied (`radius[i] = (Σ r_child^p)^(1/p)`, `:65`).

So the machinery the task asks us to add — leader, apical growth, taper, growth order — *is partly
already present*. It still renders as a wire-armature / hanging-basket cage. **Why it fails anyway is the
real finding, and it is more specific than "it interpolated an arc":**

1. **The attractor cloud is a hollow SHELL, not a filled volume.** `leafback_graph.py:49` places every
   sprig within `SHELL_THICK = 1.3 m` of the envelope surface, biased *onto* the surface
   (`depth = U(0,1)^1.6 · 1.3`). The entire crown interior beyond ~1.3 m from the skin has **no
   attractors**. Growth therefore has nothing to build *through* — every limb shoots from the trunk to
   the shell and can only ramify *on* the shell. This is exactly the failure mode the space-colonization
   literature warns about: Runions et al. require the crown **volume** to be filled with attraction
   points, not its surface ([Runions, Lane & Prusinkiewicz 2007](https://algorithmicbotany.org/papers/colonization.egwnp2007.large.pdf)).
   Chris's own note — "space colonization's failure was the hollow lantern from missing interior
   attractors, NOT the attractor principle" — is precisely correct and is provable from this one line.

2. **The core-crossing leader is UNFORKED, so the pipe model makes it a constant-radius garden hose.**
   Phase A adds one child per step across the empty core (`:140`). Under the pipe model, an unbranched
   chain has `radius[i] = radius[child]` — **constant radius along its whole length**. The leader arrives
   at the shell carrying the summed thickness of everything it feeds, then holds that thickness, untapered,
   all the way back across the void to the trunk. That is the "garden-hose / no-taper arc" in the
   screenshots — and it is a *direct, mechanical* violation of Leonardo's rule (below), not a stylistic
   choice. All the real forking and taper is crammed into the thin shell where Phase B runs.

3. **Growth order exists as a partition weight but is not expressed in the geometry.** The four primaries
   each emit as a *single* arc-to-shell, so the age gradient (old/low = thick, many sub-limbs; young/high
   = thin, simple) never becomes visible branch architecture. The capacity heuristic sizes the *shell
   patch* each scaffold colonizes, not a legible excurrent→decurrent limb hierarchy.

**Conclusion of the diagnosis:** the defect is not "no growth model." It is **(a) shell-only attractors
(hollow lantern) and (b) unforked core-crossing leaders (constant-radius, no en-route ramification).**
The fix is to fill the envelope as a *volume* and to ramify *continuously along* the growing limbs with
pipe-model taper and age-graded emission — i.e. a genuine growth grammar, targeted to the same envelope.
"You can't draw what you don't understand" — the missing understanding is specifically the *volumetric,
continuously-ramifying, age-ordered* connection between trunk and crown.

---

## 0.5 Prior art — primary sources (read in full)

The method leaf-back reaches for is a published, mature line of work from the Algorithmic Botany group
(U. Calgary). Reading the two seminal papers directly (not summaries) validated the diagnosis and named
the mechanisms the proposal needs. **The single most important confirmation: our hollow-lantern failure
is a figure in the original paper.**

**Runions, Lane & Prusinkiewicz 2007, "Modeling Trees with a Space Colonization Algorithm"**
([EG Workshop on Natural Phenomena](https://algorithmicbotany.org/papers/colonization.egwnp2007.large.pdf)).
- **Attractors fill the crown VOLUME by default.** "The attraction points were **uniformly distributed
  in the crown volume**" (§3). The crown envelope is any test-inside-volume shape (they use a surface of
  revolution); it is **seeded throughout**, not on its surface.
- **★ Our shell cloud is their Figure 7 — the explicit *degenerate* case.** "A shrub generated with
  attraction points **placed exclusively near the envelope** … has an **open, sparse branch system, with
  small twigs limited to the crown surface**." That is a verbatim description of our cage. The primary
  source confirms shell-only attractors → hollow surface crown; it is not our inference.
- **Algorithm (matches ours):** each node grows a segment of length `D` toward the normalized-average
  direction of attractors within radius of influence `di`; an attractor is deleted when a node comes
  within kill distance `dk`. Pipe model sets diameters basipetally, `rⁿ = r₁ⁿ + r₂ⁿ`, `n≈2–3` (our
  `PIPE_POWER=2.3` is in-range).
- **★ Excurrent↔decurrent is EMERGENT from `di` + envelope width, not a bespoke parameter.** "narrower
  trees have a clearly delineated trunk, whereas in widely spread trees even the main limbs are highly
  ramified. This correlation … is an **emergent property of the algorithm, and captures … excurrent (with
  the main stem) and decurrent (without a distinct main stem)**" (§3; Fig. 5 varies `di=∞ → 8D`). This is
  our three-bucket age axis, named and mechanized.
- **Density / perf levers are canonical and named:** `N` (attractor count) and `dk` set sparseness
  ("Decreasing N and increasing dk yields crowns that are increasingly sparse"); `D` (segment length) is
  the node-count unit; **node decimation is step (d)** of the pipeline, **node relocation (e)** reduces
  branching angles, **subdivision (f)** smooths curves. A **hierarchy of branch sizes** (mature-tree
  look) is produced by **progressively adding attractors with decreasing spacing** (Fig. 8).
- **Branch self-intersection is prevented by the algorithm** (Discussion) — so our AC-15 fork
  interpenetration is a *skinner* (tube-overlap) artifact, not a skeleton property. Consistent with the
  2026-07-07 diagnosis.

**Palubicki, Horel, Longay, Runions, Lane, Měch & Prusinkiewicz 2009, "Self-organizing tree models for
image synthesis"** ([SIGGRAPH](https://algorithmicbotany.org/papers/selforg.sig2009.pdf)) — the follow-on
that adds bud fate, apical control, and shedding.
- **★ Removing apical control over development *is* the excurrent→decurrent age progression — proven as a
  developmental animation.** Fig. 11: "**a progression from the excurrent form of the young tree to the
  decurrent form of the old tree**" produced by removing apical control over the course of development;
  Fig. 10 varies *when/where* control is removed. This is the three-buckets-are-one-growth-process reframe,
  in the primary literature (§4.2).
- **The age knob has a named form: the Borchert–Honda `λ`.** Resource `v` reaching a fork is split between
  the continuing main axis and the lateral by `λ`: **`λ>0.5` biases the main axis → excurrent**;
  **`λ<0.5` → decurrent** (Fig. 7 sweeps `λ=0.46…0.54`). An alternative "priority model" concentrates
  resource on the top-`κ` most-lit axes (more excurrent as fewer axes are favored). Either gives a single,
  citable dominance parameter.
- **Light environment = shadow propagation + light-based bud fate + shedding.** Buds sense light via a
  voxel **shadow-propagation** grid; shaded buds get less resource; **branch shedding** (Takenaka 1994:
  shed when light-gathered / branch-size falls below threshold) **"is the key to the formation of tall
  boles"** (§4.4, Fig. 14). This is precisely the mechanism for our missing **woodland drawn-up** form (§2
  second axis): shade → suppress + shed lower/interior limbs → tall clear bole, narrow high crown.
- **Perception geometry (maps onto our `di`/`dk`):** bud perception cone `θ≈90°`, distance `r=4–6`
  internode lengths; occupancy radius `ρ=2` internode lengths. At our `D=0.35 m` that is `di ≈ 1.4–2.1 m`
  — our tuned `di_far=1.9` sits in range, but the leader-hack `di_near=6.0` is far outside it (further
  evidence the Phase-A leader is a shell workaround, unnecessary once the volume is filled).
- **Pipe model with memory:** diameter accumulates basipetally and is **not** reduced when branches are
  shed (the tree "remembers" past leaves) — matters for tall-bole caliper.

**Net effect on this proposal:** the reframe and the volumetric-fill fix are confirmed by the *original*
paper (Fig. 7 is our bug); the age axis is a *named, published mechanism* (Runions `di`+envelope,
emergent; or Palubicki BH-`λ` / apical-control schedule, explicit); the woodland second axis has a
concrete implementation (shadow propagation + shedding); and the density/smoothing levers (`D`, `N`,
decimation, relocation) are canonical pipeline steps, not inventions. §2–§4 below are written accordingly.

---

## 1. The connection grammar (study, with sources)

The pattern by which trunk and crown connect in *Platanus × acerifolia* — the thing leaf-back never
modeled.

### 1.1 Growth order — the tree is a frozen record of its own history
A tree's form is a time-integral: the branches that exist *first* (lowest, oldest) have had the longest
to thicken and to grow their own sub-structure; the branches formed *last* (highest, youngest, and the
distal tips of every limb) are thinnest and simplest. Any grammar must **emit branches in growth order**
and let the older ones accumulate both caliber and ramification. This ontogenetic ordering is the
organizing principle of the architectural-model tradition of
[Hallé, Oldeman & Tomlinson (1978), *Tropical Trees and Forests: An Architectural Analysis*](https://books.google.com/books/about/Tropical_Trees_and_Forests.html?id=Z-7wCAAAQBAJ),
in which crown form emerges from meristem behaviour repeated and **reiterated** through the tree's life,
modulated by environment.

### 1.2 Taper law — pipe model / Da Vinci's rule
Branch cross-sectional area at any point ≈ the sum of the cross-sectional areas of the daughters above it;
equivalently, caliber tracks the **leaf area subtended**. This is Leonardo's rule, formalized as **pipe
model theory**: leaf mass above a level is proportional to the summed stem cross-section at that level,
independent of age or habitat ([Shinozaki et al. 1964](https://ci.nii.ac.jp/naid/110001881211/en);
review: [Lehnebach et al., *Ann. Bot.* 2018, "the pipe model theory half a century on"](https://dx.doi.org/10.1093/aob/mcx194)).
[Eloy (2011), *Phys. Rev. Lett.*](https://link.aps.org/doi/10.1103/PhysRevLett.107.258101) shows the same
area-preserving exponent emerges when branch diameters are set to hold a **constant probability of
wind-fracture** — i.e. taper is a mechanical optimum, not decoration. `PIPE_POWER = 2.3` in our code sits
squarely in the empirical 2.0–2.5 range. **The law governs two things at once:** taper *along* a limb, and
the low-thick / high-thin gradient *between* limbs. The current constant-radius leader violates both;
correct growth satisfies them for free *because radius is derived from what each node actually feeds* —
provided limbs ramify as they go (so there are children to sum).

### 1.3 Branching pattern — where forks occur and at what angle
Platanus extends by **sympodial / zig-zag** relay in the mature crown: after the leader's dominance
relaxes, one or more upper laterals overtake and displace the terminal, so the axis is a chain of relayed
segments with a characteristic slight zig-zag and forks at the relay points, rather than one smooth
monopodial rod ([excurrent→decurrent mechanism, Iowa State Extension, *Tree Anatomy 101*](https://naturalresources.extension.iastate.edu/forestry/tree_biology/101.html)).
Lateral emergence angles are moderate (not the near-perpendicular of a spruce, not the acute broom of a
Lombardy poplar); self-pruning removes shaded interior laterals, so surviving forks bias outward and
upward toward light.

### 1.4 Apical dominance and its decay with age — the central axis of the reframe
Young trees are **excurrent**: strong apical dominance suppresses laterals, giving a single leader and a
narrow, conical/ovoid crown. As the tree matures, apical *control* weakens; upper laterals become
co-dominant, the crown **broadens and rounds**; in old open-grown trees the single leader is often lost
entirely, leaving a few massive low limbs and a wide spreading crown. This excurrent→decurrent transition
is a **fundamental, near-universal feature of hardwood ontogeny**
([Iowa State *Tree Anatomy 101*](https://naturalresources.extension.iastate.edu/forestry/tree_biology/101.html);
[decurrent form overview, ScienceDirect Topics](https://www.sciencedirect.com/topics/agricultural-and-biological-sciences/decurrent);
classical treatment: [Brown, McAlpine & Kormanik 1967, "Apical dominance and form in woody plants: a
reappraisal", *Am. J. Bot.*](https://bsapubs.onlinelibrary.wiley.com/doi/abs/10.1002/j.1537-2197.1967.tb06904.x)).
**This decaying-dominance parameter is the single knob that should generate all three of our buckets** —
see §2 for the verify/refute.

### 1.5 The optimization the form solves — light capture vs. structural/hydraulic cost
Crown form is the solution to *maximize intercepted light per unit of structural and hydraulic
investment*. Branches taper (pipe model / Eloy: minimum material for a fixed fracture risk), fork toward
light and self-prune when shaded, and the whole crown grows toward a self-similar shape set by gravity and
light sensing ([Bentley et al. / crown self-similarity, arXiv 1801.00964](https://arxiv.org/pdf/1801.00964)).
This optimization is also **why the same species takes two different shapes by light environment**:
- **Open-grown** (Great Lawn specimens): light on all sides → low branching retained, wide spreading
  decurrent crown, large crown-depth ratio.
- **Woodland / drawn-up** (Ramble, competition): side light suppressed → self-pruned lower limbs, tall
  clear bole, narrow crown high on the stem.
The park needs **both**, which means light environment is a *second* generator axis distinct from age
(§2).

### 1.6 London-plane specifics
- *Platanus × acerifolia* naturally makes a **longer bole and a higher, slenderer canopy** than
  *P. orientalis* — it holds excurrent form longer before spreading; some of that is also early formative
  pruning of street stock ([London plane, Wikipedia](https://en.wikipedia.org/wiki/London_plane);
  [Trees and Shrubs Online, *Platanus × hispanica*](https://www.treesandshrubsonline.org/articles/platanus/platanus-x-hispanica/)).
- **Pollarding morphotype:** many urban planes are pollarded to knuckled "fists" (cyclic winter cutback),
  giving a dense witches'-broom of same-age shoots from swollen knuckles — a *distinct* architecture, not a
  point on the natural age series ([Forest Garden, "Pollarded Platanus"](https://forestgardenblog.wordpress.com/2014/05/27/pollarded-platanus/);
  [Morton Arboretum, London planetree](https://mortonarb.org/plant-and-protect/trees-and-plants/london-planetree/)).
  **Recommendation: do NOT model the pollard morphotype for Central Park.** CP's planes (Mall, Literary
  Walk, Fifth Ave. perimeter) are grown as natural spreading specimens, not pollarded to fists; the
  pollard is a European-streetscape form. Keep it out of scope unless a specific CP location proves
  otherwise from reference photos (real-world-observation rule).
- **Crown-depth-to-height ratio rises with age / openness:** young street tree ~small crown high on a
  clear bole; open veteran ~crown occupying most of the height. This matches our `cb_frac` dropping
  0.35 → 0.30 → 0.20 across s → m → l.

---

## 2. Verdict — are the three buckets three time-slices of one growth process?

**Yes, along the age axis — strongly, and it is confirmed by both our own bucket table and the
literature. But a complete generator needs a second axis (light environment), and the current three
buckets sample only the open-grown series.**

Read the bucket parameters as an ontogenetic series (`leafback_skeleton.py:326`):

| tier | name | H (m) | DBH | `cb_frac` | `aspect` (W/H) | profile — widest at height *t* |
|------|------|------:|----:|----------:|---------------:|-------------------------------|
| s | Upright Ovoid | 10.0 | 7″ | 0.35 | 0.80 | t ≈ 0.55 (**above** mid) |
| m | Broad Dome | 14.4 | 15″ | 0.30 | 1.00 | t ≈ 0.50 (mid) |
| l | Low-Forked Spread | 22.0 | 28″ | 0.20 | 1.20 | t ≈ 0.33 (**below** mid) |

Every parameter moves **monotonically**, and each move is exactly what decaying apical dominance predicts:
- **aspect 0.80 → 1.00 → 1.20**: crown broadens with age (dominance decay → co-dominant laterals spread).
- **widest point descends** (0.55 → 0.50 → 0.33): excurrent egg (widest high) → dome → decurrent spread
  (widest low). This is the *signature* of the excurrent→decurrent shift.
- **`cb_frac` 0.35 → 0.30 → 0.20**: crown base descends as low limbs are retained and thicken.
- **DBH 7″ → 15″ → 28″ and H 10 → 14.4 → 22**: caliper and stature accumulate with age.

So the three "shapes" are **not independent silhouettes to be hit separately — they are one growth
trajectory sampled at three ages**, and an **age (dominance-decay) parameter can generate all three.** This
is not speculation: Palubicki et al. 2009 Fig. 11 shows *exactly* this — removing apical control over
development yields "a progression from the excurrent form of the young tree to the decurrent form of the
old tree" (§0.5). The **named knob** is the Borchert–Honda `λ` (main-axis vs. lateral resource split;
`λ>0.5` excurrent → `λ<0.5` decurrent), scheduled to **decay with tier age** — or, in the plainer Runions
2007 model, the **radius of influence `di` together with envelope aspect** produces the same
excurrent↔decurrent emergent axis. The iNaturalist envelope data is not thereby thrown away: it becomes the
*ground-truth checkpoint* the age trajectory must pass through at each tier (fit the three tables → solve
for the `λ`-schedule / `di`+aspect that reproduces them).

**The refutation-check that keeps this honest:** age and *light environment* are confounded in these three
buckets. A woodland plane stays narrow, drawn-up, high-crown-based **even when old**, because competition,
not youth, suppresses its laterals (§1.5). Our s/m/l as defined are the **open-grown** series (aspect
*increasing* with size). A full model wants **two parameters — ontogenetic age × light/competition** — of
which the current buckets are the age series at one light setting. This matters for the park: Great Lawn =
open-grown series (what we have); Ramble/North Woods = drawn-up woodland form (a narrower envelope at the
*same* age), which the three buckets do **not** currently represent. The literature gives this second axis
a concrete mechanism (§0.5): **shadow-propagation light sensing + light-based bud fate + branch shedding**
(Palubicki §4.4 — shedding shaded lower/interior limbs "is the key to the formation of tall boles"). So the
woodland form is not a fourth hand-authored envelope — it is the *same* grower run under a shaded light
field. Flagging now so it is a designed axis, not a later surprise. (Woodland-perf note: those are the
exact stands that are vertex-bound — see §4.)

---

## 3. PROPOSAL — target-directed growth generator (this is a PROPOSAL, not a spec)

> Everything in §3 is a design proposal for Chris's sign-off, per the multi-position-ADR rule. No code
> exists for it. It is written to **drop into** the existing stages, not replace them.

**Shape:** constrained / envelope-biased forward growth. Grow a real tree forward (leader + apical
dominance + taper + growth order) but bias every growth step to fill the tier's crown **volume**, so the
result naturally lands on the envelope without either the leaf-back arc or the space-colonization lantern.

**G1 — Fill the envelope as a VOLUME, not a shell (the lantern fix).**
Replace the 1.3 m surface shell (`leafback_graph.py:49`) with attraction points distributed through the
**whole** crown interior bounded by the profile table — dense enough near the skin to define silhouette,
present throughout the interior so limbs have something to ramify *through*. This is Runions et al.'s
actual input (crown *volume* filled with attractors) rather than the degenerate shell we shipped. Interior
density can fall off toward the core (real crowns are shell-weighted) but must be **non-zero** to the
centre.

**G2 — One forward growth process with an age (apical-dominance-decay) parameter.**
A single grower, parameterized by an **age/dominance value α** that reproduces s/m/l as time-slices (§2).
Bind α to a **named, published mechanism** (§0.5), not a bespoke term:
- **Leader + apical dominance:** either the **Borchert–Honda `λ(α)`** (main-axis vs. lateral resource
  split, `λ>0.5→0.5→<0.5` as α ages → excurrent ovoid → dome → decurrent spread; Palubicki Fig. 7/11) or,
  in the simpler Runions model, **`di(α)` + envelope aspect** (large `di` + narrow envelope → distinct
  leader; small `di` + wide envelope → highly-ramified, no leader; Runions Fig. 5). Both are *emergent*
  — the leader is not scripted, it falls out of the parameter. This is the knob that *makes* the three
  envelopes instead of hand-authoring three shells.
- **Growth-order emission:** laterals are emitted in order along each axis as it extends; older (lower)
  laterals get more subsequent growth iterations, so they thicken and ramify most — the age gradient
  becomes *visible* branch hierarchy, not just a partition weight.
- **Continuous ramification with pipe-model taper:** limbs **fork as they traverse the volume** (sympodial
  relay, §1.3), so no long unforked span exists — which means the pipe model produces **continuous taper**
  (each node sums real children) and the garden-hose is structurally impossible. Radius stays derived, not
  imposed.

**G3 — The biasing mechanism (how growth is steered to the envelope without arc or lantern).**
Recommended: **space-colonization-style growth over the volumetric attractor cloud of G1**, with the
envelope table as a hard **growth boundary** (a node may only grow toward attractors inside the profile
envelope; attractors are consumed within a kill radius). This is the mechanism the current code *reaches
for* — the fix is upstream (G1 volume) and in-limb (G2 continuous forking), not a new steering law.
- vs. **leaf-back arc:** there is no interpolation step; position is the emergent result of competing for
  interior space, so limbs bend *because attractors pull them*, with taper and forks the whole way.
- vs. **space-colonization lantern:** interior attractors (G1) mean the frontier ramifies through the
  volume before reaching the skin, so no valence-1 ribs spanning an empty core.
- The existing directed Phase-A leader is **retained but demoted** to short trunk→crown-base clearance
  (the "guaranteed clear proximal length"), not a full core-crossing arc — it should hand off to
  volumetric colonization *at the crown base*, not at the shell. **Primary-source check (§0.5):** the
  Phase-A leader hack exists *only* to cross the empty core of a shell cloud (its `di_near=6.0` is 3× the
  literature's `di≈1.4–2.1 m` perception range); once G1 fills the volume, the canonical algorithm grows
  the leader on its own via large `di` in a narrow envelope (Runions Fig. 5). The hack is a symptom of the
  shell bug, not a needed feature.

**G4 — Output contract: feeds `leafback_skinner.py` UNCHANGED.**
The grower emits the same node graph the skinner already consumes — `nodes[{pos, parent, radius}]` +
`strand[]` + `root` — via the same `.npz` written by `build_leafback_skeletons.py`. **No skinner change,
no contract change** (verified in §5). `strand` (primary-child continuation = Mtree `stem_id`) and the
pipe-model `radius` are produced exactly as today (`_finish`, `leafback_skeleton.py:54`); only the *node
positions and the fork structure that generates them* change.

**What this proposal deliberately does NOT claim:** it does not add foliage/card logic (unchanged
downstream), and it does not by itself solve perf (§4).

---

## 4. Perf — honest accounting (growth does not escape the density budget)

**Per-tier LOD0 vertex budgets** (blocking, from `docs/leafback_lod0_density_escalation.md`): Upright Ovoid
≤ 3 k · Broad Dome ≤ 6 k · Low-Forked Spread ≤ 10 k v/tree. Current line-C skin **fails ~5× on m and ~10×
on l** (measured `l ≈ 71 k`). The escalation doc establishes `bark_verts ≈ skeleton_nodes × RING(24)`, so
**node count is the driver.**

**Target-directed growth does not reduce this — it re-homes it, and in one respect makes it worse before
better:** G1's volumetric fill *adds* interior attractors, which without a governor means *more* nodes.
The honest consequence:

- **The vertex budget must become a first-class GENERATOR INPUT.** The grower grows to a **target tip /
  node count** per tier (derived from `budget / RING`), reached via apical-dominance limits + self-pruning
  of shaded interior laterals (both are real biology, §1.5, and both are natural stop criteria). The
  canonical method gives two named node-count knobs (§0.5): **`D` (segment length)** — larger `D` = fewer
  nodes, the direct coarsening dial — and **`N` (attractor count)**; plus **skeleton decimation as
  pipeline step (d)** of Runions 2007 (Fig. 1d), a *built-in* post-pass, not a bolt-on. So node reduction
  is native to the method, not a workaround. This **supersedes** the AC-7 approach of
  *generate-dense-then-coarsen-the-shell* (`SPRIG_SPACE` up-tuning): a grower simply stops growing at
  budget (tune `D`/`N`) or decimates via step (d), rather than post-hoc thinning a shell. Net verdict on
  the density work:
  - **Lever 1 / AC-7 (coarser attractor cloud, `SPRIG_SPACE`): ADAPTED, not reused as-is.** The post-hoc
    shell-coarsening knob is replaced by a *grow-to-node-budget* stop criterion. The underlying goal
    (fewer nodes born) is identical; the mechanism moves upstream into growth. `{SPRIG_SPACE, di, dk}` as a
    *coupled retune* no longer applies to a shell; the analogous couple becomes {interior attractor
    density, kill radius, target tip count}.
  - **Lever 2 (radius-scaled RING, ~1.5× v/node): REUSED unchanged.** It lives in the skinner
    (`_ring_for_radius`, `leafback_skinner.py:199`), is generator-agnostic, and stays. The escalation doc
    flags it as *load-bearing on lantern risk* — and G1's volumetric fill directly reduces that risk, so
    the two are complementary.
- **Woodland is vertex-bound** (`project_woodland_perf_investigation.md`): the Ramble/North Woods stands
  are exactly where a bark-vertex blow-up hurts most, and (per §2) exactly where a *narrower drawn-up*
  envelope is wanted — which, helpfully, is a **lower** node budget. Design the drawn-up woodland form and
  its tighter budget together.
- **LOD1** (currently skipped for london_plane) is the other lever the growth grammar doesn't change:
  a grown skeleton decimates to an LOD1 the same as any other. Out of scope here but noted.

**Bottom line:** perf is *not* solved by switching to growth. It requires the node budget to be an explicit
per-tier growth target, plus the retained radius-scaled RING, plus (eventually) LOD1. State this in any
future spec so the density problem is designed-in, not rediscovered.

---

## 5. Reuse confirmation (explicit)

**SURVIVES — confirmed by reading the code:**
- **Envelope targets** (Ovoid / Broad Dome / Low-Forked Spread) and the **iNaturalist silhouette data**:
  reused as the growth boundary + per-tier checkpoint (§2, §3-G3).
- **Per-bucket profile tables** (`leafback_skeleton.py:318` `_T_*/_P_*`): repurposed from
  interpolation shells into **growth boundaries / volumetric fill bounds** — same numbers, new role.
- **`scripts/leafback_skinner.py` + the 5-attribute contract: REUSE CONFIRMED (this is the biggest
  reuse, and it holds).** Evidence:
  - The skinner's **input** is a minimal, generator-agnostic node graph: `load_graph_npz` reads only
    `pos, parent, radius, strand, root` (`leafback_skinner.py:304`); `build_tube_mesh` documents its
    input as "*a leaf-back node-graph `g` (keys: nodes[{pos,parent,radius}], strand[list])*" (`:218`).
  - The skinner's own header states its reason for existing is that "*a skeleton is a skeleton*" — it
    skins "*the node graph … regardless of how the nodes were produced*," writing the full contract so
    the **shared cleaners + foliage + wind bake run unchanged** (`:1`, `:28`).
  - The **5 output attributes** (`radius`, `stem_id`, `hierarchy_depth`, `branch_extent`, `direction`)
    are all **derived by the skinner from the node graph** (`:28`–`:35`), not supplied by the generator.
    A growth grammar that emits `(pos, parent, radius, strand)` therefore satisfies the contract with
    **zero skinner changes**.
  - The `radius_scaled` RING lever and the axial-emergence weld fix live entirely in the skinner and are
    unaffected by how nodes are grown.
  - **One caveat to design to, not a blocker:** the skinner's cross-strand weld tolerance is tuned to the
    thickest node's azimuthal ring spacing (`π·r_max/RING`); a grown skeleton with different caliper
    distribution should re-confirm the weld margin, but this is a parameter check, not a contract change.
- **Attractor-cloud machinery (`leafback_graph.py`): PARTIALLY reused, repurposed.** The sprig-placement
  code becomes the **volumetric** attractor generator (G1) — same idea (Poisson-ish thinned point cloud in
  the envelope), changed from a 1.3 m shell to a filled volume. The bottom-up *merge tree* it also builds
  is already dead in production (line-C ignores it; `leafback_graph.py:19`) and stays dead.

**DIES:**
- **Arc-interpolation / core-crossing unforked leader** (`grow_scaffold` Phase A as a full arc to shell,
  `leafback_skeleton.py:122`) — the defect. Replaced by clear-bole leader + volumetric colonization from
  the crown base (§3-G3).
- **Shell-only attractor placement** (`leafback_graph.py:49`, `SHELL_THICK` regime) — replaced by
  volumetric fill.
- **Post-hoc shell coarsening as the density lever** (AC-7 `SPRIG_SPACE` up-tune) — replaced by
  grow-to-node-budget (§4).
- **Any assumption of constant-radius / no-growth-order limbs** — impossible once limbs ramify
  continuously and radius is derived from real children.

---

## 6. Verify-gap — the contract needs a LEADER-CONTINUITY check (applies to ANY generator)

**Finding (grounded in `docs/leafback_meshdisconnect_diagnosis.md`):** the integrity gate's
`components == 1` check is **blind to a severed leader**, and the current Broad Dome's visible upper-trunk
discontinuity is a live instance of this blind spot.

- The **actually-rendered** trunk-scaffold mesh had **62 connected components**, while the integrity
  diagnostic reported **3** — because the diagnostic omitted the `radius`/`stem_id` attributes the real
  render uses, under-reporting disconnection ~20×. **The gate can pass a mesh that is visually severed.**
- Worse for *this* symptom specifically: `stitch_bark_islands` has a **`stem_id` "same-branch skip"** — it
  deliberately declines to weld junctions *within one strand* (to preserve twig ring cross-sections). The
  central trunk/leader is a single strand (`stem_id = 0`). So the very junctions along the leader that
  ring-framing left gapped (gap `∝ radius`, worst at the thick trunk, up to 25 mm vs the 5 mm weld tol) are
  the ones stitch **refuses to touch** → the upper trunk can be topologically/visually broken while a thin
  bridge elsewhere still holds `components` at 1 (or 3).
- **Same blind-spot class as the ring-transition cracks:** a global component count is a coarse invariant
  that a thin accidental bridge satisfies while a load-bearing axis is broken.

**Proposed contract addition (design note, for whatever generator ships):**
> **Leader-continuity check.** Trace the central axis by `stem_id == 0` (or the pipe-model-thickest child
> chain) from root to apex and assert **geometric continuity**: no inter-segment gap exceeds the weld
> tolerance anywhere along it, and no segment is missing. Run it on the **rendered** attribute set
> (with `radius` + `stem_id`), not the attribute-stripped diagnostic. Extend to every primary scaffold
> strand, not only the trunk. Report per-strand max-gap, not just a global component count.

This is independent of the growth-vs-interpolation decision — it must exist for any skeleton→skin path.

---

## 7. Summary for report-back

- **(0) Prior art read FIRST (§0.5):** Runions et al. 2007 + Palubicki et al. 2009 (Algorithmic Botany),
  read in full. They confirm the diagnosis (our shell cloud = Runions Fig. 7's sparse-surface degenerate
  case) and *name* the mechanisms (age axis = Borchert–Honda `λ` / `di`+envelope; woodland axis = shadow
  propagation + shedding; density = `D`/`N`/decimation-step-d). Grounding these materially sharpened the
  proposal — the lesson recorded as [[feedback_check_prior_art_first]] (prior art is job 1, all projects).
- **(a) Three-buckets-are-one-growth-process reframe: HOLDS along the age axis** — every bucket parameter
  moves monotonically exactly as decaying apical dominance predicts (widest point descends, aspect
  broadens, crown base drops, caliper/stature grow), confirmed by our own table, the excurrent→decurrent
  ontogeny literature, *and* Palubicki Fig. 11 (removing apical control over development animates young
  excurrent → old decurrent — the reframe, proven). **Caveat:** age and light environment are confounded; the
  current s/m/l are the *open-grown* series only. A complete generator wants **age × light-environment**;
  the drawn-up woodland form (Ramble/North Woods) is a distinct, narrower, lower-node-budget envelope not
  yet represented.
- **(b) Skinner reuse verdict: CONFIRMED, biggest reuse intact.** `leafback_skinner.py` consumes a
  generator-agnostic `(pos, parent, radius, strand)` node graph and *derives* all five contract attributes
  itself; a growth grammar emitting that graph drops in with **zero skinner/contract changes**. Only a weld-
  margin re-confirmation is advised (parameter check, not contract change).
- **Root cause sharpened:** the failure is **shell-only attractors (hollow lantern) + unforked
  core-crossing leaders (constant-radius garden-hose)**, not "arc-interpolation" in the abstract — and the
  current line-C skeleton already contains most of the growth machinery, which is why the fix is *volumetric
  fill + continuous in-limb ramification*, not "add a grower."
- **Perf stays a designed constraint:** node budget becomes a first-class per-tier growth target
  (supersedes AC-7 shell-coarsening); radius-scaled RING (Lever 2) is reused unchanged.
- **Contract gap:** add a **leader-continuity check** (trace `stem_id==0` root→apex on the rendered
  attribute set); the current `components==1` gate is blind to a severed leader — the visible upper-trunk
  break is a live instance.

*No code written, no build run, no protected file edited, nothing committed. Deliverable is this document.*
