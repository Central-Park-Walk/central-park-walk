extends Node

# Godot-side impostor albedo baker.
#
# Renders each tree GLB through the runtime leaf + bark shaders at 8×8
# hemisphere angles and saves the result as the albedo atlas PNG. This is
# approach #1 from the plan: bake from the runtime shader itself so there
# is zero color drift between LOD0 and the impostor.
#
# The Blender bake (scripts/bake_impostors.py) is still the source of truth
# for the normal and depth atlases — this tool overwrites only the `_albedo`
# images. Frame layout (8×8 octahedral hemisphere, orthographic, radius×2
# camera distance) matches bake_impostors.py exactly so the three atlas
# channels stay aligned.
#
# Launch:
#   Godot_v4.6.1-stable_linux.x86_64 --path . res://scenes/impostor_bake.tscn \
#     --resolution 512x512
#   # Optional filter: add `--only=birch` (or any species name) to the end.

const FRAME_SIZE := 8
const ATLAS_RES := 2048
const FRAME_RES := ATLAS_RES / FRAME_SIZE     # 256
const SUPERSAMPLE := 2                         # render 2× then downsample → cleaner edges
const FRAME_RES_BAKE := FRAME_RES * SUPERSAMPLE
const OUT_DIR := "res://textures/impostors/"
const TREE_DIR := "res://models/trees/"

# Species metadata. Keep this in sync with tree_builder.gd (leaf_tints,
# bark_colors, bark_style resolution) and tree_species.gdshaderinc (sp_idx).
const SPECIES_INFO := {
	"birch":         {"sp_idx": 3,  "tint": Vector3(0.34, 0.52, 0.22), "bark": Color(0.80, 0.76, 0.68), "bstyle": 1, "evergreen": 0.0},
	"callery_pear":  {"sp_idx": 7,  "tint": Vector3(0.28, 0.48, 0.18), "bark": Color(0.42, 0.36, 0.28), "bstyle": 4, "evergreen": 0.0},
	"cathedral_elm": {"sp_idx": 2,  "tint": Vector3(0.24, 0.42, 0.15), "bark": Color(0.30, 0.25, 0.18), "bstyle": 0, "evergreen": 0.0},
	"cherry":        {"sp_idx": 11, "tint": Vector3(0.30, 0.50, 0.20), "bark": Color(0.52, 0.32, 0.22), "bstyle": 1, "evergreen": 0.0},
	"deciduous":     {"sp_idx": 4,  "tint": Vector3(0.26, 0.44, 0.16), "bark": Color(0.42, 0.34, 0.26), "bstyle": 0, "evergreen": 0.0},
	"elm":           {"sp_idx": 2,  "tint": Vector3(0.24, 0.42, 0.15), "bark": Color(0.30, 0.25, 0.18), "bstyle": 0, "evergreen": 0.0},
	"ginkgo":        {"sp_idx": 8,  "tint": Vector3(0.30, 0.50, 0.22), "bark": Color(0.50, 0.42, 0.32), "bstyle": 0, "evergreen": 0.0},
	"honeylocust":   {"sp_idx": 6,  "tint": Vector3(0.32, 0.52, 0.20), "bark": Color(0.45, 0.38, 0.28), "bstyle": 0, "evergreen": 0.0},
	"linden":        {"sp_idx": 10, "tint": Vector3(0.26, 0.48, 0.18), "bark": Color(0.42, 0.36, 0.28), "bstyle": 0, "evergreen": 0.0},
	"london_plane":  {"sp_idx": 9,  "tint": Vector3(0.24, 0.44, 0.16), "bark": Color(0.60, 0.56, 0.48), "bstyle": 2, "evergreen": 0.0},
	"magnolia":      {"sp_idx": 13, "tint": Vector3(0.18, 0.35, 0.12), "bark": Color(0.52, 0.48, 0.44), "bstyle": 4, "evergreen": 0.0},
	"maple":         {"sp_idx": 1,  "tint": Vector3(0.30, 0.50, 0.18), "bark": Color(0.50, 0.40, 0.30), "bstyle": 0, "evergreen": 0.0},
	"oak":           {"sp_idx": 0,  "tint": Vector3(0.24, 0.40, 0.14), "bark": Color(0.40, 0.32, 0.24), "bstyle": 0, "evergreen": 0.0},
	"pine":          {"sp_idx": 5,  "tint": Vector3(0.14, 0.30, 0.10), "bark": Color(0.48, 0.34, 0.22), "bstyle": 3, "evergreen": 1.0},
	"willow":        {"sp_idx": 12, "tint": Vector3(0.30, 0.50, 0.15), "bark": Color(0.40, 0.35, 0.28), "bstyle": 1, "evergreen": 0.0},
}

const BARK_TEX_PATHS := {
	0: {"albedo": "res://textures/bark/oak/Bark012_1K-JPG_Color.jpg",
		"normal": "res://textures/bark/oak/Bark012_1K-JPG_NormalGL.jpg",
		"roughness": "res://textures/bark/oak/Bark012_1K-JPG_Roughness.jpg"},
	1: {"albedo": "res://textures/bark/smooth/Bark003_1K-JPG_Color.jpg",
		"normal": "res://textures/bark/smooth/Bark003_1K-JPG_NormalGL.jpg",
		"roughness": "res://textures/bark/smooth/Bark003_1K-JPG_Roughness.jpg"},
	2: {"albedo": "res://textures/bark/exfoliating/Bark015_1K-JPG_Color.jpg",
		"normal": "res://textures/bark/exfoliating/Bark015_1K-JPG_NormalGL.jpg",
		"roughness": "res://textures/bark/exfoliating/Bark015_1K-JPG_Roughness.jpg"},
	3: {"albedo": "res://textures/bark/pine/pine_bark_diff_1k.jpg",
		"normal": "res://textures/bark/pine/pine_bark_nor_gl_1k.jpg",
		"roughness": "res://textures/bark/pine/pine_bark_rough_1k.jpg"},
	4: {"albedo": "res://textures/bark/furrowed/Bark007_1K-JPG_Color.jpg",
		"normal": "res://textures/bark/furrowed/Bark007_1K-JPG_NormalGL.jpg",
		"roughness": "res://textures/bark/furrowed/Bark007_1K-JPG_Roughness.jpg"},
}

@onready var sub_viewport: SubViewport = $SubViewport
@onready var camera: Camera3D = $SubViewport/Camera3D
@onready var tree_root: Node3D = $SubViewport/TreeRoot
@onready var world_env: WorldEnvironment = $SubViewport/WorldEnvironment

var _leaf_shader: Shader
var _bark_shader: Shader
var _bark_tex_cache: Dictionary = {}
var _filter_species: String = ""


func _ready() -> void:
	# User args — everything after `--` on the Godot command line. Godot may
	# strip known flags from get_cmdline_args(), so use the user-arg list.
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			_filter_species = arg.substr("--only=".length())
	if _filter_species != "":
		print("impostor_baker: filter species = '%s'" % _filter_species)

	sub_viewport.size = Vector2i(FRAME_RES_BAKE, FRAME_RES_BAKE)
	sub_viewport.transparent_bg = true
	sub_viewport.msaa_3d = Viewport.MSAA_4X       # alpha_to_coverage needs MSAA
	sub_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS

	_leaf_shader = load("res://shaders/tree_leaf.gdshader")
	_bark_shader = load("res://shaders/tree_bark.gdshader")
	_prime_bark_textures()
	_set_environment_for_bake()

	# Neutralize runtime-driving globals so the shader paints static summer
	# foliage. main.gd registers these at runtime; in this standalone scene
	# we register them ourselves so the shaders see valid values. Pinned to
	# summer/no-weather so the atlas captures a "default" canopy frame.
	_register_global("wind_vec",            RenderingServer.GLOBAL_VAR_TYPE_VEC2,  Vector2.ZERO)
	_register_global("snow_cover",          RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	_register_global("rain_wetness",        RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	_register_global("season_t",            RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 1.0)
	_register_global("sky_reflect_color",   RenderingServer.GLOBAL_VAR_TYPE_VEC3,  Vector3(0.78, 0.84, 0.90))
	_register_global("lightning_flash",     RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	_register_global("dew_amount",          RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	_register_global("lamp_glow",           RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	_register_global("impostor_brightness", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 1.0)

	await get_tree().process_frame
	await _bake_all()
	print("impostor_baker: DONE")
	get_tree().quit()


func _register_global(name: String, type: int, value) -> void:
	# Idempotent: if a previous run left the param registered (editor session),
	# or another script registered it, skip and just set the value.
	if not RenderingServer.global_shader_parameter_get_list().has(name):
		RenderingServer.global_shader_parameter_add(name, type, value)
	else:
		RenderingServer.global_shader_parameter_set(name, value)


func _set_environment_for_bake() -> void:
	# Sky-dome ambient + SSAO: replaces the old flat (1,1,1) ambient. The sky
	# gives natural cool-top/warm-horizon modulation, and SSAO bakes canopy
	# self-occlusion into the atlas so branches read 3D from distance.
	var env := Environment.new()
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.55, 0.70, 0.92)
	sky_mat.sky_horizon_color = Color(0.82, 0.85, 0.90)
	sky_mat.sky_curve = 0.15
	sky_mat.sky_energy_multiplier = 1.0
	sky_mat.ground_bottom_color = Color(0.22, 0.20, 0.17)
	sky_mat.ground_horizon_color = Color(0.55, 0.50, 0.42)
	sky_mat.ground_curve = 0.02
	sky_mat.ground_energy_multiplier = 0.55  # dim the ground so canopy doesn't light from below too strongly
	sky.sky_material = sky_mat
	env.sky = sky
	env.background_mode = Environment.BG_CLEAR_COLOR    # Keep alpha-transparent bg for atlas
	env.background_color = Color(0, 0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 1.0
	# Ambient lowered 1.0 → 0.7 (was washing out canopy tops at distance).
	# SSAO disabled — at impostor distance the AO detail is invisible, and
	# ssao_intensity=1.8 was producing dark-hat rim artifacts that defined
	# the silhouette against bright sky. If canopies read flat after this
	# rebake, reintroduce SSAO at 0.3.
	env.ambient_light_energy = 0.7
	env.ssao_enabled = false
	env.glow_enabled = false
	env.adjustment_enabled = false
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world_env.environment = env


func _prime_bark_textures() -> void:
	for style_id in BARK_TEX_PATHS:
		var paths: Dictionary = BARK_TEX_PATHS[style_id]
		var texs := {}
		for k in paths:
			var t = load(paths[k])
			if t:
				texs[k] = t
		if texs.size() == 3:
			_bark_tex_cache[style_id] = texs


func _bake_all() -> void:
	var species_list: Array = SPECIES_INFO.keys()
	species_list.sort()
	# Two seasonal passes: summer (mid-leaf, season_t=1.0) and winter
	# (mid-winter, season_t=3.0). The runtime leaf shader responds to
	# season_t via PHENOLOGY and WINTER_RETENTION — so a winter pass with
	# a clean-abscission species produces bare trunks and a marcescent
	# species produces sparse dead-brown canopy, baked into the atlas.
	# Output suffix: "" for summer (backward-compatible filename) and
	# "_winter" for winter.
	var seasons := [
		{"season_t": 1.0, "suffix": ""},         # mid-summer (full leaf)
		{"season_t": 3.3, "suffix": "_winter"},  # past bare_start for most species
	]
	for pass_info in seasons:
		RenderingServer.global_shader_parameter_set("season_t", pass_info.season_t)
		await get_tree().process_frame  # let the new uniform propagate
		for species in species_list:
			if _filter_species != "" and species != _filter_species:
				continue
			for tier in ["_s", "_m", "_l"]:
				var path: String = TREE_DIR + species + tier + ".glb"
				if not FileAccess.file_exists(path):
					continue
				await _bake_one(species, species + tier, path, pass_info.suffix)
			var fallback_tier := ""
			for t in ["_m", "_l", "_s"]:
				if FileAccess.file_exists(TREE_DIR + species + t + ".glb"):
					fallback_tier = t
					break
			if fallback_tier != "":
				await _bake_one(species, species,
					TREE_DIR + species + fallback_tier + ".glb", pass_info.suffix)


func _bake_one(species: String, label: String, glb_path: String, suffix: String = "") -> void:
	print("impostor_baker: === %s%s ===" % [label, suffix])
	# Wipe the previous tree before loading the next — otherwise variants pile
	# up in TreeRoot and each bake renders every prior tree behind the new one.
	for child in tree_root.get_children():
		child.queue_free()
	await get_tree().process_frame

	var meshes := _load_glb_meshes(glb_path)
	if meshes.is_empty():
		push_warning("impostor_baker: no meshes in %s" % glb_path)
		return

	var info: Dictionary = SPECIES_INFO[species]
	# Pick a single representative variant. GLBs hold 5 variants; variant 0
	# is a stable choice and matches how tree_builder.gd's first seeded pick
	# would read. (Runtime uses per-instance variant; impostor collapses all
	# variants to one silhouette — acceptable because at impostor range you
	# can't resolve variant-to-variant shape differences anyway.)
	var variant_idx := 0
	if variant_idx >= meshes.size():
		variant_idx = 0
	var mesh: Mesh = meshes[variant_idx].duplicate(true)
	_assign_bake_materials(mesh, info, species)

	# One instance, driven by MultiMesh so INSTANCE_CUSTOM feeds correctly.
	var mm := MultiMesh.new()
	mm.use_custom_data = true
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = 1
	mm.set_instance_transform(0, Transform3D.IDENTITY)
	# sp_idx encoded into R (× 1/13), timing_off=0.5 (neutral), evergreen flag,
	# jitter=0.5 (no per-tree warp) — mirrors tree_builder's runtime encoding.
	var sp_r: float = float(info.sp_idx) / 13.0
	mm.set_instance_custom_data(0, Color(sp_r, 0.5, info.evergreen, 0.5))

	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	tree_root.add_child(mmi)

	# Tight orthographic framing: max-dimension, not aabb diagonal. Using
	# diagonal (sqrt(x² + y² + z²)) over-frames every species — for an oak
	# with dims 12×17×12 the diagonal is 24m, but the silhouette never
	# exceeds 17m × 17m from any view direction. The runtime billboard
	# inherits this size, so loose framing → impostors render larger than
	# the meshes they replace at the LOD1↔impostor boundary. Tight framing
	# matches sizes exactly and gives the silhouette more atlas pixels.
	var ab: AABB = mesh.get_aabb()
	var center: Vector3 = ab.get_center()
	var max_dim: float = maxf(ab.size.x, maxf(ab.size.y, ab.size.z))
	var frame_half: float = max_dim * 0.5 * 1.05  # 5% safety margin
	frame_half = maxf(frame_half, 0.01)

	# Look-at distance: keep whole mesh in front of near plane regardless of
	# view direction. Use aabb diagonal/2 (always >= max_dim/2 + a margin).
	var cam_dist: float = ab.size.length() * 0.5 + 0.5

	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = frame_half * 2.0
	camera.near = 0.01
	camera.far = cam_dist * 4.0

	# Allocate the atlas as 8-bit RGBA (final PNG is 8-bit; float accumulation
	# buys nothing without blending).
	var atlas := Image.create(ATLAS_RES, ATLAS_RES, false, Image.FORMAT_RGBA8)
	atlas.fill(Color(0, 0, 0, 0))

	for iy in range(FRAME_SIZE):
		for ix in range(FRAME_SIZE):
			var u := float(ix) / float(FRAME_SIZE - 1)
			var v := float(iy) / float(FRAME_SIZE - 1)
			var bake_dir := _hemisphere_octa(u, v)             # Blender-space
			# Blender → Godot: Blender (x=right, y=fwd, z=up) → Godot (x=right, y=up, z=back)
			var godot_dir := Vector3(bake_dir.x, bake_dir.z, -bake_dir.y)
			var cam_pos: Vector3 = center + godot_dir * cam_dist * 2.0
			camera.global_transform = _look_at_from_position(cam_pos, center)

			# Two frames: one to apply the new transform, one after
			# frame_post_draw so the texture contains the new render.
			await RenderingServer.frame_post_draw
			await RenderingServer.frame_post_draw
			var frame_img: Image = sub_viewport.get_texture().get_image()
			if frame_img.get_format() != Image.FORMAT_RGBA8:
				frame_img.convert(Image.FORMAT_RGBA8)
			# Super-sample downsample: render at 2× target res, downsample
			# to FRAME_RES for cleaner edges + better alpha coverage.
			if SUPERSAMPLE > 1:
				frame_img.resize(FRAME_RES, FRAME_RES, Image.INTERPOLATE_LANCZOS)
			atlas.blit_rect(frame_img, Rect2i(0, 0, FRAME_RES, FRAME_RES),
				Vector2i(ix * FRAME_RES, iy * FRAME_RES))

	# Dilation (edge bleed for mipmap safety) is skipped — the GDScript loop
	# was costing ~55s per atlas. If distant impostors show darkened edges,
	# we can add a post-bake Python pass that runs in 1-2s per atlas.

	var albedo_path := OUT_DIR + label + "_impostor_albedo" + suffix + ".png"
	var abs_path := ProjectSettings.globalize_path(albedo_path)
	atlas.save_png(abs_path)
	print("impostor_baker:   saved %s" % abs_path)


func _assign_bake_materials(mesh: Mesh, info: Dictionary, species: String) -> void:
	var leaf_tint: Vector3 = info.tint
	var bark_col: Color = info.bark
	var bstyle: int = info.bstyle
	for si in mesh.get_surface_count():
		var smat: Material = mesh.surface_get_material(si)
		var is_leaf := false
		if smat is StandardMaterial3D:
			var sm: StandardMaterial3D = smat as StandardMaterial3D
			is_leaf = sm.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED
		if is_leaf:
			var leaf_mat := ShaderMaterial.new()
			leaf_mat.shader = _leaf_shader
			leaf_mat.set_shader_parameter("albedo_tint", leaf_tint)
			# Match the runtime preference: DDS coverage-preserving mips when
			# present, otherwise fall back to the GLB-embedded texture.
			var dds_path := "res://textures/leaves/%s_leaf.dds" % species
			if ResourceLoader.exists(dds_path):
				leaf_mat.set_shader_parameter("albedo_tex", load(dds_path))
			elif smat is StandardMaterial3D and (smat as StandardMaterial3D).albedo_texture:
				leaf_mat.set_shader_parameter("albedo_tex", (smat as StandardMaterial3D).albedo_texture)
			mesh.surface_set_material(si, leaf_mat)
		else:
			# Bark: restored for silhouette parity with LOD2 mesh. The previous
			# canopy-only approach made distant birch less washed-out but
			# introduced a universal trunk-pop at the LOD2↔impostor transition
			# boundary (verified via silhouette comparison across all species).
			# Mipmap bark-bleed is now mitigated by post-bake alpha dilation
			# (scripts/dilate_impostors.py) + aerial perspective fog at distance.
			var bark_mat := ShaderMaterial.new()
			bark_mat.shader = _bark_shader
			bark_mat.set_shader_parameter("bark_color", Vector3(bark_col.r, bark_col.g, bark_col.b))
			bark_mat.set_shader_parameter("bark_style", bstyle)
			if _bark_tex_cache.has(bstyle):
				var btex: Dictionary = _bark_tex_cache[bstyle]
				bark_mat.set_shader_parameter("bark_albedo_tex", btex["albedo"])
				bark_mat.set_shader_parameter("bark_normal_tex", btex["normal"])
				bark_mat.set_shader_parameter("bark_roughness_tex", btex["roughness"])
			mesh.surface_set_material(si, bark_mat)


func _look_at_from_position(pos: Vector3, target: Vector3) -> Transform3D:
	var t := Transform3D()
	t.origin = pos
	# Godot's Transform3D.looking_at builds a basis where -Z points at target.
	# Use Y+ as reference up; if direction is nearly parallel, fall to Z+.
	var up := Vector3.UP
	var dir := (target - pos).normalized()
	if abs(dir.dot(up)) > 0.999:
		up = Vector3.FORWARD
	return t.looking_at(target, up)


# ── Hemisphere octahedral mapping (must mirror scripts/bake_impostors.py) ──
func _hemisphere_octa(u: float, v: float) -> Vector3:
	var x: float = u - v
	var z: float = -1.0 + u + v
	var y: float = 1.0 - absf(x) - absf(z)
	var L: float = sqrt(x * x + y * y + z * z)
	if L < 0.001:
		return Vector3(0, 0, 1)
	return Vector3(x / L, y / L, z / L)


# ── GLB loading ────────────────────────────────────────────────────────────
func _load_glb_meshes(path: String) -> Array:
	var abs_path := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		return []
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(abs_path, state)
	if err != OK:
		push_warning("impostor_baker: GLB load failed %s (%d)" % [path, err])
		return []
	var root := doc.generate_scene(state)
	var meshes: Array = []
	_collect_meshes(root, meshes)
	root.queue_free()
	return meshes


func _collect_meshes(node: Node, out: Array) -> void:
	if node is MeshInstance3D:
		var mi: MeshInstance3D = node
		if mi.mesh:
			out.append(mi.mesh)
	for c in node.get_children():
		_collect_meshes(c, out)


# ── Atlas dilation (extend opaque pixels into transparent gutter per frame) ─
#
# Trees have soft alpha edges — without dilation, mipmap filtering pulls in
# the transparent-black gutter and darkens the silhouette. We walk outward
# from opaque pixels by `distance` steps, copying color (not alpha) into
# the newly reached transparent cells. Per-frame loop avoids color bleeding
# across the grid boundaries.
func _dilate_frames(atlas: Image, distance: int) -> void:
	for fy in FRAME_SIZE:
		for fx in FRAME_SIZE:
			_dilate_region(atlas, fx * FRAME_RES, fy * FRAME_RES,
				FRAME_RES, FRAME_RES, distance)


func _dilate_region(atlas: Image, x0: int, y0: int, w: int, h: int, distance: int) -> void:
	# Raw byte access — get_pixel/set_pixel in GDScript are ~1000× slower.
	# Atlas is RGBA8, so 4 bytes per pixel, stride = atlas.get_width() × 4.
	var data: PackedByteArray = atlas.get_data()
	var stride: int = atlas.get_width() * 4
	for _iter in distance:
		var writes_xy: PackedInt32Array = PackedInt32Array()
		var writes_rgb: PackedByteArray = PackedByteArray()
		for y in h:
			var row: int = (y0 + y) * stride
			for x in w:
				var p: int = row + (x0 + x) * 4
				if data[p + 3] > 2:
					continue
				var found := false
				for dy in range(-1, 2):
					if found: break
					for dx in range(-1, 2):
						if dx == 0 and dy == 0:
							continue
						var nx: int = x + dx
						var ny: int = y + dy
						if nx < 0 or nx >= w or ny < 0 or ny >= h:
							continue
						var q: int = (y0 + ny) * stride + (x0 + nx) * 4
						if data[q + 3] > 2:
							writes_xy.append(p)
							writes_rgb.append(data[q])
							writes_rgb.append(data[q + 1])
							writes_rgb.append(data[q + 2])
							found = true
							break
		if writes_xy.is_empty():
			break
		for i in writes_xy.size():
			var p: int = writes_xy[i]
			data[p]     = writes_rgb[i * 3]
			data[p + 1] = writes_rgb[i * 3 + 1]
			data[p + 2] = writes_rgb[i * 3 + 2]
			# Alpha stays 0 — dilation is for mipmap color correctness only.
	atlas.set_data(atlas.get_width(), atlas.get_height(), false, Image.FORMAT_RGBA8, data)
