# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-22 DONE — no model change. `q` was measured, and it REFUTED the law it was measured for. Then the
same table closed the whole FAMILY, and moved the defect.** The shipped model is still the iter-17 tree
(DBH 1.43/0.93/0.94x, sapwood 20.9/9.5/4.4%). ★ The size term has now cost SIX iterations; it is
finished, and not by being solved.

- **★★ `q = 0.987`, NOT the 0.4 the pre-registration expected.** The census demands the total real leaf
  count rise **x3.23** from m to l; the model's own mass rises **x3.28**. Same number ⇒ the exponent the
  data forces is the LINEAR one iter-20 already killed. Amplification `1/(1-q)` = **79x** — a fixed point
  finer than the model's own 10–15% seed noise. **Unsolvable, not unsolved.** (`tmp/iter22_q.py`)
- **★★★ AND THE FAMILY IS EMPTY.** For any `L = K*X^q`, the census forces `q = ln(3.23)/ln(X_l/X_m)`, so
  **gain < 1 iff `X(l)/X(m) > 3.23`.** Tabulated against *every* readable variable (`tmp/iter22_family.py`):
  mass and wood volume TIE the bar (3.279 — the knife edge); crown volume 2.97, n_nodes 2.98, F_H 2.93,
  A_built 2.77, age 2.21, crown surface 2.06, height 1.80, F_S 1.32 — **all force `q > 1`. Not one clears
  it.** ⇒ **NO NUMERATOR EXISTS.** Six iterations hunted a member of an empty set.
- **★★★ THE SAME TABLE SAYS WHERE THE DEFECT REALLY IS — TWO ROWS NOBODY DIVIDED:**

      tips EVER MADE (F_S+F_H)   181 -> 490  = x2.71     <- the census wants x3.0 (Hellstrom)
      tips STILL ALIVE    (F_S)   25 ->  33  = x1.32
      live-tip survival          13.8% -> 6.7%           <- IT HALVES FROM m TO l

  **The tree MAKES tips at very nearly the right rate. It then KILLS them.** Hold survival at m's 13.8%
  and l carries 67.6 live tips (x2.71 vs m) with **`N_def` CONSTANT, `S == 1`, no new law, no new
  constant** — 84% of the census's 3.23 with *nothing added to the model*.
- **★ This is the shortcut the standing rule names, for the sixth time.** `N_def` = what one armature tip
  *stands in for* = a **parameter in an output's clothes**, patching the deferred A4/A5 layer. A real tree
  DERIVES its tip count — from branching **and from survival**. So must we.
- ⚠ **Stale constant, caught and fixed in the code:** `N_DEF_REF` is **21.7**, not the 354 quoted in every
  comment and ledger entry since iter-8 (`DBH_CALIB` fell 12.85 -> 3.813 at iter-17). Every **ratio** — and
  so every conclusion — is unaffected; every **absolute** twig count before iter-22 is 16.3x too large.

## Open defects

1. **★★ The live leaf-unit count saturates** — still THE defect, but it is **no longer `N_def`**. It is
   **TIP SURVIVAL**: 13.8% -> 6.7% from m to l. Re-indicted with new evidence (see NEXT).
2. **Caliber splay** — `s 1.43, m 0.93, l 0.94`. One-sided, all in `s`. Same thing as (3).
3. **`s` floor** — a constant `N_def` over-serves the sapling. Free when (1) lands.
4. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-23: WHY DOES LIVE-TIP SURVIVAL HALVE? (investigate; do NOT reach for a constant)

- **★ The question, not the fix.** Survival is shading-driven (`SHADOW_A/B`, `FOLIAGE_LIFE`, the shed
  rule). ⚠ iter-20 already noted **shade is cast at MARKER resolution** — every armature tip casts the
  same 12 markers' worth regardless of what it stands for. Find out what makes the l-tier crown shade
  itself twice as hard as the m-tier one. **Get the mechanism before touching a number.**
- **⛔ DO NOT "turn the shed rate down."** That is the fitted constant this project keeps refusing. The
  rate is calibrated; the *dependence on size* is what is unexplained.
- **★ The rails to PRE-REGISTER:** DBH must HOLD (0.93/0.94x) — it is the tight instrument (9–19%).
  `sap_frac` must rise at **BOTH** m and l (a size term must be tested at both ends of size — iter-20).
  And the loop is a **negative** feedback (more tips -> more shade -> fewer tips), structurally unlike the
  numerator family — but **compute its gain before coding it anyway.**
- ⚠ **The shed rule and `MAX_CAT` are on the exonerated list — but they were exonerated for CROWN WIDTH,
  never for TIP COUNT.** This is a new indictment on new evidence, not a re-litigation. Say so, and keep
  it honest: if the width verdict is threatened, stop.

## Rails — each cost a session; do not re-litigate

- ⛔⛔ **★★★ THE `N_def` NUMERATOR FAMILY IS CLOSED (iter-22).** No variable the tree owns grows faster
  than the x3.23 the census demands ⇒ every `L = K*X^q` has gain >= 0.987. **Do not propose a seventh
  numerator.** Dead members: `V_crown` (15), `M_sub` linear (20), `V_sap` (21), `M^q` (22).
- ⛔ **★ …AND DO NOT CODE `M^(3/4)`.** It is an **output** of the heartwood law we already simulate
  (Berry 2024, opened), not an input. Coding it is fitting the appearance.
- ⛔ **★ Solve a loop's constant INSIDE the loop** (iter-19). ★ But **a root-find that CONVERGES can still
  be the refutation: report the local SENSITIVITY with the root.** >=10x means unsolvable.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` makes DBH an analytic function of age — a parameter in an
  output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn `HEART_RATIO`
  down to buy sapwood. ⚠ `F_H = 0` is a STARVATION signature, never a heartwood win.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS** (iter-17). A scalar may **CENTRE**
  and **UN-SUPPRESS**; it may never **FIX**. ⇒ **so target a RATIO.**
- ⛔ **STATICS IS EXONERATED** (iter-21): `pipe/built = 100.0%` in all three tiers — the cantilever never
  binds at the base, so `sap_frac == sap_frac_pipe`. Defect 1 really is the plumbing.
- ⛔ **LAI cannot rescue p = 2.3** (needs 2.45 -> 6.96 -> 12.18; plane is 4.0–6.0). ⚠ `p = 2.3` is also what
  puts 1.0 *between* the cube gain (1.30) and the square gain (0.87) — it is load-bearing twice.
- ⛔ **EXONERATED FOR CROWN WIDTH — do not re-indict *for width*:** the tip budget (iter-11), the shed
  rule, `MAX_CAT`, the reiteration rate, `N_def` accumulating with tip AGE, the statics. **The crown was
  never 2x too wide** — five width mechanisms built and refuted. No sixth.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13. Read
  and on disk (`tmp/papers/`, gitignored): Aye 2022, Hellström 2018. Aye's equations are **GIF images**.
  Berry 2024 + Xu 2014 were opened in iter-21 (web).
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.
- ⚠ **Grep for the probe you already built.** `sap_frac_pipe` sat unread in the code for 7 iterations.

## Housekeeping

- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
