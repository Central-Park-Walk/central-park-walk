# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-12 DONE** (`ffc3496`). The pipe layer had **no heartwood**, and the cause was a real bug:
`ratchet()` summed only LIVE children into a `radius` array rebuilt from zero every year, so a shed
branch's wood **vanished** from the trunk — pure sapwood at every age. Fixed per Shinozaki's disused
pipes / Kubo 2022 branch-thinning: sum ALL woody children, dead ones frozen at their death radius.
**No new constant.** It works, and **it is not a scalar** — the falsifier passed. Per-tier DBH
multiplier **2.02× / 2.49× / 3.14×**, monotone in age; splay s/l fell **2.68× → 1.73×**.

    DBH vs census    before: s 1.96  m 1.00  l 0.73     after: s 3.96  m 2.49  l 2.29
    re-centred on m                                     after: s 1.59  m 1.00  l 0.92

⚠ But absolute girth now **overshoots ~2.5×**: `DBH_CALIB` was fitted in a heartwood-free world and is
stale. **Do not ship.**

## Open defects

1. **★ The sapwood fraction is wrong** — the model now implies sapwood = 16% (m) / 10% (l) of basal
   area, but Platanus is noted for **WIDE** sapwood ⇒ the dead sum **over-counts**: disused pipes are
   summed in the **p = 2.3 metric, which is not area-conserving**. Heartwood is AREA. This is iter-13.
2. **`DBH_CALIB` is stale** — the one legitimate re-centring scalar; refit ONCE, but only *after* (1).
3. **Caliber splay, residual** — re-centred: s 1.59 / l 0.92. `l` has come home; **`s` is the one left**.
4. **`s` floor** — constant `R_TIP` floors DBH at 2·R_TIP at any age; `s`'s census DBH is 12.7 cm ⇒ `s`
   is pinned near the floor and *cannot* be thin. This is why `s` stays thick. (A `DBH_CALIB` refit
   moves the floor too — watch it.) **One term won't mend both this and (3).**
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — the one hypothesis: iter-13 = SUM THE DEAD PIPES AS AREA

Defect 2 is the lever, and it is coupled to the overshoot. Live pipes branch with p = 2.3 (da Vinci
taper); **disused pipes are dead wood — they are conserved AREA (p = 2), not a taper law.** Bank the
dead term as `A_dead` (area) and combine `A = π·r_live² + A_dead` while the LIVE sum keeps p = 2.3.
Predicts: less over-count, a bigger sapwood fraction, and less of the 2.5× overshoot — *before* any
refit. Refit `DBH_CALIB` **once, after** that, and only then read the residual splay. **Derive first.**

## Rails — each cost a session; do not re-litigate

- ⛔ **No scalar can FIX a two-sided error** (`R0`, `DBH_CALIB`, `R_TIP`, constant `N_def` are uniform
  DBH multipliers) — but a scalar is the right tool to **CENTRE** one, *after* a size-dependent term exists.
- ⛔ **LAI cannot rescue p = 2.3** — it would need 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0.
- ⛔ **The tip budget is EXONERATED** (iter-11, measured against an independent ground truth). The old
  "`l` has 2.1× too few tips" was an artifact of reading the pipe layer's own demand.
- ⛔ **The crown was never 2× too wide** — five width mechanisms built and refuted against an artifact.
  **Never add a sixth.**
- ⛔ **Shed rule, `MAX_CAT`, reiteration rate, `N_def` accumulating with tip age: EXONERATED / REFUTED.**
- ⚠ **Suspect the CLOCK before the MECHANISM** — that has been the answer twice.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
