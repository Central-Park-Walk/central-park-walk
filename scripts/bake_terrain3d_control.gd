@tool
extends SceneTree
## Headless script: bakes landuse_map + structure_mask + shore_distance into
## Terrain3D control maps. Run with:
##   godot --headless -s scripts/bake_terrain3d_control.gd
##
## Texture slot allocation:
##   0 = grass       5 = asphalt
##   1 = meadow      6 = concrete
##   2 = rock        7 = paving
##   3 = dirt        8 = gravel
##   4 = shore       9 = wood

const WORLD_SIZE := 5000.0
const HALF := WORLD_SIZE / 2.0
const ATLAS_RES := 8192
const CELL := WORLD_SIZE / float(ATLAS_RES)  # ~0.61m

# Terrain3D config — must match import_terrain3d.gd
const VERTEX_SPACING := 0.6104
const REGION_SIZE := 1024  # vertices per region side

# Texture slot IDs
const TEX_GRASS    := 0
const TEX_MEADOW   := 1
const TEX_ROCK     := 2
const TEX_DIRT     := 3
const TEX_SHORE    := 4
const TEX_ASPHALT  := 5
const TEX_CONCRETE := 6
const TEX_PAVING   := 7
const TEX_GRAVEL   := 8
const TEX_WOOD     := 9

# Landuse zone → texture slot
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
	10: TEX_MEADOW,   # wood
	11: TEX_MEADOW,   # forest
	12: TEX_GRASS,    # water (hole, but fallback to grass)
	13: TEX_SHORE,    # shore
}

# Structure mask values → texture slot (crude mapping based on slope in shader)
# We'll use asphalt as default for structures, paving for flat areas
const STRUCT_FLAT  := TEX_PAVING
const STRUCT_SLOPE := TEX_CONCRETE

func _init() -> void:
	print("=== Baking Terrain3D control maps ===")

	# Load data maps
	var landuse_img := _load_grayscale("res://landuse_map.png")
	var structure_img := _load_grayscale("res://structure_mask.png")
	var shore_img := _load_grayscale("res://shore_distance.png")
	var park_mask_img := _load_grayscale("res://boundary_mask.png")

	if not landuse_img or not structure_img:
		push_error("Cannot load landuse_map.png or structure_mask.png")
		quit(1)
		return

	# Load existing Terrain3D
	var terrain := Terrain3D.new()
	get_root().add_child(terrain)
	terrain.region_size = Terrain3D.SIZE_1024
	terrain.vertex_spacing = VERTEX_SPACING
	terrain.data_directory = "res://data/terrain3d/"

	# Wait for data to load
	await get_process_frames(3)

	if not terrain.data:
		push_error("Terrain3D data not loaded")
		quit(1)
		return

	print("Terrain3D loaded: %d regions" % terrain.data.get_region_count())

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

				# Determine base texture and overlay
				var base_id: int = TEX_GRASS
				var over_id: int = TEX_ROCK  # default overlay for autoshader
				var blend: float = 0.0
				var use_auto: bool = true

				# Outside park boundary → concrete (city sidewalk/road)
				if park_val < 0.5:
					base_id = TEX_CONCRETE
					use_auto = false
				# Water zone → mark as hole
				elif zone_id == 12:
					# Set hole bit — Terrain3D handles water separately
					var pos := Vector3(wx, 0, wz)
					terrain.data.set_control(pos, _encode_control(TEX_GRASS, TEX_ROCK, 0.0, false, true))
					pixels_set += 1
					continue
				# Structure detected (LiDAR)
				elif struct_val > 1 and park_val > 0.5:
					base_id = TEX_PAVING
					use_auto = false
				# Shore zone — blend shore with grass
				elif zone_id == 13 or (shore_val > 0.0 and shore_val < 0.5):
					var shore_dist_m: float = shore_val * 30.0
					if shore_dist_m < 15.0:
						blend = clampf(1.0 - shore_dist_m / 15.0, 0.0, 1.0)
						base_id = TEX_GRASS
						over_id = TEX_SHORE
						use_auto = false
					else:
						base_id = ZONE_TO_TEX.get(zone_id, TEX_GRASS)
				else:
					base_id = ZONE_TO_TEX.get(zone_id, TEX_GRASS)
					# Woodland/forest: disable autoshader (want meadow, not rock)
					if zone_id == 10 or zone_id == 11:
						use_auto = false

				var pos := Vector3(wx, 0, wz)
				terrain.data.set_control(pos, _encode_control(base_id, over_id, blend, use_auto, false))
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
