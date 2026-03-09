# boundary_builder.gd
# Park boundary: collision walls, brownstone perimeter wall, building facades, labels
# Extracted from park_loader.gd — all shared utilities accessed via _loader reference.

var _loader  # Reference to park_loader for shared utilities

func _init(loader) -> void:
	_loader = loader


func _build_boundary(boundary: Array) -> void:
	if boundary.size() < 3:
		push_warning("ParkLoader: boundary too small – skipping walls")
		return

	# Polygon already populated early in _ready() — just build collision walls
	var body := StaticBody3D.new()
	body.name = "BoundaryWalls"
	_loader.add_child(body)

	var n := boundary.size()
	for i in range(n):
		var p1 := Vector2(float(boundary[i][0]),           float(boundary[i][1]))
		var p2 := Vector2(float(boundary[(i + 1) % n][0]), float(boundary[(i + 1) % n][1]))

		var seg_len := p1.distance_to(p2)
		if seg_len < 0.3:
			continue

		var mid := (p1 + p2) * 0.5
		var dir := (p2 - p1) / seg_len

		var box  := BoxShape3D.new()
		box.size  = Vector3(seg_len, 80.0, 0.5)

		var col      := CollisionShape3D.new()
		col.shape     = box
		col.position  = Vector3(mid.x, 40.0, mid.y)
		col.rotation.y = atan2(-dir.y, dir.x)

		body.add_child(col)


func _build_perimeter_wall(boundary: Array, paths: Array) -> void:
	## Central Park's brownstone perimeter wall — 1.17m tall, 0.45m thick,
	## slanted top (15-degree batter angle on inner cap). rock_wall texture.
	## Gate openings where paths cross the boundary.
	if boundary.size() < 3:
		return
	var wall_h := 1.17
	var wall_t := 0.45
	var batter := tan(deg_to_rad(15.0))  # inner face cap slope
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")

	# Centroid for inward normal
	var cx := 0.0; var cz := 0.0
	for pt in boundary:
		cx += float(pt[0]); cz += float(pt[1])
	cx /= float(boundary.size()); cz /= float(boundary.size())

	# Find gate positions: where a path segment crosses the boundary polygon
	# Only actual entry/exit roads and paths (service, footway, pedestrian)
	var gate_positions: Array = []  # Array of Vector2
	var gate_radius := 4.0  # gate half-width in metres
	for path in paths:
		if bool(path.get("bridge", false)) or bool(path.get("tunnel", false)):
			continue
		var hw: String = str(path.get("highway", "path"))
		if hw == "steps" or hw == "track" or hw == "bridleway":
			continue
		var ppts: Array = path["points"]
		if ppts.size() < 2:
			continue
		# Check consecutive points for boundary crossings
		for pi in range(ppts.size() - 1):
			var ax := float(ppts[pi][0]); var az := float(ppts[pi][2])
			var bx := float(ppts[pi+1][0]); var bz := float(ppts[pi+1][2])
			var a_in: bool = _loader._in_boundary(ax, az)
			var b_in: bool = _loader._in_boundary(bx, bz)
			if a_in == b_in:
				continue
			# Crossing found — approximate position at midpoint
			var gx := (ax + bx) * 0.5
			var gz := (az + bz) * 0.5
			# Gate width scales with path type
			var too_close := false
			for gp in gate_positions:
				if Vector2(gx, gz).distance_to(gp) < gate_radius * 2.5:
					too_close = true
					break
			if not too_close:
				gate_positions.append(Vector2(gx, gz))
	print("ParkLoader: perimeter wall gates = %d" % gate_positions.size())

	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()

	var n := boundary.size()
	var cum_d := 0.0
	for i in range(n):
		var p1 := Vector2(float(boundary[i][0]), float(boundary[i][1]))
		var p2 := Vector2(float(boundary[(i + 1) % n][0]), float(boundary[(i + 1) % n][1]))
		var seg_len := p1.distance_to(p2)
		if seg_len < 0.5:
			cum_d += seg_len
			continue

		# Subdivide long segments for smooth curves
		var n_sub := int(ceil(seg_len / 5.0))
		for si in n_sub:
			var t0 := float(si) / float(n_sub)
			var t1 := float(si + 1) / float(n_sub)
			var a := p1.lerp(p2, t0)
			var b := p1.lerp(p2, t1)
			var sub_len := a.distance_to(b)
			# Skip segments near gate positions
			var mid := (a + b) * 0.5
			var is_gate := false
			for gp in gate_positions:
				if mid.distance_to(gp) < gate_radius:
					is_gate = true
					break
			if is_gate:
				cum_d += sub_len
				continue
			var dir := (b - a) / sub_len if sub_len > 0.01 else Vector2.RIGHT
			# Inward normal (toward centroid)
			var nrm2 := Vector2(-dir.y, dir.x)
			if nrm2.dot(Vector2(cx - a.x, cz - a.y)) < 0.0:
				nrm2 = -nrm2
			var outward := -nrm2

			var ya: float = _loader._terrain_y(a.x, a.y) - 0.02  # sink base below terrain
			var yb: float = _loader._terrain_y(b.x, b.y) - 0.02
			var ht := wall_t * 0.5

			# Outer wall origin (outward from boundary center)
			var oa := Vector2(a.x + outward.x * ht, a.y + outward.y * ht)
			var ob := Vector2(b.x + outward.x * ht, b.y + outward.y * ht)
			var ia2 := Vector2(a.x - outward.x * ht, a.y - outward.y * ht)
			var ib2 := Vector2(b.x - outward.x * ht, b.y - outward.y * ht)

			var u0 := cum_d / 1.5  # UV tiling 1.5m horizontal
			var u1 := (cum_d + sub_len) / 1.5
			var v_top := wall_h / 1.5

			# Outer face (vertical)
			var on3 := Vector3(outward.x, 0.0, outward.y)
			var base := verts.size()
			verts.append(Vector3(oa.x, ya, oa.y))
			verts.append(Vector3(ob.x, yb, ob.y))
			verts.append(Vector3(ob.x, yb + wall_h, ob.y))
			verts.append(Vector3(oa.x, ya + wall_h, oa.y))
			for _j in 4: normals.append(on3)
			uvs.append(Vector2(u0, 0.0)); uvs.append(Vector2(u1, 0.0))
			uvs.append(Vector2(u1, v_top)); uvs.append(Vector2(u0, v_top))

			# Inner face (vertical)
			var in3 := Vector3(-outward.x, 0.0, -outward.y)
			base = verts.size()
			verts.append(Vector3(ib2.x, yb, ib2.y))
			verts.append(Vector3(ia2.x, ya, ia2.y))
			verts.append(Vector3(ia2.x, ya + wall_h, ia2.y))
			verts.append(Vector3(ib2.x, yb + wall_h, ib2.y))
			for _j in 4: normals.append(in3)
			uvs.append(Vector2(u1, 0.0)); uvs.append(Vector2(u0, 0.0))
			uvs.append(Vector2(u0, v_top)); uvs.append(Vector2(u1, v_top))

			# Slanted cap (outer edge at full height, inner edge slightly lower = batter)
			var cap_inner_h := wall_h - wall_t * batter  # inner edge lower
			var cap_n := Vector3(-outward.x * batter, 1.0, -outward.y * batter).normalized()
			base = verts.size()
			verts.append(Vector3(oa.x, ya + wall_h, oa.y))
			verts.append(Vector3(ob.x, yb + wall_h, ob.y))
			verts.append(Vector3(ib2.x, yb + cap_inner_h, ib2.y))
			verts.append(Vector3(ia2.x, ya + cap_inner_h, ia2.y))
			for _j in 4: normals.append(cap_n)
			uvs.append(Vector2(u0, 0.0)); uvs.append(Vector2(u1, 0.0))
			uvs.append(Vector2(u1, wall_t / 1.5)); uvs.append(Vector2(u0, wall_t / 1.5))

			cum_d += sub_len

	if verts.is_empty():
		return

	# Build indices (simple quads)
	var indices := PackedInt32Array()
	var n_quads := verts.size() / 4
	for qi in n_quads:
		var b2 := qi * 4
		indices.append_array(PackedInt32Array([b2, b2+1, b2+2, b2, b2+2, b2+3]))

	# Manhattan schist: gray with subtle warm weathering (Wikimedia reference)
	var mat: StandardMaterial3D = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh, Color(0.48, 0.46, 0.42))
	var mesh: ArrayMesh = _loader._make_mesh(verts, normals, uvs, null, indices)
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "PerimeterWall"
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	_loader.add_child(mi)

	# Collision
	var body := StaticBody3D.new()
	body.name = "PerimeterWallCollision"
	_loader.add_child(body)
	var shape := ConcavePolygonShape3D.new()
	var tri_verts := PackedVector3Array()
	for qi in n_quads:
		var b2 := qi * 4
		tri_verts.append(verts[b2]); tri_verts.append(verts[b2+1]); tri_verts.append(verts[b2+2])
		tri_verts.append(verts[b2]); tri_verts.append(verts[b2+2]); tri_verts.append(verts[b2+3])
	shape.set_faces(tri_verts)
	var col := CollisionShape3D.new()
	col.shape = shape
	body.add_child(col)
	print("ParkLoader: perimeter wall = %d segments" % n_quads)

	# Gate pillars — stone posts flanking each gate opening
	# Real CP gates have paired granite pillars ~2.4m tall with capstones
	var pillar_verts := PackedVector3Array()
	var pillar_normals := PackedVector3Array()
	var pillar_w := 0.55   # pillar width
	var pillar_h := 2.4    # pillar height (taller than wall)
	var cap_overhang := 0.08  # capstone extends beyond pillar
	for gp in gate_positions:
		# Find nearest boundary segment to get wall direction
		var best_dir := Vector2.RIGHT
		var best_d := INF
		for bi in range(boundary.size()):
			var bp1 := Vector2(float(boundary[bi][0]), float(boundary[bi][1]))
			var bp2 := Vector2(float(boundary[(bi + 1) % boundary.size()][0]),
							float(boundary[(bi + 1) % boundary.size()][1]))
			var seg2 := bp2 - bp1
			var sl := seg2.length()
			if sl < 0.5: continue
			var t2 := clampf(seg2.dot(gp - bp1) / (sl * sl), 0.0, 1.0)
			var closest := bp1 + seg2 * t2
			var d: float = gp.distance_to(closest)
			if d < best_d:
				best_d = d
				best_dir = seg2.normalized()
		var nrm2 := Vector2(-best_dir.y, best_dir.x)
		if nrm2.dot(Vector2(cx - gp.x, cz - gp.y)) < 0.0:
			nrm2 = -nrm2
		var gy: float = _loader._terrain_y(gp.x, gp.y) - 0.02
		# Place two pillars at ±(gate_radius + pillar_w/2) along wall direction
		for side in [-1.0, 1.0]:
			var offset: Vector2 = best_dir * (gate_radius + pillar_w * 0.5) * side
			var pc: Vector2 = gp + offset  # pillar center XZ
			var phw := pillar_w * 0.5
			var py: float = _loader._terrain_y(pc.x, pc.y) - 0.02
			# 4 vertical faces of the pillar
			for face in range(4):
				var fn: Vector3; var c0: Vector3; var c1: Vector3; var c2: Vector3; var c3: Vector3
				if face == 0:  # +X face
					fn = Vector3(1, 0, 0)
					c0 = Vector3(pc.x + phw, py, pc.y - phw)
					c1 = Vector3(pc.x + phw, py, pc.y + phw)
					c2 = Vector3(pc.x + phw, py + pillar_h, pc.y + phw)
					c3 = Vector3(pc.x + phw, py + pillar_h, pc.y - phw)
				elif face == 1:  # -X face
					fn = Vector3(-1, 0, 0)
					c0 = Vector3(pc.x - phw, py, pc.y + phw)
					c1 = Vector3(pc.x - phw, py, pc.y - phw)
					c2 = Vector3(pc.x - phw, py + pillar_h, pc.y - phw)
					c3 = Vector3(pc.x - phw, py + pillar_h, pc.y + phw)
				elif face == 2:  # +Z face
					fn = Vector3(0, 0, 1)
					c0 = Vector3(pc.x + phw, py, pc.y + phw)
					c1 = Vector3(pc.x - phw, py, pc.y + phw)
					c2 = Vector3(pc.x - phw, py + pillar_h, pc.y + phw)
					c3 = Vector3(pc.x + phw, py + pillar_h, pc.y + phw)
				else:  # -Z face
					fn = Vector3(0, 0, -1)
					c0 = Vector3(pc.x - phw, py, pc.y - phw)
					c1 = Vector3(pc.x + phw, py, pc.y - phw)
					c2 = Vector3(pc.x + phw, py + pillar_h, pc.y - phw)
					c3 = Vector3(pc.x - phw, py + pillar_h, pc.y - phw)
				pillar_verts.append_array(PackedVector3Array([c0, c1, c2, c0, c2, c3]))
				for _j in 6: pillar_normals.append(fn)
			# Capstone top face
			var cw := phw + cap_overhang
			var cap_y := py + pillar_h
			pillar_verts.append_array(PackedVector3Array([
				Vector3(pc.x - cw, cap_y, pc.y - cw),
				Vector3(pc.x + cw, cap_y, pc.y - cw),
				Vector3(pc.x + cw, cap_y, pc.y + cw),
				Vector3(pc.x - cw, cap_y, pc.y - cw),
				Vector3(pc.x + cw, cap_y, pc.y + cw),
				Vector3(pc.x - cw, cap_y, pc.y + cw)
			]))
			for _j in 6: pillar_normals.append(Vector3.UP)

	if not pillar_verts.is_empty():
		# Light gray granite for gate pillars (dressed stone, lighter than schist wall)
		var pillar_mat: StandardMaterial3D = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh, Color(0.62, 0.60, 0.56))
		var pillar_mesh: ArrayMesh = _loader._make_mesh(pillar_verts, pillar_normals)
		pillar_mesh.surface_set_material(0, pillar_mat)
		var pillar_mi := MeshInstance3D.new()
		pillar_mi.mesh = pillar_mesh
		pillar_mi.name = "GatePillars"
		pillar_mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		_loader.add_child(pillar_mi)
		print("ParkLoader: gate pillars = %d" % (gate_positions.size() * 2))


func _build_boundary_facades() -> void:
	## NYC building facades along the park boundary, matching real skyline.
	## Coordinate mapping: Z = 1967 - (street - 59) * 74.7
	##   +Z = south (59th St), -Z = north (110th St)
	##   +X = east (Fifth Ave ≈ +1019), -X = west (CPW ≈ -1228)
	if _loader.boundary_polygon.size() < 3:
		return

	# Centroid for inward-normal detection
	var cx := 0.0
	var cz := 0.0
	for pt in _loader.boundary_polygon:
		cx += pt.x; cz += pt.y
	cx /= float(_loader.boundary_polygon.size())
	cz /= float(_loader.boundary_polygon.size())

	# 5 style buckets reusing existing building materials
	# 0=LIMESTONE 1=GLASS 2=RED_BRICK 3=BUFF_BRICK 4=DARK_STONE
	var sv: Array = []; var sn: Array = []; var su: Array = []; var sc: Array = []
	for _i in range(5):
		sv.append(PackedVector3Array())
		sn.append(PackedVector3Array())
		su.append(PackedVector2Array())
		sc.append(PackedColorArray())
	var roof_v := PackedVector3Array()
	var roof_n := PackedVector3Array()
	var roof_c := PackedColorArray()

	# --- Landmark tables: [z_min, z_max, height, style] ---
	# East side (Fifth Avenue): cream limestone co-ops, 12-18 stories
	# Z coords: 59th=1967, 70th=1145, 72nd=996, 80th=398, 84th=99, 88th=-199, 110th=-1842
	var east_lm := [
		[1890.0, 1970.0, 77.0,  3],  # Plaza Hotel — 18 stories, white/buff brick (76m)
		[1100.0, 1200.0, 15.0,  0],  # Frick Collection — 3-story limestone mansion (14m)
		[99.0,   398.0,  28.0,  0],  # Metropolitan Museum — wide, low, limestone/granite
		[-275.0, -199.0, 28.0,  0],  # Guggenheim Museum — white concrete spiral (28m)
		[-1320.0,-946.0, 50.0,  1],  # Mount Sinai Hospital — institutional glass/brick
	]
	# West side (Central Park West): Art Deco twin-towers + buff brick
	var west_lm := [
		[1890.0, 1970.0, 229.0, 1],  # Deutsche Bank Center (Time Warner) — 55-story glass (229m)
		[1750.0, 1830.0, 199.0, 0],  # 15 CPW — modern limestone, 43 stories (199m)
		[1670.0, 1750.0, 100.0, 3],  # The Century — Art Deco twin tower, 30 stories (100m)
		[996.0,  1071.0, 96.0,  3],  # The Majestic — Art Deco twin tower, 29 stories (96m)
		[920.0,  996.0,  29.0,  3],  # The Dakota — Victorian Gothic, 9 stories (29m)
		[772.0,  920.0,  126.0, 3],  # The San Remo — twin tower, 27 stories (126m)
		[324.0,  622.0,  23.0,  0],  # Am. Museum of Natural History — wide low limestone
		[250.0,  324.0,  87.0,  3],  # The Beresford — triple tower, 23 stories (87m)
		[-424.0, -349.0, 96.0,  3],  # The El Dorado — Art Deco twin tower, 29 stories (96m)
	]
	# South side (59th St / CPS): Art Deco hotels + supertall backdrop
	# Uses X coordinate instead of Z
	var south_lm := [
		[800.0,  1020.0, 77.0,  3],  # Plaza Hotel (east end) (76m)
		[500.0,  650.0,  426.0, 0],  # 432 Park Avenue — white concrete grid (426m)
		[-150.0, -50.0,  152.0, 3],  # Essex House — 44-story Art Deco, cream brick (152m)
		[-300.0, -200.0, 120.0, 3],  # Hampshire House — white brick Art Deco (120m)
		[-500.0, -350.0, 472.0, 1],  # Central Park Tower — 98-story glass (472m)
		[-250.0, -100.0, 435.0, 1],  # Steinway Tower (111 W 57th) — slender glass (435m)
		[-100.0, 50.0,   306.0, 1],  # One57 — glass curtain wall (306m)
	]

	# Build spatial grid index for fast perimeter height lookups
	var _ph_grid: Dictionary = {}  # "gx,gz" → Array of [x, z, h] entries
	var PH_CELL := 50.0  # grid cell size in metres
	for ph in _loader._perimeter_heights:
		var gx := int(floor(float(ph[0]) / PH_CELL))
		var gz := int(floor(float(ph[1]) / PH_CELL))
		var key := "%d,%d" % [gx, gz]
		if not _ph_grid.has(key):
			_ph_grid[key] = []
		_ph_grid[key].append(ph)
	var ph_search_r := int(ceil(300.0 / PH_CELL))  # grid cells to search

	var n: int = _loader.boundary_polygon.size()
	var cum_dist := 0.0

	for i in range(n):
		var p1: Vector2 = _loader.boundary_polygon[i]
		var p2: Vector2 = _loader.boundary_polygon[(i + 1) % n]
		var seg := p2 - p1
		var seg_len := seg.length()
		if seg_len < 0.3:
			cum_dist += seg_len
			continue

		var dir := seg / seg_len
		var mid := (p1 + p2) * 0.5
		var mx := mid.x
		var mz := mid.y  # Z stored in Vector2.y

		# Outward offset (2m outside boundary)
		var left_n := Vector2(-dir.y, dir.x)
		var to_center := Vector2(cx - mx, cz - mz)
		if left_n.dot(to_center) < 0.0:
			left_n = -left_n
		var inward := left_n
		var face_offset := -inward * 2.0
		var fp1 := p1 + face_offset
		var fp2 := p2 + face_offset
		var norm3 := Vector3(inward.x, 0.0, inward.y)

		# Building block index for style variation (30m blocks)
		var block_idx := int(floor(cum_dist / 30.0))
		var bh := fmod(abs(float(block_idx) * 73.7 + 17.3), 1.0)  # 0..1 hash

		# --- Find nearest real building height from NYC data (grid lookup) ---
		var bld_h := 10.0  # fallback
		var found_nyc := false
		var best_dist_sq := 300.0 * 300.0
		var cgx := int(floor(mx / PH_CELL))
		var cgz := int(floor(mz / PH_CELL))
		for gx2 in range(cgx - ph_search_r, cgx + ph_search_r + 1):
			for gz2 in range(cgz - ph_search_r, cgz + ph_search_r + 1):
				var key2 := "%d,%d" % [gx2, gz2]
				if _ph_grid.has(key2):
					for ph in _ph_grid[key2]:
						var dx := float(ph[0]) - mx
						var dz := float(ph[1]) - mz
						var dsq := dx * dx + dz * dz
						if dsq < best_dist_sq:
							best_dist_sq = dsq
							bld_h = float(ph[2])
							found_nyc = true

		# --- Classify side for style + tint ---
		var style: int
		var tint := Color(1.0, 1.0, 1.0)
		var matched_lm := false

		if mx > 500.0 and mz > -1700.0 and mz < 1800.0:
			# ═══ EAST SIDE — Fifth Avenue ═══
			style = 0  # LIMESTONE
			tint = Color(1.02, 1.0, 0.96)  # warm cream
			for lm in east_lm:
				if mz >= lm[0] and mz <= lm[1]:
					style = int(lm[3]); matched_lm = true; break
			if mz < -1320.0:
				style = 2  # red brick north of 103rd
				tint = Color(0.98, 0.94, 0.90)

		elif mx < -700.0 and mz > -1700.0 and mz < 1800.0:
			# ═══ WEST SIDE — Central Park West ═══
			style = 3  # BUFF_BRICK
			tint = Color(1.0, 0.98, 0.94)
			for lm in west_lm:
				if mz >= lm[0] and mz <= lm[1]:
					style = int(lm[3]); matched_lm = true; break
			if matched_lm and mz >= 920.0 and mz < 996.0:
				tint = Color(1.05, 1.02, 0.86)  # Dakota tint
			if mz < -700.0 and not matched_lm:
				style = 2
				tint = Color(0.96, 0.93, 0.88)

		elif mz > 1700.0:
			# ═══ SOUTH SIDE — Central Park South / 59th St ═══
			style = 3  # BUFF_BRICK
			tint = Color(1.0, 0.98, 0.95)
			for lm in south_lm:
				if mx >= lm[0] and mx <= lm[1]:
					style = int(lm[3]); matched_lm = true; break

		else:
			# ═══ NORTH SIDE — 110th St ═══
			style = 2  # RED_BRICK
			tint = Color(0.98, 0.94, 0.90)
			if bld_h > 30.0:
				style = 1  # glass for taller buildings

		if not found_nyc:
			# No NYC data — use procedural fallback
			if mx > 500.0: bld_h = 40.0 + bh * 20.0
			elif mx < -700.0: bld_h = 28.0 + bh * 14.0
			elif mz > 1700.0: bld_h = 100.0 + bh * 45.0
			else: bld_h = 15.0 + bh * 8.0

		# Per-building tint variation (±15%)
		var rv := fmod(abs(float(block_idx) * 17.3), 0.30) - 0.15
		var gv := fmod(abs(float(block_idx) * 11.1), 0.24) - 0.12
		var bv2 := fmod(abs(float(block_idx) * 7.7), 0.16) - 0.08
		tint.r += rv; tint.g += gv; tint.b += bv2

		var base_y: float = _loader._terrain_y(mx, mz) - 1.0
		var top_y := base_y + bld_h

		# Wall quad
		# Building depth (outward from park, behind the front face)
		var depth := 25.0
		var ro := -inward * depth
		# Front face (faces park)
		var a := Vector3(fp1.x, base_y, fp1.y)
		var b := Vector3(fp2.x, base_y, fp2.y)
		var c := Vector3(fp2.x, top_y,  fp2.y)
		var d := Vector3(fp1.x, top_y,  fp1.y)
		sv[style].append_array(PackedVector3Array([a, b, c, a, c, d]))
		for _j in range(6):
			sn[style].append(norm3)
			sc[style].append(tint)
		su[style].append_array(PackedVector2Array([
			Vector2(0.0,     0.0),
			Vector2(seg_len, 0.0),
			Vector2(seg_len, bld_h),
			Vector2(0.0,     0.0),
			Vector2(seg_len, bld_h),
			Vector2(0.0,     bld_h),
		]))
		# Back face (faces away from park)
		var ba := Vector3(fp1.x + ro.x, base_y, fp1.y + ro.y)
		var bb := Vector3(fp2.x + ro.x, base_y, fp2.y + ro.y)
		var bc := Vector3(fp2.x + ro.x, top_y,  fp2.y + ro.y)
		var bd := Vector3(fp1.x + ro.x, top_y,  fp1.y + ro.y)
		var back_n := -norm3
		sv[style].append_array(PackedVector3Array([bb, ba, bd, bb, bd, bc]))
		for _j in range(6):
			sn[style].append(back_n)
			sc[style].append(tint * Color(0.85, 0.85, 0.85))  # slightly darker back
		su[style].append_array(PackedVector2Array([
			Vector2(seg_len, 0.0),
			Vector2(0.0,     0.0),
			Vector2(0.0,     bld_h),
			Vector2(seg_len, 0.0),
			Vector2(0.0,     bld_h),
			Vector2(seg_len, bld_h),
		]))
		# Left side wall
		var side_n_l := Vector3(-dir.x, 0.0, -dir.y)  # perpendicular to segment
		sv[style].append_array(PackedVector3Array([a, ba, bd, a, bd, d]))
		for _j in range(6):
			sn[style].append(side_n_l)
			sc[style].append(tint * Color(0.90, 0.90, 0.90))
		su[style].append_array(PackedVector2Array([
			Vector2(0.0, 0.0), Vector2(depth, 0.0), Vector2(depth, bld_h),
			Vector2(0.0, 0.0), Vector2(depth, bld_h), Vector2(0.0, bld_h),
		]))
		# Right side wall
		var side_n_r := Vector3(dir.x, 0.0, dir.y)
		sv[style].append_array(PackedVector3Array([bb, b, c, bb, c, bc]))
		for _j in range(6):
			sn[style].append(side_n_r)
			sc[style].append(tint * Color(0.90, 0.90, 0.90))
		su[style].append_array(PackedVector2Array([
			Vector2(0.0, 0.0), Vector2(depth, 0.0), Vector2(depth, bld_h),
			Vector2(0.0, 0.0), Vector2(depth, bld_h), Vector2(0.0, bld_h),
		]))

		# Roof quad (full depth)
		roof_v.append_array(PackedVector3Array([d, c, bc, d, bc, bd]))
		var roof_rv := fmod(abs(float(block_idx) * 11.3 + mz * 0.17), 10.0)
		var roof_col := Color(0.18, 0.17, 0.16)
		if roof_rv >= 3.0 and roof_rv < 6.0:
			roof_col = Color(0.52, 0.50, 0.48)
		elif roof_rv >= 6.0 and roof_rv < 8.0:
			roof_col = Color(0.34, 0.28, 0.20)
		elif roof_rv >= 8.0:
			roof_col = Color(0.28, 0.36, 0.26)
		for _j in range(6):
			roof_n.append(Vector3.UP)
			roof_c.append(roof_col)

		# Front parapet — 0.8m wall on park-facing edge
		var parapet_h := 0.8
		var pa := Vector3(fp1.x, top_y, fp1.y)
		var pb := Vector3(fp2.x, top_y, fp2.y)
		var pc := Vector3(fp2.x, top_y + parapet_h, fp2.y)
		var pd := Vector3(fp1.x, top_y + parapet_h, fp1.y)
		sv[style].append_array(PackedVector3Array([pa, pb, pc, pa, pc, pd]))
		for _j in range(6):
			sn[style].append(norm3)
			sc[style].append(tint * Color(0.88, 0.88, 0.88))
		su[style].append_array(PackedVector2Array([
			Vector2(0.0, bld_h), Vector2(seg_len, bld_h),
			Vector2(seg_len, bld_h + parapet_h), Vector2(0.0, bld_h),
			Vector2(seg_len, bld_h + parapet_h), Vector2(0.0, bld_h + parapet_h),
		]))

		cum_dist += seg_len

	# Build facade meshes per style
	var style_names := ["Limestone", "Glass", "RedBrick", "BuffBrick", "DarkStone"]
	var style_mats := [
		_loader._building_builder._make_facade_limestone(),
		_loader._building_builder._make_facade_glass(),
		_loader._building_builder._make_facade_red_brick(),
		_loader._building_builder._make_facade_buff_brick(),
		_loader._building_builder._make_facade_dark_stone(),
	]
	_loader.facade_materials.append_array(style_mats)
	var total_quads := 0
	for s in range(5):
		if sv[s].is_empty():
			continue
		var mesh: ArrayMesh = _loader._make_mesh(sv[s], sn[s], su[s], sc[s])
		mesh.surface_set_material(0, style_mats[s])
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.name = "BoundaryFacade_" + style_names[s]
		_loader.add_child(mi)
		total_quads += sv[s].size() / 6

	# Roof mesh
	if not roof_v.is_empty():
		var r_mesh: ArrayMesh = _loader._make_mesh(roof_v, roof_n, null, roof_c)
		var r_mat := StandardMaterial3D.new()
		r_mat.vertex_color_use_as_albedo = true
		r_mat.roughness = 0.92
		r_mesh.surface_set_material(0, r_mat)
		var r_mi := MeshInstance3D.new()
		r_mi.mesh = r_mesh
		r_mi.name = "BoundaryFacade_Roofs"
		_loader.add_child(r_mi)

	print("ParkLoader: boundary facades = %d segments" % total_quads)

	# Add name labels for park-facing buildings from OSM data
	_label_boundary_buildings()


func _label_boundary_buildings() -> void:
	## Add Label3D name tags to named buildings near the park boundary.
	## Only shows buildings that are outside the park but close to it.
	var fh := FileAccess.open("res://park_data.json", FileAccess.READ)
	if not fh:
		return
	var data: Dictionary = JSON.parse_string(fh.get_as_text())
	fh.close()
	var buildings: Array = data.get("buildings", [])
	var count := 0
	for b in buildings:
		var bname: String = str(b.get("name", ""))
		if bname.is_empty():
			continue
		var pts: Array = b.get("points", [])
		if pts.size() < 3:
			continue

		# Compute centroid
		var cx := 0.0
		var cz := 0.0
		for pt in pts:
			cx += float(pt[0])
			cz += float(pt[1])
		cx /= float(pts.size())
		cz /= float(pts.size())

		# Skip buildings inside the park — we only want perimeter buildings
		if _loader._in_boundary(cx, cz):
			continue

		# Must be close to park boundary (within 200m)
		var min_dist := 999999.0
		for bp in _loader.boundary_polygon:
			var d := Vector2(cx - bp.x, cz - bp.y).length()
			if d < min_dist:
				min_dist = d
		if min_dist > 200.0:
			continue

		# Estimate building height from footprint area
		var min_x := INF; var max_x := -INF
		var min_z := INF; var max_z := -INF
		for pt in pts:
			var px := float(pt[0]); var pz := float(pt[1])
			if px < min_x: min_x = px
			if px > max_x: max_x = px
			if pz < min_z: min_z = pz
			if pz > max_z: max_z = pz
		var footprint_w := max_x - min_x
		var footprint_d := max_z - min_z
		var diag := sqrt(footprint_w * footprint_w + footprint_d * footprint_d)
		# Estimate height: small building=15m, large=60m+
		var est_h := clampf(diag * 0.8, 15.0, 200.0)

		var ty: float = _loader._terrain_y(cx, cz)
		var label_y := ty + est_h * 0.6  # place label at ~60% building height

		var lbl := Label3D.new()
		lbl.text = bname
		lbl.font_size = 36
		lbl.pixel_size = 0.008
		lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED

		lbl.modulate = Color(0.70, 0.68, 0.64, 0.45)
		lbl.outline_size = 4
		lbl.outline_modulate = Color(0.08, 0.08, 0.08, 0.30)
		lbl.no_depth_test = false
		lbl.position = Vector3(cx, label_y, cz)
		_loader.add_child(lbl)
		count += 1

	if count > 0:
		print("ParkLoader: building labels = %d" % count)
