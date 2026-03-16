# grass_builder.gd
# Full-geometry grass (hexaquo method). Each blade is its own MultiMesh
# instance. Patchiness, color, wind, AO all driven by the shader.
#
# Single layer of individual blades at 400/m² (hexaquo density).
# Positions from ground_cover_instances.bin, expanded to blades per chunk.
# 4 blade meshes: Lawn (4 tris), Wild (8), Shade (6), Sedge (6).

var _loader
var _blade_meshes: Array = []
var _grass_shader: Shader
var _positions_by_chunk: Dictionary = {}  # "cx|cz" -> Array of pos dicts
var _active_chunks: Dictionary = {}       # "bt|cx|cz" -> MultiMeshInstance3D
var _last_camera_chunk := Vector2i(-9999, -9999)

const CHUNK := 10.0
const BLADES_PER_M2 := 400.0
const BLADE_SPREAD := 0.55
const VIS_RANGE := 18.0
const LOAD_RANGE := 25.0
const UNLOAD_RANGE := 35.0

const BLADE_NAMES: Array = ["Blade_Lawn", "Blade_Wild", "Blade_Shade", "Blade_Sedge"]

# Grass type (0-9) -> blade mesh index
const TYPE_TO_BLADE: Array = [
	0, 0, 0, 0, 0,  # types 0-4 -> Lawn
	2, 2,            # types 5-6 -> Shade
	3,               # type 7 -> Sedge
	1,               # type 8 -> Wild
	0,               # type 9 -> Lawn
]


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()

	_grass_shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")

	# Load blade meshes
	for bname in BLADE_NAMES:
		var mesh: Mesh = _load_blade_model(bname)
		_blade_meshes.append(mesh)

	var loaded := 0
	for m in _blade_meshes:
		if m != null:
			loaded += 1
	if loaded == 0:
		print("Grass: no blade meshes — run make_blade_mesh.py in Blender")
		return

	# Load prebaked positions and organize by chunk
	var instances: Array = _load_binary("res://ground_cover_instances.bin", 0x47524332)
	if instances.is_empty():
		print("Grass: no ground cover instances — run convert_to_godot.py")
		return

	var x_arr: PackedFloat32Array = instances[0]
	var z_arr: PackedFloat32Array = instances[1]
	var type_arr: PackedByteArray = instances[2]
	var y_arr: PackedFloat32Array = instances[3]
	var prox_arr: PackedByteArray = instances[4]

	for i in x_arr.size():
		var cx := int(floorf(x_arr[i] / CHUNK))
		var cz := int(floorf(z_arr[i] / CHUNK))
		var ck := "%d|%d" % [cx, cz]
		if not _positions_by_chunk.has(ck):
			_positions_by_chunk[ck] = []
		_positions_by_chunk[ck].append({
			"x": x_arr[i], "z": z_arr[i], "y": y_arr[i],
			"type": type_arr[i], "prox": prox_arr[i]
		})

	print("Grass: %d positions in %d chunks (%.0fms)" % [
		x_arr.size(), _positions_by_chunk.size(), Time.get_ticks_msec() - t0])

	# Build initial chunks near spawn
	_update_chunks_near(Vector3(-480, 0, 1020))


func update_camera(camera_pos: Vector3) -> void:
	var cam_cx := int(floorf(camera_pos.x / CHUNK))
	var cam_cz := int(floorf(camera_pos.z / CHUNK))
	if cam_cx == _last_camera_chunk.x and cam_cz == _last_camera_chunk.y:
		return
	_last_camera_chunk = Vector2i(cam_cx, cam_cz)
	_update_chunks_near(camera_pos)


func _update_chunks_near(pos: Vector3) -> void:
	var load_chunks := int(ceili(LOAD_RANGE / CHUNK))

	var cam_cx := int(floorf(pos.x / CHUNK))
	var cam_cz := int(floorf(pos.z / CHUNK))
	var needed: Dictionary = {}

	for dx in range(-load_chunks, load_chunks + 1):
		for dz in range(-load_chunks, load_chunks + 1):
			var cx := cam_cx + dx
			var cz := cam_cz + dz
			var chunk_center := Vector3((cx + 0.5) * CHUNK, 0, (cz + 0.5) * CHUNK)
			if chunk_center.distance_to(pos) > LOAD_RANGE:
				continue
			var ck := "%d|%d" % [cx, cz]
			if _positions_by_chunk.has(ck):
				needed[ck] = true

	# Unload distant chunks
	var to_remove: Array = []
	for key: String in _active_chunks:
		var parts: PackedStringArray = key.split("|")
		var ck: String = "%s|%s" % [parts[1], parts[2]]
		if not needed.has(ck):
			var mmi: MultiMeshInstance3D = _active_chunks[key]
			mmi.queue_free()
			to_remove.append(key)
	for key in to_remove:
		_active_chunks.erase(key)

	# Load new chunks
	var built := 0
	for ck in needed:
		var any_loaded := false
		for bt in BLADE_NAMES.size():
			if _active_chunks.has("%d|%s" % [bt, ck]):
				any_loaded = true
				break
		if any_loaded:
			continue
		_build_chunk(ck)
		built += 1

	if built > 0 or to_remove.size() > 0:
		print("Grass chunks: +%d -%d (active: %d)" % [built, to_remove.size(), _active_chunks.size()])


func _build_chunk(ck: String) -> void:
	var positions: Array = _positions_by_chunk[ck]
	if positions.is_empty():
		return

	var grid_area: float = positions.size() * 1.49  # each grid pos covers ~1.49m²
	var target_blades := int(grid_area * BLADES_PER_M2 / positions.size())
	var blades_per_pos := clampi(target_blades, 10, 800)

	var by_type: Dictionary = {}
	var rng := RandomNumberGenerator.new()

	for pos_data in positions:
		var wx: float = pos_data["x"]
		var wz: float = pos_data["z"]
		var wy: float = pos_data["y"]
		var orig_type: int = pos_data["type"]
		var prox: int = pos_data["prox"]
		var path_prox: float = float(prox) / 255.0

		var blade_type: int = 0
		if orig_type < TYPE_TO_BLADE.size():
			blade_type = TYPE_TO_BLADE[orig_type]
		if blade_type >= _blade_meshes.size() or _blade_meshes[blade_type] == null:
			continue

		rng.seed = int(abs(wx) * 73856.0 + abs(wz) * 19349.0) & 0x7FFFFFFF

		if not by_type.has(blade_type):
			by_type[blade_type] = {"xf": [], "cd": []}

		for _b in blades_per_pos:
			var bx: float = wx + rng.randf_range(-BLADE_SPREAD, BLADE_SPREAD)
			var bz: float = wz + rng.randf_range(-BLADE_SPREAD, BLADE_SPREAD)
			var y_rot: float = rng.randf() * TAU
			var h_scale: float = rng.randf_range(0.7, 1.3)
			if path_prox > 0.1:
				h_scale *= lerpf(1.0, 0.4, path_prox)

			var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(1.0, h_scale, 1.0))
			var tf := Transform3D(basis, Vector3(bx, wy, bz))

			by_type[blade_type]["xf"].append(tf)
			by_type[blade_type]["cd"].append(Color(float(orig_type), rng.randf(), path_prox, 0.0))

	for blade_type in by_type:
		var data: Dictionary = by_type[blade_type]
		var xf_list: Array = data["xf"]
		var cd_list: Array = data["cd"]
		if xf_list.is_empty():
			continue

		var mesh: Mesh = _blade_meshes[blade_type]

		# Chunk center for local coordinates
		var sx := 0.0; var sy := 0.0; var sz := 0.0
		for tf: Transform3D in xf_list:
			sx += tf.origin.x; sy += tf.origin.y; sz += tf.origin.z
		var n := float(xf_list.size())
		var origin := Vector3(sx / n, sy / n, sz / n)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = xf_list.size()
		for j in xf_list.size():
			var tf: Transform3D = xf_list[j]
			mm.set_instance_transform(j, Transform3D(tf.basis, tf.origin - origin))
			mm.set_instance_custom_data(j, cd_list[j])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = origin
		mmi.name = "Grass_%d_%s" % [blade_type, ck]
		mmi.visibility_range_end = VIS_RANGE
		mmi.visibility_range_end_margin = VIS_RANGE * 0.40
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		_active_chunks["%d|%s" % [blade_type, ck]] = mmi


func _load_blade_model(bname: String) -> Mesh:
	var abs_path := ProjectSettings.globalize_path("res://models/vegetation/%s.glb" % bname)
	if not FileAccess.file_exists(abs_path):
		return null
	var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
	if meshes.is_empty():
		return null
	var mesh: Mesh = meshes.values()[0]
	for si in mesh.get_surface_count():
		var new_mat := ShaderMaterial.new()
		new_mat.shader = _grass_shader
		if _loader._canopy_texture:
			new_mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
		new_mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		mesh.surface_set_material(si, new_mat)
	return mesh


func _load_binary(res_path: String, expected_magic: int) -> Array:
	var abs_path := ProjectSettings.globalize_path(res_path)
	var f := FileAccess.open(abs_path, FileAccess.READ)
	if f == null:
		f = FileAccess.open(res_path, FileAccess.READ)
	if f == null:
		return []
	var magic: int = f.get_32()
	var magic_rev: int = ((magic & 0xFF) << 24) | ((magic & 0xFF00) << 8) | ((magic & 0xFF0000) >> 8) | ((magic & 0xFF000000) >> 24)
	if magic != expected_magic and magic_rev != expected_magic:
		return []
	var cnt: int = f.get_32()
	if cnt == 0:
		return []
	var x_bytes := f.get_buffer(cnt * 4)
	var y_bytes := f.get_buffer(cnt * 4)
	var z_bytes := f.get_buffer(cnt * 4)
	var t_bytes := f.get_buffer(cnt)
	var pp_bytes := f.get_buffer(cnt)
	var x_a := PackedFloat32Array(); x_a.resize(cnt)
	var y_a := PackedFloat32Array(); y_a.resize(cnt)
	var z_a := PackedFloat32Array(); z_a.resize(cnt)
	var type_a := PackedByteArray(); type_a.resize(cnt)
	var prox_a := PackedByteArray(); prox_a.resize(cnt)
	for j in cnt:
		x_a[j] = x_bytes.decode_float(j * 4)
		y_a[j] = y_bytes.decode_float(j * 4)
		z_a[j] = z_bytes.decode_float(j * 4)
		type_a[j] = t_bytes[j]
		prox_a[j] = pp_bytes[j]
	print("  Grass: %d prebaked positions loaded" % cnt)
	return [x_a, z_a, type_a, y_a, prox_a]
