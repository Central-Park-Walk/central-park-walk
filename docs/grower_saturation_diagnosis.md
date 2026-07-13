# Why the live terminal count saturates — measured diagnosis (2026-07-13)

Read-only. No generator code changed. Probe: `tmp/iter15_saturation_probe.py` (wraps `shed()`,
the last call of each grower year, and records the tip budget + the resource economy).

## The measurement (l tier, 104 yr, single seed)

| yr | live tips | dormant | shed | reiterates | foliage | pool v_base (m³) |
|----|-----------|---------|------|------------|---------|------------------|
| 10 | 12 | 3 | 3 | 9 | 64 | 0.0047 |
| 24 | 17 | 7 | 3 | 59 | 160 | 0.0570 |
| 52 | 8 | 3 | 2 | 187 | 132 | 0.0221 |
| 80 | 25 | 9 | 6 | 319 | 368 | 0.1005 |
| 104 | 20 | 10 | 4 | 458 | 380 | 0.1200 |

**The count does not "saturate" — it never grows.** It reaches a band of 8–25 by ~yr 20 and holds it
for 80 years. Births (458 reiterates over the run, ~5/yr) are matched by shedding (~5/yr): steady-state
churn, no accumulation. 30–50% of live apices are DORMANT (cannot buy one metamer) at every age past 10.
The pool grows only ×2.1 from yr 24 → 104, against a census basal area that grows ×2.71 m→l.

## Why — the economy is SCALE-FREE IN TIPS (structural, not a bad constant)

- Each live tip carries exactly `FOLIAGE_PER_TIP · FOLIAGE_LIFE` = 12 foliage markers ⇒
  `Q_base = 12 · n_tips · L̄`, `v_base = ALPHA · Q_base`.
- That pool is split among ~`n_tips` apices ⇒ **mean income per apex ≈ ALPHA · 12 · L̄, independent of
  `n_tips`.** Measured `L̄` is flat with age: 1.38 units/marker at yr 24, 1.22 at yr 104.
- Cost per apex is `n · π · R_TIP² · INTERNODE` (`l_afford = v/(n·π·R_TIP²)`, L602) — also constant.

⇒ affordable extension is a function of **mean light per marker alone**. Income ∝ tips, cost ∝ tips;
they cancel. `n_tips` has **no growth term anywhere** — it sits at the fixed point that iter-9's
`ALPHA`/`R_TIP` pair was calibrated to, for ever. Nothing about being old or big makes a tip richer.
This is the same statement as "no scalar can fix a two-sided error", arrived at from the light side.

## What it means for iter-15 (sharpens the plan; does NOT replace it)

`N_def` today sits on the **cost** side (`R_TIP = DBH_CALIB·R0`) and in the DBH/heartwood **ledger**.
It is **absent from the light income and from the shade**: a tip pays 354 twigs' worth of wood to
extend and earns 1 tip's worth of light.

**A size-dependent `N_def` in the LEDGER ALONE will move the sapwood fraction and leave the crown just
as pinned.** It must also enter `grow_foliage()` / `build_shadow()`: a tip that stands for N deferred
A4/A5 twigs must intercept N twigs' worth of light and cast N twigs' worth of shade. That is the
missing positive term, and it is the same term on both sides of the ledger — still an OUTPUT, still
no new fit. Read Hellström et al. 2018 (branch carrying capacity) before writing it, per the rails.

## Secondary flag (not chased)

`_bill_total` (the iter-8 self-support bill, L1061 — "is the mechanism biting at all?") reads
**0.0000 m³ every year of the 104**, i.e. <0.05% of the pool. The billed quantity is the structural
*excess over the pipe radius*, and the pipe radius appears to dominate everywhere, so self-support
is currently **not biting**. Flagged, not investigated — it is not the cause of the saturation.
