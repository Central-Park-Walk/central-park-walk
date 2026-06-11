# BRIEF — Callery Pear (Pyrus calleryana)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `callery_pear` (~2 k census) · **Layer:** sub-canopy/canopy (small) · **Tier coverage:** s/m/l (verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 22 research-grade _Pyrus calleryana_ in bbox (under-recorded; census ~2 k).
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §8; NCSU/Morton.
- [ ] **In-stand video:** none — non-blocking; very common, well documented.

## 1. Habit
- **One-liner:** *a small, tight, dense tree — narrowly pyramidal-to-oval (Bradford) or
  conical-columnar (Chanticleer) — with steeply ascending branches packed close around a
  central leader; neat and uniform, sometimes congested.*
- **Form:** pyramidal/oval → columnar; dense. **Aspect:** ~0.5–0.7 : 1, often narrow
  (6–10 m spread on 9–15 m). **Fork:** low (`branch_start` 0.18), branches crowd the trunk.
  **Branch character:** steeply ascending, narrow crotch angles (the notoriously weak,
  tight forks). **Asymmetry:** low — uniform/congested is characteristic.
  > **Mesher note:** conical crown crashes Mtree 5.5 → `crown_shape` is "Spherical"
  > (generator comment). Shape the columnar read via gravity/up-attraction, not a conical crown.

## 2. Interaction
- **Stand:** dense narrow crowns **pack into a tight wall** in rows (street-tree look); little
  see-through. **Target reading:** a dense uniform screen of tight oval crowns.

## 3. Density
- **Bucket:** opaque/dense (heavy shade for its size). **Real:** LAI **4.0–6.0**; transmission ~8–15%.

## 4. Detail
- **Bark:** gray-brown, shallow fissures; smooth-ish young. **Leaf:** alternate, simple,
  **glossy, broadly ovate-round, finely scalloped, ~as wide as long**, 4–8 cm; thick/leathery.
  **Summer:** glossy dark green. **Fall:** **late, showy — red / purple / bronze** (holds very
  late, often into Nov–Dec). **Bloom:** **profuse white blossom in early spring before/with
  leaves** (showy, malodorous) — a spring spectacle to capture.

## 5. Behavior
- **Wind:** stiff, dense — small leathery glossy leaves shimmer slightly; tight crown moves little.
- **Season:** **white bloom (early spring)** → glossy green summer → **late red-purple fall** → bare tight oval.

## 6. The one unmistakable thing
The **tight, dense, glossy oval/columnar crown** that flares **white in early spring** and turns
**deep red-purple very late**. If it reads loose or open, it's wrong.

## 7. Variation envelope
- **Varies:** crown width (oval↔columnar), height (DBH), lean, density, bloom/fall timing.
- **Count:** **6–8** (high census; confirm picker >5).

## 8. Build mapping
- **Params** (`callery_pear` @ ln 743): keep low `branch_start` 0.18, steeply ascending tight
  branches, dense `leaf_density`; respect the Spherical-not-Conical mesher workaround.
- **Textures:** glossy ovate leaf; spring-white + late red-purple in the seasonal recolor.
- **Placement:** row overlap → dense screen. **Perf:** opaque small tree; fragment-bound. Gate ×5.

## 9. DoD
- [ ] Thumbnail: tight glossy oval/columnar pear. [ ] Spring white bloom + late red-purple fall.
- [ ] In-row capture: dense screen. [ ] Tier handoff + crossfade. [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
