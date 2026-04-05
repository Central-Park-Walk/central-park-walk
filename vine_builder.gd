# vine_builder.gd — Biologically-accurate vine placement for Central Park.
# 7 species with climbing-mechanism-specific geometry, bark affinity,
# forest-edge probability boost, and ground-running patches.
# Static placement at startup (like trees), chunked MultiMesh with visibility_range.

var _loader  # park_loader.gd reference

# Per-species mesh variants loaded from GLB
var _species_meshes: Dictionary = {}  # species_name -> Array[Mesh]
var _vine_shader: Shader

const CHUNK := 80.0
const VIS_RANGE := 180.0
const GROUND_VIS_RANGE := 120.0

# --- 7 vine species with climbing mechanism data ---
# idx: shader species index (0-1), mechanism: climb/twine/tendril
# bark_aff: rough=1.0, moderate=0.7, smooth=0.3, exfoliating=0.4
# max_h: maximum height fraction of tree (0-1)
# evergreen: 0=deciduous, 1=evergreen, 0.4=semi-evergreen
enum Mechanism { CLIMB, TWINE, TENDRIL }
const VINE_SPECIES := [
	# 0: Virginia Creeper — adhesive disc pads, native, brilliant fall red
	{name="Vine_VirginiaCreeper", idx=0.0, mech=Mechanism.CLIMB, max_h=0.7,
	 evergreen=0.0, bark_smooth_ok=true},
	# 1: English Ivy — aerial rootlets, invasive, evergreen, one-sided
	{name="Vine_EnglishIvy", idx=0.143, mech=Mechanism.CLIMB, max_h=0.6,
	 evergreen=1.0, bark_smooth_ok=false},
	# 2: Oriental Bittersweet — twining, invasive, girdles trees
	{name="Vine_Bittersweet", idx=0.286, mech=Mechanism.TWINE, max_h=0.8,
	 evergreen=0.0, bark_smooth_ok=true},
	# 3: Porcelain Berry — forked tendrils, invasive, multi-color berries
	{name="Vine_PorcelainBerry", idx=0.429, mech=Mechanism.TENDRIL, max_h=0.6,
	 evergreen=0.0, bark_smooth_ok=false},
	# 4: Wild Grape — forked tendrils, native, reaches full canopy
	{name="Vine_WildGrape", idx=0.571, mech=Mechanism.TENDRIL, max_h=0.9,
	 evergreen=0.0, bark_smooth_ok=false},
	# 5: Japanese Honeysuckle — twining, invasive, semi-evergreen
	{name="Vine_Honeysuckle", idx=0.714, mech=Mechanism.TWINE, max_h=0.5,
	 evergreen=0.4, bark_smooth_ok=false},
	# 6: Wisteria — twining, ONLY on pergola structures
	{name="Vine_Wisteria", idx=0.857, mech=Mechanism.TWINE, max_h=1.0,
	 evergreen=0.0, bark_smooth_ok=true},
]

# Zone -> {chance, species_weights: Array of [species_idx, weight]}
# Based on NYC forest ecology data: 91% of forest plots contain invasive vines,
# ~30% of mature trees in Ramble/North Woods show vine presence.
const VINE_ZONES := {
	5: {chance=0.25, species=[  # North Woods
		[0, 0.30],  # Virginia creeper (native, common)
		[2, 0.25],  # bittersweet (invasive, dominant)
		[3, 0.20],  # porcelain berry
		[4, 0.15],  # wild grape (native, stream corridors)
		[5, 0.10],  # honeysuckle
	]},
	6: {chance=0.30, species=[  # Ramble — densest vine coverage
		[0, 0.25],  # Virginia creeper
		[2, 0.30],  # bittersweet (dominant invasive)
		[3, 0.25],  # porcelain berry
		[4, 0.10],  # wild grape
		[1, 0.05],  # English ivy (managed but present)
		[5, 0.05],  # honeysuckle
	]},
	7: {chance=0.15, species=[  # Waterside
		[4, 0.40],  # wild grape (moisture-loving)
		[0, 0.30],  # Virginia creeper
		[3, 0.20],  # porcelain berry
		[5, 0.10],  # honeysuckle
	]},
	8: {chance=0.18, species=[  # Wild Meadow edges
		[2, 0.35],  # bittersweet
		[3, 0.30],  # porcelain berry
		[0, 0.25],  # Virginia creeper
		[4, 0.10],  # wild grape
	]},
}

# Woodland Z ranges where vines grow even without zone classification
const WOODLAND_Z_RANGES := [
	Vector2(-1800, -1050),  # North Woods / Ravine
	Vector2(375, 975),      # Ramble + Dene
	Vector2(1650, 2050),    # Hallett Nature Sanctuary
]

# Bark affinity by tree species archetype
# Rough bark (deep fissures) = ideal for all vine types
# Smooth bark = only adhesive-pad vines (Virginia creeper) can climb
const BARK_AFFINITY := {
	"oak": 1.0, "elm": 1.0, "maple": 1.0, "linden": 1.0,
	"cathedral_elm": 1.0, "deciduous": 0.8,
	"honeylocust": 0.7, "ginkgo": 0.6,
	"london_plane": 0.4, "zelkova": 0.5,
	"cherry": 0.3, "birch": 0.25, "magnolia": 0.3, "callery_pear": 0.3,
	"pine": 0.5, "conifer": 0.5,
	"willow": 0.4, "dead": 0.0,
}


func _init(loader) -> void:
	_loader = loader


func _build_vines(trees: Array) -> void:
	# Load per-species vine meshes
	var loaded := 0
	for sp in VINE_SPECIES:
		if sp.name == "Vine_Wisteria":
			continue  # Wisteria placed on structures, not trees
		var glb_path := ProjectSettings.globalize_path(
			"res://models/vegetation/%s.glb" % sp.name)
		if not FileAccess.file_exists(glb_path):
			continue
		var meshes: Dictionary = _loader._load_glb_meshes(glb_path)
		if meshes.is_empty():
			continue
		_species_meshes[sp.name] = meshes.values()
		loaded += 1
	print("Vine: loaded %d species (%d total mesh variants)" % [
		loaded, _species_meshes.values().reduce(func(a, b): return a + b.size(), 0)])

	if loaded == 0:
		print("Vine: no vine models found — skipping")
		return

	_vine_shader = _loader._get_shader("vine", "res://shaders/vine.gdshader")

	# Build zone map
	var zone_map := _build_zone_map()

	var rng := RandomNumberGenerator.new()

	# Collect vine instances per chunk
	# Key: "sp_idx|chunk_key" -> {xf: Array[Transform3D], cd: Array[Color], mesh_idx: Array[int]}
	var chunk_data: Dictionary = {}
	var total_vines := 0
	var trees_with_vines := 0

	for i in trees.size():
		var tree_entry = trees[i]
		if typeof(tree_entry) != TYPE_DICTIONARY:
			continue

		var pt: Array = tree_entry["pos"]
		var tx := float(pt[0])
		var tz := float(pt[2])
		var species_name: String = str(tree_entry.get("species", "deciduous"))

		# Skip dead trees
		if species_name == "dead":
			continue

		# Tree height and DBH
		var dbh: int = int(tree_entry.get("dbh", 12))
		var desired_h := 15.0
		if tree_entry.has("lidar_h") and float(tree_entry["lidar_h"]) > 0.0:
			desired_h = float(tree_entry["lidar_h"])
		else:
			desired_h = lerpf(10.0, 22.0, clampf((float(dbh) - 3.0) / 30.0, 0.0, 1.0))
		if desired_h < 5.0:
			continue  # Too short for vines
		if dbh < 6:  # 6 inches ≈ 15cm
			continue

		# Zone check
		var chunk_key := "%d|%d" % [int(floor(tx / CHUNK)), int(floor(tz / CHUNK))]
		var zone_cfg: Dictionary = {}
		if zone_map.has(chunk_key):
			var zone_type: int = zone_map[chunk_key]
			if VINE_ZONES.has(zone_type):
				zone_cfg = VINE_ZONES[zone_type]
		# Woodland Z-range fallback
		if zone_cfg.is_empty():
			for zr in WOODLAND_Z_RANGES:
				if tz >= zr.x and tz <= zr.y:
					zone_cfg = {chance=0.15, species=[[0, 0.35], [2, 0.30], [3, 0.20], [4, 0.15]]}
					break
		if zone_cfg.is_empty():
			continue

		# Bark affinity
		var bark_mult: float = BARK_AFFINITY.get(species_name, 0.6)

		# Forest edge boost — trees near paths get 1.5x vine chance
		var edge_boost := 1.0
		var apx: int = int((tx + _loader._hm_world_size * 0.5) * float(_loader._atlas_res) / _loader._hm_world_size)
		var apz: int = int((tz + _loader._hm_world_size * 0.5) * float(_loader._atlas_res) / _loader._hm_world_size)
		if apx >= 0 and apx < _loader._atlas_res and apz >= 0 and apz < _loader._atlas_res:
			# Check nearby cells for paths (surface type 2 or 3)
			for dxy in [[-4,0],[4,0],[0,-4],[0,4]]:
				var nx: int = apx + dxy[0]
				var nz: int = apz + dxy[1]
				if nx >= 0 and nx < _loader._atlas_res and nz >= 0 and nz < _loader._atlas_res:
					var ns: int = _loader._atlas_data[(nz * _loader._atlas_res + nx) * 2]
					if ns == 2 or ns == 3:
						edge_boost = 1.5
						break

		# RNG per tree (deterministic)
		rng.seed = (i * 73856093 + int(tx * 311.7) + int(tz * 183.3)) & 0x7FFFFFFF
		var final_chance: float = float(zone_cfg.chance) * bark_mult * edge_boost
		if rng.randf() > final_chance:
			continue

		# This tree gets vines
		trees_with_vines += 1
		var ty: float = _loader._terrain_y(tx, tz)

		# Select vine species via weighted random
		var sp_idx: int = _pick_species(zone_cfg.species, rng, bark_mult, species_name)
		if sp_idx < 0 or sp_idx >= VINE_SPECIES.size():
			continue
		var vine_sp: Dictionary = VINE_SPECIES[sp_idx]
		if not _species_meshes.has(vine_sp.name):
			continue

		var meshes: Array = _species_meshes[vine_sp.name]
		var mesh_idx: int = rng.randi() % meshes.size()

		# Placement transform based on climbing mechanism
		var vine_h: float = desired_h * float(vine_sp.max_h) * rng.randf_range(0.4, 1.0)
		var scale := vine_h / 3.0  # models are ~3m reference height
		var y_rot := rng.randf() * TAU
		var basis := Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(scale, scale, scale))
		var origin := Vector3(tx, ty, tz)
		var tf := Transform3D(basis, origin)

		# Custom data: R=species_idx, G=seed, B=height_frac, A=age
		var custom := Color(
			vine_sp.idx,
			rng.randf(),
			clampf(vine_h / desired_h, 0.0, 1.0),
			rng.randf_range(0.3, 1.0))

		var ck := "%d|%s" % [sp_idx, chunk_key]
		if not chunk_data.has(ck):
			chunk_data[ck] = {xf=[], cd=[], mi=[]}
		chunk_data[ck].xf.append(tf)
		chunk_data[ck].cd.append(custom)
		chunk_data[ck].mi.append(mesh_idx)
		total_vines += 1

		# Ground-running patch (50% chance for climbing-pad species)
		if vine_sp.mech == Mechanism.CLIMB and rng.randf() < 0.5:
			var ground_mesh_idx: int = meshes.size() - 1  # last variant is ground runner
			var gx: float = tx + rng.randf_range(-3.0, 3.0)
			var gz: float = tz + rng.randf_range(-3.0, 3.0)
			var gy: float = float(_loader._terrain_y(gx, gz))
			var g_scale := rng.randf_range(0.6, 1.2)
			var g_rot := rng.randf() * TAU
			var g_basis := Basis(Vector3.UP, g_rot) * Basis().scaled(Vector3(g_scale, g_scale, g_scale))
			var g_tf := Transform3D(g_basis, Vector3(gx, gy, gz))
			chunk_data[ck].xf.append(g_tf)
			chunk_data[ck].cd.append(Color(vine_sp.idx, rng.randf(), 0.0, 0.2))
			chunk_data[ck].mi.append(ground_mesh_idx)
			total_vines += 1

	# --- Create MultiMesh instances per chunk per species ---
	var vine_root := Node3D.new()
	vine_root.name = "Vines"
	_loader.add_child(vine_root)
	var mmi_count := 0

	for ck: String in chunk_data:
		var data: Dictionary = chunk_data[ck]
		var xfs: Array = data.xf
		var cds: Array = data.cd
		var mis: Array = data.mi

		var sp_idx_str: String = ck.split("|")[0]
		var sp_idx: int = int(sp_idx_str)
		if sp_idx >= VINE_SPECIES.size():
			continue
		var vine_sp: Dictionary = VINE_SPECIES[sp_idx]
		if not _species_meshes.has(vine_sp.name):
			continue
		var meshes: Array = _species_meshes[vine_sp.name]

		# Group by mesh variant for efficient batching
		var by_mesh: Dictionary = {}
		for idx in xfs.size():
			var mi: int = mis[idx]
			if mi >= meshes.size():
				mi = 0
			if not by_mesh.has(mi):
				by_mesh[mi] = {xf=[], cd=[]}
			by_mesh[mi].xf.append(xfs[idx])
			by_mesh[mi].cd.append(cds[idx])

		for mi: int in by_mesh:
			var group: Dictionary = by_mesh[mi]
			var gxfs: Array = group.xf
			var gcds: Array = group.cd
			if gxfs.is_empty():
				continue

			# Centroid
			var cx := 0.0; var cy := 0.0; var cz := 0.0
			for tf: Transform3D in gxfs:
				cx += tf.origin.x; cy += tf.origin.y; cz += tf.origin.z
			cx /= gxfs.size(); cy /= gxfs.size(); cz /= gxfs.size()
			var centroid := Vector3(cx, cy, cz)

			# Apply shader
			var mesh: Mesh = meshes[mi]
			var mat_mesh := mesh.duplicate()
			var mat := ShaderMaterial.new()
			mat.shader = _vine_shader
			mat.set_shader_parameter("wind_flex", 0.5)
			mat.set_shader_parameter("is_trunk_wrap",
				1.0 if vine_sp.mech == Mechanism.TWINE else 0.0)
			mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
			if _loader._canopy_texture:
				mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
			for si in mat_mesh.get_surface_count():
				mat_mesh.surface_set_material(si, mat)

			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true
			mm.instance_count = gxfs.size()
			mm.mesh = mat_mesh
			for idx in gxfs.size():
				var tf: Transform3D = gxfs[idx]
				tf.origin -= centroid
				mm.set_instance_transform(idx, tf)
				mm.set_instance_custom_data(idx, gcds[idx])

			var vis := VIS_RANGE
			if gcds[0].b < 0.1:  # ground runner
				vis = GROUND_VIS_RANGE

			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.position = centroid
			mmi.visibility_range_end = vis
			mmi.visibility_range_end_margin = vis * 0.15
			mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
			mmi.name = "V_%s_%d_%s" % [vine_sp.name.get_file(), mi,
				ck.split("|")[1] + "|" + ck.split("|")[2] if ck.count("|") >= 2 else ck]
			vine_root.add_child(mmi)
			mmi_count += 1

	print("Vine: %d trees with vines, %d instances, %d MMIs" % [
		trees_with_vines, total_vines, mmi_count])


func _pick_species(weights: Array, rng: RandomNumberGenerator,
		bark_mult: float, tree_species: String) -> int:
	"""Pick vine species via weighted random, respecting bark affinity."""
	var total := 0.0
	var adjusted: Array = []
	for w in weights:
		var sp_idx: int = w[0]
		var weight: float = w[1]
		# Smooth-bark trees can only support adhesive-pad climbers
		if bark_mult < 0.4 and VINE_SPECIES[sp_idx].mech != Mechanism.CLIMB:
			if not VINE_SPECIES[sp_idx].bark_smooth_ok:
				weight *= 0.1  # drastically reduce, don't eliminate
		adjusted.append([sp_idx, weight])
		total += weight
	if total <= 0.0:
		return -1
	var roll := rng.randf() * total
	var accum := 0.0
	for w in adjusted:
		accum += w[1]
		if roll <= accum:
			return w[0]
	return adjusted[-1][0]


func _build_zone_map() -> Dictionary:
	"""Classify chunks into vine zones from Z coordinate."""
	var zone_map: Dictionary = {}
	var x_chunks: int = int(ceil(_loader._hm_world_size / CHUNK))
	for cx_i in range(-x_chunks / 2, x_chunks / 2 + 1):
		for cz_i in range(-x_chunks / 2, x_chunks / 2 + 1):
			var wz := (float(cz_i) + 0.5) * CHUNK
			var ck := "%d|%d" % [cx_i, cz_i]
			var zone := _zone_from_z(wz)
			if zone >= 0:
				zone_map[ck] = zone
	return zone_map


func _zone_from_z(wz: float) -> int:
	"""Classify position into vine-eligible zone from Z coordinate."""
	if wz >= -1800.0 and wz <= -1050.0: return 5   # North Woods
	if wz >= 375.0 and wz <= 975.0: return 6        # Ramble
	if wz >= 1650.0 and wz <= 2050.0: return 6      # Hallett (Ramble-like)
	if wz >= 600.0 and wz <= 1100.0: return 7       # Waterside (Lake area)
	if wz >= -750.0 and wz <= -375.0: return 8      # Wild Meadow edges
	return -1
