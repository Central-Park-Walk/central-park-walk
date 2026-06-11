# BRIEF — Weeping Willow (Salix babylonica)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `willow` · **Layer:** canopy (waterside) · **Tier coverage:** s/m (no `_l` — per §1; verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 9 research-grade _Salix_ in bbox (few; iconic waterside specimens at the lake/pond).
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §9; Morton/NCSU.
- [ ] **In-stand video:** none — non-blocking; the weeping curtain is unmistakable and well documented.

## 1. Habit
- **One-liner:** *a broad rounded dome whose long **pendulous branches sweep all the way to the
  ground in a continuous curtain** — the interior is open, the weeping perimeter is the whole read.*
- **Form:** broad rounded dome + **weeping curtain to the ground**. **Aspect:** ~1–1.3 : 1,
  **often wider than tall** (12–18 m spread on 9–15 m). **Fork:** low (`branch_start` 0.18).
  **Branch character:** main limbs arch out, then **long whip-like branchlets hang vertically**
  to the ground. **Asymmetry:** the curtain drapes asymmetrically; interior relatively open.

## 2. Interaction
- **Stand:** willows are **solitary/sparse waterside specimens**, not thickets — each is a
  self-contained weeping dome reflected in water. **Target reading:** a graceful weeping curtain
  beside water, draping to the surface.

## 3. Density
- **Bucket:** dappled curtain (open interior, dense pendulous perimeter screen). **Real:** LAI
  **3.0–5.0**; transmission through the outer curtain ~15–25%.

## 4. Detail
- **Bark:** gray-brown, deeply ridged/furrowed with age. **Leaf:** alternate, **very narrow,
  lanceolate (8–16 cm × 1–2 cm)**, fine; along the full length of the pendulous whips.
  **Summer:** light yellow-green (pale, luminous). **Fall:** yellow-green → yellow, **late**. **Bloom:** catkins (subtle).

## 5. Behavior
- **Wind:** **curtain** — the canonical weeping sway; the hanging whips swing and ripple as a
  drape (the willow wind reference). Tune to the pendulous-curtain biomechanics.
- **Season:** early flush (pale green) → luminous summer curtain → late yellow fall → bare weeping whip-frame winter.

## 6. The one unmistakable thing
The **continuous weeping curtain of long narrow branchlets sweeping to the ground/water.** If the
branches don't hang to the ground, it's not a weeping willow.

## 7. Variation envelope
- **Varies:** dome width, curtain length/density, lean toward water, height, asymmetry.
- **Count:** 5 (low census).
  > **Mesher note:** willow `sub_gravity > 30` crashes Mtree (memory `mtree_pipeline`); willow_l
  > rides the lod2 0.15 keep floor (64.8 k weeping-strand cards). Keep the workarounds; no `_l`.

## 8. Build mapping
- **Params** (`willow` @ ln 796): keep low `branch_start` 0.18 + heavy `sub_gravity` (capped ≤30)
  for the curtain; long pendulous sub-branches. s/m only.
- **Textures:** narrow lanceolate leaf, pale yellow-green; furrowed bark. **Wind:** curtain biomechanics.
- **Placement:** solitary waterside, lean to water. **Perf:** weeping strands are card-heavy — watch overdraw; Gate ×5.

## 9. DoD
- [ ] Thumbnail: weeping dome, curtain to ground. [ ] Curtain wind sway. [ ] Pale summer + late yellow fall.
- [ ] Waterside capture: drape to water surface. [ ] Tier handoff (s/m). [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
