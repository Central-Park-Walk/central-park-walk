# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-21 DONE — no model change, and the strongest result the project has had: THE TWO GROUND TRUTHS
AGREE.** The size term is still CODED and OFF; the shipped model is unchanged (the iter-17 tree).

- **★★★ THE SAPWOOD TARGET AND THE TWIG-COUNT TARGET ARE THE SAME TARGET.** Never compared before.
  Invert the model's own pipe law (`A_sap ∝ L^(2/p)`, `L` = total real leaf count) for the `L` each tier
  needs to reach the census's ~50% sapwood: **m needs L = 59,700 (×6.75), l needs L = 192,700 (×16.5)**
  ⇒ `L(l)/L(m) = 3.23`. The **independent** Hellström real-tip census says **×3.0**. A 7% match.
  ⇒ **`N_def` is not mis-SHAPED. It is mis-ANCHORED, ~6.75× too low.** `S(m) ≈ 6.75`, `S(l) ≈ 16.5`.
- **★★ ONE TERM MOVES BOTH TRUTHS, IN OPPOSITE DIRECTIONS.** `c_H` is banked at the `S` of the year a unit
  DIED (`nd.death_c` — already coded, iter-15). A **rising** `S(t)` makes the early deaths (most of them:
  F_H 28 → 457) bank *less* heartwood while live tips carry *more* sapwood: **`A_sap` UP and `A_heart` DOWN
  from the same term.** That is how sap_frac reaches 50% while `A_built` — and so DBH (0.93/0.94×) — holds.
- **★ STATICS IS EXONERATED.** `pipe/built = 100.0%` in all three tiers (`tmp/iter21_sapwood_split.py`):
  the cantilever is **never binding at the base**, so `sap_frac ≡ sap_frac_pipe`. Defect 1 really is the
  plumbing. Six iterations of numerator-hunting were aimed at the right mechanism.
- **★ BOTH CANDIDATE NUMERATORS DIED BEFORE THE EDITOR OPENED** (zero CPU-seconds — the rail worked):
  - `M^(3/4)` — **Berry et al. 2024 (JXB 75:3993, OPENED)**: the ¾ is **not a metabolic law**, it *emerges
    from heartwood accumulation*, which this model already simulates. Coding it = **fitting the appearance**.
    (And the measured exponent isn't ¾: Xu 2014 = **0.873**, CI 0.851–0.895.)
  - `L ∝ V_sapwood` (Berry's actual law) — laid on top of the pipe law the model **already has**, it
    over-determines the system: `L ∝ h^(1/(1−2/p))` = **h^7.67**. Detonates worse than iter-20.

## The measurement everything now hangs on (iter-21, all 3 tiers)

    tier age   DBH    A_built    A_sap  A_heart  sap/built  pipe/built   F_S   F_H
      s   15  1.43x    258.7c    54.1c   204.6c     20.9%      100.0%    10    28
      m   47  0.93x   1260.1c   120.1c  1140.1c      9.5%      100.0%    25   156
      l  104  0.94x   3492.6c   152.8c  3339.8c      4.4%      100.0%    33   457

## Open defects

1. **★★ The live leaf-unit count saturates** — still THE defect, still `N_def`. Now **quantified**: `L` must
   reach 59.7k (m) and 192.7k (l), and `S` must RISE ~2.44× from m to l.
2. **Caliber splay** — `s 1.43, m 0.93, l 0.94` (term off). One-sided, all in `s`. Same thing as (3).
3. **`s` floor** — a constant `N_def` over-serves the sapling. Free when (1) lands.
4. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-22: A RISING `S(t)`, ANCHORED ON THE RATIO, WITH THE GAIN COMPUTED FIRST

- **★ The target is a RATIO, so it is scalar-proof: `A_sap/A_heart = 1` at m AND at l** (today 0.105 and
  0.046). `DBH_CALIB` cancels in a ratio — the iter-17 rail (a scalar may CENTRE, never FIX) cannot bite.
  **Pre-registered at BOTH ends of size**, and DBH (0.93/0.94×) is the rail that must HOLD.
- **Candidate law:** `S ∝ M^q`. The required `S(l)/S(m) = 2.44` **measures `q` directly** — take the tiers'
  mass ratio from the model and solve. If `M(l)/M(m) ≈ 8–10`, then **`q ≈ 0.4`**, which IS the loop gain
  (amplification `1/(1−q)` ≈ 1.7 — tame, vs iter-19's 3.2 and iter-20's ~100). ★ **Measure the mass ratio
  and report `q` BEFORE coding the term** — `q` is the deliverable, not the tree.
- ⚠ `N_DEF_REF` / `S(m) = 1` is an **anchor now known to be wrong by 6.75×**. Re-anchoring it is not a
  "scalar fix" — it is the term's own definition. But re-anchor it *with* the law, not before it.

## Rails — each cost a session; do not re-litigate

- ⛔ **★ `N_def` MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, iter-15) — positive feedback on income,
  measured from its own product.
- ⛔ **★ …NOR LINEARLY FROM MASS** (iter-20). `N_def ∝ M_sub`: the divisor cancels, aggregate gain = 1.0,
  transcritical bifurcation, **no constant leaves all three tiers sane.** Do not re-pin, re-solve, or
  "just try a lower cap". The fix is the **EXPONENT**.
- ⛔ **★ …NOR FROM SAPWOOD VOLUME** (iter-21). The model already owns the pipe law; adding Berry's
  isometric `L ∝ V_sap` over-determines it ⇒ `L ∝ h^7.67`. **A law that is stable alone can detonate in
  company — compute a new term's gain IN THE PRESENCE OF THE EXISTING TERMS.**
- ⛔ **★ …AND DO NOT CODE `M^(3/4)`.** It is an **output** of the heartwood law we already simulate
  (Berry 2024), not an input. Coding it is fitting the appearance.
- ⛔ **★ Solve a loop's constant INSIDE the loop** (iter-19) — an open-loop pin measures a tree that never
  exists. ★ But **a root-find that CONVERGES can still be the refutation: report the local SENSITIVITY
  with the root.** ~100 means unsolvable, not solved.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age — a parameter in an
  output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn `HEART_RATIO`
  down to buy sapwood — iter-21 shows the *numerator* lowers `A_heart` on its own, via `death_c`.
  ⚠ And `F_H = 0` is a STARVATION signature, never a heartwood win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). A scalar may **CENTRE**
  and **UN-SUPPRESS**; it may never **FIX**. ⇒ **so target a RATIO.**
- ⛔ **LAI cannot rescue p = 2.3** (needs 2.45 → 6.96 → 12.18; plane is 4.0–6.0). ⚠ `p = 2.3` is also what
  puts 1.0 *between* the cube gain (1.30) and the square gain (0.87) — it is load-bearing twice.
- ⛔ **EXONERATED — do not re-indict:** the tip budget (iter-11), the shed rule, `MAX_CAT`, the reiteration
  rate, `N_def` accumulating with tip AGE, and **the STATICS/cantilever (iter-21)**. **The crown was never
  2× too wide** — five width mechanisms built and refuted. No sixth.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13. Read
  and on disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Aye's equations are **GIF images**.
  Berry 2024 + Xu 2014 were opened in iter-21 (web).
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.
- ⚠ **Grep for the probe you already built.** `sap_frac_pipe` sat unread in the code for 7 iterations.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
