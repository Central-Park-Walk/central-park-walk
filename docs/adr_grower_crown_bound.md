# ADR — What bounds the crown?

**Status:** PROPOSED, awaiting sign-off (canonical design change)
**Date:** 2026-07-11
**Context:** `scripts/plane_grower.py` iter-7. Supersedes nothing; extends
`docs/adr_grower_resource_economy.md` (signed off, still correct — it just doesn't reach this far).

---

## 1. The question

The grower's height now **emerges** (m 14.6 m vs a 14.4 m target; s 9.6 vs 10). Its **crown width
does not**: m spreads ~20 m against a 12–18 m reference, and no amount of tuning has bounded it.

A real London plane reaches **~14 m up but only ~6–9 m out**. Vertical reach is ~2× horizontal. No
single shared reach identity can produce both, so **the asymmetry has to come from a mechanism** —
and the whole question of this ADR is *which one*, because three attempts have now failed on the
same diagnosis.

## 2. What is already refuted (do not re-litigate)

| # | attempt | result |
| --- | --- | --- |
| 1 | **posture** — θ_GSA 40° vs 62°; SAG_K 0.10 vs 0.50 | REFUTED. 25.6 / 27.4 m; sag ≈ nil |
| 2 | **the economy alone** (iter-6) | NO BOUND. Allocation telescopes to light-proportional; a peripheral bud keeps f≈1 forever, so **light rewards runaway** |
| 3 | **D as a length multiplier** (iter-7a) | AMPUTATION. ext < `EXT_MIN` at birth → `DORMANT_ABORT` → spread 5.9 m, half the wood dead |
| 4 | **D on the split, swept 1→6** (iter-7b) | NO BOUND. Spread non-monotone in K and seed-dominated (K=3 → 14.3 / 27.4 / 28.1 m across seeds); kills wood monotonically (−46 % at K=6) |

Attempts 2–4 are **one diagnosis** — *"crown width is bounded by dominance / resource allocation"* —
failing three times. The two-strike rule has fired twice over.

## 3. The root cause of the three failures

**The model we are implementing does not contain a crown-width bound.** Palubicki 2009 §Discussion,
in its own words:

> "In our model, we **ignored changes in branch position and orientation over time**. Such changes,
> due to active reorientation or **passive bending of branches under their weight, play an essential
> role in the development of some tree forms**." — remedy they name: Costes et al. 2008 (biomechanics)

Palubicki has exactly **two** levers on crown extent, and both are spent:
- **the shadow environment** — structurally cannot bound an *open-grown* tree, whose peripheral bud
  is never shaded (= failure 2, restated);
- **tropism / growth direction** (their Fig. 12–13: downward tropism ⇒ wider spread) — this *is*
  posture (= failure 1).

And **C&E contains no lengths at all** (checked end to end: node counts per growth unit and whole-tree
heights, nothing else); its D is **apical control**, which is failures 3 and 4.

⇒ **The bound is outside both papers.** Palubicki names the missing piece. This ADR is about whether
we accept that, and what we put in its place.

---

## 4. The positions

### Position A — **Self-support cost: a limb pays for the wood that holds it out** ★ RECOMMENDED

A vertical axis is a **column in compression** and pays almost nothing to stand up. A horizontal limb
is a **cantilever**: to hold mass *M* at lever arm *L* at constant safe stress, its basal section must
satisfy `d³ ∝ M·L / σ` (Metzger's uniform-stress / constant-safety-factor result; McMahon & Kronauer's
elastic similarity is the same statement). So the **wood a limb must build to exist grows super-linearly
with its reach, while the light it earns grows at best with its new leaf area.**

Today the grower gets that wood **for free**: the pipe-model ratchet computes radius in `finalize()`,
*after* the fact, and the economy only ever buys **internode length**. Make secondary thickening a
**paid cost from the same finite pool** — `v` buys extension *and* the year's thickening increment —
and horizontal reach stops being free.

- **Width becomes an OUTPUT** of what the tree can afford to hold up. No length parameter, no clamp.
- **One mechanism produces the 2:1 asymmetry**, because the cost is a function of the *lever arm*,
  which is exactly what a vertical axis doesn't have.
- **It reuses what already exists**: the sag model already computes load × lever arm per limb, and the
  ratchet already computes the pipe radius. We are charging for a quantity we already compute.
- **Its constants are published, not fitted** — green-wood modulus and allowable bending stress are
  looked up, in the spirit of the resource-economy ADR.
- **Falsifiable, and it is the whole point:** horizontal reach must settle at 6–9 m while vertical reach
  stays ~14 m, from the cost asymmetry alone, on a seed *replicate* — and node count must NOT collapse
  (that would be amputation, i.e. failure 3 wearing a new hat).
- **Risk, stated honestly:** the earnings of a spreading limb also grow with its leaf area, so it is not
  guaranteed *a priori* that cost outruns income and produces a bound rather than merely a slower
  runaway. **This must be measured, not assumed.** It is the first thing to check, and it is cheap.

### Position B — **Mechanical failure: limbs that overreach BREAK**

Not a budget but a **threshold**: compute bending stress at each limb base; when it exceeds a critical
value, the limb is **shed** (storm-pruning / self-pruning is a real and dominant process in open-grown
urban planes, and the census carries its signature — the 3 short-thick outliers already flagged).

- Bounds width by **removal**, not by pauperization; would produce the characteristic broken-back
  veteran form for free.
- **Against:** it is a *discrete* bound on a *continuous* problem — it lets a limb grow to 20 m and then
  deletes it, which reads as damage, not as form. It also does nothing to explain why an *undamaged*
  plane's crown stops at 6–9 m. Real trees do both A and B; **A is the one that shapes the crown, B is
  the one that scars it.** Recommend B *later*, on top of A, not instead of it.

### Position C — **Hydraulic path-length limitation**

Extension scales with water potential, which falls with the path length from root to bud (Ryan & Yoder's
hydraulic-limitation hypothesis; West–Brown–Enquist).

- **Against:** it bounds *total path*, so it penalizes a bud 14 m up the trunk exactly as hard as one
  9 m out along a limb — it produces **no asymmetry**, which is the one thing we actually need. It would
  also bound *height*, which currently emerges correctly and which we would be breaking to fix width.
  And a path-length constant fitted to give 6–9 m is a **reach parameter in a mechanism costume** — the
  fifth OUTPUT-not-parameter, arriving right on schedule. **Reject.**

### Position D — **Bound the crown extrinsically (envelope / mould)**

The deprecated leaf-back envelope tables were deliberately kept "as growth boundaries"
(`scripts/leafback_graph.py`). Grow into a measured crown envelope and let it clip the periphery.

- **For:** it works today, it is cheap, and the envelope is real measured data.
- **Against:** it is precisely the thing this project has re-learned four times not to do. The crown
  shape would become a **parameter we drew**, and every derived quantity downstream of it inherits the
  lie. It also cannot answer *why* the crown stops. **Reject as a mechanism — retain only as a
  validation target** (grow freely, then check the crown against the envelope).

### Position E — **One more variant of the refuted diagnosis** (pauperize `V_SAT` by wave, not D)

Named only to be dispatched: make each successive wave intrinsically poorer by raising its saturation
constant rather than multiplying its length. This is the same diagnosis a fourth time. **The two-strike
rule blocks it.** Not to be attempted unless A *and* B both fail.

---

## 5. Recommendation

**Position A**, with **B** held as a later addition, **D** demoted to a validation target, **C** and
**E** rejected.

**First step is a cheap falsification, not an implementation** (~1 h, no production code): on the
existing iter-7 tree, compute for each limb the self-support wood its lever arm demands, and check
whether that cost **outruns the light income of a spreading limb**. If cost/income rises with reach,
the bound exists and A is worth building. If it doesn't, A is dead on paper and we go to B — and we
will have paid one hour instead of another iteration.

## 6. Consequences

- The economy gains a second sink (thickening). `ALPHA`/`V_SAT` will need refitting; height emergence
  must be **re-verified**, not assumed to survive.
- The grower stops being a pure Palubicki implementation and becomes Palubicki + the biomechanical
  extension its own Discussion asks for. That should be stated in `docs/grower_reiterate_design.md`.
- ⚠ **All width results must be replicated across ≥3 seeds from here on.** The single-seed grid in
  iter-7 looked like control and was noise.
