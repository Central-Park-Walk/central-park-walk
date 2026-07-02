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

## 4. The frame budget (binding)

GPU ms at 1080p, measured at the worst of the 5 locations. A subsystem over its line is a regression even if total fps passes (headroom is for weather/seasons, not for spending). Per `architecture.md` §9, new subsystems must name their budget line.

| line | budget (ms) | measured today (worst) | gap |
|---|---|---|---|
| sky + volumetric clouds | 1.0 | inside floor (§5) | measure |
| Terrain3D camera raster | 1.5 | ~4 | −2.5 |
| trees — camera raster | 4.0 | ~25 (ramble) | −21 |
| trees — shadow casting (proxies) | 1.0 | 18–28 | −17 to −27 |
| other shadow casting + sampling | 2.5 | ~19–21 | −17 |
| SDFGI | 1.5 | ~7 | −5.5 |
| volumetric fog | 1.0 | ~1 | ok |
| grass (all tiers, camera) | 1.5 | ~7 | −5.5 |
| undergrowth + ground cover | 0.5 | <1 | ok |
| post (SSAO, SSIL, glow, TAA, tonemap) | 1.5 | ~1 (TAA untested) | ok? |
| water, weather particles, misc | 0.6 | <1 | ok |
| water planar reflection (2026-07-01, near water only; sleeps >250 m away) | 1.5 | TBD — measure on/off at Lake shore (`--no-water-reflection`) | ? |
| **total** | **16.6** | ~83–88 | |

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
