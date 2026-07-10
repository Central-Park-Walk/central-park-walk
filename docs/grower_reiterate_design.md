# Grower architecture — THE REITERATE AS A FIRST-CLASS OBJECT (design spec)

**Role:** Planner — *design and specify only.* **No grower code written. Nothing built. Nothing committed.**
Opus 4.8 (1M) · 2026-07-09
**Parent:** [`docs/london_plane_part_model.md`](london_plane_part_model.md) — the source-grounded mechanism.
[`docs/london_plane_growth_architecture.md`](london_plane_growth_architecture.md) §0.5–§8 = the engine, §10 = the crown.
**Scope (Chris's call):** the reiterate abstraction and *only* the structural changes it necessarily forces.
Not a top-to-bottom grower redesign. Where the reiterate touches something and the right change is unclear,
this doc **states the options and flags them (F1…F6)** rather than choosing silently.

**Status of every number below: see §10.** Design-ready ≠ numbers known. Provisional values are labelled
`[PROV]`; they exist so a prototype can run, and must never be cited as measured.

---

## 0. The headline — the abstraction under the abstraction is TIME

The part model established that C1 (annual modules), C2 (pipe ratchet), C3 (scaffolds≠reiterates) and C5
(set-point + survival) are one missing abstraction: the reiterate. Designing it surfaces something one level
deeper, and it is the single most important finding of this document.

**The grower has no clock.** Verified by reading `scripts/leafback_skeleton.py` and `leafback_graph.py`:

- `build_trunkscaffold()` runs **once**, to convergence. There is no time index anywhere.
- `_finish()` (`:59–67`) computes `radius` from the **final** children — one bottom-up pass — and then
  **rescales the whole field so the root equals `DBH_m/2`**. Caliber is *imposed*, not earned.
- Greps for `year`, `annual`, `module`, `shed` (as a rule), `light` (as a field), `ratchet`, `physiological`:
  **zero**.

Now observe what each of the four corrections actually requires:

| correction | what it is, formally |
|---|---|
| C1 annual modules | a **year boundary** — a discrete event at which the apex aborts and a lateral relays |
| C2 pipe ratchet | `radius[i] = max over t` of the pipe radius of its **then-live** children |
| C3 reiterate firing | a **threshold crossing** of a differentiation state that advances over development |
| C5 survival gating | light **integrated over the branch's life**, compared to branch size |
| C5 posture | self-weight sag **accumulating** while righting capacity **decays with radius** |

Every one is a statement about *history*. **You cannot ratchet without a past, you cannot cross a threshold
without a trajectory, and you cannot shed what was never grown.** The reiterate is first-class only if **the
year is first-class**. That is the structural change; everything else in this document follows from it.

> **This also explains, retroactively, why the AC-14 partition had to exist.** A one-shot grower cannot let the
> low limb *earn* its caliber, so `w^(p/2)` was introduced to hand it the answer (§5). The partition is not a
> bad heuristic — it is a **clock substitute**. Give the grower a clock and it deletes itself.

**Consequence for cost, stated up front:** the grower becomes an **iterative developmental simulation**
(≈ tens of year-steps per tree, offline, per tier — 3 skeletons total, not 6808). This is a real cost increase
over the current single pass. **F3 below offers a cheaper analytic approximation and recommends against it.**

---

## 1. THE REITERATE OBJECT

### 1.1 ✅ GAP-AU CLOSED — plane's ARCHITECTURAL UNIT, from the source

> **Revised 2026-07-09 (second pass).** Caraglio & Édelin 1990 is on disk
> (`reference/Architecture_et_dynamique_de_croissance.pdf`) and has now been **read in full — French text plus
> all five Planches rendered as images** (`tmp/partmodel/plates/`). The AU below is *transcribed from the
> paper's own table* ("Caractéristiques des différents ordres de ramification", Planche 2, p. 284), not inferred.
> **Everything downstream of `trunc_depth` in the first draft of this document was written against a 3-rung AU
> and is corrected in place.**

**A reiterate is a *truncated copy of the architectural unit*. You cannot truncate what does not exist.** The
first draft took `AU = [T, B, S]` from **B&C Fig. 18C — which is a teaching diagram illustrating that category ≠
branching order, not a specification of plane's AU.** That was a diagram read second-hand for a purpose it was
not drawn for. Plane's real AU has **five** axis categories, indexed by **apparent order A1…A5**, and it is
*"atteinte au cours des six premières années de la vie de l'arbre; c'est sa structure élémentaire, fonctionnelle,
son 'unité architecturale'."*

```
AU(Platanus) = [ A1 → A2 → A3 → A4 → A5 ]        |AU| = 5
```

| | **A1** (tronc) | **A2** | **A3** | **A4** | **A5** |
|---|---|---|---|---|---|
| orientation | **orthotropic** | plagiotropic | plagiotropic | plagiotropic | plagiotropic |
| **module length** | **[GAP-A1GU]** | ~15 nodes | ~10 nodes | 7 nodes | 5 nodes |
| phyllotaxis | alternate **spiral, 2/5** | base distichous → distal spiro-distichous to spiral | base distichous → distal distichous to spiro-distichous | **distichous** throughout | **distichous** |
| sexuality | — | — | — | **terminal** | **terminal** |
| **self-pruning** (`élagage`) | **never** | long term | medium term | after **1–6 yr** | after **1–4 yr** |

- **A5 = `rameaux courts`** (short shoots), and *"les A5 sont peu nombreux."* Our old `S` is A5 — **but A4 also
  bears terminal sexuality**, so "the category that flowers" is A4 **and** A5, not S alone.
- **The old T/B/S maps in, and `B` splits three ways:** `T = A1`, `B = {A2, A3, A4}`, `S = A5`. The three
  B-categories differ in module length, phyllotaxis and sexuality — differences the 3-rung AU could not express.
- ⚠ **The trunk's module length is NOT in the table** (the A1 column is blank there, and the text gives only
  "distichous base + distal spiral zone"). → **GAP-A1GU**, new and honest. Do not interpolate it from 15.

**Within-module production rule (trunk), from the text — this replaces the `[PROV]` acrotony fraction (§4):**

> *"Chaque module comprend une base distique et une partie distale à phyllotaxie spiralée d'indice 2/5. Il porte
> des rameaux à développement retardé à l'aisselle de **toutes les feuilles de la zone spiralée**. Le rameau **le
> plus distal** est orthotrope et assure le **relais** du module. Les autres, sous-jacents, sont plagiotropes
> distiques et constituent **les étages de branches**."*

So: **laterals occupy exactly the distal spiral zone; the most distal is the orthotropic relay; the rest are the
plagiotropic tier.** Acrotony is not a tuned fraction — it is *the spiral zone*, and the tier is a **pseudo-whorl**
(the paper's own word, `pseudo-verticille`) because it is the sub-relay laterals of **one annual module**.
**Tier spacing is therefore one year's growth**, derived, not authored.

Branch (plagiotropic) modules carry the same two-part rule: *"le plus distal se développe dans le prolongement du
module dont il est issu; il en assure le relais — les sous-jacents forment des rameaux latéraux présentant un
**angle d'insertion ouvert**."* → **relay departs at a small angle (the axis reads continuous); laterals depart
wide.** Qualitative, no numbers → **GAP-θ_relay narrows but does not close.**

**★ Category ≡ apparent order, and apparent order ≠ topological order.** Each A-axis is *"une série linéaire de
modules"* — a sympodial chain in which **every annual module is topologically a new branch**. So a 60-year-old A2's
distal module sits at true branching order ≈ 60. **`hierarchy_depth` is not merely a weak identity signal for this
species; it is meaningless as one.** (§9.1's caveat, now with the reason.)

### 1.2 The object

```
Reiterate:
    id                  int
    parent_reiterate    id | NONE            # NONE ⇒ this is the seed tree
    insertion_node      node_id              # where it was born on its parent
    birth_step          int                  # the year it fired
    birth_mode          TERMINAL_FORK | LATENT_BUD          # ← NEW (§2). C&E give BOTH.
    u_ins               float ∈ [0,1]        # normalized insertion position, base→periphery  (§3)
    start_order  s      int ∈ [1..5]         # the AU rung this copy STARTS at; it expresses A_s…A5  (§3)
    axes                [Axis]               # its own A_s (leader) and everything below
    D_0                 float ∈ [0,1]        # relay dominance inherited at birth  (§2)

Axis:                                        # == a "strand" == ONE apparent-order chain (a série linéaire)
    category            A1 | A2 | A3 | A4 | A5      # == apparent order; NOT topological order
    modules             [Module]             # exactly one per year of its life
    set_point_angle     float                # GSA, from category  (§7)
    D                   float ∈ [0,1]        # relay dominance; decays with age, reset per wave (§2)
    alive               bool

Module:                                      # == one annual shoot == one growth unit == ONE YEAR (§8)
    year                int
    nodes               [node_id]            # the metamers laid down that year
    spiral_zone         slice                # the distal sub-range that bears laterals (§1.1)
    relay_kink          float                # the angular discontinuity at its distal boundary (§8)
    laterals            [Axis]               # emitted over the spiral zone; most distal = relay (§1.1)
```

> ⚠ **`trunc_depth` (a count) is renamed `start_order` (a rung), because C&E label reiterates by *the rung they
> reproduce*, not by how many rungs they get:** `c.r.t.` (complexe réitéré **total**) on the trunk, and — drawn and
> labelled on Planche 4, Fig. 5 — **`c.r.p. A3`** and **`c.r.p. A4`**, partial complexes having *"la même structure
> que des axes A3 et A4 séquentiels."* A copy with `s = 3` **is** an A3: it expresses A3, A4, A5 and nothing above.
> `s = 1` is a total reiterate — a whole small tree. `s = 5` is a flowering short shoot (the Minimal Architectural
> Unit). The count is `6 − s`; the *identity* is `s`.

**Relation to existing entities — deliberately minimal:**
- `Axis` **is** the existing `strand`. One axis ↔ one strand id. No new concept.
- `Module` is new, and is the grower's time quantum.
- `Reiterate` is a *grouping* of axes. It is **not** emitted to the skinner (§9); it is scaffolding for growth.
- The tree is `Reiterate(order 0)` plus the nested reiterates that fire on it. **Recursion is the point:** a
  reiterate grows by the *same code path* as the seed tree, with `trunc_depth` and `phi_0` different.
  This is what "several trees fused" means, literally.

### 1.3 The four properties, discharged
| part-model requirement | how the object satisfies it |
|---|---|
| (a) inherits the relay | its leader axis is built of `Module`s with relay kinks, identically to the seed trunk |
| (b) truncated by insertion | `start_order s` — §3. **Two laws, one per `birth_mode`.** |
| (c) earns its own bole by its own shedding-ratchet | it has its own leader, its own leaves, its own shed events; the ratchet (§5) runs per-node and therefore per-reiterate |
| (d) born when relay dominance collapses | **`TERMINAL_FORK`:** the bearing axis's `D` falls below `Φ_fork`, its single dominant relay is replaced by 2–3 co-equal ones, and **each becomes a reiterate.** **`LATENT_BUD`:** a dormant bud on old wood releases and re-erects. Both are §2. |

**Nesting.** A reiterate reiterates in turn: *"chaque élément des fourches présente d'abord une forte acrotonie et
une grande dominance … il y a ensuite diminution de cette dominance ce qui aboutit à une **nouvelle vague de
réitération**."* So `D` **resets high in each newborn fork element and decays again** — the wave structure is a
recursion on `D`, not a counter. *"D'une vague à l'autre le caractère dominant du ou des relais diminue pour
devenir **nul**"* → the recursion terminates **on its own**, at the crown periphery, when `D_0 → 0`.
**`max_order` is therefore an OUTPUT, not a cap.** The `[PROV] max_order = 3` is deleted; keep a loop guard only.
**GAP-D₀** (how much dominance a newborn wave inherits) replaces the old GAP-carry, and is still a Genoyer number.

---

## 2. THE FIRING SCHEDULE (and how `N_PRIMARIES` dies)

### 2.1 The rule, from the source — ★ REWRITTEN. The state variable is RELAY DOMINANCE, and C&E say so.

Crown-building reiteration is **automatic / sequential** — it fires *"automatically … after a definite threshold
of differentiation"* and is *"**part of** this sequence,"* not a regression (B&C). No trauma trigger. That much
stands. But B&C leave the threshold's *substrate* abstract, and the first draft therefore invented a scalar φ and
thresholded it. **C&E name the substrate outright, for plane, and it is `D` — the dominance of the relay:**

> *"L'arbre n'est monopodial qu'en apparence et ce caractère est lié à l'existence d'un **seul relais dominant à
> chaque unité de croissance**."* … *"Le caractère dominant du relais **se modifie tout au long de la vie de la
> plante**."*

The paper then gives `D`'s whole trajectory, in three phases, and — crucially — says **reiteration *is* what
happens when `D` collapses**:

| phase | `D` | what the tree does |
|---|---|---|
| **early sympodial** | low | *"plusieurs relais assez équivalents"* → sometimes **orthotropic forks** → shrubby, even bushy habit |
| **establishment** | rising | *"la dominance d'un relais unique est de plus en plus marquée (**l'acrotonie augmente**)"* → the monopodial *appearance*, strong hierarchy, apparent orders differentiate |
| **crown building** | falling | *"diminution progressive de la dominance des relais subterminaux. Ce phénomène se traduit par la présence de **fourche sur les branches** (complexes réitérés **partiels**), puis à l'**extrémité du tronc** (complexes réitérés **totaux**)."* |

**★ A fork IS a reiteration.** When `D` falls below threshold, the module's one dominant relay is replaced by
2–3 co-equal relays, and each co-equal relay *is* a reiterated complex. This is the mechanism the first draft was
missing entirely — it had reiterates born only by **re-erecting an existing lateral**, which is C&E's *other*,
later mode. The trunk does not sprout its master branches sideways; **it forks, and stops being a trunk**:
*"une partie haute constituée par une **fourche de 2 ou 3 branches maîtresses orthotropes**. Dans cette zone le
tronc en tant que structure unique **s'est arrêté**."* And: *"La structure de ces branches maîtresses est
comparable à celle du tronc (A1) de l'arbre jeune. **Ce sont donc des complexes réitérés totaux.**"*

⚠ **This is a substantive design change, not a rewording** → flagged as **F7** (§11), because it changes the
object model: a `Reiterate` can be born as one of N co-equal siblings **at an axis tip**, sharing an insertion
node, rather than as a re-categorized lateral. `spine_top` becomes an output: **the trunk ends where `D` first
crosses `Φ_fork` on A1.**

### 2.2 The two state variables, kept separate

**`D` (relay dominance)** governs *topology* — how many relays a module hands off to. **`φ` (physiological age)**
governs *character* — GU length, leaf size, whether an axis flowers. They are different quantities and the first
draft conflated them into one threshold. Keep both:

```
D(axis) = D_0 (inherited at birth)
        · decay(modules produced so far)                 # "diminution progressive"
        · env_release(light, water_stress, trauma)       # ← §7.4 / F1 AMENDMENT. LOWERS D.

φ(axis) = category_rung (A1…A5)                          # ★ MEASURED: module length 15/10/7/5 (§1.1)
        + drift_rate · (modules produced so far)         # drift: ageing along ONE axis — NOT in C&E
        − base_relief(first n_base modules)              # base effect: establishment
```

⚠ **A conflation caught in this pass, and it is exactly the error §4 exists to prevent.** The first reading of
C&E claimed its falling module lengths (15 → 10 → 7 → 5) "independently confirm **drift**." **They do not.** That
series runs **across apparent orders A2→A5**, which is the *category / order* gradient. **Drift** is the decline of
successive GUs **along one axis**. C&E tabulates the former and is **silent on the latter**. `drift_rate` remains
a gap; the **category rung is now measured**. (And note the order gradient is *not* "weak and superimposed" for
plane, as B&C describe it generally — 15 → 5 nodes is a 3× effect. It is the AU.)

### 2.3 Firing — two modes, because C&E describes two

```
at each year-step:

  # MODE 1 — TERMINAL FORK (builds the crown; the automatic/sequential one)
  for each live axis a, at its module boundary:
      if D(a) < Φ_fork:
          n = 2 or 3                                        # C&E: "une fourche de 2 ou 3"
          for i in 1..n:
              fire Reiterate(insertion = a.tip_node, birth_mode = TERMINAL_FORK,
                             start_order = order(a),        # ← the bearer's OWN rung. §3
                             D_0 = D_reset(wave))           # resets HIGH, lower each wave
          a is finished: it has no single relay any more

  # MODE 2 — LATENT BUD (reinforces the ageing crown; "issus tardivement de bourgeons latents")
  for each dormant bud b on old wood:
      if released(b):                                       # light, or arch-summit position (§7.2)
          fire Reiterate(insertion = b.node, birth_mode = LATENT_BUD,
                         start_order = s(u_ins(b)),         # ← positional law. §3
                         D_0 = D_reset(wave))
          re-categorize: plagiotropic → orthotropic set-point   # the re-erection (C5)
```

- **`Φ_fork`** — the dominance threshold, replacing the old `Φ_reiterate`. **GAP-Φ**, still a Genoyer number.
- **`D_reset(wave)`** — *"chaque élément des fourches présente **d'abord** une forte acrotonie et une grande
  dominance … il y a **ensuite** diminution."* So a newborn fork element is **partially rejuvenated**, and the
  reset is lower each wave until it reaches zero at the periphery. **GAP-D₀** (was GAP-carry). The *shape* is now
  sourced; the *numbers* are not.
- ⚠ Mode 2's `released(b)` is not a scheduled threshold — C&E ties it to **position** (§3) and to the **arch
  summit** (§7.2). Do not model it as random damage.

### 2.4 `N_PRIMARIES` becomes an OUTPUT
Today: `N_primaries = 4`, origins at `np.linspace(0.04, spine_frac, N)` × golden-angle azimuth
(`leafback_skeleton.py:232–247`). **Deleted.**

Tomorrow: the primaries **are** the master branches — the total reiterates born when A1 forks. Their
**count, heights and azimuths are all outputs**:
- *count* ← **C&E: the trunk fork yields 2 or 3 orthotropic master branches**, plus late `LATENT_BUD` total
  reiterates lower down;
- *heights* ← where `D` on A1 first crossed `Φ_fork`;
- *azimuths* ← phyllotaxis of the trunk's metamers (**2/5 spiral ⇒ 144° divergence**, now sourced), **not** a
  golden-angle sprinkle.

This is the same **"output, not parameter"** correction as the retired depth cap and as `cb_frac` (§6).

> ⚠ **Honest risk, and it has SHARPENED against the source.** The leaf-back study measured **~4** emergent
> primaries. C&E says the trunk forks into **2 or 3**. These are not obviously the same number, and the
> discrepancy is *informative*, not a nuisance: a veteran's visible heavy limbs are the 2–3 master branches
> **plus** the largest `LATENT_BUD` total reiterates on their lower parts (*"plus ils sont proches de la base des
> branches maîtresses … plus ils sont développés"*). So ~4 heavy limbs from a 2–3 fork is *predicted*, not
> contradicted — **but only if Mode 2 is implemented.** A grower with Mode 1 alone should yield 2–3 and be judged
> to have done so correctly. **Do not tune `Φ_fork` to hit 4** (F5 stands). Report the split by `birth_mode`.

---

## 3. PAUPERIZATION-TRUNCATION (the position law)

### 3.1 The law
> *"They all duplicate the original sequence of differentiation of the original individual **but the duplication
> is smaller and more 'pauperized' according to their insertion from the base of the trunk to the 'periphery' of
> the crown**. At the top of the tree and in the most peripheral part of the crown, pauperization… is the highest
> and reiterated complexes all have a reduced and minimal specific structure… '**Minimal Architectural Unit**'."*
> — B&C Fig. 23, read in full; Fig. 23A labels **Complete reiteration LOW** on the trunk, **Partial HIGHER**.

### 3.2 The coordinate — it is topological, not height
The gradient runs *"from the base of the trunk to the periphery of the crown."* That is **path distance from
the root**, not `y`. A limb tip and a high trunk node can share a height and be at opposite ends of the
gradient. Define:

```
u_ins = pathlen(insertion_node) / max_pathlen(tree)        ∈ [0,1]
```

`pathlen` **already exists** in the grower (`leafback_skeleton.py:118, 142, 181`) and is already threaded
through growth. This is a rename, not new machinery.

### 3.3 The mapping — ★ CORRECTED: five rungs, and it governs `LATENT_BUD` births ONLY

```
# MODE 2 (LATENT_BUD) — the positional law
start_order  s(u_ins) = clamp( round( 1 + (|AU| − 1) · u_ins^γ ), 1, 5 )        # |AU| = 5

# MODE 1 (TERMINAL_FORK) — NOT positional. The fork elements reproduce the FORKING AXIS's own rung.
start_order  s = order(forking_axis)
```

| `u_ins` | `s` | C&E's own name | expresses | reads as |
|---|---|---|---|---|
| trunk base | **1** | `c.r.t.` — complexe réitéré **total** | A1…A5 | a whole small tree |
| low on a master branch | **1–2** | `c.r.t.`, *"issus tardivement de bourgeons latents"* | A1…A5 | the veteran's heavy low limb |
| out along an A2 | **3** | **`c.r.p. A3`** | A3, A4, A5 | a branched sprout with flowering tips |
| further out | **4** | **`c.r.p. A4`** | A4, A5 | a small flowering spray |
| crown periphery | **5** | the **Minimal Architectural Unit** | A5 | a flowering short shoot |

**The mapping is no longer inferred — the paper draws and names the rungs.** Planche 4, Fig. 5 labels `c.r.p. A3`
and `c.r.p. A4` on the low branches, and the text: the sprouts covering old A2 axes *"sont des systèmes ramifiés
possédant **la même structure que des axes A3 et A4 séquentiels**."* A partial reiterate is **literally an axis of
order s, grown where an axis of order s does not belong.**

**This is where the brief's crux discharges.** A low primary and a high primary are **the same object started at a
different rung**. Nobody authors "low limbs are thick and complex."

- **γ (the pauperization rate) is a Genoyer number.** **GAP-γ.** Provisional `γ = 1.0` (linear) `[PROV]`.
- ⚠ **Mode 1 has no `γ` and no `u_ins`.** A fork at the tip of A1 gives `s = 1` **however high the tip is** — which
  is why the trunk's *apex* produces **total** reiterates while B&C's gradient says "peripheral ⇒ pauperized."
  **The two are not in conflict:** B&C's gradient indexes *insertion on old wood* (Mode 2); C&E's waves index
  *the forking axis's identity* (Mode 1). Applying `s(u_ins)` to a terminal fork would produce M.A.U.s at the top
  of the trunk and no master branches at all. **Keep the two laws apart.** This distinction did not exist in the
  first draft and is the single easiest way to get the crown wrong.

### 3.4 ⚠ Scope discipline: pauperization applies to REITERATES, not to ordinary laterals
B&C state pauperization for **reiterated complexes**. Ordinary laterals differ by **category and the other
gradients** (§2.2), which is a *different* mechanism. **The design must not apply `s(u_ins)` to every branch** —
that would re-collapse the gradients into one, the exact error the part model diagnosed. Ordinary laterals get
their character from their **category rung** (measured: 15/10/7/5) plus φ; only reiterates get truncated.
And within the reiterates, **only `LATENT_BUD` births use `s(u_ins)`** (§3.3) — a second scope boundary, new in
this revision, and just as easy to breach.

---

## 4. THE FOUR GRADIENTS, KEPT SEPARATE

The part model's §3 table demands these stay distinct. In the design they attach to different objects:

| gradient | attaches to | effect |
|---|---|---|
| **base effect** | the first `n_base` `Module`s of **any** axis | few, weak laterals; vigour rises acropetally out of the establishment zone |
| **acrotony** | *within* one `Module` | ✅ **now structural, not a fraction:** laterals at the axil of **every leaf of the module's distal spiral zone**; the **most distal is the relay**, the sub-jacent ones are the plagiotropic tier (§1.1) |
| **category / apparent order** | an **Axis**, at birth | ✅ **MEASURED (C&E):** module length **15 / 10 / 7 / 5** nodes for A2/A3/A4/A5; phyllotaxis; terminal sexuality at A4–A5 |
| **drift** | *along* an axis, module by module | φ rises → GU length ↓, laterals/GU ↑, short shoots appear, leaf size ↓ (B&C Fig. 27). ⚠ **C&E does not evidence this** — see §2.2 |
| **pauperization** | a **Reiterate** at birth | `start_order` — which AU rung the copy starts at (Mode 2 only) |

**The bare proximal limb now has its three distinct causes, each from a different mechanism**, exactly as the
part model requires: *base effect* (it branched weakly there), *shedding* (§6 — what it bore was dropped), and
*pauperization* (if it is a reiterate, its proximal region is its own clear bole). No hand-tuned "bare zone
fraction" parameter appears anywhere in this design. Good — because we do not have that number (§10).

- **acrotony distribution** for plane: ✅ **rule CLOSED** (spiral zone, most-distal relays). The *extent* of the
  spiral zone as a fraction of the module is still unstated → `[PROV]` distal 60%, but it is now a **measurement
  of one quantity with a known meaning**, not a shape guess.
- **epitony vs hypotony** (which *side* of a slanted parent branches): **GAP, NARROWED.** C&E settles the case
  that matters most: on a sagged branch, the next reiterated complex develops *"au **sommet de l'arcure**"* — the
  **summit of the arch**, i.e. the upper/convex side. That is **epitony, at the arch**, and it is `[PS]`. It does
  *not* settle which side an *ordinary* lateral takes on a slanted parent. Keep the gap, narrow the claim.

---

## 5. THE PIPE-MODEL RATCHET — and the death of AC-14's partition

### 5.1 The rule
Palubicki, read in full: *"Importantly, branch width is **not decreased** when leaves and branches are shed or
pruned. The model thus requires a **memory** of past leaves and branches."*

```
each year-step, bottom-up over LIVE nodes:
    r_live[i] = R0                                  if i has no live children
              = (Σ_{c live} r[c]^p)^(1/p)           otherwise
    r[i] = max(r[i], r_live[i])                     # ← THE RATCHET. monotone, never decreases.
```

Shed subtrees are removed from the emitted graph but **their contribution is already baked into every
ancestor's `r`**. A thick bare proximal limb is then not a special case: it is a limb that *had* children, kept
the girth, and lost them.

### 5.2 Does this delete the AC-14 `w^(p/2)` partition? **YES — the implementation. NOT the acceptance criterion.**

- **DELETED:** `partition_mode="growth"` and the whole block `leafback_skeleton.py:264–283` —
  `w = attractors-above-attachment`, `tgt = w**(PIPE_POWER/2)`, the capacity-constrained assignment.
  The part model showed this **fakes the ratchet**: it hands the lowest primary the biggest sub-crown *a priori*
  so that the one-shot pipe model will report a thick base. With a clock, the low reiterate gets a thick base
  because it **lived longer, bore more, and shed more** — which is the actual mechanism.
- **ALSO DELETED:** the Voronoi/anchor pre-assignment of attractors to scaffolds (`:257–286`) *in its entirety*.
  Reiterates do not receive a private attractor subset; they **compete** for the shared leaf field. Sub-crown
  size becomes an outcome of competition, not an allocation.
- **KEPT — as a TEST:** **AC-14 (primary-limb caliber: bold→medium→fine, lower = thicker) remains a blocking
  acceptance criterion.** It is now something the grower must *earn* rather than something it is *told*. Keeping
  the AC while deleting its implementation is the whole point.

### 5.3 ★ `DBH` also converts from parameter to output — and we have the data to validate it
`_finish()` currently rescales the entire radius field so `r[root] = DBH_m/2` (`:66–67`). Under the ratchet the
root radius **emerges** from the tree's integrated historical leaf load. Two options — **F2**.

**Recommended:** let DBH emerge, then **validate against the measured CP distribution we already hold**
(`central_park_trees.json`: LP median DBH 15 in, mode 12–18 in, n = 1564). That converts DBH from an imposed
input into an *independent check on the whole developmental model* — the strongest validation available to this
project, and it costs nothing because the data is on disk. If the grower's emergent DBH-vs-height curve matches
the census cloud, the ratchet is right. If it doesn't, something upstream is wrong and we want to know.

⚠ Risk: the emergent DBH depends on `PIPE_POWER` (2.3), `R0` (4 mm) and the total leaf count — a mis-set leaf
count silently rescales all caliber. Mitigation: fit **one** free scalar (`R0` or leaf count) to the census
median, then check the *shape* of the DBH–H relation, which is the falsifiable part.

---

## 6. SCAFFOLD REPLACEMENT — what the current code becomes

Concretely, against `scripts/leafback_skeleton.py`:

| current | fate | why |
|---|---|---|
| `N_PRIMARIES = 4` (`:340`) | **DELETED** → output of firing (§2.4) | C3 |
| scaffold origins `linspace(0.04, spine_frac, N)` × golden-angle (`:232–247`) | **DELETED** → reiterate firing sites | C3 |
| `partition_mode`, `growth` capacity partition (`:264–283`) | **DELETED** | §5.2 |
| Voronoi anchor assignment (`:257–262, 284–286`) | **DELETED** | §5.2 |
| `grow_scaffold` **Phase A** — unforked directed leader across the core (`:122–144`) | **DELETED** | it was a workaround for the hollow shell (growth doc §3-G3, `di_near` 6.0→2.0 already conceded this). A reiterate's leader is a **T axis grown by modules**, which forks as it goes. |
| `grow_scaffold` **Phase B** — space colonization (`:146–199`) | **KEPT, DEMOTED** | retained, but only as the production rule for the **space-filling axis categories** (S / distal twigs). See §7 and **F1**. |
| `_scaled()` di/dk ramps (`:91–94`) | **KEPT** | still the right shape for twig-scale ramification |
| trunk spine (`:218–228`) | **KEPT, REINTERPRETED** | it is `Reiterate(0).axes[T]`, now grown module-by-module rather than laid down in one `linspace` |
| `spine_frac`, `L_clear`, `seed_elev`, `golden` | **DELETED / derived** | all are placements the firing schedule now produces |
| `_finish()` radius pass + DBH rescale (`:59–67`) | **REPLACED** by the ratchet (§5) | C2 |
| `_finish()` `strand` assignment by `max(children, key=radius)` (`:70–82`) | **REPLACED** by the grower's own axis ids | the grower *knows* which child is the relay continuation; inferring it from radius is a guess. Same output type, so **skinner unaffected**. |
| `cb_frac` (`BUCKETS`, `:335`) | **OUTPUT, not input** | clear bole = what survives shedding (§10 growth doc C4) |
| crown envelope `_T_*/_P_*` (`:323–328`) | **KEPT as soft bound + checkpoint** | unchanged from growth doc §3-G3 |

**Net:** `build_trunkscaffold` is replaced by `grow_tree(tier, years)`; `grow_scaffold` shrinks to
`grow_twigs(axis)`. The trunk spine, the envelope tables, `_scaled`, `_topo_leaves_first` and the strand *concept*
all survive.

---

## 7. SET-POINT + SURVIVAL-GATING (C5) — light does not steer

The part model's correction: **limbs grow at a gravitropic set-point angle and are survival-gated by light;
they are not steered toward it.** Overhead shade *kills* a limb (branch autonomy); it does not redirect it.

### 7.1 Direction — by axis CATEGORY, which is the botanically correct carve
Orthotropy/plagiotropy is a **category syndrome** (B&C), so the direction law belongs to the category:

```
A1  (trunk, reiterate leader) : orthotropic set-point (vertical), + relay kink at each module boundary
A2  (primary limb)            : plagiotropic set-point θ_GSA, + self-weight sag − reaction-wood righting
A3  (secondary)               : plagiotropic, same law, shorter modules (10 nodes)
A4  (fine branch)             : plagiotropic, 7 nodes, TERMINAL SEXUALITY
A5  (short shoot / twig)      : 5 nodes, distichous, terminal sexuality, few. Space-filling — the EXISTING
                                space-colonization rule. Sheds in 1–4 yr.
```
⚠ **Posture is a two-valued category syndrome** (orthotropic A1 vs plagiotropic A2–A5), but **module length,
phyllotaxis and sexuality vary across all five rungs.** The old T/B/S carve conflated A2, A3 and A4 — which is
precisely the resolution the reiterate needs, since `c.r.p. A3` and `c.r.p. A4` are *different objects* (§3.3).

**★ This is the sharpest single insight in the design.** Space colonization was applied to the *whole tree*. It
belongs only to the **physiologically-old, space-filling categories** — the fine twigs, which is exactly where it
already looked right. The limbs are **posture-driven**, which is exactly where it looked like a wire armature.
The "pom-pom of equal sticks" and the "garden-hose arc" were the same error: using a twig rule to build a limb.

### 7.2 Posture (B axes)
```
per year-step:
    M_self     ∝ Σ (mass of subtree · lever arm)             # rises with length and load
    righting   ∝ maturation_strain / r                        # "the thicker the stem, the less it is
                                                              #  liable to curve" (Coutand 2007, read in full)
    dθ         = (righting toward θ_GSA) − (sag from M_self)
```
The limb **loses this contest slowly** — Alméras & Fournier: without gravitropic correction the design *"would
ultimately lead to a weeping habit."* The **ascend-then-arch-with-upturned-tip** profile then falls out for free:
proximal = stout, near set-point, rising; distal = thin, longest lever, arching; tip = young, light, still
righting. **No arc is authored.**

- `θ_GSA` per category for plane: **GAP.** Provisional: A1 = 0°, A2–A5 = 60° from vertical `[PROV]`.
- maturation-strain constant: **GAP** (Huang et al. 2010 would give it — paywalled).

**★ The arch is not a profile — it is a CASCADE, and C&E states the loop.** The first draft derived
"ascend-then-arch" as the static integral of righting-vs-sag along one limb. That is right but incomplete. The
paper's low branches — *"très longues et retombantes jusqu'au sol"* — are:

> *"une **succession de complexes réitérés partiels s'étant affaissés**. Le complexe réitéré suivant s'est
> développé **au sommet de l'arcure** formée par l'affaissement du précédent."* … *"d : **dépérissement de la
> partie distale** de l'axe affaissé."* (Planche 4, Figs. 3–4)

```
loop, per limb, over developmental time:
    the complex arches under its own accumulating load        (§7.2, already specified)
    a LATENT_BUD reiterate fires at the ARCH SUMMIT           (§2.3 Mode 2; epitony-at-the-arch)
    it re-erects, grows, and takes the light
    the distal continuation beyond the summit DIES BACK       (← falls out of §7.3's shed rule for free)
    the new complex becomes the arch. repeat.
```

**Nothing in that loop is authored.** The dieback is the shed rule applied to a subtree newly overtopped by its
own offspring; the re-erection is Mode 2; the arch is posture. But the **loop itself** — reiterate-at-the-summit
feeding the next arch — is a structure the design did not have, and it is what makes a veteran's low limbs reach
the ground as a chain of sagged complexes rather than as one long sagging beam. **The grower must run this loop,
not approximate it with a deeper arc.**

### 7.3 Survival (all categories)
Palubicki/Takenaka, read in full: *"The total amount of light gathered by a branch is compared with the branch
size measured in the number of internodes. If this ratio falls below a specified threshold, the branch is
considered a liability for the tree and is **shed**."* And: *"it is the key to the formation of tall boles."*

```
if  light_gathered(subtree) / size_in_internodes(subtree)  <  τ_shed :
        shed(subtree)                        # remove nodes; DO NOT reduce ancestor radius (§5)
```

This one rule produces, with no further authoring: the **clear bole** (→ `cb_frac` is an output), the **bare
proximal limb zone**, the **open crown interior**, and the **woodland drawn-up form** when the light field is
shaded (growth doc §2's missing second axis, now mechanized).

- **`τ_shed` is a species trait** (Kothari 2025, read in full: shade-tolerant species self-prune at a lower
  threshold). **GAP-τ** for plane. Provisional: tune τ so the m tier's emergent `cb_frac` lands near the measured
  0.30 `[PROV]` — a legitimate one-parameter fit against an independent measurement.

#### ★ C&E's five self-pruning tempos are a VALIDATION CURVE, not five parameters

C&E measures, per category: **A1 never · A2 long-term · A3 medium-term · A4 after 1–6 yr · A5 after 1–4 yr.**

The obvious move — and the one the task brief proposed — is to replace the single `[PROV] τ_shed` with these five
measured values, keyed to the five AU rungs. **That would be a Rule 3 violation, and this document exists to catch
exactly that.** An axis lifespan is *not a property the tree is given*; it is **what happens to an axis** that
gathers too little light for its size. A real plane derives its A5 lifespan; so must we.

> **Rule 3 (standing):** *anything a real thing derives, we derive → **OUTPUT not parameter.*** Learned four times.
> Five hard-coded lifespans would be the fifth.

So: **`τ_shed` stays ONE species-level scalar**, and the five tempos become a **five-point curve the grower must
reproduce**. This is strictly better than the old single-anchor calibration, because the ordering is *forced* by
the mechanism and is therefore falsifiable:

- **A1 never sheds** — the trunk's subtree gathers all the tree's light; its light/size ratio never approaches τ.
- **A5 sheds in 1–4 yr** — 5 nodes of size, borne deepest in the crown, flowers and is done.
- A2 → A3 → A4 fall monotonically in between, because module length falls **15 → 10 → 7 → 5** and each is borne
  deeper inside the shaded crown than its parent.

**One free scalar, five ordered predictions.** If a single τ cannot reproduce the ordering, the shed rule or the
light field is wrong, and we want to know — the same bargain §5.3 strikes for DBH. **`τ_shed` and `cb_frac` and
now the lifespan curve are one calibration problem with one knob.** Do not add four more.

⚠ Status change: **GAP-τ is not closed** (the *threshold* is still unknown). What changed is that its calibration
target went from one weakly-measured number (`cb_frac ≈ 0.30`) to a **five-point ordered curve from the species'
own monograph.** That is a large upgrade in falsifiability at zero parameter cost.

### 7.4 The light field — **F1, the biggest fork**
Palubicki's caution, verbatim: the shed rule *"is more suitable for models that rely on **shadow propagation**
rather than space colonization. In the [space-colonization] case, the **binary** nature of the environmental
input (Q = 1 or Q = 0) would cause branches to be shed **immediately** after they stop growing."*

**Our attractors give a binary Q. The shed rule therefore cannot be bolted onto the current space-col grower.**
Options in **F1** (§11).

### 7.5 ★★ AMENDMENT TO F1 (ratified) — light modulates RELAY DOMINANCE, not just survival

> **F1 is RATIFIED (§13.2) and is NOT overturned.** Space colonization stays confined to twig/A5 axes; light still
> does **not steer** a limb's direction. What follows **adds a third channel** through which light acts, and it is
> named in the plane's own monograph. An amendment to a ratified fork is recorded loudly, not absorbed silently.

F1 gave light exactly one job at limb scale: **a survival gate** (shed or don't shed). C&E gives it a second, and
it is *topological*:

> *"au début de la phase sympodiale il se forme plusieurs relais assez équivalents. Cela va même parfois jusqu'à la
> formation de **fourches orthotropes (milieu très ensoleillé)** conférant à la plante un aspect arbustif, voire
> buissonnant (en conditions très drastiques)."*

and, in the discussion:

> *"le moindre traumatisme, **un haut niveau d'énergie lumineuse** ou un stress hydrique peuvent **redonner, sans
> difficulté, une équivalence aux différents modules émanant d'une même u.c.**, favorisant tout processus
> réitératif."*

**High irradiance lowers `D`.** Low `D` means co-equal relays, which means **forking**, which (§2.1) means
**reiteration**. So light does not merely decide *which* limbs live — it decides **how often an axis forks, and
therefore how many limbs there are.**

```
D(axis) = D_0 · decay(age) · env_release(L, water_stress, trauma)      # env_release ≤ 1, falls as L rises
```

For CPW, `water_stress` and `trauma` are out of scope (§1.6 of the growth doc — CP planes are not cut). **`L` is
in scope and it varies across the park**, so this term is not academic.

**★ The payoff: the open-grown / woodland split now has TWO independent mechanisms, and they predict different
things.** The part model quoted USDA Silvics: *"Under forest conditions … a long, slightly tapered bole clear of
branches for 20 or 25 m"* vs *"Open-grown sycamores have a large irregular crown."* §7.3 claimed the **shed rule
alone** produces this. It does not — it produces the *bole length*. The **fork count and the fork timing** come
from `env_release`:

| | woodland (low `L`) | open-grown (high `L`) |
|---|---|---|
| **shed rule** (§7.3) | long clear bole | low limbs retained |
| **`env_release`** (this amendment) | `D` stays high → single dominant relay → **late, few forks** → tall excurrent form | `D` falls early → **early, many forks** → spreading, "several trees fused" |

Neither mechanism produces the other's effect. **Both are needed, and they are separable in a test** (same
grower, two light fields, four outcomes to check rather than two). This is a strictly stronger version of the
experiment C4 already proposed.

**⚠ It also resolves C7** (part model §6), the flagged tension between the two literatures. B&C: environment
*"almost never (**except probably in extreme conditions**) modify the inherent morphogenetic and ontogenetic
constructional rules."* C&E: extreme light gives forks, a shrubby habit, *"en conditions **très drastiques**."*
**The two agree, and the exception clause is where they meet.** The architecture school's own plane monograph
grants the environment a *parametric* handle on `D` inside an otherwise endogenous programme — which is exactly
the synthesis C7 said a grower needs and declined to invent. It did not need inventing.

⚠ **What this amendment does NOT license.** No space colonization at limb scale. No phototropic steering. No
light-seeking growth direction. `L` enters at exactly three places: `env_release(D)` (here), the shed gate (§7.3),
and the twig-scale space-filling rule (§7.1). **Nowhere else.**

---

## 8. ANNUAL MODULE BOUNDARIES (C1) — where a crook can be born

*Platanus* has **no true terminal bud**; the apex aborts and the topmost axillary bud relays (part model E1;
B&C Fig. 18C marks apical mortality `x` at *every* axis tip). A crook can only exist at an event, and the event
is the year boundary.

```
grow_module(axis, year):
    n = GU_length(φ(axis))                       # drift: GU length shortens with physiological age
    lay down n metamers along the current direction, with posture applied per step (§7.2)
    emit laterals acrotonically within this module (§4), azimuths from phyllotaxis
    # --- year boundary: the relay ---
    abort the apex
    promote the distal-most viable lateral to continue the axis
    apply relay_kink ~ Dist(θ_relay)             # ← the ONLY source of natural crookedness
    the new module's direction = relayed direction, then GSA-corrected over subsequent years
```

- **The crook is now structural**, not noise added to a smooth curve. Between boundaries the axis is
  near-straight; direction changes **at nodes** — precisely what the cut-limb imagery shows
  **[IMG — `cut_pruned_hard.jpg`]**.
- **`θ_relay` (the per-year kink angle) is a named GAP** and is *not* closed. **Narrowed by C&E:** the relay is
  *"le rameau le plus distal … dans le **prolongement** du module"* and Planche 1 Fig. 3 draws it as a near-straight
  continuation past the apical scar `c` — a **small** deflection — while the sub-jacent laterals take *"un angle
  d'insertion **ouvert**."* So relay-angle ≪ lateral-angle, `[PS]`, **still no number.** Provisional as before.

### 8.1 ✅ GAP-RHYTHM — CLOSED. **A Module IS a year.**

C&E settles it three independent ways, and the answer is the one the design assumed:

1. **A module is definitionally one growth unit.** *"le tronc … est constitué par la succession linéaire de
   **modules orthotropes, longs chacun d'une seule unité de croissance**"*; branch axes likewise, *"modules
   plagiotropes distiques, **longs d'une seule u.c.**"*
2. **There is exactly one apex-abortion event per axis per year.** *"les bourgeons terminaux de **tous les axes**
   **avortent chaque année en octobre-novembre** (parfois en septembre)."* One abortion ⇒ one relay ⇒ one module.
3. **Growth is rhythmic.** *"Les branches sont ramifiées de façon **rythmique** jusqu'à l'ordre apparent A5."*

**⇒ Module = growth unit = one year. Plane is MONOCYCLIC.** The relay count does **not** double. §8's atomic step
is vindicated, and the escalation is withdrawn.

> ⚠ **Correction to this project's own first-pass note** (`tmp/partmodel/ce1990_first_pass.md`), which claimed:
> *"The young plant's A1 carries two u.c. in year 2, so GU ≠ year in the juvenile phase — polycyclism is present
> early."* **That is a misreading.** The sentence is *"**Deux années après la germination**, au début du printemps
> la jeune plante est constituée d'un axe orthotrope (A1) comprenant **deux** unités de croissance"* — two growth
> units after **two** years is **one per year**. The paper never uses *polycyclique* and describes no second flush.
> **There is no polycyclism in this species per this source.** (See also the part-model correction to "*Platanus*
> is … polycyclic," which was never a B&C claim about plane but an inference layered onto a general sentence.)

**Honest residue.** C&E does not use the word *monocyclique*; the conclusion is an inference from (1)+(2)+(3),
each of which is an explicit statement. The one nuance: during the brief **monopodial phase** (*"un an ou deux,"*
range 1–4 yr) the module boundary is a genuine **resting winter bud** (*"arrêt de croissance hivernal avec
formation d'un bourgeon"*), not an aborted apex — annual abortion begins only after. **One module per year holds
in both regimes**; only the boundary's anatomy differs. A grower may ignore the distinction for the s/m/l tiers,
all of which are past it.

---

## 9. INTEGRATION — what stays untouched

### 9.1 `leafback_skinner.py` + the 5-attribute contract: **UNCHANGED**
The skinner consumes a generator-agnostic `(pos, parent, radius, strand, root)` node graph
(`leafback_skinner.py:304`) and **derives all five attributes itself** (`radius`, `stem_id`, `hierarchy_depth`,
`branch_extent`, `direction`). The design emits exactly that:
- `pos`, `parent` — from the modules;
- `radius` — from the ratchet (§5) instead of the one-shot pass. Same type, same units, **monotone along any
  root→tip path**, which is *stronger* than what the skinner assumes today.
- `strand` — from the grower's axis ids instead of the `max-radius-child` guess. Same type.
- `root` — unchanged.
**→ zero skinner change, zero contract change.** Two caveats, both parameter checks:
1. **Weld-margin re-confirm.** The skinner's cross-strand weld tolerance is tuned to `π·r_max/RING`. A ratcheted
   caliber distribution has *thicker* proximal nodes than today's, so the `l`-tier weld fix
   (`max(_twig_d, π·r_max/RING·1.1)`) must be re-verified. Parameter check, not contract change.
2. ⚠ **`hierarchy_depth` is a branching-order counter**, and the part model established (B&C Fig. 18C, *Platanus*
   by name) that **category ≠ order** for this species. It is safe as a *shading* attribute. It must **never**
   gate part identity. Add that as a comment where it is consumed, not as a code change.

### 9.2 Relationship to the §8 leaf-field recovery — **they compose, with one correction**
§8 of the growth doc: leaf positions are determined **first**, filling the crown volume; the skeleton grows to
reach them; cards render where the tips arrived.

- **Compatible, and the reiterate needs it.** Runions' attractors mark *"the availability of **empty space**"* —
  **not light**. So a leaf field steering twig growth is *space-filling*, not phototropism, and does **not**
  contradict the part model's "light does not steer." The two were never in conflict; the conflict was that
  space-col steering was applied to **limbs**.
- **The correction:** under §7.1 the leaf field steers **S/twig axes only**. T and B axes are posture-driven and
  ignore it. The leaf field also becomes the **light source** for the shed rule (§7.3) — leaves are what gather
  light — which is what finally couples §8's foliage to C5's survival gate.
- **Ordering.** Reiterate firing happens **during** growth (year-stepped); the leaf field is generated **before**
  growth (§8 Step 2). A reiterate fires into an *existing* leaf field and competes for the unconsumed leaves.
  **New question: should reiterates get fresh leaves as they age?** Runions produces a **branch-size hierarchy**
  by *"progressively adding attractors… with a gradually decreasing distance between the points"* during the run
  — which is precisely a time-stepped leaf field. **F4.**

### 9.3 Leaf card size — flagged, not designed here
Fig. 27 (read directly): **leaf size ↓ and form simplifies with physiological age**; FNA independently: plane
leaves *to 30 × 40 cm on sucker shoots* vs 6–20 cm typical. **Cards should scale with φ of the bearing axis**
(large/lobed on young, vigorous, basal, reiterate-leader axes; small/simple at the mature periphery). We render
one size.
⚠ **This is the one place the design would touch the contract**: card size needs `φ` per node, i.e. a **6th
attribute**. Deferred to the foliage layer; flagged so it is designed in, not rediscovered. Not in this scope.

---

## 10. NUMBER GAPS — every one, flagged

**Rule: the design specifies STRUCTURE. Where it needs a plane number it does not have, it names the gap.**
Nothing here is fitted to a thin anchor. That is what produced the lollipop (growth doc §9).

> **Revised 2026-07-09 after the full C&E read.** Four gaps closed, three narrowed, two new, one reframed.
> Every `[PROV]` that became **MEASURED** is marked ✅.

| symbol | what it is | status | closes with |
|---|---|---|---|
| **GAP-AU** | plane's **axis-category production rules** | ✅ **CLOSED (structure).** A1…A5 tabulated: module length, phyllotaxis, orientation, sexuality, self-pruning (§1.1) | **Caraglio & Édelin 1990** — read in full, text + all 5 plates |
| **GAP-RHYTHM** | rhythmic vs continuous; mono- vs polycyclic | ✅ **CLOSED. Rhythmic, MONOCYCLIC. Module = year** (§8.1). Escalation withdrawn | C&E, three independent statements |
| **GAP-acrotony** | lateral distribution within a module | ✅ **RULE CLOSED**: laterals on the distal **spiral zone**, most-distal = relay. Zone *extent* still `[PROV]` 60% | C&E (rule); one twig for the fraction |
| — | **phyllotaxis** | ✅ **CLOSED: 2/5 spiral** on orthotropic axes, **distichous** on plagiotropic, spiro-distichous in transition. *(Part model §4.1 said "not confirmed — do not hard-code." It is now confirmed.)* | C&E |
| **GAP-A1GU** | ★ **NEW** — the **trunk's** module length in nodes | unknown. The A1 column of C&E's table is **blank** for module length | measurement, or Genoyer |
| **GAP-D₀** | ★ **NEW** (replaces GAP-carry) — dominance a newborn fork element inherits, and its decrement per wave | *shape* known (resets high, falls each wave, → 0 at periphery); numbers unknown | **Genoyer 1999** |
| **GAP-Φ** | the **fork threshold** on relay dominance `D` (was: a threshold on φ) | reframed by §2.1; number unknown | **Genoyer 1999** staging |
| **GAP-γ** | pauperization rate (`s(u_ins)` exponent), **Mode 2 only** | unknown; `[PROV] γ = 1.0` | **Genoyer 1999** |
| **GAP-drift** | ★ decline of successive GUs **along one axis** | unknown — and ⚠ **C&E does NOT supply it** (its 15/10/7/5 is the *category* gradient; §2.2) | Genoyer; or measurement |
| **GAP-ORDER** | max reiterate order per stage | **reframed: an OUTPUT, not a cap** (§1.3). `[PROV] 3` deleted. C&E: mature crown expresses **6** apparent orders (A6 appears), *"un ordre de ramification supplémentaire"* | — |
| **GAP-τ** | shed threshold (light/size) for plane | unknown; ONE `[PROV]` scalar. ★ **Calibration target upgraded** from `cb_frac ≈ 0.30` to C&E's **five-point ordered lifespan curve** (§7.3) | one-param fit, now 5× more falsifiable |
| **GAP-θ_GSA** | set-point angle per category | unknown; `[PROV]` A1 0°, A2–A5 60° | Wilson 2000 (paywalled) |
| **GAP-strain** | maturation-strain / righting constant | unknown | Huang et al. 2010 (paywalled) |
| **GAP-θ_relay** | per-relay kink angle | **NARROWED**: relay ≪ lateral (*"prolongement"* vs *"angle d'insertion ouvert"*). No number | measurement; or emit as output of relay × righting |
| **GAP-epitony** | which side of a slanted parent branches | **NARROWED**: reiterates arise at the **arch summit** (upper side) `[PS]`. Ordinary laterals still unknown | literature; scaled photo |
| — | `PIPE_POWER = 2.3` | in the empirical range 1.8–2.3 (Eloy 2011) | keep; sits at the top of the range |
| — | **DBH per tier** | ✅ **MEASURED** (census, n = 1564) | **validation target**, not an input (§5.3) |
| — | **`cb_frac` per tier** | ✅ measured-ish | an **output**; one of τ's calibration targets |
| — | **A2–A5 module lengths** | ✅ **MEASURED: 15 / 10 / 7 / 5 nodes** | — |
| — | **A1–A5 self-pruning tempos** | ✅ **MEASURED** (never / long / medium / 1–6 yr / 1–4 yr) | **validation curve** for `τ_shed`, *not* five parameters (§7.3) |
| — | crown envelope tables | measured (thin) | soft bound + checkpoint, unchanged |

### What this revision changed, beyond the numbers
1. **★ GAP-AU is closed, and it had five rungs, not three.** B&C Fig. 18C was a *teaching diagram*, not plane's AU.
   Everything keyed to `|AU|` re-derived (§1.1, §1.2, §3.3).
2. **★ Reiteration is FORKING** (§2.1). The state variable is **relay dominance `D`**, not physiological age, and
   C&E gives its whole life trajectory. The design had only the secondary birth mode. → **F7.**
3. **★ There are TWO birth modes with TWO truncation laws** (§2.3, §3.3). Merging them puts M.A.U.s at the top of
   the trunk and produces no master branches at all.
4. **★ Light modulates `D`** → an **amendment to ratified F1** (§7.5), and it **resolves C7**.
5. **The arch is a cascade, not a profile** (§7.2) — reiterate at the summit → dieback → new arch → repeat.
6. **A Module is a year** (§8.1). Monocyclic. The load-bearing gap is closed *in the design's favour*.
7. **Two of this project's own claims were wrong and are corrected**: "plane is polycyclic" (§8.1) and "C&E's
   falling GU lengths confirm drift" (§2.2 — they evidence the *category* gradient; the gradients must stay apart).
8. **`τ_shed` must NOT become five constants** (§7.3) — Rule 3. Lifespans are outputs.

---

## 11. FORKS — Chris's calls, stated not taken

**F1 — the light/steering model (the biggest).** The shed rule needs a graded light field; our attractors give
binary `Q`.
- *(a)* **Keep space colonization everywhere**, approximate shedding some other way. Cheapest; contradicts the
  part model and Palubicki's explicit warning. **Not recommended.**
- *(b)* **Category-split** (§7.1): posture for T/B, space colonization for S/twigs; light for shedding computed
  from a **coarse shadow-propagation voxel grid** (Palubicki §4.1, `Δs = a·b^(−q)`, `Q = max(C − s + a, 0)`).
  Offline, 3 skeletons — cost is irrelevant. **RECOMMENDED.**
- *(c)* **Full Palubicki**: shadow propagation for direction *and* shedding, BH-λ for resource. Most faithful,
  largest departure from the validated line-C base, and it discards the space-col work that *does* function at
  twig scale.

**F2 — DBH: imposed or emergent?** Recommend **emergent + validated against the census** (§5.3). Cost: one free
scalar must be fitted; benefit: the strongest independent check the project can run.

**F3 — the clock.** *(a)* full year-stepped developmental simulation (**recommended**, faithful, the whole point);
*(b)* an analytic ratchet approximation without a clock — e.g. estimate each node's historical peak load from
its position. Cheaper; but it is **exactly the AC-14 partition again under a new name**, and it cannot produce
firing thresholds, module boundaries, or shedding. **Recommend rejecting (b) explicitly**, so it is not
rediscovered later as an "optimization."

**F4 — is the leaf field static or time-stepped?** Runions gets a branch-size hierarchy by *progressively adding
attractors at decreasing spacing.* A time-stepped leaf field would let reiterates fire into fresh space and would
produce the size hierarchy for free — but it changes §8's "leaves determined FIRST" property, which Chris
explicitly framed as "World A, no chicken-and-egg." **Genuine tension; Chris's call.** Middle path: generate the
full field once (World A preserved), but **release** it in shells over developmental time.

**F5 — do we keep `N_PRIMARIES ≈ 4` as an acceptance criterion?** If firing yields a different count, is that a
bug or a finding? Recommend: **treat 4 as a soft expectation, not a gate**, and report the emergent count
(§2.4's honest risk).

**F6 — scope of the first prototype.** Recommend proving the mechanism on the **m tier only**, leafless, judged
on: (i) emergent primary count and heights, (ii) AC-14 caliber gradient earned not imposed, (iii) a clear bole
emerging from shedding, (iv) crooks at module boundaries, (v) emergent DBH vs census. **No mesh, no perf gate,
no cards** until those five pass on the skeleton.

---

### ★ F7 — NEW FORK, surfaced by the C&E read: **which reiterate birth mode(s) does the grower implement?**

C&E describes **two**, with different geometry, different truncation laws, and different roles (§2.3, §3.3).
The first draft implemented only Mode 2, and called it the crown-building mechanism. **It is not.**

| | **Mode 1 — `TERMINAL_FORK`** | **Mode 2 — `LATENT_BUD`** |
|---|---|---|
| trigger | `D < Φ_fork` at a module boundary | dormant bud released on old wood |
| where | the **tip** of the bearing axis | anywhere on old wood; **arch summits** (§7.2) |
| how many | 2–3 co-equal siblings | one per released bud |
| `start_order` | **the forking axis's own rung** | `s(u_ins)` — the positional law |
| builds | **the crown**: master branches, the wave series, the fork-density gradient toward the periphery | the veteran's low heavy limbs, the arch cascade, the *"multitude de petits rejets"* on old A2s |
| stage | C&E's phases 2–3 (*arbre du présent*) | C&E's phases 4–5 (*arbre du passé*) |

- *(a)* **Mode 1 only.** Gets the *arbre du présent* — a forked, tiered, rounding crown. Cheapest. **Cannot make a
  veteran**: no arch cascade, no low heavy limbs, no ground-sweeping branches, and the emergent primary count
  lands at 2–3 rather than ~4.
- *(b)* **Both (RECOMMENDED).** They are the *same* `D` threshold at two different bud origins, so Mode 2 is a
  small addition once Mode 1 exists, and it is what makes an *old* tree old. The l tier needs it; the s tier
  never fires either. **This is what C&E's five-phase développement actually is.**
- *(c)* **Mode 2 only** — the status quo ante. Now known to be the wrong one. **Not recommended.**

**Recommend (b).** But it is Chris's call because it is a scope decision: Mode 2 is where the *arbre du passé*
lives, and CP's l-tier planes are exactly that tree.

> **✅ RATIFIED 2026-07-10 (Chris): (b) — BOTH birth modes.** The grower implements `TERMINAL_FORK` (crown
> builder) and `LATENT_BUD` (ager) as the same `D` threshold at two bud origins. F6 (the prototype) is
> unblocked. The m-tier prototype must fire at least `TERMINAL_FORK` to build its crown; `LATENT_BUD` is
> exercised properly by the l tier but the object model carries both from the start.

> **Why this is a fork and not a correction:** the first draft's `Reiterate` is born by *re-categorizing an
> existing axis*. A `TERMINAL_FORK` reiterate has **no prior axis to re-categorize** — it is born as one of N
> siblings sharing an insertion node, and the bearing axis *ends*. That is an object-model change, and object-model
> changes go to Chris.

---

## 12. Report-back summary

> ⚠ **This summary was written against the 3-rung AU and is superseded in points (a), (b) and (d) by the
> 2026-07-09 revision.** Corrected in place; the shape of the argument survived, the mechanism sharpened.

- **(a) The reiterate object** (§1): a recursive `Reiterate{insertion, birth_mode, u_ins, start_order, axes[], D₀}`
  whose `Axis` **is** the existing `strand` and whose `Module` is the new time quantum — **and is one year** (§8.1).
  It inherits the relay, starts at an AU rung set by its birth mode, earns its bole via the ratchet, and is born
  either as **one of 2–3 co-equal fork siblings at an axis tip** (`TERMINAL_FORK` — this builds the crown) or by a
  **latent bud re-erecting on old wood** (`LATENT_BUD` — this ages the tree). It is growth scaffolding and is
  **never emitted to the skinner**.
- **(b) Firing + pauperization** (§2, §3): firing is **automatic/sequential**, with no trauma trigger — but the
  state variable is **relay dominance `D`**, not physiological age, and **a fork *is* a reiteration.** `D` rises
  (acrotony increases), then falls; when it crosses `Φ_fork` the axis hands off to 2–3 co-equal relays and ends.
  `D` **resets high in each new wave and lower each time**, reaching zero at the crown periphery — so `max_order`
  is an output, not a cap. **Pauperization has five rungs (A1…A5) and applies to `LATENT_BUD` births only**;
  a terminal fork reproduces the forking axis's own rung, which is why the trunk's apex makes **total** reiterates.
  Low vs high primary = **same object started at a different rung.** `N_PRIMARIES` becomes an output — and C&E
  predicts **2–3** master branches, plus late latent-bud complexes.
- **(c) The scaffold code** (§6): `linspace`+golden-angle origins, the Voronoi anchor assignment, the growth
  partition, and Phase-A's unforked leader are all **deleted**. Phase-B space colonization is **kept but demoted**
  to the twig categories. The trunk spine, envelope tables and `_scaled` survive. **AC-14's `w^(p/2)` partition is
  DELETED** — it was a *clock substitute* — while **AC-14 the acceptance criterion is KEPT**, now something the
  grower must earn. `DBH` and `cb_frac` convert from inputs to outputs (and thence to validation targets).
- **(d) Number gaps** (§10): **four closed** by C&E (GAP-AU, GAP-RHYTHM, the acrotony *rule*, phyllotaxis 2/5),
  **three narrowed** (θ_relay, epitony, GAP-τ's calibration target), **two new** (GAP-A1GU, GAP-D₀), **one
  reframed** (GAP-ORDER → an output). Genoyer 1999 still supplies every *number* — `Φ_fork`, `D₀`, γ, drift.
  ⚠ **`τ_shed` must not become five constants**: C&E's five self-pruning tempos are a **validation curve**, and
  lifespans are outputs (Rule 3).
- **(e) Forks** (§11): **F1** the light/steering model (recommend category-split + coarse shadow grid) —
  ★ **AMENDED**, light also modulates relay dominance (§7.5); **F2** emergent DBH validated against the census;
  **F3** accept a year-stepped grower and explicitly reject the clockless approximation; **F4** dissolved by the
  leaf-back deprecation; **F5** whether ~4 primaries is a gate or an expectation (sharpened: C&E predicts 2–3 from
  the fork, plus late latent-bud complexes); **F6** prototype scope; ★ **F7 — NEW: which birth mode(s) to
  implement.** Recommend both. **F7 blocks F6.**
- **★ And the finding under the finding** (§0): the reiterate is first-class only if **the year** is. C1/C2/C3/C5
  do not merely share an abstraction — they each assert something about *history*, and the grower has no clock.
  Adding the clock is the structural change; the reiterate is what it is for.

*No grower code written. No build run. No protected file edited. Nothing committed.*

---

# 13. DECISIONS — all six forks RESOLVED (Chris, 2026-07-09). Design doc is HELD.

> Recorded at session close. **Nothing built. Nothing committed.** These are ratified decisions, not proposals;
> a future session may not silently re-open them. Where a decision reverses an earlier plan of record, the
> superseded doc is named.

## 13.0 ★ PROJECT PRINCIPLE — bigger than this tree, and it governs all future species and systems

> **The park's method is to demonstrate not just what the world looks like, but HOW IT COMES TO LOOK THAT WAY.
> Simulate the process; let appearance emerge.**
>
> **A process cannot be a convincing fake. A snapshot can.** The lollipop was a snapshot — a shape fitted to a
> thin anchor, which is why it read wrong from every angle and why no amount of margin-noise could rescue it. A
> tree that *grows* right *looks* right, because appearance is a **consequence** of correct process rather than
> a target to be hit.
>
> **This is never-ending by design.** Realism grows with Claude's understanding of the process and with the
> compute available to run it. There is no "done" state to converge on — there is a mechanism that gets more
> right as it gets better understood.

Promoted to [`docs/standing_rules.md`](standing_rules.md) as **Rule 3**, permanent and all-projects.
Consequences already visible in this document: `N_PRIMARIES`, `cb_frac`, `DBH` and skeleton depth are all
**outputs** — because in a process they *have* to be. Anything a real tree derives, we derive.

## 13.1 FOUNDATIONAL — the two facts every future session must open from

**(i) TIME is the abstraction under the reiterate.** The grower runs over **developmental years**, not one-shot
(§0). This is *why* depth, `cb_frac`, `N_PRIMARIES` and `DBH` become outputs: each is a fact about a history, and
a grower with a clock has one. **RATIFIED.**

**(ii) GAP-AU is a PREREQUISITE, not a refinement.** Plane's **architectural unit** must be specified before the
reiterate — which is *by definition a truncation of it* — is buildable. **You cannot truncate what does not
exist.** This reorders the library priority:

| priority | source | what it holds | status |
|---|---|---|---|
| **1st** | **Caraglio & Édelin 1990**, *Bull. Soc. Bot. France, Lettres Bot.* **137(4–5): 279–291** | ★ **the thing being staged** — plane's axis categories **A1…A5** and their production rules | ✅ **READ IN FULL 2026-07-09** (§13.4). Prerequisite **satisfied**. It also gave the *mechanism* (relay dominance), which was not expected of it |
| 2nd | Genoyer et al. 1999, *Acta Hort.* 496:209–220, [DOI 10.17660/ActaHortic.1999.496.26](https://doi.org/10.17660/ActaHortic.1999.496.26) | the **staging numbers** (`Φ_fork`, `D₀`, γ, drift, reiterate order per stage) | **priority unchanged.** C&E supplies the mechanism and the AU; Genoyer still supplies every number that makes them run |

**RATIFIED.** *(The ratification stands; the prerequisite is now discharged, not withdrawn.)*

## 13.2 The six forks

| fork | decision | note |
|---|---|---|
| **F1 — light / steering** | ★ **RATIFIED: category-split.** Space colonization → **twig / `A5` axes ONLY**. Posture set-point + **shadow-propagation survival gating** → `A1`–`A4` limbs. **★ AMENDED 2026-07-09 — see §7.5:** light **also modulates relay dominance `D`**, and therefore forking. Ratification stands; a third channel is added. | *"The pom-pom of equal sticks and the garden-hose arc were **one error: a twig rule building a limb**."* Palubicki's warning stands. **The amendment does not re-open steering** — `L` enters at `env_release(D)`, the shed gate, and the twig rule, and **nowhere else**. It resolves C7. |
| **F2 — DBH** | ★ **RATIFIED: emergent, validated against the 1564-tree census** (LP median 15 in, mode 12–18 in, `central_park_trees.json`). | DBH stops being an input and becomes the project's **strongest free independent check** on the whole developmental model. Fit one scalar; the falsifiable part is the *shape* of the DBH–H relation. |
| **F3 — the clock** | ★ **RATIFIED: the year is REAL.** Full year-stepped developmental simulation. **The clockless analytic ratchet is REJECTED** — it *is* AC-14's deleted `w^(p/2)` partition renamed. | Recorded explicitly so it is not rediscovered later as an "optimization." A clockless ratchet cannot express firing thresholds, module boundaries, or shedding. |
| **F4 — leaf field** | ★★ **RESOLVED BY DEPRECATION — see §13.3.** There is no leaf field to place or time. | The question dissolved rather than being answered. |
| **F5 — `N_PRIMARIES`** | ★ **RATIFIED: an emergent EXPECTATION, not a tuned target.** | ~4 is what the merge study measured; the grower must *reproduce* it. **Do not tune Φ to hit 4.** If it yields 9, that is a finding — report it. |
| **F6 — prototype scope** | ★ **RATIFIED: follows the AU work.** No prototype until GAP-AU is specified (§13.1-ii). | Then: m tier, leafless, judged on the five criteria in §11-F6. Not "build the reiterate" — the AU first. |

## 13.3 ★★ LEAF-BACK IS DEPRECATED AS A GENERATION STRATEGY

**Decision (Chris, 2026-07-09). This supersedes `docs/london_plane_growth_architecture.md` §8 (the
"leaves-as-attractors" recovery) and retires the World-A/World-B framing entirely.**

**What leaf-back was for.** It was a workaround for exactly one problem: *coherent trees that did not read, at
distance, as what they were.* Fill the crown with the foliage the tree must end up carrying, then connect
backwards to the trunk — the silhouette is then correct by construction.

**Why it is no longer needed.** The developmental grower solves that **same** problem, and solves it better:

- **The tree looks right because it GROWS right.** Appearance is a *consequence* of a correct process, not a
  target the process is aimed at (§13.0). Silhouette, caliber gradient, crown depth, bole clearance and limb
  character all fall out of relay + shedding + ratchet + posture + reiteration.
- **It dissolves the problems leaf-back *created*:**
  - **skeleton-meets-cards** — a grown tree puts leaves at twig terminals **by construction**; nothing has to be
    reconciled after the fact. (`_card_placements_per_branch`'s post-hoc bark-vertex re-derivation, and §8's
    proposed replacement, both become moot.)
  - **clustering** — adjacent leaves share an upstream branch because they *grew from* it, not because a capture
    radius was tuned to make them appear to.
  - **World-A / World-B (the chicken-and-egg)** — there is no ordering problem left. Growth is forward. Leaves
    exist where twigs arrived.
- **Therefore: there is NO separate leaf field to place, to shape, or to time.** F4's entire question — static
  field vs. time-released shells — **does not arise.** §8.3's authored clumping/margin terms (honestly labelled
  there as *"literature-shaped, not species-measured"*) are **no longer needed at all**; irregularity comes from
  the growth process reaching an uneven light field.

**What survives from leaf-back:**
- **The three per-tier crown envelopes** (`_T_*/_P_*`, from the iNat silhouette work) — **as growth boundaries,
  targets and per-tier validation checkpoints.** Same numbers, and the same role §3-G3 already assigned them.
- The **measured distributions**: DBH (n = 1564), heights, tier mix — now **validation targets** (F2).
- `scripts/leafback_skinner.py` and the **5-attribute contract** — unchanged and unaffected (§9.1). *A skeleton is
  a skeleton.* The name "leafback" on that file is now a historical artifact, not a description.

**What dies with it:** the attractor cloud as a *persisted leaf field*; the leaves-as-attractors recovery (§8);
the clumping/margin authored terms; the World-A framing; `dk` as the "economy knob"; and the framing of the
crown as something to be *filled* rather than *grown*.

**Honest note.** Leaf-back is **not being called wrong.** It was the right response to a real defect, it produced
the crown envelopes we still use, it forced the depth-as-output lesson, and its failures (the hollow lantern, the
wire armature) are precisely what taught us that the connection had to be a *process*. It is **superseded**, which
is the good outcome for a scaffold.

## 13.4 ✅ DONE — Caraglio & Édelin 1990 obtained and read in full (2026-07-09)

**Citation:** Caraglio, Y. & Édelin, C. (1990). "Architecture et dynamique de croissance du platane, *Platanus
hybrida* Brot. (Platanaceae) {Syn. *Platanus acerifolia* (Aiton) Willd.}." *Bull. Soc. Bot. France, Lettres Bot.*
**137**(4–5): 279–291. DOI [10.1080/01811797.1990.10824889](https://doi.org/10.1080/01811797.1990.10824889).
On disk: `reference/Architecture_et_dynamique_de_croissance.pdf` (14 pp).

**Read in full: the French body *and* all five Planches rendered as images** (`tmp/partmodel/plates/`, pp. 5, 7,
8, 10, 12 = Planches 1–5). ⚠ A prior note listed the plate pages as 5/8/10/12; **Planche 2 — the architectural
unit, the single most important figure — is on page 7**, and a page-list read from captions alone would have
missed it. *The corollary held: the plates carry geometry the captions do not.* What they added:

- **Planche 2** — the AU table *and* a branch drawn **from above**, showing the distichous A4/A5 sprays as a
  **planar fan**. Phyllotaxis is the readout of orthotropy: spiral ⇒ orthotropic, distichous ⇒ plagiotropic.
- **Planche 1 Fig. 3** — the relay leaves the aborted apex at a **small** angle; the axis reads continuous. The
  caption says only "sympodial branching."
- **Planche 3 Fig. 1** — the crown is **three stacked zones on the trunk** (low plagiotropic / transition /
  high orthotropic). Reiteration potential is a function of **position on the trunk**, not age alone.
- **Planche 3 Fig. 2** — a tier drawn **in plan**: a **pseudo-whorl** of ~5–6 limbs off *one* trunk node, each
  forking. Confirms tier = one annual module's spiral zone.
- **Planche 4 Figs. 3–5** — the **arch cascade** (§7.2) and the labels **`c.r.p. A3` / `c.r.p. A4`**, which are
  the pauperization rungs *named by the paper* (§3.3).
- **Planche 5** — the five-phase développement, and *"conforme au **modèle de Massart**"* — now **primary**, where
  the part model had it only via a secondary source.

**Result: GAP-AU CLOSED (§1.1) · GAP-RHYTHM CLOSED (§8.1) · GAP-acrotony rule closed · phyllotaxis closed.**
**F1 AMENDED (§7.5) · C7 RESOLVED · one NEW FORK (F7, §11) · two of our own claims corrected (§10).**

### 13.5 ★ AMENDMENT to ratified F1 — recorded, not absorbed

**F1 stands.** Space colonization remains confined to twig/A5 axes; light still does not steer a limb. **Added:**
light (with trauma and water stress) **modulates relay dominance `D`**, hence forking, hence reiteration — C&E,
verbatim: *"un haut niveau d'énergie lumineuse … peu[t] redonner … une équivalence aux différents modules émanant
d'une même u.c., favorisant tout processus réitératif."* Full statement and its consequences in **§7.5**.
This is why the woodland/open-grown split needs **two** mechanisms (shedding sets bole length; `env_release` sets
fork count and timing), and it is what dissolves **C7**.

> **✅ RATIFIED 2026-07-10 (Chris): F1 amendment adopted as written.** Light modulates `D` (fork count + timing)
> in addition to survival-gating — the third channel stands. F1 itself is unchanged: space colonization stays
> confined to twig/A5 axes, light does not steer a limb's direction. `L` enters at exactly three places:
> `env_release(D)`, the shed gate, the twig rule.

### 13.6 The next task — F6, the m-tier prototype (F7 called 2026-07-10)

**F7 and the F1 amendment are ratified (both, and as-written — §11, §13.5).** F6's precondition (the AU) was
already met; the object-model decision is now made. → **Build the F6 prototype: the year-stepped grower on the
m tier only, leafless**, judged on the five §11-F6 criteria before any mesh/perf/cards.

The numbers that make the AU *runnable* — `Φ_fork`, `D₀`, `γ`, drift, A1's module length — remain **Genoyer
1999** (still unobtained); they are the *staging numbers*, not the mechanism. The prototype therefore runs on
**`[PROV]` values, labelled as such**, and reports emergent outputs (primary count, caliber gradient, clear-bole
fraction, DBH) as *predictions to be checked against the census and Genoyer*, not as tuned results.

*Grower build STARTED 2026-07-10.*
