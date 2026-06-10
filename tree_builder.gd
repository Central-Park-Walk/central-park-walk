# tree_builder.gd
# Tree geometry: GLB-based trees with spatially chunked MultiMesh instances
# Extracted from park_loader.gd — all shared utilities accessed via _loader reference.

var _loader  # Reference to park_loader for shared utilities
var _shell_data: Array = []  # per-tree data for impostor billboards
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
var _lod1_xf: Dictionary = {}  # LOD1 (decimated _lod1 mesh) transforms per key
var _lod1_cd: Dictionary = {}  # LOD1 custom data per key
var _species_meshes: Dictionary = {}  # archetype_name -> Array[Mesh]
var _species_heights: Dictionary = {} # archetype_name -> float (mesh height)

# MMI / instance counts per LOD tier — read by HUD perf overlay
var lod0_instances: int = 0
var lod0_chunks: int = 0
var lod1_instances: int = 0
var lod1_chunks: int = 0
var imp_instances: int = 0
var imp_chunks: int = 0

# Shadow proxies (docs/trees.md §3, prototype): visible trees stop casting;
# a ~90-tri trunk+crown hull per species-variant casts instead (SHADOWS_ONLY).
# Flag-gated for A/B measurement until the perf gate + visual DoD pass.
var _shadow_proxy: bool = false
var _proxy_mesh_cache: Dictionary = {}  # mesh_key -> ArrayMesh
var proxy_instances: int = 0
# --tier-isolate=mesh|impostor (diagnostic): render ONLY that tree tier with
# crossfade dither disabled, so DoD captures can compare pure tiers at the
# same distance (docs/trees.md §2 validation).
var _tier_isolate: String = ""

func _init(loader) -> void:
	_loader = loader
	_shadow_proxy = "--tree-shadow-proxy" in OS.get_cmdline_user_args()
	if _shadow_proxy:
		print("TreeBuilder: shadow proxies ON (visible trees cast nothing)")
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--tier-isolate="):
			_tier_isolate = arg.substr("--tier-isolate=".length())
			print("TreeBuilder: TIER ISOLATE '%s' — single tier, no crossfade (diagnostic)" % _tier_isolate)

# Size tier boundaries per species: [small_max, medium_max]
# Trees below small_max use _s model, below medium_max use _m, else _l.
# Matches the height_range overlaps in scripts/generate_trees_mtree.py.
const TIER_BOUNDS := {
	"oak":           [12.0, 20.0],
	"maple":         [14.0, 22.0],
	"elm":           [14.0, 22.0],
	"cathedral_elm": [0.0, 26.0],   # no _s tier — all Mall elms are mature
	"deciduous":     [14.0, 22.0],
	"birch":         [0.0, 12.0],   # no _s tier (0 in census)
	"cherry":        [9.0, 16.0],
	"honeylocust":   [14.0, 22.0],
	"callery_pear":  [10.0, 18.0],
	"ginkgo":        [14.0, 22.0],
	"london_plane":  [0.0, 25.0],   # no _s tier (0 in census)
	"linden":        [14.0, 22.0],
	"willow":        [14.0, 999.0], # no _l tier (0 in census); only _s and _m
	"magnolia":      [0.0, 0.0],    # only _s tier (41 in census, all small)
	"conifer":       [0.0, 18.0],   # no _s tier (0 in census); shares pine models
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
	## Returns empty dict on cache miss or stale cache.
	var meta_path := CACHE_DIR + model_name + ".cfg"
	if not FileAccess.file_exists(meta_path):
		return {}
	# Invalidate cache if source GLB is newer than cached .cfg
	var glb_path := ProjectSettings.globalize_path("res://models/trees/%s.glb" % model_name)
	var cfg_abs := ProjectSettings.globalize_path(meta_path)
	if FileAccess.file_exists(glb_path):
		var glb_time := FileAccess.get_modified_time(glb_path)
		var cfg_time := FileAccess.get_modified_time(cfg_abs)
		if glb_time > cfg_time:
			return {}  # source is newer — force re-parse
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
	# Uses class members _species_meshes and _species_heights.
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
	# Load tiered models (_s, _m, _l): age/size variants per archetype.
	# Plus _lod1 decimated variants of each (same tree, fewer polygons) for
	# the 3-tier LOD system (LOD0 mesh → LOD1 decimated → impostor).
	for base_name in _base_model_names:
		var tier_list: Array
		if base_name == "dead":
			tier_list = [""]
		else:
			tier_list = ["_s", "_m", "_l"]
		var full_list: Array = []
		for ts in tier_list:
			full_list.append(ts)
			if ts != "":
				full_list.append(ts + "_lod1")
		for tier_suffix in full_list:
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
			tier_suffixes = ["_s", "_m", "_l", "_s_lod1", "_m_lod1", "_l_lod1"]
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
							# Prefer DDS with coverage-preserving mipmaps over GLB-embedded texture
							var dds_path := "res://textures/leaves/%s_leaf.dds" % model_base
							if ResourceLoader.exists(dds_path):
								leaf_mat.set_shader_parameter("albedo_tex", load(dds_path))
							elif ltexs[mi]:
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

		# Pick variant deterministically per (species_tier, 80m-cell) so all
		# same-species trees in one MMI chunk share a mesh. Without this, the
		# per-tree `i % n_variants` fragments every 80m cell into one MMI per
		# variant — turning 6808 LOD0 instances into 4315 tiny MMIs (avg 1.6
		# instances each). Per-cell variants collapse that to ~1500 chunks.
		# 80.0 here MUST match CHUNK used in the spawning loop below.
		var cx_var := int(floorf(tx / 80.0))
		var cz_var := int(floorf(tz / 80.0))
		var variant_idx: int = int(abs(hash("%s|%d|%d" % [species_tier, cx_var, cz_var]))) % n_variants

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

		# Two-tier LOD: _lod1 mesh is used directly in the main chunk pathway
		# below (mesh lookup swap at chunk-build time), so there's no longer
		# a separate LOD1 accumulation. Impostors take over past 250m.

		# Canopy data for dappled shade map.
		# LiDAR crown_a measures only the dense inner canopy (often 10-30m²
		# for a 20m tree), producing absurdly small crown radii (1-3m).
		# Use proportional radius from desired_h instead — matches visual spread.
		var crown_r: float = desired_h * (0.25 if species == "conifer" else 0.35)
		canopy_data.append({"x": tx, "z": tz, "r": crown_r, "ev": species == "conifer"})

		# Impostor data — per-tree info for billboard generation
		_shell_data.append({"x": tx, "y": ty, "z": tz, "h": desired_h,
			"r": crown_r, "sp": pheno_idx, "ev": is_evergreen,
			"timing": timing_off + 0.5, "dead": species == "dead",
			"archetype": species, "jitter": color_jitter,
			"tier": tier_suffix.trim_prefix("_")})

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
	var lod0_buckets: Dictionary = {}

	for key in xf_by_key:
		var xf_arr: Array = xf_by_key[key]
		var cd_arr: Array = cd_by_key[key]
		for j in xf_arr.size():
			var tf: Transform3D = xf_arr[j]
			var cx := int(floorf(tf.origin.x / CHUNK))
			var cz := int(floorf(tf.origin.z / CHUNK))
			var ck0 := "%s|%d|%d" % [key, cx, cz]
			if not lod0_buckets.has(ck0):
				lod0_buckets[ck0] = {"mesh_key": key, "cx": cx, "cz": cz, "xf": [], "cd": []}
			lod0_buckets[ck0]["xf"].append(tf)
			lod0_buckets[ck0]["cd"].append(cd_arr[j])
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
	for ckey in lod0_buckets:
		var info: Dictionary = lod0_buckets[ckey]
		var mesh_key: String = info["mesh_key"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue
		var last_us := mesh_key.rfind("_")
		var sp_name: String = mesh_key.substr(0, last_us)
		var vi: int = int(mesh_key.substr(last_us + 1))
		# Two-tier LOD: render the _lod1 decimated mesh in the main chunk
		# pathway so close and mid-distance share one tier. Falls back to the
		# base mesh only if no _lod1 variant exists (e.g., dead snags).
		var lod1_key: String = sp_name + "_lod1"
		var mesh_source: String = lod1_key if _species_meshes.has(lod1_key) else sp_name
		var lod1_vars: Array = _species_meshes[mesh_source]
		var mesh: Mesh = lod1_vars[vi % lod1_vars.size()]
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
		# Two-tier LOD: single mesh tier (_lod1) covers 0-290m, dithers out
		# 230-250m to the impostor. Chunk visibility extends 40m past the
		# fade end (= half CHUNK) so chunks whose origin is past 250m but
		# contain near-side instances at 210-250m still render.
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_end = 290.0
		mmi.visibility_range_begin_margin = 0.0
		mmi.visibility_range_end_margin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		if _shadow_proxy:
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			var pmm := MultiMesh.new()
			pmm.transform_format = MultiMesh.TRANSFORM_3D
			pmm.mesh = _get_shadow_proxy_mesh(mesh_source, sp_name, mesh)
			pmm.instance_count = xf_list.size()
			for i in xf_list.size():
				var tf: Transform3D = xf_list[i]
				pmm.set_instance_transform(i, Transform3D(tf.basis, tf.origin - chunk_origin))
			var pmmi := MultiMeshInstance3D.new()
			pmmi.multimesh = pmm
			pmmi.position = chunk_origin
			pmmi.name = "ShdwProxy_%s" % ckey.replace("|", "_")
			pmmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
			pmmi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
			pmmi.visibility_range_begin = 0.0
			pmmi.visibility_range_end = 290.0
			pmmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
			_loader.add_child(pmmi)
			proxy_instances += xf_list.size()
		if _tier_isolate != "impostor":
			_loader.add_child(mmi)
		lod0_instances += xf_list.size()
		lod0_chunks += 1

	# Canopy occluders disabled: OccluderInstance3D inherits Node3D (not
	# GeometryInstance3D) so visibility_range cannot limit them. Without a
	# distance gate they stay active at all ranges, hiding distant impostor
	# trees behind canopy boxes and making distant woodland look sparse.

	# Two-tier LOD: separate LOD1 chunk pass removed — the _lod1 mesh is now
	# rendered directly by the main chunk pathway above (mesh lookup swap),
	# so there's a single mesh tier from 0-290m that hands off to impostors.

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
		all_trunk_xf.size(), lod0_buckets.size(), _skip_surface, _nudged])

	# --- Impostors: octahedral billboards for distant trees (>90m) ---
	_build_canopy_shells()

	# Per-tier dither fade ranges. Shader dithering replaces Godot's
	# VISIBILITY_RANGE_FADE_SELF (known bug #88854 with alpha_to_coverage).
	# Two-tier system:
	#   _lod1 mesh:  visible 0-290m, fades out 230-250m → impostor.
	#   Base mesh:   unused (kept for impostor data); no fade needed.
	#   Impostor:    fades in 230-250m (set in _build_canopy_shells).
	const MESH_FADE_OUT := Vector2(230.0, 250.0)
	const NO_FADE := Vector2(0.0, 0.0)
	for sp_key in _species_meshes:
		var fade_in := NO_FADE
		var fade_out := NO_FADE
		# tier_brightness was originally LOD1 compensation for reading brighter
		# than LOD0 at distance. With one mesh tier covering 0-290m, that
		# rationale is gone — 0.95 keeps a slight knock-down so close trees
		# don't blast bright, without the heavy darkening the 0.82 produced.
		var tier_brightness: float = 0.95 if "_lod1" in sp_key else 1.0
		if "_lod1" in sp_key and _tier_isolate != "mesh":
			fade_out = MESH_FADE_OUT
		for mesh: Mesh in _species_meshes[sp_key]:
			for si in mesh.get_surface_count():
				var mat = mesh.surface_get_material(si)
				if mat is ShaderMaterial:
					mat.set_shader_parameter("lod_fade_out", fade_out)
					mat.set_shader_parameter("lod_fade_in", fade_in)
					mat.set_shader_parameter("tier_brightness", tier_brightness)


func _build_lod_tier_chunks(xf_data: Dictionary, cd_data: Dictionary,
		prefix: String, vis_begin: float, vis_end: float,
		cast_shadow: bool = true) -> void:
	## Spawns MultiMesh chunks for a single LOD tier from pre-collected
	## transform/custom-data dictionaries. Visibility range limits when the
	## tier's chunks are drawn; shader-side dither (set_shader_parameter
	## "lod_fade_in" / "lod_fade_out") handles the crossfade with neighbors.
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
		mmi.visibility_range_begin_margin = 0.0
		mmi.visibility_range_end_margin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		if not cast_shadow:
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		instance_count += xf_list.size()
		if prefix == "TreeL1":
			lod1_instances += xf_list.size()
			lod1_chunks += 1

	print("%s: %d instances in %d chunks (%.0f-%.0fm)" % [
		prefix, instance_count, chunks.size(), vis_begin, vis_end])
	xf_data.clear()
	cd_data.clear()


func _get_shadow_proxy_mesh(mesh_key: String, sp_name: String, src: Mesh) -> ArrayMesh:
	## Whole-tree shadow caster (docs/trees.md §3): trunk cylinder + crown hull
	## fit to the variant mesh AABB, in the same model space so instance
	## transforms are shared with the visible MMI. ~90 tris vs 10k+ foliage.
	if _proxy_mesh_cache.has(mesh_key):
		return _proxy_mesh_cache[mesh_key]
	var ab: AABB = src.get_aabb()
	var h: float = ab.size.y
	var base_y: float = ab.position.y
	var cx: float = ab.position.x + ab.size.x * 0.5
	var cz: float = ab.position.z + ab.size.z * 0.5
	var crown_w: float = maxf(ab.size.x, ab.size.z)
	var is_conifer := sp_name.begins_with("conifer")
	var crown_base: float = base_y + h * (0.12 if is_conifer else 0.35)
	var crown_h: float = base_y + h - crown_base
	var am := ArrayMesh.new()
	# Trunk
	var trunk := CylinderMesh.new()
	trunk.radial_segments = 6
	trunk.rings = 1
	trunk.cap_top = false
	trunk.cap_bottom = false
	trunk.top_radius = maxf(h * 0.012, 0.10)
	trunk.bottom_radius = maxf(h * 0.018, 0.14)
	trunk.height = crown_base - base_y + crown_h * 0.2  # reach into the crown
	_append_offset_surface(am, trunk, Vector3(cx, base_y + trunk.height * 0.5, cz))
	# Crown: squashed sphere for broadleaf, cone for conifers
	if is_conifer:
		var cone := CylinderMesh.new()
		cone.radial_segments = 8
		cone.rings = 1
		cone.cap_bottom = true
		cone.cap_top = false
		cone.top_radius = 0.0
		cone.bottom_radius = crown_w * 0.5
		cone.height = crown_h
		_append_offset_surface(am, cone, Vector3(cx, crown_base + crown_h * 0.5, cz))
	else:
		var crown := SphereMesh.new()
		crown.radial_segments = 8
		crown.rings = 4
		crown.radius = crown_w * 0.5
		crown.height = crown_h
		_append_offset_surface(am, crown, Vector3(cx, crown_base + crown_h * 0.5, cz))
	# Dapple: world-space noise discard on the crown so the shadow map gets
	# holes PCF blurs into mottled canopy light (docs/trees.md §3). Conifers
	# keep a denser crown (real conifer shade is near-solid).
	var crown_mat := ShaderMaterial.new()
	crown_mat.shader = _proxy_dapple_shader()
	crown_mat.set_shader_parameter("coverage", 0.80 if is_conifer else 0.62)
	am.surface_set_material(1, crown_mat)
	_proxy_mesh_cache[mesh_key] = am
	return am


var _dapple_shader: Shader = null
func _proxy_dapple_shader() -> Shader:
	if _dapple_shader:
		return _dapple_shader
	_dapple_shader = Shader.new()
	# Runs in the shadow (depth) pass — discard punches leaf-density holes.
	# World-space hash so holes are stable per tree and don't swim.
	_dapple_shader.code = """
shader_type spatial;
render_mode unshaded, cull_disabled;

uniform float coverage : hint_range(0.0, 1.0) = 0.62;
uniform float hole_scale = 1.1;

float hash3(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

void fragment() {
	vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	if (hash3(floor(wp / hole_scale)) > coverage) {
		discard;
	}
}
"""
	return _dapple_shader


func _append_offset_surface(am: ArrayMesh, prim: PrimitiveMesh, offset: Vector3) -> void:
	var arrays: Array = prim.get_mesh_arrays()
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	for i in verts.size():
		verts[i] += offset
	arrays[Mesh.ARRAY_VERTEX] = verts
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)


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
# Impostor: octahedral billboard — camera-facing quad with view-dependent
# atlas sampling. The shader selects and blends 3 nearest atlas frames based on
# camera angle, with depth-based parallax correction for pseudo-3D appearance.
# Uses per-species 8×8 hemi-octahedral atlases (albedo + normal + depth).
# ---------------------------------------------------------------------------

const IMPOSTOR_DIR := "res://textures/impostors"

func _create_billboard_quad_mesh() -> ArrayMesh:
	"""Simple unit quad for billboard impostor. UVs 0→1 drive the shader's
	billboard projection — actual vertex positions are overwritten by the shader."""
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := Vector3(0.0, 0.0, 1.0)
	# Tri 1: BL, BR, TR
	st.set_normal(n); st.set_uv(Vector2(0.0, 1.0)); st.add_vertex(Vector3(-0.5, -0.5, 0.0))
	st.set_normal(n); st.set_uv(Vector2(1.0, 1.0)); st.add_vertex(Vector3( 0.5, -0.5, 0.0))
	st.set_normal(n); st.set_uv(Vector2(1.0, 0.0)); st.add_vertex(Vector3( 0.5,  0.5, 0.0))
	# Tri 2: BL, TR, TL
	st.set_normal(n); st.set_uv(Vector2(0.0, 1.0)); st.add_vertex(Vector3(-0.5, -0.5, 0.0))
	st.set_normal(n); st.set_uv(Vector2(1.0, 0.0)); st.add_vertex(Vector3( 0.5,  0.5, 0.0))
	st.set_normal(n); st.set_uv(Vector2(0.0, 0.0)); st.add_vertex(Vector3(-0.5,  0.5, 0.0))
	return st.commit()

func _build_canopy_shells() -> void:
	if _shell_data.is_empty():
		return
	if _tier_isolate == "mesh":
		print("Trees Impostor: skipped (--tier-isolate=mesh)")
		return

	# Load octahedral billboard impostor shader — view-dependent 3-frame
	# blending with depth parallax for photorealistic distant trees.
	var impostor_shader: Shader = load("res://shaders/tree_impostor.gdshader")
	if not impostor_shader:
		print("Trees Impostor: impostor shader not found")
		return

	# Load impostor atlas textures (albedo + normal + depth) and metadata.
	# Per-tier atlases (e.g. oak_m) preferred for shape matching; falls back
	# to generic species atlas (e.g. oak) when per-tier not available.
	var impostor_mats: Dictionary = {}  # "model_tier" or "model" -> ShaderMaterial
	var impostor_meta: Dictionary = {}  # same key -> metadata dict

	# Helper: try to load an impostor material for a given label (e.g. "oak_m" or "oak")
	var _load_impostor_mat := func(label: String) -> bool:
		if impostor_mats.has(label):
			return true
		var albedo_path := "%s/%s_impostor_albedo.png" % [IMPOSTOR_DIR, label]
		if not ResourceLoader.exists(albedo_path):
			return false
		var albedo_tex: Texture2D = load(albedo_path)
		if not albedo_tex:
			return false
		var normal_tex: Texture2D = load("%s/%s_impostor_normal.png" % [IMPOSTOR_DIR, label])
		var depth_tex: Texture2D = load("%s/%s_impostor_depth.png" % [IMPOSTOR_DIR, label])
		# Winter atlas (baked at season_t=3.3 by impostor_baker.gd). When
		# absent — e.g. during a summer-only iteration — fall back to the
		# summer atlas so the shader's winter_mix_t blend is a no-op.
		var winter_path := "%s/%s_impostor_albedo_winter.png" % [IMPOSTOR_DIR, label]
		var winter_tex: Texture2D = load(winter_path) if ResourceLoader.exists(winter_path) else albedo_tex
		var meta := {}
		var meta_file := FileAccess.open("%s/%s_impostor_meta.json" % [IMPOSTOR_DIR, label], FileAccess.READ)
		if meta_file:
			meta = JSON.parse_string(meta_file.get_as_text())
			meta_file.close()
		if meta.is_empty():
			meta = {"scale": 3.0, "aabb_max": 1.5, "position_offset": [0, 0, 0]}
		# Override scale + position_offset using live LOD0 mesh AABB so the
		# runtime billboard always matches the active impostor_baker.gd
		# framing regardless of which baker last wrote meta JSON. Use the
		# same diagonal-based radius the baker uses — tighter framing
		# (max_dim) clips silhouettes at oblique viewing angles.
		var mesh_key := label
		if not _species_meshes.has(mesh_key):
			# Generic fallback (e.g., "oak") → use _m tier as proxy.
			mesh_key = label + "_m"
		var live_scale: float = meta.get("scale", 3.0)
		var live_offset := Vector3.ZERO
		if _species_meshes.has(mesh_key):
			var mesh_variants: Array = _species_meshes[mesh_key]
			if mesh_variants.size() > 0:
				var mab: AABB = (mesh_variants[0] as Mesh).get_aabb()
				live_scale = mab.size.length() * 0.5  # diagonal/2 = baker radius
				live_offset = -mab.get_center()  # billboard pivots at AABB center
		var mat := ShaderMaterial.new()
		mat.shader = impostor_shader
		mat.set_shader_parameter("atlas", albedo_tex)
		mat.set_shader_parameter("atlas_winter", winter_tex)
		mat.set_shader_parameter("atlas_normal", normal_tex if normal_tex else albedo_tex)
		mat.set_shader_parameter("atlas_depth", depth_tex if depth_tex else albedo_tex)
		mat.set_shader_parameter("frames", Vector2(8.0, 8.0))
		mat.set_shader_parameter("scale", live_scale)
		mat.set_shader_parameter("aabb_max", live_scale * 0.5)
		mat.set_shader_parameter("position_offset", live_offset)
		mat.set_shader_parameter("depth_scale", 0.3)
		# Low clamp lets mip-level alpha compensation in tree_impostor.gdshader
		# do its work — fragments with low pre-boost alpha (0.05-0.1) survive
		# the discard test and then get lifted by mip_level * 0.45 so distant
		# impostor silhouettes read solid instead of as a sparse ghost.
		mat.set_shader_parameter("alpha_clamp", 0.05)
		impostor_mats[label] = mat
		impostor_meta[label] = meta
		return true

	# Load per-tier impostor materials for exact shape matching, plus generic
	# species fallbacks. Import files use compress/mode=2 (BC7/BPTC) so all
	# 56 sets fit in ~672 MB VRAM (vs 2.6 GB when uncompressed).
	for model_name in ARCHETYPE_MODEL.values():
		for tier in ["s", "m", "l"]:
			_load_impostor_mat.call("%s_%s" % [model_name, tier])
		_load_impostor_mat.call(model_name)  # generic fallback

	# Impostors fade in 230-250m, complementing LOD1's fade-out band.
	var imp_fade_in := Vector2(230.0, 250.0)
	if _tier_isolate == "impostor":
		imp_fade_in = Vector2(0.0, 0.0)   # pure tier at any distance
	for mat_key in impostor_mats:
		impostor_mats[mat_key].set_shader_parameter("lod_fade_in", imp_fade_in)

	if impostor_mats.is_empty():
		print("Trees Impostor: no impostor atlases found — skipping")
		return
	print("Trees Impostor: loaded %d impostor materials (per-tier + fallbacks)" % impostor_mats.size())

	var billboard_mesh := _create_billboard_quad_mesh()  # 2 tris

	# Bucket into spatial chunks × species (each species has its own material)
	const CHUNK := 80.0
	var chunks: Dictionary = {}  # "cx|cz|model" -> {"xf": [], "cd": [], "model": ""}

	for sd in _shell_data:
		if sd.dead:
			continue
		var model_name: String = ARCHETYPE_MODEL.get(sd.archetype, "deciduous")
		var tier: String = sd.get("tier", "m")

		# Select impostor material: prefer per-tier, fall back to generic species
		var mat_key := "%s_%s" % [model_name, tier]
		if not impostor_mats.has(mat_key):
			mat_key = model_name
		if not impostor_mats.has(mat_key):
			mat_key = "deciduous_%s" % tier
		if not impostor_mats.has(mat_key):
			mat_key = "deciduous"
		if not impostor_mats.has(mat_key):
			continue

		var cx: int = int(floorf(sd.x / CHUNK))
		var cz: int = int(floorf(sd.z / CHUNK))
		var ck := "%d|%d|%s" % [cx, cz, mat_key]
		if not chunks.has(ck):
			chunks[ck] = {"xf": [], "cd": [], "model": mat_key}

		# Per-tree Y rotation for atlas view variety across instances
		var y_rot := fmod(abs(sin(sd.x * 127.1 + sd.z * 311.7) * 43758.5453), 1.0) * TAU
		var cd := Color(float(sd.sp) / 13.0, sd.timing, sd.ev, sd.jitter)

		# Billboard instance: uniform scale at trunk base. The shader's
		# position_offset shifts the billboard up to the canopy center.
		# Use the same scale factor as LOD0 (desired_h / model_height).
		var tier_key := model_name + "_" + tier
		var model_height: float = _species_heights.get(tier_key,
			_species_heights.get(model_name + "_m",
			_species_heights.get(model_name + "_l",
			_species_heights.get(model_name + "_s", 5.0))))
		var sy: float = sd.h / maxf(model_height, 0.1)
		var sx: float = sy * (1.50 if sd.archetype == "cathedral_elm" else 1.0)
		var basis := Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(sx, sy, sx))
		var tf := Transform3D(basis, Vector3(sd.x, sd.y, sd.z))
		chunks[ck].xf.append(tf)
		chunks[ck].cd.append(cd)

	var impostor_count := 0
	for ck in chunks:
		var chunk_data: Dictionary = chunks[ck]
		var xf_list: Array = chunk_data.xf
		var cd_list: Array = chunk_data.cd
		var model_name: String = chunk_data.model
		if xf_list.is_empty():
			continue

		var cx_sum := 0.0; var cy_sum := 0.0; var cz_sum := 0.0
		for tf: Transform3D in xf_list:
			cx_sum += tf.origin.x; cy_sum += tf.origin.y; cz_sum += tf.origin.z
		var n := float(xf_list.size())
		var origin := Vector3(cx_sum / n, cy_sum / n, cz_sum / n)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = billboard_mesh
		mm.instance_count = xf_list.size()
		for i in xf_list.size():
			var local_tf := Transform3D(xf_list[i].basis, xf_list[i].origin - origin)
			mm.set_instance_transform(i, local_tf)
			mm.set_instance_custom_data(i, cd_list[i])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = impostor_mats[model_name]
		mmi.position = origin
		mmi.name = "TreeImp_%s_%s" % [model_name, ck.get_slice("|", 0) + "_" + ck.get_slice("|", 1)]
		# Impostors take over where LOD1 mesh fades out (~230m). Chunk
		# visibility begins at 190m (= 230 - half CHUNK) so chunks whose
		# origin is just inside fade-in band still render. Shader-side
		# dither (lod_fade_in) handles the 230-250m crossfade.
		mmi.visibility_range_begin = 0.0 if _tier_isolate == "impostor" else 190.0
		mmi.visibility_range_end = 2500.0
		mmi.visibility_range_begin_margin = 0.0
		mmi.visibility_range_end_margin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# Billboard quad mesh is unit-sized so the MultiMesh AABB is only ~2-5m
		# tall, but the shader shifts each rendered billboard to canopy height
		# (10-25m above ground via position_offset + pivot_to_cam_dir * aabb_max).
		# Without margin, distant chunks frustum-cull when the camera looks at
		# the horizon — AABB is below the view, even though the fragments above
		# it. 40m covers the tallest canopy lift + atmospheric headroom.
		mmi.extra_cull_margin = 40.0
		_loader.add_child(mmi)
		impostor_count += xf_list.size()
		imp_instances += xf_list.size()
		imp_chunks += 1

	print("Trees Impostor: %d billboard impostors (190-2500m) in %d chunks (%d species)" % [
		impostor_count, chunks.size(), impostor_mats.size()])
