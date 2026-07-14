# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-25 was an INVESTIGATION, and it found the instrument broken. It repaired it, and the repair
FAILED ITS OWN TARGET — which is the most useful thing that has happened in ten iterations.**
Probes: `tmp/iter25_retention.py` (the wood ledger), `tmp/iter25b_conduit.py`,
`tmp/iter25c_saturation.py` (the instrument audit), `tmp/iter25_prereg.md` (binding), commit `b6381e0`.

      P1 [TARGET]  live wood l/m   1.77 -> 1.91x     FAIL   (pre-registered PASS >= 2.40x)
      P2  kept%   m 56.7 -> 66.0 | l 41.2 -> 59.6    PASS
          KILLED l/m       3.30 -> 2.52x             PASS
      P3 [UNTARGETED]  sapwood  m 10.4 -> 22.0% | l 5.6 -> 13.8% | s 21.1 -> 50.4%   PASS
      R1  DBH/census  0.93/0.95 -> 1.09/1.08 (7% under -> 8% over; l/m ratio HELD 1.02 -> 0.99)
      R2  self-pruning alive, no runaway            PASS

- **★★ THE INSTRUMENT WAS SATURATED.** `light_at` was `max(C - shadow + own, 0)` — Palubicki, coded
  faithfully. It CLAMPS: the clamp sits at **7** and the shadow field **runs to 30**. Past 7 the law
  returns 0.000 at *every* depth ⇒ ~77% of the dynamic range discarded. **73% (m) / 69% (l) of live
  woody internodes read EXACTLY zero light.** The shed gate is a RATIO test on that numerator, so it
  never measured light — it read a saturation flag. Now `C * exp(-(s - own)/C)`: Beer–Lambert, the
  unique exponential TANGENT to the old law at s=own, so the calibrated lit regime is untouched and
  **no constant is invented**. ⚠ Runs are now **~4x slower** (s+m+l: 2m26 → 9m46).
- **★★★ AND F1 FIRING IS THE FINDING. The light field is now sound and THE DEFECT IS STILL THERE ⇒
  THE DEFECT WAS NEVER IN THE LIGHT.** The entire shading/light family — iters 15, 20, 23, 24, 25 —
  is CLOSED. Read the refutation for what it exonerates.
- **★ The A5 isotropic-placement suspect is REFUTED** (mirror/here = 0.98 / 1.00 — there is no
  gradient to climb). **And iter-23's stillbirth finding was true by COUNT and irrelevant by WOOD:**
  stillbirths are 53–60% of kill *events* but only **10–13% of the lost wood**. The currency of a
  retention defect is internodes, and iter-23 weighed events.

## ★★★ WHY THE TREE CANNOT SCALE — the structural argument, and it is a THEOREM about this model

Chris asked for the day we say *we can't build a tree this way, and why*. **This is not that day** —
but it is the day the *why* stopped being a mystery. All ten failed iterations have one cause:

1. **INCOME IS BOUNDED PER COLUMN, hence ∝ R².** Under Beer–Lambert a vertical column of stacked
   markers earns `C·Σ exp(-j/C)` = `C/(1 - e^(-1/C))` ≈ **39, no matter how many markers stand in
   it.** (Under the old clamped law it was likewise bounded, ~21.) So total income ≈ 39 × the number
   of occupied columns = **39 × the crown's PROJECTED AREA**. No light law changes this — a canopy
   cannot absorb more than falls on its silhouette. **INCOME ∝ R².**
2. **COST IS THE INTERNODE COUNT, hence ∝ R³.** The gate's denominator `S` = woody internodes in the
   subtree. A crown that fills its volume with twigs has **S ∝ crown VOLUME ∝ R³.**
3. **⇒ ratio = L/S ∝ R²/R³ = 1/R.** **THE GATE'S RATIO FALLS MONOTONICALLY WITH TREE SIZE, FOREVER,
   BY CONSTRUCTION. A tree twice as big has half the light per internode. THE GATE CONDEMNS BIGNESS
   ITSELF** — and it must shed its own interior to stay solvent, which is exactly what the ledger
   shows (l builds 2.43x, keeps 1.77x, kills 3.30x, against a census bar of 3.23x).
4. **⇒ AND THAT RETRO-EXPLAINS THE WHOLE FAILURE HISTORY.** Every numerator (15, 19, 20, 21, 22),
   the A5 layer (24) and the light law (25) tried to raise `L` or redistribute it. **None of them
   can change the R²/R³ exponent.** The ratio has crept **1.32 → 1.61 → 1.77 → 1.91** and never
   approached 3.23 because *the exponent is wrong, not the coefficient.* We have been fitting
   coefficients to an exponent error for ten iterations.

## NEXT — iter-26: THE DENOMINATOR. ⚠ MEASURE Σ sap_frac FIRST; DO NOT CODE IT BLIND.

**The resolution is in the denominator, and THE MODEL ALREADY CONTAINS THE LAW.** The pipe model
(Shinozaki 1964): **leaf area ∝ sapwood area.** We already simulate heartwood formation (iters
12–14, "the heartwood law is DONE"). Sapwood is a **SHELL** — sapwood volume ∝ R²·H, **not R³** — and
maintenance respiration is borne by LIVING tissue only: **heartwood is metabolically dead and costs
nothing.** So the physiologically correct denominator scales as **R², matching income's R², and the
ratio becomes SIZE-INVARIANT.** The gate stops condemning bigness.
⇒ **The gate's denominator is the one quantity in the model that the model's OWN physiology says is
wrong.** Two already-simulated laws contradict each other, and the gate is on the losing side.

- **⚠ THE UNIT-PRESERVING FORM MAY BE A WEAK LEVER — THIS IS THE THING TO MEASURE.** The tempting
  version is *cost per internode = its sapwood FRACTION* (∈[0,1]), which preserves `TAU_SHED`'s units
  and calibration exactly (a young twig is ~100% sapwood ⇒ costs 1, unchanged — and twigs are where
  TAU was calibrated). **But the internode count is dominated by fine twigs, and fine twigs have
  sap_frac ≈ 1.** If `Σ sap_frac_i ≈ Σ 1`, NOTHING MOVES. **Measure `Σ sap_frac_i` against `Σ 1` per
  gated subtree, at m and at l, BEFORE writing the term.** Report the l/m ratio of the two sums —
  that ratio IS the loop's lever arm, and if it is ~1.0 the term is dead on arrival.
- **If it is weak, the honest denominator is sapwood VOLUME** (`Σ sap_area_i × INTERNODE`). That
  changes TAU's units. TAU is the one scalar we are allowed to fit — but **ONLY against its
  independent ground truth (the measured `cb_frac ≈ 0.30`), NEVER to chase l/m.**
- **★ PRE-REGISTER, and include the rails.** DBH must not drift further (it is now 1.09/1.08 —
  already 8% over; a second unforced level shift is a refutation). Sapwood must keep RISING toward
  ~50%. Self-pruning must stay alive (kept% < 90%).
- **★ AND THIS IS THE DAY-WE-SAY-SO TEST.** If the sapwood denominator is measured and *also* cannot
  deliver R² scaling, then this model's cost structure cannot be reconciled with its income
  structure, and **the developmental grower is refuted for cross-size allometry.** Say it, don't
  grind. That verdict is now one measurement away — which is why the measurement must be clean.

## Open defects

1. **★★ THE EXPONENT, not the coefficient** (above). Live wood l/m **1.91x**, census bar 3.23x.
2. **Caliber splay** — `s 1.53, m 1.09, l 1.08`. Still one-sided, all in `s`. Unchanged in kind.
3. **Sapwood 22.0% / 13.8%** against ~50% census — **moving fast now** (was 10.4 / 5.6), and `s`
   already lands on 50.4%. Plausibly the SAME defect as (1); do not chase it separately.
4. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE LIGHT/SHADING FAMILY IS CLOSED (iter-25).** The field is now sound and the defect
  survived ⇒ it was never in the light. **Do not propose another light, shade or placement term.**
- ⛔⛔ **★★★ THE `N_def` NUMERATOR FAMILY IS CLOSED (iter-22).** No variable the tree owns grows
  faster than the x3.23 the census demands ⇒ every `L = K*X^q` has gain >= 0.987. **Do not propose a
  seventh numerator.** Dead: `V_crown` (15), `M_sub` linear (20), `V_sap` (21), `M^q` (22).
  ★ iter-25 explains WHY the family had to be closed: no numerator can fix an R²/R³ exponent error.
- ⛔ **★ …AND DO NOT CODE `M^(3/4)`.** It is an **output** of the heartwood law we already simulate
  (Berry 2024, opened), not an input.
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20). ★ And read the probe's
  DISTRIBUTION, not only the statistic you came for — ⚠ **iter-25's medians hid the defect**: the
  established kills had median S=1 (dark stubs) but a MEAN of 16 internodes. The wood was in the tail.
- ⛔ **★ AN UNFITTABLE CONSTANT IS THE SIGNATURE OF A SATURATED INSTRUMENT** (iter-25). iter-24 found
  "every theta in [0, 0.25] selects the same set" and treated it as a curiosity. It was the clamp,
  screaming. **When a constant cannot be fitted at all, audit the instrument, not the constant.**
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` = 0.11 m vs
  `VOX` = 0.6 m.
- ⛔ **★ Solve a loop's constant INSIDE the loop** (iter-19). ★ A root-find that CONVERGES can still
  be the refutation: report the local SENSITIVITY with the root. >=10x means unsolvable.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age. **b(n) is the
  VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a
  win. ★ iter-26 USES it (sapwood as the gate's denominator) — that is reading its output, not
  re-opening it.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). ⇒ **target a RATIO.**
  ⚠ iter-25 moved it anyway (10.4 → 22.0%) — because it was not a scalar, it was a LAW.
- ⛔ **STATICS IS EXONERATED** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⛔ **EXONERATED FOR CROWN WIDTH — do not re-indict *for width*:** the tip budget (iter-11), the shed
  rule, `MAX_CAT`, the reiteration rate, `N_def` accumulating with tip AGE, the statics. **The crown
  was never 2x too wide.** If the width verdict is ever threatened, STOP.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022 (equations are GIF images), Hellström 2018. Berry
  2024 + Xu 2014 opened in iter-21 (web). ⚠ **Shinozaki 1964 (the pipe model) is CITED FROM MEMORY in
  the iter-26 plan above and has NOT been opened — open it before it becomes load-bearing.**
- ⚠ **Instrument limit:** seed spread is 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%).**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP` is **None** ⇒ `s_def == 1.0` always,
  so the iter-15 S-scaled shade is NOT live. Also `S_IN_SHADE`, `S_IN_LIGHT`, `MAX_CAT`. A retired
  term reads exactly like a live one in the source.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
