shader_type spatial;

uniform vec3 bark_color = vec3(0.48, 0.38, 0.28);
// 0=deep furrows (oak/elm), 1=smooth+lenticels (birch/cherry),
// 2=exfoliating patches (london plane), 3=scaled plates (pine), 4=smooth (magnolia)
uniform int bark_style = 0;
global uniform float rain_wetness;
global uniform float snow_cover;
global uniform float season_t;
global uniform vec2 wind_vec;
global uniform vec3 sky_reflect_color;

// PBR bark textures — photogrammetry-scanned real bark surfaces (CC0)
// One set per bark style, blended with procedural FBM for per-tree variation
uniform sampler2D bark_albedo_tex : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D bark_normal_tex : hint_normal, filter_linear_mipmap_anisotropic;
uniform sampler2D bark_roughness_tex : filter_linear_mipmap_anisotropic;
uniform float tex_blend = 0.45;        // 0=pure procedural, 1=pure texture
uniform float tex_uv_scale = 0.7;      // world-space tiling frequency

varying vec3 world_pos;
varying vec3 world_nrm;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/seasonal.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"
#include "res://shaders/include/tree_species.gdshaderinc"
#include "res://shaders/include/wind.gdshaderinc"

// Variable-octave FBM for bark texture detail
float fbm(vec2 p, int oct) {
	float v = 0.0, a = 0.5;
	for (int i = 0; i < oct; i++) { v += a*vnoise(p); p *= 2.17; a *= 0.49; }
	return v;
}

void vertex() {
	// --- Per-species wind sway (shared wind include) ---
	int sp_idx = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	vec4 wp = WIND_PARAMS[sp_idx];
	float trunk_flex = wp.x;
	float branch_flex = wp.y;
	float sway_freq = wp.z;
	float gust_resp = wp.w;

	vec3 tree_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float h = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);
	float rustle = 0.3 + wind_str * 0.7;
	float phase = wind_phase(tree_origin);

	float branch_phase = COLOR.b * 6.283 + phase;
	float crown = smoothstep(1.5, 4.0, h);

	// Cantilever trunk + branch sway + wind push
	vec2 trunk_d = wind_cantilever_trunk(h, sway_freq, trunk_flex, rustle, phase);
	vec2 branch_d = wind_branch_sway(h, crown, sway_freq, branch_flex, branch_phase, rustle, 0.06, 0.04);
	vec2 push_d = wind_push(wind_vec, h, 0.10, trunk_flex);
	VERTEX.x += trunk_d.x + branch_d.x + push_d.x;
	VERTEX.z += trunk_d.y + branch_d.y + push_d.y;

	// Gusts
	float gust = wind_gust(tree_origin, 0.3, 3.0);
	float gust_strength = gust * wind_str * 0.20 * gust_resp;
	VERTEX.x += wind_vec.x * h * gust_strength;
	VERTEX.z += wind_vec.y * h * gust_strength;

	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	// Per-tree variation seed from model origin
	vec3 tree_base = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float tree_var = hash2(floor(tree_base.xz * 0.5));
	vec3 col = bark_color * (0.90 + tree_var * 0.20);

	float local_h = world_pos.y - tree_base.y;
	float furrow = 0.5;
	float rough = 0.88;
	float micro = 0.0;

	// Triplanar weights — used for BOTH procedural noise and PBR textures.
	// Eliminates horizontal stripe artifacts from planar UV projection on
	// cylindrical branches and angled trunk faces.
	vec3 tri_w = abs(world_nrm);
	tri_w = pow(tri_w, vec3(4.0));
	tri_w /= (tri_w.x + tri_w.y + tri_w.z);

	// Per-tree UV offset to break tiling between adjacent trees
	vec2 tree_uv_ofs = floor(tree_base.xz * 0.37) * 0.31;

	// Triplanar UVs for procedural bark patterns (world-space, per-tree offset)
	vec2 puv_yz = world_pos.yz + tree_uv_ofs;
	vec2 puv_xz = world_pos.xz + tree_uv_ofs;
	vec2 puv_xy = world_pos.xy + tree_uv_ofs;

	// Triplanar FBM helper — samples from 3 planes, blends by normal
	// Vertical stretch (1.2x) makes cracks run mostly vertical on trunks

	if (bark_style == 0) {
		// --- Style 0: Rough fissured bark (oak, elm, maple, ginkgo, etc.) ---
		float cn_yz = fbm(puv_yz * vec2(2.5, 1.2), 4);
		float cn_xz = fbm(puv_xz * vec2(2.5, 1.2), 4);
		float cn_xy = fbm(puv_xy * vec2(2.5, 1.2), 4);
		float crack_noise = cn_yz * tri_w.x + cn_xz * tri_w.y + cn_xy * tri_w.z;
		furrow = smoothstep(0.42, 0.46, crack_noise);
		col *= mix(0.62, 1.08, furrow);
		float mi_yz = fbm(puv_yz * vec2(8.0, 6.0), 3);
		float mi_xz = fbm(puv_xz * vec2(8.0, 6.0), 3);
		float mi_xy = fbm(puv_xy * vec2(8.0, 6.0), 3);
		micro = mi_yz * tri_w.x + mi_xz * tri_w.y + mi_xy * tri_w.z;
		float gr_yz = vnoise(puv_yz * vec2(14.0, 12.0));
		float gr_xz = vnoise(puv_xz * vec2(14.0, 12.0));
		float gr_xy = vnoise(puv_xy * vec2(14.0, 12.0));
		float grit = gr_yz * tri_w.x + gr_xz * tri_w.y + gr_xy * tri_w.z;
		col *= (0.88 + micro * 0.16 + grit * 0.08);
		rough = mix(0.78, 0.96, furrow) + micro * 0.04;
	} else if (bark_style == 1) {
		// --- Style 1: Smooth bark with horizontal lenticels (birch, cherry) ---
		// Lenticels are genuinely horizontal, so we use local_h for the banding
		// but triplanar for the noise perturbation to avoid facet stripes
		float np_yz = vnoise(puv_yz * vec2(0.4, 0.6));
		float np_xz = vnoise(puv_xz * vec2(0.4, 0.6));
		float np_xy = vnoise(puv_xy * vec2(0.4, 0.6));
		float noise_perturb = np_yz * tri_w.x + np_xz * tri_w.y + np_xy * tri_w.z;
		float h_band = sin(local_h * 21.6 + noise_perturb * 1.5);
		furrow = smoothstep(0.3, 0.6, h_band);
		// Lenticels: use triplanar for horizontal position
		float lu_yz = vnoise(puv_yz * vec2(8.0, 2.0));
		float lu_xz = vnoise(puv_xz * vec2(8.0, 2.0));
		float lu_xy = vnoise(puv_xy * vec2(8.0, 2.0));
		float lenticel_u = lu_yz * tri_w.x + lu_xz * tri_w.y + lu_xy * tri_w.z;
		float lenticel_h = sin(local_h * 42.0 + lenticel_u * 3.0);
		float lenticel = smoothstep(0.75, 0.90, lenticel_h) * smoothstep(0.4, 0.8, lenticel_u);
		col *= mix(1.0, 0.65, lenticel * 0.7);
		col *= (0.96 + furrow * 0.08);
		float mi_yz = vnoise(puv_yz * vec2(15.0, 10.0));
		float mi_xz = vnoise(puv_xz * vec2(15.0, 10.0));
		float mi_xy = vnoise(puv_xy * vec2(15.0, 10.0));
		micro = (mi_yz * tri_w.x + mi_xz * tri_w.y + mi_xy * tri_w.z) * 0.06;
		col *= (0.97 + micro);
		rough = 0.55 + lenticel * 0.20;
		float pl_yz = fbm(puv_yz * vec2(1.2, 0.8), 2);
		float pl_xz = fbm(puv_xz * vec2(1.2, 0.8), 2);
		float pl_xy = fbm(puv_xy * vec2(1.2, 0.8), 2);
		float peel_n = pl_yz * tri_w.x + pl_xz * tri_w.y + pl_xy * tri_w.z;
		float peel = smoothstep(0.60, 0.75, peel_n);
		peel *= smoothstep(2.0, 4.0, local_h) * smoothstep(8.0, 5.0, local_h);
		col = mix(col, col * 1.15, peel * 0.3);
	} else if (bark_style == 2) {
		// --- Style 2: Exfoliating mottled patches (london plane / sycamore) ---
		float pn_yz = fbm(puv_yz * vec2(1.5, 1.0), 3);
		float pn_xz = fbm(puv_xz * vec2(1.5, 1.0), 3);
		float pn_xy = fbm(puv_xy * vec2(1.5, 1.0), 3);
		float patch_n = pn_yz * tri_w.x + pn_xz * tri_w.y + pn_xy * tri_w.z;
		float p2_yz = vnoise(puv_yz * vec2(2.8, 2.2) + vec2(17.0, 0.0));
		float p2_xz = vnoise(puv_xz * vec2(2.8, 2.2) + vec2(17.0, 0.0));
		float p2_xy = vnoise(puv_xy * vec2(2.8, 2.2) + vec2(17.0, 0.0));
		float patch2 = p2_yz * tri_w.x + p2_xz * tri_w.y + p2_xy * tri_w.z;
		vec3 cream_bark = col * vec3(1.30, 1.25, 1.10);
		vec3 olive_bark = col * vec3(0.82, 0.88, 0.75);
		vec3 gray_bark  = col * vec3(0.90, 0.88, 0.85);
		float zone1 = smoothstep(0.3, 0.5, patch_n);
		float zone2 = smoothstep(0.5, 0.7, patch2);
		col = mix(gray_bark, cream_bark, zone1);
		col = mix(col, olive_bark, zone2 * 0.6);
		float edge = abs(fract(patch_n * 3.0) - 0.5) * 2.0;
		edge = 1.0 - smoothstep(0.0, 0.15, edge);
		col *= (1.0 - edge * 0.12);
		furrow = 1.0 - edge;
		float mi_yz = vnoise(puv_yz * vec2(10.0, 8.0));
		float mi_xz = vnoise(puv_xz * vec2(10.0, 8.0));
		float mi_xy = vnoise(puv_xy * vec2(10.0, 8.0));
		micro = (mi_yz * tri_w.x + mi_xz * tri_w.y + mi_xy * tri_w.z) * 0.08;
		col *= (0.96 + micro);
		rough = mix(0.65, 0.80, zone1);
	} else if (bark_style == 3) {
		// --- Style 3: Thick scaled plates (pine / conifer) ---
		float sn_yz = vnoise(puv_yz * vec2(0.5, 0.3));
		float sn_xz = vnoise(puv_xz * vec2(0.5, 0.3));
		float sn_xy = vnoise(puv_xy * vec2(0.5, 0.3));
		float shift_n = sn_yz * tri_w.x + sn_xz * tri_w.y + sn_xy * tri_w.z;
		// Use triplanar base coords for plate pattern
		vec2 plate_uv = puv_yz * tri_w.x + puv_xz * tri_w.y + puv_xy * tri_w.z;
		float plate_y = floor(plate_uv.y * 2.5 + shift_n * 0.8);
		float plate_u = floor(plate_uv.x * 1.8 + shift_n * 0.6);
		float plate_fy = fract(plate_uv.y * 2.5 + shift_n * 0.8);
		float plate_fu = fract(plate_uv.x * 1.8 + shift_n * 0.6);
		float fissure_y = smoothstep(0.0, 0.08, plate_fy) * smoothstep(1.0, 0.92, plate_fy);
		float fissure_u = smoothstep(0.0, 0.10, plate_fu) * smoothstep(1.0, 0.90, plate_fu);
		furrow = fissure_y * fissure_u;
		float plate_var = hash2(vec2(plate_y, plate_u));
		col *= mix(0.85, 1.15, plate_var);
		col *= mix(0.72, 1.0, furrow);
		float mi_yz = fbm(puv_yz * vec2(8.0, 6.0), 2);
		float mi_xz = fbm(puv_xz * vec2(8.0, 6.0), 2);
		float mi_xy = fbm(puv_xy * vec2(8.0, 6.0), 2);
		micro = mi_yz * tri_w.x + mi_xz * tri_w.y + mi_xy * tri_w.z;
		col *= (0.94 + micro * 0.12);
		rough = mix(0.85, 0.95, 1.0 - furrow) + micro * 0.04;
	} else {
		// --- Style 4: Smooth gray (magnolia, callery pear, beech) ---
		float mo_yz = vnoise(puv_yz * vec2(2.5, 2.0));
		float mo_xz = vnoise(puv_xz * vec2(2.5, 2.0));
		float mo_xy = vnoise(puv_xy * vec2(2.5, 2.0));
		float mottled = mo_yz * tri_w.x + mo_xz * tri_w.y + mo_xy * tri_w.z;
		float fm_yz = vnoise(puv_yz * vec2(5.0, 4.5));
		float fm_xz = vnoise(puv_xz * vec2(5.0, 4.5));
		float fm_xy = vnoise(puv_xy * vec2(5.0, 4.5));
		float fine_mot = fm_yz * tri_w.x + fm_xz * tri_w.y + fm_xy * tri_w.z;
		furrow = smoothstep(0.3, 0.7, mottled);
		col *= (0.94 + furrow * 0.10 + fine_mot * 0.04);
		float mi_yz = vnoise(puv_yz * vec2(10.0, 8.0));
		float mi_xz = vnoise(puv_xz * vec2(10.0, 8.0));
		float mi_xy = vnoise(puv_xy * vec2(10.0, 8.0));
		micro = (mi_yz * tri_w.x + mi_xz * tri_w.y + mi_xy * tri_w.z) * 0.04;
		col *= (0.98 + micro);
		rough = 0.58 + furrow * 0.12;
		float bu_yz = fbm(puv_yz * vec2(5.0, 3.0), 2);
		float bu_xz = fbm(puv_xz * vec2(5.0, 3.0), 2);
		float bu_xy = fbm(puv_xy * vec2(5.0, 3.0), 2);
		float bump = bu_yz * tri_w.x + bu_xz * tri_w.y + bu_xy * tri_w.z;
		col *= (0.96 + bump * 0.08);
	}

	// --- Height-based bark variation (all styles) ---
	float height_factor = smoothstep(0.0, 6.0, local_h);
	col *= mix(0.88, 1.0, height_factor);
	rough = mix(rough + 0.03, rough, height_factor);
	float upper = smoothstep(4.0, 10.0, local_h);
	col = mix(col, col * 1.12, upper * 0.3);  // lighter higher up

	// --- 3D relief from fissure pattern ---
	// Perturb the surface normal so cracks catch light at different angles.
	// Uses screen-space derivatives of the furrow depth — ridges face outward,
	// fissures recede. This is what makes bark look 3D instead of painted on.
	float relief_h = furrow + micro * 0.4;
	vec3 bark_normal_perturb = vec3(dFdx(relief_h), dFdy(relief_h), 0.0);

	// --- Triplanar PBR texture blending ---
	// tri_w and tree_uv_ofs already computed above
	vec2 uv_yz = world_pos.yz * tex_uv_scale + tree_uv_ofs;
	vec2 uv_xz = world_pos.xz * tex_uv_scale + tree_uv_ofs;
	vec2 uv_xy = world_pos.xy * tex_uv_scale + tree_uv_ofs;

	// Albedo from texture — tints procedural color, doesn't replace it
	vec3 tex_alb_yz = texture(bark_albedo_tex, uv_yz).rgb;
	vec3 tex_alb_xz = texture(bark_albedo_tex, uv_xz).rgb;
	vec3 tex_alb_xy = texture(bark_albedo_tex, uv_xy).rgb;
	vec3 tex_albedo = tex_alb_yz * tri_w.x + tex_alb_xz * tri_w.y + tex_alb_xy * tri_w.z;

	// Normal from texture — unpack and triplanar blend
	vec3 tn_yz = texture(bark_normal_tex, uv_yz).rgb * 2.0 - 1.0;
	vec3 tn_xz = texture(bark_normal_tex, uv_xz).rgb * 2.0 - 1.0;
	vec3 tn_xy = texture(bark_normal_tex, uv_xy).rgb * 2.0 - 1.0;
	vec3 tex_nrm = normalize(tn_yz * tri_w.x + tn_xz * tri_w.y + tn_xy * tri_w.z);

	// Roughness from texture — triplanar blend
	float tr_yz = texture(bark_roughness_tex, uv_yz).r;
	float tr_xz = texture(bark_roughness_tex, uv_xz).r;
	float tr_xy = texture(bark_roughness_tex, uv_xy).r;
	float tex_rough = tr_yz * tri_w.x + tr_xz * tri_w.y + tr_xy * tri_w.z;

	// Blend: procedural provides structure + per-tree variation,
	//        texture provides photographic surface detail
	col = mix(col, col * tex_albedo * 2.2, tex_blend);  // multiply-blend preserves procedural tone
	rough = mix(rough, tex_rough, tex_blend * 0.6);
	vec3 final_normal_perturb = mix(bark_normal_perturb, tex_nrm * 0.4, tex_blend);
	NORMAL = normalize(NORMAL + final_normal_perturb * 2.5);

	// Per-pixel micro-variation: lichen spores, mineral deposits,
	// moisture stains, insect marks — millions of unique shades
	vec2 bark_px = world_pos.xz * 67.3 + world_pos.yy * 3.7;
	float bark_pn = hash2(bark_px) * 0.06 - 0.03;
	float bark_phr = hash2(bark_px + vec2(71.9, 0.0)) * 0.025;
	float bark_phb = hash2(bark_px + vec2(0.0, 53.1)) * 0.025;
	col += vec3(bark_pn + bark_phr, bark_pn, bark_pn + bark_phb);

	ALBEDO = col;
	ROUGHNESS = clamp(rough, 0.0, 1.0);
	METALLIC = 0.0;
	SPECULAR = 0.04;

	// --- Lichen patches: gray-green crusty patches common on NYC park trees ---
	float lichen_season = smoothstep(0.0, 0.8, season_t) * (1.0 - smoothstep(3.0, 3.8, season_t));
	if (lichen_season > 0.01) {
		vec2 lich_uv = puv_yz * tri_w.x + puv_xz * tri_w.y + puv_xy * tri_w.z;
		float lich_noise = fbm(lich_uv * vec2(2.0, 1.5) + tree_var * 10.0, 2);
		float lich_mask = smoothstep(0.55, 0.72, lich_noise) * lichen_season;
		// Only on bark ridges (not in deep furrows) and mid-height
		lich_mask *= furrow * smoothstep(1.0, 3.0, local_h) * smoothstep(8.0, 5.0, local_h);
		if (lich_mask > 0.01) {
			// Gray-green crustose lichen
			vec3 lichen_col = mix(vec3(0.35, 0.42, 0.30), vec3(0.45, 0.48, 0.38), lich_noise);
			ALBEDO = mix(ALBEDO, lichen_col, lich_mask * 0.45);
			ROUGHNESS = mix(ROUGHNESS, 0.92, lich_mask * 0.3);
		}
	}

	// --- Moss at trunk base: more in spring/summer, north-facing ---
	float spring_summer = sn_warm_season(season_t);
	float moss_height = smoothstep(3.0, 0.0, local_h);  // bottom 3m of trunk
	float moss_facing = max(0.0, -world_nrm.z) * 0.5 + max(0.0, -world_nrm.x) * 0.3 + 0.2;
	vec2 moss_uv = puv_yz * tri_w.x + puv_xz * tri_w.y + puv_xy * tri_w.z;
	float moss_noise = fbm(moss_uv * vec2(3.0, 2.0), 2);
	float moss = moss_height * moss_facing * smoothstep(0.35, 0.6, moss_noise) * spring_summer;
	if (moss > 0.01) {
		vec3 moss_col = mix(vec3(0.10, 0.20, 0.06), vec3(0.16, 0.26, 0.08), moss_noise);
		ALBEDO = mix(ALBEDO, moss_col, moss * 0.45);
		ROUGHNESS = mix(ROUGHNESS, 0.95, moss * 0.3);
	}

	// --- Rain: wet bark darkens, gets glossy ---
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.62, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.35, rain_wetness);
		SPECULAR = mix(SPECULAR, 0.28, rain_wetness);
		// Water streaks in furrows — darker wet lines running down bark
		float wet_streak = smoothstep(0.45, 0.20, furrow) * rain_wetness;
		ALBEDO *= mix(1.0, 0.82, wet_streak * 0.6);
		ROUGHNESS = mix(ROUGHNESS, 0.12, wet_streak * 0.4);
		// Wet moss becomes vivid green
		if (moss > 0.01) {
			ALBEDO = mix(ALBEDO, ALBEDO * vec3(0.82, 1.25, 0.78), moss * rain_wetness * 0.4);
		}
	}

	// --- Snow on upward-facing bark and branch crotches ---
	if (snow_cover > 0.01) {
		float upward = max(world_nrm.y, 0.0);
		float snow_noise = hash2(floor(world_pos.xz * 5.0 + world_pos.yy * 3.0));
		float snow_amt = snow_cover * smoothstep(0.3, 0.7, upward + snow_noise * 0.3);
		// Snow collects more in bark furrows (concavities)
		snow_amt += snow_cover * (1.0 - furrow) * upward * 0.15;
		snow_amt = min(snow_amt, 1.0);
		ALBEDO = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_amt * 0.7);
		ROUGHNESS = mix(ROUGHNESS, 0.85, snow_amt);
	}

	// --- Sap runs and resin: dark wet streaks on deciduous trees ---
	// Especially visible in spring when sap flows
	float sap_season = smoothstep(0.0, 0.5, season_t) * (1.0 - smoothstep(1.5, 2.5, season_t));
	if (sap_season > 0.01) {
		vec2 sap_uv = puv_yz * tri_w.x + puv_xz * tri_w.y + puv_xy * tri_w.z;
		float sap_hash = hash2(floor(sap_uv * vec2(2.0, 0.5)) + tree_var * 20.0);
		// Only ~8% of positions show sap runs
		if (sap_hash > 0.92) {
			// Dark glossy streak running downward
			float sap_run = smoothstep(0.92, 0.96, sap_hash) * sap_season;
			ALBEDO *= mix(1.0, 0.72, sap_run * 0.6);
			ROUGHNESS = mix(ROUGHNESS, 0.25, sap_run * 0.4);
			SPECULAR = mix(SPECULAR, 0.30, sap_run * 0.3);
		}
	}

	// Aerial perspective: desaturate + cool shift + haze blend at distance.
	float bark_dist = length(tree_base - INV_VIEW_MATRIX[3].xyz);
	float bark_aerial = smoothstep(60.0, 300.0, bark_dist);
	ALBEDO = apply_aerial(ALBEDO, bark_aerial, 0.30, 0.30, sky_reflect_color);
}
