# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-31: THE INSTRUMENT EXISTS, AND IT KILLED THE DEFECT WE WERE ABOUT TO CHASE.

`scripts/plane_bench.py` — n seeds × tiers as independent processes (5×{s,m,l} = **20 min wall**, not
the 2–3 h we feared: the runs are parallel, the box has 24 threads). Every observable carries its
**resolution**: residual vs census in units of `2·SEM` ⇒ `** RESOLVED **`, or `-- noise --` plus the
seed count that would resolve it. Levers paired per seed. `--set K=V` for fits, `--load x.npz` to
re-report free. Baseline cached: **`tmp/iter31_bench.npz`** (log: `tmp/iter31_bench.log`).

**No parameter moved this session.** ALPHA is still 1.026e-5.

**★★★ THE CROWN-AT-`m` DEFICIT WAS NOISE.** The 0.71x that three sessions of geometry theory were
aimed at reads **0.86x, `-- noise --`, needs n~14** (seed spread **85%**). It is off the board.

## The board, as the instrument actually reads it (n=5)

**RESOLVED — these, and only these, may be the tell an iteration turns on:**
1. **★★ sapwood frac RESOLVED LOW AT EVERY TIER, WORSENING WITH SIZE: 0.58x / 0.40x / 0.33x** census
   (29.2 / 20.2 / 16.7% vs ~50%). Clears its half-width by 3–11x. **A residual that worsens
   monotonically with size is a LAW error, not a calibration error** — no scalar fixes this shape.
2. **★ DBH lever m→l = 1.950 ± 0.181 vs census 1.646 — RESOLVED, 1.18x too steep.** First time this
   lever has ever been measurable. Caliber accrues too fast with age.
3. **DBH magnitude 1.05x (`m`, barely) / 1.25x (`l`)** — too much wood, more so at the top.
4. **`s` is broken across the board:** DBH 1.52x, H 0.63x, crown 0.43x; every s→m lever resolved-wrong.
   The DBH half is structural (`2*R_TIP` floors DBH at 10.3 cm at any age); H + crown are NEW.

**NOT AN INSTRUMENT — may not be a tell:**
- crown r_p50 lever m→l: 1.98 ± 0.83 vs 1.34 — `-- noise --`, **needs n~7**. Five grows from being
  real; not real today.
- height anywhere: 1.01x / 1.03x, `-- noise --` (n~31 / n~18). **The leader is not starved.** Rail.
- foliage count: 90–112% seed spread. Not an instrument at any tier. Stop quoting it.

## NEXT — iter-32: THE SAPWOOD LAW. ⛔ Only a `** RESOLVED **` line may be the tell.

**Hypothesis to test:** DBH-too-high and sapwood-too-low are **one defect, not two** — the tree
builds too much wood and nearly all of it is heartwood (`sap_frac` = sapwood / built basal area), so
the same excess shows up as inflated caliber *and* a starved sapwood ring, and both worsen with size
(DBH 1.05x→1.25x while sap 0.40x→0.33x). Falsify or confirm that they are the same term before
touching either. ⚠ The heartwood law itself is DONE (iters 12–14) — suspect what FEEDS it.

Run `plane_bench --set ...` against `tmp/iter31_bench.npz` as the paired baseline. **Do not fit
against a `-- noise --` line.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (iter-30). **The bench now enforces this.**
- ⛔ **★★★ A SCALAR ON A STOCK IS NOT A SCALAR ON A FLOW** (iter-30). True of R_TIP/DBH_CALIB (static
  multipliers on DBH); FALSE of ALPHA (a multiplier on a compounding income). Check which kind first.
- ⛔ **★★ ONE GROUND TRUTH WILL CERTIFY A CORPSE** (iter-30). At k=0.30 census DBH is met almost
  exactly — by a starved stick with a 0.67x crown. A fit is only as honest as its SECOND observable.
- ⛔ **★★★ A CONSTANT FITTED AGAINST A LEAK IS THE LEAK'S TWIN** (iter-29). Ask what the model
  DISCARDS before fitting anything.
- ⛔ **★★ A SATURATED SINK HAS LOOP GAIN ZERO** (iter-29) — compute `pool / Σcapacity` before fearing G.
  **A CLAMPED SINK IS A LEAK** (iter-28) — audit every saturating term for its surplus.
- ⛔ **★★ THE ECONOMY'S *STRUCTURE* IS EXONERATED** — numerator (22), denominator (26), light law (25).
  iter-29/30 re-fitted its **SCALE ONLY**. Still: no gate term, no light term, no new TAU.
- ⛔ **★★ DROOP / `arch` / `DROOP_K` / `vigour` EXONERATED as the geometric root** (iter-28).
- ⛔ **★★ A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION** (iter-27); **"the class is rich" ≠ "the member
  is funded"** (iter-28). Read the percentiles — and now, the SPREAD.
- ⛔ **★ DO NOT CODE `M^(3/4)`.** An OUTPUT of the heartwood law we already simulate (Berry 2024).
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20). It paid for itself at iter-29.
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` 0.11 m vs `VOX` 0.6 m.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH analytic in age. **b(n) is the VALIDATOR.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION** — narrower than it reads: `DBH_CALIB` cancels, but
  **ALPHA does not** (iter-30 moved sap_frac 8.2% → 16%).
- ⛔ **STATICS IS EXONERATED for load-bearing** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Berry 2024 + Xu 2014 opened (web).
  **Shinozaki 1964 is still UNOPENED** — and it is the sapwood/pipe paper. Open it before iter-32.
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP`, `TWIG_DENSITY` are **None** (retired).
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- ALPHA = 1.026e-5 remains PROVISIONAL — fitted on DBH@m magnitude alone, never on a resolved lever.
- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
