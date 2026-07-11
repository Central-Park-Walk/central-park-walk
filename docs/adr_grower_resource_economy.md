# ADR — the grower needs a resource economy (crown radius is an OUTPUT, not a parameter)

> **Status: PROPOSAL, awaiting Chris's sign-off.** This is a canonical design change to
> `scripts/plane_grower.py`. No code has been written for it. Raised 2026-07-11 after iter-5
> measurement (`84c3c60`).

## 1. The finding

iter-5 passes at s and m and fails at l. Measured (`tmp/grower_measure.py`, `tmp/grower_diag.py`):

| | iter-4 l | iter-5 l | want |
|---|---|---|---|
| caliber corr(height, base_r) | −0.48 | **−0.10** | negative |
| reiterations | 132 | **465** | — |
| live wood nodes | 129k | 161k | — |
| r_max / H | — | **1.63** | ~0.35 |
| crown width | — | **~76 m** | 12–18 m (spread) |

The l render is a flat slab: limbs level out and run outward to ±15–20 m. The m render is the
best this grower has produced (clear bole, vase fork, ascend-then-arch, a low limb sweeping to
2 m). So iter-5's mechanisms are not wrong in kind — they are unbounded, and 35 years compounds it.

**Reference** (`reference_tree_canopy_data.md` §11): mature London plane crown **spread 12–18 m**
(radius 6–9 m) against height 18–30 m ⇒ spread/H ≈ 0.6–0.75. We are 2–3× too wide.

## 2. Root cause — ONE cause, five symptoms

`grow_module()` does `n = GU_NODES[ax.cat]`. **Every living axis grows a fixed module every year,
forever, regardless of the light reaching its apex.** Extension is gated on nothing.

Therefore limb length — and hence crown radius — is a **de-facto parameter**. `docs/standing_rules.md`
warns that a derived quantity smuggled in as a parameter is this project's recurring failure, that it
has cost us four times, and to expect a fifth. **This is the fifth.**

Everything else follows from it, and the diagnostic numbers confirm the chain:

1. unbounded extension ⇒ plagiotropic limbs reach **36–40 m arc length** (a real plane limb is ~10 m);
2. ⇒ r_max/H = 1.63, a 76 m crown;
3. ⇒ each arch-summit's distal continuation is a **572–1,978-node subtree carrying its own foliage**;
4. ⇒ its Takenaka shed ratio is **0.35–0.52 vs TAU_SHED = 0.18** — 2–3× above the gate — so the
   arch-cascade dieback has fired **exactly zero times** in both tiers (56 registered in l, 0 collected;
   `_arch_distal` grows monotonically);
5. ⇒ the 465 reiterates are pure *additions* with no compensating dieback ⇒ mid-height thick limbs
   accumulate ⇒ caliber correlation collapses to −0.10.

Two things are **not** broken, and must not be "fixed":
- **The shed rule is correct.** Ours *is* Takenaka 1994 (light gathered / internode count < threshold),
  the exact rule Palubicki uses. Our distals are genuinely productive; they should not be shed. They
  should never have grown that large.
- **Sag/posture is not mistuned.** The oldest limbs weep 13–19 m because they are 40 m long. The 94%
  of limbs that never arch (they summit at their own tip) are straight *ascending* rays — a limb that
  extends forever cannot arch, because the arch is a consequence of accumulated load over length.

## 3. The prior art we half-implemented

Palubicki et al. 2009, *Self-organizing tree models for image synthesis* (SIGGRAPH; text at
`tmp/palubicki.txt`, PDF archived). We took its **shadow-propagation grid** (`build_shadow`, cited in
the code) and skipped the half that makes it mean anything: the extended **Borchert–Honda** economy.

- **Basipetal pass:** light Q accumulates from buds to the base. Total resource is **v_base = α·Q_base**
  — proportional to the light the tree actually *captured*.
- **Acropetal pass:** at a branching point the resource splits between main axis and lateral:

  > v_m = v·λQ_m / (λQ_m + (1−λ)Q_l)   and   v_l = v·(1−λ)Q_l / (λQ_m + (1−λ)Q_l)

  λ > 0.5 biases the main axis (excurrent); λ < 0.5 biases laterals (decurrent). Fig. 7 spans the
  entire habit range over **λ ∈ [0.46, 0.54]** — a very sensitive knob.
- **The line that bounds the crown:**

  > "The integer part of the amount v of the resource reaching a bud determines the number of metamers
  > produced by this bud: **n = ⌊v⌋**. The length l of these internodes is calculated as **l = v/n**."

**Why this bounds lateral reach without a cap.** Resource is *finite and shared*. As bud count grows,
per-bud v falls. When v < 1, ⌊v⌋ = 0 and the bud produces **nothing**. Extension stops when the tree's
captured light can no longer pay for it. Crown radius stops being imposed and starts being **earned** —
which is the whole thesis of this grower. Internode *length* becomes an output too (ours is a constant).

The paper also hands us the plane's life story: apical control present when young, removed with age,
*"resulting in a progression from the excurrent form of the young tree to the decurrent form of the old
tree"* — citing Barthélémy & Caraglio, i.e. the same architectural school as C&E. Our staging problem
and their λ/apical-control knob are the same knob.

## 4. Positions

### A — Full extended-BH. Replace `GU_NODES` with `n = ⌊v⌋`, `l = v/n`.
Faithful to the paper; maximal emergence; module size and internode length both become outputs.
**Against:** it discards C&E's *measured, species-specific* growth-unit sizes (A2…A5). Those numbers are
the reason this is a London plane and not a generic self-organizing tree. Adopting A means the species
signature now rests entirely on λ, α and the light field. That is a large bet against our own primary source.

### B — Hybrid: C&E's GU is the **potential**; resource realizes it. *(recommended)*
Keep `GU_NODES[cat]` as the module a **well-supplied** axis of that category makes — which is what C&E
measured, on vigorous axes. Let the resource share scale it down under competition:

```
n_realized = round(GU_NODES[cat] · f(v)),   f(v) = min(1, v / V_SAT)     [FIT: V_SAT]
n_realized == 0  ⇒  the apex is dormant this year; below a floor for k years ⇒ abort
```

A young, uncrowded apex reproduces C&E's measured module **exactly** (f = 1). A starved apex in a
crowded 35-year crown shortens, then stalls, then aborts. Crown radius becomes an output; C&E's measured
architecture is preserved as the ceiling, not thrown away. C&E's A1…A5 ladder is *already* a vigour
ladder, so this is consistent with, not a departure from, our primary source.
Optionally adopt `l = v/n` for internode length (starved shoots make short internodes — real; short
shoots/brachyblasts). Flag [PROV], land it separately.

### C — Priority model (whole-axis) with age-removed apical control.
The paper's alternative: rank an axis's buds by mean light, put the terminal bud first (apical control),
distribute by weights `v_i = v·Q_i·w_i / Σ Q_j·w_j`. Removing apical control with age gives the
excurrent-young → decurrent-old progression directly — exactly the plane, and exactly C&E's staging.
**Not exclusive with B**: B is *how much a bud converts resource into metamers*; C is *how resource is
split among buds*. They compose. Recommend B + C together, with λ / apical-control-removal as the
staging knob rather than a hand-authored curve.

### D — Reject the economy; cap limb length or crown radius allometrically.
Cheapest, lands today, and would make the l metrics pass.
**Rejected.** This is the exact move the standing rule forbids: it imposes the answer we are supposed to
derive, for the fifth time. It also would not fix the arch cascade (the distals would still be productive
and still never collect) — it would only hide the slab. Named here so it is on the record as considered.

## 5. Recommendation

**B + C.** Wire the Borchert–Honda economy; keep C&E's measured GU as the potential that resource
realizes. One mechanism removes all five symptoms: extension is paid for, so limbs stay ~10 m; limbs of
real length arch under real load; distal continuations never become self-feeding 1,400-node subtrees, so
the Takenaka gate collects them; reiterates stop being free additions; caliber recovers.

**No new caps. No new gates. Delete no C&E data.**

## 6. New falsifiable criterion (add to the gate)

Existing criteria (i)–(v) never tested lateral extent, which is why iter-5 shipped a slab that passed s/m.

> **(vi) EMERGENT CROWN RADIUS.** Crown spread must emerge at **12–18 m** for a mature (l) tree, i.e.
> **spread/H ≈ 0.6–0.75**, r_max/H ≈ 0.35 — against `reference_tree_canopy_data.md` §11 and the census.
> Not a clamp: measured, and allowed to fail.

## 7. Risks

- **λ is razor-sharp** (whole habit range in ±0.04). Expect to fit it, and expect the fit to interact
  with our shed threshold. Sweep it; do not eyeball it.
- α, V_SAT, λ are three new fitted scalars. That is a real cost in free parameters — mitigated by
  their deleting the *implicit* parameters currently hidden in unbounded extension, and by (vi) making
  the result falsifiable.
- The s/m tiers currently pass. This change **must not regress them**; they are the control.
- Cost: l is a ~4.5 min run. Fit on s/m, confirm on l. Do not sweep on l.
