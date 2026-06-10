# Architecture

System map for Central Park Walk. Written 2026-06-09 from a full-codebase audit.
Companion docs: [`vision.md`](vision.md) (what and why), `rendering.md` (budgets — to be written from profiling), `data_pipeline.md` (pipeline detail — to be written).

**Numbers marked (est.) are code-derived estimates, not measurements.** Replace with profiled values as they're captured; never tune against an (est.).

## 1. The two halves

The project is an **offline data pipeline** (Python) that compiles real-world data into binary artifacts, and a **runtime** (Godot 4 / GDScript + one GDExtension) that renders them. The pipeline runs on the developer machine; the runtime ships.

```
OSM ─┐
LiDAR DEM/DSM ─┤                                      ┌─ park_loader.gd ─ 13 builders ─ scene
NYC tree census ─┼─ convert_to_godot.py ─ *.bin/*.png ─┤
NYC buildings ─┤                                      └─ main.gd ─ sky/weather/season/player
CC0 assets ─┘
```

## 2. Offline pipeline

### Producer → artifact → consumer

| Source | Script | Artifact | Runtime consumer |
|---|---|---|---|
| Overpass API | `download_osm.py` | `central_park_osm.json` (14 MB) | `convert_to_godot.py` only |
| NYC SODA API | `download_buildings.py` | `nyc_buildings.geojson` | `convert_to_godot.py` only |
| Terrarium tiles / LiDAR 8K GeoTIFF | `download_terrain.py` + `lidar_data/` | DEM input | `convert_to_godot.py` only |
| NYC tree census + 6M Trees + CHM | external, in `lidar_data/` | tree positions/species/heights | `convert_to_godot.py` only |
| all of the above | `convert_to_godot.py` (~3.9k lines) | see table below | runtime |
| gap inventory | `generate_gaps.py` | `data_gaps.json`/`.geojson` | `gap_builder.gd` |
| ambientCG/Polyhaven/Quaternius | `download_assets.py`, `download_models.py` | `textures/`, `models/` | builders |

### Generated artifacts

| Artifact | Format | Size | Reader |
|---|---|---|---|
| `park_data.bin` | CPW1 tagged sections (META/BNDY/TREE/BLDG/PATH/BARR/BNCH/LAMP/TRSH/FLAG), columnar, little-endian, string tables per section | 1.7 MB | `park_loader.gd` |
| `park_data.json` | full JSON (water, streams, statues, amenities, zones, …) — complex types not in .bin | 3.6 MB | `park_loader.gd` |
| `heightmap.bin` | u32 w/h + f32 world_size/origin + f32[w×h] | 257 MB | `main.gd` (CPU height queries) |
| `heightmap_gpu.bin` | u32 w/h + f32 min/max + RG8 16-bit heights, 4096² | 129 MB | `park_loader.gd` → vertex shaders |
| `world_atlas.bin` | u32 w/h + RG8 8192² — R=surface type (0 outside,1 grass,2 paved,3 unpaved,4 water,5 building,6 bridge,7 rock), G=occupancy bitmask | 129 MB | `park_loader.gd` `_atlas_surface()`/`_atlas_occupancy()` |
| `grass_instances.bin`, `ground_cover_instances.bin` | serialized instance transforms | 9+14 MB | grass/ground-cover builders |
| `water_grids.bin` | per-body water grids (fast path; runtime rasterization is the ~5s fallback) | 2.9 MB | `water_builder.gd` |
| `boundary_mask.png`, `shore_distance.png`, `landuse_map.png` | rasters | — | shaders |

Incremental rebuild via `.pipeline_cache.json` (mtime/sha256 signatures); `--force` regenerates. Full cold rebuild ≈ 50 min (network-bound).

### Coordinate system (the contract everything depends on)

- Projection defined in `convert_to_godot.py:37-40`: `REF_LAT=40.7829, REF_LON=-73.9654`, equirectangular meters-per-degree. **Duplicated in `generate_gaps.py:17-20`** — keep in sync (debt #D1).
- Origin (0,0) = ref point; **+X = east, +Z = south** (`project()` negates latitude delta). Godot forward is −Z = north.
- `WORLD_SIZE = 5000.0` m, world spans [−2500, +2500] on X and Z. Defined in `convert_to_godot.py:61` and assumed by `park_loader.gd` grid indexing and `main.gd` ground plane. **Not linked by any shared constant** (debt #D1).
- Grid resolutions: heightmap + atlas 8192² (0.61 m/px), GPU heightmap 4096², canopy map 2048² (2.44 m/px, runtime-baked).
- All lat/lon → XZ conversion happens in Python; GDScript only ever sees pre-projected meters.

## 3. Runtime startup

`main.gd::_ready()` (the orchestrator; ~2-5 s total):

1. Parse CLI flags (`--pos --time --weather --season --walk --tour …`).
2. Load `heightmap.bin` into `_hm_data`; carve terrain voids (Bethesda arcade).
3. Build Environment: volumetric cloud sky (`cloud_sky.tres`) or procedural fallback; SDFGI 6 cascades; volumetric fog; SSAO/SSIL; AGX tonemap; sun with 8192px 4-cascade shadows, 150m max distance. Register ~12 global shader uniforms.
4. Create WindSystem, WeatherManager, DayNightCycle singletons.
5. Terrain3D setup (shader override, collision radius 128).
6. **ParkLoader**: load `park_data.bin` + `world_atlas.bin`, then run 13 builders **in strict order** (labels → bridges → trees → undergrowth → ground cover → vines → furniture → infrastructure → landmarks → details → water → boundary → buildings). Order is load-bearing and implicit (debt #D2).
7. GPU grass: 4 biomes × 3 tiers ⇒ ~12-16 GPUParticles3D/GPUGrass nodes.
8. Player (CharacterBody3D + Head + Camera), HUD, color-grade CanvasLayer, lamp-light pool (48 SpotLight3D serving ~950 lamp positions).
9. Apply initial time of day; enter tour/walk-bot mode if flagged.

## 4. Subsystem ownership

| File | Owns | Per-frame work |
|---|---|---|
| `main.gd` (~2.3k lines) | god-object: env/sky, season, lamps, grass setup, tour/walk bots, diagnostics, input, profiling overlay | orchestrates everything below in `_process` |
| `park_loader.gd` (~1.7k) | data load, atlas queries, canopy map bake, builder lifecycle, texture/shader cache | none |
| `player.gd` | movement, stair-step, fly mode, boundary clamp | `move_and_slide` + 2 `test_move` (1-5 ms est.) |
| `day_night_cycle.gd` | 5-keyframe interpolation (5h/6.5h/12h/19h/21h) of ~30 env/sun/sky params; weather overrides; facade night factor | `apply()` early-outs unless time moved >0.01h; full apply ~1-2 ms (est.) incl. loop over all facade materials |
| `wind_system.gd` | 4-layer FastNoiseLite wind (direction/breeze/swell/gust) | per frame: 4 noise samples + `wind_vec` global + per-node set on 12-16 grass nodes |
| `weather_manager.gd` | rain/snow/leaf/blossom GPUParticles (6k-30k particles); snow_cover/rain_wetness accumulators | reposition 4 systems to player, set gravity from wind |
| `hud_manager.gd` | HUD + F9 perf overlay | label updates; perf text every 0.25 s |
| `tree_builder.gd` | the tree system — see §5 | none (engine visibility_range does culling) |
| `undergrowth_builder.gd`, `ground_cover_builder.gd` (via `chunk_builder.gd`) | distance-streamed chunks (80m chunks, 200m load, 350m unload) | `update_camera` check per frame; ≤1 chunk build/frame (~1-5 ms spike per build, est.) |
| `grass_*` + `gpu_grass/` GDExtension | 3-tier grass (Tier 0 GPU compute 0-10m, clusters 10-35m, tufts 13-120m) | compute dispatch per frame; camera-follow grid snap |
| static builders (`path/water/boundary/building/furniture/infrastructure/landmark/detail/gap`) | static world; mostly MultiMesh + combined meshes; ~600-750 scene nodes total (est.) | none (water particles/mist are GPU) |
| `audio_manager.gd` | ambient + footsteps | ~1-2 ms (est.) — NOTE: implemented despite vision.md deferring audio; keep, but it's not a v1.0 work area |

## 5. Tree system (the project's hardest subsystem)

Current state (post two-tier collapse, commit 20486e4):

- **Mesh tier 0-290m**: `{species}_{s|m|l}_lod1` decimated meshes; one MMI per species-tier × 80m chunk, positioned at instance centroid; per-chunk deterministic variant pick (`tree_builder.gd:523`) to limit MMI fragmentation; dither crossfade out 230-250m. ~9,852 census + woodland-fill trees, 17 archetypes.
- **Impostor tier 190-2500m**: octahedral billboards, 8×8 hemisphere frames, 2048² atlas per species-tier (56 atlases), premultiplied alpha, crossfade in 230-250m, shadows off.
- **Bake** (`scripts/impostor_baker.gd`): renders **lit color** under a fixed procedural sky (ambient 0.7, SSAO off) — this is the root cause of the impostor/mesh color mismatch family of bugs (May 19 finding: atlas RGB dark olive while alpha was fine). Baker already outputs `_impostor_albedo/_normal/_depth.png` + winter pass.
- **Sprint change (D3-5)**: switch to **unlit albedo + normal atlases, lit at runtime** in `tree_impostor.gdshader` with the same sun/ambient as meshes. Touch points identified: `impostor_baker.gd:315-343` (don't bake lighting/tint), `tree_leaf.gdshader:115-154` (bake-mode flag), `tree_impostor.gdshader` (decode normals, output NORMAL). Existing normal/depth atlases must be quality-checked before reuse.
- Re-bake protocol: one Godot process per species (~12 s each); all-at-once hangs (see memory `lessons_impostor_bake.md`).

## 6. Global shader state

Set via `RenderingServer.global_shader_parameter_set`, mostly from `main.gd::_process`:
`wind_vec, season_t (0-4), snow_cover, rain_wetness, lightning_flash, dew_amount, lamp_glow, player_world_pos, sky_reflect_color, cloud_coverage_g, cloud_speed_g, impostor_brightness`.
Parameter names are string literals repeated across 3+ files (debt #D3).

## 7. Performance — what we know vs. suspect

**Known (measured before, re-verify):** Ramble ≈10 fps, ~80M triangles reported, bottleneck reported as ~67 ms CPU "process" not GPU render. Profiled GDScript subsystems (F9 overlay buckets) account for only ~5-10 ms.

**Unprofiled suspects (hypotheses to TEST in the D1-2 profiling pass, not act on):**
1. Shadow rendering: 4 cascades × all LOD0 tree shadow casters.
2. SDFGI: 6 cascades over tree-dense geometry.
3. Terrain3D clipmap updates.
4. Volumetric fog compute (density 0.003, long range).
5. Draw-call / MMI count (tree MMIs ≈ 1.2-2k (est.) + undergrowth chunks + grass nodes).
6. Vertex load: 80M tris at the Ramble suggests mesh-tier density × no occlusion culling (canopy occluders disabled — `tree_builder.gd:703-706`).

The F9 overlay's "unaccounted" bucket is where most of the 67 ms hides. **Rule: no perf change ships without a before/after measurement at the 5 test locations** (Literary Walk −600,1420 · Bethesda −480,1020 · Ramble −400,600 · Great Lawn −99,173 · North Woods 600,−1315).

## 8. Debt register (prioritized)

| # | Debt | Where | Risk |
|---|---|---|---|
| D1 | Projection + WORLD_SIZE constants duplicated, unlinked | `convert_to_godot.py:37-40,61`, `generate_gaps.py:17-20`, GDScript implicit | silent world-wide corruption on drift |
| D2 | Builder order implicit in `park_loader` | `park_loader.gd` builder sequence | reorder breaks world silently |
| D3 | Shader global names as scattered string literals | main/day_night/builders | typo = silently dead uniform |
| D4 | god-object `main.gd` (~2.3k lines) | main.gd | every feature passes through one file |
| D5 | CPU/GPU noise + height interpolation duplicated | `park_loader.gd:563-593` vs shaders; `main._terrain_height` vs `park_loader._terrain_y` | drift between CPU placement and GPU rendering |
| D6 | Impostor bakes lit color (being fixed in sprint D3-5) | `impostor_baker.gd` | whole class of color-mismatch bugs |
| D7 | CPW1 binary schema duplicated writer/reader, no validation/version negotiation | `convert_to_godot.py:540-870` ↔ `park_loader.gd` | format change = silent corruption |
| D8 | Dead/unused data paths: landuse zones parsed not rendered; playgrounds/viewpoints extracted not all instanced; legacy `shaders/cloud_sky.gdshader` vs active `cloud_sky/clouds.glsl`; vine system disabled | various | confusion, wasted load |
| D9 | Hardcoded landmark coords + statue GLB dicts in code, not data files | `landmark_builder.gd`, `infrastructure_builder.gd` | contradicts data-first auditability |
| D10 | Magic numbers (eye height 1.55 vs 1.58, path Y offsets, chunk ranges) duplicated | player/main/builders | tuning drift |

Repo-root clutter (scratch .odp/.txt/.rar, session transcripts) is being cleaned in sprint D0.

## 9. Change rules

- A change that contradicts this document means one of the two is wrong — update whichever is, in the same commit.
- New subsystems must declare: data source, node/instance count, per-frame cost, and which budget line in `rendering.md` they spend.
- Anything in §7 listed as a hypothesis must be measured before it is "fixed."
