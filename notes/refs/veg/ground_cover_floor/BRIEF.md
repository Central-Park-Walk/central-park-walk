# BRIEF — Woodland Ground-Cover Floor (litter / moss / twigs / seedlings)

> Shared brief for the floor-ephemera layer (NOT a single species). The falsifiable target
> the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §8.

- **Archetype keys:** `GroundCover_DeadLeaves_01/02`, `GroundCover_ForestLeaves_01/02`,
  `GroundCover_Moss_01/02`, `GroundCover_Branch_01/02`, `GroundCover_Seedling_01/02` —
  runtime `ground_cover_builder.gd` `COVER_MODELS` (chunk-MultiMesh; `seasonal` flag 0
  year-round / 1 seedling / 2 autumn litter). Generator: `scripts/make_ground_cover.py`
  (currently turf tiles only — the `GroundCover_*.glb` set's origin must be verified, §8).
- **Layer:** floor (connective tissue / ephemera — thickens woodland coherence, does not supply it)
- **Tier coverage:** n/a (chunk-MultiMesh; close-range floor detail, culled at distance)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
The real CP woodland floor (Ramble, North Woods, Hallett) is the reference: an oak/maple
leaf-litter mat over Manhattan-schist soil, moss on rocks and shaded north faces, fallen
twigs/branches, and scattered tree seedlings. iNat/field note TO CONFIRM the dominant
litter species (oak + maple). The cached North Woods walk videos
([[project-tree-model-redesign-plan]]) show the floor in leaf-out and winter-snow states.

- [ ] **Leaf-litter mat** (autumn fallen leaves vs decomposed year-round duff)
- [ ] **Moss** (patches on rock/soil/north faces; year-round green)
- [ ] **Fallen twigs/branches** (woody floor debris)
- [ ] **Tree seedlings** (deciduous + conifer first-year sprouts)
- [ ] **Seasonal floor states** (fresh autumn litter → matted winter → spring sprout → summer duff)

## 1. Habit — how it flows over itself
- **One-liner:** a low, broken, naturalistic carpet of leaf litter, moss patches, twigs,
  and seedlings scattered over the woodland floor — irregular and patchy, never a uniform
  texture tile.
- **Form:** flat-to-ground scatter; the realism is in **patchiness and seasonal change**,
  not in any one model's shape.

## 2. Interaction — how it meets its neighbors
- **In a stand:** fills the gaps between and beneath the shrubs (spicebush thickets),
  ferns, and forbs — the floor of the same North Woods / Ramble validation stands. It
  **thickens** woodland coherence (method §4) but, per the user, does **not** supply it;
  the canopy and shrub/herb layers carry coherence.
- **Target stand reading:** a believable shaded forest floor — litter mat with moss
  patches, twigs, and the odd seedling — under and around the taller undergrowth.

## 3. Density
- **Bucket:** patchy floor scatter; concentrate under the canopy buffer (litter is deep
  under trees, absent on open lawn).
- **Light transmission:** n/a (floor layer).

## 4. Detail
- **Litter:** oak/maple leaf shapes; fresh autumn litter is warm brown/tan, year-round
  duff is darker/decomposed.
- **Moss:** soft green cushions on rock/soil/north faces; year-round.
- **Twigs/branches:** gray-brown woody debris.
- **Seedlings:** small deciduous (2–4 leaves) and conifer first-year sprouts.

## 5. Behavior
- **Wind:** none (floor litter); seedlings flutter faintly.
- **Seasonal timeline (the point of this layer):**
  - **Spring:** old matted litter thinning; **seedlings sprout**; moss bright green.
  - **Summer:** decomposed duff baseline; moss green; seedlings leafed.
  - **Autumn:** **fresh fallen leaves arrive** (`seasonal=2` litter appears with/after
    canopy leaf-drop — must NOT be present in spring/summer); warm tan/brown.
  - **Winter:** matted/snow-flattened litter; moss persists green; bare twigs.

## 6. The one unmistakable thing
A **seasonally-correct** woodland floor: fresh leaf litter that appears at autumn
leaf-drop (not year-round), year-round moss and duff, scattered twigs and seedlings —
patchy and concentrated under the canopy, not a flat repeating tile.

## 7. Per-instance variation envelope
- **Varies:** litter/moss/twig/seedling mix per chunk, rotation, density by canopy depth.
- **Variant count:** the existing ×2 per model gives variety; rely on mix + rotation +
  density jitter to avoid tiling.

## 8. What this brief drives (build mapping)
- **PROVENANCE AUDIT (blocking for v1.0):** confirm each `GroundCover_*.glb` is an
  original/distributable asset, not an unattributed gscatter/photogrammetry import
  ([[reference-vegetation-inventory]], [[feedback-distributable-assets]]). If any are
  imports, regenerate as originals (extend `make_ground_cover.py` beyond turf tiles).
  **Record the finding either way** — this is the first task here.
- **Seasonal wiring:** verify `COVER_MODELS` `seasonal` flags fire correctly vs `season_t`
  (dead leaves only at/after leaf-drop, clearing by late spring; moss/duff year-round;
  seedlings spring/summer); confirm litter concentrates under the canopy buffer, not on lawn.
- **Builder:** `ground_cover_builder.gd` (chunk-MultiMesh) — keep; tune density-by-canopy.
- **Perf:** floor scatter is cheap but high-count; perf-gate woodland after any density change.

## 9. Definition of Done
- [ ] Provenance of every `GroundCover_*.glb` confirmed (original or replaced) and recorded.
- [ ] **Seasonal sweep:** fresh litter appears only in autumn/winter, clears in spring;
      moss/duff year-round; seedlings in spring/summer.
- [ ] Woodland-floor capture reads as a believable patchy forest floor under the undergrowth.
- [ ] Litter concentrated under canopy, absent on open lawn.
- [ ] Perf gate ×5 equal-or-better.
- [ ] User walk-around sign-off.
