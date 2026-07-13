# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-13 DONE — and its hypothesis was REFUTED.** The dead pipes are now banked as conserved AREA
(p = 2) and the live sapwood alone tapers (p = 2.3) — two banks that never meet in one metric. That
law is right and it stays. But both of its predictions failed:

    DBH vs census      iter-12: s 3.96  m 2.49  l 2.29     iter-13: s 4.81  m 3.41  l 3.11
    re-centred on m    iter-12: s 1.59  m 1.00  l 0.92     iter-13: s 1.41  m 1.00  l 0.91
    sapwood % of area  iter-12:        m ~16%  l ~10%      iter-13:        m 7.5%  l 3.7%

Girth overshoots MORE (~3.3×), and the sapwood fraction got WORSE — a 104 yr trunk is now **96%
heartwood**, where a real plane is ~50% and is noted for WIDE sapwood. The one gain: re-centred splay
1.59 → 1.41. **The metric was never the fault. Do not ship.**

## Open defects

1. **★ The model banks too much dead wood.** Every dead branch's full living section is kept forever,
   so heartwood grows without bound while the live crown does not. This is THE defect; 2–4 are
   downstream of it and cannot be read until it is fixed.
2. **`DBH_CALIB` is stale** (fitted heartwood-free) — the one legitimate re-centring scalar. Refit
   ONCE, and only *after* (1). It cannot fix (1); see the rails.
3. **Caliber splay, residual** — re-centred s 1.41 / l 0.91. `l` is home; **`s` is the one left.**
4. **`s` floor** — constant `R_TIP` floors DBH at 2·R_TIP at any age, and `s`'s census DBH is 12.7 cm,
   so `s` is pinned near the floor and *cannot* be thin. **One term won't mend both this and (3).**
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — the one hypothesis: READ KUBO 2022 FIRST. No code until then.

Kubo et al. 2022, *Tree Physiology* 42:2174 — sapwood/heartwood profiles from pipe model + branch
thinning. I have been working from a summary of its mechanism, not from its figures, and two
iterations have now been spent guessing at it. **Prior art is job 1.** The specific question to put to
the paper: *does a disused pipe persist at the stem base at its full living diameter?* If it does,
then branch death is far too cheap in our model and the shed rule is the suspect. If it does not, the
missing mechanism is in the paper and there is no need to invent one. **Derive, then measure.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★ No scalar can move the SAPWOOD FRACTION — `DBH_CALIB` CANCELS.** Live sapwood scales as
  `R_TIP·n_live^(1/p)`, the dead bank as `R_TIP²·Σ n_c^(2/p)`; the ratio is R_TIP-free. The 96%
  heartwood is a pure STRUCTURAL statement, not a calibration error. (iter-13)
- ⛔ **No scalar can FIX a two-sided error** (`R0`, `DBH_CALIB`, `R_TIP`, constant `N_def` are uniform
  DBH multipliers) — but a scalar is the right tool to **CENTRE** one, *after* a size-dependent term exists.
- ⛔ **LAI cannot rescue p = 2.3** — it would need 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0.
- ⛔ **The tip budget is EXONERATED** (iter-11, vs an independent ground truth). So are the **shed rule,
  `MAX_CAT`, reiteration rate**, and **`N_def` accumulating with tip age** (REFUTED).
- ⛔ **The crown was never 2× too wide** — five width mechanisms built and refuted against an artifact.
  **Never add a sixth.**
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
