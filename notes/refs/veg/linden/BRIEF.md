# BRIEF — Linden / Basswood (Tilia americana / T. cordata)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `linden` (~1.75 k census) · **Layer:** canopy · **Tier coverage:** s/m/l (verify TIER_BOUNDS) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 445 research-grade _Tilia_ in park bbox — abundant formal/street tree.
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §10; NCSU/Morton.
- [ ] **In-stand video:** none yet — non-blocking (dense formal tree, well documented).

## 1. Habit
- **One-liner:** *dense, symmetrical tree — narrowly pyramidal when young, broadening to a
  rounded/oval dome with age — branching low and full, foliage to the silhouette edge.*
- **Form:** pyramidal → broadly rounded/oval, very dense and tidy.
- **Aspect:** ~0.5–0.7 : 1 (9–15 m spread on 18–24 m). **Fork:** moderately low, branches
  full down the trunk (`branch_start` 0.24). **Branch character:** ascending, dense, regular;
  lower branches can droop with age. **Asymmetry:** modest — lindens read orderly.

## 2. Interaction
- **Stand:** dense crowns **close into a solid ceiling**; in rows merge into a continuous
  formal canopy. **Target reading:** an unbroken dense green dome line, heavy shade beneath.

## 3. Density
- **Bucket:** opaque (one of the densest). **Real:** LAI **5.0–7.0**; transmission ~3–8%
  (CANOPY_OPACITY 1.0 already). Large heart-shaped leaves fill gaps efficiently.

## 4. Detail
- **Bark:** smooth gray young → shallow flat-ridged/furrowed gray-brown mature (`furrowed`).
- **Leaf:** alternate, simple, **heart-shaped (cordate), asymmetric base**, doubly serrate,
  13–25 cm; dense along branches. **Summer:** dark green. **Fall:** clear **yellow** (Oct).
  **Bloom:** small fragrant yellow-cream flowers on a leafy bract (early summer; subtle).

## 5. Behavior
- **Wind:** moderate — dense crown moves as a coherent mass, big leaves flip; mid-stiff.
- **Season:** flush (Apr) → dense dark-green summer → clear-yellow fall → bare rounded crown.

## 6. The one unmistakable thing
A **dense, tidy, symmetrical heart-leaved dome** turning uniform yellow — the orderly opaque
crown, distinct from the oak's tiered layers and the elm's vase.

## 7. Variation envelope
- **Varies:** crown width, height (DBH), lower-limb droop, slight asymmetry, density, fall timing.
- **Count:** **6–8** (high census; confirm picker >5).

## 8. Build mapping
- **Params** (`generate_trees_mtree.py` `linden` @ ln 851): keep dense full crown, `branch_start`
  0.24, high `leaf_density`; widen seeds to 6–8.
- **Textures:** `furrowed` bark; cordate leaf. **Placement:** row/formal overlap → ceiling.
- **Perf:** opaque + high count → worst-case; fragment-bound, no card-overdraw inflation. Gate ×5.

## 9. DoD
- [ ] Thumbnail reads as dense heart-leaved linden, distinct from oak/elm.
- [ ] In-stand/row capture: solid closed dome line. [ ] Tier handoff + crossfade.
- [ ] No tiling (6–8 variants). [ ] Yellow fall. [ ] Perf gate ×5. [ ] User sign-off.
