# grass_builder.gd
# Data-driven grass system based on real Central Park vegetation zones.
# Three grass types reflecting actual ground cover:
#   Type 0 — Lawn: Kentucky bluegrass (Sheep Meadow, Great Lawn, etc.)
#   Type 1 — Woodland floor: shade-adapted understory (North Woods, Ramble)
#   Type 2 — Wild meadow: unmowed nature reserve areas
# Density inversely proportional to canopy density (from Conservancy data).
# Positions prebaked in convert_to_godot.py → grass_instances.bin.

var _loader  # Reference to park_loader for shared utilities

const CHUNK := 40.0      # spatial chunk size in metres
const VIS_LAWN := 80.0   # lawn visibility — larger patches, farther vis
const VIS_WOOD := 50.0   # woodland — sparser, less vis needed
const VIS_MEADOW := 70.0 # meadow — moderate


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()

	var grass_shader: Shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")

	# Load Blender-built patch models (3 types)
	var lawn_mesh: Mesh = _load_patch_model("Grass_Patch_Lawn", grass_shader)
	var woodland_mesh: Mesh = _load_patch_model("Grass_Patch_Woodland", grass_shader)
	var meadow_mesh: Mesh = _load_patch_model("Grass_Patch_Meadow", grass_shader)

	# Fallback: try old names if new ones not found
	if lawn_mesh == null:
		lawn_mesh = _load_patch_model("Grass_Patch_Mowed", grass_shader)
	if meadow_mesh == null and woodland_mesh == null and lawn_mesh == null:
		print("Grass: no patch models loaded — skipping")
		return

	# Read prebaked instance positions
	var instances: Array = _load_instances()
	if instances.is_empty():
		print("Grass: no prebaked instances — skipping")
		return

	var x_arr: PackedFloat32Array = instances[0]
	var z_arr: PackedFloat32Array = instances[1]
	var type_arr: PackedByteArray = instances[2]
	var count: int = x_arr.size()

	# Map type → mesh and visibility range
	var mesh_for_type: Array = [lawn_mesh, woodland_mesh, meadow_mesh]
	var vis_for_type: Array = [VIS_LAWN, VIS_WOOD, VIS_MEADOW]
	var prefix_for_type: Array = ["l", "w", "m"]

	# Build transforms and group by type + spatial chunk
	var chunks: Dictionary = {}
	var total := 0
	var rng := RandomNumberGenerator.new()

	for i in count:
		var wx: float = x_arr[i]
		var wz: float = z_arr[i]
		var gtype: int = type_arr[i]

		# Clamp to valid type range
		if gtype > 2:
			gtype = 0

		# Skip if we don't have the model for this type
		var mesh: Mesh = mesh_for_type[gtype]
		if mesh == null:
			continue

		# Terrain height
		var wy: float = _loader._terrain_y(wx, wz) + 0.002

		# Deterministic rotation + scale from position hash
		rng.seed = int(wx * 73856.0 + wz * 19349.0) & 0x7FFFFFFF
		var y_rot := rng.randf() * TAU
		var s := rng.randf_range(0.85, 1.15)
		var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(s, s, s))
		var tf := Transform3D(basis, Vector3(wx, wy, wz))

		var grass_type_f := float(gtype)
		var cx := int(floorf(wx / CHUNK))
		var cz := int(floorf(wz / CHUNK))
		var tk: String = prefix_for_type[gtype]
		var ck := "%s|%d|%d" % [tk, cx, cz]
		if not chunks.has(ck):
			chunks[ck] = {"type": gtype, "tk": tk, "xf": [], "cd": []}
		chunks[ck]["xf"].append(tf)
		chunks[ck]["cd"].append(Color(grass_type_f, rng.randf(), 0.0, 0.0))
		total += 1

	# Build MultiMesh per chunk
	var chunk_count := 0
	for ck in chunks:
		var info: Dictionary = chunks[ck]
		var gtype: int = info["type"]
		var tk: String = info["tk"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue

		var mesh: Mesh = mesh_for_type[gtype]
		var vis_end: float = vis_for_type[gtype]

		# Compute chunk centroid for positioning
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
		for i in xf_list.size():
			var tf: Transform3D = xf_list[i]
			mm.set_instance_transform(i, Transform3D(tf.basis, tf.origin - chunk_origin))
			mm.set_instance_custom_data(i, cd_list[i])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = chunk_origin
		mmi.name = "Grass_%s" % ck.replace("|", "_")
		mmi.visibility_range_end = vis_end
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_count += 1

	print("Grass: %d patches (%d chunks) in %.0fms" % [
		total, chunk_count, Time.get_ticks_msec() - t0])


func _load_patch_model(mname: String, shader: Shader) -> Mesh:
	## Load a grass patch GLB, replace material with wind shader, return mesh.
	## Vertex colors in the model are preserved — shader uses COLOR as albedo.
	var path := "res://models/vegetation/%s.glb" % mname
	var abs_path := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		print("WARNING: grass model not found: %s" % abs_path)
		return null

	var gltf_doc := GLTFDocument.new()
	var gltf_state := GLTFState.new()
	var err := gltf_doc.append_from_file(abs_path, gltf_state)
	if err != OK:
		print("WARNING: failed to load GLB %s (error %d)" % [abs_path, err])
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

	# Replace each surface material with wind-responsive shader
	for si in mesh.get_surface_count():
		var new_mat := ShaderMaterial.new()
		new_mat.shader = shader
		mesh.surface_set_material(si, new_mat)

	root.queue_free()
	print("Grass: loaded %s — aabb %s, %d surfaces" % [
		mname, aabb.size, mesh.get_surface_count()])
	return mesh


func _load_instances() -> Array:
	## Read prebaked grass_instances.bin → [x_arr, z_arr, type_arr]
	## Format: uint32 count, float32[N] x, float32[N] z, uint8[N] type
	## Type: 0=lawn, 1=woodland, 2=meadow
	for path in ["res://grass_instances.bin"]:
		var abs_path := ProjectSettings.globalize_path(path)
		var f := FileAccess.open(abs_path, FileAccess.READ)
		if f == null:
			f = FileAccess.open(path, FileAccess.READ)
		if f == null:
			print("WARNING: grass_instances.bin not found")
			return []

		var count: int = f.get_32()
		if count == 0:
			return []

		var x_arr := PackedFloat32Array()
		x_arr.resize(count)
		var z_arr := PackedFloat32Array()
		z_arr.resize(count)
		var type_arr := PackedByteArray()
		type_arr.resize(count)

		var x_bytes := f.get_buffer(count * 4)
		var z_bytes := f.get_buffer(count * 4)
		var t_bytes := f.get_buffer(count)

		for j in count:
			x_arr[j] = x_bytes.decode_float(j * 4)
			z_arr[j] = z_bytes.decode_float(j * 4)
			type_arr[j] = t_bytes[j]

		print("Grass: loaded %d prebaked instances" % count)
		return [x_arr, z_arr, type_arr]

	return []
