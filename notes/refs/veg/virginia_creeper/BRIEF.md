# BRIEF — Virginia Creeper (Parthenocissus quinquefolia)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_VirginiaCreeper` — generator `build_virginia_creeper()` in
  `scripts/make_vine.py:305` (seed 4000); runtime `vine_builder.gd` (**currently DISABLED,
  ln 111** — all vines are stick-card primitives awaiting this redesign + re-enable).
- **Layer:** vine (climbs tree trunks + sprawls; native, the "good" vine of the set)
- **Tier coverage:** n/a (tree-attached; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Native, abundant on CP woodland tree trunks and edges per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. **Walk video helpful** for how it clings flat to bark vs
drapes — and for the autumn crimson, which is its whole identity.

- [ ] **Habit on a host** — iNat CP; how it climbs (cling-disk pads flat to bark)
- [ ] **Leaf detail** (palmately compound, **5 leaflets** — the ID vs poison ivy's 3)
- [ ] **FALL color** (crimson-scarlet — the diagnostic season) + berries (blue-black on red stalks)
- [ ] **In a stand** (sheeting a trunk; draping a canopy edge)

## 1. Habit — how it flows over itself
- **One-liner:** clings **flat against bark** by adhesive tendril disks, sheeting up a
  trunk as a layer of palmate leaves, then drapes and festoons off branch ends — a leafy
  skin on the host, not a free-standing form.
- **Climbing mechanism:** **adhesive tendril pads** (`make_climbing_pad`) — a leaf sheet
  conforming to the trunk surface; plus draping runners off the canopy edge.
- **Asymmetry:** follows the host; irregular drapes.

## 2. Interaction — how it meets its neighbors
- **On a host:** sheets the lower-mid trunk and lower branches; in the open it carpets
  the ground and low shrubs. Reads as part of the tree, not a separate plant.
- **Target stand reading:** a trunk wearing a flat skin of 5-leaflet leaves that flares
  into crimson drapes in fall.

## 3. Density
- **Bucket:** medium sheet (a layer of leaves over bark, gaps showing bark).
- **Light transmission:** low where it sheets, but it's a thin layer.

## 4. Detail
- **Stem:** thin woody runner pressed to bark, with branched tendrils ending in **adhesive disks**.
- **Leaf:** **palmately compound, 5 leaflets** (toothed, pointed) — the signature; medium green.
- **Summer color:** medium-dark green.
- **Bloom:** inconspicuous greenish (early summer); the showy fruit is **blue-black
  berries on bright red/pink stalks** in fall.

## 5. Behavior
- **Wind:** low on the clinging sheet; draping runners flutter.
- **Seasonal timeline:** leaf-out (spring) → green sheet (summer) → inconspicuous flowers
  (early summer) → **brilliant crimson-scarlet fall (the identity — one of the first and
  best fall colors in the park) + blue-black berries on red stalks** → leaf drop →
  bare woody runners + tendril disks visible on bark (winter, deciduous).

## 6. The one unmistakable thing
A trunk sheeted in **5-leaflet palmate leaves that turn brilliant crimson** in early
fall, clinging flat by adhesive disks (not twining).

## 7. Per-instance variation envelope
- **Varies across seeds:** sheet extent up the trunk, drape length, leaf density, host size.
- **Variant count:** 3 — set `v=3` (placed across many host trunks; tiling visible).

## 8. What this brief drives (build mapping)
- **Generator:** `build_virginia_creeper()` — redesign the geometry from a stick-card to
  a **bark-conforming leaf sheet** (`make_climbing_pad` lifted to a real clinging sheet)
  + draping runners; 5-leaflet palmate leaf cards.
- **Textures:** 5-leaflet palmate leaf (green + a crimson fall variant); berry cluster.
- **Re-enable:** delete the `vine_builder.gd:111` early return only after the GLB passes
  its brief + perf gate; keep `BARK_AFFINITY` / forest-edge boost.
- **Placement:** native — woodland tree trunks + edges (zones 5/6, edge-boosted).
- **Perf:** sheeting adds overdraw on every hosted trunk — perf-gate woodland after re-enable.

## 9. Definition of Done
- [ ] Reads as Virginia creeper (flat-clinging 5-leaflet sheet, NOT twining).
- [ ] **Fall capture** shows the crimson (the identity).
- [ ] On-host capture — sheets a trunk + drapes a canopy edge (interaction).
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
