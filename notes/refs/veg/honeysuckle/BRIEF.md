# BRIEF — Japanese Honeysuckle (Lonicera japonica)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_Honeysuckle` — generator `build_honeysuckle()` in
  `scripts/make_vine.py:406` (seed 4500); runtime `vine_builder.gd` (**DISABLED, ln 111**).
- **Layer:** vine (twining; semi-evergreen; invasive, managed)
- **Tier coverage:** n/a (tree-attached; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Invasive, twining and blanketing CP edges/shrubs per [[reference-cp-botany-full]]; iNat
CP-bbox count TO CONFIRM. The paired white→yellow fragrant flowers are the identity in stills.

- [ ] **Habit** — twines over shrubs/fences and blankets; semi-evergreen
- [ ] **Leaf detail** (opposite, oval, untoothed; semi-evergreen)
- [ ] **BLOOM** (paired tubular flowers, white aging to yellow — diagnostic, fragrant)
- [ ] **Semi-evergreen winter** (holds leaves in mild winters) + black berries

## 1. Habit — how it flows over itself
- **One-liner:** a vigorous **twining** vine that scrambles and blankets shrubs, fences
  and the woodland floor in a dense tangle of paired oval leaves, sweetly scented at
  bloom — semi-evergreen, so it lingers green into winter.
- **Climbing mechanism:** **twining** (`make_spiral_wrap`) over low supports + sprawling
  ground/shrub tangle.
- **Asymmetry:** dense irregular tangle.

## 2. Interaction — how it meets its neighbors
- **On a host:** twines over and blankets shrubs, fence lines and low edges into a
  smothering tangle; carpets the ground in shade.
- **Target stand reading:** a shrubby edge buried under a fragrant honeysuckle tangle,
  dotted with paired white-and-yellow flowers in early–mid summer.

## 3. Density
- **Bucket:** dense tangle.
- **Light transmission:** low where it blankets.

## 4. Detail
- **Stem:** thin, twining, hairy when young.
- **Leaf:** **opposite, oval, untoothed (entire)**; medium green; **semi-evergreen**.
- **Summer color:** medium green.
- **Bloom:** **paired tubular two-lipped flowers, opening white and aging to yellow**
  (so white + yellow on the vine at once), very fragrant, **early–mid summer** (`bl`
  ~[1.0,1.6]); then small **black berries**.

## 5. Behavior
- **Wind:** the blanket ripples; tangled tips sway.
- **Seasonal timeline:** leaf-out (spring) → twining blanket growth (summer) → **paired
  white→yellow fragrant flowers (early–mid summer, the identity)** → black berries (late
  summer–fall) → **semi-evergreen: holds green leaves into/through mild winter** (`green`
  partial), browning only in hard cold.

## 6. The one unmistakable thing
**Paired tubular flowers opening white and aging to yellow** (both colors at once),
intensely fragrant, on a semi-evergreen twining blanket.

## 7. Per-instance variation envelope
- **Varies across seeds:** blanket extent, twining vs ground-sprawl, leaf density, flower load.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `build_honeysuckle()` — redesign to a **twining/blanketing tangle**
  (`make_spiral_wrap` + sprawl); opposite oval untoothed leaves; the **paired white/yellow
  tubular flower** is the must-model identity.
- **Textures:** opposite oval entire leaf; paired white-and-yellow tubular flower.
- **`SPECIES`/runtime:** mark **semi-evergreen** (holds leaves into winter).
- **Re-enable:** after GLB passes brief + perf gate.
- **Placement:** invasive — shrubby/fence edges and woodland floor (zones 5/6/8 edges).
- **Perf:** dense blanket overdraw; perf-gate after re-enable.

## 9. Definition of Done
- [ ] Reads as honeysuckle (twining blanket, opposite oval leaves).
- [ ] **Bloom capture** shows paired white→yellow flowers (early–mid summer, the identity).
- [ ] Semi-evergreen — winter capture holds green leaves.
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
