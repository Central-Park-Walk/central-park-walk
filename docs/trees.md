# Trees — tier spec, runtime-lit impostors, shadow proxies

> **Model/geometry redesign** (art direction, per-species silhouette tuning,
> per-instance variation, cathedral-elm convergence) is specified separately in
> [`tree_model_redesign.md`](tree_model_redesign.md). This file owns the *rendering
> tiers and their budgets*; that file owns the *source meshes* that feed them.

Spec for the D3–5 sprint work (written 2026-06-10, before implementation, per
[`workflow.md`](workflow.md)). Budget lines this subsystem spends
([`rendering.md`](rendering.md) §4): **camera raster 4.0 ms, shadow casting 1.0 ms**
at the worst test location. Measured today: ~25 ms camera (Ramble), 18–28 ms shadows.

## 1. Tier architecture (target state)

> **CANONICAL TIER CHAIN (since 2026-07-03): `lod0` (full base model) → `impostor`.
> There is NO mid tier.** The former `lod1` mid mesh was REMOVED (Chris 2026-07-03):
> the `_lod1` GLBs had gone stale vs the current lod0 models, and impostors baked from
> them (`_m`/`_l`) changed shape vs lod0 across octahedral angles ("l keeps changing
> shape"; `l_lod1` was a 30 %-vert decimation with an ~8 %-wider crown). Impostors now
> **bake from lod0** and hand off directly from it. The `--lod1-as-near`/`--no-lod1`/
> `--full-lod0`/`--tree-lod1-range` toggles and `--tier-isolate=lod1` are gone; the
> `_lod1` GLBs were deleted. **Legacy `lod1`/`lod2`/`TreeL2` tokens linger in older
> prose — §2 body (dated as-built logs), §4–§9 — they describe retired tiers; the live
> chain is lod0 → impostor. Where old prose contradicts this banner on numbers, the
> banner wins: `IMPOSTOR_FAR` is **800 m** (not 2500), the handoff is **40–80 m** (not
> 250/340/400 m), and the impostor's crossfade partner is **lod0** (not `_lod1`).**

| tier | range | fade | representation | casts shadow | lit |
|---|---|---|---|---|---|
| lod0 (near) | 0–80 m | solid 0–40 m, dither out 40–80 m | `{species}_{s,m,l}` — the **full base model**, MMI per species-size × 80 m chunk | **never** (proxy does) / own per-leaf when proxy off | runtime sun + ambient |
| shadow proxy | 0–290 m | none (pops with cascade distance, invisible; shadow distance is 150 m so the 290 m cap is never the binding limit) | trunk cylinder + crown hull ≤ ~300 tris, alpha-test dapple mask, MMI `SHADOWS_ONLY` | is the shadow | n/a |
| impostor | 40–800 m | dither in 40–80 m (complementary to lod0), solid 80→800 m | **16×16** hemisphere octahedral, 2048² albedo+normal+orm+vis atlas per species-tier, **baked from lod0** (§2, as-built 2026-06-23, sun-visibility 2026-07-02, lod0-source 2026-07-03) | never | **runtime sun + ambient** |

The lod0 → impostor handoff is `_mesh_fade_end` (**80 m default**, `LOD_FADE_RATIO` 0.5 →
band [40, 80]; Chris 2026-07-03), height-scaled per tree via `_lod_scale` so every tree
switches at the same on-screen size (tunable `--tree-mesh-range=N`). lod0 is the
full-detail mesh, only needed close; past ~80 m the octahedral impostor reads as well
and is far cheaper. Impostors run out to `IMPOSTOR_FAR` = 800 m.

> **PERF NOTE (2026-07-03):** with the mid tier gone, the near tier is the FULL lod0
> mesh out to ~80 m (was the cheaper lod1). Re-measure deep-woods fps (Ramble/North
> Woods); `--tree-mesh-range` moves the handoff if the full-lod0 near band is too heavy.
> See [[project_performance_investigation]].

The lod0 mesh and the impostor spawn from the same per-chunk buckets (transforms +
custom data identical, crossfade water-tight); chunk visibility ends derive from each
chunk's actual max instance-to-centroid radius (the old fixed +40 m margin could
under-cover skewed chunks). Diagnostics: `--tier-isolate=lod0|impostor|mesh` renders
one tier across the full range; `--tree-mesh-range=N` moves the handoff;
`TIER_A`/`TIER_B` env vars on `tier_handoff_check.sh` pick the compared pair.

**Density-modulated handoff (`--density-lod[=frac]`, 2026-07-03).** Off by default (flat
80 m handoff). When on, each tree's handoff distance scales by its baked local-density
**openness** ∈ [0,1]: an open-grown lawn specimen holds lod0 to the full 80 m, a dense
forest-interior tree hands off at `dense_frac` of that (default **0.35** → ~28 m, under
Chris's 40 m ceiling and near his ~20 m ideal), because its crown is mostly occluded by
nearer crowns up close anyway. This recovers the "far handoff where it's noticeable"
benefit of the retired mid tier **and** cuts deep-forest lod0 overdraw, without a mid
tier. Openness is computed once at placement (`_pack_lod_openness` in `tree_builder.gd`:
neighbours within 18 m via a spatial grid, `smoothstep(N_OPEN=2, N_DENSE=7, count)` —
**calibrated 2026-07-03 to the placed-tree neighbour histogram** (mean 4.7 within 18 m);
the original 1/9 thresholds left most woods trees classed "open" (mean openness 0.66) so
the handoff never shortened where it mattered) and packed into the custom-data **B
channel alongside the evergreen flag** (deciduous b∈[0,0.49], evergreen b∈[0.51,1.0];
decode `openness=(b>=0.5?b-0.51:b)/0.49`), so it costs nothing at runtime and **can't
pop** as the camera moves (unlike view-dependent occlusion). The shaders scale the
*dither distance* only (`lod_dist = dist / handoff_factor`), leaving detail gates on true
distance; the impostor carries `handoff_factor` in the spent `quad_blend_weights.w` to
avoid a new varying (budget-critical).
**Plan A — geometry cull (2026-07-04).** The dither alone only discards *fragments*; the
lod0 mesh was still submitted (vistri + draw) out to the chunk's padded ~80 m range, so it
saved fill but no geometry. Now `tree_builder` also buckets lod0 by openness **class** with
a per-class cell size (dense <0.34 → 40 m cells, mid <0.67 → 60 m, open → 80 m) and shortens
each chunk's `visibility_range_end` to `80·lscale·factor_cull + hd`, where `factor_cull =
lerp(dense_frac, 1, max openness in the chunk)` (the least-dense member, so no tree is culled
before its own dither ends). Small cells are essential: the MMI culls by camera→AABB-centre
padded by the half-diagonal `hd`, so a big cell pads the range back past the handoff — a
dense chunk's lod0 now culls at ~63 m vs ~153 m before. The impostor's
`visibility_range_begin` is pulled in by the same factor so it is already drawn where lod0
culls (no hole). Openness is baked once at placement, so **density-LOD is a build/launch
decision, not a live toggle**: `--density-lod` (**opt-in, default OFF pending the 2026-07-04
artifact fixes below**) / `--no-density-lod` /
`--density-lod=<frac>`; the `lod_density_enabled`/`lod_density_dense_frac` globals (main.gd)
keep the shader dither in step with the baked cull. Verified: openness spans 0.00–1.00 across
1892 park trees (431 fully dense ~28 m, 885 fully open 80 m, 576 gradient); park builds to
644 LOD0 chunks. **Watch on a walk:** more/smaller chunks = more draw calls (a
vistri-for-drawcalls trade — check the draw-call HUD in dense woods); the shadow proxy is
still full-range (a phase-2 lever). F6 trees-off is the instant is-it-even-trees check.
**KNOWN ARTIFACTS (2026-07-04 walk, why it is opt-in / default OFF):** (1) **s-tier impostors
too close** — screen-size LOD shrinks the small-tree handoff (`80 × h/22`) and density
shrinks it AGAIN, so a small dense tree becomes a billboard at ~20 m even unoccluded. FIX =
a **minimum handoff floor** (~35 m, clamp the effective handoff regardless of size×density).
(2) **crossfade dither stipple** — the lod0↔impostor dither-discard is meant to be resolved
by TAA, but the project runs FSR2 with TAA off and FSR2 does not dissolve it, so every tree
in its handoff band shows the raw net (worst vs bright sky; visible even at 1× motion). The
closer/more-numerous density handoffs made it pervasive. FIX = narrow `LOD_FADE_RATIO`
(0.5→~0.25) to thin the stipple zone, and/or a real resolve (alpha-blend the impostor).
"Dithers across differing heights" = mixed size tiers handing off at different distances
(small/low canopy stipples while tall/high canopy stays solid) — the min-floor helps this too.
(3) **impostor trunk-green** — season tint bleeds onto the baked trunk region of the impostor
atlas (pre-existing, on true impostors); needs the trunk region masked from the season hue.
The **bark/leaf desync** (lod0 grey trunk lingering after the crown handed off) is FIXED:
`tree_bark.gdshader` now density-scales its dither with the same `v_lod_factor` as tree_leaf.

**Impostor wind (2026-07-03).** The far crowns now rock in the wind to match the mesh at
the handoff. `tree_impostor.gdshader` reuses the shared `wind.gdshaderinc` structural
terms (trunk cantilever + steady push + gust) and the same `WIND_PARAMS` row the mesh
uses, evaluated once at the crown centroid height (`world_height*0.62`) so the whole
billboard leans coherently with neighbouring mesh trees; the per-branch term is omitted
(crown detail, averages to ~0 over the card). The world-space sway is transformed to
object space and weighted by `UV.y` (top leans, base planted). Full amplitude through the
40–80 m handoff (mesh wind is full to ~140 m), fading out by ~450 m. Amplitude lever:
`impostor_wind_strength` global (default 1.0; 0 = static billboards), live-tunable on a
walk with **I** / **Shift+I** (raise/lower). Values print to the console.

**Impostor backlit SSS/glow (`IMP_SSS`, 2026-07-03, 76d4da3).** The near mesh glows
amber when backlit via Godot's built-in BACKLIGHT; the impostor's custom `light()`
bypasses that path, so the far tier never glowed (fix-ladder #2 from the impostor
rebuild). Fix: re-inject transmission inside `light()` with Godot's exact backlight
formula (`light_color * (1/PI − diffuse_brdf_NL) * backlight`), magnitude-matched to
the mesh — amber tint blended with per-tree season colour, scaled by canopy fraction,
capped at 15 % of ALBEDO, NOT gated by `v_vis` (mesh SSS ignores crown AO too). Zero
new varyings; `sss_strength` uniform folds the per-species factor (0.6 = london plane).
Awaiting Chris's motion walk. Bears on §5's open "specular response at low sun" item.

**Riparian canopy (2026-07-03, 9599957).** Watercourse census trees are almost all
NAMED species (cherry/oak/maple) that the bare-until-redesigned policy skips — so
streams ran through bare ground and read as pale sky-reflecting sheets. A skipped named
species within `RIPARIAN_BUFFER` (18 m) of a watercourse (stream polylines rasterised
into a spatial hash, O(1) test) is now placed as the ready london_plane model: +463
trees (1429→1892), normal tier chain, feeds the canopy map automatically. Policy is
unchanged everywhere else. Result: shaded dark ravine rills (see the water memory).

## 2. Runtime-lit octahedral impostors (as-built 2026-06-23)

> **Rebuilt from scratch 2026-06-23** after the 2026-06-22 reset wiped the far
> tier. Grounded in **Godot-community / AAA SOP** (Ryan Brucks octahedral
> impostors; the `wojtekpil` / `zhangjt93` Godot ports), NOT the prior in-repo
> spec — which this section used to describe. That spec's mistake was twofold:
> it hand-rolled a bespoke `impostor_baker.gd` that reimplemented the installed
> `addons/Imposter/` octahedral rig, AND it baked albedo **lit**, so every
> impostor was lit twice and patched by an `impostor_brightness` global fudge —
> the root cause of the dark-olive-atlas and time-of-day-mismatch bugs. The
> as-built system keeps the addon's proven octahedral math and lights **at
> runtime** from a normal atlas, so the fudge is gone.

**Parameters (research-grounded):** 16×16 hemisphere views, 2048² atlas, albedo +
camera-space normal + ORM channels (depth default neutral; parallax off for v1).
These replace the old spec's 8×8 (under-sampled).

**Bake — `scripts/bake_impostors.gd` (run via `--bake-impostors[=species]`):**
- Runs inside the normal app right after `tree_builder` materialises
  `_species_meshes` (the exact in-game `tree_leaf`/`tree_bark` ShaderMaterials),
  then quits — no placement, terrain, or editor needed. A SubViewport parented
  under `park_loader` pumps `RenderingServer.frame_post_draw`.
- Each of the 16×16 hemisphere views is rendered separately (4× supersampled →
  128 px cell) with an ortho camera aimed by `OctaUtils.octa_uv_to_world` — the
  same hemisphere mapping the addon decoder uses, so layout matches by
  construction. The mesh is drawn via a 1-instance MultiMesh carrying
  london_plane `INSTANCE_CUSTOM` (`Color(9/13, .5, 0, .5)`) so the leaf shader
  picks the right species colour; globals forced to summer / no-wind / no-snow.
- `bake_mode` uniform (`tree_leaf`/`tree_bark`): when set, the fragment emits ONE
  channel UNSHADED via EMISSION with the identical discard — `1` = albedo (leaf
  colour with the **dapple self-shadow folded in** but before the top-lit/fresnel
  directional fakes; runtime lighting supplies directionality), `2` = camera-space
  normal packed 0.5+0.5, `3` = ORM (**R = crown-interior AO**, G = roughness,
  B = metallic). The AO and dapple are the two darkening terms the live canopy
  applies that a naive albedo bake omits — leaving them out made the far tier read
  **1.56× too bright** vs lod0/lod1 (measured 2026-06-23, noon, Bethesda handoff).
- Writes `textures/impostors/<species>_<tier>_{albedo,normal,orm,vis}.png` + a
  `<species>_manifest.json` (frames, `scale`, `aabb_max`, **`position_offset` =
  +AABB-centre** so the billboard sits at canopy height — the sign that, inverted,
  buried the whole far tier in the old system).

**Sun-visibility channel (`_vis.png`, 2026-07-02).** The static AO-on-direct fake
(a801c20) matched the mesh only at its calibration hours — measured impostor/lod0
luminance 1.08× at 13h/16h/18h but **0.29×
at 9h** (the always-on `pow(AO,1.5)` crushes the crown whenever N·L is already
low). Chris's field report: same tree, same view, great at one hour, terrible at
another. Fix = per-texel **directional occlusion**, evaluated against the real sun:
- Bake (`_bake_vis_channel`, summer only): per octa cell, render `bake_mode 4`
  (white lambert; BACKLIGHT=0 or transmission leaks into the shadowed pass) lit by
  a probe DirectionalLight from **9 directions** (zenith + 4@40° + 4@12°), shadows
  ON and OFF; the per-pixel ON/OFF ratio is pure geometric sun-visibility (N·L and
  BRDF cancel exactly; probe energy 0.6 so the OFF pass can't clip). A GPU
  least-squares **L1 fit** (one canvas pass over a `Texture2DArray` of the probes)
  compresses the 9 ratios to `R = c0` (mean visibility), `GBA = bent vector`
  (bake-object space). Stored **LINEAR** (hdr_2d composite readback — verified),
  so the runtime samples it *without* `source_color`.
- Runtime: fragment evaluates `clamp(c0 + dot(c_vec, sun_obj), 0, 1)` (sun rotated
  per instance in *vertex* — `MODEL_MATRIX` is chunk-locked past vertex, #76292;
  `sun_dir_world` global pushed from main.gd) and a custom `light()` (exact
  scene_forward_lights burley; specular dropped — measured no-op) multiplies
  direct light by it. Winter relaxes vis→1 (a bare crown barely occludes). With a
  vis atlas bound, tree_builder retires the static fake (`ao_light_affect=0`,
  `ao_power/floor` neutral — ambient AO back to plain mesh parity); manifests
  without `vis` keep the old behaviour via an in-shader AO-on-direct replica (the
  custom `light()` bypasses the engine's `AO_LIGHT_AFFECT` path). `IMP_VIS` env
  sweeps `vis_strength`.
- ⚠ **Varying budget:** engine interpolators share the 32-slot cap in the full
  scene — +2 user varyings broke this shader (33/32) while a minimal project
  compiled fine. The dormant depth-parallax basis (`xy_frame1..3`) was dropped to
  pay for the vis pair; to restore parallax, recompute those per-fragment.
- New PNGs need one editor import pass (`godot --headless --import`) before the
  game can `load()` them.

**Seasonal shape — TWO atlas sets per tier (2026-06-27).** A single summer atlas
read *too full in summer* (a full crown projects solid at bake res — a blob, not the
see-through live mesh) and *very too full in winter* (the runtime only recoloured the
summer silhouette brown; it never thinned). The far tier's SHAPE must track season, so
each tier is now baked TWICE (`bake_tier(season_t, file_suffix)`):
- **SUMMER** (`SUMMER_SEASON=2.0`, suffix `""`): for london_plane's single-variant
  bake, `LP_SUMMER_CARD_KEEP=0.6` thins the crown via the leaf shader's `bake_density`
  per-card drop so the projected crown reads as see-through as the live lod0
  (`-1`/full = the old blob). Tuning lever for distant summer density. **The drop is
  spatially EVEN, not silhouette-random (2026-07-03, 32e8a47/0cdc677):** a random
  per-card drop clumped and read as an "oddly decimated" far crown; an even per-card
  keep (0.6) preserves crown shape at the same density. (An earlier attempt to thin by
  card-drop at *runtime* caused crossfade region-fade and was reverted, 46f03b8 —
  density belongs in the BAKE, not the live mesh.)
- **WINTER** (`WINTER_SEASON=3.5` = Jan, suffix `"_winter"`, `card_keep=-1`): at
  `season_t=3.5` london_plane's phenology `canopy=min(grow,shed)=0`, so the leaf
  shader's own `v_leaf_density` collapses to `WINTER_RETENTION` (0.05). With no fixed
  `bake_density` override, that drives a per-card drop to a near-bare branch skeleton +
  a few marcescent sprigs — REAL geometry, baked. (This replaces the 2026-06-27 runtime
  per-fragment stochastic discard, which crawled in motion and was reverted.)
- Winter atlas paths are grafted onto the summer tier's manifest entry under
  `winter_{albedo,normal,orm}` keys (geometry — scale/offset/diag — is shared). Atlas
  coverage drops ~4-5× summer→winter (l 16%→4%, m 12%→4%, s 7%→1%).

**Runtime — `shaders/tree_impostor.gdshader`:** adapts the addon `ImpostorShader`
(octahedral 3-nearest-frame blend + virtual-plane parallax). Drops
`impostor_brightness`; `ALBEDO = atlas` and Godot lights it via the normal atlas +
`diffuse_burley` (roughness 1, specular 0.1). The ORM atlas is sampled
`source_color` (the bake viewport sRGB-encodes EMISSION on readback, like the
albedo atlas) and its **R drives `AO` with `AO_LIGHT_AFFECT = 0`** — ambient-only,
exactly as the mesh leaf shader, so the far tier darkens by canopy occlusion across
all sun angles instead of reading ~1.5× too bright. A residual sun-angle-dependent
gap (diffuse_burley vs the leaf shader's directional response: ~1.20× at noon but
~0.95× at 18h) is closed by a gentle near-neutral `albedo` calibration tint
`(0.93,0.94,0.96)` in `_build_impostor_assets` (the far-tier analog of the leaf
shader's `tier_brightness`). Adds `lod_fade_in` dither so it crossfades with lod0 (was `_lod1` pre-5b2bed8)
over the same band the mesh tier dithers out.

When a winter atlas set is bound (`has_winter_atlas`), the shader samples BOTH sets
and blends `mix(winter, summer, v_leaf_frac)` per fragment, where `v_leaf_frac` is the
per-tree seasonal canopy fraction computed in vertex with the SAME `min(grow,shed)`
phenology curve as `tree_leaf` — so the far crown thins in lockstep with the mesh and
the winter hue comes from the existing `v_season_color` (brown). The blend branch is
gated on `v_leaf_frac < 0.999` and is coherent (season-driven), so the extra atlas
fetches are skipped outright in full summer and only paid through the fall/spring
transition bands. Season presets: `summer=1.5`→frac 1.0 (pure summer atlas),
`winter=3.5`→frac 0.0 (pure winter atlas, matching `WINTER_SEASON`).

**Integration — `tree_builder.gd`:** `_build_impostor_assets()` builds one billboard
QuadMesh + material per baked tier (params from the manifest, `lod_fade_in` band
height-scaled per `_lod_scale`). `_spawn_impostor_chunks()` spawns an impostor MMI
per chunk sharing the mesh tiers' transforms/custom-data, `visibility_range_begin`
at the lod0 fade-out, out to `IMPOSTOR_FAR` (800 m since 0100d19; was 2500). `--tier-isolate=impostor`
renders the tier pure from 0 m for comparison.

> **`aabb_max` forced to 0 (size fix, 2026-06-23 PM).** The addon ships
> `aabb_max = diag/4` (= `scale/2`) and the shader does
> `VERTEX.xyz += pivotToCameraDir * aabb_max` — a forward depth-push toward the
> camera by `aabb_max × per-tree-scale` world-metres (~9 m for a ~22 m london
> plane). Under perspective that renders the card at `D/(D−push)` of true size:
> measured **7–10 % TALLER than lod0/lod1** at the eval row, the oversize scaling
> with tree height (the push fingerprint — short specimens ~1.00×, tall ~1.10×).
> The orthographic bake already frames the silhouette AT THE PIVOT, so the
> size-correct push is **zero**; any forward offset only inflates. `_build_impostor_assets`
> now sets `aabb_max = 0.0` (atlases unaffected — this was a runtime placement bug,
> **NOT a bake bug, no rebake**). Post-fix the impostor matches lod0 to within ~2 %
> (residual = off-axis billboard perspective). Method: `--tier-isolate=lod0|lod1|impostor`
> from one `--pos` at the eval `=london_plane` row, foliage-silhouette top-edge per
> x-bin; lod0≡lod1 confirmed lod1 was never the culprit.

**Validation (2026-06-23, london_plane, `--all-london-plane`):**
1. `--tier-isolate=impostor`: billboards render at canopy height (not buried),
   correct london_plane silhouette from all angles incl. top-down, with runtime
   directional lighting (sunlit tops, shaded undersides). **PASS.**
2. Normal mode: a london_plane clump crosses the impostor↔`_lod1` handoff
   continuously on a clean Great-Lawn approach (snapshot bot, `--shots`) — no
   pop/vanish. Code confirms why: complementary per-tree dither + overlapping
   mesh/impostor MMI visibility ranges = no geometric cull gap. **PASS.**
3. **Quantitative brightness (`scripts/tier_handoff_check.sh`, Bethesda 240 m):** the
   pre-AO bake read the impostor **1.56× brighter** than lod0/lod1 (the earlier
   "shares tone — PASS" was a visual miss; measure, don't eyeball). Folding dapple +
   ambient-only AO + the calibration tint lands **1.10× at noon / 0.86× at 18h**
   (balanced, leaning slightly dark). **PASS (brightness).** Residual: evening hue
   skews warm (B≈0.75 — impostor lacks the mesh's underside sky-fill); a flat tint
   can't track it without skewing noon. Open.
4. perf_gate at the 5 locations — **TODO** (the tier adds a transparent-quad pass).
5. Pixel-sample mean|ΔRGB| < 0.05 at the handoff — still ~0.12, but inflated by the
   header's backdrop-bleed caveat + soft-card-vs-crisp-leaf silhouette edges; the
   luma ratio (item 3) is the actionable brightness metric and now matches. **Open.**

**Scope:** london_plane (s/m/l) only — the one species rebuilt to the new skeleton
method. Other species render mesh-only past `_lod1` until their rebuilds land, then
`--bake-impostors=<species>` adds each atlas.

> **✅ RESOLVED 2026-06-26 (85349b7) — kept as diagnostic history.** Root cause: in a
> MultiMesh **fragment** shader, `MODEL_MATRIX[3]` is the NODE (chunk) origin, not the
> per-instance position (Godot #76292) — so the dither distance was computed from the
> chunk origin, and instances far from it dither-discarded in the wrong band ("mesh
> fragments present-but-dither-discarded", exactly the key deduction below). Fix: capture
> the instance position in `vertex()` into a `v_inst_pos` varying and compute the fade
> from that. Full record: memory `project_tree_lod_disappearance_bug`. Note the repro
> bands quoted below (100/150/250 m) are the OLD height-scaled handoffs, pre-80 m chain.
>
> *(Original block, 2026-06-24 PM:)* **specific trees go
> see-through across the mesh→impostor handoff. Trees are NOT "done" until resolved.**
> On specific, deterministic instances (the SAME trees every session; rare overall), the
> canopy goes near-totally see-through (~90% gone, ground-shadow stays solid) across that
> tree's mesh→impostor handoff, recovering to a solid impostor past it. Confirmed this
> session to hit **s, m AND l** models, each at its own height-scaled band (s ~100 m,
> m ~150 m, l ~250 m = `mesh_end = 200 × height/22`). **Per-instance, not per-model:**
> other instances of the identical model+tier nearby do NOT fade. Tied to the tree, NOT
> the camera (not view/angle/position dependent). Holes are real (visible vs sky AND
> ground). Repro is **GPU-only** (`DISPLAY=:0`; xvfb/lavapipe renders solid).
>
> **Engine fact (confirmed):** Godot 4.6 PR #113486 (in 4.6.1; closes #79471/#102799)
> culls a MultiMeshInstance by camera distance to the CENTRE of the AABB encompassing its
> instances — not the node origin; node `custom_aabb` is ignored/recomputed (#79573). The
> mesh MMI and impostor MMI carry different meshes → different AABB centres → their per-
> chunk handoff can desync. This was the leading hypothesis.
>
> **Two fixes tried THIS session — BOTH FAILED (Chris tested):**
> 1. `custom_aabb` pinning the cull box to `chunk_origin` — **no-op** (Godot ignores it,
>    #79573).
> 2. Pad each MMI's `visibility_range` by its own multimesh AABB half-diagonal
>    (`mm.get_aabb().size.length()*0.5`) so both tiers stay drawn through the band — did
>    **NOT** resolve it. (Code KEPT: it is the correct bound given #113486 and is a
>    defensible robustness improvement; the see-through has another/additional cause.)
>
> **Key deduction from fix #2's failure:** if the mesh MMI is now guaranteed drawn through
> the band yet the tree is still see-through, the mesh fragments are present-but-dither-
> discarded and the impostor is NOT filling them → points at the **shader crossfade
> coverage** (sparse-leaf-card mesh XOR filled-billboard impostor, or the octahedral
> impostor cell mismatching the per-tree rotation), NOT the MMI cull — OR the pad isn't
> applying at runtime. Earlier "uniform dither" theories were set aside because most trees
> DON'T fade; reconcile via per-instance Y-rotation → per-instance octahedral-cell mismatch.
>
> **Recommended next experiment (the one un-run test that would split it):** `IMP_RED=1`
> at a known repro tree's band — if the holes are RED, the impostor is drawn but not
> covering (shader/silhouette XOR); if SKY, the impostor is absent (visibility/data). Plus
> `DEBUG_TREE_CHUNK` to confirm the AABB pad actually applied. Do NOT re-attempt blind
> fixes; do NOT re-capture the visual bug just to re-confirm it exists. A removed symptom
> ≠ a diagnosis. Full notes + history: assistant memory `project_tree_lod_disappearance_bug`.

## 3. Shadow proxies (user decision 2026-06-09)

"The entire tree casts a shadow, instead of each leaf. Most shadows are too far
away to appreciate; under a canopy it's just dark all around." Policy in
[`rendering.md`](rendering.md) §7.

**Design:**
- Per species-size proxy mesh generated at bake time from the source mesh:
  trunk = capped cylinder fit to trunk radius/height; crown = low-poly hull
  (icosphere fit to crown AABB/ellipsoid, ~150–300 tris total).
- Crown surface uses an **alpha-tested leaf-density noise mask** so the shadow map
  gets holes; existing PCF (1.5° penumbra) blurs them into dapple. Opaque pipeline,
  early-Z friendly.
- One proxy MMI per species-size × chunk mirroring the visible MMI transforms,
  `cast_shadow = SHADOWS_ONLY`, `gi_mode = DISABLED` (the visible mesh keeps GI
  contribution; proxies must not double-feed SDFGI).
- Visible tree MMIs: `cast_shadow = OFF`.
- Proxy visibility range = mesh tier (0–290 m). Impostors continue to cast nothing.
- Optional escalation (only if reference comparison fails): near-field real-foliage
  caster MMI, `SHADOWS_ONLY`, visibility range ≤ 20 m.

**Validation (DoD):**
1. `shtri` counter at Great Lawn drops from ~17.4 M to < 2 M.
   **PASS 2026-06-10: 1.91 M** (no-proxy same day: 5.97 M). Required a
   census find: `WaterBodies` — one park-wide 3.1 M-tri surface mesh —
   was casting into every cascade (~12.4 M shtri at EVERY location, in
   every measurement since the mesh existed). Water now casts nothing
   (water_builder.gd). The old "~17.4 M" baseline was mostly water, not
   trees; tree casting at Great Lawn was ~4 M of it.
2. perf_bisect at ramble + north_woods: ≥ 15 ms / ≥ 25 ms reduction vs today's
   baseline, no other line regresses.
3. Dapple visual: noon + 8:00 captures under Literary Walk elms and Ramble canopy
   vs reference photos — mottled, not blob-dark, not stripe-artifacted.
4. No GI change: SDFGI on/off A/B identical before/after proxies (within noise).

**SHIPPED — default ON since 2026-06-10 (commit 5af7abc).** Opt-out
`--no-tree-shadow-proxy` (diagnostic). Full DoD record:
1. shtri @ Great Lawn **1.91 M < 2 M** (see item 1 note above — water-caster
   discovery included).
2. Reduction vs the Jun 9 baseline (83/88 ms): ramble −26.6, north_woods
   −28.8 → ≥15/≥25 PASS. Honest caveat: vs the post-impostor-fix Jun 10
   baseline (69.6/75.3 ms, the comparable world) the proxy+water gain is
   −13.2/−16.1 ms — perf gate 20260610_132307: all 5 locations improved,
   none regressed. **Canonical shipped-defaults gate (proxies + atlas 4096,
   20260610_135252): 30.8 / 21.3 / 52.1 / 20.4 / 50.3 ms** (lit_walk /
   bethesda / ramble / great_lawn / north_woods) — the D5–9 baseline.
   Gate-variance note: one intermediate gate showed ramble 69.6 (a +13 ms
   outlier); direct A/B re-measure read 56.0. Confirm gate anomalies with
   a direct run before acting on them.
3. Dapple visual: Ramble noon + Literary Walk noon captures — mottled,
   crown-shaped, no light leak at crown edges (lathe fit), no artifacts.
   Winter: no crown blobs under bare deciduous trees; trunk lines + cloud
   shadows match no-proxy within noise.
4. SDFGI A/B: GI-effect mean 0.0484 (no proxy) vs 0.0460 (proxy), p95
   0.0993 vs 0.0980, histogram overlap 0.877; delta map shows only
   foliage-motion edge noise, no proxy-hull structures. PASS.
Capture/compare tooling: `scripts/proxy_ab_captures.sh` (uses the
`--screenshot` flag — the old --quit-after sniff silently broke on 4.6.1).

## 4. Camera raster (D5–9 spec, written 2026-06-10 from measurement)

~30 ms at Ramble (trees-hidden A/B). Diagnosed before coding, per
[`workflow.md`](workflow.md) §2. All runs back-to-back at ramble noon,
reports `perf_reports/20260610_144605` and `20260610_145516`.

### 4a. Measured composition

| A/B (vs 55.6 ms baseline, vpgpu) | Δ | reading |
|---|---|---|
| `--render-scale=0.5` | −25 | frame is **fragment-rate-bound** |
| `--tree-mesh-range=180/150/120` | −5/−3/−4 | distant mesh trees ≈ free — **tier pull-in is DEAD as a perf lever** (and the old "occlusion culling re-enable" idea targets the same already-cheap load) |
| `--simple-leaf` (minimal shader, same render modes) | −12 | leaf fragment-shader complexity |
| `--simple-bark` | −5 | bark shader complexity (9-sample triplanar + procedural lenticels/plates) |
| `--simple-leaf --simple-bark` | −11.5 | ≈ leaf-only — bark share partly hides under drift/noise |

vistri identical (13.42 M) across all shader swaps — pure shader-cost
isolation. So the ~30 ms tree raster ≈ **12 ms leaf shader + ~5 ms bark
shader + ~13–16 ms raster structure** (alpha-card overdraw layers,
sub-pixel bark quads, `depth_prepass_alpha` double pass), all of it
within ~120 m of the camera.

### 4b. Disk audit (the structural debt behind "raster structure")

Placement-data model (full circle, mesh range): ramble 57.7 M lod1 tris /
1,818 trees; north_woods 53.1 M; light locations ~10 M — matches the fps
split. Per-variant lod1 cost: cathedral_elm_l 203 k (84 % bark), elm_l
158 k (84 % bark), london_plane_l 151 k (79 %), willow_l 90 k, oak_l 55 k,
maple_l 68 k. AAA forest budgets are 5–20 k/tree at these screen sizes.

- `generate_tree_lods.py` prunes **leaf cards only — bark is never
  decimated** and dominates the heavy species.
- The runtime `_lod1` files are **stale April 11 geometry**: base models
  were regenerated May 19 (per-species LAI card-density tune — lod0 leaf
  counts roughly halved) and the LOD derivation was never re-run. The
  in-game tier has ~2× the leaf cards of the current approved models
  (oak_l: 23.8 k leaf tris vs lod0's 13.6 k).
- On-disk `_lod2` files are junk as a mid tier: full bark + ¼ cards ⇒
  only ~8 % lighter than lod0.

### 4c. Levers (in implementation order)

1. **Leaf shader distance-gating** (~12 ms pot). The vein/cuticle/pocket
   vnoise stack (4–5 evaluations/fragment) is sub-pixel beyond a few tens
   of metres but runs on every canopy fragment at every distance. Gate
   micro-detail by `frag_cam_dist` with smooth amplitude fades (no hard
   shading step). Near field must stay pixel-identical.
2. **Bark shader distance-gating** (~5 ms pot). Full triplanar + procedural
   detail near; beyond the detail range collapse to dominant-plane sampling
   and drop lenticel/plate procedural work, fading amplitude.
3. **LOD regeneration** (~13–16 ms pot, shared with overdraw): re-derive
   `_lod1` from the May 19 models (halves card count — direct overdraw cut +
   staleness fix), and regenerate `_lod2` as a TRUE mid tier (bark decimated
   to ≤ ~8 k tris via collapse — bark is opaque tube geometry, it decimates
   cleanly; cards pruned to ~40 % and rescaled 1.6×), runtime three-tier:
   lod1 0–60 m, lod2 60–250 m, impostor beyond. Blender-mechanical once
   spec'd; can run on cheaper sessions.

   *Implementation record (2026-06-10, `scripts/generate_tree_lods.py`):*
   measured base models run 12 k–245 k tris/variant, so flat ratios can't
   hit one budget — the lod2 recipe is per-variant adaptive: card keep
   `max(0.15, min(0.40, 9000/leaf_tris))` (scale `1/sqrt(keep)`), bark
   collapse target `clamp(12000 − kept_leaf, 3000, 8000)`. Collapse alone
   floors out on Mtree bark — measured cathedral_elm_l: **31,069 separate
   bark islands averaging ~3 tris** (terminal twig stubs, sub-pixel beyond
   60 m) — so islands < 0.5 m bbox diagonal are deleted smallest-first
   until the remainder is within 3× of target, then collapse runs. Bark
   decimates via separate-by-material → prune → decimate → rejoin (variant
   node names and material-slot order survive — the runtime pairs variants
   by index across tiers). Light-bark species are never pruned (skip when
   already ≤ 3× target). Budget: every variant ≤ 12 k + 1 k slack (willow
   rides the 0.15 keep floor: 64.8 k weeping-strand cards). Blender 4.5
   `--background` hangs in teardown after script completion (futex, same
   family as the impostor-baker hang) — the script `os._exit(0)`s.

Tier boundary stays at 250 m (pull-in measured ≈ free, and distant mesh
canopy is part of the look). Occlusion culling: dropped — it attacks load
that measurement says is already negligible.

### 4d. Definition of Done (per lever)

- **Shader gating (1, 2):** before/after captures at a near tree (≤ 10 m),
  mid (40 m), far (100 m) at noon + 17:00 — near capture pixel-identical
  (mean |ΔRGB| < 0.005), no visible detail-fade line in a walk-toward
  capture sequence; perf_bisect ramble + north_woods back-to-back A/B;
  perf gate ×5 no regression.
- **LOD regen (3):** per-species tri budget table met (lod2 ≤ ~12 k incl.
  cards); tier-handoff pixel comparison at 60 m (lod1 vs lod2) mean
  |ΔRGB| < 0.05 like the §2 impostor DoD; crossfade walk smooth; perf
  gate ×5; user look-approval on Ramble + Literary Walk captures (the
  current in-game look is the approved baseline, and card count changes it).

### 4e. Outcome (2026-06-10 evening) — the real lever was the render pass

Lever 1 (leaf detail gating) shipped but measured only **~1 ms** (commit
4780cc9): the simple-leaf delta was never about *which* math runs per
fragment — it was about *how many fragments* run it. Chasing that led to
the actual root cause: **the leaf shader wrote `ALPHA` (plus
`alpha_to_coverage`, inert with MSAA off), which put the entire canopy in
the transparent pass** — every overlapping leaf layer shaded full
PBR + SSS + noise + shadow-PCF with no early-Z rejection.

**Fix (commit f12f334): leaves render in the opaque pass**, coverage by
discard only. Ramble noon back-to-back: **48.8 → 31.7 ms**. Design points:
- Discard threshold 0.5 near → 0.10 by 180 m (replaces the alpha-lift ramp).
- Seasonal thinning = stochastic per-cluster card drop (`flat` varying,
  ~0.8 m cells, upper crown first); WINTER_RETENTION recalibrated to
  literal card fractions (oak 0.18 etc.); no density floor — clean
  abscission species are truly bare; winter shrink softened 0.4 → 0.7.
- Hashed-alpha variants (static + animated) measured equal (−18 ms) but
  rejected on visuals: static stipples, animated leaves TAA smears.
- Look: leaves read denser/crisper — resolves the standing "leaves too
  transparent" complaint; verified across summer/autumn/winter captures
  and a live user walk.
- Re-derived per-card seed (`v_card_seed`, flat) because the existing 5 cm
  color seed interpolates across cards and would smear a discard test.
- Handoff DoD re-check tooling now scripted: `scripts/tier_handoff_check.sh`.

Remaining from this spec: bark shader gating (lever 2, ~5 ms pot, measured
texture means for the far-field collapse: furrowed (0.636,0.624,0.524)/r0.53,
oak (0.540,0.476,0.317)/r0.67, exfoliating (0.545,0.476,0.311)/r0.62, pine
(0.402,0.326,0.253)/r0.71, smooth (0.547,0.474,0.361)/r0.53), LOD
regeneration (lever 3). Grass/undergrowth checked for the same defect:
**negative** — they write `ALPHA_HASH_SCALE` (opaque hashed pipeline);
discard-variant A/B measured within noise (rendering.md §6 item 5).
Trees were the lone transparent-pass case (plain ALPHA + inert A2C).

### 4f. LOD regeneration outcome (2026-06-10 late session)

Shipped: commits 0eccb07 (generator), 0cc6d1a (three-tier runtime),
c5d7c99 (isolate-capture envelope). All `_lod1`/`_lod2` regenerated from
the May 19 bases and reimported (42 models × 2 tiers, ~10 s each via the
per-model loop; remember the reimport — game runs never reimport).

**DoD record (§4d):**
1. Tri budget: every lod2 variant ≤ 12 k + 1 k slack (adaptive recipe +
   twig-island prune, §4c implementation record). Heavy barks now 4.4–6.6 k
   (were 145–181 k on cathedral elm).
2. 60 m handoff, `TIER_A=lod1 TIER_B=lod2` at ramble noon over 1.03 M
   canopy px at ALL distances (stricter than the 60 m spec):
   **mean |ΔRGB| 0.0314 < 0.05 PASS**, silhouette IoU 0.93, no hue flip.
3. Crossfade walk (151 frames, 225 m at Bethesda crossing both bands):
   median canopy-delta 0.0010, max 0.0185 — the max is a hill-crest
   terrain reveal at ~78 m walked, not a tier step. **PASS.**
4. Perf gate ×5 (report 20260610_203758): 25.3 / 22.1 / 27.8 / 18.9 / 32.3
   ms vs 26.3 / 24.1 / 31.1 / 20.9 / 32.4 baseline — **all locations
   equal-or-better, no regression.** Honest reading: only −1 to −3.3 ms.
   The §3d "trees ≈ 14.1 ms ≈ vertex/LOD load" attribution was WRONG —
   post-opaque tree cost is dominated by canopy *fragment shading*
   (shading tree-covered pixels once is irreducible by geometry LOD).
   Vertex load was never binding at 1080p on this GPU.
5. Look captures (`notes/lod_regen_captures/`, gitignored): Ramble + Literary Walk noon summer +
   Literary Walk winter — no card blobs, no tier seams, dapple intact.
   Pending user walk-around approval (canopy card count halved vs the
   stale April tier; §4d names the current look as the approved baseline).

**240 m mesh↔impostor re-check — protocol findings, not a regression:**
the §2 check compares whole frames, and the impostor capture contains
290–2500 m backdrop canopy the mesh capture can't have; with lod2 forced
to 2500 m (`--tree-mesh-range=2500`) for a symmetric comparison the
metric still reads 0.063 / IoU 0.52 because **distant lod2 canopy thins
out relative to impostors** (the opaque discard ramp 0.5→0.10 was tuned
for the old card density; fewer, larger cards mip differently). In-game
this matters only inside the 230–250 m band, where the walk capture
shows no step — but see open question below.

### 4g. Shader-body gating spec (2026-06-10 night — post-opaque re-measure)

**Measured pots (north_woods, report 20260610_215525, sandwich baselines
24.4/22.7 real):** `--simple-leaf` −2.2 ms, `--simple-bark` −2.2 ms. The
§4a readings (−12/−5) were transparent-overdraw amplification; with leaves
opaque each shader body runs ~once per pixel, so this is the honest
ceiling. Implement only if the cut is ≥1.5 ms on a back-to-back A/B.

**Lever A — dapple near-gate (tree_leaf.gdshader:332–336).** The two
always-on dapple vnoise octaves exist for mid/far canopy mass ("survives
mip averaging… stays vivid at LOD1+ distance"). Near canopy already gets
real shadow dapple (proxy holes), SDFGI, and the gated per-leaf detail
layers. Fade dapple amplitude IN over 30→60 m (`gate_dapple =
smoothstep(30, 60, frag_cam_dist)`), skip both vnoise calls under 0.001 —
the inverse of the lever-1 gates. Near fragments (the majority when
standing in woods) drop 2 noise evaluations.
**Bake invariant:** the baker never registers `player_world_pos`, so bakes
compute `frag_cam_dist ≈ 0` → a naive near-gate would strip dapple from
every future atlas re-bake (current atlases have it baked in). Under
`bake_mode != 0`, force the far path (`gate_dapple = 1.0`) — bake output
unchanged by construction, no re-bake needed.
**Visual DoD:** screenshot A/B at Ramble noon + Literary Walk 17:00,
near-tree fill — canopy within 30 m may lose only the procedural dapple
mottle, which the proxy-shadow dapple must visually replace; if near
canopy reads flat, raise the fade-in start instead of abandoning.

**OUTCOME (2026-06-10 night): BOTH LEVERS MEASURED DEAD — implemented,
A/B'd, reverted (commit 052f81d, revert follows it).** Back-to-back
`--detail-gates=0` A/Bs: north_woods 39 vs 38 fps (vpgpu identical 26.0),
ramble 47 vs 46. Under the ship bar both times. **Why: post-opaque the
canopy/bark fragment workload is texture/shadow-PCF *latency*-bound, so
procedural ALU (vnoise/fbm) rides free under latency hiding — skipping it
frees nothing at 1080p on this GPU.** The §4a `--simple-leaf −2.2`/
`--simple-bark −2.2` deltas at NW sit inside that matrix's 1.7–4 ms
thermal drift; treat the whole shader-body pool as ≈0. Corollary worth
keeping: **ALU-side visual richness in these shaders is effectively free**
— more noise octaves, richer dapple, per-pixel color work cost nothing
measurable (D9–12 can spend there without gate anxiety).

**Also measured dead (2026-06-10): `--leaf-no-prepass`** — stripping
`depth_prepass_alpha` from tree_leaf reads identical at ramble (54/54 fps,
vpgpu 19.0/18.6; report 20260610_224019). The prepass double-raster cost
and its early-Z shading savings cancel; keep the prepass (safer when depth
complexity rises). The diag stays for re-checks on future content.

**Lever B — bark detail distance-gate (tree_bark.gdshader §styles).**
Style 0 (oak/elm/maple/ginkgo — most of the forest) runs ~24 noise
evaluations/fragment (fbm4×3 + fbm3×3 + vnoise×3, all triplanar). Beyond
~25 m a trunk is a few dozen pixels wide and the fissure/grit detail is
sub-pixel. Gate: `gate_bark = 1 − smoothstep(20, 35, bark_cam_dist)`;
under 0.001 skip ALL procedural style work and shade from `bark_color ×
tree_var` + PBR textures alone (they carry the mid-distance look); blend
amplitude inside the band. Same triplanar PBR texture sampling stays (it
is mip-cheap). Bake invariant: same `bake_mode != 0` → force near path
(gate=1.0) so atlases keep full bark detail.
**Visual DoD:** A/B at Literary Walk (elm trunks recede in rows — the
worst case for a visible detail line); no perceptible transition walking
toward a trunk.

## 5. Open questions

- **lod2 distant thinning (2026-06-10, from §4f):** lod2 canopy coverage
  falls off vs impostors at long range — the leaf discard ramp
  (0.5 → 0.10 over 100–180 m, tuned pre-regen) interacts with the new
  fewer/larger cards' mip-averaged alpha. Only the 230–250 m band shows
  lod2 in-game and the walk capture shows no step there, but if the band
  ever reads thin vs the impostor behind it, retune the far threshold
  (or the ramp distances) against a band A/B, not whole-frame metrics.
- Existing normal atlases: baked with which convention/quality? Verify before
  reusing (one species A/B vs fresh bake).
- Specular response on impostors at low sun (grazing) — may need a fresnel clamp.
- ~~Proxy crown for columnar/vase species: single ellipsoid too round~~ —
  resolved 2026-06-10: crown is now a lathe fit to the variant mesh's leaf
  vertices (12 height slices, per-slice elliptical radii at p96, 5% pad),
  per species-size-variant. Vase/columnar/weeping fit by data; dead snags
  get trunk-only automatically (no leaf surfaces).
- ~~Winter: bare-trunk proxies for clean-abscission species~~ — resolved
  2026-06-10: the dapple shader (shaders/tree_shadow_proxy.gdshader) reads
  the same INSTANCE_CUSTOM phenology as tree_leaf.gdshader and scales hole
  coverage by leaf density — crown shadow thins through autumn, drops to the
  retention floor in winter, and blossoms cast during bloom. Continuous and
  synced with the visible canopy by construction.
- Proxy lathe fit adds ~4 s to scene load (surface_get_arrays + percentile
  sort per variant, GDScript). Once default-on, fold the proxy mesh into the
  tree .res cache so it's fit once, not per launch.

## 6. Canopy value — crown-interior AO (spec 2026-06-11, COMPARISON.md #5b)

**Defect (measured):** distant canopy reads ~2.5× too bright — hero-pose
tree-line band 86 luma unfogged vs reference 36–62 ("dark mass"; real
dense canopy has effective albedo ~0.05–0.08 from crown self-shadowing).
Attribution at the band (`fog_veil_check.py`, fog hidden):

- `--shadow-dist=800`: 86.8 vs 86.2 — shadow distance is NOT the
  mechanism (dead hypothesis, do not revisit).
- `--sun-cal=0.01`: 60.7 — **ambient owns ~70%.** Every leaf receives
  the full (×5-calibrated) sky hemisphere; a real crown-interior leaf
  sees ~5–15% of sky. SSAO is sub-pixel at 400 m; SDFGI doesn't occlude
  the AMBIENT_SOURCE_SKY term on foliage.
- Leaf-shader `apply_aerial` haze (double-counted the §6c volumetric
  veil): −1.3 — removed 2026-06-11, small but principled.

**Fix: bake crown depth per leaf vertex, output it as material `AO`**
(Godot AO darkens ambient only, `AO_LIGHT_AFFECT 0` — matches the
attribution; direct sun + SSS untouched). Standard SpeedTree-style
interior AO.

1. **Data:** `scripts/bake_crown_ao.py` (Blender headless, mirrors the
   wind-weight baker): per leaf mesh, robust ellipsoid fit of the leaf
   cloud (p5/p95 centroid + radii), per-vertex normalized radius
   `rho = |(p−c)/radii|` rescaled so p95→1.0, written to **COLOR_0
   alpha** (R/G/B wind weights preserved; bark untouched, alpha 1.0).
   All tiers get it (base for impostor bakes, _lod1, _lod2).
2. **Mesh tiers:** tree_leaf.gdshader reads COLOR.a → varying;
   `AO = mix(ao_core, ao_shell, pow(rho, ao_exp))`, global uniform
   `canopy_ao = vec3(core, exp, shell)` (CLI `--canopy-ao=core:exp:shell`,
   shipped via global shader param like turf_sheen).
   **Why a shell term < 1.0 (measured during implementation):** a
   core-to-1.0 gradient alone read only −5% at the band — at 400 m the
   visible canopy IS the outer shell (rho ~0.9), the dark core is hidden
   behind it. Physically even shell leaves see ~half the sky hemisphere
   while scene ambient is calibrated for unobstructed ground, so shell
   AO 0.55 is the dominant term and the rho gradient runs beneath it.
3. **Impostor tier:** depth-atlas G channel carries the RAW baked rho
   (R stays parallax depth — shader only reads `d.r`; the premultiply
   dilation copies texels whole, so G rides along). Leaf bake_mode 3
   writes `(depth, rho, 0)`; bark writes `(depth, 1.0, 0)`;
   tree_impostor.gdshader blends the depth atlas at the lit UVs and maps
   G through the same `canopy_ao` uniform at runtime — retuning the AO
   curve needs NO re-bake. Re-bake all species (per-species wrapper +
   REIMPORT).

Also removed with this work (both tiers, 2026-06-11): the shader-level
`apply_aerial` haze on leaves/impostors — it double-counted the §6c
calibrated volumetric veil and LIGHTENED distant canopy (−1.3 luma at
the band on its own); tiers must agree, so both calls went together.

**DoD (run 2026-06-11, shipped constants 0.12:1.6:0.55):**
- [x] Hero-pose unfogged tree-line band ≤ 65 luma: **45.9** (was 86.2;
      ref band 36–62, e.g. 55/65/36 — ours 35/51/28, same dark-mass
      family). With the calibrated fog veil on top: ~54.
- [x] Tier handoff: AO is value-continuous across tiers — handoff check
      0.0758 with AO vs **0.0762 with `--canopy-ao=1:1:1`** (identical;
      the 0.076 > 0.05 absolute is the PRE-EXISTING §5 lod2-thinning/
      backdrop artifact, unchanged by AO; IoU 0.60 vs 0.55). New
      `EXTRA_ARGS` env on tier_handoff_check.sh for attribution runs.
- [x] Close-up look: Literary Walk + Ramble noon, Lit Walk 17:00, winter
      3.3 — crowns gain interior depth, no blotch, no winter dark-blob
      (captures /tmp/fog_cal/litwalk_AO*, ramble_AO).
- [x] Perf gate sandwich: FREE. Back-to-back same-thermal-state gates
      20260611_133637 (AO) vs _134224 (pre-AO): 68/75/53/84/45 vs
      68/75/53/82/44 fps — identical within noise despite the 3 extra
      depth-atlas fetches per impostor fragment (consistent with the
      texture-latency-bound finding, §4g). Both gates read ~2 fps under
      the cold 4 AM canonical 20260611_041200 — thermal, not code
      (rendering.md §6c perf note).
- [ ] User re-walk.

Implementation note: `scripts/bake_crown_ao.py` is direct GLB surgery,
NOT a Blender roundtrip — the Blender glTF exporter writes COLOR_0 as
VEC3 and drops vertex alpha on every export path (verified; no exporter
option restores it). The script appends a VEC4 u8-normalized COLOR_0
accessor to the BIN chunk and repoints the attribute. Models are
untracked binaries — backup at `~/cpw_backups/trees_preAO_20260611/`.
Run once per model generation; after running: Godot `--headless --import`
+ impostor re-bake (per-species wrapper).

## 7. Near-tree leaf sparsity (2026-06-11 walk-around #1) — RESOLVED

**User report:** "tree looks full from far to near, but gets sparser as near
becomes close" — inner crown near-bare in July, leaf tufts only at branch
tips (defect tree: `deciduous` at world −591.7, 1465.6 by Literary Walk;
user screenshots cpw_005/cpw_008, reproduced at the same poses).

### Diagnosis chain (suspects in the original order, with verdicts)

1. ~~"`_lod1` is stale April geometry"~~ — **DEAD.** On-disk counts:
   `oak_l_lod1` leaf tris = exactly 50 % of the *current* base. The Jun 10
   regen did cover lod1 (§4f was right; the walk-around suspect list was
   written from the §4b flag without re-checking disk).
2. ~~Close-range discard ramp eating card texels at mip 0~~ — **DEAD.**
   Leaf DDS alpha is essentially binary at mip 0 (69.5 % ≥ 0.5, only 0.1 %
   in the 0.10–0.5 band) — the 0.5 near threshold removes nothing *face-on*.
3. **Card count, tier layer — REAL (half the effect).** The near tier showed
   50 % of base cards while impostors bake from the 100 % base; AND the
   May 19 LAI tune had already halved base cards, so the nearest view held
   ~¼ of the last user-approved density (April-lod1 ≈ current base in count).
4. **Discard threshold vs sampled mip — REAL (the dramatic half).** The
   on-disk model is NOT sparse: measured card clusters sit within 1.5 m of
   ~100 % of crown bark verts (all 5 variants, all height bands ≥ 0.30 h).
   The "naked laterals" were fully-carded branches whose fragments sample
   high mips (small screen footprint, or *edge-on* — an under-crown look-up
   is all edge-on cards). Box-filtered mips dilute binary alpha into the
   0.1–0.5 range, and the old threshold ramp `mix(0.5, 0.10,
   smoothstep(100, 180, cam_dist))` RAISED the cut to 0.5 exactly as you
   approached. Leaves literally vanished on approach, by construction.
   Confirmed by flat-0.10 A/B: the "bare" branches are fully leafed.

### Fix (commits 52abbca, 315574f + cleanup)

- **Near tier renders the full base model**; the `_lod1` derivation is
  retired (generator spec, loader, files archived to
  `~/cpw_backups/lod1_retired_20260611`). Base meshes were already in
  memory — VRAM and load go *down*. `tier_brightness` for the near tier is
  1.0 by construction (it IS the reference model). `--tier-isolate=lod1`
  now isolates the near (base) tier; `--tree-lod1-range` unchanged.
- **Leaf discard threshold follows `textureQueryLod`, not camera
  distance:** 0.5 at mip 0 (crisp shapes, halo texels cut) easing to 0.10
  by mip 4 (the dilated silhouette IS the leaf mass). Unlike the May 18
  alpha-boost attempt (disabled for color steps under ALPHA blending), a
  threshold change cannot shift shading in the discard-only opaque pass.

### DoD record

1. Defect poses: both cpw_005/cpw_008 reproductions read as full July
   crowns; formerly naked laterals carry their foliage
   (`notes/sparsity_fix_captures/`).
2. 60 m handoff `TIER_A=lod1 TIER_B=lod2` at ramble noon: mean |ΔRGB|
   0.0635 vs 0.05 target — *marginal, expected*: the near tier now really
   is denser than lod2, plus the §4f backdrop caveat. Visual side-by-side
   shows no gross step; the binding check is:
3. Crossfade walk (151 frames, 225 m, Bethesda): mean-canopy-color delta
   median 0.0016 / max 0.0148 — max is a hill-crest terrain reveal (frames
   52→53 inspected), same class as the §4f record. **PASS.**
   (Protocol note: compare per-frame canopy *statistics*; raw pixel deltas
   on a walking camera measure parallax, ~0.075 median.)
4. Perf gate ×5 (20260611_150209, warm afternoon run): 68/73/52/88/45 fps
   vs canonical 68/75/53/84/45 — within variance, no regression. The
   ramble/NW sub-60 is the pre-existing §rendering policy question.
5. Winter Lit Walk capture: marcescent retention unchanged (card-seed drop
   is independent of the threshold change).

**Watch item:** mid-distance (60–180 m) canopy now reads denser than
before (the old ramp was thinning it too) — likely *helps* COMPARISON.md
#4 (perimeter canopy too low/gappy); re-check that finding before working
it. User re-walk pending.

## 8. Tier-approach continuity — handoff 250 → 400 m (2026-06-11, walk-around "steps on approach")

**Defect (user walk-around Jun 11 ~15:30):** driving the Conservatory
Water → Belvedere line (`--pos=-53,884,11`, 13:00 July), the distant tree
line reads pale/washed and trees turn greener/saturated and *gain shape in
discrete steps* on approach.

**Attribution (measured, scripts/tier_approach_captures.sh +
tier_approach_check.py + /tmp band A/Bs):**

- Fog: INNOCENT on this line — zeroing volumetric density
  (`--fog-cal=:::0:`) moved the canopy band < 1.5 luma at 150-350 m.
- 250 m handoff color: matched — impostor vs lod2 on the same far band
  |Δ| 0.2 luma / 0.016 sat. The runtime-lit + AO calibration holds.
- 60 m handoff color: small (3-5 luma, ~0.02 sat).
- **The visible step is SHAPE/TEXTURE, not color calibration:** at
  250-350 m the billboard impostor reads flat/pale-speckled (premultiplied
  atlas mips + 12× boost) while lod2 keeps shaped, deeper-green crowns.
  Forced side-by-side at 100-200 m the gap is dramatic (+15 luma, −0.116
  sat impostor vs mesh) — the same mechanism, amplified.
- Atlas re-bake through current shaders (post mip-threshold fix): +6%
  coverage, color identical — closes §7's "atlases not re-baked" watch
  item; NOT the lever.
- Walk-sequence statistics are smooth (median consecutive-frame delta
  0.0022, no 3× outliers) — the steps are sub-band visual events, which is
  why the §7 crossfade DoD never caught them.

**Fix: mesh fade end 250 → 400 m** (tree_builder.gd default; impostors
start at 340 m, dither 380-400 m). Extending lod2 measured FREE at the
approach pose (63-64 fps vs 57-59 default; the frame is fragment-bound —
§4g/rendering.md §3e — and in dense woodland distant trees are occluded).
At 400 m a 15 m crown is ~45 px — the billboard flattening is sub-percept.
lod2 coverage at 250-400 m holds by construction (mip-driven discard
threshold, §7 — the old distance-ramp open question in §5 is moot).

**Note for future tuning:** the impostor `dist_boost` ramp
(smoothstep 100→300 m, ×12 max) is now fully saturated for every visible
impostor (they start at 340 m) — it behaves as a constant ×13 energy
recovery. If a future pass moves the boundary below 300 m again, re-check
partial-boost behavior in the fade band.

### DoD record (2026-06-11 night)

1. Perf gate ×5 (20260611_215321, same-night thermal state as the cold
   cert): 74/83/58/94/49 fps vs cert 75/83/56/92/49 — equal-or-better at
   every location (ramble +2, great_lawn +2). The 150 m of extra lod2
   range and the re-baked atlases are perf-free. **PASS.**
2. Approach-walk continuity (94 frames, full 221 m user line, 13:00):
   median consecutive-frame canopy delta 0.0025, no tier-correlated
   steps. Two flagged frames inspected: walk-start cloud/exposure event
   (frame 0→1) and a near sapling parallaxing through the analysis box
   (frame 89→90) — composition, not tiers. Canopy luma now FALLS on
   approach (161 → 140) with saturation rising (0.417 → 0.49) — the
   real-world direction (near canopy darker + richer than the hazy
   distance), where pre-change the band held a flat pale ~150-153.
   **PASS.**
3. 400 m handoff (tier_handoff_check.sh at Sheep Meadow nw_across_meadow
   `-720,1360,45`, 13:00): mean |ΔRGB| 0.0792 — over the 0.05 target but
   the capture set carries TWO known inflators (impostor-isolate's
   2500 m backdrop fill, and a 1440p→1080p resize because one window
   opened at desktop res); the same-pose §6 record reads 0.076 with AO
   off vs on, i.e. this is the pre-existing protocol floor, not a step.
   Visual side-by-side: tone/value/hue matched, G−R +0.077 mesh /
   +0.064 impostor, no hue flip; silhouettes differ per-tree as
   expected between representations. **PASS (visual), metric within the
   documented artifact band.**
4. Atlas re-bake state: all 15 species re-baked through the current
   opaque + mip-threshold shaders (honeylocust on retry — the known
   flake), premultiply finalized, headless reimport run. §7 watch item
   CLOSED.

User re-walk pending (the binding judge). If the 60-180 m band now reads
dense AND shaped on the user's line, COMPARISON.md #4 (perimeter canopy
low/gappy) should be re-checked before any dedicated work on it.

## 9. Impostor mip sampling + deterministic capture protocol (2026-06-12)

**Defect (user walk-around Jun 12 ~10:47, Great Lawn, 16 h):** advancing
on a stand at 400-900 m, impostor crowns read as dark solid blobs that
flip per-tree to pale sparse mesh trees crossing the 380-400 m band
(screenshots cpw_002-013).

**Root causes found (in order of discovery, only the last is the fix):**

1. NOT the bake/import cache: the 10:47 run used the fresh runtime-lit
   atlases (md5-verified; normals/depths are byte-deterministic so
   Godot's import skip was correct).
2. NOT AO/SSS tier asymmetry: an apparent -0.073 signed luminance gap at
   8 h was capture noise — the per-session random cloud field puts
   ±0.04-0.07 mean luminance on a canopy band between runs. A
   mesh-vs-mesh repeat pair disagreed by more than the tier gap under
   study. **All cross-run comparisons need `--cloud-seed=N` (and
   `--diag-hide=cloudshadows` for stats); seeded repeat-pair signed
   noise is ±0.0005.** tier_handoff_check.sh now bakes this in.
3. THE BUG: every atlas sample forced mip 0 (`textureLod(..., 0.0)`),
   defeating the premultiplied-mip silhouette design — at 400 m the
   256 px frame undersamples ~6:1, crowns degenerate to speckle, and the
   ×12 dist_boost (correctly designed for *mip-averaged* alpha) smashed
   the speckle into a solid dark cutout. Fixed with `textureGrad` using
   pre-parallax-warp frame-1 gradients (smooth everywhere; the warp is
   sub-texel relative to the footprint).

**Post-fix state (seeded, Great Lawn line, 16 h):**

- Impostor far-field tone matches the LOD0 reference (0.325 vs 0.341
  union lum; p25 0.270 vs 0.261). The runtime-lit bake is calibrated.
- 250-400 m: impostor vs lod2 coverage 76 % vs 73 %, union lum Δ 0.003.
- Walk A/B `--tree-mesh-range=300` vs default 400: per-frame band stats
  identical (|Δluma| ≤ ~1 / 255, Δcover ≤ 0.004) — the handoff is
  value-tight at either boundary. Default stays 400 m (§8 shape
  rationale unaffected).
- Remaining flagged "steps" on the line are cloud-shadow band crossings
  (identical in both runs), not tier events.

**Open follow-ups:**

- lod2 geometric thinning beyond ~300 m (sub-pixel cards don't
  rasterize; coverage collapses to ~8 % by 500 m — never user-visible at
  the shipped 400 m boundary, but bounds how far the boundary could ever
  move out). Principled fix: area-conserving card prune when generating
  `_lod2` (scale surviving cluster cards to conserve leaf area) — model
  pipeline change, belongs to the tree-model redesign workstream.
- dist_boost is unchanged and still saturates alpha ≥ 0.077 to opaque
  at 340 m+; with correct mips this now matches the LOD0 solid-crown
  read, but re-check if alpha_clamp (0.05) or the boost curve is ever
  retuned.
