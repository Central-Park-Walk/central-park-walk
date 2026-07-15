# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-37: THE MISSED LOOP IS GATED ON PAPER. Handle chosen: cut the n_tips DIVISOR.

The iter-36 explosion is a **fold** whose closed-loop gain is `β = −d log n_tips/d log S`, living entirely
in the shade→shed→n_tips-divisor channel — **no `q` in it** (that is why the sub-linear numerator couldn't
tame it). Forward arm: `build_shadow` deposits `s ∝ S` ⇒ interior `L = C·exp(−LIGHT_K·S·τ₀)` ⇒ `shed`
(raw light, verified) thins tips. Return arm: `S = K·M^q/(N_DEF_REF·n_tips)`. Stable iff β<1; β rises with
S ⇒ contractive→repelling = the observed discontinuity (K 31.09→362 tips vs 31.14→1 tip, M_sub ~850 kg
throughout). Full derivation + A/B/C decision in **`docs/adr_grower_size_law_numerator.md` §6**.

**Decision (Position B):** drive `S = C·M_sub^q` **directly, with NO live n_tips divisor**. `N_def=S·N_DEF_REF`
becomes primary; `T_total=N_def·n_tips` floats. Cuts the return arm (β's divisor), keeps S in shade AND
income (sampling-consistent), leaves open only the `≤q<1` mass loop iter-36 confirmed tame. Rejected: A
(fixed-density shade — breaks sampling consistency, under-shades big crowns); C (dS/dt cap — a dam on an
OUTPUT). This is board #3's size-dependent-R_TIP handle, arrived at from the gain.

## The board (only a `** RESOLVED **` line is a tell)

1. **★★★ THE S→SHADE→n_tips LOOP — GATED (iter-37).** Gain `G = β`; kill it by cutting the n_tips divisor
   (Position B). ⛔ CODE PENDING (iter-38). The gate is on paper only; the tree still explodes until B ships.
2. **★ SIZE-LAW STILL OFF.** With S≡1 the tree is scale-free in tips; census wants sapwood ~2× larger at
   l (F_S 2.4× low at m/l). B routes the size signal into R_TIP — the M^q numerator gated at last.
3. **★ R_TIP vs F_S degeneracy** — B IS the R_TIP handle (size-dependent R_TIP off M_sub, no n_tips loop).
4. **HEARTWOOD 1.77→2.63×** over-fills with size — leaf-unit LOSS rate, ⛔ NOT `HEART_RATIO`. After #1.
5. **`s` DBH floor** — DBH floored at `2·R_TIP`=10.3 cm at any age (uniform-R_TIP floor). After #1.

## NEXT — iter-38: CODE POSITION B in `update_n_def`, pin C, then bench.

`S = C·M_sub^q` (drop the `/n_tips` divisor; `N_def=S·N_DEF_REF` primary). Pin `C` by a closed-loop
root-find on `S(m@47)=1`, then **check conditioning `d log M/d log C = 1/(1−q) ≈ 3`** — if ≫10, stop
(mass loop secretly near q=1). Then `plane_bench.py` 5×{s,m,l}. Refuted-if (pre-registered, ADR §6.4):
C-conditioning ≫10 · S fails to SETTLE (n_tips no stable carrying capacity ⇒ an unframed loop >1) · S
rises but R_TIP/sapwood don't track. HOLD: M_sub ~10³ kg at m (not 10⁴); height ≈ 1.0×.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ GAIN EVERY LOOP THE TERM CLOSES, NOT THE ONE YOU FRAMED** (36/37). §2 gated the mass loop and
  missed β entirely by asserting "the n_tips cancels" — true in the income IDENTITY, false in the DYNAMICS.
  A var in the DENOMINATOR is a 2nd feedback path if the numerator's var drives it (S drives n_tips via shade).
- ⛔ **★★★ A LAW GUARDED BY `if CONST is None: return` IS A NO-OP** (34). `K_NDEF=None` now = S≡1 baseline
  (verified S≡1.0000, n_tips=17). B replaces this guard with the divisor-free form.
- ⛔ **★★★ q/K ARE OUTPUTS.** `Q_MASS=2/E_M` (parsed, not typed 3/4); WBE `M^(3/4)` is the VALIDATOR.
- ⛔ **★★★ DECOMPOSE A RATIO BEFORE READING ITS SHAPE** (32); `sap_frac` is a smoke alarm, not a fit target.
- ⛔ **★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (30). `plane_bench.py` 5×{s,m,l} ≈ 5 min (records
  `m_sub`/`S`). Baseline `tmp/iter31_bench.npz`. Solve harness `tmp/iter36_solve_K.py`. Never fit a `-- noise --` line.
- ⛔ **★★ HEART_RATIO IS NOT A KNOB** — fix what FEEDS the bank (leaf-loss rate). `F_H=0` = starvation.
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022, Hellström 2018, WBE/Enquist. LEDGER APPEND-ONLY.

## Housekeeping

- ALPHA=1.026e-5 PROVISIONAL (fitted on DBH@m alone). Open agent branches: **ginkgo**, **magnolia** (unmerged).
