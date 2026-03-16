# grass_builder.gd
# Full-geometry grass (hexaquo method). Each blade is its own MultiMesh
# instance. Patchiness, color, wind, AO all driven by the shader.
#
# Blades are scattered uniformly within each chunk, filtered by the world
# atlas (surface==1 = grass). Type and path proximity come from
# the pre-baked cell lookup.
#
# Queue-based chunk loading: chunks build 1 per frame, closest first,
# so grass appears gradually instead of in 10m blocks.

var _loader
var _blade_meshes: Array = []
var _grass_shader: Shader
var _positions_by_chunk: Dictionary = {}  # "cx|cz" -> Array of pos dicts
var _active_chunks: Dictionary = {}       # "bt|cx|cz" -> MultiMeshInstance3D
var _last_update_pos := Vector3(-99999, 0, -99999)
var _build_queue: Array = []              # [ck: String] — chunks waiting to build
var _queued_set: Dictionary = {}          # ck -> true — fast lookup for queue

const CHUNK := 10.0
const BLADES_PER_M2 := 600.0
const CELL_SIZE := 1.22
const MAX_BLADES_PER_CHUNK := 40000  # cap to keep build time reasonable
const VIS_RANGE := 18.0
const LOAD_RANGE := 30.0             # pre-load further ahead
const UNLOAD_RANGE := 40.0
const UPDATE_DIST := 3.0             # re-check chunks every 3m moved

const BLADE_NAMES: Array = ["Blade_Lawn", "Blade_Wild", "Blade_Shade", "Blade_Sedge"]

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

	print("Grass: %d cell positions in %d chunks (%.0fms)" % [
		x_arr.size(), _positions_by_chunk.size(), Time.get_ticks_msec() - t0])

	# Build initial chunks synchronously (at spawn, no queue delay)
	var spawn := Vector3(-480, 0, 1020)
	_last_update_pos = spawn
	_update_chunks_near(spawn)
	_flush_queue(spawn)


func update_camera(camera_pos: Vector3) -> void:
	# Re-check which chunks are needed every UPDATE_DIST meters
	if camera_pos.distance_to(_last_update_pos) > UPDATE_DIST:
		_last_update_pos = camera_pos
		_update_chunks_near(camera_pos)

	# Build 1 queued chunk per frame (closest first)
	if not _build_queue.is_empty():
		_process_queue(camera_pos)


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

	# Queue chunks that need building
	for ck in needed:
		if _chunk_is_loaded(ck) or _queued_set.has(ck):
			continue
		_build_queue.append(ck)
		_queued_set[ck] = true

	# Remove queued chunks that are no longer needed
	var new_queue: Array = []
	for ck in _build_queue:
		if needed.has(ck):
			new_queue.append(ck)
		else:
			_queued_set.erase(ck)
	_build_queue = new_queue


func _process_queue(pos: Vector3) -> void:
	# Find closest queued chunk and build it
	var best_idx := -1
	var best_dist := 999999.0
	for i in _build_queue.size():
		var ck: String = _build_queue[i]
		var parts: PackedStringArray = ck.split("|")
		var center := Vector3((float(parts[0]) + 0.5) * CHUNK, 0, (float(parts[1]) + 0.5) * CHUNK)
		var d := center.distance_to(pos)
		if d < best_dist:
			best_dist = d
			best_idx = i

	if best_idx < 0:
		return

	var ck: String = _build_queue[best_idx]
	_build_queue.remove_at(best_idx)
	_queued_set.erase(ck)

	if _chunk_is_loaded(ck):
		return
	if not _positions_by_chunk.has(ck):
		return

	_build_chunk(ck)


func _flush_queue(pos: Vector3) -> void:
	# Build all queued chunks immediately (used at startup)
	while not _build_queue.is_empty():
		_process_queue(pos)
	print("Grass: initial chunks built (active: %d)" % _active_chunks.size())


func _chunk_is_loaded(ck: String) -> bool:
	for bt in BLADE_NAMES.size():
		if _active_chunks.has("%d|%s" % [bt, ck]):
			return true
	return false


func _build_chunk(ck: String) -> void:
	var positions: Array = _positions_by_chunk[ck]
	if positions.is_empty():
		return

	var ck_parts: PackedStringArray = ck.split("|")
	var chunk_x: float = float(ck_parts[0]) * CHUNK
	var chunk_z: float = float(ck_parts[1]) * CHUNK

	# Cell lookup for type/prox
	var cell_lookup: Dictionary = {}
	for p in positions:
		var lx: int = int((p["x"] - chunk_x) / CELL_SIZE)
		var lz: int = int((p["z"] - chunk_z) / CELL_SIZE)
		cell_lookup[lx * 256 + lz] = p

	# Target blade count, capped for build performance
	var grass_area: float = positions.size() * CELL_SIZE * CELL_SIZE
	var target: int = mini(int(grass_area * BLADES_PER_M2), MAX_BLADES_PER_CHUNK)

	var rng := RandomNumberGenerator.new()
	rng.seed = (int(ck_parts[0]) * 73856093 + int(ck_parts[1]) * 19349669) & 0x7FFFFFFF

	var by_type: Dictionary = {}
	var placed := 0

	for _i in int(target * 1.5):
		if placed >= target:
			break
		var bx: float = chunk_x + rng.randf() * CHUNK
		var bz: float = chunk_z + rng.randf() * CHUNK

		if _loader._atlas_surface(bx, bz) != 1:
			continue

		var lx: int = int((bx - chunk_x) / CELL_SIZE)
		var lz: int = int((bz - chunk_z) / CELL_SIZE)
		var cell_key: int = lx * 256 + lz

		var orig_type: int = 9
		var path_prox: float = 0.0
		if cell_lookup.has(cell_key):
			orig_type = cell_lookup[cell_key]["type"]
			path_prox = float(cell_lookup[cell_key]["prox"]) / 255.0

		var blade_type: int = 0
		if orig_type < TYPE_TO_BLADE.size():
			blade_type = TYPE_TO_BLADE[orig_type]
		if blade_type >= _blade_meshes.size() or _blade_meshes[blade_type] == null:
			continue

		var wy: float = _loader._terrain_y(bx, bz)

		var y_rot: float = rng.randf() * TAU
		var h_scale: float = rng.randf_range(0.7, 1.3)
		if path_prox > 0.1:
			h_scale *= lerpf(1.0, 0.4, path_prox)

		if not by_type.has(blade_type):
			by_type[blade_type] = {"xf": [], "cd": []}

		var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(1.0, h_scale, 1.0))
		by_type[blade_type]["xf"].append(Transform3D(basis, Vector3(bx, wy, bz)))
		by_type[blade_type]["cd"].append(Color(float(orig_type), rng.randf(), path_prox, 0.0))
		placed += 1

	for blade_type in by_type:
		var data: Dictionary = by_type[blade_type]
		var xf_list: Array = data["xf"]
		var cd_list: Array = data["cd"]
		if xf_list.is_empty():
			continue

		var mesh: Mesh = _blade_meshes[blade_type]

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
