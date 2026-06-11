# BRIEF — London Plane (Platanus × acerifolia)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md). Obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md). **Hero for the bark
> workflow** (§6) — the mottled camouflage bark is the worked example other bark styles copy.

- **Archetype key:** `london_plane` (≈1.7 k census trees — one of CP's most abundant)
- **Layer:** canopy (formal allées, perimeters, drives)
- **Tier coverage:** `_m` / `_l` (no `_s` — per TIER_BOUNDS; verify)
- **Brief written:** 2026-06-11 · **by:** Opus 4.8

## Reference set
- [x] **iNaturalist, CP-geofiltered** — API: **28 research-grade _Platanus_ (genus)**
  observations in the park bbox (only 4 keyed to the `× acerifolia` hybrid — iNat under-keys
  the hybrid; the genus count + census ~1.7 k confirm abundance). Population is real and large.
- [x] **Habit / bark / fall / winter (authoritative)** — Cornell UHI tree tour, Stanford
  Trees, Woodland Trust, NCSU Extension, [[reference-tree-canopy-data]] §11.
- [ ] **Walk-through / in-stand video** — NOT yet gathered (the Mall video is elms; North
  Woods is native woodland). **Non-blocking:** the bark is iconic and exhaustively documented;
  habit is well-established. A formal-allée / Fifth-Ave-perimeter walk would refine the
  pollarded-row look — *take the user up on the offer only if convenient* (their offer
  2026-06-11). Mark any AI art target explicitly if used (none so far).

## 1. Habit — how it flows over itself
- **One-liner:** *a massive broad-spreading tree on a high clear bole; stout, somewhat
  crooked/sinuous limbs ascend and spread wide into a rounded-to-irregular crown — often
  pollarded into knuckled rows in formal settings.*
- **Overall form / crown shape:** young pyramidal → broad, rounded, massive at maturity;
  irregular and characterful on old trees.
- **Aspect (width : height):** ~0.6–0.8 : 1 (12–18 m spread on 18–30 m; exceptional to 50 m).
- **First branch / fork height:** **high clear bole** (`branch_start` 0.30 is right) — shows
  off the bark; in formal CP rows often pollarded/pruned up.
- **Branch character:** stout, horizontal-to-ascending (`branch_angle` 60° — notably
  horizontal), crooked and sinuous on age; foliage concentrated in the **outer crown shell**
  (parasol layering).
- **Asymmetry:** old planes are characterfully irregular and lean; pollarded ones are
  knuckled and denser — span both (§7).

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** in formal allées/rows the broad crowns **merge into a continuous
  arched shade ceiling** (similar role to the elm allée but heavier/rounder, not a fountain);
  as park specimens, broad and spreading with overlap at census spacing.
- **Target stand reading:** *a plane allée/row reads as a heavy continuous shade canopy on
  pale mottled trunks — the camouflage boles in rhythm beneath a broad ceiling.*

## 3. Density
- **Bucket:** opaque / dense (good shade tree; large flat leaves block sun).
- **Real number:** LAI **4.0–6.0** (largest leaf area of any tree in inner London)
  ([[reference-tree-canopy-data]] §11).
- **Light transmission:** ~8–15% (heavy shade); can shed 30–50% of leaves in extreme heat.

## 4. Detail
- **Bark — THE feature:** **mottled, exfoliating "camouflage / jigsaw" bark** — olive-green
  to grey scaly plates flake off in large patches to reveal **creamy-tan** inner bark;
  trunk reads as cream + tan + olive-green + brown-fleck patchwork. Pale, smooth higher up.
  This is the species' identity and the §6 bark-workflow hero target. `bark_color`
  `(0.48,0.45,0.36)` is the pale base; the **plane/mottled bark style** must paint the patches.
- **Leaf:** alternate, simple, **palmately 3–5 lobed (maple-like but larger)**, 10–25 cm,
  often wider than long, thick/stiff, long petiole; outer-shell concentrated.
- **Summer color:** medium-dark green. · **Fall:** orange-yellow → brown (not showy; often
  just browns and drops, Oct–Nov). · **Fruit/winter:** **bristly round seed balls** (~2.5–4 cm),
  1–3 dangling per stalk, **persist through winter** on bare pale-mottled crooked limbs.

## 5. Behavior
- **Wind character:** large stiff leaves and stout limbs → **moderate, heavy** motion; the
  big leaves clatter/flip rather than flutter. Mid-stiff (closer to oak than birch).
- **Seasonal timeline:** late-ish flush → dense green summer → orange-yellow/brown fall →
  bare pale-mottled crown with **persistent dangling seed balls** (the winter signature) → spring.

## 6. The one unmistakable thing
The **camouflage exfoliating bark** — cream/tan/olive patchwork — on a high clear bole.
Get the bark right and the tree is unmistakable even bare; get it wrong and it's a generic
broadleaf. (Secondary tell: dangling seed balls in winter.)

## 7. Per-instance variation envelope
- **Varies across seeds:** crown width, limb crookedness/sinuosity, bole height, lean,
  pollarded-knuckled vs free-form, bark-patch pattern (per-instance bark seed), height (DBH).
- **Variant count:** **6–8** (high census ~1.7 k — tiling visible in formal rows; confirm
  picker handles >5).

## 8. What this brief drives (build mapping)
- **Generator/params** (`generate_trees_mtree.py`, `london_plane` @ ln 904): keep high
  `branch_start` 0.30 + horizontal `branch_angle` 60; stout crooked limbs; outer-shell foliage.
- **Textures — the hero deliverable:** the **mottled plane-bark style** in `tree_bark.gdshader`
  + bark texture — cream/tan/olive camouflage patches with a per-instance seed so trunks don't
  repeat. This is the §6 bark-workflow proof the cheaper model copies for other bark styles.
  Palmate 3–5-lobe leaf texture.
- **Builder/placement** (`tree_builder.gd`): formal-row overlap so allée crowns merge (§2);
  per-instance bark seed.
- **Perf budget:** fragment-bound; bark detail is texture-latency-cheap
  ([`trees.md`](../../../docs/trees.md) §4g — ALU/texture richness is ~free) so the bark style
  can be rich. Perf gate ×5, no regression.

## 9. Definition of Done (captures that validate this brief)
- [ ] Thumbnail reads as a plane: **camouflage bark** + palmate leaves + broad crown.
- [ ] **In-game near capture** at a plane location — the mottled bark reads correctly close up,
  no per-instance repeat in a row.
- [ ] **Row/allée capture** — broad crowns merge over pale mottled boles (§2).
- [ ] Tier handoff + crossfade ([`tree_model_redesign.md`](../../../docs/tree_model_redesign.md) §9).
- [ ] Bare-winter capture — persistent seed balls + mottled crown.
- [ ] Perf gate ×5 equal-or-better.
- [ ] User walk-around sign-off.
