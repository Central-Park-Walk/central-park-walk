# BRIEF — Arrowwood Viburnum (Viburnum dentatum)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Shrub_Viburnum` — generator `make_viburnum()` in
  `scripts/make_undergrowth.py:957`; runtime `undergrowth_builder.gd` `SPECIES` **index 2**.
- **Layer:** shrub / sub-canopy (the dense **screening** shrub — contrast witch hazel's openness)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP per [[reference-cp-botany-full]] (woodland edges, Ramble, shrub plantings);
iNat CP-bbox count TO CONFIRM. Stills are adequate for the dense-rounded habit; a walk
video helps only for how a viburnum **screen/thicket** reads as a solid mass.

- [ ] **Habit, summer mass** — iNat CP; CPC / Missouri Bot / NCSU extension
- [ ] **Winter bare structure** (dense fine straight twiggy skeleton)
- [ ] **In a thicket/screen** (crowns merging — the interaction this species carries)
- [ ] **Leaf detail** (opposite, ovate, coarsely dentate, glossy)
- [ ] **Flower cyme + berry detail** (flat white cyme → blue-black drupes)
- [ ] **Fall color** (wine red-purple)

## 1. Habit — how it flows over itself
- **One-liner:** dense, rounded, multi-stemmed shrub of many fine, **straight** upright
  arching stems (the "arrow-shaft" canes) that fill out into a solid twiggy dome — a
  visual **screen**, full to its edge.
- **Overall form:** dense rounded / mounded; **2–3 m.**
- **Aspect (w:h):** ~1.0–1.3 (often wider than tall, suckering outward).
- **First fork height:** low, many stems from the base.
- **Branch character:** numerous **straight, slender** stems (unlike witch hazel's
  zigzag), upright then gently arching at the tips; fine twiggy infill.
- **Asymmetry:** mild — reads as a full rounded mass.

## 2. Interaction — how it meets its neighbors
- **In a stand:** **thicket / screen-forming** — suckers and clumps merge into a
  continuous dense shrub wall. HIGH interaction; this is the species that fills the
  understory edge into a solid green screen.
- **Target stand reading:** a continuous waist-to-head-high dense green mass with no
  air-gaps between individuals — the opposite of witch hazel.

## 3. Density
- **Bucket:** opaque / dense (the densest of the shrub set).
- **Real number:** high leaf density; generator `leaf_density=60` is appropriate — keep dense.
- **Light transmission:** low — it screens.

## 4. Detail
- **Stem/bark:** gray-brown, smooth, slender straight canes.
- **Leaf:** **opposite** (key — most shrubs here are alternate), ovate, **coarsely
  dentate (sharp teeth)**, glossy dark green, prominent straight veins.
- **Summer color:** glossy dark green · **Fall:** wine **red-purple** (`fall=[0.60,0.10,0.15]`).
- **Bloom:** flat-topped **white cymes** late spring (`bl=[0.6,1.2]`), held above foliage;
  then **blue-black berries** (drupes) late summer on red stalks (model as a late-season
  fruit cluster if the season system supports it).

## 5. Behavior
- **Wind:** moderate (`flex=0.30`) — dense crown sways as a mass, leaves flutter.
- **Seasonal:** flush → dense summer screen → white cymes (late spring) → blue-black
  berries (late summer) → wine-red fall → fine twiggy bare skeleton.

## 6. The one unmistakable thing
A dense rounded **screen** of straight twiggy stems with **opposite, sharply toothed
glossy leaves**, topped by flat white flower plates that become blue-black berries.

## 7. Per-instance variation envelope
- **Varies across seeds:** overall size (2–3 m), roundness, stem count, lean; flower/berry presence.
- **Variant count:** 4 — placed densely as a screen, tiling is very visible; set `v=4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_viburnum()` — keep the dense leaf mass but **replace generic stems
  with real straight slender canes + opposite-leaf placement**; proper flat-topped cymes
  (currently 6 small white card clusters — make them read as flat plates).
- **Textures:** opposite ovate dentate glossy leaf; white flat cyme cluster; blue-black berry cluster.
- **`SPECIES` row (idx 2):** `fc` white / `bl` late-spring correct; `fall` wine-red correct;
  `flex=0.30`; **add `v=4`.**
- **Placement:** re-wire into `WOODLAND_SPECIES` + `ZONE_SPECIES[5]`/`[6]` at MEDIUM-HIGH
  density to form screens at woodland edges (~2–3/100 m²).
- **Perf:** dense + high placement = the costliest shrub; perf-gate woodland carefully,
  gain the screen from overlap of full-edged crowns, not extra cards per shrub.

## 9. Definition of Done
- [ ] Thumbnail reads as a dense rounded screen with opposite toothed glossy leaves.
- [ ] **Thicket capture** shows crowns merging into a continuous screen (the interaction).
- [ ] White cymes (late spring) + blue-black berries (late summer) fire at right `season_t`.
- [ ] Dense same-species screen shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
