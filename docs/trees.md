# Trees — tier spec, runtime-lit impostors, shadow proxies

Spec for the D3–5 sprint work (written 2026-06-10, before implementation, per
[`workflow.md`](workflow.md)). Budget lines this subsystem spends
([`rendering.md`](rendering.md) §4): **camera raster 4.0 ms, shadow casting 1.0 ms**
at the worst test location. Measured today: ~25 ms camera (Ramble), 18–28 ms shadows.

## 1. Tier architecture (target state)

| tier | range | fade | representation | casts shadow | lit |
|---|---|---|---|---|---|
| mesh | 0–290 m | dither out 230–250 m | `{species}_{s,m,l}_lod1`, MMI per species-size × 80 m chunk | **never** (proxy does) | runtime sun + ambient |
| shadow proxy | 0–290 m | none (pops with cascade distance, invisible) | trunk cylinder + crown hull ≤ ~300 tris, alpha-test dapple mask, MMI `SHADOWS_ONLY` | is the shadow | n/a |
| impostor | 190–2500 m | dither in 230–250 m | 8×8 hemisphere octahedral, 2048² atlas per species-size (56 atlases) | never | **runtime sun + ambient (NEW)** |

Changes from today: visible mesh stops casting (proxy takes over); impostor albedo
becomes unlit so both tiers are lit by the same sun/ambient at runtime.

## 2. Runtime-lit impostors (kills the bake-mismatch bug class)

**Today's defect:** `tree_impostor.gdshader` is *shaded* (`diffuse_burley`, writes
`NORMAL` from the normal atlas) but the albedo atlas is baked **lit** under a fixed
sky (`impostor_baker.gd`: ambient 0.7, ground 0.55) — every impostor is lit twice,
patched by the `impostor_brightness` global (day_night_cycle.gd:93) and a ×3.0
luminance compensation in the fall recolor. Root cause of the May 19 dark-olive
atlas failure and all time-of-day mismatch bugs.

**Bake changes** (`impostor_baker.gd` + `bake_mode` uniform in
`tree_leaf.gdshader` / `tree_bark.gdshader` — implemented 2026-06-10):
- Albedo pass renders **unlit**: bake materials route the shader's final
  ALBEDO through EMISSION (`bake_mode=1`) under a black, ambient-disabled
  environment. The atlas stores the mesh tier's exact albedo output — all
  albedo-level character (top-light gradient fakes excluded only where
  view/light-dependent) — with zero lighting. Alpha from coverage as today.
- Normal + depth now bake in the **same Godot pass set** (`bake_mode=2/3`):
  the 2026-06-10 quality check found the Blender-baked atlases unusable —
  AgX view-transform distortion (constant +0.3 xy bias) AND framing baked at
  bounding-sphere radius while albedo uses AABB-diagonal radius (coverage
  IoU 0.32 on birch). Godot bakes all three channels from one scene/framing/
  alpha pipeline, aligned by construction. Normal = camera-space, flipped
  toward viewer (leaves are double-sided); depth normalized over 0..4R so
  tree center sits at the shader's 0.5 parallax reference. Normal/depth read
  back via HDR viewport (linear; LDR readback is sRGB-encoded — probed) to
  match their linear sampler hints. `scripts/bake_impostors.py` (Blender) is
  superseded entirely.
- Winter pass: same unlit rule; albedo only (normal/depth are season-independent).
- Post chain: `premultiply_impostors.py` (albedo premultiply — replaced the
  old dilate pass — plus neutral background fill for normal/depth so edge
  bleed through bilinear/mip filtering is a no-op).

**Shader changes** (`tree_impostor.gdshader`):
- Delete `impostor_brightness` fudge (line ~430) and its global registration +
  day_night writer once no shader reads it.
- Keep `NORMAL` path; set foliage-appropriate response (roughness 1.0, specular ~0.1)
  so burley diffuse dominates.
- Re-derive the fall-recolor mix for true-albedo luminance (the ×3.0 factor
  compensated baked-lit summer luminance ~0.33; with unlit atlases it's wrong).
- Per-tree jitter, world tonal fBm, snow, aerial perspective stay (they operate on
  albedo, which is now actually albedo).

**Validation (Definition of Done) — run 2026-06-10:**
1. Pixel-sample comparison mesh tier vs impostor at the 240 m handoff
   (`--tier-isolate=mesh|impostor` renders one pure tier, no crossfade) at
   8:00 / 12:00 / 17:00: mean |ΔRGB| over canopy pixels < 0.05, no hue flip.
   **PASS: 0.038 / 0.047 / 0.018, G−R sign preserved, silhouette IoU 0.73-0.81.**
2. Crossfade band shows no brightness step in a slow walk-through capture.
   **PASS: 36-frame walk 280→196 m, median frame delta 0.002, max 0.011
   (cloud drift, outside the band).**
3. perf_gate at all 5 locations: no regression. (Caveat below — the tier was
   not drawing at all before this date, so the honest baseline changed.)
4. Re-bake all species via the per-species wrapper (~12 s each, one Godot process
   per species — all-at-once hangs, see memory `lessons_impostor_bake.md`). **DONE.**

**Discovery (2026-06-10): the impostor tier had been invisible since P1.7.**
Commit `2c2334d` set the billboard `position_offset` to `-aabb.center` —
Blender's sign convention in Godot space — which shifted every billboard its
canopy-center height DOWN and buried the whole 190-2500 m tier under the
terrain. Confirmed pre-existing at c95ef42 via checkout + capture; fixed by
`+aabb.center` in tree_builder.gd. Consequences: every distant-canopy
observation made between P1.7 and this fix (including the 2026-06-09 perf
baseline) describes a world with NO impostor raster cost; perf numbers gain
a tier of transparent-pass quads from here on.

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
2. perf_bisect at ramble + north_woods: ≥ 15 ms / ≥ 25 ms reduction vs today's
   baseline, no other line regresses.
3. Dapple visual: noon + 8:00 captures under Literary Walk elms and Ramble canopy
   vs reference photos — mottled, not blob-dark, not stripe-artifacted.
4. No GI change: SDFGI on/off A/B identical before/after proxies (within noise).

**Prototype status (2026-06-10, flag `--tree-shadow-proxy`):** implemented incl.
dapple discard (coverage 0.62 broadleaf / 0.80 conifer, 1.1 m holes). Measured:
ramble 83→67 ms, north_woods 88→65 ms proxy-alone; 49/46 ms with filter-1 +
atlas-4096 stack (see rendering.md §3). Visual A/B pass at Mall + Ramble.
Outstanding before default-on: DoD items 1 & 4, crown fit for irregular/vase
archetypes (light leak where ellipsoid under-fills), winter trunk-only swap,
perf gate at all 5 locations.

## 4. Camera raster (follow-up, D5–9, spec'd separately)

~25 ms at Ramble. Levers, in test order: re-enable occlusion culling (canopy
occluder vs `visibility_range` conflict, `tree_builder.gd:703-706`), tier boundary
(290 m mesh range is generous), LOD1 triangle audit per species. Not part of D3–5
implementation; listed so the tier table above is read as the full picture.

## 5. Open questions

- Existing normal atlases: baked with which convention/quality? Verify before
  reusing (one species A/B vs fresh bake).
- Specular response on impostors at low sun (grazing) — may need a fresnel clamp.
- Proxy crown for columnar/vase species (Lombardy poplar, elm): single ellipsoid
  may be too round — fit per archetype, not one shape for all.
- Winter: bare-trunk proxies should swap to trunk-only (no crown shadow) for
  clean-abscission species; tie to the winter atlas season threshold.
