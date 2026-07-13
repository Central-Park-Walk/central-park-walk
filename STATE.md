# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**★★ iter-17 DONE — THE PIPE IS RE-CENTRED AND STATICS IS ALIVE. The hard falsification did not fire.**
`DBH_CALIB 12.85 → 3.813` and `ALPHA 2.59e-4 → 2.281e-5` — one scalar `k = 1/3.37` in two constants,
a derivation with no search: `R_TIP → k·R_TIP`, `ALPHA → k²·ALPHA` leaves the price of a unit of
extension unchanged, so lengths are invariant and every radius scales by `k`. It is EXACT while the
support bill is zero — which is exactly the condition iter-16 measured, and exactly the condition it
was built to destroy.

**The pre-registered prediction, and what came back:**

- **Statics wakes up.** Median `r_mech/r_pipe` **0.14/0.20/0.23 → 0.22/0.56/0.52**; max **1.03 → 2.54**.
  On load-bearing wood (lever > 2 m) it now binds on **55% (m) and 72% (l)** of nodes, against 0.2%.
- **`_bill_total` leaves 0.0000 for the first time.** On `l`: non-zero in **86/104 years**, 0.2586 m³
  of support wood, taking **4.8% of the pool at yr 20, 20.7% at yr 47, 63.7% at yr 60, 49.2% at 104 —
  and 0.0% at yr 10.** A magnitude, not a slope. **Absent in a sapling, dominant in a centenarian**:
  that is the shape defect 1 has wanted since iter-10.
- **And the rails HELD, which is how we know the instrument is honest.** DBH **1.43 / 0.93 / 0.94×**;
  re-centred on m: **s 1.54, l 1.01** against a prediction of **s 1.53, l 1.00**. Sapwood **20.9 / 9.5
  / 4.4%** — unmoved (was 18.3/9.9/4.7). The scalar CENTRED and UN-SUPPRESSED. It fixed nothing, took
  nothing, and hid nothing. **Defect 1 is exactly as alive as it was this morning.**

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — still THE defect, and it is still `N_def`.** The economy
   is scale-free in tips (income ∝ tips, cost ∝ tips ⇒ they cancel; `docs/grower_saturation_diagnosis.md`).
   iter-15 confirmed the *cure* (a size-dependent `N_def` on both sides — it took `s` from 5.15× to
   1.15×) and refuted its numerator (`V_crown`); iter-16 refuted the next (cantilever capacity, on a
   PIPE radius). **Ground truth: real tips ×~3.0 m→l** (Hellström b(n) ×3.09; census basal area ×2.71 —
   independent, and they agree) ⇒ sapwood ≈ 50% at 104 yr with c_H held at c_S.
2. ~~`DBH_CALIB` is stale~~ — **CLOSED, iter-17.** It was never a cosmetic re-centring: it was what
   hid (1)'s only candidate cure.
3. **Caliber splay** — now honestly stated instead of buried under a 3.4×: **s 1.54, m 1.00, l 1.01.**
   The whole residual error is now ONE-SIDED and it is ALL IN `s`. See defect 4 — they are the same thing.
4. **`s` floor** — cause confirmed, cure known (iter-15): it is (1) from the other end. A constant
   `N_def` over-serves the sapling. Free when (1) lands; nothing else will touch it.
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-18: THE SIZE TERM GOES IN THE STATICS. ⚠ BUT COMPUTE THE LOOP GAIN FIRST — THAT IS THE RAIL, AND IT IS NOT A FORMALITY.

`N_def` must be read off a quantity **this year's income cannot bid up**. iter-16 refuted
`N_cap ∝ r³/lever` on a **loop gain of 1.30 > 1** — but that gain was computed with `r` taken from the
**PIPE** (`r ∝ T^(1/p) = T^0.435` ⇒ `r³/lever ∝ T^1.30`, strength outrunning the load that sets it).
**On 55–72% of load-bearing wood the pipe no longer sets `r`. Statics does.** The gain must therefore
be re-derived, and it is a genuinely different number:

- if the moment is dominated by **WOOD** mass (`∝ r²·L·ρ`): `r³ ∝ r²·L·lever` ⇒ `r ∝ L·lever`, with
  **no `T` in it at all** ⇒ `N_cap ∝ r³/lever` has **loop gain 0 in T.** Exogenous *and* stable — the
  regulator we have been looking for since iter-15.
- if it is dominated by **LEAF** mass (`∝ T·lever`): `r ∝ (T·lever)^(1/3)` ⇒ `N_cap ∝ T`. **Gain
  exactly 1.0 — a knife edge**, neutrally stable, and not safe to code.

iter-8's falsification §5 asserts wood dominates. **It is an assertion, and iter-16 is the whole lesson
about building on an eight-iteration-old assertion.** So:

> **iter-18 STEP 1 (measure, do not assume): on the nodes where statics now BINDS, what is the
> wood-vs-leaf share of the bending moment `M`, and what is the resulting `d log N_cap / d log T`?**
> `tmp/iter16_mech_probe.py` already computes `M`, the wood mass and `LEAF_KG` per node — this is a
> reporting change to a script that runs, not a new mechanism. **If the gain is < 1 with margin, code
> the term. If it is ≈ 1, STOP: it is a knife edge and we say so.**

## Rails — each cost a session; do not re-litigate

- ⛔ **★ `N_def` MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, hull or voxels; iter-15) — positive
  feedback on income, measured from its own product. **Check the loop gain of the NEXT one BEFORE
  coding it.** (iter-16 refuted the cantilever-on-a-pipe-radius at gain 1.30 for exactly this reason.
  iter-17 did not repeal that; it changed what sets `r`, so the gain must be RE-COMPUTED, not assumed
  to have improved.)
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` on years makes DBH an analytic function of age — a
  parameter in an output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn
  `HEART_RATIO` down to buy sapwood.
- ⛔ **NO SCALAR CAN MOVE THE SAPWOOD FRACTION — `DBH_CALIB` CANCELS.** iter-17 **measured this rail
  holding** (sapwood 18.3/9.9/4.7 → 20.9/9.5/4.4 under a 3.37× thinning). A scalar may **CENTRE** a
  two-sided error and **UN-SUPPRESS** a mechanism; it may never **FIX** the error. `DBH_CALIB` is now
  spent — there is no third scalar move left. **The remaining error is structural, and it is (1).**
- ⛔ **LAI cannot rescue p = 2.3** (needs 2.45 → 6.96 → 12.18; plane is 4.0–6.0).
- ⛔ **EXONERATED — do not re-indict:** the tip budget (iter-11), the shed rule, `MAX_CAT`, the
  reiteration rate, and `N_def` accumulating with tip AGE (refuted on paper: A4/A5 sprays self-prune
  in 1–4 yr). **The crown was never 2× too wide** — five width mechanisms built and refuted. No sixth.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  Aye 2022 and Hellström 2018 are read (`tmp/papers/`, gitignored). Aye's equations are **GIF images** —
  a text-only fetch silently deletes every number.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Housekeeping

- `LEDGER.md` is **~25 KB** — at the `/distill` threshold. Run it **between** units of work, never inside one.
- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
