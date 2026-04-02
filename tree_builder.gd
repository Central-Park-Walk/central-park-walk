# tree_builder.gd
# Tree geometry: GLB-based trees with spatially chunked MultiMesh instances
# Extracted from park_loader.gd — all shared utilities accessed via _loader reference.

var _loader  # Reference to park_loader for shared utilities
var _shell_data: Array = []  # per-tree canopy shell data for LOD1
var species_filter: Array = []  # CLI: only place these species (empty = all)

# Maps data species archetype → phenology index for GPU seasonal color (12 species)
const PHENOLOGY_INDEX := {
	"oak": 0, "maple": 1, "elm": 2, "birch": 3, "deciduous": 4, "conifer": 5,
	"honeylocust": 6, "callery_pear": 7, "ginkgo": 8, "london_plane": 9,
	"linden": 10, "cherry": 11, "zelkova": 2,  # zelkova shares elm phenology
	"dead": 4,  # dead trees use deciduous phenology (no leaves rendered anyway)
	"willow": 12,  # willow: golden yellow fall, early spring
	"magnolia": 13,  # magnolia: spring blossom, brown-gold fall
	"cathedral_elm": 2,  # shares elm phenology
}
# Maps archetype → base GLB model name
const ARCHETYPE_MODEL := {
	"oak": "oak", "maple": "maple", "elm": "elm", "birch": "birch",
	"deciduous": "deciduous", "conifer": "pine",
	"honeylocust": "honeylocust", "callery_pear": "callery_pear", "ginkgo": "ginkgo",
	"london_plane": "london_plane", "linden": "linden", "cherry": "cherry",
	"zelkova": "elm", "dead": "dead", "willow": "willow", "magnolia": "magnolia",
	"cathedral_elm": "cathedral_elm",
}

# Literary Walk / Mall: mature trees flanking the straight promenade get the
# wide-vase cathedral elm model. Most are tagged "deciduous" in OSM data but
# are historically American Elms. Zone covers both rows (X≈-640 and X≈-710).
const CATHEDRAL_ELM_ZONE := Rect2(-720.0, 1180.0, 90.0, 340.0)  # x, z, w, h

var canopy_data: Array = []  # [{x, z, radius}] for canopy map generation
var _lod1_xf: Dictionary = {}  # LOD1: _m model transforms per key
var _lod1_cd: Dictionary = {}  # LOD1: custom data per key
var _lod2_xf: Dictionary = {}  # LOD2: _s model transforms per key
var _lod2_cd: Dictionary = {}  # LOD2: custom data per key
var _species_meshes: Dictionary = {}  # archetype_name -> Array[Mesh]
var _species_heights: Dictionary = {} # archetype_name -> float (mesh height)

func _init(loader) -> void:
	_loader = loader

# Size tier boundaries per species: [small_max, medium_max]
# Trees below small_max use _s model, below medium_max use _m, else _l.
# Matches the height_range overlaps in scripts/generate_trees_mtree.py.
const TIER_BOUNDS := {
	"oak":           [12.0, 20.0],
	"maple":         [14.0, 22.0],
	"elm":           [14.0, 22.0],
	"cathedral_elm": [18.0, 26.0],
	"deciduous":     [14.0, 22.0],
	"pine":          [10.0, 18.0],
	"birch":         [8.0, 12.0],
	"cherry":        [9.0, 16.0],
	"honeylocust":   [14.0, 22.0],
	"callery_pear":  [10.0, 18.0],
	"ginkgo":        [14.0, 22.0],
	"london_plane":  [15.0, 25.0],
	"linden":        [14.0, 22.0],
	"willow":        [14.0, 20.0],
	"magnolia":      [9.0, 16.0],
	"conifer":       [10.0, 18.0],  # shares pine models
	"zelkova":       [14.0, 22.0],  # shares elm models
	"dead":          [0.0, 0.0],    # no tiers
}
const TIERS := ["s", "m", "l"]

func _get_tier(species: String, desired_h: float) -> String:
	## Return size tier suffix based on species and desired height.
	var bounds: Array = TIER_BOUNDS.get(species, [12.0, 20.0])
	if desired_h < bounds[0]:
		return "s"
	elif desired_h < bounds[1]:
		return "m"
	else:
		return "l"

const CACHE_DIR := "user://cache/trees/"

func _try_load_cached_tree(model_name: String) -> Dictionary:
	## Load tree meshes from .res cache (much faster than GLTF parsing).
	## Returns empty dict on cache miss.
	var meta_path := CACHE_DIR + model_name + ".cfg"
	if not FileAccess.file_exists(meta_path):
		return {}
	var cfg := ConfigFile.new()
	if cfg.load(meta_path) != OK:
		return {}
	var n_v: int = cfg.get_value("model", "n_variants", 0)
	var height: float = cfg.get_value("model", "height", 0.0)
	if n_v == 0:
		return {}
	var meshes: Array = []
	var ltexs: Array = []
	for i in n_v:
		var rp := CACHE_DIR + "%s_%d.res" % [model_name, i]
		if not FileAccess.file_exists(rp):
			return {}
		var m = ResourceLoader.load(rp)
		if m == null:
			return {}
		meshes.append(m)
		var tex: Texture2D = null
		for si in m.get_surface_count():
			var smat = m.surface_get_material(si)
			if smat is StandardMaterial3D:
				var sm := smat as StandardMaterial3D
				if sm.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
					if sm.albedo_texture:
						tex = sm.albedo_texture
		ltexs.append(tex)
	return {"meshes": meshes, "height": height, "ltexs": ltexs}

func _save_tree_cache(model_name: String, meshes: Array, height: float) -> void:
	## Save tree meshes as .res files for fast subsequent loads.
	var abs_dir := ProjectSettings.globalize_path(CACHE_DIR)
	DirAccess.make_dir_recursive_absolute(abs_dir)
	for i in meshes.size():
		ResourceSaver.save(meshes[i], CACHE_DIR + "%s_%d.res" % [model_name, i])
	var cfg := ConfigFile.new()
	cfg.set_value("model", "n_variants", meshes.size())
	cfg.set_value("model", "height", height)
	cfg.save(CACHE_DIR + model_name + ".cfg")


func _build_trees(trees: Array) -> void:
	if trees.is_empty():
		return

	var rng := RandomNumberGenerator.new()

	# --- Load Mtree-generated GLB tree models ---
	# Each GLB has 5 tree variants. Size-tiered: {species}_s.glb / _m.glb / _l.glb
	# Models generated by scripts/generate_trees_mtree.py (Blender 4.5 + Mtree addon).
	# Scale-aware branching: larger tiers have proportionally denser canopies.
	# Per-archetype leaf and bark colors (12 species)
	var leaf_tints := {
		"oak":           Vector3(0.24, 0.40, 0.14),   # dark green
		"maple":         Vector3(0.30, 0.50, 0.18),   # bright green, warm
		"elm":           Vector3(0.24, 0.42, 0.15),   # medium-warm green (American Elm)
		"birch":         Vector3(0.34, 0.52, 0.22),   # light yellow-green
		"deciduous":     Vector3(0.26, 0.44, 0.16),   # medium green
		"pine":          Vector3(0.14, 0.30, 0.10),   # dark desaturated green
		"honeylocust":   Vector3(0.32, 0.52, 0.20),   # light airy green (compound leaves)
		"callery_pear":  Vector3(0.28, 0.48, 0.18),   # fresh green, dense crown
		"ginkgo":        Vector3(0.30, 0.50, 0.22),   # yellow-green (fan-shaped leaves)
		"london_plane":  Vector3(0.24, 0.44, 0.16),   # medium green, large leaves
		"linden":        Vector3(0.26, 0.48, 0.18),   # warm green (heart-shaped leaves)
		"cherry":        Vector3(0.30, 0.50, 0.20),   # fresh green, small ornamental
		"zelkova":       Vector3(0.22, 0.40, 0.14),   # dark warm green (elm family)
		"dead":          Vector3(0.42, 0.38, 0.34),   # gray weathered (no leaves)
		"willow":        Vector3(0.30, 0.50, 0.15),   # yellow-green, narrow leaves
		"magnolia":      Vector3(0.18, 0.35, 0.12),   # dark glossy green, large leaves
		"cathedral_elm": Vector3(0.24, 0.42, 0.15),   # same as elm
	}
	var bark_colors := {
		"oak":           Color(0.40, 0.32, 0.24),     # dark brown, deeply furrowed
		"maple":         Color(0.50, 0.40, 0.30),     # medium brown
		"elm":           Color(0.30, 0.25, 0.18),     # gray-brown (American Elm bark)
		"birch":         Color(0.80, 0.76, 0.68),     # distinctive white bark
		"deciduous":     Color(0.42, 0.34, 0.26),     # dark brown
		"pine":          Color(0.48, 0.34, 0.22),     # reddish-brown
		"honeylocust":   Color(0.45, 0.38, 0.28),     # dark gray-brown
		"callery_pear":  Color(0.42, 0.36, 0.28),     # gray-brown, smooth
		"ginkgo":        Color(0.50, 0.42, 0.32),     # gray, furrowed with age
		"london_plane":  Color(0.60, 0.56, 0.48),     # distinctive mottled cream-gray
		"linden":        Color(0.42, 0.36, 0.28),     # gray-brown, ridged
		"cherry":        Color(0.52, 0.32, 0.22),     # reddish-brown, glossy
		"zelkova":       Color(0.38, 0.30, 0.22),     # gray, exfoliating
		"dead":          Color(0.42, 0.38, 0.34),     # weathered gray dead wood
		"willow":        Color(0.40, 0.35, 0.28),     # gray-brown, deeply furrowed
		"magnolia":      Color(0.52, 0.48, 0.44),     # smooth light gray
		"cathedral_elm": Color(0.30, 0.25, 0.18),     # same as elm
	}
	# --- Load 5 base GLB models, then create per-archetype colored copies ---
	# Uses class members _species_meshes and _species_heights (shared with _build_lod1_chunks)
	_species_meshes.clear()
	_species_heights.clear()

	# Step 1: Load raw meshes + heights from 5 GLB files
	var base_meshes: Dictionary = {}     # model_name -> Array[Mesh]
	var base_heights: Dictionary = {}    # model_name -> float
	var base_leaf_textures: Dictionary = {} # model_name -> Array[Texture2D or null]
	var leaf_shader: Shader = _loader._get_shader("tree_leaf_glb", _tree_glb_leaf_shader_code())
	var bark_shader: Shader = _loader._get_shader("tree_bark", "res://shaders/tree_bark.gdshader")

	# PBR bark textures — photogrammetry-scanned real bark surfaces, one set per style
	# Style 0: oak/furrowed, Style 1: birch/smooth, Style 2: london plane/exfoliating,
	# Style 3: pine/plated, Style 4: magnolia/smooth
	var bark_tex_paths := {
		0: { "albedo": "res://textures/bark/oak/Bark012_1K-JPG_Color.jpg",
			 "normal": "res://textures/bark/oak/Bark012_1K-JPG_NormalGL.jpg",
			 "roughness": "res://textures/bark/oak/Bark012_1K-JPG_Roughness.jpg" },
		1: { "albedo": "res://textures/bark/smooth/Bark003_1K-JPG_Color.jpg",
			 "normal": "res://textures/bark/smooth/Bark003_1K-JPG_NormalGL.jpg",
			 "roughness": "res://textures/bark/smooth/Bark003_1K-JPG_Roughness.jpg" },
		2: { "albedo": "res://textures/bark/exfoliating/Bark015_1K-JPG_Color.jpg",
			 "normal": "res://textures/bark/exfoliating/Bark015_1K-JPG_NormalGL.jpg",
			 "roughness": "res://textures/bark/exfoliating/Bark015_1K-JPG_Roughness.jpg" },
		3: { "albedo": "res://textures/bark/pine/pine_bark_diff_1k.jpg",
			 "normal": "res://textures/bark/pine/pine_bark_nor_gl_1k.jpg",
			 "roughness": "res://textures/bark/pine/pine_bark_rough_1k.jpg" },
		4: { "albedo": "res://textures/bark/furrowed/Bark007_1K-JPG_Color.jpg",
			 "normal": "res://textures/bark/furrowed/Bark007_1K-JPG_NormalGL.jpg",
			 "roughness": "res://textures/bark/furrowed/Bark007_1K-JPG_Roughness.jpg" },
	}
	var bark_textures := {}  # style_id -> { "albedo": Texture2D, "normal": ..., "roughness": ... }
	for style_id in bark_tex_paths:
		var paths: Dictionary = bark_tex_paths[style_id]
		var texs := {}
		for map_name in paths:
			var tex = load(paths[map_name])
			if tex:
				texs[map_name] = tex
		if texs.size() == 3:
			bark_textures[style_id] = texs
			print("Trees: loaded bark textures for style %d" % style_id)
		else:
			push_warning("Trees: missing bark textures for style %d" % style_id)

	var _base_model_names := ["maple", "birch", "deciduous", "pine", "elm", "oak", "cherry", "ginkgo", "honeylocust", "linden", "london_plane", "callery_pear", "dead", "willow", "magnolia", "cathedral_elm"]
	# Load tiered models (_s, _m, _l) for each base model. Dead has no tiers.
	for base_name in _base_model_names:
		var tier_list: Array
		if base_name == "dead":
			tier_list = [""]  # single model, no tier suffix
		else:
			tier_list = ["_s", "_m", "_l"]
		for tier_suffix in tier_list:
			var model_key: String = base_name + tier_suffix
			# Try .res cache first (skips GLTF parsing — much faster on subsequent loads)
			var cached := _try_load_cached_tree(model_key)
			if not cached.is_empty():
				base_meshes[model_key] = cached.meshes
				base_heights[model_key] = cached.height
				base_leaf_textures[model_key] = cached.ltexs
				continue
			var abs_path := ProjectSettings.globalize_path("res://models/trees/%s.glb" % model_key)
			if not FileAccess.file_exists(abs_path):
				# Fallback: try base model without tier suffix (backward compat)
				if tier_suffix != "":
					var fallback_path := ProjectSettings.globalize_path("res://models/trees/%s.glb" % base_name)
					if FileAccess.file_exists(fallback_path):
						abs_path = fallback_path
					else:
						continue
				else:
					continue
			# --- GLB loading (slow path — first run only) ---
			var root: Node = _loader._load_glb_scene(abs_path)
			if root == null:
				continue
			var meshes: Array = []
			_loader._collect_meshes(root, meshes)
			var max_h := 0.0
			for m: Mesh in meshes:
				var ab: AABB = m.get_aabb()
				var h := ab.size.y
				if h < 0.001:
					h = maxf(ab.size.x, maxf(ab.size.y, ab.size.z))
				max_h = maxf(max_h, h)
			var ltexs: Array = []
			for m: Mesh in meshes:
				var tex: Texture2D = null
				for si in m.get_surface_count():
					var smat: Material = m.surface_get_material(si)
					if smat is StandardMaterial3D:
						var sm: StandardMaterial3D = smat as StandardMaterial3D
						if sm.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
							if sm.albedo_texture:
								tex = sm.albedo_texture
				ltexs.append(tex)
			root.queue_free()
			if meshes.is_empty():
				continue
			base_meshes[model_key] = meshes
			base_heights[model_key] = max_h
			base_leaf_textures[model_key] = ltexs
			_save_tree_cache(model_key, meshes, max_h)
			print("Trees: loaded %s — %d variants, h=%.3f" % [model_key, meshes.size(), max_h])

	# Step 2: Create per-archetype+tier mesh copies with distinct leaf/bark colors
	# Keys: "oak_s", "oak_m", "oak_l", "dead" (no tier suffix for dead)
	for archetype in ARCHETYPE_MODEL:
		var model_base: String = ARCHETYPE_MODEL[archetype]
		var leaf_tint: Vector3 = leaf_tints.get(archetype, Vector3(0.28, 0.48, 0.18))
		var bark_col: Color = bark_colors.get(archetype, Color(0.48, 0.38, 0.28))
		# Bark style for this archetype
		var bstyle := 0
		if archetype in ["birch", "cherry"]:
			bstyle = 1
		elif archetype in ["london_plane", "zelkova"]:
			bstyle = 2
		elif archetype == "pine":
			bstyle = 3
		elif archetype in ["magnolia", "callery_pear"]:
			bstyle = 4

		var tier_suffixes: Array
		if archetype == "dead":
			tier_suffixes = [""]
		else:
			tier_suffixes = ["_s", "_m", "_l"]
		for tier_suffix in tier_suffixes:
			var model_key: String = model_base + tier_suffix
			if not base_meshes.has(model_key):
				continue
			var src_meshes: Array = base_meshes[model_key]
			var ltexs: Array = base_leaf_textures[model_key]
			var arch_meshes: Array = []
			for mi in src_meshes.size():
				var m: Mesh = src_meshes[mi].duplicate(true)
				for si in m.get_surface_count():
					var smat: Material = m.surface_get_material(si)
					if smat is StandardMaterial3D:
						var sm: StandardMaterial3D = smat as StandardMaterial3D
						if sm.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
							var leaf_mat := ShaderMaterial.new()
							leaf_mat.shader = leaf_shader
							leaf_mat.set_shader_parameter("albedo_tint", leaf_tint)
							if ltexs[mi]:
								leaf_mat.set_shader_parameter("albedo_tex", ltexs[mi])
							m.surface_set_material(si, leaf_mat)
						else:
							var bark_mat := ShaderMaterial.new()
							bark_mat.shader = bark_shader
							bark_mat.set_shader_parameter("bark_color", Vector3(bark_col.r, bark_col.g, bark_col.b))
							bark_mat.set_shader_parameter("bark_style", bstyle)
							if bark_textures.has(bstyle):
								var btex: Dictionary = bark_textures[bstyle]
								bark_mat.set_shader_parameter("bark_albedo_tex", btex["albedo"])
								bark_mat.set_shader_parameter("bark_normal_tex", btex["normal"])
								bark_mat.set_shader_parameter("bark_roughness_tex", btex["roughness"])
							m.surface_set_material(si, bark_mat)
					elif smat is ShaderMaterial:
						var sm: ShaderMaterial = smat as ShaderMaterial
						var new_mat := sm.duplicate()
						new_mat.set_shader_parameter("albedo_tint", leaf_tint)
						m.surface_set_material(si, new_mat)
				arch_meshes.append(m)
			var arch_key: String = archetype + tier_suffix
			_species_meshes[arch_key] = arch_meshes
			_species_heights[arch_key] = base_heights[model_key]
	print("Trees: %d archetype×tier combos from %d model files" % [_species_meshes.size(), base_meshes.size()])

	if _species_meshes.is_empty():
		print("WARNING: no tree GLB models loaded, falling back skipped")
		return

	# Desired height ranges per species archetype (metres)
	# [min, max] — census DBH drives interpolation within range
	# DBH fallback height ranges (metres). Minimums raised because woodland-fill
	# trees represent established 150-year-old Central Park canopy, not saplings.
	# "cherry" includes black cherry (Prunus serotina, 25m+) not just ornamentals.
	var height_ranges := {
		"oak":           [15.0, 30.0],   # red/white oak — massive when mature
		"maple":         [14.0, 26.0],   # sugar/Norway maple
		"elm":           [16.0, 32.0],   # American Elm — tall vase shape
		"conifer":       [14.0, 30.0],
		"deciduous":     [14.0, 28.0],   # generic canopy tree
		"birch":         [10.0, 22.0],   # gray/river birch
		"honeylocust":   [14.0, 25.0],   # open, airy crown
		"callery_pear":  [8.0, 18.0],    # medium street tree
		"ginkgo":        [10.0, 22.0],   # slow-growing
		"london_plane":  [16.0, 32.0],   # tall broad crown, like sycamore
		"linden":        [14.0, 24.0],   # dense symmetrical crown
		"cherry":        [10.0, 22.0],   # includes black cherry (P. serotina 25m+)
		"zelkova":       [14.0, 24.0],   # upright vase shape
		"dead":          [8.0, 20.0],    # shorter (broken top)
		"willow":        [10.0, 22.0],   # weeping willow — wide, medium height
		"magnolia":      [6.0, 16.0],    # sweetbay magnolia can reach 20m
		"cathedral_elm": [22.0, 34.0],   # mature Literary Walk elms — tall, wide vase
	}

	# Foliage zone data for deciduous sub-species assignment

	# Collect transforms + season data per species-variant for MultiMesh batching
	# Key: "species_variantIdx" -> Array[Transform3D]
	var xf_by_key: Dictionary = {}
	var cd_by_key: Dictionary = {}  # parallel Color arrays for custom_data (season info)
	var all_trunk_xf: Array = []  # for collision
	var _skip_surface := 0
	var _nudged := 0
	for i in trees.size():
		var tree_entry = trees[i]
		var pt: Array
		var tree_species := "deciduous"
		var dbh := 12
		# Support both new dict format and legacy [x, h, z] arrays
		if typeof(tree_entry) == TYPE_DICTIONARY:
			pt = tree_entry["pos"]
			tree_species = str(tree_entry.get("species", "deciduous"))
			dbh = int(tree_entry.get("dbh", 12))
		else:
			pt = tree_entry
		var tx := float(pt[0]); var tz := float(pt[2])
		# Use atlas surface type instead of boundary polygon — atlas correctly covers
		# the full park area while the OSM boundary polygon may be undersized.
		var surf: int = _loader._atlas_surface(tx, tz)
		if surf != 1 and surf != 7:  # not on grass (1) or rock (7)
			# Trees on paths/bridges are common — GPS offset or canopy overlap.
			# Nudge to nearest grass/rock cell within ~3m (5 cells at 0.61m).
			if surf == 2 or surf == 3 or surf == 6:
				var nudged: bool = false
				var cell_m: float = _loader._hm_world_size / float(_loader._atlas_res)
				for radius in range(1, 6):
					if nudged:
						break
					for dx in range(-radius, radius + 1):
						if nudged:
							break
						for dz in range(-radius, radius + 1):
							if abs(dx) != radius and abs(dz) != radius:
								continue  # only check perimeter of each ring
							var nx: float = tx + float(dx) * cell_m
							var nz: float = tz + float(dz) * cell_m
							var ns: int = _loader._atlas_surface(nx, nz)
							if ns == 1 or ns == 7:
								tx = nx; tz = nz
								nudged = true
								_nudged += 1
								break
				if not nudged:
					_skip_surface += 1
					continue
			else:
				# water (4), building (5), outside (0) — truly skip
				_skip_surface += 1
				continue
		var ty: float = _loader._terrain_y(tx, tz)
		rng.seed = i * 1234567891 + 987654321

		# Use the species from data as-is (census or OSM archetype)
		var species: String = tree_species
		# Literary Walk/Mall: mature elms AND deciduous trees get cathedral elm
		# (OSM tags most Mall trees as generic "deciduous" — they're American Elms)
		if (species == "elm" or species == "deciduous") and CATHEDRAL_ELM_ZONE.has_point(Vector2(tx, tz)):
			species = "cathedral_elm"

		# Standing dead trees (snags): ~3% of non-conifer trees become dead snags
		if species != "conifer" and species != "dead":
			var dead_hash := fmod(abs(sin(float(i) * 127.1 + tx * 311.7 + tz * 183.3) * 43758.5453), 1.0)
			if dead_hash < 0.03:
				species = "dead"

		# CLI species filter: skip species not in the filter list
		if not species_filter.is_empty() and species not in species_filter:
			continue

		# Desired height: use LiDAR measurement if available, else DBH estimate
		var desired_h: float
		if typeof(tree_entry) == TYPE_DICTIONARY and tree_entry.has("lidar_h") and float(tree_entry["lidar_h"]) > 0.0:
			desired_h = float(tree_entry["lidar_h"])
			desired_h = clampf(desired_h, 3.0, float(height_ranges.get(species, [10.0, 35.0])[1]) * 1.2)
		else:
			var h_range: Array = height_ranges.get(species, [10.0, 22.0])
			var h_min := float(h_range[0])
			var h_max := float(h_range[1])
			var dbh_t := clampf((float(dbh) - 3.0) / 45.0, 0.0, 1.0)
			desired_h = lerpf(h_min, h_max, dbh_t)

		# Select size tier based on desired height → _s, _m, or _l model
		var tier_suffix: String
		if species == "dead":
			tier_suffix = ""  # dead has no tiers
		else:
			tier_suffix = "_" + _get_tier(species, desired_h)
		var species_tier: String = species + tier_suffix

		# Validate mesh exists for this species+tier; fallback chain
		if not _species_meshes.has(species_tier):
			# Try without tier (backward compat with old single-tier models)
			if _species_meshes.has(species):
				species_tier = species
			elif _species_meshes.has("deciduous" + tier_suffix):
				species = "deciduous"
				species_tier = "deciduous" + tier_suffix
			elif _species_meshes.has("deciduous"):
				species = "deciduous"
				species_tier = "deciduous"
			else:
				continue

		var variants: Array = _species_meshes[species_tier]
		var n_variants := variants.size()
		if n_variants == 0:
			continue

		# Pick variant based on tree index
		var variant_idx := i % n_variants

		# Scale factor: desired_height / mesh_height_in_raw_units
		var mesh_h: float = _species_heights[species_tier]
		if mesh_h < 0.001:
			mesh_h = 0.06
		var sy := desired_h / mesh_h

		# Crown width: uniform scaling (sx = sy) preserves model proportions.
		# LiDAR crown_area measures only the dense inner canopy (~10-30m²
		# for a 20m tree) which compressed sx to 0.72×sy for nearly every
		# tree, making them all look like sticks. Removed data-driven width.
		var sx := sy
		if species == "cathedral_elm":
			# Cathedral elms MUST stay wide — override crown scaling
			# Literary Walk path is ~15m wide; elms are ~10m apart per row.
			# Need each crown to reach 8-10m laterally to converge overhead.
			sx = sy * 1.50  # force 50% wider than tall for canopy convergence

		# Random Y rotation for variety
		var y_rot := rng.randf() * TAU

		# Build transform: Y rotation × non-uniform scale
		# GLB models are Y-up (standard GLTF export from Blender).
		# sx scales crown width (XZ), sy scales height (Y)
		var basis := Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(sx, sy, sx))
		var tf := Transform3D(basis, Vector3(tx, ty, tz))

		var key := "%s_%d" % [species_tier, variant_idx]
		if not xf_by_key.has(key):
			xf_by_key[key] = []
			cd_by_key[key] = []
		xf_by_key[key].append(tf)
		# Pack season data: R=species phenology index, G=timing offset, B=evergreen flag
		var pheno_idx: int = PHENOLOGY_INDEX.get(species, 4)
		var timing_off := rng.randf_range(-0.15, 0.15)
		var is_evergreen := 1.0 if species == "conifer" else 0.0
		# Per-tree color jitter (0-1): deterministic hash from position.
		# Consistent across all LOD tiers since they share the same tx/tz.
		var color_jitter := fmod(abs(sin(tx * 127.1 + tz * 311.7) * 43758.5453), 1.0)
		var cd := Color(float(pheno_idx) / 13.0, timing_off + 0.5, is_evergreen, color_jitter)
		cd_by_key[key].append(cd)

		# 4-tier LOD chain: LOD0=best, LOD1=_m, LOD2=_s, LOD3=impostor
		# Every tree MUST populate ALL tiers to avoid distance gaps.
		# Missing _m/_s variants reuse the tree's own mesh — crossfade
		# is invisible (same mesh at different visibility ranges).
		for lod_idx in [1, 2]:
			var lod_tier_suffix: String
			if lod_idx == 1:
				# LOD1 prefers _m; falls back to _s, then same tier
				if _species_meshes.has(species + "_m"):
					lod_tier_suffix = "_m"
				elif _species_meshes.has(species + "_s"):
					lod_tier_suffix = "_s"
				else:
					lod_tier_suffix = tier_suffix
			else:
				# LOD2 always _s (cheapest 3D)
				if _species_meshes.has(species + "_s"):
					lod_tier_suffix = "_s"
				elif _species_meshes.has(species + "_m"):
					lod_tier_suffix = "_m"
				else:
					lod_tier_suffix = tier_suffix
			var lod_sp := species + lod_tier_suffix
			if not _species_meshes.has(lod_sp):
				lod_sp = "deciduous" + lod_tier_suffix
			if not _species_meshes.has(lod_sp):
				# Final fallback: reuse the tree's own mesh rather than
				# skipping this LOD tier (which creates a visibility gap)
				lod_sp = species + tier_suffix
			if not _species_meshes.has(lod_sp):
				continue  # truly no mesh available
			var lod_vars: Array = _species_meshes[lod_sp]
			var lod_vi := i % lod_vars.size()
			var lod_mh: float = _species_heights.get(lod_sp, mesh_h)
			var lod_sy := desired_h / maxf(lod_mh, 0.06)
			var lod_sx := lod_sy * (1.50 if species == "cathedral_elm" else 1.0)
			var lod_basis := Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(lod_sx, lod_sy, lod_sx))
			var lod_tf := Transform3D(lod_basis, Vector3(tx, ty, tz))
			var lod_key := "%s_%d" % [lod_sp, lod_vi]
			var xf_dict: Dictionary = _lod1_xf if lod_idx == 1 else _lod2_xf
			var cd_dict: Dictionary = _lod1_cd if lod_idx == 1 else _lod2_cd
			if not xf_dict.has(lod_key):
				xf_dict[lod_key] = []
				cd_dict[lod_key] = []
			xf_dict[lod_key].append(lod_tf)
			cd_dict[lod_key].append(cd)

		# Canopy data for dappled shade map + LOD1 shells.
		# LiDAR crown_a measures only the dense inner canopy (often 10-30m²
		# for a 20m tree), producing absurdly small crown radii (1-3m).
		# Use proportional radius from desired_h instead — matches visual spread.
		var crown_r: float = desired_h * (0.25 if species == "conifer" else 0.35)
		canopy_data.append({"x": tx, "z": tz, "r": crown_r, "ev": species == "conifer"})

		# LOD1 canopy shell data — collected for dome mesh generation
		_shell_data.append({"x": tx, "y": ty, "z": tz, "h": desired_h,
			"r": crown_r, "sp": pheno_idx, "ev": is_evergreen,
			"timing": timing_off + 0.5, "dead": species == "dead",
			"archetype": species, "jitter": color_jitter})

		# Collision: trunk cylinder from actual DBH data (census measurement)
		var trunk_r: float
		if dbh > 0:
			trunk_r = float(dbh) * 0.0254 * 0.5  # DBH inches → radius metres
			trunk_r = maxf(trunk_r, 0.05)  # minimum 5cm radius
		else:
			trunk_r = desired_h * 0.012  # fallback: slimmer ratio than old 0.02
		var col_basis := Basis(
			Vector3(trunk_r, 0.0,      0.0),
			Vector3(0.0,     desired_h, 0.0),
			Vector3(0.0,     0.0,      trunk_r))
		all_trunk_xf.append(Transform3D(col_basis, Vector3(tx, ty + desired_h * 0.5, tz)))

	# --- Spatial chunking for culling ---
	# Each chunk's MMI is positioned at its spatial centre so that
	# visibility_range works per-chunk (distance from camera to node).
	const CHUNK := 80.0

	# Woodland Z ranges where canopy is dense enough for occlusion culling
	const WOODLAND_Z := [
		[-1800.0, -1050.0],  # North Woods + The Pool
		[375.0, 975.0],      # The Ramble
		[1650.0, 2050.0],    # Hallett & The Pond
	]

	# Per-spatial-chunk canopy bounds for occluder generation
	# Key: "cx|cz" → {y_min, y_max, x_min, x_max, z_min, z_max, count}
	var chunk_bounds: Dictionary = {}

	# Bucket transforms by spatial chunk per-species-variant
	var lod0_chunks: Dictionary = {}

	for key in xf_by_key:
		var xf_arr: Array = xf_by_key[key]
		var cd_arr: Array = cd_by_key[key]
		for j in xf_arr.size():
			var tf: Transform3D = xf_arr[j]
			var cx := int(floorf(tf.origin.x / CHUNK))
			var cz := int(floorf(tf.origin.z / CHUNK))
			var ck0 := "%s|%d|%d" % [key, cx, cz]
			if not lod0_chunks.has(ck0):
				lod0_chunks[ck0] = {"mesh_key": key, "cx": cx, "cz": cz, "xf": [], "cd": []}
			lod0_chunks[ck0]["xf"].append(tf)
			lod0_chunks[ck0]["cd"].append(cd_arr[j])
			# Accumulate per-spatial-chunk canopy bounds for occluders
			var bk := "%d|%d" % [cx, cz]
			var px := tf.origin.x
			var py := tf.origin.y
			var pz := tf.origin.z
			var tree_h: float = tf.basis.y.length() * float(_species_heights.get(key.substr(0, key.rfind("_")), 15.0))
			var crown_top: float = py + tree_h
			var crown_base: float = py + tree_h * 0.4
			if not chunk_bounds.has(bk):
				chunk_bounds[bk] = {"x0": px, "x1": px, "z0": pz, "z1": pz,
					"yb": crown_base, "yt": crown_top, "n": 1}
			else:
				var b: Dictionary = chunk_bounds[bk]
				b["x0"] = minf(b["x0"], px)
				b["x1"] = maxf(b["x1"], px)
				b["z0"] = minf(b["z0"], pz)
				b["z1"] = maxf(b["z1"], pz)
				b["yb"] = minf(b["yb"], crown_base)
				b["yt"] = maxf(b["yt"], crown_top)
				b["n"] += 1

	# Spawn LOD0 chunks — position MMI at instance centroid for accurate culling
	for ckey in lod0_chunks:
		var info: Dictionary = lod0_chunks[ckey]
		var mesh_key: String = info["mesh_key"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue
		var last_us := mesh_key.rfind("_")
		var sp_name: String = mesh_key.substr(0, last_us)
		var vi: int = int(mesh_key.substr(last_us + 1))
		var mesh: Mesh = _species_meshes[sp_name][vi]
		var cx_sum := 0.0
		var cy_sum := 0.0
		var cz_sum := 0.0
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
			var local_tf := Transform3D(tf.basis, tf.origin - chunk_origin)
			mm.set_instance_transform(i, local_tf)
			mm.set_instance_custom_data(i, cd_list[i])
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = chunk_origin
		mmi.name = "Tree_%s" % ckey.replace("|", "_")
		# LOD0: full geometry — extended range for leafy canopy visibility
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_end = 180.0
		mmi.visibility_range_begin_margin = 0.0
		mmi.visibility_range_end_margin = 50.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		_loader.add_child(mmi)

	# --- Canopy occluders for dense woodland chunks ---
	var occ_count := 0
	for bk in chunk_bounds:
		var b: Dictionary = chunk_bounds[bk]
		if b["n"] < 6:
			continue  # too sparse to occlude
		var parts: PackedStringArray = bk.split("|")
		var cx_i := int(parts[0])
		var cz_i := int(parts[1])
		var chunk_center_z := (cz_i + 0.5) * CHUNK
		var in_woodland := false
		for zr in WOODLAND_Z:
			if chunk_center_z >= zr[0] and chunk_center_z <= zr[1]:
				in_woodland = true
				break
		if not in_woodland:
			continue
		# Build box occluder spanning the canopy volume
		var sx: float = maxf(float(b["x1"]) - float(b["x0"]), 4.0)
		var sz: float = maxf(float(b["z1"]) - float(b["z0"]), 4.0)
		var sy: float = maxf(float(b["yt"]) - float(b["yb"]), 3.0)
		# Shrink slightly so camera inside canopy doesn't trigger self-occlusion
		var occ := BoxOccluder3D.new()
		occ.size = Vector3(sx * 0.85, sy * 0.7, sz * 0.85)
		var oi := OccluderInstance3D.new()
		oi.occluder = occ
		var cx_mid: float = (float(b["x0"]) + float(b["x1"])) * 0.5
		var cz_mid: float = (float(b["z0"]) + float(b["z1"])) * 0.5
		var cy_mid: float = (float(b["yb"]) + float(b["yt"])) * 0.5
		oi.position = Vector3(cx_mid, cy_mid, cz_mid)
		oi.name = "TreeOcc_%d_%d" % [cx_i, cz_i]
		# Limit occluder to range where solid tree geometry exists (LOD0-LOD1).
		# Without this, occluders hide terrain even during LOD gaps, causing
		# terrain to pop in/out and water/land to flicker.
		oi.visibility_range_begin = 0.0
		oi.visibility_range_end = 350.0
		oi.visibility_range_end_margin = 60.0
		_loader.add_child(oi)
		occ_count += 1
	if occ_count > 0:
		print("Trees: %d canopy occluders in woodland zones" % occ_count)

	# --- LOD1: _m models (derived from _l — same silhouette) ---
	_build_lod_tier_chunks(_lod1_xf, _lod1_cd, "TreeL1",
		130.0, 350.0, 50.0, 60.0)
	# --- LOD2: _s models (derived from _l — same silhouette, thinned) ---
	_build_lod_tier_chunks(_lod2_xf, _lod2_cd, "TreeL2",
		300.0, 600.0, 60.0, 80.0)

	_build_tree_collision(all_trunk_xf)
	# Debug: print a few tree heights to verify scale
	var _dbg_count := 0
	for key in xf_by_key:
		if _dbg_count >= 5: break
		var xfs: Array = xf_by_key[key]
		if xfs.size() > 0:
			var tf: Transform3D = xfs[0]
			var sy := tf.basis.y.length()  # Y basis length = scale factor
			var mesh_h_val: float = _species_heights.get(key.split("_")[0], 5.0)
			var actual_h := sy * mesh_h_val  # true world height in metres
			print("  Tree '%s': mesh=%.1fm × sy=%.2f = %.1fm tall, at y=%.1f" % [
				key, mesh_h_val, sy, actual_h, tf.origin.y])
			_dbg_count += 1
	print("Trees: %d placed, %d LOD0 chunks (skipped %d non-grass, nudged %d from paths)" % [
		all_trunk_xf.size(), lod0_chunks.size(), _skip_surface, _nudged])

	# --- LOD2: Crossed-quad impostors for distant trees ---
	_build_canopy_shells()


func _build_lod_tier_chunks(xf_data: Dictionary, cd_data: Dictionary,
		prefix: String, vis_begin: float, vis_end: float,
		begin_margin: float, end_margin: float) -> void:
	## Generic LOD tier chunk builder. Spawns MultiMesh chunks from
	## pre-collected transform/custom-data dictionaries.
	if xf_data.is_empty():
		return
	const CHUNK := 80.0
	var chunks: Dictionary = {}
	for key in xf_data:
		var xf_arr: Array = xf_data[key]
		var cd_arr: Array = cd_data[key]
		for j in xf_arr.size():
			var tf: Transform3D = xf_arr[j]
			var cx := int(floorf(tf.origin.x / CHUNK))
			var cz := int(floorf(tf.origin.z / CHUNK))
			var ck := "%s|%d|%d" % [key, cx, cz]
			if not chunks.has(ck):
				chunks[ck] = {"mesh_key": key, "xf": [], "cd": []}
			chunks[ck]["xf"].append(tf)
			chunks[ck]["cd"].append(cd_arr[j])

	var instance_count := 0
	for ckey in chunks:
		var info: Dictionary = chunks[ckey]
		var mesh_key: String = info["mesh_key"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue
		var last_us := mesh_key.rfind("_")
		var sp_name: String = mesh_key.substr(0, last_us)
		var vi: int = int(mesh_key.substr(last_us + 1))
		if not _species_meshes.has(sp_name):
			continue
		var variants: Array = _species_meshes[sp_name]
		if vi >= variants.size():
			continue
		var mesh: Mesh = variants[vi]
		var cx_sum := 0.0; var cy_sum := 0.0; var cz_sum := 0.0
		for tf: Transform3D in xf_list:
			cx_sum += tf.origin.x; cy_sum += tf.origin.y; cz_sum += tf.origin.z
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
		mmi.name = "%s_%s" % [prefix, ckey.replace("|", "_")]
		mmi.visibility_range_begin = vis_begin
		mmi.visibility_range_end = vis_end
		mmi.visibility_range_begin_margin = begin_margin
		mmi.visibility_range_end_margin = end_margin
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		_loader.add_child(mmi)
		instance_count += xf_list.size()

	print("%s: %d instances in %d chunks (%.0f-%.0fm)" % [
		prefix, instance_count, chunks.size(), vis_begin, vis_end])
	xf_data.clear()
	cd_data.clear()


func _build_tree_collision(trunk_xf: Array) -> void:
	if trunk_xf.is_empty():
		return
	# One StaticBody3D with a CylinderShape3D per trunk.
	# trunk_xf basis encodes scale + Y rotation. Extract via column lengths.
	var body := StaticBody3D.new()
	body.name = "TreeTrunkCollision"
	for tf: Transform3D in trunk_xf:
		var r: float = tf.basis.x.length()   # trunk_r (x column length)
		var h: float = tf.basis.y.y           # trunk_h (y unaffected by Y rotation)
		var shape        := CylinderShape3D.new()
		shape.radius      = r
		shape.height      = h
		var col          := CollisionShape3D.new()
		col.shape         = shape
		col.position      = tf.origin  # already at trunk centre (base + h/2)
		body.add_child(col)
	_loader.add_child(body)


func _tree_glb_leaf_shader_code() -> String:
	return "res://shaders/tree_leaf.gdshader"


# ---------------------------------------------------------------------------
# LOD3: Octahedral billboard impostors — single quad per tree with
# view-dependent atlas sampling, normal maps, and depth parallax.
# ---------------------------------------------------------------------------

const IMPOSTOR_FRAME_SIZE := 8  # 8×8 octahedral grid (hemisphere)
const IMPOSTOR_DIR := "res://textures/impostors"

# Map archetype model name → impostor atlas filename
var _impostor_textures: Dictionary = {}  # model_name -> Texture2D (albedo)
var _impostor_normals: Dictionary = {}   # model_name -> Texture2D (normal)
var _impostor_depths: Dictionary = {}    # model_name -> Texture2D (depth)
var _impostor_materials: Dictionary = {}  # model_name -> ShaderMaterial
var _impostor_meta: Dictionary = {}      # model_name -> {"scale": float, ...}

func _load_impostor_atlases() -> void:
	"""Load baked impostor atlas textures + metadata for all tree species."""
	var impostor_shader: Shader = load("res://shaders/tree_impostor.gdshader")
	if not impostor_shader:
		print("Trees LOD3: impostor shader not found")
		return

	for model_name in ARCHETYPE_MODEL.values():
		if _impostor_textures.has(model_name):
			continue
		var albedo_path := "%s/%s_impostor_albedo.png" % [IMPOSTOR_DIR, model_name]
		var tex: Texture2D = load(albedo_path)
		if not tex:
			continue
		_impostor_textures[model_name] = tex

		# Load normal and depth atlases (optional — shader has fallbacks)
		var normal_path := "%s/%s_impostor_normal.png" % [IMPOSTOR_DIR, model_name]
		var depth_path := "%s/%s_impostor_depth.png" % [IMPOSTOR_DIR, model_name]
		var normal_tex: Texture2D = load(normal_path)
		var depth_tex: Texture2D = load(depth_path)
		if normal_tex:
			_impostor_normals[model_name] = normal_tex
		if depth_tex:
			_impostor_depths[model_name] = depth_tex

		# Load baking metadata
		var meta_path := ProjectSettings.globalize_path(
			"%s/%s_impostor_meta.json" % [IMPOSTOR_DIR, model_name])
		var imp_scale := 3.5  # fallback
		var pos_offset := Vector3.ZERO
		var aabb_max := 1.75
		if FileAccess.file_exists(meta_path):
			var f := FileAccess.open(meta_path, FileAccess.READ)
			var json := JSON.new()
			if json.parse(f.get_as_text()) == OK:
				var d: Dictionary = json.data
				imp_scale = d.get("scale", imp_scale)
				aabb_max = d.get("aabb_max", imp_scale * 0.5)
				var po: Array = d.get("position_offset", [0, 0, 0])
				pos_offset = Vector3(po[0], po[1], po[2])
			f.close()
		_impostor_meta[model_name] = {
			"scale": imp_scale,
			"position_offset": pos_offset,
			"aabb_max": aabb_max,
		}

		# Create material — billboard impostor shader
		var mat := ShaderMaterial.new()
		mat.shader = impostor_shader
		mat.set_shader_parameter("atlas", tex)
		mat.set_shader_parameter("frames", Vector2(IMPOSTOR_FRAME_SIZE, IMPOSTOR_FRAME_SIZE))
		mat.set_shader_parameter("alpha_clamp", 0.2)
		mat.set_shader_parameter("scale", imp_scale)
		mat.set_shader_parameter("aabb_max", aabb_max)
		mat.set_shader_parameter("position_offset", pos_offset)
		if normal_tex:
			mat.set_shader_parameter("atlas_normal", normal_tex)
		if depth_tex:
			mat.set_shader_parameter("atlas_depth", depth_tex)
			mat.set_shader_parameter("depth_scale", 0.3)
		_impostor_materials[model_name] = mat

	var n_with_normals := _impostor_normals.size()
	var n_with_depth := _impostor_depths.size()
	print("Trees LOD3: loaded %d impostor atlases (%d with normals, %d with depth)" % [
		_impostor_textures.size(), n_with_normals, n_with_depth])


func _create_billboard_quad_mesh() -> ArrayMesh:
	"""Build a single quad (2 triangles) in XY plane, unit scale.
	Billboard rotation happens in shader via SpriteProjection."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var normal := Vector3(0.0, 0.0, 1.0)
	# Tri 1: bl, br, tr
	st.set_normal(normal); st.set_uv(Vector2(0, 1)); st.add_vertex(Vector3(-0.5, -0.5, 0))
	st.set_normal(normal); st.set_uv(Vector2(1, 1)); st.add_vertex(Vector3(0.5, -0.5, 0))
	st.set_normal(normal); st.set_uv(Vector2(1, 0)); st.add_vertex(Vector3(0.5, 0.5, 0))
	# Tri 2: bl, tr, tl
	st.set_normal(normal); st.set_uv(Vector2(0, 1)); st.add_vertex(Vector3(-0.5, -0.5, 0))
	st.set_normal(normal); st.set_uv(Vector2(1, 0)); st.add_vertex(Vector3(0.5, 0.5, 0))
	st.set_normal(normal); st.set_uv(Vector2(0, 0)); st.add_vertex(Vector3(-0.5, 0.5, 0))
	return st.commit()


func _build_canopy_shells() -> void:
	if _shell_data.is_empty():
		return

	_load_impostor_atlases()

	if _impostor_materials.is_empty():
		print("Trees LOD3: no impostor atlases found — skipping")
		return

	# Single billboard quad — shader handles orientation via SpriteProjection
	var billboard_mesh := _create_billboard_quad_mesh()

	# Bucket into spatial chunks × species (each species needs its own material)
	const CHUNK := 80.0
	var chunks: Dictionary = {}  # "cx|cz|model" -> {"xf": [], "cd": [], "model": ""}

	for sd in _shell_data:
		if sd.dead:
			continue
		var model_name: String = ARCHETYPE_MODEL.get(sd.archetype, "deciduous")
		if not _impostor_materials.has(model_name):
			model_name = "deciduous"
		if not _impostor_materials.has(model_name):
			continue

		var cx: int = int(floorf(sd.x / CHUNK))
		var cz: int = int(floorf(sd.z / CHUNK))
		var ck := "%d|%d|%s" % [cx, cz, model_name]
		if not chunks.has(ck):
			chunks[ck] = {"xf": [], "cd": [], "model": model_name}

		# Scale: billboard is unit-sized, needs to cover the tree at world height.
		# The shader's scale uniform controls atlas projection; the mesh scale
		# handles world-space sizing. scale_ratio maps the 5m model to actual height.
		var scale_ratio: float = sd.h / 5.0
		var mesh_scale: float = scale_ratio
		# No Y rotation — billboard shader faces camera automatically from every angle
		var basis := Basis().scaled(Vector3.ONE * mesh_scale)

		var crown_y: float = sd.y + sd.h * 0.5
		var tf := Transform3D(basis, Vector3(sd.x, crown_y, sd.z))
		chunks[ck].xf.append(tf)
		chunks[ck].cd.append(Color(float(sd.sp) / 13.0, sd.timing, sd.ev, sd.jitter))

	# Create MultiMesh chunks per species
	var impostor_count := 0
	for ck in chunks:
		var chunk_data: Dictionary = chunks[ck]
		var xf_list: Array = chunk_data.xf
		var cd_list: Array = chunk_data.cd
		var model_name: String = chunk_data.model
		if xf_list.is_empty():
			continue

		var cx_sum := 0.0
		var cy_sum := 0.0
		var cz_sum := 0.0
		for tf: Transform3D in xf_list:
			cx_sum += tf.origin.x
			cy_sum += tf.origin.y
			cz_sum += tf.origin.z
		var n := float(xf_list.size())
		var chunk_origin := Vector3(cx_sum / n, cy_sum / n, cz_sum / n)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = billboard_mesh
		mm.instance_count = xf_list.size()
		for i in xf_list.size():
			var tf: Transform3D = xf_list[i]
			var local_tf := Transform3D(tf.basis, tf.origin - chunk_origin)
			mm.set_instance_transform(i, local_tf)
			mm.set_instance_custom_data(i, cd_list[i])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = _impostor_materials[model_name]
		mmi.position = chunk_origin
		mmi.name = "TreeImp_%s_%s" % [model_name, ck.get_slice("|", 0) + "_" + ck.get_slice("|", 1)]
		# LOD3: octahedral billboard impostors — overlap with _s for smooth handoff
		mmi.visibility_range_begin = 500.0
		mmi.visibility_range_end = 2500.0
		mmi.visibility_range_begin_margin = 100.0
		mmi.visibility_range_end_margin = 200.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		impostor_count += xf_list.size()

	print("Trees LOD3: %d octahedral billboard impostors in %d chunks (%d species)" % [
		impostor_count, chunks.size(), _impostor_materials.size()])
