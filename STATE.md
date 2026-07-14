# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-32: THE SINGLE-TERM STORY IS DEAD. IT IS TWO TERMS, PULLING OPPOSITE WAYS.

**Shinozaki 1964 is OPENED** (`tmp/papers/shinozaki1964_I.pdf`, `_II.pdf`). Its Eq. 2 (`F = L·C`) is a
law on **sapwood AREA**, not on the sapwood *fraction* — the paper makes no claim about the fraction.
Fig. 7/8: heartwood is the **horizontal** part of `F~C`, a stock of history, outside the law.

So the fraction was split into its parts, against the cached bench (`tmp/iter32_areas.py`, free, no
grow). **No parameter moved. Nothing fitted.** All six lines `** RESOLVED **`:

| tier | basal area | SAPWOOD area | heartwood area |
|---|---|---|---|
| s | 2.31x | **1.32x** | **3.30x** |
| m | 1.11x | **0.45x** | **1.77x** |
| l | 1.57x | **0.51x** | **2.63x** |

**Sapwood is HALF the census at m/l; heartwood is 1.8–2.6x too much.** They cancel at `m` — the ONLY
reason DBH ever read as a mild 1.05x. ★ And the SHAPE inverts: sapwood area is **flat ~0.5x**
(scalar-shaped), heartwood **grows with size**. iter-31's "monotone worsening ⇒ law error" was an
artifact of the division. Independent check, from the paper: at Table 1's `L≈60 cm` our `m` pipe
carries **12.3 kg** dry leaf vs the census trunk's **27.2 kg**; crown geometry (r 6.3 m, LAI≈3,
LMA≈75) independently says ~26 kg. Two routes, no shared constant, both say the census is right.

## The board (n=5, and only a `** RESOLVED **` line may be a tell)

1. **★★ SAPWOOD AREA 0.45x / 0.51x at m/l** — flat, scalar-shaped. The live crown under-carries.
2. **★★ HEARTWOOD AREA 1.77x → 2.63x** — grows with size. The dead bank over-fills. ⚠ Suspect the
   **rate of leaf-unit LOSS** that feeds it; ⛔ NOT `HEART_RATIO` (see 4).
3. **★ DBH lever m→l = 1.950 ± 0.181 vs census 1.646** — 1.18x too steep. Now explained by (2).
4. **`s` is broken separately** — sapwood 1.32x AND heartwood 3.30x, both high; DBH 1.52x, H 0.63x,
   crown 0.43x. Its DBH half is structural (`2*R_TIP` floors DBH at 10.3 cm at any age).
- **NOT instruments, may not be a tell:** crown r_p50 lever (needs n~7) · height anywhere (1.01/1.03x
  — the leader is NOT starved; rail) · foliage count (90–112% spread — stop quoting it).

## NEXT — iter-33: WHICH OF THE TWO FIRST? Take **SAPWOOD**, and do not fit it.

**Hypothesis to test:** sapwood area = `c_S · N_live`, and `c_S` is pinned by R_TIP. A flat 0.5x at
m/l with **1.32x at s** cannot be bought by any scalar on `c_S` (it slides all three tiers together —
the iter-10 argument, again). ⇒ the deficit is in **`N_live`, the live leaf-unit count**: the crown
holds too few live units at m/l and too many at s. **Falsify that before touching a constant** —
read `N_live` per tier out of a bench run and check it against the crown's own leaf area
(r_p50, LAI). ⚠ If `N_live` is right and the area is still low, then `c_S` is wrong and the whole
R_TIP derivation is back on the table.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ DECOMPOSE A RATIO BEFORE YOU READ ITS SHAPE** (iter-32). A ratio inherits the shape of
  neither part. **TWO ERRORS THAT CANCEL LOOK LIKE ONE SMALL ERROR** — DBH's 1.05x was the healthiest
  number on the board and it was hiding 0.45x and 1.77x.
- ⛔ **★★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (iter-30). `plane_bench.py` now enforces this:
  n seeds × tiers in parallel (5×{s,m,l} = **20 min wall**), every observable carries its resolution
  (`** RESOLVED **` vs `-- noise --`). Baseline cached: **`tmp/iter31_bench.npz`**. `--load` re-reports
  free; `--set K=V` for a paired fit. **Never fit against a `-- noise --` line.**
- ⛔ **★★★ A SCALAR ON A STOCK IS NOT A SCALAR ON A FLOW** (iter-30). True of R_TIP/DBH_CALIB; FALSE of
  ALPHA (a multiplier on compounding income). Check which kind before you reach for it.
- ⛔ **★★ ONE GROUND TRUTH WILL CERTIFY A CORPSE** (iter-30); **A CONSTANT FITTED AGAINST A LEAK IS THE
  LEAK'S TWIN** (iter-29) — and iter-32 caught one: `c_H/c_S = 1.07` was fitted to basal-area growth
  while sapwood leaked half of it. ⛔ **HEART_RATIO IS STILL NOT A KNOB** — the paper's own physics
  (Fig. 8: the disused pipe is the SAME pipe) is untouched by the leak. Fix what FEEDS the bank.
- ⛔ **★★ THE ECONOMY'S *STRUCTURE* IS EXONERATED** — numerator (22), denominator (26), light law (25).
  iter-29/30 re-fitted its **SCALE ONLY**. No gate term, no light term, no new TAU.
- ⛔ **★★ THE HEARTWOOD LAW IS DONE** (12–14) · **DROOP/`arch`/`DROOP_K`/`vigour` EXONERATED** (28) ·
  **STATICS EXONERATED** (21: `pipe/built = 100%` all tiers) · **the crown-at-`m` deficit was NOISE**
  (31) · **LAI cannot rescue p = 2.3**. ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **★★ A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION** (27); **"the class is rich" ≠ "the member is
  funded"** (28). Read the percentiles — and the SPREAD.
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (20) · **A DENSITY IS THE THING TO CONSERVE,
  NOT A COUNT** (24) · **DO NOT CODE `M^(3/4)`** — an OUTPUT (Berry 2024) · **No age lookup**:
  `K(n) = alpha(n+1)^d` makes DBH analytic in age; **b(n) is the VALIDATOR**.
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (23): `MASS_CAP`, `TWIG_DENSITY` are **None** (retired).
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): **Shinozaki 1964 I + II**, Aye 2022, Hellström 2018. Berry 2024
  + Xu 2014 opened (web). **Nothing on the critical path is unopened now.**
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- ✅ **DONE (distill, 2026-07-14):** the `0.50` sapwood target is now SOURCED in `plane_bench.py`
  (Shinozaki Eq. 2 + crown geometry, two routes, no shared constant) — and the same comment marks
  `sap` as a **smoke alarm, not a fit target** (a fraction is a ratio the pipe model never claims).
- **Distilled 2026-07-14:** iters 18–32's staged lessons are promoted and archived
  (`ledger_archive/2026-07.md`); LEDGER's staging section is empty. Two rules reached Tier 0 —
  *a ratio is not a fact* and *a mean without a resolution is a lie* — so the rails below marked
  ⛔★★★ now have full write-ups in `~/.claude/rules/practices.md`. **Nothing else changed.**
- ALPHA = 1.026e-5 remains PROVISIONAL — fitted on DBH@m magnitude alone, and iter-32 just showed
  DBH@m is the number most corrupted by cancellation. **Treat ALPHA as unfitted.**
- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
