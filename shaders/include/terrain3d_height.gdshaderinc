// Sample TERRAIN3D's OWN height maps — the exact surface the player sees and collides with.
// Grass/ground layers used to conform to the separate project heightmap (heightmap.bin), which
// diverges from Terrain3D by 0.2-6.5 m on slopes (same source data, but runtime tunnel-void
// lowering + a texel-vs-vertex sampling offset), burying short blades under the terrain mesh.
// These uniforms + get_index_coord are the addon's own height path (extras/particle_example);
// push them from GDScript via RenderingServer.material_set_param (RID/array uniforms can't go
// through set_shader_parameter):
//   _height_maps      = terrain.data.get_height_maps_rid()
//   _region_map       = terrain.data.get_region_map()
//   _region_size      = terrain.region_size ; _region_texel_size = 1.0/region_size
//   _vertex_density   = 1.0 / terrain.vertex_spacing
//   _background_mode  = terrain.material.world_background ; _region_map_size = 32
uniform highp sampler2DArray _height_maps : repeat_disable;
uniform int   _region_map[1024];
uniform int   _region_map_size = 32;
uniform float _region_size = 1024.0;
uniform float _region_texel_size = 0.0009765625;
uniform float _vertex_density = 1.0;
uniform uint  _background_mode = 0u;

// world XZ grid coord → (texel xy, region layer). Verbatim from the Terrain3D addon.
ivec3 t3d_index_coord(vec2 uv) {
	vec2 r_uv = round(uv);
	vec2 o_uv = mod(r_uv, _region_size);
	ivec2 pos;
	int bounds, layer_index = -1;
	for (int i = -1; i < 0; i++) {
		if ((layer_index == -1 && _background_mode == 0u) || i < 0) {
			r_uv -= i == -1 ? vec2(0.0) : vec2(float(o_uv.x <= o_uv.y), float(o_uv.y <= o_uv.x));
			pos = ivec2(floor((r_uv) * _region_texel_size)) + (_region_map_size / 2);
			bounds = int(uint(pos.x | pos.y) < uint(_region_map_size));
			layer_index = (_region_map[pos.y * _region_map_size + pos.x] * bounds - 1);
		}
	}
	return ivec3(ivec2(mod(r_uv, _region_size)), layer_index);
}

// Bilinear Terrain3D height (metres) at world XZ. Same name/signature as the old heightmap
// sample_terrain so call sites are unchanged.
float sample_terrain(vec2 world_xz) {
	vec2 uv = world_xz * _vertex_density;
	vec2 b  = floor(uv);
	vec2 w  = uv - b;
	float h00 = texelFetch(_height_maps, t3d_index_coord(b + vec2(0.0, 0.0)), 0).r;
	float h10 = texelFetch(_height_maps, t3d_index_coord(b + vec2(1.0, 0.0)), 0).r;
	float h01 = texelFetch(_height_maps, t3d_index_coord(b + vec2(0.0, 1.0)), 0).r;
	float h11 = texelFetch(_height_maps, t3d_index_coord(b + vec2(1.0, 1.0)), 0).r;
	return mix(mix(h00, h10, w.x), mix(h01, h11, w.x), w.y);
}
