@tool
extends SceneTree
## Headless script: bakes landuse_map + structure_mask + shore_distance into
## Terrain3D control maps. Run with:
##   godot --headless -s scripts/bake_terrain3d_control.gd
##
## Texture slot allocation:
##   0 = grass          5 = asphalt       10 = leaf_litter
##   1 = meadow         6 = concrete      11 = flagstone
##   2 = rock           7 = paving        12 = wet_earth
##   3 = dirt           8 = gravel        13 = sparse_grass
##   4 = shore          9 = wood

const WORLD_SIZE := 5000.0
const HALF := WORLD_SIZE / 2.0
const ATLAS_RES := 8192
const CELL := WORLD_SIZE / float(ATLAS_RES)  # ~0.61m

# Terrain3D config — must match import_terrain3d.gd
const VERTEX_SPACING := 0.6104
const REGION_SIZE := 1024  # vertices per region side

# Texture slot IDs
const TEX_GRASS        := 0
const TEX_MEADOW       := 1
const TEX_ROCK         := 2
const TEX_DIRT         := 3
const TEX_SHORE        := 4
const TEX_ASPHALT      := 5
const TEX_CONCRETE     := 6
const TEX_PAVING       := 7
const TEX_GRAVEL       := 8
const TEX_WOOD         := 9
const TEX_LEAF_LITTER  := 10
const TEX_FLAGSTONE    := 11
const TEX_WET_EARTH    := 12
const TEX_SPARSE_GRASS := 13

# Landuse zone → texture slot
# All 14 texture slots registered in terrain_assets.tres
const ZONE_TO_TEX := {
	0:  TEX_GRASS,    # unzoned
	1:  TEX_GRASS,    # garden (formal lawn)
	2:  TEX_GRASS,    # grass
	3:  TEX_GRASS,    # pitch
	4:  TEX_DIRT,     # playground
	5:  TEX_GRASS,    # nature reserve
	6:  TEX_DIRT,     # dog park
	7:  TEX_GRASS,    # sports
	8:  TEX_CONCRETE, # pool
	9:  TEX_DIRT,     # track (cinder)
	10: TEX_LEAF_LITTER,  # wood (forest floor)
	11: TEX_LEAF_LITTER,  # forest (dense canopy → leaf litter)
	12: TEX_GRASS,    # water (hole, but fallback to grass)
	13: TEX_SHORE,    # shore
}

# Zone → terrain color tint (multiplicative on texture albedo).
# Aligns with grass_particle_render.gdshader zone palettes so terrain
# surface matches grass roots. The grass shader samples color_maps at
# particle positions, so these tints feed directly into root blending.
# Alpha = 0.5 = neutral roughness modifier for Terrain3D color map.
const ZONE_TO_COLOR := {
	0:  Color(0.92, 1.00, 1.06, 0.5),  # unzoned: cool blue-green
	1:  Color(0.93, 0.97, 0.95, 0.5),  # garden: deep emerald
	2:  Color(1.08, 1.02, 0.86, 0.5),  # grass: warm golden
	3:  Color(0.97, 1.04, 0.96, 0.5),  # pitch: bright formal green
	4:  Color(1.04, 0.98, 0.90, 0.5),  # playground: sandy warm
	5:  Color(0.88, 0.90, 0.86, 0.5),  # nature_reserve: dark cool shade
	6:  Color(1.02, 0.96, 0.88, 0.5),  # dog_park: worn earth
	7:  Color(0.93, 1.03, 1.01, 0.5),  # sports: lush cool green
	8:  Color(1.00, 1.00, 1.00, 0.5),  # pool: neutral concrete
	9:  Color(1.06, 0.96, 0.86, 0.5),  # track: warm cinder
	10: Color(0.86, 0.84, 0.78, 0.5),  # wood: brown-green understory
	11: Color(0.84, 0.82, 0.76, 0.5),  # forest: darker brown understory
	12: Color(1.00, 1.00, 1.00, 0.5),  # water: neutral
	13: Color(0.98, 0.94, 0.88, 0.5),  # shore: sandy warm
}

# Structure mask values → texture slot
const STRUCT_FLAT  := TEX_FLAGSTONE   # plazas, terraces
const STRUCT_SLOPE := TEX_CONCRETE

var _terrain: Terrain3D
var _landuse_img: Image
var _structure_img: Image
var _shore_img: Image
var _park_mask_img: Image
var _atlas_data := PackedByteArray()  # world_atlas.bin RG8 — R = surface type
var _frame := 0

# Terrain hole polygons — structures where terrain must be invisible.
# Points in world XZ coordinates (same as park_data.json).
const HOLE_POLYGONS := [
	{
		"name": "Bethesda Terrace",
		"points": [
			Vector2(-454.4, 1019.5), Vector2(-459.5, 1018.0), Vector2(-493.6, 1008.0),
			Vector2(-499.0, 1006.4), Vector2(-497.6, 1001.6), Vector2(-496.2, 997.0),
			Vector2(-491.0, 998.5), Vector2(-486.9, 999.7), Vector2(-485.5, 1001.1),
			Vector2(-483.8, 995.4), Vector2(-472.7, 998.7), Vector2(-462.2, 1001.8),
			Vector2(-457.3, 1009.2), Vector2(-451.8, 1010.8), Vector2(-453.1, 1015.2),
		],
	},
]

func _init() -> void:
	print("=== Baking Terrain3D control maps ===")

func _process(_delta: float) -> bool:
	_frame += 1
	if _frame == 1:
		# Frame 1: load data maps and create Terrain3D
		_landuse_img = _load_grayscale("res://landuse_map.png")
		_structure_img = _load_grayscale("res://lidar_data/structure_mask.png")
		_shore_img = _load_grayscale("res://shore_distance.png")
		_park_mask_img = _load_grayscale("res://boundary_mask.png")

		if not _landuse_img:
			push_error("Cannot load landuse_map.png")
			quit(1)
			return false
		if not _structure_img:
			push_warning("structure_mask.png not found — structures will use default grass")

		# World atlas surface types (convert_to_godot.py): cells the targeted
		# rock outcrop restoration marked as type 7 must bake as rock — the
		# domes are too smooth for the slope autoshader to ever rock them
		# (walk-around 2026-06-12 cpw_000: grass-skinned "green mounds").
		var afh := FileAccess.open("res://world_atlas.bin", FileAccess.READ)
		if afh:
			var aw := afh.get_32()
			var ah := afh.get_32()
			if aw == ATLAS_RES and ah == ATLAS_RES:
				_atlas_data = afh.get_buffer(aw * ah * 2)
			else:
				push_warning("world_atlas.bin is %dx%d, expected %d — rock outcrops not baked" % [aw, ah, ATLAS_RES])
			afh.close()
		else:
			push_warning("world_atlas.bin not found — rock outcrops not baked")

		_terrain = Terrain3D.new()
		get_root().add_child(_terrain)
		_terrain.region_size = Terrain3D.SIZE_1024
		_terrain.vertex_spacing = VERTEX_SPACING
		_terrain.data_directory = "res://data/terrain3d/"
		return false

	elif _frame == 5:
		# Frame 5: Terrain3D data should be loaded, run bake
		_do_bake()

	return false


func _point_in_polygon(p: Vector2, poly: Array) -> bool:
	## Raycasting point-in-polygon test.
	var inside := false
	var n := poly.size()
	var j := n - 1
	for i in range(n):
		var pi: Vector2 = poly[i]
		var pj: Vector2 = poly[j]
		if ((pi.y > p.y) != (pj.y > p.y)) and \
			(p.x < (pj.x - pi.x) * (p.y - pi.y) / (pj.y - pi.y) + pi.x):
			inside = not inside
		j = i
	return inside


func _build_hole_mask() -> PackedByteArray:
	## Precompute an atlas-resolution bitmask for terrain hole polygons.
	## Returns empty array if no holes defined.
	if HOLE_POLYGONS.is_empty():
		return PackedByteArray()
	# Find bounding box of all polygons to avoid scanning entire 8192x8192
	var mask := PackedByteArray()
	mask.resize(ATLAS_RES * ATLAS_RES)
	mask.fill(0)
	for hole in HOLE_POLYGONS:
		var pts: Array = hole.points
		# Compute AABB in atlas pixels
		var xmin := 99999.0; var xmax := -99999.0
		var zmin := 99999.0; var zmax := -99999.0
		for pt: Vector2 in pts:
			xmin = minf(xmin, pt.x); xmax = maxf(xmax, pt.x)
			zmin = minf(zmin, pt.y); zmax = maxf(zmax, pt.y)
		# Convert world bounds to atlas pixel bounds (with 2-cell margin)
		var ax0 := maxi(int((xmin + HALF) / WORLD_SIZE * ATLAS_RES) - 2, 0)
		var ax1 := mini(int((xmax + HALF) / WORLD_SIZE * ATLAS_RES) + 2, ATLAS_RES - 1)
		var az0 := maxi(int((zmin + HALF) / WORLD_SIZE * ATLAS_RES) - 2, 0)
		var az1 := mini(int((zmax + HALF) / WORLD_SIZE * ATLAS_RES) + 2, ATLAS_RES - 1)
		var hole_pixels := 0
		for az in range(az0, az1 + 1):
			var wz: float = float(az) / float(ATLAS_RES) * WORLD_SIZE - HALF
			for ax in range(ax0, ax1 + 1):
				var wx: float = float(ax) / float(ATLAS_RES) * WORLD_SIZE - HALF
				if _point_in_polygon(Vector2(wx, wz), pts):
					mask[az * ATLAS_RES + ax] = 1
					hole_pixels += 1
		print("  Hole '%s': %d pixels" % [hole.name, hole_pixels])
	return mask


func _do_bake() -> void:
	var terrain := _terrain
	var landuse_img := _landuse_img
	var structure_img := _structure_img
	var shore_img := _shore_img
	var park_mask_img := _park_mask_img

	if not terrain.data:
		push_error("Terrain3D data not loaded")
		quit(1)
		return

	print("Terrain3D loaded: %d regions" % terrain.data.get_region_count())

	# Precompute terrain hole mask (structure polygons that carve through terrain)
	var hole_mask := _build_hole_mask()

	# Iterate over all regions and set control map data
	var regions_updated := 0
	var pixels_set := 0

	for region_idx in range(terrain.data.get_region_count()):
		var region_loc: Vector2i = terrain.data.get_region_locations()[region_idx]
		# Region world origin (in Terrain3D vertex space)
		var region_origin_x: float = float(region_loc.x) * REGION_SIZE * VERTEX_SPACING
		var region_origin_z: float = float(region_loc.y) * REGION_SIZE * VERTEX_SPACING

		for lz in range(REGION_SIZE):
			for lx in range(REGION_SIZE):
				# World position
				var wx: float = region_origin_x + float(lx) * VERTEX_SPACING
				var wz: float = region_origin_z + float(lz) * VERTEX_SPACING

				# Atlas pixel coordinates
				var ax: int = int((wx + HALF) / WORLD_SIZE * ATLAS_RES)
				var az: int = int((wz + HALF) / WORLD_SIZE * ATLAS_RES)
				ax = clampi(ax, 0, ATLAS_RES - 1)
				az = clampi(az, 0, ATLAS_RES - 1)

				# Read data maps
				var zone_id: int = _pixel_val(landuse_img, ax, az)
				var struct_val: int = _pixel_val(structure_img, ax, az)
				var shore_val: float = _pixel_valf(shore_img, ax, az) if shore_img else 0.0
				var park_val: float = _pixel_valf(park_mask_img, ax, az) if park_mask_img else 1.0

				var pos := Vector3(wx, 0, wz)
				var zone_color: Color = ZONE_TO_COLOR.get(zone_id, Color(1.0, 1.0, 1.0, 0.5))

				# Structure holes (Bethesda Terrace etc.) — terrain invisible here
				if not hole_mask.is_empty() and hole_mask[az * ATLAS_RES + ax] > 0:
					terrain.data.set_control(pos, _encode_control(TEX_GRASS, TEX_ROCK, 0.0, false, true))
					terrain.data.set_color(pos, zone_color)
					pixels_set += 1
					continue

				# Determine base texture and overlay
				var base_id: int = TEX_GRASS
				var over_id: int = TEX_ROCK  # default overlay for autoshader
				var blend: float = 0.0
				var use_auto: bool = true

				# Outside park boundary → concrete (city sidewalk/road)
				if park_val < 0.5:
					base_id = TEX_CONCRETE
					zone_color = Color(0.85, 0.85, 0.87, 0.5)
					use_auto = false
				# Water zone → mark as hole
				elif zone_id == 12:
					# Set hole bit — Terrain3D handles water separately
					terrain.data.set_control(pos, _encode_control(TEX_GRASS, TEX_ROCK, 0.0, false, true))
					terrain.data.set_color(pos, zone_color)
					pixels_set += 1
					continue
				# Structure detected (LiDAR) — only strong detections
				elif struct_val > 16 and park_val > 0.5:
					base_id = STRUCT_FLAT
					zone_color = Color(1.0, 1.0, 1.0, 0.5)
					use_auto = false
				# Rock outcrop (world atlas type 7 — DSM-restored schist).
				# Before shore: real outcrops (e.g. Hernshead) run into the
				# lake and should stay rock, not mud. Census of all 1154
				# clusters: scripts/rock_outcrop_census.py.
				elif not _atlas_data.is_empty() and _atlas_data[(az * ATLAS_RES + ax) * 2] == 7:
					base_id = TEX_ROCK
					over_id = TEX_ROCK
					zone_color = Color(0.95, 0.95, 0.97, 0.5)
					use_auto = false
				# Shore zone — blend shore/wet_earth with base texture
				elif zone_id == 13 or (shore_val > 0.0 and shore_val < 0.5):
					var shore_dist_m: float = shore_val * 30.0
					if shore_dist_m < 15.0:
						blend = clampf(1.0 - shore_dist_m / 15.0, 0.0, 1.0)
						base_id = ZONE_TO_TEX.get(zone_id, TEX_GRASS)
						# Woodland shores → wet earth; open shores → muddy shore
						if zone_id == 10 or zone_id == 11:
							over_id = TEX_WET_EARTH
						else:
							over_id = TEX_SHORE
						use_auto = false
					else:
						base_id = ZONE_TO_TEX.get(zone_id, TEX_GRASS)
				else:
					base_id = ZONE_TO_TEX.get(zone_id, TEX_GRASS)
					# Woodland/forest: disable autoshader (want leaf litter, not rock)
					if zone_id == 10 or zone_id == 11:
						use_auto = false

				terrain.data.set_control(pos, _encode_control(base_id, over_id, blend, use_auto, false))
				terrain.data.set_color(pos, zone_color)
				pixels_set += 1

		regions_updated += 1
		if regions_updated % 8 == 0:
			print("  %d / %d regions..." % [regions_updated, terrain.data.get_region_count()])

	print("Control map: %d pixels set across %d regions" % [pixels_set, regions_updated])

	# Save
	terrain.data.save_directory("res://data/terrain3d/")
	print("Saved to res://data/terrain3d/")
	quit()


func _encode_control(base_id: int, over_id: int, blend: float, auto: bool, hole: bool) -> float:
	## Encode control map uint32 in Terrain3D format.
	var ctrl: int = 0
	ctrl |= (base_id & 0x1F) << 27
	ctrl |= (over_id & 0x1F) << 22
	ctrl |= (int(blend * 255.0 + 0.5) & 0xFF) << 14
	if auto:
		ctrl |= 0x1
	if hole:
		ctrl |= 0x4
	# Return as float (Terrain3D stores control as float-encoded uint32)
	return _uint_to_float(ctrl)


static func _uint_to_float(v: int) -> float:
	var ba := PackedByteArray()
	ba.resize(4)
	ba.encode_u32(0, v)
	return ba.decode_float(0)


func _load_grayscale(path: String) -> Image:
	if not FileAccess.file_exists(path):
		push_warning("Missing: " + path)
		return null
	var img := Image.new()
	var err := img.load(path)
	if err != OK:
		push_warning("Failed to load: " + path)
		return null
	img.convert(Image.FORMAT_L8)
	print("  Loaded %s (%dx%d)" % [path, img.get_width(), img.get_height()])
	return img


func _pixel_val(img: Image, x: int, y: int) -> int:
	if not img or x < 0 or x >= img.get_width() or y < 0 or y >= img.get_height():
		return 0
	return int(img.get_pixel(x, y).r * 255.0 + 0.5)


func _pixel_valf(img: Image, x: int, y: int) -> float:
	if not img or x < 0 or x >= img.get_width() or y < 0 or y >= img.get_height():
		return 0.0
	return img.get_pixel(x, y).r


func get_process_frames(n: int) -> void:
	for i in n:
		await create_timer(0.1).timeout
