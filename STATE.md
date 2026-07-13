# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-19 DONE — the size term is CODED (`N_def ∝ M_sub`, both sides, `MASS_CAP`), and it is OFF.**
The mechanism survives; **the PIN was refuted, and its failure is the whole finding.** Shipped model =
the iter-17 tree, verified unchanged after the revert (`s` DBH 18.2 cm, sapwood 20.9%).

- **Switched on at `MASS_CAP = 0.6400`, the tree came out 4x TOO THIN on every tier** — DBH
  0.34 / 0.24 / 0.23x census (baseline 1.43 / 0.93 / 0.94), `F_H = 0` (not one leaf unit ever died,
  so the 56–68% "sapwood" is a starved stick, not a win).
- **★ The ratios to baseline are 0.24 / 0.26 / 0.24 — a UNIFORM thinning.** A size term that scales
  all three tiers alike did not act as a size term. `tmp/iter19_s_trace.py`: **`S` sits ON THE
  `S_MIN` FLOOR (0.020) for 16 years** and reaches only **0.171 at the m anchor it was pinned to 1.0**.
- **★★ WHY: the pin was measured OPEN-LOOP, on a tree that never exists once the term runs.**
  `MASS_CAP = N_DEF_REF·n_tips(m)/M_sub(m)` was read off the S ≡ 1 tree. The tree that *runs* the term
  is thinner all through its youth ⇒ arrives at the anchor **lighter** (455 kg, not 848) and with
  **MORE tips** (77, not 25 — cheap tips: the `n_tips` negative feedback doing its job). Both terms of
  `S = MASS_CAP·M_sub/n_tips` move the wrong way at once.
- **★ Gain < 1 bought STABILITY, not INSENSITIVITY.** `d log S / d log MASS_CAP = 1/(1−g)` = **3.2–7.7**.
  Nothing ran away (rail 5 held; the crown neither exploded nor collapsed) — it fell into a **LOW**
  fixed point. The constant must be **SOLVED**, never estimated.
- **Exonerated:** iter-18's gain analysis · `M_sub` as the exogenous numerator · the `n_tips` negative
  feedback · **the size shape itself** — `S` still climbs monotonically 0.02 → 0.17 with the tree.

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — still THE defect, still `N_def`.** The numerator is
   settled (`M_sub`, gain 0.69). **What is open is now purely the CALIBRATION: `MASS_CAP` + `S_MIN`.**
   Ground truth: real tips ×~3.0 m→l ⇒ sapwood ≈ 50% at 104 yr.
2. **★ NEW (iter-19): `S_MIN = 0.02` is INCOHERENT, not merely small.** It puts `N_def` at **0.4 real
   twigs per armature tip** — a tip standing for less than itself. The floor must be `N_def ≥ 1` ⇒
   `S_MIN = 1/N_DEF_REF` (= 0.046; `N_DEF_REF` is only 21.7 twigs since iter-17 re-centred the pipe).
3. **Caliber splay** — `s 1.43, m 0.93, l 0.94` (term off). One-sided, all in `s`. Same thing as (4).
4. **`s` floor** — a constant `N_def` over-serves the sapling. Free when (1) lands.
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-20: SOLVE `MASS_CAP` AS A FIXED POINT OF THE LOOP IT CLOSES.

- **Fix the floor FIRST, in the same change:** `S_MIN = 1.0 / N_DEF_REF`. Not a tuning knob — it is the
  statement that a tip stands for at least one twig. The 16 floor-bound years are its work.
- **Then root-find `MASS_CAP`** on `S(m @ 47 yr) = 1` in the **closed loop** (`tmp/iter19_s_trace.py`
  prints `S` at any year; an m-tier run is ~45 s, so a ~6-eval bisection is ~5 min). It is monotone in
  `MASS_CAP`, so bisection is safe. **Bracket it first** — with a 3–8x amplification the useful range is
  NARROW: 0.64 gave S = 0.171, so expect the root within ~1.2–2x of 0.64, not 6x it.
- **★ PRE-REGISTER again — and this time the falsifiable claim is the SHAPE, not the mean.** With the
  anchor solved, `S(s)/S(m)/S(l)` must SPREAD; that is the entire point of the term. Write the predicted
  `s`/`m`/`l` DBH **and `l` sapwood** down before running. ⚠ **A uniform response = the term is inert.**
- ⚠ The mean is now cheap to hit and is therefore not evidence. **Defect 1 is decided by `l` sapwood
  (4.4% → must move materially toward ~50%) and the m→l real-tip ratio (must be ~×3.0).**

## Rails — each cost a session; do not re-litigate

- ⛔ **★ `N_def` MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, iter-15) — positive feedback on
  income, measured from its own product. **COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM.**
- ⛔ **★ …AND SOLVE THE CONSTANT INSIDE THE LOOP** (iter-19). An open-loop pin measures a tree that never
  exists. Stability (g < 1) is not insensitivity (`1/(1−g)` = 3–8).
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age — a parameter in an
  output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn `HEART_RATIO`
  down to buy sapwood. ⚠ And `F_H = 0` is a STARVATION signature, never a heartwood win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). A scalar may **CENTRE**
  and **UN-SUPPRESS**; it may never **FIX**. `DBH_CALIB` is spent. The remaining error is structural.
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
