shader_type spatial;
render_mode cull_disabled, world_vertex_coords;

// POC v2: shell-textured short mown turf, de-plasticised.
// Fixes the "astroturf / green hedgehog" read of v1:
//  - blades are anisotropic RIBBONS (thin slivers), not round cones
//  - patch-scale noise varies height / colour / density (turf is patchy)
//  - per-area FLOW direction combs blades coherently (kills the radial swirl)
//  - softer, varied specular (less uniform plastic glint)

uniform int   shell_count  = 44;
uniform float grass_height  = 0.09;   // meters
uniform float density       = 33.0;   // blade cells per meter
uniform float blade_len     = 0.46;   // half-length along the blade (cell frac)
uniform float blade_wid     = 0.110;  // half-width across the blade (cell frac)
uniform float lean_amt      = 0.62;   // top-of-blade lean (cell frac)
uniform vec3  understory : source_color = vec3(0.055, 0.100, 0.035);
uniform vec3  blade_base : source_color = vec3(0.090, 0.170, 0.050);
uniform vec3  blade_tip  : source_color = vec3(0.360, 0.550, 0.200);

varying float v_layer;
varying vec3  v_world;

// Hash21/22 (Hoskins) — no axis symmetry, so no mirror seam at x=0/z=0.
float hash21(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}
vec2 hash22(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}
float vnoise(vec2 p){
	vec2 i = floor(p), f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash21(i), b = hash21(i + vec2(1.0, 0.0));
	float c = hash21(i + vec2(0.0, 1.0)), d = hash21(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void vertex(){
	float f = float(INSTANCE_ID) / float(max(shell_count - 1, 1));
	v_layer = f;
	VERTEX.y += f * grass_height;
	v_world = VERTEX;
}

void fragment(){
	vec2 world = v_world.xz;
	float f = v_layer;

	// --- patch-scale variation (low frequency) ---
	float patch  = vnoise(world * 0.22);          // ~4.5 m colour patches
	float patchH = vnoise(world * 0.55 + 31.0);    // height patches
	float sparse = vnoise(world * 0.40 + 7.0);     // density patches

	// --- per-blade cell ---
	vec2 uv    = world * density;
	vec2 cell  = floor(uv);
	vec2 local = fract(uv) - 0.5;
	float r1   = hash21(cell);
	local -= (hash22(cell) - 0.5) * 0.5;            // jitter blade centre

	// thin out blades in sparse patches (varies density, breaks the grid)
	if (hash21(cell + 3.3) > mix(0.82, 0.995, sparse)) discard;

	// --- combing: coherent per-area flow direction + per-blade jitter ---
	float ang = vnoise(world * 0.16) * 6.2831 + (r1 - 0.5) * 1.3;
	vec2  dir = vec2(cos(ang), sin(ang));
	// Lean: a linear term tilts even low shells (so blades aren't pure-vertical
	// at the base — that verticality is what empties the nadir top-down), plus a
	// quadratic term so the tip still bends over more than the base.
	local -= dir * (f * 0.35 + f * f * 0.65) * lean_amt;

	// --- blade height (patch-modulated) ---
	float bh = clamp(mix(0.5, 1.0, r1) * mix(0.72, 1.12, patchH), 0.0, 1.0);
	if (f > bh) discard;
	float t = f / bh;                               // 0 base .. 1 tip

	// --- anisotropic RIBBON footprint (long along dir, thin across) ---
	vec2 rl = vec2(dot(local, dir), dot(local, vec2(-dir.y, dir.x)));
	float halfL = mix(blade_len, blade_len * 0.45, t);
	float halfW = mix(blade_wid, 0.010, t);          // taper width to the tip
	if (abs(rl.x) > halfL || abs(rl.y) > halfW) discard;

	// --- colour ---
	float ao  = mix(0.42, 1.0, f);                   // base dark / tip bright
	vec3  col = mix(blade_base, blade_tip, f);
	col *= mix(0.88, 1.12, patch);                   // patch value
	col  = mix(col, col * vec3(1.08, 1.0, 0.70), patch * 0.40); // warm/cool patches
	col *= mix(0.92, 1.08, r1);                       // per-blade value
	float lum = dot(col, vec3(0.30, 0.59, 0.11));
	col = mix(vec3(lum), col, 0.90);                  // pull a touch of saturation out
	ALBEDO = mix(understory, col, smoothstep(0.0, 0.10, f)) * ao;

	// --- shading: flatter ribbon normal, softer varied specular ---
	vec3 n = normalize(vec3(rl.y * 0.5 * dir.x, 1.0, rl.y * 0.5 * dir.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ROUGHNESS = mix(0.55, 0.80, hash21(cell + 9.1));
	SPECULAR  = 0.25;
	BACKLIGHT = vec3(0.25 * f);
}
