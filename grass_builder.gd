# grass_builder.gd
# Wind-responsive 3D vegetation scattered across grass terrain surfaces.
# Uses Quaternius CC0 GLTF models (grass, clover, wildflowers) with wind shader.
# Model mix varies by landuse zone: mowed lawn vs wild meadow.

var _loader  # Reference to park_loader for shared utilities

# Landuse raw data for fast zone queries (from landuse_map.png)
var _landuse_data: PackedByteArray
var _landuse_res: int = 0

const CHUNK := 40.0      # spatial chunk size in metres
const VIS_END := 120.0   # grass beyond this distance not rendered
const STRIDE := 3        # sample every Nth atlas cell (~1.83m spacing)

# Model specs: [filename, target_h_min, target_h_max, selection_weight]
const MOWED_SPECS := [
	["Grass_Common_Short", 0.10, 0.18, 55],
	["Grass_Wispy_Short",  0.08, 0.15, 25],
	["Clover_1",           0.05, 0.10, 12],
	["Clover_2",           0.05, 0.10,  8],
]
const MEADOW_SPECS := [
	["Grass_Wispy_Tall",   0.30, 0.50, 40],
	["Grass_Common_Tall",  0.25, 0.40, 25],
	["Flower_3_Group",     0.18, 0.30, 20],
	["Flower_4_Group",     0.18, 0.30, 15],
]


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()
	_load_landuse()

	# Load all vegetation GLTF models and apply wind shader
	var grass_shader: Shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")
	var models: Dictionary = {}  # name -> { "mesh": Mesh, "raw_h": float }

	for specs in [MOWED_SPECS, MEADOW_SPECS]:
		for spec in specs:
			var mname: String = spec[0]
			if models.has(mname):
				continue
			var info: Variant = _load_veg_model(mname, grass_shader)
			if info:
				models[mname] = info

	if models.is_empty():
		print("Grass: no vegetation models loaded — skipping")
		return

	# Build flat weight tables for O(1) random selection
	var mowed_table := _build_weight_table(MOWED_SPECS, models)
	var meadow_table := _build_weight_table(MEADOW_SPECS, models)
	if mowed_table.is_empty() and meadow_table.is_empty():
		print("Grass: no valid models for any zone — skipping")
		return

	# Atlas data for surface queries
	var res: int = _loader._atlas_res
	var data: PackedByteArray = _loader._atlas_data
	if data.is_empty() or res == 0:
		print("Grass: no atlas data — skipping")
		return

	var ws: float = _loader._hm_world_size
	var half := ws * 0.5
	var cell_m := ws / float(res)

	# Collect instances grouped by model + spatial chunk
	# Key: "model|cx|cz" -> { "xf": Array, "cd": Array }
	var chunks: Dictionary = {}
	var total := 0
	var rng := RandomNumberGenerator.new()

	for gz in range(0, res, STRIDE):
		for gx in range(0, res, STRIDE):
			var idx := (gz * res + gx) * 2
			var surf: int = data[idx]
			if surf != 1:  # not grass
				continue
			var occ: int = data[idx + 1]
			if occ & 0x1F != 0:  # occupied (tree, bench, lamp, trash, barrier)
				continue

			# World position with deterministic jitter
			rng.seed = gx * 73856093 + gz * 19349663
			var wx := float(gx) * cell_m - half + rng.randf_range(-0.4, 0.4) * cell_m
			var wz := float(gz) * cell_m - half + rng.randf_range(-0.4, 0.4) * cell_m

			# Determine grass type from landuse zone
			var zone := _landuse_at(wx, wz)
			if zone == 4 or zone == 6 or zone == 8 or zone == 9:
				continue
			var is_meadow := (zone == 5 or zone == 10 or zone == 11)

			# Pick model from weighted table
			var table: Array = meadow_table if is_meadow else mowed_table
			if table.is_empty():
				continue
			var pick: Array = table[rng.randi() % table.size()]
			var mname: String = pick[0]
			var h_min: float = pick[1]
			var h_max: float = pick[2]

			var info: Dictionary = models[mname]
			var raw_h: float = info["raw_h"]

			# Terrain height
			var wy: float = _loader._terrain_y(wx, wz) + 0.005

			# Scale to target real-world height
			var target_h := rng.randf_range(h_min, h_max)
			var scale_y := target_h / raw_h
			var scale_xz := scale_y * rng.randf_range(0.85, 1.15)
			var y_rot := rng.randf() * TAU
			var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(scale_xz, scale_y, scale_xz))
			var tf := Transform3D(basis, Vector3(wx, wy, wz))

			var grass_type := 1.0 if is_meadow else 0.0
			var cx := int(floorf(wx / CHUNK))
			var cz := int(floorf(wz / CHUNK))
			var ck := "%s|%d|%d" % [mname, cx, cz]
			if not chunks.has(ck):
				chunks[ck] = {"model": mname, "xf": [], "cd": []}
			chunks[ck]["xf"].append(tf)
			chunks[ck]["cd"].append(Color(grass_type, rng.randf(), 0.0, 0.0))
			total += 1

	# Build MultiMesh per model+chunk
	var chunk_count := 0
	for ck in chunks:
		var info: Dictionary = chunks[ck]
		var mname: String = info["model"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue

		var mesh: Mesh = models[mname]["mesh"]

		# Compute chunk centroid for visibility culling
		var cx_sum := 0.0; var cy_sum := 0.0; var cz_sum := 0.0
		for tf: Transform3D in xf_list:
			cx_sum += tf.origin.x
			cy_sum += tf.origin.y
			cz_sum += tf.origin.z
		var n := float(xf_list.size())
		var chunk_origin := Vector3(cx_sum / n, cy_sum / n, cz_sum / n)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = xf_list.size()
		for i in xf_list.size():
			var tf: Transform3D = xf_list[i]
			mm.set_instance_transform(i, Transform3D(tf.basis, tf.origin - chunk_origin))
			mm.set_instance_custom_data(i, cd_list[i])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = chunk_origin
		mmi.name = "Grass_%s" % ck.replace("|", "_")
		mmi.visibility_range_end = VIS_END
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_count += 1

	print("Grass: %d clumps (%d models, %d chunks) in %.0fms" % [
		total, models.size(), chunk_count, Time.get_ticks_msec() - t0])


func _load_veg_model(mname: String, shader: Shader) -> Variant:
	## Load a vegetation GLTF, replace materials with wind shader, return mesh + raw height.
	var path := "res://models/vegetation/%s.gltf" % mname
	var abs_path := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		print("WARNING: vegetation model not found: %s" % abs_path)
		return null

	var gltf_doc := GLTFDocument.new()
	var gltf_state := GLTFState.new()
	var err := gltf_doc.append_from_file(abs_path, gltf_state)
	if err != OK:
		print("WARNING: failed to load GLTF %s (error %d)" % [abs_path, err])
		return null

	var root: Node = gltf_doc.generate_scene(gltf_state)
	if root == null:
		return null

	var meshes: Array = []
	_loader._collect_meshes(root, meshes)
	if meshes.is_empty():
		root.queue_free()
		return null

	var mesh: Mesh = meshes[0]
	var aabb: AABB = mesh.get_aabb()
	var raw_h: float = aabb.size.y
	if raw_h < 0.001:
		raw_h = maxf(aabb.size.x, maxf(aabb.size.y, aabb.size.z))

	# Replace each surface material with our wind-responsive shader
	for si in mesh.get_surface_count():
		var smat: Material = mesh.surface_get_material(si)
		var tex: Texture2D = null
		var alpha := 0.0
		if smat is StandardMaterial3D:
			var sm: StandardMaterial3D = smat as StandardMaterial3D
			tex = sm.albedo_texture
			if sm.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
				alpha = sm.alpha_scissor_threshold
		var new_mat := ShaderMaterial.new()
		new_mat.shader = shader
		if tex:
			new_mat.set_shader_parameter("albedo_tex", tex)
		new_mat.set_shader_parameter("alpha_scissor", alpha)
		mesh.surface_set_material(si, new_mat)

	root.queue_free()
	print("Grass: loaded %s — raw_h=%.3f, %d surfaces" % [mname, raw_h, mesh.get_surface_count()])
	return {"mesh": mesh, "raw_h": raw_h}


func _build_weight_table(specs: Array, models: Dictionary) -> Array:
	## Build a flat array of [model_name, h_min, h_max] entries, repeated by weight.
	## Selection is O(1): table[randi() % table.size()].
	var table: Array = []
	for spec in specs:
		var mname: String = spec[0]
		if not models.has(mname):
			continue
		var weight: int = int(spec[3])
		for _i in weight:
			table.append([mname, spec[1], spec[2]])
	return table


func _load_landuse() -> void:
	## Load landuse_map.png as raw bytes for fast zone queries.
	for path in ["res://landuse_map.png"]:
		var img: Image = null
		if FileAccess.file_exists(path):
			img = Image.load_from_file(path)
		else:
			var global_path := ProjectSettings.globalize_path(path)
			if FileAccess.file_exists(global_path):
				img = Image.load_from_file(global_path)
		if img:
			if img.get_format() != Image.FORMAT_R8:
				img.convert(Image.FORMAT_R8)
			_landuse_data = img.get_data()
			_landuse_res = img.get_width()
			return


func _landuse_at(wx: float, wz: float) -> int:
	## Returns landuse zone ID at world position.
	if _landuse_data.is_empty():
		return 0
	var half: float = _loader._hm_world_size * 0.5
	var scale: float = float(_landuse_res) / _loader._hm_world_size
	var px := clampi(int((wx + half) * scale), 0, _landuse_res - 1)
	var pz := clampi(int((wz + half) * scale), 0, _landuse_res - 1)
	return _landuse_data[pz * _landuse_res + px]
