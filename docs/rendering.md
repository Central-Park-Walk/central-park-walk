# Rendering — performance budgets and frame anatomy

Written 2026-06-09 from the D1–2 bisection (commits `06d3991`–`3ee9777`).
Companion docs: [`architecture.md`](architecture.md) (system map; its §7 hypotheses are now measured here), [`workflow.md`](workflow.md) (Definition of Done).

**Hard target ([`vision.md`](vision.md)): 16.6 ms/frame (60 fps) at 1920×1080 on RTX 3060 Ti** at the open locations (literary_walk, bethesda, great_lawn); **deep woodland (ramble, north_woods) floor is 22.2 ms (45 fps)** — user decision 2026-06-11, recorded in vision.md. 60 stays the aspiration everywhere.

## 1. How we measure

- `scripts/perf_gate.sh` — pass/fail at the 5 locations. The gate for any perf-relevant change.
- `scripts/perf_bisect.sh <location> [label=hides ...]` — per-subsystem attribution via `--diag-hide=` (terrain trees undergrowth grass shadows sdfgi fog ssao ssil glow treeshadows) and raw knobs (`--shadow-dist=`, `--shadow-size=`).
- Protocol: 1080p, vsync off, noon/clear/summer, stationary, 60 s/run, stats from the last 10 `[PERF]` samples (2 s cadence). Scene load is ~35 s — runs shorter than ~50 s produce zero samples. **fps is median; ms columns are means** and include spikes (see §5 floor anomaly). Never touch a measurement window (`overlay=ON` marks the run contaminated).
- `[PERF]` fields: `process` = main-loop ms (includes main thread blocked on GPU), `sub` = our profiled GDScript, `vpcpu`/`vpgpu` = `viewport_get_measured_render_time` CPU/GPU ms, `pmax`/`pspk` = worst TIME_PROCESS + count >8 ms per 2 s window, `dmax`/`dspk` = same from `_process` delta (true wall dt — trust these for frame pacing). `[SPIKE]` lines timestamp any frame >50 ms.
- **TIME_PROCESS caveat (measured 2026-06-10, §5):** at >100 fps the `process` column reads the *worst* recent frames, not the typical one — real frame time is `1000 / median fps`. At ≤60 fps the two agree.

## 2. The headline finding: we are GPU-bound

At every heavy location, `vpgpu` ≈ `process` while `vpcpu` ≈ 8–9 ms and our GDScript `sub` < 1 ms. The May conclusion "bottleneck is CPU process time" misread `TIME_PROCESS` — it counts the main thread *waiting for the GPU*. Consequences:

- MMI-consolidation / per-frame-GDScript work is **not** the lever. Raster load is.
- Any fix must move `vpgpu`, and is verified by `vpgpu` at ramble + north_woods.

## 3. Measured attribution (2026-06-09)

Mean ms over last 10 samples; Δ vs. that location's baseline. Reports in `perf_reports/20260609_*`.

| config | ramble ms (fps) | north_woods ms (fps) | reading |
|---|---|---|---|
| baseline | 83.1 (12) | 87.5 (11) | vpgpu 82.2 / 84.6 — GPU-bound |
| trees hidden | 25.9 (56) | 33.4 (40) | trees own ~57 / ~54 ms |
| tree shadow casting off (trees visible) | 65.2 (17) | 59.9 (18) | tree→cascade raster: **18 / 28 ms** |
| all shadows off | 45.9 (25) | 38.5 (27) | shadow system total: 37 / 49 ms |
| shadows+trees off (union) | 20.7 (78) | 28.3 (54) | tree camera raster ≈ **25 / 10 ms** |
| SDFGI off | −6.7 | −4.0 | |
| grass off | −7.1 | −5.9 | camera raster only (grass never casts) |
| terrain hidden | −4.2 | −3.7 | camera raster; terrain also casts (in "other shadows") |
| fog / undergrowth / post(ssao,ssil,glow) off | ~0 | ~0 | within run noise |
| everything off (floor) | 16.0 mean / ~3.4 typ (294) | 18.5 mean / ~3.1 typ (318) | spiky floor — see §5 |
| shadow atlas 8192→4096 | — | −32 | fragment-bound share |
| atlas 4096→2048 | — | ~0 | remainder is vertex/primitive-bound |
| shadow distance 150→75 m | — | ~0 | caster load is already near-field |
| terrain casting off | −8.7 | — | fragment-bound (only ~0.4 M of 18.5 M shadow tris, but full-cascade coverage) |
| PCF filter quality 2→1 (or →0) | −16 | — | penumbra blocker-search cost (1.5° angular distance); q1 ≈ q0 cost |
| tree+terrain casting off | −26.2 | — | filter sampling cost remains |

The shadow system thus splits (Ramble, non-additive): tree casters ~18, terrain caster ~9, PCF sampling ~16.

**Water-caster correction (2026-06-10, commit 5524126):** every shadow
measurement above was taken while `WaterBodies` — one park-wide 3.1 M-tri
surface mesh — cast into every cascade (~12.4 M shtri at every location;
found via `--shadow-census` at Great Lawn). Water now casts nothing. The
per-line *deltas* above remain valid A/Bs, but absolute shtri figures
(e.g. "17.4 M at Great Lawn") were mostly water: post-fix Great Lawn is
5.97 M without proxies, **1.91 M with proxies** (trees.md §3 DoD item 1).

### 3b. Re-measured anatomy at Ramble (2026-06-10 PM, shipped defaults: proxies + atlas 4096, commit 003ee04)

All four June-9 structural assumptions changed in one day (impostor tier
unburied, water caster removed, proxies shipped, atlas 4096), so the table
above is historical. Fresh back-to-back runs at ramble noon, 52 ms frame:

| config | ms | reading |
|---|---|---|
| baseline (shipped defaults) | 52.0 | vpgpu 51.9, shtri 2.35 M |
| `--tier-isolate=mesh` (impostors off) | 51.7 | **impostor raster ≈ 0** (only 650 visible tris at Ramble — canopy occludes the distance) |
| `--diag-hide=proxyshadows` (no tree shadows) | 28.3 | tree-shadow system total ≈ **24 ms** |
| `--proxy-solid` (no dapple discard) | 49.8 | dapple shader ≈ 2 ms — innocent |
| `--no-tree-shadow-proxy` (per-leaf casting) | 62.0 | proxies save **−10 ms** vs the old world (shtri 12.9 M vs 0.42 M) |
| `--shadow-filter=1` | 44.7 | q2 penumbra search ≈ 7 ms at noon |
| `--diag-hide=trees` (visible trees hidden) | 15.9 | mesh-tier camera raster ≈ **30 ms** — the biggest single line |

Reading: the ~24 ms tree-shadow cost is NOT caster triangle load (0.42 M
tris) — it is dominated by receiver-side PCF over canopy-filled shadow maps
(sampling + q2 blocker search; empty maps early-out and sample coherently).
Levers must attack receiver cost (filter quality, shadow distance, cascade
content), not caster geometry — proxies already took the caster win.

**D5–9 priority order at Ramble: (1) mesh-tier camera raster ~30 ms
(occlusion culling, tier boundary, tri audit), (2) shadow receiver cost
~24 ms gross. Everything else combined is ~13 ms and within run noise.**

**Bisect protocol warning (measured 2026-06-10):** `perf_bisect.sh` runs its
baseline first on a cold GPU; configs 10+ minutes later read 4–8 ms slower
from thermal drift alone (fog/undergrowth/terrain "regressions" in run
20260610_140325 are artifacts). Single-run deltas under ~8 ms are not
actionable — confirm with back-to-back A/B runs. North Woods re-measure
still pending (expected to mirror Ramble).

### 3c. Opaque-pass leaf fix (2026-06-10 evening) — §3b's "mesh-tier raster" mostly dissolved

The ~30 ms "mesh-tier camera raster" line in §3b was mostly **transparent-
pass overdraw**: tree_leaf.gdshader wrote `ALPHA` (+ `alpha_to_coverage`,
inert with MSAA off), so every canopy layer shaded full PBR + SSS + noise +
shadow-PCF with no early-Z. Leaves now render opaque, coverage by discard
(commit f12f334, full record trees.md §4e). Gate 20260610_171918 vs the
§3b-era 20260610_135252 baseline:

| location | was | now |
|---|---|---|
| literary_walk | 30.8 | 26.3 |
| bethesda | 21.3 | 24.1 → back-to-back sandwich says **no regression** (new 23.8 / old 25.6 / new 23.7; the 21.3 was a favorable run) |
| ramble | 52.1 | **31.1** |
| great_lawn | 20.4 | 20.9 |
| north_woods | 50.3 | **32.4** |

Consequences for the plan:
- Grass/undergrowth transparency ruled out by measurement (§6 item 5) —
  ALPHA_HASH_SCALE is already the opaque hashed pipeline; tree_leaf's
  plain-ALPHA+A2C was the lone defect.
- Tier pull-in and occlusion culling are DEAD levers (measured ~3 ms for
  impostors-at-120 m — distant mesh trees were never the cost).

### 3d. Post-opaque attribution at Ramble (2026-06-10 evening, report 20260610_175940)

| config | ms (fps) | reading |
|---|---|---|
| baseline | 29.4 (36) | vpgpu 28.7, vistri 13.42 M |
| shadows off | 25.3 | shadow system now ≈ **7** (was ~24 gross — opaque leaves slashed PCF receiver work) |
| SDFGI off | 28.0 → vpgpu −4.7 | SDFGI ≈ 5 |
| grass off | 24.7 | grass ≈ **6.6** (5.5 M of the 13.4 M vistri) |
| trees off | 18.8 | trees total ≈ **14.1** — still the biggest line; with shading now ~once per pixel this is mostly **vertex/LOD load** (the un-decimated 153–203 k bark meshes, trees.md §4b) |
| floor (all off) | 10.0 mean (vpgpu 4.5) | §5 spikes still open |

**D5–9 next levers, in measured order: (1) LOD regeneration (trees.md §4c
lever 3 — true mid-LOD via bark decimation + card prune, Blender-mechanical,
spec'd); (2) shadow receiver ~7 + SDFGI ~5 sweeps; (3) grass tier/density
~6.6; (4) floor spikes/cloud compute (§5). Gap to 16.6 ms at ramble:
~13 ms.**

### 3e. Post-LOD-regen attribution at Ramble (2026-06-10 late, report 20260610_212106, sandwich baselines)

| config | ms (fps) | Δ | reading |
|---|---|---|---|
| baseline | 28.3 (38) | | vistri 11.71 M, shtri 2.34 M |
| baseline2 (end of matrix) | 30.3 (38) | | thermal drift ~2 ms — deltas under that are noise |
| notrees | 19.6 (61) | **8.7** | still #1 — canopy *fragment shading* (LOD regen barely moved it) |
| nograss | 22.2 (53) | **6.1** | 5.5 M of the vistri |
| noshadow | 23.7 (47) | **4.6** | receiver-side PCF, post-proxy |
| nosdfgi | 27.5 (40) | **0.8 — collapsed** | vpgpu identical (24.5 vs 24.7); the old ~5 ms reading predates opaque leaves + LOD regen. SDFGI sweep is a dead lever. |
| floor | 10.6 process / **3.3 real** (314) | | §5: process column is a worst-frame proxy at high fps |

Attribution closes: 8.7 + 6.1 + 4.6 + 0.8 + 3.3 ≈ 23.5 vs 26.3 real
(1000/38). Remaining levers by size: trees-fragment ~8.7, grass ~6.1,
shadow receiver ~4.6. Real gap to 16.6 at ramble: ~9.7 ms.

**Stacked candidate state** (2026-06-10, commit d8f1784, solid-hull proxies):

| stack | ramble ms (fps) | north_woods ms (fps) |
|---|---|---|
| + tree shadow proxies | 67.0 (16) | 64.7 (16) |
| + furniture casting off | 66.4 (15) | — |
| + PCF filter 1 | 52.7 (20) | — |
| + atlas 4096 (full stack) | **49.2 (22)** | **45.5 (23)** |

Furniture casting off bought ~0 despite the census's 8.4 M caster tris — the 150 m shadow distance already culls most of it from the cascades. **Furniture keeps its shadows.** (Census tool: `--shadow-census`, dumps top node-level casters.)

### 3f. Turf-dome perf pass at Bethesda (2026-07-01 night, reports 20260701_225053 → 20260701_232728)

The 2026-06-29 mystery (`vpgpu` ≪ `process`, a large "CPU-side" cost the viewport
measure missed) is **RESOLVED**: it was the water-reflection SubViewport re-rendering
the turf dome. `viewport_get_measured_render_time` only reads the MAIN viewport;
the mirror's GPU time surfaces as main-thread wait inside `process`. And blade
VERTEX work doesn't shrink with the mirror's 1/3 resolution, so the mirror re-paid
nearly the dome's full ~12 M-invocation bill every frame.

Opening attribution (32 fps / 33.1 ms, sandwich clean):

| config | ms (fps) | Δ | reading |
|---|---|---|---|
| baseline | 33.1 (32) | | vpgpu 21.3, vistri 14.2 M (dome = 10.4 M) |
| nograss (incl. dome — diag fixed this session) | 12.1 (101) | **~21** | THE frame |
| norefl (`--no-water-reflection`) | 22.1 (49) | **~11** | mostly the dome again, in the mirror |
| noshadow | 29.8 (36) | 3.3 | fine |
| notreeshadows | 31.9 (33) | ~1 | **the "6808 LOD0 shadow casters" HUD line was mislabeled** — it printed the park-wide LOD0 instance count. Tree shadows were never the gate. |
| nosdfgi | 32.8 (34) | ~0 | still dead |

Shipped fixes — all **visually neutral** (A/B pixel-diff at the standard grass pose ==
the wind-phase run-to-run noise floor; sward eyeballed intact):

1. **Dome out of the mirror** (`TurfTiles.layers = 8`, the terrain policy) — the
   reflection now costs ~2 ms gross (its §4 line).
2. **Dead-blade early-out** in `turf_tile.gdshader` vertex(): rank-collapsed blades
   skip the terrain/landuse fetches; the tile mesh is emitted in RANK ORDER so dead
   blades are index-contiguous and warps exit coherently.
3. **Altitude fade via `cam_alt` uniform** (camera ground clearance, CPU, once per
   frame) instead of a per-vertex `sample_terrain`.
4. **Indexed tile mesh** (`st.index()`): 18 emitted verts per 6-tri blade dedup to
   ~8 unique — the post-transform cache skips the rest. Biggest single win.

The dome measured **vertex-bound**: cost linear in `--turf-blades`, flat under
internal-res halving (sweep 20260701_232042). Sweep knobs `--turf-blades=N` /
`--turf-radius=R` are permanent. **Result: Bethesda 33.1 → 16.6 ms (32 → 69–70 fps)
with identical visuals**; grass residual ~5 ms, reflection residual ~2 ms. If more
is ever needed: `--turf-blades=2000` measured 64 fps pre-indexing (visible density
cut — user call), and the mirror could update at half rate.

### 3g. Literary Walk — the one gate failure (2026-07-01 night, reports 20260701_233915 / 234753)

Post-dome-pass gate (20260701_233341): bethesda 70 / ramble 73 / great_lawn 74 /
north_woods 74 — **all PASS, woodland now clears the 60 aspiration** — but
literary_walk 43 (was 66 in the June canonical gate). Bisect at the Mall:

| lever | ms (fps) | reading |
|---|---|---|
| baseline | 25.0 (43) | shtri **5.42 M** (vs 1.83 at bethesda) — the elm corridor casts per-leaf |
| notrees | 17.5 (68) | visible tree raster ~7.5 |
| noshadow | 18.1 (68) | shadows ~6.9 |
| notreeshadows | 19.3 (62) | **tree casting ~5.5 — the lever** (shtri → 1.79 M) |
| norefl | 20.9 (54) | mirror ~4.1: full elm-corridor re-render for a Pond ~150 m away |
| nograss | 20.1 (56) | grass residual ~4.9 |
| `--shadow-dist=100` | 26.7 (50) | **dead** — casters are near-field |

Shipped: **distance-staged mirror rate** (water_reflection.gd: every frame ≤60 m
from a body, every 2nd to 140 m, every 4th to the 250 m sleep; UPDATE_ONCE per Nth
frame, camera tracks every frame, no pop) → literary_walk 43 → **51 fps**. Verify
in motion on a walk: reflection lag only exists ≥60 m from water where the surface
is a few grazing pixels.

**Remaining gap at literary_walk ≈ 3 ms = tree shadow casting (5.5 ms measured).**
Per-leaf casting came back when the shadow proxy was defaulted OFF (2026-06-28
crown-flip fix, trees.md); the Mall's elm density is where that trade bites.
Candidate next levers, in order: `Mesh.shadow_mesh` (decimated caster mesh on the
lod0 trees — keeps the self-shadow-consistency that fixed the flip, cuts cascade
raster; needs care with the LOD-dither shadow pass), or revisiting proxies with
leaf shadow-receive disabled. A tree-pipeline session, not a knob.

**★ RESOLVED 2026-07-02 (deep-forest perf push).** Confirmed on the GPU (`perfab`
launcher + `[PERF]` log's `shtri`/`vpgpu`/`mrgpu`) that per-leaf tree shadows were the
dominant deep-forest cost, far above the 5.5 ms at literary_walk: in the all-london-plane
forest, visible trees generated **37.7 M shadow tris** (2.5× the 15 M seen) and the
water mirror re-rendered them again; `--diag-hide=treeshadows` → fps 15→27, shtri
37.7 M→1.76 M. Fix = **shadow proxy restored to default ON** (chosen over `Mesh.shadow_mesh`;
the deeper rebaked impostor mitigates the 06-28 flip). Result ~38-39 fps deep Ramble,
worst-case density. (NOTE 2026-07-03: the `_lod1` mid tier — briefly used as the default
near tier for a perf win — was removed; the near tier is now the full lod0 mesh to ~80 m
(solid to 40, dither to impostor by 80), so deep-woods fps needs a re-measure. See
[`trees.md`](trees.md) §1 perf note.) **SDFGI verdict revised:** the old "dead
lever" reading was wrong — SDFGI is not dead, it actively darkens dense canopy to BLACK
(`sdfgi_use_occlusion` drives its sky-ambient to ~0 under the canopy, ×the leaf shader's
0.12 crown-interior AO). It costs ~2 fps + ~512 MB VRAM; kept ON by Chris's preference
for the moody eye-level look (F2 toggle, F8 = occlusion, `--no-sdfgi`). Full record:
[[project_performance_investigation]].

### 3h. Cherry Hill water report — mirror attribution + motion-aware idle rate (2026-07-02, commit a1590ea)

Chris (screenshots cpw_003/4): standing at Cherry Hill (-552, 959), facing the
Lake 40 fps, turned away 87. Bisect at that pose (yaw −62.6, `--time=16`,
stationary, reports 20260702_051711 / 052439):

| config | ms (fps) | reading |
|---|---|---|
| no-reflection | 13.7 (73) | ceiling; deltas below are within one warm batch |
| idle-staged (shipped default) | 14.7 (68) | mirror ~1.0 residual (every-4th-frame render) |
| full-rate mirror (old behaviour) | 15.9 (63) | mirror ~2.2 at the shore |
| shadows off (earlier batch) | mrgpu 3.0→1.6 | **~half the mirror is its own directional-cascade re-render** — cascades refit per camera; Godot 4.6 has no per-viewport shadow disable, so this share only yields via update rate |

New attribution (permanent): `[PERF]` prints `mrgpu/mrtri/mrshtri` via
`viewport_set_measure_render_time` on the mirror SubViewport (its GPU time is
invisible to the main viewport's numbers, §3f — this closes that hole for good);
the F9 HUD shows a "Water mirror: X ms GPU, Y tris, 1/N rate" line;
`perf_bisect.sh` reports `mrgpu/mrtri` columns.

**Motion-aware idle rate (shipped):** if the camera has drifted < 2 cm / 0.03°
since the mirror's LAST RENDER, interval = max(distance-staged, 4). Motion
restores the staged cadence the same frame (shore = renders that frame, no stale
first look). Drift is measured against the last-render pose, not per-frame
deltas, so slow pans accumulate to the threshold instead of slipping under an
epsilon forever. Wave distortion runs in water.gdshader at full rate — only tree
sway and cloud drift update at ~15 Hz in the mirrored image. A/B water crops
pixel-identical (tmp/refl_{idle,full}_ab.png).

Flags: `--refl-full-rate` (diag: defeat idle staging — the moving-at-shore worst
case), `--refl-half-rate` (walk experiment: doubles staged intervals, shore
renders every 2nd frame while moving, worth another ~1.1 ms — promote to default
if reflection lag is invisible on a Lake-shore walk).

**Tested & rejected — per-camera cull_mask to strip tree shadows from the mirror
(2026-07-03).** The mirror re-renders a full directional shadow pass: at a forested
shore (Azalea Pond, `--pos=-389,653,105`) `mrshtri` = **1.58 M** shadow tris, mirror
GPU ~5 ms — nearly the main view's own 1.86 M. Godot *does* gate shadow raster by the
rendering camera's `cull_mask` (godot #98231; verified here — moving the SHADOWS_ONLY
tree proxies off layer 1 dropped mirror `mrshtri` by exactly their contribution while
main `shtri` held), so the layer trick is a real per-viewport lever. **But it's
worthless here:** the proxies are only ~76 k tris (~5 % of the mirror's shadow load —
turning proxy casting fully off drops *main* `shtri` by the same 76 k, confirming they're
a minor caster). The mirror's remaining ~1.4 M shadow tris come from the **visible
reflected casters** — `TreeImpostor_*` (cast ON) plus bridges/undergrowth — which can't
be layer-excluded without deleting them from the reflection itself. `shadow_caster_mask`
(4.4+) is per-*light* and global, so it can't isolate the mirror either. **Conclusion
stands: no clean per-viewport directional-shadow suppression exists; the mirror's shadow
share only yields to update-rate reduction** (idle/distance staging, 30 m sleep — all
shipped). Do not re-attempt the layer trick. Raw logs: `tmp/perf_{base_azalea,proxy_layer,proxyoff}.log`.

⚠ Protocol notes: (1) stationary gate/bisect runs now measure the IDLE-rate
mirror; use `--refl-full-rate` to measure the moving case. (2) Cross-batch fps
comparisons drift several fps (first run of a cold session reads low — shader/
pipeline caches); trust within-batch deltas. (3) A `--pos` spawn at cherry_lake
renders far fewer trees than Chris's walked-in session (his 16.6M HUD triangles
vs ~8M global here; the Lake-shore tree field is visibly missing) — absolute ms
at this location understate the live-session load, mirror included. The HUD
mirror line reads the truth in-session.

### 3i. Mirror reprojection — "reflections popping at normal walk" (2026-07-02)

Chris's walk after §3h found reflections **popping** during ordinary walking.
Two causes, both fixed:

1. **Screen-anchored sampling of a stale mirror.** water.gdshader sampled the
   mirror at `(1-SCREEN_UV.x, SCREEN_UV.y)` — correct only on the frame the
   mirror rendered. Any staged/idle skip composited a frames-old image as if
   rendered from the CURRENT camera, so each sparse update snapped the
   reflection by the accumulated camera motion (worst under mouse-look: degrees
   per update at 15 Hz). Fix: water_reflection.gd pushes the mirror camera's
   view-projection (`planar_mirror_vp`) on every render; the shader reprojects
   each water fragment's world position through it. Stale frames stay
   world-anchored — only reflected CONTENT (tree sway, clouds) updates
   sparsely, which is what §3h assumed all along. Gotcha: the GDScript-side
   `Projection` is GL-style (NDC y-up); the viewport texture is top-left
   v-down, so the shader flips y (`-refl_clip.y`) — unlike the in-shader
   `PROJECTION_MATRIX`, which has the Vulkan flip baked in. The x-flip falls
   out of the mirror basis's negated X.
2. **Idle misfiring during locomotion.** Walking pace at 60–90 fps is
   1.3–2 cm/frame — right at `IDLE_POS_EPS` (2 cm). The frame after each
   render read as "still" → alternating fresh/stale mirror at half rate while
   walking straight at the shore. Idle now also requires the per-frame delta
   under a much tighter `FRAME_*_EPS` (2 mm / 0.01°): real locomotion never
   idles; sub-eps drift still idles and is reprojection-anchored anyway.

Also: waking from the >250 m sleep now renders immediately (explicit `_asleep`
flag — `UPDATE_ONCE` self-resets to `DISABLED`, so the mode can't distinguish
"asleep" from "between staged renders"), and the frozen last image stays
world-anchored while asleep instead of dragging with the camera.

Verified (Cherry Hill `--pos=-552,959,-62.6`, time 16, cloud-seed 1): (a)
fresh-frame equivalence — stationary A/B vs pre-change baseline, water-crop
mean |Δ| 7.98 vs ~5 run-to-run floor (a y-flip variant read 21.4 and lost the
cloud reflections — the flip test is sensitive); (b) world-anchoring —
`--refl-freeze` (new diag: render once, then freeze) + 5.5 m walk-bot run:
frozen-mirror frames match a live-mirror run within noise, boathouse/far-shore
reflection bands pixel-aligned. Captures in tmp/refl_*.

Follow-up: with reprojection, staleness is far less visible — `--refl-half-rate`
(and possibly longer idle intervals) may now be promotable; needs a fresh Chris
shore walk on defaults first.

## 4. The frame budget (binding)

GPU ms at 1080p, measured at the worst of the 5 locations. A subsystem over its line is a regression even if total fps passes (headroom is for weather/seasons, not for spending). Per `architecture.md` §9, new subsystems must name their budget line.

| line | budget (ms) | measured (worst, 2026-07-01 §3f/3g unless noted) | gap |
|---|---|---|---|
| sky + volumetric clouds | 1.0 | inside floor (§5) | ok |
| Terrain3D camera raster | 1.5 | ~4 (2026-06-09) | −2.5 |
| trees — camera raster | 4.0 | ~7.5 (literary_walk) | −3.5 |
| trees — shadow casting (proxies restored default-ON 2026-07-02, §3g ★RESOLVED; deep-forest shtri 37.7M→1.76M) | 1.0 | ~5.5 was the per-leaf cost with proxies OFF (2026-07-01, stale) | re-measure with proxies on + post-lod1-removal near band |
| other shadow casting + sampling | 2.5 | ~1.4 (bethesda all-shadows 3.3 minus tree share) | ok |
| SDFGI | 1.5 | ~0 | ok |
| volumetric fog | 1.0 | ~0 | ok |
| grass (dome + terrain, camera) | 1.5 | ~5 | −3.5 (vertex-bound; lever = `--turf-blades`, a look trade) |
| undergrowth + ground cover | 0.5 | <1 | ok |
| post (SSAO, SSIL, glow, TAA, tonemap) | 1.5 | ~1 (TAA untested) | ok? |
| water, weather particles, misc | 0.6 | <1 | ok |
| water planar reflection (near water only; staged rate + >250 m sleep §3g; idle rate §3h; reprojection §3i) | 1.5 | ~2.2 at the shore moving, ~1.0 standing (idle-staged) | ok (accepted; §3i may unlock half-rate) |
| **total** | **16.6** | 14.2–16.6 at 4 locations; ~19.5 literary_walk (driven by the stale per-leaf shadow line — table wants a full re-measure post proxy-restore + lod1 removal) | |

CPU is not currently binding (`vpcpu` ~9 ms peak, GDScript <1 ms) but inherits the same 16.6 ms ceiling.

## 5. Floor anomaly — RESOLVED 2026-06-10: measurement artifact, no real stalls

Frame-tail instrumentation (`pmax`/`pspk` from TIME_PROCESS, `dmax`/`dspk`
from `_process` delta, `[SPIKE]` stall locator — commits 2ad3e0d, and the
delta follow-up) settled it:

- **Real frame pacing at the floor is clean.** Wall dt: 3.3 ms typical,
  window max 6–9 ms, ~0 frames over 8 ms per 2 s window. There are no
  periodic stalls. Cloud compute measured innocent too (floor with
  `--diag-hide=clouds`: identical).
- **The "16–18 ms floor mean" was TIME_PROCESS itself.** At high fps the
  monitor reads 8–9 ms while true dt is 3.3 ms — empirically it tracks the
  *worst* recent frames, not the last frame. At low fps (heavy locations) it
  converges to real frame time, so historical A/B deltas stand.
- A 2.2 s **scene-load frame** leaks into the early sample windows; 60 s
  runs keep load inside the "last 10 samples" tail. That produced the
  earlier pmax=2210 reading.

**Protocol consequences (binding):** real frame time = `1000 / median fps`,
not the process column. Treat `process` as a worst-frame proxy at >100 fps.
The true floor is ~3.3 ms (vpgpu ~2), so the §4 budget's available pool is
larger than the old floor reading implied.

## 6. Reduction plan (D5–9, in order of measured size)

1. **Tree shadow proxies** (−13..16 vs post-impostor-fix world) — **SHIPPED, default ON 2026-06-10** (tree_builder.gd, opt-out `--no-tree-shadow-proxy`): trunk cylinder + crown lathe fit to each variant's leaf vertices (12 slices, p96 elliptical radii), `SHADOWS_ONLY`, GI off, phenology-driven dapple discard (shaders/tree_shadow_proxy.gdshader — thins in autumn, bare in winter, blossoms cast). Full DoD record in trees.md §3.
2. **Tree camera raster — RESOLVED 2026-06-10** (−21 at ramble, −18 at north_woods): the cost was transparent-pass leaf overdraw, not geometry (§3c, trees.md §4e). The spec'd follow-ups occlusion-culling/tier-boundary were measured dead (~3 ms); LOD regeneration (true mid-LOD: bark decimate + card prune, trees.md §4c lever 3) remains queued for the residual vertex load.
   **LOD regen SHIPPED 2026-06-10 late (trees.md §4f): −1 to −3.3 ms per location, NOT the estimated 13–16.** New canonical gate (20260610_203758, commit 0cc6d1a): **25.3 / 22.1 / 27.8 / 18.9 / 32.3 ms** (lit_walk / bethesda / ramble / great_lawn / north_woods) — the D5–9 baseline. The §3d "trees ≈ 14.1 ms mostly vertex/LOD load" attribution was WRONG: with leaves opaque, the remaining tree line is canopy *fragment shading* (per-pixel PBR + SSS + shadow receive), which geometry LOD cannot reduce. Remaining tree levers are per-pixel: bark shader gating (§4c lever 2), leaf shader cost, shadow-receive sampling. Re-attribute (trees-off A/B at ramble/north_woods) before picking the next lever.
3. **Other shadows — DECIDED 2026-06-10** (re-measured post-proxy/post-water; the old −16/−32 deltas no longer exist because the shadow load they amplified is gone): **atlas 4096 is the default** (−3.4 ms at Ramble 17:00, visually neutral at Ramble + Literary Walk golden hour — if anything slightly softer, which suits the tone). **PCF filter stays quality 2**: filter 1 now saves only ~5 ms and visibly hardens the long-shadow penumbra at low sun — and the proxy dapple *depends* on PCF blur to read as mottle (its holes sharpen into cut-outs at quality 1). Terrain caster (−9 pre-fix) not retested — candidate for D5–9 with a golden-hour visual check.
4. **SDFGI — DEAD LEVER (measured 2026-06-10, §3e):** 0.8 ms at ramble post-opaque-leaves/post-LOD-regen (vpgpu identical with it off). The −5.5 reading was from the old transparent-canopy world. No sweep needed; settings stay 6 cascades @ 0.5 m.
5. **Grass** (−6.1, §3e): transparency ruled OUT 2026-06-10 — grass/tuft/undergrowth write `ALPHA_HASH_SCALE`, which keeps them in the opaque hashed pipeline (measured: discard-only variant within noise at great_lawn 20.2→19.7 and ramble 29.8→29.4; trees were the lone transparent-pass defect because tree_leaf wrote plain ALPHA + inert A2C). Remaining grass cost is honest geometry.
   **Density/range sweep (2026-06-10 late, report 20260610_213900):** half density (`--grass-spacing-mult=1.41`) = **−3.6 ms real** at ramble (38→44 fps, vistri −3.2 M); range cut (`--grass-grid-mult=0.7`) = **~0 — dead** (cost is near-field density, not distant coverage); both ≈ density alone. Density cut NOT shipped blind — the Sheep Meadow comparison flags turf as "tall uniform blades vs real mown mottled texture," so the cut ships with the turf re-look (screenshot A/B first; if subtle at eye height, ship now and fold the look change into D9–12).
6. **Floor spikes — RESOLVED, measurement artifact (§5).**
7. **Shader-body ALU gates — MEASURED DEAD 2026-06-10** (trees.md §4g): canopy/bark fragment work is texture/PCF *latency*-bound; skipping procedural noise frees nothing. Corollary: ALU visual richness in those shaders is ~free.
8. **Shadow cascade knobs — MEASURED DEAD 2026-06-10** (report 20260610_220421): `--shadow-splits=2` regresses (each split rasterizes more atlas area); `--shadow-blend=0` within a drifting matrix's noise. Receiver cost does not yield without breaking the PCF-q2/dapple policy.
9. **FSR2 upscaling — SHIPPED default 2026-06-10 (commit 1366702): `fsr2 @ 0.77` internal scale, −4.6 ms real at north_woods (38→46 fps); 0.85 = −2.5 (report 20260610_222030, clean sandwich).** Visual DoD passed: 1:1 still crops (canopy/sky edges, grass blades, trunks) near-pixel-identical to native; walk-motion frames show no ghost trails or smear (dense moving foliage is FSR2's worst case — checked specifically). Output stays 1080p. `--upscale=off` = native; `--upscale=mode:scale` overrides.

**Canonical gate after this session (20260610_223349, commit 1366702):
literary_walk 66 / bethesda 73 / great_lawn 84 fps — PASS; ramble 54
(−1.9 ms short), north_woods 46 (−5.1 ms short).** Session start was
40/45/53/36/31. Remaining measured pools at NW (real ms): trees ~7,
shadows ~6, grass ~3.6, floor ~3.3 — all resistant within current visual
policy (§6.4/6.7/6.8, trees.md §4g). Closing the last 5 ms at NW likely
requires a policy-level trade (deeper internal scale, grass step 2,
shadow-distance cut) — surface to the user before taking any of them.

**★ CANONICAL GATE 2026-07-01 (20260701_235245, turf-dome + mirror pass, §3f/§3g):
literary_walk 51 / bethesda 72 / ramble 73 / great_lawn 79 / north_woods 78.**
Four of five PASS — deep woodland now clears the 60 aspiration, not just its 45
floor. All of it visually neutral (A/B'd). The one FAIL, literary_walk, is ~3 ms
short with tree shadow casting (5.5 ms, per-leaf since proxies went off) as the
measured lever — see §3g for candidates. The June-10 numbers above predate the
grass overhaul, sky work, and water reflection; this gate supersedes them.

Every step: perf_gate before/after at all 5 locations, committed with the numbers in the message.

## 6b. Sky calibration (2026-06-10/11 — D9–12 item 1, "dark storm noon" fixed)

The Sheep Meadow comparison's #1 finding (clear noon renders as dark storm
overcast, sky 48–78/255 vs real ~200) had two roots, both fixed:

1. **Weather map had no clear sky in it.** The stock demo `weather.bmp`
   coverage channel (B) was mid-gray noise — 94% of texels >0.3, zero
   texels at 0 — so `cloud_coverage × weather.b` was non-zero across the
   whole dome and the Schneider threshold remap produced one giant
   connected slab at ANY coverage setting. Replaced by
   `scripts/gen_weather_map.py`: discrete fair-weather cumulus cells
   (lognormal 0.35–1.8 km radii, 2.1 km jittered grid, cloud-street
   anisotropy, 5–10 km patchiness, 67% true zeros, 0.32 areal coverage).
   NOAA monthly coverage (day_night_cycle) remains the global scale.
2. **Both sky and clouds sat 1.2–1.5 stops under reference** beneath our
   AgX pipeline (the upstream `/50` LUT convention assumed a different
   exposure). Calibrated by measured sweep at noon-clear (`--cloud-seed`
   fixes the field; `--sky-cal=bg:sun:amb` overrides): **background ×5,
   cloud direct-sun ×20, cloud ambient ×6** → blue zenith 127 / mid-dome
   144 sRGB (real 120–160), cumulus bodies p50 ~192 with shaded bases
   intact (×40/×8 went flat-white, rejected).
3. **The multipliers are day-blended on `sun_energy`** (NOT sun pitch — the
   keyframes repurpose the light as a high moon at night): full by day,
   1.0 at night. Verified endpoints: 22:00 sky median 51 (matches the ×1
   baseline), noon 144. 8:00/17:00/19:30 visually verified.

Gotchas embedded: editing `clouds.glsl` requires a reimport or the game
runs the stale SPIR-V (a push-constant size mismatch silently kills the
dispatch — cloudless sky + spurious flat tint from the cleared textures).

4. **Ground-light calibration is COUPLED to this** (2026-06-11,
   docs/grass.md §6): the sky calibration brightened the rendered sky
   ~1.2–1.5 stops but the DirectionalLight was left at the keyframe
   values — sunlit turf measured ~1 stop dark vs reference. `SUN_CAL=3.0`
   (day_night_cycle.gd) now multiplies sun.light_energy, day-blended like
   the sky cal. The cloud-march direct-sun term multiplies LIGHT_ENERGY
   (clouds.glsl:171), so `vol_sky.sun_scale` is divided by the same
   factor — **any future change to SKY_CAL_SUN or SUN_CAL must preserve
   that compensation** or clouds shift with ground light. Sweep knob:
   `--sun-cal=mult`. Direct:diffuse is now ~4.9:1 at clear noon
   (physical; ambient keyframes untouched).

## 6c. Aerial perspective / fog-veil calibration (2026-06-11 — COMPARISON.md #5a)

The distant tree line measured ~2.5× too bright: at the Sheep Meadow hero
pose (clear noon), volumetric fog added **+41 luma (+48%) of warm-grey
wash** (ΔRGB +53/+38/+40) over the ~400 m tree-line band, vs the real
clear-day NYC veil of ~10%, slightly blue. Protocol:
`scripts/fog_veil_check.py` (tree-line band + tower patch, shared-mask
fog-on/off deltas, poses from `sheep_meadow_ref_captures.sh`,
`--cloud-seed=7`).

Component attribution (zeroing each in-scatter source via `--fog-cal`):
the **sun forward-scatter term owned ~95% of the veil**. Root cause is
the §6b coupling rule by omission: SUN_CAL=3.0 multiplies
`sun.light_energy`, which the fog sun in-scatter also multiplies — the
clouds got the `/sun_mult` compensation, `light_volumetric_fog_energy`
(5.0) never did. Ambient inject / GI inject / emission were ~+1 luma
each.

Shipped (day_night_cycle.gd `FOG_CAL_*`, main.gd fog colors):

1. **`/sun_mult` compensation** on the volumetric sun energy (day-blended;
   night exact). Alone: +48% → +20%. **The §6b coupling rule now covers
   three terms: cloud direct-sun, AND fog sun in-scatter.**
2. **`FOG_CAL_SUNVOL = 0.4`** on top, blended back to 1.0 at low sun via
   `sun_low_factor` — dawn/dusk forward scatter IS the god rays, and the
   compensation alone already restores their pre-SUN_CAL strength
   (verified: dawn Ramble medians 29.2 vs old 29.3, RGB identical).
3. **Blue skylight floor**: fog albedo cooled (0.92,0.93,0.96)→
   (0.85,0.90,0.98); emission color → sky-blue (0.45,0.62,1.0) with
   energy ×7 (`FOG_CAL_EMIS`), gated on **sun elevation** (`day_f ×
   smoothstep(15°,40°, elevation)`) — a plain day_f gate turned 6:30
   golden-hour mist blue (keyframe sun_energy is already 0.90 at dawn);
   elevation gating restores dawn exactly while noon keeps the floor.
4. **Heavy-weather gate**: any weather ≠ CLEAR resets SUNVOL/EMIS cals to
   1.0 — bright sun in-scatter is the white of a fog bank, and a blue
   floor under overcast is wrong. Weather fog keeps its long-standing
   pre-SUN_CAL look (the compensation cancels SUN_CAL by construction).

**Result (hero pose, shipped defaults): tree-line veil +8.5 luma (+10% of
unfogged), ΔRGB +9/+8/+16 — blue-led.** Night 21:00 medians 19.9 vs 20.0;
dusk 24.4 vs 24.8. Closer tree bands get proportionally less (+3% at the
nw_across_meadow band) — correct, the veil is an integral over distance.

Open, related (COMPARISON.md #5): towers at 1–3 km net ≈0 veil — on
bright surfaces extinction cancels in-scatter, and the fog volume ends at
`volumetric_fog_length` 800 m, so aerial perspective stops accumulating
past that. Lifting distant-tower blacks needs depth-range fog (classic
`fog_aerial_perspective` re-enable or longer froxel volume — measure god-ray
depth-resolution cost first). And the unfogged canopy itself is still too
bright (96.5 vs ref 36–62) — that's work item (b), canopy value.

Sweep knob: `--fog-cal=sunvol:amb:emis:density:gi` (exact multipliers,
bypass all blends/gates; partial OK, e.g. `--fog-cal=0.4::7`).

Perf: free, verified by sandwich A/B (gates 20260611_123225 new vs
_123800 old, same thermal state: 52/59/41/64/34 vs 51/58/41/64/35 fps).
Both read ~+7 ms/location vs the cold 4 AM canonical gate
20260611_042800 — a second documented instance of the §1 thermal-drift
trap, this time offsetting a WHOLE gate uniformly: an absolute gate
FAIL after a long capture session is not actionable without a
same-state sandwich.

## 6d. Cloud shape, flow, and twilight sky (2026-06-11 — "psychedelic marshmallows" fixed)

The user walk-around defect (clouds as tall vertical pills that morph
rather than flow) plus "flat dawn/dusk skies" had four distinct roots,
all fixed. References: `notes/refs/sky_2026_06_11/` (user-supplied CP
dusk walking tour XY9f8t46G9M + Columbus Circle sunrise time-lapses);
BEFORE/AFTER capture protocol: `scripts/sky_captures.sh` (16 poses,
`--cloud-seed=7`).

1. **Vertical pills = no height control.** The weather map's G channel
   was unused, so every cell extruded as a cylinder through the full
   2.5 km layer (~1:1 aspect; median cell 1.7 km wide). Real fair-weather
   cumulus is ~2.5–3:1 wide. `gen_weather_map.py` now writes per-column
   tower height into G (h ≈ 0.75 × cell radius, 0.35 km floor, dome
   profile `blob^0.45`); `clouds.glsl density()` rescales the height
   fraction by it → flat shared bases at the condensation level, capped
   domed tops.
2. **Smooth extruded sides = base noise far coarser than cells.** The
   perlin-worley base sampled at 12.5 km wavelength vs 1–3 km cells, so
   the soft weather-disc envelope WAS the silhouette. Now 5.6 km
   (0.00018) — lobes at cell scale. CAUTION: this couples to the cell
   coverage threshold — at 0.00025 the within-cell variance dropped whole
   cells below the Schneider remap and the noon dome emptied; the map's
   interior values were lifted to compensate (`b_chan = coverage^0.75`).
3. **Morph-not-flow = three drift rates.** Envelope moved at 16.7×wind,
   base noise at 12×, detail at −40× (sign-opposed!) plus a 40 m/s
   constant vertical scroll — clouds churned through their own shapes.
   All three now ride ONE world offset (`wind_world()`); evolution comes
   from a 5 m/s vertical boil only. Side fix: the light march's distant
   sample omitted the drift offset entirely (shaded against a stale
   field). **Follow-up same day (user: "static even at max wind"):
   `wind_vec` is a shader-units vector (max ~1.65), not m/s — true
   advection was ~2 m/s at 2 km altitude, imperceptible; the "motion"
   seen before the unification was the churn defect itself. `wind_speed`
   is now honest m/s end-to-end: main.gd maps surface wind → 4–24 m/s
   aloft (winds at cloud height never read zero), shader factor 1.**
4. **Grey clouds at noon (regression risk class):** the march's ambient
   term mixed ground→sky by ABSOLUTE layer height; shallow tower-capped
   clouds live entirely in the bottom 30 % of the layer and went
   ground-grey. The mix now uses position within the cloud (`hf`).

Twilight sky (companion commit `ada7052`): celestial sun decoupled from
the shadow light — see the commit message and day_night_cycle.gd
comments. Coupled rule added to §6b's family: **cal_bg blends on
`max(day_f, twilight_f)`**, because day_f (sun_energy) fades exactly when
the below-horizon LUT needs its exposure correction most (dusk went
near-black without it).

Knobs: `--cloud-seed=N` (reproducible field), map regen
`python3 scripts/gen_weather_map.py --coverage 0.42`. Flow flip-book:
`scripts/cloud_flow_check.sh`. NOAA monthly coverage remains the global
scale (June ≈ 0.30 — a data-correct June sky is ~1/3 cloud, not the
drama-selected reference frames).

Reimport gotcha applies to BOTH clouds.glsl and weather.bmp (§6b).

## 7. Shadow-casting policy (design rule)

Only things whose shadow you can *name from a walk* cast: trees (via proxies), large structures, lamps at night. Grass, undergrowth, ground cover, leaves-as-geometry never cast (enforced in every builder; verified 2026-06-09 — shadow-pass primitives identical at 17.44M with grass shown vs hidden at Great Lawn). Perceived grass shadows are in-shader blade shading + SSAO/SSIL contact darkening. Shadow detail is a near-field privilege; beyond the first cascade, shape fidelity is invisible and dapple is texture, not geometry.

Counter snapshot (Great Lawn close-up, 10:00, `vistri/shobj/shtri` in `[PERF]`): visible 13.0M tris of which **grass alone is 9.4M** (~11.5 ms vpgpu — the §6.5 grass problem is vertex/overdraw); shadow pass re-rasterizes **17.4M tris from 688 casters** — more triangles than the camera sees, at a lawn. *(2026-06-10 update: that 17.4M was mostly the WaterBodies caster — see §3 correction. Post water-fix + proxies, Great Lawn shadow pass is 1.91M.)*

## 8. Not yet measured

- bethesda / great_lawn / literary_walk attribution matrices (lighter scenes; gate covers them pass/fail).
- TAA and tonemap cost (no toggle yet).
- Cloud compute (§5).
- Win interactions — proxy shadows + atlas 4096 + occlusion overlap; never sum the table's deltas. Measure combined.
