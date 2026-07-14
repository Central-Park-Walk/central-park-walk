# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-20 DONE — `MASS_CAP` was SOLVED in the closed loop, and the solve REFUTED THE NUMERATOR.** The
size term stays CODED and OFF. Shipped model = the iter-17 tree, re-verified unchanged after the edit
(DBH 1.43 / 0.93 / 0.94x census, sapwood 20.9 / 9.5 / 4.4%).

- **The root exists and it is a KNIFE EDGE.** `MASS_CAP ≈ 2.205` is a **transcritical bifurcation**:
  2.1832 → `S(m)` = 0.58; 2.2568 → 9.73; 3.14 → 1102 and a **66-tonne** tree with 7 tips.
  `d log S / d log MASS_CAP` ≈ **80–130** ⇒ **loop gain ≈ 0.99**, not iter-18's 0.69.
- **★★ NO CONSTANT LEAVES ALL THREE TIERS SANE.** At the solved root (2.2059): `s` DBH **0.52x** and
  still **on the floor** (`F_H` = 0, starved) · `m` 0.76x, `S` = 0.769 — it does not even reproduce its
  own solved root of 1.000 · `l` **33.6x — a 23.9 METRE trunk**, `S` = 51,817. **Age is the bifurcation
  parameter.**
- **★ THE ALGEBRA THAT KILLS IT — one line, available before a single CPU-second was spent:**
  `N_def · n_tips ≡ MASS_CAP · M_sub` — **the `n_tips` division CANCELS in the total.** So the crown's
  total leaf count ∝ the tree's own mass ⇒ `dM/dt ∝ MASS_CAP·M`, a **linear positive feedback on mass**.
  **`n_tips` is a REDISTRIBUTION, NOT A REGULATOR** — it parcels the twigs out; it cannot change how many
  there are. Self-shading was the only bound, and shade is cast at *marker* resolution, so as `n_tips`
  collapses (287 → 7) the regulator evaporates exactly when it is needed.
- **★ iter-18's gain of 0.69 was not wrong — it was of the WRONG LOOP** (one tip's radius). The loop that
  runs is the whole crown's leaf count against the whole tree's mass, and its gain is the **exponent on
  `M_sub`**, i.e. 1.0. A per-element gain does not bound an aggregate loop.
- **Shipped and kept:** `S_MIN = 1/N_DEF_REF` (0.046) — a tip stands for **at least one real twig**. A
  definition, not a knob. (The old 0.02 = 0.4 twigs/tip was incoherent.) Inert while the term is off.
- **Exonerated:** `M_sub` really is exogenous *within* the year. That property held. It is not enough.

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — still THE defect, still `N_def`, and THE NUMERATOR IS OPEN
   AGAIN.** Ground truth: real tips ×~3.0 m→l ⇒ sapwood ≈ 50% at 104 yr (today 4.4%).
2. **Caliber splay** — `s 1.43, m 0.93, l 0.94` (term off). One-sided, all in `s`. Same thing as (3).
3. **`s` floor** — a constant `N_def` over-serves the sapling. Free when (1) lands.
4. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-21: A SUB-LINEAR NUMERATOR. THE EXPONENT *IS* THE GAIN.

- Total leaf ∝ `M^q` with **`q < 1`** is the only shape that bounds the loop **structurally** rather than
  by luck. The standard allometry puts leaf mass ∝ `M^(3/4)` (WBE / Enquist).
- ⚠ **READ THE PAPER FIRST — West, Brown & Enquist is a MEMORY right now, not a citation.** This project
  has already paid two iterations for a fabricated author line. Open it, read the figures, then code.
- ★ **Compute the gain of the WHOLE-CROWN loop before writing the line.** Reduce the term algebraically
  first (`N_def · n_tips = ?`) and take the gain of *that*, not of one tip's radius.
- ★ **Pre-register at BOTH ENDS of size.** One tier's anchor is not evidence; the SPREAD is the claim. A
  sane `m` flanked by a starved `s` and a detonated `l` is what a bad exponent looks like.

## Rails — each cost a session; do not re-litigate

- ⛔ **★ `N_def` MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, iter-15) — positive feedback on income,
  measured from its own product.
- ⛔ **★ …AND EXOGENOUS IS NOT ENOUGH** (iter-20). `N_def ∝ M_sub` is **structurally refuted**: the divisor
  cancels, the aggregate gain is 1.0, and no constant exists. **Do not re-pin it, do not re-solve it, do
  not "just try a lower cap".** The fix is the EXPONENT, not the constant.
- ⛔ **★ …AND SOLVE A LOOP'S CONSTANT INSIDE THE LOOP** (iter-19) — an open-loop pin measures a tree that
  never exists. But ★ **a root-find that CONVERGES can still be the refutation: report the local
  SENSITIVITY with the root.** ~100 means unsolvable, not solved.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age — a parameter in an
  output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn `HEART_RATIO`
  down to buy sapwood. ⚠ And `F_H = 0` is a STARVATION signature, never a heartwood win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). A scalar may **CENTRE**
  and **UN-SUPPRESS**; it may never **FIX**. The remaining error is structural.
- ⛔ **LAI cannot rescue p = 2.3** (needs 2.45 → 6.96 → 12.18; plane is 4.0–6.0). ⚠ `p = 2.3` is also what
  puts 1.0 *between* the cube gain (1.30) and the square gain (0.87) — it is load-bearing twice.
- ⛔ **EXONERATED — do not re-indict:** the tip budget (iter-11), the shed rule, `MAX_CAT`, the reiteration
  rate, and `N_def` accumulating with tip AGE. **The crown was never 2× too wide** — five width mechanisms
  built and refuted. No sixth.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13. Aye
  2022 and Hellström 2018 are read (`tmp/papers/`, gitignored). Aye's equations are **GIF images**.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
