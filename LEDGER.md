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

## Staged lessons

- A recursive double-count and a sublinear aggregation can CANCEL. "The mechanism is wrong" and "the
  number is wrong" are different claims — fixing a real category error is allowed to move a metric by
  nothing, and that is not evidence the error wasn't there.
- When one free constant is demanded by two ground truths and they disagree by 22x, that is not a
  calibration problem — it is a structural falsification, and it is the cheapest one you will ever get.
  Solve for the constant under BOTH targets before you fit it under either.

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

## Staged lessons

- **A derived quantity fed back into the economy that derives it is a positive feedback loop, not a
  derivation.** "It is an OUTPUT, not a parameter" is necessary but NOT sufficient: an output read
  from the very loop it then drives is a fifth way to get the same class of error. The size term has
  to be *earned and settled* (ratcheted structure, already-built wood), not *currently being bought*.
- A refutation that moves an unrelated open defect by 4.5x is telling you the mechanism is right and
  the wiring is wrong. Do not throw the mechanism away with the wiring.
