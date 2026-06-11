# BRIEF — Maple (Acer — sugar / red / Norway)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `maple` · **Layer:** canopy · **Tier coverage:** s/m/l (verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** **1126** research-grade _Acer_ in bbox — the most-recorded canopy genus (sugar/red/Norway/silver).
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §3; Morton/NCSU.
- [ ] **In-stand video:** maples are present in the North Woods canopy (`250HlDgDVNw`) but not keyed; non-blocking.

## 1. Habit
- **One-liner:** *a dense, symmetrical, rounded-to-oval crown on opposite branching — full,
  tidy, and uniform; one of the heaviest-shade broadleaves.*
- **Form:** rounded/oval, dense, symmetrical. **Aspect:** ~0.6–0.8 : 1 (10–18 m spread on
  20–27 m). **Fork:** moderate (`branch_start` 0.22). **Branch character:** **opposite**
  branching (diagnostic structure), ascending then arching; regular, full. **Asymmetry:** low–moderate.

## 2. Interaction
- **Stand:** dense crowns **close into a heavy ceiling** (opposite large leaves fill gaps
  efficiently). **Target reading:** a solid, deep-shade canopy; brilliant in fall.

## 3. Density
- **Bucket:** opaque (very heavy shade). **Real:** LAI **5.0–7.0**; transmission **~3–8%**
  (CANOPY_OPACITY 1.0). Shade-tolerant — holds foliage in low light.

## 4. Detail
- **Bark:** smooth gray young → furrowed/plated gray-brown mature (`furrowed`). **Leaf:**
  **opposite, palmately 3–5 lobed** (the maple leaf), to ~20 cm. **Summer:** dark green.
  **Fall — a feature:** brilliant — **sugar: orange-red/scarlet; red maple: scarlet; Norway:
  yellow** (Oct). **Bloom:** small early reddish/yellow (subtle).

## 5. Behavior
- **Wind:** moderate — dense crown moves as a mass; broad leaves flip showing paler undersides.
- **Season:** flush (Apr) → dense green summer → **brilliant fall** → bare rounded crown.

## 6. The one unmistakable thing
A **dense symmetrical palmate-leaved dome that blazes orange-red/scarlet in fall.** Distinct
from oak (lobed-but-alternate, tiered) by the opposite branching + rounder, fuller crown.

## 7. Variation envelope
- **Varies:** crown width, height (DBH), lean, density, fall color (scarlet↔yellow across species), timing.
- **Count:** **6–8** (highest-recorded; confirm picker >5).

## 8. Build mapping
- **Params** (`maple` @ ln 483): keep dense rounded crown, `branch_start` 0.22, high
  `leaf_density`; ensure opposite-branch read; widen seeds to 6–8.
- **Textures:** `furrowed` bark; palmate leaf; **brilliant fall recolor** (species spread).
- **Placement:** woodland/row overlap → closed ceiling. **Perf:** opaque + high count → worst-case; fragment-bound. Gate ×5.

## 9. DoD
- [ ] Thumbnail: dense palmate maple dome, distinct from oak. [ ] Brilliant fall.
- [ ] In-stand: closed heavy-shade ceiling. [ ] Tier handoff + crossfade. [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
