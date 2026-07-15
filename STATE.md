# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-36: ADR-A CODED AND REFUTED. The sub-linear numerator explodes anyway.

Coded ADR Position A (`T_total = K·M_sub^q`, `q=2/E_M=0.625` a *derived* output; K by S(m@47)=1). It
**has no stable fixed point**: S stays <0.5 up to K≈31, then explodes discontinuously (K 31.09→S 0.499
n_tips 362; **K 31.14→S 94 n_tips 1** — 0.16% of K flips S 190×). Reverted to **`K_NDEF=None`** (the
S-inert baseline, verified S≡1.0000); the sub-linear code stays as the refutation's named home.

**Root cause — ADR §2 gated the WRONG loop.** Blow-ups coincide with `n_tips→1`, NOT mass runaway
(M_sub small at blow-up, ~850 kg). The divergent loop never touches mass: **S↑ → S_IN_SHADE casts more
shade/marker → interior foliage dies → n_tips↓ → S=K·M^q/n_tips ↑ → more shade** (gain>1). "The n_tips
cancels" (ADR §2) is true in the income *identity* but FALSE in the *dynamics*: n_tips is a function of
S through the shade S casts. Sub-linearity-in-mass is orthogonal to this loop; iter-20's linear form
had the identical n_tips collapse (100→65→12→7). iter-15 saw it: "S_IN_SHADE off tames it, not the loop."

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips LOOP (gain>1) IS THE REAL BLOCKER** — must be tamed BEFORE any numerator can
   stand. Candidates (iter-37): (a) cast shade at a FIXED reference density, decoupling S from the shade
   it makes; (b) drive R_TIP directly off M_sub, bypassing the n_tips divisor; (c) cap dS/dt per year.
   ⛔ COMPUTE THIS LOOP'S GAIN ON PAPER FIRST, exactly as the mass loop was gated. Do NOT re-pin K.
2. **★ SIZE-LAW STILL OFF.** With S≡1 the tree is scale-free in tips; census wants sapwood ~2× larger at
   l (F_S 2.4× low at m/l). The M^q numerator is *necessary but insufficient* — #1 gates it.
3. **★ R_TIP vs F_S degeneracy** — a size-dependent R_TIP (from S>1) hits census sapwood as well as F_S;
   biology favors the R_TIP handle. Candidate (b) above IS this handle, and it sidesteps the n_tips loop.
4. **HEARTWOOD 1.77→2.63×** over-fills with size — leaf-unit LOSS rate, ⛔ NOT `HEART_RATIO`. After #1.
5. **`s` DBH floor** — DBH floored at `2·R_TIP`=10.3 cm at any age (uniform-R_TIP floor). After #1.

## NEXT — iter-37: GATE THE S→SHADE→n_tips LOOP, then pick the handle (design/ADR, no numerator yet).

On paper: write the shade→n_tips→S gain and show which candidate (a/b/c) makes it <1. Candidate (b),
R_TIP directly off M_sub, is the strongest lead — it deletes the n_tips divisor (the whole instability)
AND is board #3's favored handle. If a design call, write it as a multi-position ADR. Refuted-if: the
chosen decoupling makes a NEW loop >1 — gain every loop it closes, not just the one you framed.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES, NOT THE ONE YOU FRAMED** (36). A var in the DENOMINATOR is a
  2nd feedback path if the numerator's var drives it too. A cancellation valid at the FIXED POINT is not
  valid along the TRAJECTORY. A stability gate must confirm the null (S≈1 achieved) before reading slope.
- ⛔ **★★★ A LAW GUARDED BY `if CONST is None: return` IS A NO-OP** (34). Verify a term is live by RUNNING
  it and reading its value. `K_NDEF=None`/`MASS_CAP=None` = the size-law is INERT (the working baseline).
- ⛔ **★★★ q/K ARE OUTPUTS.** `Q_MASS=2/E_M` derived from two measured structural exponents (parsed, not
  typed 3/4); WBE `M^(3/4)` is the VALIDATOR. A typed exponent is the output-as-parameter trap (5×).
- ⛔ **★★★ DECOMPOSE A RATIO BEFORE READING ITS SHAPE** (32); a UNIFORM scalar can't make a tier-varying
  shape, a SIZE-DEPENDENT one (S) can (10/33). `sap_frac` is a smoke alarm, not a fit target — decompose.
- ⛔ **★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (30). `plane_bench.py` 5×{s,m,l} ≈ 5 min (now records
  `m_sub`/`S`). Baseline `tmp/iter31_bench.npz`. Solve harness `tmp/iter36_solve_K.py`. Never fit a `-- noise --` line.
- ⛔ **★★ HEART_RATIO IS NOT A KNOB** — fix what FEEDS the bank (leaf-loss rate). `F_H=0` = starvation.
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022, Hellström 2018, WBE/Enquist. LEDGER APPEND-ONLY.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
