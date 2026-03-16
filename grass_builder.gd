# grass_builder.gd
# Two-layer grass system: ground cover (turf carpet) + detail blades.
#
# Layer 1: Ground cover — low, outward-leaning turf tiles that carpet the
#   terrain. Dense placement (stride 2). Provides continuous green mass.
#   4 turf types: Lawn, Wild, Shade, Sedge.
#
# Layer 2: Detail blades — taller individual grass tiles for visual depth,
#   wind animation, wildflowers. Sparser placement (stride 2-8).
#   10 types from Conservancy ABCD lawn data.
#
# Both layers use the same grass_blade shader and share type-based coloring.
# The green terrain shader base carries color beyond visibility range.
#
# Positions prebaked in convert_to_godot.py:
#   grass_instances.bin        — detail blade positions
#   ground_cover_instances.bin — ground cover positions

var _loader  # Reference to park_loader for shared utilities

const CHUNK := 40.0       # spatial chunk size in metres

# --- Detail blade layer (10 types) ---
const MODEL_NAMES: Array = [
	"Grass_Tile_SheepMeadow",   # 0
	"Grass_Tile_GreatLawn",     # 1
	"Grass_Tile_NorthMeadow",   # 2
	"Grass_Tile_FormalGarden",  # 3
	"Grass_Tile_SportsTurf",    # 4
	"Grass_Tile_NorthWoods",    # 5
	"Grass_Tile_Ramble",        # 6
	"Grass_Tile_Waterside",     # 7
	"Grass_Tile_WildMeadow",    # 8
	"Grass_Tile_OpenLawn",      # 9
]

const VIS_RANGES: Array = [
	80.0,  # sheep_meadow
	80.0,  # great_lawn
	70.0,  # north_meadow
	70.0,  # formal_garden
	70.0,  # sports_turf
	50.0,  # north_woods
	50.0,  # ramble
	60.0,  # waterside
	60.0,  # wild_meadow
	70.0,  # open_lawn
]

# --- Ground cover layer (4 turf types) ---
const TURF_NAMES: Array = [
	"Turf_Lawn",    # 0 — mowed lawn carpet
	"Turf_Wild",    # 1 — wild meadow ground cover
	"Turf_Shade",   # 2 — woodland floor cover
	"Turf_Sedge",   # 3 — waterside ground cover
]

# Map detail type (0-9) → turf type (0-3)
const TYPE_TO_TURF: Array = [
	0,  # SheepMeadow   → Turf_Lawn
	0,  # GreatLawn     → Turf_Lawn
	0,  # NorthMeadow   → Turf_Lawn
	0,  # FormalGarden   → Turf_Lawn
	0,  # SportsTurf    → Turf_Lawn
	2,  # NorthWoods    → Turf_Shade
	2,  # Ramble        → Turf_Shade
	3,  # Waterside     → Turf_Sedge
	1,  # WildMeadow    → Turf_Wild
	0,  # OpenLawn      → Turf_Lawn
]

# Ground cover visibility: shorter range since terrain carries green beyond
const TURF_VIS_RANGES: Array = [
	50.0,  # lawn — moderate range, terrain matches well
	45.0,  # wild
	35.0,  # shade — short range, dark under canopy
	40.0,  # sedge
]


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()

	var grass_shader: Shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")

	# --- Load detail blade models (10 types) ---
	var meshes: Array = []
	var loaded := 0
	for mname in MODEL_NAMES:
		var mesh: Mesh = _load_tile_model(mname, grass_shader)
		meshes.append(mesh)
		if mesh != null:
			loaded += 1

	if loaded == 0:
		var old_mesh: Mesh = _load_tile_model("Grass_Patch_Lawn", grass_shader)
		if old_mesh == null:
			print("Grass: no tile models loaded — skipping")
			return
		for i in meshes.size():
			if meshes[i] == null:
				meshes[i] = old_mesh

	# --- Load ground cover models (4 types) ---
	var turf_meshes: Array = []
	var turf_loaded := 0
	for tname in TURF_NAMES:
		var mesh: Mesh = _load_tile_model(tname, grass_shader)
		turf_meshes.append(mesh)
		if mesh != null:
			turf_loaded += 1

	# --- Build detail blade layer ---
	var instances: Array = _load_binary("res://grass_instances.bin", 0x47525332)  # "GRS2"
	var detail_total := 0
	var detail_chunks := 0
	if not instances.is_empty():
		var result := _build_layer(instances, meshes, VIS_RANGES, "Grass")
		detail_total = result[0]
		detail_chunks = result[1]

	# --- Build ground cover layer ---
	var gc_total := 0
	var gc_chunks := 0
	if turf_loaded > 0:
		var gc_instances: Array = _load_binary("res://ground_cover_instances.bin", 0x47524332)  # "GRC2"
		if not gc_instances.is_empty():
			# Remap types: detail type (0-9) → turf type (0-3) for mesh selection
			# but keep original type in custom data for shader coloring
			var result := _build_layer_mapped(gc_instances, turf_meshes, TURF_VIS_RANGES, TYPE_TO_TURF, "Turf")
			gc_total = result[0]
			gc_chunks = result[1]
	elif not instances.is_empty():
		print("  Ground cover: no turf models found — skipping (run make_ground_cover.py in Blender)")

	var elapsed := Time.get_ticks_msec() - t0
	print("Grass: %d detail + %d cover = %d tiles (%d chunks) in %.0fms" % [
		detail_total, gc_total, detail_total + gc_total,
		detail_chunks + gc_chunks, elapsed])


func _build_layer(instances: Array, meshes: Array, vis_ranges: Array, prefix: String) -> Array:
	"""Build MultiMesh chunks for a grass layer where type maps directly to mesh index."""
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

	var chunks: Dictionary = {}
	var total := 0
	var rng := RandomNumberGenerator.new()

	for i in count:
		var wx: float = x_arr[i]
		var wz: float = z_arr[i]
		var gtype: int = type_arr[i]

		if gtype >= meshes.size():
			gtype = meshes.size() - 1
		if meshes[gtype] == null:
			continue

		rng.seed = int(wx * 73856.0 + wz * 19349.0) & 0x7FFFFFFF

		var wy: float
		var path_prox: float
		if has_v2:
			wy = y_arr[i]
			path_prox = float(prox_arr[i]) / 255.0
		else:
			wy = _loader._terrain_y(wx, wz) + 0.002
			path_prox = 0.0

		var y_rot := rng.randf() * TAU
		# Heights come from CPC data baked into Blender models — don't override.
		# Tiny natural variation only (±3%), not random scaling.
		var s_xz := rng.randf_range(0.95, 1.05)
		var s_y := rng.randf_range(0.97, 1.03)
		if path_prox > 0.1:
			s_y *= lerpf(1.0, 0.55, path_prox)
		var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(s_xz, s_y, s_xz))
		var tf := Transform3D(basis, Vector3(wx, wy, wz))

		var cx := int(floorf(wx / CHUNK))
		var cz := int(floorf(wz / CHUNK))
		var ck := "%d|%d|%d" % [gtype, cx, cz]
		if not chunks.has(ck):
			chunks[ck] = {"type": gtype, "xf": [], "cd": []}
		chunks[ck]["xf"].append(tf)
		chunks[ck]["cd"].append(Color(float(gtype), rng.randf(), path_prox, 0.0))
		total += 1

	var chunk_count := _emit_multimeshes(chunks, meshes, vis_ranges, prefix)
	return [total, chunk_count]


func _build_layer_mapped(instances: Array, meshes: Array, vis_ranges: Array,
						  type_map: Array, prefix: String) -> Array:
	"""Build MultiMesh chunks where instance type is remapped via type_map for mesh selection,
	   but original type is preserved in custom data for shader coloring."""
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

	var chunks: Dictionary = {}
	var total := 0
	var rng := RandomNumberGenerator.new()

	for i in count:
		var wx: float = x_arr[i]
		var wz: float = z_arr[i]
		var orig_type: int = type_arr[i]

		# Map to mesh type
		var mesh_type: int = 0
		if orig_type < type_map.size():
			mesh_type = type_map[orig_type]
		if mesh_type >= meshes.size() or meshes[mesh_type] == null:
			continue

		rng.seed = int(wx * 99371.0 + wz * 27183.0) & 0x7FFFFFFF

		var wy: float
		var path_prox: float
		if has_v2:
			wy = y_arr[i]
			path_prox = float(prox_arr[i]) / 255.0
		else:
			wy = _loader._terrain_y(wx, wz) + 0.002
			path_prox = 0.0

		var y_rot := rng.randf() * TAU
		var s_xz := rng.randf_range(0.85, 1.25)  # less scale variation for carpet
		var s_y := rng.randf_range(0.80, 1.10)
		if path_prox > 0.1:
			s_y *= lerpf(1.0, 0.40, path_prox)  # more trampled near paths
		var basis := Basis(Vector3.UP, y_rot).scaled(Vector3(s_xz, s_y, s_xz))
		var tf := Transform3D(basis, Vector3(wx, wy, wz))

		var cx := int(floorf(wx / CHUNK))
		var cz := int(floorf(wz / CHUNK))
		# Group by mesh_type for rendering, not orig_type
		var ck := "%d|%d|%d" % [mesh_type, cx, cz]
		if not chunks.has(ck):
			chunks[ck] = {"type": mesh_type, "xf": [], "cd": []}
		chunks[ck]["xf"].append(tf)
		# Store original type in custom data so shader colors correctly
		chunks[ck]["cd"].append(Color(float(orig_type), rng.randf(), path_prox, 0.0))
		total += 1

	var chunk_count := _emit_multimeshes(chunks, meshes, vis_ranges, prefix)
	return [total, chunk_count]


func _emit_multimeshes(chunks: Dictionary, meshes: Array, vis_ranges: Array, prefix: String) -> int:
	"""Create MultiMeshInstance3D nodes from chunk data."""
	var chunk_count := 0
	for ck in chunks:
		var info: Dictionary = chunks[ck]
		var gtype: int = info["type"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue

		var mesh: Mesh = meshes[gtype]
		var vis_end: float = vis_ranges[gtype] if gtype < vis_ranges.size() else 50.0

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
		mmi.name = "%s_%s" % [prefix, ck.replace("|", "_")]
		mmi.visibility_range_end = vis_end
		mmi.visibility_range_end_margin = vis_end * 0.15
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_count += 1

	return chunk_count


func _load_tile_model(mname: String, shader: Shader) -> Mesh:
	var abs_path := ProjectSettings.globalize_path("res://models/vegetation/%s.glb" % mname)
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
	"""Load a grass/ground-cover binary file (v2 format with magic header)."""
	var abs_path := ProjectSettings.globalize_path(res_path)
	var f := FileAccess.open(abs_path, FileAccess.READ)
	if f == null:
		f = FileAccess.open(res_path, FileAccess.READ)
	if f == null:
		return []

	var magic: int = f.get_32()
	# Check for expected magic in either byte order
	var magic_rev: int = ((magic & 0xFF) << 24) | ((magic & 0xFF00) << 8) | ((magic & 0xFF0000) >> 8) | ((magic & 0xFF000000) >> 24)
	if magic != expected_magic and magic_rev != expected_magic:
		# v1 format fallback (magic was count) — only for grass_instances
		if expected_magic == 0x47525332:
			var cnt: int = magic
			if cnt == 0:
				return []
			var x_arr := PackedFloat32Array(); x_arr.resize(cnt)
			var z_arr := PackedFloat32Array(); z_arr.resize(cnt)
			var type_arr := PackedByteArray(); type_arr.resize(cnt)
			var x_bytes := f.get_buffer(cnt * 4)
			var z_bytes := f.get_buffer(cnt * 4)
			var t_bytes := f.get_buffer(cnt)
			for j in cnt:
				x_arr[j] = x_bytes.decode_float(j * 4)
				z_arr[j] = z_bytes.decode_float(j * 4)
				type_arr[j] = t_bytes[j]
			print("  %s: %d instances (v1 — needs re-bake)" % [res_path, cnt])
			return [x_arr, z_arr, type_arr]
		return []

	var cnt: int = f.get_32()
	if cnt == 0:
		return []
	var x_bytes := f.get_buffer(cnt * 4)
	var y_bytes := f.get_buffer(cnt * 4)
	var z_bytes := f.get_buffer(cnt * 4)
	var t_bytes := f.get_buffer(cnt)
	var pp_bytes := f.get_buffer(cnt)

	var x_arr := PackedFloat32Array(); x_arr.resize(cnt)
	var y_arr := PackedFloat32Array(); y_arr.resize(cnt)
	var z_arr := PackedFloat32Array(); z_arr.resize(cnt)
	var type_arr := PackedByteArray(); type_arr.resize(cnt)
	var prox_arr := PackedByteArray(); prox_arr.resize(cnt)
	for j in cnt:
		x_arr[j] = x_bytes.decode_float(j * 4)
		y_arr[j] = y_bytes.decode_float(j * 4)
		z_arr[j] = z_bytes.decode_float(j * 4)
		type_arr[j] = t_bytes[j]
		prox_arr[j] = pp_bytes[j]
	print("  %s: %d instances (v2)" % [res_path, cnt])
	return [x_arr, z_arr, type_arr, y_arr, prox_arr]
