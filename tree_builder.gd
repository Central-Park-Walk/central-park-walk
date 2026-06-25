# tree_builder.gd
# Tree geometry: GLB-based trees with spatially chunked MultiMesh instances
# Extracted from park_loader.gd — all shared utilities accessed via _loader reference.

var _loader  # Reference to park_loader for shared utilities
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
var _species_meshes: Dictionary = {}  # archetype_name -> Array[Mesh]
var _species_heights: Dictionary = {} # archetype_name -> float (RAW mesh-unit height; divisor for placement scale)
var _species_real_h: Dictionary = {} # species_tier -> float (mean PLACED real-world height, metres) for screen-size LOD
# Per-tree LOD handoff distances (metres) for the F1 distance overlay, so its
# colour reflects the ACTUAL tier the engine renders (not a fixed distance band).
# Each entry: {"pos": Vector3, "lod1_end": float, "mesh_end": float}. dist < lod1_end
# → lod0 (green); < mesh_end → lod1 (yellow); else culled (red). Saplings have no
# lod1 so lod1_end == mesh_end (green straight to red). These are the SAME scaled
# bands the lod_fade shaders dither at (_lod1_end/_mesh_fade_end × _lod_scale).
var tree_lod_bands: Array = []

# MMI / instance counts per LOD tier — read by HUD perf overlay
var lod0_instances: int = 0
var lod0_chunks: int = 0
var lod1_instances: int = 0
var lod1_chunks: int = 0
# Far LOD tier: runtime-lit octahedral impostors (rebuilt 2026-06-23, Godot-community
# /AAA SOP; scripts/bake_impostors.gd + shaders/tree_impostor.gdshader). Billboard
# quad per species-tier, dithers in where _lod1 dithers out, out to IMPOSTOR_FAR.
var impostor_instances: int = 0
var impostor_chunks: int = 0
# sp_tier -> billboard QuadMesh carrying the tree_impostor material (atlases + octa
# params from textures/impostors/<species>_manifest.json). Empty until bakes exist.
var _impostor_meshes: Dictionary = {}
# Far cull for the impostor tier (m). Trees only need an impostor from the mesh
# handoff (~200m) out to here; beyond this they're sub-pixel / fog-veiled and are
# culled entirely (user 2026-06-23). Was 2500m — far past any useful range, which
# kept ~2737 impostor MMIs drawing across the whole 2.5km park every frame and
# regressed fps. 500m culls to the chunks that actually matter (the dominant fix
# for the impostor draw-call regression; see [[project_impostor_system_rebuilt]]).
const IMPOSTOR_FAR: float = 500.0

# Shadow proxies (docs/trees.md §3): visible trees cast nothing; a ~220-tri
# trunk cylinder + leaf-vertex-fit crown lathe per species-size-variant casts
# instead (SHADOWS_ONLY, GI off), with phenology-driven dapple coverage.
var _shadow_proxy: bool = false
var _proxy_solid: bool = false
var _proxy_mesh_cache: Dictionary = {}  # mesh_key -> ArrayMesh
var proxy_instances: int = 0
# --tier-isolate=mesh|lod0|lod1 (diagnostic): render ONLY that tree tier with
# the crossfade dither disabled, so captures can compare pure tiers at the same
# distance. mesh = both mesh tiers together; lod0 = base mesh; lod1 = the mid
# mesh, each across the whole mesh range (for the handoff comparison).
var _tier_isolate: String = ""
# --bake-impostors[=species]: offline octahedral atlas bake (scripts/bake_impostors.gd).
# Non-empty => after materialising _species_meshes, bake that species' tiers and quit.
var _bake_impostors_species: String = ""
# --tree-mesh-range=N: lod1 (mid mesh) fade-out END distance (metres) — the far
# edge of the mesh LOD chain. The dither band (LOD_FADE_RATIO of this = 20m at
# 200m) and mesh chunk visibility (+40m = half chunk) derive from it. Shadow
# proxies are NOT tied to it — they keep casting to 290m regardless.
#
# Default 200 since 2026-06-20 (was 400): in CP, trees are not seen unobstructed
# beyond ~200m (dense, hilly sightlines — user observation), and beyond ~300m a
# leaf-card canopy goes sub-pixel and mip-diluted alpha discards the cards, so no
# geometry tier holds coverage there regardless of card count. Running meshes
# farther is wasted; the shorter range is also a perf win.
var _mesh_fade_end: float = 200.0
# --tree-lod1-range=N: lod0 (full base) → lod1 (mid mesh) handoff (fade END,
# metres). Dither band = LOD_FADE_RATIO of the handoff (8m at 80m); near chunk
# visibility extends +40m past it.
# Default 80 since 2026-06-21 (was 100, was 60): lod0's full-detail base model
# is only needed at close range (<80m); lod1 then carries 80–200m. The 80/200
# split is the user's spec; the dither band is the Godot HLOD convention.
var _lod1_end: float = 80.0
# SCREEN-SIZE LOD (AAA / Godot community best practice, user 2026-06-22): a tree's
# on-screen pixel height is (world_height / distance) × const, so to make EVERY
# tree switch tiers at the same APPARENT size — not the same world distance — the
# handoff distance must scale linearly with the model's height. _lod1_end (80m)
# and _mesh_fade_end (200m) are the REFERENCE distances for a REF_TREE_HEIGHT-tall
# canopy tree; a 30m london_plane_l then holds mesh ~36% farther and a 10m sapling
# switches ~55% sooner, all at the same ~77px switch size. This also SUBSUMES the
# old hardcoded _sapling_mesh_end=90 (≈ 200 × 10/22): saplings are short, so the
# unified formula hands them off early on its own — no special case. Sources:
# PulseGeek "prefer screen-size thresholds for LOD switches"; Godot HLOD tutorial.
const REF_TREE_HEIGHT: float = 22.0  # m — height the 80/200m defaults were tuned for
# Min/max clamp keeps extreme variants sane (tiny shrubs don't pop at 30m; giant
# elms don't carry full mesh absurdly far).
const LOD_SCALE_RANGE := Vector2(0.40, 1.60)
# Crossfade dither band as a fraction of each tier's handoff distance. Godot's
# official HLOD tutorial sizes End Margin at 10% of the visibility range
# (End=10 → Margin=1); SpeedTree/AAA guidance is to keep the dither band SHORT
# because overdraw cost scales with dithered area. 10% satisfies both → 8m at
# the 80m handoff, 20m at the 200m handoff. Computed inline at each fade site so
# CLI range overrides (--tree-lod1-range / --tree-mesh-range) track automatically.
const LOD_FADE_RATIO: float = 0.10
# --simple-leaf / --simple-bark (diagnostic): swap tree surface shaders for
# minimal ones with identical render modes, splitting the camera-raster cost
# into shader complexity vs raster structure (overdraw, quad efficiency).
var _simple_leaf: bool = false
var _simple_bark: bool = false
# --leaf-no-prepass (diagnostic): clone tree_leaf without depth_prepass_alpha.
# The prepass rasterizes all canopy geometry twice (alpha-tested depth, then
# shade); whether it pays for itself depends on depth complexity — measure.
var _leaf_no_prepass: bool = false
# --all-london-plane (TEMP diagnostic): force EVERY tree to the london_plane
# species so the whole park renders with just the london plane lod0/lod1
# variants. Keeps each tree's real height (so s/m/l tiers still vary) and
# suppresses the cathedral-elm and dead-snag reassignments.
var _all_london_plane: bool = false
# TEST ROUND 2026-06-24 (user): when --all-london-plane forces the whole park to
# london_plane, also pin every tree — and the impostor bake — to a SINGLE variant
# per size tier instead of the per-tree hash spread, so the assessment walk sees
# exactly one chosen specimen everywhere. v3 = the strongest specimen in each tier
# (_s/_m/_l) from the variant-grid review. -1 disables the pin (full 7-variant
# spread). The bake at _run_impostor_bake sources the SAME index so lod0/_lod1/
# impostor are all the one variant.
const LP_SINGLE_VARIANT := 3
var _noprepass_shader: Shader = null

# Desired height ranges per species archetype (metres)
# [min, max] — census DBH drives interpolation within range
# DBH fallback height ranges (metres). Minimums raised because woodland-fill
# trees represent established 150-year-old Central Park canopy, not saplings.
# "cherry" includes black cherry (Prunus serotina, 25m+) not just ornamentals.
# Class-level so eval_plot_builder.gd can size its specimen rows from it.
const HEIGHT_RANGES := {
	"oak":           [15.0, 30.0],   # red/white oak — massive when mature
	"maple":         [14.0, 26.0],   # sugar/Norway maple
	"elm":           [16.0, 32.0],   # American Elm — tall vase shape
	"conifer":       [14.0, 30.0],
	"deciduous":     [14.0, 28.0],   # generic canopy tree
	"birch":         [10.0, 22.0],   # gray/river birch
	"honeylocust":   [14.0, 25.0],   # open, airy crown
	"callery_pear":  [8.0, 18.0],    # medium street tree
	"ginkgo":        [10.0, 22.0],   # slow-growing
	"london_plane":  [9.0, 32.0],    # tall broad crown; floor lowered for young street/lawn planes (_s sapling)
	"linden":        [14.0, 24.0],   # dense symmetrical crown
	"cherry":        [10.0, 22.0],   # includes black cherry (P. serotina 25m+)
	"zelkova":       [14.0, 24.0],   # upright vase shape
	"dead":          [8.0, 20.0],    # shorter (broken top)
	"willow":        [10.0, 22.0],   # weeping willow — wide, medium height
	"magnolia":      [6.0, 16.0],    # sweetbay magnolia can reach 20m
	"cathedral_elm": [22.0, 34.0],   # mature Literary Walk elms — tall, wide vase
}

func _init(loader) -> void:
	_loader = loader
	# Default ON since 2026-06-10 (docs/trees.md §3 DoD passed: shtri, SDFGI
	# A/B, crown fit, winter shed, perf gate). Opt-out is a diagnostic.
	_shadow_proxy = not ("--no-tree-shadow-proxy" in OS.get_cmdline_user_args())
	if not _shadow_proxy:
		print("TreeBuilder: shadow proxies OFF (diagnostic) — visible trees cast per-leaf")
	# Diagnostic: solid crowns (no dapple discard material) to isolate the
	# alpha-tested shadow-pass cost from the proxy geometry cost.
	_proxy_solid = "--proxy-solid" in OS.get_cmdline_user_args()
	if _proxy_solid:
		print("TreeBuilder: proxy crowns SOLID (diagnostic) — no dapple discard")
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--tier-isolate="):
			_tier_isolate = arg.substr("--tier-isolate=".length())
			print("TreeBuilder: TIER ISOLATE '%s' — single tier, no crossfade (diagnostic)" % _tier_isolate)
		elif arg.begins_with("--tree-mesh-range="):
			_mesh_fade_end = clampf(float(arg.substr("--tree-mesh-range=".length())), 60.0, 1000.0)
			print("TreeBuilder: lod1 mesh fade-out end = %.0fm (default 200, scaled per tree height)" % _mesh_fade_end)
		elif arg.begins_with("--tree-lod1-range="):
			_lod1_end = clampf(float(arg.substr("--tree-lod1-range=".length())), 20.0, 250.0)
			print("TreeBuilder: near mesh (_lod1) reference fade end = %.0fm (default 80, scaled per tree height) — _lod1 takes over there" % _lod1_end)
		elif arg == "--simple-leaf":
			_simple_leaf = true
			print("TreeBuilder: SIMPLE LEAF shader (diagnostic) — isolates leaf shader complexity cost")
		elif arg == "--simple-bark":
			_simple_bark = true
			print("TreeBuilder: SIMPLE BARK shader (diagnostic) — isolates bark shader complexity cost")
		elif arg == "--leaf-no-prepass":
			_leaf_no_prepass = true
			print("TreeBuilder: LEAF NO-PREPASS (diagnostic) — depth_prepass_alpha stripped from tree_leaf")
		elif arg == "--all-london-plane":
			_all_london_plane = true
			print("TreeBuilder: ALL-LONDON-PLANE (TEMP) — every tree forced to london_plane")
		elif arg.begins_with("--bake-impostors"):
			# --bake-impostors  or  --bake-impostors=<species>  (default london_plane).
			# Bakes octahedral atlases for that species' size tiers, then quits — runs
			# right after the meshes are materialised, before placement.
			var eq := arg.find("=")
			_bake_impostors_species = arg.substr(eq + 1) if eq >= 0 else "london_plane"
			print("TreeBuilder: IMPOSTOR BAKE mode — species '%s', will quit after baking" % _bake_impostors_species)

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
	"london_plane":  [13.0, 25.0],  # _s sapling added — ~1/3 of census is young (<12" DBH, 2026-06-19)
	"linden":        [14.0, 22.0],
	"willow":        [14.0, 999.0], # no _l tier (0 in census); only _s and _m
	"magnolia":      [0.0, 0.0],    # only _s tier (41 in census, all small)
	"conifer":       [0.0, 18.0],   # no _s tier (0 in census); shares pine models
	"zelkova":       [14.0, 22.0],  # shares elm models
	"dead":          [0.0, 0.0],    # no tiers
}
const TIERS := ["s", "m", "l"]

func _lod_scale(species_tier: String) -> float:
	## Screen-size LOD multiplier: handoff distances scale with the tree's REAL-WORLD
	## height so every tree switches tiers at the same APPARENT on-screen size (AAA /
	## Godot best practice). Strip any "_lod1" suffix — the mid mesh shares its base
	## height. Returns 1.0 for a REF_TREE_HEIGHT-tall canopy tree, so the 80/200m
	## defaults are unchanged for a typical tree and only the size-relative spread is
	## added. MUST use the placed metres height (_species_real_h), NOT _species_heights
	## — the latter is RAW mesh units (~5) and dividing it by 22m clamped every tree to
	## the 0.40 floor, collapsing the far LOD handoff to ~80m (2026-06-22 LOD bug).
	var base_key: String = species_tier.trim_suffix("_lod1")
	var h: float = _species_real_h.get(base_key, REF_TREE_HEIGHT)
	return clampf(h / REF_TREE_HEIGHT, LOD_SCALE_RANGE.x, LOD_SCALE_RANGE.y)

func _get_tier(species: String, desired_h: float) -> String:
	## Return size tier suffix based on species and desired height.
	# NOTE (2026-06-21): the force-_s assessment hack was REVERTED — it made every
	# m/l-sized london plane render the heavy STRUCTURAL-leaf _s model (3D sprigs),
	# which tanked fps to ~7-8 (user diagnosis). Real m/l use cheap cluster CARDS.
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
	var cfg := ConfigFile.new()
	if cfg.load(meta_path) != OK:
		return {}
	# Invalidate when the source GLB's mtime differs from the one stamped into the
	# cache at build time. Using != on the STAMPED mtime (not file-mtime > on the
	# .cfg, which races — see _save_tree_cache) means any GLB regen forces a
	# re-parse, even if the stale cache file is newer than the GLB. A cache with
	# no stamp (pre-2026-06-21) is treated as stale so it rebuilds once.
	var glb_path := ProjectSettings.globalize_path("res://models/trees/%s.glb" % model_name)
	if FileAccess.file_exists(glb_path):
		var glb_time := FileAccess.get_modified_time(glb_path)
		var stamped: int = cfg.get_value("model", "glb_mtime", -1)
		if stamped != glb_time:
			return {}  # source changed (or unstamped) — force re-parse
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
	# Stamp the SOURCE GLB's mtime so the cache invalidates on != (not file-mtime
	# >, which races: a render that rebuilds the cache writes it NEWER than the
	# GLB, after which glb_time > cfg_time is forever false and a stale mesh is
	# served even after the GLB is regenerated. Comparing the stamped source mtime
	# is robust to that. (2026-06-21: cost a session of "identical" eval shots.)
	var src_glb := ProjectSettings.globalize_path("res://models/trees/%s.glb" % model_name)
	if FileAccess.file_exists(src_glb):
		cfg.set_value("model", "glb_mtime", FileAccess.get_modified_time(src_glb))
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
	# Plus _lod1 (card-pruned + bark-decimated) variants of each for the
	# mesh LOD chain: base near mesh → _lod1 mid mesh. The near tier renders
	# the FULL base model — a card-pruned _lod1 tier put a visibly thinned
	# crown at the closest viewing distances (Jun 11 walk-around defect #1).
	for base_name in _base_model_names:
		var tier_list: Array
		if base_name == "dead":
			tier_list = [""]
		else:
			tier_list = ["_s", "_m", "_l"]
		var full_list: Array = []
		for ts in tier_list:
			full_list.append(ts)
			# lod1 mid mesh for m/l only; the _s sapling is lod0 only
			# (no lod1) per the LOD policy (user 2026-06-19).
			if ts != "" and ts != "_s":
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
			tier_suffixes = ["_s", "_m", "_l",
				"_m_lod1", "_l_lod1"]  # _s: lod0 only (no lod1)
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
							# Prefer DDS with coverage-preserving mipmaps over GLB-embedded texture.
							# Per-tier DDS first (e.g. london_plane_s_leaf.dds = opaque single-leaf
							# for the true-3D distributed sapling) then the species cluster DDS
							# (e.g. london_plane_leaf.dds = alpha card mass for m/l). This is the
							# hybrid: real leaves near/small, card mass on big crowns (2026-06-20).
							var dds_path := "res://textures/leaves/%s_leaf.dds" % model_key
							if not ResourceLoader.exists(dds_path):
								dds_path = "res://textures/leaves/%s_leaf.dds" % model_base
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

	# Offline impostor bake: meshes are now fully materialised (exact in-game
	# leaf/bark ShaderMaterials). Bake the requested species' tiers and quit
	# before any placement — no terrain or full park build needed.
	if _bake_impostors_species != "":
		await _run_impostor_bake()
		_loader.get_tree().quit()
		return

	# NOTE: the impostor tier assets are built LATER (after _species_real_h is
	# populated below), NOT here. Their lod_fade_in band is scaled by _lod_scale,
	# which reads _species_real_h — empty at this point, so building here gave every
	# tier the default scale 1.0 and faded impostors in at the unscaled ~200m while
	# the mesh tiers faded OUT at the per-tier scaled distance. That desync opened a
	# LOD hole (mesh gone, impostor not yet in), widest on short tiers. See below.

	if _species_meshes.is_empty():
		print("WARNING: no tree GLB models loaded, falling back skipped")
		return

	# Foliage zone data for deciduous sub-species assignment

	# Collect transforms + season data per species-variant for MultiMesh batching
	# Key: "species_variantIdx" -> Array[Transform3D]
	var xf_by_key: Dictionary = {}
	var cd_by_key: Dictionary = {}  # parallel Color arrays for custom_data (season info)
	var all_trunk_xf: Array = []  # for collision
	# Screen-size LOD: accumulate placed real-world height (metres) per species_tier
	# so _lod_scale can size handoffs by apparent on-screen size. {tier: [sum, count]}.
	var real_h_accum: Dictionary = {}
	_species_real_h.clear()
	tree_lod_bands.clear()
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

		# TEMP --all-london-plane: override every tree to london_plane, keeping its
		# real height so the s/m/l tiers still vary. Done after the cathedral-elm
		# block and before dead-snag so nothing else reassigns it.
		if _all_london_plane:
			species = "london_plane"

		# Standing dead trees (snags): ~3% of non-conifer trees become dead snags
		# (never eval-plot specimens — a labelled oak must stay an oak)
		var is_eval: bool = typeof(tree_entry) == TYPE_DICTIONARY and tree_entry.get("eval", false)
		if not _all_london_plane and species != "conifer" and species != "dead" and not is_eval:
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
			desired_h = clampf(desired_h, 3.0, float(HEIGHT_RANGES.get(species, [10.0, 35.0])[1]) * 1.2)
		else:
			var h_range: Array = HEIGHT_RANGES.get(species, [10.0, 22.0])
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

		var variant_idx: int = int(abs(hash("%s|%.1f|%.1f" % [species_tier, tx, tz]))) % n_variants  # PER-TREE variant (local diversity, user 2026-06-22; was per-80m-cell which tiled). Position-derived → identical across lod0/lod1 (no handoff pop). COST: ~3x tree MMIs (mixed variants per chunk) — frame is fragment-bound (trees.md §4a) so likely cheap, but PERF-GATE before commit.
		# TEST ROUND: pin to ONE london_plane variant when --all-london-plane (see
		# LP_SINGLE_VARIANT). vi flows into the bucket key, so lod0 AND _lod1 both pick
		# this index (near_mesh/mid_mesh share vi at chunk-build time).
		if _all_london_plane and species == "london_plane" and LP_SINGLE_VARIANT >= 0:
			variant_idx = clampi(LP_SINGLE_VARIANT, 0, n_variants - 1)
		# Eval-only: a specimen may force a specific variant (eval_plot_builder
		# VARIANT_ROW — show every lod0 variant side by side). No effect on the park.
		if is_eval and typeof(tree_entry) == TYPE_DICTIONARY and tree_entry.has("variant"):
			variant_idx = clampi(int(tree_entry["variant"]), 0, n_variants - 1)

		# Scale factor: desired_height / mesh_height_in_raw_units
		var mesh_h: float = _species_heights[species_tier]
		if mesh_h < 0.001:
			mesh_h = 0.06
		var sy := desired_h / mesh_h

		# Screen-size LOD: track this tier's placed real-world height (metres). The
		# mean feeds _lod_scale so handoffs scale with apparent on-screen size.
		var acc: Array = real_h_accum.get(species_tier, [0.0, 0])
		acc[0] += desired_h
		acc[1] += 1
		real_h_accum[species_tier] = acc

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
		# --- §5b per-instance coherence: break same-species clone tiling ---
		# Derived from world XZ (NOT the sequential rng) so the basis is identical
		# across lod0/lod1 tiers; a leaning, slightly stretched tree must
		# not pop or change shape at a tier handoff.
		var h1 := fmod(abs(sin(tx * 12.9898 + tz * 78.233) * 43758.5453), 1.0)
		var h2 := fmod(abs(sin(tx * 39.346 + tz * 11.135) * 24634.6345), 1.0)
		var h3 := fmod(abs(sin(tx * 73.156 + tz * 52.235) * 13793.4537), 1.0)
		# Plus/minus 10% XZ-scale jitter -> per-tree slenderness. Cathedral elms
		# keep their exact forced width (allee convergence depends on it, §5b).
		var sj := 1.0
		if species != "cathedral_elm":
			sj = 0.90 + h1 * 0.20
		# Small natural lean (1-5 deg) at random azimuth; no real tree is vertical.
		var lean_angle := deg_to_rad(1.0 + h2 * 4.0)
		var lean_dir := h3 * TAU
		var lean_axis := Vector3(cos(lean_dir), 0.0, sin(lean_dir))

		# Build transform: lean * Y-rotation * non-uniform scale. GLB base sits at
		# local origin, so the lean pivots at the trunk base.
		var basis := Basis(lean_axis, lean_angle) \
			* Basis(Vector3.UP, y_rot) * Basis().scaled(Vector3(sx * sj, sy, sx * sj))
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

		# Mesh tiers (base/_lod1) are spawned in the main chunk pathway
		# below (mesh lookup at chunk-build time), so there's no separate
		# per-tier accumulation here.

		# Canopy data for dappled shade map.
		# LiDAR crown_a measures only the dense inner canopy (often 10-30m²
		# for a 20m tree), producing absurdly small crown radii (1-3m).
		# Use proportional radius from desired_h instead — matches visual spread.
		var crown_r: float = desired_h * (0.25 if species == "conifer" else 0.35)
		canopy_data.append({"x": tx, "z": tz, "r": crown_r, "ev": species == "conifer"})

		# F1 distance-overlay tier bands — finalised after _species_real_h below
		# (needs the per-tier mean height). Store the inputs now, one per placed tree.
		tree_lod_bands.append({"pos": Vector3(tx, ty, tz), "_tier": species_tier,
			"_lod1": _species_meshes.has(species_tier + "_lod1")})

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

	# Finalise screen-size-LOD reference heights: mean placed metres per species_tier.
	# Read by _lod_scale at every handoff/fade site below.
	for tier_key in real_h_accum:
		var racc: Array = real_h_accum[tier_key]
		if racc[1] > 0:
			_species_real_h[tier_key] = racc[0] / float(racc[1])

	# Build the far impostor tier assets HERE — after _species_real_h exists — so each
	# impostor's lod_fade_in band is scaled by the SAME per-tier _lod_scale the mesh
	# fade-out bands use below. Building this before population (the old bug) gave every
	# tier scale 1.0, faded impostors in at ~200m regardless of size, and opened a LOD
	# hole vs the height-scaled mesh fade-out. Runs before _spawn_impostor_chunks.
	_build_impostor_assets()

	# Resolve each tree's LOD bands now that per-tier mean heights exist. Uses the
	# exact scaled handoffs the lod_fade shaders dither at, so the F1 overlay colour
	# matches the rendered tier. No lod1 (saplings/dead) → lod1_end == mesh_end.
	for band in tree_lod_bands:
		var lsc: float = _lod_scale(band["_tier"])
		var me: float = _mesh_fade_end * lsc
		band["mesh_end"] = me
		band["lod1_end"] = (_lod1_end * lsc) if band["_lod1"] else me
		band.erase("_tier")
		band.erase("_lod1")

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
		# Mesh LOD chain: FULL base mesh (lod0) near to _lod1_end, then _lod1 mid
		# mesh (bark-decimated, card-pruned) to _mesh_fade_end. Falls back: no
		# _lod1 (saplings, dead snags) → lod0 near mesh covers the whole range.
		var lod1_key: String = sp_name + "_lod1"
		var near_vars: Array = _species_meshes[sp_name]
		var near_mesh: Mesh = near_vars[vi % near_vars.size()]
		var mid_mesh: Mesh = null
		if _species_meshes.has(lod1_key):
			var mid_vars: Array = _species_meshes[lod1_key]
			mid_mesh = mid_vars[vi % mid_vars.size()]
		var cx_sum := 0.0
		var cy_sum := 0.0
		var cz_sum := 0.0
		for tf: Transform3D in xf_list:
			cx_sum += tf.origin.x
			cy_sum += tf.origin.y
			cz_sum += tf.origin.z
		var n := float(xf_list.size())
		var chunk_origin := Vector3(cx_sum / n, cy_sum / n, cz_sum / n)
		# Chunk visibility must extend past each tier's fade end by this
		# chunk's actual instance spread, or members far from the centroid
		# drop out before their dither band completes (the old fixed +40m
		# margin under-covered skewed chunks). Exact per chunk: max member
		# distance from centroid + pad. Beyond-band members cost vertex work
		# only — their fragments are dither-discarded.
		var chunk_r := 0.0
		for tf: Transform3D in xf_list:
			chunk_r = maxf(chunk_r, (tf.origin - chunk_origin).length())
		# Screen-size LOD: handoff distances scale with this species_tier's height
		# (a 30m _l holds mesh farther; a ~10m _s switches sooner — same on-screen
		# size). The scale also subsumes the old sapling special-case: short _s
		# trees get a near far-cull (≈90m) on their own, no separate constant.
		var lscale: float = _lod_scale(sp_name)
		var eff_mesh_end: float = _mesh_fade_end * lscale
		var mesh_vis_end: float = eff_mesh_end + chunk_r + 5.0
		if _tier_isolate != "":
			# Isolate captures render a tier pure with the dither disabled, so
			# the tight per-chunk bound (correct in normal play, where trees
			# beyond the fade end are fully discarded) would drop sparse far
			# chunks out of the comparison band — keep a generous fixed
			# envelope for diagnostics instead.
			mesh_vis_end = _mesh_fade_end + 60.0
		# TEMP DIAG (DEBUG_TREE_CHUNK=cx,cz): dump the LOD geometry for one chunk so the
		# mesh-leaves-early-vs-impostor question can be answered with numbers, not pixels.
		if OS.has_environment("DEBUG_TREE_CHUNK"):
			var dbg: PackedStringArray = OS.get_environment("DEBUG_TREE_CHUNK").split(",")
			if dbg.size() == 2 and info["cx"] == int(dbg[0]) and info["cz"] == int(dbg[1]):
				var has_l1 := _species_meshes.has(sp_name + "_lod1")
				print("[DIAG] chunk %d|%d sp=%s vi=%d n=%d lscale=%.3f real_h=%.1f chunk_r=%.1f" % [
					info["cx"], info["cz"], sp_name, vi, xf_list.size(), lscale,
					_species_real_h.get(sp_name, -1.0), chunk_r])
				print("[DIAG]   centroid=(%.1f,%.1f,%.1f) lod1?=%s" % [chunk_origin.x, chunk_origin.y, chunk_origin.z, has_l1])
				print("[DIAG]   lod0 vis_end(near)=%.1f  lod1 mesh_vis_end=%.1f" % [
					(_lod1_end * lscale + chunk_r + 5.0) if has_l1 else mesh_vis_end, mesh_vis_end])
				print("[DIAG]   shader bands: lod0->lod1 [%.1f,%.1f]  mesh_fade_out [%.1f,%.1f]" % [
					_lod1_end*lscale*(1.0-LOD_FADE_RATIO), _lod1_end*lscale,
					_mesh_fade_end*lscale*(1.0-LOD_FADE_RATIO), _mesh_fade_end*lscale])
				print("[DIAG]   impostor MMI begin=%.1f  shader fade_in [%.1f,%.1f]  per-tree origin.y=%.1f" % [
					eff_mesh_end*(1.0-LOD_FADE_RATIO) - chunk_r - 5.0,
					_mesh_fade_end*lscale*(1.0-LOD_FADE_RATIO), _mesh_fade_end*lscale, xf_list[0].origin.y])
		# [mesh, name prefix, visibility end] per mesh tier this chunk spawns
		var tier_specs: Array = []
		match _tier_isolate:
			"lod0":
				tier_specs.append([near_mesh, "Tree", mesh_vis_end])
			"lod1":
				var iso_mesh: Mesh = mid_mesh if mid_mesh != null else near_mesh
				tier_specs.append([iso_mesh, "TreeLod1", mesh_vis_end])
			"impostor":
				pass  # impostor-only isolate: no mesh tiers, just the billboards below
			_:
				var near_end: float = (_lod1_end * lscale + chunk_r + 5.0) if mid_mesh != null else mesh_vis_end
				tier_specs.append([near_mesh, "Tree", near_end])
				if mid_mesh != null:
					tier_specs.append([mid_mesh, "TreeLod1", mesh_vis_end])
		for spec: Array in tier_specs:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true
			mm.mesh = spec[0]
			mm.instance_count = xf_list.size()
			for i in xf_list.size():
				var tf: Transform3D = xf_list[i]
				var local_tf := Transform3D(tf.basis, tf.origin - chunk_origin)
				mm.set_instance_transform(i, local_tf)
				mm.set_instance_custom_data(i, cd_list[i])
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.position = chunk_origin
			mmi.name = "%s_%s" % [spec[1], ckey.replace("|", "_")]
			mmi.visibility_range_begin = 0.0
			mmi.visibility_range_end = spec[2]
			mmi.visibility_range_begin_margin = 0.0
			mmi.visibility_range_end_margin = 0.0
			mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
			if _shadow_proxy:
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			_loader.add_child(mmi)
			if spec[1] == "TreeLod1":
				lod1_instances += xf_list.size()
				lod1_chunks += 1
			else:
				lod0_instances += xf_list.size()
				lod0_chunks += 1
		if _shadow_proxy:
			var pmm := MultiMesh.new()
			pmm.transform_format = MultiMesh.TRANSFORM_3D
			pmm.use_custom_data = true  # phenology packing — proxy shader sheds crown shadow in winter
			var proxy_key := "%s_%d" % [sp_name, vi % near_vars.size()]
			pmm.mesh = _get_shadow_proxy_mesh(proxy_key, sp_name, near_mesh)
			pmm.instance_count = xf_list.size()
			for i in xf_list.size():
				var tf: Transform3D = xf_list[i]
				pmm.set_instance_transform(i, Transform3D(tf.basis, tf.origin - chunk_origin))
				pmm.set_instance_custom_data(i, cd_list[i])
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

	# Canopy occluders disabled: OccluderInstance3D inherits Node3D (not
	# GeometryInstance3D) so visibility_range cannot limit them. Without a
	# distance gate they stay active at all ranges, hiding distant trees
	# behind canopy boxes and making distant woodland look sparse.

	# Both mesh tiers (base near, _lod1 mid) are spawned by the main chunk
	# pathway above from the same buckets, so their per-tree transforms and
	# custom data match exactly and the 60m crossfade is water-tight.

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
	print("Trees mesh tiers: %d near (base) MMIs / %d instances, %d mid (_lod1) MMIs / %d instances" % [
		lod0_chunks, lod0_instances, lod1_chunks, lod1_instances])

	# --- Far LOD tier: runtime-lit octahedral impostors (rebuilt 2026-06-23). For
	# every chunk whose species-tier has a baked atlas, spawn a billboard MMI that
	# dithers in where _lod1 dithers out (shader lod_fade_in), out to IMPOSTOR_FAR. ---
	_spawn_impostor_chunks(lod0_buckets)
	if not _impostor_meshes.is_empty():
		print("Trees impostor tier: %d MMIs / %d instances" % [impostor_chunks, impostor_instances])

	# Per-tier dither fade ranges. Shader dithering replaces Godot's
	# VISIBILITY_RANGE_FADE_SELF (known bug #88854 with alpha_to_coverage).
	# Two mesh tiers:
	#   Base near mesh: full model 0 → _lod1_end, fades out over the LOD_FADE_RATIO
	#                   band (8m at 80m) ending at _lod1_end → _lod1.
	#   _lod1 mid mesh: fades in over that band, out over the LOD_FADE_RATIO band
	#                   (20m at 200m) ending at _mesh_fade_end → culled.
	#   No _lod1 (dead/sapling): near mesh covers the whole range, fades at the far band.
	const NO_FADE := Vector2(0.0, 0.0)
	for sp_key in _species_meshes:
		# Screen-size LOD: fade bands scale with this tier's model height so each
		# tree crossfades at the same on-screen size.
		var s: float = _lod_scale(sp_key)
		var lod1_fade := Vector2(_lod1_end * s * (1.0 - LOD_FADE_RATIO), _lod1_end * s)
		var mesh_fade_out := Vector2(_mesh_fade_end * s * (1.0 - LOD_FADE_RATIO), _mesh_fade_end * s)
		var fade_in := NO_FADE
		var fade_out := NO_FADE
		# tier_brightness: decimated tiers read slightly brighter than the
		# full model (less self-shadowing) — keep a small knock-down on _lod1.
		# The near tier IS the full base model (lod0): 1.0 by construction.
		var tier_brightness: float = 0.95 if "_lod1" in sp_key else 1.0
		if _tier_isolate == "lod0" or _tier_isolate == "lod1":
			pass  # pure single-LOD render for the 60m handoff DoD — no crossfade
		elif "_lod1" in sp_key:
			fade_in = lod1_fade
			if _tier_isolate != "mesh":
				fade_out = mesh_fade_out
		else:
			# Base key = near tier (lod0). With a _lod1 sibling it hands off at
			# _lod1_end; without one (saplings, dead snags) it covers the whole range.
			if _species_meshes.has(sp_key + "_lod1"):
				fade_out = lod1_fade
			elif sp_key.ends_with("_s") and _tier_isolate != "mesh":
				# Sapling: no _lod1, fades out at the height-scaled mesh_fade_out
				# (short tree → ~90m on its own).
				fade_out = mesh_fade_out
			elif _tier_isolate != "mesh":
				fade_out = mesh_fade_out
		for mesh: Mesh in _species_meshes[sp_key]:
			for si in mesh.get_surface_count():
				var mat = mesh.surface_get_material(si)
				if mat is ShaderMaterial:
					# Diagnostic shader swap (--simple-leaf / --simple-bark):
					# same render modes, none of the per-fragment work.
					if (_simple_leaf or _simple_bark) and mat.shader != null:
						var spath: String = mat.shader.resource_path
						if _simple_leaf and "tree_leaf" in spath:
							var simple := ShaderMaterial.new()
							simple.shader = load("res://shaders/diag_leaf_minimal.gdshader")
							simple.set_shader_parameter("albedo_tint", mat.get_shader_parameter("albedo_tint"))
							simple.set_shader_parameter("albedo_tex", mat.get_shader_parameter("albedo_tex"))
							mesh.surface_set_material(si, simple)
							mat = simple
						elif _simple_bark and "tree_bark" in spath:
							var simple := ShaderMaterial.new()
							simple.shader = load("res://shaders/diag_bark_minimal.gdshader")
							simple.set_shader_parameter("bark_color", mat.get_shader_parameter("bark_color"))
							mesh.surface_set_material(si, simple)
							mat = simple
					if _leaf_no_prepass and mat.shader != null \
							and mat.shader != _noprepass_shader \
							and "tree_leaf" in mat.shader.resource_path:
						if _noprepass_shader == null:
							_noprepass_shader = Shader.new()
							_noprepass_shader.code = (mat.shader as Shader).code.replace(
								"render_mode cull_disabled, depth_prepass_alpha;",
								"render_mode cull_disabled;")
						# duplicate keeps all set parameters; only the shader swaps
						var np: ShaderMaterial = mat.duplicate()
						np.shader = _noprepass_shader
						mesh.surface_set_material(si, np)
						mat = np
					mat.set_shader_parameter("lod_fade_out", fade_out)
					mat.set_shader_parameter("lod_fade_in", fade_in)
					mat.set_shader_parameter("tier_brightness", tier_brightness)


# Crown lathe fit (docs/trees.md §3/§5): rings × segments of the silhouette
# profile measured from the variant's leaf vertices. Per-ring elliptical radii
# at a high percentile so one stray branch doesn't inflate the shadow, with a
# small pad because shadow over-coverage is benign (dapple punches holes) but
# under-coverage leaks light through the canopy.
const PROXY_RINGS := 12
const PROXY_SEGS := 8
const PROXY_QUANTILE := 0.96
const PROXY_PAD := 1.05

func _get_shadow_proxy_mesh(mesh_key: String, sp_name: String, src: Mesh) -> ArrayMesh:
	## Whole-tree shadow caster (docs/trees.md §3): trunk cylinder + crown
	## lathe fit per height-slice to the variant's leaf geometry, in the same
	## model space so instance transforms are shared with the visible MMI.
	## ~220 tris vs 10k+ foliage. Vase/columnar/weeping crowns fit by data,
	## not by archetype guess; leafless meshes (dead snags) get trunk only.
	if _proxy_mesh_cache.has(mesh_key):
		return _proxy_mesh_cache[mesh_key]
	var ab: AABB = src.get_aabb()
	var h: float = ab.size.y
	var base_y: float = ab.position.y
	var cx: float = ab.position.x + ab.size.x * 0.5
	var cz: float = ab.position.z + ab.size.z * 0.5
	# Leaf-surface vertices drive the crown fit (bark shader surfaces are
	# trunk/branches). Dead snags have no leaf surfaces → trunk-only proxy.
	var leaf_pts := PackedVector3Array()
	for si in src.get_surface_count():
		var smat: Material = src.surface_get_material(si)
		if smat is ShaderMaterial and (smat as ShaderMaterial).shader \
				and "tree_bark" in (smat as ShaderMaterial).shader.resource_path:
			continue
		leaf_pts.append_array(src.surface_get_arrays(si)[Mesh.ARRAY_VERTEX])
	var crown_base: float = base_y + h * 0.35
	if leaf_pts.size() >= 48:
		var lo := INF
		for p in leaf_pts:
			lo = minf(lo, p.y)
		crown_base = lo
	var am := ArrayMesh.new()
	# Trunk
	var trunk := CylinderMesh.new()
	trunk.radial_segments = 6
	trunk.rings = 1
	trunk.cap_top = false
	trunk.cap_bottom = false
	trunk.top_radius = maxf(h * 0.012, 0.10)
	trunk.bottom_radius = maxf(h * 0.018, 0.14)
	trunk.height = maxf(crown_base - base_y, h * 0.1) + (base_y + h - crown_base) * 0.2
	_append_offset_surface(am, trunk, Vector3(cx, base_y + trunk.height * 0.5, cz))
	if leaf_pts.size() >= 48 and _append_crown_lathe(am, leaf_pts):
		# Dapple: world-space noise discard on the crown so the shadow map
		# gets holes PCF blurs into mottled canopy light, modulated by the
		# same per-instance phenology as the visible leaves (winter = bare).
		# Conifers keep a denser crown (real conifer shade is near-solid).
		if not _proxy_solid:
			var crown_mat := ShaderMaterial.new()
			crown_mat.shader = _loader._get_shader("tree_shadow_proxy",
				"res://shaders/tree_shadow_proxy.gdshader")
			crown_mat.set_shader_parameter("coverage",
				0.80 if sp_name.begins_with("conifer") else 0.62)
			am.surface_set_material(1, crown_mat)
	_proxy_mesh_cache[mesh_key] = am
	return am


func _append_crown_lathe(am: ArrayMesh, pts: PackedVector3Array) -> bool:
	## Closed lathe of the crown silhouette: PROXY_RINGS height slices, each an
	## ellipse at the slice's vertex centroid with |dx| / |dz| radii at
	## PROXY_QUANTILE, capped by apex fans at the crown's Y extents.
	## Returns false (no surface added) if every slice is too sparse to fit.
	var y_min := INF
	var y_max := -INF
	for p in pts:
		y_min = minf(y_min, p.y)
		y_max = maxf(y_max, p.y)
	var span := maxf(y_max - y_min, 0.01)
	# Bucket vertices into height slices
	var bins: Array = []
	for i in PROXY_RINGS:
		bins.append({"x": PackedFloat32Array(), "z": PackedFloat32Array()})
	for p in pts:
		var bi := clampi(int((p.y - y_min) / span * PROXY_RINGS), 0, PROXY_RINGS - 1)
		bins[bi]["x"].append(p.x)
		bins[bi]["z"].append(p.z)
	# Per-ring center + percentile radii; sparse rings inherit from neighbors
	var ring_c: Array = []   # Vector2(cx, cz) or null
	var ring_r: Array = []   # Vector2(rx, rz) or null
	for i in PROXY_RINGS:
		var xs: PackedFloat32Array = bins[i]["x"]
		var zs: PackedFloat32Array = bins[i]["z"]
		if xs.size() < 16:
			ring_c.append(null)
			ring_r.append(null)
			continue
		var mx := 0.0
		var mz := 0.0
		for j in xs.size():
			mx += xs[j]
			mz += zs[j]
		mx /= xs.size()
		mz /= zs.size()
		var dx := PackedFloat32Array()
		var dz := PackedFloat32Array()
		dx.resize(xs.size())
		dz.resize(zs.size())
		for j in xs.size():
			dx[j] = absf(xs[j] - mx)
			dz[j] = absf(zs[j] - mz)
		dx.sort()
		dz.sort()
		var qi := clampi(int(dx.size() * PROXY_QUANTILE), 0, dx.size() - 1)
		ring_c.append(Vector2(mx, mz))
		ring_r.append(Vector2(maxf(dx[qi], 0.15), maxf(dz[qi], 0.15)) * PROXY_PAD)
	var any_valid := false
	for i in PROXY_RINGS:
		if ring_c[i] != null:
			any_valid = true
			break
	if not any_valid:
		return false
	# Fill sparse rings from nearest valid neighbor (crown tips often have
	# few verts in their slice but still need silhouette).
	for i in PROXY_RINGS:
		if ring_c[i] != null:
			continue
		for off in PROXY_RINGS:
			var lo := i - off
			var hi := i + off
			if lo >= 0 and ring_c[lo] != null:
				ring_c[i] = ring_c[lo]
				ring_r[i] = ring_r[lo] * 0.7
				break
			if hi < PROXY_RINGS and ring_c[hi] != null:
				ring_c[i] = ring_c[hi]
				ring_r[i] = ring_r[hi] * 0.7
				break
	# Build the lathe: ring vertices + bottom/top apex points
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	for i in PROXY_RINGS:
		var ry: float = y_min + span * (float(i) + 0.5) / PROXY_RINGS
		var c: Vector2 = ring_c[i]
		var r: Vector2 = ring_r[i]
		for s in PROXY_SEGS:
			var a := TAU * float(s) / PROXY_SEGS
			verts.append(Vector3(c.x + cos(a) * r.x, ry, c.y + sin(a) * r.y))
			norms.append(Vector3(cos(a), 0.0, sin(a)))
	var bot_i := verts.size()
	verts.append(Vector3(ring_c[0].x, y_min, ring_c[0].y))
	norms.append(Vector3.DOWN)
	var top_i := verts.size()
	verts.append(Vector3(ring_c[PROXY_RINGS - 1].x, y_max, ring_c[PROXY_RINGS - 1].y))
	norms.append(Vector3.UP)
	var idx := PackedInt32Array()
	for i in PROXY_RINGS - 1:
		for s in PROXY_SEGS:
			var s1 := (s + 1) % PROXY_SEGS
			var a0 := i * PROXY_SEGS + s
			var a1 := i * PROXY_SEGS + s1
			var b0 := (i + 1) * PROXY_SEGS + s
			var b1 := (i + 1) * PROXY_SEGS + s1
			idx.append_array(PackedInt32Array([a0, b0, a1, a1, b0, b1]))
	for s in PROXY_SEGS:
		var s1 := (s + 1) % PROXY_SEGS
		idx.append_array(PackedInt32Array([bot_i, s, s1]))
		var base := (PROXY_RINGS - 1) * PROXY_SEGS
		idx.append_array(PackedInt32Array([top_i, base + s1, base + s]))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_INDEX] = idx
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return true


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


# Spawn the far impostor tier from the same per-chunk buckets the mesh tiers use,
# so transforms/custom-data match and the crossfade is water-tight. One billboard
# MMI per chunk whose species-tier has a baked atlas (_impostor_meshes). Skipped in
# mesh-only --tier-isolate modes; --tier-isolate=impostor renders it from 0m.
func _spawn_impostor_chunks(buckets: Dictionary) -> void:
	if _impostor_meshes.is_empty():
		return
	if _tier_isolate != "" and _tier_isolate != "impostor":
		return
	for ckey in buckets:
		var info: Dictionary = buckets[ckey]
		var mesh_key: String = info["mesh_key"]
		var xf_list: Array = info["xf"]
		var cd_list: Array = info["cd"]
		if xf_list.is_empty():
			continue
		var sp_name: String = mesh_key.substr(0, mesh_key.rfind("_"))
		if not _impostor_meshes.has(sp_name):
			continue
		# Centroid + spread (mirror the mesh-tier chunk math for matching culling).
		var c := Vector3.ZERO
		for tf: Transform3D in xf_list:
			c += tf.origin
		var chunk_origin: Vector3 = c / float(xf_list.size())
		var chunk_r := 0.0
		for tf: Transform3D in xf_list:
			chunk_r = maxf(chunk_r, (tf.origin - chunk_origin).length())
		var lscale: float = _lod_scale(sp_name)
		var eff_mesh_end: float = _mesh_fade_end * lscale

		var imm := MultiMesh.new()
		imm.transform_format = MultiMesh.TRANSFORM_3D
		imm.use_custom_data = true
		imm.mesh = _impostor_meshes[sp_name]
		imm.instance_count = xf_list.size()
		for i in xf_list.size():
			var tf: Transform3D = xf_list[i]
			imm.set_instance_transform(i, Transform3D(tf.basis, tf.origin - chunk_origin))
			imm.set_instance_custom_data(i, cd_list[i])
		var immi := MultiMeshInstance3D.new()
		immi.multimesh = imm
		immi.position = chunk_origin
		immi.name = "TreeImpostor_%s" % ckey.replace("|", "_")
		var imp_begin: float = eff_mesh_end * (1.0 - LOD_FADE_RATIO) - chunk_r - 5.0
		if _tier_isolate == "impostor":
			imp_begin = 0.0
		immi.visibility_range_begin = maxf(imp_begin, 0.0)
		immi.visibility_range_end = IMPOSTOR_FAR + chunk_r
		immi.visibility_range_begin_margin = 0.0
		immi.visibility_range_end_margin = 0.0
		immi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		immi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(immi)
		impostor_instances += xf_list.size()
		impostor_chunks += 1


# Build the far impostor tier: for every <species>_manifest.json under
# textures/impostors/, make one billboard QuadMesh per tier carrying the
# tree_impostor material (atlases + octahedral params). The crossfade-in band is
# baked into the material's lod_fade_in (per-tier, height-scaled) so it dithers in
# exactly where _lod1 dithers out. Instances reuse the mesh tiers' transforms, so
# positionOffset/scale (mesh-units) scale to world per-tree automatically.
func _build_impostor_assets() -> void:
	_impostor_meshes.clear()
	var imp_shader: Shader = load("res://shaders/tree_impostor.gdshader")
	var dir_path := "res://textures/impostors/"
	var da := DirAccess.open(dir_path)
	if da == null:
		return
	for fname in da.get_files():
		if not fname.ends_with("_manifest.json"):
			continue
		var f := FileAccess.open(dir_path + fname, FileAccess.READ)
		if f == null:
			continue
		var data = JSON.parse_string(f.get_as_text())
		f.close()
		if typeof(data) != TYPE_DICTIONARY:
			continue
		for tier in data:
			var meta: Dictionary = data[tier]
			var alb_path: String = meta.get("albedo", "")
			var nrm_path: String = meta.get("normal", "")
			if not ResourceLoader.exists(alb_path) or not ResourceLoader.exists(nrm_path):
				push_warning("Impostor: missing atlas for %s" % tier)
				continue
			var scale_v: float = meta.get("scale", 1.0)
			var po: Array = meta.get("position_offset", [0.0, 0.0, 0.0])
			var offset := Vector3(po[0], po[1], po[2])
			# Crossfade-in band = where this tier's mesh dithers out (height-scaled).
			# NOTE 2026-06-24: a prior attempt offset this band earlier (impostor solid
			# by F0, mesh fades F0→F1 over it) to kill the see-through transition. It did
			# NOT resolve the bug (the mesh is REMOVED in normal mode before the impostor
			# is solid — proven: lod1-isolate shows the tree solid at the transition where
			# normal shows see-through stipple). Reverted to baseline pending a real
			# diagnosis of WHY the mesh leaves early. See [[project_tree_lod_disappearance_bug]].
			var lscale: float = _lod_scale(tier)
			var band_end: float = _mesh_fade_end * lscale
			var band_begin: float = band_end * (1.0 - LOD_FADE_RATIO)
			# Impostor-only isolate: render solid from 0m, no crossfade dither.
			if _tier_isolate == "impostor":
				band_begin = 0.0
				band_end = 0.0

			var mat := ShaderMaterial.new()
			mat.shader = imp_shader
			# Far-tier brightness/hue calibration (the impostor analog of the leaf
			# shader's tier_brightness). After folding dapple + ambient-only AO into
			# the bake, the runtime-lit impostor's residual vs lod0/lod1 is SUN-ANGLE
			# dependent (diffuse_burley relight vs the leaf shader's top-lit/fresnel
			# response): measured imp/mesh ~1.20x at noon but ~0.95x at 18h, since the
			# ambient-only AO does more work when ambient dominates (evening). So this
			# is a GENTLE, near-neutral knockdown that balances the day rather than a
			# noon-tuned tint (which crashed 18h to 0.79x — too dark). Slight cool bias
			# (B highest) emulates the mesh's underside sky-fill the impostor lacks.
			# Lands ~1.12x noon / ~0.89x 18h (scripts/tier_handoff_check.sh, lp mode).
			mat.set_shader_parameter("albedo", Color(1.0, 0.0, 0.0) if OS.has_environment("IMP_RED") else Color(0.93, 0.94, 0.96))  # TEMP diag: IMP_RED=1 tints impostor red to see tier coverage
			mat.set_shader_parameter("imposterTextureAlbedo", load(alb_path))
			mat.set_shader_parameter("imposterTextureNormal", load(nrm_path))
			# ORM atlas (R = crown-interior AO, applied ambient-only by the shader so
			# the far tier isn't ~1.5x too bright). Optional — pre-AO bakes omit it,
			# and the shader's hint_default_white falls back to AO=1 (no occlusion).
			var orm_path: String = meta.get("orm", "")
			if orm_path != "" and ResourceLoader.exists(orm_path):
				mat.set_shader_parameter("imposterTextureOrm", load(orm_path))
			mat.set_shader_parameter("imposterFrames", Vector2(meta.get("frames", 16), meta.get("frames", 16)))
			mat.set_shader_parameter("isFullSphere", meta.get("is_full_sphere", false))
			mat.set_shader_parameter("scale", scale_v)
			# aabb_max = forward depth-push: the shader does
			# `VERTEX.xyz += pivotToCameraDir * aabb_max`, shoving the billboard
			# toward the camera by aabb_max * (per-tree instance scale) world-metres.
			# The addon ships aabb_max = diag/4 (= scale/2), which for a ~22m london
			# plane is a ~9m push → the card renders at D/(D-9) of true size: +9% at
			# 110m, +4% at 250m, and worse up close (measured 2026-06-23: impostor
			# 7-10% TALLER than lod0/lod1 at the eval row, oversize scaling with tree
			# height = the push fingerprint). The orthographic bake already captures
			# the true silhouette AT THE PIVOT, so the size-correct push is ZERO — any
			# forward offset only inflates. Atlases are unaffected (size is a runtime
			# placement bug, NOT a bake bug — no rebake needed). With 0 the impostor
			# matches lod0 to within ~2% (residual = off-axis billboard perspective).
			mat.set_shader_parameter("aabb_max", 0.0)
			mat.set_shader_parameter("positionOffset", offset)
			mat.set_shader_parameter("lod_fade_in", Vector2(band_begin, band_end))

			var quad := QuadMesh.new()
			quad.size = Vector2(2.0, 2.0)  # actual extent comes from the shader (scale/aabb_max)
			# Generous custom AABB so the camera-expanded billboard never frustum-culls early.
			var ext: float = scale_v * 2.0
			quad.custom_aabb = AABB(offset - Vector3(ext, ext, ext), Vector3(ext, ext, ext) * 2.0)
			quad.surface_set_material(0, mat)
			_impostor_meshes[tier] = quad
	if not _impostor_meshes.is_empty():
		print("Trees: impostor tier ready for %d species-tiers: %s" % [
			_impostor_meshes.size(), ", ".join(_impostor_meshes.keys())])


# Offline octahedral impostor bake (--bake-impostors). Bakes each size tier of
# _bake_impostors_species via ImpostorBaker and writes a manifest JSON the runtime
# impostor tier reads back. Reuses the materialised _species_meshes so the atlas
# matches the in-game tree exactly.
func _run_impostor_bake() -> void:
	var baker_script := preload("res://scripts/bake_impostors.gd")
	var out_abs := ProjectSettings.globalize_path(baker_script.OUT_DIR)
	DirAccess.make_dir_recursive_absolute(out_abs)
	var baker = baker_script.new(_loader)
	var sp := _bake_impostors_species
	var manifest := {}
	for tier in ["_s", "_m", "_l"]:
		var key: String = sp + tier
		if not _species_meshes.has(key):
			print("Impostor bake: no mesh for %s, skipping" % key)
			continue
		# Bake from the _lod1 mid mesh when it exists so the impostor's silhouette
		# and foliage density match the tier it hands off FROM (lod1 → impostor),
		# minimising the crossfade pop. Saplings (_s) have no _lod1 → bake lod0.
		# The atlas/manifest key stays the species_tier (e.g. london_plane_m) so the
		# runtime impostor loader is unaffected; only the SOURCE mesh changes.
		var lod1_key: String = key + "_lod1"
		var src_key: String = lod1_key if _species_meshes.has(lod1_key) else key
		# TEST ROUND: bake from the ONE pinned variant (LP_SINGLE_VARIANT), not all
		# variants stacked at the origin. The old all-variants bake superimposed every
		# variant crown → a denser/fuller silhouette than any single placed tree; with
		# the park now pinned to one variant the impostor must be that same single mesh
		# so the lod1→impostor handoff matches. -1 keeps the all-variants behaviour.
		var src_meshes: Array = _species_meshes[src_key]
		# bake_density: -1 (no drop) for the single-variant bake — the crown is ONE
		# variant, not 7 superimposed, so the default 90%-drop would empty it.
		var card_keep: float = baker_script.BAKE_DENSITY
		if sp == "london_plane" and LP_SINGLE_VARIANT >= 0:
			var vi: int = clampi(LP_SINGLE_VARIANT, 0, src_meshes.size() - 1)
			src_meshes = [src_meshes[vi]]
			card_keep = -1.0
			print("Impostor bake: %s from %s variant v%d (single, no card-drop, %d surfaces)…" % [key, src_key, vi, src_meshes[0].get_surface_count()])
		else:
			print("Impostor bake: %s from %s (%d meshes)…" % [key, src_key, src_meshes.size()])
		var meta: Dictionary = await baker.bake_tier(key, src_meshes, _species_heights.get(key, 0.0), card_keep)
		manifest[key] = meta
	var mpath: String = baker_script.OUT_DIR + "%s_manifest.json" % sp
	var f := FileAccess.open(mpath, FileAccess.WRITE)
	f.store_string(JSON.stringify(manifest, "\t"))
	f.close()
	print("Impostor bake complete: %s tiers -> %s" % [manifest.size(), mpath])
