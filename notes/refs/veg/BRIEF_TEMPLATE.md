# BRIEF — <Common Name> (<Latin name>)

> Per-species reference brief. Copy this file to `notes/refs/veg/<species>/BRIEF.md`
> and fill every field from the reference set — do not estimate a field the references
> can answer (workflow.md §3). This is the falsifiable target the visual DoD is judged
> against; if a field stays `<TODO>`, the model will guess it and guess wrong. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md). Trees also obey
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `<oak | spicebush | …>` (the generator/runtime name)
- **Layer:** `<canopy | sub-canopy | shrub | herb | grass | floor>`
- **Tier coverage:** `<s/m/l as the runtime requests — see TIER_BOUNDS; trees only>`
- **Brief written:** `<date>` · **by:** `<model/session>`

## Reference set
List what you actually gathered, with source + link. Sourcing order (user-confirmed):
iNaturalist CP-geofiltered → claudetube walk/time-lapse video → Conservancy/NYBG →
user-supplied. **Ask the user for a walk video if winter-structure or in-stand habit is
unclear from stills.** Mark AI-generated art targets explicitly (gap-fill only, never
traced).

- [ ] **Habit, summer mass** — `<source/link>`
- [ ] **Winter bare structure** (most important — the skeleton is where habit lives) — `<…>`
- [ ] **In a stand/thicket/grove** (interaction, NOT an isolated specimen) — `<…>`
- [ ] **Bark / stem detail** — `<…>`
- [ ] **Leaf / needle / cluster detail** — `<…>`
- [ ] **Fall color** — `<…>`
- [ ] **Bloom** (if showy) — `<…>`
- [ ] **Wind/behavior video** — `<…>`

## 1. Habit — how it flows over itself
*One sentence first (the gesture), then specifics. This is the biggest realism lever
and the current models' weakest point.*

- **One-liner:** `<e.g. "multi-stemmed; primary stems arch to ~3 m then secondary growth droops and layers into a mound — cascades, never a V">`
- **Overall form / crown shape:** `<vase | rounded | columnar | weeping | mounding | irregular>`
- **Aspect (width : height):** `<…>`
- **First branch / fork height:** `<fraction of total height>`
- **Branch character:** `<angle; arch vs straight; droop; tapering>`
- **Asymmetry:** `<how lopsided a real light-competing specimen is — drives variation>`

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** `<crowns interlace into a ceiling | thicket-forming, masses overlap | solitary, gaps between>`
- **Target stand reading:** `<one sentence describing what a correct grove/thicket capture should look like>`

## 3. Density
- **Bucket:** `<opaque | dappled | open/lacy>`
- **Real number:** `<LAI x.x | stems per m² | cover %>` (source: [[reference-tree-canopy-data]] / [[reference-cp-botany-full]] — cite, don't estimate)
- **Light transmission:** `<~% through crown>`

## 4. Detail
- **Bark / stem:** `<style: furrowed | smooth | mottled-plane | exfoliating | …; color>`
- **Leaf / needle / cluster:** `<shape; size; arrangement; cluster vs along-branch>`
- **Summer color:** `<…>` · **Fall color + timing:** `<…>` · **Bloom:** `<color + season, if any>`

## 5. Behavior
- **Wind character:** `<stiff (oak) | trembling (birch) | bouncing on arching stems | curtain (willow) | …>`
- **Seasonal timeline:** `<flush → summer mass → fall color (when) → drop (clean vs marcescent) → winter state → bloom (when)>`

## 6. The one unmistakable thing
`<the single trait that makes someone say "that's a <species>" — the model must nail this>`

## 7. Per-instance variation envelope
*What spans the 5 (or 6–8) seed variants so a stand never tiles. Survey the real range
(age, sun vs shade, soil) — [[feedback-research-before-generator]].*

- **Varies across seeds:** `<height; crown width; lean; asymmetry; density; …>` with ranges `<…>`
- **Variant count:** `<5 default; 6–8 for high-census species>`

## 8. What this brief drives (build mapping)
*For trees: which `generate_trees_mtree.py` `SPECIES` keys and shaders this changes.
For other plants: the generator + builder. Plus the perf note.*

- **Generator/params:** `<SPECIES dict keys to tune; or generator script>`
- **Textures:** `<gen_leaf_textures / gen_cluster_textures / bark>`
- **Builder/placement:** `<tree_builder.gd / undergrowth_builder.gd; any placement-orientation need, e.g. cathedral-elm convergence>`
- **Perf budget:** fragment-bound — gain density from form/texture/placement, not card overdraw (tree_model_redesign.md §2). Perf gate ×5, no regression.

## 9. Definition of Done (captures that validate this brief)
- [ ] Thumbnail reads as this species, matches §1–§6.
- [ ] **In-game stand/thicket capture** at `<dominant location>` — interaction (§2) reads correctly. *The stand is a validation unit, not just the thumbnail.*
- [ ] Tier handoff + crossfade (trees: tree_model_redesign.md §9).
- [ ] Dense same-species stand shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better.
- [ ] User walk-around sign-off.
