## Landmark builder — named Central Park structures and buildings.

var _loader



func _init(loader) -> void:
	_loader = loader



# ---------------------------------------------------------------------------
# Bethesda Terrace — data-measured model, verified coordinate mapping
# ---------------------------------------------------------------------------
func _build_bethesda_terrace() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_bethesda_terrace.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Bethesda Terrace: GLB not found, skipping")
		return

	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		print("WARNING: failed to load Bethesda Terrace GLB")
		return

	# Solved analytically from 2 stalagmite wall peaks in heightmap:
	#   West parapet: (-484, 997) h=26.4
	#   East parapet: (-462, 1004) h=26.5
	# tx = midpoint X = -473, tz = midpoint Z = 1000.5
	# rotation = atan2(3.5, -11) = PI - 0.308 = 2.834
	# wall spacing = 23.1m → ARCADE_W = 22m
	var tx := -473.0
	var tz := 1000.5
	# Sample terrain OUTSIDE the collision carve zone (Z:[968,1005])
	# Upper terrace at Z=1010 is outside carve zone and at road level (23.6m)
	var upper_h: float = _loader._terrain_y(tx, 1010.0)
	var ty: float = upper_h - 6.0  # model origin = arcade floor = upper - level_drop

	root.position = Vector3(tx, ty, tz)
	root.rotation.y = 2.834  # from wall peak positions, NOT assumed PI
	root.name = "BethesdaTerrace"

	# Debug: print where model walls map to in world space
	var ct := cos(2.834)
	var st := sin(2.834)
	# half_arc + WALL_T/2 = 11 + 0.4 = 11.4 (Blender X of wall centers)
	var a := 11.4
	print("  WEST WALL: world (%.1f, %.1f) — target stalagmite (-484, 997)" % [
		tx + a * ct, tz - a * st])
	print("  EAST WALL: world (%.1f, %.1f) — target stalagmite (-462, 1004)" % [
		tx - a * ct, tz + a * st])
	# South edge: Blender (0, +29, 0) → GLTF (0, 0, -29)
	# world X = tx + (-29)*sin(θ), world Z = tz + (-29)*cos(θ)
	var south_d := 29.0
	print("  SOUTH EDGE: world (%.1f, %.1f)" % [
		tx - south_d * st, tz - south_d * ct])
	# North edge: Blender (0, -20, 0) → GLTF (0, 0, +20)
	var north_d := 20.0
	print("  NORTH EDGE: world (%.1f, %.1f)" % [
		tx + north_d * st, tz + north_d * ct])

	# Apply stone material to all mesh surfaces
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")

	# Material lookup by Blender material name
	var mat_map: Dictionary = {}
	mat_map["Sandstone"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.72, 0.65, 0.52))
	mat_map["Brownstone"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.42, 0.32, 0.24))
	mat_map["VaultTile"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.82, 0.72, 0.55))
	mat_map["StairStone"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.60, 0.56, 0.48))
	# Default sandstone fallback
	var default_mat: Material = mat_map["Sandstone"]

	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					var surf_mat := mi.mesh.surface_get_material(si)
					var applied := false
					if surf_mat:
						var mname: String = surf_mat.resource_name
						for key in mat_map:
							if mname.contains(key):
								mi.mesh.surface_set_material(si, mat_map[key])
								applied = true
								break
					if not applied:
						mi.mesh.surface_set_material(si, default_mat)
		for c in n.get_children():
			stack.append(c)

	_loader.add_child(root)

	# Arcade walkthrough collision — walls, floor, and ceiling as box shapes.
	# Arcade is ~22m wide (wall-to-wall), ~10m long (N-S), ~5m tall.
	# Aligned to model rotation (2.834 rad).
	var arcade_body := StaticBody3D.new()
	arcade_body.name = "BethesdaArcadeCollision"
	arcade_body.position = Vector3(tx, ty, tz)
	arcade_body.rotation.y = 2.834

	# Floor: flat box at arcade level
	var floor_shape := BoxShape3D.new()
	floor_shape.size = Vector3(22.0, 0.3, 10.0)
	var floor_col := CollisionShape3D.new()
	floor_col.shape = floor_shape
	floor_col.position = Vector3(0, -0.15, 0)
	arcade_body.add_child(floor_col)

	# Ceiling: flat box at vault top (~5m above floor)
	var ceil_shape := BoxShape3D.new()
	ceil_shape.size = Vector3(22.0, 0.3, 10.0)
	var ceil_col := CollisionShape3D.new()
	ceil_col.shape = ceil_shape
	ceil_col.position = Vector3(0, 5.15, 0)
	arcade_body.add_child(ceil_col)

	# West wall
	var west_shape := BoxShape3D.new()
	west_shape.size = Vector3(0.8, 5.0, 10.0)
	var west_col := CollisionShape3D.new()
	west_col.shape = west_shape
	west_col.position = Vector3(-11.4, 2.5, 0)
	arcade_body.add_child(west_col)

	# East wall
	var east_shape := BoxShape3D.new()
	east_shape.size = Vector3(0.8, 5.0, 10.0)
	var east_col := CollisionShape3D.new()
	east_col.shape = east_shape
	east_col.position = Vector3(11.4, 2.5, 0)
	arcade_body.add_child(east_col)

	_loader.add_child(arcade_body)
	print("ParkLoader: Bethesda Terrace placed at (%.0f, %.1f, %.0f) with arcade collision" % [tx, ty, tz])

	# Bethesda Fountain — photogrammetry model at fountain center
	_build_bethesda_fountain(ty)


func _build_bethesda_fountain(terrace_floor_y: float) -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/bethesda_fountain_photogrammetry.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Bethesda Fountain: photogrammetry GLB not found, skipping")
		return

	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		print("WARNING: failed to load Bethesda Fountain GLB")
		return

	# Position from park_data.json OSM amenity data
	var fx := -457.28
	var fz := 948.97
	# Fountain sits on the lower terrace floor (same elevation as arcade floor)
	var fy: float = _loader._terrain_y(fx, fz)
	# Use lower terrace elevation if terrain query returns upper terrace height
	# (the terrain hole means Terrain3D may return 0). Use terrace floor as fallback.
	if fy < 1.0 or fy > 25.0:
		fy = terrace_floor_y

	root.position = Vector3(fx, fy, fz)
	root.name = "BethesdaFountain"

	_loader.add_child(root)
	print("ParkLoader: Bethesda Fountain placed at (%.0f, %.1f, %.0f)" % [fx, fy, fz])


# ---------------------------------------------------------------------------
# Belvedere Castle — Victorian folly on Vista Rock
# ---------------------------------------------------------------------------
func _build_belvedere_castle() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_belvedere_castle.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Belvedere Castle: GLB not found, skipping")
		return

	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		print("WARNING: failed to load Belvedere Castle GLB")
		return

	# Belvedere Castle sits on Vista Rock at approximately (0, ?, 525)
	var cx := 0.0
	var cz := 525.0
	var cy: float = _loader._terrain_y(cx, cz)

	# The castle faces south (toward the Turtle Pond and Great Lawn).
	# Blender +Y = south → glTF -Z. Park +Z = south. Rotate 180° around Y.
	root.position = Vector3(cx, cy, cz)
	root.rotation.y = PI
	root.name = "BelvedereCastle"

	# Apply stone material to all surfaces
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")

	var mat_map: Dictionary = {}
	mat_map["Schist"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.38, 0.36, 0.33))
	mat_map["Granite"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.52, 0.50, 0.46))
	mat_map["Slate"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.30, 0.28, 0.26))
	var default_mat: Material = mat_map["Schist"]

	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					var surf_mat := mi.mesh.surface_get_material(si)
					var applied := false
					if surf_mat:
						var mname: String = surf_mat.resource_name
						for key in mat_map:
							if mname.contains(key):
								mi.mesh.surface_set_material(si, mat_map[key])
								applied = true
								break
					if not applied:
						mi.mesh.surface_set_material(si, default_mat)
		for c in n.get_children():
			stack.append(c)

	_loader.add_child(root)
	print("ParkLoader: Belvedere Castle placed at (%.0f, %.1f, %.0f)" % [cx, cy, cz])


# ---------------------------------------------------------------------------
# Comfort stations — small stone restroom buildings at 30 OSM toilet locations
# ---------------------------------------------------------------------------
func _build_comfort_stations(amenities: Array) -> void:
	# Load comfort station GLB model
	var cs_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_comfort_station.glb")
	if cs_mesh == null:
		print("  Comfort stations: GLB not found, skipping")
		return

	# Apply stone material
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.58, 0.54, 0.48))
	for si in range(cs_mesh.get_surface_count()):
		cs_mesh.surface_set_material(si, stone_mat)

	var xforms: Array = []
	for am in amenities:
		if am.get("type", "") != "toilets":
			continue
		var pos: Array = am.get("position", [])
		if pos.size() < 3:
			continue
		var x: float = pos[0]
		var z: float = pos[2]
		if not _loader._in_boundary(x, z):
			continue
		var y: float = _loader._terrain_y(x, z)
		# Random rotation from position hash for variety
		var rot := fmod(absf(x * 73.17 + z * 137.29), TAU)
		var basis := Basis(Vector3.UP, rot)
		xforms.append(Transform3D(basis, Vector3(x, y, z)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(cs_mesh, null, xforms, "ComfortStations")
	print("  Comfort stations: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Vanderbilt Gate — ornamental iron gate at Conservatory Garden entrance
# ---------------------------------------------------------------------------
func _build_vanderbilt_gate() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_vanderbilt_gate.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Vanderbilt Gate: GLB not found, skipping")
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	# Gate at Conservatory Garden entrance — east side, 105th St
	var gx := 1063.0
	var gz := -1088.0
	var gy: float = _loader._terrain_y(gx, gz)
	root.position = Vector3(gx, gy, gz)
	root.rotation.y = PI * 0.5  # Faces west into garden
	root.name = "VanderbiltGate"
	# Apply iron material to gate parts, stone to piers
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.58, 0.55, 0.50))
	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					mi.mesh.surface_set_material(si, stone_mat)
		for c in n.get_children():
			stack.append(c)
	_loader.add_child(root)
	print("  Vanderbilt Gate placed at (%.0f, %.1f, %.0f)" % [gx, gy, gz])


# ---------------------------------------------------------------------------
# Naumburg Bandshell — Neoclassical concert stage on the Mall
# ---------------------------------------------------------------------------
func _build_bandshell() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_bandshell.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Bandshell: GLB not found, skipping")
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var bx := -473.0
	var bz := 1131.0
	var by: float = _loader._terrain_y(bx, bz)
	root.position = Vector3(bx, by, bz)
	root.rotation.y = PI  # Shell faces south toward Mall
	root.name = "NaumburgBandshell"
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.68, 0.64, 0.58))
	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					mi.mesh.surface_set_material(si, stone_mat)
		for c in n.get_children():
			stack.append(c)
	_loader.add_child(root)
	print("  Bandshell placed at (%.0f, %.1f, %.0f)" % [bx, by, bz])


# ---------------------------------------------------------------------------
# Conservatory Garden pergola — wisteria pergola in the North Garden
# ---------------------------------------------------------------------------
func _build_pergola() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_pergola.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Pergola: GLB not found, skipping")
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	# Pergola in the North Garden of Conservatory Garden
	var px := 1100.0
	var pz := -1200.0
	var py: float = _loader._terrain_y(px, pz)
	root.position = Vector3(px, py, pz)
	root.rotation.y = PI * 0.15  # Slightly angled to garden axis
	root.name = "WisteriaPergola"
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.65, 0.60, 0.54))
	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					mi.mesh.surface_set_material(si, stone_mat)
		for c in n.get_children():
			stack.append(c)
	_loader.add_child(root)
	print("  Pergola placed at (%.0f, %.1f, %.0f)" % [px, py, pz])


# ---------------------------------------------------------------------------
# Ladies' Pavilion — Victorian cast-iron gazebo on the Lake shore
# ---------------------------------------------------------------------------
func _build_ladies_pavilion() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_ladies_pavilion.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Ladies' Pavilion: GLB not found, skipping")
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var lx := -636.0
	var lz := 578.0
	var ly: float = _loader._terrain_y(lx, lz)
	root.position = Vector3(lx, ly, lz)
	root.rotation.y = PI * 0.3
	root.name = "LadiesPavilion"
	_loader.add_child(root)
	print("  Ladies' Pavilion placed at (%.0f, %.1f, %.0f)" % [lx, ly, lz])


# ---------------------------------------------------------------------------
# Cherry Hill Fountain — Victorian ornamental fountain
# ---------------------------------------------------------------------------
func _build_cherry_hill_fountain() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_cherry_hill_fountain.glb")
	if not FileAccess.file_exists(glb_path):
		print("  Cherry Hill Fountain: GLB not found, skipping")
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var cx := -615.9
	var cz := 906.9
	var cy: float = _loader._terrain_y(cx, cz)
	root.position = Vector3(cx, cy, cz)
	root.name = "CherryHillFountain"
	_loader.add_child(root)
	print("  Cherry Hill Fountain placed at (%.0f, %.1f, %.0f)" % [cx, cy, cz])


# ---------------------------------------------------------------------------
# Summerhouse at the Dene — small rustic stone shelter
# ---------------------------------------------------------------------------
func _build_summerhouse() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_summerhouse.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var sx := -372.0
	var sz := 1433.0
	var sy: float = _loader._terrain_y(sx, sz)
	root.position = Vector3(sx, sy, sz)
	root.rotation.y = PI
	root.name = "SummerhouseDene"
	_loader.add_child(root)
	print("  Summerhouse placed at (%.0f, %.1f, %.0f)" % [sx, sy, sz])


# ---------------------------------------------------------------------------
# Kerbs Model Boathouse — small pavilion at Conservatory Water
# ---------------------------------------------------------------------------
func _build_model_boathouse() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_model_boathouse.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	# West shore of Conservatory Water
	var mx := -190.0
	var mz := 960.0
	var my: float = _loader._terrain_y(mx, mz)
	root.position = Vector3(mx, my, mz)
	root.rotation.y = PI * 0.5  # Faces east toward water
	root.name = "KerbsModelBoathouse"
	_loader.add_child(root)
	print("  Model Boathouse placed at (%.0f, %.1f, %.0f)" % [mx, my, mz])


# ---------------------------------------------------------------------------
# Boat landings — wooden docks on the Lake shore
# ---------------------------------------------------------------------------
func _build_boat_landings() -> void:
	var dock_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_boat_landing.glb")
	if dock_mesh == null:
		return
	var dock_positions: Array = [
		[-688.0, 593.0, PI * 0.7],   # Hernshead
		[-692.0, 770.0, PI * 0.5],   # Western Shore
		[-669.0, 895.0, PI * 0.4],   # Wagner Cove
	]
	var xforms: Array = []
	for dock in dock_positions:
		var dx: float = dock[0]
		var dz: float = dock[1]
		var dr: float = dock[2]
		var dy: float = _loader._terrain_y(dx, dz)
		var basis := Basis(Vector3.UP, dr)
		xforms.append(Transform3D(basis, Vector3(dx, dy, dz)))
	if not xforms.is_empty():
		_loader._spawn_multimesh(dock_mesh, null, xforms, "BoatLandings")
	print("  Boat landings: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Cop Cot — rustic timber shelter on rocky knoll overlooking the Lake
# ---------------------------------------------------------------------------
func _build_cop_cot() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_cop_cot.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	# Cop Cot sits on a rocky knoll southwest of the Lake
	var cx := -750.0
	var cz := 930.0
	var cy: float = _loader._terrain_y(cx, cz)
	root.position = Vector3(cx, cy, cz)
	root.rotation.y = PI * 0.8
	root.name = "CopCot"
	_loader.add_child(root)
	print("  Cop Cot placed at (%.0f, %.1f, %.0f)" % [cx, cy, cz])


# ---------------------------------------------------------------------------
# Imagine mosaic — Strawberry Fields memorial
# ---------------------------------------------------------------------------
func _build_imagine_mosaic() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_imagine_mosaic.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var ix := -787.4
	var iz := 826.8
	var iy: float = _loader._terrain_y(ix, iz) + 0.02  # Flush with ground
	root.position = Vector3(ix, iy, iz)
	root.name = "ImagineMosaic"
	_loader.add_child(root)
	print("  Imagine mosaic placed at (%.0f, %.1f, %.0f)" % [ix, iy, iz])


# ---------------------------------------------------------------------------
# Tennis House — Tudor Revival building at the Tennis Center
# ---------------------------------------------------------------------------
func _build_tennis_house() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_tennis_house.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var tx := 297.0
	var tz := -721.0
	var ty: float = _loader._terrain_y(tx, tz)
	root.position = Vector3(tx, ty, tz)
	root.rotation.y = PI
	root.name = "TennisHouse"
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.52, 0.28, 0.20))
	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					mi.mesh.surface_set_material(si, stone_mat)
		for c in n.get_children():
			stack.append(c)
	_loader.add_child(root)
	print("  Tennis House placed at (%.0f, %.1f, %.0f)" % [tx, ty, tz])


# ---------------------------------------------------------------------------
# 79th Street Maintenance Yard
# ---------------------------------------------------------------------------
func _build_maintenance_yard() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_maintenance_yard.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	var mx := -476.0
	var mz := 266.0
	var my: float = _loader._terrain_y(mx, mz)
	root.position = Vector3(mx, my, mz)
	root.rotation.y = PI * 0.5
	root.name = "MaintenanceYard"
	_loader.add_child(root)
	print("  Maintenance Yard placed at (%.0f, %.1f, %.0f)" % [mx, my, mz])


# ---------------------------------------------------------------------------
# Dana Pier — stone pier at Harlem Meer
# ---------------------------------------------------------------------------
func _build_dana_pier() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_dana_pier.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	# Near Dana Discovery Center, extending into Harlem Meer
	var dx := 420.0
	var dz := -1830.0
	var dy: float = _loader._terrain_y(dx, dz)
	root.position = Vector3(dx, dy, dz)
	root.rotation.y = PI  # Points north into Meer
	root.name = "DanaPier"
	_loader.add_child(root)
	print("  Dana Pier placed at (%.0f, %.1f, %.0f)" % [dx, dy, dz])


# ---------------------------------------------------------------------------
# Stone weirs — low dams along The Loch and other streams
# ---------------------------------------------------------------------------
func _build_stone_weirs() -> void:
	var weir_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_stone_weir.glb")
	if weir_mesh == null:
		return
	# Weir positions along The Loch and other waterfall locations
	var weir_positions: Array = [
		[600.0, -1200.0, PI * 0.3],    # The Loch upper
		[700.0, -1380.0, PI * 0.5],    # The Loch middle
		[850.0, -1480.0, PI * 0.2],    # The Loch lower
		[-600.0, 430.0, PI * 0.7],     # Gill stream
	]
	var xforms: Array = []
	for w in weir_positions:
		var wx: float = w[0]
		var wz: float = w[1]
		var wr: float = w[2]
		var wy: float = _loader._terrain_y(wx, wz)
		var basis := Basis(Vector3.UP, wr)
		xforms.append(Transform3D(basis, Vector3(wx, wy, wz)))
	if not xforms.is_empty():
		_loader._spawn_multimesh(weir_mesh, null, xforms, "StoneWeirs")
	print("  Stone weirs: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Bethesda Terrace Arcade — tiled barrel-vault passage beneath 72nd St
# ---------------------------------------------------------------------------
func _build_bethesda_arcade() -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/furniture/cp_bethesda_arcade.glb")
	if not FileAccess.file_exists(glb_path):
		return
	var root: Node3D = _loader._load_glb_scene(glb_path)
	if root == null:
		return
	# Centered between upper Mall terrace and Bethesda Fountain
	var ax := -480.0
	var az := 1020.0
	var ay: float = _loader._terrain_y(ax, az) - 1.0  # slightly below grade (arcade is sunken)
	root.position = Vector3(ax, ay, az)
	root.rotation.y = PI * 0.05  # slight rotation matching terrace alignment
	root.name = "BethesdaArcade"

	# Apply stone materials — Minton tile vault, sandstone walls, brownstone trim
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var mat_map: Dictionary = {}
	mat_map["Sandstone"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.72, 0.65, 0.52))
	mat_map["Brownstone"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.42, 0.32, 0.24))
	mat_map["VaultTile"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.82, 0.72, 0.55))
	mat_map["StairStone"] = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.60, 0.56, 0.48))
	var default_mat: Material = mat_map["Sandstone"]
	var stack: Array = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				for si in range(mi.mesh.get_surface_count()):
					var surf_mat := mi.mesh.surface_get_material(si)
					var applied := false
					if surf_mat:
						var mname: String = surf_mat.resource_name
						for key in mat_map:
							if mname.contains(key):
								mi.mesh.surface_set_material(si, mat_map[key])
								applied = true
								break
					if not applied:
						mi.mesh.surface_set_material(si, default_mat)
		for c in n.get_children():
			stack.append(c)

	_loader.add_child(root)
	print("  Bethesda Arcade placed at (%.0f, %.1f, %.0f)" % [ax, ay, az])


# ---------------------------------------------------------------------------
# Conservatory Garden fountains — Untermyer + Burnett Memorial
# ---------------------------------------------------------------------------
func _build_conservatory_fountains() -> void:
	# Untermyer Fountain (Three Dancing Maidens) — south/Italian garden
	var u_path := ProjectSettings.globalize_path("res://models/furniture/cp_untermyer_fountain.glb")
	if FileAccess.file_exists(u_path):
		var root: Node3D = _loader._load_glb_scene(u_path)
		if root:
			var ux := 1134.0
			var uz := -1256.0
			var uy: float = _loader._terrain_y(ux, uz)
			root.position = Vector3(ux, uy, uz)
			root.name = "UntermyerFountain"
			_loader.add_child(root)
			print("  Untermyer Fountain placed at (%.0f, %.1f, %.0f)" % [ux, uy, uz])

	# Burnett Memorial Fountain (Secret Garden) — north/English garden
	var b_path := ProjectSettings.globalize_path("res://models/furniture/cp_burnett_fountain.glb")
	if FileAccess.file_exists(b_path):
		var root: Node3D = _loader._load_glb_scene(b_path)
		if root:
			var bx := 1065.0
			var bz := -1134.0
			var by: float = _loader._terrain_y(bx, bz)
			root.position = Vector3(bx, by, bz)
			root.name = "BurnettFountain"
			_loader.add_child(root)
			print("  Burnett Fountain placed at (%.0f, %.1f, %.0f)" % [bx, by, bz])


# ---------------------------------------------------------------------------
# Rustic bridges — log bridges at woodland stream crossings
# ---------------------------------------------------------------------------
func _build_rustic_bridges() -> void:
	var bridge_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_rustic_bridge.glb")
	if bridge_mesh == null:
		return
	# Known rustic bridge locations at stream crossings in woodland areas
	# The Loch (North Woods) — multiple crossings along its 71-point course
	# The Gill (Ramble area) — crossings along cascading streams
	var bridge_positions: Array = [
		[560.0, -1180.0, PI * 0.4],    # The Loch — upper crossing near North Woods
		[650.0, -1300.0, PI * 0.6],    # The Loch — middle crossing
		[750.0, -1420.0, PI * 0.3],    # The Loch — lower crossing near Pool
		[-380.0, 500.0, PI * 0.8],     # The Gill — upper Ramble crossing
		[-420.0, 600.0, PI * 0.5],     # The Gill — lower cascade crossing
		[-500.0, 350.0, PI * 0.6],     # Ramble stream crossing near Azalea Pond
	]
	var xforms: Array = []
	for b in bridge_positions:
		var bx: float = b[0]
		var bz: float = b[1]
		var br: float = b[2]
		var by: float = _loader._terrain_y(bx, bz)
		var basis := Basis(Vector3.UP, br)
		xforms.append(Transform3D(basis, Vector3(bx, by, bz)))
	if not xforms.is_empty():
		_loader._spawn_multimesh(bridge_mesh, null, xforms, "RusticBridges")
	print("  Rustic bridges: %d placed" % xforms.size())
