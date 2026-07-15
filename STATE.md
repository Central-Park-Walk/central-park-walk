# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-33: THE SAPWOOD DEFICIT IS IN THE LIVE-UNIT COUNT, NOT THE PIPE CONSTANT.

Sapwood area is `A_sap = pi*R_TIP^2 * F_S^(2/p)` (p=2.3): a UNIFORM per-unit area `c_S == pi*R_TIP^2`
times a per-tier count `F_S` (= N_live, live armature tips). iter-32 RESOLVED the sapwood residual as
**1.32x (s) / 0.45x (m) / 0.51x (l)**. iter-33 inverted the law (free, off `tmp/iter31_bench.npz`,
`tmp/iter33_nlive.py`) — the `F_S` each tier NEEDS at fixed `R_TIP` vs what it HAS:

| tier | A_sap | need/have F_S | leaf/unit model→need |
|---|---|---|---|
| s | 1.32x | **0.72x** (too many units) | 0.7 → 5.3 m2 |
| m | 0.45x | **2.48x** (too few units)  | 3.4 → 1.9 m2 |
| l | 0.51x | **2.17x** (too few units)  | 3.1 → 1.1 m2 |

`need/have = (1/ratio)^(p/2)` — a fixed transform of RESOLVED ratios, so it's resolved too. It is NOT
a scalar (0.72x vs 2.48x, opposite signs), so **`c_S`/`R_TIP` is EXONERATED by the shape** (iter-10,
now measured). **The deficit is in `F_S`.** Refutation branch ("F_S right ⇒ R_TIP back on the table")
did not fire. The model's leaf-area-per-live-unit is INVERTED vs census — it overloads each armature
tip at m/l and underloads at s ⇒ the fix feeds from **`N_def(t)`**, not any pipe constant.

## The board (n=5, and only a `** RESOLVED **` line may be a tell)

1. **★★ N_live (F_S) COUNT is wrong-SHAPED** — 1.4x too many at `s`, ~2.2–2.5x too few at m/l. This
   is the whole sapwood story (it IS the 0.45x/0.51x/1.32x areas, re-expressed as a count). Suspect
   `N_def(t)` — the deferred-twig count one armature tip stands in for (iter-15 machinery, `S(t)`).
2. **★ HEARTWOOD AREA 1.77x → 2.63x** — grows with size, the dead bank over-fills. Suspect the **rate
   of leaf-unit LOSS** that feeds it; ⛔ NOT `HEART_RATIO`. Second term; take it after N_live.
3. **`s` is broken separately** — its DBH half is structural (`2*R_TIP` floors DBH at 10.3 cm at any
   age); its "too many live units" (0.72x) is the same floor seen through the count.
- **NOT instruments, may not be a tell:** crown r_p50 lever (needs n~7) · height (1.01/1.03x — rail)
  · foliage count (90–112% spread — stop quoting it).

## NEXT — iter-34: WHY DOES F_S SETTLE ~2.4x LOW AT m/l? Read `N_def(t)` and `S(t)`, do not fit.

**Hypothesis to test:** the live-unit count `F_S` is set by the economy through `N_def(t) = MASS_CAP *
M_sub_root / n_tips` (`S = N_def/N_DEF_REF`), so `F_S` low ⇔ `N_def` too high per tip (each tip defers
too many real twigs). **Falsify by reading `N_def`, `S`, and `n_tips` per tier out of ONE grow** (the
bench doesn't record them) and checking whether `S` runs low at m/l as the count demands. ⚠ Do NOT
tune a constant this session — first find WHICH term in the N_def economy carries the 2.4x. ⛔ Compute
the loop gain before coding any term (iter-20): `N_def` sits on BOTH income and cost sides.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ DECOMPOSE A RATIO BEFORE YOU READ ITS SHAPE** (iter-32). TWO ERRORS THAT CANCEL LOOK LIKE
  ONE SMALL ERROR — DBH's 1.05x hid sapwood 0.45x and heartwood 1.77x.
- ⛔ **★★★ A UNIFORM SCALAR CANNOT MAKE A TIER-VARYING SHAPE** (iter-10, MEASURED at iter-33): `c_S`
  slides all tiers together, so a `need/have` of 0.72x/2.48x/2.17x proves the defect is per-tier
  (the count), not the constant. This is how `R_TIP` was exonerated without a grow.
- ⛔ **★★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (iter-30). `plane_bench.py`: n seeds × tiers in
  parallel (5×{s,m,l} ≈ **20 min wall**), every observable carries its resolution. Baseline cached:
  **`tmp/iter31_bench.npz`** (records dbh/h/rp50/rp90/nfol/sap/F_S/F_H per seed). `--load` re-reports
  free; `--set K=V` for a paired fit. **Never fit against a `-- noise --` line.**
- ⛔ **★★ A SCALAR ON A STOCK IS NOT A SCALAR ON A FLOW** (iter-30). True of R_TIP/DBH_CALIB; FALSE of
  ALPHA. ⛔ **HEART_RATIO IS NOT A KNOB** — fix what FEEDS the bank (rate of leaf-unit loss), not c_H.
- ⛔ **★★ THE ECONOMY'S *STRUCTURE* IS EXONERATED** — numerator (22), denominator (26), light law (25);
  only its SCALE was refitted. **STATICS EXONERATED** (21) · **DROOP/vigour EXONERATED** (28) · **the
  crown-at-`m` deficit was NOISE** (31). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (20) · **DO NOT CODE `M^(3/4)`** — an OUTPUT
  · `K(n)=alpha(n+1)^d` makes DBH analytic in age; **b(n) is the VALIDATOR**.
- ⚠ **NEVER cite a paper you have not OPENED.** On disk (`tmp/papers/`): Shinozaki 1964 I+II, Aye 2022,
  Hellström 2018. Berry 2024 + Xu 2014 opened (web). Nothing on the critical path is unopened.
- ⚠ **LEDGER is APPEND-ONLY.** Its entry ships in the same commit as the change.

## Housekeeping

- ALPHA = 1.026e-5 remains PROVISIONAL — fitted on DBH@m alone, the number most corrupted by
  cancellation. **Treat ALPHA as unfitted.**
- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
