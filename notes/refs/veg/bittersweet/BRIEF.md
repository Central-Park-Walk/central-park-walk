# BRIEF — Oriental Bittersweet (Celastrus orbiculatus)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_Bittersweet` — generator `build_bittersweet()` in
  `scripts/make_vine.py:348` (seed 4200); runtime `vine_builder.gd` (**DISABLED, ln 111**).
- **Layer:** vine (twining; invasive, strangling, managed)
- **Tier coverage:** n/a (tree-attached; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Aggressive invasive twining CP trees/edges per [[reference-cp-botany-full]]; iNat CP-bbox
count TO CONFIRM. **Walk video helpful** for the twining-and-strangling habit and the
diagnostic autumn fruit.

- [ ] **Habit on a host** — twines/spirals up and around trunks (strangling)
- [ ] **Leaf detail** (round, glossy, finely toothed)
- [ ] **FALL fruit** (yellow capsules splitting to scarlet-orange berries — the identity)
- [ ] **Bare winter** (woody twining stems girdling the host, fruit persisting)

## 1. Habit — how it flows over itself
- **One-liner:** a woody vine that **twines and spirals tightly around the host trunk**,
  girdling and strangling it, then sprawls into the canopy — defined by the helix, not by
  clinging flat.
- **Climbing mechanism:** **twining** (`make_spiral_wrap`) — a helix winding up the trunk.
- **Asymmetry:** spiral around the host; sprawling top.

## 2. Interaction — how it meets its neighbors
- **On a host:** spirals up and constricts the trunk; heavy infestations pull crowns
  down. Reads as girdling the host (its invasive signature).
- **Target stand reading:** a trunk wrapped by a woody spiral, with the canopy edge
  studded by orange-and-red fruit in fall.

## 3. Density
- **Bucket:** open-medium (a winding stem with scattered leaves, not a sheet).
- **Light transmission:** medium.

## 4. Detail
- **Stem:** woody, twining; older stems thick and girdling.
- **Leaf:** **round (orbicular), glossy, finely toothed**; medium green.
- **Summer color:** medium green · **Fall:** clear **yellow**.
- **Bloom:** inconspicuous greenish (early summer); the showy feature is **fall FRUIT —
  yellow-orange capsules that split open to reveal scarlet-orange berries** clustered
  along the stems at leaf axils (the identity; persists into winter, popular in wreaths).

## 5. Behavior
- **Wind:** low on the twined stem; sprawling tips move.
- **Seasonal timeline:** leaf-out (spring) → green twining growth (summer) → **yellow fall
  foliage + the diagnostic yellow-capsule/scarlet-berry fruit clusters** → leaf drop →
  bare woody spiral girdling the trunk with **persistent orange-red fruit through winter**.

## 6. The one unmistakable thing
**Clusters of yellow capsules splitting to scarlet-orange berries** along a stem that
**twines tightly around (and strangles) the trunk**.

## 7. Per-instance variation envelope
- **Varies across seeds:** spiral pitch/extent, sprawl, leaf density, fruit load.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `build_bittersweet()` — redesign to a real **twining helix**
  (`make_spiral_wrap`) up the host + canopy sprawl; round glossy leaf; the **axillary
  yellow-capsule/red-berry fruit cluster** is the must-model feature.
- **Textures:** round glossy toothed leaf (green + yellow fall); yellow-capsule/scarlet-berry fruit.
- **Re-enable:** after GLB passes brief + perf gate; keep `BARK_AFFINITY`.
- **Placement:** invasive — twining on edge/woodland host trees (zones 5/6, edge-boosted),
  as scattered infestations.
- **Perf:** moderate (open winding form); perf-gate after re-enable.

## 9. Definition of Done
- [ ] Reads as bittersweet (tight twining helix on the trunk, NOT a flat sheet).
- [ ] **Fall capture** shows yellow-capsule/scarlet-berry clusters (the identity); persist in winter.
- [ ] On-host capture — spiraling/girdling the trunk (interaction).
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
