# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-24 SHIPPED the A5 short-shoot layer** (`grow_foliage` + the `SHORT_SHOOT_LIGHT` block). Every
live internode of OLDER wood standing in `light >= TAU_SHED` now bears short-shoot foliage at the
linear density the model already asserted for a lit shoot (`FOLIAGE_PER_TIP / GU_NODES[cat]`), self-
pruning on the existing `FOLIAGE_LIFE = 3`. **It invents no constant.** Income now scales with LIT
BRANCH LENGTH, not with tip count. Probes: `tmp/iter24_gate.py` (pre-registration), `tmp/iter24_run.py`.

      LIVE TIPS F_S      l/m  1.32 -> 1.61x   <- THE TARGET MOVES (census wants ~3.0)
      SAPWOOD            m 9.5 -> 10.4% | l 4.4 -> 5.6%   BOTH ROSE — the pre-registered rail HELD
      DBH vs census      1.48 / 0.93 / 0.95x  (was 1.43 / 0.93 / 0.94)  <- HELD, l/m ratio 1.021
      LIT FOLIATED LEN   l/m  1.81x          (census bar 3.23)  <- SHORT
      LOOP GAIN q = 0.50, amplification 2.0x  (pre-registered 0.70 / 3.3x — stable, more damped)

- **★ THE PRE-REGISTERED VERDICT BINDS: lit length did not reach x3.23, so THE DEFECT SURVIVES.** The
  first term in nine iterations to move the target at all without breaking a rail — and it delivers
  about **half** of what is needed. A partial. **Do not call it the fix.**
- **★★ THE LAYER SHADES ITSELF OUT** — the finding, and it was not predicted. Lit fraction of live wood
  **60% (m) / 74% (l) → 30% / 30%.** The new foliage's own shade halved its own lit surface: the
  realised lit-length ratio 1.81 came in BELOW the static 2.29, and q damped 0.70 → 0.50. **The
  feedback that keeps us off the bifurcation is the same one capping the income.**
- **★★★ AND THE DEFECT HAS MOVED.** Lit length now tracks total live wood almost exactly (x1.81 vs
  x1.77) ⇒ **income DOES scale with the limb now; that half is genuinely fixed.** What remains:

      live woody internodes   m 1087 -> l 1920  = x1.77
      tree mass                                 = x3.28
      axes BORN               m  186 -> l  516  = x2.77   (births were never the problem)

  **The l tree carries 3.28x the mass on 1.77x the live wood. IT IS NOT KEEPING THE LIMB IT BUILDS.**

## Open defects

1. **★★ THE TREE SHEDS TOO MUCH OF THE LIMB IT BUILDS** — Defect 1, restated for the third time and
   now on the *retention* side. Not income scaling (fixed), not shade level, not the birth rate.
2. **Caliber splay** — `s 1.48, m 0.93, l 0.95`. One-sided, all in `s` (a constant `N_def` over-serves
   the sapling). Unchanged by iter-24.
3. **Sapwood is 10.4% / 5.6% against a ~50% census.** Moving, and nowhere near.
4. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-25: WHY DOES THE TREE NOT KEEP ITS LIMB? MEASURE BEFORE YOU CODE.

- **★ This is an INVESTIGATION, not a term.** iter-23's lesson: *decomposing a statistic tells you where
  it moved; only looking at the individual EVENTS tells you what it did.* Extend
  `tmp/iter23_survival.py` to the iter-24 tree and ask the shed gate, per event, at m and at l:
  **which axes now die, at what age, against what ratio?** Re-read the stillbirth share first (96% of
  kills at iter-23) — **the A5 layer cannot have touched it**, because a single-internode newborn has no
  old wood to bear short shoots on. **If stillbirths are still ~96% of kills, then the retention defect
  and the lifetime defect were never the same defect**, and the one we just half-fixed was the smaller.
- **★ The concrete suspect — but PROVE IT FIRST:** short shoots are placed **isotropically**
  (`FOLIAGE_SPREAD` in a random direction), so roughly half fire INWARD into the limb's own shade —
  paying shade, earning nothing. A real A5 short shoot is borne on the lit flank. If the probe says the
  interior markers gather ~0, orienting the shoot away from the local shade gradient is a principled,
  constant-free fix, and it attacks the 60/74% → 30/30% collapse directly.
- **⚠ Two candidate defects are now live (retention, self-shading) and they are entangled.** Measure
  which one owns the x1.77 before coding either.
- ⛔ **Still do NOT touch TAU_SHED**, and do not re-fit `ALPHA`/`DBH_CALIB` to chase a level — **DBH
  HELD, so there is nothing to centre.** A scalar may CENTRE and UN-SUPPRESS; it may never FIX.

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE `N_def` NUMERATOR FAMILY IS CLOSED (iter-22).** No variable the tree owns grows faster
  than the x3.23 the census demands ⇒ every `L = K*X^q` has gain >= 0.987. **Do not propose a seventh
  numerator.** Dead: `V_crown` (15), `M_sub` linear (20), `V_sap` (21), `M^q` (22). ⚠ The family test
  assumes the tree's X-trajectory is FIXED — deriving a deferred LAYER changes X itself, so it is not a
  member. iter-24 was exactly such a layer, and it cleared the bar the family could not.
- ⛔ **★ …AND DO NOT CODE `M^(3/4)`.** It is an **output** of the heartwood law we already simulate
  (Berry 2024, opened), not an input.
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20; honoured by iter-24). ★ And read the
  probe's DISTRIBUTION, not only the statistic you came for: iter-24's light field is **bimodal** (40%
  of woody internodes at exactly zero light), which is why **the A5 gate's constant cannot be fitted at
  all** — every theta in [0, 0.25] selects the same set.
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` = 0.11 m against
  `VOX` = 0.6 m — a full cohort per internode would have been a **30x** inflation of the income the
  economy's constants were calibrated against.
- ⛔ **★ Solve a loop's constant INSIDE the loop** (iter-19). ★ A root-find that CONVERGES can still be
  the refutation: report the local SENSITIVITY with the root. >=10x means unsolvable.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age. **b(n) is the
  VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). ⇒ **target a RATIO.**
- ⛔ **STATICS IS EXONERATED** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **SELF-SHADING AS THE *LIFETIME* KILLER IS REFUTED** (iter-23) — the shipped l crown was BRIGHTER.
  ⚠ iter-24 re-opens self-shading on a **different charge** (the A5 layer shading its own lit surface),
  on a different tree, with new evidence. Do not confuse the two.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⛔ **EXONERATED FOR CROWN WIDTH — do not re-indict *for width*:** the tip budget (iter-11), the shed
  rule, `MAX_CAT`, the reiteration rate, `N_def` accumulating with tip AGE, the statics. **The crown was
  never 2x too wide.** If the width verdict is ever threatened, STOP.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13. On
  disk (`tmp/papers/`, gitignored): Aye 2022 (equations are GIF images), Hellström 2018. Berry 2024 +
  Xu 2014 opened in iter-21 (web).
- ⚠ **Instrument limit:** seed spread is 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%).**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP` is **None** ⇒ `s_def == 1.0` always, so
  the iter-15 S-scaled shade is NOT live. Also `S_IN_SHADE`, `S_IN_LIGHT`, `MAX_CAT`. A retired term
  reads exactly like a live one in the source.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
