# BRIEF — Austrian Pine / conifer (Pinus nigra)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).
> Renders the census **`conifer`** archetype too. **Old "bare sticks" species — needs
> needle-mass work** (§6); escalate to Opus if it fights the broadleaf template.

- **Archetype key:** `pine` · **Layer:** canopy (evergreen) · **Tier coverage:** m/l (no `_s` — verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 246 research-grade _Pinus_ in bbox.
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §4; Morton/NCSU.
- [ ] **In-stand video:** none specific — non-blocking; evergreen mass is well documented.

## 1. Habit
- **One-liner:** *pyramidal and dense when young, maturing to a **broad, flat-topped, irregular,
  picturesque** crown — heavy dark needle masses held in tufted shelves on stout spreading limbs.*
- **Form:** pyramidal → broad flat-topped/irregular. **Aspect:** ~0.5–0.7 : 1 (7.5–10.5 m
  spread on 12–18 m). **Fork:** mid (`branch_start` 0.22); stout horizontal-to-ascending limbs.
  **Branch character:** stout, spreading; needles in an **outer shell 1–2 m deep**, tufted at
  branch ends. **Asymmetry:** high with age (the characterful old-pine irregularity).

## 2. Interaction
- **Stand:** dark dense evergreen masses **anchor the scene year-round**; overlap into heavy
  shadowed groups. **Target reading:** solid dark-green needle mass — NOT bare sticks with
  needle tufts only at the tips (the defect to fix).

## 3. Density
- **Bucket:** dense (dark). **Real:** needle LAI **1.0–2.5** projected (×~2.8 total surface);
  transmission **~10–20%** (dark for a 2-needle pine; 4–7 yr needle retention stacks mass).

## 4. Detail
- **Bark:** dark gray-brown, **scaly plated, deeply furrowed** (pine bark style). **Needles:**
  **fascicles of 2, stiff, dark green, 8–15 cm**, spirally arranged, persisting 4–7 yr.
  **Color:** dark green year-round (evergreen). **No fall/drop** — constant mass. **Cones:** ovoid, optional detail.

## 5. Behavior
- **Wind:** **stiff** — whole branches sway slowly; needle tufts hiss/shimmer but hold. Low amplitude.
- **Season:** **evergreen — minimal seasonal change**; dark mass in winter when broadleaves are bare (a key winter anchor — model the winter presence well).

## 6. The one unmistakable thing
A **dark, dense, evergreen needle mass on a broad irregular crown** — present and heavy in
winter. If it reads as bare branches with sparse tip-tufts, it has the documented defect.

## 7. Variation envelope
- **Varies:** crown shape (pyramidal↔flat-topped), irregularity, height, lean, needle-mass density.
- **Count:** 5 (moderate census).

## 8. Build mapping
- **Params** (`pine` @ ln 535): the priority is **needle mass** — fill the outer shell (more/
  deeper needle cards along branches), not tip-only tufts; keep stout spreading limbs.
  `branch_start` 0.22.
- **Textures:** 2-needle fascicle/branchlet texture; pine bark style; dark-green constant color.
- **Placement:** evergreen anchors; overlap into dark groups. **Perf:** dense needle cards — watch
  overdraw (fragment-bound); gain mass from texture, not raw card count. Gate ×5.

## 9. DoD
- [ ] Thumbnail: dense dark needle mass, NOT bare sticks. [ ] Winter capture: heavy evergreen presence.
- [ ] In-stand: dark anchor masses. [ ] Tier handoff + crossfade (no impostor blob). [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
