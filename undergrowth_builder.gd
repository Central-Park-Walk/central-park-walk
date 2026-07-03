# undergrowth_builder.gd
# Chunk-based MultiMesh placement for undergrowth species.
# Fills the missing vertical layers between grass (0-25cm) and tree canopy (5m+).
# Placement driven by atlas zone type — data-first, no procedural invention.
# Species with "v" key use mesh variants (_0–_N-1) for visual variety per chunk.

var _loader
var season_t: float = 1.5       # updated by main.gd each frame
var rain_wetness: float = 0.0   # updated by main.gd each frame
var _meshes: Dictionary = {}    # species_name -> Mesh (or species_base -> [Mesh, Mesh, ...] for variants)
var _shader: Shader
var _leaf_atlas: Texture2D       # 2048x2048 leaf texture atlas (4x4 grid)
var _active_chunks: Dictionary = {}
var _last_update_pos := Vector3(-99999, 0, -99999)
var _build_queue: Array = []
var _queued_set: Dictionary = {}

# Diagnostic: peak/last _build_chunk wall time (microseconds)
var _peak_build_us: int = 0
var _last_build_us: int = 0

# Cached data refs
var _atlas_data: PackedByteArray
var _atlas_res: int
var _atlas_scale: float
var _atlas_half: float
var _hm_data: Array
var _hm_w: int
var _hm_d: int
var _hm_ws: float
var _hm_half: float

# Canopy coverage map (CPU-side) for shade-dependent placement
var _canopy_buf: PackedByteArray  # L8 grayscale, 0=open sky, 255=dense canopy
var _canopy_res: int = 0
var _canopy_cell_m: float = 0.0

# Zone type data from ground_cover_instances
var _zone_map: Dictionary = {}  # "cx|cz" (grass chunk) -> dominant zone type
var _waterside_chunks: Dictionary = {}  # "cx|cz" -> true if it contains zone-7 cells
var _catkin_tex: Texture2D = null       # cattail female-spike velvety texture (lazy-loaded)
var _scenario: RID               # cached world scenario for RS instance creation

const CHUNK := 20.0
# PERF (Chris 2026-07-03): nothing renders past ~102m now (max per-species cull 85m +
# ~17m fade, see _species_cull_dist), so don't build chunks out to 160m. Keep a small
# margin beyond the max visible edge so a chunk is ready before it comes into range.
const LOAD_RANGE := 110.0    # was 160
const UNLOAD_RANGE := 130.0  # was 180
const UPDATE_DIST := 2.0
const VIS_END := 200.0
const VIS_FADE_MARGIN := 30.0

# Species definitions — 30 species across shrubs, ferns, herbs, wetland, grasses.
# Parameters are research-backed from CPC/NYBG/iNat field data.
# name: GLB filename in models/vegetation/  s: scale multiplier range
# flex: wind sway 0-1   green: 1=evergreen   fall: fall color RGB
# fc: flower color RGB (0,0,0 = no flowers)  bl: bloom season_t range
const ATLAS_COLS := 4
const ATLAS_ROWS := 7
const SPECIES := [
	# --- SHRUBS (0-6) --- multi-stemmed woody plants 1.5-4m ---
	# sc: stem_color RGB, sr: stem_roughness (woody bark = 0.90+, herbaceous = 0.80-0.88)
	# 0: Spicebush (Lindera benzoin) — dominant understory, yellow fall, tiny yellow spring flowers
	{name="Shrub_Spicebush", v=3, s=[0.6, 1.1], flex=0.30, green=0, fall=[0.84, 0.72, 0.12], fc=[0.70, 0.68, 0.10], bl=[0.1, 0.5], berry=[0.80, 0.07, 0.05], br=[1.8, 2.9], trans=0.90, sc=[0.35, 0.28, 0.15], sr=0.92},
	# 1: Witch Hazel (Hamamelis virginiana) — zigzag branches, yellow fall, flowers in AUTUMN
	{name="Shrub_WitchHazel", s=[0.7, 1.2], flex=0.25, green=0, fall=[0.75, 0.65, 0.12], fc=[0.80, 0.72, 0.08], bl=[2.2, 3.0], sc=[0.30, 0.25, 0.18], sr=0.93},
	# 2: Viburnum (Viburnum dentatum) — dense screening, red-purple fall, white spring flowers
	{name="Shrub_Viburnum", s=[0.6, 1.0], flex=0.30, green=0, fall=[0.60, 0.10, 0.15], fc=[0.94, 0.96, 0.90], bl=[0.6, 1.2], sc=[0.28, 0.26, 0.22], sr=0.90},
	# 3: Sumac (Rhus typhina) — flat-topped colony, vivid scarlet fall; velvety stems
	{name="Shrub_Sumac", s=[0.7, 1.3], flex=0.20, green=0, fall=[0.85, 0.15, 0.05], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.40, 0.22, 0.12], sr=0.95},
	# 4: Elderberry (Sambucus nigra) — arching, white flower clusters, purple berries
	{name="Shrub_Elderberry", s=[0.6, 1.1], flex=0.35, green=0, fall=[0.55, 0.50, 0.12], fc=[0.94, 0.96, 0.88], bl=[0.8, 1.3], sc=[0.32, 0.30, 0.25], sr=0.90},
	# 5: Sweet Pepperbush (Clethra alnifolia) — bottlebrush white flowers, wetland edge
	{name="Shrub_SweetPepperbush", s=[0.6, 1.0], flex=0.30, green=0, fall=[0.70, 0.55, 0.10], fc=[0.96, 0.96, 0.92], bl=[1.0, 1.6], sc=[0.35, 0.28, 0.18], sr=0.91},
	# 6: Flowering Raspberry (Rubus odoratus) — large maple-like leaves, rose-purple flowers
	{name="Shrub_FloweringRaspberry", s=[0.6, 1.0], flex=0.35, green=0, fall=[0.60, 0.45, 0.08], fc=[0.75, 0.25, 0.55], bl=[0.8, 1.5], sc=[0.38, 0.30, 0.20], sr=0.88},

	# --- FERNS (7-10) --- frond-based, no flowers ---
	# Fern rachis: green, not bark-like
	# 7: Ostrich Fern (Matteuccia struthiopteris) — 1.3m vase, dramatic drooping fronds
	{name="Fern_Ostrich", s=[0.7, 1.3], flex=0.40, green=0, fall=[0.55, 0.45, 0.10], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], rough=0.82, spec=0.06, trans=0.90, sc=[0.18, 0.28, 0.08], sr=0.85},
	# 8: Christmas Fern (Polystichum acrostichoides) — 0.5m rosette, EVERGREEN
	{name="Fern_Christmas", s=[0.7, 1.2], flex=0.25, green=1, fall=[0.05, 0.18, 0.04], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], rough=0.52, spec=0.20, trans=0.40, sc=[0.10, 0.18, 0.05], sr=0.82},
	# 9: Cinnamon Fern (Osmundastrum cinnamomeum) — 1.1m, cinnamon fertile fronds
	{name="Fern_Cinnamon", s=[0.7, 1.2], flex=0.35, green=0, fall=[0.60, 0.50, 0.12], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], rough=0.78, spec=0.08, trans=0.85, sc=[0.22, 0.20, 0.10], sr=0.88},
	# 10: Sensitive Fern (Onoclea sensibilis) — 0.75m, broad triangular fronds, first frost kills
	{name="Fern_Sensitive", s=[0.7, 1.2], flex=0.35, green=0, fall=[0.65, 0.55, 0.12], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], rough=0.76, spec=0.10, trans=1.05, sc=[0.20, 0.28, 0.10], sr=0.84},

	# --- HERBS (11-23) --- non-woody forbs 0.3-3m ---
	# 11: Pokeweed (Phytolacca americana) — 2m, VIVID MAGENTA stems
	{name="Herb_Pokeweed", s=[0.7, 1.2], flex=0.40, green=0, fall=[0.65, 0.20, 0.30], fc=[0.90, 0.85, 0.88], bl=[0.8, 1.5], sc=[0.55, 0.15, 0.25], sr=0.82},
	# 12: Japanese Knotweed (Reynoutria japonica) — 3m invasive, bamboo-like; green with purple nodes
	{name="Herb_JapaneseKnotweed", s=[0.7, 1.3], flex=0.20, green=0, fall=[0.55, 0.48, 0.10], fc=[0.92, 0.92, 0.88], bl=[1.2, 1.8], sc=[0.30, 0.35, 0.18], sr=0.80},
	# 13: Joe-Pye Weed (Eutrochium purpureum) — 2m, purple-tinged at nodes
	{name="Herb_JoePyeWeed", s=[0.7, 1.2], flex=0.35, green=0, fall=[0.55, 0.40, 0.12], fc=[0.72, 0.42, 0.58], bl=[1.0, 1.8], sc=[0.35, 0.20, 0.28], sr=0.84},
	# 14: Coneflower (Rudbeckia laciniata) — 2m, green herbaceous stems
	{name="Herb_Coneflower", s=[0.7, 1.2], flex=0.35, green=0, fall=[0.50, 0.42, 0.08], fc=[0.85, 0.72, 0.10], bl=[1.0, 1.8], sc=[0.22, 0.32, 0.10], sr=0.82},
	# 15: Cardinal Flower (Lobelia cardinalis) — 0.8m, brilliant scarlet spike, shade streams
	{name="Herb_CardinalFlower", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.45, 0.35, 0.08], fc=[0.85, 0.08, 0.08], bl=[1.0, 1.6], sc=[0.20, 0.30, 0.08], sr=0.80},
	# 16: White Wood Aster (Eurybia divaricata) — 0.4m, dark wiry zigzag stems
	{name="Herb_WhiteWoodAster", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.50, 0.40, 0.08], fc=[0.94, 0.94, 0.90], bl=[1.5, 2.5], sc=[0.22, 0.15, 0.10], sr=0.88},
	# 17: Jewelweed (Impatiens capensis) — 0.8m, translucent pale green succulent stems
	{name="Herb_Jewelweed", s=[0.7, 1.2], flex=0.45, green=0, fall=[0.50, 0.42, 0.08], fc=[0.90, 0.50, 0.08], bl=[1.0, 1.8], sc=[0.35, 0.50, 0.18], sr=0.72},
	# 18: Mugwort (Artemisia vulgaris) — 1m, ridged woody gray-brown stems
	{name="Herb_Mugwort", s=[0.7, 1.2], flex=0.25, green=0, fall=[0.50, 0.45, 0.15], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.30, 0.24, 0.16], sr=0.90},
	# 19: White Snakeroot (Ageratina altissima) — 1.2m, green erect stems
	{name="Herb_WhiteSnakeroot", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.48, 0.38, 0.08], fc=[0.96, 0.96, 0.92], bl=[1.4, 2.2], sc=[0.24, 0.32, 0.12], sr=0.82},
	# 20: Ironweed (Vernonia noveboracensis) — 2m, stiff purple-tinged stems
	{name="Herb_Ironweed", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.50, 0.38, 0.10], fc=[0.50, 0.15, 0.55], bl=[1.0, 1.8], sc=[0.28, 0.20, 0.26], sr=0.86},
	# 21: Rose Mallow (Hibiscus moscheutos) — 1.6m, sturdy green stems
	{name="Herb_RoseMallow", s=[0.7, 1.2], flex=0.35, green=0, fall=[0.50, 0.40, 0.08], fc=[0.88, 0.55, 0.65], bl=[1.0, 1.8], sc=[0.26, 0.34, 0.12], sr=0.84},
	# 22: Burdock (Arctium minus) — 1.2m, stout gray-brown stems
	{name="Herb_Burdock", s=[0.7, 1.2], flex=0.25, green=0, fall=[0.50, 0.42, 0.10], fc=[0.60, 0.30, 0.55], bl=[1.0, 1.6], sc=[0.30, 0.26, 0.20], sr=0.90},
	# 23: Goldenrod (Solidago spp.) — 1m, densely-leafy stem, one-sided arching golden plume
	{name="Flower_Goldenrod", v=3, s=[0.8, 1.3], flex=0.35, green=0, fall=[0.72, 0.58, 0.10], fc=[0.85, 0.75, 0.10], bl=[1.5, 2.5], sc=[0.28, 0.30, 0.14], sr=0.84},

	# --- GRASSES (24) --- tall bunch/clump grasses ---
	# Grass stems: green, low roughness (smooth culms)
	# 24: Bottlebrush Grass (Elymus hystrix) — 1.1m, shade-tolerant woodland grass
	{name="Grass_Bottlebrush", s=[0.7, 1.2], flex=0.40, green=0, fall=[0.60, 0.50, 0.15], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.30, 0.36, 0.20], sr=0.78},

	# --- WETLAND (25-28) --- waterside specialists ---
	# 25: Cattail (Typha latifolia) — 2m, iconic brown cylinder heads, pond edge.
	# sc (stem_color) = WARM CINNAMON-BROWN: in the undergrowth shader opaque stem
	# geometry is painted with stem_color (vertex color is ignored for stems), and the
	# spike is stem-tagged — so this IS the spike color. The thin culms read tan/brown
	# too, which is correct. The blades are leaf-tagged (textured), so they stay green.
	{name="Wetland_Cattail", v=3, s=[0.8, 1.25], flex=0.30, green=0, fall=[0.55, 0.45, 0.12], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.52, 0.36, 0.24], sr=0.80, trans=0.82, sen=0.55, stem_vtx=1.0},
	# 26: Yellow Iris (Iris pseudacorus) — 1.2m, bright yellow flowers, wet meadow
	{name="Wetland_YellowIris", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.55, 0.48, 0.10], fc=[0.88, 0.82, 0.10], bl=[0.6, 1.2], sc=[0.20, 0.30, 0.10], sr=0.76},
	# 27: Lizard's Tail (Saururus cernuus) — 0.9m, drooping white spikes, stream edge
	{name="Wetland_LizardsTail", s=[0.7, 1.1], flex=0.35, green=0, fall=[0.50, 0.42, 0.08], fc=[0.96, 0.96, 0.90], bl=[0.8, 1.4], sc=[0.22, 0.32, 0.12], sr=0.80},
	# 28: Phragmites (Phragmites australis) — 3m, tall invasive reed beds; rigid tan culms
	{name="Wetland_Phragmites", s=[0.7, 1.3], flex=0.35, green=0, fall=[0.65, 0.55, 0.18], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.38, 0.38, 0.20], sr=0.82},

	# --- ACCENT FLOWERS (29) --- used as undergrowth in meadow zones ---
	# 29: Aster (Symphyotrichum spp.) — bushy mound smothered in small purple/yellow daisies; fall bloom
	{name="Flower_Aster", v=3, s=[0.8, 1.3], flex=0.30, green=0, fall=[0.50, 0.40, 0.10], fc=[0.60, 0.40, 0.72], bl=[1.5, 2.5], sc=[0.26, 0.30, 0.14], sr=0.82},

	# --- ADDITIONAL GRASSES (30-33) + MEADOW FLOWER (34) ---
	# 30: Little Bluestem (Schizachyrium scoparium) — 0.9m bunch grass, blue-green culms
	{name="Grass_LittleBluestem", s=[0.7, 1.2], flex=0.35, green=0, fall=[0.60, 0.38, 0.15], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.28, 0.34, 0.22], sr=0.76},
	# 31: Switchgrass (Panicum virgatum) — 1.6m tall warm-season, golden fall
	{name="Grass_Switchgrass", s=[0.7, 1.3], flex=0.35, green=0, fall=[0.65, 0.52, 0.18], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.28, 0.36, 0.20], sr=0.76},
	# 32: Tussock Sedge (Carex stricta) — 0.7m clumping wetland, yellow-green
	{name="Grass_TussockSedge", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.55, 0.48, 0.15], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.26, 0.34, 0.16], sr=0.74},
	# 33: PA Sedge (Carex pensylvanica) — 0.22m low ground cover, shade-tolerant
	{name="Grass_PASedge", s=[0.7, 1.2], flex=0.20, green=0, fall=[0.45, 0.38, 0.12], fc=[0.0, 0.0, 0.0], bl=[1.0, 2.0], sc=[0.22, 0.30, 0.14], sr=0.74},
	# 34: Black-eyed Susan (Rudbeckia hirta) — 0.8m, hairy green stems
	{name="Herb_BlackeyedSusan", s=[0.7, 1.2], flex=0.30, green=0, fall=[0.50, 0.40, 0.08], fc=[0.88, 0.72, 0.08], bl=[1.0, 1.8], sc=[0.24, 0.32, 0.12], sr=0.84},
]

# Zone type -> list of [species_index, density_per_100m2]
# Densities calibrated from CPC field surveys and NYBG Flora of Central Park.
# Zone types: 0=SheepMeadow, 1=GreatLawn, 2=NorthMeadow, 3=FormalGarden,
#   4=SportsTurf, 5=NorthWoods, 6=Ramble, 7=Waterside, 8=WildMeadow, 9=OpenLawn
#
# Primitive species (2026-05-08): generic-helper procedurals retired from
# placement until rebuilt to the Spicebush bespoke bar. Re-enabled so far:
# Spicebush (0), Goldenrod (23) and Aster (29) — the two meadow fall-color
# forbs rebuilt 2026-06-12 with bespoke habit (secund golden plume / bushy
# daisy mound). The rest remain a data gap over fake — see model-redo program.
const ZONE_SPECIES := {
	# Zones 0,1,3,4: no undergrowth (maintained lawn / formal / sports)
	# NOTE: zones 5 (North Woods) and 6 (Ramble) carry NO instances in
	# ground_cover_instances.bin — woodland undergrowth is placed via the
	# canopy-gated WOODLAND_SPECIES fallback below, NOT through these entries.
	# Goldenrod and aster are open-sun meadow forbs, so they live in the real
	# open-meadow zones (2 North Meadow, 8 Wild Meadow); _build_chunk runs them
	# through the sun-optimal (open_meadow=true) branch of _ecology_density_mult.
	2: [  # North Meadow — managed meadow with grass + forb margins
		[23, 4.0],  # goldenrod (one-sided golden plumes, colonial patches)
		[29, 3.0],  # aster (bushy mounds of purple daisies)
	],
	5: [  # North Woods (dead via zone map — see note; kept for documentation)
		[0, 4.0],   # spicebush (placed via WOODLAND_SPECIES fallback)
	],
	6: [  # Ramble (dead via zone map — see note; kept for documentation)
		[0, 5.0],   # spicebush (placed via WOODLAND_SPECIES fallback)
	],
	7: [],  # Waterside — placed via the WATERSIDE_SPECIES overlay below, NOT here.
	        # Zone 7 is a thin shoreline fringe (3047 gc cells) almost never the
	        # DOMINANT zone of its 20m chunk (present in 188 chunks, dominant in only
	        # 32), so a ZONE_SPECIES[7] entry would miss nearly every real lakeshore —
	        # the same coarse-zoning trap as the spicebush north-band bug.
	8: [  # Wild Meadow — colonial sun forbs, the autumn fall-color read
		[23, 7.0],  # goldenrod (massed golden plume patches)
		[29, 6.0],  # aster (bushy mounds smothered in purple daisies)
	],
	9: [],  # Open Lawn — empty. The Ramble/Hallett woods are labelled OpenLawn
	        # by the ground-cover zoning, so this empty entry deliberately falls
	        # through to the canopy-gated woodland fallback (see _build_chunk).
}

# Woodland chunks (no pre-baked data) get understory — but ONLY in actual
# woodland foliage zones, not on maintained lawns that happen to lack data.
# All remaining helper-based procedurals retired 2026-05-08 — only Spicebush meets
# the bespoke quality bar.
const WOODLAND_SPECIES: Array = [
	[0, 3.5],   # spicebush (thicket-forming dominant)
]
# Waterside emergents overlay — added to any chunk that CONTAINS Waterside (zone 7)
# ground-cover cells (tracked in _waterside_chunks), then gated per-instance to the
# actual water's edge (atlas water cells within WATER_EDGE_CELLS). Mirrors the
# woodland overlay so the thin shoreline fringe is placed despite the coarse
# dominant-zone map dropping it.
const WATERSIDE_SPECIES: Array = [
	[25, 12.0],  # cattail — clone-patch colony (BRIEF §2/§8). Data-fit to real Typha at the
	             # OPEN-marsh density ~10 ramets/m² (FEIS) — CP's lake/pond edges are open &
	             # wind-exposed, NOT the sheltered 15-21/m² (user 2026-06-19: clusters too dense).
	             # Each clump model ≈ 4-6 ramets, so ~2 clumps/m² → ~10 ramets/m². density 12 →
	             # ~48 clumps/chunk across 2-3 clusters (derivation in _build_chunk).
]
# Cattails are EMERGENT AQUATICS: they root AT and just INTO the water's edge, with only ~1m
# of saturated land behind (user 2026-06-19, authoritative — Typha roots in 15-75cm of water,
# the stand straddles the waterline). So the band is TIGHT to the shore and the stand straddles
# it (grass fringe + shallow-water cells), NOT pulled inland.
const WATER_EDGE_CELLS: int = 4   # ~2.4m: a grass cell qualifies only if water is this close
const LAND_EDGE_CELLS: int = 2    # ~1.2m: a water cell qualifies only if land is this close
                                  # (the shallow fringe — don't wade out into deep water)
# Waterside emergents are tall transparent cards and a lakeshore can ring the whole
# visible water, so cull them before the general undergrowth range as a precaution
# against shoreline-panorama overdraw. PRECAUTIONARY/untuned — the real cost must be
# measured on a real display (headless fps is an Xvfb present-stall artifact).
const WATERSIDE_MAX_DIST: float = 90.0
# Z ranges where woodland fallback is allowed (from park_data.json foliage_zones)
const WOODLAND_Z_RANGES: Array = [
	[-1800, -1050],  # North Woods + The Pool
	[375, 975],      # The Ramble
	[1650, 2050],    # Hallett & The Pond
]


func _init(loader) -> void:
	_loader = loader


func _build_undergrowth() -> void:
	var t0 := Time.get_ticks_msec()
	_shader = _loader._get_shader("undergrowth", "res://shaders/undergrowth.gdshader")
	if _shader == null:
		print("Undergrowth: shader not found"); return

	# Load leaf texture atlas
	var atlas_path := ProjectSettings.globalize_path("res://textures/leaf_atlas.png")
	if FileAccess.file_exists(atlas_path):
		var img := Image.load_from_file(atlas_path)
		if img:
			_leaf_atlas = ImageTexture.create_from_image(img)
			print("Undergrowth: leaf atlas loaded (%dx%d)" % [img.get_width(), img.get_height()])

	# Load all species meshes (species with "v" key get variant arrays)
	var loaded := 0
	for sp in SPECIES:
		var variant_count: int = sp.get("v", 0)
		if variant_count > 1:
			# Load mesh variants _0 through _(v-1)
			var variants: Array = []
			for vi in variant_count:
				var vname := "%s_%d" % [sp.name, vi]
				var mesh := _load_model(vname)
				if mesh != null:
					variants.append(mesh)
			if not variants.is_empty():
				_meshes[sp.name] = variants[0]  # default
				_meshes[sp.name + "_variants"] = variants
				loaded += 1
		else:
			var mesh := _load_model(sp.name)
			if mesh != null:
				_meshes[sp.name] = mesh
			loaded += 1
	print("Undergrowth: %d/%d species loaded" % [loaded, SPECIES.size()])
	if loaded == 0: return

	# Cache atlas/heightmap
	_atlas_data = _loader._atlas_data
	_atlas_res = _loader._atlas_res
	_atlas_scale = float(_atlas_res) / _loader._hm_world_size
	_atlas_half = _loader._hm_world_size * 0.5
	_hm_data = _loader._hm_data
	_hm_w = _loader._hm_width
	_hm_d = _loader._hm_depth
	_hm_ws = _loader._hm_world_size
	_hm_half = _hm_ws * 0.5

	# Cache canopy coverage map for shade-dependent placement
	if _loader._canopy_texture:
		var cimg: Image = _loader._canopy_texture.get_image()
		if cimg:
			_canopy_res = cimg.get_width()
			_canopy_cell_m = _loader._hm_world_size / float(_canopy_res)
			_canopy_buf = cimg.get_data()
			print("Undergrowth: canopy map cached (%d×%d)" % [_canopy_res, _canopy_res])

	# Build zone map from ground_cover_instances (same data as grass builder)
	_build_zone_map()

	# Cache scenario RID for RS direct instance creation
	_scenario = _loader.get_world_3d().get_scenario()

	# Initial chunk loading near spawn
	var spawn := Vector3(-480, 0, 1020)
	_last_update_pos = spawn
	_update_chunks_near(spawn)
	print("Undergrowth: ready (%d chunks queued, %.0fms)" % [
		_build_queue.size(), Time.get_ticks_msec() - t0])


func _build_zone_map() -> void:
	# Read ground_cover_instances.bin to get zone type per grass cell.
	# Build a coarse map: one dominant zone type per 20m chunk.
	var abs_path := ProjectSettings.globalize_path("res://ground_cover_instances.bin")
	var f := FileAccess.open(abs_path, FileAccess.READ)
	if f == null:
		f = FileAccess.open("res://ground_cover_instances.bin", FileAccess.READ)
	if f == null:
		print("Undergrowth: no ground_cover_instances.bin"); return

	f.get_32()  # magic
	var count: int = f.get_32()
	if count == 0: return

	# Binary format: magic(4) + count(4) + gc_x(float32) + gc_y/height(float32)
	#                + gc_z(float32) + gc_type(uint8) + gc_prox(uint8)
	var x_buf := f.get_buffer(count * 4)   # gc_x = world X
	f.get_buffer(count * 4)                # gc_y = height (skip)
	var z_buf := f.get_buffer(count * 4)   # gc_z = world Z
	var t_buf := f.get_buffer(count)       # gc_type = zone type (0-9)
	f.close()

	# Build per-chunk zone type histogram
	var chunk_types: Dictionary = {}  # "cx|cz" -> Dictionary of type->count
	for i in count:
		var wx: float = x_buf.decode_float(i * 4)
		var wz: float = z_buf.decode_float(i * 4)
		var zt: int = t_buf[i]
		var cx: int = int(floorf(wx / CHUNK))
		var cz: int = int(floorf(wz / CHUNK))
		var ck := "%d|%d" % [cx, cz]
		if not chunk_types.has(ck):
			chunk_types[ck] = {}
		var d: Dictionary = chunk_types[ck]
		d[zt] = d.get(zt, 0) + 1

	# Pick dominant type per chunk; also flag chunks containing Waterside (zone 7)
	# cells so the shoreline overlay can place emergents the dominant vote would drop.
	for ck in chunk_types:
		var d: Dictionary = chunk_types[ck]
		var best_type := -1
		var best_count := 0
		for zt in d:
			if d[zt] > best_count:
				best_count = d[zt]
				best_type = zt
		if best_type >= 0:
			_zone_map[ck] = best_type
		if d.get(7, 0) >= 2:  # ≥2 waterside cells = a real shoreline chunk
			_waterside_chunks[ck] = true

	print("  Undergrowth: zone map built (%d chunks, %d waterside)" % [
		_zone_map.size(), _waterside_chunks.size()])


# Free every live chunk's RenderingServer RIDs. Called from main at quit —
# chunk unloading only frees DISTANT chunks, so whatever was active at exit
# leaked (instance + multimesh RIDs, which also pin their meshes/materials).
func free_all_chunks() -> void:
	for key in _active_chunks:
		var rids: Array = _active_chunks[key]
		RenderingServer.free_rid(rids[1])  # instance first
		RenderingServer.free_rid(rids[0])  # multimesh second
	_active_chunks.clear()
	for rids in _eval_rids:
		RenderingServer.free_rid(rids[1])
		RenderingServer.free_rid(rids[0])
	_eval_rids.clear()


# --- Eval plot (--eval-plot) -----------------------------------------------
# Persistent specimen blocks for the Great Lawn evaluation plot
# (eval_plot_builder.gd). Same instance buffer layout, meshes, materials and
# custom data as _build_chunk, so specimens render exactly as in-park
# placements — but at fixed positions, never chunk-streamed, and visible from
# across the plot. Mesh variants are cycled across specimens so every variant
# of a species is on display.
var _eval_rids: Array = []  # [mm_rid, inst_rid] pairs, freed in free_all_chunks

func build_eval_block(sp_idx: int, pts: Array, scales: Array, tag: String) -> bool:
	var sp: Dictionary = SPECIES[sp_idx]
	var sp_name: String = sp.name
	if not _meshes.has(sp_name):
		return false
	var variants: Array = _meshes[sp_name + "_variants"] \
		if _meshes.has(sp_name + "_variants") else [_meshes[sp_name]]
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(tag) & 0x7FFFFFFF
	var by_variant: Dictionary = {}  # variant idx -> Array of pts indices
	for j in pts.size():
		var vi: int = j % variants.size()
		if not by_variant.has(vi):
			by_variant[vi] = []
		by_variant[vi].append(j)
	var RS := RenderingServer
	for vi in by_variant:
		var idxs: Array = by_variant[vi]
		var c: int = idxs.size()
		var ys := PackedFloat32Array()
		ys.resize(c)
		var ox := 0.0
		var oy := 0.0
		var oz := 0.0
		for k in c:
			var p: Vector2 = pts[idxs[k]]
			ys[k] = _dem_height(p.x, p.y)
			ox += p.x; oy += ys[k]; oz += p.y
		ox /= float(c); oy /= float(c); oz /= float(c)
		var buf := PackedFloat32Array()
		buf.resize(c * 16)
		for k in c:
			var j: int = idxs[k]
			var p: Vector2 = pts[j]
			var sc: float = scales[j]
			var yr: float = rng.randf() * TAU
			var mx: float = 1.0 if rng.randf() > 0.5 else -1.0
			var tilt: float = rng.randf_range(-0.087, 0.087)
			var cr := cos(yr)
			var sr := sin(yr)
			var ct := cos(tilt)
			var st := sin(tilt)
			var o: int = k * 16
			buf[o]    = cr * sc * mx;  buf[o+1] = sr * st * sc * mx; buf[o+2]  = sr * ct * sc * mx; buf[o+3]  = p.x - ox
			buf[o+4]  = 0.0;           buf[o+5] = ct * sc;           buf[o+6]  = -st * sc;          buf[o+7]  = ys[k] - oy
			buf[o+8]  = -sr * sc;      buf[o+9] = cr * st * sc;      buf[o+10] = cr * ct * sc;      buf[o+11] = p.y - oz
			buf[o+12] = rng.randf(); buf[o+13] = sc; buf[o+14] = float(sp_idx); buf[o+15] = 0.0
		var mm_rid := RS.multimesh_create()
		RS.multimesh_allocate_data(mm_rid, c, RS.MULTIMESH_TRANSFORM_3D, false, true)
		RS.multimesh_set_mesh(mm_rid, (variants[vi] as Mesh).get_rid())
		RS.multimesh_set_buffer(mm_rid, buf)
		var aabb_min := Vector3(INF, INF, INF)
		var aabb_max := Vector3(-INF, -INF, -INF)
		for k in c:
			var o := k * 16
			aabb_min = aabb_min.min(Vector3(buf[o + 3], buf[o + 7], buf[o + 11]))
			aabb_max = aabb_max.max(Vector3(buf[o + 3], buf[o + 7], buf[o + 11]))
		aabb_min -= Vector3(3, 1, 3)
		aabb_max += Vector3(3, 4, 3)
		RS.multimesh_set_custom_aabb(mm_rid, AABB(aabb_min, aabb_max - aabb_min))
		var inst_rid := RS.instance_create()
		RS.instance_set_base(inst_rid, mm_rid)
		RS.instance_set_scenario(inst_rid, _scenario)
		RS.instance_set_transform(inst_rid, Transform3D(Basis.IDENTITY, Vector3(ox, oy, oz)))
		RS.instance_set_visible(inst_rid, true)
		RS.instance_geometry_set_visibility_range(inst_rid, 0.0, 500.0, 0.0, 30.0,
			RS.VISIBILITY_RANGE_FADE_SELF)
		RS.instance_geometry_set_cast_shadows_setting(inst_rid,
			RS.SHADOW_CASTING_SETTING_OFF)
		_eval_rids.append([mm_rid, inst_rid])
	return true


func update_camera(camera_pos: Vector3) -> void:
	var moved := camera_pos.distance_to(_last_update_pos) > UPDATE_DIST
	if moved:
		_last_update_pos = camera_pos
		_update_chunks_near(camera_pos)
	# Build 1 queued chunk per frame
	if not _build_queue.is_empty():
		_process_queue(camera_pos)


func _update_chunks_near(pos: Vector3) -> void:
	var load_r := int(ceili(LOAD_RANGE / CHUNK))
	var cam_cx := int(floorf(pos.x / CHUNK))
	var cam_cz := int(floorf(pos.z / CHUNK))
	var needed: Dictionary = {}

	for dx in range(-load_r, load_r + 1):
		for dz in range(-load_r, load_r + 1):
			var cx := cam_cx + dx
			var cz := cam_cz + dz
			var cc := Vector3((cx + 0.5) * CHUNK, 0, (cz + 0.5) * CHUNK)
			if cc.distance_to(pos) > LOAD_RANGE: continue
			var ck := "%d|%d" % [cx, cz]

			# Check atlas: only place undergrowth on grass (type 1)
			var sample_x: float = (cx + 0.5) * CHUNK
			var sample_z: float = (cz + 0.5) * CHUNK
			var apx: int = int((sample_x + _atlas_half) * _atlas_scale)
			var apz: int = int((sample_z + _atlas_half) * _atlas_scale)
			if apx < 0 or apx >= _atlas_res or apz < 0 or apz >= _atlas_res: continue
			if _atlas_data[(apz * _atlas_res + apx) * 2] != 1: continue

			needed[ck] = true

	# Unload distant chunks
	var to_remove: Array = []
	for key: String in _active_chunks:
		# key format: "species|cx|cz"
		var p: PackedStringArray = key.split("|")
		var ck := "%s|%s" % [p[1], p[2]]
		if not needed.has(ck):
			var rids: Array = _active_chunks[key]
			RenderingServer.free_rid(rids[1])  # instance first
			RenderingServer.free_rid(rids[0])  # multimesh second
			to_remove.append(key)
	for key in to_remove:
		_active_chunks.erase(key)

	# Queue new chunks
	for ck in needed:
		if _chunk_loaded(ck) or _queued_set.has(ck):
			continue
		_build_queue.append(ck)
		_queued_set[ck] = true

	# Prune queue
	var nq: Array = []
	for ck in _build_queue:
		if needed.has(ck): nq.append(ck)
		else: _queued_set.erase(ck)
	_build_queue = nq


func _process_queue(pos: Vector3) -> void:
	var best_i := -1
	var best_d := 999999.0
	for i in _build_queue.size():
		var ck: String = _build_queue[i]
		var p: PackedStringArray = ck.split("|")
		var d := Vector3((float(p[0]) + 0.5) * CHUNK, 0,
						 (float(p[1]) + 0.5) * CHUNK).distance_to(pos)
		if d < best_d: best_d = d; best_i = i
	if best_i < 0: return
	var ck: String = _build_queue[best_i]
	_build_queue.remove_at(best_i)
	_queued_set.erase(ck)
	if not _chunk_loaded(ck):
		var _bt0 := Time.get_ticks_usec()
		_build_chunk(ck)
		var _bt_us := Time.get_ticks_usec() - _bt0
		if _bt_us > _peak_build_us: _peak_build_us = _bt_us
		_last_build_us = _bt_us
		if _bt_us > 5000:
			print("[undergrowth] _build_chunk %s: %.1f ms (queue=%d)" % [ck, _bt_us / 1000.0, _build_queue.size()])


func _chunk_loaded(ck: String) -> bool:
	for sp_idx in SPECIES.size():
		if _active_chunks.has("%d|%s" % [sp_idx, ck]): return true
	return false


func _canopy_at(wx: float, wz: float) -> int:
	# Returns canopy coverage 0-255 at world position. 0 = open sky.
	if _canopy_res == 0: return 0
	var px: int = int((wx + _hm_half) / _canopy_cell_m)
	var pz: int = int((wz + _hm_half) / _canopy_cell_m)
	if px < 0 or px >= _canopy_res or pz < 0 or pz >= _canopy_res: return 0
	return _canopy_buf[pz * _canopy_res + px]


func _near_water(apx: int, apz: int) -> bool:
	# True if any world-atlas cell within WATER_EDGE_CELLS is water (surface type 4).
	# Keeps the waterside overlay hugging the shoreline instead of spreading inland
	# across the whole 20m chunk. apx/apz are atlas-grid coords.
	# Stride-sampled (every 2 cells) so this stays cheap in the per-attempt placement
	# loop — water bodies are large contiguous blobs, so a coarse sample never misses
	# a real shore. Short-circuits on the first water cell.
	var r := WATER_EDGE_CELLS
	var r2 := r * r
	for dz in range(-r, r + 1, 2):
		var nz := apz + dz
		if nz < 0 or nz >= _atlas_res: continue
		for dx in range(-r, r + 1, 2):
			if dx * dx + dz * dz > r2: continue
			var nx := apx + dx
			if nx < 0 or nx >= _atlas_res: continue
			if _atlas_data[(nz * _atlas_res + nx) * 2] == 4:
				return true
	return false


func _near_land(apx: int, apz: int) -> bool:
	# True if any world-atlas cell within LAND_EDGE_CELLS is grass (type 1). Keeps cattails
	# placed ON water to the SHALLOW fringe right at the bank, not out in open/deep water.
	var r := LAND_EDGE_CELLS
	for dz in range(-r, r + 1):
		var nz := apz + dz
		if nz < 0 or nz >= _atlas_res: continue
		for dx in range(-r, r + 1):
			var nx := apx + dx
			if nx < 0 or nx >= _atlas_res: continue
			if _atlas_data[(nz * _atlas_res + nx) * 2] == 1:
				return true
	return false


# ── Ecology-driven density modulation ──────────────────────────────────
# Real understory density varies with microsite conditions. Instead of
# uniform placement, modulate per-chunk density based on what drives
# vegetation growth in Eastern deciduous forest:
#
#   Canopy cover: Shade-tolerant shrubs (spicebush, viburnum) peak at
#     40-75% cover. Deep shade (>85%) suppresses even shade species.
#     Full sun (<20%) favors grass over shrubs.
#
#   Slope: Steep terrain → thin soil, erosion, poor rooting. Gentle
#     slopes and flats accumulate organic matter and moisture.
#
#   Moisture proxy: Lower local elevation relative to surroundings =
#     moister microsite. Spicebush especially loves moist soil.
#
#   Patch structure: Large-scale noise creates natural thicket/clearing
#     mosaic. Real forests are patchy — dense in some spots, open in
#     others, driven by disturbance history and soil variation.

func _slope_at(wx: float, wz: float) -> float:
	# Return slope magnitude (0 = flat, 1+ = steep) from DEM heightmap.
	# Central difference over ~2m step.
	var step := 1.0
	var h_c := _dem_height(wx, wz)
	var h_e := _dem_height(wx + step, wz)
	var h_n := _dem_height(wx, wz - step)
	var dx := (h_e - h_c) / step
	var dz := (h_n - h_c) / step
	return sqrt(dx * dx + dz * dz)

func _dem_height(wx: float, wz: float) -> float:
	var xi: float = (wx + _hm_half) / _hm_ws * (_hm_w - 1)
	var zi: float = (wz + _hm_half) / _hm_ws * (_hm_d - 1)
	var xi0: int = clampi(int(xi), 0, _hm_w - 2)
	var zi0: int = clampi(int(zi), 0, _hm_d - 2)
	var fx: float = xi - xi0
	var fz: float = zi - zi0
	var h00: float = float(_hm_data[zi0 * _hm_w + xi0])
	var h10: float = float(_hm_data[zi0 * _hm_w + xi0 + 1])
	var h01: float = float(_hm_data[(zi0 + 1) * _hm_w + xi0])
	var h11: float = float(_hm_data[(zi0 + 1) * _hm_w + xi0 + 1])
	if fz <= fx:
		return h00 + (h10 - h00) * fx + (h11 - h10) * fz
	else:
		return h00 + (h11 - h01) * fx + (h01 - h00) * fz

func _ecology_density_mult(wx: float, wz: float, open_meadow := false) -> float:
	# Returns 0.15 – 2.5 multiplier on base density for this position.
	# open_meadow=true flips the canopy response for sun-loving meadow forbs
	# (goldenrod, aster): they peak in open sun and are shaded out under canopy,
	# the opposite of woodland understory.
	var mult := 1.0

	var canopy: float = float(_canopy_at(wx, wz)) / 255.0  # 0-1
	if open_meadow:
		# Sun forbs — full sun is ideal, partial-to-deep shade thins them out.
		if canopy < 0.35:
			mult *= 1.0  # open sun — the meadow optimum
		elif canopy < 0.65:
			mult *= lerpf(1.0, 0.5, (canopy - 0.35) / 0.30)  # edge shade
		else:
			mult *= lerpf(0.5, 0.2, clampf((canopy - 0.65) / 0.35, 0.0, 1.0))  # shaded out
	else:
		# 1) Canopy sweet spot — understory peaks at partial shade (40-75%).
		#    Deep shade (>85%) or full sun (<20%) suppresses growth.
		if canopy < 0.20:
			mult *= 0.3  # open sun — grass dominates
		elif canopy < 0.40:
			mult *= lerpf(0.3, 1.0, (canopy - 0.20) / 0.20)  # transition
		elif canopy <= 0.75:
			mult *= lerpf(1.0, 1.4, (canopy - 0.40) / 0.35)  # sweet spot — peaks at 75%
		elif canopy <= 0.85:
			mult *= lerpf(1.4, 0.8, (canopy - 0.75) / 0.10)  # declining in deep shade
		else:
			mult *= lerpf(0.8, 0.4, (canopy - 0.85) / 0.15)  # suppressed

	# 2) Slope penalty — steep terrain has thin soil, poor rooting.
	var slope: float = _slope_at(wx, wz)
	if slope > 0.3:
		mult *= lerpf(1.0, 0.2, clampf((slope - 0.3) / 0.5, 0.0, 1.0))

	# 3) Moisture proxy — lower relative elevation = moister = more growth.
	#    Compare chunk center height to local neighborhood average.
	var h_center := _dem_height(wx, wz)
	var h_avg := (_dem_height(wx - 10, wz) + _dem_height(wx + 10, wz)
	            + _dem_height(wx, wz - 10) + _dem_height(wx, wz + 10)) * 0.25
	var elev_diff: float = h_center - h_avg  # negative = lower = moister
	# Moist hollows get up to 1.3x, ridgetops get 0.7x
	mult *= clampf(1.0 - elev_diff * 0.15, 0.7, 1.3)

	# 4) Patch noise — large-scale (30-50m) spatial variation creates
	#    natural thicket/clearing mosaic. Hash-based for determinism.
	var nx: float = wx * 0.022 + 31.7
	var nz: float = wz * 0.022 + 17.3
	# Simple 2D hash noise (deterministic, no import needed)
	var patch: float = fposmod(sin(nx * 127.1 + nz * 311.7) * 43758.5453, 1.0)
	var patch2: float = fposmod(sin(nx * 0.7 * 269.5 + nz * 0.7 * 183.3) * 43758.5453, 1.0)
	var patch_val: float = (patch + patch2) * 0.5  # 0-1, clustered
	# Map to 0.15 – 2.0 range: some spots nearly bare, others dense thickets
	mult *= lerpf(0.15, 2.0, patch_val)

	return clampf(mult, 0.15, 2.5)


func _species_cull_dist(sp_idx: int) -> float:
	## Per-species visibility range based on plant size.
	## PERF (Chris 2026-07-03): the old 80/140/200m ranges rendered dense alpha-card
	## understory FAR past where it resolves — measured the #1 deep-forest cost (hiding
	## undergrowth was 6→35fps, vpgpu 168→35ms; it's overdraw, not tris). A 2m shrub is
	## ~2px at 200m. Trim to where a plant of that size actually reads (same "don't render
	## past visibility" principle as the water-mirror boundary). Tune for look after.
	var s_hi: float = SPECIES[sp_idx].s[1]
	if s_hi <= 0.5:
		return 40.0    # small herbs/flowers (was 80)
	elif s_hi <= 1.0:
		return 60.0    # medium herbs/ferns (was 140)
	else:
		return 85.0    # large shrubs, spicebush etc. (was 200/VIS_END)


func _density_tier(chunk_dist: float) -> float:
	## Distance-based density thinning — AAA standard.
	## Full density near camera, progressively thinner at distance.
	if chunk_dist < 60.0:
		return 1.0
	elif chunk_dist < 120.0:
		return 0.5
	else:
		return 0.25


func _build_chunk(ck: String) -> void:
	var ck_p: PackedStringArray = ck.split("|")
	var cx: float = float(ck_p[0]) * CHUNK
	var cz: float = float(ck_p[1]) * CHUNK

	# Determine what species to place. Two independent, ADDITIVE layers — each
	# entry is [species_index, density, require_canopy]:
	#   1. Zone-assigned forbs from the ground-cover zoning (goldenrod/aster) —
	#      sun-loving, no canopy requirement.
	#   2. Woodland understory overlay (spicebush) — added wherever a chunk
	#      falls inside a woodland Z-range, REGARDLESS of its ground-cover zone.
	#      The per-instance canopy gate places it only under actual tree cover,
	#      so it fills the real forest floor while staying out of the open
	#      clearings/meadow that the coarse band also spans. This is why a chunk
	#      the zoning mislabels — forested ground tagged OpenLawn (the Ramble &
	#      Hallett bands, ~88%/93%) or NorthMeadow (43% of the North Woods band)
	#      — still gets its understory instead of coming up bare or forb-only.
	# Entry layout: [species_index, density, require_canopy, require_water]
	var zone_type: int = _zone_map.get(ck, -1)
	var species_list: Array = []
	if zone_type >= 0 and ZONE_SPECIES.has(zone_type):
		for e in ZONE_SPECIES[zone_type]:
			species_list.append([e[0], e[1], false, false])

	var chunk_z: float = cz + CHUNK * 0.5
	for zr in WOODLAND_Z_RANGES:
		if chunk_z >= zr[0] and chunk_z <= zr[1]:
			for e in WOODLAND_SPECIES:
				species_list.append([e[0], e[1], true, false])
			break

	# Waterside overlay — shoreline emergents on chunks holding zone-7 cells,
	# gated per-instance to the water's edge (require_water).
	if _waterside_chunks.has(ck):
		for e in WATERSIDE_SPECIES:
			species_list.append([e[0], e[1], false, true])

	if species_list.is_empty():
		return  # No zone forbs, not woodland, not waterside — nothing to place

	# Distance-based density thinning
	var chunk_center := Vector3(cx + CHUNK * 0.5, 0, cz + CHUNK * 0.5)
	var chunk_dist := chunk_center.distance_to(_last_update_pos)
	var tier_mult := _density_tier(chunk_dist)

	var rng := RandomNumberGenerator.new()
	rng.seed = (int(ck_p[0]) * 73856093 + int(ck_p[1]) * 19349669 + 42) & 0x7FFFFFFF

	# Seasonal check for fungi (indices 16, 17)
	# Mushrooms: peak late summer through fall (season_t 1.5-2.8), absent otherwise
	var cur_season: float = season_t
	var mushroom_active: bool = cur_season > 1.3 and cur_season < 2.9
	# Rain boosts mushroom density
	var rain_boost: float = 1.0 + rain_wetness * 0.5

	# Ecology-driven density modulation based on canopy cover, slope, moisture,
	# and patch noise. Sampled at chunk centre for both responses: woodland
	# understory (canopy-required) wants the shade-loving curve; the open-meadow
	# forbs want full sun as the optimum. A single chunk can host both layers,
	# so compute each once and pick per species below.
	var ccx := cx + CHUNK * 0.5
	var ccz := cz + CHUNK * 0.5
	var eco_shade := _ecology_density_mult(ccx, ccz, false)
	var eco_sun := _ecology_density_mult(ccx, ccz, true)

	# Pre-allocate buffers per species
	var bufs: Dictionary = {}
	var cnts: Dictionary = {}
	var sums: Dictionary = {}

	for sp_entry in species_list:
		var sp_idx: int = sp_entry[0]
		var entry_require_canopy: bool = sp_entry[2]
		var entry_require_water: bool = sp_entry[3]
		# Hard distance cull for waterside emergents (see WATERSIDE_MAX_DIST).
		if entry_require_water and chunk_dist > WATERSIDE_MAX_DIST: continue
		var density: float = sp_entry[1] * (eco_shade if entry_require_canopy else eco_sun)
		var sp_name: String = SPECIES[sp_idx].name
		if not _meshes.has(sp_name): continue

		# Skip fungi outside their season
		if sp_idx >= 16 and sp_idx <= 17:
			if not mushroom_active: continue
			density *= rain_boost

		var target := int(density * CHUNK * CHUNK / 100.0 * tier_mult)
		if target <= 0: continue

		var buf := PackedFloat32Array()
		buf.resize(target * 2 * 16)  # over-allocate
		bufs[sp_idx] = buf
		cnts[sp_idx] = 0
		sums[sp_idx] = [0.0, 0.0, 0.0]

		var placed := 0
		var sp: Dictionary = SPECIES[sp_idx]
		var s_lo: float = sp.s[0]
		var s_hi: float = sp.s[1]

		# PLACEMENT — data-fit (user 2026-06-19: "be sure placement fits the data, as well as
		# cluster size and density"). Terminology (user): a CLUMP = one model instance — a
		# rhizome knot of ~3-4 ramets (3-4 catkins + ~36 blades, confirmed by the new 3D-model
		# refs); a CLUSTER = a clone patch = a group of clumps.
		# Data (FEIS Typha latifolia + GoBotany + BRIEF §3):
		#   • clone patch (CLUSTER) = discrete 3-5 m diameter, with GAPS between patches.
		#   • shoot (ramet) density in a sheltered stand ~15-21 /m² (CP shores = dense end).
		# Derivation: at ~3.4 ramets per clump → 4.4-6 clumps/m²; a 4 m patch (~12.5 m²) holds
		# ~55-75 clumps. So: seed a FEW land-biased clusters per shoreline chunk (discrete,
		# with gaps) and pack each to that density. With WATERSIDE density 44 → target≈176,
		# n_clusters≈3 → ~59 clumps each → ~4.7 clumps/m² → ~16 ramets/m² (inside FEIS band).
		# Each cluster: [centre:Vector2, radius:float (clone-patch radius), weight:float].
		var clusters: Array = []
		var weight_sum := 0.0
		if entry_require_water:
			var n_clusters := rng.randi_range(2, 3)  # a few discrete patches per shoreline chunk
			for _c in range(n_clusters):
				# Anchor sits ON the WATERLINE: among the (already edge-tight) tries keep the
				# one with the most WATER around it, so the clone patch roots AT the shore and
				# straddles into the shallows — emergent aquatics stand in the water, not behind
				# it (user 2026-06-19). (Reverses the earlier mistaken land-bias.)
				var ax := 0.0
				var az := 0.0
				var found := false
				var best_water := -1
				for _try in range(24):
					var tx := cx + rng.randf() * CHUNK
					var tz := cz + rng.randf() * CHUNK
					var tpx := int((tx + _atlas_half) * _atlas_scale)
					var tpz := int((tz + _atlas_half) * _atlas_scale)
					if not _near_water(tpx, tpz): continue
					var water := 0
					for ddx in range(-4, 5, 2):
						for ddz in range(-4, 5, 2):
							var nx := tpx + ddx
							var nz := tpz + ddz
							if nx >= 0 and nx < _atlas_res and nz >= 0 and nz < _atlas_res:
								if _atlas_data[(nz * _atlas_res + nx) * 2] == 4:
									water += 1
					if water > best_water:
						best_water = water
						ax = tx
						az = tz
						found = true
				if not found: continue
				# clone-patch radius 1.2-2.0 m → straddles the waterline (~1-2m into the shallows
				# + ~1m of saturated bank); tighter than the old 3-5m to hug the edge band.
				var radius: float = clampf(rng.randfn(1.6, 0.4), 1.2, 2.0)
				var weight: float = clampf(rng.randfn(1.0, 0.4), 0.4, 2.0)
				clusters.append([Vector2(ax, az), radius, weight])
				weight_sum += weight
			if clusters.is_empty(): continue  # no shoreline found in this chunk

		for _attempt in int(target * 3):
			if placed >= target: break
			var bx: float
			var bz: float
			if clusters.is_empty():
				bx = cx + rng.randf() * CHUNK
				bz = cz + rng.randf() * CHUNK
			else:
				# Weighted pick — bigger-weight patches get proportionally more clumps
				var r := rng.randf() * weight_sum
				var kc: Vector2 = clusters[0][0]
				var krad: float = clusters[0][1]
				for c in clusters:
					r -= c[2]
					if r <= 0.0:
						kc = c[0]
						krad = c[1]
						break
				# sd = radius/2 → ~95% of clumps fall within the clone-patch radius. BOUND the
				# offset to the patch edge: real clone patches have a defined edge (rhizomes
				# expand as a front), so no far-flung singleton clumps — the unbounded Gaussian
				# tail produced lone clumps 2-3× the radius out (user 2026-06-19).
				var off := Vector2(rng.randfn(0.0, krad * 0.5), rng.randfn(0.0, krad * 0.5))
				if off.length() > krad:
					off = off.normalized() * krad  # hard patch edge — no clump strays past it
				bx = kc.x + off.x
				bz = kc.y + off.y

			# Atlas check — must be grass, with 1.5m buffer from paths
			var apx: int = int((bx + _atlas_half) * _atlas_scale)
			var apz: int = int((bz + _atlas_half) * _atlas_scale)
			if apx < 0 or apx >= _atlas_res or apz < 0 or apz >= _atlas_res: continue
			var ai: int = (apz * _atlas_res + apx) * 2
			var cell: int = _atlas_data[ai]
			if entry_require_water:
				# Cattail straddles the waterline: GRASS cells at the immediate edge (saturated
				# fringe) AND shallow-WATER cells right at the bank — emergent aquatics root in
				# the water, not on dry land behind it (user 2026-06-19).
				if cell == 1:
					if not _near_water(apx, apz): continue
				elif cell == 4:
					if not _near_land(apx, apz): continue
				else:
					continue
			elif cell != 1:
				continue
			# Check occupancy — avoid trees, benches, etc.
			if _atlas_data[ai + 1] != 0: continue
			# Canopy check — the woodland overlay requires tree cover overhead
			if entry_require_canopy and _canopy_at(bx, bz) < 30: continue
			# Path proximity buffer (~1.5m = ~2.5 atlas cells at 0.6m/cell)
			var near_path := false
			for dxy in [[-2,0],[2,0],[0,-2],[0,2],[-2,-2],[2,2],[-2,2],[2,-2]]:
				var nx: int = apx + dxy[0]
				var nz: int = apz + dxy[1]
				if nx >= 0 and nx < _atlas_res and nz >= 0 and nz < _atlas_res:
					var ns: int = _atlas_data[(nz * _atlas_res + nx) * 2]
					if ns == 2 or ns == 3:  # paved or unpaved path
						near_path = true
						break
			if near_path: continue

			# Height from raw DEM heightmap — same source the GPU grass uses.
			var xi: float = (bx + _hm_half) / _hm_ws * (_hm_w - 1)
			var zi: float = (bz + _hm_half) / _hm_ws * (_hm_d - 1)
			var xi0: int = clampi(int(xi), 0, _hm_w - 2)
			var zi0: int = clampi(int(zi), 0, _hm_d - 2)
			var fx: float = xi - xi0
			var fz: float = zi - zi0
			var h00: float = float(_hm_data[zi0 * _hm_w + xi0])
			var h10: float = float(_hm_data[zi0 * _hm_w + xi0 + 1])
			var h01: float = float(_hm_data[(zi0 + 1) * _hm_w + xi0])
			var h11: float = float(_hm_data[(zi0 + 1) * _hm_w + xi0 + 1])
			var wy: float
			if fz <= fx:
				wy = h00 + (h10 - h00) * fx + (h11 - h10) * fz
			else:
				wy = h00 + (h11 - h01) * fx + (h01 - h00) * fz

			var yr: float = rng.randf() * TAU
			# Normal distribution (mean at 40% of range, sd = 20% of range)
			# Biases toward smaller plants — few reach maximum size
			var s_mean: float = s_lo + (s_hi - s_lo) * 0.4
			var s_sd: float = (s_hi - s_lo) * 0.20
			var sc: float = clampf(rng.randfn(s_mean, s_sd), s_lo, s_hi)
			var seed_val: float = rng.randf()
			# Random X-mirror (50% chance) — doubles perceived mesh variety
			var mx: float = 1.0 if rng.randf() > 0.5 else -1.0
			# Slight random lean (±5°) via R_y(yr) * R_x(tilt)
			var tilt: float = rng.randf_range(-0.087, 0.087)
			var cr: float = cos(yr)
			var sr: float = sin(yr)
			var ct: float = cos(tilt)
			var st: float = sin(tilt)

			var c: int = cnts[sp_idx]
			var o: int = c * 16
			buf[o]    = cr * sc * mx;        buf[o+1]  = sr * st * sc * mx; buf[o+2]  = sr * ct * sc * mx; buf[o+3]  = bx
			buf[o+4]  = 0.0;                 buf[o+5]  = ct * sc;           buf[o+6]  = -st * sc;          buf[o+7]  = wy
			buf[o+8]  = -sr * sc;            buf[o+9]  = cr * st * sc;      buf[o+10] = cr * ct * sc;      buf[o+11] = bz
			buf[o+12] = seed_val; buf[o+13] = sc; buf[o+14] = float(sp_idx); buf[o+15] = 0.0
			cnts[sp_idx] = c + 1
			sums[sp_idx][0] += bx
			sums[sp_idx][1] += wy
			sums[sp_idx][2] += bz
			placed += 1

	# Create MultiMesh per species — pick mesh variant per chunk for variety
	for sp_idx in bufs:
		var c: int = cnts[sp_idx]
		if c == 0: continue
		var sp: Dictionary = SPECIES[sp_idx]
		var sp_name: String = sp.name
		var mesh: Mesh = _meshes.get(sp_name)
		if mesh == null: continue
		# Pick variant based on chunk hash for spatial consistency
		var variants_key := sp_name + "_variants"
		if _meshes.has(variants_key):
			var variants: Array = _meshes[variants_key]
			var vi: int = (int(ck_p[0]) * 48271 + int(ck_p[1]) * 91969 + sp_idx * 31) % variants.size()
			mesh = variants[vi]

		var buf: PackedFloat32Array = bufs[sp_idx]
		var ox: float = sums[sp_idx][0] / float(c)
		var oy: float = sums[sp_idx][1] / float(c)
		var oz: float = sums[sp_idx][2] / float(c)

		# Relocate to local space
		for j in c:
			var o: int = j * 16
			buf[o+3] -= ox; buf[o+7] -= oy; buf[o+11] -= oz
		buf.resize(c * 16)

		var RS := RenderingServer
		var mm_rid := RS.multimesh_create()
		RS.multimesh_allocate_data(mm_rid, c, RS.MULTIMESH_TRANSFORM_3D, false, true)
		RS.multimesh_set_mesh(mm_rid, mesh.get_rid())
		RS.multimesh_set_buffer(mm_rid, buf)

		# Compute tight AABB from local-space instance positions for frustum culling
		var aabb_min := Vector3(INF, INF, INF)
		var aabb_max := Vector3(-INF, -INF, -INF)
		for j in c:
			var o := j * 16
			var px: float = buf[o + 3]
			var py: float = buf[o + 7]
			var pz: float = buf[o + 11]
			if px < aabb_min.x: aabb_min.x = px
			if py < aabb_min.y: aabb_min.y = py
			if pz < aabb_min.z: aabb_min.z = pz
			if px > aabb_max.x: aabb_max.x = px
			if py > aabb_max.y: aabb_max.y = py
			if pz > aabb_max.z: aabb_max.z = pz
		# Pad for mesh extent (plants up to ~3m tall/wide)
		aabb_min -= Vector3(3, 1, 3)
		aabb_max += Vector3(3, 4, 3)
		RS.multimesh_set_custom_aabb(mm_rid, AABB(aabb_min, aabb_max - aabb_min))

		var inst_rid := RS.instance_create()
		RS.instance_set_base(inst_rid, mm_rid)
		RS.instance_set_scenario(inst_rid, _scenario)
		RS.instance_set_transform(inst_rid, Transform3D(Basis.IDENTITY, Vector3(ox, oy, oz)))
		RS.instance_set_visible(inst_rid, true)
		var cull_d := _species_cull_dist(sp_idx)
		RS.instance_geometry_set_visibility_range(inst_rid, 0.0, cull_d, 0.0,
			minf(VIS_FADE_MARGIN, cull_d * 0.2), RS.VISIBILITY_RANGE_FADE_SELF)
		RS.instance_geometry_set_cast_shadows_setting(inst_rid,
			RS.SHADOW_CASTING_SETTING_OFF)
		_active_chunks["%d|%s" % [sp_idx, ck]] = [mm_rid, inst_rid]


func _load_model(sp_name: String) -> Mesh:
	# Try .glb first, then .gltf (mushroom models are .gltf)
	var abs_path := ProjectSettings.globalize_path(
		"res://models/vegetation/%s.glb" % sp_name)
	if not FileAccess.file_exists(abs_path):
		abs_path = ProjectSettings.globalize_path(
			"res://models/vegetation/%s.gltf" % sp_name)
	if not FileAccess.file_exists(abs_path): return null
	var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
	if meshes.is_empty(): return null
	var mesh: Mesh = meshes.values()[0]

	# Find species config. Variant meshes carry a "_<n>" suffix (e.g.
	# "Flower_Goldenrod_0") not present in the SPECIES name ("Flower_Goldenrod"),
	# so match the base name — otherwise variants silently fall back to default
	# material params (no flower color, no fall tint, default stem).
	var cfg_name := sp_name
	var us := sp_name.rfind("_")
	if us != -1 and sp_name.substr(us + 1).is_valid_int():
		cfg_name = sp_name.substr(0, us)
	var sp_cfg: Dictionary = {}
	for sp in SPECIES:
		if sp.name == cfg_name:
			sp_cfg = sp
			break

	# Atlas grid coordinates from species config
	var ai: int = sp_cfg.get("ai", -1)
	var atlas_off := Vector2.ZERO
	var has_atlas := ai >= 0
	if has_atlas:
		var atlas_col: int = ai % ATLAS_COLS
		var atlas_row: int = ai / ATLAS_COLS
		atlas_off = Vector2(float(atlas_col) / ATLAS_COLS, float(atlas_row) / ATLAS_ROWS)

	# Detect embedded PBR textures from 3D meshes.
	var surface_textures: Array = []
	var has_embedded_tex := false
	for si in mesh.get_surface_count():
		var orig_mat = mesh.surface_get_material(si)
		var tex: Texture2D = null
		if orig_mat is StandardMaterial3D:
			tex = orig_mat.albedo_texture
			if tex:
				has_embedded_tex = true
		elif orig_mat != null:
			print("  %s surf %d: material is %s (not StandardMaterial3D)" % [sp_name, si, orig_mat.get_class()])
		surface_textures.append(tex)

	# Apply undergrowth shader per surface
	for si in mesh.get_surface_count():
		var mat := ShaderMaterial.new()
		mat.shader = _shader
		mat.set_shader_parameter("wind_flex", sp_cfg.get("flex", 0.3))
		mat.set_shader_parameter("is_evergreen", float(sp_cfg.get("green", 0)))
		var ft: Array = sp_cfg.get("fall", [0.5, 0.35, 0.08])
		mat.set_shader_parameter("fall_tint", Color(ft[0], ft[1], ft[2]))
		var fc: Array = sp_cfg.get("fc", [0.0, 0.0, 0.0])
		mat.set_shader_parameter("flower_color", Vector3(fc[0], fc[1], fc[2]))
		var bl: Array = sp_cfg.get("bl", [1.0, 2.0])
		mat.set_shader_parameter("bloom_range", Vector2(bl[0], bl[1]))
		var bc: Array = sp_cfg.get("berry", [0.0, 0.0, 0.0])
		mat.set_shader_parameter("berry_color", Vector3(bc[0], bc[1], bc[2]))
		var brg: Array = sp_cfg.get("br", [2.0, 2.9])
		mat.set_shader_parameter("berry_range", Vector2(brg[0], brg[1]))
		mat.set_shader_parameter("roughness_base", sp_cfg.get("rough", 0.82))
		mat.set_shader_parameter("specular_base", sp_cfg.get("spec", 0.04))
		mat.set_shader_parameter("translucency", sp_cfg.get("trans", 0.5))
		mat.set_shader_parameter("leaf_senescence", sp_cfg.get("sen", 0.0))
		mat.set_shader_parameter("stem_use_vtx", sp_cfg.get("stem_vtx", 0.0))
		if sp_cfg.get("stem_vtx", 0.0) > 0.0:
			if _catkin_tex == null:
				_catkin_tex = load("res://models/vegetation/tex_catkin_Wetland_Cattail.png")
			if _catkin_tex:
				mat.set_shader_parameter("catkin_tex", _catkin_tex)
		var sc: Array = sp_cfg.get("sc", [0.30, 0.25, 0.15])
		mat.set_shader_parameter("stem_color", Color(sc[0], sc[1], sc[2]))
		mat.set_shader_parameter("stem_roughness", sp_cfg.get("sr", 0.92))
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		if _loader._canopy_texture:
			mat.set_shader_parameter("canopy_map", _loader._canopy_texture)

		if has_embedded_tex and si < surface_textures.size() and surface_textures[si]:
			mat.set_shader_parameter("use_texture", 1.0)
			mat.set_shader_parameter("albedo_tex", surface_textures[si])
			mat.set_shader_parameter("use_atlas", 0.0)
		elif _leaf_atlas and has_atlas:
			mat.set_shader_parameter("use_texture", 0.0)
			mat.set_shader_parameter("leaf_atlas", _leaf_atlas)
			mat.set_shader_parameter("atlas_offset", atlas_off)
			mat.set_shader_parameter("atlas_cell_size", Vector2(1.0 / ATLAS_COLS, 1.0 / ATLAS_ROWS))
			mat.set_shader_parameter("use_atlas", 1.0)
		mesh.surface_set_material(si, mat)
	return mesh
