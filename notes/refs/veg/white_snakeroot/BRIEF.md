# BRIEF — White Snakeroot (Ageratina altissima)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_WhiteSnakeroot` — generator `make_white_snakeroot()` in
  `scripts/make_undergrowth.py:1479`; runtime `undergrowth_builder.gd` `SPECIES` **index 19**.
- **Layer:** herb (clump-forming woodland perennial, ~1.0–1.2 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP in rich deciduous woods and woodland edges (Ramble, North Woods, Hallett) per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Source:
[`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §9. A late-season
woodland walk would confirm the **white-cloud-under-canopy** read.

- [ ] **Habit, summer/bloom mass** — iNat CP; herbs doc §9
- [ ] **In a woodland-edge stand** (white cloud hovering over dark green)
- [ ] **Leaf detail** (OPPOSITE — rare here; ovate, sharply serrate, 3-veined base)
- [ ] **Bloom detail** (bright white flat-topped fuzzy corymbs, late season)
- [ ] **Stem detail** (smooth green, opposite forking)

## 1. Habit — how it flows over itself
- **One-liner:** upright bushy clump that branches in the upper half — by **opposite**
  forking, regular and organized — into a broad flat-topped to mounded canopy of bright
  white fuzzy flower clouds hovering above bright green foliage.
- **Overall form / crown shape:** broad flat-topped to mounded; bushier than white wood aster.
- **Aspect (width : height):** ~0.6 : 1.
- **First branch / fork height:** upper half; the opposite branching forks symmetrically.
- **Branch character:** moderately stiff, regularly forking (opposite) — an organized look.
- **Asymmetry:** modest — more orderly than most weedy forbs because of the opposite forking.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** clump-forming, spreading slowly by short rhizomes — adjacent
  clumps' white corymbs merge into a **continuous late-season white drift along the
  woodland edge**.
- **Target stand reading:** a rich-woods edge reads as a low white cloud floating over
  dark green understory in Sep–Oct — masses merging, not isolated bushes.

## 3. Density
- **Bucket:** dappled (bright thin-textured leaves; airy flat-topped flower layer).
- **Real number:** 0.6–1.5 m tall, 0.5–0.8 m spread, clump-forming
  ([[reference-cp-botany-full]]; herbs doc §9). No published LAI — bucket from habit.
- **Light transmission:** moderate; foliage thin-textured and somewhat lax.

## 4. Detail
- **Bark / stem:** round, smooth, glabrous, green, 4–8 mm; opposite forking in the upper portion.
- **Leaf / cluster:** **OPPOSITE** (rare among these herbs — key ID), simple, ovate,
  coarsely sharply serrate, acuminate tip, rounded-to-cordate base, 3-veined at base,
  thin/lax, bright green. Model the opposite arrangement explicitly.
- **Summer color:** bright/medium green. · **Fall:** foliage dying, no showy color. ·
  **Bloom:** **bright white** flat-topped fuzzy corymbs (`fc` white), pure clean white with
  protruding white styles — a flat white cloud; late season, `bl=[1.4,2.2]`.

## 5. Behavior
- **Wind character:** moderately flexible (`flex=0.30`) — upper branching sways, flat
  corymbs bob gently, thin leaves flutter; not rigid, not a curtain. Dead stems collapse by mid-winter.
- **Seasonal timeline:** opposite-leaf shoots (Apr–May, distinctive even early) → bushy
  green summer → bright white corymb bloom (Aug–Oct, the event) → seed → stems break down
  (not strongly persistent into winter).

## 6. The one unmistakable thing
The combination of **opposite leaves** (rare here) and **bright clean-white flat-topped
fuzzy flower clouds** in the late-season woodland understory. The whiteness is pure, not creamy.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.6–1.5 m), clump fullness, corymb size, lean, leaf size.
- **Variant count:** 3–4 (set `v` to ≥3 for the merging edge drift).

## 8. What this brief drives (build mapping)
- **Generator:** `make_white_snakeroot()` (`scripts/make_undergrowth.py:1479`) — model the
  **opposite** branching/leaves and the bright-white flat-topped fuzzy corymb; bushy upper-half
  branching over a green clump. Replace any generic helper.
- **Textures:** ovate sharply-serrate opposite leaf, bright-white fuzzy corymb cluster.
- **`SPECIES` row (idx 19):** reconcile to brief — `fc` white, `bl=[1.4,2.2]` (late season),
  `flex=0.30`; set `v` ≥3.
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED) in rich woods /
  woodland edge — `[5]` North Woods, `[6]` Ramble (and their edges). Cluster along edges
  so the white drift merges.
- **Perf note:** chunk-MultiMesh; overdraw rises where corymbs overlap — gain density from
  form/texture/placement, not card count. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as white snakeroot (opposite leaves, bright white flat corymbs).
- [ ] **Woodland-edge stand capture** shows the merged white drift over green.
- [ ] Bloom fires at the late-season `season_t` (`bl=[1.4,2.2]`).
- [ ] Dense stand shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
