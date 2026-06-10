# Rendering — performance budgets and frame anatomy

Written 2026-06-09 from the D1–2 bisection (commits `06d3991`–`3ee9777`).
Companion docs: [`architecture.md`](architecture.md) (system map; its §7 hypotheses are now measured here), [`workflow.md`](workflow.md) (Definition of Done).

**Hard target ([`vision.md`](vision.md)): 16.6 ms/frame (60 fps) at 1920×1080 on RTX 3060 Ti, at all 5 canonical test locations.**

## 1. How we measure

- `scripts/perf_gate.sh` — pass/fail at the 5 locations. The gate for any perf-relevant change.
- `scripts/perf_bisect.sh <location> [label=hides ...]` — per-subsystem attribution via `--diag-hide=` (terrain trees undergrowth grass shadows sdfgi fog ssao ssil glow treeshadows) and raw knobs (`--shadow-dist=`, `--shadow-size=`).
- Protocol: 1080p, vsync off, noon/clear/summer, stationary, 60 s/run, stats from the last 10 `[PERF]` samples (2 s cadence). Scene load is ~35 s — runs shorter than ~50 s produce zero samples. **fps is median; ms columns are means** and include spikes (see §5 floor anomaly). Never touch a measurement window (`overlay=ON` marks the run contaminated).
- `[PERF]` fields: `process` = main-loop ms (includes main thread blocked on GPU), `sub` = our profiled GDScript, `vpcpu`/`vpgpu` = `viewport_get_measured_render_time` CPU/GPU ms.

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

## 5. Floor anomaly (open)

With everything hidden, median fps ≈ 300 (≈3.3 ms typical frame) but *mean* process is 16–18 ms — large periodic spikes survive in the means of every config above. Prime suspect: volumetric cloud compute (768² target, 64-frame update cycle). Until measured, treat all ms columns as ~10–20% pessimistic and trust deltas more than absolutes. Follow-up: add a `clouds` diag option, measure, and either amortize the dispatch or budget it explicitly.

## 6. Reduction plan (D5–9, in order of measured size)

1. **Tree shadow proxies** (−13..16 vs post-impostor-fix world) — **SHIPPED, default ON 2026-06-10** (tree_builder.gd, opt-out `--no-tree-shadow-proxy`): trunk cylinder + crown lathe fit to each variant's leaf vertices (12 slices, p96 elliptical radii), `SHADOWS_ONLY`, GI off, phenology-driven dapple discard (shaders/tree_shadow_proxy.gdshader — thins in autumn, bare in winter, blossoms cast). Full DoD record in trees.md §3.
2. **Tree camera raster** (−21 at ramble): re-enable occlusion culling (canopy occluders vs `visibility_range` conflict, `tree_builder.gd:703-706`), tier boundary review (mesh tier to 290 m is far), LOD0/1 triangle audit. Spec first.
3. **Other shadows — DECIDED 2026-06-10** (re-measured post-proxy/post-water; the old −16/−32 deltas no longer exist because the shadow load they amplified is gone): **atlas 4096 is the default** (−3.4 ms at Ramble 17:00, visually neutral at Ramble + Literary Walk golden hour — if anything slightly softer, which suits the tone). **PCF filter stays quality 2**: filter 1 now saves only ~5 ms and visibly hardens the long-shadow penumbra at low sun — and the proxy dapple *depends* on PCF blur to read as mottle (its holes sharpen into cut-outs at quality 1). Terrain caster (−9 pre-fix) not retested — candidate for D5–9 with a golden-hour visual check.
4. **SDFGI** (−5.5): cascade count and cell size sweep — 6 cascades @ 0.5 m is generous for a park walk.
5. **Grass** (−5.5): tier ranges/density sweep; it casts nothing already, so this is camera raster + overdraw.
6. **Floor spikes** (§5).

Every step: perf_gate before/after at all 5 locations, committed with the numbers in the message.

## 7. Shadow-casting policy (design rule)

Only things whose shadow you can *name from a walk* cast: trees (via proxies), large structures, lamps at night. Grass, undergrowth, ground cover, leaves-as-geometry never cast (enforced in every builder; verified 2026-06-09 — shadow-pass primitives identical at 17.44M with grass shown vs hidden at Great Lawn). Perceived grass shadows are in-shader blade shading + SSAO/SSIL contact darkening. Shadow detail is a near-field privilege; beyond the first cascade, shape fidelity is invisible and dapple is texture, not geometry.

Counter snapshot (Great Lawn close-up, 10:00, `vistri/shobj/shtri` in `[PERF]`): visible 13.0M tris of which **grass alone is 9.4M** (~11.5 ms vpgpu — the §6.5 grass problem is vertex/overdraw); shadow pass re-rasterizes **17.4M tris from 688 casters** — more triangles than the camera sees, at a lawn. *(2026-06-10 update: that 17.4M was mostly the WaterBodies caster — see §3 correction. Post water-fix + proxies, Great Lawn shadow pass is 1.91M.)*

## 8. Not yet measured

- bethesda / great_lawn / literary_walk attribution matrices (lighter scenes; gate covers them pass/fail).
- TAA and tonemap cost (no toggle yet).
- Cloud compute (§5).
- Win interactions — proxy shadows + atlas 4096 + occlusion overlap; never sum the table's deltas. Measure combined.
