# Falsification — does self-support cost outrun a spreading limb's light income?

**Verdict: ✅ IT DOES. Position A survives. Build it.**
**Date:** 2026-07-11 · **Runs the §5 test of** [`adr_grower_crown_bound.md`](adr_grower_crown_bound.md)
**Code:** `tmp/grower_selfsupport_falsify.py` (read-only probe; subclasses `Grower`, **no production
code touched**) · **Figure:** `tmp/selfsupport_falsification.png` · 3 seeds, m tier, 20 yr, ~21 s.

---

## 1. What was asked, and what was measured

The ADR signed off *falsify-first*: before any production code, check on the **existing iter-7 tree**
whether the wood a limb's lever arm demands **outruns the light that limb earns**. Cost/income rises
with reach ⇒ the bound is real ⇒ build A. It doesn't ⇒ A is dead on paper ⇒ go to B.

**Cost** is not assumed — it is solved. Each node must carry its own subtree's static self-weight at a
constant safe stress: `r_req = (4·M / (π·σ))^(1/3)`, with

> `M_i = g · ‖ Σ_j m_j (p_j − p_i)_xz ‖` over the subtree of *i*.

The loads are parallel and vertical, so the moment is a **vector** sum: a symmetric vertical axis
cancels to ≈ 0. **The vertical/horizontal asymmetry is a consequence of the physics, not an assumption
bolted on.** `m_j` itself depends on `r_req`, so it is solved to a **fixed point** (a limb with no fixed
point cannot hold itself up — that would be a hard bound; none was found, see §5).

**Income** is the grower's own light field: the light gathered by the limb's living foliage that year.

Constants are published, not fitted: ρ_green = 900 kg/m³, MOR_green = 45 MPa (American sycamore),
safety factor 4 ⇒ σ = 11.25 MPa; E_green = 7 GPa.

> ★ **The verdict is scale-free in σ and ρ.** They multiply cost by a constant and cannot change
> whether the ratio *rises*. Only the **location** of the bound depends on them. Nothing below is
> hostage to a fitted number.

## 2. T2 — the decisive test: the lever arm is a real, size-independent cost

A far-reaching limb is also a *bigger* limb, so "cost rises with reach" could be nothing but "big limbs
have more wood." Partial exponents settle it — leaf count holds size fixed:

| | leaves | **lever arm** | R² |
| --- | --- | --- | --- |
| log(support wood demanded) | +0.94 | **+1.09** | **0.96** |
| log(light income) | +0.60 | **+0.27** | 0.80 |

**At fixed limb size, cost/income ~ lever^+0.82.** The fit is tight over two decades of lever arm.

Note the honest part: **income does rise with reach** (+0.27) — a spreading limb's leaves *are* better
lit, because they escape the crown's shade. That is failure-2's *"light rewards runaway"*, now
quantified. **It is simply swamped: 1.09 against 0.27.** The reward is real and the cost is four times
bigger.

## 3. T4 — the bound, with no exchange rate and no new constant

The obvious objection to A is that charging wood from a light pool needs a wood↔resource price, and a
fitted price would be *"a reach parameter in a mechanism costume"* — the very thing the ADR rejected
Position C for. It doesn't. Split a limb's annual wood into **thickening** (sections that already
existed) and **extension** (internodes born this year). **Both are m³.** The price cancels.

| limb reach | support tax = thicken/(thicken+extend) | support wood per 1 m³ of new extension |
| --- | --- | --- |
| 0–2 m | 0.48 | 0.9× |
| 2–4 m | 0.73 | 2.7× |
| 4–6 m | 0.88 | 7.3× |
| 6–8 m | 0.91 | 9.8× |
| 8–10 m | 0.94 | 16.7× |
| 10–13 m | **0.96** | **22.5×** |

**A limb at 10 m reach must lay down ~22 m³ of wood merely to keep holding what it already has, for
every 1 m³ it spends reaching further.** Near the trunk that ratio is ~1. Charged from one finite pool,
that is a **~25× swing in the price of a marginal metamer** between a vertical axis and a 10-m limb —
far more authority than the 2:1 reach asymmetry we need. The bound exists, and it is steep.

## 4. ★ T3 — the implementation trap: `DBH_CALIB` would make the mechanism INERT

This is the finding that changes the build, and it would have cost an iteration to discover the hard way.

The mechanical demand, compared against what the tree's radii are today:

| limb reach | mech / **raw pipe** radius | mech / **built** radius (pipe × `DBH_CALIB`) | limbs where mech > built |
| --- | --- | --- | --- |
| 0–2 m | **1.00×** | 0.05× | 0 % |
| 4–6 m | **3.06×** | 0.16× | 0 % |
| 8–10 m | **4.51×** | 0.24× | 0 % |

Against the **raw pipe model**, mechanics binds exactly as A predicts: it adds nothing at the trunk and
**4.5× at the periphery** — a surcharge *shaped by the lever arm*.

But the grower does not build the raw pipe radius. `finalize()` multiplies **every** radius by the
`[FIT]` scalar `DBH_CALIB = 4.37`. That is a **uniform** fudge, and it is uniformly *larger* than the
mechanical demand. So a naive `r = max(r_pipe, r_mech)` **never binds — in 0 % of limbs, at every
reach.** Position A would be implemented, would look correct, and would do **nothing**.

⇒ **Requirement on the build: the mechanical term must sit in front of `DBH_CALIB`, not behind it.**
The construction is `r = max(r_pipe_raw, r_mech)`.

And then a win falls out: `DBH_CALIB` exists because the raw pipe radius came out too thin against the
census. **Mechanics supplies precisely the missing wood, in the right shape** (×1 at the bole, ×4.5 in
the crown) where `DBH_CALIB` fattens everything equally. A can **retire a fitted constant in the crown**
— the fifth OUTPUT-not-parameter, caught early for once, exactly where `CLAUDE.md` says to look for it.

**But not at the bole, and this is the honest limit.** Measured trunk radii:

| | mech | raw pipe | built today | census median |
| --- | --- | --- | --- | --- |
| trunk radius | 28–45 mm | 15–21 mm | 66–92 mm | **190 mm** |

Static self-weight bending **cannot** derive trunk DBH — and it *shouldn't*: a roughly symmetric crown
exerts a near-zero **net** moment at the bole. Real trunk girth is set by wind loading, hydraulics, and
the deferred A4/A5 foliage mass that `DBH_CALIB` was standing in for. **`DBH_CALIB` (or a successor)
survives for the bole; it must stop masking the crown.**

## 5. What the falsification does *not* show

- **The fixed point never diverged**, and Greenhill buckling leaves the trunk at 2.7× safety. So the
  bound is **economic, not structural**: mechanics does not *forbid* a 20 m crown, it makes it ~25×
  more expensive per metamer. That is what A needs, and all it needs — but it means the crown will
  settle where the **price** puts it, and the price is set by σ and the pool, so **width emergence must
  be re-measured after the build, not assumed.**
- **Static self-weight only** — no wind. Sufficient here; wind would only strengthen the asymmetry.
- **T1's gross scaling is noisy** (cost ~ L^2.07, income ~ L^0.70, R² ≈ 0.2) precisely because of the
  size confound. **T2 is the load-bearing result** (R² 0.96), not T1. Quoting T1 alone would be sloppy.
- It does **not** show that the built grower lands at 6–9 m. That is the build, and the ADR's
  falsifiable claim: horizontal reach settles at 6–9 m while height holds ~14 m, on **≥ 3 seed
  replicates**, with **no collapse in node count** (that would be amputation — failure 3 in a new hat).

## 6. Consequences for the build (Position A)

1. `r = max(r_pipe_raw, r_mech)` — **mechanical term ahead of `DBH_CALIB`**, else inert (§4).
2. The economy's `v` buys **wood volume**, not internode length. Thickening and extension are then
   priced in the same currency and no exchange-rate constant is invented (§3).
3. Re-verify **height emergence** — the economy gains a second sink; `ALPHA`/`V_SAT` will need refitting
   and height must not be assumed to survive it (ADR §6).
4. Keep `DBH_CALIB` for the bole; scope it so it no longer multiplies crown radii (§4).
5. **≥ 3 seeds for every width number, from here on.** (Seed spread this run: crown width 19.6 / 22.6 /
   16.1 m — the single-seed grid in iter-7 was noise.)

## 7. Seeds

| seed | wood nodes | H | crown width | limbs |
| --- | --- | --- | --- | --- |
| 20260710 | 1614 | 12.8 m | 19.6 m | 19 |
| 20260711 | 1128 | 13.0 m | 22.6 m | 15 |
| 20260712 | 783 | 14.4 m | 16.1 m | 14 |

Reference: ~14 m tall, 12–18 m crown (Broad Dome bucket). Width is the defect A is meant to fix.
