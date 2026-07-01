# Grass & Turf

Spec for the lawn/turf system. Written 2026-06-11 (D9–12 of the Fable 5 sprint) from the
Sheep Meadow reference comparison (`notes/refs/sheep_meadow_game/COMPARISON.md`, finding #3:
"turf reads as unmown deep field") plus a zone-encoding audit. Binding in the same way as
`docs/trees.md`: code that contradicts this file is wrong, or this file gets updated in the
same commit.

## 0. Fantasy mode (alpha-testing QoL — ACTIVE since 2026-06-28)

The data-driven Central Park palette below is currently **suspended** in favour
of one lush, idealized fantasy green, so testers evaluate trees/vegetation
against a clean lawn instead of muted, patchy, wear/dead-tuft turf. This is a
deliberate, reversible departure from the data-first philosophy — *temporary*.

- Toggle: `GRASS_FANTASY` in `main.gd` (default `1.0` = ON). It drives a
  `fantasy` uniform on **both** `grass_particle_render.gdshader` and
  `terrain3d_override.gdshader` (they must stay matched).
- ON: `fantasy_grass_color()` in `grass_zone_colors.gdshaderinc` — lush green +
  gentle all-green vitality drift; no zone palette, thatch, turf wear, dead
  tufts, golden undertone, biome amber/teal tints, canopy litter, or
  autumn/winter dry-down. Translucent backlight boosted.
- OFF (`0.0`): restores everything in §1–§6 verbatim. Every data path is
  preserved behind `if (fantasy < 0.5)` — nothing was deleted, only branched.
- Blades (`make_blade_mesh.py`) retuned taller/arched/sharper for the lush look.

Set `GRASS_FANTASY := 0.0` to return to the data-driven spec that follows.

## 0b. Grass overhaul — direction reset (2026-06-29)

The instanced-tuft approach was rejected by Chris on two grounds the screenshots
proved (cpw_000/001/002): **(1)** straight down, every clump — geometry tuft *or*
crossed-quad card — projects to a flat green **starburst/asterisk**, because both
build a tuft as blades radiating from a single point (a side-view-only trick);
**(2)** spacing tufts out will never reach 60 fps (vertex load + transparent
overdraw across a 60–140 m band). The **card LOD tier** (§1 row, `GRASS_CARDS`,
`make_grass_card.py`) is part of the rejected approach — pending removal.

New mental model: grass is **a textured ground surface with blades growing out of
it near the camera**, not a field of discrete tuft objects. Three layers:

1. **The ground IS grass.** `make_turf_texture.py` generates a real top-down turf
   texture (thousands of z-tested blade strokes over a dark-green understory →
   `textures/terrain3d/grass_albedo_height.png` + `_normal_rough.png`), replacing
   the old flat pale speckle. Retiled small (`texture_grass.tres` `uv_scale 1.6`
   ≈ 1.25 m) so blades resolve. The terrain shader injects this texture's
   blade-scale luminance as relief into the recoloured palette (see §3 note) so
   the lawn reads as blades from **any** angle, including straight down — no
   starbursts, no bare dirt. **This is the foundation; landed 2026-06-29.**
2. **Near blades (next):** real upright *individual* curved blades within ~18 m,
   not radial domes — depth/parallax/wind up close. Not yet built.
3. **No mid/far card tier.** Distant grass = terrain texture only.

Eval bare terrain with `--no-grass` (skips blade particles; `main.gd`). The
`--terrain-only` capture path honours `--pitch` (e.g. `-89` for straight down).

## 0c. Turf-tile grass — the "3D mesh world" blades (CURRENT near/mid, 2026-06-30 → 07-01)

The near/mid grass is now **real 3D blade geometry**, not cards/tufts: a tile mesh packed
with hundreds–thousands of baked curved blades (`_make_turf_tile_mesh`, `turf_tile.gdshader`),
instanced on a camera-following grid so blades are genuine from **any** angle incl. straight
down — no billboard swivel, no radial starbursts. Beyond it, the §0b shell/terrain texture
fills the distance (`near_clear_r = TURF_REACH - 8`).

**Density & perf — single dense mesh + continuous falloff (2026-07-01, final).** First tried
3 LOD-density rings (dense near → sparse far) to cut the ~37.6M-tri single-8000-tile field.
That **regressed**: the discrete rings cross-faded ahead of the camera as a visible *shimmer /
odd LOD overlap*, and the thinned mid/far rings read *bare* at a grazing angle (far blades went
sub-pixel → sparse crawling specks under FSR2). Reverted to **one dense mesh** with a
**continuous per-blade rank falloff** (`turf_tile.gdshader`: `keep = 1 - smoothstep(near_full,
far_radius, dist)`, blade lives where `rank < keep`): full density within `TURF_NEAR_FULL`,
thinning smoothly to zero by `TURF_RADIUS` — no ring boundaries (no shimmer), and blades vanish
while still resolvable (no sub-pixel far specks). Perf comes from the **radius + baked count**,
not from thinning the visible sward. The shell/ground texture carries beyond the turf
(`near_clear_r = TURF_REACH-9`, ramps in as the turf thins so there's no bare ring at the handoff).

Tuned 2026-07-01 after Chris's walk ("start reducing density sooner but keep going farther out;
easy to see where the dome ends"): **`TURF_NEAR_FULL` 9→5 m** (thin sooner), **`TURF_RADIUS`
14→20 m** (reach farther so the dome edge dissolves), **`TURF_BLADES` 8000→4000** (hold vertex cost
flat — tiles grow with R², so radius 14→20 nearly doubles tile count; the textured mat carries near
coverage at the lower density). **385 tiles × 4000 = ~9.2M tris** (perf-neutral vs the 197×8000
radius-14 build, +6 m reach). Levers for more fps: `TURF_RADIUS` / `TURF_BLADES`. Note: the bulk of
frame cost is elsewhere — F9 showed **6808 tree LOD0 shadow casters**; grass ≈ 9.2M of a ~17M-tri
total, and fps is ~47–51 (the trees, not grass, gate the path to 70).

Mat colour: `mat_tint`/`mat_bright` in `turf_tile.gdshader` tint the world-XZ grass photo into the
sward palette; lowered 2026-07-01 (Chris: straight-down mat too bright green) to `(0.72,0.98,0.60)`
× `0.82`.

**Pulse fix.** The old single grid's leading short edge sat inside the far-fade, so a new tile
row popped in at cover ~0.16 every ~2 m walked ("grass pulses ahead of me"). Fixed by the
**pop-free grid margin**: the grid extends a tile past `TURF_RADIUS`, and tiles whose nearest
blade is past the fade-out are skipped, so any tile entering the grid as the camera moves is
already collapsed (cover 0) — nothing appears/disappears abruptly.

**Textured ground mat (2026-07-01).** The horizontal backstop mat + thatch (flagged via
`UV2.x` in `_turf_vert`) are textured with `textures/grass_albedo.jpg` sampled by **true world
XZ** (`mat_tex` in `turf_tile.gdshader`, `mat_tex_scale`/`mat_tint`/`mat_bright` uniforms), so
straight down shows continuous grass detail between the standing blades — **no flat colour
pools** (the old `d1_down` defect). World-XZ sampling ⇒ seamless across overlapping tiles
regardless of per-tile yaw. Standing blades stay vertex-coloured.

Gated by `--no-blades`. Walk: `--park --pos "-464,1051,86,1.7" --time 13` (add `--pitch -88`
for the straight-down mat check).

## 1. System map

Three cooperating layers; color coherence comes from every layer including
`shaders/include/grass_zone_colors.gdshaderinc`.

| layer | files | range | role |
|---|---|---|---|
| Tier 0 blades + accents | `main.gd` `GRASS_TIER0`/`GRASS_ACCENTS`, `shaders/grass_particles.gdshader` (spawn), `grass_particle_render.gdshader` (draw) | 0–6 m | close-up blade variety, clover/dandelion (data-driven mode only) |
| Tier 1 geometry tufts | `main.gd` `GRASS_BIOMES`, same shaders | 0–60.5 m (dither fade from ~36 m) | near-field dense CLUMP geometry (~260 tris, `make_blade_mesh.py`), one mesh per biome |
| Card LOD tier | `main.gd` `GRASS_CARDS`, same shaders | 14–140 m (dither fade from ~84 m) | mid/far coverage: 3-crossed-quad cards (6 tris, `make_grass_card.py`) textured with the baked tuft silhouette (`Blade_*_card.png` alpha). **Added 2026-06-29** to kill the hard cutoff line where grass geometry stopped and the world became flat terrain albedo (cpw_001/002). |
| Terrain albedo | `shaders/terrain3d_override.gdshader` | everywhere | blends Terrain3D source 85% toward the grass color in grass zones — now only the dominant signal beyond ~140 m |

LOD crossfade: Tier-1 geometry tufts draw 0–60 m (fade from ~36 m); the card tier
draws 14–140 m (fade from ~84 m). They overlap 14–60 m so the tuft fade hands off
to full card coverage with no seam. Card `near_cull=14 m` keeps big flat cards
from rendering up close, where the geometry tufts own the band.

Dormant duplicates **removed 2026-06-28**: the Tier-2 static MultiMesh tuft
chunks (`grass_tuft_builder.gd`), the crossed-card cluster tier
(`grass_cluster_builder.gd`), and the `GPUGrass` compute GDExtension
(`gpu_grass/`, `shaders/grass_compute.glsl`) were all built, superseded by the
particle path, and never instantiated. Recoverable from git history. (The card
tier above revives the `grass_cluster_builder` crossed-quad *recipe* — 3 quads at
60° — inside the live GPUParticles path, not the retired static-chunk system.)

Spawn-side data: `landuse_map.png` (R8 8192², zone IDs) + canopy map. Both sampled in the
particle spawn shader and the terrain shader.

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

## 5. Definition of Done (this spec's work) — measured 2026-06-11

- [x] Zone re-truthing: heights/biomes/comments per §2–§3 tables; render-shader biome_id
      now a material uniform. Verified via new `--grass-highlight` CLI (the F4 toggle was
      driving the retired GPU-grass nodes — fixed): wild=blue inside Dene Slope, sedge=
      yellow on the Lake shore ring, lawn=red on mown turf.
- [x] Wear map generated (7.5% nonzero); terrain + blades respond (tuft tier dormant).
      Path-edge capture at (-715,1160): blades thin into the worn corridor, no
      green-on-dirt.
- [x] Sheep Meadow re-capture vs reference: mown read at eye level (no deep-field
      silhouette); brown-fraction metric degenerate (both ≈0.003 — reference mottle is
      value-variation within green, not literal brown), replaced by patch-contrast match:
      clean-turf normalized block contrast 0.080–0.157 vs reference 0.132, hue std 5.0 vs
      5.3 (hq_02-08 clean window).
- [x] Under-canopy capture at meadow edge: compacted dirt under crowns + dry margins,
      litter/dapple preserved.
- [x] No hard lattice reintroduced (visual: no axis-aligned edges at hero/treeline poses).
      NOTE: the finding-#2 "block ratio ≈1.24" target is superseded — wear mottle
      intentionally raises patch contrast to reference levels (p95/p5 1.55 with worn
      patches in frame; reference-amplitude criterion above is the binding one).
- [x] Perf gate ×5 (20260611_004804): 68/74/52/82/44 vs baseline 66/73/54/84/46 fps —
      +2/+1/−2/−2/−2, within documented gate variance (wear = 1 texture sample + ALU in
      latency-bound shaders). 3-of-5 pass status unchanged; ramble/NW remain the open
      policy decision from the perf sprint, not a turf regression.

## 6. Lawn brightness calibration — RESOLVED 2026-06-11

Saved protocol: `scripts/turf_luminance_check.py` (green-masked median display
luminance, fixed fractional boxes per image — replaces the ad-hoc 0.37/0.63
measurement, whose boxes weren't comparable). Re-measured targets: reference
clean turf luma **142–149/255, R/G 0.87–0.88 display** (hq_02-08 / hq_08-08);
game was **89/255, R/G 0.57**. Blade tier and terrain albedo agreed (86–110
across distance bands) — the whole chain was dark, not one tier.

Three measured components, all shipped (hero pose, `--cloud-seed=7` sweeps):

1. **`SUN_CAL = 3.0`** (day_night_cycle.gd): the sky calibration (rendering.md
   §6b) brightened the rendered sky ~1.2–1.5 stops but the DirectionalLight
   kept its keyframe energy — the missing stop was ground lighting, not
   albedo. Day-blended on sun_energy (night/dusk untouched, verified 21:00);
   cloud direct-sun term compensated (`sun_scale / sun_mult` — clouds.glsl
   multiplies LIGHT_ENERGY). Verified no sky shift: dark-cloud fraction flat
   across the sweep (16.8%→15.6%); sky median +10 = background mie term
   (physical sun-side haze). Direct:diffuse now ~4.9:1 (physical clear noon —
   reference's "very dark shadow pools" preserved; ambient untouched).
   Sweep knob: `--sun-cal=mult`.
2. **Thatch mix 0.22** (grass_zone_colors.gdshaderinc, mown zones only): a
   mown canopy is ~20–25% dead thatch + dried cut tips by optical cross-
   section — lifts red the way turf-canopy field spectra show vs single-leaf.
   This closed most of the chroma gap (R/G 0.68→0.81 at fixed sun). The
   spectral palettes stay pure live-leaf values.
3. **`turf_sheen = 0.6`** (main.gd global, `--turf-sheen` overrides): broad
   white cuticle specular (terrain SPECULAR 0.04→0.30, rough 0.65; blades
   matched via the same global so the 36–60 m fade ring stays invisible).
   The old terrain comment "grass has no specular sheen" was wrong.

Result (shipped defaults): **lawn luma 129/255 (reference band 126–149),
R/G 0.82 (reference 0.87), lawn/sky 0.49→0.67.** Times-of-day 8/13/17/19:30/21
visually verified; Literary Walk / Ramble / Bethesda collateral-checked (no
stone blow-out, shade readable). Perf gate 20260611_020824: 69/76/55/84/45 fps
vs prior 68/74/52/82/44 — all equal-or-better (sheen/thatch are ALU in
latency-bound shaders, per rendering.md §6.7).

Calibration anchor sanity (kept honest): game *trees* measure R/G 0.90 vs
reference 0.85 — no global camera-desaturation excuse; the turf chroma gap
was real. Side finding from the same measurement: **distant tree line is
~2.5× too bright** (luma ~130 vs reference 36–62 "dark mass") — the real
lawn≫treeline value relationship is inverted in game. Logged in
COMPARISON.md #5; belongs to the aerial-perspective/fog work, NOT turf.
Remaining minor gap: lawn B channel 74 vs reference 88 — likely the warm
noon `ambient_color` keyframe suppressing blue skylight; scene-wide
question, queued with the tree-line item.

## 6b. Dark blade-circle — RESOLVED 2026-06-11 (walk-around defect #2)

User walk-around (screenshots/cpw_005/007/009): near-field grass read as a
dark saturated circle following the player, soft arc boundary at tens of
meters. Measured at the cpw_005 pose (`--pos=-339.5,957.5,309.6 --pitch=-20`,
`--cloud-seed=7`, same-pixel A/B vs `--diag-hide=grass`): game near→far lawn
ramp **+18–22% luma** vs **+4%** in reference footage (hq_08-08 bands, R/G
flat 0.87–0.89). Two roots, both view-geometry dependent (hence "follows the
player"):

1. **Terrain Burley grazing retro-reflection** (~half the ramp): diffuse_burley
   brightens high-roughness ground toward grazing view angles; real turf
   self-shadows at grazing and stays flat. → `diffuse_lambert` on
   terrain3d_override + both grass shaders (commit 651af6a). Far grazing band
   −6.7%; specular measured innocent (≤0.9%/band, sheen unaffected).
2. **Engine backface-normal negation on the blade carpet** (the blade half):
   with `cull_disabled`, the renderer negates the geometric normal for
   backfacing fragments — half of all blade quads lit from BELOW
   (ground-hemisphere ambient, zero sun). Blade pixels −25..−40% vs the
   terrain they cover under ambient-only light (`--sun-cal=0.01` isolation).
   → `FRONT_FACING` pre-flip + card normals up-blended 0.7 toward world up +
   0.905 equalization trim (the blade chain's extras overshot once lighting
   was correct) (commit 12e7b7d).

Ruled out by measurement: volumetric fog ≤0.9%/band at <100m, turf_sheen
≤0.9%, SSAO/SSIL ~1.5% differential, native-texture leak in the spectral
blend ~2%, "SDFGI under-lights particles" (symptom of flipped normals).

**DoD (all pass):** blade-band vs terrain-only delta +0.4..+1.5% across all
distance bands at noon and 17:00 (target ≤5%); turf_luminance_check lawn
131.7/255 (band 126–149) — Lambert didn't break the §6 calibration; perf
gate 20260611_041200: 71/77/55/86/47 fps, all equal-or-better. Protocol
note: when measuring blade-vs-terrain, use whole-band means — a changed-pixel
classifier self-biases toward outliers as the tiers converge. User re-walk
pending.

## 7. Open / deferred

- True species mixes per CPC class ([grass conservancy data] memory) — palettes currently
  KBG/rye/fescue approximations; fine for now.
- Mow-stripe feature: real footage shows mottle, not stripes, on meadows — stripes stay
  sport-turf-only (`ground_surface.gdshader`).
- Wildflower meadow species models (zone 14) — post-sprint model program.
- GPU-grass GDExtension (`gpu_grass/`) is retired from the lawn path (2026-05-09
  unification); `_setup_gpu_grass()` and `_setup_grass_tuft_chunks()` are both
  never called. Grass coverage now extends to ~140 m via the card tier (added
  2026-06-29); beyond that the lawn is terrain albedo only.
- Card tier follow-ups (2026-06-29): (P2) near-field continuity — close the bright
  bare-ground gaps between geometry clumps + darken the under-grass terrain tone;
  (P3) shading depth — translucency, tip→base value gradient, sheen, per-clump hue
  variation, and kill the terrain triangulation banding. Perf gate not yet re-run
  with the +4 card layers (~360 K cards, ~196 extra GPUParticles nodes).
