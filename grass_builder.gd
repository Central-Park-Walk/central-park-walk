# grass_builder.gd
# Two-layer hexaquo grass system with dynamic chunk loading.
#
# Layer 1 — Ground cover: Turf_*.glb tiles (500-600 pre-baked blades each)
#   placed at ground_cover_instances.bin positions. Dense carpet, hides terrain.
#
# Layer 2 — Detail blades: Blade_*.glb individual blades expanded from
#   grass_instances.bin positions. Taller silhouette grass above the carpet.
#
# Layer 3 — Impostor: terrain shader green base (handled in terrain.gdshader).
#
# Hexaquo principles: cylinder normals, patchiness via world-space noise,
# color tied to patch size, proper specular + translucency, self-shadowing AO.

var _loader
var _grass_shader: Shader
var _turf_meshes: Dictionary = {}   # turf_type → [variant_mesh_0..4]
var _blade_meshes: Array = []       # [Lawn, Wild, Shade, Sedge]
var _turf_by_chunk: Dictionary = {} # "cx|cz" → Array of pos dicts
var _blade_by_chunk: Dictionary = {} # "cx|cz" → Array of pos dicts
var _active_chunks: Dictionary = {} # "L|bt|cx|cz" → MultiMeshInstance3D
var _last_camera_chunk := Vector2i(-9999, -9999)

const CHUNK := 10.0

# Ground cover (turf tiles) — close range, dense carpet
const TURF_VIS := 14.0
const TURF_LOAD := 18.0
const TURF_UNLOAD := 26.0

# Detail blades — taller, sparser, visible further
const BLADE_VIS := 20.0
const BLADE_LOAD := 25.0
const BLADE_UNLOAD := 35.0
const BLADE_SPREAD := 0.45        # random jitter from grid position (m)
const BLADES_PER_POS := 20        # detail blades expanded per grid position

const TURF_NAMES: Array = ["Turf_Lawn", "Turf_Wild", "Turf_Shade", "Turf_Sedge"]
const BLADE_NAMES: Array = ["Blade_Lawn", "Blade_Wild", "Blade_Shade", "Blade_Sedge"]
const TURF_VARIANTS := 5

# Grass type (0-9) → model index (0=Lawn, 1=Wild, 2=Shade, 3=Sedge)
const TYPE_TO_MODEL: Array = [
	0, 0, 0, 0, 0,  # types 0-4 → Lawn
	2, 2,            # types 5-6 → Shade
	3,               # type 7 → Sedge
	1,               # type 8 → Wild
	0,               # type 9 → Lawn
]


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()

	_grass_shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")

	# Load turf tile meshes (4 types × 5 variants)
	var turf_loaded := 0
	for ti in TURF_NAMES.size():
		var variants: Array = []
		for vi in TURF_VARIANTS:
			var name := "%s_v%d" % [TURF_NAMES[ti], vi]
			var mesh: Mesh = _load_model(name)
			variants.append(mesh)
			if mesh != null:
				turf_loaded += 1
		_turf_meshes[ti] = variants
	print("Grass: %d/%d turf variants loaded" % [turf_loaded, TURF_NAMES.size() * TURF_VARIANTS])

	# Load individual blade meshes (4 types)
	var blade_loaded := 0
	for bname in BLADE_NAMES:
		var mesh: Mesh = _load_model(bname)
		_blade_meshes.append(mesh)
		if mesh != null:
			blade_loaded += 1
	print("Grass: %d/%d blade meshes loaded" % [blade_loaded, BLADE_NAMES.size()])

	if turf_loaded == 0 and blade_loaded == 0:
		print("Grass: no meshes available — run make_ground_cover.py + make_blade_mesh.py")
		return

	# Load data files
	var turf_data := _load_binary("res://ground_cover_instances.bin", 0x47524332)
	if not turf_data.is_empty():
		_organize_by_chunk(turf_data, _turf_by_chunk)
		print("Grass: %d turf positions in %d chunks" % [turf_data[0].size(), _turf_by_chunk.size()])

	var blade_data := _load_binary("res://grass_instances.bin", 0x47525332)
	if not blade_data.is_empty():
		_organize_by_chunk(blade_data, _blade_by_chunk)
		print("Grass: %d blade positions in %d chunks" % [blade_data[0].size(), _blade_by_chunk.size()])

	print("Grass: ready (%.0fms)" % [Time.get_ticks_msec() - t0])

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
	var cam_cx := int(floorf(pos.x / CHUNK))
	var cam_cz := int(floorf(pos.z / CHUNK))

	# Determine needed chunks for each layer
	var turf_needed: Dictionary = {}
	var blade_needed: Dictionary = {}
	var max_load := int(ceili(maxf(TURF_LOAD, BLADE_LOAD) / CHUNK))

	for dx in range(-max_load, max_load + 1):
		for dz in range(-max_load, max_load + 1):
			var cx := cam_cx + dx
			var cz := cam_cz + dz
			var chunk_center := Vector3((cx + 0.5) * CHUNK, 0, (cz + 0.5) * CHUNK)
			var dist := chunk_center.distance_to(pos)
			var ck := "%d|%d" % [cx, cz]
			if dist <= TURF_LOAD and _turf_by_chunk.has(ck):
				turf_needed[ck] = true
			if dist <= BLADE_LOAD and _blade_by_chunk.has(ck):
				blade_needed[ck] = true

	# Unload distant chunks
	var to_remove: Array = []
	for key in _active_chunks:
		var parts := key.split("|")
		var layer := parts[0]
		# Extract cx,cz from key — turf: "T|type|variant|cx|cz", blade: "B|type|cx|cz"
		var cx_str: String; var cz_str: String
		if layer == "T" and parts.size() >= 5:
			cx_str = parts[3]; cz_str = parts[4]
		elif parts.size() >= 4:
			cx_str = parts[2]; cz_str = parts[3]
		else:
			continue
		var chunk_center := Vector3((int(cx_str) + 0.5) * CHUNK, 0, (int(cz_str) + 0.5) * CHUNK)
		var dist := chunk_center.distance_to(pos)
		var unload_range := TURF_UNLOAD if layer == "T" else BLADE_UNLOAD
		if dist > unload_range:
			var mmi: MultiMeshInstance3D = _active_chunks[key]
			mmi.queue_free()
			to_remove.append(key)
	for key in to_remove:
		_active_chunks.erase(key)

	# Load new turf chunks
	var turf_built := 0
	for ck in turf_needed:
		if not _has_layer_chunk("T", ck):
			_build_turf_chunk(ck)
			turf_built += 1

	# Load new blade chunks
	var blade_built := 0
	for ck in blade_needed:
		if not _has_layer_chunk("B", ck):
			_build_blade_chunk(ck)
			blade_built += 1

	if turf_built + blade_built + to_remove.size() > 0:
		print("Grass: +%dT +%dB -%d (active: %d)" % [
			turf_built, blade_built, to_remove.size(), _active_chunks.size()])


func _has_layer_chunk(layer: String, ck: String) -> bool:
	# Key format: "T|type|variant|cx|cz" (turf) or "B|type|cx|cz" (blade)
	for key in _active_chunks:
		var parts := key.split("|")
		if parts[0] != layer:
			continue
		if layer == "T" and parts.size() >= 5:
			if "%s|%s" % [parts[3], parts[4]] == ck:
				return true
		elif layer == "B" and parts.size() >= 4:
			if "%s|%s" % [parts[2], parts[3]] == ck:
				return true
	return false


func _build_turf_chunk(ck: String) -> void:
	var positions: Array = _turf_by_chunk[ck]
	if positions.is_empty():
		return

	# Group by (model_type, variant) for separate MultiMeshes
	var by_group: Dictionary = {}  # "type|variant" → {xf: [], cd: []}

	for pos_data in positions:
		var wx: float = pos_data["x"]
		var wz: float = pos_data["z"]
		var wy: float = pos_data["y"]
		var orig_type: int = pos_data["type"]
		var prox: int = pos_data["prox"]
		var path_prox: float = float(prox) / 255.0

		var model_type: int = 0
		if orig_type < TYPE_TO_MODEL.size():
			model_type = TYPE_TO_MODEL[orig_type]

		# Pick variant deterministically from position
		var variant: int = int(abs(wx * 73.1 + wz * 97.3)) % TURF_VARIANTS
		var variants: Array = _turf_meshes.get(model_type, [])
		if variant >= variants.size() or variants[variant] == null:
			continue

		var gk := "%d|%d" % [model_type, variant]
		if not by_group.has(gk):
			by_group[gk] = {"xf": [], "cd": [], "type": model_type, "variant": variant}

		# Random Y rotation, no XZ scale (preserve coverage), slight Y scale for variety
		var y_rot: float = fmod(abs(wx * 193.7 + wz * 47.9), TAU)
		var basis := Basis(Vector3.UP, y_rot)
		var tf := Transform3D(basis, Vector3(wx, wy, wz))

		by_group[gk]["xf"].append(tf)
		# INSTANCE_CUSTOM: r=grass_type, g=rng_seed, b=path_prox, a=1.0 (turf flag)
		by_group[gk]["cd"].append(Color(float(orig_type), fmod(abs(wx * 31.7 + wz * 59.3), 1.0), path_prox, 1.0))

	# Create MultiMesh per group
	for gk in by_group:
		var data: Dictionary = by_group[gk]
		var xf_list: Array = data["xf"]
		var cd_list: Array = data["cd"]
		if xf_list.is_empty():
			continue

		var model_type: int = data["type"]
		var variant: int = data["variant"]
		var mesh: Mesh = _turf_meshes[model_type][variant]

		# Compute chunk center for local coordinates
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
		mmi.name = "Turf_%d_v%d_%s" % [model_type, variant, ck]
		mmi.visibility_range_end = TURF_VIS
		mmi.visibility_range_end_margin = TURF_VIS * 0.35
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		_active_chunks["T|%s|%s" % [gk, ck]] = mmi


func _build_blade_chunk(ck: String) -> void:
	var positions: Array = _blade_by_chunk[ck]
	if positions.is_empty():
		return

	var by_type: Dictionary = {}  # blade_type → {xf: [], cd: []}
	var rng := RandomNumberGenerator.new()

	for pos_data in positions:
		var wx: float = pos_data["x"]
		var wz: float = pos_data["z"]
		var wy: float = pos_data["y"]
		var orig_type: int = pos_data["type"]
		var prox: int = pos_data["prox"]
		var path_prox: float = float(prox) / 255.0

		var blade_type: int = 0
		if orig_type < TYPE_TO_MODEL.size():
			blade_type = TYPE_TO_MODEL[orig_type]
		if blade_type >= _blade_meshes.size() or _blade_meshes[blade_type] == null:
			continue

		rng.seed = int(abs(wx) * 73856.0 + abs(wz) * 19349.0) & 0x7FFFFFFF

		if not by_type.has(blade_type):
			by_type[blade_type] = {"xf": [], "cd": []}

		for _b in BLADES_PER_POS:
			var bx: float = wx + rng.randf_range(-BLADE_SPREAD, BLADE_SPREAD)
			var bz: float = wz + rng.randf_range(-BLADE_SPREAD, BLADE_SPREAD)
			var y_rot: float = rng.randf() * TAU
			var h_scale: float = rng.randf_range(0.7, 1.3)
			if path_prox > 0.1:
				h_scale *= lerpf(1.0, 0.4, path_prox)

			var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(1.0, h_scale, 1.0))
			var tf := Transform3D(basis, Vector3(bx, wy, bz))

			by_type[blade_type]["xf"].append(tf)
			# INSTANCE_CUSTOM: r=grass_type, g=rng_seed, b=path_prox, a=0.0 (blade flag)
			by_type[blade_type]["cd"].append(Color(float(orig_type), rng.randf(), path_prox, 0.0))

	# Create MultiMesh per blade type
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
		mmi.name = "Blade_%d_%s" % [blade_type, ck]
		mmi.visibility_range_end = BLADE_VIS
		mmi.visibility_range_end_margin = BLADE_VIS * 0.40
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		_active_chunks["B|%d|%s" % [blade_type, ck]] = mmi


func _load_model(model_name: String) -> Mesh:
	var abs_path := ProjectSettings.globalize_path("res://models/vegetation/%s.glb" % model_name)
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


func _organize_by_chunk(instances: Array, out_dict: Dictionary) -> void:
	var x_arr: PackedFloat32Array = instances[0]
	var z_arr: PackedFloat32Array = instances[1]
	var type_arr: PackedByteArray = instances[2]
	var y_arr: PackedFloat32Array = instances[3]
	var prox_arr: PackedByteArray = instances[4]

	for i in x_arr.size():
		var cx := int(floorf(x_arr[i] / CHUNK))
		var cz := int(floorf(z_arr[i] / CHUNK))
		var ck := "%d|%d" % [cx, cz]
		if not out_dict.has(ck):
			out_dict[ck] = []
		out_dict[ck].append({
			"x": x_arr[i], "z": z_arr[i], "y": y_arr[i],
			"type": type_arr[i], "prox": prox_arr[i]
		})


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
	print("  Loaded %d positions from %s" % [cnt, res_path])
	return [x_a, z_a, type_a, y_a, prox_a]
