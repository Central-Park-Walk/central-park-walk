# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `LEDGER.md` (append-only) — iterate from here, not from it.

## Where we are — ★★ iter-35: THE SIZE-LAW NUMERATOR IS DERIVED. Loop gain computed, gate PASSED, WBE on disk.

Design/ADR session (no grower change). Closed the open problem iter-20/21 left in `update_n_def`.
**Result → [`docs/adr_grower_size_law_numerator.md`](docs/adr_grower_size_law_numerator.md) (PROPOSED,
awaiting Chris's sign-off).** The form:

> **`N_def = K · M_sub^q / n_tips`**, so **`T_total = N_def·n_tips = K·M_sub^q`**, with
> **`q = 2/e_M`** — the ratio of the area-preserving pipe exponent (2) to the model's *measured*
> mass–radius exponent `e_M`. WBE's leaf ∝ M^(3/4) is the VALIDATOR, not the typed input.

- **Loop gain (the gate, computed on paper before any line):** income `∝ S·L`, n_tips cancels ⇒
  `I ∝ M^q·ℓ̄`, self-shading makes ℓ̄ non-increasing ⇒ **whole-crown gain `g ≤ q`**. Bifurcation is
  **at q=1** (that IS iter-20's 0.99); any q<1 is stable, conditioning `d log M/d log K = 1/(1−q)`.
  Model's measured `e_M≈3.19` ⇒ **q≈0.63**, or WBE-ideal 0.75 — both < 1, margin ≥0.25. ✓
- **WBE discharged:** `tmp/papers/wbe_quarterpower_arxiv1507.07820.pdf` + `.txt` on disk & READ —
  da Vinci area-preserving (r² conserved) ∘ Greenhill/McMahon elastic similarity (`l∝r^(2/3)`) → 3/4.
  ⚠ Paper: real trees run *steeper than 2/3* at small scale ⇒ MEASURE the model's e_M, don't type 8/3.
- **Predicted (pre-registered):** S rises ~2.5× s→l ⇒ R_TIP ~1.5× ⇒ sapwood ~2× extra at l — closes
  F_S **without a tip explosion** (census forbids it). HOLD: height, foliage, tip count.

## The board (n=5; only a `** RESOLVED **` line is a tell)

1. **★★ SIZE-LAW OFF, and now a numerator to turn it back on (ADR-A).** Next session codes it.
2. **★ R_TIP vs F_S degeneracy** — a size-dependent R_TIP (from S>1) hits census sapwood as well as F_S
   does; same retired term (S), two handles. ADR-A drives the R_TIP handle (biology favors it). ADR-C rej.
3. **★ HEARTWOOD 1.77→2.63×** over-fills with size — leaf-unit LOSS rate, ⛔ NOT `HEART_RATIO`. After the size-law.
4. **`s` broken separately** — DBH floored at `2·R_TIP`=10.3 cm at any age (the uniform-R_TIP floor).
- **NOT tells:** crown r_p50 (n~7) · height (1.01/1.03× — rail) · foliage count (90–112%).

## NEXT — iter-36: CODE ADR-A (pending sign-off). One line in `update_n_def`; K by S(m)=1; gate = conditioning.

`N_def = K·M_sub^q/n_tips`. (1) probe the model's mass–radius exponent, freeze `q=2/e_M` as a *derived*
constant (parsed, not typed). (2) root-find K on S(m@47yr)=1 (iter-20's harness). (3) **GATE: verify
`d log M/d log K = 1/(1−q) ≈ 3–4`; if ≫10, q is near 1 — STOP, A is wrong.** (4) bench 5×{s,m,l}, read
F_S/F_H/R_TIP vs census. Refuted-if in ADR §5.

## Rails — each cost a session; do not re-litigate

- ⛔ **★★★ A LAW GUARDED BY `if CONST is None: return` IS A NO-OP** (iter-34). Verify a term is live by
  RUNNING and reading its value. `MASS_CAP=None` made the size-law inert for 14 iters.
- ⛔ **★★★ COMPUTE THE LOOP GAIN BEFORE YOU CODE THE TERM** (20/35). A feedback term (reads what income
  built) is admissible ONLY if gain<1. Linear-in-mass = gain 1 = transcritical bifurcation. Sub-linear q<1.
- ⛔ **★★★ q IS AN OUTPUT.** `M^(3/4)`/`(n+1)^d` are VALIDATORS, never inputs. Derive q from two measured
  structural exponents (ADR §3); a typed exponent is the OUTPUT-as-parameter trap (5× now).
- ⛔ **★★★ DECOMPOSE A RATIO BEFORE READING ITS SHAPE** (32); **A UNIFORM SCALAR CAN'T MAKE A TIER-VARYING
  SHAPE but a SIZE-DEPENDENT one can** (10/33) — `S` is exactly that; iter-33 exonerated the UNIFORM case only.
- ⛔ **★★ AN n=1 INSTRUMENT CANNOT MEASURE A RATIO** (30). `plane_bench.py`: n seeds × tiers, 5×{s,m,l}
  ≈ **20 min**; 1-seed 3-tier ≈ **17 min**. Baseline **`tmp/iter31_bench.npz`** (`--load` free; `--set K=V`
  paired). Never fit against a `-- noise --` line.
- ⛔ **★★ HEART_RATIO IS NOT A KNOB** — fix what FEEDS the bank (leaf-loss rate). `F_H=0` = starvation.
- ⛔ **★★ ECONOMY STRUCTURE EXONERATED** — numerator(22)/denominator(26)/light(25)/STATICS(21)/DROOP(28);
  crown-at-`m` was NOISE(31). Only SCALE refit remains.
- ⚠ **Papers on disk** (`tmp/papers/`): Shinozaki I+II, Aye 2022, Hellström 2018, **WBE/Enquist (iter-35)**.
- ⚠ **LEDGER is APPEND-ONLY;** its entry ships in the same commit as the change.

## Housekeeping

- ALPHA = 1.026e-5 PROVISIONAL — fitted on DBH@m alone (most corrupted by cancellation). Treat as unfitted.
- Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
