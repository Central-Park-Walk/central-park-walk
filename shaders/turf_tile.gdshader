shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// TURF TILE — a real 3D mesh of a patch of grass (hundreds of baked blade geometries),
// instanced as tiles across a camera-following world grid. This is the "3d mesh world"
// approach: genuine blades viewable from ANY angle (including straight down), no
// billboard swivel, no radial rings. Cost lives in triangles (batched, few instances),
// not in millions of per-blade instances. Per-blade shape/colour is BAKED at build time
// (main.gd _make_turf_tile_mesh) so the vertex shader stays cheap: terrain conform,
// per-tile yaw (breaks the one-mesh repeat), wind, far-rim fade.

// Conform to TERRAIN3D's real surface (not the divergent heightmap.bin) — see the include.
#include "res://shaders/include/terrain3d_height.gdshaderinc"

global uniform vec2 wind_vec;
global uniform vec3 player_world_pos;   // camera world position (main.gd, per frame)
// Altitude fade: retire the 3D blade dome as the camera climbs above the ground.
uniform float alt_fade_lo = 12.0;   // full dome at/below this height above terrain (m)
uniform float alt_fade_hi = 28.0;   // dome fully gone by here (flying)
uniform vec2  band_center = vec2(0.0);
// CONTINUOUS density falloff (single mesh, no LOD rings): every blade carries a stable rank
// in [0,1); a blade survives where its rank is under keep(dist), which is 1 within near_full
// and eases to 0 at far_radius. So the sward is full near and thins smoothly to nothing by
// far_radius — no ring boundaries to cross-fade (which shimmered), and blades vanish while
// still resolvable so there are no sub-pixel far specks to crawl under FSR.
uniform float near_full   = 9.0;   // full density within this radius
uniform float far_radius  = 14.0;  // blades thinned to zero by here
uniform float far_fade    = 2.5;   // soft size-fade at the very rim

// Camera-snap passed as a UNIFORM instead of moving the MMI. Moving the MMI made MODEL_MATRIX
// jump 2 m at each snap; because the blades are placed procedurally (VERTEX = worldxz - base),
// Godot then emitted a bogus 2 m motion vector for every blade and TAA/FSR2 smeared the whole
// field to "catch up" every couple metres (Chris: unplayable popping). With the MMI held fixed
// (MODEL_MATRIX constant) and the snap fed here, motion vectors stay correct → no temporal pop.
uniform vec2  tile_snap    = vec2(0.0);

// Ground-mat grass texture (world-XZ planar): breaks up the flat colour of the horizontal
// mat + thatch so straight-down shows real turf detail, never solid colour pools.
uniform sampler2D mat_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float mat_tex_scale = 1.3;                    // texture repeats per metre
uniform vec3  mat_tint      = vec3(0.48, 0.94, 0.56); // re-measured to KBG sod ref: red pulled
                                                      // DOWN (grass_albedo.jpg is olive → too
                                                      // red) so the mat reads blue-green (G/R~2)
uniform float mat_bright    = 0.46;                   // darker — the flat up-facing mat catches
                                                      // full sun; this is the bright midground
                                                      // Chris wants darkened toward the sod ref

// LAND MASK — the grass is tied to the LAND, not the camera: only render blades where the
// landuse zone is actually grass. Without this the camera-following dome drew turf over
// water, paths and pavement ("follows me out over water, everywhere"). Same landuse map +
// jittered lookup the shell grass and terrain felt use.
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform float world_size = 5000.0;

varying vec3  v_col;
varying float v_up;
varying float v_ground;   // 1 = horizontal ground mat/thatch (sample mat_tex)
varying vec2  v_wxz;      // stable (uncollapsed) world XZ for the mat texture

float h21(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// Landuse zone at world XZ, jittered so zone boundaries dither instead of rendering the
// low-res landuse texel grid as hard staircases (matches the shell/terrain lookup).
int zone_at(vec2 w){
	vec2 jit = vec2(h21(w * 13.1), h21(w * 13.1 + vec2(7.3, 41.9))) - 0.5;
	vec2 uv = (w + jit * 1.8 + world_size * 0.5) / world_size;
	return int(texture(landuse_map, uv).r * 255.0 + 0.5);
}
// Zones with NO grass (docs/grass.md §2): 8=pool 12=water. Grass is culled here so the
// dome never draws over water/pool. (Paths/pavement handled by the wear map later.)
bool zone_no_grass(int z){ return z == 8 || z == 12; }

void vertex(){
	// inst = this tile's FIXED instance origin (the MMI is never moved, so MODEL_MATRIX is
	// constant → correct motion vectors). tile_snap (uniform) slides the tile to the camera.
	vec3 inst = MODEL_MATRIX[3].xyz;
	vec2 base_xz = inst.xz + tile_snap;           // camera-following tile world origin
	// Per-tile yaw so the single tile mesh doesn't read as a repeating stamp.
	float yaw = h21(floor(base_xz + 0.5) * 0.137) * 6.2831;
	float cy = cos(yaw), sy = sin(yaw);
	vec2  lx  = VERTEX.xz;
	vec2  rot = vec2(lx.x * cy - lx.y * sy, lx.x * sy + lx.y * cy);

	float up   = UV.y;                            // 0 base .. 1 tip (baked)
	float rank = UV.x;                            // per-blade stable density priority [0,1)

	vec2  rot_full = rot;                         // uncollapsed rotated offset (for mat UV)
	vec2  approx_w = base_xz + rot;
	float dist  = distance(approx_w, band_center);

	// CONTINUOUS falloff: keep=1 within near_full, easing to 0 at far_radius. A blade lives
	// where rank < keep. Wider `alive` band = the density thins over a LONGER taper (denser
	// centre → gradually sparser out), so the rim dissolves instead of ending in a hard line
	// (Chris: "hard line at the edge of the dome" + "field pops as I move").
	float keep  = 1.0 - smoothstep(near_full, far_radius, dist);
	float alive = smoothstep(0.0, 0.28, keep - rank);
	// Extra soft size-fade over the very rim so the last blades shrink out rather than pop.
	float cover = alive * (1.0 - smoothstep(far_radius - far_fade, far_radius, dist));
	// ALTITUDE FADE: from the air the 3D dome only hurts — black inter-blade gaps straight
	// down, the terrain quilt revealed through its own thinning, and a dome that visibly
	// follows the camera — while the terrain macro texture already reads as grass. So retire
	// it with camera height above the tile's ground (also a GPU win when flying).
	float cam_alt = player_world_pos.y - sample_terrain(base_xz);
	cover *= 1.0 - smoothstep(alt_fade_lo, alt_fade_hi, cam_alt);
	// LAND MASK: kill grass where the land isn't grass (water/pool) so the dome is tied to
	// the land, not the camera. Collapses the blade/mat to nothing over water.
	if (zone_no_grass(zone_at(approx_w))) cover = 0.0;
	rot *= cover;
	float y = VERTEX.y * cover;

	// Wind: gentle coherent sway of the tip (bend from base). The wave PHASE runs along a
	// FIXED axis (not the wind direction): phasing off the wandering wind dir × the absolute
	// world position (±2 km in the park) made a tiny gust-wander snap the whole field's phase
	// by radians = the "crazy wind" thrash. Wind now only sets AMPLITUDE (scaled by strength,
	// capped so it never explodes) and the lean DIRECTION.
	float wlen = length(wind_vec);
	vec2  wdir = wlen > 0.001 ? wind_vec / wlen : vec2(0.7071, 0.7071);
	float wstr = clamp(wlen * 1.6, 0.0, 1.0);                 // 0 calm .. 1 strong (capped)
	float phase = TIME * 0.9 + dot(approx_w, vec2(0.7071, 0.7071)) * 0.35;   // stable spatial wave
	float sway = sin(phase) * mix(0.008, 0.05, wstr);         // still in calm, fuller when windy
	vec2  worldxz = base_xz + rot + wdir * (sway * up * up * cover);

	float H = sample_terrain(worldxz);
	// Subtract the FIXED instance origin (not the snapped tile origin) so MODEL_MATRIX * VERTEX
	// lands at the true world position while MODEL_MATRIX itself never changes.
	VERTEX = vec3(worldxz.x, H + y, worldxz.y) - inst;
	NORMAL = vec3(0.0, 1.0, 0.0);                 // up (lit as a soft mass; ramp is baked)

	float tint = mix(0.90, 1.10, h21(floor(base_xz + 0.5) * 1.7 + 3.0));
	v_col = COLOR.rgb * tint;
	v_up  = up;
	v_ground = UV2.x;
	v_wxz = base_xz + rot_full;                   // true world XZ (stable under collapse)
}

void fragment(){
	vec3 alb = v_col;
	if (v_ground > 0.5) {
		// Real grass detail on the horizontal mat/thatch: the world-XZ texture supplies
		// blade detail, the baked mat tone (v_col, per-quad brightness jitter) keeps it in
		// the shaded-thatch value range. No flat colour pools when looking straight down.
		vec3 tex = texture(mat_tex, v_wxz * mat_tex_scale).rgb;
		float qbright = clamp(v_col.g * 3.2, 0.5, 1.3);   // carries per-quad brightness var
		alb = tex * mat_tint * (mat_bright * qbright);
	}
	ALBEDO    = alb;
	ROUGHNESS = 0.98;   // near-matte — Chris: "grass is too shiny"
	SPECULAR  = 0.02;   // was 0.10; kill the plasticky highlight
	// Faint translucency only at the very tip — kept low so blades read as solid grass,
	// not a pale/washed-out sheen (Chris: "less white/transparent").
	BACKLIGHT = vec3(0.06, 0.09, 0.04) * v_up * v_up;
}
