# STATE — cpw / london-plane

The developmental grower: `scripts/plane_grower.py`. Grow a plane from a seed; let crown, caliber and
depth **emerge**. Deep history: `project_london_plane_crown_mould.md` (not needed — iterate from here).

## Where we are

**iter-15 DONE — hypothesis REFUTED, but it MOVED THE SAPLING and that is the finding.** Hellström et
al. 2018 (the branch-thinning paper, now READ — `tmp/papers/`) gives the missing growth term: a branch
of age n bears `b(n) = min{mu^n, beta*(n+1)^d}` tips — a power law, then thinning. Their red-maple fit
(**beta = 6.69, d = 1.44**) predicts m→l tip growth of **×3.09**, against the census's independently
demanded **×2.71** basal area. Two unrelated sources, same number: the target is now pinned twice.

I made `N_def` size-dependent and put it on **both** sides (light income, shade, tip pipe, heartwood),
realized through space rather than looked up on age: `N_def = TWIG_DENSITY · V_crown / n_tips`.

**★ IT FIXED THE SAPLING: s went 5.15× → 1.15× of its census DBH.** With `N_def` free to be SMALL for
a small tree (13 twigs, not 355), the constant-`R_TIP` floor — **open defect 4**, untouched for six
iterations — simply dissolves. **The size-dependence is RIGHT. Keep it.**

**★★ AND IT REFUTED THE NUMERATOR: `V_crown` IS NOT EXOGENOUS.** `N_def` is read off the live crown →
income scales with `N_def` → income buys the extension that **grows the live crown**. That is a
**positive feedback loop on income, measured from its own product**, and it is unstable in both
directions: the m crown sprawled to 466 m³ (baseline 215), then l collapsed to 358 m³ (62 m³ with the
shade term on). Crown growth came out **×0.77 m→l** where it must be ~×2.7.

    variant                 s DBH   m DBH   l DBH    V_crown s/m/l (m³)   real_tips m→l   sap l
    baseline (iter-14)      5.15x   3.37x   3.36x     19 / 216 / 597           —           4.7%
    S in light + shade      6.83x   4.00x   3.90x    547 / 121 /  62         x0.63         1.0%
    S in light, shade off   1.15x   3.56x   4.02x      5 / 466 / 358         x0.83         3.8%

Model reverted to iter-14 (`TWIG_DENSITY = None`, verified bit-identical). The mechanism, the anchor
probe and the `S_IN_LIGHT`/`S_IN_SHADE` switches all stay in the code — the next iteration re-arms
them with a different numerator.

## Open defects

1. **★★ THE LIVE LEAF-UNIT COUNT SATURATES — still THE defect, and it is still `N_def`.** The economy
   is **scale-free in tips** (income ∝ tips, cost ∝ tips, they cancel ⇒ no growth term anywhere;
   `docs/grower_saturation_diagnosis.md`). iter-15 confirmed the *cure* (a size-dependent `N_def` on
   both sides) and refuted the *source* of the size term. **2–4 are downstream and cannot be read
   until it is fixed.**
   - ⚠ **The S-scaled SHADE is a separate hazard.** The light field is a **linear, clamped-at-zero**
     subtraction, not Beer–Lambert, so a multiplied deposit responds savagely: a small tree (S<1) has
     its shade *relieved* and sprawls; a big one (S>1) blacks out its interior and sheds. Whatever the
     next numerator is, **re-arm `S_IN_SHADE` on its own and look at it**, not bundled.
   - ⚠ **SECONDARY FLAG, now promoted to a lead:** `_bill_total` — the iter-8 self-support bill —
     reads **0.0000 m³ in all 104 years**. It bills only the structural *excess over pipe*, and pipe
     dominates ⇒ **self-support is not biting at all.** See NEXT.
2. **`DBH_CALIB` is stale** (fitted heartwood-free) — the one legitimate re-centring scalar. Refit
   ONCE, and only *after* (1). It cannot fix (1); see the rails.
3. **Caliber splay** — s 5.15 / m 3.37 / l 3.36 (all ~3.4× too thick; that part is (2)'s to fix).
   Re-centred on m: **s 1.53, l 1.00.**
4. **`s` floor** — ~~constant `R_TIP` floors DBH at 2·R_TIP~~ **→ CAUSE CONFIRMED AND CURE FOUND
   (iter-15): a size-dependent `N_def` takes s to 1.15×.** Not a separate defect at all — it is (1)
   seen from the other end. It comes back for free when (1) lands.
5. Criterion vi unmet ⇒ **do not ship.**

## NEXT — iter-16: THE SIZE TERM MUST COME FROM SUPPORT, NOT FROM SPACE

**★ The rule iter-15 bought: a size term the income can BID UP is a feedback loop, not a derivation.**
It must be read from something **earned and settled** — already-built, ratcheted wood — never from a
quantity this year's growth is currently buying. `V_crown` fails that test. The trunk/branch wood does
not: it is monotone (the ratchet), it cannot retract, and it is the *record* of past income, not a
claim on this year's.

**The hypothesis, and Hellström hands it over:** how many twigs a branch can carry is bounded by its
ability to **hold them out** — and their own Eq. 10 prices a growth module by McMahon & Kronauer's
elastic similarity (`r ∝ l^(3/2)`, `M_n ∝ n^3`). Their fitted **d = 1.44 ≈ 3/2** is that exponent. We
already own this mechanism: **the iter-8 self-support bill** — which currently reads **0.0000 m³, i.e.
it never bites**, because it bills only the excess over pipe. So:

> `N_def` = the twigs the wood that carries the tip **can actually hold out** — derived from the
> cantilever capacity already built, not from the space the crown happens to occupy.

That makes the size term exogenous to the light economy (wood is already paid for), gives the dead
support-bill mechanism its job back, and reproduces the paper's own exponent instead of importing it.
⚠ **Read Eq. 10 and the McMahon & Kronauer 1976 basis before coding** — that is the same rule that
made iter-15's diagnosis clean instead of a guess.

**Ground truth to hit:** real tips ×~3 m→l (Hellström b(n), ×3.09; census basal area, ×2.71 — they
agree) ⇒ sapwood ≈ 50% at 104 yr with c_H held at c_S. Then, and only then, refit `DBH_CALIB` once
(defect 2). Expect s ≈ 1.15× to come back with it.

## Rails — each cost a session; do not re-litigate

- ⛔ **★ N_def MUST NOT BE READ FROM THE LIVE CROWN** (`V_crown`, hull or voxels; iter-15). Positive
  feedback on income, measured from its own product. Unstable with AND without the shade term.
- ⛔ **★ No age lookup.** `K(n) = alpha(n+1)^d` as a function of years would make DBH an analytic
  function of age — a parameter in an output's clothes. The paper itself forbids it (p. E45): the
  capacity is "realized through other factors, such as light or nutrient limitation." **b(n) is the
  VALIDATOR, never the input.**
- ⛔ **★ THE HEARTWOOD LAW IS DONE.** Three iterations (12, 13, 14). It is the published law, its
  constant is pinned twice, it is not the defect. ⛔ Do NOT turn `HEART_RATIO` down to buy sapwood.
- ⛔ **★ No scalar can move the SAPWOOD FRACTION — `DBH_CALIB` CANCELS.** It is R_TIP-free: a pure
  STRUCTURAL statement, not a calibration error. **No scalar can FIX a two-sided error** — but a
  scalar is the right tool to **CENTRE** one, *after* a size-dependent term exists.
- ⛔ **LAI cannot rescue p = 2.3** — it would need 2.45 → 6.96 → 12.18; plane's range is 4.0–6.0.
- ⛔ **The tip budget is EXONERATED** (iter-11). So are the **shed rule, `MAX_CAT`, reiteration rate**,
  and **`N_def` accumulating with tip AGE** (REFUTED — per-tip age is a *different* mechanism from
  `N_def` scaling with tree SIZE, which is defect 1 and which iter-15 CONFIRMED is right).
- ⛔ **The crown was never 2× too wide** — five width mechanisms built and refuted against an
  artifact. **Never add a sixth.**
- ⚠ **NEVER cite a paper you have not OPENED.** "Kubo 2022" was fabricated and cost iter-12 AND
  iter-13. Aye 2022 and Hellström 2018 are both read (`tmp/papers/`, gitignored). Aye's equations are
  **GIF images** — a text-only fetch returns the prose with every number silently deleted.
- ⚠ **Instrument limit:** seed spread is 127% (`s` span) / 69–78% (H) ⇒ nothing finer than ~10–15% is
  measurable. **DBH is the tight one (9–19%)** — the only metric worth reading closely.

## Open for Chris — abandoned agent branches hold unmerged work: **ginkgo**, **magnolia**.
