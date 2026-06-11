# Grass & Turf

Spec for the lawn/turf system. Written 2026-06-11 (D9–12 of the Fable 5 sprint) from the
Sheep Meadow reference comparison (`notes/refs/sheep_meadow_game/COMPARISON.md`, finding #3:
"turf reads as unmown deep field") plus a zone-encoding audit. Binding in the same way as
`docs/trees.md`: code that contradicts this file is wrong, or this file gets updated in the
same commit.

## 1. System map

Four cooperating layers; color coherence comes from every layer including
`shaders/include/grass_zone_colors.gdshaderinc`.

| layer | files | range | role |
|---|---|---|---|
| Tier 0 blades + accents | `main.gd` `GRASS_TIER0`/`GRASS_ACCENTS`, `shaders/grass_particles.gdshader` (spawn), `grass_particle_render.gdshader` (draw) | 0–6 m | close-up blade variety, clover/dandelion |
| Tier 1 blades | `main.gd` `GRASS_BIOMES`, same shaders | 0–60.5 m (dither fade from ~36 m) | base blade coverage, one mesh per biome |
| Tier 2 tufts (**dormant**) | `grass_tuft_builder.gd`, `shaders/grass_tuft_render.gdshader` | 13–120 m | `_setup_grass_tuft_chunks()` is never called (audited 2026-06-11) — retired in the 2026-05-09 unification; code kept wear-consistent in case of revival |
| Terrain albedo | `shaders/terrain3d_override.gdshader` | everywhere | blends Terrain3D source 85% toward `grass_base_color_no_dead()` in grass zones — the dominant signal beyond ~20 m |

Spawn-side data: `landuse_map.png` (R8 8192², zone IDs) + canopy map. Both sampled in the
particle spawn shader, the tuft builder (CPU), and the terrain shader.

## 2. Zone encoding — the truth table

The ONLY encoding is the one `convert_to_godot.py` `prebake_landuse_map()` writes
(`ZONE_MAP`, ~line 3805). There is no runtime remap (`main.gd _apply_landuse_map` loads the
PNG verbatim).

```
0 unzoned (grass surface default inside park)   8 swimming_pool
1 garden                                        9 track
2 grass  ← ALL named lawns: Sheep Meadow,      10 wood
         Great Lawn, North Meadow, ...         11 forest
3 pitch                                        12 water
4 playground                                   13 shore (water dilation ring)
5 nature_reserve (Hallett)                     14 wild_meadow (102nd St + Dene Slope,
6 dog_park                                        hand-drawn — the only true meadows)
7 sports
```

**History note (audited 2026-06-11):** `grass_particles.gdshader`, `grass_zone_colors.gdshaderinc`
and `grass_tuft_builder.gd` carried comments describing a fictional encoding
("0=SheepMeadow 1=GreatLawn 2=NorthMeadow …"). Branches keyed to that fiction caused real,
user-visible defects:

- Zone 2 (= every named lawn) took the "NorthMeadow open meadow" branch: `zone_height 2.0`
  → 15 cm × random 0.6–1.4 × patch 0.7–1.3 ≈ up to 27 cm blades on lawns the CPC mows at
  2.5–3 in. **This was the root cause of comparison finding #3.**
- Sedge biome spawned on zone 7 (sports fields); wild-meadow biome on zone 8 (pools);
  zones 13/14 — the places sedge and wild grass actually belong — got nothing.
- `grass_particle_render.gdshader` decoded `biome_id` from `COLOR.b`, but the spawn shader
  writes terrain-tint there → per-biome blade tints never fired (or fired arbitrarily).

## 3. Heights & mowing (data: CPC Turf Care Handbook, see convert_to_godot.py comment ~3814)

All named lawns are maintained turf. A-class mows 2×/week at 2.5–3 in (6.4–7.6 cm); B/C/D
mow less often at the same height. Standing height between mows ≈ 7–10 cm. Only zones 5
(nature reserve), 10/11 (woodland floor), 13 (shore sedge), 14 (wild meadow) are unmown.

Blade meshes: Lawn 7.6 cm, Shade 12 cm, Wild 25 cm, Sedge 16 cm at scale 1.0.

| zone | biome | zone_height | standing | notes |
|---|---|---|---|---|
| 0 unzoned | lawn | 1.3 | ~10 cm | informal fringes, tree lawns |
| 1 garden | lawn | 0.9 | ~7 cm | formal panels, tightest |
| 2 grass | lawn | 1.1 | ~8.5 cm | named lawns (A/B class) |
| 3 pitch | lawn | 0.95 | ~7 cm | ballfields |
| 4 playground | lawn | 1.0 | ~7.6 cm | |
| 6 dog_park | lawn | 1.0 | ~7.6 cm | heavy ambient wear (see §4) |
| 9 track | lawn | 0.95 | ~7 cm | |
| 5 nature_reserve | shade | 1.8 | ~22 cm | unmown |
| 10/11 wood/forest | shade | 1.4 | ~17 cm | |
| 13 shore | sedge | 1.3 | ~21 cm | Carex stricta |
| 14 wild_meadow | wild | 1.2 | ~30 cm | Switchgrass placeholder |

Mowing homogenizes: maintained zones (1,2,3,4,6,9) use patch height variation ±10 %
(unmaintained keep ±30 %) and lawn-biome per-instance y-scale 0.85–1.15 (width randomness
unchanged at 0.6–1.4).

## 4. Wear & mottle (comparison finding #3, reference NOTES.md)

Reference (Sheep Meadow footage): mown turf reads as *texture* beyond a few meters — mottled
green-brown, worn patches everywhere, trending to bare compacted dirt under canopy and at
high-traffic edges; mid-meadow greenest.

Three wear sources, combined as `max()`:

1. **Path/bench proximity (data-driven, baked).** `scripts/gen_wear_map.py` reads
   `world_atlas.bin` (surface R: 2=paved 3=unpaved; occupancy G bit1=bench) and writes
   `wear_map.png` (L8 4096, gitignored like landuse_map.png):
   - unpaved path: wear 1.0 within 1 m of the path, linear falloff to 0 at 6 m
   - paved path: 0.55 max, falloff 0.7→3.5 m (desire lines hug pavement)
   - bench: 0.7 max, radial falloff to 2.5 m
2. **Canopy compaction (runtime).** `smoothstep(0.45, 0.9, canopy) * 0.75` — bare ground
   under big crowns (reference hq_06-08). Leaf litter overlays ON TOP of the dirt.
3. **Ambient mottle (runtime noise).** Low-level everywhere on lawn zones: rotated-octave
   noise → wear 0–0.35, so mid-lawn shows worn green-brown patches, not only path edges.
   Zone 6 (dog park) gets +0.5 base.

Color response (`apply_turf_wear()` in grass_zone_colors.gdshaderinc), two stages with
noise-perturbed edges so boundaries are organic:
- wear 0.15–0.55: blend toward thin/dry turf (desaturated, yellow-brown — reuses the dried
  grass spectral color 0.315/0.243/0.120 mixed with soil)
- wear 0.55–1.0: blend toward compacted dirt `vec3(0.150, 0.120, 0.082)`

Geometry response (coherence rule — **no green blades on dirt**):
- spawn shader: skip chance `smoothstep(0.2, 0.75, wear) * 0.97`, height ×`mix(1.0, 0.55, wear)`
- tuft builder: same skip CPU-side (samples wear_map image)
- blade/tuft color: same `apply_turf_wear()` so survivors in worn areas read dusty

## 5. Definition of Done (this spec's work)

- [ ] Zone re-truthing: heights/biomes/comments per §2–§3 tables in all three consumers;
      render-shader biome_id passed as a material uniform. Verify: debug-highlight capture
      shows sedge on shores, wild on the two meadows, nothing on pools/sports beyond lawn.
- [ ] Wear map generated; terrain + blades + tufts all respond; close-up capture shows
      blades thinning into dirt patches, no green-on-dirt.
- [ ] Sheep Meadow pose re-capture vs reference: lawn shows green-brown mottle (brown-pixel
      fraction in lawn crop within 0.5–2× of reference crop, same pose/time); no "deep
      field" blade silhouette read at eye level.
- [ ] Under-canopy capture at a meadow-edge crown vs hq_06-08: compacted dirt + sparse
      blades + litter, dapple preserved.
- [ ] Macro-mottle softness from the finding-#2 fix preserved (same-pose block ratio ≈1.24,
      no hard lattice edges reintroduced).
- [ ] Perf gate ×5: no regression vs 20260610_223349 (66/73/54/84/46 fps).

## 6. Open / deferred

- **Lawn absolute brightness**: clean-turf luminance ratio lawn/sky measured 0.37 in game
  vs 0.63 in reference footage (2026-06-11, hero pose vs hq_02-08) — our sunlit turf is
  ~1 stop dark relative to sky. Candidate causes: no turf sheen/specular, blade
  self-shadowing at grazing angles, AgX shoulder. Needs its own measured calibration pass
  (like the sky ×5/×20/×6 session); don't band-aid with an albedo multiplier.

- True species mixes per CPC class ([grass conservancy data] memory) — palettes currently
  KBG/rye/fescue approximations; fine for now.
- Mow-stripe feature: real footage shows mottle, not stripes, on meadows — stripes stay
  sport-turf-only (`ground_surface.gdshader`).
- Wildflower meadow species models (zone 14) — post-sprint model program.
- GPU-grass GDExtension (`gpu_grass/`) is retired from the lawn path (2026-05-09
  unification); `_setup_gpu_grass()` and `_setup_grass_tuft_chunks()` are both
  never called — beyond ~60 m the lawn is terrain albedo only.
