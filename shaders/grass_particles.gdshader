// Copyright © 2025 Cory Petkovsek, Roope Palmroos, and Contributors.

// This is an example particle shader designed to procedurally place
// particles like grass, small rocks, and other ground effects, on the terrain
// surface by reading the Terrain3D data maps. It works in tandem with the
// provided GDScript.

shader_type particles;
render_mode disable_velocity, disable_force;

group_uniforms options;
uniform sampler2D main_noise;
uniform float main_noise_scale = 0.01;
uniform vec3 position_offset = vec3(0.);
uniform bool align_to_normal = true;
uniform float normal_strength : hint_range(0.01, 1.0, 0.01) = 0.3;
uniform bool random_rotation = true;
uniform float random_spacing : hint_range(0.0, 1.0, 0.01) = 0.5;
uniform vec3 min_scale = vec3(1.0);
uniform vec3 max_scale = vec3(1.0);

group_uniforms wind;
uniform float noise_scale = 0.0041;
uniform float wind_speed = 0.025;
uniform float wind_strength : hint_range(0.0, 1.0, 0.01) = 1.0;
uniform float wind_dithering = 4.0;
uniform vec2 wind_direction = vec2(1.0,1.0);

group_uniforms shapeing;
uniform float clod_scale_boost = 3.0;
uniform float clod_min_threshold : hint_range(0.0, 1.0, 0.001) = 0.2;
uniform float clod_max_threshold : hint_range(0.0, 1.0, 0.001) = 0.5;
uniform float patch_min_threshold : hint_range(0.0, 1.0, 0.001) = 0.025;
uniform float patch_max_threshold : hint_range(0.0, 1.0, 0.001) = 0.2;

group_uniforms filtering;
uniform float condition_dither_range : hint_range(0.0, 1.0, 0.01) = 0.15;
uniform float surface_slope_min : hint_range(0.0, 1.0, 0.01) = 0.87;
uniform float distance_fade_ammount : hint_range(0.0, 1.0, 0.01) = 0.5;

group_uniforms central_park;
// Zone-aware grass: only grow on grass/meadow zones, suppress under canopy
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float world_size = 5000.0;
global uniform float season_t;
global uniform float snow_cover;

#include "res://shaders/include/seasonal.gdshaderinc"

// Biome filter: 0=lawn 1=shade 2=wild 3=sedge  10=tuft_lawn 11=tuft_wild  -1=all(legacy)
uniform int biome_id = -1;

group_uniforms private;
uniform float max_dist = 1.;
uniform vec3 camera_position = vec3(0.);
uniform uint instance_rows = 1;
uniform float instance_spacing = 0.5;
uniform uint _background_mode = 0u;
uniform float _vertex_spacing = 1.0;
uniform float _vertex_density = 1.0; // = 1/_vertex_spacing
uniform float _region_size = 1024.0;
uniform float _region_texel_size = 0.0009765625; // = 1/REGION_SIZE
uniform int _region_map_size = 32;
uniform int _region_map[1024];
uniform vec2 _region_locations[1024];
uniform highp sampler2DArray _height_maps : repeat_disable;
uniform highp sampler2DArray _control_maps : repeat_disable;
uniform highp sampler2DArray _color_maps : repeat_disable;

// Defined Constants
#define SKIP_PASS 0
#define VERTEX_PASS 1
#define FRAGMENT_PASS 2

// Takes in world space XZ (UV) coordinates & search depth (only applicable for background mode none)
// Returns ivec3 with:
// XY: (0 to _region_size - 1) coordinates within a region
// Z: layer index used for texturearrays, -1 if not in a region
ivec3 get_index_coord(const vec2 uv, const int search) {
	vec2 r_uv = round(uv);
	vec2 o_uv = mod(r_uv,_region_size);
	ivec2 pos;
	int bounds, layer_index = -1;
	for (int i = -1; i < 0; i++) {
		if ((layer_index == -1 && _background_mode == 0u) || i < 0) {
			r_uv -= i == -1 ? vec2(0.0) : vec2(float(o_uv.x <= o_uv.y), float(o_uv.y <= o_uv.x));
			pos = ivec2(floor((r_uv) * _region_texel_size)) + (_region_map_size / 2);
			bounds = int(uint(pos.x | pos.y) < uint(_region_map_size));
			layer_index = (_region_map[ pos.y * _region_map_size + pos.x ] * bounds - 1);
		}
	}
	return ivec3(ivec2(mod(r_uv,_region_size)), layer_index);
}

#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	#define fma(a, b, c) ((a) * (b) + (c))
#endif
float random(vec2 v) {
	return fract(1e4 * sin(fma(17.0, v.x, v.y * 0.1)) * (0.1 + abs(sin(fma(v.y, 13.0, v.x)))));
}

mat3 rotation_matrix(vec3 axis, float angle) {
	float c = cos(angle);
	float s = sin(angle);
	float t = 1.0 - c;
	vec3 n = normalize(axis);
	float x = n.x;
	float y = n.y;
	float z = n.z;

	return mat3(
		vec3(t * x * x + c, t * x * y - z * s, t * x * z + y * s),
		vec3(t * x * y + z * s, t * y * y + c, t * y * z - x * s),
		vec3(t * x * z - y * s, t * y * z + x * s, t * z * z + c));
}

mat3 align_to_vector(vec3 normal) {
	vec3 up = vec3(0.0, 1.0, 0.0);
	if (abs(dot(normal, up)) > 0.9999) { // Avoid singularity
		up = vec3(1.0, 0.0, 0.0);
	}
	vec3 tangent = normalize(cross(up, normal));
	vec3 bitangent = normalize(cross(tangent, normal));
	return mat3(tangent, normal, bitangent);
}

void start() {
	// Create centered a grid
	vec3 pos = vec3(float(INDEX % instance_rows), 0.0, float(INDEX / instance_rows)) - float(instance_rows >> 1u);

	// Apply spcaing
	pos *= instance_spacing;
	// Move the grid to the emitter, snapping is handled CPU side
	pos.xz += EMISSION_TRANSFORM[3].xz;

	// Create random values per-instance, incorporating the seed, mask bits to avoid NAN/INF
	float seed = fract(uintBitsToFloat(RANDOM_SEED & 0x7EFFFFFFu));
	vec3 r = fract(vec3(random(pos.xz), random(pos.xz + vec2(0.5)), random(pos.xz - vec2(0.5))) + seed);
	// Randomize instance spacing
	pos.x += ((r.x * 2.0) - 1.0) * random_spacing * instance_spacing;
	pos.z += ((r.z * 2.0) - 1.0) * random_spacing * instance_spacing;

	// Lookup offsets, ID and blend weight
	const vec3 offsets = vec3(0, 1, 2);
	vec2 index_id = floor(pos.xz * _vertex_density);
	vec2 weight = fract(pos.xz * _vertex_density);
	vec2 invert = 1.0 - weight;
	vec4 weights = vec4(
		invert.x * weight.y, // 0
		weight.x * weight.y, // 1
		weight.x * invert.y, // 2
		invert.x * invert.y  // 3
	);

	ivec3 index[4];
	// Map lookups
	index[0] = get_index_coord(index_id + offsets.xy, VERTEX_PASS);
	index[1] = get_index_coord(index_id + offsets.yy, VERTEX_PASS);
	index[2] = get_index_coord(index_id + offsets.yx, VERTEX_PASS);
	index[3] = get_index_coord(index_id + offsets.xx, VERTEX_PASS);

	highp float h[8];
	h[0] = texelFetch(_height_maps, index[0], 0).r; // 0 (0,1)
	h[1] = texelFetch(_height_maps, index[1], 0).r; // 1 (1,1)
	h[2] = texelFetch(_height_maps, index[2], 0).r; // 2 (1,0)
	h[3] = texelFetch(_height_maps, index[3], 0).r; // 3 (0,0)
	h[4] = texelFetch(_height_maps, get_index_coord(index_id + offsets.yz, VERTEX_PASS), 0).r; // 4 (1,2)
	h[5] = texelFetch(_height_maps, get_index_coord(index_id + offsets.zy, VERTEX_PASS), 0).r; // 5 (2,1)
	h[6] = texelFetch(_height_maps, get_index_coord(index_id + offsets.zx, VERTEX_PASS), 0).r; // 6 (2,0)
	h[7] = texelFetch(_height_maps, get_index_coord(index_id + offsets.xz, VERTEX_PASS), 0).r; // 7 (0,2)
	vec3 index_normal[4];
	index_normal[0] = vec3(h[0] - h[1], _vertex_spacing, h[0] - h[7]);
	index_normal[1] = vec3(h[1] - h[5], _vertex_spacing, h[1] - h[4]);
	index_normal[2] = vec3(h[2] - h[6], _vertex_spacing, h[2] - h[1]);
	index_normal[3] = vec3(h[3] - h[2], _vertex_spacing, h[3] - h[0]);
	vec3 w_normal = normalize(
		index_normal[0] * weights[0] +
		index_normal[1] * weights[1] +
		index_normal[2] * weights[2] +
		index_normal[3] * weights[3]);

	// Set the height according to the heightmap data
	pos.y =
		h[0] * weights[0] +
		h[1] * weights[1] +
		h[2] * weights[2] +
		h[3] * weights[3] ;

	// Offset, Rotation, Alignment.
	TRANSFORM = mat4(1.0);
	vec3 orientation = vec3(0., 1., 0.);

	// --- Zone lookup (needed before scale) ---
	vec2 splat_uv = (pos.xz + world_size * 0.5) / world_size;
	float zone_val = textureLod(landuse_map, splat_uv, 0.0).r * 255.0;
	int zone_id = int(zone_val + 0.5);
	float canopy_cover = textureLod(canopy_map, splat_uv, 0.0).r;

	// Biome-based zone filtering
	// Zone IDs: 0=SheepMeadow 1=GreatLawn 2=NorthMeadow 3=FormalGarden
	//   4=SportsTurf 5=NorthWoods 6=Ramble 7=Waterside 8=WildMeadow 9=OpenLawn
	//   10,11=Woodland  12=water 13=shore
	bool is_grass_zone;
	bool is_woodland;
	if (biome_id == 0 || biome_id == 10) {
		// Lawn (Turf_Lawn / Tuft accent): maintained lawns + sports + open
		is_grass_zone = (zone_id == 0 || zone_id == 1 || zone_id == 2
		              || zone_id == 3 || zone_id == 4 || zone_id == 9);
		is_woodland = false;
	} else if (biome_id == 1 || biome_id == 11) {
		// Shade (Turf_Shade / Tuft accent): woodland + ramble forest floor
		is_grass_zone = false;
		is_woodland = (zone_id == 5 || zone_id == 6 || zone_id == 10 || zone_id == 11);
	} else if (biome_id == 2) {
		// Wild (Turf_Wild): unmowed wild meadow
		is_grass_zone = (zone_id == 8);
		is_woodland = false;
	} else if (biome_id == 3) {
		// Sedge (Turf_Sedge): waterside edges
		is_grass_zone = (zone_id == 7);
		is_woodland = false;
	} else {
		// Legacy: all grass zones
		is_grass_zone = (zone_id == 0 || zone_id == 1 || zone_id == 2
		              || zone_id == 3 || zone_id == 4 || zone_id == 7
		              || zone_id == 8 || zone_id == 9);
		is_woodland = (zone_id == 5 || zone_id == 6 || zone_id == 10 || zone_id == 11);
	}

	vec2 uv = (pos.xz) * main_noise_scale;
	float noise = textureLod(main_noise, uv, 0.0).r;
	float clods = smoothstep(clod_min_threshold, clod_max_threshold, noise) * clod_scale_boost;
	float patch = smoothstep(patch_min_threshold, patch_max_threshold, noise);
	float width_modifier = 1.0 + 3.0 * smoothstep(0., max_dist, length(camera_position - pos));

	// --- Data-driven grass height from CPC lawn classification ---
	// A-lawns (zone 0,1,2,3,4): mowed 2x/week to 7.6cm, dense, uniform
	// B/C-lawns (zone 7,9): mowed weekly/as-needed, slightly taller
	// D-lawns/woodland (zone 5,10,11): infrequent mow, tall, patchy
	// Wild meadow (zone 8): unmowed, tallest
	float zone_height = 1.0;  // multiplier on Y scale
	float zone_spread = 1.0;  // multiplier on XZ scale
	if (zone_id == 0 || zone_id == 1) {
		zone_height = 0.7; zone_spread = 0.9;   // A-lawn: short, tight mow
	} else if (zone_id == 2) {
		zone_height = 0.8; zone_spread = 0.95;  // A-lawn (NorthMeadow)
	} else if (zone_id == 3) {
		zone_height = 0.6; zone_spread = 0.85;  // Formal garden: shortest
	} else if (zone_id == 7) {
		zone_height = 0.9; zone_spread = 1.0;   // C-lawn (waterside)
	} else if (zone_id == 5) {
		zone_height = 1.4; zone_spread = 1.1;   // NorthWoods: tall shade grass
	} else if (zone_id == 6) {
		zone_height = 1.2; zone_spread = 1.0;   // Ramble: moderate woodland
	} else if (zone_id == 8) {
		zone_height = 1.8; zone_spread = 1.2;   // WildMeadow: tallest, unmowed
	} else if (zone_id == 10 || zone_id == 11) {
		zone_height = 1.0; zone_spread = 0.8;   // Woodland: medium, sparse
	}

	vec3 scale = vec3(
		mix(min_scale.x, max_scale.x, r.x) * width_modifier * zone_spread,
		mix(min_scale.y, max_scale.y, r.y) * zone_height + clods,
		mix(min_scale.z, max_scale.z, r.z) * width_modifier * zone_spread) * patch;

	// Apply scale to offset
	vec3 offset = position_offset * scale;

	// Apply normal orientation
	if (align_to_normal) {
		orientation = mix(orientation, w_normal, normal_strength);
		mat3 alignment = align_to_vector(orientation);
		offset = alignment * offset;
		TRANSFORM = mat4(alignment);
	}

	// Apply rotation around orientation
	if (random_rotation) {
		mat3 rotation = rotation_matrix(orientation, r.x * TAU);
		TRANSFORM = mat4(rotation) * TRANSFORM;
	}

	// Filtering - Causes some particles to be rendered as degenerate triangles
	// via 0./0. - Particles filtered this way are still processed by the GPU.
	// For compatibility it seems we must shift as well.
	// Surface slope filtering
	if (surface_slope_min > w_normal.y + (r.y - 0.5) * condition_dither_range) {
		pos.y = 0. / 0.;
		pos.xz = vec2(100000.0);
	}

	// --- Central Park zone-aware grass filtering ---
	// No grass on dirt(4), dog_park(6), pool(8), track(9), water(12), shore(13)
	if (!is_grass_zone && !is_woodland) {
		pos.y = 0. / 0.;
		pos.xz = vec2(100000.0);
	}

	// Canopy suppression: under dense tree cover, forest floor is leaf litter
	if (canopy_cover > 0.4) {
		// Skip 70-90% of blades under dense canopy
		float skip_chance = smoothstep(0.3, 0.8, canopy_cover) * 0.9;
		if (r.y < skip_chance) {
			pos.y = 0. / 0.;
			pos.xz = vec2(100000.0);
		}
	}

	// Data-driven density from CPC lawn classification
	// A-lawns: 95% coverage (dense turf). D-lawns/woodland: 25-40% (patchy, mulch zones)
	float zone_density = 0.5;
	if (zone_id == 0 || zone_id == 1) zone_density = 0.95;       // A-lawn: dense
	else if (zone_id == 2) zone_density = 0.90;                   // A-lawn (NorthMeadow)
	else if (zone_id == 3) zone_density = 0.98;                   // Formal garden: manicured
	else if (zone_id == 4) zone_density = 0.85;                   // Sports turf
	else if (zone_id == 7) zone_density = 0.80;                   // C-lawn (waterside)
	else if (zone_id == 8) zone_density = 0.55;                   // Wild meadow: thick but gaps
	else if (zone_id == 9) zone_density = 0.70;                   // B/C open lawn
	else if (zone_id == 5) zone_density = 0.35;                   // NorthWoods: sparse shade
	else if (zone_id == 6) zone_density = 0.30;                   // Ramble: patchy woodland floor
	else if (zone_id == 10 || zone_id == 11) zone_density = 0.20; // Woodland: sparse, mostly litter

	if (r.x > zone_density) {
		pos.y = 0. / 0.;
		pos.xz = vec2(100000.0);
	}

	// Winter dormancy + snow: cull nearly all blades under heavy snow
	float winter_t = smoothstep(2.7, 3.5, season_t);
	float cull_factor = max(winter_t, snow_cover);
	if (cull_factor > 0.1 && r.y < cull_factor * 0.95) {
		pos.y = 0. / 0.;
		pos.xz = vec2(100000.0);
	}

	// Pass zone info to render shader via COLOR
	// R = zone_id normalized, G = canopy_cover, B = woodland flag, A = season_t / 4
	COLOR = vec4(float(zone_id) / 15.0, canopy_cover, is_woodland ? 1.0 : 0.0, season_t / 4.0);

	if (length(camera_position - pos) > max_dist) {
		pos.y = 0. / 0.;
		pos.xz = vec2(100000.0);
	} else {
		float fade_factor = 1.0 - smoothstep(max_dist * distance_fade_ammount, max_dist + 0.0001, length(camera_position - pos)) + 0.001;
		scale.y *= fade_factor;
		offset *= fade_factor;
	}

	// Apply scale
	TRANSFORM[0] *= scale.x;
	TRANSFORM[1] *= scale.y;
	TRANSFORM[2] *= scale.z;

	// Apply the position
	TRANSFORM[3].xyz = pos.xyz + offset;

	// Save Fixed 2 Random values for Reg/Green color randomness
	CUSTOM.rg = r.rg;
	// Save Y component scale pre-rotation
	CUSTOM[3] = scale.y;
}

void process() {
	// Extract world space UV from Transform Matrix
	vec2 uv = (TRANSFORM[3].xz + CUSTOM.rg * wind_dithering) * noise_scale;
	// Scaled wind noise, updated per instance, at process FPS. Passed to Vertex()
	CUSTOM[2] = textureLod(main_noise, uv + TIME * wind_speed * normalize(wind_direction), 0.0).r * wind_strength;
}
