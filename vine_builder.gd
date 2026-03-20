# vine_builder.gd — Invasive vine system for Central Park woodland areas.
# Places porcelain berry + oriental bittersweet on qualifying trees.
# Static placement at startup (like trees), chunked MultiMesh with visibility_range.

var _loader  # park_loader.gd reference

# Mesh variants loaded from GLB
var _strand_meshes: Dictionary = {}  # "PorcelainBerry_A" -> Mesh, etc.
var _wrap_meshes: Dictionary = {}    # "TrunkWrap_A" -> Mesh

# Vine shader (applied to all vine meshes)
var _vine_shader: Shader
var _wrap_shader: Shader

# Chunk size for spatial batching (matches tree_builder)
const CHUNK := 80.0
const VIS_RANGE := 200.0  # strands visible to 200m
const WRAP_VIS_RANGE := 150.0  # trunk wraps visible to 150m

# Zone types where vines grow (from ground_cover_instances zone classification)
# 5 = NorthWoods, 6 = Ramble, 7 = Waterside, 8 = WildMeadow
const VINE_ZONES := {
	5: {"chance": 0.22, "strands": [3, 6], "wraps": [1, 2]},  # NorthWoods: moderate
	6: {"chance": 0.28, "strands": [4, 8], "wraps": [1, 3]},  # Ramble: heaviest
	7: {"chance": 0.12, "strands": [2, 4], "wraps": [0, 1]},  # Waterside: light
	8: {"chance": 0.18, "strands": [2, 5], "wraps": [1, 2]},  # WildMeadow: moderate
}

# Woodland Z ranges where vines grow even without zone classification
# (matches undergrowth_builder.gd WOODLAND_Z_RANGES)
const WOODLAND_Z_RANGES := [
	Vector2(-1800, -1050),  # North Woods / Ravine
	Vector2(375, 975),      # Ramble + Dene
	Vector2(1650, 2050),    # Hallett Nature Sanctuary
]


func _init(loader) -> void:
	_loader = loader


func _build_vines(trees: Array) -> void:
	# Load vine meshes
	var glb_path := ProjectSettings.globalize_path("res://models/vegetation/cp_vines.glb")
	if not FileAccess.file_exists(glb_path):
		print("Vine: cp_vines.glb not found — skipping vine placement")
		return

	var meshes: Dictionary = _loader._load_glb_meshes(glb_path)
	if meshes.is_empty():
		print("Vine: no meshes found in cp_vines.glb")
		return

	# Sort meshes into strands and wraps
	for mesh_name: String in meshes:
		var mesh: Mesh = meshes[mesh_name]
		if mesh_name.begins_with("Vine_TrunkWrap"):
			_wrap_meshes[mesh_name] = mesh
		elif mesh_name.begins_with("Vine_"):
			_strand_meshes[mesh_name] = mesh

	print("Vine: loaded %d strand + %d wrap meshes" % [_strand_meshes.size(), _wrap_meshes.size()])

	if _strand_meshes.is_empty():
		print("Vine: no strand meshes — skipping")
		return

	# Load shaders
	_vine_shader = _loader._get_shader("vine", "res://shaders/vine.gdshader")

	# Build zone map from atlas (coarse: which 80m chunks are in vine zones)
	var zone_map := _build_zone_map()

	# Determine which trees get vines
	var rng := RandomNumberGenerator.new()
	rng.seed = 0xD3ADB33F  # deterministic

	# Collect vine instances per chunk
	var strand_xf_by_chunk: Dictionary = {}  # "cx|cz" -> Array[Transform3D]
	var strand_cd_by_chunk: Dictionary = {}  # parallel Color arrays (custom data)
	var strand_mesh_by_chunk: Dictionary = {}  # which mesh variant per instance
	var wrap_xf_by_chunk: Dictionary = {}
	var wrap_cd_by_chunk: Dictionary = {}
	var wrap_mesh_by_chunk: Dictionary = {}

	var strand_names: Array = _strand_meshes.keys()
	var wrap_names: Array = _wrap_meshes.keys()
	# Separate by species
	var pb_strands: Array = strand_names.filter(func(n: String): return "PorcelainBerry" in n)
	var bs_strands: Array = strand_names.filter(func(n: String): return "Bittersweet" in n)

	var total_strands := 0
	var total_wraps := 0
	var trees_with_vines := 0

	for i in trees.size():
		var tree_entry = trees[i]
		if typeof(tree_entry) != TYPE_DICTIONARY:
			continue

		var pt: Array = tree_entry["pos"]
		var tx := float(pt[0])
		var tz := float(pt[2])
		var species_name: String = str(tree_entry.get("species", "deciduous"))

		# Skip conifers and dead trees — vines don't grow on them
		if species_name == "conifer" or species_name == "dead":
			continue

		# Check if tree is in a vine zone
		var chunk_key := "%d|%d" % [int(floor(tx / CHUNK)), int(floor(tz / CHUNK))]
		var zone_cfg: Dictionary = {}

		if zone_map.has(chunk_key):
			var zone_type: int = zone_map[chunk_key]
			if VINE_ZONES.has(zone_type):
				zone_cfg = VINE_ZONES[zone_type]

		# Fallback: check woodland Z ranges
		if zone_cfg.is_empty():
			for zr in WOODLAND_Z_RANGES:
				if tz >= zr.x and tz <= zr.y:
					zone_cfg = {"chance": 0.15, "strands": [2, 5], "wraps": [1, 2]}
					break

		if zone_cfg.is_empty():
			continue

		# RNG per tree (deterministic from position)
		rng.seed = (i * 73856093 + int(tx * 311.7) + int(tz * 183.3)) & 0x7FFFFFFF
		if rng.randf() > zone_cfg["chance"]:
			continue

		# This tree gets vines
		trees_with_vines += 1
		var ty: float = _loader._terrain_y(tx, tz)

		# Tree height and crown radius
		var desired_h := 15.0
		if tree_entry.has("lidar_h") and float(tree_entry["lidar_h"]) > 0.0:
			desired_h = float(tree_entry["lidar_h"])
		else:
			var dbh := int(tree_entry.get("dbh", 12))
			desired_h = lerpf(10.0, 22.0, clampf((float(dbh) - 3.0) / 30.0, 0.0, 1.0))
		if desired_h < 5.0:
			continue  # Too short for vines

		var crown_r := desired_h * 0.35
		if tree_entry.has("crown_a"):
			var crown_a := float(tree_entry["crown_a"])
			if crown_a > 0.0:
				crown_r = sqrt(crown_a / PI)

		# Pick vine species: 60% porcelain berry, 40% bittersweet
		var is_bittersweet := rng.randf() > 0.6

		# Place hanging strands around canopy perimeter
		var n_strands: int = rng.randi_range(zone_cfg["strands"][0], zone_cfg["strands"][1])
		for s in n_strands:
			var angle := rng.randf() * TAU
			var dist := crown_r * rng.randf_range(0.5, 0.95)
			var sx := tx + cos(angle) * dist
			var sz := tz + sin(angle) * dist
			# Attachment height: 60-90% of tree height
			var attach_y := ty + desired_h * rng.randf_range(0.60, 0.90)

			# Random scale variation
			var scale := rng.randf_range(0.7, 1.4)
			var y_rot := rng.randf() * TAU
			var basis := Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(scale, scale, scale))
			var tf := Transform3D(basis, Vector3(sx, attach_y, sz))

			# Pick mesh variant
			var variant_list: Array = bs_strands if is_bittersweet else pb_strands
			if variant_list.is_empty():
				variant_list = strand_names
			var mesh_name: String = variant_list[rng.randi() % variant_list.size()]

			var ck := "%d|%d" % [int(floor(sx / CHUNK)), int(floor(sz / CHUNK))]
			if not strand_xf_by_chunk.has(ck):
				strand_xf_by_chunk[ck] = []
				strand_cd_by_chunk[ck] = []
				strand_mesh_by_chunk[ck] = []
			strand_xf_by_chunk[ck].append(tf)
			strand_cd_by_chunk[ck].append(Color(
				1.0 if is_bittersweet else 0.0,  # R: species
				rng.randf(),                       # G: seed
				0.0, 0.0))
			strand_mesh_by_chunk[ck].append(mesh_name)
			total_strands += 1

		# Place trunk wraps at tree base
		var n_wraps: int = rng.randi_range(zone_cfg["wraps"][0], zone_cfg["wraps"][1])
		if wrap_names.is_empty():
			n_wraps = 0
		for w in n_wraps:
			var wrap_scale_y := desired_h * rng.randf_range(0.3, 0.7) / 3.0  # mesh is ~3m tall
			var wrap_scale_xz := rng.randf_range(0.8, 1.3)
			var y_rot := rng.randf() * TAU
			var basis := Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(wrap_scale_xz, wrap_scale_y, wrap_scale_xz))
			var tf := Transform3D(basis, Vector3(tx, ty, tz))

			var mesh_name: String = wrap_names[rng.randi() % wrap_names.size()]

			var ck := "%d|%d" % [int(floor(tx / CHUNK)), int(floor(tz / CHUNK))]
			if not wrap_xf_by_chunk.has(ck):
				wrap_xf_by_chunk[ck] = []
				wrap_cd_by_chunk[ck] = []
				wrap_mesh_by_chunk[ck] = []
			wrap_xf_by_chunk[ck].append(tf)
			wrap_cd_by_chunk[ck].append(Color(
				1.0 if is_bittersweet else 0.0,
				rng.randf(),
				0.0, 0.0))
			wrap_mesh_by_chunk[ck].append(mesh_name)
			total_wraps += 1

	# --- Create MultiMesh instances per chunk ---
	# Group by mesh variant within each chunk for efficient batching
	var vine_root := Node3D.new()
	vine_root.name = "Vines"
	_loader.add_child(vine_root)

	var mmi_count := 0

	# Strand MMIs
	for ck: String in strand_xf_by_chunk:
		var xfs: Array = strand_xf_by_chunk[ck]
		var cds: Array = strand_cd_by_chunk[ck]
		var mesh_keys: Array = strand_mesh_by_chunk[ck]

		# Group by mesh variant
		var by_mesh: Dictionary = {}
		for idx in xfs.size():
			var mk: String = mesh_keys[idx]
			if not by_mesh.has(mk):
				by_mesh[mk] = {"xf": [], "cd": []}
			by_mesh[mk]["xf"].append(xfs[idx])
			by_mesh[mk]["cd"].append(cds[idx])

		for mk: String in by_mesh:
			var group: Dictionary = by_mesh[mk]
			var group_xfs: Array = group["xf"]
			var group_cds: Array = group["cd"]
			mmi_count += _create_mmi(vine_root, mk, ck,
				_strand_meshes[mk], group_xfs, group_cds,
				VIS_RANGE, false)

	# Wrap MMIs
	for ck: String in wrap_xf_by_chunk:
		var xfs: Array = wrap_xf_by_chunk[ck]
		var cds: Array = wrap_cd_by_chunk[ck]
		var mesh_keys: Array = wrap_mesh_by_chunk[ck]

		var by_mesh: Dictionary = {}
		for idx in xfs.size():
			var mk: String = mesh_keys[idx]
			if not by_mesh.has(mk):
				by_mesh[mk] = {"xf": [], "cd": []}
			by_mesh[mk]["xf"].append(xfs[idx])
			by_mesh[mk]["cd"].append(cds[idx])

		for mk: String in by_mesh:
			var group: Dictionary = by_mesh[mk]
			var group_xfs: Array = group["xf"]
			var group_cds: Array = group["cd"]
			mmi_count += _create_mmi(vine_root, mk, ck,
				_wrap_meshes[mk], group_xfs, group_cds,
				WRAP_VIS_RANGE, true)

	print("Vine: %d trees with vines, %d strands + %d wraps, %d MMIs" % [
		trees_with_vines, total_strands, total_wraps, mmi_count])


func _create_mmi(parent: Node3D, mesh_name: String, chunk_key: String,
		mesh: Mesh, xfs: Array, cds: Array,
		vis_range: float, is_wrap: bool) -> int:
	"""Create a MultiMeshInstance3D for a group of vine instances."""
	if xfs.is_empty():
		return 0

	# Compute centroid
	var cx := 0.0
	var cy := 0.0
	var cz := 0.0
	for tf: Transform3D in xfs:
		cx += tf.origin.x
		cy += tf.origin.y
		cz += tf.origin.z
	cx /= xfs.size()
	cy /= xfs.size()
	cz /= xfs.size()
	var centroid := Vector3(cx, cy, cz)

	# Apply material
	var mat_mesh := mesh.duplicate()
	var mat := ShaderMaterial.new()
	mat.shader = _vine_shader
	mat.set_shader_parameter("wind_flex", 0.5 if not is_wrap else 0.2)
	mat.set_shader_parameter("is_trunk_wrap", 1.0 if is_wrap else 0.0)
	mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
	if _loader._canopy_texture:
		mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
	for si in mat_mesh.get_surface_count():
		mat_mesh.surface_set_material(si, mat)

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.instance_count = xfs.size()
	mm.mesh = mat_mesh

	for idx in xfs.size():
		var tf: Transform3D = xfs[idx]
		tf.origin -= centroid  # local space
		mm.set_instance_transform(idx, tf)
		mm.set_instance_custom_data(idx, cds[idx])

	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.position = centroid
	mmi.visibility_range_end = vis_range
	mmi.visibility_range_end_margin = vis_range * 0.15  # ~30m for strands, ~22m for wraps
	mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
	mmi.name = "V_%s_%s" % [mesh_name.get_file(), chunk_key]
	parent.add_child(mmi)
	return 1


func _build_zone_map() -> Dictionary:
	"""Build coarse zone type map per 80m chunk from world atlas."""
	var zone_map: Dictionary = {}
	if _loader._atlas_data.is_empty():
		return zone_map

	# Load ground_cover_instances.bin for zone type data
	# Fallback: use atlas surface types to approximate zones
	# Zone detection via foliage zone Z ranges
	var res: int = _loader._atlas_res
	var scale: float = float(res) / _loader._hm_world_size
	var half: float = _loader._hm_world_size * 0.5

	# Sample atlas at chunk centers to determine dominant zone
	var x_chunks := int(ceil(_loader._hm_world_size / CHUNK))
	var z_chunks := int(ceil(_loader._hm_world_size / CHUNK))

	for cx_i in range(-x_chunks / 2, x_chunks / 2 + 1):
		for cz_i in range(-z_chunks / 2, z_chunks / 2 + 1):
			var wx := (float(cx_i) + 0.5) * CHUNK
			var wz := (float(cz_i) + 0.5) * CHUNK
			var ck := "%d|%d" % [cx_i, cz_i]

			# Determine zone from Z coordinate (foliage zone heuristic)
			var zone := _zone_from_position(wx, wz)
			if zone >= 0:
				zone_map[ck] = zone

	return zone_map


func _zone_from_position(_wx: float, wz: float) -> int:
	"""Classify a position into a foliage zone type based on Z coordinate.
	Returns zone type (5-8) or -1 if not in a vine-eligible zone."""
	# North Woods: Z roughly -1800 to -1050
	if wz >= -1800.0 and wz <= -1050.0:
		return 5
	# Ramble: Z roughly 375 to 975
	if wz >= 375.0 and wz <= 975.0:
		return 6
	# Hallett Nature Sanctuary: Z roughly 1650 to 2050
	if wz >= 1650.0 and wz <= 2050.0:
		return 6  # treat as Ramble-like
	# Waterside: near water bodies — approximate with Z bands near The Lake
	if wz >= 600.0 and wz <= 1100.0:
		return 7
	# Wild Meadow: North Meadow edges
	if wz >= -750.0 and wz <= -375.0:
		return 8
	return -1
