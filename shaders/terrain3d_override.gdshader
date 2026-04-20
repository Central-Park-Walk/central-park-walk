// Terrain3D hybrid shader: native lightweight base + Central Park custom overlays
// Base: Terrain3D lightweight.gdshader (autoshader, height blending, macro variation)
// Overlays: seasons, weather, canopy shade, cloud shadows, atmosphere
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx, skip_vertex_transform;

// ---- Constants ----
#define SKIP_PASS 0
#define VERTEX_PASS 1
#define FRAGMENT_PASS 2
#define COLOR_MAP vec4(1.0, 1.0, 1.0, 0.5)
#define DIV_255 0.003921568627450

// Control map bit layout
#define DECODE_BLEND(control) float(control >> 14u & 0xFFu) * DIV_255
#define DECODE_AUTO(control) bool(control & 0x1u)
#define DECODE_BASE(control) int(control >> 27u & 0x1Fu)
#define DECODE_OVER(control) int(control >> 22u & 0x1Fu)
#define DECODE_HOLE(control) bool(control >> 2u & 0x1u)

#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	#define fma(a, b, c) ((a) * (b) + (c))
	#define dFdxCoarse(a) dFdx(a)
	#define dFdyCoarse(a) dFdy(a)
#endif

#include "res://shaders/include/seasonal.gdshaderinc"
#include "res://shaders/include/hash_noise.gdshaderinc"

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
uniform vec2 _region_locations[1024];
uniform float _texture_normal_depth_array[32];
uniform float _texture_ao_strength_array[32];
uniform float _texture_roughness_mod_array[32];
uniform float _texture_uv_scale_array[32];
uniform vec4 _texture_color_array[32];
uniform highp sampler2DArray _height_maps : repeat_disable;
uniform highp sampler2DArray _control_maps : repeat_disable;
uniform highp sampler2DArray _color_maps : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform highp sampler2DArray _texture_array_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform highp sampler2DArray _texture_array_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;

// ---- Terrain3D public uniforms ----
uniform float blend_sharpness : hint_range(0, 1) = 0.5;
// Autoshader
uniform float auto_slope : hint_range(0, 10) = 2.0;
uniform float auto_height_reduction : hint_range(0, 1) = 0.1;
uniform int auto_base_texture : hint_range(0, 31) = 0;
uniform int auto_overlay_texture : hint_range(0, 31) = 2; // rock
// Macro variation
uniform bool enable_macro_variation = true;
uniform vec3 macro_variation1 : source_color = vec3(0.90, 0.92, 0.88);
uniform vec3 macro_variation2 : source_color = vec3(1.0, 0.97, 0.95);
uniform float macro_variation_slope : hint_range(0., 1.) = 0.333;
uniform highp sampler2D noise_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float noise1_scale : hint_range(0.001, 1.) = 0.04;
uniform float noise1_angle : hint_range(0, 6.283) = 0.0;
uniform vec2 noise1_offset = vec2(0.5);
uniform float noise2_scale : hint_range(0.001, 1.) = 0.076;

// ---- Central Park custom uniforms ----
uniform float world_size = 5000.0;
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform sampler2D canopy_map : filter_linear, repeat_disable;

// Global uniforms (set by main.gd)
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform float season_t;
global uniform vec3 sky_reflect_color;
global uniform vec2 wind_vec;
global uniform float dew_amount;
global uniform float cloud_coverage_g;
global uniform float cloud_speed_g;

// ---- Varyings ----
varying vec3 v_normal;
varying vec3 v_vertex;
varying mat3 TBN;

// ===========================================================================
// Terrain3D vertex (from lightweight.gdshader)
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

vec3 get_index_uv(const vec2 uv2) {
	ivec2 pos = ivec2(floor(uv2)) + (_region_map_size / 2);
	int bounds = int(uint(pos.x | pos.y) < uint(_region_map_size));
	int layer_index = _region_map[pos.y * _region_map_size + pos.x] * bounds - 1;
	return vec3(uv2 - _region_locations[layer_index], float(layer_index));
}

void vertex() {
	v_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float v_vertex_xz_dist = length(v_vertex.xz - _camera_pos.xz);

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
	bool hole = DECODE_HOLE(control);

	if (!(CAMERA_VISIBLE_LAYERS == _mouse_layer) &&
			(hole || (_background_mode == 0u && v_region.z == -1))) {
		v_vertex.x = 0.0 / 0.0;
	} else {
		ivec3 uv_a = get_index_coord(start_pos, VERTEX_PASS);
		ivec3 uv_b = get_index_coord(end_pos, VERTEX_PASS);
		float h = mix(texelFetch(_height_maps, uv_a, 0).r, texelFetch(_height_maps, uv_b, 0).r, vertex_lerp);
		v_vertex.y = h;

		float u = mix(texelFetch(_height_maps, get_index_coord(start_pos + vec2(1, 0), VERTEX_PASS), 0).r,
			texelFetch(_height_maps, get_index_coord(end_pos + vec2(1, 0), VERTEX_PASS), 0).r, vertex_lerp);
		float v = mix(texelFetch(_height_maps, get_index_coord(start_pos + vec2(0, 1), VERTEX_PASS), 0).r,
			texelFetch(_height_maps, get_index_coord(end_pos + vec2(0, 1), VERTEX_PASS), 0).r, vertex_lerp);

		v_normal = normalize(vec3(h - u, _vertex_spacing, h - v));
	}

	VERTEX = (VIEW_MATRIX * vec4(v_vertex, 1.0)).xyz;

	vec3 w_tangent = normalize(cross(v_normal, vec3(0.0, 0.0, 1.0)));
	vec3 w_binormal = normalize(cross(v_normal, w_tangent));
	TBN = mat3(w_tangent, w_binormal, v_normal);

	NORMAL = normalize((VIEW_MATRIX * vec4(v_normal, 0.0)).xyz);
	BINORMAL = normalize((VIEW_MATRIX * vec4(w_binormal, 0.0)).xyz);
	TANGENT = normalize((VIEW_MATRIX * vec4(w_tangent, 0.0)).xyz);
}

// ===========================================================================
// Hash & noise utilities
// ===========================================================================

// hash2, vnoise, cloud_shadow now from hash_noise.gdshaderinc

// Noise logic in hash_noise.gdshaderinc; terrain-specific tuning here
float fbm(vec2 p, int oct) { return fbm_n(p, oct, 2.13, 0.47); }

// ===========================================================================
// Fragment
// ===========================================================================

mat2 rotate_plane(float angle) {
	float c = cos(angle), s = sin(angle);
	return mat2(vec2(c, s), vec2(-s, c));
}

void fragment() {
	vec2 uv = UV;
	vec2 uv2 = UV2;

	// =====================================================================
	// PART 1: Terrain3D native texturing (from lightweight.gdshader)
	// =====================================================================

	vec3 region_uv = get_index_uv(uv2);
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

	ivec3 index[4];
	index[0] = get_index_coord(index_id + offsets.xy, FRAGMENT_PASS);
	index[1] = get_index_coord(index_id + offsets.yy, FRAGMENT_PASS);
	index[2] = get_index_coord(index_id + offsets.yx, FRAGMENT_PASS);
	index[3] = get_index_coord(index_id + offsets.xx, FRAGMENT_PASS);

	vec3 base_ddx = dFdxCoarse(v_vertex);
	vec3 base_ddy = dFdyCoarse(v_vertex);
	vec4 base_dd = vec4(base_ddx.xz, base_ddy.xz);
	float region_mip = log2(max(length(base_ddx.xz), length(base_ddy.xz)) * _vertex_density);

	vec4 color_map = region_uv.z > -1.0 ? textureLod(_color_maps, region_uv, region_mip) : COLOR_MAP;

	vec4 normal_rough = vec4(0.0, 1.0, 0.0, 0.7);
	vec4 albedo_height = vec4(1.0);
	float normal_map_depth = 1.0;
	float ao_strength = 0.0;

	// Texture accumulation
	{
		albedo_height = vec4(0.0);
		normal_rough = vec4(0.0);
		normal_map_depth = 0.0;
		ao_strength = 0.0;
		float total_weight = 0.0;
		float sharpness = fma(56.0, blend_sharpness, 8.0);

		uvec4 control = floatBitsToUint(vec4(
			texelFetch(_control_maps, index[0], 0).r,
			texelFetch(_control_maps, index[1], 0).r,
			texelFetch(_control_maps, index[2], 0).r,
			texelFetch(_control_maps, index[3], 0).r));

		// Autoshader
		{
			float auto_blend = clamp(fma(auto_slope * 2.0, (v_normal.y - 1.0), 1.0)
				- auto_height_reduction * 0.01 * v_vertex.y, 0.0, 1.0);
			uvec4 is_auto = (control & uvec4(0x1u)) | uvec4(uint(region_uv.z < 0.0));
			uint u_auto =
				((uint(auto_base_texture) & 0x1Fu) << 27u) |
				((uint(auto_overlay_texture) & 0x1Fu) << 22u) |
				((uint(fma(auto_blend, 255.0, 0.5)) & 0xFFu) << 14u);
			control = control * (1u - is_auto) + u_auto * is_auto;
		}

		// Texture weights
		ivec4 t_id[2] = {ivec4(control >> uvec4(27u) & uvec4(0x1Fu)),
			ivec4(control >> uvec4(22u) & uvec4(0x1Fu))};
		ivec2 texture_ids[4] = ivec2[4](
			ivec2(t_id[0].x, t_id[1].x),
			ivec2(t_id[0].y, t_id[1].y),
			ivec2(t_id[0].z, t_id[1].z),
			ivec2(t_id[0].w, t_id[1].w));

		vec4 weights_id_1 = vec4(control >> uvec4(14u) & uvec4(0xFFu)) * DIV_255 * weights;
		vec4 weights_id_0 = weights - weights_id_1;
		vec2 t_weights[4] = {vec2(0), vec2(0), vec2(0), vec2(0)};
		for (int i = 0; i < 4; i++) {
			vec2 w_0 = vec2(weights_id_0[i]);
			vec2 w_1 = vec2(weights_id_1[i]);
			ivec2 id_0 = texture_ids[i].xx;
			ivec2 id_1 = texture_ids[i].yy;
			t_weights[0] += fma(w_0, vec2(equal(texture_ids[0], id_0)), w_1 * vec2(equal(texture_ids[0], id_1)));
			t_weights[1] += fma(w_0, vec2(equal(texture_ids[1], id_0)), w_1 * vec2(equal(texture_ids[1], id_1)));
			t_weights[2] += fma(w_0, vec2(equal(texture_ids[2], id_0)), w_1 * vec2(equal(texture_ids[2], id_1)));
			t_weights[3] += fma(w_0, vec2(equal(texture_ids[3], id_0)), w_1 * vec2(equal(texture_ids[3], id_1)));
		}

		// Sample textures (one read per unique ID)
		uint id_read = 0u;
		vec4 nrm = vec4(0.0, 1.0, 0.0, 1.0);
		uv *= _vertex_spacing;
		for (int i = 0; i < 4; i++) {
			for (int t = 0; t < 2; t++) {
				int id = texture_ids[i][t];
				uint mask = 1u << uint(id);
				if ((id_read & mask) == 0u) {
					id_read |= mask;
					float id_w = t_weights[i][t];
					float id_scale = _texture_uv_scale_array[id] * 0.5;
					vec2 id_uv = fma(uv, vec2(id_scale), vec2(0.5));
					vec4 i_dd = base_dd * id_scale;
					vec4 alb = textureGrad(_texture_array_albedo, vec3(id_uv, float(id)), i_dd.xy, i_dd.zw);
					float world_normal = clamp(fma(TBN[0], vec3(nrm.x), fma(TBN[1], vec3(nrm.z), v_normal * vec3(nrm.y))).y, 0.0, 1.0);
					nrm = textureGrad(_texture_array_normal, vec3(id_uv, float(id)), i_dd.xy, i_dd.zw);
					alb.rgb *= _texture_color_array[id].rgb;
					nrm.a = clamp(nrm.a + _texture_roughness_mod_array[id], 0.0, 1.0);
					nrm.xyz = fma(nrm.xzy, vec3(2.0), vec3(-1.0));
					float id_weight = exp2(sharpness * log2(id_w + alb.a * world_normal));
					albedo_height += alb * id_weight;
					normal_rough += nrm * id_weight;
					normal_map_depth += _texture_normal_depth_array[id] * id_weight;
					ao_strength += _texture_ao_strength_array[id] * id_weight;
					total_weight += id_weight;
				}
			}
		}
		float weight_inv = 1.0 / total_weight;
		albedo_height *= weight_inv;
		normal_rough *= weight_inv;
		normal_map_depth *= weight_inv;
		ao_strength *= weight_inv;
	}

	// Macro variation
	vec3 macrov = vec3(1.0);
	if (enable_macro_variation) {
		float noise1 = texture(noise_texture, (uv * noise1_scale * 0.1 + noise1_offset) * rotate_plane(noise1_angle)).r;
		float noise2 = texture(noise_texture, uv * noise2_scale * 0.1).r;
		macrov = mix(macro_variation1, vec3(1.0), noise1);
		macrov *= mix(macro_variation2, vec3(1.0), noise2);
		macrov = mix(vec3(1.0), macrov, clamp(v_normal.y + macro_variation_slope, 0.0, 1.0));
	}

	float roughness = clamp(fma(color_map.a - 0.5, 2.0, normal_rough.a), 0.0, 1.0);

	// Apply native PBR
	ALBEDO = albedo_height.rgb * color_map.rgb * macrov;
	// Grass and natural surfaces need higher roughness — raw texture values
	// produce waxy specular sheen in side light. Raise floor to 0.82.
	ROUGHNESS = max(roughness, 0.82);
	SPECULAR = 0.04;  // dielectric minimum — grass has no specular sheen
	NORMAL_MAP = fma(normalize(normal_rough.xzy), vec3(0.5), vec3(0.5));
	NORMAL_MAP_DEPTH = normal_map_depth;

	float ao = (1.0 - (albedo_height.a * log(2.1 - ao_strength))) * (1.0 - normal_rough.y);
	AO = clamp(1.0 - ao * ao_strength, albedo_height.a, 1.0);
	AO_LIGHT_AFFECT = (1.0 - albedo_height.a) * clamp(normal_rough.y, 0.0, 1.0);
	METALLIC = 0.0;

	// =====================================================================
	// PART 2: Central Park custom overlays
	// Applied on top of native Terrain3D output
	// =====================================================================

	float cam_dist = length(v_vertex - _camera_pos);
	vec2 splat_uv = (v_vertex.xz + world_size * 0.5) / world_size;

	// Zone lookup (for season/weather zone awareness)
	float zone_val = texture(landuse_map, splat_uv).r * 255.0;
	int zone_id = int(zone_val + 0.5);
	bool is_woodland = (zone_id == 5 || zone_id == 10 || zone_id == 11);
	bool is_grass_zone = (zone_id == 0 || zone_id == 1 || zone_id == 2
	                   || zone_id == 3 || zone_id == 7);

	// ---- Canopy leaf litter (under dense tree cover) ----
	{
		float canopy_cover = texture(canopy_map, splat_uv).r;
		if (canopy_cover > 0.3 && (is_grass_zone || is_woodland)) {
			vec3 litter_col = mix(vec3(0.28, 0.22, 0.14), vec3(0.34, 0.26, 0.16), vnoise(v_vertex.xz * 0.5));
			float litter_blend = smoothstep(0.3, 0.7, canopy_cover) * 0.50;
			ALBEDO = mix(ALBEDO, litter_col, litter_blend);
		}
	}

	// ---- Seasonal color shift ----
	{
		float spring_t = sn_veg_spring(season_t);
		float autumn_t = sn_veg_autumn(season_t);
		float winter_t = sn_veg_winter(season_t);
		ALBEDO = mix(ALBEDO, ALBEDO * vec3(1.1, 1.15, 0.75), spring_t * 0.6);
		ALBEDO = mix(ALBEDO, vec3(0.16, 0.12, 0.04), autumn_t * 0.7);
		ALBEDO = mix(ALBEDO, vec3(0.12, 0.10, 0.06), winter_t);
		if (winter_t > 0.01) {
			NORMAL_MAP = mix(NORMAL_MAP, vec3(0.5, 0.5, 1.0), winter_t);
			ROUGHNESS = mix(ROUGHNESS, 0.95, winter_t);
		}
	}

	// ---- Dappled canopy shade ----
	{
		float canopy = texture(canopy_map, splat_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = sn_canopy_loss(season_t);
			float winter_bare = sn_canopy_bare(season_t);
			float spring_fill = sn_canopy_fill(season_t);
			float seasonal_canopy = canopy;
			seasonal_canopy *= mix(1.0, 0.3, deciduous_loss);
			seasonal_canopy *= mix(1.0, 0.15, winter_bare);
			seasonal_canopy *= mix(0.5, 1.0, spring_fill);

			vec2 dapple_uv = v_vertex.xz * 0.35 + wind_vec * TIME * 0.08;
			float light_gap = smoothstep(0.35, 0.65, vnoise(dapple_uv)) * 0.6
				+ smoothstep(0.55, 0.75, vnoise(v_vertex.xz * 1.2 + wind_vec * TIME * 0.15)) * 0.4;

			float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum);

			float shade = seasonal_canopy * sun_factor;
			ALBEDO *= (1.0 - shade * (1.0 - light_gap) * 0.12);
			float warm_spots = light_gap * shade;
			ALBEDO *= vec3(1.0 + warm_spots * 0.15, 1.0 + warm_spots * 0.10, 1.0 - warm_spots * 0.05);
		}
	}

	// ---- Per-pixel micro-variation ----
	vec2 terr_px = v_vertex.xz * 23.7 + vec2(v_vertex.y * 5.1);
	ALBEDO += vec3(hash2(terr_px) * 0.05 - 0.025);

	// ---- Cloud shadows ----
	float sky_lum_cs = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
	float daytime = smoothstep(0.05, 0.20, sky_lum_cs);
	ALBEDO *= (1.0 - cloud_shadow(v_vertex.xz, cloud_coverage_g, cloud_speed_g, TIME, wind_vec) * daytime);

	// ---- Rain wetness ----
	if (rain_wetness > 0.01) {
		float wet = rain_wetness;
		ALBEDO *= mix(1.0, 0.65, wet);
		ROUGHNESS = mix(ROUGHNESS, max(ROUGHNESS * 0.3, 0.08), wet);
		SPECULAR = mix(SPECULAR, 0.5, wet);

		// Puddles on flat terrain
		if (v_normal.y > 0.95) {
			float puddle_noise = fbm(v_vertex.xz * 0.10, 3);
			float puddle_threshold = mix(0.48, 0.22, wet);
			float puddle = smoothstep(puddle_threshold, puddle_threshold - 0.08, puddle_noise) * v_normal.y;
			if (puddle > 0.01) {
				float p_sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
				float p_night = smoothstep(0.15, 0.02, p_sky_lum);
				vec3 puddle_col = sky_reflect_color * 0.35 + ALBEDO * 0.12;
				puddle_col = mix(puddle_col, vec3(0.08, 0.06, 0.03) + ALBEDO * 0.06, p_night);
				ALBEDO = mix(ALBEDO, puddle_col, puddle);
				ROUGHNESS = mix(ROUGHNESS, 0.02, puddle);
				SPECULAR = mix(SPECULAR, 0.8, puddle);
			}
		}
	}

	// ---- Fallen leaf scatter (autumn) ----
	{
		float leaf_autumn = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(3.3, 3.8, season_t));
		float slope = 1.0 - v_normal.y;
		if (leaf_autumn > 0.01 && slope < 0.25) {
			vec2 leaf_drift = wind_vec * TIME * 0.015;
			float leaf_clump = vnoise(v_vertex.xz * 0.08 - leaf_drift * 0.3);
			float leaf_detail = vnoise(v_vertex.xz * 0.6 - leaf_drift);
			float gather = is_woodland ? 0.5 : 0.15;
			gather += (1.0 - smoothstep(0.3, 0.6, fbm(v_vertex.xz * 0.02, 2))) * 0.15;
			float leaf_mask = smoothstep(0.3, 0.7, leaf_clump) * gather * leaf_autumn;
			leaf_mask *= smoothstep(0.2, 0.5, leaf_detail);
			if (leaf_mask > 0.01) {
				float col_var = vnoise(v_vertex.xz * 1.2);
				vec3 leaf_col = mix(vec3(0.45, 0.28, 0.10),
					mix(vec3(0.65, 0.35, 0.10), vec3(0.55, 0.20, 0.08), col_var),
					smoothstep(0.3, 0.7, leaf_clump));
				ALBEDO = mix(ALBEDO, leaf_col, leaf_mask * 0.65);
				ROUGHNESS = mix(ROUGHNESS, 0.92, leaf_mask * 0.5);
			}
		}
	}

	// ---- Dawn dew ----
	if (dew_amount > 0.01 && v_normal.y > 0.80) {
		float dew = dew_amount * v_normal.y;
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

	// ---- Winter frost ----
	{
		float frost_season = sn_frost(season_t);
		if (frost_season > 0.01 && snow_cover < 0.3) {
			// Multi-frequency smooth noise — no grid artifacts
			float frost_noise = vnoise(v_vertex.xz * 0.5) * 0.5
				+ vnoise(v_vertex.xz * 1.7) * 0.3
				+ vnoise(v_vertex.xz * 5.0) * 0.2;
			float frost_mask = smoothstep(0.35, 0.55, frost_noise) * frost_season;
			frost_mask *= (is_woodland ? 0.3 : 1.0) * v_normal.y;
			ALBEDO = mix(ALBEDO, vec3(0.85, 0.88, 0.92), frost_mask * 0.35);
			ROUGHNESS = mix(ROUGHNESS, 0.10, frost_mask * 0.5);
			SPECULAR = mix(SPECULAR, 0.6, frost_mask * 0.4);
		}
	}

	// ---- Snow accumulation ----
	if (snow_cover > 0.01) {
		float snow_noise = fbm(v_vertex.xz * 0.12, 4) * 0.20
			+ vnoise(v_vertex.xz * 0.03) * 0.10;  // broad undulation
		float snow_amt = smoothstep(0.3, 0.7, v_normal.y + snow_noise - 0.2) * snow_cover;
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_amt);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_amt);
		SPECULAR = mix(SPECULAR, 0.3, snow_amt);
		if (snow_amt > 0.3) {
			// Smooth sparkle — no grid
			float sparkle = vnoise(v_vertex.xz * 30.0);
			float sparkle_mask = smoothstep(0.85, 0.95, sparkle);
			if (sparkle_mask > 0.01) {
				SPECULAR = mix(SPECULAR, 0.95, sparkle_mask * snow_amt);
				ROUGHNESS = mix(ROUGHNESS, 0.02, sparkle_mask * snow_amt * 0.5);
				ALBEDO += vec3(0.05) * sparkle_mask * snow_amt;
			}
		}
	}

	// ---- Atmospheric distance haze ----
	float terr_fade = smoothstep(200.0, 600.0, cam_dist);
	if (terr_fade > 0.01) {
		float sky_lum2 = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
		vec3 haze_col = mix(vec3(0.58, 0.56, 0.52), sky_reflect_color * 0.8 + vec3(0.20), 0.35);
		haze_col = mix(haze_col, vec3(0.14, 0.10, 0.06), smoothstep(0.15, 0.02, sky_lum2) * 0.6);
		float autumn_h = sn_atmo_autumn(season_t);
		haze_col = mix(haze_col, haze_col * vec3(1.10, 1.00, 0.82), autumn_h * 0.4);
		float winter_h = sn_atmo_winter(season_t);
		haze_col = mix(haze_col, haze_col * vec3(0.90, 0.95, 1.08), winter_h * 0.3);
		ALBEDO = mix(ALBEDO, haze_col, terr_fade * 0.35);
		ROUGHNESS = mix(ROUGHNESS, 0.95, terr_fade * 0.25);
		EMISSION = haze_col * 0.25 * terr_fade * 0.4;
	}
}
