# Rendering — performance budgets and frame anatomy

Written 2026-06-09 from the D1–2 bisection (commits `06d3991`–`3ee9777`).
Companion docs: [`architecture.md`](architecture.md) (system map; its §7 hypotheses are now measured here), [`workflow.md`](workflow.md) (Definition of Done).

**Hard target ([`vision.md`](vision.md)): 16.6 ms/frame (60 fps) at 1920×1080 on RTX 3060 Ti, at all 5 canonical test locations.**

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

## 7. Shadow-casting policy (design rule)

Only things whose shadow you can *name from a walk* cast: trees (via proxies), large structures, lamps at night. Grass, undergrowth, ground cover, leaves-as-geometry never cast (enforced in every builder; verified 2026-06-09 — shadow-pass primitives identical at 17.44M with grass shown vs hidden at Great Lawn). Perceived grass shadows are in-shader blade shading + SSAO/SSIL contact darkening. Shadow detail is a near-field privilege; beyond the first cascade, shape fidelity is invisible and dapple is texture, not geometry.

Counter snapshot (Great Lawn close-up, 10:00, `vistri/shobj/shtri` in `[PERF]`): visible 13.0M tris of which **grass alone is 9.4M** (~11.5 ms vpgpu — the §6.5 grass problem is vertex/overdraw); shadow pass re-rasterizes **17.4M tris from 688 casters** — more triangles than the camera sees, at a lawn. *(2026-06-10 update: that 17.4M was mostly the WaterBodies caster — see §3 correction. Post water-fix + proxies, Great Lawn shadow pass is 1.91M.)*

## 8. Not yet measured

- bethesda / great_lawn / literary_walk attribution matrices (lighter scenes; gate covers them pass/fail).
- TAA and tonemap cost (no toggle yet).
- Cloud compute (§5).
- Win interactions — proxy shadows + atlas 4096 + occlusion overlap; never sum the table's deltas. Measure combined.
