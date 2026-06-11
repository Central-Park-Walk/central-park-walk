# BRIEF — Dead tree / snag (bare structure)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).
> **Special archetype:** bare structure only — **no foliage, no impostor by design**
> ([`trees.md`](../../../docs/trees.md) / memory architecture note). Most fields below are
> deliberately n/a; the entire model IS the §"winter bare structure" reference for everything else.

- **Archetype key:** `dead` (standing dead snag) · **Layer:** canopy/sub-canopy (scattered) · **Tier coverage:** near mesh across 0–250 m (no `_lod2`, no impostor) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **Authoritative:** standing-dead-snag ecology (a real, valued woodland feature — habitat).
- [ ] **In-stand video:** the **winter North Woods walk** (being processed) is the ideal
  reference for bare branch architecture and weathered snags — apply its bare-structure read here.

## 1. Habit
- **One-liner:** *a bare, weathered standing skeleton — trunk + main branch architecture with
  broken/lost limbs, no twig-fine ends, no leaves; characterful and gaunt.*
- **Form:** bare branching skeleton; often **broken-topped or limb-shed** (snags lose fine
  structure first). **Branch character:** main limbs only, blunt/broken ends, no leaf cards.
  **Asymmetry:** high — dead trees are irregular, leaning, partial.

## 2. Interaction
- **Stand:** **scattered single snags** standing among living trees — a sparse accent, an
  ecological marker, not a mass. **Target reading:** the occasional gaunt grey skeleton that
  reads as deliberately dead, not as a bug/broken model.

## 3. Density — n/a (no foliage)

## 4. Detail
- **Bark:** **grey, weathered, partly shed** (bare wood showing through); rougher/paler than
  living bark. **Leaf / fall / bloom:** **none** (by design — clean-bare in every season).

## 5. Behavior
- **Wind:** **rigid** — dead wood barely moves; at most a stiff trunk creak, no foliage motion.
- **Season:** **no seasonal change** — bare year-round (the one tree that looks identical winter & summer).

## 6. The one unmistakable thing
A **gaunt grey bare skeleton that reads as intentionally dead** — broken limbs, weathered wood —
so it never looks like a foliage model that failed to load.

## 7. Per-instance variation envelope
- **Varies:** degree of limb loss (broken-top ↔ mostly-intact snag), lean, height, weathering.
- **Count:** small set (low census); variety in brokenness matters more than count.

## 8. Build mapping
- **Generation:** bare structure only — no leaf cards, no `_lod2`, **no impostor bake** (skip
  per design); near mesh across the full range. Confirm the `dead` path in the generator/runtime
  before editing (it is not a standard `SPECIES` dict entry).
- **Textures:** weathered grey bark style. **Placement:** scattered single snags in woodland.
- **Perf:** cheap (no foliage cards). Gate ×5 (should be net-positive).

## 9. DoD
- [ ] Thumbnail: reads as a deliberate bare snag, not a broken/unloaded model.
- [ ] In-stand: occasional grey skeleton among living trees, convincingly dead.
- [ ] **No impostor / no leaf cards** confirmed (by design). [ ] Identical summer & winter. [ ] Gate ×5. [ ] User sign-off.
