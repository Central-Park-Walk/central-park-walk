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
# Per-card keep-fraction used DURING the bake (tree_leaf bake_density): a full
# crown projects SOLID at bake resolution, so without thinning the atlas read
# ~0.64-0.74 filled vs the live mesh's see-through ~0.38-0.58 at the handoff =>
# impostor solid-blob "fuller/bigger than lod1". This drops (1-value) of the
# cluster cards (reusing the seasonal v_card_seed drop) to punch matching
# card-scale holes. Calibrated 2026-06-24 so the impostor silhouette matches the
# mesh at the lod1->impostor handoff. -1 = no drop (full crown).
const BAKE_DENSITY := 0.1

var _loader  # park_loader — in the scene tree; bake viewport parents here

func _init(loader) -> void:
	_loader = loader

# Bake one species-size tier. Returns a metadata dict for the manifest.
func bake_tier(tier_key: String, meshes: Array, world_height: float) -> Dictionary:
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

	var saved := _push_bake_globals()
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
					sm.set_shader_parameter("bake_density", BAKE_DENSITY)
					_set_n += 1
	print("  bake_density=%.2f applied to %d leaf surfaces" % [BAKE_DENSITY, _set_n])

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
		var path: String = OUT_DIR + "%s_%s.png" % [tier_key, ch[0]]
		atlas.save_png(ProjectSettings.globalize_path(path))
		atlases[ch[0]] = path
		print("  Impostor bake: %s %s -> %s" % [tier_key, ch[0], path])

	_set_bake_mode(meshes, 0)
	_pop_bake_globals(saved)
	vp.queue_free()

	# scale / aabb_max per the addon export_scene convention (ImpostorShader uniforms).
	# position_offset = +center lifts the billboard to canopy height — the SIGN that,
	# inverted, buried the whole far tier under the terrain in the prior system.
	var scale_instance := diag / 2.0
	return {
		"tier": tier_key, "frames": FRAMES, "atlas_res": ATLAS_RES, "is_full_sphere": false,
		"scale": scale_instance, "aabb_max": scale_instance / 2.0,
		"position_offset": [center.x, center.y, center.z],
		"world_height": world_height, "diag": diag,
		"albedo": atlases.get("albedo", ""), "normal": atlases.get("normal", ""),
		"orm": atlases.get("orm", ""),
	}

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

# Force a clean summer, windless, snowless, haze-free bake regardless of the
# app's current time-of-day; restore afterwards so a non-quitting caller is safe.
const _BAKE_GLOBALS := {
	"season_t": SUMMER_SEASON,
	"snow_cover": 0.0,
	"rain_wetness": 0.0,
	"wind_vec": Vector2.ZERO,
	"player_world_pos": Vector3(0, 1000, 0),
}

func _push_bake_globals() -> Dictionary:
	# global_shader_parameter_get is editor-only, and this bake run quits afterwards,
	# so we just SET the bake conditions and skip save/restore.
	for k in _BAKE_GLOBALS:
		RenderingServer.global_shader_parameter_set(k, _BAKE_GLOBALS[k])
	return {}

func _pop_bake_globals(_saved: Dictionary) -> void:
	pass
