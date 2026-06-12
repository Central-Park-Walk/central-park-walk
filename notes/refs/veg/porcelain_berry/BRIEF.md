# BRIEF — Porcelain Berry (Ampelopsis glandulosa / brevipedunculata)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_PorcelainBerry` — generator `build_porcelain_berry()` in
  `scripts/make_vine.py:368` (seed 4300); runtime `vine_builder.gd` (**DISABLED, ln 111**).
- **Layer:** vine (tendril-climbing; invasive blanket, managed)
- **Tier coverage:** n/a (tree-attached; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Aggressive invasive blanketing CP edges, shrubs, fences per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. The multicolored berries are unmistakable in stills.

- [ ] **Habit** — tendril-climbs and **blankets** shrubs/canopy edge (grape-like)
- [ ] **Leaf detail** (grape-like, 3–5 lobed, variable; some heart-shaped)
- [ ] **FALL berries** (porcelain: turquoise/lilac/purple/white speckled — the identity)
- [ ] **In a stand** (a smothering blanket over edge vegetation)

## 1. Habit — how it flows over itself
- **One-liner:** a grape-like tendril vine that **blankets** shrubs and the canopy edge
  in a dense sprawling sheet of lobed leaves — a smothering mantle, climbing by tendrils
  rather than clinging or twining tightly.
- **Climbing mechanism:** **branched tendrils** (grape-type) gripping twigs; sprawls over
  and blankets supporting vegetation (canopy-edge drape — adapt `make_ground_runner` /
  sprawl over a host crown rather than a single trunk).
- **Asymmetry:** irregular blanket following whatever it covers.

## 2. Interaction — how it meets its neighbors
- **On a host:** drapes over and smothers shrubs and small trees at sunny edges, forming
  a continuous leafy blanket — reads as a sheet over the supporting plants.
- **Target stand reading:** a sunny edge buried under a sprawling lobed-leaf mantle,
  studded in fall with the multicolored berries.

## 3. Density
- **Bucket:** dense blanket (overlapping lobed leaves).
- **Light transmission:** low (it smothers what it covers).

## 4. Detail
- **Stem:** thin, climbing by branched tendrils; bark with **white pith** (vs grape's brown — ID detail).
- **Leaf:** **grape-like, 3–5 lobed, highly variable** (some nearly heart-shaped), coarsely toothed; medium green.
- **Summer color:** medium green · **Fall:** yellow-green (foliage not showy).
- **Bloom:** inconspicuous greenish (summer); the showpiece is **fall FRUIT — clusters of
  hard "porcelain" berries in turquoise, lilac, purple, pale blue and white, speckled,
  all colors at once** (the identity; nothing else looks like it).

## 5. Behavior
- **Wind:** the draped blanket ripples; tendril-held sheet sways with the host.
- **Seasonal timeline:** leaf-out (spring) → blanketing green growth (summer) →
  inconspicuous flowers → **the multicolored porcelain berries (fall, the identity)** →
  leaf drop → bare tangled tendril stems (winter, deciduous).

## 6. The one unmistakable thing
**Clusters of speckled porcelain berries in turquoise/lilac/purple/white all at once**,
on a grape-like vine blanketing a sunny edge.

## 7. Per-instance variation envelope
- **Varies across seeds:** blanket extent, leaf lobing (it's highly variable), berry-cluster load.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `build_porcelain_berry()` — redesign to a **sprawling tendril blanket**
  over a host crown/shrub (not a trunk sheet); variable grape-like lobed leaves; the
  **multicolored berry cluster** is the must-model identity (a special multi-hue berry texture).
- **Textures:** variable 3–5-lobed grape-like leaf; multicolored speckled berry cluster.
- **Re-enable:** after GLB passes brief + perf gate.
- **Placement:** invasive — sunny woodland/meadow edges over shrubs (zones 5/6/8 edges).
- **Perf:** dense blanket overdraw at edges; perf-gate after re-enable.

## 9. Definition of Done
- [ ] Reads as porcelain berry (grape-like blanket over a host, tendril-climbing).
- [ ] **Fall capture** shows the multicolored speckled berries (the identity).
- [ ] Edge-blanket capture (interaction — smothering, not a single trunk).
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
