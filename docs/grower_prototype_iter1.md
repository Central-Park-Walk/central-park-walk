# London plane developmental grower — F6 prototype, ITERATION 1

**Status: prototype RUNS; mechanisms wired and topologically correct; 3 real bugs found &
fixed; 5 F6 criteria PARTIALLY met with specific diagnosed shortfalls. Awaiting review.**

Design of record: [`grower_reiterate_design.md`](grower_reiterate_design.md) (F7 = both birth
modes, F1 amendment ratified 2026-07-10). Code: `scripts/plane_grower.py` (new, isolated — the
frozen `leafback_skeleton.py` is untouched). Measurement + render harness: `tmp/grower_measure.py`
(gitignored). Renders: `tmp/grower_iter1_{s,m,l}.png`.

This is the F6 gate: **prove the year-stepped process on the m-tier skeleton, leafless, before
any mesh / perf / cards.** It is deliberately not a finished tree.

---

## What the grower does (per design)

A year-stepped developmental simulation. Each year every living axis grows one **annual module**
(§8, GAP-RHYTHM: a module = one year, monocyclic); the apex aborts and the distal-most lateral
**relays with a small kink** (the only source of crookedness). Laterals are emitted
**acrotonically** in the module's distal spiral zone (§4); most axillary buds stay **dormant**
(proleptic — available to Mode-2 later). Firing is by **relay dominance `D`** (§2): `D` decays,
and when it crosses `Φ_fork` the axis **forks into 2–3 co-equal reiterates and ends** — *a fork
IS a reiteration*. `D` resets lower each wave and terminates the recursion at the periphery (`D→0`,
so `max_order` is an OUTPUT). Radius is the **pipe-model ratchet** (§5, monotone max over history —
a shed limb keeps its girth in every ancestor). Posture is by **category** (§7: A1 orthotropic;
A2–A5 plagiotropic set-point + sag − righting). A **shadow-propagation light grid** (F1) drives the
**shed rule** (§7.3: `light/size < τ` → shed subtree, keep radius) and modulates `D`. Both **birth
modes** are implemented (F7): `TERMINAL_FORK` (crown builder) + `LATENT_BUD` (old-wood re-erection).

**F6 scope decision (recorded):** the prototype grows the **woody armature only — A1 trunk,
A2 primaries, A3 secondaries** (`MAX_CAT=3`). The A4/A5 short-shoot + twig layer is the
space-filling FOLIAGE layer (design §7.1, §9.2) and is deferred; being **leafless**, the terminal
A3 tips are the light-gathering proxy.

---

## Three real bugs found and fixed (this is what iter-1 is for)

1. **Over-ramification (124 k live nodes).** Growing an axis at *every* spiral-zone axil down
   through A5 gave ~7^order explosion. Fix: `BRANCH_GRADE` (a small number of buds release per
   module; rest dormant) + `MAX_CAT=3` armature scope. → sane node counts.
2. **Runaway vertical growth (tree reached ~30 m at H=14.4).** Reiterate leaders were gated by the
   *seedling's* 6-year AU-establishment window and had no height bound. Fix: short establishment
   for reiterate leaders (`REITER_MIN_AGE`) + crown-envelope **soft height cap** driving `D→0` as
   the apex nears H (§6). → height bounded.
3. **★ Floating-crown islands (zombie axes).** `_kill_subtree` marked shed *nodes* dead but not the
   `Axis` objects inside the subtree; those zombie axes kept growing, appending live nodes onto dead
   parents — a crown of disconnected islands that *looked* full but was a topology artifact. Fix:
   shedding now also kills every axis whose apex it severs. **This is the integrity-trace lesson in
   action** ([[lessons_critic_role_pipeline]]): the pretty render was wrong; component-tracing caught
   it. Use a connectivity check, never gestalt.

---

## The five F6 criteria — honest scoring

| # | criterion | verdict | evidence |
|---|---|---|---|
| (i) | emergent primary count + heights | **PARTIAL** | count emerges (s 14 / m 12) but skews to many low limbs; no distinct 2–3 master fork yet (C&E predicts 2–3). Not tuned to a number (F5 respected). |
| (ii) | AC-14 caliber gradient EARNED | **PARTIAL–GOOD** | taper along a limb is real & visible (trunk 190 → primary 64 → twig, all from the ratchet, nothing imposed). Across-primary *lower=thicker*: **s tier corr −0.62 ✓**; m tier not differentiated (primaries cluster low, co-equal). |
| (iii) | clear bole from shedding | **PARTIAL** | a bole emerges from the shed rule (mechanism works, cb is an OUTPUT) but too low: cb_frac s 0.14 / m 0.10 vs measured ~0.30. |
| (iv) | crooks at module boundaries | **MECHANISM ✓, magnitude GAP** | turning is concentrated at year nodes (2.3° at boundary vs 0.00° interior). Correct by construction; 2.3° reads straight — but `θ_relay` is an un-closed GAP (Genoyer), not a free knob. |
| (v) | emergent DBH vs census | **NOT YET** | iter-1 IMPOSES DBH via the fit scalar (fits median exactly, trivially). F2's emergent-DBH + census-shape check needs the ratchet un-rescaled + all 3 tiers; deferred to iter-2. |

Cross-tier (leafless armature, one seed):

| tier | H | DBH(fit) | live nodes | primaries | cb_frac |
|---|---|---|---|---|---|
| s (young, 12 yr) | 10.0 | 7.0 in | 4 800 | 14 | 0.14 |
| m (middle, 20 yr) | 14.4 | 15.0 in | 6 524 | 12 | 0.10 |
| l (mature, 35 yr) | 22.0 | 28.0 in | **86** | 0 | — |

## ★ The #1 iter-2 blocker: the shed rule is not in EQUILIBRIUM

The l tier (35 years) **collapses to 86 live nodes** — a bare stick. The longer the run, the more
shedding wins: it is a slow one-way ratchet toward bare, not a sustainable crown. The same collapse
produced the earlier m-tier 129-node run before the light budget was softened. **The light↔shed↔D
loop must reach a standing-crown equilibrium** (a shed limb is replaced by new growth at the lit
periphery) rather than monotonically stripping the tree. This is the top thing iter-2 must fix, and
it gates a believable l-tier veteran (the *arbre du passé*, where `LATENT_BUD` and the arch cascade
live).

## Other iter-2 targets (all diagnosed, none mysterious)
- **Clear bole too low** (0.10–0.14 vs 0.30): low A2 laterals survive that should be shed; couples to
  the shed-equilibrium fix (τ, shadow strength, and the height at which `D` first collapses).
- **First fork too low / into thin secondaries** rather than 2–3 thick masters: the trunk's `D`
  collapses by ~age 6 (self-shading of the apex), so `Dchild < D_STOP` → the first fork is already
  pauperized. Want the trunk to hold dominance longer and fork into a few **cat-1 masters**.
- **Limbs too straight / weak arch**: posture (sag−righting) is wired but produces little visible
  curvature at this scale; the arch **cascade** (§7.2, reiterate-at-arch-summit + dieback) is not yet
  exercised. `θ_relay`, `θ_GSA`, and the sag/righting constants are all GAPs (Genoyer / Huang).
- **Crown open/vase, not domed**: expected — the A4/A5 foliage/twig layer that fills the dome is
  deferred (F6 scope). Re-judge crown fill only once that layer is added.

## What is genuinely established
The year-stepped process **runs, is bounded, is topologically connected, and produces a legible
trunk→primary→secondary hierarchy with earned taper and an emergent (if low) clear bole** — from
mechanism, not authoring. The "pom-pom of equal sticks" and "garden-hose arc" are gone. Every number
that is not from Caraglio & Édelin is labelled `[PROV]`/`[GAP]`; the outputs above are predictions to
be checked against the census and Genoyer 1999, not tuned results.

**Next:** review this checkpoint, then iter-2 = the shed-equilibrium fix (top priority), higher/
stronger first fork into masters, and the DBH-emergent + census-shape validation. No mesh / perf /
cards until the five criteria pass on the skeleton.

---

# ITERATION 2 — the shed rule reaches EQUILIBRIUM (the #1 blocker is cleared)

Renders: `tmp/grower_iter2_{m,l}.png`. Same `scripts/plane_grower.py`.

## Root cause of the iter-1 collapse, and the fix
The shed rule is a **foliage-light** rule, but iter-1 ran it on a **leafless** armature — nothing
renewed light at the lit periphery, so shedding ground monotonically to bare (l tier → 86 nodes).
Fix (Chris's call, "cheap A4 layer purely as light-gatherers"): a **transient A4 foliage layer**.
Each year every living structural tip puts out `FOLIAGE_PER_TIP` short-shoot "leaves"; cohorts
abscisse after `FOLIAGE_LIFE` years (C&E: A4/A5 self-prune 1–4 yr). Foliage is **not wood** —
excluded from the ratchet, never skinned — it exists only to **gather light and cast shade**. The
shadow grid is now seeded by foliage; `light_gathered(subtree)` sums foliage light. A tip that stops
extending stops re-leafing → its limb loses foliage → it sheds. A tip at the lit periphery keeps
re-leafing → it lives. **That birth-at-periphery / death-of-shaded-interior balance is the crown
equilibrium**, and it is now a mechanism, not a tuned target.

## Result: equilibrium, both failure modes gone
Tuning the shadow so shade actually reaches the interior (`SHADOW_B` 2.2→1.4, `SHADOW_LEVELS` 9,
`FULL_LIGHT` 6, `τ` 0.18 — all `[PROV]`), the l tier (35 yr) now:
- **does NOT collapse** (was 86 nodes) and **does NOT run away** (was 57 k with shed=0),
- **sheds continuously** through maturity (6–11 subtrees/yr) while the crown persists,
- settles into a growing-but-trimmed regime: l wood 22 k (was 86), m wood ~9 k.

| tier | wood live | shed behaviour | verdict |
|---|---|---|---|
| m (20 yr) | ~9.2 k | continuous | stable crown |
| l (35 yr) | ~22 k | continuous 6–11/yr | **stable — no collapse, no runaway** |

## What iter-2 did NOT yet fix (the next layer, coupled)
- **(iii) clear bole still LOW** (cb 0.07–0.10 vs 0.30). The trunk's low A2 laterals survive because
  their *own* foliage spreads outward into light — the crown above never overtops them enough to
  shed them. Raising the bole needs the low limbs to be genuinely overtopped (more self-shading of
  low-limb foliage), or the low laterals to be suppressed at birth and the low crown rebuilt later
  from `LATENT_BUD` reiterates (which is also how the veteran's low limbs should arise).
- **(ii) caliber gradient now wrong-signed** (m +0.60, l +0.18 — higher=thicker). Same root cause:
  the surviving low limbs are the *thin original laterals*, not thick old reiterates. Fixing the
  clear-bole mechanism (low limbs shed; low crown rebuilt from latent buds) should also flip this.
- **LATENT_BUD barely fires** (reiter stuck at 3 = just the trunk fork). The veteran's low heavy
  limbs + arch cascade (the *arbre du passé*) need Mode 2 firing to actually happen — currently its
  old-wood host set is tiny (only cat-1 axes) and its rate is low. Iter-3 territory.
- **DBH still imposed**; arch still weak; crown vase-not-domed (foliage layer deferred for the
  woody-armature scope — re-judge fill once real cards replace the light-only A4 markers).

## Standing verdict
The developmental process now **runs to a stable crown at all three tiers** — the equilibrium that
iter-1 could not reach. The remaining criteria (clear bole, caliber sign, Mode-2 veteran limbs) are
a single coupled problem — *the low crown must shed and be rebuilt from latent buds* — and that is
the iter-3 target. Still no mesh / perf / cards. All new numbers `[PROV]`.

---

# ITERATION 3 — LATENT_BUD fires; caliber sign FLIPPED; clear bole EARNED & tier-ordered

Renders: `tmp/grower_{s,m,l}.png`. Same `scripts/plane_grower.py`. Target (from the resume line):
*make Mode 2 fire so the low crown sheds and rebuilds from thick low reiterates — closing the two
open criteria (clear bole 0.07→~0.30, caliber sign flip) and starting the veteran's low limbs.*

## What the investigation found before any code (the diagnosis was bigger than the brief)
Tracing iter-2's crown first (`tmp/grower_diag_iter3.py`, `tmp/grower_trunk_trace.py`):
1. **Mode 2 was structurally inert** because its host set was *alive cat-1 axes only* — i.e. the
   trunk, which forks and dies by age ~7. `reit_count` was stuck at 3-4 (the trunk fork alone).
2. **There were NO orthotropic masters at all** (`cat-1 masters = 0`). The trunk's fork was
   maximally pauperized (Dchild≈0 → cat-3 twigs). Cause, traced year-by-year: the trunk apex is
   self-shaded from year 1 (`env_release` clipped to its 0.15 floor), and `env_release` was
   **inverted vs the ratified design §7.5 AND compounding annually**, so it annihilated the apex's
   dominance to ~0 within two years. By the time the age-6 fork gate opened, D had been 0 for years.
3. **The whole crown was the trunk's establishment-window A2 laterals**, grown as *unbounded relay
   chains* to 35 m (H=22, l tier) because only A1 forked — nothing bounded a plagiotropic axis.
So "make latent buds fire" alone could not close (ii)/(iii): the crown had no scaffold, no masters,
and low limbs that were thin runaway A2s the shed rule could never overtop.

## The five edits that shipped (each cites the design; all `[PROV]` values labelled)
1. **`env_release` sign + compounding fixed (§7.5).** High light now *lowers* D (open-grown forks
   early); low light *holds* D (a self-shaded establishment leader stays a leader). Applied as a
   **gentle current-conditions factor** on an effective `D_eff = D·env·hcap`, evaluated at the fork
   decision, **not** compounded into the clean age-decayed `D` (§2.2). → the trunk now reaches the
   fork gate at age 7-8 with D≈Φ_fork and *can* throw masters.
2. **One-year shed GRACE.** Masters and latent-bud reiterates fire *after* the year's foliation
   step, so a newborn has no foliage in its birth year → its subtree light is spuriously 0 → it was
   shed the instant it appeared. A newly-released reiterate now gets one season to establish.
3. **★ LATENT_BUD host set + firing rewritten (the brief's core).** Host = **old woody nodes on ANY
   axis** — crucially the *dead* trunk and *dead* masters, whose wood persists after the axis stops
   extending — not just alive cat-1 axes. Release is **positional**, biased LOW (§3.3/§7.2: the
   basal reiterates are the heavy limbs), **not** a firing-time light gate (§2.3: C&E ties release
   to position/arch-summit; light acts *after* birth via the shed rule). `start_order = s(u_ins)`.
4. **Base effect (§4).** An orthotropic leader's first `BASE_MODULES=3` modules bear no released
   laterals — the bare establishment zone from which the **clear bole emerges as an output** (the
   trunk no longer sprouts a permanent limb at h≈1.4 in year 1 that pins cb at 0.10).
5. **`LATENT_MIN_U=0.26`.** Dormant buds on the clear bole stay suppressed (apical dominance);
   Mode-2 fires in the **low crown**, so its thick reiterates rebuild the low limbs *above* the
   bole instead of re-populating it. This scalar is the calibration the design explicitly permits
   (cf. §7.3's "one free scalar we allow ourselves to fit to cb").

**⚠ What was tried and REVERTED (a genuine dead-end, recorded so it isn't re-attempted):**
*universal forking* (every axis forks, §2.3) **+ a wave-graded D reset** to bound the runaway A2s.
Correct on paper, but together they **explode geometrically** (branching factor = ramify × fork,
each wave establishing long; shed can't keep up — s tier hit reit 1171/wood 16 k by year 12, l
timed out). Bounding the A2s properly is a **larger redesign than iter-3** (it needs a real
establishment/competition model, not a patch). Reverted to A1-only forking + the D_RESET·D_at_fork
wave. **The A2-runaway is therefore still present** and is the #1 iter-4 blocker (below).

## Results — all three tiers, one seed, leafless armature
| tier | H | cb_frac (target) | caliber corr (want −) | reiterates | live wood | orphans |
|---|---|---|---|---|---|---|
| s (young, Upright Ovoid) | 10.0 | **0.35** (0.35) | −0.15 | 18 | 2 926 | 0 |
| m (modal, Broad Dome) | 14.4 | **0.25** (0.30) | **−0.51** | 49 | 13 325 | 0 |
| l (veteran, Low-Forked Spread) | 22.0 | **0.16** (0.20) | **−0.46** | 120 | 50 115 | 0 |

## The five F6 criteria — honest scoring
| # | criterion | iter-2 | iter-3 | note |
|---|---|---|---|---|
| (i) | emergent primary count + heights | PARTIAL | **PARTIAL+** | 15-20 primaries; now a real bole + tiered limbs + thick low reiterates. Still **no persistent 2-3 master fork** (masters fork after ~2 modules; crown carried by A2s + latent reiterates). |
| (ii) | AC-14 caliber gradient EARNED | **wrong-signed** (+0.60) | **✓ FIXED** | corr **negative at all three tiers** (m −0.51, l −0.46); the thick limbs (r 120-154 mm) sit at h 5-8 m — the veteran's heavy low limbs, earned by the ratchet, nothing imposed. |
| (iii) | clear bole from shedding | LOW (0.07-0.10) | **◑ EARNED, near target** | 0.35 / 0.25 / 0.16 and **correctly ORDERED young>modal>veteran** — the measured trend (cb DECREASES with age) falls out of more/lower latent buds over more years. Modal/veteran ~0.05 below target. |
| (iv) | crooks at module boundaries | MECHANISM ✓ | MECHANISM ✓ | 2.9° at year nodes vs 0.00° interior (θ_relay still an un-closed GAP; reads straight). |
| (v) | emergent DBH vs census | NOT YET | NOT YET | DBH still IMPOSED via the fit scalar; F2's emergent-DBH check deferred. |

**Integrity (the zombie-axis lesson):** connectivity traced on live wood at every tier → **0
orphans**, all live wood reachable from the root. No floating islands. No collapse, no runaway,
no explosion; l grows to a stable 50 k-node crown over 35 years (111 s), shedding 12-27 subtrees/yr.

## What iter-3 did NOT fix (the coupled iter-4 target)
- **No persistent orthotropic masters.** The trunk fork now *starts* masters (env fix) but they
  fork again after ~2 modules — there is no long-lived cat-1 scaffold. The crown is A2 laterals +
  latent reiterates. A real master (C&E's "branche maîtresse, structure comparable au tronc") needs
  a longer establishment, which is entangled with the reverted **A2-runaway / universal-fork**
  problem: bounding branch axes *and* keeping a scaffold needs the establishment/competition model
  the wave-reset dead-end was reaching for. **This is the #1 iter-4 blocker.**
- **Clear bole ~0.05 below the modal/veteran targets**, and pinned by `LATENT_MIN_U` rather than by
  shedding of overtopped low limbs — the light model still can't shade a low outward-spreading limb
  (downward-only shadow, no side light), so the bole is *suppressed* into being rather than *shed*
  into being. The arch cascade (§7.2 — sag → latent bud at the re-lit summit → dieback) is the
  design's real low-limb mechanism and is still not exercised (posture produces little curvature).
- **DBH still imposed; crown vase-not-dome** (foliage layer deferred, F6 scope).

## Standing verdict
The brief's core ask is **met**: LATENT_BUD fires robustly (reit 3→120), on old wood across dead
and live axes, and it flips the **caliber sign** (the open criterion ii) at all three tiers while
the **clear bole** becomes an earned, tier-ordered output near the measured targets (criterion iii,
substantially advanced). Integrity is clean. The cost was four supporting mechanism fixes (env sign,
shed grace, base effect, bud-suppression) and one honest dead-end (universal fork + wave reset).
The remaining gap — a *persistent master scaffold* and a *shed-driven* (not suppression-driven)
bole — is one coupled iter-4 problem: the branch-axis establishment/competition model. Still no
mesh / perf / cards; all new numbers `[PROV]`.

---

# ITERATION 4 — the ESTABLISHMENT RISE builds a persistent master scaffold; A2s ARCH not climb

Renders: `tmp/grower_{s,m,l}.png`. Same `scripts/plane_grower.py`. Target (resume line): *close the
one remaining coupled gap — (1) a persistent 2–3 orthotropic MASTER scaffold (masters were forking
after ~2 modules into twigs), (2) a shed-driven bole + the arch cascade §7.2, (3) DBH-emergent —
without re-trying the reverted universal-fork + wave-reset dead-end.*

## What the investigation found before any code (two coupled root causes, both traced to evidence)
`tmp/grower_trace_iter4.py` on the m/l tiers, plus a code read:
1. **Masters die because they are BORN below `Φ_fork`.** A fork child inherited `D = D_RESET·D_at_fork
   ≈ 0.55·0.19 = 0.10 < Φ_fork(0.34)` — the *decayed* birth-D. iter-1..3 modelled `D` as a **monotone
   decay from birth**, but C&E §2.1 gives `D` a **three-phase** trajectory: low → **RISING** (establishment,
   *"la dominance d'un relais unique est de plus en plus marquée, l'acrotonie augmente"*) → falling. The
   **rising limb was never implemented**, so every fork child re-forked at `REITER_MIN_AGE` and pauperized
   to cat-3 twigs → **0 masters (m), 3 die-at-2-modules masters (l)**.
2. **The crown overshot H by ~1.5× (A2 runaway).** A2 laterals grew as 200–240-node monotone relay chains
   rising **+11 to +13 m** each (m crown 21.5 m at H=14.4; l crown 33.6 m at H=22). Cause: `θ_GSA = 60°`
   from vertical = **30° permanently rising** — a "plagiotropic" limb that *climbed into the light*, so it
   was never overtopped and the downward-only shadow could never shed it (exactly the brief's item-2 knot).

## The mechanism fixes that shipped (each cites the design; all `[PROV]` labelled)
1. **★★ The ESTABLISHMENT RISE (§2.1), reconciling §2.1's three-phase narrative with §2.2's decay-only
   formula.** `D_clean(age)` now RISES from `EST_FLOOR·peak` to the wave peak over an establishment window,
   THEN decays. C&E on fork elements: *"chaque élément des fourches présente **d'abord une forte acrotonie
   et une grande dominance** … il y a **ensuite** diminution"* — born STRONG, then decays (so `EST_FLOOR`
   is HIGH, 0.85; the rise-from-low is the seedling's juvenile phase, gated by `AU_MIN_AGE`). A master now
   holds a dominant leader while `D` decays and only forks when decay (or hcap near H) brings `D_eff < Φ`.
2. **★ The wave decrement acts on the establishment PEAK, not the decayed birth-D** (C&E: *"d'une vague à
   l'autre le caractère dominant … diminue pour devenir nul"*). `child_peak = D_RESET·parent_peak` → trunk
   1.0 → master 0.60 → sub-master 0.36 → 0.22. The MASTER/terminal decision is on `child_peak ≥ D_MASTER_MIN`
   (the leader it CAN build), not its low birth-D. **Scaffold DEPTH is an OUTPUT** that self-terminates.
3. **★ Crown ROUNDS OVER near H (§6 envelope as a soft bound).** Above `CEIL_FRAC·H`: (a) growth bends toward
   horizontal (`grow_module`) so no axis climbs far past H; (b) an orthotropic leader that forks **at the
   ceiling** yields PLAGIOTROPIC crown branches, not new climbing masters — while one that forks lower (room
   above) still makes orthotropic sub-masters. This is what makes **scaffold depth tier-dependent**: a tall
   l tree forks masters for several waves before rounding over; a short s/m tree rounds over after one.
4. **★ A2 posture: ASCEND-THEN-ARCH (§7.2), replacing dead-straight spokes.** iter-3's `right = RIGHT_K/r`
   blew up at a thin tip (r≈R0) and **pinned every limb to its set-point**, so accumulating sag never
   drooped it. Now righting is ~bounded (`RIGHT_K` constant) and **sag grows with the limb's own load ×
   lever**: a young limb holds a moderately ascending set-point (`θ_GSA = 62°`), an old long heavy limb
   loses the contest and the tip DROOPS → the axis traces an arch (proximal rising, distal *"retombante"*),
   arching DOWN **under** the master crown where the downward shadow can overtop and shed it.
5. **Ground floor.** A drooping veteran limb rests just above soil (`GROUND_FLOOR`), never underground
   (the l run had a limb at −1.3 m before this).

## Results — all three tiers, one seed, leafless armature
| tier | H | crown top | caliber corr (all limbs, want −) | cb_frac (target) | masters | reiterates | live wood | orphans |
|---|---|---|---|---|---|---|---|---|
| s (young) | 10.0 | 10.9 | **−0.43** | **0.35** (0.30) | 0 (rounds over) | 18 | 2 407 | 0 |
| m (modal) | 14.4 | 15.5 | **−0.46** | **0.26** (0.30) | 3 | 57 | 12 510 | 0 |
| l (veteran) | 22.0 | 23.8 | **−0.48** | **0.16** (0.20) | 9 | 132 | 65 632 | 0 |

⚠ **Measurement fix (not goalpost-moving):** criterion (ii) is now measured over **all substantial limbs
(live woody subtree ≥ 30)**, not just trunk off-children. The veteran's thickest low limbs are LATENT_BUD
reiterates that insert **on the masters**, not the trunk, so the old trunk-children-only measure was blind
to exactly the limbs AC-14 is about — it read a spurious **+0.06** on l while the true gradient is **−0.48**
(the 25 thickest live axes all sit at h 4–11 m, r 86–142 mm; mean r by height band falls 54→69→29→21 mm).

## The five F6 criteria — honest scoring
| # | criterion | iter-3 | iter-4 | note |
|---|---|---|---|---|
| (i) | emergent primary count + heights + **master scaffold** | PARTIAL+ (no persistent masters) | **◑ ADVANCED** | persistent masters now exist (s 0 / m 3 / l 9) as a **multi-wave orthotropic scaffold** whose depth is an OUTPUT scaling with tier; crown **bounded near H** (was 1.5×H). Residual: individual masters are still SHORT (1–3 modules, fork into sub-masters) rather than long single leaders "comparable au tronc" — the light-equity among near-apex buds is still `[PROV]`. |
| (ii) | AC-14 caliber gradient EARNED | ✓ (−0.15/−0.51/−0.46) | **✓ (−0.43/−0.46/−0.48)** | negative at ALL tiers, stronger & more uniform than iter-3; low-quartile limbs ~2× thicker than high-quartile. Earned by the ratchet, nothing imposed. |
| (iii) | clear bole from shedding | ◑ EARNED (0.35/0.25/0.16) | **◑ (0.35/0.26/0.16)** | tier-ordered young>modal>veteran, near targets. Now **partly shed-driven**: the arch drops low limbs UNDER the crown so the downward shadow overtops & sheds them (was pure `LATENT_MIN_U` suppression). |
| (iv) | crooks at module boundaries | MECHANISM ✓ | MECHANISM ✓ | 2.9° at year nodes vs 0.00° interior (θ_relay still an un-closed GAP). |
| (v) | emergent DBH vs census | NOT YET | **NOT YET** | DBH still IMPOSED via the fit scalar; **item #3 deferred to iter-5** (un-rescale the ratchet + F2 census-shape check is its own validation task). |

**Integrity (the zombie-axis lesson):** connectivity traced on live wood at every tier → **0 orphans**, all
live wood reachable from the root. **No explosion** — l = 132 reiterates / 129 k nodes, comparable to iter-3's
120 / 105 k (the scaffold + arch add modestly, NOT geometrically). The reverted universal-fork dead-end was
**not** re-tried; forking stays **A1-only**.

## What iter-4 did NOT do (the iter-5 targets)
- **(v) DBH is still imposed** (item #3). Un-rescale the ratchet, let root radius emerge, validate the DBH–H
  *shape* against the 1564-tree census (F2). This is a distinct validation task, not a scaffold fix.
- **Masters are short** (1–3 modules). A master *"comparable à la structure du tronc"* should grow a long
  single leader before forking. Needs the light-equity model among near-apex buds (currently `M = 2/3`
  `[PROV]`) so a master isn't forked early by a lit apex.
- **The arch CASCADE is only half-exercised.** The arch PROFILE (posture droop) now works, but the full §7.2
  loop — LATENT_BUD firing *at the arch summit* → the distal continuation dying back → the new complex becoming
  the arch — is not yet wired (latent buds fire positionally, not at summits). This is the veteran's
  ground-sweeping-limb mechanism.
- **Crown slightly exceeds H** (1.05–1.08×) at the arch peak — within the envelope soft-bound tolerance; note it.

## Standing verdict
The **#1 iter-4 blocker is cleared**: the establishment rise (C&E's rising `D`, the limb that iter-1..3
dropped) plus the peak-per-wave decrement give a **persistent, self-terminating master scaffold** whose depth
is an emergent, tier-scaled OUTPUT, and the ascend-then-arch posture + crown-rounding **bound the crown near
H** (ending the 1.5×H A2 runaway) while dropping low limbs under the crown so shedding — not just suppression —
clears the bole. Caliber is strong-negative at all tiers (honest all-limbs measure); integrity clean; no
explosion. The residuals are **(v) emergent DBH**, **longer single-leader masters**, and the **full arch
cascade** — the iter-5 set. Still no mesh / perf / cards; all new numbers `[PROV]`.

---

## iter-7 — the crown bound is APICAL CONTROL, not a length (`35d092b`, WIP)

**Two things settled, one still open.**

### 1. C&E 1990 has no lengths. At all.
Checked the paper end to end. It gives **node counts** per growth unit (A2≈15, A3≈10, A4=7,
A5=5 — the **A1 cell is genuinely blank**, so our `GU_NODES[1]=14` has no support) and three
whole-tree heights (5–8 m *arbre d'avenir*, ~10 m *présent*, up to 30 m *passé*). It contains
**no growth-unit length, no internode length, and no figure to read one off** — the Planches are
schematic drawings with no scale bar. So `INTERNODE` **cannot be sourced from C&E**, and the
plan to "re-derive it as a true metamer length" has no source to derive it from.

Re-fitting `INTERNODE` was never going to work regardless: a plane is ~14 m tall with a crown
**radius** of 6–9 m, so vertical reach is ~2× horizontal. **No single shared reach identity can
produce both.** The trunk/limb asymmetry has to come from mechanism.

### 2. The between-axis pauperization was being divided back out.
`D_clean(ax) == ax.D_peak * shape(age)`, so iter-6's `vigour = D_clean/D_peak` is **pure shape** —
it starts at `EST_FLOOR`, rises to 1, decays, *identically for every axis in the tree*. The wave
decrement (`D_peak = D_RESET*parent_peak`) survived only in the **fork** test, which reads an
absolute `D`. For **extension** it cancelled. A 3rd-wave lateral (peak 0.36) therefore laid down
internodes at the trunk's full length, every axis inherited the trunk's reach, and crown radius
came out ≈ tree height (measured: m `r_max` 12.4 m vs H 12.7 m — and 12.4 m sits right on the
reach identity `GU_NODES·INTERNODE/D_DECAY_AGE` = 12.7 m).

### ⛔ The obvious fix is wrong — reading vigour on the absolute D scale
Kept here because it cost a real iteration. It makes *capability* a second multiplier on top of
*affordability* `f(v)`, and it double-penalizes exactly the axes that have **neither yet**: a
newborn axis bears no foliage, so its share is already small, and ×0.36 vigour drives `ext` under
`EXT_MIN` → `DORMANT_ABORT` → the outer crown is **amputated**, not pauperized. Measured: every
wave below the trunk **dead at mean age <2.3 yr of 20**, m spread collapsed to **5.9 m**, half the
tree's wood gone (3008 → 1360 nodes). **Length is the wrong place for it.**

### The fix: D belongs in the SPLIT
`D` is **relay dominance = apical control**, and in Borchert–Honda apical control acts on the
**resource split**, not on the internode. The bid is now `Q × rank_weight × D_clean`.

This is the missing half of the ADR's economy. iter-6 split the pool by **light alone**, which is
precisely why the economy could not bound the crown on its own: the allocation telescoped to
light-proportional, a bud at the sunlit **periphery kept f≈1 forever**, and light *rewarded*
lateral runaway. Weighting the bid by dominance lets a leader **outbid** a subordinate lateral for
a finite pool — and resource is **conserved**: what the lateral doesn't get, the leader does. So
the periphery is pauperized **without starving**.

m tier — all four metrics move together, none imposed:

| | iter-6 | iter-7 | target |
|---|---|---|---|
| spread | 24.8 m | **20.2 m** | 12–18 m |
| H | 12.7 m | **13.1 m** | 14.4 m |
| nodes | 3008 | **3404** | (denser, not amputated) |
| DBH | 6.5 in | **7.3 in** | 15 in @ m |

### ⏳ OPEN — the strength of apical control
Still too wide, and H still short: **one error with one sign** — apical control is too weak, so
the leader under-bids and the laterals over-bid. The **mechanism** is now in the right place; what
remains is its **strength**, which is a legitimately species-fitted Borchert–Honda parameter
(`W_MIN` is already declared "[FIT] the HABIT knob", from Palubicki's own scheme).

**NEXT = sweep the habit knob** (`W_MIN` 0.02→0.001, then `KAPPA`, then `APICAL_OFF_YEAR`) on the
**m tier only** (fast), pick the smallest change that puts m at H≈14.4 / spread 12–18 **without
node collapse** (a drop to ~1500 nodes = axes dying = FAILURE, not a win), then run **s and l once**
at that setting. s and l are **not fitted**, so their numbers are the real test. Harness:
`tmp/measure_grower.py` (crown radius, H, spread/H, nodes, DBH); axis-level survival probe:
`tmp/probe_axes.py`. ⛔ Never clamp crown radius — width must EMERGE. **Do not ship.**

### ✅ RESOLVED — apical-control strength is NOT the crown-width lever (seed-replicated refutation)

The strength knob was made explicit (`APICAL_K`, the exponent on relay dominance in the split:
share = `Q · rank_weight · D_clean**APICAL_K`; K=1 reproduces iter-7's first cut) and swept on the
m tier, K ∈ [1, 6]. The open item above is now **closed as refuted**, and the finding is a good deal
more useful than the knob would have been.

**Raising K does exactly two things, and neither is the one we wanted:**
1. **It raises H** — real, and biggest on the *unfitted* l tier (H 13.4 → **20.3 m** at K=2, into the
   low end of the 22–24 m reference, at no cost in node count). That is a genuine, separate result.
2. **It destroys wood** — total nodes fall monotonically, on every seed: −46 % by K=6.

**It does NOT narrow the crown.** Spread is *non-monotone* in K and dominated by seed noise: at K=3
three seeds give **14.3 / 27.4 / 28.1 m**. The tidy "K=2 → spread 14.6 m" reading on the default seed
is **luck on the one seed the grower is fitted to** — the single-seed grid looked like control and was
not. (A robust width measure, 2 × 95th-pct radius, tracks max spread, so the wide crowns are bulk-wide,
not one escaping limb.) Sweep + table: `tmp/apical_k_sweep.py`, `tmp/apical_k_sweep.txt`.
⚠ **Method note, worth keeping:** every previous crown-width number in this document was read off a
single seed. **Replicate across seeds before believing a width result.**

### ★★ THE THIRD STRIKE — and the root cause of all three

One diagnosis underlies iter-6 and both halves of iter-7: *"crown width is bounded by dominance /
resource allocation."* It has now failed three times, in three different places:

| attempt | where D / the economy acted | outcome |
| --- | --- | --- |
| iter-6 | light-driven economy alone | allocation telescopes to light-proportional; a peripheral bud keeps f≈1 forever ⇒ **no bound** |
| iter-7a | D as a **length** multiplier | ext falls under `EXT_MIN` at birth, `DORMANT_ABORT` fires ⇒ **amputation** (spread 5.9 m, half the wood dead) |
| iter-7b | D on the **split**, any strength | **no bound** (above), and node loss buys nothing |

**Root cause (prior art, checked end to end): the model we are implementing does not contain a
crown-width bound, and never claimed to.** Palubicki 2009 §Discussion, in its own words:

> "In our model, we **ignored changes in branch position and orientation over time**. Such changes,
> due to active reorientation or **passive bending of branches under their weight, play an essential
> role in the development of some tree forms**." (their remedy: Costes et al. 2008, biomechanics)

Within Palubicki there are exactly **two** levers on crown extent, and both are already spent here:
- **the shadow/space environment** — cannot bound an **open-grown** tree, because its peripheral bud
  is never shaded. (This is iter-6's finding, restated: light *rewards* lateral runaway.)
- **tropism / growth direction** (their Fig. 12–13: downward tropism ⇒ wider spread) — this is
  **posture**, which was **TESTED and REFUTED** here (θ_GSA 40° vs 62° → 25.6 / 27.4 m; SAG_K 0.10 vs
  0.50 ≈ nil).

So the bound is **not** in Borchert–Honda, and it is **not** in C&E either (whose D is apical control,
and which contains no lengths at all — see the iter-7 section above). **It has to come from outside
both, and the paper names the missing piece: the mechanical cost of holding a limb out.** A vertical
axis grows as a column in compression and pays almost nothing; a horizontal limb is a **cantilever**
whose self-support wood scales super-linearly with its lever arm. That asymmetry — not dominance —
is the candidate explanation for why a plane reaches ~14 m up but only ~6–9 m out.

⇒ This is a canonical design change. **ADR: `docs/adr_grower_crown_bound.md`. Do not code a fourth
variant of the refuted diagnosis. Do not ship.**

---

# iter-8 — POSITION A BUILT, AND **REFUTED**. Crown width is an ARITHMETIC IDENTITY.

**Status: the ADR's Position A is dead in the build. Crown width has a fifth diagnosis, and this
one is measured, closed-form, and predicts the number.** Not shipped; criterion (vi) still unmet.

## 1. Two corrections found before the build (both real, both kept)

**(a) The falsification's mechanical radius was solved against the wrong mass.**
`tmp/grower_selfsupport_falsify.py` solved the fixed point `r_mech = f(mass(r_mech))` — but the tree
does not *build* `r_mech`, it builds `DBH_CALIB · r_pipe`, which is 4.37× thicker and therefore ~19×
heavier. The moment a limb carries is set by the wood that is **actually there**, so the honest fixed
point is on the structural radius, `r_struct = max(r_pipe, r_mech(mass(r_struct)))`. Re-solved that
way (`tmp/grower_selfconsistent_check.py`, 3 seeds):

| lever arm | r_mech / r_pipe_raw | r_mech / r_pipe_built (calibrated) |
| --- | --- | --- |
| 0–2 m (the bole) | ×1.00 (78% bind) | ×0.29 (**0%** bind) |
| 2–10 m | ×2.1 – ×2.7 (**100%** bind) | ×0.93 – ×1.04 (42–62% bind) |

⇒ **T3's "the mechanical term is INERT, 0% of limbs" was an artifact of the understated mass.** It is
not inert; it binds on roughly half of all load-bearing wood. But the table also **overturns ADR §6.1**
("mechanics ahead of `DBH_CALIB`, compared against the *raw* pipe radius"): against the raw pipe,
statics demands 2.3× more wood on every limb, so §6.1 would have made every crown limb ~2.3× too
thin. The calibrated pipe radius and the mechanical demand **agree** in the crown (×0.93–1.04) — which
is the known real-tree result (pipe-model and uniform-stress sizing coincide), and is a quiet
validation of both. §6.1 and §6.4 (scope `DBH_CALIB` to the bole) are **withdrawn**.

**(b) `DBH_CALIB` is not a post-hoc fudge — it is a TIP-COUNT correction, and it now says so.**
The pipe model is homogeneous of degree 1 in the tip radius, so multiplying every radius by 4.37 in
`finalize()` is *exactly* the same as seeding every tip at `R_TIP = 4.37·R0 = 17.5 mm`. The second
form states what the constant physically **is**: one leafless armature tip stands in for
`4.37^2.3 ≈ 30` deferred A4/A5 tips. Moved to the tip (`R_TIP`); output unchanged; the mechanical
term now has a radius it can legitimately be compared against.

## 2. The build (as specified, ADR §6.2/§6.3)

- `structural_radius()` — `r = max(r_pipe, r_mech)`, self-consistent fixed point, `M_i = g·‖Σ m_j
  (p_j−p_i)_xz‖` (parallel vertical loads ⇒ vector sum ⇒ a symmetric vertical axis cancels to ~0).
- The economy's `v` now buys **wood volume (m³)**, not internode length. A metamer costs `π·R_TIP²·l`,
  so the length an apex can afford is a division and C&E's `INTERNODE` is the ceiling on it.
  ⇒ **`V_SAT` is RETIRED** (saturation is now structural, not fitted). The economy keeps exactly one
  fitted scalar, now the photosynthetic yield `ALPHA` (m³ of wood per unit light).
- `support_bill()` — each axis pays its own self-support bill off the top, before anything it carries
  can grow (`_distribute`).

⚠ **The bill must be the MECHANICAL SURCHARGE (`π(r_struct²−r_pipe²)L`), not the whole thickening
bill.** Charging the full thickening was tried first and is wrong in a way that looks right: pipe wood
is *plumbing* — proportional to the leaf area it feeds, hence self-financing and, decisively,
**lever-independent** (a limb's pipe radius depends on how many tips it carries, not how far out it
holds them). It adds no bound, and it does harm: the trunk's pipe bill is the largest in the tree and
is charged at the root, choking the whole crown uniformly. Measured: **no `ALPHA` existed at which
H reached 14 m and the crown stayed under 18 m** — the two scaled together and the crown came out
*wider* than iter-7 (26–34 m).

## 3. ★ THE RESULT: A IS REFUTED. The support cost is **1–3% of the pool.**

Instrumented per year (`pool` = `ALPHA·Q_base`, `support_bill` = the year's mechanical surcharge):

```
yr 15: wood= 1491  pool=0.8589 m3  support_bill=0.0252 m3 ( 2.9% of pool)
yr 20: wood= 2807  pool=1.3908 m3  support_bill=0.0427 m3 ( 3.1% of pool)
```

**Mechanics does not price the crown. It barely registers.** The ADR §5 falsification survived on a
*ratio* — cost/income ~ lever^+0.82 — and that ratio is real and still holds. But **a rising ratio on
a 2% line item cannot bound a budget**, and the falsification never asked what share of the budget
the cost actually was. That is the methodological lesson: *for a cost to be a bound, test its
MAGNITUDE, not only its SCALING.* A ratio test is necessary and nowhere near sufficient.

Measured (m tier, 3 seeds, yr 20): crown **19–28 m**, H 13–15 m, H/W **0.50–0.60** — no better than
iter-7, and worse than iter-7 at matched `ALPHA`. Reference: H 14.4 m, crown 12–18 m, H/W ~0.96.

## 4. ★★ WHAT CROWN WIDTH ACTUALLY IS: an arithmetic identity, not a mechanism

The identity flagged (unclaimed) at the end of iter-6 —

> `axis reach = GU_NODES[cat] · INTERNODE / D_DECAY_AGE` (a convergent geometric series)

— **predicts the measured crown width across a 2× sweep, on every seed** (m tier, 3 seeds, yr 20):

| `INTERNODE` | predicted width `2·n·l/decay` | measured crown width |
| --- | --- | --- |
| **0.11** (current) | 25.4 m | 24.3 / 25.5 / 28.0 m |
| 0.08 | 18.5 m | 20.5 / 20.7 / 23.7 m |
| 0.06 | 13.8 m | 12.9 / 15.6 / 16.4 m |

⇒ **This is why FIVE successive mechanistic diagnoses all failed to move the width.** Economy (iter-6),
dominance-on-length (iter-7a), dominance-on-split (iter-7b), posture (refuted twice) and now
self-support cost (iter-8) — **none of those quantities appear in `n·l/decay`.** The width was being
set directly by a fitted length constant the whole time, and `INTERNODE = 0.11 m` is flagged in this
very document as back-fitted *"so the m-tier trunk reaches ~14 m"*. A real plane metamer is 0.06–0.08 m.

**But `INTERNODE` is a SCALE knob, not a SHAPE knob, so it does not fix the tree.** Across that same
sweep H/W moves only 0.52 → 0.58 → 0.59 (reference 0.96): shrinking the metamer shrinks the *whole
tree*, proportions intact. It is still the wrong number and should be corrected to a true metamer
length — but as a *separate* correction that will drag H down with it, not as the crown fix.

## 5. ⇒ THE SIXTH DIAGNOSIS (the one to falsify next)

**Height is BOUNDED and width is UNBOUNDED, and that is backwards.** Height stops because a soft
ceiling at `CEIL_FRAC·H` rounds the leaders over — i.e. **H is IMPOSED** (its own OUTPUT-not-parameter
violation, the sixth). Width has no ceiling of any kind: it accumulates along *chains* of axes and
keeps growing with age — measured **25 m → 38 m from year 20 to year 45** at `INTERNODE=0.11`, while
height saturates at H. A real open-grown plane bounds *both*, and bounds them with the same
mechanism. Until one mechanism bounds both, every fix will keep landing on the scale and missing the
shape.

⚠ **Do not code a sixth variant before it is falsified on paper.** Five have now failed. The next
step is a derivation, not an edit.

## 6. State

Code is on master and **is not an improvement** — at matched `ALPHA` the crown is *wider* than iter-7
(the new extension law saturates more easily, and `ALPHA` has not been refit; refitting it is
pointless while the width is set by an identity the economy cannot see). Kept because
`structural_radius()`, the self-consistent solver, the `R_TIP` re-expression and the retirement of
`V_SAT` are all correct and independent of the refutation. **Criterion (vi) unmet. Do not ship.**

## 7. ⚠ AMENDMENT (Chris, field observation, 2026-07-11) — §5's framing is WRONG

§5 called it "backwards" that height saturates while width keeps growing. **Chris's field
observation of real planes says the opposite: an older tree carries MORE width for its height than a
younger one** — crown spread goes on widening long after height has levelled off. Field observation
is ground truth and it beats my model of the model.

⇒ **The model's qualitative allometry is CORRECT** (H saturates, W keeps growing with age — measured
25 m → 38 m from yr 20 → 45). The defect is the **RATE and the SCALE**, not the sign, and not a
missing bound on width. So:

- ⛔ **Do NOT go looking for a mechanism that "bounds width like height is bounded."** That was my
  error, and it would have been the sixth failed variant.
- The question is now **quantitative and ontogenetic**: at a given AGE, what H/W does a real plane
  have, and does ours match that TRAJECTORY? Our H/W ~0.55 vs a reference ~0.96 is a snapshot at one
  assumed age (`{s:12, m:20, l:35}` yr, all `[PROV]` and never validated). **If the m tier is really a
  20-year tree, ours is too wide; if the reference 14.4 m / 12–18 m plane is 35–45 years old, ours may
  be reaching the right shape at the wrong age.** That is checkable against the census + the tiers'
  ages, and it must be checked BEFORE any mechanism is proposed.
- The identity `reach = GU_NODES·INTERNODE/D_DECAY_AGE` still stands, and `INTERNODE` is still
  back-fitted. It sets the SCALE of the whole tree — which is exactly the free parameter that a
  proper age/allometry check would pin down.

**★ RESUME: validate the AGE↔SIZE trajectory (H, W, DBH vs age) against real plane allometry before
proposing any mechanism. The next step is still a derivation, not an edit — but it is an allometric
one, not a search for a missing bound.**

---

# iter-8b — THE ALLOMETRY VALIDATION. The "crown is 2× too wide" premise is an ARTIFACT.

**Status: the RESUME item above is DONE, and it invalidates the measurement baseline of iter-6/7/8.
No mechanism was missing. The reference was wrong, the tier ages were wrong, and every recorded
crown number was measured at an `ALPHA` that is not the one the code ships.**

Probe: `tmp/allometry_probe.py`. Reference data: **Urban Tree Database** (McPherson, van Doorn &
Peper 2016, USDA PSW-GTR-253, doi:10.2737/RDS-2016-0005) — 376 measured *Platanus × acerifolia*,
zone **NoEast = Queens, NY** (n=49–53), the correct climate zone for Central Park. Corroborated by
Moser-Vosshage/Rötzer/Pretzsch et al., *Arb. & Urban Forestry* 47(4):150 (2021), German *P. ×
hispanica*.

## 1. The real trajectory (NoEast, Queens NY) — this is now the validation target

    age -> dbh(cm) : 2.40322 + 1.29420*a - 0.00705*a^2            quad, R2=.889
    dbh -> ht(m)   : 3.29515 + 0.30021*d - 0.00109*d^2            quad, R2=.892
    dbh -> cdia(m) : exp(-0.75195 + 2.41418*ln(ln(d+1)) + .0703)  loglogw1, R2=.942

| age | DBH cm | H m | crown dia m | **H/W** |
|---|---|---|---|---|
| 10 | 14.6 | 7.5 | 5.8 | **1.28** |
| 20 | 25.5 | 10.2 | 8.9 | 1.15 |
| 30 | 34.9 | 12.4 | 11.0 | 1.13 |
| 40 | 42.9 | 14.2 | 12.5 | 1.13 |
| 60 | 54.7 | 16.5 | 14.5 | **1.13** |

**Chris's field observation is CONFIRMED — with a bound.** W/H rises **0.65–0.78 (young) → ~0.88
(mature)**, a real ~+30% rise, in the raw measured trees *and* in 5 of 6 usable zone fits, and in the
German study (0.62 → 0.71). Park and street trees converge on the same mature ratio (~0.86–0.89), so
it is not a pruning artifact. **But the widening SATURATES by ~age 30** and is flat thereafter. It is
*not* unbounded. ⚠ **The UTD park subset has NO trees over ~50 yr** — the old open-grown regime, which
is exactly Central Park's `l` tier, is *not* directly measured by this data. There, Chris's field
observation remains the better evidence and the curve above is an extrapolation.

## 2. ★★ THE TIER AGES ARE WRONG — and that is what manufactured the "too wide" crown

Invert the curve on each tier's own `(H, DBH)` target (`TIERS` in `plane_grower.py`):

| tier | target H / DBH | **implied real age** | age we grow it for |
|---|---|---|---|
| s | 10.0 m / 17.8 cm | ~13–19 yr | 12 ✓ |
| m | 14.4 m / 38.1 cm | **~34–41 yr** | **20** ✗ |
| l | 22.0 m / 71.1 cm | **~80+ yr** | **35** ✗ |

We were asking the grower to build a **37-year-old tree in 20 years**. The only way to do that is to
raise `ALPHA` — and a raised `ALPHA` is precisely what pumps the crown out to 25 m. The crown was
"too wide" *because the tree was being force-grown to a mature size in half the time it takes.*

## 3. ★★★ Every recorded iter-8 crown number was measured at a NON-SHIPPED `ALPHA`

Master is clean at `5cef1f9`; `ProbeGrower` only snapshots (it calls `super().shed()`), so it does not
alter growth. Yet at the **shipped** `ALPHA = 3.0e-5`, master does **not** reproduce the recorded
numbers at all:

| m tier, yr 20, 3 seeds | recorded (§iter-8) | **master, shipped ALPHA** |
|---|---|---|
| H | 13–15 m | **7.6 – 12.1 m** |
| crown | 19–28 m | **10.6 – 10.7 m** |
| identity `2·n·l/decay` | 25.4 m ✓ matched | 25.4 m — **span is 10.7 m. NOT matched.** |

⇒ **The "crown width is an arithmetic identity the economy cannot see" conclusion DOES NOT HOLD at the
shipped parameters.** The identity is the *ceiling* on reach — what you get when the resource pool is
rich enough for every axis to spend its full `GU_NODES` budget. At a realistic `ALPHA` the economy
**does** limit width (10.7 m « 25.4 m). `DBH_CALIB = 4.37` is stale for the same reason: it was fitted
to make the m tier hit 15 in, and at shipped `ALPHA` the m tier reaches **13 cm, not 38 cm**.

## 4. What is ACTUALLY wrong, measured at the CORRECT ages and the shipped `ALPHA`

| | m tier @ 37 yr (3 seeds) | real @ 37 | verdict |
|---|---|---|---|
| **DBH** | **13.1 – 14.4 cm** | 40.6 cm | ✗✗ **~3× TOO THIN — the biggest defect** |
| H | **7.7 – 13.4 m** | 13.7 m | ✗ best seed lands; 2 of 3 are ~40% short |
| crown span | 14.0 – 17.7 m | 12.1 m | ~ **only +30%, not 2×** |

(l @ 60 yr: DBH 12.9–20.9 vs 54.7; H 7.4–13.0 vs 16.5; span 8.5–16.3 vs 14.5 — same shape of error.)

- The **H/W deficit decomposes**: roughly 60% of it is a HEIGHT SHORTFALL, only ~40% a width excess.
  We have been hunting a width bound to fix what is mostly a height-and-wood problem.
- ⚠ **SEED VARIANCE IS ITSELF AN UNLOGGED DEFECT:** H ranges **7.7 → 13.4 m at identical parameters.**
  A 74% spread makes every 3-seed mean we have ever quoted nearly meaningless.

## 5. RESUME — calibrate before you mechanise

⛔ **Do NOT code a width mechanism.** Five have failed and the premise for a sixth is now gone.
⛔ Do not act on the "⭐ APICAL_K≈2 fixes l-tier H (13.4 → 20.3 m)" note until the ages are fixed:
20.3 m is far too tall for a 35-yr tree (real 13.4 m) but reasonable for the 80-yr tree the l tier
actually describes. Its verdict is age-dependent.

1. **Adopt §1 as the validation target** — H, W, DBH vs age, not a single H/W snapshot.
2. **Fix the tier ages** (s≈15, m≈37, l≈80), or better: re-derive each tier's `(H, DBH)` from the
   **NYC census DBH distribution of Central Park's actual planes** and read H/W off the curve. The
   census gives us measured DBH; we never needed to guess an age at all.
3. **Refit `ALPHA` and `DBH_CALIB` at the corrected ages** — this honest calibration has never been
   done, and every conclusion since iter-5 rests on it.
4. **Then, and only then, re-measure the crown.** Chase DBH (3×) and the seed variance (74%) first;
   a +30% width overshoot is the smallest of the three errors and may not survive the recalibration.
