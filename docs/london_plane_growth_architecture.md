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
method.** The crown envelope per tier (s tier / m tier / l tier), fit from the
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

| tier | age class | H (m) | DBH | `cb_frac` | `aspect` (W/H) | profile — widest at height *t* |
|------|------|------:|----:|----------:|---------------:|-------------------------------|
| s | young | 10.0 | 7″ | 0.35 | 0.80 | t ≈ 0.55 (**above** mid) |
| m | middle | 14.4 | 15″ | 0.30 | 1.00 | t ≈ 0.50 (mid) |
| l | mature | 22.0 | 28″ | 0.20 | 1.20 | t ≈ 0.33 (**below** mid) |

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

**Per-tier LOD0 vertex budgets** (blocking, from `docs/leafback_lod0_density_escalation.md`): s tier
≤ 3 k · m tier ≤ 6 k · l tier ≤ 10 k v/tree. Current line-C skin **fails ~5× on m and ~10×
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
- **Envelope targets** (s / m / l tiers) and the **iNaturalist silhouette data**:
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
`components == 1` check is **blind to a severed leader**, and the current m tier's visible upper-trunk
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

---

# 8. RECOVERY REFRAME — leaves-as-attractors (the amputated Step 2)

> ## ⛔ SUPERSEDED 2026-07-09 — READ THIS BEFORE §8
> **Leaf-back is DEPRECATED as a generation strategy** (Chris's decision; full record:
> [`docs/grower_reiterate_design.md`](grower_reiterate_design.md) §13.3). §8 below is **retained as history, not
> as a plan.** Do not implement it.
>
> Leaf-back existed to fix one thing: *coherent trees that did not read, at distance, as what they were.* The
> **developmental grower** fixes that same thing better — **the tree looks right because it GROWS right;
> appearance is a consequence of a correct process** (standing Rule 3) — and it **dissolves the problems
> leaf-back created**: skeleton-meets-cards, leaf clustering, and the World-A/World-B chicken-and-egg. A grown
> tree puts leaves at twig terminals **by construction**.
>
> **Therefore there is no separate leaf field to place, shape, or time.** §8.3's authored clumping/margin terms
> (honestly labelled there as "literature-shaped, not species-measured") are **no longer needed at all** —
> irregularity comes from growth reaching an uneven light field.
>
> **What survives:** the three per-tier **crown envelopes** (`_T_*/_P_*`) as growth boundaries + validation
> checkpoints; the measured DBH/height/tier distributions as **validation targets**; and
> `scripts/leafback_skinner.py` + the 5-attribute contract, **unchanged** — *a skeleton is a skeleton*. The
> "leafback" prefix on that file is now a historical artifact, not a description.
>
> **What dies:** the persisted leaf field, leaves-as-attractors, the clumping/margin terms, the World-A framing,
> and `dk` as the "economy knob."
>
> Leaf-back is **not wrong** — it was the right answer to a real defect, it produced the crown envelopes we still
> use, it forced the *depth-is-an-output* lesson, and its failures taught us the connection had to be a *process*.
> It is **superseded**, which is the good outcome for a scaffold.

> **Planner addendum, 2026-07-08 (this session).** Everything below is a PROPOSAL for Chris's sign-off.
> Nothing built, no protected file edited, nothing committed. This section *sharpens* §0–§7, it does not
> retract it: G1 (volumetric fill) and G2a (`di_near=2.0`) still stand as the validated base; the recovery
> is a change to what the attractor field *is and does*, layered on that base.

## 8.0 The reframe — a RECOVERY, not a new direction

Chris's ORIGINAL leaf-back was **three** steps, and step 2 was amputated during the rebuilds. That single
amputation is the root cause of **both** the hollow lantern (§0.5, Runions Fig. 7) **and** the too-neat
lollipop silhouette — they are the same wound.

1. **CARVE THE SHELL** — the crown's final outer shape. *We have this:* the three iNat crown-type envelopes.
2. **FILL THE SHELL WITH LEAVES** — distribute leaf-card positions *through the volume*, naturalistically /
   unevenly. **These positions are BOTH the render leaves AND the growth attractors — one unified set.**
   *This is the dropped step.*
3. **BRANCH THE SKELETON OUT TO REACH THE LEAVES** — grow branches from trunk to the step-2 leaves; leaves
   render at the branch terminals they were grown to.

What got built instead is **steps 1 + 3 with step 2 missing**: a throwaway attractor cloud, then leaves
re-derived from the grown bark. *"We were bending skeleton to fit the shell; we should be branching skeleton
to reach the leaves."* The space-colonization machinery is **not a new paradigm** — it is the *implementation
of step 3* Chris always intended, and it only behaves once step 2 feeds it a **leaf field** instead of a bare
uniform cloud that gets discarded.

**Why this is "World A" by construction:** the leaf positions are determined FIRST, independent of the
skeleton, by filling the shell; the skeleton grows TO them. No chicken-and-egg — the leaves exist before
growth and *are* the growth targets. The current pipeline drifted into deriving leaves *from* the grown
skeleton (§8.1); recovering step 2 puts leaf determination back where Chris designed it, before the branches.

## 8.1 (a) I1 — the amputation is CONFIRMED in code; the G1 cloud IS convertible

Traced the full leaf-back path (`leafback_graph.py` → `leafback_skeleton.py` → `build_leafback_skeletons.py`
→ `generate_trees_mtree.py`). Findings, with evidence:

- **Leaf-card render positions are derived FROM the grown skeleton, post-growth** — case (c), not an
  independent pre-growth field and not shell-surface placement. `_card_placements_per_branch`
  (`generate_trees_mtree.py:2832–2955`) selects **thin-twig bark-mesh vertices** of the *skinned grown
  skeleton* (`eligible = finite & (radii < max_radius)`, `:2893`; tip-first per-`stem_id` pick of
  `coords[vi]`, `:2948–2955`) and orients cards by the `direction` attr. Call site `:4558–4565`.
- **The G1 attractor cloud is DISCARDED.** `leafback_graph.py` builds the volume-uniform sprig cloud
  (`rr = R*np.sqrt(U)`, `:55`; Poisson-thinned, `:57–69`); `leafback_skeleton.py:341–342` takes only the
  sprig *positions* as space-colonization attractors, which are **killed** as branches reach them
  (`alive_local[killed]=False`, `:193`). `save_skeleton` (`build_leafback_skeletons.py:29–41`) persists only
  the grown nodes (`pos/parent/radius/strand/trunk_ids/origin_ids/fork/root/…`) — **no sprig/attractor array
  is written**. The pre-growth field never reaches the npz and is never used for rendering.
- **Step 2 is MISSING.** There is no single coordinate set that is simultaneously the render leaves and the
  growth attractors; the two are decoupled, and the pre-growth field is the *discarded* one.
- **Convertible: YES — it is already a proto leaf field.** The sprigs are points sampled inside the crown
  envelope (exactly the coordinate type cards want). To recover step 2: (i) **persist** the sprig positions
  in the npz; (ii) **render cards at those positions** (or a naturalistically redistributed version) instead
  of re-deriving from bark verts; (iii) **redistribute** from uniform-in-volume to a naturalistic field
  (§8.3). Only (iii) is substantive; (i)/(ii) are plumbing.

## 8.2 (b) I2 — Step 3 is the canonical algorithm as-configured; cluster-sharing is FREE

Re-read Runions et al. 2007 and Palubicki et al. 2009 from the PDFs (not summaries). Verdict:

- **Attractors ARE the marker cloud.** Palubicki §4.1: "a set S of **marker points M** … uniform
  distribution … at the beginning of the simulation"; Runions §2: points "signal the availability of empty
  space … removed when reached by a branch." Not abstract voxels — the concrete seeded cloud.
- **Kill distance `dk` does both jobs.** (a) termination: "An attraction point s is removed when there is at
  least one tree node v closer to s than a threshold **kill distance dk**"; (b) clump capture: "with larger
  kill distance values, the **set of attraction points affecting individual branch tips increases**."
- **Cluster-sharing emerges for free — it is the defining behaviour, no extra machinery.** It falls out of
  (influence-set averaging, Runions §2: v′ grows toward the *normalized average* of vectors to all
  `s ∈ S(v)`) + (closest-node association, Palubicki §4.1: a marker seen by several buds "is associated with
  the **closest** of these buds") + (`dk`). Adjacent leaves ahead of one node advance the shared parent, then
  split across child tips → **adjacent leaves descend from one forking upstream branch.** *This is exactly
  Chris's "adjacent leaves draw from a single branch," and it is not bolted on — it is the core dynamic.*
- **Non-uniform / clumpy distribution is explicitly supported.** Runions §2: "the **distribution of the
  attraction points is a user-controlled attribute of the method**"; §3 grades density near the envelope to
  make outer-crown branch concentration. **But the markers must fill the VOLUME** — shell-only is the named
  degenerate **Figure 7** (our old cage).
- **Economy levers are standard configuration, not new code:** `N` (attractor count) + `dk` set sparseness;
  `di` sets trunk-vs-ramified + smoothness; `D` is the node-count/resolution unit. Age/woodland axes have
  named knobs (Palubicki BH-`λ`, priority model, shedding).

**Verdict: step 3 is the canonical Runions space-colonization algorithm as-configured — configuration, not
new code — and adjacent-leaf cluster-sharing comes free from the capture radius + closest-node association.**

## 8.3 (c) I3 — DATA for a naturalistic plane leaf distribution (the crux)

**Bottom line: the repo has the outer OUTLINE (real, iNat-measured) but ZERO measured *internal* density for
Platanus. No source — repo or published — gives a Platanus-specific 3D leaf-area-density (LAD) profile.**
The current fill is deliberately **volume-uniform** (`leafback_graph.py:55`, β=0.5). But there *is* enough to
**shape** the fill non-arbitrarily, so a naturalistic field is **data-informed, not free-handed**:

- **iNat imagery cannot yield internal density.** Only the outer silhouette was ever extracted
  (`docs/first_mould_leafback_prototype.md` Part C → crown aspect + clear-bole per bucket). Of 311 obs, ~4
  clean summer whole-crowns + 2–3 bare winter silhouettes survive triage — single-angle, different trees, no
  aerials, no multi-angle specimen. Supports the 2D outline (already used) and at most a weak 2D projected
  opacity read; **not a recoverable 3D LAD field.** Extracting "more" is low-yield.
- **Repo canopy data gives the SHAPE, not numbers** (`reference_tree_canopy_data.md` §11, sourced USDA
  Silvics / i-Tree / ISA): LAI 4.0–6.0; light transmission **8–15%** (heavy shade → dense near-opaque outer
  canopy); ~59 k leaves; **"leaves tend to be concentrated in the outer crown shell," "layered parasol
  effect."** → **shell-weighting is data-backed for planes.**
- **Published broadleaf LAD gives the vertical shape:** vertical LAD is **unimodal for small trees, bimodal
  for large**; **open-grown/dominant trees concentrate leaf area in the sunlit UPPER crown**, thinning to the
  base (Ulmus laevis, Trees 2012; TLS LAD, Remote Sensing 2018). The **beta function** is the standard fit
  for vertical crown profiles. Radial: the canonical primitive is a **voxel turbid-medium** crown carrying
  LAD (TLS/Beer–Lambert) — the same shell-weighting the repo's "8–15% transmission / outer-shell" describes.
- **Procedural prior art confirms the density field IS the authored lever** (Runions/Palubicki): the crown is
  seeded uniform by default but "any kind of distribution" is allowed, and **denser marker regions develop
  finer/denser branching** — precisely the knob the repo already exposes (`SPRIG_SPACE` + the `rr` radial
  sampler at `leafback_graph.py:55`).

**Minimal data-shaped density function** (the recovered Step-2 fill; replaces uniform β=0.5):

1. **Radial: shell-weighted, non-zero to the core.** Replace `rr = R·√U` with an outer-biased radial CDF,
   `rr = R · U^p`, **p ≈ 0.35–0.5** (p<0.5 pushes points outward; p=0.5 = today's uniform), with a non-zero
   interior floor per G1 (so it never regresses to the Fig. 7 shell). *Shape = data-grounded (§11 outer-shell
   + transmission).*
2. **Vertical: beta-function weight on normalized crown height, mode ≈ 0.55–0.70** (unimodal; allow bimodal
   for the veteran `l` spread). *Shape = data-grounded (open-grown upper-crown LAD).*
3. **Irregularity — the silhouette-breaking term — is AUTHORED, and I flag it as such.** Neither a smooth
   shell-weight nor a smooth beta is enough on its own: both are radially symmetric and will still yield a
   *smooth* lollipop. The outline breaks up only if the field is **clumped/uneven azimuthally and vertically**
   (denser lobes, gaps at the margin). The repo/literature justify shell + vertical *shape* but give **no
   Platanus-specific clumping data**, so the clumping term (e.g. low-frequency blue/Perlin-noise density
   modulation + a jittered margin) is **literature-shaped, NOT species-measured** — pick parameters to match
   the general broadleaf look and tune against reference crown renders; label them honestly. Margin/lobe
   raggedness *of the branch outline itself* additionally emerges from the growth grammar reaching an uneven
   field (§8.2), not only from the fill.

**Honesty ledger for the fill:** *shape* (shell-weighted radial + upper-mid vertical peak + beta form) =
**data-grounded**; exact parameter values (`p`, beta mode/shape, clumping amplitude/frequency) =
**literature-shaped, not Platanus-measured** — tune-and-label, do not call them "data."

## 8.4 PROPOSAL — the recovered three-step pipeline (marked)

> PROPOSAL for sign-off. Drops into the existing stages; emits the same npz the skinner already consumes.

- **STEP 1 — SHELL (reuse, confirmed).** The three iNat crown envelopes (`_T_*/_P_*` profile tables,
  `leafback_skeleton.py:318`) remain the soft bound on where leaves may go. Same numbers, unchanged role.
- **STEP 2 — FILL WITH A LEAF FIELD (the recovery).** Generate ONE coordinate set that is **both the render
  leaves and the growth attractors**, distributed by the §8.3 data-shaped field (shell-weighted radial +
  beta vertical + authored clumping). **Persist it in the npz.** This is where irregularity is injected —
  make that explicit in any spec: *the silhouette is won here, not in the grower.*
- **STEP 3 — GROW TO THE FIELD (canonical, §8.2).** Space colonization over the step-2 field; `dk` makes tips
  terminate at leaves and adjacent leaves share a forking branch. Skinner + 5-attribute contract consume the
  grown graph **unchanged** (§5, re-confirmed by I1). **Cards render at the step-2 positions the tips grew
  to** — replacing the post-hoc bark-vertex re-derivation (`_card_placements_per_branch`), so leaves sit
  exactly where the tree was grown to carry them.
- **ECONOMY control (Chris: "not excessive").** Lever = **`dk` (capture/kill radius)** primarily, with `N`
  (attractor/leaf count) and `di` (perception) secondary: larger `dk` → each tip captures more of a
  leaf-cluster → **fewer, more-shared limbs per cluster** (Runions §3). Tune `dk` up until the wire-fan
  collapses into legible shared limbs but before coverage drops — one lever, measured on the leafless
  skeleton (§8.8).

## 8.5 REUSE / REPLACE ledger (update to §5)

- **G1 volumetric cloud → REPURPOSED as the persisted leaf field** (not discarded). This is the core of the
  recovery. β=0.5 uniform → §8.3 data-shaped field.
- **Crown envelope → REUSED as soft bound** (Step 1), unchanged.
- **`leafback_skinner.py` + 5-attribute contract → UNCHANGED** (I1 re-confirms it derives all attrs from the
  grown graph; a leaves-as-attractors grower still emits `(pos, parent, radius, strand)`).
- **`_card_placements_per_branch` (post-hoc bark-vertex card derivation) → REPLACED** by rendering at the
  persisted step-2 leaf positions the tips grew to. *(This is the one downstream change vs. §3, which had
  left foliage untouched.)*
- **`di_near=2.0` / G2a → still relevant, partially subsumed.** `di` remains the perception radius (now in
  the literature 1.4–2.1 m range); its old *leader-hack* rationale (`di_near=6.0` to cross an empty core) is
  gone once the volume is a real leaf field. **Capture-based termination (`dk`) becomes the primary economy
  knob; `di` reverts to plain perception.** G1+G2a remain the validated base this builds on.
- **Post-hoc shell coarsening (AC-7 `SPRIG_SPACE` up-tune) → still superseded** by grow-to-node-budget (§4),
  now expressed as tuning `N`/`dk` of the leaf field.

## 8.6 PERF honesty — cluster-sharing plausibly LOWERS node count

Leaf/card count is ~fixed by the shell fill (the target foliage). The open question is grower **node** count.
Expectation, stated for later measurement (not claimed): **growing to *clusters* should raise coverage
efficiency and LOWER node count vs. the uniform volumetric fill**, because (a) shell-weighting puts fewer
attractors in the deep interior than uniform-in-volume, and (b) cluster-sharing merges several leaves onto
one upstream limb (fewer shared limbs). If so, the recovery **fixes the silhouette AND eases the vertex
budget** in the same move. This does **not** retire §4: node budget stays a first-class per-tier growth
target (tune `N`/`dk`/`D`), and the radius-scaled RING (Lever 2) is still reused unchanged. Measure
before/after on the leafless m skeleton (nodes, LOD0 verts, attractor reach) to confirm the direction.

## 8.7 (verify-gap) The upper-trunk break survived the 352 mm trace — why, and the fix

**Instance:** the break visible looking down from above PASSED the leader-continuity trace (352.3 mm max
span, "1 D-seg, PASS") — the **second** trunk break to survive the gate. Read the trace code to find why.

**Root cause — the trace is GRAPH-level; the break is MESH-level.** `tmp/g2a/measure_g2a.py:72–79` computes,
for every `strand==0` node, `‖pos[i] − pos[parent[i]]‖`, and reports the max. That is a **node-graph
parent-link distance**, which is ~`D=350 mm` *by construction* — the grower steps one segment of length `D`
at a time, so consecutive strand-0 nodes are always ~one segment apart and the check is **near-vacuous for
the leader** (it can essentially only "fail" if a node were dropped entirely). It **never touches the
rendered mesh**, so it is structurally blind to the actual defect:

1. **Ring-framing gaps that `stitch` refuses to weld (§6).** `stitch_bark_islands` has a `stem_id`
   *same-branch skip*: it declines to weld junctions *within one strand* (to preserve twig ring
   cross-sections). The trunk/leader is a single strand (`stem_id==0`). So the ring-to-ring gaps along the
   leader (gap ∝ radius, worst at the thick trunk — up to ~25 mm vs the ~32 mm weld tol) are the very ones
   stitch **won't touch**. The node graph is continuous there; the *tube mesh* is cracked.
2. **The trace only walks `strand==0`.** A break at a **scaffold origin** (cross-strand trunk→limb junction)
   or where a **sympodial relay** hands the axis to a different strand id near the apex is *off* the strand-0
   path entirely — invisible to this trace even in principle.

**Proposed check that WOULD catch it (design note; applies to any grower):** run continuity on the
**rendered mesh with attributes**, not the node graph.
- **Mesh-loop continuity along each strand:** order each strand's ring cross-sections by arc-length and
  assert consecutive rings are topologically joined (share the quad band) OR their nearest-vertex distance
  ≤ weld tol. Report per-strand, per-junction **max gap** — do NOT inherit stitch's same-strand skip (that
  skip is the very thing to audit).
- **Scaffold-origin attachment:** assert each scaffold-origin ring is welded to the trunk surface within tol
  (the cross-strand junctions the strand-0 walk never visits).
- **Relay-aware trunk trace:** trace the load-bearing axis by **pipe-model-thickest child** root→apex (which
  follows a sympodial relay across strand-id changes), not by `stem_id==0` alone.
- Run on the **rendered** attribute set (with `radius`+`stem_id`) — the diagnosis (`components 62` real vs
  `3` attribute-stripped) shows a graph/stripped check under-reports disconnection ~20×.

This is independent of the growth decision and must exist for any skeleton→skin path. It also implicates a
**fix, not just a gate**: the same-branch skip on `stem_id==0` should weld thick-trunk ring gaps that exceed
tol (the skip's rationale — preserving *twig* rings — does not apply at trunk caliber).

## 8.8 Report-back summary (this addendum)

- **(a) I1 — amputation CONFIRMED:** leaf cards are derived post-growth from bark-mesh verts
  (`generate_trees_mtree.py:2832–2955`); the G1 attractor cloud is killed during growth and **never saved**
  (`build_leafback_skeletons.py:29–41`). Step 2 (an independent pre-growth field that IS the attractors) is
  missing. The G1 cloud **is convertible** — already a proto leaf field; recovery = persist + render-there +
  redistribute (only the last is substantive).
- **(b) I2 — Step 3 is canonical, off-the-shelf:** attractors ARE the marker cloud; `dk` terminates tips at
  leaves and captures adjacent leaves at a clump; **cluster-sharing is FREE** (influence-set averaging +
  closest-node association + `dk`); non-uniform/clumpy fill is explicitly supported *provided it fills the
  volume* (shell-only = Fig. 7). Configuration, not new code.
- **(c) I3 — DATA (the crux):** no Platanus-specific 3D LAD exists; iNat imagery can't supply it. But the
  fill *shape* is data-grounded — **shell-weighted radial** (repo §11: outer-shell concentration, 8–15%
  transmission) + **upper-mid vertical peak, beta form** (broadleaf LAD literature). Exact parameters and the
  silhouette-breaking **clumping/margin term are authored (literature-shaped, not species-measured)** — must
  be labelled so and tuned against reference renders.
- **Verify-gap:** the 352 mm trace passed because it is a graph-level `strand==0` parent-link check
  (~`D` by construction), blind to the mesh-level ring gap that `stitch` skips within a strand and to
  off-strand-0 breaks. Fix = mesh-loop + scaffold-origin + relay-aware continuity on the rendered attribute
  set (§8.7).

*No code written, no build run, no protected file edited, nothing committed. Deliverable is this addendum.*

---

# 9. The LOLLIPOP diagnosis — is the crown aspect-bucketed, or one shape + an aspect scalar?

> **Planner addendum, 2026-07-08 (this session).** Investigation of the m-tier "lollipop" (compact, roughly
> spherical crown, aspect ≈ 1) vs. the m tier's then-assumed form (broad, wider than tall — an assumption §10 overturns). PROPOSAL only; nothing
> built, edited, or committed. This does **not** re-litigate the July-6 distribution decision — it asks
> whether that distribution was split *by shape/aspect*, which it turns out it never was.

## 9.1 (a) ONE mould or THREE? — THREE profiles + THREE aspect scalars in code, but the shape is essentially ONE

At the code level there **are** three profile tables and three aspect scalars, per tier
(`leafback_skeleton.py:318–330`):

| tier | age class | aspect W/H | profile | widest at *t* |
|------|------|-----------:|---------|--------------:|
| s | young | **0.80** | `_P_S` | 0.55 |
| m | middle | **1.00** | `_P_M` | 0.50 |
| l | mature | **1.20** | `_P_L` | 0.33 |

So the literal "one averaged blob applied to all tiers" hypothesis is **false** — the tiers carry distinct
aspects. **But the profile *shapes* are essentially one mould with two hand-drawn variations, and the tiers
differ almost entirely by the aspect scalar:**

- `_P_M` is the real data-derived shape — the v2 mould, its **radial profile sampled from a single
  specimen, `obs75867287`** (`first_mould_leafback_prototype.md` Part D:317). Its widest point is exact
  **mid-crown (t=0.50)**, a symmetric bump (0.14→1.00→0.18).
- `_P_S` and `_P_L` are **hand-authored variations** of `_P_M` — the validation script says so in
  its own comments (`tmp/leafback_bucket_validation.py`: the s profile is widest slightly ABOVE mid
  (~0.55), the l profile widest LOW (~0.33)). The s and m profiles (widest 0.55 and 0.50) are **nearly
  identical shapes**; only `_P_L` is genuinely different.

**Verdict: not one mould, but not three data-bucketed moulds either — one data-sampled shape (from a single
specimen) + two hand variations, differentiated mainly by an aspect scalar (0.80 / 1.00 / 1.20).** The
"shape-UNbucketed" half of the hypothesis is essentially correct.

## 9.2 (b) Provenance — the m tier shape came from a YOUNG OVOID specimen, and was NARROWED to spherical

The crown target was **not** derived from all 311 silhouettes pooled, and **not** from an aspect-matched
per-bucket subset. It came from **three hand-measured anchor specimens** (`first_mould_leafback_prototype.md`
Part C:295–301), of which the mould geometry used exactly **one**:

- Part C measured only **3 clean crowns**: `obs75867287` (young-mature ovoid, **W/H ≈ 0.85**), `obs122865830`
  (mature, "wide low-spreading," *crown top out of frame — no number*), `obs11670158` (veteran, **W/H > 1.2**).
- Part B's v1 representative from the **mode (mature-dome) bucket measured W/H_crown ≈ 1.16** — *wider than
  tall* (`Part B:176`).
- Part D rebuilt the mould with its **profile sampled from `obs75867287`** (the young **ovoid**, 0.85) and
  its **aspect explicitly reduced 1.16 → 1.00** ("was 1.16", `Part D:317–325`).

So the modal "m tier" mould has its **shape taken from a young ovoid specimen** and its **aspect
narrowed from a measured 1.16 down to a spherical 1.00.** The Part D note calls this "broadened toward the
measured distribution," but 1.16 → 1.00 is a *narrowing* — that line is internally contradictory, and the
net effect moved the modal crown *toward a sphere, away from the broad dome the v1 mode specimen measured.*

## 9.3 (c) The measured aspect of the current m-tier target — the smoking gun

**m-tier crown aspect = 1.00 (W/H), spherical.** Confirmed from `BUCKETS["m"]` (`leafback_skeleton.py:328`)
and the envelope math `RX = aspect·CH/2` (`:345`): for m (H=14.4, cb_frac=0.30 → CB=4.32, CH=10.08),
crown width = aspect·CH = **10.08 m**, crown height = **10.08 m** → a bounding box as wide as tall, widest at
exact mid (`_P_M`) → **a sphere. That is the lollipop, and it is aspect = 1.00 by construction.**

Two things are simultaneously true and both point at aspect 1.00 as the defect:
- It is *literally spherical* (W/H = 1), regardless of any averaging story.
- It also *equals the arithmetic mean* of the three bucket aspects (mean(0.80, 1.00, 1.20) = 1.00) — so the
  cross-bucket-mean intuition lands on the same number. But the mechanism is not a runtime average; m was
  independently set to 1.00 by narrowing the measured 1.16 (§9.2).

Either framing, the fix is the same: **the m tier must be wider than tall.** *(⚠ direction SUPERSEDED by
§10.0 — the hybrid is taller-than-wide; this §9 conclusion is retained only as the record of the reasoning
that §10 then corrects.)*

## 9.4 (d) Do the 311 carry per-observation aspect? — NO. Re-bucketing 311 by aspect is INFEASIBLE

The 311 do **not** carry per-observation aspect, and cannot be cheaply re-bucketed by shape:
- `tmp/inat_lp/candidates.json` = **68** observations, keys `[id, qg, n, urls, desc]` — metadata + photo
  URLs only, **no aspect, no crown geometry.**
- `tmp/inat_lp/crown/meta.json` = ~20 curated crowns, keys `[file, season, place]` — **no aspect.**
- **Only 3 specimens were ever hand-measured for aspect** (Part C table). Of the full 311, triage leaves
  **≈4 usable summer whole-crowns + ≈2–3 bare winter silhouettes** — mostly ID close-ups (bark/leaf/seed-ball).

So the brief's premise ("the pull produced per-observation aspect; re-bucket the 311 by aspect") does **not
hold** — the shape data for 311 does not exist, and extracting it from the imagery is exactly the low-yield
single-angle problem Part C already hit. **A re-bucket-the-311 proposal is not actionable with data in hand.**

## 9.5 PROPOSAL (marked) — fix the aspect first; it is a one-lever, data-in-hand change

> PROPOSAL for Chris's sign-off. No new pull, no clumping work, no new photos.

**The re-bucket-311-by-aspect path is dead (§9.4).** But the diagnosis yields a cleaner, cheaper fix that
uses only data already in hand:

1. **Raise the m tier aspect from 1.00 to the measured mode value (≥ 1.16, wider than tall).** This
   *restores* a real measurement — the v1 mode-bucket specimen's W/H_crown ≈ 1.16 (`Part B:176`) — that was
   narrowed to 1.00 in the v2 rebuild (§9.2). It is a **single scalar** in `BUCKETS["m"]`
   (`leafback_skeleton.py:328`), measured-before-changed. (Sanity-bracket: s = 0.80 ovoid, l = 1.20 spread;
   a mature dome at ~1.15–1.25 sits correctly between "balanced" and "veteran spread" and stops reading as a
   ball.)
2. **Differentiate the m profile from the s profile.** `_P_M` (widest at mid, from a young s-stage specimen)
   is nearly identical to `_P_S`; the m tier should be **widest slightly below mid with a flatter,
   broader top**. This is a profile-table edit (`_P_M`), shaped to the qualitative rounded-crown description
   (reference_tree_canopy_data §11: "broad, spreading, rounded"), flagged **authored-not-measured** (no
   mature-dome silhouette was ever measured — Part C's mature anchor had its crown top out of frame).
3. **Order of operations — aspect is PRIMARY; margin-irregularity and interior-clumping are SECONDARY.** A
   proportion defect cannot be fixed by un-smoothing a margin: un-smoothing a sphere gives a *lumpy* sphere,
   still not a m tier. So the §8 recovery work (naturalistic leaf-field clumping, ragged margin) is a
   refinement that only pays off **after** the per-tier aspect is right. Sequence: (i) fix m aspect → (ii)
   verify it reads as a broad dome on the leafless skeleton → (iii) then apply the §8 leaf-field/clumping.
4. **Structural reuse — unaffected.** Only the aspect scalar and the `_P_M` numbers change.
   `build_bucket_skeleton` → `build_graph` → `leafback_skinner` all consume the same envelope contract; the
   envelope→skinner path is structurally identical (§5). No plumbing change.

**Honesty ledger:** aspect 1.16 is a *measured* value being restored (data-in-hand); the exact target
(≥1.16) and the dome-profile reshape are *shape-informed, tune-and-verify* — no mature-dome silhouette was
ever measured, so do not label the final numbers "data," label them "restored measurement + shaped-to-
description, verified on render."

## 9.6 Report-back summary (this addendum)

- **(a) ONE or THREE:** three aspect scalars + three profile tables in code, but the *shape* is one
  data-sampled mould (`_P_M`, from `obs75867287`) + two hand-authored variations; tiers differ mainly by
  the aspect scalar. Shape was effectively **not** bucketed from data.
- **(b) Pooling:** neither all-311-pooled nor per-bucket-fit — the mould geometry came from **one** young
  **ovoid** specimen, with the m tier aspect **narrowed 1.16 → 1.00** in the v2 rebuild.
- **(c) m-tier aspect = 1.00 (W/H), spherical — the smoking gun confirmed.** The lollipop is a proportion
  defect: the m tier is built as a ball.
- **(d) The 311 do NOT carry per-observation aspect** (candidates.json 68 obs = metadata only; only 3 hand-
  measured; ~6–7 usable crowns). Re-bucketing the 311 by aspect is infeasible with data in hand.
- **Proposal:** skip the re-bucket; **raise the m tier aspect to the measured ~1.16 (one scalar) + reshape
  `_P_M` to a genuine below-mid-widest dome**, verify on the leafless skeleton, and treat margin/clumping
  (§8) as a strictly secondary refinement. Envelope→skinner path unaffected.

*No code written, no build run, no protected file edited, no new data pulled, nothing committed. Deliverable
is this addendum.*

---

# 10. FORM MODEL — a grounded understanding of London plane crown form, with its gaps left open

> **Planner addendum, 2026-07-08 (this session).** COMPREHENSION deliverable, not a build. The task: describe
> the crown well enough to *sculpt* it, grounded in botanical authority — and **where the understanding
> genuinely isn't there, LEAVE THE GAP AND NAME IT** rather than fit a number to fake completeness (fitting a
> number to a thin anchor is exactly what produced the lollipop, §9). Nothing built, edited, or committed.
> Sources: our own docs (§10.1), the primary tree-architecture + dendrology literature (§10.2–10.4), and
> direct visual study of the on-disk specimen imagery (my own pixel reads, §10.3). Authority tags on claims:
> **[PS]** plane-specific & sourced · **[BG]** broadleaf-general & sourced · **[?]** assumption/uncertain.

## 10.0 ★ The premise correction — the deleted m-tier shape-name assumed "wider than tall", which is WRONG for the hybrid; it retracts §9.5

The single most important finding, and it **corrects my own §9 proposal.** The documented central tendency
of the *hybrid* London plane crown is **taller-than-wide to roughly balanced (W/H ≈ 0.65–0.85), a rounded /
broad-pyramidal head** — **not** a wide, flat, squat dome. "The crown tends to grow **taller than wide**,
particularly in older clones" **[PS — Trees & Shrubs Online / Bean, *Platanus × hispanica*]**; horticultural
dimension sheets give ~70–100 ft tall × 60–80 ft wide → **W/H ≈ 0.65–0.85 [PS — Morton Arboretum; Missouri
Botanical Garden; NC State Extension]**. The **wider-than-tall, low, flat-spreading** form belongs to the
*isolated parents* — *P. orientalis* ("a remarkably spreading tree, and often a low one") and open-grown
*P. occidentalis* (crown to 30 m diameter) **[PS — Trees & Shrubs Online; USDA Silvics]** — which the hybrid
only approaches at **extreme age / open exposure**.

**Consequences:**
- The lollipop (aspect 1.00 sphere) is wrong, but **not because it should be broader.** If anything the mature
  hybrid is **taller than wide (~0.75–0.85)**, not spherical and not wide-flat.
- **§9.5 is RETRACTED on direction.** My proposal there to "raise the m tier aspect toward ≥1.16 (wider
  than tall)" read the bucket's *name* literally and reasoned from the v1 1.16 measurement **without botanical
  grounding** — it would have propagated the very "wider than tall" assumption this task exists to kill. The
  §9 code-provenance findings (aspect narrowed 1.16→1.00, shape sampled from a young ovoid, 311 carry no
  aspect) all still stand; only the *proposed target direction* is wrong and is replaced by §10 below.
- The current code aspect series **0.80 → 1.00 → 1.20** runs **too wide across the board and crosses 1.0 too
  early** (at the mature tier). The grounded series stays **≤ ~0.85 until the veteran stage.**

## 10.1 (a) What our OWN docs already established (prior-art-first)

- **Measured (but thin — 3 single-angle anchor specimens, `first_mould_leafback_prototype.md:296–301`):** the
  cross-age *trend directions* — clear-bole fraction **falls** 0.33→0.30→0.20 (trees fork *lower* with age),
  aspect **rises** 0.85→>1.2, widest-point **descends** 0.55→0.50→0.33; the veteran W/H > 1.2 (one winter tree
  `obs11670158`); the young ~0.85 (one tree `obs75867287`). Sourced **foliage-density** (not proportion): LAI
  4–6, light transmission 8–15%, ~59 k leaves, "leaves concentrated in the **outer crown shell**, layered
  **parasol** effect" **[PS — reference_tree_canopy_data §11, USDA Silvics/i-Tree/ISA]**.
- **Authored / landmine:** the modal **m tier aspect 1.00** (narrowed from a measured 1.16, its *shape
  sampled from the young ovoid* `obs75867287` — §9.2), the young aspect 0.80, both hand-authored profile
  tables (`_P_S`/`_P_L` are variations of `_P_M`), the 4-primary fork count (emergent), all branch
  angles, and the entire internal leaf-density field.
- **Gaps our docs ALREADY name:** ★ **no mature-dome crown was ever measured** (the one mature anchor
  `obs122865830` had its crown top out of frame); only 3 anchors / ~4 summer + ~2–3 winter usable of 311; no
  multi-angle or aerial of any tree; the "per-angle typicality is automatic" retirement of the multi-angle gap
  (`crown_data_audit.md`, Part D) is **undercut** by the §8–§9 lollipop diagnosis and should be treated as
  optimistic; the woodland/drawn-up light axis is entirely absent (open-grown series only).

## 10.2 The architectural model — the frame the whole life-history hangs on

Édelin's architectural analysis assigns *Platanus* to **Massart's model**: a **monopodial, rhythmically
growing orthotropic (vertical) trunk bearing plagiotropic (near-horizontal / wide-angle) branches produced in
rhythmic tiers** **[PS — Édelin, *Architecture et dynamique de croissance du platane*; model def. Hallé,
Oldeman & Tomlinson 1978 / CIRAD GreenLab]**. The mature and veteran crowns are **not primary shapes** — they
are **emergent**, produced by **crown metamorphosis + reiteration**: the leader's dominance breaks up, several
scaffold limbs each **reiterate the whole architectural unit** (behaving like new "trees" on the old frame),
and juvenile plagiotropic branches partly **re-erect** (secondary orthotropy) into the rounded head. A subtle
but load-bearing point for us: the architecture is **monopodial in organization but sympodial in module
function** (each visible axis is a relay of short annual modules) — this is *why* the plane tolerates pollard/
pruning, and it is the botanical justification for the sympodial-relay + reiteration language in §1.3/§2.

**Sculpting consequence:** the mature crown must be built as an **aggregation of several heavy, reiterated
limb-systems**, not as one smooth envelope. This is exactly the §8 "grow to a leaf field, don't impose a
shell" recovery, now independently grounded in the species' architectural model. It is also *why* the smooth
lollipop reads so wrong — a single smooth shell erases the "several trees fused" massing that is the plane's
mature identity.

## 10.3 (b) The form model — three stages as ONE developing form (gaps marked inline)

### STAGE 1 — YOUNG "Upright Pyramidal" (≈7–12 m)
- **Proportion:** clearly **taller than wide** — upright, **broad-pyramidal to conical** (young trees read
  "straggly, leaves too large for the tree"). W/H **< 1** (direction grounded; a rough ~0.7–0.8 is plausible
  but **not pinned**). **WHY:** strong apical dominance/control keeps a dominant leader and a vertically-biased
  crown **[PS — Morton; T&SO]** **[BG — excurrent form under apical dominance]**.
- **Branch architecture:** Massart signature — a **single dominant orthotropic leader**; **plagiotropic
  branches in rhythmic tiers** spaced along the bole, leaving the trunk at wide angles; **few, thin, evenly
  angled scaffolds**; branching is **rhythmic/periodic**, not continuous **[PS — Édelin; UF/IFAS ENH643
  "develops a dominant central leader"]**.
- **Reads as young because:** a clean single leader + a tapering, tiered, vertically-biased crown + few thin
  scaffolds — not yet heavy crooked limbs.
- **Plane-specific vs generic:** the **rhythmic TIERING of plagiotropic branches along a persistent leader** is
  the diagnostic juvenile cue — more organized/layered than a generic young-broadleaf blob. A smooth lollipop
  erases it.
- **GAPS:** exact young aspect unpinned (0.80 is authored); **no young-ovoid whole-crown exists on disk** (§10.3
  imagery); tier spacing / scaffold-count per growth cycle for this hybrid unknown → needs the full Édelin
  monograph (paywalled) or branch-order fieldwork.

### STAGE 2 — MATURE (the workhorse; the tier that carried the now-deleted crown-form label)
- **Proportion:** **rounded to broad-pyramidal / oval**, **taller-than-wide to balanced, W/H ≈ 0.65–0.85**,
  **rounded (not flat) top**. **Not spherical, not wide-flat.** **WHY:** apical dominance weakens with size so
  the crown fills out and rounds, but in the *hybrid* it does **not** collapse into a squat dome the way
  isolated *orientalis* does **[PS — T&SO "taller than wide"; Morton/MoBot/NC State dims]** **[BG — dominance
  decay → decurrent rounding]**.
  - ⚠ **Tension to hold honestly:** the best on-disk CP summer whole-crown (`S_286898477`) reads to my eye
    (and the imagery agent's) as **balanced to *slightly* wider than tall** — softer/wider than the 0.65–0.85
    horticultural prior. Possible causes: a spreading clone, real age, or distance-flattening/over-read width.
    So the *CP-specific* value is genuinely between "~0.8 taller-than-wide" (literature) and "~1.0 balanced"
    (thin local imagery) — **unpinned**, direction only.
- **Branch architecture:** a **few large, heavy, crooked, TWISTING spreading limbs** (coarse branching — "a
  huge rounded head of somewhat contorted branches"); major limbs **ascend then arch**, with **weeping /
  pendulous OUTER tips** in large trees (the dominant 'Media' clone: "twisting major limbs and rather weeping
  outer branches"); crown assembled from **several reiterated Massart units** (metamorphosis) → an irregular,
  "several trees fused" massing; often a relatively **short bole** carrying strong branches **[PS — T&SO;
  MoBot; Édelin]**.
- **Reads as mature because:** loss of a single clean leader; several **co-dominant reiterated limb systems**;
  heavy crooked twisting scaffolds; **weeping tips**; a full rounded/oval head.
- **Plane-specific vs generic (the exact axis the lollipop got wrong):** (a) **weeping outer twigs on ascending
  heavy limbs**; (b) **few large crooked twisting scaffolds**, not many fine even ramifications; (c) crown from
  **discrete reiterated units** → irregular massing, not a smooth uniform shell; (d) **taller-than-wide /
  balanced**, not wide-flat.
- **GAPS (the load-bearing one — SHOULD stay open):** ★ **no clean mature-dome crown has ever been measured**
  (the one CP mature anchor is top-cropped and grove-context; the horticultural W/H is a cultivar/context
  average, not open-grown crown geometry). The **exact open-grown mature aspect for CP planes is an
  off-computer gap** → closes only with **LiDAR/QSM or photogrammetric crown measurement** of a sample of CP
  open-grown specimens. Compounding gap: **clone identity of CP's planes is unknown**, and form varies sharply
  by clone ('Media' twisting/weeping vs 'Pyramidalis' stiff vs 'Tremonia' spire) → closes with field/records
  clone ID. Branch insertion angles and tip-weep geometry are documented **qualitatively only**.

### STAGE 3 — VETERAN "l tier" (≈18–28 m)
- **Proportion:** irregular, increasingly **broad and spreading**; here the crown **can** finally become
  **as-wide-as or wider than tall**, approaching the parental habit — but **asymmetric and gappy**, not a tidy
  dome. Exact hybrid veteran aspect **[?] not quantified in sources found** (the >1.2 in our docs is *one*
  winter silhouette, foreshortened). **WHY:** full dominance decay + reiteration + epicormic rebuild **[PS —
  extrapolated from veteran *P. orientalis*; T&SO]**.
- **Branch architecture:** "a tangle of crooked, widely spreading limbs," some **low / near-horizontal**
  (sometimes layering toward the ground); **epicormic / partial reiteration** (sprout clusters, secondary
  crowns) progressively builds and repairs the crown; **low multi-stem fork** **[PS — T&SO *orientalis*
  analogue]** **[BG — partial reiteration in veterans, Édelin/Hallé]**.
- **Reads as veteran because:** heavy low twisting limbs, crown asymmetry + dieback gaps, epicormic sprout
  masses, a gnarled tangled silhouette.
- **Plane-specific vs generic:** crooked/contorted heavy limbs + **retained pendulous fine tips** + **profuse
  epicormic sprouting** distinguish a veteran plane from, e.g., a veteran oak's blockier framework.
- **GAPS:** exact hybrid veteran aspect unquantified; the best on-disk winter veterans (`W_11648420`,
  `W_11999230`) are foreshortened → soft on proportion.

### Cross-stage — the developing form as ONE process
One **Massart architecture** undergoing progressive **dominance-decay + reiteration + metamorphosis**: aspect
moves **clearly-taller-than-wide (young) → taller-to-balanced (mature) → balanced-to-wider & asymmetric
(veteran)**; **clear-bole fraction falls** (forks lower with age — our measured trend, and consistent with the
botany); **widest point descends**. This validates "three buckets = one growth process" (§2) on the age axis
**and** re-grounds it in the species' actual architectural model — but with the **magnitudes shifted narrower**
than the current code (which crosses W/H = 1 at the mature tier; the grounded form stays ≤ ~0.85 until the
veteran). Woodland/drawn-up remains a separate, still-unrepresented light axis (§2).

### My own image reads (pixel-level, for the record)
- `S_75867287` (the specimen the dome mould was sampled from): **broad, roughly balanced, widest ~mid, clear
  bole ~2–3 m, divides low into several ascending co-dominant limbs — NOT a tall narrow ovoid.** The "0.85
  ovoid" label is shakier than its number. (Upward foreshortening likely inflates height, so true crown may be
  even broader.)
- `S_122865830` (mature anchor): **crown top out of frame — W/H unmeasurable — and grove-edge (competition
  context), not clean open-grown.** Confirms the load-bearing gap.
- Winter bares: architecture legible (clear bole; few heavy sinuous ascending-then-arching primaries) but every
  crown top cropped or the tree is a leaner → **no measurable full silhouette on disk.**

## 10.4 (c) Representative form per bucket + candidate reference image (image confirms; it is not the source)
Each candidate needs a human/vision pass on the actual pixels before it is an acceptance criterion (WebFetch
cannot see images; on-disk frames all carry a hazard).
- **Young:** upright broad-pyramidal, single leader + rhythmic plagiotropic tiers, few thin scaffolds, W/H < 1.
  *Candidate ref:* the Weyerhaeuser-campus young plane on Trees & Shrubs Online (**unverified** — no clean
  young whole-crown on disk).
- **Mature:** rounded/oval, taller-than-wide-to-balanced head of a **few heavy crooked twisting ascending-then-
  arching limbs with weeping tips**, "several trees fused" massing. *Candidate ref:* on-disk `S_286898477`
  (best summer, but distance-flattened) cross-checked against a Monumental-Trees open-grown Paris specimen
  (**unverified**).
- **Veteran:** low multi-fork, heavy widely-spreading crooked twisting limbs, asymmetric & gappy, epicormic
  sprouts. *Candidate ref:* on-disk `W_11648420` (winter veteran, foreshortened) / the Mottisfont plane on
  Trees & Shrubs Online (**unverified**).
- **Imagery-infrastructure gap:** `reference_photos/london_plane/` **does not exist**; all LP imagery lives in
  gitignored `tmp/inat_lp/` and would vanish on a clean checkout — promote the usable frames into the repo if
  this form model is to be the standing acceptance reference.

## 10.5 THE HONESTY GATE — sculpt-readiness per bucket (gaps are expected and are a success)

- **YOUNG — PARTIAL (architecture sculpt-ready; proportion direction-only).** *Sculpt-ready:* the Massart
  juvenile form (single leader + rhythmic plagiotropic tiers + few thin wide-angle scaffolds, taller-than-wide)
  is well enough understood to sculpt. *Named gap:* the exact aspect value and a **verified young whole-crown
  reference** (none on disk; the web candidate is unverified) — closes with a vision pass on a good young
  specimen photo (on-computer, cheap).
- **MATURE — NOT-YET on proportion; PARTIAL on architecture (the crux, and the gap SHOULD stay open).**
  *Sculpt-ready (qualitative):* the architectural form — a rounded, **taller-than-wide-to-balanced** head built
  as an **aggregation of a few heavy crooked twisting ascending limbs with weeping outer tips**, coarse
  branching, "several trees fused" — is now grounded enough to sculpt the *character*. *Named off-computer
  gap:* the **exact open-grown mature crown aspect (W/H) for CP planes is not pinned** — no clean mature crown
  was ever measured, the horticultural prior (0.65–0.85) and the thin local imagery (~0.8–1.0) disagree, and
  **clone identity is unknown**. This closes only with **LiDAR/QSM or photogrammetric crown measurement of CP
  open-grown specimens + clone ID** — genuine fieldwork we cannot do from here. **Leave it open.** Interim
  guidance for any build: use **taller-than-wide (~0.80), rounded top**, and *do not* re-fit a single number
  as if it were measured — the architecture (aggregated twisting limbs + weeping tips) carries the identity far
  more than the exact ratio, and is the thing to get right first.
- **VETERAN — PARTIAL (architecture sculpt-ready; proportion direction-only).** *Sculpt-ready:* low multi-fork,
  heavy widely-spreading crooked/twisting limbs, asymmetric & gappy, epicormic sprouting. *Named gap:* the
  exact hybrid veteran aspect (best local refs foreshortened; the >1.2 is one winter tree) — closes with a
  vision pass on good veteran silhouettes and/or the same crown measurement as the mature bucket.

**Net verdict:** the **architecture/branch-habit** understanding is now grounded enough to sculpt the
qualitative form at all three stages (and it decisively kills the smooth lollipop — the plane's mature crown
is an aggregation of few heavy crooked twisting limbs with weeping tips, taller-than-wide, not a ball and not a
wide flat dome). The **exact crown proportion** is grounded in *direction* but **not pinned in magnitude** for
the CP hybrid at any stage; the mature-tier aspect specifically is a **legitimate off-computer gap** (needs
crown-measurement fieldwork + clone ID) that **should remain open and flagged**, not filled with another fitted
number. That open gap is the correct, honest state — and naming it is the outcome that prevents the next
lollipop.

*No tree built, no code changed, no data pulled, nothing committed. Deliverable is this addendum.*

---

## 10.6 Label cleanup + standing next-steps (2026-07-08)

**Crown-form SHAPE NAMES deleted repo-wide.** The three descriptive crown-form labels formerly attached to
the s/m/l tiers are removed everywhere they were used as an identifier or display string. Rationale: a
two-word name can't hold a form model, so it held an *assumption* instead — and here the m-tier label's
assumption (that the mature crown is wider than tall) was botanically wrong for the hybrid (§10.0) and
re-taught the wrong shape to whoever read it (it drove the lollipop and mis-led §9.5). **`s`/`m`/`l` are the only tier labels** — neutral keys that
make no shape claim and force the reader to *this* form model. The grounded form knowledge is preserved here,
keyed to the tiers (§10.2–10.5); the **architecture** description (young: leader + rhythmic plagiotropic
tiers; m: aggregation of heavy crooked twisting ascending-then-arching limbs with weeping outer tips; l: low
multi-fork, heavy widely-spreading crooked limbs, asymmetric/gappy, epicormic; all under Massart's model)
survives, not just the aspect scalar.

**m-tier aspect — recorded PROVISIONAL.** m aspect = **~0.80 (taller-than-wide)** per §10 interim guidance —
explicitly **provisional, pending off-computer crown measurement (LiDAR/QSM or crown photogrammetry of CP
open-grown specimens + clone ID; NYC data trip, post-revenue).** Do **not** re-fit this number to any thin
anchor — **identity is carried by the ARCHITECTURE** (aggregated heavy crooked twisting limbs + weeping tips),
not the scalar. The live code scalar is left at its legacy **1.00** (`leafback_skeleton.py` BUCKETS,
`generate_trees_mtree.py` crown_bucket) and flagged in-line; **changing it belongs to the sculpt cut**, not
this label round.

**Files changed this round (label cleanup only; nothing committed):**
- Code: `scripts/leafback_skeleton.py` (BUCKETS names→age-class; `_P_OVOID/_DOME/_SPREAD`→`_P_S/_M/_L`),
  `scripts/generate_trees_mtree.py` (dropped inert `crown_bucket["name"]` ×3), `scripts/leafback_graph.py`
  (docstring/comments), `scripts/build_leafback_skeletons.py`, `scripts/leafback_skinner.py`, `tree_builder.gd`,
  `eval_plot_builder.gd` (comments).
- Docs: this file (§0–§10 re-keyed to s/m/l, architecture preserved), `docs/crown_type_buckets.md`,
  `docs/smla_bucket_migration.md`, `docs/leafback_bucket_validation.md` (+ its result table),
  `docs/leafback_lod0_density_escalation.md`, `docs/leafback_tree_planner_spec.md`,
  `docs/leafback_trunkscaffold_prototype.md`, `docs/first_mould_leafback_prototype.md`,
  `docs/leafback_critique_iter2.md`, `docs/leafback_topology_redesign_plan.md`,
  `docs/leafback_spacecolonization_prototype.md`, `docs/leafback_skin_spike_phaseA.md`,
  `docs/mtree_skeleton_input_investigation.md`.
- **NOT touched (correctly):** `TIER_BOUNDS`, GLB/impostor filenames, the `london_plane_m`→`rfind("_")` suffix
  parse, and the cross-species s/m/l schema — the structural keys are unchanged. `tmp/` working scripts
  (gitignored, not shipped; `tmp/leafback_graph.py` is the protected never-edit original) retain historical
  names by design — out of the committed surface.

---

## 10.7 ★ The PART level now exists — see the sibling doc (2026-07-09)

§10 grounded the **crown**; §0.5–§8 hold the **engine**. The level between them —
*what developmental process produces each part, and why the same part-type differs by position* — is now
written up in **[`docs/london_plane_part_model.md`](london_plane_part_model.md)**. Read it before any
sculpt/generator cut. Headlines that bear on THIS doc:

- **★ Citation correction to §10.2.** The plane architecture paper is **Caraglio, Y. & Édelin, C. (1990)**,
  *Bull. Soc. Bot. France, Lettres Bot.* **137(4–5): 279–291** — **Caraglio is first author**, not "Édelin".
  Its **body has never been read** by this project (403-blocked); both §10.2 claims (Massart's model; crown
  metamorphosis) rest on **secondary sources** and should be tagged as such.
- **A second, better plane source was found and is unread:** **Genoyer, Atger, Edelin & Caraglio (1999)**,
  "Some architectural markers of plane tree development…", *Acta Hort.* **496**: 209–220, **DOI
  [10.17660/ActaHortic.1999.496.26](https://doi.org/10.17660/ActaHortic.1999.496.26)** — the plane's
  **reference ontogenic sequence**. Its abstract states that a plane's developmental state is read off its
  **primary limbs** (`branches maîtresses`): their orientation, growth direction, **order of total
  reiteration**, and growth-unit morphology. Highest-value unread source we have. ★ Its own volume also
  contains **Fournier-Djimbi & Chanson, "Biomechanics of trees and wood…", 496:197–208**
  ([…496.25](https://doi.org/10.17660/ActaHortic.1999.496.25)) — **one volume closes two named gaps.**
- **§10.2's "aggregation of reiterated Massart units" is confirmed and sharpened** — and the part model shows
  the current `N_PRIMARIES = 4` scaffolds-off-one-spine **structurally cannot** produce it (scaffolds are
  laterals; reiterates are sub-trees). §10's mature crown is unreachable at any parameter setting.
- **★ 2026-07-09 — the reiterate is now DESIGN-READY, and §10's crown series is mechanized.** Barthélémy &
  Caraglio 2007 is **open access** (PMC2802949); its **figures** (not just captions) were read. Crown-building
  reiteration is **"automatic"/sequential** — fired "*after a definite threshold of differentiation*," and
  explicitly "*not… a move backwards… but rather **part of [the developmental] sequence***." Reiterates are
  placed and **truncated by the PAUPERIZATION GRADIENT**: complete at the trunk base → partial mid-crown →
  **Minimal Architectural Unit** at the apex/periphery. Fig. 26 draws the whole §10 series (unit expressed →
  duplicated → mature crown = "*a succession of reiterated complexes*"), with the **lower branches re-erecting**
  into the reiterates that build it. **So ovoid→rounded→spread is reiterate accumulation, not envelope
  interpolation.** Genoyer et al. 1999 drops from **blocker → refinement** (it holds plane's staging *numbers*).
- **Two plane-specific B&C figures confirm/extend §10.2's citations.** Fig. 18C (*Platanus*, citing Caraglio &
  Édelin 1990) — verified verbatim, **and** it shows plane labelled by **apparent** branching order, apex
  mortality at every axis, and a **short-shoot (S) axis category** we never modelled. Fig. 9B — **plane is the
  textbook exemplar of *delayed* (proleptic) branching** (short first internode + prophyll-α scar), which closes
  the part model's "syllepsis unconfirmed" gap.
- ⚠ **Pruning imagery, hardened rule.** Genoyer et al. studied *traumatised* planes and found their development
  **departs from the reference ontogenic sequence**. Cut-limb/pollard photos are evidence for limb **geometry**
  (taper, fork caliber step, insertion angle, crook-at-node), **never** for developmental **sequence**
  (reiterate order, crown assembly). A pollard is a tree whose ontogeny has been overwritten.
- **Two engine-level conflicts the part model exposes**, both explaining defects already in this doc's record:
  the pipe model is applied as a *snapshot* when it must be a **ratchet over history** (this is why limbs read
  "thin/wire" and why AC-14 needed a hand-weighted partition), and the grower steps by a fixed length `D` when
  *Platanus* extends by **annual sympodial modules** (this is why twigs are straight — plane has **no terminal
  bud**, and a relay kink per year is the species' crooked identity).
- `cb_frac` is imposed as an envelope input, but **clear bole is an output of shedding** — the next instance of
  this project's own retired lesson, *"depth is an OUTPUT, not a parameter."*

**★ STANDING NEXT-STEPS (parked here so the next round opens from them — NOT done this round):**
1. **Sculpt the m crown to its grounded ARCHITECTURE (the real §10 win, and the substance).** §10.2 grounded
   the mature form as Massart's model: build the crown as an **aggregation of several heavy crooked twisting
   ascending-then-arching limbs with weeping outer tips** — NOT one smooth envelope. §10 notes this
   **independently grounds the §8 "grow to a leaf field" recovery** (architecture research and growth-mechanism
   research converged). Next cut = sculpt the m crown to this architecture (provisional ~0.80 aspect, identity
   in the limb character), folded into the §8 leaf-field growth. This is the substance the rename cleared the
   way for.
2. **Representative reference image per tier — the standing visual acceptance criterion — OPEN, BLOCKED.** §10
   found only ~2 summer + ~2 winter proportion-readable frames on disk, all hazarded, no young whole-crown at
   all. Blocked on the **same imagery gap as the m aspect** — closes with the post-revenue NYC data trip. Keep
   the acceptance-criterion thread visible; pick it up when imagery improves.

*Label cleanup only. Structural keys untouched. Form knowledge preserved keyed to s/m/l. Nothing committed —
awaiting Chris's sign-off on the change set.*
