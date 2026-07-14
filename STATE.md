# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-29: THE SPILL WORKS. THE CROWN WIDENS. THE LEAK WAS THE CALIBRATION.

`_distribute` now WATER-FILLS: the surplus above an apex's clamp point (where marginal reach is
provably zero) spills back to candidates still below theirs. Committed `9511e05`. Loop gain was
computed first (`tmp/iter29_prereg.md`): the sink SATURATES, so the spill channel's gain is **0** —
it cannot run away. Measured (`tmp/iter29_spill.log`, and the unchanged iter-27 tool A/B in
`tmp/iter29_columns_AFTER.log`):

- **THE RIM FUNDS.** Median rim `l_afford/INTERNODE` **0.000 → 1.000**; gini **0.96 → 0.00–0.45**.
- **THE SPEND RISES.** `spend/alloc` **5.0% → 53.8%**; residue 5.1% of pool; self-pruning ALIVE (98/104 yr).
- **★★ THE CROWN WIDENS — the scaling defect is DEAD.** Bulk p50 radius lever m→l **0.933 → 1.297**,
  against the census's demanded **1.34**. Reach IS bought with resource; iter-27/28's diagnosis STANDS.
- **★★★ AND EVERY MAGNITUDE BLEW OUT** (the pre-registered at-risk rail, named in advance): l DBH
  **1.08x → 1.89x** census (rail was < 1.30x), m 1.41x; DBH lever 1.62 → **2.21** (census 1.65); p50
  radius 1.54x census; foliage 3,872 → **35,863**; apices 16–42 → **167–199**; sap_frac 13.8% → 8.2%.

**⇒ ALPHA and its partners were derived (iter-17) against a model that DISCARDED 95% OF ITS POOL.**
The mechanism is now right and the SCALE is wrong by 1.5–1.9x. The spill is KEPT — a discarded budget
is a bug, and reverting restores it.

## NEXT — iter-30: RE-DERIVE THE INCOME SCALE UNDER CONSERVATION.

The magnitude family reopens — **not** because a gate / light law / TAU is needed (all still
exonerated), but because the income scale was fitted to a leaking sink. ONE scalar, re-derived, then
s and l read as OUTPUTS.

- **★ ALPHA is the suspect, not DBH_CALIB.** Rail (iter-17): a DBH_CALIB scalar CANCELS out of the
  sapwood fraction. ALPHA prices light → wood and does not. **Solve it under BOTH ground truths
  (census DBH *and* the m→l lever) before fitting under either** — a large disagreement is a
  structural falsification, and the cheapest one available.
- **★ PRE-REGISTER**, incl. the rails expected to HOLD: the crown's m→l lever (1.297) must SURVIVE
  the rescale — it is now the thing that works, and a scalar must not cost it.
- ⚠ The tree now runs 66,774 live wood nodes at `l` — **runs are slower again.** Budget for it.

## Open defects

1. **★★ EVERY MAGNITUDE IS 1.4–1.9x OVER** (iter-29). DBH 1.89x, p50 radius 1.54x, 9x the foliage.
   The root: the constants are calibrated against the leak. **Do not chase them separately.**
2. **★ THE DBH LEVER GOT WORSE** — 2.21 m→l against the census's 1.65 (was 1.62). Over-thickening at
   `l`: a huge crown demands a huge support bill. Plausibly downstream of (1); may not be.
3. **sapwood 8.2% at `l`** (was 13.8%) vs ~50% census; F_H 1784 lost vs F_S 341 live.
4. **Extension is a FIXED COST PER APEX PER YEAR** — only apex COUNT can absorb resource. The spill
   raised the count 10x on its own; if the rescale re-starves the crown, THIS is the term that needs
   a botanical sink (more shoots), not the pool's size. ⚠ `n = floor(v)` is NOT it (iter-6).
5. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ A CONSTANT FITTED AGAINST A LEAK IS THE LEAK'S TWIN** (iter-29). The mechanism can be RIGHT
  and the scale 1.9x wrong in the same run. Ask what the model DISCARDS before fitting anything.
- ⛔ **★★ A SATURATED SINK HAS LOOP GAIN ZERO** (iter-29) — compute `pool / Σcapacity` before fearing G.
- ⛔ **★★ A CLAMPED SINK IS A LEAK** (iter-28) — `min(1, …)` on the only thing resource can buy discards
  the remainder silently. Audit every saturating term for what happens to the surplus.
- ⛔ **★★ THE ECONOMY'S *STRUCTURE* IS EXONERATED** — numerator (22), denominator (26), light law (25).
  ⚠ iter-29 reopens its **SCALE ONLY**. Still: no gate term, no light term, no new TAU.
- ⛔ **★★ DROOP / `arch` / `DROOP_K` and `vigour` ARE EXONERATED as the geometric root** (iter-28).
- ⛔ **★★ A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION** (iter-27); **"the class is rich" ≠ "the member
  is funded"** (iter-28, gini 0.96). Read the percentiles.
- ⛔ **★ DO NOT CODE `M^(3/4)`.** An OUTPUT of the heartwood law we already simulate (Berry 2024).
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20). It paid for itself at iter-29.
- ⛔ **★ AN UNFITTABLE CONSTANT IS THE SIGNATURE OF A SATURATED INSTRUMENT** (iter-25).
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` 0.11 m vs `VOX` 0.6 m.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH analytic in age. **b(n) is the VALIDATOR.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17) ⇒ target a RATIO.
- ⛔ **STATICS IS EXONERATED for load-bearing** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Berry 2024 + Xu 2014 opened (web).
  **Shinozaki 1964 is still UNOPENED.**
- ⚠ **Instrument limit:** seed spread 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is measurable.
  **DBH is the tight one (9–19%).**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP`, `TWIG_DENSITY` are **None** (retired).
  A retired term reads like a live one. (`MASS_CAP is None` ⇒ `s_def == 1`, `r_tip == R_TIP`.)
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
