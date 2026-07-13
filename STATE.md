# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-16 DONE — the cantilever plan is REFUTED, and it never got coded. That is the win.** iter-15's
successor was to read `N_def` off the self-support capacity (`N_cap ∝ r³/lever` — settled wood, income
cannot bid it up). It dies twice over:

- **Analytic.** The pipe sets `r ∝ T^(1/p) = T^0.435`; statics demands only `r ∝ (T·lever)^(1/3) =
  T^0.33`. So capacity `r³/lever ∝ T^1.30` **outgrows the load that sets it** — loop gain 1.30 > 1, a
  runaway. Exogenous is necessary, **not sufficient**: compute the gain before you code the term.
- **Measured** (`tmp/iter16_mech_probe.py`, every wood node, every year, 3 tiers). **Statics never
  binds.** Median `r_mech/r_pipe` = 0.14 / 0.20 / 0.23 (s/m/l); max 0.65 / 1.03 / 1.03. On lever > 2 m
  wood — where iter-8's docstring claimed **42–62%** binding — it binds on **9/958** and **26/10917**
  nodes, by **3%**. `_bill_total = 0.0000` is **STRUCTURAL, not a wiring bug.**

**★★ AND THE REFUTATION HANDS OVER THE LEAD: THE FAT PIPE HAS BEEN SUPPRESSING THE ONLY NON-SCALE-FREE
LAW WE OWN.** The pipe, the light-per-marker and the tip budget are all scale-free — **statics is the
one law with an absolute length scale in it** (SIGMA, GRAV, RHO), so it is the only place a size term
can come from. A 3.4×-too-fat pipe drowns it: `r_mech` falls only as `r_pipe^(2/3)` where wood mass
dominates the moment and **not at all** where leaf mass does, so a census-correct pipe lifts
`r_mech/r_pipe` by **1.5× at the bole and up to 3.4× on the distal limbs** — where the leverage is.

Model unchanged (two stale docstrings corrected). Baseline still iter-14: DBH 5.15 / 3.37 / 3.36×.

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — still THE defect, and it is still `N_def`.** The economy
   is scale-free in tips (income ∝ tips, cost ∝ tips ⇒ they cancel; `docs/grower_saturation_diagnosis.md`).
   iter-15 confirmed the *cure* (a size-dependent `N_def` on both sides — it took `s` from 5.15× to
   1.15×) and refuted its numerator (`V_crown`); iter-16 refutes the *next* numerator (cantilever).
   **Ground truth: real tips ×~3.0 m→l** (Hellström b(n) ×3.09; census basal area ×2.71 — independent,
   and they agree) ⇒ sapwood ≈ 50% at 104 yr with c_H held at c_S.
2. **★ `DBH_CALIB` is stale** (fitted heartwood-free, iter-9) ⇒ the pipe is 3.4× too fat. **Promoted
   from "downstream" to NEXT — it is not a cosmetic re-centring, it is what hides (1)'s cure.**
3. **Caliber splay** — s 5.15 / m 3.37 / l 3.36×. Re-centred on m: **s 1.53, l 1.00.** (2)'s to fix.
4. ~~`s` floor~~ — **cause confirmed, cure known** (iter-15): it is (1) from the other end. Free when (1) lands.
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-17: REFIT `DBH_CALIB`, THEN RE-RUN THE PROBE. (A DELIBERATE RE-ORDERING.)

STATE has said "refit `DBH_CALIB` only *after* (1)" since iter-12, on the correct ground that a scalar
cannot fix a two-sided error. **iter-16 overturns the ORDER, not the rail:** the refit is not being
asked to fix (1) — it is being asked to **stop hiding it.** The rails below still hold.

It is a **derivation, not a search** (see the R_TIP block, l. 60–67): `R_TIP → k·R_TIP` with
`ALPHA → k²·ALPHA` leaves the cost of a unit of extension unchanged, so the economy is preserved
exactly and only the wood thins. Take `k = 1/3.37` from the m tier, then:

> **Re-run `tmp/iter16_mech_probe.py`. Does statics wake up?** Predicted: median `r_mech/r_pipe` → ~0.30
> at the bole, > 1 on the distal limbs; `_bill_total` leaves 0.0000 for the first time. **If it does
> not, the mechanical term is dead for good and (1) needs a source we have not yet named — say so and
> stop; do not tune.** If it does, iter-18 puts the size term there.

## Rails — each cost a session; do not re-litigate

- ⛔ **★ `N_def` MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, hull or voxels; iter-15) — positive
  feedback on income, measured from its own product. ⛔ **NOR FROM CANTILEVER CAPACITY** (iter-16) —
  loop gain 1.30, and statics never binds anyway. **Check the loop gain of the NEXT one before coding.**
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` on years makes DBH an analytic function of age — a
  parameter in an output's clothes. The paper forbids it (p. E45). **b(n) is the VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE** (iters 12–14); its constant is pinned twice. Do NOT turn
  `HEART_RATIO` down to buy sapwood.
- ⛔ **No scalar can move the SAPWOOD FRACTION — `DBH_CALIB` CANCELS.** It is a structural error, not a
  calibration one. A scalar may **CENTRE** a two-sided error and **UN-SUPPRESS** a mechanism; it may
  never **FIX** the error. iter-17 is the second thing, not the third.
- ⛔ **LAI cannot rescue p = 2.3** (needs 2.45 → 6.96 → 12.18; plane is 4.0–6.0).
- ⛔ **EXONERATED — do not re-indict:** the tip budget (iter-11), the shed rule, `MAX_CAT`, the
  reiteration rate, and `N_def` accumulating with tip AGE (refuted on paper: A4/A5 sprays self-prune
  in 1–4 yr). **The crown was never 2× too wide** — five width mechanisms built and refuted. No sixth.
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iters 12 AND 13.
  Aye 2022 and Hellström 2018 are read (`tmp/papers/`, gitignored). Aye's equations are **GIF images** —
  a text-only fetch silently deletes every number.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
