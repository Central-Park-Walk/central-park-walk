# BRIEF — Generic Deciduous (census fallback)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).
> **This is the catch-all** for census genera not mapped to a specific archetype
> (`convert_to_godot.py` `SPECIES_MAP`). Goal (§6): a **believable average broadleaf** — never
> the star, never obviously wrong; it must blend into any mixed stand.

- **Archetype key:** `deciduous` · **Layer:** canopy · **Tier coverage:** s/m/l (verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **Authoritative:** synthesized average of the mapped broadleaves
  ([[reference-tree-canopy-data]] genus summary table). Not a single species → no iNat query.
- [x] **In-stand video:** the defect tree from the sparsity report (`deciduous` at −591.7, 1465.6)
  is by Literary Walk (`bCQ0TCUSuBA` context) — keep it reading as a plausible neighbor there.

## 1. Habit
- **One-liner:** *a plausible average broadleaf — a rounded, moderately dense crown on an
  ordinary trunk, with enough per-instance variation that it never looks like a "default."*
- **Form:** rounded/oval, medium. **Aspect:** ~0.7 : 1. **Fork:** moderate (`branch_start` 0.22).
  **Branch character:** ascending-then-spreading, unremarkable, well-distributed. **Asymmetry:** moderate — lean on variation to avoid a generic-ball read.

## 2. Interaction
- **Stand:** crowns **overlap into a normal mixed-canopy fill** — its job is to thicken the
  woodland between the characterful species, not to stand out. **Target reading:** disappears
  convincingly into a mixed stand.

## 3. Density
- **Bucket:** dappled (mid). **Real:** LAI ~**4.0–5.0** (median broadleaf); transmission ~15–25%.

## 4. Detail
- **Bark:** gray-brown `furrowed` (the safe average). **Leaf:** alternate, simple, ovate,
  serrate (generic broadleaf). **Summer:** medium green. **Fall:** yellow (the safe default;
  no showy red/scarlet that would imply a specific species). **Bloom:** none.

## 5. Behavior
- **Wind:** moderate (mid of the range). **Season:** flush → green summer → yellow fall → bare rounded crown.

## 6. The one unmistakable thing
*Nothing* — by design. Its success criterion is the inverse: it must NOT be identifiable as
anything in particular, and must NOT look like a repeated default. Variation is its whole job.

## 7. Variation envelope
- **Varies (most important here):** crown width, height (DBH), lean, asymmetry, density, fall
  timing — widely, so a cluster of `deciduous` never tiles or reads as filler.
- **Count:** **6–8** (it appears wherever genera are unmapped — could cluster anywhere; tiling risk high).

## 8. Build mapping
- **Params** (`deciduous` @ ln 1060): keep neutral average; `branch_start` 0.22, mid `leaf_density`;
  **prioritize the widened variation envelope** (6–8) over any distinctive feature.
- **Textures:** `furrowed` bark; generic ovate leaf; yellow fall. **Placement:** normal overlap.
- **Perf:** mid; fragment-bound. Gate ×5.

## 9. DoD
- [ ] Thumbnail: a believable nondescript broadleaf (not obviously wrong, not a star).
- [ ] In mixed stand: blends in, no "default tree" read. [ ] Tier handoff + crossfade.
- [ ] Cluster shows **no tiling** (§7 — the key check). [ ] Gate ×5. [ ] User sign-off.
