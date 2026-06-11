# Trees — tier spec, runtime-lit impostors, shadow proxies

Spec for the D3–5 sprint work (written 2026-06-10, before implementation, per
[`workflow.md`](workflow.md)). Budget lines this subsystem spends
([`rendering.md`](rendering.md) §4): **camera raster 4.0 ms, shadow casting 1.0 ms**
at the worst test location. Measured today: ~25 ms camera (Ramble), 18–28 ms shadows.

## 1. Tier architecture (target state)

| tier | range | fade | representation | casts shadow | lit |
|---|---|---|---|---|---|
| near mesh | 0–60 m | dither out 50–60 m | `{species}_{s,m,l}_lod1` (50 % cards × 1.41, full bark), MMI per species-size × 80 m chunk | **never** (proxy does) | runtime sun + ambient |
| mid mesh | 50–250 m | dither in 50–60 m, out 230–250 m | `{species}_{s,m,l}_lod2` (≤ ~12 k tris: adaptive card prune + bark decimation, §4c) | never | runtime sun + ambient |
| shadow proxy | 0–290 m | none (pops with cascade distance, invisible) | trunk cylinder + crown hull ≤ ~300 tris, alpha-test dapple mask, MMI `SHADOWS_ONLY` | is the shadow | n/a |
| impostor | 190–2500 m | dither in 230–250 m | 8×8 hemisphere octahedral, 2048² atlas per species-size (56 atlases) | never | **runtime sun + ambient (NEW)** |

Both mesh tiers spawn from the same per-chunk buckets (transforms + custom
data identical, crossfade water-tight); chunk visibility ends derive from
each chunk's actual max instance-to-centroid radius (the old fixed +40 m
margin could under-cover skewed chunks). Species without a `_lod2` (dead
snags) run the near mesh across the whole 0–250 m band. Diagnostics:
`--tree-lod1-range=N` moves the 60 m handoff; `--tier-isolate=lod1|lod2`
renders one mesh LOD across the full range (60 m handoff DoD);
`TIER_A`/`TIER_B` env vars on `tier_handoff_check.sh` pick the compared pair.

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
