# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-14 DONE — hypothesis REFUTED, and the refutation is the whole finding.** The heartwood bank now
counts **lost leaf units** (Aye et al. 2022 Eq. 6) instead of dead branch cross-sections, which removed
a genuine recursive double-count. It moved almost nothing: **sapwood at l went 3.7% → 4.7%** against a
50% target (the old sublinear p = 2.3 aggregation at death had been silently cancelling the recursion).
The heartwood law is now correct-by-the-paper. **It was never the defect.** Keep it; stop touching it.

**★ THE DEFECT IS THE LIVE CROWN, AND iter-14 PINNED IT.** With the count clean, c_H is fixed by two
independent routes that AGREE: the paper's physics (heartwood IS the disused sapwood pipe ⇒ c_H = c_S)
and the census (the measured m→l basal-area growth, ×2.71, demands c_H/c_S = **1.07**). The 50% sapwood
target would demand **0.049** — **22× apart, so one constant cannot serve both, and the census has first
claim.** Hold c_H = c_S, and the arithmetic is forced:

    tier  F_S live  F_H lost  lost/live  sapwood   DBH vs census      F_S needed for 50% at l
    s        10        33       3.3       18.3%      5.15x             F_H^(p/2) = 1311
    m        31       180       5.8        9.9%      3.37x             we carry 41
    l        41       514      12.5        4.7%      3.36x             ⇒ 32x TOO SMALL

F_S goes 10 → 31 → 41 over 15/47/104 yr (**m→l = ×1.32**) while the real trunk's basal area grows
**×2.71**. The model's leaf area SATURATES; a real plane's does not.

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — this is now THE defect, and it is `N_def`.** One armature
   tip stands in for a FIXED `DBH_CALIB^p` ≈ 354 real twigs at every age and size: it over-serves the
   sapling and under-serves the centenarian, in one monotone direction. Flagged in the module header
   since iter-9; iter-14 is the first *quantitative* indictment of it. **2–4 are downstream and cannot
   be read until it is fixed.** ⚠ It does NOT contradict iter-11's exoneration of the tip budget — the
   ARMATURE count is fine; what must scale is the deferred A4/A5 foliage each tip *stands for*.
   - **★★ 2026-07-13 — MEASURED, and it is worse and cleaner than "a constant is wrong"**
     (`docs/grower_saturation_diagnosis.md`, `tmp/iter15_saturation_probe.py`). The armature tip count
     **NEVER GROWS**: 8–25 from yr 20 to yr 104, ~5 born and ~5 shed a year (458 reiterates, zero
     accumulation), with **30–50% of live apices DORMANT** — unable to buy one metamer — at every age.
     **Why: THE ECONOMY IS SCALE-FREE IN TIPS.** Each tip carries exactly 12 foliage markers ⇒
     `Q_base = 12·n_tips·L̄` ⇒ **mean income per apex = ALPHA·12·L̄, independent of `n_tips`**
     (measured `L̄` flat: 1.38 → 1.22 units/marker, yr 24 → 104), while cost per apex
     `n·π·R_TIP²·INTERNODE` is *also* constant. Income ∝ tips, cost ∝ tips — **they cancel; `n_tips`
     has no growth term anywhere** and sits at iter-9's calibrated fixed point for ever. Pool ×2.1
     over 80 yr vs a census basal area ×2.71.
   - ⚠ **SECONDARY FLAG (not chased):** `_bill_total` — the iter-8 self-support bill — reads **0.0000 m³
     in every one of the 104 years** (<0.05% of the pool). It bills only the structural *excess over
     pipe*, and pipe dominates ⇒ **self-support is not biting at all.** Not the cause of (1).
2. **`DBH_CALIB` is stale** (fitted heartwood-free) — the one legitimate re-centring scalar. Refit
   ONCE, and only *after* (1). It cannot fix (1); see the rails.
3. **Caliber splay** — s 5.15 / m 3.37 / l 3.36 (all ~3.4× too thick in absolute terms; that part is
   (2)'s to fix). Re-centred on m: **s 1.53, l 1.00.** `l` is home; **`s` is the one left.**
4. **`s` floor** — constant `R_TIP` floors DBH at 2·R_TIP at any age, and `s`'s census DBH is 12.7 cm,
   so `s` is pinned near the floor and *cannot* be thin. **One term won't mend both this and (3).**
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-15: MAKE `N_def` SIZE-DEPENDENT. Derive it; do not fit it.

**★★ 2026-07-13 — THE TARGET IS NOW SPECIFIC: `N_def` MUST ENTER THE LIGHT INCOME, NOT JUST THE LEDGER.**
Today it sits on the **cost** side (`R_TIP = DBH_CALIB·R0`) and in the DBH/heartwood **ledger**, and is
**absent from `grow_foliage()` and `build_shadow()`** — so a tip pays 354 twigs' worth of wood to extend
and earns **1 tip's worth of light**. ⛔ **A size-dependent `N_def` in the LEDGER ALONE will move the
sapwood number and leave the crown exactly as pinned** (the fixed point above is an income/cost identity,
and the ledger is not in it). A tip standing for N twigs must **intercept N twigs' worth of light and cast
N twigs' worth of shade.** Same term on both sides — still an OUTPUT, still no new fit.

The deferred A4/A5 twig system a tip stands for must grow as the tree does. **It is an OUTPUT, not a
parameter** — so do not reach for a lookup or a fitted exponent. The honest routes, in order:

- **Derive it from what a tip can actually carry.** A twig's short-shoot population is bounded by the
  light it intercepts and the wood it can hang off itself — the same two currencies the grower already
  runs (the light field and the support bill). If `N_def` falls out of those, it is derived.
- ⚠ **Read the prior art BEFORE proposing.** The last three iterations were all built on a *guess* at a
  paper's mechanism. Hellström et al. 2018 (the branch-thinning half of Aye 2022 — on the **carrying
  capacity of a branch**, which is exactly this question) is the obvious first read, and it is not yet read.

**Ground truth to hit:** F_S grows ~×2.7 m→l (not ×1.32) ⇒ sapwood ≈ 50% of basal area at 104 yr, with
c_H held at c_S. Then, and only then, refit `DBH_CALIB` once (defect 2). **The `s` floor (defect 4) is
still separate and will NOT be fixed by this.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★ THE HEARTWOOD LAW IS DONE.** Three iterations (12, 13, 14) went into it; it is now the
  published law, its constant is pinned twice over, and it is not the defect. **Do not re-open it, and
  ⛔ do NOT turn `HEART_RATIO` down to buy sapwood fraction** — that is the fit the census forbids.
- ⛔ **★ No scalar can move the SAPWOOD FRACTION — `DBH_CALIB` CANCELS.** It is R_TIP-free: a pure
  STRUCTURAL statement, not a calibration error. (iter-13; iter-14 re-derived it in leaf units.)
- ⛔ **No scalar can FIX a two-sided error** (`R0`, `DBH_CALIB`, `R_TIP`, constant `N_def` are uniform
  DBH multipliers) — but a scalar is the right tool to **CENTRE** one, *after* a size-dependent term exists.
- ⛔ **LAI cannot rescue p = 2.3** — it would need 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0.
- ⛔ **The tip budget is EXONERATED** (iter-11, vs an independent ground truth). So are the **shed rule,
  `MAX_CAT`, reiteration rate**, and **`N_def` accumulating with tip AGE** (REFUTED — note that is
  per-tip age, a *different* mechanism from `N_def` scaling with tree SIZE, which is defect 1).
- ⛔ **The crown was never 2× too wide** — five width mechanisms built and refuted against an artifact.
  **Never add a sixth.**
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iter-12 AND
  iter-13. Aye 2022 is read (local copy `tmp/papers/`, gitignored; re-fetch PMC9652016). Its equations
  are **GIF images** — a text-only fetch returns the prose with every number silently deleted.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
