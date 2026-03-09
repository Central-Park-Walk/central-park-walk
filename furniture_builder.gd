var _loader

func _init(loader) -> void:
	_loader = loader

# ---------------------------------------------------------------------------
# Tree-base dirt circles
# ---------------------------------------------------------------------------
func _make_dirt_circle_mesh() -> ArrayMesh:
	## Flat disc (8-segment fan), radius 1.0 (scaled per-instance)
	var verts   := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	var seg := 8
	verts.append(Vector3(0.0, 0.0, 0.0))
	normals.append(Vector3(0.0, 1.0, 0.0))
	for i in seg:
		var a := TAU * float(i) / float(seg)
		verts.append(Vector3(cos(a), 0.0, sin(a)))
		normals.append(Vector3(0.0, 1.0, 0.0))
	for i in seg:
		indices.append(0)
		indices.append(i + 1)
		indices.append((i + 1) % seg + 1)
	var mesh: ArrayMesh = _loader._make_mesh(verts, normals, null, null, indices)
	return mesh


func _build_furniture(bench_data: Array, lamppost_data: Array, paths: Array) -> void:
	# --- Load GLB furniture models (cache for reuse by _build_trash_cans) ---
	if _loader._furn_glb_meshes.is_empty():
		var furn_path := ProjectSettings.globalize_path("res://models/furniture/park_furniture/glb/parkfurnitures.glb")
		_loader._furn_glb_meshes = _loader._load_glb_meshes(furn_path)
	var furn_meshes: Dictionary = _loader._furn_glb_meshes
	if furn_meshes.is_empty():
		print("WARNING: furniture GLB not loaded, skipping furniture")
		return
	print("Furniture: loaded %d meshes from GLB" % furn_meshes.size())

	# --- Lamp meshes ---
	# Load CP-specific lamppost (Bishop's Crook style)
	var cp_lamp_path := ProjectSettings.globalize_path("res://models/furniture/cp_lamppost.glb")
	var cp_lamp_meshes: Dictionary = _loader._load_glb_meshes(cp_lamp_path)
	var lamp_meshes_formal: Array[Mesh] = []
	var lamp_meshes_standard: Array[Mesh] = []
	var lamp_meshes_simple: Array[Mesh] = []
	var _cp_lamp_loaded := false
	if cp_lamp_meshes.has("CP_Lamppost"):
		var cp_mesh: Mesh = cp_lamp_meshes["CP_Lamppost"] as Mesh
		lamp_meshes_formal.append(cp_mesh)
		lamp_meshes_standard.append(cp_mesh)
		lamp_meshes_simple.append(cp_mesh)
		_cp_lamp_loaded = true
		print("Lamp: loaded CP lamppost model (Bishop's Crook)")
	# Fallback to generic furniture GLB variants
	if not _cp_lamp_loaded:
		for lname in ["ParkFurn_Lamp_A", "ParkFurn_Lamp_B"]:
			if furn_meshes.has(lname):
				lamp_meshes_formal.append(furn_meshes[lname] as Mesh)
		for lname in ["ParkFurn_Lamp_C"]:
			if furn_meshes.has(lname):
				lamp_meshes_standard.append(furn_meshes[lname] as Mesh)
		for lname in ["ParkFurn_Lamp_D", "ParkFurn_Lamp_E"]:
			if furn_meshes.has(lname):
				lamp_meshes_simple.append(furn_meshes[lname] as Mesh)
	if lamp_meshes_standard.is_empty():
		print("WARNING: no lamp meshes found in GLB")
		return
	if lamp_meshes_formal.is_empty():
		lamp_meshes_formal = lamp_meshes_standard
	if lamp_meshes_simple.is_empty():
		lamp_meshes_simple = lamp_meshes_standard
	var lamp_post_mat := StandardMaterial3D.new()
	lamp_post_mat.albedo_color = Color(0.08, 0.08, 0.06)  # dark wrought iron
	lamp_post_mat.roughness    = 0.78
	lamp_post_mat.metallic     = 0.45
	var lamp_mat_override: Material = lamp_post_mat
	# Emissive bulb material (main.gd modulates emission for day/night)
	var lamp_bulb_mat := StandardMaterial3D.new()
	lamp_bulb_mat.albedo_color = Color(1.0, 0.72, 0.32)
	lamp_bulb_mat.roughness    = 0.3
	lamp_bulb_mat.emission_enabled = true
	lamp_bulb_mat.emission         = Color(0.0, 0.0, 0.0)  # start dark; main.gd modulates
	lamp_bulb_mat.emission_energy_multiplier = 0.0
	_loader.lamppost_material = lamp_bulb_mat

	# --- Bench mesh (CP-specific model with iron + wood materials baked in) ---
	var cp_bench_path := ProjectSettings.globalize_path("res://models/furniture/cp_bench.glb")
	var cp_bench_meshes: Dictionary = _loader._load_glb_meshes(cp_bench_path)
	var bench_mesh: Mesh = null
	if cp_bench_meshes.has("ParkFurn_Bench_CP"):
		bench_mesh = cp_bench_meshes["ParkFurn_Bench_CP"] as Mesh
		print("Bench: loaded CP bench model (iron + wood)")
	else:
		# Fallback: first available bench from furniture GLB
		for bname in ["ParkFurn_Bench_A", "ParkFurn_Bench_B", "ParkFurn_Bench_C"]:
			if furn_meshes.has(bname):
				bench_mesh = furn_meshes[bname] as Mesh
				break
	if bench_mesh == null:
		print("WARNING: no bench mesh found in GLB")
		return

	# --- Place lampposts: OSM positions + procedural supplement ---
	# Zone classification: formal areas get ornate lamps, naturalistic get standard,
	# recreational get simple utilitarian lamps
	# Formal: Mall/Literary Walk, Bethesda, Conservatory Garden
	# Simple/recreational: Great Lawn, fields, perimeter paths
	var lamp_xf_formal: Array = []
	var lamp_xf_standard: Array = []
	var lamp_xf_simple: Array = []
	# Always place OSM lampposts first (standard style)
	for lp in lamppost_data:
		var lx := float(lp[0])
		var lz := float(lp[2])
		if not _loader._in_boundary(lx, lz):
			continue
		var ly: float = _loader._terrain_y(lx, lz)
		var tf := Transform3D(Basis.IDENTITY, Vector3(lx, ly, lz))
		var zone: int = _loader._lamp_zone(lx, lz)
		if zone == 0:
			lamp_xf_formal.append(tf)
		elif zone == 2:
			lamp_xf_simple.append(tf)
		else:
			lamp_xf_standard.append(tf)
	var osm_lamp_count := lamp_xf_formal.size() + lamp_xf_standard.size() + lamp_xf_simple.size()
	var lamp_xf: Array = lamp_xf_formal + lamp_xf_standard + lamp_xf_simple

	# --- Place benches: OSM positions + procedural supplement ---
	var bench_xf: Array = []
	# Always place OSM benches first
	for b in bench_data:
		var bx := float(b[0])
		var bz := float(b[2])
		if not _loader._in_boundary(bx, bz):
			continue
		var by: float = _loader._terrain_y(bx, bz) + 0.42  # bench mesh origin is at center, lift to sit on terrain
		var dir_deg := float(b[3]) if b.size() > 3 else 0.0
		var angle := deg_to_rad(-dir_deg)
		var basis := Basis(Vector3.UP, angle)
		bench_xf.append(Transform3D(basis, Vector3(bx, by, bz)))
	var osm_bench_count := bench_xf.size()

	# Build spatial hash of bench positions (used by undergrowth to keep clear)
	var bench_grid_cell: float = _loader.BENCH_GRID_CELL
	for xf in bench_xf:
		var pos: Vector3 = xf.origin
		var fwd: Vector3 = xf.basis.z
		for step in 4:
			var px := pos.x + fwd.x * float(step)
			var pz := pos.z + fwd.z * float(step)
			var key := Vector2i(int(floor(px / bench_grid_cell)), int(floor(pz / bench_grid_cell)))
			_loader._bench_grid[key] = true

	print("ParkLoader: lampposts = %d (%d OSM + %d procedural)  benches = %d (%d OSM + %d procedural)" % [
		lamp_xf.size(), osm_lamp_count, lamp_xf.size() - osm_lamp_count,
		bench_xf.size(), osm_bench_count, bench_xf.size() - osm_bench_count])
	print("  Lamp zones: formal=%d, standard=%d, simple=%d" % [lamp_xf_formal.size(), lamp_xf_standard.size(), lamp_xf_simple.size()])
	# Spawn lamps per zone with appropriate mesh variants
	var bulb_mesh := SphereMesh.new()
	bulb_mesh.radius = 0.07
	bulb_mesh.height = 0.14
	bulb_mesh.radial_segments = 8
	bulb_mesh.rings = 4
	var all_bulb_xf: Array = []
	var zone_data: Array = [
		[lamp_xf_formal, lamp_meshes_formal, "Lampposts_Formal"],
		[lamp_xf_standard, lamp_meshes_standard, "Lampposts_Standard"],
		[lamp_xf_simple, lamp_meshes_simple, "Lampposts_Simple"],
	]
	for zd in zone_data:
		var xf_list: Array = zd[0]
		var meshes: Array = zd[1]
		var label: String = zd[2]
		if xf_list.is_empty() or meshes.is_empty():
			continue
		# Distribute across mesh variants
		var n_vars := meshes.size()
		var var_xf: Array = []
		for _v in n_vars:
			var_xf.append([])
		for i in xf_list.size():
			var_xf[i % n_vars].append(xf_list[i])
		for vi in n_vars:
			if not var_xf[vi].is_empty():
				_loader._spawn_multimesh(meshes[vi], lamp_mat_override, var_xf[vi], "%s_%d" % [label, vi])
		# Bulb positions for all lamps in this zone
		# CP lamppost globe at (0.45, 3.2, 0), generic at (0.012, 2.79, 0.475)
		var bulb_offset := Vector3(0.45, 3.2, 0.0) if _cp_lamp_loaded else Vector3(0.012, 2.79, 0.475)
		for xf in xf_list:
			var bxf: Transform3D = xf
			bxf.origin += bulb_offset
			all_bulb_xf.append(bxf)
	if not all_bulb_xf.is_empty():
		_loader._spawn_multimesh(bulb_mesh, lamp_bulb_mat, all_bulb_xf, "LampBulbs")
	# Spawn all benches with the CP bench model (materials baked into GLB)
	if not bench_xf.is_empty():
		_loader._spawn_multimesh(bench_mesh, null, bench_xf, "Benches_0")


func _build_trash_cans(trash_data: Array, paths: Array) -> void:
	## Trash receptacles from OSM data, with procedural fallback.
	# Load CP-specific trash can (green wire basket)
	var cp_tc_path := ProjectSettings.globalize_path("res://models/furniture/cp_trash_can.glb")
	var cp_tc_meshes: Dictionary = _loader._load_glb_meshes(cp_tc_path)
	var mesh: Mesh
	var mat: Material = null
	if cp_tc_meshes.has("CP_TrashCan"):
		mesh = cp_tc_meshes["CP_TrashCan"] as Mesh
		print("TrashCan: loaded CP trash can model (green wire)")
	elif _loader._furn_glb_meshes.has("ParkFurn_TrashCan_A"):
		mesh = _loader._furn_glb_meshes["ParkFurn_TrashCan_A"]
		var trash_mat := StandardMaterial3D.new()
		trash_mat.albedo_color = Color(0.08, 0.08, 0.06)
		trash_mat.roughness = 0.78
		trash_mat.metallic = 0.45
		mat = trash_mat
	else:
		print("WARNING: no trash can mesh found, skipping")
		return

	# Place from OSM data + procedural supplement
	var xforms: Array = []
	for tc in trash_data:
		var tx := float(tc[0])
		var tz := float(tc[2])
		if not _loader._in_boundary(tx, tz):
			continue
		var ty: float = _loader._terrain_y(tx, tz)
		xforms.append(Transform3D(Basis.IDENTITY, Vector3(tx, ty, tz)))
	var osm_trash_count := xforms.size()
	if true:
		var rng := RandomNumberGenerator.new()
		rng.seed = 77711
		for path in paths:
			var hw: String = str(path.get("highway", "path"))
			if hw == "cycleway" or hw == "track" or hw == "steps":
				continue
			if bool(path.get("bridge", false)) or bool(path.get("tunnel", false)):
				continue
			var pts: Array = path["points"]
			if pts.size() < 2:
				continue
			var half_w: float = _loader._hw_width(hw) * 0.5
			var cum := 0.0
			var next := rng.randf_range(45.0, 75.0)
			var side := 1.0 if rng.randf() > 0.5 else -1.0
			for pi in range(1, pts.size()):
				var x0 := float(pts[pi-1][0]); var z0 := float(pts[pi-1][2])
				var x1 := float(pts[pi][0]);   var z1 := float(pts[pi][2])
				var dx := x1 - x0; var dz := z1 - z0
				var seg_len := sqrt(dx * dx + dz * dz)
				if seg_len < 0.01:
					continue
				cum += seg_len
				if cum >= next:
					cum = 0.0
					next = rng.randf_range(50.0, 70.0)
					side = -side
					var nx := -dz / seg_len; var nz := dx / seg_len
					var tx := x1 + nx * (half_w + 0.6) * side
					var tz := z1 + nz * (half_w + 0.6) * side
					if not _loader._in_boundary(tx, tz):
						continue
					var bridge_grid_cell: float = _loader.BRIDGE_GRID_CELL
					var bgk := Vector2i(int(floor(tx / bridge_grid_cell)), int(floor(tz / bridge_grid_cell)))
					if _loader._bridge_grid.has(bgk):
						continue
					var ty: float = _loader._terrain_y(tx, tz)
					xforms.append(Transform3D(Basis.IDENTITY, Vector3(tx, ty, tz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, mat, xforms, "TrashCans")
	print("ParkLoader: trash cans = %d (from %s)" % [
		xforms.size(), "OSM" if not trash_data.is_empty() else "procedural"])


# ---------------------------------------------------------------------------
# Water grid population -- marks cells near water bodies for exclusion
# ---------------------------------------------------------------------------
func _populate_water_grid(water: Array) -> void:
	var water_grid_cell: float = _loader.WATER_GRID_CELL
	for body in water:
		var pts: Array = body["points"]
		if pts.size() < 3:
			continue
		for pi in pts.size():
			var sx := float(pts[pi][0])
			var sz := float(pts[pi][1])
			# Mark a radius of ~12m around each shore point
			for dx in range(-3, 4):
				for dz in range(-3, 4):
					var key := Vector2i(
						int(floor(sx / water_grid_cell)) + dx,
						int(floor(sz / water_grid_cell)) + dz)
					_loader._water_grid[key] = true


func _bobbing_shader_code() -> String:
	return """shader_type spatial;
render_mode cull_disabled;

uniform vec3 base_color : source_color = vec3(0.45, 0.30, 0.15);

varying vec3 origin;

void vertex() {
	origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float bob = sin(TIME * 0.8 + origin.x * 0.3 + origin.z * 0.5) * 0.05;
	VERTEX.y += bob;
	// Gentle rock
	float rock = sin(TIME * 0.5 + origin.z * 0.2) * 0.02;
	VERTEX.x += rock * VERTEX.y;
}

void fragment() {
	ALBEDO = base_color;
	ROUGHNESS = 0.75;
	SPECULAR = 0.1;
	METALLIC = 0.0;
}
"""

func _make_boat_mesh() -> ArrayMesh:
	## Simple rowing boat hull: elongated oval, open top, 2 seat planks, 2 oars.
	var v := PackedVector3Array(); var n := PackedVector3Array(); var idx := PackedInt32Array()
	var hull_len := 1.25  # half-length
	var hull_w := 0.50    # half-width
	var hull_d := 0.25    # depth
	var segs := 10
	# Hull sides: ring of quads
	for i in segs:
		var a0 := TAU * float(i) / float(segs)
		var a1 := TAU * float(i + 1) / float(segs)
		var x0 := cos(a0) * hull_len; var z0 := sin(a0) * hull_w
		var x1 := cos(a1) * hull_len; var z1 := sin(a1) * hull_w
		var base := v.size()
		v.append(Vector3(x0, -hull_d, z0))
		v.append(Vector3(x1, -hull_d, z1))
		v.append(Vector3(x1, 0.05, z1))
		v.append(Vector3(x0, 0.05, z0))
		var nn := Vector3(sin(a0), 0.0, cos(a0)).normalized()
		for _j in 4: n.append(nn)
		idx.append_array(PackedInt32Array([base, base+1, base+2, base, base+2, base+3]))
	# Bottom (flat)
	var base := v.size()
	for i in segs:
		var a0 := TAU * float(i) / float(segs)
		v.append(Vector3(cos(a0) * hull_len * 0.9, -hull_d, sin(a0) * hull_w * 0.9))
		n.append(Vector3.DOWN)
	v.append(Vector3(0.0, -hull_d, 0.0)); n.append(Vector3.DOWN)
	var center_idx := base + segs
	for i in segs:
		idx.append_array(PackedInt32Array([center_idx, base + (i + 1) % segs, base + i]))
	# 2 seat planks
	_loader._add_box_verts(v, n, idx, 0.0, 0.0, 0.0, 0.08, 0.02, hull_w * 0.8)
	_loader._add_box_verts(v, n, idx, -0.5, 0.0, 0.0, 0.08, 0.02, hull_w * 0.8)
	# 2 oars (thin cylinders angled outward)
	_loader._add_box_verts(v, n, idx, 0.0, 0.08, hull_w + 0.3, 0.7, 0.015, 0.015)
	_loader._add_box_verts(v, n, idx, 0.0, 0.08, -hull_w - 0.3, 0.7, 0.015, 0.015)
	var mesh: ArrayMesh = _loader._make_mesh(v, n, null, null, idx)
	return mesh

func _build_boats(water: Array) -> void:
	## Scatter ~12 rowing boats on "The Lake" (largest water body).
	if water.is_empty():
		return
	# Find the largest water body by point count (The Lake)
	var lake_idx := 0
	var max_pts := 0
	for wi in water.size():
		if water[wi]["points"].size() > max_pts:
			max_pts = water[wi]["points"].size()
			lake_idx = wi
	var lake_pts: Array = water[lake_idx]["points"]
	if lake_pts.size() < 3:
		return
	# Compute lake centroid and scatter boats around it
	var rng := RandomNumberGenerator.new()
	rng.seed = 55533
	var cx := 0.0; var cz := 0.0
	for pt in lake_pts:
		cx += float(pt[0]); cz += float(pt[1])
	cx /= float(lake_pts.size()); cz /= float(lake_pts.size())
	var boat_mesh := _make_boat_mesh()
	var boat_sh: Shader = _loader._get_shader("boat_bob", _bobbing_shader_code())
	var boat_mat := ShaderMaterial.new()
	boat_mat.shader = boat_sh
	boat_mat.set_shader_parameter("base_color", Vector3(0.45, 0.30, 0.15))
	var xforms: Array = []
	var water_grid_cell: float = _loader.WATER_GRID_CELL
	var water_y: float = _loader.WATER_Y
	for _bi in 12:
		# Place 15-30m from random shore point, but toward centroid
		var shore_i := rng.randi_range(0, lake_pts.size() - 1)
		var sx := float(lake_pts[shore_i][0])
		var sz := float(lake_pts[shore_i][1])
		var to_center := Vector2(cx - sx, cz - sz).normalized()
		var dist := rng.randf_range(15.0, 35.0)
		var bx := sx + to_center.x * dist
		var bz := sz + to_center.y * dist
		# Check it's actually on water
		var wgk := Vector2i(int(floor(bx / water_grid_cell)), int(floor(bz / water_grid_cell)))
		if not _loader._water_grid.has(wgk):
			continue
		var by: float = water_y
		var angle := rng.randf() * TAU
		var basis := Basis(Vector3.UP, angle)
		xforms.append(Transform3D(basis, Vector3(bx, by, bz)))
	if not xforms.is_empty():
		_loader._spawn_multimesh(boat_mesh, boat_mat, xforms, "RowingBoats")
	print("ParkLoader: rowing boats = ", xforms.size())
