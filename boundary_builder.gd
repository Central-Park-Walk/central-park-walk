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
		if path.get("bridge", false) or path.get("tunnel", false):
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
	var mat: ShaderMaterial = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh, Color(0.48, 0.46, 0.42))
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
		var pillar_mat: ShaderMaterial = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh, Color(0.62, 0.60, 0.56))
		var pillar_mesh: ArrayMesh = _loader._make_mesh(pillar_verts, pillar_normals)
		pillar_mesh.surface_set_material(0, pillar_mat)
		var pillar_mi := MeshInstance3D.new()
		pillar_mi.mesh = pillar_mesh
		pillar_mi.name = "GatePillars"
		pillar_mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		_loader.add_child(pillar_mi)
		print("ParkLoader: gate pillars = %d" % (gate_positions.size() * 2))


func _label_boundary_buildings(buildings: Array) -> void:
	## Add Label3D name tags to named buildings near the park boundary.
	## Uses real building height data for label placement.
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

		var bld_h: float = float(b.get("height", 15.0))
		var ty: float = _loader._terrain_y(cx, cz)
		var label_y := ty + bld_h * 0.6  # place label at ~60% building height

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
