#version 450

// GPU Grass compute shader — world-fixed placement with indirect draw.
//
// Evaluates a grid of potential grass positions centered on the camera.
// Positions snap to a world-fixed grid so blades are spatially deterministic:
// a brown patch at (100, 200) stays brown from every angle and distance.
//
// Samples heightmap for terrain Y, landuse for zone filtering, canopy for shade.

layout(local_size_x = 64, local_size_y = 1, local_size_z = 1) in;

// Binding 0: MultiMesh instance buffer (16 floats per instance)
layout(set = 0, binding = 0, std430) restrict writeonly buffer InstanceBuffer {
	float data[];
} instances;

// Binding 1: Indirect draw command buffer
layout(set = 0, binding = 1, std430) restrict buffer CommandBuffer {
	uint data[];
} cmd;

// Binding 2: Heightmap texture (R channel = terrain height in world units)
layout(set = 0, binding = 2) uniform sampler2D heightmap_tex;

// Binding 3: Landuse zone map (R channel = raw byte zone_id, 0..14)
layout(set = 0, binding = 3) uniform sampler2D landuse_tex;

// Binding 4: Canopy coverage map (R channel = 0-1 canopy density)
layout(set = 0, binding = 4) uniform sampler2D canopy_tex;

// Push constants (48 bytes)
layout(push_constant, std430) uniform PushConstants {
	vec4 camera_pos_spacing;   // xyz = camera world position, w = grid spacing
	vec4 grid_params;          // x = grid_side, y = max_distance, z = max_instances, w = world_size
	vec4 wind_config;          // x = target_biome, y = wind_x, z = wind_y, w = time
} pc;

// --- Deterministic hash functions ---
float hash1(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec2 hash2(vec2 p) {
	return fract(sin(vec2(
		dot(p, vec2(127.1, 311.7)),
		dot(p, vec2(269.5, 183.3))
	)) * 43758.5453);
}

// --- Smooth value noise for wind field ---
// Continuous noise with C1 interpolation (hermite smoothstep).
// Used to generate spatially coherent wind waves that travel across the field.
float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash1(i);
	float b = hash1(i + vec2(1.0, 0.0));
	float c = hash1(i + vec2(0.0, 1.0));
	float d = hash1(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// 3-octave fBm with per-octave rotation to break axis alignment.
// Returns ~0.0–1.0 range.
float fbm3(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	// Per-octave rotation avoids grid-aligned artifacts
	const mat2 rot = mat2(0.8, 0.6, -0.6, 0.8);
	for (int i = 0; i < 3; i++) {
		v += a * vnoise(p);
		p = rot * p * 2.0;
		a *= 0.5;
	}
	return v;
}

// World position → UV for texture sampling
vec2 world_to_uv(vec2 world_xz, float world_size) {
	return (world_xz + world_size * 0.5) / world_size;
}

void main() {
	uint gid = gl_GlobalInvocationID.x;

	int grid_side = int(pc.grid_params.x);
	uint total = uint(grid_side) * uint(grid_side);
	if (gid >= total) return;

	float spacing = pc.camera_pos_spacing.w;
	vec3 cam = pc.camera_pos_spacing.xyz;
	float world_size = pc.grid_params.w;

	// World-fixed grid centered on camera (snapped to spacing)
	vec2 grid_origin = floor(cam.xz / spacing) * spacing;
	int half_side = grid_side / 2;
	int ix = int(gid) % grid_side - half_side;
	int iz = int(gid) / grid_side - half_side;
	vec2 world_xz = grid_origin + vec2(float(ix), float(iz)) * spacing;

	// Per-position jitter (deterministic, breaks grid)
	vec2 jitter = (hash2(world_xz) - 0.5) * spacing * 0.8;
	world_xz += jitter;

	// Distance cull (circular)
	float dist = distance(world_xz, cam.xz);
	if (dist > pc.grid_params.y) return;

	// Texture UV for this world position
	vec2 uv = world_to_uv(world_xz, world_size);

	// Bounds check — skip positions outside the heightmap
	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return;

	// Sample terrain height
	float terrain_height = texture(heightmap_tex, uv).r;

	// Sample landuse zone (R8 byte 0..14 sampled as float 0..14/255)
	float zone_raw = texture(landuse_tex, uv).r;
	int zone_id = int(zone_raw * 255.0 + 0.5);

	// Zone filtering: only place grass on grass-bearing zones.
	// Biome 0 (lawn):  0=unzoned, 1=garden, 2=grass, 3=pitch, 4=playground,
	//                  6=dog_park, 7=sports, 9=track
	// Biome 1 (shade): 5=nature_reserve, 10=wood, 11=forest
	// Biome 2 (wild):  14=wild_meadow (hand-marked D-class lawns)
	// Biome 3 (sedge): 13=shore (15m dilation of water bodies)
	// Skip 8=pool, 12=water, and anything else.
	int biome_id = -1;
	if (zone_id == 0 || zone_id == 1 || zone_id == 2 || zone_id == 3
		|| zone_id == 4 || zone_id == 6 || zone_id == 7 || zone_id == 9) {
		biome_id = 0; // lawn
	} else if (zone_id == 5 || zone_id == 10 || zone_id == 11) {
		biome_id = 1; // shade
	} else if (zone_id == 14) {
		biome_id = 2; // wild meadow
	} else if (zone_id == 13) {
		biome_id = 3; // sedge / waterside
	}
	int target_biome_early = int(pc.wind_config.x);
	if (target_biome_early != -2 && biome_id < 0) return; // Not a grass zone

	// Biome filter: skip positions that don't match target biome.
	// target_biome == -2 is a debug mode that bypasses zone/canopy/distance
	// filters and forces a blade at every grid position (regardless of
	// landuse zone). Used by F3 to diagnose whether the rendering pipeline
	// is alive, independent of zone-data correctness.
	int target_biome = int(pc.wind_config.x);
	bool debug_force = target_biome == -2;
	if (!debug_force && target_biome >= 0 && biome_id != target_biome) return;

	// Sample canopy coverage
	float canopy = texture(canopy_tex, uv).r;

	// Canopy suppression (biome-specific)
	float suppress = 0.0;
	if (biome_id == 0) suppress = 0.90;      // Lawn: sun-loving, heavy suppression
	else if (biome_id == 1) suppress = 0.30;  // Shade: tolerant
	else suppress = 0.60;                      // Wild/Sedge: moderate
	float canopy_thresh = canopy * suppress;
	if (!debug_force && hash1(world_xz * 3.7) < canopy_thresh) return;

	// Deterministic per-position properties
	float h1 = hash1(world_xz);
	float h2 = hash1(world_xz * 1.7 + vec2(31.5, 97.2));

	float rotation = h1 * 6.283185;
	float scale = 0.7 + h2 * 0.6; // 0.7–1.3

	// Macro patch tone (20-25m scale) — deterministic per world position
	float patch_tone = hash1(floor(world_xz / 22.0));

	// Distance-based thinning: probabilistically skip blades at distance.
	// Start late (60%) so near-field stays dense; thin to nothing by max.
	float dist_ratio = dist / pc.grid_params.y;
	float thin_prob = smoothstep(0.6, 1.0, dist_ratio);
	if (!debug_force && hash1(world_xz * 5.3 + vec2(71.0, 13.0)) < thin_prob) return;

	// Allocate instance slot. atomicAdd always increments, so threads that
	// overflow past max_instances must clamp instanceCount back via atomicMin
	// — otherwise the indirect draw issues 3-10× more draws than buffer slots,
	// causing OOB reads in vkCmdDrawIndexedIndirect.
	uint idx = atomicAdd(cmd.data[1], 1);
	if (idx >= uint(pc.grid_params.z)) {
		atomicMin(cmd.data[1], uint(pc.grid_params.z));
		return;
	}

	// Build Y-rotation + scale transform
	float cos_r = cos(rotation);
	float sin_r = sin(rotation);

	// Buffer layout: 12 transform + 4 color + 4 custom_data = 20 floats per instance
	uint base = idx * 20u;

	// Row 0: (scale*cos, 0, scale*-sin, world_x)
	instances.data[base + 0u] = scale * cos_r;
	instances.data[base + 1u] = 0.0;
	instances.data[base + 2u] = scale * -sin_r;
	instances.data[base + 3u] = world_xz.x;

	// Row 1: (0, scale, 0, terrain_height)
	instances.data[base + 4u] = 0.0;
	instances.data[base + 5u] = scale;
	instances.data[base + 6u] = 0.0;
	instances.data[base + 7u] = terrain_height;

	// Row 2: (scale*sin, 0, scale*cos, world_z)
	instances.data[base + 8u] = scale * sin_r;
	instances.data[base + 9u] = 0.0;
	instances.data[base + 10u] = scale * cos_r;
	instances.data[base + 11u] = world_xz.y;

	// COLOR layout: (zone_id/15, canopy, biome_id_norm, reserved)
	// biome_id_norm encodes biome 0..3 as 0.0..0.75 so the render shader
	// can apply a per-biome tint independent of zone-palette lookups.
	// In debug_force mode biome_id can be -1 (no zone match); fall back
	// to whichever biome this dispatch targets so the tint is still meaningful.
	int biome_for_tint = biome_id;
	if (biome_for_tint < 0) biome_for_tint = (target_biome >= 0 ? target_biome : 0);
	instances.data[base + 12u] = float(zone_id) / 15.0;
	instances.data[base + 13u] = canopy;
	instances.data[base + 14u] = float(biome_for_tint) * 0.25;
	instances.data[base + 15u] = 0.0;

	// INSTANCE_CUSTOM: (random1, random2, wind_noise, grass_scale)
	// Wind noise: traveling fBm waves create visible wind fronts across the field.
	// Nearby blades get similar values (spatial coherence), scrolled by wind direction.
	vec2 wind_dir = vec2(pc.wind_config.y, pc.wind_config.z);
	float wind_str = length(wind_dir);
	float t = pc.wind_config.w;

	float wind_noise = 0.0;
	if (wind_str > 0.001) {
		vec2 wn = normalize(wind_dir);

		// Primary traveling wave: fBm scrolled along wind direction
		// 0.08 scale = ~12m wavelength — visible grass ripples
		vec2 wave_uv = world_xz * 0.08 - wn * t * 2.5;
		float wave = fbm3(wave_uv);

		// Secondary gust front: broader scale, slower scroll
		// 0.02 scale = ~50m — creates large sweeping gusts
		vec2 gust_uv = world_xz * 0.02 - wn * t * 0.8;
		float gust = fbm3(gust_uv + vec2(73.1, 41.7));
		gust = smoothstep(0.42, 0.72, gust); // Only peaks become gusts

		// Combined: base sway + wave modulation + gust surges
		wind_noise = wind_str * (0.5 + 0.5 * wave) + gust * wind_str * 0.7;

		// Per-blade micro-variation so adjacent blades aren't perfectly in sync
		wind_noise *= 0.85 + 0.3 * h1;
	}

	instances.data[base + 16u] = h1;           // random seed for color variation
	instances.data[base + 17u] = patch_tone;   // macro patch tone
	instances.data[base + 18u] = wind_noise;   // per-instance wind bend strength
	instances.data[base + 19u] = scale;         // grass_scale for wind strength
}
