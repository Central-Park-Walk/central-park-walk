# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-26 REFUTED THE DEFECT WE HAVE BEEN CHASING SINCE ITER-15

iter-26 was a read-only measurement (`tmp/iter26_denominator.py`, `tmp/iter26b_leafgate.py`; both
tiers to census age). It killed its own hypothesis AND the theorem behind it.

**1. Every denominator the tree owns fails.** (gate ratio l/m; 1.0 = size-invariant, today 0.686)

      count Σ1 → 0.686 · sap_frac → 0.797 · sap_vol → 0.600 (WORSE) · LEAVES → 0.784

  ⇒ ⛔ **THE DENOMINATOR FAMILY IS CLOSED.** Sapwood is **not a shell** in a crown sum (`Σ r_sap²`
  grows 2.19x vs the count's 1.91x); branch autonomy (bill the leaves) fails too.

**2. ★★★ THE CENSUS HAS THE SAME "EXPONENT ERROR".** UTD (in the source, `plane_grower.py:2065`):
real m = DBH 43.2 cm / crown 12.6 m; real l = DBH 71.1 cm / crown 16.9 m ⇒ crown projected area
×1.80, basal area ×2.71 ⇒ **real light per unit wood falls to 0.664 l/m. Ours falls to 0.686. WE
ALREADY MATCH IT.** iter-25's R²/R³ theorem is TRUE — and true of nature. **The gate's size-scaling
was never the defect.**

**3. ⇒ THE DEFECT IS THE LEVEL, NOT THE SLOPE — and it is ONE deficit, not two:**

      income  L   model l/m 1.314   vs census 1.80   = −27%
      live wood   model l/m 1.914   vs census 2.71   = −29%

  Both sides of the ratio are short by the same ~28%, which is exactly why the ratio looked healthy.
  **There is no economic term left to add. The tree simply never gets big enough.**

## NEXT — iter-27: WHERE ARE THE 27%? MEASURE THE CROWN, DO NOT CODE A TERM.

Under Beer–Lambert, income ≈ 39 × **OCCUPIED COLUMNS** ≈ the crown's **projected area**. So a −27%
income shortfall IS a −27% projected-area shortfall at `l`. But iter-9 measured crown width at
**1.07x / 1.05x of census** — on the **HULL**. **A hull can be right while its columns are empty** —
iter-23 saw exactly this ("the crown is not darker, it is emptier") and set it aside on a counting
technicality. Read-only probe, m and l:

1. **Occupied columns** (distinct (x,z) voxel columns holding live foliage) vs **hull projected area**
   vs the **UTD crown disc** (π·6.3² = 125 m² at m, π·8.45² = 224 m² at l). Report l/m for all three.
2. If hull ≈ census but columns ≪ hull ⇒ the defect is **crown FILL**, not the gate. If the hull is
   also short at l ⇒ the defect is **extension** (the crown stops widening) — a growth law, not an
   economy.
3. **★ PRE-REGISTER before running.** Rails: DBH must not move (1.09/1.08 — already 8% over);
   self-pruning stays alive.

⚠ **Do NOT propose another gate term.** Both of its families are now closed by measurement.

## Open defects

1. **★★ THE `l` TREE IS ~28% TOO SMALL** in income *and* wood, in the same proportion (above).
   Live wood l/m 1.91x, census 2.71–3.23x. This is defect #1 restated with the mythology removed.
2. **Caliber splay** — `s 1.53, m 1.09, l 1.08`. One-sided, all in `s`. Unchanged in kind.
3. **Sapwood 22.0% / 13.8%** vs ~50% census — moving fast since iter-25 (was 10.4 / 5.6); `s` lands
   on 50.4%. Plausibly the same defect as (1); do not chase separately.
4. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE GATE IS EXONERATED (iter-26).** Both families are closed: the **numerator** (iter-22:
  every `L = K·X^q` has gain ≥ 0.987) and the **denominator** (iter-26: count / sap_frac / sap_vol /
  leaves all measured). **And its size-scaling matches the census (0.686 vs 0.664).** Do not propose
  a seventh numerator, a second denominator, or a new `TAU`.
- ⛔⛔ **★★★ THE LIGHT/SHADING FAMILY IS CLOSED (iter-25).** The field is sound (Beer–Lambert, no
  invented constant) and the defect survived ⇒ it was never in the light. No new light/shade/placement
  term. ⚠ Runs are now **~4x slower** (s+m+l ≈ 10 min) — budget for it.
- ⛔ **★ …AND DO NOT CODE `M^(3/4)`.** It is an **output** of the heartwood law we already simulate
  (Berry 2024, opened), not an input.
- ⛔ **★ CHECK THE GROUND TRUTH'S OWN RATIO BEFORE BUILDING ON A SCALING THEOREM** (iter-26). The
  census was on disk for ten iterations and nobody divided two of its numbers.
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20). ★ And read the probe's
  DISTRIBUTION, not only the statistic you came for (iter-25's medians hid the wood in the tail).
- ⛔ **★ AN UNFITTABLE CONSTANT IS THE SIGNATURE OF A SATURATED INSTRUMENT** (iter-25). When a constant
  cannot be fitted at all, audit the instrument, not the constant.
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` = 0.11 m vs `VOX` = 0.6 m.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH analytic in age. **b(n) is the VALIDATOR.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17) ⇒ target a RATIO. A
  LAW can (iter-25 moved it 10.4 → 22.0%).
- ⛔ **STATICS IS EXONERATED** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⛔ **EXONERATED FOR CROWN *WIDTH*** (the HULL: 1.07x / 1.05x of census — iter-9). ⚠ iter-27 does NOT
  re-open width: it asks whether the hull is **FILLED**. If the hull verdict is ever threatened, STOP.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Berry 2024 + Xu 2014 opened (web).
  **Shinozaki 1964 is still UNOPENED** — iter-26 used the pipe model only as an already-coded law.
- ⚠ **Instrument limit:** seed spread 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%).** A −28% deficit is well outside it.
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP` is **None** ⇒ the iter-15 S-scaled
  shade is NOT live. Also `S_IN_SHADE`, `S_IN_LIGHT`, `MAX_CAT`. A retired term reads like a live one.
- ⚠ **LEDGER is APPEND-ONLY, and iter-25's entry was never written** (backfilled in iter-26). A STATE
  rewrite is not the record. **Write the LEDGER entry in the same commit as the change.**

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
