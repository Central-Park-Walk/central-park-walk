shader_type spatial;

// Runtime-lit octahedral impostor (far tree LOD). Adapted from
// addons/Imposter/imposter/materials/shaders/ImpostorShader.gdshader (the proven
// Godot-community / Brucks octahedral billboard: 3-nearest-frame blend + virtual-
// plane parallax). Changes vs the addon:
//   * NO `impostor_brightness` global fudge — the albedo atlas is baked UNLIT
//     (scripts/bake_impostors.gd, bake_mode), so Godot lights it here via the
//     normal atlas + diffuse_burley. This kills the double-lit / time-of-day
//     mismatch bug class that sank the prior hand-rolled baker.
//   * `lod_fade_in` dither so the impostor crossfades into lod0 over the same
//     band the lod0 mesh dithers out (tree_builder sets it per instance group).
// Atlases are produced by scripts/bake_impostors.gd with a matching cell/direction
// convention (OctaUtils.octa_uv_to_world), so this decoder lines up by construction.

// OPAQUE, alpha-tested (depth_prepass_alpha) — NOT blend_mix. Required so the impostor
// can CAST shadows: Godot's transparent queue doesn't cast shadows, and a `blend_mix`
// material that writes ALPHA lands there. Discard-only coverage (no ALPHA write, like
// tree_leaf) keeps it opaque; the discard runs in the depth/shadow prepass so the cast
// shadow is the crown silhouette, not a solid quad. Visually identical to the old
// ALPHA=1.0 in the colour pass (it was never actually blended).
//
// shadows_disabled: the impostor does NOT RECEIVE shadows (it still CASTS them — casting
// is the instance cast_shadow=ON setting, tree_builder.gd; receiving is this render_mode).
// WHY: the billboard faces the CAMERA in the colour pass but the SUN in the shadow pass
// (tree_builder.gd:1576), so the two oriented planes intersect and the camera-facing crown
// self-shadows behind the sun-facing plane along their intersection — a dead-straight line
// bisecting the crown (Chris 2026-06-28, l·28m impostor). A planar gap of metres can't be
// closed by shadow bias, so the only clean fix is to stop the billboard receiving its own
// cast shadow. Crown form/depth still come from the normal-atlas directional shading + the
// baked ambient AO (AO=ormTex.r below) — soft, organic "darker in-shadow" pockets, not a
// hard line — so average tint/brightness/coverage are unchanged. Tradeoff: the impostor no
// longer takes building/neighbour/cloud shadows either, acceptable at the far LOD range and
// in line with keeping the far tier's average brightness consistent.
render_mode depth_prepass_alpha, cull_back, diffuse_burley, specular_schlick_ggx, shadows_disabled;

uniform vec4 albedo : source_color = vec4(1, 1, 1, 1);
uniform float specular = 0.1f;                 // foliage: low spec so diffuse dominates
uniform float metallic = 0.0f;
uniform float roughness : hint_range(0.0f, 1.0f) = 1.0f;
// Crown self-shadow fake: a flat billboard can't geometrically self-shadow its
// interior the way the volumetric mesh does, so optionally let the baked crown AO
// attenuate DIRECT light too (not just ambient). 0 = ambient-only (mesh parity).
uniform float ao_light_affect : hint_range(0.0f, 1.0f) = 0.0f;
// Deepen baked crown AO (interior occlusion) without darkening lit edges:
// AO = pow(ormTex.r, ao_power). >1 pushes the interior darker, edges (AO=1) stay 1.
uniform float ao_power : hint_range(0.25f, 4.0f) = 1.0f;
// AO floor: AO-on-direct on the near-zero trunk AO blacks the trunk out; this
// floors AO so the trunk stays visible. Crown interior AO (~0.42) is above it,
// so the floor rescues the trunk without lightening the crown.
uniform float ao_floor : hint_range(0.0f, 1.0f) = 0.0f;

uniform sampler2D imposterTextureAlbedo : source_color;
// source_color, NOT hint_normal: the bake viewport sRGB-ENCODES its framebuffer on
// get_image() readback (same LDR SubViewport as albedo/ORM — bake_impostors.gd bakes
// EMISSION = NORMAL*0.5+0.5, a LINEAR packed camera-space normal). Stored sRGB, it must
// be sRGB→linear decoded before the xy*2-1 unpack (below) to recover that packed value.
// hint_normal reads RAW (no decode), so a face-on normal component of 0 (packed linear
// 0.5 → stored sRGB ~0.735) unpacked to ~+0.47 instead of 0 — every baked normal carried
// a systematic +tangent skew (measured 2026-07-04: median opaque texel unpacked to
// +0.40 raw vs -0.10 decoded), bending N·L and mis-lighting the crown at low sun angles.
// The .import is byte-identical to albedo/ORM (plain RGBA8, compress/normal_map=0), so
// this is purely the runtime decode hint — matching how albedo/ORM already handle it.
uniform sampler2D imposterTextureNormal : source_color;
uniform sampler2D imposterTextureDepth : hint_default_white;
// source_color: the bake viewport sRGB-encodes EMISSION on readback (same as the
// albedo atlas), so the linear AO/roughness the leaf shader emitted is stored sRGB.
// Decoding it here recovers the linear AO the mesh actually applies (~0.42), not the
// sRGB-inflated 0.71 a linear sampler would read (which would under-darken).
uniform sampler2D imposterTextureOrm : source_color, hint_default_white;

// Sun-visibility L1 fit (bake_impostors.gd _bake_vis_channel): R = c0 (mean
// visibility), GBA = bent vector * 0.5 + 0.5, in BAKE-OBJECT space. fragment()
// evaluates clamp(c0 + dot(c_vec, sun_obj), 0, 1) so the crown's DIRECT-light
// self-shadowing tracks the REAL sun direction across the day. This replaces
// the static AO-on-direct fake (ao_light_affect), which was only right at its
// calibration hours — measured 2026-07-02: impostor/lod0 1.08x at 13h but
// 0.29x at 9h. LINEAR data (hdr_2d composite readback) — NO source_color.
uniform sampler2D imposterTextureVis : hint_default_white;
uniform bool has_vis_atlas = false;
// 0 = ignore the vis atlas (old behaviour), 1 = full sun-visibility. Sweep lever.
uniform float vis_strength : hint_range(0.0, 1.0) = 1.0;

// Subsurface-scattering (backlit transmission) strength — fix-ladder #2. The near mesh
// (tree_leaf.gdshader) GLOWS when the sun is behind it via Godot's built-in BACKLIGHT;
// this shader's custom light() BYPASSES that path, so the far tier had zero SSS. This
// folds the mesh's per-species leaf-thickness factor (london plane 0.6, magnolia 0.55,
// conifer 0.25 of the base) AND doubles as a global tuning lever. The impostor tier is
// london_plane-only today, so the default is london plane's 0.6; tree_builder sets it
// per-species (IMP_SSS env override) as other species get impostors. 0 = no SSS.
uniform float sss_strength : hint_range(0.0, 1.5) = 0.6;

// WINTER atlas set (baked at season_t=winter, card_keep=-1 → the leaf shader's own
// WINTER_RETENTION floor thins the crown to a near-bare skeleton + a few marcescent
// sprigs). Blended against the summer set by the per-tree phenology fraction
// (v_leaf_frac) so the far tier's SHAPE tracks season — summer airy, winter near-gone
// — instead of the old single summer blob merely recoloured. Gated by has_winter_atlas
// so tiers/species without a winter bake fall back to summer-only (no behaviour change).
uniform bool has_winter_atlas = false;
uniform sampler2D imposterTextureAlbedoWinter : source_color;
uniform sampler2D imposterTextureNormalWinter : source_color;  // sRGB-decode: see imposterTextureNormal above
uniform sampler2D imposterTextureOrmWinter : source_color, hint_default_white;

uniform vec2 imposterFrames = vec2(16.0f, 16.0f);
uniform vec3 positionOffset = vec3(0.0f);
uniform bool isFullSphere = false;             // foliage = hemisphere
uniform float alpha_clamp = 0.5f;
uniform float scale = 1.0f;
uniform float depth_scale : hint_range(0, 1) = 0.0f;
uniform float normalmap_depth : hint_range(-5, 5) = 1.0f;
uniform float aabb_max = 1.0;

// LOD crossfade-in band (begin, end) in metres. The impostor dithers IN over this
// band as the camera approaches, complementary to lod0's dither-out. vec2(0,0) off.
uniform vec2 lod_fade_in = vec2(0.0, 0.0);
// Player camera world pos (pushed from main.gd) — same source the mesh tiers use,
// so the crossfade discards consistently across shadow/reflection passes.
global uniform vec3 player_world_pos;
// World-space direction TO the sun (pushed from main.gd each frame) — the vis
// term needs the sun paired with the per-instance basis, which only exists in
// vertex (#76292), so light()'s LIGHT built-in can't be used for this.
global uniform vec3 sun_dir_world;
// Wind (world XZ dir + magnitude) — same global the mesh leaf/bark shaders sample, so
// the far crown rocks in lockstep with the mesh trees it crossfades into at the handoff.
global uniform vec2 wind_vec;
// Impostor crown wind sway amplitude (1 = matched to the mesh's gross crown motion).
// Global so it's live-tunable on a walk (main.gd I / Shift+I); registered in main.gd
// with default 1.0. 0 = static billboards (old behaviour).
global uniform float impostor_wind_strength;

#include "res://shaders/include/lod_dither.gdshaderinc"
#include "res://shaders/include/tree_species.gdshaderinc"
#include "res://shaders/include/wind.gdshaderinc"

// Season/foliage HUE applied at RUNTIME (option 2, 2026-06-24): the atlas is used as
// a LUMINANCE/detail map and the colour comes from the per-tree season tint (decoded
// from INSTANCE_CUSTOM, exactly as tree_leaf does). So the baked albedo HUE no longer
// matters: where the density-thinning (bake_density) drops cards and the bark shows
// through, it reads as darker-GREEN canopy variation instead of brown, and the far
// tier now tracks season (summer green / fall colour) per tree.
global uniform float season_t;
// Linear luminance of a full leaf atlas pixel — leaf areas map to ~v_season_color,
// darker (bark/dapple) areas to proportionally darker green. This is the ~p97 of
// opaque linear leaf luminance in the summer albedo atlas (a "full leaf" texel);
// texels below it render proportionally darker. RE-DERIVED 2026-07-05 against the
// post-137f286 s/m/l rebake (b66c106): ALL-tier p97 = 0.274 (was 0.277→stored 0.28
// on the pre-rebake 97e06ba atlas). The skeleton rebake barely moved this reference
// (−1.4%) — it changed COVERAGE (s +46%) and MEAN luminance (m +5.8%), which are
// density effects mirroring the denser lod0, NOT the per-texel full-leaf brightness
// this normalises. So this knob was only marginally stale; the material recalibration
// was the hue tint (tree_builder _imp_calib_tint). See project_impostor_system_rebuilt.
uniform float detail_ref_lum = 0.274;

// On-screen-size mip LOD. The atlas now carries mipmaps; the impostor selects a mip
// from the billboard's apparent size (real height vs camera distance) rather than
// fetching mip0 always. Without this, a far crown's sub-pixel holes + shading can't
// downsample and the binary scissor fills them solid → a flat dark-green blob past
// ~500m (measured 2026-06-27). world_height = the tree's real height (m, manifest);
// cell_px = atlas pixels per octa view; LOD is capped so mips stay within a cell
// (cells are packed gutterless, so deep mips would bleed neighbouring views).
uniform float world_height = 22.0;
const float IMPOSTOR_CELL_PX = 128.0;   // ATLAS_RES/FRAMES = 2048/16 (bake_impostors.gd)
// Mip cap. The mip's ONLY job here is to make the atlas ALPHA fractional so the hashed
// alpha test (below) can render see-through coverage instead of a binary scissor — mip1
// (2×2 box of the binary mask) already supplies that. Higher mips ALSO average the
// crown COLOUR, and past ~mip2 the interior dapple is gone → a flat-green disc; with
// London plane's dense summer alpha the hashed test then passes nearly every interior
// pixel → the "flat blob with a hard outline" Chris saw at extreme distance (2026-06-27).
// So cap at mip1: fractional alpha for the hash, but interior detail preserved out to
// 800m so the far crown keeps the airy/detailed look the 200-500m range already has.
const float IMPOSTOR_LOD_MAX = 1.0;

// ⚠ VARYING BUDGET: the engine's internal interpolators share the 32-slot cap
// with user varyings IN THE FULL SCENE (this shader broke it at +2 user varyings,
// 2026-07-02, while compiling fine in a minimal project). The xy_frameN varyings
// (virtual-plane parallax basis) were dropped to pay for the sun-visibility pair
// below — they only fed the DORMANT depth-parallax path (depth_scale = 0, no
// depth atlas baked). To restore parallax, recompute them per-fragment from the
// frame bases instead of re-adding varyings.
varying vec3 v_season_color;
varying vec2 uv_frame1;
varying flat vec2 frame1;
varying flat vec3 frame1_normal;
varying vec2 uv_frame2;
varying flat vec2 frame2;
varying flat vec3 frame2_normal;
varying vec2 uv_frame3;
varying flat vec2 frame3;
varying flat vec3 frame3_normal;
varying vec4 quad_blend_weights;
varying vec3 v_inst_pos;
// xyz = sun direction in BAKE-OBJECT space, rotated per instance in vertex (the
// ONLY stage where MODEL_MATRIX is per-instance for MultiMesh, #76292) from the
// sun_dir_world global — each placed tree's baked visibility field follows its
// yaw. w = per-tree seasonal leaf fraction (1=full canopy, 0=bare; same phenology
// curve as tree_leaf), which blends the winter↔summer atlas sets and relaxes the
// vis term as the crown sheds.
varying flat vec4 v_sun_leaf;
// Evaluated sun-visibility (fragment-written, consumed in light()).
varying float v_vis;

vec2 VecToSphereOct(vec3 pivotToCamera) {
	vec3 octant = sign(pivotToCamera);
	float sum = dot(pivotToCamera, octant);
	vec3 octahedron = pivotToCamera / sum;
	if (octahedron.y < 0.0f) {
		vec3 absolute = abs(octahedron);
		octahedron.xz = octant.xz * vec2(1.0f - absolute.z, 1.0f - absolute.x);
	}
	return octahedron.xz;
}

vec2 VecToHemiSphereOct(vec3 pivotToCamera) {
	pivotToCamera.y = max(pivotToCamera.y, 0.001);
	pivotToCamera = normalize(pivotToCamera);
	vec3 octant = sign(pivotToCamera);
	float sum = dot(pivotToCamera, octant);
	vec3 octahedron = pivotToCamera / sum;
	return vec2(octahedron.x + octahedron.z, octahedron.z - octahedron.x);
}

vec2 VectorToGrid(vec3 vec) {
	if (isFullSphere) { return VecToSphereOct(vec); }
	else { return VecToHemiSphereOct(vec); }
}

vec3 OctaSphereEnc(vec2 coord) {
	coord = (coord - 0.5) * 2.0;
	vec3 position = vec3(coord.x, 0.0f, coord.y);
	vec2 absolute = abs(position.xz);
	position.y = 1.0f - absolute.x - absolute.y;
	if (position.y < 0.0f) {
		position.xz = sign(position.xz) * vec2(1.0f - absolute.y, 1.0f - absolute.x);
	}
	return position;
}

vec3 OctaHemiSphereEnc(vec2 coord) {
	vec3 position = vec3(coord.x - coord.y, 0.0f, -1.0 + coord.x + coord.y);
	vec2 absolute = abs(position.xz);
	position.y = 1.0f - absolute.x - absolute.y;
	return position;
}

vec3 GridToVector(vec2 coord) {
	if (isFullSphere) { return OctaSphereEnc(coord); }
	else { return OctaHemiSphereEnc(coord); }
}

vec3 FrameXYToRay(vec2 frame, vec2 frameCountMinusOne) {
	vec2 f = (frame.xy / frameCountMinusOne);
	vec3 vec = GridToVector(f);
	vec = normalize(vec);
	return vec;
}

vec3 SpriteProjection(vec3 pivotToCameraRayLocal, vec2 size, vec2 loc_uv) {
	vec3 z = normalize(pivotToCameraRayLocal);
	vec3 x, y;
	vec3 up = vec3(0, 1, 0);
	if (abs(z.y) > 0.999f) { up = vec3(0, 0, -1); }
	x = normalize(cross(up, z));
	y = normalize(cross(x, z));
	loc_uv -= vec2(0.5, 0.5);
	vec2 uv = (loc_uv) * 2.0;
	vec3 newX = x * uv.x;
	vec3 newY = y * uv.y;
	vec2 vecSize = size * 0.5;
	newX *= vecSize.x;
	newY *= vecSize.y;
	return newX + newY;
}

vec4 quadBlendWieghts(vec2 coords) {
	vec4 res;
	res.x = min(1.0f - coords.x, 1.0f - coords.y);
	res.y = abs(coords.x - coords.y);
	res.z = min(coords.x, coords.y);
	res.w = ceil(coords.x - coords.y);
	return res;
}

vec2 virtualPlaneUV(vec3 plane_normal, vec3 plane_x, vec3 plane_y, vec3 pivotToCameraRay, vec3 vertexToCameraRay, float size) {
	plane_normal = normalize(plane_normal);
	plane_x = normalize(plane_x);
	plane_y = normalize(plane_y);
	float projectedNormalRayLength = dot(plane_normal, pivotToCameraRay);
	float projectedVertexRayLength = dot(plane_normal, vertexToCameraRay);
	float offsetLength = projectedNormalRayLength / projectedVertexRayLength;
	vec3 offsetVector = vertexToCameraRay * offsetLength - pivotToCameraRay;
	vec2 duv = vec2(dot(plane_x, offsetVector), dot(plane_y, offsetVector));
	duv /= 2.0 * size;
	duv += 0.5;
	return duv;
}

void calcuateXYbasis(vec3 plane_normal, out vec3 plane_x, out vec3 plane_y) {
	vec3 up = vec3(0, 1, 0);
	if (abs(plane_normal.y) > 0.999f) { up = vec3(0, 0, 1); }
	plane_x = normalize(cross(plane_normal, up));
	plane_y = normalize(cross(plane_x, plane_normal));
}

vec3 projectOnPlaneBasis(vec3 ray, vec3 plane_normal, vec3 plane_x, vec3 plane_y) {
	return normalize(vec3(dot(plane_x, ray), dot(plane_y, ray), dot(plane_normal, ray)));
}

void vertex() {
	v_inst_pos = MODEL_MATRIX[3].xyz;
	// World->object direction: basis-column dots = transpose = inverse rotation
	// up to uniform scale (normalised away).
	v_sun_leaf.xyz = normalize(vec3(dot(MODEL_MATRIX[0].xyz, sun_dir_world),
			dot(MODEL_MATRIX[1].xyz, sun_dir_world), dot(MODEL_MATRIX[2].xyz, sun_dir_world)));

	// Per-tree seasonal foliage colour (hue source; the atlas supplies luminance/
	// detail in fragment). Decode matches tree_leaf: INSTANCE_CUSTOM r=species/13,
	// g=timing+0.5, a=jitter. Blossom + per-leaf hash are omitted (negligible far).
	int sp_idx = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	float timing_off = INSTANCE_CUSTOM.g - 0.5;
	float s = mod(season_t + timing_off, 4.0);
	vec3 species_green = SUMMER_COLORS[sp_idx];
	vec4 ph = PHENOLOGY[sp_idx];

	// Seasonal canopy fraction — IDENTICAL curve to tree_leaf (grow ∧ shed), so the
	// impostor thins in lockstep with the mesh it hands off from. Evergreens stay full.
	float grow = smoothstep(ph.w - 0.1, ph.w + 0.3, s);
	float shed = 1.0 - smoothstep(ph.z - 0.2, ph.z + 0.3, s);
	v_sun_leaf.w = (INSTANCE_CUSTOM.b > 0.5) ? 1.0 : clamp(min(grow, shed), 0.0, 1.0);
	vec3 fall_col = FALL_COLORS[sp_idx];
	vec3 spring_tint = species_green * vec3(1.15, 1.2, 0.7);
	vec3 col = mix(spring_tint, species_green, smoothstep(ph.w, ph.w + 0.4, s));
	col = mix(col, fall_col, smoothstep(ph.x, ph.y, s));
	col = mix(col, fall_col * 0.5, smoothstep(ph.y, ph.z, s) * 0.6);
	float jitter = INSTANCE_CUSTOM.a;
	col *= 1.0 + (jitter - 0.5) * 0.25;
	col += (fract(jitter * 7.37) - 0.5) * vec3(0.025, -0.008, -0.03);
	v_season_color = col;

	vec2 framesMinusOne = imposterFrames - vec2(1);
	mat4 inv_model = inverse(MODEL_MATRIX);
	vec3 cameraPos_WS = (INV_VIEW_MATRIX * vec4(vec3(0), 1.0)).xyz;
	vec3 cameraPos_OS = (inv_model * vec4(cameraPos_WS, 1.0)).xyz;
	vec3 pivotToCameraRay = (cameraPos_OS) * 10.0;
	vec3 pivotToCameraDir = normalize(cameraPos_OS);

	vec2 grid = VectorToGrid(pivotToCameraDir);
	grid = clamp((grid + 1.0) * 0.5, vec2(0, 0), vec2(1, 1));
	grid *= framesMinusOne;
	grid = clamp(grid, vec2(0), vec2(framesMinusOne));
	vec2 gridFloor = min(floor(grid), framesMinusOne);
	vec2 gridFract = fract(grid);

	vec2 size = vec2(2.0) * scale;
	vec3 projected = SpriteProjection(pivotToCameraDir, size, UV);
	vec3 vertexToCameraRay = (pivotToCameraRay - (projected));
	vec3 vertexToCameraDir = normalize(vertexToCameraRay);

	frame1 = gridFloor;
	quad_blend_weights = quadBlendWieghts(gridFract);
	vec3 projectedQuadADir = FrameXYToRay(frame1, framesMinusOne);

	frame2 = clamp(frame1 + mix(vec2(0, 1), vec2(1, 0), quad_blend_weights.w), vec2(0, 0), framesMinusOne);
	vec3 projectedQuadBDir = FrameXYToRay(frame2, framesMinusOne);

	frame3 = clamp(frame1 + vec2(1), vec2(0, 0), framesMinusOne);
	vec3 projectedQuadCDir = FrameXYToRay(frame3, framesMinusOne);

	frame1_normal = (MODELVIEW_MATRIX * vec4(projectedQuadADir, 0)).xyz;
	frame2_normal = (MODELVIEW_MATRIX * vec4(projectedQuadBDir, 0)).xyz;
	frame3_normal = (MODELVIEW_MATRIX * vec4(projectedQuadCDir, 0)).xyz;

	vec3 plane_x1, plane_y1, plane_x2, plane_y2, plane_x3, plane_y3;
	calcuateXYbasis(projectedQuadADir, plane_x1, plane_y1);
	uv_frame1 = virtualPlaneUV(projectedQuadADir, plane_x1, plane_y1, pivotToCameraRay, vertexToCameraRay, scale);

	calcuateXYbasis(projectedQuadBDir, plane_x2, plane_y2);
	uv_frame2 = virtualPlaneUV(projectedQuadBDir, plane_x2, plane_y2, pivotToCameraRay, vertexToCameraRay, scale);

	calcuateXYbasis(projectedQuadCDir, plane_x3, plane_y3);
	uv_frame3 = virtualPlaneUV(projectedQuadCDir, plane_x3, plane_y3, pivotToCameraRay, vertexToCameraRay, scale);

	VERTEX.xyz = projected + positionOffset;
	VERTEX.xyz += pivotToCameraDir * aabb_max;

	// --- Wind: rock the whole crown to match the mesh's gross sway at the handoff -----
	// Reuse the shared structural terms (trunk cantilever + steady push + gust) — the SAME
	// wind.gdshaderinc functions and WIND_PARAMS row the mesh uses — evaluated once at the
	// crown's world height, so a far crown leans coherently with the neighbouring mesh
	// trees it crossfades into. (The per-branch term is crown detail that averages to ~0
	// over the whole billboard, so it's omitted.) Full amplitude through the 40–80m
	// handoff (matching the mesh, whose wind is full to ~140m), fading out by ~450m.
	vec4 wp = WIND_PARAMS[sp_idx];
	float wind_dist = length(v_inst_pos - player_world_pos);
	float wind_lod = 1.0 - smoothstep(250.0, 450.0, wind_dist);
	float wind_str = length(wind_vec);
	float rustle = (0.3 + wind_str * 0.7) * wind_lod;
	float crown_h = world_height * 0.62;                    // crown centroid height (m)
	vec2 trunk_d = wind_cantilever_trunk(crown_h, wp.z, wp.x, rustle, wind_phase(v_inst_pos));
	vec2 push_d  = wind_push(wind_vec, crown_h, 0.10, wp.x) * wind_lod;
	float gust = wind_gust(v_inst_pos, 0.3, 3.0);
	float gust_strength = gust * wind_str * 0.20 * wp.w * wind_lod;
	vec2 sway_world = (trunk_d + push_d + wind_vec * crown_h * gust_strength) * impostor_wind_strength;
	// World XZ offset → object space (via inv_model, scale-robust), weighted by UV.y so the
	// top of the card leans and the base stays planted.
	vec3 sway_obj = (mat3(inv_model) * vec3(sway_world.x, 0.0, sway_world.y)) * UV.y;
	VERTEX.xyz += sway_obj;

	NORMAL = normalize(pivotToCameraDir);
	TANGENT = normalize(cross(NORMAL, vec3(0.0, 1.0, 0.0)));
	BINORMAL = normalize(cross(TANGENT, NORMAL));
}

vec4 blenderColors(vec2 uv_1, vec2 uv_2, vec2 uv_3, vec4 grid_weights, sampler2D atlasTexture, float lod) {
	// Explicit LOD (not auto-derivatives): the atlas UV jumps between octa cells, so
	// auto-mip would spike the derivative at cell seams and bleed across cells. The
	// caller computes lod from the billboard's on-screen size instead (continuous,
	// per-instance) — so far crowns downsample to a correctly-averaged mini-crown
	// instead of the no-mip mip0 fetch binarizing into a flat dark blob.
	vec4 quad_a = textureLod(atlasTexture, uv_1, lod);
	vec4 quad_b = textureLod(atlasTexture, uv_2, lod);
	vec4 quad_c = textureLod(atlasTexture, uv_3, lod);
	return quad_a * grid_weights.x + quad_b * grid_weights.y + quad_c * grid_weights.z;
}

vec3 normal_from_normalmap(vec4 normalTex, vec3 tangent, vec3 binormal, vec3 f_norm) {
	vec3 normalmap;
	normalmap.xy = normalTex.xy * 2.0 - 1.0;
	normalmap.z = sqrt(max(0.0, 1.0 - dot(normalmap.xy, normalmap.xy)));
	normalmap = normalize(normalmap);
	return normalize(tangent * normalmap.x + binormal * normalmap.y + f_norm * normalmap.z);
}

vec3 blendedNormals(vec2 uv_1, vec3 f1_n, vec2 uv_2, vec3 f2_n, vec2 uv_3, vec3 f3_n,
		vec3 tangent, vec3 binormal, vec4 grid_weights, sampler2D atlasTexture, float lod) {
	vec4 quad_a = textureLod(atlasTexture, uv_1, lod);
	vec4 quad_b = textureLod(atlasTexture, uv_2, lod);
	vec4 quad_c = textureLod(atlasTexture, uv_3, lod);
	vec3 norm1 = normal_from_normalmap(quad_a, tangent, binormal, f1_n);
	vec3 norm2 = normal_from_normalmap(quad_b, tangent, binormal, f2_n);
	vec3 norm3 = normal_from_normalmap(quad_c, tangent, binormal, f3_n);
	return normalize(norm1 * grid_weights.x + norm2 * grid_weights.y + norm3 * grid_weights.z);
}

vec2 recalculateUV(vec2 uv_f, vec2 frame, vec2 xy_f, vec2 frame_size, float d_scale, sampler2D depthTexture) {
	uv_f = clamp(uv_f, vec2(0), vec2(1));
	// No depth atlas is baked (foliage; depth_scale stays 0), so the virtual-plane
	// parallax offset is a no-op. Skip it and its 3-per-fragment depth fetches; map
	// straight to the atlas cell. (Restore-ready: a non-zero depth_scale + a bound
	// depth atlas re-enables full parallax below.)
	if (d_scale <= 0.0) {
		return clamp(frame_size * (frame + uv_f), vec2(0), vec2(1));
	}
	vec2 uv_quad = frame_size * (frame + uv_f);
	vec4 n_depth = (textureLod(depthTexture, uv_quad, 0));
	uv_f = xy_f * (0.5 - n_depth.r) * d_scale + uv_f;
	uv_f = clamp(uv_f, vec2(0), vec2(1));
	uv_f = frame_size * (frame + uv_f);
	return clamp(uv_f, vec2(0), vec2(1));
}

// --- Stable hashed alpha testing (Wyman & McGuire 2017) -------------------------
// Renders the mipped FRACTIONAL coverage as partial transparency so far crowns read
// see-through (sky breaks through) instead of the binary scissor filling sub-pixel
// holes solid. The threshold noise is anchored to a SURFACE coordinate (the atlas UV,
// fixed on the crown) and quantised at a screen-space-derivative scale, so the grain
// stays ~1px and STICKS TO THE TREE as the camera moves — this is the property the
// reverted screen-space thinning lacked (it crawled). Opaque pass via discard (no
// alpha blending / sorting). TAA resolves the residual grain.
float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float hashed_alpha_threshold(vec2 anchor) {
	float max_deriv = max(length(dFdx(anchor)), length(dFdy(anchor)));
	float pix_scale = 1.0 / max(max_deriv, 1e-8);
	vec2 pix_scales = vec2(exp2(floor(log2(pix_scale))), exp2(ceil(log2(pix_scale))));
	vec2 a = vec2(hash12(floor(pix_scales.x * anchor)), hash12(floor(pix_scales.y * anchor)));
	float lf = fract(log2(pix_scale));
	float x = (1.0 - lf) * a.x + lf * a.y;
	float lo = min(lf, 1.0 - lf);
	vec3 cases = vec3(
		x * x / (2.0 * lo * (1.0 - lo)),
		(x - 0.5 * lo) / (1.0 - lo),
		1.0 - ((1.0 - x) * (1.0 - x) / (2.0 * lo * (1.0 - lo))));
	float thr = (x < 1.0 - lo) ? ((x < lo) ? cases.x : cases.y) : cases.z;
	return clamp(thr, 1.0e-6, 1.0);
}

// FAR BAND (metres). The 200-500m impostors already read well (Chris 2026-06-27), so
// they stay EXACTLY as before — mip0 + crisp binary scissor. Only beyond ~500m, where
// the crown was filling into a flat dark blob, do mips + hashed fractional coverage
// ramp in to make the far tier match the mid-range airy/detailed look. Tunable.
uniform float far_band_begin = 500.0;
uniform float far_band_full = 660.0;

void fragment() {
	// LOD crossfade-in: dither IN over the band where the mesh dithers out —
	// complementary to the mesh fade-out at the same per-tree distance.
	if (lod_fade_in.y > 0.0) {
		float d = length(v_inst_pos - player_world_pos);
		if (d < lod_fade_in.y) {
			if (lod_dither_discard(d, lod_fade_in.x, lod_fade_in.y, FRAGCOORD.xy, true)) discard;
		}
	}

	vec2 quad_size = vec2(1.0f) / imposterFrames;
	vec2 uv_f1 = recalculateUV(uv_frame1, frame1, vec2(0.0), quad_size, depth_scale, imposterTextureDepth);
	vec2 uv_f2 = recalculateUV(uv_frame2, frame2, vec2(0.0), quad_size, depth_scale, imposterTextureDepth);
	vec2 uv_f3 = recalculateUV(uv_frame3, frame3, vec2(0.0), quad_size, depth_scale, imposterTextureDepth);

	// Atlas mip from the billboard's on-screen height (perspective): a world_height-tall
	// tree at distance d projects to ~ P[1][1]*world_height/d * VIEWPORT.y/2 pixels; the
	// atlas spends IMPOSTOR_CELL_PX on that height, so texels-per-pixel = cell/px and the
	// mip is log2 of that. Continuous in distance (no cell-seam derivative spike), capped
	// to keep mips within a cell.
	float d_cam = length(v_inst_pos - player_world_pos);
	float screen_px = max(1.0, PROJECTION_MATRIX[1][1] * world_height / max(d_cam, 1.0) * VIEWPORT_SIZE.y * 0.5);
	float atlas_lod_raw = clamp(log2(max(IMPOSTOR_CELL_PX / screen_px, 1.0)), 0.0, IMPOSTOR_LOD_MAX);
	// Gate the far treatment to >~500m: below the far band, far_factor=0 → atlas_lod=0
	// (mip0) so the 200-500m range is BYTE-FOR-BYTE the original look (Chris: that range
	// was already good — don't touch it). The far band ramps in mips + hashed coverage.
	float far_factor = smoothstep(far_band_begin, far_band_full, d_cam);
	float atlas_lod = atlas_lod_raw * far_factor;

	vec4 baseTex = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureAlbedo, atlas_lod);
	vec4 ormTex = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureOrm, atlas_lod);
	vec3 normalTex = blendedNormals(uv_f1, frame1_normal, uv_f2, frame2_normal, uv_f3, frame3_normal,
			TANGENT, BINORMAL, quad_blend_weights, imposterTextureNormal, atlas_lod);

	// Seasonal SHAPE: blend toward the near-bare winter atlas as the canopy sheds. The
	// branch is coherent across all impostor fragments in a frame (v_leaf_frac is
	// season-driven, ~uniform per neighbourhood), so the extra fetches are skipped
	// outright in full summer / deep winter and only paid during the transition bands.
	if (has_winter_atlas && v_sun_leaf.w < 0.999) {
		vec4 wBase = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureAlbedoWinter, atlas_lod);
		vec4 wOrm = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureOrmWinter, atlas_lod);
		vec3 wNormal = blendedNormals(uv_f1, frame1_normal, uv_f2, frame2_normal, uv_f3, frame3_normal,
				TANGENT, BINORMAL, quad_blend_weights, imposterTextureNormalWinter, atlas_lod);
		baseTex = mix(wBase, baseTex, v_sun_leaf.w);
		ormTex = mix(wOrm, ormTex, v_sun_leaf.w);
		normalTex = normalize(mix(wNormal, normalTex, v_sun_leaf.w));
	}

	// Sun-visibility: fetch (blended over the same 3 octa frames as every other
	// channel), decode to (c0, c_vec), evaluate against the object-space sun.
	// Winter: a near-bare crown barely self-occludes, so vis relaxes toward 1
	// as v_leaf_frac drops. light() consumes the single evaluated float.
	// NO vis atlas -> replicate the engine's AO-on-direct here (the custom
	// light() bypasses the built-in AO_LIGHT_AFFECT path — measured 1.141x
	// bright without this), so pre-vis species/manifests keep the a801c20 look.
	if (has_vis_atlas) {
		vec4 vraw = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureVis, atlas_lod);
		float v = clamp(vraw.r + dot(vraw.gba * 2.0 - 1.0, v_sun_leaf.xyz), 0.0, 1.0);
		v_vis = mix(1.0, v, vis_strength * v_sun_leaf.w);
	} else {
		v_vis = mix(1.0, max(pow(ormTex.r, ao_power), ao_floor), ao_light_affect);
	}

	// Runtime-lit: HUE from the per-tree season colour, LUMINANCE/detail from the
	// atlas (dapple, leaf texture, bark-through-gaps). Recolours baked brown bark to
	// darker-green canopy variation and lets the far tier track season. Godot still
	// lights it directionally via NORMAL below (atlas is unlit → no double-lit).
	float atlas_lum = dot(baseTex.rgb, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = v_season_color * clamp(atlas_lum / detail_ref_lum, 0.0, 1.6) * albedo.rgb;
	NORMAL = normalTex.xyz;

	// Coverage. Below the far band (≤~500m) this is the ORIGINAL crisp binary scissor —
	// unchanged. In the far band, the mipped alpha (baseTex.a) carries the true fractional
	// crown coverage, and a stable hashed alpha test renders it as partial see-through so
	// the far crown stops filling into a flat dark blob and matches the airy mid-range
	// look. Anchor = atlas texel coord (sticks to the crown surface) + per-tree offset to
	// decorrelate neighbours; derivative-scaled so the grain is ~1px and doesn't crawl.
	// Coverage is discard-only — NO `ALPHA =` write (writing ALPHA would flag the material
	// transparent → no shadow casting; see render_mode note at top). depth_prepass_alpha
	// runs this discard in the depth/shadow prepass, so the silhouette is correct.
	vec2 hash_anchor = uv_f1 * 2048.0 + v_inst_pos.xz * 7.0;
	float far_thr = mix(alpha_clamp, hashed_alpha_threshold(hash_anchor), far_factor);
	if (baseTex.a < far_thr) discard;

	METALLIC = ormTex.b * metallic;
	SPECULAR = specular;
	ROUGHNESS = ormTex.g * roughness;

	// Crown-interior ambient occlusion, baked into the ORM red channel
	// (bake_impostors.gd, bake_mode 3). Applied ambient-only — exactly as the
	// mesh leaf shader does (AO_LIGHT_AFFECT = 0) — so the far tier stops reading
	// ~1.5x too bright vs lod0 without dimming the direct-sun side. Defaults
	// to 1.0 (no occlusion) when no ORM atlas is bound (hint_default_white).
	// With a vis atlas bound, tree_builder zeroes ao_light_affect and neutralises
	// ao_power/ao_floor: direct-light occlusion moves to light() (sun-aware),
	// ambient AO returns to plain mesh parity.
	AO = max(pow(ormTex.r, ao_power), ao_floor);
	AO_LIGHT_AFFECT = ao_light_affect;
}

void light() {
	// Custom diffuse = Godot's burley formula x baked sun-visibility. Replacing
	// the built-in is required to inject a per-texel, sun-direction-dependent
	// occlusion into DIRECT light — AO_LIGHT_AFFECT is scalar and static (the
	// a801c20 fake, right only at its calibration hours; 0.29x lod0 at 9h).
	// Specular is dropped: measured no-op at specular=0.1/roughness~1 (0.996x,
	// a801c20). Burley matches scene_forward_lights so the 13h/18h calibration
	// carries over (LIGHT_COLOR already includes x PI; ALBEDO applied by Godot
	// after light()).
	float ndotl = clamp(dot(NORMAL, LIGHT), 0.0, 1.0);
	float ndotv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec3 h = normalize(VIEW + LIGHT);
	float ldoth = clamp(dot(LIGHT, h), 0.0, 1.0);
	float fd90m1 = 2.0 * ldoth * ldoth * ROUGHNESS - 0.5;
	float fdv = 1.0 + fd90m1 * pow(1.0 - ndotv, 5.0);
	float fdl = 1.0 + fd90m1 * pow(1.0 - ndotl, 5.0);
	float burley = (1.0 / PI) * fdv * fdl * ndotl;
	DIFFUSE_LIGHT += burley * v_vis * ATTENUATION * LIGHT_COLOR;

	// --- Subsurface transmission (backlit glow) — fix-ladder #2 ------------------
	// The near mesh glows when the sun is behind it via Godot's built-in BACKLIGHT.
	// A custom light() BYPASSES that built-in path, so without this the far tier stays
	// flatly opaque at every sun angle: the vis fix keeps it from being wrongly DARK,
	// but it also never GLOWS. Re-inject transmission with Godot's EXACT backlight
	// formula (light_color * (1/PI − diffuse_brdf_NL) * backlight) so the amber glow is
	// magnitude-matched to the mesh across the handoff. The (1/PI − burley) factor is ~0
	// when frontlit (burley high) and ~1/PI when backlit (burley→0, normals facing away
	// from the sun) — it fills only the sun-away side, exactly like leaf transmission.
	// NOT gated by v_vis: the mesh leaves SSS untouched by crown AO (tree_leaf: AO_LIGHT_
	// AFFECT=0, SSS untouched), so matching it keeps the handoff seamless.
	vec3 backlight_col = mix(vec3(0.62, 0.50, 0.14), v_season_color * 0.75, 0.5);
	float spring_boost = (1.0 - smoothstep(0.3, 0.8, season_t)) * 0.15;
	// v_sun_leaf.w = per-tree canopy fraction (winter → little glow, matching the mesh's
	// v_leaf_density term). sss_strength folds the species leaf-thickness factor.
	float sss = (v_sun_leaf.w * 0.7 + spring_boost) * sss_strength;
	// Cap at real leaf transmittance (5-15% of albedo) — same clamp the mesh uses, so a
	// too-hot swing can't make solid far foliage read see-through as the camera rotates.
	vec3 backlight = min(backlight_col * sss, ALBEDO * 0.15);
	DIFFUSE_LIGHT += LIGHT_COLOR * (vec3(1.0 / PI) - burley) * backlight * ATTENUATION;
}
