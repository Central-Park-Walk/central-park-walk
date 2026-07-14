# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-23 DONE — investigation, no model change. The mechanism is found, and it is NEITHER of the two
things we suspected.** Shipped model is still the iter-17 tree. Probe: `tmp/iter23_survival.py`.

- **★ FACT 0, read from the code:** `MASS_CAP is None` ⇒ `update_n_def()` returns immediately ⇒
  **`s_def == 1.0` everywhere.** The iter-15 S-scaled shade is NOT LIVE in the shipped tree. Entries
  since iter-20 reasoned about a term that is switched off. **Check the flag before the theory.**
- **★★ SELF-SHADING IS REFUTED** (iter-20's pre-registered suspect). The l crown is **BRIGHTER**:
  light/marker 1.219 → 1.592 (**x1.30**); light per live tip 8.08 → 14.32 (**x1.77**).
- **★★ "BUDS FIRED INTO THE DARK" IS REFUTED.** The stillbirth fraction is **FLAT: 68% → 70%.**
  Births scale x2.70 (census wants x3.0); dark births x2.78. Birth is not the defect.
- **★★★ THE CROWN IS NOT DARKER — IT IS EMPTIER.**

      crown envelope area   230.7 -> 515.0 m2  = x2.23
      LIVE tips (F_S)          25 ->     33    = x1.32
      tip density on the lit surface           = x0.59   <- HALVES
      => mean tip LIFETIME  (1.32 / 2.70)      = x0.49   <- HALVES

  Live tips = births x lifetime. **Births are right; the LIFETIME halves.** The l crown is a bigger,
  sparser, brighter shell — which is *why* light per marker went UP: fewer neighbours to shade you.
- **★★★ AND WHY LIFETIME HALVES: income is counted at TIP resolution, cost at INTERNODE resolution.**
  The gate is `light(subtree)/size(subtree) < TAU_SHED (0.18)`. Its numerator counts only the 12
  markers on each ARMATURE TIP; its denominator counts EVERY WOODY INTERNODE. At l an axis carries
  **8.5x more wood per live tip** (tips/internode 1.000 → 0.118), so its gate ratio sits 3.4x closer to
  the cliff (1.810 → 0.593) and an overtopped tip has no margin left. **A real plane's limb bears short
  shoots along its whole lit length, so its income grows with the limb. Ours does not.** The deferred
  A4/A5 layer is exactly the foliage that would pay that bill — the SAME deferral iter-22 indicted for
  `N_def`, arriving from the other side.
- ⚠ **What the evidence FORBIDS:** wood-per-tip is the **margin**, not the killer. 96% of the axes the
  gate actually sheds are zero-light single-internode **stillbirths** (median L/tip = 0.000), ~82% of
  all shed events in both tiers. **A fix must lengthen tip LIFETIME — not merely lower the rent.**

## Open defects

1. **★★ THE LIT CROWN SURFACE IS UNDER-POPULATED WITH FOLIAGE** — tip density x0.59, tip lifetime
   x0.49. Defect 1 restated correctly. It is **not** `N_def`, **not** shade, **not** the birth rate.
2. **Caliber splay** — `s 1.43, m 0.93, l 0.94`. One-sided, all in `s`.
3. **`s` floor** — a constant `N_def` over-serves the sapling. Free when (1) lands.
4. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-24: DERIVE THE A5 SHORT-SHOOT LAYER (the deferral, paid at last)

- **★ The hypothesis:** foliage lives only at armature apices, so a limb's income cannot grow with the
  limb. Give every **live internode standing in light** its own short-shoot foliage cohort (C&E A5:
  space-filling twigs that self-prune in 1–4 yr — `FOLIAGE_LIFE = 3` already encodes exactly that;
  reuse `FOLIAGE_PER_TIP`, **invent no new constant**). Then income scales with **lit branch LENGTH**,
  the wood/tip divergence closes, and the leaf count becomes an OUTPUT of the lit surface.
- **★★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (the standing rail). Income ∝ lit foliated
  length. Against mass (x3.28 m→l): if lit length tracks the **lit SURFACE** (x2.23) ⇒ `q = 0.68`,
  amplification **3.1x — stable**, and the self-shading of interior short shoots is the negative
  feedback that keeps it there. If it tracks **TOTAL wood** (n_nodes, x2.98) ⇒ `q = 0.92`,
  amplification **12x — the iter-20 bifurcation regime.** ⇒ **Short shoots MUST be gated on light, and
  the gate must BITE.** Measure the lit/total foliated-length ratio and report `q` WITH the result.
- **★ The rails to PRE-REGISTER:** DBH must HOLD (0.93/0.94x — the tight instrument, 9–19%). `sap_frac`
  must rise at **BOTH** m and l. Tip **lifetime** must rise (that is the target); tip **birth** rate
  must NOT (already right at x2.70). The census bar is `L(l)/L(m) = 3.23` — ⚠ the lit surface today is
  only x2.23, so **if the new crown's lit length does not reach x3.23, the defect survives.** Say so
  before the run, not after.
- ⛔ **Do NOT touch TAU_SHED.** Lowering the rent is the fitted-constant shortcut, and (C) says it would
  spare stillbirths, not lengthen lifetimes.

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE `N_def` NUMERATOR FAMILY IS CLOSED (iter-22).** No variable the tree owns grows faster
  than the x3.23 the census demands ⇒ every `L = K*X^q` has gain >= 0.987. **Do not propose a seventh
  numerator.** Dead: `V_crown` (15), `M_sub` linear (20), `V_sap` (21), `M^q` (22). ⚠ The family test
  assumes the tree's X-trajectory is FIXED — deriving a deferred LAYER changes X itself, so it is not a
  member. But it must clear the same bar: **tabulate the ratio before coding.**
- ⛔ **★ …AND DO NOT CODE `M^(3/4)`.** It is an **output** of the heartwood law we already simulate
  (Berry 2024, opened), not an input.
- ⛔ **★ Solve a loop's constant INSIDE the loop** (iter-19). ★ A root-find that CONVERGES can still be
  the refutation: report the local SENSITIVITY with the root. >=10x means unsolvable.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age. **b(n) is the
  VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14). ⚠ `F_H = 0` is a STARVATION signature, never a win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). A scalar may **CENTRE**
  and **UN-SUPPRESS**; it may never **FIX**. ⇒ **target a RATIO.**
- ⛔ **STATICS IS EXONERATED** (iter-21): `pipe/built = 100.0%` in all three tiers.
- ⛔ **LAI cannot rescue p = 2.3.** ⚠ `p = 2.3` is load-bearing twice (it also puts 1.0 between the cube
  gain 1.30 and the square gain 0.87).
- ⛔ **EXONERATED FOR CROWN WIDTH — do not re-indict *for width*:** the tip budget (iter-11), the shed
  rule, `MAX_CAT`, the reiteration rate, `N_def` accumulating with tip AGE, the statics. **The crown was
  never 2x too wide.** ⚠ iter-23 re-indicts the shed gate's *resolution* for TIP LIFETIME — a different
  charge, on new evidence. If the width verdict is ever threatened, STOP.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13. On
  disk (`tmp/papers/`, gitignored): Aye 2022 (equations are GIF images), Hellström 2018. Berry 2024 +
  Xu 2014 opened in iter-21 (web).
- ⚠ **Instrument limit:** seed spread is 127% (`s`) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%).**
- ⚠ **★ CHECK THE FLAG BEFORE THE THEORY** (iter-23): `MASS_CAP`, `S_IN_SHADE`, `S_IN_LIGHT`, `MAX_CAT`.
  A retired term reads exactly like a live one in the source, and three iterations theorised about
  `s_def` while it was pinned at 1.0.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
