# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — iter-31: THE INSTRUMENT EXISTS. `scripts/plane_bench.py` (`5fcc208`).

iter-30 stopped the fitting: an n=1 instrument cannot measure a ratio, and every magnitude fitted in
iters 27–30 was fitted inside its own seed noise. iter-31 built the replacement instead of a model
change. **No parameter moved this session.**

`python3 scripts/plane_bench.py -n 5 --tiers s,m,l` — n seeds × tiers as **independent processes**
(wall = the slowest single run, ~20–25 min, NOT the 2–3 h STATE feared: the runs are parallel and
the box has 24 threads). Every observable prints its residual against census in **units of the
instrument** (half-width `2·SEM`): `** RESOLVED **`, or `-- noise --` with the seed count that
would resolve it. **Levers are paired per seed.** `--set ALPHA=…` for fits; `--load x.npz` to
re-report free.

**⏳ THE 5-SEED RUN WAS STILL IN FLIGHT AT HAND-OFF** → `tmp/iter31_bench.log` (+ `tmp/iter31_bench.npz`).
**Next session: read that log FIRST.** If it died, re-run it; it is the whole basis of iter-32.

Smoke (3 seeds × `s`) already resolved three unmeasured defects at `s`: DBH **1.58x** census (the
R_TIP floor), height **0.67x**, crown r_p50 **0.30x** — and showed foliage count at `s` has a
**112% seed spread**, i.e. it is not an instrument.

**Correction:** the old STATE claimed iter-30's default seed was the richest of the three. It is not
— the default (`20260710`) is the MIDDLE tree (1692 foliage); `SEED+2` is the 3822 one. iter-30's
conclusion stands (the ±50% lever spread is the reason), but not that reason.

## NEXT — iter-32: READ THE BENCH, THEN PICK THE ONE RESOLVED DEFECT.

Rule for the whole magnitude family from here: **only a `** RESOLVED **` line may be the tell an
iteration turns on.** Provisional expectation from n=3: DBH@m is resolvable (7.4% spread); crown
r_p50 (~41%) and every LEVER (~±50%) are probably NOT at n=5 — if so, the bench will print the `n`
that would be, and that number is the decision. Do not fit against a `-- noise --` line.

## Open defects

1. **★ Crown at `m` = 0.71x census** (n=3) — the `m` tree may be too NARROW. Resolved or not? Ask the bench.
2. **DBH lever 1.95 vs census 1.65**, crown lever 2.21 vs 1.34 — both **unmeasured** at n=3.
3. **ALPHA = 1.026e-5 is PROVISIONAL** — justified by DBH magnitude at `m` alone (1.41x → 1.07x),
   never by the lever that motivated it.
4. **sapwood ~16% at `l`** vs ~50% census (was 8.2%; the ALPHA cut helped).
5. **`s` tier is badly off** (new, from the smoke run): DBH 1.58x, H 0.67x, crown 0.30x. The DBH
   floor is structural — `2*R_TIP` = 10.3 cm for any tree at any age.
6. **Extension is a FIXED COST PER APEX PER YEAR** — only apex COUNT can absorb resource.
   ⚠ `n = floor(v)` is NOT the fix (iter-6).
7. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (iter-30). A lever compounds the spreads of its
  two terms. Measure a number's seed spread BEFORE it becomes the tell. **The bench now does this.**
- ⛔ **★★★ A SCALAR ON A STOCK IS NOT A SCALAR ON A FLOW** (iter-30). "No uniform scalar fixes a
  size-dependent error" is TRUE of R_TIP/DBH_CALIB (static multipliers on DBH) and **FALSE of ALPHA**
  (a multiplier on a compounding income). The rail nearly forbade a fit that worked.
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
  **Shinozaki 1964 is still UNOPENED.**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP`, `TWIG_DENSITY` are **None** (retired).
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
