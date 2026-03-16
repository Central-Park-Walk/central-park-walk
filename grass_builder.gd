# grass_builder.gd
# Individual-blade grass system (hexaquo approach).
#
# Each grass blade is a separate MultiMesh instance with its own transform.
# Blade positions generated from prebaked tile positions + random offsets.
# The shader uses NODE_POSITION_WORLD for per-blade patchiness, wind, color.
#
# 4 blade meshes: Lawn, Wild, Shade, Sedge (single curved blades with
# cylinder-derived normals from Blender).
#
# Positions from convert_to_godot.py → ground_cover_instances.bin

var _loader

const CHUNK := 40.0
const BLADES_PER_POSITION := 30  # individual blades per prebaked grid position (~20/m²)

# Blade meshes — one curved blade per type
const BLADE_NAMES: Array = [
	"Blade_Lawn",   # 0
	"Blade_Wild",   # 1
	"Blade_Shade",  # 2
	"Blade_Sedge",  # 3
]

# Map detail type (0-9) → blade mesh (0-3)
const TYPE_TO_BLADE: Array = [
	0,  # SheepMeadow   → Lawn
	0,  # GreatLawn     → Lawn
	0,  # NorthMeadow   → Lawn
	0,  # FormalGarden   → Lawn
	0,  # SportsTurf    → Lawn
	2,  # NorthWoods    → Shade
	2,  # Ramble        → Shade
	3,  # Waterside     → Sedge
	1,  # WildMeadow    → Wild
	0,  # OpenLawn      → Lawn
]

const BLADE_VIS_RANGES: Array = [
	16.0,  # lawn
	18.0,  # wild (taller, visible further)
	12.0,  # shade
	15.0,  # sedge
]


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()

	var grass_shader: Shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")

	# Load 4 blade meshes
	var blade_meshes: Array = []
	var loaded := 0
	for bname in BLADE_NAMES:
		var mesh: Mesh = _load_blade_model(bname, grass_shader)
		blade_meshes.append(mesh)
		if mesh != null:
			loaded += 1

	if loaded == 0:
		print("Grass: no blade meshes found — run make_blade_mesh.py in Blender")
		return

	# Load prebaked positions
	var instances: Array = _load_binary("res://ground_cover_instances.bin", 0x47524332)
	if instances.is_empty():
		print("Grass: no ground cover instances — run convert_to_godot.py")
		return

	var x_arr: PackedFloat32Array = instances[0]
	var z_arr: PackedFloat32Array = instances[1]
	var type_arr: PackedByteArray = instances[2]
	var count: int = x_arr.size()
	var has_v2 := instances.size() >= 5
	var y_arr: PackedFloat32Array
	var prox_arr: PackedByteArray
	if has_v2:
		y_arr = instances[3]
		prox_arr = instances[4]

	# Generate individual blade instances from prebaked tile positions
	var chunks: Dictionary = {}
	var total := 0
	var rng := RandomNumberGenerator.new()

	for i in count:
		var wx: float = x_arr[i]
		var wz: float = z_arr[i]
		var orig_type: int = type_arr[i]

		var blade_type: int = 0
		if orig_type < TYPE_TO_BLADE.size():
			blade_type = TYPE_TO_BLADE[orig_type]
		if blade_type >= blade_meshes.size() or blade_meshes[blade_type] == null:
			continue

		var wy: float = y_arr[i] if has_v2 else 0.002
		var path_prox: float = (float(prox_arr[i]) / 255.0) if has_v2 else 0.0

		# Seed from position for deterministic blade placement
		rng.seed = int(abs(wx) * 73856.0 + abs(wz) * 19349.0) & 0x7FFFFFFF

		# Generate N individual blades around this position
		for _b in BLADES_PER_POSITION:
			var bx: float = wx + rng.randf_range(-0.55, 0.55)
			var bz: float = wz + rng.randf_range(-0.55, 0.55)
			var y_rot: float = rng.randf() * TAU
			# Height scale from patchiness — varies per blade
			var h_scale: float = rng.randf_range(0.7, 1.3)
			if path_prox > 0.1:
				h_scale *= lerpf(1.0, 0.4, path_prox)

			var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(1.0, h_scale, 1.0))
			var tf := Transform3D(basis, Vector3(bx, wy, bz))

			var cx := int(floorf(bx / CHUNK))
			var cz := int(floorf(bz / CHUNK))
			var ck := "%d|%d|%d" % [blade_type, cx, cz]
			if not chunks.has(ck):
				chunks[ck] = {"type": blade_type, "xf": [], "cd": []}
			chunks[ck]["xf"].append(tf)
			chunks[ck]["cd"].append(Color(float(orig_type), rng.randf(), path_prox, 0.0))
			total += 1

	# Build MultiMesh per chunk
	var chunk_count := 0
	for ck in chunks:
		var info: Dictionary = chunks[ck]
		var btype: int = info["type"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue

		var mesh: Mesh = blade_meshes[btype]
		var vis_end: float = BLADE_VIS_RANGES[btype] if btype < BLADE_VIS_RANGES.size() else 16.0

		var sx := 0.0; var sy := 0.0; var sz := 0.0
		for tf: Transform3D in xf_list:
			sx += tf.origin.x
			sy += tf.origin.y
			sz += tf.origin.z
		var n := float(xf_list.size())
		var chunk_origin := Vector3(sx / n, sy / n, sz / n)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = xf_list.size()
		for j in xf_list.size():
			var tf: Transform3D = xf_list[j]
			mm.set_instance_transform(j, Transform3D(tf.basis, tf.origin - chunk_origin))
			mm.set_instance_custom_data(j, cd_list[j])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = chunk_origin
		mmi.name = "Grass_%s" % ck.replace("|", "_")
		mmi.visibility_range_end = vis_end
		mmi.visibility_range_end_margin = vis_end * 0.40
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_count += 1

	var elapsed := Time.get_ticks_msec() - t0
	print("Grass: %d blades (%d chunks) in %.1fs" % [total, chunk_count, elapsed / 1000.0])


func _load_blade_model(bname: String, shader: Shader) -> Mesh:
	var abs_path := ProjectSettings.globalize_path("res://models/vegetation/%s.glb" % bname)
	if not FileAccess.file_exists(abs_path):
		return null
	var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
	if meshes.is_empty():
		return null
	var mesh: Mesh = meshes.values()[0]
	for si in mesh.get_surface_count():
		var new_mat := ShaderMaterial.new()
		new_mat.shader = shader
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
