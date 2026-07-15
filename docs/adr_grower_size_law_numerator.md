# ADR — The sub-linear N_def numerator (the size-law that has been refuted five times)

**Status:** 🔴 **ADOPTED (Chris, 2026-07-14) → REFUTED at the code iter (iter-36).** Position A was
signed off and coded; it has **no stable fixed point** and explodes. The loop-gain gate in §2 is
CORRECT but INCOMPLETE — it bounds the *mass* loop (`g ≤ q < 1`) and misses a second loop the term
closes: **S → S_IN_SHADE → n_tips → S** (the `n_tips` divisor is a function of S through the shade S
casts, so it does NOT cancel in the dynamics as §2 assumes; gain > 1). See `LEDGER.md` iter-36 and
`STATE.md` board #1. The M^q numerator is *necessary but insufficient*: this loop must be gained < 1
FIRST. This is a canonical design change (it decides the functional form of the term the model has
failed at through iters 15/16/19/20). Position **A** was the recommendation.
**Date:** 2026-07-14 · **Context:** `scripts/plane_grower.py`, iter-35 design session.
Supersedes nothing; it *closes* the open problem `MASS_CAP`/`update_n_def` was left holding at iter-20.

---

## 1. The question

`N_def(t)` — the count of real deferred A4/A5 twigs one armature tip stands for — is the model's
**only** size-dependent term. Everything rides on `S(t) = N_def/N_DEF_REF`: it scales the light a
marker intercepts (`S_IN_LIGHT`), the shade it casts (`S_IN_SHADE`), the pipe its tip seeds
(`r_tip = R0·DBH_CALIB·S^(1/p)`) and the heartwood it wills on death. **With `S ≡ 1` the economy is
scale-free in tips and the tree has no size law** (iter-34: `S`, `N_def`, `r_tip` bit-identical across
s/m/l). The census wants sapwood area ~2× larger at `l` than the model gives (F_S 2.4× low at m/l);
that deficit is the **signature of the absent size-law**, felt through a uniform `R_TIP`.

Every numerator tried has died on **loop gain**:

| iter | numerator | why it died |
|---|---|---|
| 15 | `N_def = TWIG_DENSITY·V_crown/n_tips` | V_crown is the economy's own product → positive feedback, gain > 1 |
| 16 | cantilever `r³/lever`, r from **pipe** | `r ∝ T^(1/p)` ⇒ `r³ ∝ T^(3/p)=T^1.30` → cube runaway |
| 19 | `N_def = MASS_CAP·M_sub/n_tips` | n_tips cancels → `T_total ∝ M` **linear**; whole-crown gain 0.99 |
| 20 | *(diagnosis)* | linear-in-mass is a **transcritical bifurcation at MASS_CAP≈2.205**. |

iter-20's verdict, unchanged: **the numerator must be SUB-LINEAR in mass, `T_total ∝ M^q, q<1`**, and
`q` must be an OUTPUT — WBE's leaf ∝ M^(3/4) is the validator, never the typed input.

**So: what functional form, and with what q?**

---

## 2. What "loop gain" means here, computed once (the gate)

From the code, income is (`_gather_light`, line 1636–1667):

```
I_year = ALPHA · S · Σ_markers light(marker)  =  ALPHA · S · L
```

`S = s_def` is one tree-wide scalar/year; `L` is total light caught by the foliage markers, and
markers ∝ n_tips. Write the numerator as **`N_def = T_total / n_tips`** with `T_total = K · M^q`
(`M` = standing subtended mass, banked from *last* year's structure — exogenous to this year's income,
the property V_crown lacked). Then:

```
S = T_total/(N_DEF_REF·n_tips) = K·M^q/(N_DEF_REF·n_tips)
I = ALPHA·S·L ∝ M^q · (L/n_tips) = M^q · ℓ̄        (ℓ̄ = mean light per marker)
```

**The n_tips cancels** (iter-20's identity, now working *for* us): income depends on `M^q` and on
`ℓ̄`, the per-marker light. Self-shading closes the interior as the crown fills, so `ℓ̄` is
**non-increasing** in size. Therefore the **whole-crown loop gain** — the elasticity of total income
to standing mass, the exact quantity iter-20 said is the only one that matters —

```
g  =  d log I / d log M  =  q + d log ℓ̄/d log M  ≤  q.
```

Mass then accretes as `dM/dt = I − maintenance ∝ M^q − …`. The bifurcation iter-20 hit is **exactly
at q=1**; any `q<1` is on the stable side, and the sensitivity of tier size to the calibration
constant `K` is well-conditioned:

```
d log M* / d log K = 1/(1 − q).
    q = 3/4 → 4      q = 2/3 → 3      q = 1 (iter-19/20) → ∞
```

That `∞` **is** iter-20's measured `d log S/d log MASS_CAP ≈ 80–130` — the numerical face of sitting
on the transcritical point. **A gain of q ≤ 3/4 clears the gate with a margin of 0.25**, and unlike a
tuned constant near a bifurcation it is a fixed geometric exponent, not a knob.

---

## 3. Where q=3/4 comes from — and why it is an OUTPUT, not a parameter

Two mechanisms the model **already owns**, each independently grounded and citable, compose to fix `q`:

- **Area-preserving pipe** (da Vinci / Shinozaki 1964; the ratchet already builds it): a basal
  cross-section serves `T_total = (r_base/r_tip)²` terminal tubes ⇒ `T_total ∝ r_base²`. Exponent **2**.
- **Elastic similarity** (Greenhill 1881 / McMahon & Kronauer 1976): a self-supporting column of radius
  r stands to length `l_max ∝ r^(2/3)`, so standing mass `M ∝ r²·l ∝ r^(8/3)`. Exponent **8/3**.

Eliminating `r_base`:  **`T_total ∝ M^(2 / (8/3)) = M^(3/4)`.** ★

`q = (pipe area exponent) / (mass–radius exponent)` — a **ratio of two measured structural
exponents**, neither of which is the number 3/4. Change the pipe power or the tree's mass–radius law
and q moves with them. This is a *feedback* term (T_total reads the mass income has built), which is
admissible **because its loop gain q<1** — the precise discipline the loop-gain rail demands. It is not
the iter-15 sin (`(n+1)^d` age lookup makes DBH analytic in *age*; this reads earned *mass*, gated by q).

**Validator, from the paper now on disk** (`tmp/papers/wbe_quarterpower_arxiv1507.07820.pdf`, read
2026-07-14): WBE/Enquist compose exactly these two assumptions (area-preserving a=1/2; elastic
similarity `l∝r^(2/3)`) to leaf ∝ M^(3/4) — Enquist 2002, *Tree Physiology* 22:1045, confirms leaf mass
scales as the 3/4 power of plant mass empirically. **⚠ The paper also reports real trees run *steeper
than 2/3* at small scales** (between flow- and elastic-similarity), elastic similarity binding best at
the base of large trees. So the code iter must **measure the model's own mass–radius exponent** and set
`q = 2/e_M` from it, using WBE's 3/4 only as the sanity bracket — not hard-code 8/3.

### Measured corroboration (iter-31 bench × iter-34 read, no new grow)
`M ~ DBH^3.19`, `nfol ~ DBH^2.63` ⇒ the model's own **`e_M ≈ 3.19`**, so `q = 2/3.19 ≈ 0.63` — *more*
sub-linear (safer) than WBE's 0.75, and comfortably < 1. The current (S-inert) model already earns
`nfol ~ M^0.82` and iter-18 measured a component-gain ceiling of 0.866; the linear numerator's 0.99
(iter-20) is the outlier, and it is the outlier **because it bypasses the pipe elasticity** the M^q form
routes through.

---

## 4. The positions

**A — `T_total = K·M_sub^q`, q = 2/e_M derived from the model's measured mass–radius exponent,
WBE-3/4-bracketed, K pinned by S(m-tier)=1.  ★ RECOMMENDED.**
Sub-linear by construction; loop gain ≤ q ≈ 0.63–0.75 < 1 (§2); q emergent (§3); validated against WBE
and Hellström. `M_sub` is last year's banked structure — exogenous. One line in `update_n_def`, one
constant (`K`) fixed by a single anchor, not fitted per tier.

**B — `T_total = (r_stat/r_tip)²`, the area-preserving twig count of the *statics* radius `r_stat`.**
Purest emergence — *no* typed exponent at all; q falls out of the model's own `r_stat ∝ M^(1/3)`
local cantilever as 2/3. **Rejected as the primary:** `r_stat ≪ r_pipe` at the bole (statics never
binds at the trunk — iter-16 measured r_mech/r_pipe = 0.14–0.23), so reading T off `r_stat` *undercounts*
the base and rebuilds a different distortion. Keep as the *validation cross-check* for A: A's fitted K
should reproduce B's basal twig count where statics binds.

**C — drop N_def; make `R_TIP` (or `c_S`) directly size-dependent** (board #2's degeneracy: a
size-graded R_TIP hits census sapwood as well as S does). **Rejected:** it re-introduces a *fitted*
per-tier scalar with no derivation and no loop-gain protection — the exact "uniform-scalar-with-extra-
knobs" the project has refused since iter-10. `S` already drives R_TIP; fix `S`, don't fork it.

**D — code Hellström `b(n)=β(n+1)^d` as the numerator.** **Rejected, permanently:** it makes DBH an
analytic function of age — the OUTPUT-as-parameter mistake made five times. `b(n)` is the **validator**
of the emergent age-trajectory, never the input. (Its m→l prediction `(105/48)^1.44 = 3.09×` is the
post-hoc check on A.)

---

## 5. Decision & the census-target prediction

**Adopt A.** The code iter (iter-36, pending sign-off) will:
1. In `update_n_def`, replace the retired `MASS_CAP·M_sub/n_tips` with `K·M_sub^q/n_tips`, `q = 2/e_M`
   read from a one-off measurement of the model's mass–radius exponent (probe first, then freeze q as a
   derived constant with the measurement in its comment — parsed from truth, not typed).
2. Pin `K` by a single closed-loop root-find on `S(m@47yr)=1` (as iter-20's harness did), then **verify
   the conditioning `d log M/d log K = 1/(1−q) ≈ 3–4`** — the gate. If it comes back ≫ 10, q is too near
   1 and A is wrong; stop, do not tune K.
3. Re-run `plane_bench.py` (5×{s,m,l}) and read F_S / F_H / R_TIP per tier against census.

**Pre-registered prediction (the rails expected to HOLD, and what must MOVE):**
- `T_total ∝ M^0.75`, `n_tips ∝ M^0.56` (measured) ⇒ `S ∝ M^0.19` ⇒ **S rises ~2.5× s→l**, so
  `R_TIP ∝ S^(1/p)` **rises ~1.5× s→l** (board #2 wanted ~1.6×). Sapwood ∝ R_TIP² ⇒ **~2× extra at l**,
  closing the F_S deficit **without growing more tips** (the census-forbidden route: tips only ~1.1×
  off at l).
- **HOLD:** height (1.01/1.03× — rail), foliage count, tip count shape. If any of these MOVES, the term
  is leaking into a side it shouldn't — read §2, `ℓ̄` should be inert.
- Does **not** fix: heartwood 1.77→2.63× over-fill (board #3, feeds from leaf-loss RATE), nor the `s`
  DBH floor (board #4). Those are separate and come after.

**Refuted-if:** the closed-loop conditioning comes back ≫ 10 (A is secretly near q=1), OR S rises but
R_TIP/sapwood do **not** track it (S is entering the wrong side), OR the tier F_S ratios move the wrong
way. A blind `--set K=…` fit against a `-- noise --` bench line does not count as confirmation.
