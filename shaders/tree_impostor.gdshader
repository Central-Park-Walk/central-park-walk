shader_type spatial;

// Runtime-lit octahedral impostor (far tree LOD). Adapted from
// addons/Imposter/imposter/materials/shaders/ImpostorShader.gdshader (the proven
// Godot-community / Brucks octahedral billboard: 3-nearest-frame blend + virtual-
// plane parallax). Changes vs the addon:
//   * NO `impostor_brightness` global fudge — the albedo atlas is baked UNLIT
//     (scripts/bake_impostors.gd, bake_mode), so Godot lights it here via the
//     normal atlas + diffuse_burley. This kills the double-lit / time-of-day
//     mismatch bug class that sank the prior hand-rolled baker.
//   * `lod_fade_in` dither so the impostor crossfades into _lod1 over the same
//     band the mesh tiers dither out (tree_builder sets it per instance group).
// Atlases are produced by scripts/bake_impostors.gd with a matching cell/direction
// convention (OctaUtils.octa_uv_to_world), so this decoder lines up by construction.

render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec4 albedo : source_color = vec4(1, 1, 1, 1);
uniform float specular = 0.1f;                 // foliage: low spec so diffuse dominates
uniform float metallic = 0.0f;
uniform float roughness : hint_range(0.0f, 1.0f) = 1.0f;

uniform sampler2D imposterTextureAlbedo : source_color;
uniform sampler2D imposterTextureNormal : hint_normal;
uniform sampler2D imposterTextureDepth : hint_default_white;
// source_color: the bake viewport sRGB-encodes EMISSION on readback (same as the
// albedo atlas), so the linear AO/roughness the leaf shader emitted is stored sRGB.
// Decoding it here recovers the linear AO the mesh actually applies (~0.42), not the
// sRGB-inflated 0.71 a linear sampler would read (which would under-darken).
uniform sampler2D imposterTextureOrm : source_color, hint_default_white;

uniform vec2 imposterFrames = vec2(16.0f, 16.0f);
uniform vec3 positionOffset = vec3(0.0f);
uniform bool isFullSphere = false;             // foliage = hemisphere
uniform float alpha_clamp = 0.5f;
uniform float scale = 1.0f;
uniform float depth_scale : hint_range(0, 1) = 0.0f;
uniform float normalmap_depth : hint_range(-5, 5) = 1.0f;
uniform float aabb_max = 1.0;

// LOD crossfade-in band (begin, end) in metres. The impostor dithers IN over this
// band as the camera approaches, complementary to _lod1's dither-out. vec2(0,0) off.
uniform vec2 lod_fade_in = vec2(0.0, 0.0);
// Player camera world pos (pushed from main.gd) — same source the mesh tiers use,
// so the crossfade discards consistently across shadow/reflection passes.
global uniform vec3 player_world_pos;

#include "res://shaders/include/lod_dither.gdshaderinc"

varying vec2 uv_frame1;
varying vec2 xy_frame1;
varying flat vec2 frame1;
varying flat vec3 frame1_normal;
varying vec2 uv_frame2;
varying vec2 xy_frame2;
varying flat vec2 frame2;
varying flat vec3 frame2_normal;
varying vec2 uv_frame3;
varying vec2 xy_frame3;
varying flat vec2 frame3;
varying flat vec3 frame3_normal;
varying vec4 quad_blend_weights;
varying vec3 v_inst_pos;

vec2 VecToSphereOct(vec3 pivotToCamera) {
	vec3 octant = sign(pivotToCamera);
	float sum = dot(pivotToCamera, octant);
	vec3 octahedron = pivotToCamera / sum;
	if (octahedron.y < 0.0f) {
		vec3 absolute = abs(octahedron);
		octahedron.xz = octant.xz * vec2(1.0f - absolute.z, 1.0f - absolute.x);
	}
	return octahedron.xz;
}

vec2 VecToHemiSphereOct(vec3 pivotToCamera) {
	pivotToCamera.y = max(pivotToCamera.y, 0.001);
	pivotToCamera = normalize(pivotToCamera);
	vec3 octant = sign(pivotToCamera);
	float sum = dot(pivotToCamera, octant);
	vec3 octahedron = pivotToCamera / sum;
	return vec2(octahedron.x + octahedron.z, octahedron.z - octahedron.x);
}

vec2 VectorToGrid(vec3 vec) {
	if (isFullSphere) { return VecToSphereOct(vec); }
	else { return VecToHemiSphereOct(vec); }
}

vec3 OctaSphereEnc(vec2 coord) {
	coord = (coord - 0.5) * 2.0;
	vec3 position = vec3(coord.x, 0.0f, coord.y);
	vec2 absolute = abs(position.xz);
	position.y = 1.0f - absolute.x - absolute.y;
	if (position.y < 0.0f) {
		position.xz = sign(position.xz) * vec2(1.0f - absolute.y, 1.0f - absolute.x);
	}
	return position;
}

vec3 OctaHemiSphereEnc(vec2 coord) {
	vec3 position = vec3(coord.x - coord.y, 0.0f, -1.0 + coord.x + coord.y);
	vec2 absolute = abs(position.xz);
	position.y = 1.0f - absolute.x - absolute.y;
	return position;
}

vec3 GridToVector(vec2 coord) {
	if (isFullSphere) { return OctaSphereEnc(coord); }
	else { return OctaHemiSphereEnc(coord); }
}

vec3 FrameXYToRay(vec2 frame, vec2 frameCountMinusOne) {
	vec2 f = (frame.xy / frameCountMinusOne);
	vec3 vec = GridToVector(f);
	vec = normalize(vec);
	return vec;
}

vec3 SpriteProjection(vec3 pivotToCameraRayLocal, vec2 size, vec2 loc_uv) {
	vec3 z = normalize(pivotToCameraRayLocal);
	vec3 x, y;
	vec3 up = vec3(0, 1, 0);
	if (abs(z.y) > 0.999f) { up = vec3(0, 0, -1); }
	x = normalize(cross(up, z));
	y = normalize(cross(x, z));
	loc_uv -= vec2(0.5, 0.5);
	vec2 uv = (loc_uv) * 2.0;
	vec3 newX = x * uv.x;
	vec3 newY = y * uv.y;
	vec2 vecSize = size * 0.5;
	newX *= vecSize.x;
	newY *= vecSize.y;
	return newX + newY;
}

vec4 quadBlendWieghts(vec2 coords) {
	vec4 res;
	res.x = min(1.0f - coords.x, 1.0f - coords.y);
	res.y = abs(coords.x - coords.y);
	res.z = min(coords.x, coords.y);
	res.w = ceil(coords.x - coords.y);
	return res;
}

vec2 virtualPlaneUV(vec3 plane_normal, vec3 plane_x, vec3 plane_y, vec3 pivotToCameraRay, vec3 vertexToCameraRay, float size) {
	plane_normal = normalize(plane_normal);
	plane_x = normalize(plane_x);
	plane_y = normalize(plane_y);
	float projectedNormalRayLength = dot(plane_normal, pivotToCameraRay);
	float projectedVertexRayLength = dot(plane_normal, vertexToCameraRay);
	float offsetLength = projectedNormalRayLength / projectedVertexRayLength;
	vec3 offsetVector = vertexToCameraRay * offsetLength - pivotToCameraRay;
	vec2 duv = vec2(dot(plane_x, offsetVector), dot(plane_y, offsetVector));
	duv /= 2.0 * size;
	duv += 0.5;
	return duv;
}

void calcuateXYbasis(vec3 plane_normal, out vec3 plane_x, out vec3 plane_y) {
	vec3 up = vec3(0, 1, 0);
	if (abs(plane_normal.y) > 0.999f) { up = vec3(0, 0, 1); }
	plane_x = normalize(cross(plane_normal, up));
	plane_y = normalize(cross(plane_x, plane_normal));
}

vec3 projectOnPlaneBasis(vec3 ray, vec3 plane_normal, vec3 plane_x, vec3 plane_y) {
	return normalize(vec3(dot(plane_x, ray), dot(plane_y, ray), dot(plane_normal, ray)));
}

void vertex() {
	v_inst_pos = MODEL_MATRIX[3].xyz;
	vec2 framesMinusOne = imposterFrames - vec2(1);
	vec3 cameraPos_WS = (INV_VIEW_MATRIX * vec4(vec3(0), 1.0)).xyz;
	vec3 cameraPos_OS = (inverse(MODEL_MATRIX) * vec4(cameraPos_WS, 1.0)).xyz;
	vec3 pivotToCameraRay = (cameraPos_OS) * 10.0;
	vec3 pivotToCameraDir = normalize(cameraPos_OS);

	vec2 grid = VectorToGrid(pivotToCameraDir);
	grid = clamp((grid + 1.0) * 0.5, vec2(0, 0), vec2(1, 1));
	grid *= framesMinusOne;
	grid = clamp(grid, vec2(0), vec2(framesMinusOne));
	vec2 gridFloor = min(floor(grid), framesMinusOne);
	vec2 gridFract = fract(grid);

	vec2 size = vec2(2.0) * scale;
	vec3 projected = SpriteProjection(pivotToCameraDir, size, UV);
	vec3 vertexToCameraRay = (pivotToCameraRay - (projected));
	vec3 vertexToCameraDir = normalize(vertexToCameraRay);

	frame1 = gridFloor;
	quad_blend_weights = quadBlendWieghts(gridFract);
	vec3 projectedQuadADir = FrameXYToRay(frame1, framesMinusOne);

	frame2 = clamp(frame1 + mix(vec2(0, 1), vec2(1, 0), quad_blend_weights.w), vec2(0, 0), framesMinusOne);
	vec3 projectedQuadBDir = FrameXYToRay(frame2, framesMinusOne);

	frame3 = clamp(frame1 + vec2(1), vec2(0, 0), framesMinusOne);
	vec3 projectedQuadCDir = FrameXYToRay(frame3, framesMinusOne);

	frame1_normal = (MODELVIEW_MATRIX * vec4(projectedQuadADir, 0)).xyz;
	frame2_normal = (MODELVIEW_MATRIX * vec4(projectedQuadBDir, 0)).xyz;
	frame3_normal = (MODELVIEW_MATRIX * vec4(projectedQuadCDir, 0)).xyz;

	vec3 plane_x1, plane_y1, plane_x2, plane_y2, plane_x3, plane_y3;
	calcuateXYbasis(projectedQuadADir, plane_x1, plane_y1);
	uv_frame1 = virtualPlaneUV(projectedQuadADir, plane_x1, plane_y1, pivotToCameraRay, vertexToCameraRay, scale);
	xy_frame1 = projectOnPlaneBasis(-vertexToCameraDir, projectedQuadADir, plane_x1, plane_y1).xy;

	calcuateXYbasis(projectedQuadBDir, plane_x2, plane_y2);
	uv_frame2 = virtualPlaneUV(projectedQuadBDir, plane_x2, plane_y2, pivotToCameraRay, vertexToCameraRay, scale);
	xy_frame2 = projectOnPlaneBasis(-vertexToCameraDir, projectedQuadBDir, plane_x2, plane_y2).xy;

	calcuateXYbasis(projectedQuadCDir, plane_x3, plane_y3);
	uv_frame3 = virtualPlaneUV(projectedQuadCDir, plane_x3, plane_y3, pivotToCameraRay, vertexToCameraRay, scale);
	xy_frame3 = projectOnPlaneBasis(-vertexToCameraDir, projectedQuadCDir, plane_x3, plane_y3).xy;

	VERTEX.xyz = projected + positionOffset;
	VERTEX.xyz += pivotToCameraDir * aabb_max;

	NORMAL = normalize(pivotToCameraDir);
	TANGENT = normalize(cross(NORMAL, vec3(0.0, 1.0, 0.0)));
	BINORMAL = normalize(cross(TANGENT, NORMAL));
}

vec4 blenderColors(vec2 uv_1, vec2 uv_2, vec2 uv_3, vec4 grid_weights, sampler2D atlasTexture) {
	vec4 quad_a = textureLod(atlasTexture, uv_1, 0.0f);
	vec4 quad_b = textureLod(atlasTexture, uv_2, 0.0f);
	vec4 quad_c = textureLod(atlasTexture, uv_3, 0.0f);
	return quad_a * grid_weights.x + quad_b * grid_weights.y + quad_c * grid_weights.z;
}

vec3 normal_from_normalmap(vec4 normalTex, vec3 tangent, vec3 binormal, vec3 f_norm) {
	vec3 normalmap;
	normalmap.xy = normalTex.xy * 2.0 - 1.0;
	normalmap.z = sqrt(max(0.0, 1.0 - dot(normalmap.xy, normalmap.xy)));
	normalmap = normalize(normalmap);
	return normalize(tangent * normalmap.x + binormal * normalmap.y + f_norm * normalmap.z);
}

vec3 blendedNormals(vec2 uv_1, vec3 f1_n, vec2 uv_2, vec3 f2_n, vec2 uv_3, vec3 f3_n,
		vec3 tangent, vec3 binormal, vec4 grid_weights, sampler2D atlasTexture) {
	vec4 quad_a = textureLod(atlasTexture, uv_1, 0.0f);
	vec4 quad_b = textureLod(atlasTexture, uv_2, 0.0f);
	vec4 quad_c = textureLod(atlasTexture, uv_3, 0.0f);
	vec3 norm1 = normal_from_normalmap(quad_a, tangent, binormal, f1_n);
	vec3 norm2 = normal_from_normalmap(quad_b, tangent, binormal, f2_n);
	vec3 norm3 = normal_from_normalmap(quad_c, tangent, binormal, f3_n);
	return normalize(norm1 * grid_weights.x + norm2 * grid_weights.y + norm3 * grid_weights.z);
}

vec2 recalculateUV(vec2 uv_f, vec2 frame, vec2 xy_f, vec2 frame_size, float d_scale, sampler2D depthTexture) {
	uv_f = clamp(uv_f, vec2(0), vec2(1));
	vec2 uv_quad = frame_size * (frame + uv_f);
	vec4 n_depth = (textureLod(depthTexture, uv_quad, 0));
	uv_f = xy_f * (0.5 - n_depth.r) * d_scale + uv_f;
	uv_f = clamp(uv_f, vec2(0), vec2(1));
	uv_f = frame_size * (frame + uv_f);
	return clamp(uv_f, vec2(0), vec2(1));
}

void fragment() {
	// LOD crossfade-in: dither IN over the band where _lod1 dithers out.
	if (lod_fade_in.y > 0.0) {
		float d = length(v_inst_pos - player_world_pos);
		if (d < lod_fade_in.y) {
			if (lod_dither_discard(d, lod_fade_in.x, lod_fade_in.y, FRAGCOORD.xy, true)) discard;
		}
	}

	vec2 quad_size = vec2(1.0f) / imposterFrames;
	vec2 uv_f1 = recalculateUV(uv_frame1, frame1, xy_frame1, quad_size, depth_scale, imposterTextureDepth);
	vec2 uv_f2 = recalculateUV(uv_frame2, frame2, xy_frame2, quad_size, depth_scale, imposterTextureDepth);
	vec2 uv_f3 = recalculateUV(uv_frame3, frame3, xy_frame3, quad_size, depth_scale, imposterTextureDepth);

	vec4 baseTex = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureAlbedo);
	vec4 ormTex = blenderColors(uv_f1, uv_f2, uv_f3, quad_blend_weights, imposterTextureOrm);
	vec3 normalTex = blendedNormals(uv_f1, frame1_normal, uv_f2, frame2_normal, uv_f3, frame3_normal,
			TANGENT, BINORMAL, quad_blend_weights, imposterTextureNormal);

	// Runtime-lit: albedo is true (unlit) albedo; Godot lights it via NORMAL below.
	ALBEDO = baseTex.rgb * albedo.rgb;
	NORMAL = normalTex.xyz;

	// Coverage as an opaque scissor (foliage at distance reads solid).
	ALPHA = float(baseTex.a > alpha_clamp);
	ALPHA_SCISSOR_THRESHOLD = 0.5;

	METALLIC = ormTex.b * metallic;
	SPECULAR = specular;
	ROUGHNESS = ormTex.g * roughness;

	// Crown-interior ambient occlusion, baked into the ORM red channel
	// (bake_impostors.gd, bake_mode 3). Applied ambient-only — exactly as the
	// mesh leaf shader does (AO_LIGHT_AFFECT = 0) — so the far tier stops reading
	// ~1.5x too bright vs lod0/lod1 without dimming the direct-sun side. Defaults
	// to 1.0 (no occlusion) when no ORM atlas is bound (hint_default_white).
	AO = ormTex.r;
	AO_LIGHT_AFFECT = 0.0;
}
