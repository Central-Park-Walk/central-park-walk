shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

// Atlas texture (8×8 hemisphere octahedral impostor atlas)
uniform sampler2D atlas : source_color, filter_linear_mipmap;
uniform vec2 frames = vec2(8.0, 8.0);
uniform float alpha_clamp = 0.3;
uniform vec4 tint : source_color = vec4(1.3, 1.3, 1.25, 1.0);

global uniform float impostor_brightness;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float season_t;

// --- Species color data (matches tree_leaf.gdshader) ---
const vec3 SUMMER_COLORS[14] = vec3[14](
	vec3(0.22, 0.42, 0.14),  // 0 oak
	vec3(0.26, 0.48, 0.16),  // 1 maple
	vec3(0.30, 0.52, 0.20),  // 2 elm
	vec3(0.32, 0.54, 0.18),  // 3 birch
	vec3(0.28, 0.48, 0.18),  // 4 deciduous
	vec3(0.12, 0.28, 0.10),  // 5 conifer
	vec3(0.30, 0.50, 0.14),  // 6 honeylocust
	vec3(0.24, 0.44, 0.16),  // 7 callery_pear
	vec3(0.35, 0.52, 0.12),  // 8 ginkgo
	vec3(0.26, 0.45, 0.20),  // 9 london_plane
	vec3(0.24, 0.46, 0.16),  // 10 linden
	vec3(0.28, 0.48, 0.18),  // 11 cherry
	vec3(0.30, 0.50, 0.16),  // 12 willow
	vec3(0.22, 0.42, 0.14)   // 13 magnolia
);

const vec3 FALL_COLORS[14] = vec3[14](
	vec3(0.55, 0.25, 0.12),  // 0 oak
	vec3(0.85, 0.22, 0.08),  // 1 maple
	vec3(0.78, 0.72, 0.18),  // 2 elm
	vec3(0.82, 0.75, 0.22),  // 3 birch
	vec3(0.65, 0.45, 0.15),  // 4 deciduous
	vec3(0.14, 0.30, 0.10),  // 5 conifer
	vec3(0.80, 0.75, 0.28),  // 6 honeylocust
	vec3(0.72, 0.18, 0.12),  // 7 callery_pear
	vec3(0.92, 0.85, 0.20),  // 8 ginkgo
	vec3(0.70, 0.52, 0.18),  // 9 london_plane
	vec3(0.78, 0.70, 0.22),  // 10 linden
	vec3(0.80, 0.30, 0.15),  // 11 cherry
	vec3(0.82, 0.78, 0.25),  // 12 willow
	vec3(0.60, 0.42, 0.18)   // 13 magnolia
);

const vec4 PHENOLOGY[14] = vec4[14](
	vec4(2.3, 2.7, 3.1, 0.4),  // 0 oak
	vec4(2.1, 2.5, 2.9, 0.3),  // 1 maple
	vec4(2.2, 2.6, 3.0, 0.3),  // 2 elm
	vec4(2.0, 2.4, 2.8, 0.2),  // 3 birch
	vec4(2.2, 2.6, 3.0, 0.3),  // 4 deciduous
	vec4(0.0, 0.0, 0.0, 0.0),  // 5 conifer
	vec4(2.0, 2.3, 2.6, 0.4),  // 6 honeylocust
	vec4(2.3, 2.7, 3.1, 0.3),  // 7 callery_pear
	vec4(2.4, 2.6, 2.8, 0.5),  // 8 ginkgo
	vec4(2.2, 2.6, 3.0, 0.3),  // 9 london_plane
	vec4(2.1, 2.5, 2.9, 0.3),  // 10 linden
	vec4(2.0, 2.4, 2.8, 0.3),  // 11 cherry
	vec4(2.0, 2.3, 2.7, 0.2),  // 12 willow
	vec4(2.3, 2.6, 3.0, 0.2)   // 13 magnolia
);

// --- Varyings ---
varying flat float v_leaf_density;
varying flat vec3 v_season_color;
varying vec2 v_uv;
varying flat vec2 v_frame1;
varying flat vec2 v_frame2;
varying flat vec2 v_frame3;
varying flat vec4 v_blend_weights;

// Hemisphere octahedral mapping (matches bake_impostors.py)
vec2 hemi_octa(vec3 dir) {
	dir.y = max(dir.y, 0.001);
	dir = normalize(dir);
	vec3 octant = sign(dir);
	float sum = dot(dir, octant);
	vec3 oct = dir / sum;
	return vec2(oct.x + oct.z, oct.z - oct.x);
}

// 3-frame blend weights (matches ImpostorShader quadBlendWieghts)
vec4 calc_blend_weights(vec2 fract_grid) {
	vec4 res;
	res.x = min(1.0 - fract_grid.x, 1.0 - fract_grid.y);
	res.y = abs(fract_grid.x - fract_grid.y);
	res.z = min(fract_grid.x, fract_grid.y);
	res.w = ceil(fract_grid.x - fract_grid.y);
	return res;
}

void vertex() {
	// --- Season data from INSTANCE_CUSTOM ---
	int sp_idx = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	float is_evergreen = INSTANCE_CUSTOM.b;
	float timing_off = INSTANCE_CUSTOM.g - 0.5;
	float s = mod(season_t + timing_off, 4.0);

	// Leaf density (deciduous shedding)
	float leaf_density = 1.0;
	vec3 season_color = SUMMER_COLORS[sp_idx];
	if (is_evergreen < 0.5) {
		vec4 ph = PHENOLOGY[sp_idx];
		float shedding = 1.0 - smoothstep(ph.z - 0.2, ph.z + 0.3, s);
		float regrowth = smoothstep(ph.w - 0.1, ph.w + 0.3, s);
		leaf_density = max(shedding, regrowth);
		leaf_density = clamp(leaf_density, 0.08, 1.0);

		// Season color transitions
		vec3 fall_col = FALL_COLORS[sp_idx];
		vec3 spring_tint = season_color * vec3(1.15, 1.2, 0.7);
		float spring_t = smoothstep(ph.w, ph.w + 0.4, s);
		season_color = mix(spring_tint, season_color, spring_t);
		float fall_t = smoothstep(ph.x, ph.y, s);
		season_color = mix(season_color, fall_col, fall_t);
		float late_fall = smoothstep(ph.y, ph.z, s);
		season_color = mix(season_color, fall_col * 0.5, late_fall * 0.6);
	}
	v_leaf_density = leaf_density;
	v_season_color = season_color;

	// --- Wind sway (simplified for distant impostors) ---
	vec3 tree_pos = MODEL_MATRIX[3].xyz;
	float height_factor = max(VERTEX.y + 0.5, 0.0); // mesh Y: -0.5 to 0.5
	float wind_str = length(wind_vec);
	float rustle = 0.3 + wind_str * 0.7;
	VERTEX.x += sin(TIME * 0.7 + tree_pos.x * 0.04 + tree_pos.z * 0.06) * 0.04 * height_factor * rustle;
	VERTEX.z += sin(TIME * 1.1 + tree_pos.z * 0.05) * 0.025 * height_factor * rustle;
	VERTEX.x += wind_vec.x * height_factor * 0.08;
	VERTEX.z += wind_vec.y * height_factor * 0.08;

	// --- Atlas frame selection (octahedral hemisphere) ---
	vec3 cam_ws = (INV_VIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec3 to_cam_ws = cam_ws - tree_pos;
	// Transform camera direction to model space (accounts for per-tree Y rotation)
	mat3 model_rot = mat3(MODEL_MATRIX);
	vec3 cam_dir = normalize(transpose(model_rot) * to_cam_ws);

	vec2 grid = hemi_octa(cam_dir);
	grid = clamp((grid + 1.0) * 0.5, vec2(0.0), vec2(1.0));
	vec2 frames_m1 = frames - vec2(1.0);
	grid *= frames_m1;
	grid = clamp(grid, vec2(0.0), frames_m1);
	vec2 grid_floor = min(floor(grid), frames_m1);
	vec2 grid_fract = fract(grid);

	v_blend_weights = calc_blend_weights(grid_fract);
	v_frame1 = grid_floor;
	v_frame2 = clamp(grid_floor + mix(vec2(0.0, 1.0), vec2(1.0, 0.0), v_blend_weights.w), vec2(0.0), frames_m1);
	v_frame3 = clamp(grid_floor + vec2(1.0), vec2(0.0), frames_m1);

	v_uv = UV;
}

void fragment() {
	vec2 frame_size = vec2(1.0) / frames;

	// Sample 3 blended atlas frames
	vec4 c1 = texture(atlas, frame_size * (v_frame1 + v_uv));
	vec4 c2 = texture(atlas, frame_size * (v_frame2 + v_uv));
	vec4 c3 = texture(atlas, frame_size * (v_frame3 + v_uv));
	vec4 tex = c1 * v_blend_weights.x + c2 * v_blend_weights.y + c3 * v_blend_weights.z;

	// Alpha: modulated by leaf density
	float alpha = tex.a * v_leaf_density;
	if (snow_cover > 0.6 && v_leaf_density < 0.3) alpha = 0.0;
	if (alpha < alpha_clamp) discard;

	// Recolor: extract atlas luminance, apply species season color
	float lum = dot(tex.rgb, vec3(0.3, 0.6, 0.1));
	vec3 color = v_season_color * (lum * 2.5 + 0.15);
	color *= tint.rgb * max(impostor_brightness, 0.5);

	// Snow accumulation on upper canopy
	if (snow_cover > 0.1) {
		float snow_top = snow_cover * smoothstep(0.3, 0.7, 1.0 - v_uv.y);
		color = mix(color, vec3(0.85, 0.88, 0.92), snow_top * 0.4);
	}

	ALBEDO = color;
	ROUGHNESS = 0.85;
	SPECULAR = 0.1;
	METALLIC = 0.0;

	// Flip normal for back faces
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}
