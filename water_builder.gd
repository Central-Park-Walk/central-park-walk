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
	var rw_alb: ImageTexture = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: ImageTexture = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: ImageTexture = _loader._load_tex("res://textures/rock_wall_rgh.jpg")

	var lname := bname.to_lower()
	_build_fountain_pool(pts, pool_y)

	if lname.contains("bethesda"):
		_build_bethesda_fountain(cx, cz, base_y, max_r, rw_alb, rw_nrm, rw_rgh)
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
	mesh.surface_set_material(0, wmat)
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.name = "FountainPool"
	_loader.add_child(mi)





# -- Bethesda Fountain: photogrammetry GLB ------
func _build_bethesda_fountain(cx: float, cz: float, base_y: float, pool_r: float,
							  alb: ImageTexture, nrm: ImageTexture, rgh: ImageTexture) -> void:
	var glb_path := ProjectSettings.globalize_path("res://models/bethesda_fountain_photogrammetry.glb")
	if FileAccess.file_exists("res://models/bethesda_fountain_photogrammetry.glb") or FileAccess.file_exists(glb_path):
		var gltf_doc := GLTFDocument.new()
		var gltf_state := GLTFState.new()
		var err := gltf_doc.append_from_file(glb_path, gltf_state)
		if err == OK:
			var scene: Node = gltf_doc.generate_scene(gltf_state)
			if scene:
				var node3d := Node3D.new()
				node3d.name = "Bethesda_Photogrammetry"
				var glb_scale := 5.0
				node3d.scale = Vector3(glb_scale, glb_scale, glb_scale)
				node3d.position = Vector3(cx, base_y + 0.45, cz)
				var children: Array = []
				for c in scene.get_children():
					children.append(c)
				for c in children:
					scene.remove_child(c)
					node3d.add_child(c)
				scene.queue_free()
				_loader.add_child(node3d)
				print("ParkLoader: Bethesda Fountain photogrammetry placed at (%.0f, %.0f)" % [cx, cz])
		else:
			print("WARNING: failed to load Bethesda GLB: error %d" % err)



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
	return """shader_type spatial;
render_mode cull_disabled;

void fragment() {
	// UV 0..1, center at 0.5
	vec2 c = UV - 0.5;
	float r = length(c);
	float angle = atan(c.y, c.x);

	// Concentric bands + radial spokes = starburst
	float radial = sin(angle * 16.0);  // 16 radial spokes
	float rings  = sin(r * 40.0);      // concentric rings

	// Combine for mosaic pattern
	float pattern = radial * 0.5 + rings * 0.5;

	// Inner circle: solid with IMAGINE text area
	float inner = smoothstep(0.08, 0.10, r);

	// Outer border ring
	float border = smoothstep(0.46, 0.48, r) * (1.0 - smoothstep(0.49, 0.50, r));

	// Black and warm-white stones
	vec3 white_stone = vec3(0.91, 0.88, 0.82);  // #E8E0D0
	vec3 black_stone = vec3(0.10, 0.10, 0.10);  // #1A1A1A
	vec3 col = mix(black_stone, white_stone, step(0.0, pattern) * inner);

	// Central medallion area (r < 0.10): warm white for text
	col = mix(white_stone, col, inner);

	// Border ring: black
	col = mix(col, black_stone, border);

	// Outside circle: gray path surround
	float outside = smoothstep(0.49, 0.50, r);
	col = mix(col, vec3(0.45, 0.43, 0.40), outside);

	// Subtle stone grain noise
	float grain = fract(sin(dot(UV * 200.0, vec2(12.9898, 78.233))) * 43758.5453);
	col += (grain - 0.5) * 0.03;

	ALBEDO = col;
	ROUGHNESS = 0.75;
	METALLIC = 0.0;
	SPECULAR = 0.2;
	NORMAL_MAP = vec3(0.5, 0.5, 1.0);
}
""";



# ---------------------------------------------------------------------------
# Water bodies – filled polygons triangulated with Geometry2D
# ---------------------------------------------------------------------------
func _build_water(water: Array) -> void:
	if water.is_empty():
		return

	var verts   := PackedVector3Array()
	var normals := PackedVector3Array()
	const WATER_CELL := 4.0  # grid cell size in metres for dense interior mesh

	for body in water:
		var pts: Array = body["points"]
		if pts.size() < 3:
			continue
		# Skip water bodies whose centroid is outside the park
		var _wcx := 0.0; var _wcz := 0.0
		for _wpt in pts:
			_wcx += float(_wpt[0]); _wcz += float(_wpt[1])
		_wcx /= float(pts.size()); _wcz /= float(pts.size())
		if not _loader._in_boundary(_wcx, _wcz):
			continue

		# Skip oversized water bodies (rivers, ocean) — max valid is Reservoir ~800m
		var _bmin_x := INF; var _bmax_x := -INF
		var _bmin_z := INF; var _bmax_z := -INF
		for _wpt in pts:
			_bmin_x = minf(_bmin_x, float(_wpt[0]))
			_bmax_x = maxf(_bmax_x, float(_wpt[0]))
			_bmin_z = minf(_bmin_z, float(_wpt[1]))
			_bmax_z = maxf(_bmax_z, float(_wpt[1]))
		if (_bmax_x - _bmin_x) > 1000.0 or (_bmax_z - _bmin_z) > 1000.0:
			continue

		# Check if this water body is a fountain — build 3D structure instead
		var bname: String = str(body.get("name", ""))
		if bname.to_lower().contains("fountain"):
			_build_fountain(body)
			continue

		# Conservatory Water: add Atlantic Blue granite curb ring
		if bname.to_lower().contains("conservatory"):
			_build_water_curb(pts, Color(0.36, 0.42, 0.48))  # Atlantic Blue granite

		# Water level = minimum terrain height along the shore + small offset.
		var wy := INF
		for pt in pts:
			var hh: float = _loader._terrain_y(float(pt[0]), float(pt[1]))
			wy = minf(wy, hh)
		wy += _loader.WATER_Y

		var polygon := PackedVector2Array()
		for pt in pts:
			polygon.append(Vector2(float(pt[0]), float(pt[1])))

		# Expand polygon slightly (3m) so water fills under bridge crossings
		var expanded := Geometry2D.offset_polygon(polygon, 3.0)
		if not expanded.is_empty():
			polygon = expanded[0]

		# Store polygon edges for water proximity baking
		_loader._water_polygons.append(polygon)

		# Grid-based mesh: dense interior vertices so terrain clamping works
		# Without this, large triangles span the lake and terrain pokes through.
		var bb_min_x := INF; var bb_max_x := -INF
		var bb_min_z := INF; var bb_max_z := -INF
		for pt2 in polygon:
			bb_min_x = minf(bb_min_x, pt2.x); bb_max_x = maxf(bb_max_x, pt2.x)
			bb_min_z = minf(bb_min_z, pt2.y); bb_max_z = maxf(bb_max_z, pt2.y)

		var nx := int(ceil((bb_max_x - bb_min_x) / WATER_CELL)) + 1
		var nz := int(ceil((bb_max_z - bb_min_z) / WATER_CELL)) + 1

		# Build grid of inside flags
		var inside: Array = []
		inside.resize((nx + 1) * (nz + 1))
		for zi in range(nz + 1):
			for xi in range(nx + 1):
				var gx := bb_min_x + xi * WATER_CELL
				var gz := bb_min_z + zi * WATER_CELL
				var idx := zi * (nx + 1) + xi
				inside[idx] = Geometry2D.is_point_in_polygon(Vector2(gx, gz), polygon)

		# Emit two triangles per grid cell where all 4 corners are inside
		for zi in range(nz):
			for xi in range(nx):
				var i00 := zi * (nx + 1) + xi
				var i10 := i00 + 1
				var i01 := (zi + 1) * (nx + 1) + xi
				var i11 := i01 + 1
				if not (inside[i00] and inside[i10] and inside[i01] and inside[i11]):
					continue
				var x0 := bb_min_x + xi * WATER_CELL
				var x1 := x0 + WATER_CELL
				var z0 := bb_min_z + zi * WATER_CELL
				var z1 := z0 + WATER_CELL
				# Triangle 1: (x0,z0) (x1,z0) (x1,z1)
				for tri_pt in [Vector2(x0,z0), Vector2(x1,z0), Vector2(x1,z1),
							   Vector2(x0,z0), Vector2(x1,z1), Vector2(x0,z1)]:
					var ty: float = _loader._terrain_y(tri_pt.x, tri_pt.y) + _loader.WATER_Y
					verts.append(Vector3(tri_pt.x, maxf(wy, ty), tri_pt.y))
					normals.append(Vector3.UP)

	if verts.is_empty():
		return

	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)

	var mat := ShaderMaterial.new()
	mat.shader = _loader._get_shader("water", _water_shader_code())
	# Heightmap for vertex-shader terrain clamping
	if _loader._hm_texture:
		mat.set_shader_parameter("heightmap_tex", _loader._hm_texture)
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		mat.set_shader_parameter("hm_min_h",      _loader._hm_min_h)
		mat.set_shader_parameter("hm_range",      _loader._hm_max_h - _loader._hm_min_h)
		mat.set_shader_parameter("hm_res",        float(mini(_loader._hm_width, 4096)))
	mesh.surface_set_material(0, mat)

	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "WaterBodies"
	_loader.add_child(mi)


func _build_water_curb(pts: Array, tint: Color) -> void:
	## Build a raised stone curb ring around a water body (e.g. Conservatory Water).
	var rw_alb: ImageTexture = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: ImageTexture = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: ImageTexture = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
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
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.name = "WaterCurb_Conservatory"
	_loader.add_child(mi)
	print("ParkLoader: Conservatory Water curb (%d segments)" % pts.size())


func _build_streams(streams: Array) -> void:
	if streams.is_empty():
		return
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	const STREAM_W := 1.5  # half-width in metres

	for stream in streams:
		var pts: Array = stream.get("points", [])
		if pts.size() < 2:
			continue
		# Build ribbon mesh along polyline
		for i in range(pts.size() - 1):
			var x0: float = pts[i][0]
			var y0: float = pts[i][1]
			var z0: float = pts[i][2]
			var x1: float = pts[i + 1][0]
			var y1: float = pts[i + 1][1]
			var z1: float = pts[i + 1][2]

			# Direction and perpendicular
			var dx := x1 - x0
			var dz := z1 - z0
			var ln := sqrt(dx * dx + dz * dz)
			if ln < 0.01:
				continue
			var nx := -dz / ln * STREAM_W
			var nz := dx / ln * STREAM_W

			# Clamp Y to terrain + small offset so stream sits on surface
			var ty0: float = _loader._terrain_y(x0, z0) + 0.05
			var ty1: float = _loader._terrain_y(x1, z1) + 0.05
			y0 = maxf(y0, ty0)
			y1 = maxf(y1, ty1)

			# Two triangles per segment
			var a := Vector3(x0 - nx, y0, z0 - nz)
			var b := Vector3(x0 + nx, y0, z0 + nz)
			var c := Vector3(x1 + nx, y1, z1 + nz)
			var d := Vector3(x1 - nx, y1, z1 - nz)
			verts.append(a); verts.append(b); verts.append(c)
			verts.append(a); verts.append(c); verts.append(d)
			for _j in 6:
				normals.append(Vector3.UP)

	if verts.is_empty():
		return

	var s_mesh: ArrayMesh = _loader._make_mesh(verts, normals)

	var mat := ShaderMaterial.new()
	mat.shader = _loader._get_shader("water", _water_shader_code())
	if _loader._hm_texture:
		mat.set_shader_parameter("heightmap_tex", _loader._hm_texture)
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		mat.set_shader_parameter("hm_min_h",      _loader._hm_min_h)
		mat.set_shader_parameter("hm_range",      _loader._hm_max_h - _loader._hm_min_h)
		mat.set_shader_parameter("hm_res",        float(mini(_loader._hm_width, 4096)))
	s_mesh.surface_set_material(0, mat)

	var s_mi := MeshInstance3D.new()
	s_mi.mesh = s_mesh
	s_mi.name = "Streams"
	_loader.add_child(s_mi)
	print("  Streams: %d polylines, %d triangles" % [streams.size(), verts.size() / 3])


func _water_shader_code() -> String:
	return """shader_type spatial;
render_mode cull_disabled;

uniform sampler2D heightmap_tex : filter_nearest, repeat_disable;
uniform float hm_world_size = 5000.0;
uniform float hm_min_h      = 0.0;
uniform float hm_range      = 1.0;
uniform float hm_res        = 256.0;
uniform float water_y_offset = 0.03;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

varying vec3 world_pos;
varying float v_shore_dist;
varying float v_water_depth;

// Raindrop ripple rings — concentric circles from random impact points
float raindrop_ripple(vec2 p) {
	float t = TIME;
	float ripple = 0.0;
	for (int i = 0; i < 6; i++) {
		vec2 cell = floor(p * (1.5 + float(i) * 0.3)) + vec2(float(i) * 17.3, float(i) * 31.7);
		vec2 center = cell + vec2(fract(sin(dot(cell, vec2(127.1, 311.7))) * 43758.5453),
		                          fract(sin(dot(cell, vec2(269.5, 183.3))) * 43758.5453));
		float phase = fract(sin(dot(cell, vec2(113.5, 271.9))) * 43758.5453) * 3.0;
		float age = fract(t * 0.4 + phase);
		float dist = length(p * (1.5 + float(i) * 0.3) - center);
		float ring = sin((dist - age * 3.0) * 18.0) * exp(-dist * 2.5) * (1.0 - age);
		ripple += ring * 0.15;
	}
	return ripple;
}
""" + _loader.GLSL_DECODE_TERRAIN + """

// Gradient noise (returns -1..1)
vec2 ghash(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453) * 2.0 - 1.0;
}
float gnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(dot(ghash(i),          f),
	               dot(ghash(i+vec2(1,0)), f-vec2(1,0)), u.x),
	           mix(dot(ghash(i+vec2(0,1)), f-vec2(0,1)),
	               dot(ghash(i+vec2(1,1)), f-vec2(1,1)), u.x), u.y);
}

// World-space wave normal from three overlapping noise layers
vec3 wave_normal(vec2 uv) {
	float t  = TIME;
	vec2 o1  = vec2( t * 0.08,  t * 0.05);   // slow drift
	vec2 o2  = vec2(-t * 0.12,  t * 0.09);   // medium ripples
	vec2 o3  = vec2( t * 0.18, -t * 0.14);   // fine detail
	float e  = 0.04;
	float h   = gnoise(uv * 0.7 + o1) * 0.4
	          + gnoise(uv * 1.8 + o2) * 0.35
	          + gnoise(uv * 4.5 + o3) * 0.25;
	float hx  = gnoise((uv + vec2(e, 0.0)) * 0.7 + o1) * 0.4
	          + gnoise((uv + vec2(e, 0.0)) * 1.8 + o2) * 0.35
	          + gnoise((uv + vec2(e, 0.0)) * 4.5 + o3) * 0.25;
	float hz  = gnoise((uv + vec2(0.0, e)) * 0.7 + o1) * 0.4
	          + gnoise((uv + vec2(0.0, e)) * 1.8 + o2) * 0.35
	          + gnoise((uv + vec2(0.0, e)) * 4.5 + o3) * 0.25;
	return normalize(vec3(-(hx - h) / e * 0.20, 1.0, -(hz - h) / e * 0.20));
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	// Clamp water Y so it never pokes below the terrain surface
	float terrain_h = sample_terrain(w.xz) + water_y_offset;
	if (w.y < terrain_h) {
		vec3 snapped = (inverse(MODEL_MATRIX) * vec4(w.x, terrain_h, w.z, 1.0)).xyz;
		VERTEX.y = snapped.y;
		w.y = terrain_h;
	}
	world_pos = w;
	// Shore softening: sample terrain at 4 neighboring points
	float step_d = 3.0;
	float t_n = sample_terrain(w.xz + vec2(0.0, -step_d));
	float t_s = sample_terrain(w.xz + vec2(0.0,  step_d));
	float t_e = sample_terrain(w.xz + vec2( step_d, 0.0));
	float t_w = sample_terrain(w.xz + vec2(-step_d, 0.0));
	float max_neighbor = max(max(t_n, t_s), max(t_e, t_w));
	v_shore_dist = max(0.0, w.y - max_neighbor) * 3.0 + 0.5;
	if (max_neighbor > w.y) { v_shore_dist = max(0.0, w.y - max_neighbor + 0.5); }
	// Depth tinting
	float bed_h = sample_terrain(w.xz);
	v_water_depth = max(0.0, w.y - bed_h);
}

void fragment() {
	vec2 uv      = world_pos.xz / 12.0;   // natural wave scale
	vec3 wave_nrm = wave_normal(uv);

	// Three noise layers at different scales for natural variation
	float t = TIME;
	float n_large = gnoise(uv * 0.4 + vec2(t * 0.06, t * 0.04));
	float n_med   = gnoise(uv * 1.2 + vec2(-t * 0.1, t * 0.08));
	float n_fine  = gnoise(uv * 3.5 + vec2(t * 0.15, -t * 0.12));
	float wave_h  = n_large * 0.4 + n_med * 0.35 + n_fine * 0.25;

	vec3 deep    = vec3(0.020, 0.038, 0.028);   // dark olive-green (Central Park lakes)
	vec3 shallow = vec3(0.050, 0.075, 0.045);   // slightly warmer shallow
	float extra_reflect = 0.0;

	// Per-water-body character based on world position
	// Conservatory Water (Model Boat Pond): shallow formal reflecting pool
	float d_conserv = length(world_pos.xz - vec2(-152.0, 958.0));
	if (d_conserv < 80.0) {
		deep    = vec3(0.035, 0.050, 0.045);   // lighter, blue-gray
		shallow = vec3(0.065, 0.085, 0.075);
		extra_reflect = 0.15;
	}
	// Turtle Pond: shallow, murky, dark green-brown
	float d_turtle = length(world_pos.xz - vec2(-213.0, 374.0));
	if (d_turtle < 120.0) {
		deep    = vec3(0.018, 0.030, 0.020);   // darker, murkier
		shallow = vec3(0.040, 0.055, 0.035);
	}
	// Reservoir: large, open, more reflective blue
	float d_reserv = length(world_pos.xz - vec2(282.0, -424.0));
	if (d_reserv < 500.0) {
		deep    = vec3(0.015, 0.030, 0.035);   // blue-tinted deep
		shallow = vec3(0.040, 0.065, 0.070);
		extra_reflect = 0.10;
	}
	// Harlem Meer: large, dark green-blue, reflective
	float d_meer = length(world_pos.xz - vec2(1132.0, -1494.0));
	if (d_meer < 250.0) {
		deep    = vec3(0.015, 0.032, 0.032);
		shallow = vec3(0.040, 0.060, 0.058);
		extra_reflect = 0.08;
	}
	// The Pool (North Woods): secluded, dark, tree-shadowed
	float d_pool = length(world_pos.xz - vec2(-400.0, -1100.0));
	if (d_pool < 80.0) {
		deep    = vec3(0.012, 0.025, 0.018);   // very dark, canopy-shadowed
		shallow = vec3(0.030, 0.048, 0.032);
	}
	// The Lake (main): classic Central Park, moderate reflectivity
	float d_lake = length(world_pos.xz - vec2(-420.0, 740.0));
	if (d_lake < 250.0) {
		deep    = vec3(0.018, 0.034, 0.028);   // natural dark green
		shallow = vec3(0.045, 0.065, 0.050);
		extra_reflect = 0.05;
	}

	// Subtle blend — mostly deep, shallow only at wave peaks
	vec3 base_col = mix(deep, shallow, smoothstep(-0.3, 0.6, wave_h));

	// Rain ripples — concentric ring disturbance when raining
	if (rain_wetness > 0.01) {
		float rr = raindrop_ripple(world_pos.xz / 6.0);
		float e = 0.02;
		float rr_dx = raindrop_ripple((world_pos.xz + vec2(e, 0.0)) / 6.0);
		float rr_dz = raindrop_ripple((world_pos.xz + vec2(0.0, e)) / 6.0);
		vec3 ripple_n = normalize(vec3(
			-(rr_dx - rr) / e * 0.3,
			1.0,
			-(rr_dz - rr) / e * 0.3
		));
		wave_nrm = normalize(mix(wave_nrm, ripple_n, rain_wetness * 0.6));
	}

	NORMAL    = normalize((VIEW_MATRIX * vec4(wave_nrm, 0.0)).xyz);

	// Fresnel — glancing angles reflect sky (color tracks time of day)
	float fresnel = pow(1.0 - max(dot(NORMAL, VIEW), 0.0), 4.0);
	vec3 sky_col = sky_reflect_color;
	vec3 col = mix(base_col, sky_col, fresnel * (0.6 + extra_reflect));

	// Foam — white caps at wave peaks (subtle in ponds, more on reservoir)
	float foam = smoothstep(0.6, 0.85, wave_h);
	col = mix(col, vec3(0.85, 0.90, 0.92), foam * 0.7);

	ALBEDO    = col;
	ROUGHNESS = mix(0.12, 0.02, fresnel);
	METALLIC  = 0.05;
	SPECULAR  = 0.5;
	// Shore softening — fade alpha near edges
	ALPHA     = smoothstep(0.0, 1.5, v_shore_dist);
}
"""
