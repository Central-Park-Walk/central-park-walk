# water_builder.gd
# Water bodies, fountains, streams, and the Imagine mosaic

var _loader  # Reference to park_loader for shared utilities

func _init(loader) -> void:
	_loader = loader


# ---------------------------------------------------------------------------
# Fountain geometry — builds 3D structures for named fountains
# ---------------------------------------------------------------------------
func _build_fountain(body: Dictionary) -> void:
	var pts: Array = body["points"]
	var bname: String = str(body.get("name", ""))

	# Compute centroid and radius from polygon
	var cx := 0.0; var cz := 0.0
	for pt in pts:
		cx += float(pt[0]); cz += float(pt[1])
	cx /= pts.size(); cz /= pts.size()
	var max_r := 0.0
	for pt in pts:
		var dx := float(pt[0]) - cx; var dz := float(pt[1]) - cz
		max_r = maxf(max_r, sqrt(dx * dx + dz * dz))

	# Sample terrain at all polygon vertices and use the MAX so the rim
	# never sinks below the terrain on any side.
	var base_y: float = _loader._terrain_y(cx, cz)
	for pt in pts:
		base_y = maxf(base_y, _loader._terrain_y(float(pt[0]), float(pt[1])))
	# Fountain water fills to just below the rim lip (rim_h ≈ 0.45 for Bethesda)
	var pool_y := base_y + 0.35

	# Textures for stone basin
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")

	var lname := bname.to_lower()
	_build_fountain_pool(pts, pool_y)

	if lname.contains("bethesda"):
		_build_bethesda_fountain(cx, cz, base_y, max_r, rw_alb, rw_nrm, rw_rgh)

	# Water spray jets — animated GPUParticles3D for fountains with water features
	# Bethesda: tall central jet + ring of smaller jets
	# Sophie Loeb, Cherry Hill, Untermyer: single central spray
	if lname.contains("bethesda"):
		_add_fountain_spray(cx, pool_y, cz, 4.0, 350, 0.8)   # tall main jet
		for ang_i in 8:
			var ang := float(ang_i) * TAU / 8.0
			var jx := cx + cos(ang) * max_r * 0.55
			var jz := cz + sin(ang) * max_r * 0.55
			_add_fountain_spray(jx, pool_y, jz, 1.8, 80, 0.35)  # ring jets
	elif lname.contains("sophie") or lname.contains("cherry") or lname.contains("untermyer") or lname.contains("burnett"):
		_add_fountain_spray(cx, pool_y, cz, 2.5, 200, 0.5)

	# Fountain basin collision — cylinder around the basin
	var ftn_body := StaticBody3D.new()
	ftn_body.name = "Fountain_Collision"
	var cyl := CylinderShape3D.new()
	cyl.radius = max_r * 0.9
	cyl.height = 1.5
	var ftn_col := CollisionShape3D.new()
	ftn_col.shape = cyl
	ftn_body.add_child(ftn_col)
	ftn_body.position = Vector3(cx, base_y + 0.75, cz)
	_loader.add_child(ftn_body)

	print("ParkLoader: built fountain '%s' at (%.0f, %.0f)" % [bname, cx, cz])


func _build_fountain_pool(pts: Array, wy: float) -> void:
	## Render the water polygon for a fountain pool
	var polygon := PackedVector2Array()
	for pt in pts:
		polygon.append(Vector2(float(pt[0]), float(pt[1])))
	var indices := Geometry2D.triangulate_polygon(polygon)
	if indices.is_empty():
		return
	var verts   := PackedVector3Array()
	var normals := PackedVector3Array()
	for i in range(0, indices.size(), 3):
		verts.append(Vector3(polygon[indices[i    ]].x, wy, polygon[indices[i    ]].y))
		verts.append(Vector3(polygon[indices[i + 1]].x, wy, polygon[indices[i + 1]].y))
		verts.append(Vector3(polygon[indices[i + 2]].x, wy, polygon[indices[i + 2]].y))
		for _j in range(3):
			normals.append(Vector3.UP)
	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)
	var wmat := ShaderMaterial.new()
	wmat.shader = _loader._get_shader("water", _water_shader_code())
	_apply_water_wave_textures(wmat)
	if _loader._canopy_texture:
		wmat.set_shader_parameter("canopy_map", _loader._canopy_texture)
		wmat.set_shader_parameter("canopy_world_size", _loader._hm_world_size)
	mesh.surface_set_material(0, wmat)
	_loader.water_materials.append(wmat)
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.name = "FountainPool"
	mi.layers = 2  # water layer — excluded from the planar reflection camera
	_loader.add_child(mi)




func _add_fountain_spray(x: float, y: float, z: float,
						 height: float, amount: int, spread_r: float) -> void:
	## Add a vertical water jet at position (x, y, z).
	## height: max spray height in metres. amount: particle count. spread_r: horizontal spread.
	var particles := GPUParticles3D.new()
	particles.amount = amount
	particles.lifetime = 1.2 + height * 0.15  # taller jets need longer lifetime
	particles.visibility_aabb = AABB(
		Vector3(-spread_r - 1, -0.5, -spread_r - 1),
		Vector3((spread_r + 1) * 2, height + 2, (spread_r + 1) * 2))

	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 8.0 + spread_r * 10.0  # wider spread for smaller jets
	pm.initial_velocity_min = height * 2.0
	pm.initial_velocity_max = height * 2.8
	pm.gravity = Vector3(0, -9.8, 0)  # realistic gravity
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = spread_r * 0.2
	# Damping simulates air resistance on water droplets
	pm.damping_min = 1.0
	pm.damping_max = 3.0
	# Scale: larger drops at base, smaller spray at top
	pm.scale_min = 0.4
	pm.scale_max = 1.0
	particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.06, 0.06)  # small water droplet quads
	particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.75, 0.82, 0.90, 0.35)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.emission_enabled = true
	mat.emission = Color(0.5, 0.55, 0.65)
	mat.emission_energy_multiplier = 0.15
	particles.material_override = mat

	particles.position = Vector3(x, y + 0.1, z)
	particles.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_loader.add_child(particles)


# -- Bethesda Fountain: placeholder for future photogrammetry data --
# The Angel of the Waters statue needs close-range scanning data
# (drone photogrammetry or terrestrial LiDAR) to model accurately.
func _build_bethesda_fountain(cx: float, cz: float, base_y: float, pool_r: float,
							  alb: Texture2D, nrm: Texture2D, rgh: Texture2D) -> void:
	pass  # awaiting proper scan data



# ---------------------------------------------------------------------------
# Strawberry Fields — Imagine Mosaic (circular black & white starburst)
# ---------------------------------------------------------------------------
func _build_imagine_mosaic(cx: float, cy: float, cz: float) -> void:
	## 10.4m diameter disc (34ft) with procedural radial starburst pattern.
	var radius := 5.2
	var segs := 64
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	# Fan triangulation: center + rim
	for i in range(segs):
		var a0 := TAU * float(i) / float(segs)
		var a1 := TAU * float(i + 1) / float(segs)
		verts.append(Vector3(cx, cy + 0.02, cz))
		verts.append(Vector3(cx + radius * cos(a0), cy + 0.02, cz + radius * sin(a0)))
		verts.append(Vector3(cx + radius * cos(a1), cy + 0.02, cz + radius * sin(a1)))
		for _j in 3: normals.append(Vector3.UP)
		uvs.append(Vector2(0.5, 0.5))
		uvs.append(Vector2(0.5 + 0.5 * cos(a0), 0.5 + 0.5 * sin(a0)))
		uvs.append(Vector2(0.5 + 0.5 * cos(a1), 0.5 + 0.5 * sin(a1)))
	var mesh: ArrayMesh = _loader._make_mesh(verts, normals, uvs)
	var mat := ShaderMaterial.new()
	mat.shader = _loader._get_shader("imagine_mosaic", _imagine_mosaic_shader())
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new(); mi.mesh = mesh
	mi.name = "Imagine_Mosaic"
	_loader.add_child(mi)
	# "IMAGINE" label flat on ground
	var lbl := Label3D.new()
	lbl.text = "IMAGINE"
	lbl.font_size = 72
	lbl.pixel_size = 0.012
	lbl.modulate = Color(0.10, 0.10, 0.10, 0.95)
	lbl.outline_size = 0
	lbl.rotation_degrees = Vector3(-90, 0, 0)
	lbl.position = Vector3(cx, cy + 0.03, cz)
	_loader.add_child(lbl)
	print("ParkLoader: Imagine Mosaic at (%.0f, %.0f)" % [cx, cz])


func _imagine_mosaic_shader() -> String:
	return "res://shaders/imagine_mosaic.gdshader"

# ---------------------------------------------------------------------------
# Water bodies – prebaked grids from convert_to_godot.py (fast path)
# Falls back to runtime Geometry2D if water_grids.bin not found
# ---------------------------------------------------------------------------
func _build_water(water: Array) -> void:
	if water.is_empty():
		return

	var verts   := PackedVector3Array()
	var normals := PackedVector3Array()
	var WATER_CELL: float = _loader._hm_world_size / 8192.0  # match atlas resolution

	# --- Try prebaked water grids (eliminates ~244M point-in-polygon tests) ---
	var grids := _load_water_grids()
	if not grids.is_empty():
		_build_water_from_grids(grids, verts, normals, WATER_CELL)
	else:
		push_warning("water_grids.bin not found — falling back to runtime polygon tests (slow)")
		_build_water_runtime(water, verts, normals, WATER_CELL)

	# --- Fountains still use runtime logic (small, fast) ---
	for body in water:
		var bname: String = str(body.get("name", ""))
		if bname.to_lower().contains("fountain"):
			_build_fountain(body)

	# --- Stone coping around formal water bodies ---
	# Central Park's model-boat pond, meer, and turtle pond have dressed stone edges
	var FORMAL_WATER := ["conservatory", "harlem meer", "turtle pond"]
	for body in water:
		var bname: String = str(body.get("name", ""))
		if bname.to_lower().contains("fountain"):
			continue
		for keyword in FORMAL_WATER:
			if bname.to_lower().contains(keyword):
				_build_water_curb(body["points"], Color(0.55, 0.53, 0.50), bname)
				break

	_build_water_mesh(verts, normals, water)


func _load_water_grids() -> Array:
	## Load prebaked water_grids.bin → Array of {bb_min_x, bb_min_z, water_y, nx, nz, poly, inside}
	var fh := FileAccess.open("res://water_grids.bin", FileAccess.READ)
	if not fh:
		return []
	var magic := fh.get_buffer(4)
	if magic.get_string_from_utf8() != "WGRD":
		push_warning("water_grids.bin: bad magic")
		return []
	var count := fh.get_32()
	var bodies: Array = []
	for _i in count:
		var name_len := fh.get_16()
		var bname := fh.get_buffer(name_len).get_string_from_utf8()
		var bb_min_x := fh.get_float()
		var bb_min_z := fh.get_float()
		var water_y := fh.get_float()
		var nx := fh.get_32()
		var nz := fh.get_32()
		var poly_count := fh.get_32()
		var poly := PackedVector2Array()
		for _j in poly_count:
			poly.append(Vector2(fh.get_float(), fh.get_float()))
		var grid_size := (nx + 1) * (nz + 1)
		var inside := fh.get_buffer(grid_size)
		bodies.append({
			"name": bname,
			"bb_min_x": bb_min_x,
			"bb_min_z": bb_min_z,
			"water_y": water_y,
			"nx": nx,
			"nz": nz,
			"poly": poly,
			"inside": inside,
		})
	print("  Water grids: loaded %d bodies from water_grids.bin" % count)
	return bodies


func _build_water_from_grids(grids: Array, verts: PackedVector3Array,
		normals: PackedVector3Array, cell: float) -> void:
	## Build water mesh from prebaked inside/outside grids. No polygon tests needed.
	for grid in grids:
		var bb_x: float = grid["bb_min_x"]
		var bb_z: float = grid["bb_min_z"]
		var wy: float = grid["water_y"]
		var nx: int = grid["nx"]
		var nz: int = grid["nz"]
		var inside: PackedByteArray = grid["inside"]
		var poly: PackedVector2Array = grid["poly"]

		_loader.water_levels.append({
			"bb": Rect2(bb_x, bb_z, float(nx) * cell, float(nz) * cell),
			"wy": wy,
		})

		# Store polygon for water proximity baking (used by grass/tree builders)
		var exp_polygon := PackedVector2Array()
		for pt in poly:
			exp_polygon.append(pt)
		var expanded := Geometry2D.offset_polygon(exp_polygon, 3.0)
		if not expanded.is_empty():
			_loader._water_polygons.append(expanded[0])
		else:
			_loader._water_polygons.append(exp_polygon)

		# Emit triangles from prebaked grid
		var stride := nx + 1
		for zi in range(nz):
			for xi in range(nx):
				var i00 := zi * stride + xi
				var i10 := i00 + 1
				var i01 := (zi + 1) * stride + xi
				var i11 := i01 + 1
				if not (inside[i00] or inside[i10] or inside[i01] or inside[i11]):
					continue
				var x0 := bb_x + xi * cell
				var x1 := x0 + cell
				var z0 := bb_z + zi * cell
				var z1 := z0 + cell
				for tri_pt in [Vector2(x0,z0), Vector2(x1,z0), Vector2(x1,z1),
							   Vector2(x0,z0), Vector2(x1,z1), Vector2(x0,z1)]:
					var ty: float = _loader._terrain_y(tri_pt.x, tri_pt.y) + _loader.WATER_Y
					verts.append(Vector3(tri_pt.x, maxf(wy, ty), tri_pt.y))
					normals.append(Vector3.UP)


func _build_water_runtime(water: Array, verts: PackedVector3Array,
		normals: PackedVector3Array, cell: float) -> void:
	## Fallback: runtime polygon tests (slow, ~5s). Used only if water_grids.bin missing.
	for body in water:
		var pts: Array = body["points"]
		if pts.size() < 3:
			continue
		var _wcx := 0.0; var _wcz := 0.0
		for _wpt in pts:
			_wcx += float(_wpt[0]); _wcz += float(_wpt[1])
		_wcx /= float(pts.size()); _wcz /= float(pts.size())
		if not _loader._in_boundary(_wcx, _wcz):
			continue
		var _bmin_x := INF; var _bmax_x := -INF
		var _bmin_z := INF; var _bmax_z := -INF
		for _wpt in pts:
			_bmin_x = minf(_bmin_x, float(_wpt[0]))
			_bmax_x = maxf(_bmax_x, float(_wpt[0]))
			_bmin_z = minf(_bmin_z, float(_wpt[1]))
			_bmax_z = maxf(_bmax_z, float(_wpt[1]))
		if (_bmax_x - _bmin_x) > 1000.0 or (_bmax_z - _bmin_z) > 1000.0:
			continue
		var bname: String = str(body.get("name", ""))
		if bname.to_lower().contains("fountain"):
			continue
		var wy := INF
		for pt in pts:
			wy = minf(wy, _loader._terrain_y(float(pt[0]), float(pt[1])))
		wy += _loader.WATER_Y
		_loader.water_levels.append({
			"bb": Rect2(_bmin_x, _bmin_z, _bmax_x - _bmin_x, _bmax_z - _bmin_z),
			"wy": wy,
		})
		var polygon := PackedVector2Array()
		for pt in pts:
			polygon.append(Vector2(float(pt[0]), float(pt[1])))
		var expanded := Geometry2D.offset_polygon(polygon, 3.0)
		if not expanded.is_empty():
			polygon = expanded[0]
		_loader._water_polygons.append(polygon)
		var bb_min_x := INF; var bb_max_x := -INF
		var bb_min_z := INF; var bb_max_z := -INF
		for pt2 in polygon:
			bb_min_x = minf(bb_min_x, pt2.x); bb_max_x = maxf(bb_max_x, pt2.x)
			bb_min_z = minf(bb_min_z, pt2.y); bb_max_z = maxf(bb_max_z, pt2.y)
		var nx := int(ceil((bb_max_x - bb_min_x) / cell)) + 1
		var nz := int(ceil((bb_max_z - bb_min_z) / cell)) + 1
		var inside: Array = []
		inside.resize((nx + 1) * (nz + 1))
		for zi in range(nz + 1):
			for xi in range(nx + 1):
				var gx := bb_min_x + xi * cell
				var gz := bb_min_z + zi * cell
				inside[zi * (nx + 1) + xi] = Geometry2D.is_point_in_polygon(Vector2(gx, gz), polygon)
		for zi in range(nz):
			for xi in range(nx):
				var i00 := zi * (nx + 1) + xi
				var i10 := i00 + 1
				var i01 := (zi + 1) * (nx + 1) + xi
				var i11 := i01 + 1
				if not (inside[i00] or inside[i10] or inside[i01] or inside[i11]):
					continue
				var x0 := bb_min_x + xi * cell
				var x1 := x0 + cell
				var z0 := bb_min_z + zi * cell
				var z1 := z0 + cell
				for tri_pt in [Vector2(x0,z0), Vector2(x1,z0), Vector2(x1,z1),
							   Vector2(x0,z0), Vector2(x1,z1), Vector2(x0,z1)]:
					var ty: float = _loader._terrain_y(tri_pt.x, tri_pt.y) + _loader.WATER_Y
					verts.append(Vector3(tri_pt.x, maxf(wy, ty), tri_pt.y))
					normals.append(Vector3.UP)


func _build_water_mesh(verts: PackedVector3Array, normals: PackedVector3Array, water: Array) -> void:
	if verts.is_empty():
		return

	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)

	var mat := ShaderMaterial.new()
	mat.shader = _loader._get_shader("water", _water_shader_code())
	_apply_water_wave_textures(mat)
	# Heightmap for vertex-shader terrain clamping
	if _loader._hm_texture:
		mat.set_shader_parameter("heightmap_tex", _loader._hm_texture)
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		mat.set_shader_parameter("hm_min_h",      _loader._hm_min_h)
		mat.set_shader_parameter("hm_range",      _loader._hm_max_h - _loader._hm_min_h)
		mat.set_shader_parameter("hm_res",        float(mini(_loader._hm_width, 4096)))
	# Canopy map for dappled shade on water under trees
	if _loader._canopy_texture:
		mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
		mat.set_shader_parameter("canopy_world_size", _loader._hm_world_size)
	mesh.surface_set_material(0, mat)

	_loader.water_materials.append(mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "WaterBodies"
	# Water must not cast shadows: light passes through the surface, and this
	# is ONE park-wide 3.1M-tri mesh whose AABB hits every shadow cascade —
	# measured 2026-06-10 as ~12.4M shadow tris/frame at every location.
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.layers = 2  # water layer — excluded from the planar reflection camera
	_loader.add_child(mi)

	# --- Water body mist: localized FogVolume for atmospheric dawn/dusk mist ---
	# Only add mist to named water bodies large enough to produce visible effect
	var mist_shader: Shader = _loader._get_shader("water_mist", "res://shaders/water_mist.gdshader")
	var mist_count := 0
	for body in water:
		var pts2: Array = body["points"]
		if pts2.size() < 3:
			continue
		var bname2: String = str(body.get("name", ""))
		if bname2.is_empty():
			continue  # skip unnamed small pools
		if bname2.to_lower().contains("fountain"):
			continue  # skip fountains
		# Compute bounds
		var mn_x := INF; var mx_x := -INF
		var mn_z := INF; var mx_z := -INF
		var wc_x := 0.0; var wc_z := 0.0
		for wpt in pts2:
			var px: float = float(wpt[0]); var pz: float = float(wpt[1])
			mn_x = minf(mn_x, px); mx_x = maxf(mx_x, px)
			mn_z = minf(mn_z, pz); mx_z = maxf(mx_z, pz)
			wc_x += px; wc_z += pz
		wc_x /= float(pts2.size()); wc_z /= float(pts2.size())
		if not _loader._in_boundary(wc_x, wc_z):
			continue
		var w: float = mx_x - mn_x
		var d: float = mx_z - mn_z
		if w < 20.0 and d < 20.0:
			continue  # too small for visible mist
		var wy2: float = _loader._terrain_y(wc_x, wc_z) + _loader.WATER_Y
		var fog_vol := FogVolume.new()
		fog_vol.name = "Mist_" + bname2.replace(" ", "_")
		fog_vol.shape = RenderingServer.FOG_VOLUME_SHAPE_BOX
		fog_vol.size = Vector3(w + 10.0, 5.0, d + 10.0)  # 5m tall mist layer
		fog_vol.position = Vector3(wc_x, wy2 + 2.0, wc_z)  # center 2m above water
		var fog_mat := ShaderMaterial.new()
		fog_mat.shader = mist_shader
		fog_vol.material = fog_mat
		_loader.add_child(fog_vol)
		mist_count += 1
	if mist_count > 0:
		print("Water mist: %d fog volumes for dawn/dusk atmosphere" % mist_count)


func _build_water_curb(pts: Array, tint: Color, body_name: String = "") -> void:
	## Build a raised stone curb ring around a water body (e.g. Conservatory Water).
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var mat: ShaderMaterial = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh, tint)
	var curb_h := 0.35   # curb height above water
	var curb_w := 0.30   # curb width
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	for i in pts.size():
		var x0 := float(pts[i][0]); var z0 := float(pts[i][1])
		var ni := (i + 1) % pts.size()
		var x1 := float(pts[ni][0]); var z1 := float(pts[ni][1])
		var dx := x1 - x0; var dz := z1 - z0
		var seg_len := sqrt(dx * dx + dz * dz)
		if seg_len < 0.1:
			continue
		var nx := -dz / seg_len; var nz := dx / seg_len  # outward normal
		var y0: float = _loader._terrain_y(x0, z0); var y1: float = _loader._terrain_y(x1, z1)
		# Inner edge (water side)
		var ix0 := x0; var iz0 := z0; var ix1 := x1; var iz1 := z1
		# Outer edge
		var ox0 := x0 + nx * curb_w; var oz0 := z0 + nz * curb_w
		var ox1 := x1 + nx * curb_w; var oz1 := z1 + nz * curb_w
		# Top face
		var iy0 := y0 + curb_h; var iy1 := y1 + curb_h
		verts.append(Vector3(ix0, iy0, iz0)); verts.append(Vector3(ox0, iy0, oz0)); verts.append(Vector3(ox1, iy1, oz1))
		verts.append(Vector3(ix0, iy0, iz0)); verts.append(Vector3(ox1, iy1, oz1)); verts.append(Vector3(ix1, iy1, iz1))
		for _j in 6: normals.append(Vector3.UP)
		# Outer face
		verts.append(Vector3(ox0, y0, oz0)); verts.append(Vector3(ox1, y1, oz1)); verts.append(Vector3(ox1, iy1, oz1))
		verts.append(Vector3(ox0, y0, oz0)); verts.append(Vector3(ox1, iy1, oz1)); verts.append(Vector3(ox0, iy0, oz0))
		var fn := Vector3(nx, 0.0, nz)
		for _j in 6: normals.append(fn)
	if verts.is_empty():
		return
	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)
	mesh.surface_set_material(0, mat)
	var safe_name := body_name.replace(" ", "_") if not body_name.is_empty() else "Unknown"
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.name = "WaterCurb_" + safe_name
	_loader.add_child(mi)
	print("ParkLoader: %s water curb (%d segments)" % [body_name if not body_name.is_empty() else "Water body", pts.size()])


func _build_streams(streams: Array) -> void:
	# Waterways-style flowing channels: each jagged OSM polyline is smoothed
	# through a Catmull-Rom Curve3D, meshed as a subdivided ribbon whose width
	# comes from the waterway `type`, and each vertex carries the centreline's
	# own longitudinal steepness in COLOR.r (the ported Waterways steepness_map)
	# so the shader can drive faster flow + heavier foam on steep reaches.
	if streams.is_empty():
		return
	const CROSS_SEGS := 4        # cross-stream quads → CROSS_SEGS+1 verts across
	const SAMPLE_STEP := 1.5     # metres between along-stream samples
	const RIVER_HALF_W := 3.0    # waterway=river half-width
	const STREAM_HALF_W := 0.9   # waterway=stream half-width

	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	var cascades := []   # {pos, dir, s} — steep reaches get mist spray (Phase 3)

	for stream in streams:
		var raw: Array = stream.get("points", [])
		if raw.size() < 2:
			continue
		var stype := str(stream.get("type", "stream"))
		var half_w: float = RIVER_HALF_W if stype == "river" else STREAM_HALF_W

		# --- Smooth the polyline into a Catmull-Rom spline (Waterways SampleBaked) ---
		# Zero tangents give a linear curve, so derive Bezier handles from the
		# neighbour delta (Catmull-Rom): out = +Δ/6, in = -Δ/6 relative to point.
		var pcount := raw.size()
		var pos := []
		for p in raw:
			pos.append(Vector3(float(p[0]), float(p[1]), float(p[2])))
		var curve := Curve3D.new()
		for i in pcount:
			var tanv: Vector3
			if i == 0:
				tanv = pos[1] - pos[0]
			elif i == pcount - 1:
				tanv = pos[pcount - 1] - pos[pcount - 2]
			else:
				tanv = (pos[i + 1] - pos[i - 1]) * 0.5
			var handle := tanv / 3.0
			curve.add_point(pos[i], -handle, handle)

		var total_len := curve.get_baked_length()
		if total_len < SAMPLE_STEP:
			continue
		var rows := maxi(2, int(ceil(total_len / SAMPLE_STEP)) + 1)

		# Centreline samples grounded to terrain, with along-stream tangent.
		var centre := []   # Vector3 water-surface position
		var tang := []     # Vector3 unit xz tangent
		for r in rows:
			var d: float = float(r) / float(rows - 1) * total_len
			var cp := curve.sample_baked(d)
			var wy: float = _loader._terrain_y(cp.x, cp.z) + 0.05
			centre.append(Vector3(cp.x, wy, cp.z))
			var tv := curve.sample_baked(minf(d + 0.75, total_len)) - curve.sample_baked(maxf(d - 0.75, 0.0))
			tv.y = 0.0
			tang.append(tv.normalized() if tv.length() > 0.001 else Vector3(0, 0, 1))

		# Longitudinal steepness (the water's own tilt) per row → COLOR.r.
		var steep := []
		for r in rows:
			var r0 := maxi(r - 1, 0)
			var r1 := mini(r + 1, rows - 1)
			var dy: float = absf(centre[r1].y - centre[r0].y)
			var dxz: float = Vector2(centre[r1].x - centre[r0].x, centre[r1].z - centre[r0].z).length()
			var slope: float = dy / maxf(dxz, 0.01)
			steep.append(clampf(smoothstep(0.03, 0.5, slope), 0.0, 1.0))

		# Cascade detection: the stream's own steep reaches (real drops recorded
		# in the LiDAR DEM — The Loch falls at ~42°, the Gill ~26°) get a mist
		# spray at their foot. Data-driven, so falls land where the terrain
		# actually tumbles — not at the hand-placed weir GLBs (which sit up to
		# 45 m off the real stream lines). Spaced ≥8 m so a long drop gets one.
		var casc_run := 0.0
		var last_casc := -100.0
		for r in rows:
			if r > 0:
				casc_run += centre[r].distance_to(centre[r - 1])
			if steep[r] > 0.6 and (casc_run - last_casc) > 8.0:
				cascades.append({"pos": centre[r], "dir": tang[r], "s": steep[r]})
				last_casc = casc_run

		# Emit an indexed grid: `rows` along-stream × (CROSS_SEGS+1) cross-stream.
		var base_idx := verts.size()
		var dist_accum := 0.0
		for r in rows:
			if r > 0:
				dist_accum += centre[r].distance_to(centre[r - 1])
			var perp := Vector3(-tang[r].z, 0.0, tang[r].x)
			var col := Color(steep[r], 0.0, 0.0, 1.0)
			for c in (CROSS_SEGS + 1):
				var u := float(c) / float(CROSS_SEGS)   # 0..1 cross-stream
				var off := (u - 0.5) * 2.0 * half_w
				verts.append(centre[r] + perp * off)
				normals.append(Vector3.UP)
				uvs.append(Vector2(u, dist_accum))
				colors.append(col)
		var stride := CROSS_SEGS + 1
		for r in (rows - 1):
			for c in CROSS_SEGS:
				var i0 := base_idx + r * stride + c
				var i2 := i0 + stride
				# cull_disabled shader → winding irrelevant
				indices.append(i0); indices.append(i2); indices.append(i0 + 1)
				indices.append(i0 + 1); indices.append(i2); indices.append(i2 + 1)

	if verts.is_empty():
		return

	var s_mesh: ArrayMesh = _loader._make_mesh(verts, normals, uvs, colors, indices)

	var mat := ShaderMaterial.new()
	mat.shader = _loader._get_shader("stream", "res://shaders/stream.gdshader")
	if _loader._hm_texture:
		mat.set_shader_parameter("heightmap_tex", _loader._hm_texture)
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		mat.set_shader_parameter("hm_min_h",      _loader._hm_min_h)
		mat.set_shader_parameter("hm_range",      _loader._hm_max_h - _loader._hm_min_h)
		mat.set_shader_parameter("hm_res",        float(mini(_loader._hm_width, 4096)))
	if _loader._canopy_texture:
		mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
		mat.set_shader_parameter("canopy_world_size", _loader._hm_world_size)
	s_mesh.surface_set_material(0, mat)

	var s_mi := MeshInstance3D.new()
	s_mi.mesh = s_mesh
	s_mi.name = "Streams"
	s_mi.layers = 2  # water layer — excluded from the planar reflection camera
	_loader.add_child(s_mi)
	for c in cascades:
		_add_cascade_spray(c["pos"], c["dir"], c["s"])
	print("  Streams: %d polylines, %d triangles, %d cascades" % [streams.size(), verts.size() / 3, cascades.size()])


# Mist/spray at the foot of a stream cascade. Droplets tumble forward along the
# flow and fall — a lighter, wider cousin of the fountain jet spray.
func _add_cascade_spray(pos: Vector3, flow_dir: Vector3, intensity: float) -> void:
	var particles := GPUParticles3D.new()
	particles.amount = int(60.0 + intensity * 90.0)
	particles.lifetime = 1.8
	# AABB must cover the whole fall (gravity carries droplets ~11 m down over
	# the lifetime) or Godot frustum-culls them and the spray vanishes.
	particles.visibility_aabb = AABB(Vector3(-8, -14, -8), Vector3(16, 22, 16))

	var pm := ParticleProcessMaterial.new()
	# Fly forward along flow and downward off the lip.
	var dir := (flow_dir * 0.7 + Vector3.DOWN * 0.5).normalized()
	pm.direction = dir
	pm.spread = 32.0
	pm.initial_velocity_min = 1.5 + intensity * 2.0
	pm.initial_velocity_max = 3.0 + intensity * 3.5
	pm.gravity = Vector3(0, -9.8, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(1.0, 0.15, 1.0)
	pm.damping_min = 1.5
	pm.damping_max = 4.0
	pm.scale_min = 0.8
	pm.scale_max = 2.2
	particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.14, 0.14)
	particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.88, 0.92, 0.96, 0.65)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.emission_enabled = true
	mat.emission = Color(0.62, 0.70, 0.80)
	mat.emission_energy_multiplier = 0.18
	particles.material_override = mat

	particles.position = pos + Vector3(0.0, 0.15, 0.0)
	particles.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_loader.add_child(particles)


func _water_shader_code() -> String:
	return "res://shaders/water.gdshader"


func _apply_water_wave_textures(mat: ShaderMaterial) -> void:
	## Ripple normal maps generated by tools/gen_water_normals.py (original, tileable)
	mat.set_shader_parameter("water_normal_a", _loader._load_tex("res://textures/water_normal_a.png"))
	mat.set_shader_parameter("water_normal_b", _loader._load_tex("res://textures/water_normal_b.png"))
