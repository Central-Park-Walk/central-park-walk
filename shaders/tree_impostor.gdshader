shader_type spatial;
// Premultiplied alpha — atlas RGB is stored as color*alpha (see
// scripts/premultiply_impostors.py). Eliminates the silhouette-halo
// artifact that straight-alpha mipmap averaging produces around
// transparent borders. The blend equation becomes:
//   final = src.rgb + (1 - src.a) * dest.rgb
// so src.rgb is added directly without a second alpha multiply.
render_mode blend_premul_alpha, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

// --- Atlas textures (8×8 hemisphere octahedral, baked per species) ---
// `atlas` is the summer bake; `atlas_winter` is a second bake at season_t=3.3
// — clean-abscission species come out as bare trunks, marcescent species as
// sparse dead-brown canopy. Sampled at the same UV and blended in fragment.
uniform sampler2D atlas : source_color, filter_linear_mipmap;
uniform sampler2D atlas_winter : source_color, filter_linear_mipmap;
uniform sampler2D atlas_normal : hint_normal, filter_linear_mipmap;
uniform sampler2D atlas_depth : hint_default_white, filter_linear_mipmap;
uniform vec2 frames = vec2(8.0, 8.0);
uniform float alpha_clamp = 0.3;
uniform float depth_scale : hint_range(0, 1) = 0.3;
uniform float scale = 1.0;
uniform float aabb_max = 1.0;
uniform vec3 position_offset = vec3(0.0);

// --- Global uniforms ---
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float season_t;
global uniform vec3 sky_reflect_color;
global uniform vec3 canopy_ao;

// LOD crossfade: incoming dither range (begin, end).
uniform vec2 lod_fade_in = vec2(0.0, 0.0);

#include "res://shaders/include/tree_species.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"
#include "res://shaders/include/lod_dither.gdshaderinc"
#include "res://shaders/include/hash_noise.gdshaderinc"

// World-space tonal-region overlay (Far Cry / Ghost of Tsushima pattern).
// Without this, distant impostors mipmap-average to one flat green and
// aerial perspective blends them all toward the same haze color, reading
// as a "monochrome wall" at the horizon. Two octaves of value noise drive
// a small HSV shift per impostor instance (sampled at world XZ), creating
// tonal patches at 50-150m scales that survive the aerial blend.
vec3 rgb_to_hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}
vec3 hsv_to_rgb(vec3 c) {
	vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
	vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
	return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// --- Varyings ---
varying vec2 v_uv_frame1;
varying vec2 v_uv_frame2;
varying vec2 v_uv_frame3;
varying vec2 v_xy_frame1;
varying vec2 v_xy_frame2;
varying vec2 v_xy_frame3;
varying flat vec2 v_frame1;
varying flat vec2 v_frame2;
varying flat vec2 v_frame3;
varying flat vec3 v_frame1_normal;
varying flat vec3 v_frame2_normal;
varying flat vec3 v_frame3_normal;
varying vec4 v_blend_weights;
varying flat vec3 v_season_color;
// Packed scalars: x = leaf_density, y = color_jitter, z = fall_mix_t,
// w = winter_mix_t. Packed into a single vec4 because the hardware varying
// budget is 32 floats and the unpacked set overflows by one slot.
varying flat vec4 v_scalars;

// ── Octahedral hemisphere mapping ────────────────────────────────────────────

vec2 hemi_octa(vec3 dir) {
	// Mirror back-hemisphere views to front: trees are roughly symmetric,
	// so viewing from behind reuses front-hemisphere atlas frames.
	// Without this, back views clamp to equator → flat/wrong appearance.
	dir.y = max(abs(dir.y), 0.001);
	dir = normalize(dir);
	vec3 octant = sign(dir);
	float sum = dot(dir, octant);
	vec3 oct = dir / sum;
	return vec2(oct.x + oct.z, oct.z - oct.x);
}

vec3 hemi_octa_decode(vec2 coord) {
	vec3 position = vec3(coord.x - coord.y, 0.0, -1.0 + coord.x + coord.y);
	vec2 absolute = abs(position.xz);
	position.y = 1.0 - absolute.x - absolute.y;
	return normalize(position);
}

vec3 frame_to_ray(vec2 frame_coord, vec2 frames_m1) {
	vec2 f = frame_coord / frames_m1;
	vec3 bake = normalize(hemi_octa_decode(f));
	// Convert Blender space (X=right, Y=forward, Z=up) back to
	// Godot model space (X=right, Y=up, Z=back) so downstream
	// dot products with camera rays are in the same coordinate system.
	return vec3(bake.x, bake.z, -bake.y);
}

// ── Billboard projection (from GodotImposter) ───────────────────────────────

vec3 sprite_projection(vec3 pivot_to_cam_dir, vec2 size, vec2 uv) {
	// Spherical billboarding: billboard always faces the camera.
	// The octahedral atlas handles view-angle-dependent appearance —
	// the billboard just needs to present the correct atlas frame to the viewer.
	// (Cylindrical billboarding caused trees to vanish from elevated angles
	// because the upright billboard was seen edge-on.)
	vec3 z = normalize(pivot_to_cam_dir);
	vec3 ref_up = abs(z.y) > 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(0.0, 1.0, 0.0);
	vec3 x = normalize(cross(ref_up, z));
	vec3 y = normalize(cross(x, z));
	vec2 centered = (uv - vec2(0.5)) * 2.0;
	return x * centered.x * size.x * 0.5 + y * centered.y * size.y * 0.5;
}

// ── Virtual plane UV projection ──────────────────────────────────────────────

void calc_xy_basis(vec3 plane_n, out vec3 plane_x, out vec3 plane_y) {
	vec3 up = vec3(0.0, 1.0, 0.0);
	if (abs(plane_n.y) > 0.999) up = vec3(0.0, 0.0, 1.0);
	plane_x = normalize(cross(plane_n, up));
	plane_y = normalize(cross(plane_x, plane_n));
}

vec2 virtual_plane_uv(vec3 plane_n, vec3 plane_x, vec3 plane_y,
                       vec3 pivot_to_cam_ray, vec3 vtx_to_cam_ray, float sz) {
	plane_n = normalize(plane_n);
	plane_x = normalize(plane_x);
	plane_y = normalize(plane_y);
	float proj_n = dot(plane_n, pivot_to_cam_ray);
	float proj_v = dot(plane_n, vtx_to_cam_ray);
	float offset_len = proj_n / proj_v;
	vec3 offset_vec = vtx_to_cam_ray * offset_len - pivot_to_cam_ray;
	vec2 duv = vec2(dot(plane_x, offset_vec), dot(plane_y, offset_vec));
	duv /= 2.0 * sz;
	duv += 0.5;
	return duv;
}

vec3 project_on_plane_basis(vec3 ray, vec3 plane_n, vec3 plane_x, vec3 plane_y) {
	return normalize(vec3(dot(plane_x, ray), dot(plane_y, ray), dot(plane_n, ray)));
}

// ── Blend weights ────────────────────────────────────────────────────────────

vec4 calc_blend_weights(vec2 fract_grid) {
	vec4 res;
	res.x = min(1.0 - fract_grid.x, 1.0 - fract_grid.y);
	res.y = abs(fract_grid.x - fract_grid.y);
	res.z = min(fract_grid.x, fract_grid.y);
	res.w = ceil(fract_grid.x - fract_grid.y);
	return res;
}

// ══════════════════════════════════════════════════════════════════════════════

void vertex() {
	// --- Season data from INSTANCE_CUSTOM ---
	int sp_idx = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	float is_evergreen = INSTANCE_CUSTOM.b;
	float timing_off = INSTANCE_CUSTOM.g - 0.5;
	float jitter = INSTANCE_CUSTOM.a;  // per-tree color variation (0-1)
	float s = mod(season_t + timing_off, 4.0);

	float leaf_density = 1.0;
	vec3 season_color = SUMMER_COLORS[sp_idx];
	float fall_mix = 0.0;
	float winter_mix = 0.0;
	if (is_evergreen < 0.5) {
		vec4 ph = PHENOLOGY[sp_idx];
		float retention = WINTER_RETENTION[sp_idx];
		float grow = smoothstep(ph.w - 0.1, ph.w + 0.3, s);
		float shed = 1.0 - smoothstep(ph.z - 0.2, ph.z + 0.3, s);
		leaf_density = max(mix(retention, 1.0, min(grow, shed)), 0.08);
		vec3 fall_col = FALL_COLORS[sp_idx];
		vec3 spring_tint = season_color * vec3(1.15, 1.2, 0.7);
		float spring_t = smoothstep(ph.w, ph.w + 0.4, s);
		season_color = mix(spring_tint, season_color, spring_t);
		float fall_t = smoothstep(ph.x, ph.y, s);
		season_color = mix(season_color, fall_col, fall_t);
		float late_fall = smoothstep(ph.y, ph.z, s);
		season_color = mix(season_color, fall_col * 0.5, late_fall * 0.6);
		// Combined fall weighting — peaks at the fall_peak phenology stamp
		// and fades as leaves shed. Fragment uses this to pull summer atlas
		// toward season_color without erasing atlas texture character.
		fall_mix = clamp(fall_t - late_fall * 0.4, 0.0, 1.0);
		// Winter atlas crossfade — tracks the shed curve so the visual
		// transition matches how leaves actually fall off.
		winter_mix = 1.0 - smoothstep(ph.z - 0.2, ph.z + 0.3, s);
		winter_mix = 1.0 - min(grow, winter_mix);  // also bare in early spring
	}
	// Per-tree color variation: brightness ±12%, warm/cool ±shift
	float bright_off = (jitter - 0.5) * 0.25;
	season_color *= 1.0 + bright_off;
	float warm_off = fract(jitter * 7.37) - 0.5;
	season_color += warm_off * vec3(0.025, -0.008, -0.03);
	// Pre-divide by the species' summer-albedo luminance: fragment re-lights
	// the true-albedo atlas toward the seasonal hue as v_season_color ×
	// atlas_lum, where atlas_lum ≈ summer_lum × per-texel detail — the
	// division transfers the atlas's texture detail onto the seasonal color
	// at the correct albedo brightness. (Replaces the old ×3.0 fudge that
	// compensated lit-baked atlas luminance.)
	float summer_lum = dot(SUMMER_COLORS[sp_idx], vec3(0.299, 0.587, 0.114));
	v_season_color = season_color / max(summer_lum, 0.05);
	v_scalars = vec4(leaf_density, jitter, fall_mix, winter_mix);

	// --- Billboard projection ---
	vec2 frames_m1 = frames - vec2(1.0);
	vec3 cam_ws = (INV_VIEW_MATRIX * vec4(vec3(0.0), 1.0)).xyz;
	vec3 cam_os = (inverse(MODEL_MATRIX) * vec4(cam_ws, 1.0)).xyz;
	vec3 pivot_to_cam_ray = cam_os * 10.0;
	vec3 pivot_to_cam_dir = normalize(cam_os);

	// Species-specific wind sway: shift billboard origin
	vec4 wp = WIND_PARAMS[sp_idx];
	vec3 tree_pos = MODEL_MATRIX[3].xyz;
	float wind_str = length(wind_vec);
	float rustle = 0.3 + wind_str * 0.7;
	float phase = tree_pos.x * 0.04 + tree_pos.z * 0.06;
	// Trunk sway scaled by species flexibility
	vec3 wind_offset = vec3(
		sin(TIME * 0.7 * wp.z + phase) * 0.04 * rustle * mix(0.5, 1.0, wp.x),
		0.0,
		sin(TIME * 1.1 * wp.z + phase * 1.3) * 0.025 * rustle * mix(0.5, 1.0, wp.x)
	);
	// Wind push + gust
	float lean = 0.08 * mix(0.5, 1.0, wp.x);
	wind_offset += vec3(wind_vec.x * lean, 0.0, wind_vec.y * lean);
	float gust_ph = tree_pos.x * 0.02 + tree_pos.z * 0.03;
	float gust = sin(TIME * 0.3 + gust_ph) * 0.5 + 0.5;
	gust = gust * gust * gust;
	wind_offset += vec3(wind_vec.x, 0.0, wind_vec.y) * gust * wind_str * 0.06 * wp.w;

	// Atlas frame selection (octahedral hemisphere)
	// Convert Godot space → bake script space (Blender):
	// Godot (X, Y, Z) = (right, up, back) → Blender (X, Y, Z) = (right, forward, up)
	// Mapping: bake_x = godot_x, bake_y = -godot_z, bake_z = godot_y
	vec3 bake_dir = vec3(pivot_to_cam_dir.x, -pivot_to_cam_dir.z, pivot_to_cam_dir.y);
	vec2 grid = hemi_octa(bake_dir);
	grid = clamp((grid + 1.0) * 0.5, vec2(0.0), vec2(1.0));
	grid *= frames_m1;
	grid = clamp(grid, vec2(0.0), frames_m1);
	vec2 grid_floor = min(floor(grid), frames_m1);
	vec2 grid_fract = fract(grid);

	v_blend_weights = calc_blend_weights(grid_fract);

	// 3 blended frames
	v_frame1 = grid_floor;
	vec3 dir1 = frame_to_ray(v_frame1, frames_m1);

	v_frame2 = clamp(grid_floor + mix(vec2(0.0, 1.0), vec2(1.0, 0.0), v_blend_weights.w),
	                  vec2(0.0), frames_m1);
	vec3 dir2 = frame_to_ray(v_frame2, frames_m1);

	v_frame3 = clamp(grid_floor + vec2(1.0), vec2(0.0), frames_m1);
	vec3 dir3 = frame_to_ray(v_frame3, frames_m1);

	// Frame normals in view space (for normal map reconstruction)
	v_frame1_normal = (MODELVIEW_MATRIX * vec4(dir1, 0.0)).xyz;
	v_frame2_normal = (MODELVIEW_MATRIX * vec4(dir2, 0.0)).xyz;
	v_frame3_normal = (MODELVIEW_MATRIX * vec4(dir3, 0.0)).xyz;

	// Billboard projection — scale is bounding radius at model scale.
	// Instance transform (MODEL_MATRIX) scales this to world size automatically.
	vec2 size = vec2(2.0) * scale;
	vec3 projected = sprite_projection(pivot_to_cam_dir, size, UV);
	vec3 vtx_to_cam_ray = pivot_to_cam_ray - projected;
	vec3 vtx_to_cam_dir = normalize(vtx_to_cam_ray);

	// Virtual plane UVs for each blended frame
	vec3 px1, py1, px2, py2, px3, py3;
	calc_xy_basis(dir1, px1, py1);
	v_uv_frame1 = virtual_plane_uv(dir1, px1, py1, pivot_to_cam_ray, vtx_to_cam_ray, scale);
	v_xy_frame1 = project_on_plane_basis(-vtx_to_cam_dir, dir1, px1, py1).xy;

	calc_xy_basis(dir2, px2, py2);
	v_uv_frame2 = virtual_plane_uv(dir2, px2, py2, pivot_to_cam_ray, vtx_to_cam_ray, scale);
	v_xy_frame2 = project_on_plane_basis(-vtx_to_cam_dir, dir2, px2, py2).xy;

	calc_xy_basis(dir3, px3, py3);
	v_uv_frame3 = virtual_plane_uv(dir3, px3, py3, pivot_to_cam_ray, vtx_to_cam_ray, scale);
	v_xy_frame3 = project_on_plane_basis(-vtx_to_cam_dir, dir3, px3, py3).xy;

	// Position output
	VERTEX.xyz = projected + position_offset + wind_offset;
	VERTEX.xyz += pivot_to_cam_dir * aabb_max;

	NORMAL = normalize(pivot_to_cam_dir);
	TANGENT = normalize(cross(NORMAL, vec3(0.0, 1.0, 0.0)));
	BINORMAL = normalize(cross(TANGENT, NORMAL));
}

// ── Fragment helpers ─────────────────────────────────────────────────────────

vec2 recalc_uv(vec2 uv_f, vec2 frame_coord, vec2 xy_f,
               vec2 frame_size, float d_scale, sampler2D depth_tex) {
	uv_f = clamp(uv_f, vec2(0.0), vec2(1.0));
	vec2 uv_quad = frame_size * (frame_coord + uv_f);
	vec4 d = textureLod(depth_tex, uv_quad, 0.0);
	uv_f = xy_f * (0.5 - d.r) * d_scale + uv_f;
	uv_f = clamp(uv_f, vec2(0.0), vec2(1.0));
	uv_f = frame_size * (frame_coord + uv_f);
	return clamp(uv_f, vec2(0.0), vec2(1.0));
}

vec4 blend_colors(vec2 uv1, vec2 uv2, vec2 uv3, vec4 w, sampler2D tex) {
	vec4 a = textureLod(tex, uv1, 0.0);
	vec4 b = textureLod(tex, uv2, 0.0);
	vec4 c = textureLod(tex, uv3, 0.0);
	return a * w.x + b * w.y + c * w.z;
}

vec3 normal_from_map(vec4 n_tex, vec3 tangent, vec3 binormal, vec3 f_norm) {
	vec3 nm;
	nm.xy = n_tex.xy * 2.0 - 1.0;
	nm.z = sqrt(max(0.0, 1.0 - dot(nm.xy, nm.xy)));
	nm = normalize(nm);
	return normalize(tangent * nm.x + binormal * nm.y + f_norm * nm.z);
}

vec3 blended_normals(vec2 uv1, vec3 fn1, vec2 uv2, vec3 fn2, vec2 uv3, vec3 fn3,
                     vec3 tangent, vec3 binormal, vec4 w, sampler2D ntex) {
	vec4 a = textureLod(ntex, uv1, 0.0);
	vec4 b = textureLod(ntex, uv2, 0.0);
	vec4 c = textureLod(ntex, uv3, 0.0);
	vec3 n1 = normal_from_map(a, tangent, binormal, fn1);
	vec3 n2 = normal_from_map(b, tangent, binormal, fn2);
	vec3 n3 = normal_from_map(c, tangent, binormal, fn3);
	return normalize(n1 * w.x + n2 * w.y + n3 * w.z);
}

// ══════════════════════════════════════════════════════════════════════════════

void fragment() {
	vec2 frame_size = vec2(1.0) / frames;

	// Parallax-corrected UVs via depth atlas
	vec2 uv1 = recalc_uv(v_uv_frame1, v_frame1, v_xy_frame1, frame_size, depth_scale, atlas_depth);
	vec2 uv2 = recalc_uv(v_uv_frame2, v_frame2, v_xy_frame2, frame_size, depth_scale, atlas_depth);
	vec2 uv3 = recalc_uv(v_uv_frame3, v_frame3, v_xy_frame3, frame_size, depth_scale, atlas_depth);

	// 3-frame blended sampling — both seasonal atlases at the same UVs so
	// we can crossfade by phenology. Only one branch of the mix dominates
	// at any given time, but sampling both unconditionally avoids flicker
	// at the transition and lets the GPU overlap the fetches.
	// Atlases are premultiplied (color*alpha); see scripts/premultiply_impostors.py.
	vec4 tex_summer = blend_colors(uv1, uv2, uv3, v_blend_weights, atlas);
	vec4 tex_winter = blend_colors(uv1, uv2, uv3, v_blend_weights, atlas_winter);
	float winter_mix_t = v_scalars.w;
	float leaf_density = v_scalars.x;

	// leaf_density attenuates the summer side only (winter atlas already
	// shows what survives leaf-fall). Apply uniformly to RGB and alpha so
	// the premultiplied invariant holds.
	tex_summer *= leaf_density;
	vec4 tex = mix(tex_summer, tex_winter, winter_mix_t);

	// Cull truly-empty pixels BEFORE boosting so we don't lift dust-level
	// alpha (background sky pixels) into visible impostor speckle.
	if (snow_cover > 0.6 && leaf_density < 0.3) discard;
	if (tex.a < alpha_clamp) discard;

	// Distance-based coverage compensation: counteract silhouette-thinning
	// at distance. At deep mips the atlas frame (silhouette ~16% of frame)
	// averages to ~0.15-0.2 alpha AND ~15% colour energy — the atlas is
	// premultiplied. We must lift rgb and alpha by the SAME factor so the
	// un-premul below recovers the original colour; otherwise the math at
	// the bottom (ALBEDO = color * alpha) cancels back to the un-boosted
	// premultiplied value and the boost is visible only as reduced sky-
	// bleed, not as a brighter silhouette. Cap so alpha tops out at 1.0.
	// Aggressive curve: ramp 100-300m, max 12× — enough to saturate alpha
	// of a 0.15 atlas pixel to 1.0 by 300m so distant trees read solid.
	vec3 _imp_world_pre = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float _imp_cam_dist_pre = length(_imp_world_pre - INV_VIEW_MATRIX[3].xyz);
	float dist_boost = 1.0 + smoothstep(100.0, 300.0, _imp_cam_dist_pre) * 12.0;
	float boost = min(dist_boost, 1.0 / max(tex.a, 0.001));
	tex.rgb *= boost;
	tex.a   *= boost;
	float alpha = tex.a;

	// LOD incoming dither: fade in as camera approaches from beyond LOD2's fade-out.
	// Complementary to LOD2's outgoing dither — each pixel shows exactly one tier.
	if (lod_fade_in.y > 0.0) {
		vec3 imp_pos = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
		float imp_cam_dist = length(imp_pos - (INV_VIEW_MATRIX * vec4(vec3(0.0), 1.0)).xyz);
		if (imp_cam_dist < lod_fade_in.y) {
			if (lod_dither_discard(imp_cam_dist, lod_fade_in.x, lod_fade_in.y,
			                       FRAGCOORD.xy, true)) discard;
		}
	}

	// Normal map
	vec3 nm = blended_normals(uv1, v_frame1_normal, uv2, v_frame2_normal,
	                          uv3, v_frame3_normal, TANGENT, BINORMAL,
	                          v_blend_weights, atlas_normal);
	NORMAL = nm;

	// Un-premultiply so downstream color math (jitter, season tint, snow,
	// aerial perspective) operates on the actual color, not on color*alpha.
	// We re-premultiply at the bottom (ALBEDO = color * alpha).
	vec3 color = tex.rgb / max(alpha, 0.001);

	// Per-tree color jitter, mirroring tree_leaf.gdshader (±12% brightness,
	// small warm/cool shift). The atlas was baked with neutral jitter=0.5 so
	// all impostors would otherwise be identical; this restores the tree-to-
	// tree variation LOD0 has and eliminates the "LOD0 varies / impostors
	// flat" mismatch.
	float jitter = v_scalars.y;
	float bright_off = (jitter - 0.5) * 0.25;
	color *= 1.0 + bright_off;
	float warm_off = fract(jitter * 7.37) - 0.5;
	color += warm_off * vec3(0.025, -0.008, -0.03);

	// Seasonal shift: atlas is summer-only, so pull hue toward season_color
	// during fall using the atlas's own luminance to preserve texture detail.
	// v_season_color is pre-divided by the species' summer-albedo luminance
	// in vertex(), so this lands at true-albedo brightness.
	float fall_mix_t = v_scalars.z;
	if (fall_mix_t > 0.0) {
		float atlas_lum = dot(color, vec3(0.299, 0.587, 0.114));
		vec3 fall_recolor = v_season_color * atlas_lum;
		color = mix(color, fall_recolor, fall_mix_t);
	}

	vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
	float top_lit = world_n.y * 0.5 + 0.5;

	// Snow accumulation on upper canopy
	if (snow_cover > 0.1) {
		float snow_top = snow_cover * smoothstep(0.3, 0.7, top_lit);
		color = mix(color, vec3(0.85, 0.88, 0.92), snow_top * 0.4);
	}

	vec3 imp_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;

	// World-space tonal-region overlay (plan C). Two-octave fBm at world XZ
	// drives a small HSV shift per impostor; the per-instance variation
	// survives mipmap averaging at distance because it's modulating the
	// final color, not the atlas texel. Centered around 0.5 so unperturbed
	// regions average to identity.
	vec2 wp = imp_world.xz;
	float n_big = vnoise(wp * (1.0 / 130.0));        // ~130m wavelength
	float n_med = vnoise(wp * (1.0 / 55.0) + 17.3);  // ~55m wavelength, offset
	float n_combined = mix(n_big, n_med, 0.35);      // bias toward big patches
	vec3 hsv = rgb_to_hsv(color);
	hsv.x = fract(hsv.x + (n_big - 0.5) * 0.05);     // hue ±9° (region scale)
	hsv.y = clamp(hsv.y * (1.0 + (n_med - 0.5) * 0.20), 0.0, 1.0);  // sat ±10%
	hsv.z *= 1.0 + (n_combined - 0.5) * 0.12;        // value ±6%
	color = hsv_to_rgb(hsv);

	// NO shader-level aerial haze (removed 2026-06-11, with the matching
	// removal in tree_leaf.gdshader — tiers must agree or the 250 m
	// crossfade value-steps): the calibrated volumetric fog owns the
	// distance veil (rendering.md §6c). Reference: distant canopy stays
	// saturated and DARK.

	// Re-premultiply for blend_premul_alpha output. ALPHA controls the
	// destination factor (1 - alpha); ALBEDO is added directly without a
	// second alpha multiply.
	ALBEDO = color * alpha;
	ALPHA = alpha;
	// Foliage response: roughness 1 so burley diffuse dominates and the
	// runtime sun/ambient does the lighting over the true-albedo atlas.
	ROUGHNESS = 1.0;
	SPECULAR = 0.1;
	METALLIC = 0.0;

	// Crown-interior AO (trees.md §6): depth-atlas G carries the baked
	// crown rho (bark texels 1.0); same canopy_ao mapping as the mesh
	// tiers so the crossfade is value-continuous. Ambient only.
	float crown_rho = blend_colors(uv1, uv2, uv3, v_blend_weights, atlas_depth).g;
	AO = mix(canopy_ao.x, canopy_ao.z, pow(crown_rho, canopy_ao.y));
	AO_LIGHT_AFFECT = 0.0;
}
