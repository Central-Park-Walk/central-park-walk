shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

// --- Atlas textures (8×8 hemisphere octahedral, baked per species) ---
uniform sampler2D atlas : source_color, filter_linear_mipmap;
uniform sampler2D atlas_normal : hint_normal, filter_linear_mipmap;
uniform sampler2D atlas_depth : hint_default_white, filter_linear_mipmap;
uniform vec2 frames = vec2(8.0, 8.0);
uniform float alpha_clamp = 0.3;
uniform float depth_scale : hint_range(0, 1) = 0.3;
uniform float scale = 1.0;
uniform float aabb_max = 1.0;
uniform vec3 position_offset = vec3(0.0);

// --- Global uniforms ---
global uniform float impostor_brightness;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float season_t;
global uniform vec3 sky_reflect_color;

#include "res://shaders/include/tree_species.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"

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
varying flat float v_leaf_density;
varying flat vec3 v_season_color;
varying flat float v_color_jitter;

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
	}
	// Per-tree color variation: brightness ±12%, warm/cool ±shift
	float bright_off = (jitter - 0.5) * 0.25;
	season_color *= 1.0 + bright_off;
	float warm_off = fract(jitter * 7.37) - 0.5;
	season_color += warm_off * vec3(0.025, -0.008, -0.03);
	v_leaf_density = leaf_density;
	v_season_color = season_color;
	v_color_jitter = jitter;

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

	// 3-frame blended sampling
	vec4 tex = blend_colors(uv1, uv2, uv3, v_blend_weights, atlas);

	// Alpha: modulated by leaf density (deciduous shedding)
	float alpha = tex.a * v_leaf_density;
	if (snow_cover > 0.6 && v_leaf_density < 0.3) discard;
	if (alpha < alpha_clamp) discard;

	// Normal map
	vec3 nm = blended_normals(uv1, v_frame1_normal, uv2, v_frame2_normal,
	                          uv3, v_frame3_normal, TANGENT, BINORMAL,
	                          v_blend_weights, atlas_normal);
	NORMAL = nm;

	// Recolor: extract atlas luminance, apply species season color.
	// Ambient-lit atlases have higher luminance (~0.5-0.7) than leaf textures
	// (~0.3-0.5), so we use a tighter range to match LOD0 brightness.
	float lum = dot(tex.rgb, vec3(0.3, 0.6, 0.1));
	vec3 color = v_season_color * (0.40 + lum * 0.40);

	// Desaturation — match LOD0's 20% desaturation
	float color_lum = dot(color, vec3(0.299, 0.587, 0.114));
	color = mix(vec3(color_lum), color, 0.80);

	// Warm darken — match LOD0's tonal correction
	color *= vec3(0.96, 0.94, 0.88);

	// Time-of-day brightness applied AFTER desaturation to avoid
	// distorting the saturation blend at non-unity values.
	color *= max(impostor_brightness, 0.5);

	// Top-lit via blended normal map (atlas normals already encode canopy shape).
	// Works correctly with spherical billboarding — uses actual surface orientation,
	// not UV proxy which breaks when billboard tilts for overhead views.
	vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
	float top_lit = world_n.y * 0.5 + 0.5;
	color *= mix(0.86, 1.08, top_lit);

	// Snow accumulation on upper canopy
	if (snow_cover > 0.1) {
		float snow_top = snow_cover * smoothstep(0.3, 0.7, top_lit);
		color = mix(color, vec3(0.85, 0.88, 0.92), snow_top * 0.4);
	}

	// Aerial perspective — match tree_leaf.gdshader's distance fog
	vec3 imp_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float imp_dist = length(imp_world - (INV_VIEW_MATRIX * vec4(vec3(0.0), 1.0)).xyz);
	float imp_aerial = smoothstep(60.0, 300.0, imp_dist);
	color = apply_aerial(color, imp_aerial, 0.30, 0.30, sky_reflect_color);

	ALBEDO = color;
	ROUGHNESS = 0.82;
	SPECULAR = 0.12;
	METALLIC = 0.0;
}
