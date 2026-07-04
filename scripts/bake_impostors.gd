# bake_impostors.gd — octahedral impostor atlas baker (Godot-community / AAA SOP).
#
# Renders each hemisphere-octahedral view of a MATERIALISED tree mesh (the exact
# tree_leaf / tree_bark ShaderMaterials the in-game MMIs use) with `bake_mode` set
# so the requested channel is emitted UNSHADED via EMISSION, then packs the views
# into a 2048² atlas. Lighting is applied at RUNTIME by tree_impostor.gdshader from
# the normal atlas — so the atlas is true albedo, NOT baked-lit (kills the
# double-lit / time-of-day-mismatch bug class that sank the old hand-rolled baker).
#
# The cell↔direction convention matches addons/Imposter ImpostorShader.gdshader
# (OctaUtils.octa_uv_to_world for the direction, look_at with UP, tile (fx,fy) at
# atlas region [fx/F..]×[fy/F..]), so the adapted runtime shader decodes correctly.
#
# Run via tree_builder's `--bake-impostors=london_plane` flag (see _run_impostor_bake).
# Drives a SubViewport parented under park_loader (which is in the scene tree) so
# RenderingServer.frame_post_draw pumps; no editor / EditorInterface needed.
#
# No `class_name` on purpose: it is preloaded by tree_builder (a fresh class_name
# added outside the editor isn't in the global class cache, so referencing it by
# name fails to parse until an editor scan). OctaUtils (the addon's class_name) is
# already cached, so it is referenced directly.
extends RefCounted

const FRAMES := 16                      # views per axis (community/AAA default; 16²=256)
const ATLAS_RES := 2048                 # atlas resolution (community default)
const CELL := ATLAS_RES / FRAMES        # 128 px per view
const SS := 4                           # supersample factor per cell (AA then downscale)
const OUT_DIR := "res://textures/impostors/"
# Summer phase for a full-canopy albedo bake (season_t cycles 0..4). Verified
# visually against the in-game summer canopy at validation time.
const SUMMER_SEASON := 2.0
# Winter (Jan) phase for the bare-crown bake. At 3.5 london_plane's phenology
# canopy = min(grow,shed) = 0, so leaf_density collapses to WINTER_RETENTION (0.05):
# baking with card_keep=-1 lets the live leaf shader's own per-card drop thin the
# crown to a near-bare skeleton + a few marcescent sprigs (no stochastic runtime
# discard — the SHAPE is real geometry, which is why this replaces the reverted
# per-fragment thinning that crawled in motion). See [[project_impostor_system_rebuilt]].
const WINTER_SEASON := 3.5
# Per-card keep-fraction used DURING the bake (tree_leaf bake_density). 0.1 drops
# ~90% of cards so the baked atlas coverage MATCHES the see-through live lod0 mesh at
# the handoff (a full crown projects solid at bake res). Matching lod0 is the design:
# the impostor is derived from lod0 and must read identically so the lod0->impostor
# handoff is seamless. -1 = no drop (full crown). DO NOT raise to solid — a fuller
# impostor pops against the lod0 it replaces (the per-tier match the bug is NOT about;
# see [[project_tree_lod_disappearance_bug]] — the residual is per-INSTANCE).
const BAKE_DENSITY := 0.1

var _loader  # park_loader — in the scene tree; bake viewport parents here

# --- Sun-visibility (directional-occlusion) channel -------------------------
# Baked so the far tier's DIRECT light responds to the real sun direction at
# runtime. The static AO-on-direct fake (a801c20) was only right at its
# calibration hours — measured 2026-07-02: impostor/lod0 luminance 1.08x at
# 13h/16h/18h but 0.29x at 9h (pow(AO 0.42, 1.5) ~= 0.27 crushing the crown
# whenever N.L is already low). Method: per octa cell, render the tree lit by
# a probe DirectionalLight from K directions, shadows ON and OFF; the per-pixel
# ON/OFF ratio is pure geometric sun-visibility (N.L and the BRDF cancel
# exactly). A least-squares L1 fit (mean + bent vector) compresses the K
# ratios into one RGBA texel:
#   R = c0 (mean visibility), GBA = c_vec * 0.5 + 0.5 (bake-object space)
# and the runtime evaluates clamp(c0 + dot(c_vec, sun_obj), 0, 1) in light().
# The fit runs on the GPU (one canvas pass over a Texture2DArray of the probe
# renders). The hdr_2d composite viewport reads back LINEAR (verified
# 2026-07-02 against known constants), so the vis atlas is stored linear —
# the runtime samples it WITHOUT source_color.
# Probe energy: LIGHT_COLOR carries x PI, so a facing white-lambert pixel
# renders ~= energy; burley's grazing FdV*FdL can reach ~1.3x. 0.6 keeps every
# pixel below clipping (a clipped shadows-OFF pass would inflate the ratio).
const VIS_LIGHT_ENERGY := 0.6
const VIS_OFF_MIN := 0.015      # linear floor: below it the texel faces away -> vis 0 (occluded)

var _vis_dirs: Array[Vector3] = []   # K probe sun directions (bake-object space)
var _vis_gmat := PackedVector4Array()  # per-direction LS weights: c += gmat[k] * V_k

func _init(loader) -> void:
	_loader = loader
	_build_vis_basis()

# Probe directions: zenith + 4 @ 40deg elevation + 4 @ 12deg (NYC sun spans
# 0-73deg; low-elevation probes anchor the sunrise/sunset end of the fit).
# The LS system vis(s) ~= c0 + c.s over these dirs has cond(XtX) ~= 21 (fine);
# fit of V==1 returns exactly (1, 0-vec), fit of V=max(0,s.y) returns (0, +Y).
func _build_vis_basis() -> void:
	_vis_dirs.clear()
	_vis_dirs.append(Vector3.UP)
	for ring in [[40.0, 0.0], [12.0, 0.5]]:
		var el: float = deg_to_rad(ring[0])
		for i in 4:
			var az: float = TAU * (float(i) + ring[1]) / 4.0
			_vis_dirs.append(Vector3(cos(el) * sin(az), sin(el), cos(el) * cos(az)).normalized())
	# G = (XtX)^-1 Xt with X rows [1, sx, sy, sz]; c = sum_k gmat[k] * V_k.
	var rows := []
	for d in _vis_dirs:
		rows.append([1.0, d.x, d.y, d.z])
	var xtx := []
	for r in 4:
		xtx.append([0.0, 0.0, 0.0, 0.0])
	for row in rows:
		for r in 4:
			for c in 4:
				xtx[r][c] += row[r] * row[c]
	var inv := _mat4_inverse(xtx)
	_vis_gmat.clear()
	for row in rows:
		var g := Vector4.ZERO
		for r in 4:
			var v := 0.0
			for c in 4:
				v += inv[r][c] * row[c]
			g[r] = v
		_vis_gmat.append(g)

# Gauss-Jordan 4x4 inverse (no engine mat4-with-inverse type for plain arrays).
func _mat4_inverse(m: Array) -> Array:
	var a := []
	for r in 4:
		a.append([m[r][0], m[r][1], m[r][2], m[r][3],
				1.0 if r == 0 else 0.0, 1.0 if r == 1 else 0.0,
				1.0 if r == 2 else 0.0, 1.0 if r == 3 else 0.0])
	for col in 4:
		var piv := col
		for r in range(col + 1, 4):
			if absf(a[r][col]) > absf(a[piv][col]):
				piv = r
		var tmp = a[col]; a[col] = a[piv]; a[piv] = tmp
		var pv: float = a[col][col]
		for c in 8:
			a[col][c] /= pv
		for r in 4:
			if r == col:
				continue
			var f: float = a[r][col]
			for c in 8:
				a[r][c] -= f * a[col][c]
	var out := []
	for r in 4:
		out.append([a[r][4], a[r][5], a[r][6], a[r][7]])
	return out

# LS-fit canvas shader: layers alternate shadows-ON / shadows-OFF per probe
# direction; output = (c0, c_vec*0.5+0.5). Probe readbacks are sRGB-encoded
# 8-bit (the known bake-viewport gotcha), hence the s2l decode before the ratio.
const _VIS_FIT_SHADER := "
shader_type canvas_item;
render_mode blend_disabled;
uniform sampler2DArray probes : filter_nearest;
uniform vec4 gmat[16];
uniform int n_dirs = 9;
uniform float off_min = 0.015;
float s2l(float c) { return c <= 0.04045 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4); }
void fragment() {
	vec4 c = vec4(0.0);
	for (int k = 0; k < n_dirs; k++) {
		float on  = s2l(texture(probes, vec3(UV, float(k * 2))).r);
		float off = s2l(texture(probes, vec3(UV, float(k * 2 + 1))).r);
		float v = off > off_min ? clamp(on / off, 0.0, 1.0) : 0.0;
		c += gmat[k] * v;
	}
	COLOR = vec4(clamp(c.x, 0.0, 1.0), clamp(c.yzw, vec3(-1.0), vec3(1.0)) * 0.5 + 0.5);
}
"

# Bake one species-size tier. Returns a metadata dict for the manifest.
# card_keep overrides BAKE_DENSITY per call: the default thins a SUPERIMPOSED
# all-variants crown, but a SINGLE-variant bake has no superposition to undo, so
# the caller passes -1 (no drop) there — else the 90%-drop empties the crown to a
# near-invisible 2-6% atlas (the cpw_000 decimated/invisible impostors, 2026-06-24).
func bake_tier(tier_key: String, meshes: Array, world_height: float, card_keep: float = BAKE_DENSITY, season_t: float = SUMMER_SEASON, file_suffix: String = "", bake_vis: bool = false) -> Dictionary:
	var aabb := _combined_aabb(meshes)
	var center := aabb.get_center()
	var diag: float = aabb.size.length()
	if diag < 0.001:
		diag = maxf(aabb.size.x, maxf(aabb.size.y, aabb.size.z))

	# --- bake viewport: unlit, linear-tonemap, transparent so coverage→alpha ---
	var vp := SubViewport.new()
	vp.size = Vector2i(CELL * SS, CELL * SS)
	vp.transparent_bg = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.msaa_3d = Viewport.MSAA_4X
	var world := World3D.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0, 0, 0)
	env.ambient_light_energy = 0.0
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 1.0
	env.tonemap_white = 1.0
	world.environment = env
	vp.world_3d = world
	_loader.add_child(vp)

	# --- holder: one MultiMesh (1 instance, london_plane custom data) per surface mesh,
	#     recentred so the model sits at the world origin ---
	var holder := Node3D.new()
	holder.position = -center
	vp.add_child(holder)
	var cd := Color(9.0 / 13.0, 0.5, 0.0, 0.5)  # london_plane summer, neutral jitter (tree_builder.gd:741)
	for m: Mesh in meshes:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = m
		mm.instance_count = 1
		mm.set_instance_transform(0, Transform3D.IDENTITY)
		mm.set_instance_custom_data(0, cd)
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		holder.add_child(mmi)

	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = diag
	cam.near = 0.01
	cam.far = diag * 4.0
	cam.current = true
	vp.add_child(cam)

	var saved := _push_bake_globals(season_t)
	# Thin cluster cards so the baked coverage matches the see-through live mesh at
	# the handoff distance (a full crown projects solid at bake res). Harmless on
	# bark (no such uniform).
	var _set_n := 0
	for m: Mesh in meshes:
		for si in m.get_surface_count():
			var mt := m.surface_get_material(si)
			if mt is ShaderMaterial:
				var sm := mt as ShaderMaterial
				var is_leaf: bool = sm.shader != null and "leaf" in sm.shader.resource_path
				if is_leaf:
					sm.set_shader_parameter("bake_density", card_keep)
					_set_n += 1
	print("  bake_density=%.2f applied to %d leaf surfaces" % [card_keep, _set_n])

	var atlases := {}
	for ch in [["albedo", 1], ["normal", 2], ["orm", 3]]:
		_set_bake_mode(meshes, int(ch[1]))
		var atlas := Image.create(ATLAS_RES, ATLAS_RES, false, Image.FORMAT_RGBA8)
		atlas.fill(Color(0, 0, 0, 0))
		for fy in FRAMES:
			for fx in FRAMES:
				var uv := Vector2(float(fx) / float(FRAMES - 1), float(fy) / float(FRAMES - 1))
				var dir: Vector3 = OctaUtils.octa_uv_to_world(uv, false)
				_aim_camera(cam, dir, diag)
				vp.render_target_update_mode = SubViewport.UPDATE_ONCE
				await RenderingServer.frame_post_draw
				var cell_img := vp.get_texture().get_image()
				if SS > 1:
					cell_img.resize(CELL, CELL, Image.INTERPOLATE_LANCZOS)
				atlas.blit_rect(cell_img, Rect2i(0, 0, CELL, CELL), Vector2i(fx * CELL, fy * CELL))
		var path: String = OUT_DIR + "%s%s_%s.png" % [tier_key, file_suffix, ch[0]]
		atlas.save_png(ProjectSettings.globalize_path(path))
		atlases[ch[0]] = path
		print("  Impostor bake: %s %s -> %s" % [tier_key, ch[0], path])

	# Sun-visibility channel (summer bakes only — a near-bare winter crown barely
	# self-occludes, and the runtime blends vis toward 1 as the canopy sheds).
	var vis_path := ""
	if bake_vis:
		vis_path = await _bake_vis_channel(vp, cam, meshes, diag, tier_key, file_suffix)

	_set_bake_mode(meshes, 0)
	_pop_bake_globals(saved)
	vp.queue_free()

	# scale / aabb_max per the addon export_scene convention (ImpostorShader uniforms).
	# position_offset = +center lifts the billboard to canopy height — the SIGN that,
	# inverted, buried the whole far tier under the terrain in the prior system.
	var scale_instance := diag / 2.0
	# aabb_max = 0: the ORTHOGRAPHIC bake already captures the true silhouette AT THE
	# PIVOT, so the addon's forward depth-push (diag/4) only inflates the card (+7-10%
	# size at the handoff). The runtime also pins this to 0 defensively; emit 0 here so
	# the manifest matches what is actually used.
	return {
		"tier": tier_key, "frames": FRAMES, "atlas_res": ATLAS_RES, "is_full_sphere": false,
		"scale": scale_instance, "aabb_max": 0.0,
		"position_offset": [center.x, center.y, center.z],
		"world_height": world_height, "diag": diag,
		"albedo": atlases.get("albedo", ""), "normal": atlases.get("normal", ""),
		"orm": atlases.get("orm", ""), "vis": vis_path,
	}

# Bake the sun-visibility atlas for one tier (see the header block above the
# basis builder). Reuses the caller's bake viewport/camera (materials already
# have bake_density applied, so the vis crown geometry matches the other
# channels texel-for-texel); adds a probe light + a GPU LS-fit composite pass.
func _bake_vis_channel(vp: SubViewport, cam: Camera3D, meshes: Array, diag: float, tier_key: String, file_suffix: String) -> String:
	_set_bake_mode(meshes, 4)
	var light := DirectionalLight3D.new()
	light.light_energy = VIS_LIGHT_ENERGY
	light.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	light.directional_shadow_max_distance = diag * 4.0
	vp.add_child(light)

	# Composite viewport: hdr_2d float target -> LINEAR readback (verified), so
	# the fit coefficients are stored linear end-to-end.
	var cvp := SubViewport.new()
	cvp.disable_3d = true
	cvp.use_hdr_2d = true
	cvp.transparent_bg = true
	cvp.size = vp.size
	cvp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	var fit_sh := Shader.new()
	fit_sh.code = _VIS_FIT_SHADER
	var cmat := ShaderMaterial.new()
	cmat.shader = fit_sh
	cmat.set_shader_parameter("gmat", _vis_gmat)
	cmat.set_shader_parameter("n_dirs", _vis_dirs.size())
	cmat.set_shader_parameter("off_min", VIS_OFF_MIN)
	var rect := ColorRect.new()
	rect.size = Vector2(vp.size)
	rect.material = cmat
	cvp.add_child(rect)
	_loader.add_child(cvp)

	var atlas := Image.create(ATLAS_RES, ATLAS_RES, false, Image.FORMAT_RGBA8)
	# Background texels = (c0 0, vec 0) -> vis 0 everywhere; never sampled
	# through the alpha discard, encoded value just needs to be valid.
	atlas.fill(Color(0.0, 0.5, 0.5, 0.5))
	for fy in FRAMES:
		for fx in FRAMES:
			var uv := Vector2(float(fx) / float(FRAMES - 1), float(fy) / float(FRAMES - 1))
			var dir: Vector3 = OctaUtils.octa_uv_to_world(uv, false)
			_aim_camera(cam, dir, diag)
			var layers: Array[Image] = []
			for d: Vector3 in _vis_dirs:
				var up := Vector3.UP
				if absf(d.y) > 0.999:
					up = Vector3.BACK
				light.look_at_from_position(d * diag * 2.0, Vector3.ZERO, up)  # shines along -d
				for shadow_on in [true, false]:
					light.shadow_enabled = shadow_on
					vp.render_target_update_mode = SubViewport.UPDATE_ONCE
					await RenderingServer.frame_post_draw
					layers.append(vp.get_texture().get_image())
			var ta := Texture2DArray.new()
			ta.create_from_images(layers)
			cmat.set_shader_parameter("probes", ta)
			cvp.render_target_update_mode = SubViewport.UPDATE_ONCE
			await RenderingServer.frame_post_draw
			var cell_img := cvp.get_texture().get_image()   # RGBAH, linear
			if SS > 1:
				cell_img.resize(CELL, CELL, Image.INTERPOLATE_LANCZOS)
			cell_img.convert(Image.FORMAT_RGBA8)             # linear quantise (no sRGB)
			atlas.blit_rect(cell_img, Rect2i(0, 0, CELL, CELL), Vector2i(fx * CELL, fy * CELL))
	light.queue_free()
	cvp.queue_free()
	var path: String = OUT_DIR + "%s%s_vis.png" % [tier_key, file_suffix]
	atlas.save_png(ProjectSettings.globalize_path(path))
	print("  Impostor bake: %s vis (%d probe dirs) -> %s" % [tier_key, _vis_dirs.size(), path])
	return path

func _combined_aabb(meshes: Array) -> AABB:
	var out := AABB()
	var first := true
	for m: Mesh in meshes:
		var a: AABB = m.get_aabb()
		if first:
			out = a
			first = false
		else:
			out = out.merge(a)
	return out

func _aim_camera(cam: Camera3D, dir: Vector3, diag: float) -> void:
	var d := dir.normalized()
	cam.position = d * (diag * 1.5)
	var up := Vector3.UP
	if absf(d.y) > 0.999:
		up = Vector3.BACK   # pole: avoid degenerate look_at (matches addon prepare_scene)
	cam.look_at(Vector3.ZERO, up)

func _set_bake_mode(meshes: Array, mode: int) -> void:
	for m: Mesh in meshes:
		for si in m.get_surface_count():
			var mat := m.surface_get_material(si)
			if mat is ShaderMaterial:
				(mat as ShaderMaterial).set_shader_parameter("bake_mode", mode)

# Force a clean, windless, snowless, haze-free bake at the requested SEASON
# regardless of the app's current time-of-day; restore afterwards so a non-quitting
# caller is safe. season_t is supplied per-call (summer = full crown, winter = bare).
const _BAKE_GLOBALS := {
	"snow_cover": 0.0,
	"rain_wetness": 0.0,
	"wind_vec": Vector2.ZERO,
	"player_world_pos": Vector3(0, 1000, 0),
}

func _push_bake_globals(season_t: float) -> Dictionary:
	# global_shader_parameter_get is editor-only, and this bake run quits afterwards,
	# so we just SET the bake conditions and skip save/restore.
	RenderingServer.global_shader_parameter_set("season_t", season_t)
	for k in _BAKE_GLOBALS:
		RenderingServer.global_shader_parameter_set(k, _BAKE_GLOBALS[k])
	return {}

func _pop_bake_globals(_saved: Dictionary) -> void:
	pass
