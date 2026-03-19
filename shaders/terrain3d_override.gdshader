// Terrain3D shader override: clipmap vertex + Central Park zone/weather/season fragment
// Combines Terrain3D v1.0.1 geometry (minimum.gdshader) with our custom terrain effects.

shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx, skip_vertex_transform;

// ---- Terrain3D constants ----
#define SKIP_PASS 0
#define VERTEX_PASS 1
#define FRAGMENT_PASS 2

#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	#define fma(a, b, c) ((a) * (b) + (c))
	#define dFdxCoarse(a) dFdx(a)
	#define dFdyCoarse(a) dFdy(a)
#endif

// ---- Terrain3D private uniforms (set by C++ engine) ----
uniform vec3 _camera_pos = vec3(0.0);
uniform float _mesh_size = 48.0;
uniform uint _background_mode = 1u;
uniform uint _mouse_layer = 0x80000000u;
uniform float _vertex_spacing = 1.0;
uniform float _vertex_density = 1.0;
uniform float _region_size = 1024.0;
uniform float _region_texel_size = 0.0009765625;
uniform int _region_map_size = 32;
uniform int _region_map[1024];
uniform highp sampler2DArray _height_maps : repeat_disable;
uniform highp sampler2DArray _control_maps : repeat_disable;

// ---- Our custom uniforms ----

// Grass textures
uniform sampler2D grass_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_rough : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float tile_m = 6.0;

// Meadow/wild grass
uniform sampler2D meadow_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D meadow_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D meadow_rough : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float meadow_tile_m = 4.0;

// Rock (Manhattan schist)
uniform sampler2D rock_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_rough : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float rock_tile_m = 3.0;

// Dirt (playgrounds, dog parks)
uniform sampler2D dirt_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D dirt_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D dirt_rough : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float dirt_tile_m = 2.0;

// Shore/mud
uniform sampler2D shore_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D shore_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D shore_rough : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float shore_tile_m = 3.0;

// Anti-tiling noise
uniform sampler2D tile_noise : filter_linear_mipmap, repeat_enable;

// Data maps
uniform float world_size = 5000.0;
uniform sampler2DArray path_alb_arr : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray path_nrm_arr : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray path_rgh_arr : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float path_tile_m = 2.5;
uniform sampler2D park_mask : filter_linear, repeat_disable;
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform sampler2D shore_distance : filter_linear, repeat_disable;
uniform sampler2D structure_mask : filter_linear, repeat_disable;
uniform sampler2D canopy_map : filter_linear, repeat_disable;

// Global uniforms (set by main.gd via RenderingServer)
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform float season_t;
global uniform vec3 sky_reflect_color;
global uniform vec2 wind_vec;
global uniform float dew_amount;
global uniform float cloud_coverage_g;
global uniform float cloud_speed_g;

// ---- Terrain3D varyings ----
varying float v_vertex_xz_dist;
varying vec3 v_vertex;

// ===========================================================================
// Terrain3D vertex functions (from minimum.gdshader — DO NOT MODIFY)
// ===========================================================================

ivec3 get_index_coord(const vec2 uv, const int search) {
	vec2 r_uv = round(uv);
	vec2 o_uv = mod(r_uv, _region_size);
	ivec2 pos;
	int bounds, layer_index = -1;
	for (int i = -1; i < clamp(search, SKIP_PASS, FRAGMENT_PASS); i++) {
		if ((layer_index == -1 && _background_mode == 0u) || i < 0) {
			r_uv -= i == -1 ? vec2(0.0) : vec2(float(o_uv.x <= o_uv.y), float(o_uv.y <= o_uv.x));
			pos = ivec2(floor((r_uv) * _region_texel_size)) + (_region_map_size / 2);
			bounds = int(uint(pos.x | pos.y) < uint(_region_map_size));
			layer_index = (_region_map[pos.y * _region_map_size + pos.x] * bounds - 1);
		}
	}
	return ivec3(ivec2(mod(r_uv, _region_size)), layer_index);
}

void vertex() {
	v_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_vertex_xz_dist = length(v_vertex.xz - _camera_pos.xz);

	float scale = MODEL_MATRIX[0][0];
	float vertex_lerp = smoothstep(0.55, 0.95, (v_vertex_xz_dist / scale - _mesh_size - 4.0) / (_mesh_size - 2.0));
	vec2 v_fract = fract(VERTEX.xz * 0.5) * 2.0;
	vec2 shift = (scale < _vertex_spacing + 1e-6) ?
		mix(v_fract, vec2(v_fract.x, -v_fract.y),
			round(fract(round(mod(v_vertex.z * _vertex_density, 4.0)) *
			round(mod(v_vertex.x * _vertex_density, 4.0)) * 0.25))) :
		v_fract * round((fract(v_vertex.xz * 0.25 / scale) - 0.5) * 4.0);
	vec2 start_pos = v_vertex.xz * _vertex_density;
	vec2 end_pos = (v_vertex.xz - shift * scale) * _vertex_density;
	v_vertex.xz -= shift * scale * vertex_lerp;

	UV = v_vertex.xz * _vertex_density;
	UV2 = fma(UV, vec2(_region_texel_size), vec2(0.5 * _region_texel_size));

	ivec3 v_region = get_index_coord(start_pos, VERTEX_PASS);
	uint control = floatBitsToUint(texelFetch(_control_maps, v_region, 0)).r;
	bool hole = bool(control >> 2u & 0x1u);

	if (!(CAMERA_VISIBLE_LAYERS == _mouse_layer) &&
			(hole || (_background_mode == 0u && v_region.z < 0))) {
		v_vertex.x = 0.0 / 0.0;
	} else {
		ivec3 uv_a = get_index_coord(start_pos, VERTEX_PASS);
		ivec3 uv_b = get_index_coord(end_pos, VERTEX_PASS);
		float h = mix(texelFetch(_height_maps, uv_a, 0).r, texelFetch(_height_maps, uv_b, 0).r, vertex_lerp);
		v_vertex.y = h;
	}

	VERTEX = (VIEW_MATRIX * vec4(v_vertex, 1.0)).xyz;
	NORMAL = normalize((MODELVIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	BINORMAL = normalize((MODELVIEW_MATRIX * vec4(BINORMAL, 0.0)).xyz);
	TANGENT = normalize((MODELVIEW_MATRIX * vec4(TANGENT, 0.0)).xyz);
}

// ===========================================================================
// Hash & noise (inlined from hash_noise.gdshaderinc)
// ===========================================================================

float hash2(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 43.21);
	return fract(p.x * p.y);
}

float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1.0, 0.0)), u.x),
	           mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p, int oct) {
	float v = 0.0, a = 0.5;
	for (int i = 0; i < oct; i++) { v += a * vnoise(p); p *= 2.13; a *= 0.47; }
	return v;
}

float cloud_shadow(vec2 world_xz, float cloud_coverage_val, float cloud_speed_val,
                   float time_val, vec2 wind_val) {
	vec2 cloud_uv = world_xz * 0.00016;
	vec2 drift = vec2(cloud_speed_val, cloud_speed_val * 0.7) + wind_val * 0.002;
	cloud_uv += time_val * drift;
	float n = vnoise(cloud_uv * 3.0) * 0.5
	        + vnoise(cloud_uv * 6.0) * 0.3
	        + vnoise(cloud_uv * 12.0) * 0.2;
	float shadow = smoothstep(1.0 - cloud_coverage_val - 0.05,
	                          1.0 - cloud_coverage_val + 0.15, n);
	return shadow * 0.25;
}

// ===========================================================================
// Anti-tiling texture sampling (Inigo Quilez)
// ===========================================================================

vec3 textureNoTile_c(sampler2D tex, vec2 uv) {
	float k = texture(tile_noise, uv * 0.0085).x;
	vec2 duvdx = dFdx(uv); vec2 duvdy = dFdy(uv);
	float l = k * 12.0;
	float f = fract(l);
	vec2 offa = sin(vec2(3.0, 7.0) * floor(l));
	vec2 offb = sin(vec2(3.0, 7.0) * ceil(l));
	vec3 cola = textureGrad(tex, uv + offa, duvdx, duvdy).rgb;
	vec3 colb = textureGrad(tex, uv + offb, duvdx, duvdy).rgb;
	return mix(cola, colb, smoothstep(0.15, 0.85, f - 0.1 * dot(cola - colb, vec3(1.0))));
}

vec3 textureNoTile_n(sampler2D tex, vec2 uv) {
	float k = texture(tile_noise, uv * 0.0085).x;
	vec2 duvdx = dFdx(uv); vec2 duvdy = dFdy(uv);
	float l = k * 12.0;
	float f = fract(l);
	vec2 offa = sin(vec2(3.0, 7.0) * floor(l));
	vec2 offb = sin(vec2(3.0, 7.0) * ceil(l));
	vec3 na = textureGrad(tex, uv + offa, duvdx, duvdy).rgb;
	vec3 nb = textureGrad(tex, uv + offb, duvdx, duvdy).rgb;
	return mix(na, nb, smoothstep(0.15, 0.85, f));
}

float textureNoTile_r(sampler2D tex, vec2 uv) {
	float k = texture(tile_noise, uv * 0.0085).x;
	vec2 duvdx = dFdx(uv); vec2 duvdy = dFdy(uv);
	float l = k * 12.0;
	float f = fract(l);
	vec2 offa = sin(vec2(3.0, 7.0) * floor(l));
	vec2 offb = sin(vec2(3.0, 7.0) * ceil(l));
	float ra = textureGrad(tex, uv + offa, duvdx, duvdy).r;
	float rb = textureGrad(tex, uv + offb, duvdx, duvdy).r;
	return mix(ra, rb, smoothstep(0.15, 0.85, f));
}

// ===========================================================================
// Fragment: Terrain3D normal calculation + Central Park terrain effects
// ===========================================================================

void fragment() {
	vec2 uv = UV;

	// ---- Terrain3D normal calculation (from minimum.gdshader) ----
	const vec3 offsets = vec3(0, 1, 2);
	vec2 index_id = floor(uv);
	vec2 weight = fract(uv);
	vec2 invert = 1.0 - weight;
	vec4 weights = vec4(
		invert.x * weight.y,
		weight.x * weight.y,
		weight.x * invert.y,
		invert.x * invert.y
	);

	vec3 base_ddx = dFdxCoarse(v_vertex);
	vec3 base_ddy = dFdyCoarse(v_vertex);
	float region_mip = log2(max(length(base_ddx.xz), length(base_ddy.xz)) * _vertex_density);
	bool bilerp = region_mip < 0.0;

	ivec3 index[4];
	index[0] = get_index_coord(index_id + offsets.xy, FRAGMENT_PASS);
	index[1] = get_index_coord(index_id + offsets.yy, FRAGMENT_PASS);
	index[2] = get_index_coord(index_id + offsets.yx, FRAGMENT_PASS);
	index[3] = get_index_coord(index_id + offsets.xx, FRAGMENT_PASS);

	vec3 index_normal[4];
	float h[4];
	float u_deriv = 0.0;
	float v_deriv = 0.0;

	h[3] = texelFetch(_height_maps, index[3], 0).r;
	h[2] = texelFetch(_height_maps, index[2], 0).r;
	h[0] = texelFetch(_height_maps, index[0], 0).r;
	index_normal[3] = normalize(vec3(h[3] - h[2] + u_deriv, _vertex_spacing, h[3] - h[0] + v_deriv));

	vec3 w_normal = index_normal[3];

	if (bilerp) {
		h[1] = texelFetch(_height_maps, index[1], 0).r;
		float h_4 = texelFetch(_height_maps, get_index_coord(index_id + offsets.yz, FRAGMENT_PASS), 0).r;
		float h_5 = texelFetch(_height_maps, get_index_coord(index_id + offsets.zy, FRAGMENT_PASS), 0).r;
		float h_6 = texelFetch(_height_maps, get_index_coord(index_id + offsets.zx, FRAGMENT_PASS), 0).r;
		float h_7 = texelFetch(_height_maps, get_index_coord(index_id + offsets.xz, FRAGMENT_PASS), 0).r;

		index_normal[0] = normalize(vec3(h[0] - h[1] + u_deriv, _vertex_spacing, h[0] - h_7 + v_deriv));
		index_normal[1] = normalize(vec3(h[1] - h_5 + u_deriv, _vertex_spacing, h[1] - h_4 + v_deriv));
		index_normal[2] = normalize(vec3(h[2] - h_6 + u_deriv, _vertex_spacing, h[2] - h[1] + v_deriv));

		w_normal =
			index_normal[0] * weights[0] +
			index_normal[1] * weights[1] +
			index_normal[2] * weights[2] +
			index_normal[3] * weights[3];
	}

	// TBN from terrain normal
	vec3 w_tangent = normalize(cross(w_normal, vec3(0.0, 0.0, 1.0)));
	vec3 w_binormal = normalize(cross(w_normal, w_tangent));
	NORMAL = mat3(VIEW_MATRIX) * w_normal;
	TANGENT = mat3(VIEW_MATRIX) * w_tangent;
	BINORMAL = mat3(VIEW_MATRIX) * w_binormal;

	// ==================================================================
	// Central Park terrain texturing — everything below uses:
	//   v_vertex  (world position)
	//   w_normal  (terrain normal, y-up)
	//   w_tangent / w_binormal (for TBN normal mapping)
	// ==================================================================

	// Atlas UV for data map lookups
	vec2 splat_uv = (v_vertex.xz + world_size * 0.5) / world_size;
	float park_inside = texture(park_mask, splat_uv).r;

	// Zone lookup
	float zone_val = texture(landuse_map, splat_uv).r * 255.0;
	int zone_id = int(zone_val + 0.5);
	bool is_woodland = (zone_id == 5 || zone_id == 10 || zone_id == 11);
	bool is_grass_zone = (zone_id == 0 || zone_id == 1 || zone_id == 2
	                   || zone_id == 3 || zone_id == 7);

	// Camera metrics
	float cam_dist = length(v_vertex - _camera_pos);
	float cam_height = _camera_pos.y - v_vertex.y;
	float tex_fade = max(
		smoothstep(15.0, 50.0, cam_height),
		smoothstep(100.0, 250.0, cam_dist)
	);

	// ---- Base surface: zone-aware ----
	vec2 g_uv;
	vec3 grass_alb;
	if (is_grass_zone || is_woodland) {
		g_uv = v_vertex.xz / tile_m;
		grass_alb = textureNoTile_c(grass_albedo, g_uv);
		float avg_g = dot(grass_alb, vec3(0.299, 0.587, 0.114));
		grass_alb = mix(grass_alb, vec3(avg_g), tex_fade);
		grass_alb *= 0.85;
	} else {
		g_uv = v_vertex.xz / dirt_tile_m;
		grass_alb = textureNoTile_c(dirt_albedo, g_uv);
		float avg_g = dot(grass_alb, vec3(0.299, 0.587, 0.114));
		grass_alb = mix(grass_alb, vec3(avg_g), tex_fade);
		grass_alb *= 0.75;
	}

	// ---- Hexaquo grass impostor ----
	vec3 grass_ground = vec3(0.07, 0.15, 0.04);
	float green_blend = is_grass_zone ? 0.85 : (is_woodland ? 0.55 : 0.0);

	if (is_grass_zone || is_woodland) {
		float patch = vnoise(v_vertex.xz / 3.0);
		vec3 color_small = vec3(0.12, 0.28, 0.06);
		vec3 color_large = vec3(0.30, 0.40, 0.12);
		vec3 imp_col = mix(color_small, color_large, patch);

		vec3 view_dir = normalize(_camera_pos - v_vertex);
		float normal_to_view = 1.0 - max(dot(view_dir, w_normal), 0.0);
		imp_col = mix(imp_col, color_large, normal_to_view * 0.4);

		float wind_str = length(wind_vec);
		vec2 wind_pos = v_vertex.xz * 0.1 - wind_vec * TIME * 0.1;
		float wind_bend = vnoise(wind_pos) * wind_str;

		float ao_noise = vnoise(v_vertex.xz * 0.8);
		float btt_sim = ao_noise + smoothstep(0.6, 1.0, normal_to_view) * 0.4;
		float ao = mix(0.5, 1.0, btt_sim) - wind_bend * 0.3;
		imp_col *= clamp(ao, 0.3, 1.0);

		float spots = vnoise(v_vertex.xz * 2.0);
		float spottiness = (1.0 - normal_to_view) * 0.5 - patch * 0.2;
		float ground_show = smoothstep(spottiness + 0.1, spottiness - 0.1, spots);
		imp_col = mix(imp_col, grass_ground, ground_show);

		// Canopy → leaf litter under dense canopy
		vec2 can_uv = splat_uv;
		float canopy_cover = texture(canopy_map, can_uv).r;
		if (canopy_cover > 0.3) {
			vec3 litter_col = vec3(0.28, 0.22, 0.14);
			float litter_noise = vnoise(v_vertex.xz * 0.5);
			litter_col = mix(litter_col, vec3(0.34, 0.26, 0.16), litter_noise);
			float litter_blend = smoothstep(0.3, 0.7, canopy_cover) * 0.70;
			imp_col = mix(imp_col, litter_col, litter_blend);
		}
		if (is_woodland) {
			imp_col *= vec3(0.85, 0.88, 0.75);
		}

		float impostor_t = smoothstep(5.0, 15.0, cam_dist);
		vec3 grass_target = mix(grass_ground, imp_col, impostor_t);
		grass_alb = mix(grass_alb, grass_target, green_blend);
	}

	// Distance darkening + aerial perspective
	float dist_darken = smoothstep(30.0, 150.0, cam_dist) * 0.25;
	grass_alb *= (1.0 - dist_darken);
	float aerial_t = smoothstep(60.0, 300.0, cam_dist);
	float g_lum = dot(grass_alb, vec3(0.2126, 0.7152, 0.0722));
	grass_alb = mix(grass_alb, vec3(g_lum), aerial_t * 0.25);
	grass_alb = mix(grass_alb, grass_alb * vec3(0.94, 0.96, 1.04), aerial_t);

	// ---- Seasonal grass color ----
	{
		float spring_t = 1.0 - smoothstep(0.0, 1.0, season_t);
		float autumn_t = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(2.8, 3.5, season_t));
		float winter_t = smoothstep(2.7, 3.1, season_t);
		vec3 spring_grass = grass_alb * vec3(1.1, 1.15, 0.75);
		vec3 autumn_grass = vec3(0.16, 0.12, 0.04);
		vec3 winter_grass = vec3(0.12, 0.10, 0.06);
		grass_alb = mix(grass_alb, spring_grass, spring_t * 0.6);
		grass_alb = mix(grass_alb, autumn_grass, autumn_t * 0.7);
		grass_alb = mix(grass_alb, winter_grass, winter_t);
	}

	// Normal map sampling
	vec3 grass_nrm = textureNoTile_n(grass_normal, g_uv);
	grass_nrm = mix(grass_nrm, vec3(0.5, 0.5, 1.0), tex_fade);
	float grass_rgh = clamp(textureNoTile_r(grass_rough, g_uv) * 0.20 + 0.65, 0.0, 1.0);

	// Winter: flatten normals + force rough
	{
		float w_t = smoothstep(2.7, 3.1, season_t);
		grass_nrm = mix(grass_nrm, vec3(0.5, 0.5, 1.0), w_t);
		grass_rgh = mix(grass_rgh, 0.95, w_t);
	}

	// ---- Meadow blend (woodland zones) ----
	vec2 muv = v_vertex.xz / meadow_tile_m;
	float s60 = 0.866; float c60 = 0.5;
	vec2 muv_rot = vec2(muv.x * c60 + muv.y * s60, -muv.x * s60 + muv.y * c60);
	vec3 m_alb = texture(meadow_albedo, muv_rot).rgb;
	{
		float m_lum = dot(m_alb, vec3(0.299, 0.587, 0.114));
		m_alb = mix(m_alb, vec3(m_lum), tex_fade);
	}
	vec3 m_nrm_raw = texture(meadow_normal, muv_rot).rgb;
	vec3 m_nrm = vec3(
		(m_nrm_raw.r - 0.5) * c60 + (m_nrm_raw.g - 0.5) * s60 + 0.5,
		-(m_nrm_raw.r - 0.5) * s60 + (m_nrm_raw.g - 0.5) * c60 + 0.5,
		m_nrm_raw.b);
	m_nrm = mix(m_nrm, vec3(0.5, 0.5, 1.0), tex_fade);
	float m_rgh = clamp(texture(meadow_rough, muv).r * 0.20 + 0.65, 0.0, 1.0);

	float meadow_blend = is_woodland ? 1.0 : 0.0;
	grass_alb = mix(grass_alb, m_alb, meadow_blend);
	grass_nrm = mix(grass_nrm, m_nrm, meadow_blend);
	grass_rgh = mix(grass_rgh, m_rgh, meadow_blend);

	// ---- Olmsted landscape modes ----
	if (is_woodland) {
		grass_alb = mix(grass_alb, vec3(0.04, 0.06, 0.03), 0.5);
	} else if (zone_id == 1) {
		grass_alb *= 1.15;
		float sat = dot(grass_alb, vec3(0.299, 0.587, 0.114));
		grass_alb = mix(vec3(sat), grass_alb, 0.80);
	} else if (zone_id == 2) {
		grass_alb.r *= 1.08; grass_alb.g *= 1.06; grass_alb.b *= 0.85;
	} else if (zone_id == 3 || zone_id == 7) {
		grass_alb.g *= 1.12; grass_alb *= 1.08;
	} else if (zone_id == 5) {
		grass_alb.r *= 1.12; grass_alb.b *= 0.80;
	}

	// ---- Dirt/mulch for playgrounds, dog parks ----
	bool is_dirt = (zone_id == 4 || zone_id == 6);
	if (is_dirt) {
		vec2 duv = v_vertex.xz / dirt_tile_m;
		vec3 d_alb = textureNoTile_c(dirt_albedo, duv);
		vec3 d_nrm = textureNoTile_n(dirt_normal, duv);
		float d_rgh = clamp(textureNoTile_r(dirt_rough, duv) * 0.15 + 0.80, 0.0, 1.0);
		grass_alb = mix(grass_alb, d_alb, 0.85);
		grass_nrm = mix(grass_nrm, d_nrm, 0.85);
		grass_rgh = mix(grass_rgh, d_rgh, 0.85);
	}

	// ---- Slope + rock detection ----
	float slope = 1.0 - w_normal.y;

	// Running track (zone 9)
	if (zone_id == 9) {
		vec2 duv = v_vertex.xz / dirt_tile_m;
		vec3 d_alb = textureNoTile_c(dirt_albedo, duv);
		vec3 d_nrm = textureNoTile_n(dirt_normal, duv);
		float d_rgh = clamp(textureNoTile_r(dirt_rough, duv) * 0.15 + 0.72, 0.0, 1.0);
		vec3 cinder_tint = vec3(0.52, 0.32, 0.22);
		d_alb = mix(d_alb, d_alb * cinder_tint * 2.5, 0.6);
		grass_alb = mix(grass_alb, d_alb, 0.90);
		grass_nrm = mix(grass_nrm, d_nrm, 0.90);
		grass_rgh = mix(grass_rgh, d_rgh, 0.90);
	}

	// ---- Shore transition ----
	vec2 shore_sample = texture(shore_distance, splat_uv).ra;
	float shore_dist_m = shore_sample.r * 30.0;
	if (shore_dist_m < 15.0) {
		vec2 suv = v_vertex.xz / shore_tile_m;
		vec3 sh_alb = textureNoTile_c(shore_albedo, suv);
		vec3 sh_nrm = textureNoTile_n(shore_normal, suv);
		float sh_rgh = clamp(textureNoTile_r(shore_rough, suv) * 0.15 + 0.80, 0.0, 1.0);
		float shore_blend = smoothstep(15.0, 2.0, shore_dist_m);
		shore_blend = clamp(shore_blend, 0.0, 1.0);
		grass_alb = mix(grass_alb, sh_alb, shore_blend);
		grass_nrm = mix(grass_nrm, sh_nrm, shore_blend);
		grass_rgh = mix(grass_rgh, sh_rgh, shore_blend);
	}

	// Water zone (12) — muddy ground
	float water_near = 0.0;
	if (zone_id == 12) {
		water_near = 1.0;
	} else if (shore_dist_m < 3.0) {
		water_near = smoothstep(3.0, 0.5, shore_dist_m);
	}
	if (water_near > 0.01) {
		vec3 mud_col = vec3(0.16, 0.13, 0.09);
		grass_alb = mix(grass_alb, mud_col, clamp(water_near, 0.0, 1.0));
		grass_rgh = mix(grass_rgh, 0.92, clamp(water_near, 0.0, 1.0));
	}

	// ---- Rock on steep slopes (Manhattan schist) ----
	float rock_blend = smoothstep(0.10, 0.25, slope);
	float struct_pre = texture(structure_mask, splat_uv).r * 254.0;
	rock_blend *= (1.0 - smoothstep(0.5, 4.0, struct_pre));
	float rock_specular = 0.0;
	if (rock_blend > 0.01) {
		vec2 ruv = v_vertex.xz / rock_tile_m;
		vec3 r_alb = textureNoTile_c(rock_albedo, ruv);
		float r_lum = dot(r_alb, vec3(0.2126, 0.7152, 0.0722));
		vec3 schist_gray = vec3(0.13, 0.14, 0.16) + vec3(0.30, 0.30, 0.32) * r_lum;
		r_alb = mix(r_alb, schist_gray, 0.70);
		vec3 r_nrm = textureNoTile_n(rock_normal, ruv);
		float r_rgh = clamp(textureNoTile_r(rock_rough, ruv) * 0.15 + 0.70, 0.0, 1.0);
		grass_alb = mix(grass_alb, r_alb, rock_blend);
		grass_nrm = mix(grass_nrm, r_nrm, rock_blend);
		grass_rgh = mix(grass_rgh, r_rgh, rock_blend);
		rock_specular = rock_blend * 0.30;
	}

	// ---- Structure mask: LiDAR-detected built features ----
	float struct_val = texture(structure_mask, splat_uv).r * 254.0;
	struct_val *= smoothstep(0.3, 0.9, park_inside);
	if (struct_val > 0.5) {
		vec2 stuv = v_vertex.xz / path_tile_m;
		float struct_h = struct_val;
		float struct_slope = slope;
		float warmth = 0.5;
		if (struct_slope > 0.35) warmth = mix(warmth, 0.15, struct_slope);
		// Named location material overrides
		float d_beth_s = length(v_vertex.xz - vec2(-458.0, 949.0));
		if (d_beth_s < 60.0) warmth = 0.85;
		float d_belv = length(v_vertex.xz - vec2(-215.0, 372.0));
		if (d_belv < 50.0) warmth = 0.15;
		float d_gap = length(v_vertex.xz - vec2(-355.0, 1640.0));
		if (d_gap < 25.0) warmth = 0.18;
		float d_hudd = length(v_vertex.xz - vec2(300.0, -1050.0));
		if (d_hudd < 20.0) warmth = 0.10;
		float d_dairy = length(v_vertex.xz - vec2(-500.0, 1425.0));
		if (d_dairy < 25.0) warmth = 0.65;
		float d_dana = length(v_vertex.xz - vec2(400.0, -1800.0));
		if (d_dana < 20.0) warmth = 0.70;
		float d_naum = length(v_vertex.xz - vec2(-600.0, 1500.0));
		if (d_naum < 15.0) warmth = 0.75;
		vec3 s_tint;
		float tex_layer;
		if (struct_slope > 0.35) {
			tex_layer = 2.0;
			vec3 cool_base = vec3(0.32, 0.33, 0.35);
			vec3 warm_base = vec3(0.52, 0.47, 0.35);
			s_tint = mix(cool_base, warm_base, smoothstep(0.4, 0.6, warmth));
		} else if (struct_slope > 0.08) {
			tex_layer = 2.0;
			vec3 cool_step = vec3(0.58, 0.56, 0.52);
			vec3 warm_step = vec3(0.62, 0.56, 0.46);
			s_tint = mix(cool_step, warm_step, smoothstep(0.4, 0.6, warmth));
		} else {
			if (struct_h > 16.0) {
				tex_layer = 0.0;
				s_tint = vec3(0.44, 0.42, 0.40);
			} else {
				tex_layer = 1.0;
				s_tint = vec3(0.66, 0.63, 0.58);
			}
		}
		vec3 s_alb = texture(path_alb_arr, vec3(stuv, tex_layer)).rgb * s_tint;
		vec3 s_nrm = texture(path_nrm_arr, vec3(stuv, tex_layer)).rgb;
		float s_rgh = clamp(texture(path_rgh_arr, vec3(stuv, tex_layer)).r + 0.08, 0.0, 1.0);
		float s_blend = smoothstep(0.5, 2.0, struct_val);
		grass_alb = mix(grass_alb, s_alb, s_blend);
		grass_nrm = mix(grass_nrm, s_nrm, s_blend);
		grass_rgh = mix(grass_rgh, s_rgh, s_blend);
	}

	// ---- Named plaza overrides ----
	// Bethesda herringbone brick
	float d_beth = length(v_vertex.xz - vec2(-458.0, 949.0));
	if (d_beth < 35.0 && slope < 0.15) {
		vec2 brick_uv = v_vertex.xz * 4.0;
		float bx = fract(brick_uv.x * 0.707 + brick_uv.y * 0.707);
		float bz = fract(brick_uv.x * 0.707 - brick_uv.y * 0.707);
		float herring = step(0.5, bx) * step(0.5, bz) + (1.0 - step(0.5, bx)) * (1.0 - step(0.5, bz));
		float mortar = smoothstep(0.02, 0.04, min(fract(bx * 2.0), fract(bz * 2.0)));
		vec3 brick_col = mix(vec3(0.63, 0.32, 0.18), vec3(0.55, 0.28, 0.15), herring);
		brick_col = mix(vec3(0.72, 0.68, 0.62), brick_col, mortar);
		float beth_blend = smoothstep(35.0, 28.0, d_beth);
		grass_alb = mix(grass_alb, brick_col, beth_blend);
		grass_rgh = mix(grass_rgh, 0.78, beth_blend);
	}

	// Conservatory Garden
	float d_cg = length(v_vertex.xz - vec2(1080.0, -1195.0));
	if (d_cg < 100.0 && slope < 0.10) {
		float cg_blend = smoothstep(100.0, 70.0, d_cg);
		float sat = dot(grass_alb, vec3(0.299, 0.587, 0.114));
		vec3 formal_green = mix(vec3(sat), grass_alb, 0.80) * 1.08;
		grass_alb = mix(grass_alb, formal_green, cg_blend);
	}

	// Shakespeare Garden
	float d_shk = length(v_vertex.xz - vec2(-389.0, 343.0));
	if (d_shk < 55.0) {
		float shk_blend = smoothstep(55.0, 35.0, d_shk);
		grass_alb = mix(grass_alb, grass_alb * vec3(1.08, 0.98, 0.85), shk_blend);
		grass_rgh = mix(grass_rgh, grass_rgh + 0.05, shk_blend);
	}

	// Cherry Hill bluestone
	float d_ch = length(v_vertex.xz - vec2(-580.0, 920.0));
	if (d_ch < 30.0 && slope < 0.12) {
		float ch_blend = smoothstep(30.0, 18.0, d_ch);
		grass_alb = mix(grass_alb, vec3(0.42, 0.46, 0.50), ch_blend);
		grass_rgh = mix(grass_rgh, 0.72, ch_blend);
	}

	// Naumburg Bandshell plaza
	float d_naum_p = length(v_vertex.xz - vec2(-600.0, 1500.0));
	if (d_naum_p < 20.0 && slope < 0.10) {
		float naum_blend = smoothstep(20.0, 12.0, d_naum_p);
		grass_alb = mix(grass_alb, vec3(0.50, 0.48, 0.45), naum_blend);
		grass_rgh = mix(grass_rgh, 0.65, naum_blend);
	}

	// The Mall corridor
	bool in_mall_corridor = (v_vertex.x > -680.0 && v_vertex.x < -430.0 && v_vertex.z > 1200.0 && v_vertex.z < 1520.0);
	if (in_mall_corridor && slope < 0.08) {
		vec3 formal_green = grass_alb * vec3(1.0, 1.08, 0.88);
		float sat = dot(formal_green, vec3(0.299, 0.587, 0.114));
		formal_green = mix(vec3(sat), formal_green, 0.85);
		grass_alb = mix(grass_alb, formal_green, 0.35);
		grass_rgh = mix(grass_rgh, grass_rgh * 0.95, 0.35);
	}

	// Great Lawn
	float d_gl = length(v_vertex.xz - vec2(0.0, 100.0));
	if (d_gl < 200.0 && slope < 0.08) {
		float gl_blend = smoothstep(200.0, 150.0, d_gl);
		grass_alb = mix(grass_alb, vec3(0.04, 0.10, 0.03), gl_blend * 0.3);
	}

	// Harlem Meer
	float d_hm = length(v_vertex.xz - vec2(350.0, -1750.0));
	if (d_hm < 80.0) {
		float hm_blend = smoothstep(80.0, 40.0, d_hm);
		grass_alb = mix(grass_alb, grass_alb * vec3(0.92, 1.06, 0.90), hm_blend);
	}

	// Conservatory Water surround
	float d_cw = length(v_vertex.xz - vec2(-152.0, 958.0));
	if (d_cw < 45.0 && d_cw > 20.0 && slope < 0.10) {
		float cw_blend = smoothstep(45.0, 35.0, d_cw) * smoothstep(20.0, 28.0, d_cw);
		grass_alb = mix(grass_alb, vec3(0.55, 0.53, 0.50), cw_blend * 0.6);
		grass_rgh = mix(grass_rgh, 0.60, cw_blend * 0.5);
	}

	// Sheep Meadow
	float d_sm = length(v_vertex.xz - vec2(-750.0, 1800.0));
	if (d_sm < 200.0 && slope < 0.06) {
		float sm_blend = smoothstep(200.0, 120.0, d_sm);
		grass_alb = mix(grass_alb, grass_alb * vec3(1.04, 1.02, 0.92), sm_blend);
	}

	// Strawberry Fields
	float d_sf = length(v_vertex.xz - vec2(-790.0, 820.0));
	if (d_sf < 60.0 && slope < 0.10) {
		float sf_blend = smoothstep(60.0, 30.0, d_sf);
		float sf_lum = dot(grass_alb, vec3(0.299, 0.587, 0.114));
		vec3 formal = mix(vec3(sf_lum), grass_alb, 0.80) * vec3(0.98, 1.06, 0.92);
		grass_alb = mix(grass_alb, formal, sf_blend);
		grass_rgh = mix(grass_rgh, grass_rgh * 0.95, sf_blend);
	}

	// North Woods / Ramble woodland proximity
	float d_ramble = length(v_vertex.xz - vec2(-400.0, 600.0));
	float d_nwoods = length(v_vertex.xz - vec2(100.0, -1200.0));
	float woodland_prox = max(
		smoothstep(250.0, 100.0, d_ramble),
		smoothstep(300.0, 100.0, d_nwoods)
	);
	if (woodland_prox > 0.01) {
		grass_alb = mix(grass_alb, grass_alb * vec3(0.90, 0.98, 0.95), woodland_prox * 0.5);
		grass_alb *= mix(1.0, 0.88, woodland_prox);
	}

	// ---- Dappled canopy shade ----
	{
		float canopy = texture(canopy_map, splat_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = smoothstep(2.5, 3.2, season_t);
			float winter_bare = smoothstep(3.0, 3.5, season_t);
			float spring_fill = smoothstep(0.0, 0.4, season_t);
			float seasonal_canopy = canopy;
			seasonal_canopy *= mix(1.0, 0.3, deciduous_loss);
			seasonal_canopy *= mix(1.0, 0.15, winter_bare);
			seasonal_canopy *= mix(0.5, 1.0, spring_fill);

			vec2 dapple_uv = v_vertex.xz * 0.35 + wind_vec * TIME * 0.08;
			float dapple = vnoise(dapple_uv);
			float dapple_fine = vnoise(v_vertex.xz * 1.2 + wind_vec * TIME * 0.15);
			float light_gap = smoothstep(0.35, 0.65, dapple) * 0.6
				+ smoothstep(0.55, 0.75, dapple_fine) * 0.4;

			float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum);

			float shade = seasonal_canopy * sun_factor;
			float shade_amount = shade * (1.0 - light_gap) * 0.50;
			grass_alb *= (1.0 - shade_amount);
			float warm_spots = light_gap * shade;
			grass_alb *= vec3(1.0 + warm_spots * 0.15, 1.0 + warm_spots * 0.10, 1.0 - warm_spots * 0.05);
		}
	}

	// ---- NYC sidewalk outside park ----
	if (park_inside < 0.95) {
		vec2 city_uv = v_vertex.xz / path_tile_m;
		float is_street = smoothstep(0.02, 0.005, slope);
		float city_layer = mix(1.0, 0.0, is_street);
		vec3 city_alb = texture(path_alb_arr, vec3(city_uv, city_layer)).rgb;
		vec3 city_nrm = texture(path_nrm_arr, vec3(city_uv, city_layer)).rgb;
		float city_rgh = texture(path_rgh_arr, vec3(city_uv, city_layer)).r;
		city_alb *= mix(vec3(0.72, 0.70, 0.66), vec3(0.42, 0.40, 0.38), is_street);
		city_rgh = mix(0.78, 0.68, is_street);
		float city_blend = 1.0 - smoothstep(0.3, 0.95, park_inside);
		grass_alb = mix(grass_alb, city_alb, city_blend);
		grass_nrm = mix(grass_nrm, city_nrm, city_blend);
		grass_rgh = mix(grass_rgh, city_rgh, city_blend);
	}

	// Per-pixel micro-variation
	vec2 terr_px = v_vertex.xz * 23.7 + vec2(v_vertex.y * 5.1);
	float terr_pn = hash2(terr_px) * 0.05 - 0.025;
	float terr_hr = hash2(terr_px + vec2(71.9, 0.0)) * 0.02;
	float terr_hb = hash2(terr_px + vec2(0.0, 53.1)) * 0.02;
	grass_alb += vec3(terr_pn + terr_hr, terr_pn, terr_pn + terr_hb);

	// Cloud shadows
	float sky_lum_cs = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
	float daytime = smoothstep(0.05, 0.20, sky_lum_cs);
	float c_shadow = cloud_shadow(v_vertex.xz, cloud_coverage_g, cloud_speed_g,
	                               TIME, wind_vec) * daytime;
	grass_alb *= (1.0 - c_shadow);

	// ---- Apply PBR ----
	ALBEDO = grass_alb;
	// Normal mapping via TBN
	vec3 _gn = grass_nrm * 2.0 - 1.0;
	_gn.xy *= 0.8;
	vec3 _gfn = normalize(w_tangent * _gn.x + w_binormal * _gn.y + w_normal * _gn.z);
	NORMAL = normalize(mat3(VIEW_MATRIX) * _gfn);
	ROUGHNESS = grass_rgh;
	SPECULAR = max(0.15, rock_specular);
	METALLIC = 0.0;

	// Grass impostor material at distance
	if (is_grass_zone) {
		float imp_mat_t = smoothstep(15.0, 25.0, cam_dist) * green_blend;
		ROUGHNESS = mix(ROUGHNESS, 0.4, imp_mat_t);
		SPECULAR = mix(SPECULAR, 0.2, imp_mat_t);
		BACKLIGHT = vec3(0.2) * imp_mat_t;
	}

	// ---- Rain wetness ----
	if (rain_wetness > 0.01) {
		float wet = rain_wetness;
		ALBEDO *= mix(1.0, 0.65, wet);
		ROUGHNESS = mix(ROUGHNESS, max(ROUGHNESS * 0.3, 0.08), wet);
		SPECULAR = mix(SPECULAR, 0.5, wet);

		float flatness = w_normal.y;
		if (flatness > 0.95) {
			float puddle_noise = fbm(v_vertex.xz * 0.06, 3);
			float puddle_threshold = mix(0.6, 0.25, wet);
			float puddle = smoothstep(puddle_threshold, puddle_threshold - 0.08, puddle_noise);
			puddle *= flatness;
			if (puddle > 0.01) {
				float p_sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
				float p_night = smoothstep(0.15, 0.02, p_sky_lum);
				vec3 puddle_col = sky_reflect_color * 0.35 + ALBEDO * 0.12;
				puddle_col = mix(puddle_col, vec3(0.08, 0.06, 0.03) + ALBEDO * 0.06, p_night);
				ALBEDO = mix(ALBEDO, puddle_col, puddle);
				ROUGHNESS = mix(ROUGHNESS, 0.02, puddle);
				SPECULAR = mix(SPECULAR, 0.8, puddle);
				vec3 puddle_n = normalize(mat3(VIEW_MATRIX) * vec3(0.0, 1.0, 0.0));
				NORMAL = mix(NORMAL, puddle_n, puddle * 0.9);
			}
		}
	}

	// ---- Fallen leaf scatter (autumn) ----
	{
		float leaf_autumn = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(3.3, 3.8, season_t));
		if (leaf_autumn > 0.01 && slope < 0.25) {
			float wind_str = length(wind_vec);
			vec2 leaf_drift = wind_vec * TIME * 0.015;
			float leaf_clump = vnoise(v_vertex.xz * 0.08 - leaf_drift * 0.3);
			float leaf_detail = vnoise(v_vertex.xz * 0.6 - leaf_drift);
			float gather = is_woodland ? 0.5 : 0.15;
			float topo_low = 1.0 - smoothstep(0.3, 0.6, fbm(v_vertex.xz * 0.02, 2));
			gather += topo_low * 0.15 + wind_str * 0.08;
			float leaf_mask = smoothstep(0.3, 0.7, leaf_clump) * gather * leaf_autumn;
			leaf_mask *= smoothstep(0.2, 0.5, leaf_detail);
			if (leaf_mask > 0.01) {
				float col_var = vnoise(v_vertex.xz * 1.2);
				vec3 leaf_col = mix(
					vec3(0.45, 0.28, 0.10),
					mix(vec3(0.65, 0.35, 0.10), vec3(0.55, 0.20, 0.08), col_var),
					smoothstep(0.3, 0.7, leaf_clump)
				);
				ALBEDO = mix(ALBEDO, leaf_col, leaf_mask * 0.65);
				ROUGHNESS = mix(ROUGHNESS, 0.92, leaf_mask * 0.5);
			}
		}
	}

	// ---- Morning dew (spring/summer after rain) ----
	{
		float dew_season = smoothstep(0.0, 1.0, season_t) * (1.0 - smoothstep(2.5, 3.5, season_t));
		if (dew_season > 0.01 && rain_wetness > 0.05 && rain_wetness < 0.5) {
			float dew_noise = hash2(floor(v_vertex.xz * 12.0));
			float dew = step(0.6, dew_noise) * dew_season * rain_wetness * 2.0;
			ROUGHNESS = mix(ROUGHNESS, 0.12, dew * 0.5);
			SPECULAR = mix(SPECULAR, 0.55, dew * 0.4);
			ALBEDO *= mix(1.0, 1.06, dew * 0.4);
		}
	}

	// ---- Winter frost ----
	{
		float frost_season = smoothstep(2.8, 3.5, season_t);
		if (frost_season > 0.01 && snow_cover < 0.3) {
			float frost_noise = hash2(floor(v_vertex.xz * 8.0));
			float frost_mask = step(0.4, frost_noise) * frost_season;
			float exposed = is_woodland ? 0.3 : 1.0;
			frost_mask *= exposed * w_normal.y;
			ALBEDO = mix(ALBEDO, vec3(0.85, 0.88, 0.92), frost_mask * 0.35);
			ROUGHNESS = mix(ROUGHNESS, 0.10, frost_mask * 0.5);
			SPECULAR = mix(SPECULAR, 0.6, frost_mask * 0.4);
		}
	}

	// ---- Snow accumulation ----
	if (snow_cover > 0.01) {
		float flatness = w_normal.y;
		float snow_noise = fbm(v_vertex.xz * 0.08, 2) * 0.25;
		float snow_amt = smoothstep(0.3, 0.7, flatness + snow_noise - 0.2) * snow_cover;
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_amt);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_amt);
		SPECULAR = mix(SPECULAR, 0.3, snow_amt);
		if (snow_amt > 0.3) {
			float sparkle = hash2(floor(v_vertex.xz * 30.0));
			if (sparkle > 0.97) {
				float intensity = (sparkle - 0.97) * 33.3;
				SPECULAR = mix(SPECULAR, 0.95, intensity * snow_amt);
				ROUGHNESS = mix(ROUGHNESS, 0.02, intensity * snow_amt * 0.5);
				ALBEDO += vec3(0.05) * intensity * snow_amt;
			}
		}
	}

	// ---- Dawn dew ----
	if (dew_amount > 0.01 && !is_dirt && slope < 0.20) {
		float dew = dew_amount * w_normal.y * (1.0 - rock_blend);
		ROUGHNESS = mix(ROUGHNESS, 0.20, dew * 0.35);
		SPECULAR = mix(SPECULAR, 0.35, dew * 0.30);
		float dew_noise = vnoise(v_vertex.xz * 25.0);
		float sparkle_mask = smoothstep(0.55, 0.75, dew_noise) * dew;
		if (sparkle_mask > 0.01) {
			SPECULAR = mix(SPECULAR, 0.65, sparkle_mask * 0.4);
			ROUGHNESS = mix(ROUGHNESS, 0.08, sparkle_mask * 0.25);
		}
		ALBEDO *= mix(1.0, 1.08, dew * 0.3);
	}

	// ---- Atmospheric distance haze ----
	float terr_dist = length(v_vertex - _camera_pos);
	float terr_fade = smoothstep(200.0, 600.0, terr_dist);
	if (terr_fade > 0.01) {
		float sky_lum2 = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
		vec3 haze_col = mix(vec3(0.58, 0.56, 0.52), sky_reflect_color * 0.8 + vec3(0.20), 0.35);
		float night_t2 = smoothstep(0.15, 0.02, sky_lum2);
		haze_col = mix(haze_col, vec3(0.14, 0.10, 0.06), night_t2 * 0.6);
		float autumn_h = smoothstep(1.5, 2.5, season_t) * (1.0 - smoothstep(2.5, 3.5, season_t));
		haze_col = mix(haze_col, haze_col * vec3(1.10, 1.00, 0.82), autumn_h * 0.4);
		float winter_h = smoothstep(2.5, 3.5, season_t);
		haze_col = mix(haze_col, haze_col * vec3(0.90, 0.95, 1.08), winter_h * 0.3);
		ALBEDO = mix(ALBEDO, haze_col, terr_fade * 0.35);
		ROUGHNESS = mix(ROUGHNESS, 0.95, terr_fade * 0.25);
		EMISSION = haze_col * 0.25 * terr_fade * 0.4;
	}
}
