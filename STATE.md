# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★★ iter-27: THE DEFICIT IS GEOMETRIC, NOT ECONOMIC. THE CROWN STOPS WIDENING.

Read-only probe (`tmp/iter27_columns.py`, log beside it). **Both pre-registered predictions refuted;
the third outcome is the true one.** Rails held (DBH 1.09/1.08, sap_frac 22.0/13.8) ⇒ instrument sound.

1. **Crown FILL is constant** — columns/hull 0.341 → 0.344 (lever 1.010). The crown does not empty.
2. **Income IS column-bounded** — income per occupied column 8.72 → 8.01 (lever 0.919). ⇒ income ≈
   8.4 × columns, and **income is short exactly as the columns are**:
   `columns l/m 1.430 · income 1.314 · CENSUS BAR 1.799`.
3. **★★★ THE COLUMNS ARE SHORT BECAUSE THE CROWN NEVER WIDENS.** Foliage radius about the trunk,
   m → l, against census R 6.3 → 8.45 m (**×1.34 demanded**):

       p50   6.67 → 6.22 m  (0.933)  ← THE BULK MOVES INWARD.  1.06x → 0.74x census
       p90  11.02 → 11.66   (1.058)
       p100 14.68 → 18.77   (1.278)  ← a runaway tail, 2.2x census
       woody armature p50: 6.64 → 5.63 m (0.849) — the WOOD does it too

   **The median leaf sits 6–6.7 m from the trunk at 47 yr AND at 104 yr.** New foliage goes to the
   INTERIOR (iter-24's A5 short shoots) and to a few runaway limbs. Height 15.25 → 22.98 m (×1.51,
   and 1.20x UTD's 19.1). **The `l` tree grows UP, not OUT.**
4. **⇒ THE iter-9 HULL RAIL IS REFUTED.** The hull is not census-sized, it is *oversized* (1.51x /
   1.34x census radius) — inflated by the p95–p100 tail while the bulk stayed in. A hull can be right,
   or too big, while its BULK is short.
5. **⇒ this is why twelve iterations of economics all failed.** No gate/light/allocation term can be
   wrong, because the shortfall was never economic: **a crown whose leaves never leave a 6 m radius
   cannot earn a census income.**

## NEXT — iter-28: WHY DOES THE PERIPHERY NOT ADVANCE? MEASURE THE APICES. DO NOT CODE A TERM.

Read-only again. The census demands the *bulk* radius grow ×1.34 m→l; ours shrinks ×0.93. Ask what
happens to the outermost apices, per year, over the `l` run:

1. **Fate:** are the peripheral apices (top radial decile) **dying/shed**, **alive but not extending**
   (zero resource), or **extending but DROOPING back inward** (statics/`arch`)? Classify each.
2. **Budget:** what share of the year's allocated resource reaches an apex outside p75 of the crown
   radius? If ≈0, extension is starved and allocation is apex-biased toward the interior.
3. **Geometry:** does the branching law even *aim* outward at `l` — mean horizontal component of new
   internode directions, by year and by radius. Droop (`arch`/gravitropism) is a prime suspect: it
   turns a lateral limb into a downward one, which then re-leafs *under* the crown, not beyond it.
4. **★ PRE-REGISTER** before running. Rails: DBH must not move; self-pruning stays alive.

⚠ **Do NOT propose an economic term** (gate, light, denominator, allocation weight). Twelve iterations
of that family are closed. The answer is in the **extension geometry**.

## Open defects

1. **★★ THE CROWN DOES NOT WIDEN** — bulk radius 0.93x m→l where the census demands 1.34x; occupied
   columns 1.43x vs 1.80x. This *is* defect (2) below and the old "−28% too small": one geometric root.
2. **`l` is ~28% short in income and wood** (income 1.314 / wood 1.914 vs census 1.80 / 2.71). Restated:
   a consequence of (1), not a separate defect.
3. **The tree is too TALL and too NARROW** — H 22.98 m at `l` = 1.20x UTD; p100 radius 2.2x census
   (runaway limbs) around a 0.74x bulk. The aspect ratio is wrong at both ends.
4. **Caliber splay** — `s 1.53, m 1.09, l 1.08`. One-sided, all in `s`.
5. **Sapwood 22.0% / 13.8%** vs ~50% census. Plausibly downstream of (1); do not chase separately.
6. Criterion vi unmet ⇒ **do not ship.**

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE ECONOMY IS EXONERATED, ALL OF IT.** The gate's numerator (iter-22, gain ≥ 0.987), its
  denominator (iter-26, four forms measured), the light/shade law (iter-25, Beer–Lambert, sound), and
  the gate's size-scaling (iter-26: 0.686 vs the census's own 0.664 — it MATCHES). iter-27 closes the
  question: **the deficit is geometric.** Do not propose a gate term, a light term, or a new `TAU`.
- ⛔ **★★ A HULL / A MEAN / A MAX IS NOT A DISTRIBUTION** (iter-27). The iter-9 width rail and iter-23's
  "emptier" crown were both artifacts of measuring a crown by its ENVELOPE. Here p50 and p100 moved in
  **opposite directions**. Read the percentiles.
- ⛔ **★ DO NOT CODE `M^(3/4)`.** An OUTPUT of the heartwood law we already simulate (Berry 2024).
- ⛔ **★ CHECK THE GROUND TRUTH'S OWN RATIO BEFORE BUILDING ON A SCALING THEOREM** (iter-26).
- ⛔ **★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (iter-20).
- ⛔ **★ AN UNFITTABLE CONSTANT IS THE SIGNATURE OF A SATURATED INSTRUMENT** (iter-25).
- ⛔ **★ A DENSITY IS THE THING TO CONSERVE, NOT A COUNT** (iter-24). `INTERNODE` 0.11 m vs `VOX` 0.6 m.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH analytic in age. **b(n) is the VALIDATOR.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17) ⇒ target a RATIO.
- ⛔ **STATICS IS EXONERATED for load-bearing** (iter-21): `pipe/built = 100.0%` in all three tiers.
  ⚠ This does NOT exonerate `arch`/droop as a *geometry* term — iter-28 may legitimately measure it.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  On disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Berry 2024 + Xu 2014 opened (web).
  **Shinozaki 1964 is still UNOPENED.**
- ⚠ **Instrument limit:** seed spread 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%).** The 0.74x bulk-radius miss is far outside it.
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP` is **None** ⇒ the iter-15 S-scaled
  shade is NOT live. Also `S_IN_SHADE`, `S_IN_LIGHT`, `MAX_CAT`. A retired term reads like a live one.
- ⚠ **Runs are ~4x slower since iter-25** — m + l ≈ 8–10 min. Budget for it; run in background.
- ⚠ **LEDGER is APPEND-ONLY.** Write its entry in the same commit as the change.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
