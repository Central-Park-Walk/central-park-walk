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

**★ iter-37 (2026-07-14) — the missed loop is now GATED on paper; the handle is chosen. See §6.**
The destabiliser is the **n_tips divisor** (the return arm of a fold with gain β>1). Decision: **cut
the return arm — drive S off M_sub directly, no live n_tips divisor (§6 Position B)**. A/C rejected.

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

---

## 6. iter-37 — the SECOND loop §2 missed, gated, and the handle chosen

§2 gated the **mass** channel (income → `M_sub`, gain `g ≤ q < 1`) and asserted *"the n_tips cancels."*
That cancellation is real in the income **identity** (`I ∝ M^q·ℓ̄`) but false in the **dynamics**, because
`n_tips` is itself a function of `S` through the shade `S` casts. That is a *second* loop, and its gain
contains no `q` at all.

### 6.1 The loop, from the code

- **`update_n_def` (2037–2043):** `S = K·M_sub^q / (N_DEF_REF · n_tips)`, then `r_tip = R0·DBH_CALIB·S^(1/p)`.
  `n_tips` is **in the denominator** — the *return* arm.
- **`build_shadow` (1576):** each marker deposits `s = S · SHADOW_A · SHADOW_B^(−dl)`. So the optical depth
  over any interior site is `τ(site) = S · τ₀(site)`, `τ₀` the S-independent *geometric* depth (how many
  markers, how deep, sit above the site). — the *forward* arm.
- **`light_at` (1606):** intercepted light `L = C·exp(−LIGHT_K·τ) = C·exp(−LIGHT_K·S·τ₀)`.
- **`shed` (2145 → 1874):** fed by `foliage_light` = **raw** `light_at` (verified: the `S_IN_LIGHT` gain at
  1694 is on the *allocation* income `q_own` only, **never** on the shed light). An axis sheds when
  `lg/size < TAU_SHED`. So `S↑` dims every interior site and pushes the marginally-lit tips over the edge.

Define the **shed elasticity** `β ≡ −d log n_tips / d log S ≥ 0` (how hard a fractional rise in `S` thins
the crown; `β` = (density of tips packed against `TAU_SHED`) × the interior dimming `LIGHT_K·τ₀` per unit
`log S`). Perturb `S → S·(1+ε)`:

```
forward:  Δlog n_tips = −β·ε
return :  Δlog S′ = −Δlog n_tips = +β·ε        (the divisor, d log S/d log n_tips = −1)
⇒  CLOSED-LOOP GAIN  G = β.
```

**Stable iff β < 1**: a 1 % rise in `S` must shed **< 1 %** of the tips. It **diverges when β > 1**: a 1 %
rise sheds > 1 % of tips → raises `S` > 1 % → sheds more → runaway to `n_tips → 1`. `q` is nowhere in `G`.

### 6.2 This retrodicts iter-36 exactly (the gate's null control)

`β` is not constant: it grows with the interior depth, and `τ ∝ S`, so `β` climbs as `S` climbs. The map
`S ↦ S′` is therefore **contractive (β<1) at low S with a stable root, then repelling (β>1) above a
critical S — a fold / saddle-node**, not iter-20's transcritical. That IS the observed discontinuity:
`K 31.09 → S 0.499, n_tips 362` (β<1 branch) vs `K 31.14 → S 94, n_tips 1` (β>1 branch, collapsed to the
single-tip absorbing state where the divisor has nothing left to divide). **`M_sub` stayed ~850 kg
throughout** — the loop never touches mass, so §2's mass gate *held*; the divergence is entirely `β`.
iter-20's linear (q=1) form showed the identical `n_tips` collapse `100→65→12→7`, confirming `β` is
orthogonal to the mass exponent. The gain model reproduces the existing data with no free parameter.

### 6.3 Positions — you need cut only ONE arm of `G = β`

**A — cut the FORWARD arm: cast shade at a fixed reference density** (drop `self.s_def` from
`build_shadow`/`light_at`; a marker casts one reference-twig's shade at any `S`). Then `τ` is
S-independent and `β = 0`.
**Rejected — it breaks sampling consistency.** A marker *represents* `N_def = S·N_DEF_REF` real twigs for
income (`S_IN_LIGHT`) and for its pipe (`r_tip ∝ S^(1/p)`), so it must also **cast** that many twigs'
shade — the iter-15 "same term, both sides" rail. Shade-at-unit-density leaves a large crown optically far
too sparse for its real leaf area: the interior under-shades, tips that should die in a closed canopy
survive, and the crown stops closing at size — resurrecting board #2 (scale-free-in-tips) at large `S`.

**B — cut the RETURN arm: drive `N_def` (hence `r_tip`, `S`) off `M_sub` directly, with NO live n_tips
divisor.  ★ RECOMMENDED.** `S = C·M_sub^q` (`C` pinned by `S(m@47)=1`); `N_def = S·N_DEF_REF` becomes the
**primary**, and the crown total `T_total = N_def·n_tips` is the *derivative* that floats with the crown.
`r_tip = R0·DBH_CALIB·S^(1/p)` unchanged; `S` stays in **both** income and shade (sampling consistency
preserved — the wanted crown closure still fires). Now `d log S/d log n_tips = 0`: losing interior tips no
longer bids `S` up. The forward arm still closes the interior but **settles** instead of running away, and
total real twigs `= N_def·n_tips` genuinely falls when the crown sheds a limb — physically correct, where
the divisor's "surviving tips each inherit the dead one's twigs" was the unphysical redistribution
(LEDGER iter-20). This is board #3's biologically-favoured **size-dependent R_TIP off standing mass**.
*Gain of every loop it leaves open* (LEDGER iter-36 rail — gain them ALL, not the one you framed): the
only remaining `S`-loop is the **mass** channel `S ∝ M^q → income → ΔM_sub → S`, gain `≤ q < 1` — exactly
§2's gate, which iter-36 **confirmed held** (`M_sub` never ran away). No new loop > 1.

**C — cap `dS/dt` per year.** Leaves `β > 1` intact and merely slows the climb to the same fold. A dam on
a derived OUTPUT — the "simulate the process, let the appearance emerge" violation and a cheap hack
(CLAUDE.md §0.1 / §2). **Rejected on principle, before any measurement.**

### 6.4 Decision: **B.** — the n_tips divisor is deleted; `S` is a pure function of banked `M_sub`.

The size signal moves fully into `r_tip` (board #3's handle), the divisor's redistribution instability is
gone at the root, and `S`-in-shade is *kept* (consistent optics). This is a canonical form change to
`update_n_def`; it is **iter-38's** code unit (no numerator is coded in iter-37).

**Pre-registered for iter-38 (refuted-if):**
1. **Conditioning of the C-pin** `d log M/d log C = 1/(1−q) ≈ 3` comes back ≫ 10 → the mass loop is
   secretly near `q=1` after all; stop, do not tune C.
2. **`S` fails to settle** — with the divisor gone, `n_tips` must reach a *stable* carrying capacity within
   the grow. If it doesn't, a loop we didn't frame is > 1 (gain every arm again).
3. **`S` rises with size but sapwood / R_TIP do not track** → `S` entering the wrong side.
- **HOLD:** `M_sub` bounded (~10³ kg at m, not 10⁴ — the mass channel stays tame); height rail ≈ 1.0×.
