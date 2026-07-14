# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-30: THE REFIT IS REAL AT `m`. THE INSTRUMENT IS NOT REAL AT ALL.

iter-29's spill is **ACCEPTED (Chris)** — the conserved budget stays in. So iter-30 re-derived the
income scale it invalidated: **`ALPHA 2.281e-5 → 1.026e-5`** (k = 0.45), committed `8479c82`, swept
under BOTH ground truths at once (`tmp/iter30_prereg.md`, `tmp/iter30_alpha_sweep.log`).

**The 3-seed verification (`tmp/iter30_verify_seeds.log`) FAILED THE FIT, and that is the finding:**

- **★★★ THE DEFAULT SEED IS THE RICHEST TREE OF THREE** (3822 foliage at `m` vs 1386 / 1692).
  **Every number iters 27–30 turned on was read off that one tree.**
- **★★★ THE m→l LEVER IS UNMEASURABLE AT n = 1.** Per-seed crown lever: **1.86 / 3.40 / 1.78** (~±50%).
  iter-29's "crown lever 1.297 vs census 1.34" was **inside the noise** — and so was this session's
  own pre-registered P-KEY. The single-seed k=0.45 row does NOT reproduce (1.12x/1.15x → **1.07x/1.27x**).
- **WHAT SURVIVES: DBH at `m` is TIGHT (7.4% spread) and the refit is REAL there — 1.41x → 1.07x census.**
  `l` DBH 1.27x (spread 22.7%). Height **1.00x / 1.05x** (leader not starved). F_H 191/742 > 0.
  sap_frac 8.2% → ~16%.

**⇒ ALPHA is KEPT but PROVISIONAL** — justified by DBH magnitude alone, never by the lever that
motivated it. Two pre-registered predictions were REFUTED (see LEDGER 30): the iter-11 and iter-17
rails govern **static** multipliers; ALPHA multiplies a **compounding income**, so it DOES bend the
lever and DOES move sap_frac.

## NEXT — iter-31: ⛔ NO MORE FITTING. REBUILD THE INSTRUMENT FIRST.

The magnitude family has been fitted for four iterations to the noise of one lucky tree. The next
unit of work is **an n-seed measurement harness**, not a model change.

- **Fold the seed loop into ONE reusable tool** (extend `tmp/iter30_verify_seeds.py`; do not rebuild
  it) reporting **mean ± spread** for every observable, and the **spread of each LEVER**.
- **★ It must report which observables are ABOVE the noise floor.** Provisional read: DBH@m yes
  (7.4%); crown r_p50 no (~41%); any LEVER no (~±50%). **A quantity below its floor may never again
  be the tell an iteration turns on.**
- ⚠ **Cost is the design constraint** — an `l` run is 600–1200 s. 5 seeds × {m, l} ≈ 2–3 h wall
  clock. Budget it, run it in the background ONCE, cache the results to `.npz`.
- **Then, and only then**, re-open: is the crown at `m` really 0.71x census (too narrow), and is the
  DBH lever really 1.95 vs the census's 1.65?

## Open defects

1. **★★ THE INSTRUMENT** (above). Everything below is provisional until it exists.
2. **★ Crown at `m` = 0.71x census** (3-seed) — the `m` tree may now be too NARROW. Spread ~41%: not
   yet distinguishable from noise. **Do not chase it before iter-31.**
3. **DBH lever 1.95 vs census 1.65**, crown lever 2.21 vs 1.34 — both **unmeasured**, not met.
4. **sapwood ~16% at `l`** vs ~50% census (was 8.2% — the ALPHA cut helped). F_H 742 vs F_S live.
5. **Extension is a FIXED COST PER APEX PER YEAR** — only apex COUNT can absorb resource.
   ⚠ `n = floor(v)` is NOT the fix (iter-6).
6. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (iter-30). A lever compounds the spreads of its
  two terms. Measure a number's seed spread BEFORE it becomes the tell — and check the default seed
  is not the outlier. **Ours was.**
- ⛔ **★★★ A SCALAR ON A STOCK IS NOT A SCALAR ON A FLOW** (iter-30). "No uniform scalar fixes a
  size-dependent error" is TRUE of R_TIP/DBH_CALIB (static multipliers on DBH) and **FALSE of ALPHA**
  (a multiplier on a compounding income). The rail nearly forbade a fit that worked.
- ⛔ **★★ ONE GROUND TRUTH WILL CERTIFY A CORPSE** (iter-30). At k=0.30 census DBH is met almost
  exactly — by a starved stick with a 0.67x crown. A fit is only as honest as its SECOND observable.
- ⛔ **★★★ A CONSTANT FITTED AGAINST A LEAK IS THE LEAK'S TWIN** (iter-29). Ask what the model
  DISCARDS before fitting anything.
- ⛔ **★★ A SATURATED SINK HAS LOOP GAIN ZERO** (iter-29) — compute `pool / Σcapacity` before fearing G.
- ⛔ **★★ A CLAMPED SINK IS A LEAK** (iter-28) — audit every saturating term for its surplus.
- ⛔ **★★ THE ECONOMY'S *STRUCTURE* IS EXONERATED** — numerator (22), denominator (26), light law (25).
  iter-29/30 reopened and RE-FITTED its **SCALE ONLY**. Still: no gate term, no light term, no new TAU.
- ⛔ **★★ DROOP / `arch` / `DROOP_K` / `vigour` EXONERATED as the geometric root** (iter-28).
- ⛔ **★★ A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION** (iter-27); **"the class is rich" ≠ "the member
  is funded"** (iter-28). Read the percentiles — and now, the SPREAD.
- ⛔ **★ DO NOT CODE `M^(3/4)`.** An OUTPUT of the heartwood law we already simulate (Berry 2024).
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20). It paid for itself at iter-29.
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` 0.11 m vs `VOX` 0.6 m.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH analytic in age. **b(n) is the VALIDATOR.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION** — was iter-17's rail, and it is **narrower than it
  read**: `DBH_CALIB` cancels, but **ALPHA does not** (iter-30 moved sap_frac 8.2% → 16%).
- ⛔ **STATICS IS EXONERATED for load-bearing** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Berry 2024 + Xu 2014 opened (web).
  **Shinozaki 1964 is still UNOPENED.**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP`, `TWIG_DENSITY` are **None** (retired).
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
