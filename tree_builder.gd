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
	"conifer": "pine",
	"honeylocust": "honeylocust", "callery_pear": "callery_pear", "ginkgo": "ginkgo",
	"london_plane": "london_plane",
	"linden": "linden", "cherry": "cherry",
	"zelkova": "elm", "dead": "dead", "willow": "willow", "magnolia": "magnolia",
	"cathedral_elm": "cathedral_elm",
}

# Literary Walk / Mall: mature trees flanking the straight promenade get the
# wide-vase cathedral elm model. Most are tagged "deciduous" in OSM data but
# are historically American Elms. Zone covers both rows (X≈-640 and X≈-710).
const CATHEDRAL_ELM_ZONE := Rect2(-720.0, 1180.0, 90.0, 340.0)  # x, z, w, h

var canopy_data: Array = []  # [{x, z, radius}] for canopy map generation

# RIPARIAN CANOPY (user 2026-07-03). Real CP streams (Loch/Gill) run under dense
# Ravine woods, but the census trees along them are almost all NAMED species that
# the placement policy skips → bare, sky-exposed water. A skipped named species
# within RIPARIAN_BUFFER of a watercourse is placed as the ready london_plane model
# instead, so streams get canopy shade. Elsewhere the bare-until-redesigned policy
# is unchanged. _riparian_hash: spatial hash of stream-centreline sample points
# (cell = buffer), so the per-tree test only checks the 9 neighbouring cells.
const RIPARIAN_BUFFER := 18.0
var _riparian_hash: Dictionary = {}  # Vector2i cell -> Array[Vector2] sample points
var _species_meshes: Dictionary = {}  # archetype_name -> Array[Mesh]
var _species_heights: Dictionary = {} # archetype_name -> float (RAW mesh-unit height; divisor for placement scale)
var _species_real_h: Dictionary = {} # species_tier -> float (mean PLACED real-world height, metres) for screen-size LOD
# Per-tree LOD handoff distance (metres) for the F1 distance overlay, so its colour
# reflects the ACTUAL tier the engine renders (not a fixed distance band). Each entry:
# {"pos": Vector3, "mesh_end": float}. dist < mesh_end → lod0 (green); else impostor
# (red). This is the SAME scaled handoff the lod_fade shaders dither at
# (_mesh_fade_end × _lod_scale).
var tree_lod_bands: Array = []

# MMI / instance counts per LOD tier — read by HUD perf overlay
var lod0_instances: int = 0
var lod0_chunks: int = 0
# Far LOD tier: runtime-lit octahedral impostors (rebuilt 2026-06-23, Godot-community
# /AAA SOP; scripts/bake_impostors.gd + shaders/tree_impostor.gdshader). Billboard
# quad per species-tier, dithers in where lod0 dithers out, out to IMPOSTOR_FAR.
var impostor_instances: int = 0
var impostor_chunks: int = 0
# sp_tier -> billboard QuadMesh carrying the tree_impostor material (atlases + octa
# params from textures/impostors/<species>_manifest.json). Empty until bakes exist.
var _impostor_meshes: Dictionary = {}
# Eval-only TIER_MATCH specimens: trees tagged force_tier in the loop are pulled out
# of the chunked, distance-faded pipeline and built as dedicated single-instance MMIs
# (one chosen tier, fade disabled) in _build_forced_specimens — see eval_plot_builder.
var _forced_specimens: Array = []
# Far cull for the impostor tier (m). Trees need an impostor from the lod0→impostor
# handoff (~80m, height-scaled) out to here; beyond this they're sub-pixel / fog-
# veiled and are culled entirely. Impostor MMI count grows ~quadratically with this
# radius, so it is a real draw-call lever (an early 2500m default once regressed fps
# via ~2737 always-drawing MMIs). 800m = deep-tree-line vs cost balance (user 2026-06-26).
const IMPOSTOR_FAR: float = 800.0

# Shadow proxies (docs/trees.md §3): visible trees cast nothing; a ~220-tri
# trunk cylinder + leaf-vertex-fit crown lathe per species-size-variant casts
# instead (SHADOWS_ONLY, GI off), with phenology-driven dapple coverage.
var _shadow_proxy: bool = false
var _proxy_solid: bool = false
var _proxy_mesh_cache: Dictionary = {}  # mesh_key -> ArrayMesh
var proxy_instances: int = 0
# --tier-isolate=lod0|impostor (diagnostic): render ONLY that tree tier with the
# crossfade dither disabled, so captures can compare the pure lod0 mesh vs the
# impostor at the same distance across the whole handoff. Any value other than
# "impostor" isolates the lod0 mesh.
var _tier_isolate: String = ""
# Reference distance (height-scaled per tree) at which the impostor takes over from
# the near lod0 mesh — equals _mesh_fade_end (reassigned from it in _ready so
# --tree-mesh-range carries through). The LOD chain is lod0 → impostor, no mid tier.
var _imp_handoff_ref: float = 80.0
# --bake-impostors[=species]: offline octahedral atlas bake (scripts/bake_impostors.gd).
# Non-empty => after materialising _species_meshes, bake that species' tiers and quit.
var _bake_impostors_species: String = ""
# --tree-mesh-range=N: lod0 → impostor handoff distance (metres) — the far edge of
# the near mesh. The dither band (LOD_FADE_RATIO of this) and mesh chunk visibility
# derive from it. Shadow proxies are NOT tied to it — they keep casting to 290m.
#
# Default 80 (Chris 2026-07-03): lod0 renders solid to ~40m, dither-transitions to the
# impostor over 40–80m (LOD_FADE_RATIO 0.5), so the handoff is COMPLETE by 80m; the
# impostor then carries 80m → IMPOSTOR_FAR (800m). lod0 is the full-detail mesh, only
# needed close; past ~80m the octahedral impostor reads as well and is far cheaper.
var _mesh_fade_end: float = 80.0
# SCREEN-SIZE LOD (AAA / Godot community best practice, user 2026-06-22): a tree's
# on-screen pixel height is (world_height / distance) × const, so to make EVERY
# tree switch tiers at the same APPARENT size — not the same world distance — the
# lod0→impostor handoff distance scales linearly with the model's height.
# _mesh_fade_end (80m) is the REFERENCE distance for a REF_TREE_HEIGHT-tall canopy
# tree; a 30m london_plane_l then holds mesh ~36% farther and a 10m sapling switches
# ~55% sooner, all at the same on-screen switch size. Sources: PulseGeek "prefer
# screen-size thresholds for LOD switches"; Godot HLOD tutorial.
const REF_TREE_HEIGHT: float = 22.0  # m — height the 40/80m defaults were tuned for
# Min/max clamp keeps extreme variants sane (tiny shrubs don't pop at 30m; giant
# elms don't carry full mesh absurdly far).
const LOD_SCALE_RANGE := Vector2(0.40, 1.60)
# Crossfade dither band as a fraction of the lod0→impostor handoff distance. 0.5
# (Chris 2026-07-03) puts the transition band at [40, 80]m for a REF_TREE_HEIGHT tree:
# lod0 solid 0–40m, dither-crossfade to impostor 40–80m. Computed inline at each fade
# site so a CLI range override (--tree-mesh-range) tracks automatically.
var LOD_FADE_RATIO: float = 0.5  # tunable via --lod-fade-ratio= (transition-zone width vs overdraw cost)
# FLOOR (metres) for the size-scaled lod0-SOLID distance. The per-tree height scale
# (_lod_scale) pulls a small tree's whole handoff IN proportionally, so an s=0.40 sapling
# would render solid lod0 only to ~16m (80×0.40×0.5) and then flatten to a flat impostor
# while still reading as "up close" to a walking player — the root cause of Chris's
# "cardboard mid-trees" complaint (2026-07-04). This floors the SOLID band so no tree
# hands off to its impostor nearer than this, regardless of size. Large trees clear it
# already (solid = 40×s > this for s > 1.0) so they are unaffected — only s < 1.0 trees
# are pulled back out to the floor. Applied in _lod_scale as a scale floor derived from
# this metre value, so it tracks --tree-mesh-range / --lod-fade-ratio overrides and the
# whole (mesh fade-out / impostor fade-in / spawn) band stays consistent. Tunable — bump
# toward 50 if mid-range trees still read as cards on a walk.
const MIN_SOLID_MESH_DIST: float = 40.0
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
# SPECIES PLACEMENT POLICY (user 2026-06-26). While only london_plane is redesigned, the
# park is populated from the source data's GENERIC catch-all alone:
#   • "deciduous" (the unidentified-genus catch-all, ~35% of the data) → rendered as the one
#     ready model, london_plane. A deep all-london-plane forest already passed evaluation, so
#     this beats showing the old sparse models.
#   • Every NAMED species (oak, maple, cherry, elm, …) → skipped → BARE PATCH until its own
#     model is redesigned. This is NOT substitution (that is --all-london-plane) — the gaps
#     are intentional and fill in per-species later.
#   • The ~95 explicitly london_plane-tagged trees are ALSO treated as a named species and
#     skipped: their areas are already covered by the converted generics, so placing them
#     would add a second, redundant source of london_plane — needless bug surface (user). The
#     tags stay in park_data.bin, just unused by placement.
# GENERIC_SPECIES is the only data tag rendered; GENERIC_MODEL is what it renders as.
# REDESIGNED_SPECIES = named species to place AS THEMSELVES (empty now; add as they ship —
# "dead" snags are absent from it too, so no tree is converted to a snag).
const GENERIC_SPECIES := "deciduous"
const GENERIC_MODEL := "london_plane"
const REDESIGNED_SPECIES: Array = []
# TEST ROUND 2026-06-24 (user): when --all-london-plane forces the whole park to
# london_plane, also pin every tree — and the impostor bake — to a SINGLE variant
# per size tier instead of the per-tree hash spread, so the assessment walk sees
# exactly one chosen specimen everywhere. v3 = the strongest specimen in each tier
# (_s/_m/_l) from the variant-grid review. -1 disables the pin (full 7-variant
# spread). The bake at _run_impostor_bake sources the SAME index so lod0/_lod1/
# impostor are all the one variant.
const LP_SINGLE_VARIANT := 3
# Summer impostor card-keep for the single-variant london_plane bake. A FULL crown
# (-1, the old value) projects solid at bake res → the "too full in summer" blob.
# Dropping ~half the cards punches cluster-scale holes so the far crown reads as
# see-through as the live lod0 mesh it replaces. Tuning lever (raise → denser summer
# crown). The WINTER atlas is baked separately at card_keep=-1 + season=winter so its
# OWN retention floor (0.05) drives the bare shape (see _run_impostor_bake).
# The bake drop is now spatially EVEN (fine per-card v_bake_seed, tree_leaf.gdshader),
# not per-cluster — so a given keep removes coverage UNIFORMLY across the crown instead
# of punching clumpy cluster-scale holes. This fixed the "oddly decimated / not
# retaining shape" far crown (Chris 2026-07-03) and, because the thin no longer leaves
# whole lobes uncovered, retired the handoff-vanishing hazard below.
# (HISTORICAL, pre-even-drop: per-tier thinning _l→0.10 made _l airier but the CLUMPY
# card-drop coverage fell below lod0's in dense regions, so a lod0 crown lobe had no
# impostor to hand off to and VANISHED at the crossfade. Even drop can't do that —
# per-tier keep is safe again if _l ever wants to be thinner than _m/_s.)
# 0.6 = keep 60% of cards, evenly (raised from the clumpy-era 0.5): the even
# distribution reads coherent+airy rather than eaten, and removes the solid clumps that
# made _l read too opaque. Tuning lever (raise → denser summer crown).
const LP_SUMMER_CARD_KEEP := 0.6
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
	# Shadow proxies RESTORED to default ON (2026-07-02). GPU-confirmed at Bow
	# Bridge/noon: the per-leaf shadow path costs ~45ms of frametime in deep forest
	# — visible trees generate 37.7M shadow tris (2.5× the 15M actually seen) and
	# the water mirror re-renders them again; turning tree-shadow casting off nearly
	# doubled fps (15→27) and collapsed shadow tris 95% (37.7M→1.76M). The proxy
	# casts a cheap solid-ish crown mesh instead. Was OFF 2026-06-28 because the
	# proxy crown made the impostor flip dense-dark↔pale-flat at low sun (its 3D
	# crown shadow reached only within the directional range, then hard-popped at
	# cull distance). The deeper rebaked impostor should mitigate that flip — this
	# is a walk-verify restoration, not a settled call. Opt out: --no-tree-shadow-proxy.
	_shadow_proxy = not ("--no-tree-shadow-proxy" in OS.get_cmdline_user_args())
	if _shadow_proxy:
		print("TreeBuilder: shadow proxies ON (default) — cheap crown shadow, not per-leaf")
	else:
		print("TreeBuilder: shadow proxies OFF (--no-tree-shadow-proxy) — visible trees cast per-leaf")
	# Diagnostic: solid crowns (no dapple discard material) to isolate the
	# alpha-tested shadow-pass cost from the proxy geometry cost.
	_proxy_solid = "--proxy-solid" in OS.get_cmdline_user_args()
	if _proxy_solid:
		print("TreeBuilder: proxy crowns SOLID (diagnostic) — no dapple discard")
	# LOD chain = lod0 → impostor (no mid tier). The near lod0 mesh renders from 0m to
	# the height-scaled _mesh_fade_end, then dithers into the impostor. (The former
	# _lod1 mid tier and its --lod1-as-near/--no-lod1/--full-lod0 toggles were removed
	# 2026-07-03 when the _lod1 meshes went stale vs the current lod0 models.)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--tier-isolate="):
			_tier_isolate = arg.substr("--tier-isolate=".length())
			print("TreeBuilder: TIER ISOLATE '%s' — single tier, no crossfade (diagnostic)" % _tier_isolate)
		elif arg.begins_with("--tree-mesh-range="):
			_mesh_fade_end = clampf(float(arg.substr("--tree-mesh-range=".length())), 60.0, 1000.0)
			print("TreeBuilder: lod0 mesh → impostor fade-out end = %.0fm (default 80, scaled per tree height)" % _mesh_fade_end)
		elif arg.begins_with("--lod-fade-ratio="):
			LOD_FADE_RATIO = clampf(float(arg.substr("--lod-fade-ratio=".length())), 0.05, 0.60)
			print("TreeBuilder: LOD crossfade band = %.2f of handoff distance (wider = smoother handoff, more dither overdraw)" % LOD_FADE_RATIO)
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

	# The distance (reference, height-scaled per tree) at which the impostor takes over
	# from the near lod0 mesh — the single lod0→impostor handoff. Set AFTER arg parsing
	# so a --tree-mesh-range override is already applied.
	_imp_handoff_ref = _mesh_fade_end

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
	## Screen-size LOD multiplier: the lod0→impostor handoff distance scales with the
	## tree's REAL-WORLD height so every tree switches at the same APPARENT on-screen
	## size (AAA / Godot best practice). Returns 1.0 for a REF_TREE_HEIGHT-tall canopy
	## tree, so the 200m default is unchanged for a typical tree and only the size-
	## relative spread is added. MUST use the placed metres height (_species_real_h),
	## NOT _species_heights — the latter is RAW mesh units (~5) and dividing it by 22m
	## clamped every tree to the 0.40 floor, collapsing the handoff to ~80m (2026-06-22).
	##
	## A SECOND floor (MIN_SOLID_MESH_DIST, 2026-07-04) then keeps the SOLID lod0 band —
	## _mesh_fade_end × s × (1 − LOD_FADE_RATIO) — from dropping below a walkable minimum:
	## the pure screen-size scale pulls a small tree's handoff so close (s=0.40 → solid to
	## ~16m) that it flattens to a card while still up-close to a walker. The floor is
	## derived from the metre constant here (not hard-coded as a scale) so it tracks the
	## _mesh_fade_end / LOD_FADE_RATIO band geometry, and lives in _lod_scale so every
	## downstream handoff (mesh fade-out, impostor fade-in, spawn begin) inherits it in
	## lock-step — mismatched bands are exactly the coverage-gap bug this file has fought.
	var h: float = _species_real_h.get(species_tier, REF_TREE_HEIGHT)
	var s: float = clampf(h / REF_TREE_HEIGHT, LOD_SCALE_RANGE.x, LOD_SCALE_RANGE.y)
	# Solid-band metres at s=1.0; guard the /0 if a range/ratio override zeroes it.
	var solid_ref: float = _mesh_fade_end * (1.0 - LOD_FADE_RATIO)
	if solid_ref > 0.0:
		s = maxf(s, MIN_SOLID_MESH_DIST / solid_ref)
	return s

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


# Build the riparian spatial hash from stream polylines. Each raw OSM segment is
# sampled at <= buffer spacing so the union of the sample points' buffer-disks
# covers the whole stream corridor. Call BEFORE _build_trees.
func set_riparian_streams(streams: Array) -> void:
	_riparian_hash.clear()
	if streams.is_empty():
		return
	var step := RIPARIAN_BUFFER * 0.8   # <= buffer → gap-free corridor coverage
	var n_pts := 0
	for stream in streams:
		var raw: Array = stream.get("points", [])
		if raw.size() < 2:
			continue
		for i in range(raw.size() - 1):
			var a := Vector2(float(raw[i][0]),   float(raw[i][2]))
			var b := Vector2(float(raw[i + 1][0]), float(raw[i + 1][2]))
			var seg_len := a.distance_to(b)
			var nsub := maxi(1, int(ceil(seg_len / step)))
			for s in range(nsub + 1):
				var p := a.lerp(b, float(s) / float(nsub))
				var cell := Vector2i(int(floor(p.x / RIPARIAN_BUFFER)), int(floor(p.y / RIPARIAN_BUFFER)))
				if not _riparian_hash.has(cell):
					_riparian_hash[cell] = []
				_riparian_hash[cell].append(p)
				n_pts += 1
	print("  riparian mask: %d stream sample points in %d cells (buffer %.0fm)" % [n_pts, _riparian_hash.size(), RIPARIAN_BUFFER])

# True if (x, z) is within RIPARIAN_BUFFER of any stream centreline sample.
func _is_riparian(x: float, z: float) -> bool:
	if _riparian_hash.is_empty():
		return false
	var cx := int(floor(x / RIPARIAN_BUFFER))
	var cz := int(floor(z / RIPARIAN_BUFFER))
	var r2 := RIPARIAN_BUFFER * RIPARIAN_BUFFER
	for dx in range(-1, 2):
		for dz in range(-1, 2):
			var cell := Vector2i(cx + dx, cz + dz)
			if not _riparian_hash.has(cell):
				continue
			for p in _riparian_hash[cell]:
				var ddx: float = p.x - x
				var ddz: float = p.y - z
				if ddx * ddx + ddz * ddz <= r2:
					return true
	return false


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

	# NOTE: "deciduous" is deliberately absent — the generic catch-all data tag is
	# remapped to london_plane (GENERIC_MODEL) before any mesh lookup, so the old
	# deciduous GLB is never loaded and nothing falls back to it (user 2026-06-26).
	var _base_model_names := ["maple", "birch", "pine", "elm", "oak", "cherry", "ginkgo", "honeylocust", "linden", "london_plane", "callery_pear", "dead", "willow", "magnolia", "cathedral_elm"]
	# Load tiered models (_s, _m, _l): age/size variants per archetype. Each is a
	# full lod0 model that renders near, then hands off to its impostor (no mid tier).
	for base_name in _base_model_names:
		var tier_list: Array
		if base_name == "dead":
			tier_list = [""]
		else:
			tier_list = ["_s", "_m", "_l"]
		# LOD chain is lod0 → impostor (no mid tier). The old _lod1 mid meshes are
		# DEPRECATED and no longer loaded: they went stale vs the current lod0 models
		# (Chris 2026-07-03), so nothing may render or bake from them. With no _lod1 key
		# in _species_meshes, every `has(lod1_key)`/`mid_mesh != null` branch below no-ops
		# → lod0 is the sole near tier, fading straight into the impostor (baked from lod0).
		var full_list: Array = tier_list.duplicate()
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
			tier_suffixes = ["_s", "_m", "_l"]  # lod0 → impostor; no mid tier
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
	_forced_specimens.clear()
	var _skip_surface := 0
	var _nudged := 0
	# Eval SEASON_LOD garden: specimens may pin an ABSOLUTE season in their census
	# record ("season"). The leaf/impostor shaders read season as mod(season_t +
	# timing_off), so bake the offset relative to the season the garden is built at —
	# then each specimen renders its own season regardless of the global season_t, and
	# July + January can coexist under the one global uniform. Read the base once.
	# Read the base season from the loader (mirrors the "season_t" global shader param main
	# set). RenderingServer.global_shader_parameter_get() is editor-only and errors at
	# runtime, so we take the value from the source rather than reading it back.
	var _eval_base_season: float = float(_loader.season_t)
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
		# SPECIES PLACEMENT POLICY (see the const block): in the normal park, place ONLY the
		# generic catch-all (rendered as london_plane) plus any named species already
		# redesigned; skip everything else → bare patch. Runs BEFORE the cathedral-elm /
		# dead-snag reassignments so nothing un-redesigned is synthesised. Exempt eval plots
		# (review specific species on purpose) and --all-london-plane (substitutes instead).
		var _is_eval_tree: bool = typeof(tree_entry) == TYPE_DICTIONARY and tree_entry.get("eval", false)
		if not _all_london_plane and not _is_eval_tree:
			if species == GENERIC_SPECIES:
				species = GENERIC_MODEL          # generic catch-all → the one ready model
			elif species not in REDESIGNED_SPECIES:
				# Riparian exception: a skipped named species close to a watercourse
				# is placed as london_plane so streams get canopy shade (real CP
				# streams run under Ravine woods). Everywhere else it stays a bare patch.
				if _is_riparian(tx, tz):
					species = GENERIC_MODEL
				else:
					continue                      # named, not-yet-redesigned → bare patch
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
		# "dead" snag model is not redesigned → gate it: no london_plane becomes a snag
		# until "dead" is added to REDESIGNED_SPECIES (matches the proven all-london-plane
		# forest, which also suppressed snags).
		if not _all_london_plane and "dead" in REDESIGNED_SPECIES and species != "conifer" and species != "dead" and not is_eval:
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

		# Validate mesh exists for this species+tier; fallback chain.
		# NO deciduous fallback — the generic catch-all is already london_plane
		# (GENERIC_MODEL) by this point, so a missing tier just skips the tree
		# rather than substituting the retired deciduous model (user 2026-06-26).
		if not _species_meshes.has(species_tier):
			# Try without tier (backward compat with old single-tier models)
			if _species_meshes.has(species):
				species_tier = species
			else:
				continue

		var variants: Array = _species_meshes[species_tier]
		var n_variants := variants.size()
		if n_variants == 0:
			continue

		var variant_idx: int = int(abs(hash("%s|%.1f|%.1f" % [species_tier, tx, tz]))) % n_variants  # PER-TREE variant (local diversity, user 2026-06-22; was per-80m-cell which tiled). Position-derived → identical across lod0/lod1 (no handoff pop). COST: ~3x tree MMIs (mixed variants per chunk) — frame is fragment-bound (trees.md §4a) so likely cheap, but PERF-GATE before commit.
		# Pin london_plane to ONE variant in EVERY mode (not just --all-london-plane).
		# The impostor tier is baked from a SINGLE variant (LP_SINGLE_VARIANT; see
		# _run_impostor_bake) and is looked up per-TIER, ignoring each tree's variant. So
		# if the mesh used the per-tree hash above, a tree whose variant != the baked one
		# would hand off to a mismatched-silhouette impostor → the complementary dither
		# cross-fades two DIFFERENT shapes and the crown guts out at the handoff (the
		# "see-through band" — tree-dependent, all sizes, every angle/time, only where
		# lod1 and the impostor overlap). Pinning the mesh to the SAME variant the
		# impostor was baked from makes lod0/lod1/impostor one coherent silhouette. This
		# also realises the "one mesh per tier + shader-driven variety" direction; only
		# london_plane has an impostor today, so only it needs the pin (other species
		# keep the per-tree hash harmlessly until their impostors are baked, at which
		# point they get the same single-variant treatment). vi flows into the bucket
		# key so lod0 AND _lod1 share it (no handoff pop between the mesh tiers either).
		if species == "london_plane" and LP_SINGLE_VARIANT >= 0:
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

		# Eval-only TIER_MATCH specimens: a tree tagged force_tier renders exactly
		# ONE tier (lod0|impostor) at full opacity, bypassing the chunked,
		# distance-faded pipeline, so the three representations of the same tree can
		# be compared side by side up close. Capture its transform + season here and
		# build a dedicated single-instance MMI in _build_forced_specimens (after the
		# impostor assets exist); skip normal bucketing / canopy / LOD-band / collision.
		if is_eval and typeof(tree_entry) == TYPE_DICTIONARY \
				and str(tree_entry.get("force_tier", "")) != "":
			var pj: int = PHENOLOGY_INDEX.get(species, 4)
			var cjf := fmod(abs(sin(tx * 127.1 + tz * 311.7) * 43758.5453), 1.0)
			_forced_specimens.append({
				"tf": tf, "species_tier": species_tier, "variant": variant_idx,
				"tier": str(tree_entry["force_tier"]),
				"cd": Color(float(pj) / 13.0, 0.5, 0.0, cjf)})
			continue

		var key := "%s_%d" % [species_tier, variant_idx]
		if not xf_by_key.has(key):
			xf_by_key[key] = []
			cd_by_key[key] = []
		xf_by_key[key].append(tf)
		# Pack season data: R=species phenology index, G=timing offset, B=evergreen flag
		var pheno_idx: int = PHENOLOGY_INDEX.get(species, 4)
		var timing_off := rng.randf_range(-0.15, 0.15)
		# Eval SEASON_LOD: pin this specimen's absolute season (July/January garden).
		# s = mod(season_t + timing_off); bake the offset so s lands on the record's
		# target season at the garden's build-time global season (both lod0 mesh and
		# impostor decode INSTANCE_CUSTOM.g identically, so the tier handoff stays in
		# the same season). MultiMesh custom data holds full floats, so the >1 offset
		# a winter pin needs (g = 2.5 for Jan under a summer base) survives.
		if is_eval and typeof(tree_entry) == TYPE_DICTIONARY and tree_entry.has("season"):
			timing_off = float(tree_entry["season"]) - _eval_base_season
		var is_evergreen := 1.0 if species == "conifer" else 0.0
		# Per-tree color jitter (0-1): deterministic hash from position.
		# Consistent across all LOD tiers since they share the same tx/tz.
		var color_jitter := fmod(abs(sin(tx * 127.1 + tz * 311.7) * 43758.5453), 1.0)
		var cd := Color(float(pheno_idx) / 13.0, timing_off + 0.5, is_evergreen, color_jitter)
		cd_by_key[key].append(cd)

		# The lod0 mesh (sole near tier) is spawned in the main chunk pathway
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
		tree_lod_bands.append({"pos": Vector3(tx, ty, tz), "_tier": species_tier})

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
	# matches the rendered tier. Chain is lod0 → impostor; each band's mesh_end is the handoff.
	for band in tree_lod_bands:
		var lsc: float = _lod_scale(band["_tier"])
		band["mesh_end"] = _mesh_fade_end * lsc  # lod0 → impostor handoff (no mid tier)
		band.erase("_tier")

	# --- Spatial chunking for culling ---
	# Each chunk's MMI is positioned at its spatial centre so visibility_range works
	# per-chunk (camera distance to the node). Trees bucket into fixed cells; the lod0
	# mesh renders across the whole chunk out to its (height-scaled) handoff distance,
	# then dithers into the impostor — one handoff story for every tree (no mid tier,
	# no density modulation).
	const LOD0_CELL := 80.0

	var lod0_buckets: Dictionary = {}
	for key in xf_by_key:
		var xf_arr: Array = xf_by_key[key]
		var cd_arr: Array = cd_by_key[key]
		for j in xf_arr.size():
			var tf: Transform3D = xf_arr[j]
			var cx := int(floorf(tf.origin.x / LOD0_CELL))
			var cz := int(floorf(tf.origin.z / LOD0_CELL))
			var ck0 := "%s|%d|%d" % [key, cx, cz]
			if not lod0_buckets.has(ck0):
				lod0_buckets[ck0] = {"mesh_key": key, "cx": cx, "cz": cz, "xf": [], "cd": []}
			var bkt: Dictionary = lod0_buckets[ck0]
			bkt["xf"].append(tf)
			bkt["cd"].append(cd_arr[j])

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
		# Mesh LOD chain: the FULL lod0 mesh is the sole near tier, rendering 0m →
		# _mesh_fade_end (height-scaled), then dithering into the impostor. No mid tier.
		var near_vars: Array = _species_meshes[sp_name]
		var near_mesh: Mesh = near_vars[vi % near_vars.size()]
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
		var mesh_vis_end: float = _imp_handoff_ref * lscale + chunk_r + 5.0
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
				print("[DIAG] chunk %d|%d sp=%s vi=%d n=%d lscale=%.3f real_h=%.1f chunk_r=%.1f" % [
					info["cx"], info["cz"], sp_name, vi, xf_list.size(), lscale,
					_species_real_h.get(sp_name, -1.0), chunk_r])
				print("[DIAG]   centroid=(%.1f,%.1f,%.1f)  lod0 mesh_vis_end=%.1f" % [
					chunk_origin.x, chunk_origin.y, chunk_origin.z, mesh_vis_end])
				print("[DIAG]   impostor MMI begin=%.1f  lod0 fade_out / impostor fade_in [%.1f,%.1f]  per-tree origin.y=%.1f" % [
					eff_mesh_end*(1.0-LOD_FADE_RATIO) - chunk_r - 5.0,
					_mesh_fade_end*lscale*(1.0-LOD_FADE_RATIO), _mesh_fade_end*lscale, xf_list[0].origin.y])
		# [mesh, name prefix, FADE-TARGET distance] per mesh tier this chunk spawns.
		# The visibility_range_end is target + this MMI's AABB half-diagonal + margin,
		# computed in the loop below once the multimesh AABB is known (see cull note).
		var tier_specs: Array = []
		match _tier_isolate:
			"impostor":
				pass  # impostor-only isolate: no mesh tier, just the billboards below
			_:
				# lod0 (or --tier-isolate=lod0): the sole near mesh, → impostor at eff_mesh_end.
				tier_specs.append([near_mesh, "Tree", eff_mesh_end])
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
			# Visibility cull pad — the real fix for the see-through band. Godot 4.6
			# (#113486, in 4.6.1; also #102799/#79573) culls a MultiMeshInstance by the
			# camera distance to the CENTRE of the AABB encompassing its instances — NOT
			# the node origin, and a node custom_aabb is ignored (recomputed from the
			# multimesh). That centre sits above/aside the tree bases by the crown extent
			# + instance spread, so the per-MMI cull desynced from the per-tree shader
			# fade (true tf.origin distance) and culled the mesh mid-handoff for some
			# chunks while their impostor had not yet spawned — a near-total coverage gap
			# (the "shadow stays, canopy vanishes" Godot signature). Pad the range by THIS
			# multimesh's AABB half-diagonal, which bounds |camera→AABB-centre −
			# camera→any tree|, so every in-band tree stays drawn; the shader dither still
			# owns the visible crossfade. chunk_r (origin spread only) undercounted it —
			# it missed the crown height/width and per-tree scale. The mesh and impostor
			# MMIs carry different meshes → different AABBs → each pads by its own.
			var hd: float = mm.get_aabb().size.length() * 0.5
			# lod0 geometry stays drawn out to the (height-scaled) handoff distance
			# (spec[2]) plus this MMI's AABB half-diagonal + margin, so every in-band
			# tree is covered until its shader dither hands off to the impostor.
			var vend: float = spec[2] + hd + 5.0
			if _tier_isolate != "":
				vend = _mesh_fade_end + 60.0
			# DIAGNOSTIC (TREE_NOCULL=1): remove the per-MMI visibility_range cull on the
			# MESH tiers only (impostor untouched). Discriminates the per-instance
			# disappear/reappear dead-band: if the wink-out is GONE with the cull removed,
			# the cause is Godot's AABB-distance MMI cull (#113486) desyncing from the
			# per-tree shader fade; if it PERSISTS, the cause is the shader fade itself.
			# See [[project_tree_lod_disappearance_bug]]. Not a shipping fix.
			if OS.has_environment("TREE_NOCULL"):
				vend = 1.0e6
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.position = chunk_origin
			mmi.name = "%s_%s" % [spec[1], ckey.replace("|", "_")]
			mmi.visibility_range_begin = 0.0
			mmi.visibility_range_end = vend
			mmi.visibility_range_begin_margin = 0.0
			mmi.visibility_range_end_margin = 0.0
			mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
			if _shadow_proxy:
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			_loader.add_child(mmi)
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
			# Screen-size LOD: a tall tier's mesh hands off to its impostor farther out
			# (eff_mesh_end scales with height), so its shadow must persist at least that
			# far or the canopy keeps casting while the crown LOD is gone. 290m floor for
			# short tiers (the old fixed cap); the per-chunk spread (chunk_r) is added so
			# skewed chunks don't drop a member's shadow early.
			pmmi.visibility_range_end = maxf(290.0, eff_mesh_end + chunk_r + 5.0)
			pmmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
			_loader.add_child(pmmi)
			proxy_instances += xf_list.size()

	# Canopy occluders disabled: OccluderInstance3D inherits Node3D (not
	# GeometryInstance3D) so visibility_range cannot limit them. Without a
	# distance gate they stay active at all ranges, hiding distant trees
	# behind canopy boxes and making distant woodland look sparse.

	# The lod0 near mesh is spawned by the main chunk pathway above; its per-tree
	# transforms and custom data match the impostor tier's exactly, so the crossfade
	# to the impostor is water-tight.

	_build_tree_collision(all_trunk_xf)
	# Debug: print a few tree heights to verify scale
	var _dbg_count := 0
	for key in xf_by_key:
		if _dbg_count >= 5: break
		var xfs: Array = xf_by_key[key]
		if xfs.size() > 0:
			var tf: Transform3D = xfs[0]
			var sy := tf.basis.y.length()  # Y basis length = scale factor
			var mesh_h_val: float = _species_heights.get(key.substr(0, key.rfind("_")), 5.0)
			var actual_h := sy * mesh_h_val  # true world height in metres
			print("  Tree '%s': mesh=%.1fm × sy=%.2f = %.1fm tall, at y=%.1f" % [
				key, mesh_h_val, sy, actual_h, tf.origin.y])
			_dbg_count += 1
	print("Trees: %d placed, %d LOD0 chunks (skipped %d non-grass, nudged %d from paths)" % [
		all_trunk_xf.size(), lod0_buckets.size(), _skip_surface, _nudged])
	print("Trees mesh tier: %d lod0 near MMIs / %d instances → impostor" % [
		lod0_chunks, lod0_instances])

	# --- Far LOD tier: runtime-lit octahedral impostors (rebuilt 2026-06-23). For
	# every chunk whose species-tier has a baked atlas, spawn a billboard MMI that
	# dithers in where lod0 dithers out (shader lod_fade_in), out to IMPOSTOR_FAR. ---
	_spawn_impostor_chunks(lod0_buckets)
	if not _impostor_meshes.is_empty():
		print("Trees impostor tier: %d MMIs / %d instances" % [impostor_chunks, impostor_instances])

	# Eval TIER_MATCH garden: dedicated, distance-independent specimens (one chosen
	# tier each, fade disabled). Built after both mesh and impostor assets exist.
	if not _forced_specimens.is_empty():
		_build_forced_specimens()

	# Per-tier dither fade ranges. Shader dithering replaces Godot's
	# VISIBILITY_RANGE_FADE_SELF (known bug #88854 with alpha_to_coverage).
	# One mesh tier: the lod0 near mesh renders from 0m (no fade-in) and fades OUT
	# over the LOD_FADE_RATIO band ending at _mesh_fade_end (height-scaled), where the
	# impostor dithers IN. (The _lod1 mid tier was removed 2026-07-03.)
	const NO_FADE := Vector2(0.0, 0.0)
	for sp_key in _species_meshes:
		# Screen-size LOD: the fade band scales with this tier's model height so each
		# tree crossfades to its impostor at the same on-screen size.
		var s: float = _lod_scale(sp_key)
		var mesh_fade_out := Vector2(_mesh_fade_end * s * (1.0 - LOD_FADE_RATIO), _mesh_fade_end * s)
		var fade_in := NO_FADE  # lod0 is the near tier — always visible from 0m
		var fade_out := NO_FADE
		var tier_brightness: float = 1.0  # the near tier IS the full lod0 model
		# --tier-isolate=lod0/mesh renders the tier pure (no crossfade); otherwise
		# the lod0 mesh fades out into the impostor at the far band.
		if _tier_isolate != "lod0" and _tier_isolate != "mesh":
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


# Eval TIER_MATCH garden (eval_plot_builder): render each captured specimen as ONE
# tier at full opacity, distance-independent, so lod0 / impostor of the same
# tree can be compared side by side for texture/colour. Each gets its OWN mesh +
# materials with the LOD fade disabled (Vector2.ZERO) so mutating them never touches
# the shared park meshes, and a single-instance MMI with no visibility-range cull.
func _build_forced_specimens() -> void:
	var built := 0
	for spec: Dictionary in _forced_specimens:
		var st: String = spec["species_tier"]   # e.g. london_plane_m
		var vi: int = spec["variant"]
		var tier: String = spec["tier"]         # lod0 | impostor
		var tf: Transform3D = spec["tf"]
		var mesh: Mesh = null
		match tier:
			"impostor":
				var q = _impostor_meshes.get(st, null)
				if q == null:
					print("EvalForced: no impostor atlas for %s — skipped" % st)
					continue
				mesh = q.duplicate(false)
				var im = mesh.surface_get_material(0)
				if im is ShaderMaterial:
					var nim: ShaderMaterial = im.duplicate()
					nim.set_shader_parameter("lod_fade_in", Vector2.ZERO)
					mesh.surface_set_material(0, nim)
			_:  # lod0
				var v0: Array = _species_meshes.get(st, [])
				if v0.is_empty():
					continue
				mesh = _mesh_fade_off(v0[vi % v0.size()])
		# Apply the same octa-foreshortening size compensation the park uses
		# (_spawn_impostor_chunks) so the TIER_MATCH garden reflects the shipped size.
		var eval_basis: Basis = tf.basis
		if tier == "impostor":
			var g: float = _impostor_size_comp(st)
			eval_basis = tf.basis.scaled(Vector3(1.0, g, 1.0))
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = 1
		mm.set_instance_transform(0, Transform3D(eval_basis, Vector3.ZERO))
		mm.set_instance_custom_data(0, spec["cd"])
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = tf.origin
		mmi.name = "EvalForced_%s_%s" % [tier, st]
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		_loader.add_child(mmi)
		built += 1
	print("EvalForced: %d TIER_MATCH specimens placed (lod0/impostor, fade off)" % built)


# Shallow-duplicate a mesh and give it its OWN per-surface materials with the LOD
# crossfade disabled, so the specimen renders solid at every distance and mutating
# its materials cannot affect the shared park meshes.
func _mesh_fade_off(src: Mesh) -> Mesh:
	var dup: Mesh = src.duplicate(false)
	for si in dup.get_surface_count():
		var m = dup.surface_get_material(si)
		if m is ShaderMaterial:
			var nm: ShaderMaterial = m.duplicate()
			nm.set_shader_parameter("lod_fade_out", Vector2.ZERO)
			nm.set_shader_parameter("lod_fade_in", Vector2.ZERO)
			dup.surface_set_material(si, nm)
	return dup


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
		# Centroid for node placement; the cull pad uses the billboard multimesh's
		# own AABB half-diagonal below (not origin spread — see the begin-distance note).
		var c := Vector3.ZERO
		for tf: Transform3D in xf_list:
			c += tf.origin
		var chunk_origin: Vector3 = c / float(xf_list.size())
		var lscale: float = _lod_scale(sp_name)
		var eff_mesh_end: float = _mesh_fade_end * lscale

		# Octahedral-foreshortening size compensation (2026-07-04). A flat octa card
		# renders ~SHORTER than lod0 at the handoff: the 3-nearest-facet blend mixes in
		# facets tilted above horizon where the crown silhouette is foreshortened, and the
		# taller-relative-to-wide a crown is, the faster that silhouette height falls off
		# with view elevation. MEASURED (TIER_MATCH garden, lod0 vs impostor at equal
		# distance): impostor/lod0 HEIGHT = s 1.00, m 0.97, l 0.93, while WIDTH matches
		# (l 1.00) — a HEIGHT-ONLY deficit, NOT a uniform scale/aabb error (the billboard
		# diag + atlas framing are geometrically correct). A flat card can never be a
		# perfect 3D stand-in, so we make the best of it by up-scaling to match apparent
		# size. VERTICAL-ONLY scale (Vector3(1,g,1)): the first pass used a UNIFORM scale,
		# which fixed the height but grew the crown WIDTH ~7% too — Chris's walk read that
		# as the impostor now BIGGER than lod0 (the reversal). Scaling height alone, width
		# untouched, corrects the axis that's actually deficient and leaves the matching
		# axis alone. Anchored at the tree BASE (tf.origin = ground) so the trunk stays
		# planted; global-Y scale keeps facet selection ~intact (small horizon bias helps).
		# Runtime-only, no rebake. Env IMP_SCALE_{S,M,L} overrides for a live walk-tune.
		var imp_size_comp: float = _impostor_size_comp(sp_name)
		var imp_comp_basis := Vector3(1.0, imp_size_comp, 1.0)

		var imm := MultiMesh.new()
		imm.transform_format = MultiMesh.TRANSFORM_3D
		imm.use_custom_data = true
		imm.mesh = _impostor_meshes[sp_name]
		imm.instance_count = xf_list.size()
		for i in xf_list.size():
			var tf: Transform3D = xf_list[i]
			imm.set_instance_transform(i, Transform3D(tf.basis.scaled(imp_comp_basis), tf.origin - chunk_origin))
			imm.set_instance_custom_data(i, cd_list[i])
		var immi := MultiMeshInstance3D.new()
		immi.multimesh = imm
		immi.position = chunk_origin
		immi.name = "TreeImpostor_%s" % ckey.replace("|", "_")
		# Spawn the impostor EARLY enough that it is already drawn when each tree's
		# per-tree shader fade-in begins. Godot culls this MMI by camera distance to its
		# billboard-AABB centre (#113486/#102799), which differs from the mesh AABB centre
		# and from the tree bases — pad the begin distance back by this multimesh's AABB
		# half-diagonal (mirrors the mesh-tier fix). Without it the impostor spawned LATE
		# while the mesh had already culled → the coverage gap.
		var imp_hd: float = imm.get_aabb().size.length() * 0.5
		# Spawn the impostor so it is already drawn where each tree's per-tree shader
		# fade-in begins (the low edge of the height-scaled crossfade band), padded back
		# by this multimesh's AABB half-diagonal so no chunk spawns late.
		var imp_begin: float = (_imp_handoff_ref * lscale) * (1.0 - LOD_FADE_RATIO) - imp_hd - 5.0
		if _tier_isolate == "impostor":
			imp_begin = 0.0
		immi.visibility_range_begin = maxf(imp_begin, 0.0)
		immi.visibility_range_end = IMPOSTOR_FAR + imp_hd
		immi.visibility_range_begin_margin = 0.0
		immi.visibility_range_end_margin = 0.0
		immi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		# Impostors cast their own shadows (2026-06-28; replaces the removed shadow proxy).
		# Requires the opaque/alpha-tested shader — transparent materials don't cast shadows
		# in Godot (see tree_impostor.gdshader render_mode). In the shadow pass the billboard
		# faces the SUN, so it casts its crown silhouette.
		immi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		_loader.add_child(immi)
		impostor_instances += xf_list.size()
		impostor_chunks += 1


# Per-tier VERTICAL up-scale that compensates for octahedral-billboard foreshortening
# so the impostor's APPARENT HEIGHT matches lod0 at the handoff (see the call site in
# _spawn_impostor_chunks for the measured deficits and rationale). Factors = 1/(measured
# impostor-height ÷ lod0-height): s ~1.00 (matches, no comp), m ~0.97, l ~0.93. m bumped
# above the raw 1.028 because Chris's walk read m still slightly short after the first
# pass. Only london_plane has impostors today; the _s/_m/_l suffix keys are generic so
# other species inherit sane defaults (1.0) once baked. IMP_SCALE_{S,M,L} env overrides
# for live walk-tuning (relaunch): e.g. IMP_SCALE_L=1.06 to back the tall tier down.
func _impostor_size_comp(sp_tier: String) -> float:
	# Defaults calibrated to CHRIS'S WALK observations, which are ground truth here —
	# the headless garden proxy proved unreliable for absolute height (it read l as
	# slightly short while Chris saw it taller in the park). His anchor points: l too
	# SHORT at 1.0, too TALL at 1.075 by ~the same amount → height-neutral ≈ 1.038.
	# Tolerance: <1m of top mismatch on a 28m tree (~1.036) is fine per Chris. Tune per
	# tier on a walk with IMP_SCALE_{S,M,L} and tell me the value that reads level.
	var g := 1.0
	var tag := ""
	if sp_tier.ends_with("_l"):
		g = 1.038; tag = "L"
	elif sp_tier.ends_with("_m"):
		g = 1.045; tag = "M"
	elif sp_tier.ends_with("_s"):
		g = 1.0; tag = "S"
	if tag != "" and OS.has_environment("IMP_SCALE_" + tag):
		g = OS.get_environment("IMP_SCALE_" + tag).to_float()
	return g


# Build the far impostor tier: for every <species>_manifest.json under
# textures/impostors/, make one billboard QuadMesh per tier carrying the
# tree_impostor material (atlases + octahedral params). The crossfade-in band is
# baked into the material's lod_fade_in (per-tier, height-scaled) so it dithers in
# exactly where lod0 dithers out. Instances reuse the lod0 mesh transforms, so
# positionOffset/scale (mesh-units) scale to world per-tree automatically.
# Far-tier brightness/hue calibration tint (the impostor analog of tier_brightness).
# IMP_CALIB="r,g,b" overrides it for a headless sweep without a recompile.
func _imp_calib_tint(tier_key: String = "") -> Color:
	if OS.has_environment("IMP_CALIB"):
		var cc: PackedStringArray = OS.get_environment("IMP_CALIB").split(",")
		if cc.size() == 3:
			return Color(cc[0].to_float(), cc[1].to_float(), cc[2].to_float())
	# Per-tier (2026-07-03): the _s sapling impostor reads a touch less green than
	# lod0-s (Chris: "s impostor needs to better colour match the lod0"); measured a
	# ~5% green deficit at noon (matched at evening) in the TIER_MATCH garden. A gentle
	# green lift closes it without over-greening the evening. _m/_l keep the base tint —
	# _m reads good, and _l's gap is DENSITY (a solid-projection blob vs the airy lod0),
	# addressed by the per-tier LP_SUMMER_CARD_KEEP thin, not by colour.
	if tier_key.ends_with("_s"):
		return Color(0.93, 0.90, 0.92)
	return Color(0.90, 0.86, 0.92)  # 2026-06-28: slight de-green/cool; brightness now carried by ao_light_affect (see _build_impostor_assets)


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
			# Crossfade-in band = where this tier's lod0 mesh dithers out (height-scaled), so
			# the impostor dithers IN exactly as lod0 dithers OUT (complementary).
			var band_end: float = _imp_handoff_ref * lscale
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
			mat.set_shader_parameter("albedo", Color(1.0, 0.0, 0.0) if OS.has_environment("IMP_RED") else _imp_calib_tint(tier))  # TEMP diag: IMP_RED=1 tints impostor red to see tier coverage
			mat.set_shader_parameter("imposterTextureAlbedo", load(alb_path))
			# Crown self-shadow fake (2026-06-28, impostor<->mesh tone match). A flat
			# billboard can't geometrically self-shadow its interior the way the volumetric
			# mesh does, so it relit ~1.14x brighter + greener than lod0/lod1 at noon. The
			# diffuse-tint calib above is a near-dead lever (a 98% albedo cut moved measured
			# foliage luminance only ~22% -- the impostor brightness is dominated by an
			# albedo-INDEPENDENT ambient term that AO multiplies), so the real lever is
			# letting the baked crown AO attenuate DIRECT light too (ao_light_affect) plus
			# deepening interior AO (ao_power). Inherently sun-angle-aware: bites hard at noon
			# (strong direct -> impostor was most over-bright), little at evening; lands
			# impostor ~0.94x lod0 noon / ~0.96x evening (was 1.14x / 0.98x) -- inside the
			# lod0..lod1 band at both ends. Verified headless in the TIER_MATCH garden with a
			# fixed-pixel-mask measure (the green-classifier drifts when brightness moves).
			# IMP_AOLA / IMP_AOPOW override for a no-recompile sweep. NOTE: AO-on-direct also
			# blacks the trunk (low baked AO) -- garden-only artifact (plot renders impostors
			# at 8m); the impostor only renders past ~180m where the trunk is sub-pixel.
			# Sun-visibility atlas (2026-07-02): direct-light self-shadow that tracks
			# the REAL sun direction (tree_impostor light(); bake_impostors.gd
			# _bake_vis_channel). When bound, the static AO-on-direct fake above is
			# RETIRED (ao_light_affect 0, ao_power/floor neutral — ambient AO back to
			# plain mesh parity): the fake was correct only at its calibration hours
			# (measured impostor/lod0 1.08x at 13h/16h/18h but 0.29x at 9h). Pre-vis
			# manifests keep the old defaults so behaviour is unchanged until rebaked.
			var vis_path: String = meta.get("vis", "")
			var has_vis: bool = vis_path != "" and ResourceLoader.exists(vis_path)
			if has_vis:
				mat.set_shader_parameter("imposterTextureVis", load(vis_path))
				mat.set_shader_parameter("has_vis_atlas", true)
				var imp_vstr := 1.0
				if OS.has_environment("IMP_VIS"):
					imp_vstr = OS.get_environment("IMP_VIS").to_float()
				mat.set_shader_parameter("vis_strength", imp_vstr)
			var imp_aola := 0.0 if has_vis else 1.0
			if OS.has_environment("IMP_AOLA"):
				imp_aola = OS.get_environment("IMP_AOLA").to_float()
			var imp_aopow := 1.0 if has_vis else 1.5
			if OS.has_environment("IMP_AOPOW"):
				imp_aopow = OS.get_environment("IMP_AOPOW").to_float()
			mat.set_shader_parameter("ao_light_affect", imp_aola)
			mat.set_shader_parameter("ao_power", imp_aopow)
			var imp_aofloor := 0.0 if has_vis else 0.40
			if OS.has_environment("IMP_AOFLOOR"):
				imp_aofloor = OS.get_environment("IMP_AOFLOOR").to_float()
			mat.set_shader_parameter("ao_floor", imp_aofloor)
			# Backlit SSS/transmission (fix-ladder #2): the mesh glows when the sun is
			# behind it (tree_leaf BACKLIGHT); the impostor's custom light() bypasses the
			# built-in path, so the far tier re-injects the same Godot backlight formula.
			# sss_strength folds the mesh's per-species leaf-thickness factor -- default
			# 0.6 = london plane (the only species with impostors today). IMP_SSS sweeps it.
			var imp_sss := 0.6
			if OS.has_environment("IMP_SSS"):
				imp_sss = OS.get_environment("IMP_SSS").to_float()
			mat.set_shader_parameter("sss_strength", imp_sss)
			mat.set_shader_parameter("imposterTextureNormal", load(nrm_path))
			# ORM atlas (R = crown-interior AO, applied ambient-only by the shader so
			# the far tier isn't ~1.5x too bright). Optional — pre-AO bakes omit it,
			# and the shader's hint_default_white falls back to AO=1 (no occlusion).
			var orm_path: String = meta.get("orm", "")
			if orm_path != "" and ResourceLoader.exists(orm_path):
				mat.set_shader_parameter("imposterTextureOrm", load(orm_path))
			# WINTER atlas set: a near-bare crown baked at season=winter. Blended
			# against summer by the per-tree phenology fraction in the shader so the
			# far tier's SHAPE tracks season. Only bound when all three winter atlases
			# exist; otherwise has_winter_atlas stays false → summer-only fallback.
			var w_alb: String = meta.get("winter_albedo", "")
			var w_nrm: String = meta.get("winter_normal", "")
			var w_orm: String = meta.get("winter_orm", "")
			if w_alb != "" and w_nrm != "" and ResourceLoader.exists(w_alb) and ResourceLoader.exists(w_nrm):
				mat.set_shader_parameter("imposterTextureAlbedoWinter", load(w_alb))
				mat.set_shader_parameter("imposterTextureNormalWinter", load(w_nrm))
				if w_orm != "" and ResourceLoader.exists(w_orm):
					mat.set_shader_parameter("imposterTextureOrmWinter", load(w_orm))
				mat.set_shader_parameter("has_winter_atlas", true)
			mat.set_shader_parameter("imposterFrames", Vector2(meta.get("frames", 16), meta.get("frames", 16)))
			mat.set_shader_parameter("isFullSphere", meta.get("is_full_sphere", false))
			mat.set_shader_parameter("scale", scale_v)
			# Real tree height (m) drives the on-screen-size mip LOD in the shader, so far
			# crowns downsample correctly instead of fetching mip0 and binarizing to a flat
			# blob. Fall back to the bake diag if world_height is missing/zero.
			var wh: float = float(meta.get("world_height", 0.0))
			if wh <= 0.0:
				wh = maxf(scale_v * 2.0, 1.0)
			mat.set_shader_parameter("world_height", wh)
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
		# Bake from LOD0 — the near tier the impostor hands off FROM (lod0 → impostor;
		# there is no lod1 mid tier). The stale _lod1 GLBs on disk are DEPRECATED and
		# must never be baked from: they no longer match the current lod0 models, so an
		# impostor baked from them changes shape vs lod0 across octahedral angles (the
		# "l keeps changing shape" bug, Chris 2026-07-03 — l_lod1 was a 30%-vert
		# decimation with an 8%-wider crown; m_lod1 latently wrong too). The atlas/
		# manifest key stays the species_tier (e.g. london_plane_m) so the runtime loader
		# is unaffected; only the SOURCE mesh changes.
		var src_key: String = key
		# TEST ROUND: bake from the ONE pinned variant (LP_SINGLE_VARIANT), not all
		# variants stacked at the origin. The old all-variants bake superimposed every
		# variant crown → a denser/fuller silhouette than any single placed tree; with
		# the park now pinned to one variant the impostor must be that same single mesh
		# so the lod0→impostor handoff matches. -1 keeps the all-variants behaviour.
		var src_meshes: Array = _species_meshes[src_key]
		# bake_density: -1 (no drop) for the single-variant bake — the crown is ONE
		# variant, not 7 superimposed, so the default 90%-drop would empty it.
		var card_keep: float = baker_script.BAKE_DENSITY
		if sp == "london_plane" and LP_SINGLE_VARIANT >= 0:
			var vi: int = clampi(LP_SINGLE_VARIANT, 0, src_meshes.size() - 1)
			src_meshes = [src_meshes[vi]]
			# Summer: thin the single-variant crown so it reads see-through (not the
			# solid blob -1 produced). Winter gets its OWN bake below.
			card_keep = LP_SUMMER_CARD_KEEP
			print("Impostor bake: %s from %s variant v%d (single, summer keep=%.2f, %d surfaces)…" % [key, src_key, vi, card_keep, src_meshes[0].get_surface_count()])
		else:
			print("Impostor bake: %s from %s (%d meshes)…" % [key, src_key, src_meshes.size()])
		var hgt: float = _species_heights.get(key, 0.0)
		# SUMMER atlas (default season + suffix). Full-canopy silhouette, thinned.
		# bake_vis: also bake the sun-visibility channel (summer only — winter's
		# near-bare crown barely self-occludes; the shader relaxes vis toward 1).
		var meta: Dictionary = await baker.bake_tier(key, src_meshes, hgt, card_keep, baker_script.SUMMER_SEASON, "", true)
		# WINTER atlas: same meshes, season=winter, card_keep=-1 so the leaf shader's
		# own WINTER_RETENTION drop drives a near-bare crown. Geometry (scale/offset/
		# diag) is identical to summer, so we keep summer's meta and only graft the
		# winter atlas paths in under winter_* keys for the runtime to bind + blend.
		var wmeta: Dictionary = await baker.bake_tier(key, src_meshes, hgt, -1.0, baker_script.WINTER_SEASON, "_winter")
		meta["winter_albedo"] = wmeta.get("albedo", "")
		meta["winter_normal"] = wmeta.get("normal", "")
		meta["winter_orm"] = wmeta.get("orm", "")
		manifest[key] = meta
	var mpath: String = baker_script.OUT_DIR + "%s_manifest.json" % sp
	var f := FileAccess.open(mpath, FileAccess.WRITE)
	f.store_string(JSON.stringify(manifest, "\t"))
	f.close()
	print("Impostor bake complete: %s tiers -> %s" % [manifest.size(), mpath])
