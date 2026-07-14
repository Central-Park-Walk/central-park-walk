# LEDGER — cpw / london-plane

Append-only. One entry per unit of work: hypothesis → change → measurement → verdict.

---

## 2026-07-13 — iter-0: bind the thread (harness, not grower)

- **Hypothesis:** the grower's iterate-and-verify loop is the most expensive shape of work there is
  (context grows monotonically, each turn re-reads all of it), and it currently rebuilds its context
  from a 1400-line memory file every session. A thread with a ≤50-line STATE.md snapshot should make
  a `/clear` cheap enough to do every iteration.
- **Change:** bound the session to a new `cpw / london-plane` thread; seeded `STATE.md` from the
  running-state block at the top of `project_london_plane_crown_mould.md`. No grower code touched.
  Commit `5275fc6`.
- **Measurement:** none — this is a process change, not a grower change. Its test is whether iter-12
  can start cold from STATE.md alone without re-reading the memory file. Unverified until iter-12 runs.
- **Verdict: PENDING** (Chris to confirm the thread shape; the real check is the next session's cold start).

---

## 2026-07-13 — iter-0b: the cold start, verified

- **Hypothesis:** iter-0's real test was never "does the file look right" — it was whether a session
  that has *never seen* `project_london_plane_crown_mould.md` can pick the work up from `STATE.md`
  alone. If the snapshot lies or under-carries, a cold session will either ask a question already
  answered, or re-litigate a rail.
- **Change:** none. This session was the test instrument, not a change to the grower.
- **Measurement:** cold start after `/clear`. Three tool calls — bind, registry entry, `STATE.md` +
  ledger tail — reconstructed: the iter-11 refutation of the tip budget, the parameter-free test
  showing the two-sided caliber error survives a perfect tip count (1.36× / 0.87× / 0.68×), all
  three open defects, the six rails, and the iter-12 heartwood hypothesis. **The memory file was
  never opened.** No rail was re-litigated. The snapshot carries the project.
- **Verdict: PENDING** (Chris on the thread shape; the cold start itself is now CONFIRMED).

---
## 2026-07-13 — iter-12: HEARTWOOD = disused pipes (Shinozaki; "Kubo 2022" branch thinning)

> ⚠ **CORRECTION, 2026-07-13 (same day, later).** "**Kubo et al. 2022" IS A FABRICATED CITATION** —
> no such paper. The real one, at the identical *Tree Physiology* 42:2174, is **Aye, Brännström &
> Carlsson 2022**; the branch-thinning theory in it is **Hellström et al. 2018**. It had **never been
> read** when iter-12 and iter-13 were built on it. Now read (`tmp/papers/`). **Both claims below that
> rest on it are FALSE:** (a) "costs NO new constant" — the paper fits **two** pipe-area constants,
> c_S and c_H, separately (its Table 1); (b) the bank unit — it accumulates **lost LEAF UNITS** (Eq. 6),
> each worth c_H **once**, whereas we bank each dead branch's whole **cross-section**, a recursive
> double-count (it already contains its own dead children's sections). *That* is the unbounded
> heartwood. See STATE.md → NEXT. Kept as written below for the record.

- **Hypothesis:** the pipe layer has no heartwood. Shinozaki sizes SAPWOOD by leaf area; the pipes of
  a dead branch are not reabsorbed — they stay in the stem as DISUSED pipes and wall off as
  heartwood. Kubo et al. 2022 (Tree Physiology 42:2174) predicts the whole heartwood profile from
  branch death alone, so the term costs NO new constant. If that is the missing size-dependent term,
  it must thicken `l` (a century of self-pruning) far more than `s` (15 yr, almost nothing shed).
- **Found (the real defect):** `ratchet()` summed only LIVE children into a `radius` array rebuilt
  from zero every year (`run()`), so the §5 "monotone max over history" was a **NO-OP across years**:
  a shed branch's wood *vanished* from its parent's cross-section. The trunk was pure sapwood at
  every age, and dead wood — which cannot dissolve — contributed nothing.
- **Change:** `ratchet()` now sums over ALL woody children — live ones at this year's pipe radius,
  dead ones FROZEN at the radius they carried at death (`self._r_hist`, which also makes the ratchet
  genuinely monotone across years). The sum is exactly conserved across a death: the term moves from
  the live side to the dead side. One function, no new constant.
- **Measurement** (`tmp/grower_calib_measure.py --tiers s m l --seeds 8`), DBH vs census:
      before:  s 1.96x  m 1.00x  l 0.73x   (splay s/l = 2.68x)
      after:   s 3.96x  m 2.49x  l 2.29x   (splay s/l = 1.73x)
      the heartwood MULTIPLIER per tier: 2.02x / 2.49x / 3.14x — **monotone in age.**
  ⇒ the term is REAL and SIZE-DEPENDENT, right sign, and **not a scalar** (that was the falsifier).
  It removes 35% of the two-sided splay. Re-centred on m it would read s 1.59 / m 1.00 / l 0.92 —
  `l` comes home from 0.73 to 0.92; `s` stays thick, which is defect 2 (the R_TIP floor), as predicted.
- **But it overshoots absolute girth ~2.5x**, because `DBH_CALIB` was fitted in a heartwood-free
  world. ⚠ And the implied sapwood fraction is now only 16% (m) / 10% (l) of basal area — **too
  little**: Platanus is noted for WIDE sapwood. Suspect the p=2.3 metric inflates the dead sum
  (summing disused pipes in a non-area metric is not area-conserving). See NEXT.
- **Verdict: PENDING**

---
## 2026-07-13 — iter-13: the disused pipes are AREA, not a taper law — REFUTED (the metric was not the fault)

- **Hypothesis:** iter-12 summed the dead branches in the LIVE metric (`r**2.3`). PIPE_POWER is a
  TAPER law — a statement about how a living, *branching* plumbing system sheds conductive area
  upward. Dead wood is a fossil: it does not branch and does not taper, so its section is conserved
  AREA (p = 2). Predicted: summing it as area would **raise the sapwood fraction** toward Platanus's
  wide-sapwood norm and **shrink the ~2.5x girth overshoot**, before any refit.
- **Change:** `ratchet()` now keeps two banks that never meet in the same metric — `r_sap`
  (Shinozaki, p = 2.3, over LIVE children only, tip seed R_TIP) and `A_dead` (p = 2, conserved).
  A dying branch hands its ENTIRE frozen section (its sapwood plus its own heartwood) to the parent's
  dead bank, once, forever; `pi*r^2 = pi*r_sap^2 + A_dead`. Both banks freeze at death. Still no new
  constant. (`scripts/plane_grower.py`: one function, two arrays.)
- **Measurement** (`tmp/grower_calib_measure.py`, 8 seeds; sapwood read off the banks at the root):
      DBH vs census   iter-12:  s 3.96x  m 2.49x  l 2.29x   | re-centred on m:  s 1.59  l 0.92
                      iter-13:  s 4.81x  m 3.41x  l 3.11x   | re-centred on m:  s 1.41  l 0.91
      sapwood % of basal area   iter-12:  ~16% (m)  ~10% (l)
                                iter-13:   7.5% (m)   3.7% (l)     [s 17.2%]
- **BOTH predictions REFUTED.** The overshoot got *worse* (~2.5x -> ~3.3x) and the sapwood fraction
  got *worse*: a 104 yr trunk is now 96% heartwood, where a real plane is ~50%. The area law is still
  the physically correct one, and it bought the one real gain — the re-centred splay fell 1.59 -> 1.41
  — but **the metric was never the fault.** The over-count is in the AMOUNT of dead wood banked.
- **★ NEW RAIL — DBH_CALIB cannot answer this either, because it CANCELS.** Live sapwood scales as
  `R_TIP * n_live**(1/p)`, the dead bank as `R_TIP**2 * SUM n_c**(2/p)`, so the sapwood FRACTION is
  independent of R_TIP and hence of DBH_CALIB. It is a pure structural statement: the model has
  accumulated ~26x more dead pipe area than it has live pipe. No scalar can move that ratio.
- **What that leaves:** the model banks every dead branch's full living section forever, so heartwood
  grows without bound while the live crown does not. Real heartwood does not behave that way. Either
  branch death is far too cheap, or — the live suspect — **a disused pipe does not persist at the base
  at its full living diameter.** That is a claim about Kubo 2022's actual mechanism, and I have been
  working from a summary of it rather than from its figures. **Prior art is job 1: read the paper
  before touching this again.**
- **Verdict: PENDING**

## 14 — Bank LOST LEAF UNITS, not dead branch sections (the counting fix)

**Hypothesis.** `ratchet()` banked each dead branch's whole cross-section — which already contained
that branch's own heartwood, which contained its dead children's sections: a recursive double-count.
Aye, Brännström & Carlsson 2022 (Tree Physiology 42(11):2174-2185, PMC9652016 — the paper iter-12/13
mis-cited as "Kubo 2022" and never opened) banks **lost LEAF UNITS** (its Eq. 6): each leaf unit that
dies contributes c_H exactly once, ever. Predicted: remove the recursion and the runaway heartwood
(96% of basal area at 104 yr) collapses toward the ~50% sapwood a real plane carries.

**Change.** `ratchet()` now counts the leaf-unit census straight off the skeleton — F_S = live wood
terminals above a node (Eq. 5), F_H = dead wood terminals (Eq. 6) — and sizes the two banks from it:
`r_sap = R_TIP·F_S^(1/p)` (algebraically identical to the old p-sum recursion; the live taper law is
UNCHANGED) and `A_heart = c_H·F_H` (a pure count — it cannot recurse, because a leaf unit dies once).
Eqs 2-4 are Hellström's statistical bookkeeping for trees you cannot simulate; we simulate, so κ comes
free from the real topology. New constant `HEART_RATIO` = c_H/c_S. New diagnostic: `sap_frac`, F_S, F_H
— the metric iter-12 and iter-13 were both judged on and which was never actually printed.

**Verification.** All three tiers grown (15/47/104 yr).

    tier   F_S live   F_H lost   lost/live   sapwood %   DBH vs census
    s          10         33        3.3        18.3%        5.15x
    m          31        180        5.8         9.9%        3.37x
    l          41        514       12.5         4.7%        3.36x

**verdict: REFUTED — and the refutation is the finding.** Sapwood at l went 3.7% -> 4.7%, against a
target of 50%. The double-count was real but nearly inert: the old code banked each dead branch at
`π·r_sap(death)²` with r_sap already SUBLINEAR in its tip count (p = 2.3), and that understatement was
silently cancelling the recursion. Removing both makes heartwood slightly LARGER, so l's DBH drifted
3.11x -> 3.36x. The heartwood law is now right, and it was never the defect.

**What the fix bought — a decisive, two-sided falsification.** With the count clean, c_H is pinned by
two independent routes that agree: the paper's physics (heartwood IS the disused sapwood pipe, so
c_H = c_S) and the census (solving for the measured m->l basal-area growth, x2.71, demands
c_H/c_S = 1.07). The 50% sapwood target would demand 0.049 — **22x apart. One constant cannot serve
both, and the census has first claim.** So hold c_H = c_S and ask what F_S the 50% target needs:
F_S = F_H^(p/2) = **1311 live leaf units at l. We carry 41.**

**⇒ The live crown is ~32x too small; the dead bank is correct.** F_S goes 10 -> 31 -> 41 over
15/47/104 yr (m->l = x1.32) while the real trunk's basal area grows x2.71 over the same span. The
model's leaf area SATURATES and a real plane's does not. That is not the heartwood law and no scalar
touches it: it is the constant-`N_def` defect the module header has flagged since iter-9 — one armature
tip stands in for a FIXED 354 real twigs at every age and size, which over-serves the sapling and
under-serves the centenarian. It does NOT contradict iter-11's exoneration of the tip budget: the
ARMATURE count is fine; what must scale with size is the deferred A4/A5 foliage each tip stands for.

Do not ship (criterion vi still unmet). Two-strike fires: three iterations have now been spent inside
the heartwood law. **Stop working on the heartwood law. It is done.**

## 15 — N_def size-dependent, realized through the light field (Hellström et al. 2018)

**Prior art, read first and read properly** (the mandate STATE carried into this session). Hellström,
Carlsson, Falster, Westoby & Brännström 2018, "Branch Thinning and the Large-Scale, Self-Similar
Structure of Trees", *Am. Nat.* 192(1):E37–E47, doi:10.1086/697429 — the branch-thinning companion to
the Aye 2022 pipe/heartwood paper the ratchet already builds on. PDF opened, not summarised from
snippets (`tmp/papers/hellstrom2018_branch_thinning.pdf`, gitignored).

    K(n) = alpha*(n+1)^d            (Eq. 1)  the branch CARRYING CAPACITY, in tips
    b(n) = min{mu^n, beta*(n+1)^d}  (Eq. 4)  tips actually borne by a branch of age n

Fitted to Wilson (1966)'s red maple long-shoot counts (Fig. 8, the paper's only broadleaf):
**beta = 6.69, d = 1.44, mu = 1.42, R² = 0.98.** Over our census ages that predicts m->l tip growth of
(105/48)^1.44 = **3.09x**, against the **2.71x** basal-area growth the census independently demands —
two unrelated sources agreeing inside our instrument. That is the growth term the model lacks.

**Hypothesis.** The crown saturates because the economy is scale-free in tips (income ∝ tips, cost ∝
tips, they cancel — iter-14). Give `N_def` a size term and put it on BOTH sides — a tip that stands
for N twigs must *intercept* N twigs' worth of light and *cast* N twigs' worth of shade, not just pay
N twigs' worth of wood — and the cancellation breaks (income ∝ N_def, cost ∝ N_def^(2/p), p = 2.3 > 2).

**⛔ Not as an age lookup.** `K(n) = alpha*(n+1)^d` would make DBH an analytic function of age — a
parameter wearing an output's clothes, the mistake this project has made four times. The paper itself
forbids it (Discussion, p. E45): *"The phenomenological carrying capacity assumed here is in reality
realized through other factors, such as light or nutrient limitation."* We have a light field. So the
capacity is realized through **space and light**, and Hellström's b(n) becomes the **validator**:

    N_def(t) = TWIG_DENSITY * V_crown(t) / n_tips(t)        S(t) = N_def/N_DEF_REF

**Change.** `V_crown` = convex hull of the live foliage cloud (NOT the occupied-voxel count, which is
bounded by 12*n_tips and so would install a new fixed point of its own). S scales, in the same year:
the light a marker intercepts, the shade it casts, the tip pipe (`self.r_tip`), and the heartwood a
unit wills to the trunk when it dies (`self.c_heart`). Heartwood is consequently banked as an AREA at
the c_H of the year of death (`Node.death_c`), not a count times a global constant — same law (Aye
Eq. 6), now size-aware. `TWIG_DENSITY` = 44.51 twigs/m³ is not a new degree of freedom: it is pinned
ONCE by demanding S(m) = 1 (`tmp/iter15_anchor.py`), so it RE-EXPRESSES DBH_CALIB rather than
re-fitting it, and at the anchor the model is unchanged. New diagnostic switches `S_IN_LIGHT` /
`S_IN_SHADE`, because "which side breaks" is not a claim you can make without isolating them.

**Verification.** All three tiers grown, both variants, against the S≡1 baseline.

    variant                    s DBH    m DBH    l DBH   V_crown s/m/l (m³)   real_tips m->l   sap l
    baseline (iter-14)         5.15x    3.37x    3.36x    19 / 216 / 597           —            4.7%
    S in light + shade         6.83x    4.00x    3.90x   547 / 121 /  62         x0.63          1.0%
    S in light, shade off      1.15x    3.56x    4.02x     5 / 466 / 358         x0.83          3.8%
                                                                        (Hellström demands x3.09)

**verdict: REFUTED — the numerator is not exogenous.** `N_def` is read off the live crown; income
scales with `N_def`; income buys the extension that *grows the live crown*. **That is a positive
feedback loop on income, measured from its own product.** It is unstable in both directions: the m
crown sprawled to 466 m³ against a 215 m³ baseline, then the l crown collapsed (358 m³, or 62 m³ with
the shade term). Crown growth m->l came out **x0.77** where it must be ~x2.7. The S-scaled shade makes
the instability *violent* — a linear, clamped-at-zero light field responds savagely to a multiplied
deposit: a small tree (S<1) has its shade *relieved* and sprawls, a big one (S>1) blacks out its own
interior and sheds — but switching it off does **not** remove the loop, only its teeth. Model reverted
to iter-14 (`TWIG_DENSITY = None`, verified bit-identical), mechanism and switches kept.

**What it bought — the sapling, and it is not a small thing.** With `N_def` free to be SMALL for a
small tree (13 twigs, not 355), **the s tier went 5.15x -> 1.15x of its census DBH.** That is open
defect 4 — the constant-`R_TIP` floor that pins a 12.7 cm sapling at 2*R_TIP = 10.3 cm — moving for
the first time in six iterations, and it confirms the SIZE-DEPENDENCE ITSELF is right. The mechanism
stands; only its numerator is refuted. What must change is where the size term is READ FROM: it has to
be a quantity **this year's income cannot bid up.**

## 16 — THE CANTILEVER CANNOT CARRY THE SIZE TERM: STATICS IS INERT, AND THE FAT PIPE IS WHY

**Hypothesis (from iter-15's NEXT).** The size term in `N_def` must be read from *earned and settled*
wood, not from the live crown income bids up. Hellström's Eq. 10 prices a growth module by McMahon &
Kronauer elastic similarity (*"the branch radius r grows as branch length to the power 3/2; thus
n^(3/2) ∝ r and M_n ∝ r^2, which combine to M_n ∝ r^2 ∝ n^3"* — read, p. E44), and we already own that
mechanism: the iter-8 self-support bill. So `N_def` = the twigs the built wood **can hold out**,
`N_cap ∝ r^3 / lever`. The bill reading **0.0000 m^3 in all 104 years** was taken as the sign that the
mechanism was merely un-wired.

**★ It is refuted, and it was refuted BEFORE it was coded — on two independent grounds.**

**(a) Analytic — the loop gain is greater than 1.** The pipe sets `r ∝ T^(1/p) = T^0.435` (T = real
twigs, p = 2.3), while statics demands only `r ∝ (T·lever)^(1/3) = T^0.33`. So a cantilever capacity
`r^3/lever ∝ T^(3/p) = T^1.30` **grows faster than the load it carries.** Feed that back into `N_def`
and it amplifies instead of regulating — the *same* error as `V_crown`, one derivative up. A capacity
read off a pipe radius can never bound the tips that set the pipe radius.

**(b) Measured — `tmp/iter16_mech_probe.py`,** every live wood node, every year, all three tiers. It
re-runs the converged fixed point of `structural_radius()` and compares `r_mech` against `r_pipe`:

    tier   live wood   yrs where statics binds   max r_mech/r_pipe   median   lever>2m: binding/total
      s        346            0 / 16                   0.653          0.136          0 / 0
      m        655            3 / 48                   1.028          0.201          9 / 958
      l       1356           10 / 105                  1.033          0.230         26 / 10917

**STATICS NEVER BINDS.** The pipe is 4-7x thicker than the cantilever demands at the median node; on
the "load-bearing wood" where the iter-8 docstring claimed **42-62% binding**, it binds on **0.2%** of
nodes and exceeds pipe by **3%**. `_bill_total = 0.0000` is therefore **STRUCTURAL, not a wiring bug**
— there is no excess over pipe to charge, anywhere, ever. (The iter-8 claim was measured *before*
iter-9 refit `DBH_CALIB` to 12.85 — R_TIP = 5.1 cm — and before the heartwood ratchet. It is stale;
both docstrings now say so.)

**verdict: REFUTED — and it hands over the lead.**

**★ WHY STATICS WENT INERT IS THE FINDING: THE PIPE IS 3.4x TOO FAT, AND IT HAS BEEN SUPPRESSING THE
ONLY NON-SCALE-FREE LAW IN THE MODEL.** Everything else we own is scale-free — the pipe (homogeneous
in r_tip), the light per marker (12 markers per tip, any size), the tip budget (exonerated, iter-11).
**Statics is the one law with an absolute length scale in it** (SIGMA, GRAV, RHO — a metre means
something), which is precisely why it is the only place a size term can come from. And we have been
drowning it: `r_mech` falls only as `r_pipe^(2/3)` where wood mass dominates the moment, and **not at
all** where leaf mass dominates it. So a census-correct pipe raises `r_mech/r_pipe` by **1.5x at the
bole and up to 3.4x on the distal limbs** — exactly where the leverage is. Defect 2 (stale
`DBH_CALIB`) is not downstream of defect 1 after all: **it is what has been hiding defect 1's cure.**

**Nothing else changed.** Two stale docstrings corrected; the probe is `tmp/`-only (gitignored).

## 17 — THE PIPE RE-CENTRED (a derivation), AND STATICS WAKES UP. THE FALSIFICATION FAILED TO KILL IT.

**The change — two constants, one scalar, zero searches.** `DBH_CALIB 12.85 -> 3.813` and
`ALPHA 2.59e-4 -> 2.281e-5`, i.e. `R_TIP -> k*R_TIP` with `ALPHA -> k^2*ALPHA` at `k = 1/3.37`, taken
from the m (calibration) tier's measured DBH. Baseline re-measured first, not recalled: **5.15 / 3.37
/ 3.36x**. The transform leaves the cost of a unit of extension (`l_afford = v/(n*pi*R_TIP^2)`)
unchanged, so lengths are invariant and every radius scales by `k`; every cross-section in the model
is homogeneous of degree 2 in `R_TIP` (`c_S == pi*R_TIP^2` seeds the pipe, `C_HEART == HEART_RATIO *
pi*R_TIP^2`), so it is **exact** — *while the support bill is zero*, which iter-16 measured it to be.
The one non-homogeneous term in the model is the one we were trying to un-suppress. That is the whole
design of the instrument.

**The hard falsification, stated in STATE before the run: if statics still does not wake up, the
mechanical term is dead for good, and we say so and stop.**

**It woke up.** `tmp/iter16_mech_probe.py`, unmodified, every wood node, every year:

| tier | median `r_mech/r_pipe` | max | load-bearing wood (lever > 2 m) that BINDS |
| --- | --- | --- | --- |
| s | 0.14 -> **0.22** | 0.65 -> **1.03** | 0/958 -> **8/140** (6%) |
| m | 0.20 -> **0.56** | 1.03 -> **2.13** | 9/958 -> **4134/7494** (55%) |
| l | 0.23 -> **0.52** | 1.03 -> **2.54** | 26/10917 -> **17712/24699** (72%) |

And the number iter-16 said would move first: **`_bill_total` leaves 0.0000 for the first time in the
project's history.** On `l`: non-zero in **86 of 104 years**, **0.2586 m^3** of support wood bought,
and it takes **4.8% of the annual pool at yr 20, 20.7% at yr 47, 63.7% at yr 60, 49.2% at yr 104.**
It is zero at yr 10. **A magnitude, not a slope** — and one that is *absent in a sapling and dominant
in a centenarian*, which is the shape defect 1 has been asking for since iter-10.

**verdict: the prediction is CONFIRMED and the term is ALIVE.** Statics is no longer a decoration.

**★ AND THE TWO RAILS HELD, WHICH IS HOW WE KNOW THE INSTRUMENT IS HONEST.** A scalar may CENTRE and
UN-SUPPRESS; it may never FIX. Predicted in STATE, then measured:

- **DBH 1.43 / 0.93 / 0.94x.** Re-centred on m: **s 1.54, l 1.01** — against the pre-registered
  prediction of **s 1.53, l 1.00.** The two-sided splay is *untouched*. Defect 1 is exactly as alive
  as it was this morning, and defect 3 is now honestly stated instead of being buried under a 3.4x.
- **Sapwood 20.9 / 9.5 / 4.4%** (was 18.3 / 9.9 / 4.7). Unmoved, as the "`DBH_CALIB` CANCELS" rail
  says it must be. It is a structural error and no scalar was ever going to touch it.

The tiers are not *bit*-identical to the invariant prediction (m: 800 wood nodes vs 655; DBH 0.93
not 1.00) and **that residual IS the mechanism**: the bill is now being paid, so wood is diverted from
extension, posture stiffens, the light field shifts, and the trajectory legitimately diverges. The ~7%
DBH shortfall below the invariant prediction is the price of standing up. Do not "fix" it with another
scalar.

---

## 18 — THE GATE, MEASURED: THE LEVER CANCELS, AND `N_cap` CANNOT RUN AWAY. GAIN 0.69. **CODE THE TERM.**

`tmp/iter18_gain_probe.py` (+ `tmp/iter18_gain_probe.out`). A **reporting** pass over the converged
fixed point of `structural_radius` — no mechanism changed, not one constant touched.

**Hypothesis (pre-registered in STATE):** now that statics, not the pipe, sets `r` on 55–72% of
load-bearing wood, the loop gain of `N_cap ∝ r³/lever` is no longer iter-16's 1.30. If it is < 1
with margin, the size term is admissible; if ≈ 1 it is a knife edge and we stop.

**★ THE DERIVATION CAME FIRST, AND IT COLLAPSED THE PROPOSAL.** On a statics-bound node the grower
forms `r_mech³ ∝ M_b = g·|V_i|`, and the lever the proposal divides by is *by its own definition*
`lever_i ≡ |V_i| / M_sub,i`. Therefore

> **`N_cap ∝ r³/lever  ≡  M_sub,i` — the SUBTENDED MASS, exactly. The lever cancels.**

"Cantilever capacity" was never a third mechanism. It is *the mass the node already holds up* — and
mass is **history**: wood laid down in past years, which this year's income cannot bid up within the
year. That is the exogenous quantity iter-15 has been asking for since it refuted `V_crown`.

**The gain is then exact, not fitted** — a leaves-first elasticity recursion over the same tree, each
mass carrying the elasticity of *its own law*: foliage `∝ T` ⇒ 1.000 · pipe wood `∝ r_pipe² ∝ T^(2/p)`
⇒ **0.870** · statics wood `∝ r_mech² ∝ |V|^(2/3)` ⇒ `(2/3)·ε(|V|)`, with `ε(|V|)` the exact projected
flux. Then `d log N_cap/d log T = ε(M_sub) = A_i/M_sub,i`.

**Measured, on binding load-bearing wood (lever > 2 m), all three tiers:**

| | binding yrs | moment: wood / leaf | gain (mass-wt) | gain range | `M_sub`(root) @ tier age |
|---|---|---|---|---|---|
| s | 2/16 | 0.95 / 0.05 | 0.866 | — | 113.2 kg |
| m | 34/48 | 0.96 / 0.04 | 0.639 – 0.866, **med 0.696** | p10–p90 0.61–0.81 | 848.6 kg |
| l | 91/105 | 0.96 / 0.04 | 0.504 – 0.866, **med 0.687** | p10–p90 0.57–0.78 | 2782.2 kg |

- **iter-8 §5's assertion — "wood dominates the moment" — is now MEASURED: 95–97%.** It was right.
  It was also eight iterations old and load-bearing; iter-16 is the whole lesson about that.
- **GAIN 0.69, and it never once exceeded 0.866 in 127 binding tier-years.** That ceiling is
  **structural, not empirical**: every component elasticity is ≤ 1 (leaf 1.000, pipe 0.870, statics
  ≤ 0.667), so their mass-weighted mean is ≤ 1, and it can only *reach* 1 if the mass went ~all-leaf —
  against a measured 96% wood. **The gain cannot reach 1 while wood holds up the tree.**
- **★ WHY iter-16 CAME OUT AT 1.30 AND THIS COMES OUT AT 0.69 — it is one exponent.** Read off a
  PIPE radius, `r³ ∝ T^(3/p)`: a **CUBE** law, gain `3/p` = 1.30 > 1, a runaway. Read off STATICS,
  `r³ ∝ |V| ∝ mass ∝ T^(2/p)` at worst: a **SQUARE** law, gain ≤ `2/p` = 0.870 < 1, a regulator.
  **`p = 2.3` is what puts 1.0 between them.** iter-16 was not refuted by the cantilever; it was
  refuted by the cube.

**And the scale landed where the ground truth wanted it, with nothing fitted.** `M_sub`(root)
**m→l = 2782.2 / 848.6 = ×3.28** — against defect 1's independent ground truth of **×3.09**
(Hellström b(n)) and **×2.71** (census basal area). Inside the ~10–15% instrument floor of the
better one. This is an *observation*, not yet a result: nothing was tuned to produce it, and it is
`M_sub` itself, not the per-tip `N_def` that will actually be coded. **iter-19 must pre-register
against it, not celebrate it.** `s` is the open question — `M_sub(s)/M_sub(m) = 0.133`, and whether
that is defect 4's cure or an over-correction is exactly what iter-19 must predict *before* running.

**★ A CONSEQUENCE FOR WHAT GETS CODED, AND IT IS NOT A DETAIL.** Statics binds on only **2 of s's 16
years**, and **never at the bole** (the root is pipe-bound in every tier-year, gain 0.85). So the term
**must not be gated on "where statics binds"** — read `r³/lever` on a *pipe*-set radius and you are
back on the cube law and the 1.30 runaway, which is iter-16 rebuilt by accident. **Code `M_sub`
directly** — the supported mass. It is defined in every node in every year, it *equals* the statics
capacity wherever statics binds, and it is the quantity the gain above was actually measured on.

verdict: PENDING

---

## 19 — THE TERM, CODED: `N_def ∝ M_sub`. **PRE-REGISTERED BEFORE THE RUN.**

`MASS_CAP` pinned ONCE by `S(m) = 1` at the m anchor (`tmp/iter19_anchor.py`, term OFF, the iter-17
model): baseline `M_sub` = **113.2 / 848.6 / 2782.2 kg** (reproduces iter-18 exactly), `n_tips` =
**10 / 25 / 34**, so **`MASS_CAP` = 21.7 x 25 / 848.6 = 0.6400 real twigs per kg of supported mass**.
It re-expresses `DBH_CALIB`; it is not a new degree of freedom.

**Open-loop `S` off that baseline: `s` 0.333 · `m` 1.000 · `l` 2.411.** Note `s`'s per-tip ratio is
**0.333, not the 0.133 of the raw mass** — `n_tips` falls with the tree too (10 vs 25), and the
denominator is half the term. STATE's over-correction worry is therefore SMALLER than it looked.

**PRE-REGISTRATION — written before `MASS_CAP` was switched on. Baseline: DBH 1.43 / 0.93 / 0.94x
census, sapwood 20.9 / 9.5 / 4.4%.**

1. **`s` DBH FALLS, and defect 4 moves.** `r_tip ∝ S^(1/p)` ⇒ x0.63 open-loop ⇒ ~0.90x census; the
   negative feedback through `n_tips` should hold it above that. **Predict `s` in 0.90–1.20x** (from
   1.43x). If it lands under 0.85x the term OVER-serves and the anchor is wrong, not the mechanism.
2. **★ `l` DBH RISES — this is the one that can kill it.** `S(l) = 2.41` ⇒ `r_tip` x1.46 open-loop ⇒
   ~1.37x census, from 0.94x. **Predict `l` in 1.10–1.40x.** Above ~1.4x the term over-serves the
   centenarian and `DBH_CALIB` needs the one-time re-centring — that is a CALIBRATION verdict, not a
   refutation. It is only a REFUTATION if `l` runs away (> 2x) — the gain says it cannot.
3. **★★ THE ONE THAT DECIDES IT — `l` SAPWOOD MUST RISE.** This is defect 1, and it is why a scalar
   could never do it: heartwood is willed at `c_heart(t)` of the year a unit DIED — early, when `S`
   was small — while today's sapwood is priced at today's LARGE `r_tip`. A *rising* `S` therefore
   shrinks the historic heart against the live sap, which no uniform multiplier can. **Predict `l`
   sapwood > 8% (from 4.4%), `m` > 11% (from 9.5%).** If sapwood does NOT rise, the mechanism is
   REFUTED for defect 1 and `M_sub` is only a DBH re-centring in disguise — do not rescue it.
4. **`m` is NOT invariant.** `S = 1` holds at the anchor *year*, but `S < 1` through m's youth, so m
   DBH falls a little. **Predict `m` in 0.82–0.95x** (from 0.93x).
5. **RAILS I EXPECT TO HOLD** (read the refutation for what it exonerates): no runaway (gain 0.69) —
   `l` crown neither explodes nor collapses as it did under `V_crown`; heights unchanged; the
   caliber splay `s 1.54 / m 1.00 / l 1.01` narrows from the `s` end, not the `l` end.


**RESULT — EVERY PRE-REGISTERED RAIL BROKE, AND THEY BROKE THE SAME WAY. THE PIN IS REFUTED; THE
MECHANISM IS NOT.** (`tmp/iter14_measure.py` with `MASS_CAP = 0.64`; `tmp/iter19_s_trace.py`.)

| | DBH vs census | | sapwood | | F_H |
|---|---|---|---|---|---|
| | baseline | term ON | baseline | term ON | term ON |
| s | 1.43x | **0.34x** | 20.9% | 57.3% | **0** |
| m | 0.93x | **0.24x** | 9.5% | 67.8% | **0** |
| l | 0.94x | **0.23x** | 4.4% | 55.9% | **0** |

Prediction 1 said `s` in 0.90–1.20x; 2 said `l` in 1.10–1.40x (RISING); 4 said `m` in 0.82–0.95x.
The tree instead came out **4x too THIN everywhere**, with **no heartwood at all** — and the sapwood
"win" is worthless: `F_H = 0` means not one leaf unit ever died, so 100%-of-pipe sapwood is the
reading of a tree too starved to self-shade, not of a tree with wide sapwood.

**★ THE TELL IS IN THE RATIOS: 0.24 / 0.26 / 0.24 of baseline — a UNIFORM thinning.** A size term
that thins all three tiers by the same factor has not acted as a size term at all. `tmp/iter19_s_trace.py`
says why: **`S` sits ON THE `S_MIN` FLOOR (0.020) for the first 16 YEARS**, and at the m anchor
reaches only **`S = 0.171`, not the 1.000 it was pinned to.** All three tiers spend most of their
lives at the floor, so all three get the same scalar — the shape never gets to speak.

**★★ WHY — AND IT IS A LESSON, NOT A TYPO. THE ANCHOR WAS MEASURED ON A TREE THAT NEVER EXISTS.**
`MASS_CAP` was pinned off the S == 1 baseline's `M_sub(m) = 848.6 kg`. But the tree that RUNS with
the term does not have that mass: it is thinner all through its youth (`S < 1`), so it arrives at the
anchor **lighter** (455 kg at yr 46, not 848), and — the half I did not see coming — with **MORE
tips** (77, not 25), because tips that stand for fewer twigs are CHEAP. Both terms of
`S = MASS_CAP·M_sub/n_tips` move the wrong way at once. **The pin must be a FIXED POINT of the loop
it closes, not a measurement taken outside it.**

**★ AND THE GAIN CUTS BOTH WAYS — the one thing iter-18 did not say.** `d log S / d log MASS_CAP =
1/(1-g)` = **3.2 to 7.7** at g = 0.69–0.87. A loop gain under 1 bought STABILITY (no runaway — and
indeed nothing ran away: the crown neither exploded nor collapsed, rail 5 held). **It did not buy
INSENSITIVITY.** The size term makes DBH 3–8x more sensitive to its own constant than the scale-free
model ever was. That is the *price* of the term, it is now measured, and it is affordable — but only
if the constant is solved, never estimated.

**What it exonerates** (read the refutation for this, not only for what it kills): the gain analysis
(no runaway — the failure is a LOW fixed point, not a high one); `M_sub` as an exogenous numerator;
the negative feedback through `n_tips` (it worked — it is what ate the tip budget); and the
size-dependence itself — `S` at the m tier still climbs monotonically 0.02 → 0.17 with the tree, so
the SHAPE is there, suppressed under a bad scalar and a floor, not absent.

**A second, independent defect, found by the trace:** `S_MIN = 0.02` puts `N_def` at **0.4 real twigs
per armature tip** — a tip standing for less than *itself*. That is not a small number, it is an
incoherent one, and it is what held the sapling on the floor for 16 years. The floor must be
`N_def >= 1` ⇒ `S_MIN = 1/N_DEF_REF`. (`N_DEF_REF` is only 21.7 twigs since iter-17 re-centred the
pipe — the term now lives at a scale where the floor is *reachable*, which it never was at 354.)

`MASS_CAP` is reverted to `None` in the shipped model: the repo tree is the iter-17 tree, verified
unchanged after the revert (`s` DBH 18.2 cm, sapwood 20.9%). The term stays CODED and OFF.

verdict: ACCEPTED (Chris, 2026-07-13) — the diagnosis stands: the pin was open-loop. He set
iter-20 himself: fix `S_MIN` to `1/N_DEF_REF`, then root-find `MASS_CAP` closed-loop on `S(m) = 1`.

## 20 — SOLVE `MASS_CAP` IN THE LOOP → THE LOOP HAS NO SOLUTION. `N_def ∝ M_sub` IS REFUTED.

**Hypothesis (pre-registered, `tmp/iter20_prereg.md`, written before the solve returned):** `S` was
suppressed because (a) the floor `S_MIN = 0.02` is incoherent — it puts `N_def` at 0.4 real twigs per
armature tip, a tip standing for less than *itself* — and (b) `MASS_CAP` was pinned open-loop. Fix the
floor to `S_MIN = 1/N_DEF_REF` (= 0.046) and solve `MASS_CAP` as a fixed point of `S(m @ 47 yr) = 1` in
the closed loop, and `S` will **SPREAD** across the tiers (`S(s) < 1 < S(l)`, predicted `S(l) ≥ 1.5`),
narrowing the caliber splay from the `s` end and — the decider — lifting `l` sapwood from 4.4% past 8%.

**Change:** `tmp/iter20_solve.py` — bracket + log-space bisection on the *closed-loop* m tier (11 evals,
~9 min). `tmp/iter20_measure.py` — the three tiers at the solved constant. No model change was shipped
from the solve: `MASS_CAP` stays `None`.

**RESULT — ★★ THE ROOT EXISTS AND IT IS A KNIFE EDGE. THE TERM IS NOT MIS-CALIBRATED, IT IS THE WRONG
SHAPE.** (`tmp/iter20_solve.log`, `tmp/iter20_measure.log`.)

| MASS_CAP | S(m @ 47 yr) | n_tips | M_sub |
|---|---|---|---|
| 2.1832 | 0.58 | 100 | 628 kg |
| 2.2014 | 0.69 | 74 | 537 kg |
| **2.2105** | **1.14** | 65 | 877 kg |
| 2.2197 | 2.03 | 36 | 1057 kg |
| 2.2568 | 9.73 | 12 | 1601 kg |
| 3.1443 | **1102** | 7 | **66,648 kg** — a 66-tonne "tree" |

`d log S / d log MASS_CAP` ≈ **80–130** at the root ⇒ **loop gain g ≈ 0.99**, against iter-18's 0.69 and
iter-19's predicted amplification of 3.2–7.7. This is a **transcritical bifurcation at MASS_CAP ≈ 2.205**:
below it the tree starves onto the floor, above it it detonates.

**★★ AND THE THREE TIERS CANNOT BE SANE AT ONCE — this is the actual falsification** (@ MASS_CAP = 2.2059,
the solved root):

| | DBH vs census | S | n_tips | F_H | sapwood |
|---|---|---|---|---|---|
| s (15 yr) | **0.52x** | 0.054 — **STILL ON THE FLOOR** | 97 | **0** | 92.7% (starved) |
| m (47 yr) | 0.76x | **0.769** — not the 1.000 it was solved to | 97 | 214 | 35.4% |
| l (104 yr) | **33.6x** — a **23.9 METRE** trunk | **51,817** | 7 | 575 | 11.1% |

Every pre-registered prediction failed, and the *l* tier failed in the opposite direction from iter-19's.
Not one of them was a near miss.

**★ THE ALGEBRA THAT KILLS IT — ONE LINE, AND IT WAS AVAILABLE BEFORE A SINGLE CPU-SECOND WAS SPENT:**

    N_def · n_tips  ≡  MASS_CAP · M_sub          — the n_tips division CANCELS IN THE TOTAL.

The crown's **total** real-twig count — the thing that earns the light income — is therefore proportional
to **the tree's own standing mass**, with no `n_tips` in it at all. Income drives mass accretion, so
`dM/dt ∝ MASS_CAP · M`: a **linear positive feedback on mass**, whose rate constant *is* `MASS_CAP`.
⇒ **The `n_tips` "negative feedback" that iter-19 leaned on is a REDISTRIBUTION, NOT A REGULATOR.** It
sets how the twigs are *parcelled out* among markers; it cannot change how many there are. The only
thing bounding the loop was self-shading — and shade is cast at **marker** resolution, so as `n_tips`
collapses (287 → 7 across the bracket) the shade evaporates while the income does not. **The regulator
dies exactly when it is needed.** That is the runaway, and 7 markers standing for 24,000 twigs each is
its signature.

**★ WHY iter-18's GAIN OF 0.69 WAS NOT WRONG, IT WAS OF THE WRONG LOOP.** It is the gain of ONE TIP's
radius. The loop that actually runs is the WHOLE CROWN's leaf count against the WHOLE TREE's mass, and
its gain is 1 by construction — the exponent on `M_sub` *is* the gain. A per-element gain does not bound
an aggregate loop.

**★ EXOGENOUS WAS NECESSARY, NOT SUFFICIENT.** `M_sub` is genuinely exogenous *within* the year (banked
by last year's `structural_radius` — that property is real and survives). It still runs away *across* the
years, because year-on-year the mass it reports is the mass its own income built. Iter-15's rail said
"don't read the numerator from the live crown". The rail was necessary and too weak: **an exogenous
numerator that is still PROPORTIONAL to the tree's own product is a positive feedback with a one-year
delay.** What must be bounded is not the *timing* of the read but the *exponent*.

**And `S(m) = 0.769` at its own solved root is the last nail:** at an amplification of ~100, the fixed
point is **finer than the model's own stochastic noise**. Even if a sane root existed, it would not be
reproducible. `MASS_CAP` is **unsolvable**, not merely unsolved.

**What survives:** `S_MIN = 1/N_DEF_REF` — shipped, and it is a *definition* (a tip stands for at least
one twig), not a knob. The size term stays CODED and OFF. The shipped model is the iter-17 tree,
re-verified after the edit. Defect 1 (the saturating leaf-unit count) is **wide open again**, and the
numerator hunt is back to square one — but square one now has three rails on it instead of one.

**NEXT (iter-21): THE NUMERATOR MUST BE SUB-LINEAR IN MASS.** Total leaf ∝ `M^q`, `q < 1` — `q` *is* the
loop gain, so it is the only structural way to get `g < 1` robustly rather than by luck. The standard
allometry puts leaf mass ∝ `M^(3/4)` (WBE / Enquist). ⚠ **That paper must be OPENED AND READ before the
line is coded** — it is currently a memory, not a citation, and this project has paid twice for that
mistake. And **compute the gain of the WHOLE-CROWN loop before writing the term**, not one tip's.

verdict: PENDING

## 21 — THE PAPER SAYS THE ¾ IS AN ARTIFACT; THE PROBE SAYS THE TWO GROUND TRUTHS AGREE

**Hypothesis (as planned):** the numerator must be sub-linear in mass, `L ∝ M^(3/4)` (WBE/Enquist).

**★ THE PAPER, OPENED (the rail held, and it killed the plan).**
Berry, Anfodillo, Castorena, Echeverría & Olson (2024), *J. Exp. Bot.* 75(13):3993–4004,
"Scaling of leaf area with biomass in trees reconsidered". Fig. 3: metabolically-active sapwood
volume per unit leaf area is **CONSTANT with height growth** (slope 0.97, isometric), while
traditionally-measured sapwood volume scales at 0.84. Their conclusion, verbatim in effect: the
hypoallometric leaf-vs-mass scaling **"reflects heartwood accumulation, not metabolic constraints."**
⇒ **`M^(3/4)` IS NOT A LAW, IT IS AN OUTPUT.** Coding it would have been FITTING THE APPEARANCE —
the one thing this project forbids. (And the empirical exponent isn't ¾ anyway: Xu, Li & Wang 2014,
PLoS One, measure **0.873, 95% CI 0.851–0.895** across Chinese forests — above ¾, below 1.)

**★ AND THE GAIN, COMPUTED BEFORE A LINE WAS CODED (the rail again).** Reduce first. The model's own
pipe law already gives, exactly:

    A_sap = pi*r_tip^2 * F_S^(2/p),  r_tip = R_TIP*S^(1/p)   =>   A_sap = const * (S*F_S)^(2/p)
                                                              =>   A_sap = const * L^(2/p)

`S` and `F_S` enter ONLY AS THEIR PRODUCT `L` = the total real leaf count. So the model ALREADY
contains the pipe relation between leaf count and sapwood area (`A_sap ∝ L^0.870` at p=2.3). Impose
Berry's isometric `L ∝ V_sap ≈ A_sap·h` ON TOP of that and the system is OVER-DETERMINED:

    L = K*A_sap*h = K'*L^(2/p)*h    =>    L ∝ h^(1/(1-2/p)) = h^7.67

**A tree that doubles in height gets 200x the leaves.** Reading `N_def` from sapwood VOLUME detonates
worse than iter-20. Zero CPU-seconds spent. Both candidate numerators dead before the editor opened.

**Change:** none to the model. `tmp/iter21_sapwood_split.py` — a probe reading an instrument that has
existed since iter-14 (line 1925) and was **never once looked at**: `sap_frac_pipe` (sapwood vs the
pipe the tree owns) alongside `sap_frac` (sapwood vs the wood it BUILDS, incl. the cantilever).

**Verification (all 3 tiers, one run):**

    tier age   DBH    A_built    A_sap  A_heart  sap/built  sap/pipe  pipe/built   F_S   F_H
      s   15  1.43x    258.7c    54.1c   204.6c     20.9%     20.9%      100.0%    10    28
      m   47  0.93x   1260.1c   120.1c  1140.1c      9.5%      9.5%      100.0%    25   156
      l  104  0.94x   3492.6c   152.8c  3339.8c      4.4%      4.4%      100.0%    33   457

**★ REFUTED, AND IT EXONERATES THE STATICS.** `pipe/built = 100.0%` in every tier: the cantilever is
NEVER binding at the base. The trunk is 100% pipe+heartwood, so `sap_frac == sap_frac_pipe` identically.
The suspicion that defect 1 was really a statics artifact is **dead**, and six iterations of numerator-
hunting are hereby confirmed to have been aimed at the RIGHT mechanism. A refutation that exonerates.

**★★★ THE FINDING — TWO GROUND TRUTHS, NEVER BEFORE COMPARED, AGREE TO 7%.**
Hold `A_built` (DBH is good: 0.93x / 0.94x) and demand the ~50% sapwood the census requires. Since
`A_sap ∝ L^(2/p)`, invert for the total real leaf count `L` each tier must carry:

    tier   A_sap now -> needed      L now  ->  L needed
      m       120c   ->    630c     8,850  ->    59,700      (ratio 5.25 => L x 6.75)
      l       153c   ->  1,746c    11,682  ->   192,700      (ratio 11.43 => L x 16.5)

    ==>  L(l)/L(m) = 3.23      and the INDEPENDENT Hellström real-tip census says  x3.0.

The sapwood-fraction target and the twig-count target are **THE SAME TARGET**. They have never been
solved against each other, and they do not disagree — they agree to 7%. So `N_def` is not mis-shaped;
it is **ANCHORED ~6.75x TOO LOW**. `S(m) ≈ 6.75`, `S(l) ≈ 16.5`, ratio **2.44**.

**★ AND THE MECHANISM CLOSES ITSELF — ONE TERM MOVES BOTH GROUND TRUTHS, IN OPPOSITE DIRECTIONS.**
`c_H` is banked at the `S` prevailing ON THE YEAR A UNIT DIED (`nd.death_c`, already coded, iter-15).
So a RISING `S(t)` makes the early deaths — which are MOST of them (F_H: 28 -> 457) — bank a SMALLER
heartwood area, while the live tips carry a LARGER sapwood one. `A_sap` UP and `A_heart` DOWN from the
SAME term. That is how sap_frac can reach 50% while `A_built`, and therefore DBH, holds. Nothing else
in the model can do that, and no scalar can do it at all.

**★ The target is a RATIO, so it is scalar-proof.** `A_sap/A_heart = 1` at m AND at l (it is 0.105 and
0.046 today). `DBH_CALIB` cancels in a ratio — the iter-17 rail says a scalar may CENTRE but never FIX,
and a ratio target is immune to the thing that cancels. Pre-registered at BOTH ends of size.

verdict: PENDING

## Staged lessons

One line each. Raw, unpromoted. `/distill` empties this section — `/work` may only append to it,
and may never edit `~/.claude/rules/`, `CLAUDE.md`, or `MEMORY.md` on its own.

*(Emptied 2026-07-13 by `/distill` — iters 14–17 promoted. Raw entries and where each one went:
`ledger_archive/2026-07.md`.)*

- **ALGEBRA BEFORE INSTRUMENTATION — reduce the proposed quantity before you measure it, or you will measure a disguise.** `N_cap ∝ r³/lever` *is* the subtended mass, identically: the lever the proposal divides by is the same lever the moment multiplied by. Two iterations argued about a "cantilever capacity" that was a mass in a costume. One line of algebra, done before the probe, told us what the probe was for. (iter-18)
- **A CONSTANT INSIDE A FEEDBACK LOOP MUST BE SOLVED, NOT MEASURED — and gain < 1 does NOT mean insensitive.** Pinning it on the open-loop system (the model with the term OFF) measures a tree that never exists once the term is on: the loop moves the very quantities the pin was read from. And the DC amplification is `1/(1-g)` — at gain 0.69 a 25% error in the constant becomes a 4x error in the output. Stability and insensitivity are different properties, and only the first one follows from g < 1. (iter-19)
- **A UNIFORM RESPONSE FALSIFIES A SIZE TERM NO MATTER WHAT THE MEAN DOES.** Three tiers thinned by 0.24/0.26/0.24 is a SCALAR wearing a size term's clothes — read the ratios across the tiers before reading any one tier's number. The floor, not the law, was doing the talking. (iter-19)
- **A LOOP GAIN IS AN EXPONENT, AND THE EXPONENT IS SET BY WHERE YOU READ THE RADIUS.** Same mechanism, same tree, same year: `r` from the pipe ⇒ gain `3/p` = 1.30 (runaway); `r` from statics ⇒ gain ≤ `2/p` = 0.870 (regulator). A cube law vs a square law, with 1.0 sitting between them because `p = 2.3`. When a gain comes out on the wrong side of 1, ask which law set the variable you read — the mechanism may be innocent. (iter-18)
- **AN AGGREGATE LOOP IS NOT BOUNDED BY A PER-ELEMENT GAIN — and a division that CANCELS is not a feedback.** `N_def = C·M/n_tips` looks like it is regulated by `n_tips`, but `N_def·n_tips ≡ C·M`: the divisor cancels in the total, so it only *parcels out* the resource, it cannot change how much there is. The measured per-tip gain was 0.69; the aggregate gain was 1.0 and the system bifurcated. **Reduce the term to the quantity that actually closes the loop, and take the gain THERE.** (iter-20)
- **EXOGENOUS IS NECESSARY, NOT SUFFICIENT — what must be bounded is the EXPONENT, not the timing of the read.** A numerator read from *last* year's wood is still a positive feedback if it is PROPORTIONAL to the tree's own product: the delay changes the phase, not the gain. Only a sub-linear exponent (`M^q`, q < 1) bounds it. (iter-20)
- **A KNIFE-EDGE ROOT IS A FALSIFICATION, NOT A CALIBRATION — read the SENSITIVITY at the root, not just the root.** The bisection converged; that proved nothing. `d log out / d log const` ≈ 100 means the fixed point is finer than the model's own noise, i.e. UNSOLVABLE. **A root-find that succeeds can still be the refutation — always report the local slope with the answer.** (iter-20)
- **WHEN A TERM IS A SIZE TERM, TEST IT AT BOTH ENDS OF SIZE BEFORE BELIEVING THE ANCHOR.** The constant that gave the m tier its anchor left s starved on the floor AND detonated l to a 24-metre trunk. Age was the bifurcation parameter. One tier's success is not evidence; the SPREAD across tiers is the whole claim. (iter-20)

- **AN INSTRUMENT THAT EXISTS AND IS NEVER READ IS THE SAME AS NO INSTRUMENT.** `sap_frac_pipe` was coded in iter-14 and printed by nobody for SEVEN iterations; it took one glance to exonerate the statics and confirm the numerator hunt was aimed correctly. Before building a new probe, **grep for the one you already built.** (iter-21)
- **★★ CHECK YOUR GROUND TRUTHS AGAINST EACH OTHER *BEFORE* FITTING TO EITHER — THEY MAY AGREE, AND THAT AGREEMENT IS THE STRONGEST EVIDENCE YOU WILL EVER GET.** The 50%-sapwood census and the Hellström ×3.0 twig count had never been compared; inverted through the pipe law they demand L(l)/L(m) = 3.23 vs 3.0 — a 7% match. The companion rail (`one_constant_two_truths`) says a big DISAGREEMENT is a structural falsification; its other half is that a tight AGREEMENT between two independent truths *pins the mechanism* and tells you the term is merely mis-anchored, not mis-shaped. Two sessions of hunting the wrong shape were avoided by one line of arithmetic on numbers already printed. (iter-21)
- **★ THE LITERATURE'S EXPONENT MAY BE AN *OUTPUT* OF THE MECHANISM YOU ALREADY MODEL — CODING IT WOULD BE FITTING THE APPEARANCE.** `M^(3/4)` for leaf-vs-mass is not a metabolic law: Berry et al. 2024 show it EMERGES from heartwood accumulation, which this model already simulates. Before importing a published exponent as a rule, ask whether your own process **derives** it. If it does, importing it double-counts and over-determines the system. (iter-21)
- **★ REDUCE THE PROPOSED LAW AGAINST THE LAWS ALREADY IN THE MODEL, NOT JUST AGAINST ITSELF.** Berry's `leaf ∝ sapwood volume` is sound in isolation; laid on top of the pipe law the model already had (`A_sap ∝ L^(2/p)`), it over-determines the system and gives `L ∝ h^7.67`. A new term's gain must be computed **in the presence of the existing terms** — a law that is stable alone can detonate in company. (iter-21)

## 22 — q MEASURED = 0.987 ⇒ THE NUMERATOR FAMILY IS CLOSED. THE DEFECT MOVES TO TIP SURVIVAL.

**Hypothesis (pre-registered, iter-21):** `N_def` is mis-ANCHORED, not mis-shaped. A rising
`S ∝ M^q`, with `q` MEASURED from the tiers' mass ratio against the required `S(l)/S(m) = 2.44`,
drives `A_sap/A_heart → 1` at both m and l while DBH holds. **The deliverable is `q`, not the tree.**
iter-21 predicted: "if `M(l)/M(m) ≈ 8–10`, then `q ≈ 0.4`" ⇒ tame gain, amplification 1.7×.

**Change:** NONE to the model. Two probes: `tmp/iter22_q.py`, `tmp/iter22_family.py`.

**★ STEP 1 — THE MEASUREMENT REFUTES THE LAW BEFORE A LINE OF IT WAS CODED (`tmp/iter22_q.py`):**

    tier  age    M_sub    F_S    L now    A_sap -> needed     L NEEDED
      s    15   113.2kg    10      217    54.1c ->  129.4c        592
      m    47   848.6kg    25      543   120.1c ->  630.1c      3,655
      l   104  2782.2kg    33      717   152.8c -> 1746.3c     11,803

      M(l)/M(m)          = 3.279      <- the model's own mass ratio
      L(l)/L(m) REQUIRED = 3.230      <- the census, via the model's own pipe law
      ==>  q = 0.9873    LOOP GAIN 0.987    amplification 1/(1-q) = 78.8x

The mass ratio is **3.28, not the 8–10 the pre-registration expected.** So the exponent the census
forces is **the linear one iter-20 already killed**, and the knife-edge amplification (79x) is
iter-20's own signature: a fixed point finer than the model's 10-15% seed noise. **Unsolvable, not
unsolved.** (S implied: s 2.30 / m 6.73 / l 16.46 — reproduces iter-21's 6.75/16.5 exactly.)

⚠ **A STALE DOCSTRING, CAUGHT:** iter-21's absolute `L` figures (8,850 / 59,700 / 192,700) were 16.3x
too large — they used `N_DEF_REF = 12.85^2.3 = 354`, but `DBH_CALIB` has been **3.813** since iter-17,
so `N_DEF_REF = 21.7`. The comment at line 93 was true when written. **Every RATIO — and so every
conclusion of iter-21 — is unaffected** (the factor cancels), but the numbers were wrong on their face.

**★★ STEP 2 — AND THE GENERALISATION IS TESTABLE, SO I TESTED IT (`tmp/iter22_family.py`).**
For ANY numerator read off something the tree owns, `L = K*X^q`, the census forces
`q(X) = ln(3.23)/ln(X(l)/X(m))`. So **gain < 1 requires exactly one thing: `X(l)/X(m) > 3.23`** —
the variable must grow FASTER than the leaf count must. That is a property of the DATA, not of the
mechanism. Ask it of every readable size at once:

      X  (read off the tree)      m         l    X(l)/X(m)  q forced  1/(1-q)   verdict
      M_sub  standing mass     848.6    2782.2      3.279     0.987     78.8   knife-edge
      wood volume               0.94      3.09      3.279     0.987     78.8   knife-edge
      crown volume             202.6     600.8      2.966     1.078      inf   RUNAWAY
      n_nodes (armature)        5597     16693      2.982     1.073      inf   RUNAWAY
      F_H  dead leaf units       156       457      2.929     1.091      inf   RUNAWAY
      A_built  basal area       0.13      0.35      2.772     1.150      inf   RUNAWAY
      F_S+F_H  ever-made         181       490      2.707     1.177      inf   RUNAWAY
      age                         47       104      2.213     1.476      inf   RUNAWAY
      crown surface ~ V^2/3     34.5      71.2      2.064     1.618      inf   RUNAWAY
      height                    7.62     13.68      1.795     2.004      inf   RUNAWAY
      F_S  live leaf units        25        33      1.320     4.223      inf   RUNAWAY

**NOT ONE VARIABLE CLEARS THE BAR.** Mass and wood volume tie it (by 1.5% — the knife edge);
everything else forces `q > 1` outright. **⇒ THERE IS NO NUMERATOR WITH GAIN < 1. THE FAMILY IS
CLOSED** — V_crown (15), M_sub linear (20), V_sap (21), M^q (22), and every member never written.
Six iterations were spent looking for a member of an empty set.

**★★★ AND THE SAME TABLE SAYS WHERE THE DEFECT REALLY IS. TWO ROWS:**

      tips EVER MADE  (F_S+F_H)   181 -> 490   = x2.71     <- the census wants x3.0 (Hellstrom)
      tips STILL ALIVE     (F_S)    25 ->  33   = x1.32
      live-tip survival           13.8% -> 6.7%            <- IT HALVES

**The tree MAKES tips at very nearly the right rate. It then KILLS them.** Six iterations have been
trying to compensate for a collapsing survival fraction with a MULTIPLIER (`N_def`) on a frozen live
count — and the multiplier is now proven not to exist. Hold survival at m's 13.8% and l carries 67.6
live tips (x2.71 vs m) with **`N_def` CONSTANT, S ≡ 1, no new law and no new constant** — 84% of the
census's 3.23 with nothing added to the model at all.

**★ THIS IS THE SHORTCUT THE STANDING RULE NAMES.** `N_def` is what one armature tip *stands in for*:
a **parameter in an output's clothes**, patching the deferred A4/A5 layer. The real tip count is
DERIVED by a real tree — from branching and from SURVIVAL — so it must be derived here. Six iterations
of making a parameter behave like an output, while the actual output (the live tip count) sat frozen.

**Verification:** two probes, three tier grows each, zero model change, ~0 CPU-minutes. The refutation
is arithmetic on numbers the model already prints. The shipped tree is still the iter-17 tree.

verdict: PENDING

- **★★★ A LOOP GAIN IS SET BY THE DATA, NOT BY THE MECHANISM — SO YOU CAN REFUTE A WHOLE FAMILY OF MECHANISMS IN ONE TABLE.** For any law `output = K·X^q` fitted to a target ratio `T`, the exponent the data forces is `q = ln T / ln(X_hi/X_lo)`, so the gain is `< 1` **iff the variable grows faster than the target must**. That is a one-line test, and it can be run against EVERY readable variable at once. Six iterations were spent building and refuting members of a family (V_crown, M_sub, V_sap, M^q) that was EMPTY — one table, costing zero CPU-seconds, showed no variable in the model clears the bar. **Before hunting the next candidate term, tabulate the ratio the target demands against the ratio every candidate offers.** (iter-22)
- **★★ WHEN NO MULTIPLIER CAN FIX A COUNT, THE COUNT IS THE DEFECT — LOOK AT WHAT YOU DEFERRED.** `N_def` (what one armature tip "stands in for") existed only to patch a layer the model deliberately does not grow. It is a **parameter in an output's clothes**, and the standing rule ("anything the real thing derives, we derive") had already been broken the moment it was written. The tell was visible for six iterations in a number nobody divided: the tree makes tips at x2.71 (census x3.0) and keeps only x1.32 of them. **A stand-in factor is a shortcut with a loop in it; when it will not solve, suspect the deferral, not the factor.** (iter-22)
- **★ A CONSTANT'S DOCSTRING IS A DATED CLAIM — AND A REFIT ORPHANS EVERY ABSOLUTE NUMBER DOWNSTREAM OF IT.** `N_DEF_REF = 354` was written when `DBH_CALIB` was 12.85; iter-17 refit it to 3.813 and the true value became 21.7. Six iterations quoted the stale one. Ratios were immune (the factor cancels) so nothing was refuted — but the numbers in four ledger entries are wrong on their face. **When you refit a calibration constant, grep for every comment that quotes a number derived from it, in the same commit.** (iter-22)

## 23 — THE CROWN IS NOT DARKER. IT IS EMPTIER. (investigation; no model change)

**Mandate (from iter-22):** live-tip survival halves from m to l (13.8% -> 6.7%). *Get the
mechanism.* Pre-registered suspect (iter-20): the crown shades itself harder at l, because shade
is cast at MARKER resolution. **Probe:** `tmp/iter23_survival.py` — decompose the shed gate
(`ratio = light(subtree)/size(subtree) < TAU_SHED` -> shed) on the shipped iter-17 model, m and l.

**★ FACT 0, read from the code and not assumed:** `MASS_CAP is None` (retired at iter-20), so
`update_n_def()` returns immediately and **`s_def == 1.0` in every tier, every year.** The S-scaled
shade of iter-15 is NOT LIVE in the shipped tree. Whatever halves survival, it is not an N_def
feedback. (Every ledger entry since iter-20 has reasoned about a term that is switched off.)

**★★ SUSPECT 1 — SELF-SHADING — REFUTED. The l crown is BRIGHTER, not darker.**

      mean light per living foliage marker    m 1.219  ->  l 1.592   = x1.30   (FULL_LIGHT = 6.0)
      light per live tip, at the gated axes   m 8.08   ->  l 14.32   = x1.77

**★★ SUSPECT 2 — BUDS FIRED INTO THE DARK — REFUTED. The stillbirth rate is FLAT.**

      axes born over the life        182 -> 492   = x2.70   (the census wants x3.0)
      of those, born into L = 0      123 -> 342   = x2.78
      stillbirth fraction           68%  -> 70%             <- FLAT. Not the mechanism.

**★★★ WHAT IT ACTUALLY IS — THE CROWN IS UNDER-POPULATED.**

      crown envelope area (hull)   230.7 m2 -> 515.0 m2  = x2.23
      LIVE tips (F_S)                 25   ->    33      = x1.32
      TIP DENSITY ON THE LIT SURFACE 0.108 ->  0.064 /m2 = x0.59   <- HALVES
      => mean tip LIFETIME = 1.32 / 2.70                 = x0.49   <- HALVES

The tree BIRTHS tips at very nearly the census rate (x2.70 vs x3.0) and its buds land in the light
at an unchanged rate. But its live tips are spread over a crown envelope that grew **x2.23**, so the
l crown is not a denser, darker crown — **it is a bigger, SPARSER, BRIGHTER shell.** That is why the
light per marker went UP: fewer neighbours to shade you. The live tip count is a steady state
(births x lifetime), births are right, so **the whole defect is in the LIFETIME, and it halves.**

**★★★ AND WHY THE LIFETIME HALVES — INCOME IS COUNTED AT TIP RESOLUTION, COST AT INTERNODE
RESOLUTION.** At the axes the gate evaluates:

      live tips per woody internode   m 1.000  ->  l 0.118   = x0.118   <- 8.5x more wood per tip
      the gate ratio itself           m 1.810  ->  l 0.593   = x0.327   (TAU_SHED = 0.18)

An l-tier axis carries 8.5x more wood per live tip, so its gate ratio sits **3.4x closer to the
cliff** — and any tip that is momentarily overtopped has no margin left and goes. Note what the
gate is made of: the numerator counts the foliage of the ARMATURE TIPS (12 markers each, and
nothing else on the axis); the denominator counts EVERY WOODY INTERNODE in the subtree. A real
plane's limb bears short shoots along its whole lit length — so its income grows with the limb.
Ours does not. **The A4/A5 layer we deferred is exactly the foliage that would have paid that
bill.** This is the SAME deferral iter-22 indicted for `N_def`, arriving from the other side.

⚠ **The one thing (C) forbids:** do NOT read "wood per tip" as the proximate killer. 96% of the
axes the gate actually sheds are **zero-light single-internode stillbirths** (median L/tip = 0.000),
and they are ~82% of all shed events in both tiers. Wood-per-tip sets the MARGIN, not the cause of
death. A fix must lengthen tip lifetime; it must not merely lower the rent.

**Verification:** three probes in one script, two tier grows, zero model change. The shipped tree
is still the iter-17 tree. Every number above is printed by `tmp/iter23_survival.py`.

verdict: ACCEPTED — the mechanism stood, and iter-24 built on it directly. (Chris: "continue"; an
investigation with no model change has nothing to look at, so acceptance is the proceed.)

- **★★★ A RATIO THAT FALLS HAS TWO SUSPECTS, AND THE ONE THAT COLLAPSES NEED NOT BE THE ONE THAT KILLS.** The shed gate's ratio fell x0.33 from m to l, entirely through its denominator (wood per tip, x8.5) — an airtight decomposition that named the wrong culprit. Asking the *next* question ("so which axes does the gate actually shed?") showed 96% of the kills were **zero-light stillbirths**, and the collapsing denominator was setting the **margin**, not causing the death. **Decomposing a statistic tells you where it moved; only looking at the individual EVENTS tells you what it did.** Never stop at the decomposition. (iter-23)
- **★★ CHECK THE FLAG BEFORE THE THEORY — A RETIRED TERM READS EXACTLY LIKE A LIVE ONE.** `MASS_CAP` was set to `None` at iter-20, which makes `update_n_def()` return immediately and pins `s_def == 1.0` in every tier. Three iterations then theorised about S-scaled self-shading — a mechanism that was **switched off** — because the code, the comments and the ledger all still described it in the present tense. **A one-line guard clause silently deletes every downstream mechanism, and nothing in the source announces it.** Grep the kill-switch constants before building a theory on the machinery they gate. (iter-23)
- **★ WHEN AN OUTPUT IS "TOO LOW", ASK WHETHER IT IS A RATE OR A STEADY STATE.** Six iterations attacked a live-tip count as if the tree were failing to MAKE tips. It was making them at x2.70 (census: x3.0). A steady-state population is `birth rate x lifetime` — and the whole defect was in the **lifetime**, which halved. **Factor the stock into its flow and its residence time before you go looking for the flow.** (iter-23)

## 24 — THE A5 SHORT-SHOOT LAYER. THE TARGET MOVES (F_S 1.32 → 1.61x) AND THE DEFECT SURVIVES.

**Hypothesis (iter-23's mechanism, coded):** foliage lived only at armature apices, so a limb's
income could not grow with the limb, while the shed gate charged it for every woody internode —
so tip LIFETIME halved from m to l. Give every live internode of OLDER wood standing in light its
own A5 short-shoot cohort, and income scales with LIT BRANCH LENGTH instead of with tip count.

**The change** (`scripts/plane_grower.py`, `grow_foliage` + the `SHORT_SHOOT_LIGHT` block). **It
invents no constant:**
- Gate: `light_at(internode) >= TAU_SHED` — the SAME economic bar the shed rule already applies,
  one level down (a unit of wood keeps its foliage if it stands in TAU_SHED of light per unit).
- Density: `P(short shoot per lit internode per year) = FOLIAGE_PER_TIP / GU_NODES[cat]` — the
  linear foliage density the model ALREADY asserts for a lit shoot (a tip bears FOLIAGE_PER_TIP
  markers for the GU_NODES internodes of shoot it makes in a year). ⛔ NOT a full cohort per
  internode: INTERNODE is 0.11 m against VOX 0.6 m, so that is 22 markers per voxel of limb — a
  **30x inflation of the very income ALPHA and TAU_SHED were calibrated against.**
- Only wood born BEFORE this year bears them (this year's shoot IS the tip cohort; foliating it
  twice double-counts). Botanically exact: a proleptic A5 breaks from a lateral bud on old wood.
- Cohorts self-prune on the existing `FOLIAGE_LIFE = 3` — C&E's measured A4/A5 1–4 yr. **That
  constant was always this layer's; it just had nothing to prune.**

**★ LOOP GAIN, COMPUTED BEFORE THE TERM WAS CODED** (`tmp/iter24_gate.py`, on the shipped tree —
the standing rail). The light field over live woody internodes is **BIMODAL**: 40% of them stand at
**exactly zero** light. So the gate BITES on its own, and every theta in [0.0, 0.25] selects the
identical set — **the gate is not a fitted constant**, and that is the strongest form of this result.
Lit internodes m 481 → l 1101 = **x2.29** (the lit SURFACE, x2.23 — not total wood) ⇒ `q = 0.70`,
amplification **3.3x, STABLE** — off the q = 0.92 / 12x bifurcation regime by exactly the light gate.

**Result** (`tmp/iter24_run.py`, all three tiers):

      LIVE TIPS F_S      m 25 -> 28 | l 33 -> 45      l/m  1.32 -> 1.61x   <- THE TARGET, IT MOVES
      LIT FOLIATED LEN   m 324      | l 585           l/m         1.81x    (census bar 3.23)
      => LOOP GAIN q = 0.50, amplification 2.0x       (pre-registered 0.70 / 3.3x — MORE damped)
      SAPWOOD FRACTION   m 9.5 -> 10.4% | l 4.4 -> 5.6%   BOTH ROSE  <- the pre-registered rail
      DBH vs census      s 1.48x  m 0.93x  l 0.95x    (was 1.43 / 0.93 / 0.94)  <- HELD
      DBH l/m ratio      1.021                        (was 1.011)              <- HELD

**★ THE VERDICT I PRE-REGISTERED, AND IT BINDS: the lit length did not reach x3.23, SO THE DEFECT
SURVIVES.** F_S l/m is 1.61 against the census's ~3.0. This is a partial — the first term in nine
iterations to move the target AT ALL without breaking a rail, and it delivers about half of what
is needed. It is not the fix.

**★★ THE SURPRISE, AND IT IS THE FINDING — THE LAYER SHADES ITSELF OUT.** The lit fraction of live
wood **collapsed from 60% (m) / 74% (l) on the shipped tree to 30% / 30%.** The new short shoots'
own shade halved their own lit surface, which is why the realised lit-length ratio (1.81) came in
BELOW the static prediction (2.29) and why q was damped to 0.50. **The negative feedback that keeps
us off the bifurcation is the same thing capping the income.** It is not a bug — it is the physics
we asked for — but its magnitude was not predicted.

**★★★ AND THE FLAT 30% MOVES THE DEFECT.** Lit length now tracks **total live wood** almost exactly
(x1.81 vs x1.77) — so income DOES scale with limb length now; that half is genuinely fixed. But:

      live woody internodes   m 1087 -> l 1920  = x1.77
      tree mass                                 = x3.28
      axes born               m  186 -> l  516  = x2.77   (births were never the problem)

**The l tree carries 3.28x the mass on 1.77x the live wood. It is not KEEPING enough limb.** The
question is no longer "why doesn't income scale with the limb" (it does) but **"why does the tree
still shed so much of the limb it built?"**

**Verification:** all three tiers grown to their census ages (`tmp/iter24_run.py`, 2m27s, exit 0).
Every number above is printed by that script. DBH and sapwood rails read from the model, not
estimated; the sapwood baselines are iter-21's `A_sap/A_heart` = 0.105 / 0.046 inverted.

verdict: PENDING

- **★★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM — AND THE PROBE MAY ALSO TELL YOU THE GATE IS FREE.** The pre-registration probe was run to get `q`. It also showed the light field over woody internodes is BIMODAL (40% at exactly zero), so every threshold in [0, 0.25] selects the same set — **the gate's constant does not matter, and a constant that cannot be fitted cannot be the fit.** A probe run for one number can retire a whole class of "but you tuned it" objections for free. Look at the DISTRIBUTION, not just the summary statistic you came for. (iter-24)
- **★★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT.** The obvious coding of "foliate every lit internode" was to give each one a tip's cohort — which, at INTERNODE 0.11 m against VOX 0.6 m, is 22 markers per voxel of limb and a **30x inflation of the income that the economy's constants were calibrated against.** The change would have "worked" and detonated every calibration downstream. When extending a quantity to a new unit, carry over its **density per unit of the thing it lives on**, and check that density against the resolution of the grid that will consume it. (iter-24)
- **★ A STABILISING FEEDBACK AND AN INCOME CAP CAN BE THE SAME TERM.** The light gate is what kept the loop gain at 0.50 instead of 0.92 — and it is also why the layer delivered half the income needed: the new foliage's own shade halved its own lit surface (lit fraction 60/74% → 30/30%). **The mechanism that saves you from the bifurcation is the mechanism that starves you.** Expect any self-shading negative feedback to under-deliver against its static prediction, and measure how much BEFORE reading the shortfall as a separate defect. (iter-24)

## 25 — THE LIGHT LAW WAS SATURATED (Beer–Lambert). THE FIELD IS REPAIRED AND THE DEFECT SURVIVES.
*(backfilled 2026-07-13: iter-25 shipped as `b6381e0` + `bf3fdb2` but its LEDGER entry was never
written — the STATE rewrite was mistaken for the record. Append-only means APPEND, every time.)*

**Hypothesis (pre-registered, `tmp/iter25_prereg.md`):** the tree does not KEEP the limb it builds
(kept% m 56.7 / l 41.2) because the shed gate's numerator is read through a SATURATED instrument.
`light_at` was `max(C - shadow + own, 0)` — Palubicki, coded faithfully — and it CLAMPS: the clamp
sits at 7 while the shadow field runs to 30, so past 7 the law returns 0.000 at EVERY depth. **73%
(m) / 69% (l) of live woody internodes read EXACTLY zero light.** The shed gate is a RATIO test on
that numerator, so it never measured light — it read a saturation flag.

**Change:** `light_at` = `C * exp(-(s - own)/C)` — Beer–Lambert, the unique exponential TANGENT to
the old law at s = own, so the calibrated lit regime is preserved to first order and NO constant is
invented. Runs became ~4x slower (s+m+l: 2m26 → 9m46).

**Verification** (`tmp/iter25_retention.py`, `tmp/iter25c_saturation.py`):

      P1 [TARGET]  live wood l/m   1.77 -> 1.91x     FAIL   (pre-registered PASS >= 2.40x)
      P2  kept%   m 56.7 -> 66.0 | l 41.2 -> 59.6    PASS ; KILLED l/m 3.30 -> 2.52x  PASS
      P3 [UNTARGETED]  sapwood  m 10.4 -> 22.0% | l 5.6 -> 13.8% | s 21.1 -> 50.4%    PASS
      R1  DBH/census 0.93/0.95 -> 1.09/1.08 (7% under -> 8% over; l/m HELD 1.02 -> 0.99)
      R2  self-pruning alive, no runaway                                              PASS

**★★★ F1 FIRED, AND THAT IS THE FINDING: the light field is now sound and THE DEFECT IS STILL
THERE ⇒ THE DEFECT WAS NEVER IN THE LIGHT.** The whole shading/light family (15, 20, 23, 24, 25) is
CLOSED. The A5 isotropic-placement suspect is refuted with it (mirror/here = 0.98/1.00 — no gradient
to climb), and iter-23's stillbirth finding is true by COUNT and irrelevant by WOOD (53–60% of kill
events, only 10–13% of the lost wood).

verdict: ACCEPTED (Chris: "let's continue") — the repair stands; iter-26 tested the theory it left.

## 26 — THE DENOMINATOR, MEASURED: EVERY FORM FAILS — AND THE CENSUS REFUTES THE THEOREM ITSELF.

**Hypothesis (STATE's, from iter-25):** income is bounded per column (Beer–Lambert) ⇒ ∝ R²; the
gate's denominator is an internode COUNT ⇒ ∝ crown volume ∝ R³; so the gate ratio ∝ 1/R and **the
gate condemns bigness by construction.** The fix: bill only LIVING tissue (heartwood is dead and
costs nothing) — sapwood is a shell ∝ R²·H, so the ratio becomes size-invariant. STATE bound this
iteration to MEASURE the lever before coding the term. It was measured (`tmp/iter26_denominator.py`,
`tmp/iter26b_leafgate.py`, read-only, both tiers to census age).

**(1) EVERY DENOMINATOR THE TREE OWNS FAILS — including the two STATE proposed:**

      denominator                    m        l     lever l/m   gate ratio l/m
      INCOME   L (live light)    2353.6   3091.6      1.314          —
      count    Σ1                2224     4256        1.914        0.686   <- today
      sap_frac Σ r_s²/r²         1889.3   3112.8      1.648        0.797   <- 16% relief only
      sap_vol  Σ π r_s² ℓ         1.35 m³  2.96 m³    2.189        0.600   <- WORSE than the count
      LEAVES   F (live markers)  2310     3872        1.676        0.784   <- branch autonomy

- **The unit-preserving `Σ sap_frac` is the weak lever STATE feared:** fine twigs are ~100% sapwood
  (mean D1/D0 = 0.999 on single-internode subtrees), so the sum is 85% (m) / 73% (l) of the count.
- **★ SAPWOOD IS NOT A SHELL IN THIS MODEL — its volume grows FASTER than the internode count
  (2.189x vs 1.914x).** Summed over a crown, `Σ r_sap²` is super-linear: the l tree's limbs are
  thicker and its paths longer. The pipe-model `R²·H` intuition is about a TRUNK CROSS-SECTION, not
  a crown sum. The "honest denominator" makes the gate TIGHTER with size. **REFUTED.**
- **And the physiologically correct bill — the LEAVES (branch autonomy: a limb dies when its own
  foliage cannot pay for its own foliage) — fails too:** 0.784. Mean light per leaf falls 22% m→l,
  because foliage (1.676) also outgrows income (1.314).

**(2) ★★★ THE CENSUS REFUTES THE THEOREM.** From the UTD table already in the grower (McPherson/van
Doorn/Peper 2016, PSW-GTR-253, `plane_grower.py:2065`): real m = DBH 43.2 cm, crown dia 12.6 m; real
l = DBH 71.1 cm, crown dia 16.9 m.

      real crown PROJECTED AREA   l/m = (16.9/12.6)² = 1.80
      real BASAL AREA             l/m = (71.1/43.2)² = 2.71
      => REAL light per unit wood l/m = 1.80/2.71   = 0.664
         MODEL light per unit wood l/m              = 0.686      <- WE ALREADY MATCH IT

**A real London plane's intercepted light per unit of standing wood ALSO falls ~1.5x from m to l.
The R²/R³ "exponent error" is not a defect — it is physics, and the census has the same exponent.
The gate's size-scaling was already correct.** Ten iterations of numerator work and this iteration's
entire denominator plan were aimed at a quantity that was never broken.

**(3) ⇒ THE DEFECT IS THE LEVEL, NOT THE SLOPE — AND IT IS ONE DEFICIT, NOT TWO:**

      quantity      model l/m    census l/m    shortfall
      income  L       1.314        1.80          -27%
      live wood S     1.914        2.71          -29%

**The l tree is short by ~28% in income AND in wood, in the SAME proportion.** The gate ratio is
right precisely because both sides shrank together. There is no economic term to add: the tree
simply never gets big enough. Under Beer–Lambert income ≈ C/(1-e^(-1/C)) × OCCUPIED COLUMNS ≈ the
crown's projected area — so a 27% income shortfall IS a 27% projected-area shortfall, and iter-9's
"crown width matches census (1.07x / 1.05x)" was measured on the HULL. **A hull can be right while
its columns are empty — which is exactly what iter-23 saw ("the crown is not darker, it is emptier")
and then set aside on a counting technicality.**

**Verification:** both probes grew m and l to census age (47 / 104 yr) under the shipped grower, exit
0; every number above is printed by them (`tmp/iter26_denominator.log`, `tmp/iter26b_leafgate.log`).
The census numbers are read from the UTD table in the source, not estimated. No model change: this
iteration is a REFUTATION, and it retires a family.

verdict: ACCEPTED (Chris: "continue working on london plane") — the refutation stands; iter-27
         goes measuring for the missing 27%, as STATE directs.

## Staged lessons (iter-26)

- **★★★ CHECK YOUR "STRUCTURAL THEOREM" AGAINST THE DATA BEFORE YOU BUILD ON IT.** iter-25 proved
  a beautiful theorem — income ∝ R², cost ∝ R³, so the gate condemns bigness by construction — and
  it was TRUE. It was also true of the real tree: the census's own numbers give the SAME falling
  ratio (0.664 vs our 0.686). **A derivation that indicts the model can be indicting reality, and a
  scaling argument is only a defect if the ground truth does NOT show the same scaling.** The census
  was on disk the whole time; the theorem cost a full iteration because nobody divided two numbers
  from it. Ratios of ground-truth quantities are the cheapest falsification there is — run them
  BEFORE the derivation becomes load-bearing. (iter-26)
- **★★ A SHORTFALL THAT IS EQUAL ON BOTH SIDES OF A RATIO IS INVISIBLE IN THE RATIO — AND IT IS THE
  DEFECT.** Income −27%, wood −29%: the gate ratio looked fine (and was fine) while the tree was
  uniformly too small. **When a ratio is healthy, measure its NUMERATOR AND DENOMINATOR against
  ground truth SEPARATELY, in absolute terms.** Every iteration since 15 optimised the ratio; none
  ever asked whether both of its terms were 30% short. (iter-26)
- **★ AN ANALOGY IMPORTED FROM A PAPER MUST BE RE-DERIVED IN THE MODEL'S OWN GEOMETRY.** "Sapwood is
  a shell, ∝ R²·H" is true of a TRUNK CROSS-SECTION and false of a SUM OVER A CROWN (measured:
  Σ r_sap² grows 2.19x against the count's 1.91x). The pipe model was not wrong — the transfer was.
  Measure the quantity you are actually going to sum. (iter-26)

## 27 — THE CROWN STOPS WIDENING. THE BULK RADIUS *FALLS* m→l. (investigation; no model change)

**Pre-registered** (`tmp/iter27_prereg.md`, written before the run): the −27% income deficit is a
crown **FILL** defect — hull census-sized (iter-9), columns sparse inside it, fill FALLING m→l.
Probe `tmp/iter27_columns.py` (read-only, m + l to census age). Rails held: DBH 47.1 / 76.5 cm
(1.09x / 1.08x), sap_frac 22.0 / 13.8% — unchanged, so the instrument is sound.

**★ BOTH PRE-REGISTERED PREDICTIONS ARE REFUTED, and the third outcome is the true one.**

**1. FILL IS CONSTANT.** columns/hull = 0.341 (m) → 0.344 (l), lever **1.010**. The crown does *not*
empty with size. iter-23's "it is emptier" is dead as a *size* explanation.

**2. THE COLUMN FRAME HOLDS.** income per occupied column 8.72 → 8.01 (lever **0.919**) — Beer–Lambert
bounds it, as STATE said. So income ≈ 8.4 × columns, and **income is exactly as short as the columns
are**: columns lever **1.430** · income lever **1.314** · census bar **1.799**.

**3. ★★★ AND THE COLUMNS ARE SHORT BECAUSE THE CROWN STOPS WIDENING.** The radial distribution of the
live foliage about the trunk axis (m → l, against census R 6.3 → 8.45 m, which demands **×1.34**):

      p50   6.67 → 6.22 m   lever 0.933   (1.06x → 0.74x census)   ← THE BULK MOVES *INWARD*
      p75   9.12 → 9.27     lever 1.017
      p90  11.02 → 11.66    lever 1.058
      p100 14.68 → 18.77    lever 1.278   (2.33x → 2.22x census)   ← the tail runs away
      woody armature p50: 6.64 → 5.63 m (lever 0.849) — the WOOD does it too, not just the leaves

**The median leaf is at the same 6–6.7 m from the trunk at 47 yr and at 104 yr.** The tree adds its
new foliage *inside* (interior short shoots, iter-24's A5 layer) and along a few runaway limbs, and
almost none of it out at a widening periphery. Meanwhile height goes 15.25 → 22.98 m (×1.51, and
1.20x the UTD H of 19.1). **The `l` tree grows UP, not OUT.**

**4. ⇒ THE iter-9 HULL RAIL IS REFUTED — AND IT WAS RIGHT FOR THE WRONG REASON.** The hull is not
short; it is *oversized* (area-equiv. radius 1.51x / 1.34x census, hull area 2.29x / 1.80x the census
disc) — inflated by the p95–p100 tail. **A hull can be right — or too big — while its BULK is short.**
The pre-registered mirror of iter-23's lesson, and the hull was the instrument both times.

**5. And this is why every economic term failed.** The gate, the numerator, the denominator, the light
law: none of them can be wrong, because **the income shortfall is not economic at all — it is
GEOMETRIC.** The tree cannot earn a census income from a crown whose leaves never leave a 6 m radius.

verification: `tmp/iter27_columns.log`. Read-only; nothing shipped, nothing to regress.
verdict: PENDING

## Staged lessons (iter-27)

- ★ **A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION.** Two rails (iter-9's crown width, iter-23's
  emptiness) were both artifacts of measuring a crown by its *envelope*. The p50 and the p100 moved in
  OPPOSITE directions here. Read the percentiles, always — the statistic you came for hides the shape.
- ★ **WHEN EVERY ECONOMIC TERM IS EXONERATED, THE DEFECT IS NOT IN THE ECONOMY.** Iters 15–26 spent
  twelve sessions inside the light/gate/allocation economy because the deficit was *stated* in
  economic units (income, wood). It was geometric the whole time. Ask what SHAPE the ground truth
  demands before asking what the tree can afford.

## 28 — THE APICES: THE RIM STARVES BESIDE A LEAK. 95% OF THE EXTENSION BUDGET EVAPORATES.

hypothesis (pre-registered, `tmp/iter28_prereg.md`): the crown's bulk radius stalls (0.93x m→l vs the
census's 1.34x) because of the **extension geometry** — either P1 the arch/droop aims new growth down
instead of out, P2 the rim is unfunded, or P3 (lead) the `vigour` decay makes each axis's reach a
convergent series so nothing is born at the rim.

change: **NONE. Read-only probe** (`tmp/iter28_apices.py`), a `Grower` subclass instrumenting three
hooks (`grow_module`, `posture`, `shed`). Rails reproduce iter-27 exactly ⇒ the instrument is sound:
DBH 47.1 / 76.5 cm = **1.09x / 1.08x** census · sap_frac **22.0 / 13.8%** · crown p50 **6.67 → 6.22 m**
· self-pruning alive (6 shed in the final year).

**1. ALL THREE PRE-REGISTERED PREDICTIONS ARE REFUTED.**
- **P1 DROOP — DEAD.** `posture()` does not move existing nodes; it only rotates `ax.dirv`. And at the
  rim it *raises* it: dy `−0.339 → −0.266`. Peripheral apices aim solidly **outward** (out = +0.24 to
  +0.66). The arch is not eating the reach. ⇒ `arch`/`DROOP_K` is **exonerated as the geometric root.**
- **P3 VIGOUR CEILING — DEAD.** Peripheral vigour holds **0.69–0.83** through the late decades. The
  senescence decay is not what stops the rim.
- **P2 STARVATION — REFUTED AS STATED, AND TRUE OF THE INDIVIDUAL.** The rim as a *class* is **rich**:
  it takes **60–85% of the whole year's pool** while being ~20% of apices. Yet only ~20% of individual
  peripheral apices can afford one internode. **The class is rich and the median member has nothing.**

**2. ★★★ THE RIM'S BUDGET IS WINNER-TAKE-ALL.** `l_afford / INTERNODE` among peripheral apices, l run:
from decade 41 on the **median is 0.000** while the **max reaches 20–83 internodes**. Gini **0.83–0.96**;
the **top THREE apices take 39–100%** of the rim's entire budget. The dormancy floor is ~0.025, so the
median rim apex is two orders of magnitude below being able to move at all → dormant → `DORMANT_ABORT`
(3 yr) kills it. **The widening front is not a front. It is three limbs.** (⇒ iter-27's p100 runaway at
18.8 m / 2.2x census and its 0.74x starved bulk are ONE phenomenon, not two.)

**3. ★★★ AND THE WINNERS CANNOT SPEND IT. THE POOL LEAKS.** `ext = min(1, l_afford/INTERNODE) · vigour`
— an apex holding **83 internodes' worth grows exactly the same module as one holding 1.0**, and
`allocate_resource()` zeroes `_v` every year, so the surplus is **discarded, not banked**. Measured over
the whole `l` run (`tmp/iter28_raw.npz`): allocated to terminal buds **3,491,679 cm³**, actually spent on
extension **173,142 cm³** ⇒ **95.0% EVAPORATES**, rising 33% → **98.8%** by the last decade, and **99.7%
of the loss is at apices sitting OVER the clamp.** (A floor, not a point estimate: the formula credits
dormant apices with phantom spending.) `_v` is set only for `kind == "apex"` (line 1687), so the shares
telescope and this is not a double-count.

**4. ⇒ THE DEVIATION FROM THE PRIOR ART IS THE LEAK.** The code comments cite Palubicki, where
**`n = floor(v)`, `l = v/n`** — a rich apex buys **MORE METAMERS**. Here `n = GU_NODES[cat]` is **FIXED**
and only `l` scales, capped at `INTERNODE`. So resource has exactly one sink, and it saturates. Line 1671
says *"Resource is CONSERVED: what a lateral does not get, the leader does"* — **true of the SPLIT, false
of the SPEND.** The leader gets it and burns it against the clamp.

**5. ⇒ THIS IS WHY TWELVE ITERATIONS OF ECONOMICS DID NOTHING, AND IT DOES NOT RE-OPEN THEM.** Every one
of them changed the SIZE of the pool. **95% of the pool is thrown away at the clamp regardless of its
size** — doubling income doubles the waste and moves the crown almost not at all. The economy's
exoneration (iters 22/25/26) is *explained*, not contradicted: the defect is in the **SPEND LAW and the
VARIANCE of the split**, neither of which is a gate, a light term, a denominator, or a TAU.

verification: `tmp/iter28_apices.log` (rails + all five sections), `tmp/iter28_raw.npz` (raw per-apex
per-year log). Read-only; nothing shipped, nothing to regress.
verdict: PENDING

## Staged lessons (iter-28)

- ★★ **A CLAMPED SINK IS A LEAK.** `min(1, ...)` on the only thing resource can buy silently discards the
  surplus. Nothing in the ledger, nothing in the income, no error — just 95% of the budget gone. **Audit
  every saturating term for what happens to the REMAINDER**, and make conservation an assertion, not a
  comment: if a pool is conserved, MEASURE `allocated − spent` and print it.
- ★★ **"THE CLASS IS RICH" IS NOT "THE MEMBER IS FUNDED."** The rim held 60–85% of the pool and its median
  member had 0.000. A per-class mean is the same instrument error as a hull (iter-27), one level up:
  **when a group statistic and an individual outcome disagree, measure the GINI.**
- ★ **CHECK THE CITED PRIOR ART'S EQUATION, NOT ITS NAME.** The code cites Palubicki's `n = floor(v)` in a
  comment and then implements a FIXED `n`. The deviation was in the docstring the whole time.
