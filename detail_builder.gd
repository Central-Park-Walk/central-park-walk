## Detail builder — small repeated park elements: fences, signs, equipment, grates.

var _loader



func _init(loader) -> void:
	_loader = loader



# ---------------------------------------------------------------------------
# Dog run fencing — chain-link fence around 3 off-leash dog areas
# ---------------------------------------------------------------------------
func _build_dog_run_fences(landuse: Array) -> void:
	var fence_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_dog_run_fence.glb")
	if fence_mesh == null:
		return

	# Fence section is 3m wide — instance along polygon perimeters
	const SECTION_W := 3.0
	var xforms: Array = []
	var run_count := 0

	for zone in landuse:
		if str(zone.get("type", "")) != "dog_park":
			continue
		var pts: Array = zone.get("points", [])
		if pts.size() < 3:
			continue
		run_count += 1

		# Walk polygon perimeter, placing fence sections every SECTION_W metres
		for pi in pts.size():
			var p0x: float = float(pts[pi][0])
			var p0z: float = float(pts[pi][1])
			var ni: int = (pi + 1) % pts.size()
			var p1x: float = float(pts[ni][0])
			var p1z: float = float(pts[ni][1])

			var dx: float = p1x - p0x
			var dz: float = p1z - p0z
			var seg_len: float = sqrt(dx * dx + dz * dz)
			if seg_len < 0.5:
				continue

			var n_sections: int = maxi(1, int(round(seg_len / SECTION_W)))
			var yaw: float = atan2(dx, dz)

			for si in n_sections:
				var t: float = (float(si) + 0.5) / float(n_sections)
				var fx: float = p0x + dx * t
				var fz: float = p0z + dz * t
				var fy: float = _loader._terrain_y(fx, fz)
				var basis := Basis(Vector3.UP, yaw)
				xforms.append(Transform3D(basis, Vector3(fx, fy, fz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(fence_mesh, null, xforms, "DogRunFences")
	print("  Dog run fences: %d sections around %d runs" % [xforms.size(), run_count])


# ---------------------------------------------------------------------------
# Park wayfinding signs — brown wooden signs at major path intersections
# ---------------------------------------------------------------------------
func _build_park_signs(paths: Array) -> void:
	var sign_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_park_sign.glb")
	if sign_mesh == null:
		return

	# Apply wood shader if available, otherwise keep GLB material
	var wood_sh: Shader = _loader._get_shader("wood", "res://shaders/wood.gdshader")
	if wood_sh:
		for si in sign_mesh.get_surface_count():
			var wood_mat := ShaderMaterial.new()
			wood_mat.shader = wood_sh
			wood_mat.set_shader_parameter("wood_color", Vector3(0.25, 0.15, 0.08))
			sign_mesh.surface_set_material(si, wood_mat)

	# Find path intersections — collect all path endpoints, cluster them
	const GRID_SIZE := 10.0
	var grid: Dictionary = {}  # "gx|gz" -> Array of [x, z]

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw in ["secondary", "service", "tertiary", "residential"]:
			continue  # skip roads
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue
		# Start and end points
		for pidx in [0, pts.size() - 1]:
			var pt: Array = pts[pidx]
			var px: float = float(pt[0])
			var pz: float = float(pt[2]) if pt.size() > 2 else float(pt[1])
			var gx: int = int(floorf(px / GRID_SIZE))
			var gz: int = int(floorf(pz / GRID_SIZE))
			var gk: String = "%d|%d" % [gx, gz]
			if not grid.has(gk):
				grid[gk] = []
			grid[gk].append([px, pz])

	# Find cells with 3+ path endpoints = intersection
	var intersections: Array = []
	for gk in grid:
		var pts: Array = grid[gk]
		if pts.size() >= 3:
			var cx := 0.0
			var cz := 0.0
			for p in pts:
				cx += float(p[0])
				cz += float(p[1])
			cx /= float(pts.size())
			cz /= float(pts.size())
			intersections.append([cx, cz, pts.size()])

	# Sort by connectivity (most paths first), deduplicate within 20m
	intersections.sort_custom(func(a: Array, b: Array) -> bool: return int(a[2]) > int(b[2]))
	var final: Array = []
	for inter in intersections:
		var ix: float = float(inter[0])
		var iz: float = float(inter[1])
		if not _loader._in_boundary(ix, iz):
			continue
		var too_close := false
		for f in final:
			var fdx: float = ix - float(f[0])
			var fdz: float = iz - float(f[1])
			if fdx * fdx + fdz * fdz < 400.0:  # 20m minimum spacing
				too_close = true
				break
		if not too_close:
			final.append(inter)
		if final.size() >= 80:  # cap at ~80 signs (realistic for CP)
			break

	# Place signs
	var xforms: Array = []
	var rng := RandomNumberGenerator.new()
	for f in final:
		var fx: float = float(f[0])
		var fz: float = float(f[1])
		var fy: float = _loader._terrain_y(fx, fz)
		rng.seed = int(fx * 73856.0 + fz * 19349.0) & 0x7FFFFFFF
		var yaw: float = rng.randf() * TAU  # random facing
		var basis := Basis(Vector3.UP, yaw)
		xforms.append(Transform3D(basis, Vector3(fx, fy, fz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(sign_mesh, null, xforms, "ParkSigns")
	print("  Park signs: %d placed at path intersections" % xforms.size())

	# Named gate labels at park entrances
	var gate_names: Array = [
		["Merchants' Gate", -1050.0, 2025.0],
		["Women's Gate", -1100.0, 1800.0],
		["Artisans' Gate", -1050.0, 1575.0],
		["Naturalists' Gate", -1100.0, 1200.0],
		["Hunters' Gate", -1100.0, 750.0],
		["Mariners' Gate", -1100.0, 225.0],
		["Gate of All Saints", -1100.0, -375.0],
		["Boys' Gate", -1100.0, -900.0],
		["Strangers' Gate", -1100.0, -1500.0],
		["Farmers' Gate", 300.0, -2000.0],
		["Warriors' Gate", 700.0, -2000.0],
		["Pioneers' Gate", 1200.0, -2000.0],
		["Woodsmen's Gate", 1200.0, -1350.0],
		["Girls' Gate", 1200.0, -750.0],
		["Engineers' Gate", 1200.0, -225.0],
		["Inventors' Gate", 1200.0, 225.0],
		["Miners' Gate", 1200.0, 750.0],
		["Children's Gate", 1200.0, 1125.0],
		["Scholars' Gate", 1200.0, 1950.0],
	]
	var gate_label_count := 0
	for g in gate_names:
		var gname: String = str(g[0])
		var gx: float = float(g[1])
		var gz: float = float(g[2])
		var gy: float = _loader._terrain_y(gx, gz)
		var label := Label3D.new()
		label.text = gname
		label.font_size = 32
		label.position = Vector3(gx, gy + 3.5, gz)
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.modulate = Color(0.45, 0.35, 0.20, 0.75)
		label.outline_modulate = Color(0.1, 0.08, 0.05, 0.55)
		label.outline_size = 5
		label.no_depth_test = false
		label.pixel_size = 0.012
		_loader.add_child(label)
		gate_label_count += 1
	print("  Gate labels: %d named entrances" % gate_label_count)

	# Named path labels at midpoints of major park paths
	var path_label_count := 0
	var labeled_paths: Dictionary = {}  # dedup by name
	for path in paths:
		var pname: String = str(path.get("name", ""))
		if pname.is_empty():
			continue
		var hw: String = str(path.get("highway", ""))
		if hw in ["secondary", "tertiary", "residential", "service"]:
			continue  # skip roads
		if pname in labeled_paths:
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 5:
			continue
		# Use midpoint
		var mid: int = pts.size() / 2
		var mx: float = float(pts[mid][0])
		var mz: float = float(pts[mid][2]) if len(pts[mid]) > 2 else float(pts[mid][1])
		if not _loader._in_boundary(mx, mz):
			continue
		var my: float = _loader._terrain_y(mx, mz)
		var label := Label3D.new()
		label.text = pname
		label.font_size = 22
		label.position = Vector3(mx, my + 2.5, mz)
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.modulate = Color(0.50, 0.45, 0.35, 0.55)
		label.outline_modulate = Color(0.08, 0.06, 0.04, 0.40)
		label.outline_size = 4
		label.no_depth_test = false
		label.pixel_size = 0.01
		_loader.add_child(label)
		labeled_paths[pname] = true
		path_label_count += 1
	print("  Path labels: %d named paths" % path_label_count)


# ---------------------------------------------------------------------------
# Reservoir fence — tall chain-link around JKO Reservoir running track
# ---------------------------------------------------------------------------
func _build_reservoir_fence(water: Array) -> void:
	var fence_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_reservoir_fence.glb")
	if fence_mesh == null:
		return

	# Find the reservoir polygon
	var res_pts: Array = []
	for wb in water:
		var wname: String = str(wb.get("name", ""))
		if "reservoir" in wname.to_lower():
			res_pts = wb.get("points", wb.get("polygon", []))
			break
	if res_pts.size() < 10:
		return

	# Place fence sections around the perimeter, offset 3m outward from water edge
	const SECTION_W := 3.0
	const FENCE_OFFSET := 5.0  # metres outside water polygon

	# Compute polygon centroid for outward offset direction
	var cx := 0.0
	var cz := 0.0
	for pt in res_pts:
		cx += float(pt[0])
		cz += float(pt[1])
	cx /= float(res_pts.size())
	cz /= float(res_pts.size())

	var xforms: Array = []

	for pi in res_pts.size():
		var p0x: float = float(res_pts[pi][0])
		var p0z: float = float(res_pts[pi][1])
		var ni: int = (pi + 1) % res_pts.size()
		var p1x: float = float(res_pts[ni][0])
		var p1z: float = float(res_pts[ni][1])

		var dx: float = p1x - p0x
		var dz: float = p1z - p0z
		var seg_len: float = sqrt(dx * dx + dz * dz)
		if seg_len < 0.5:
			continue

		# Outward normal (away from centroid)
		var nx: float = -dz / seg_len
		var nz: float = dx / seg_len
		# Ensure it points away from centroid
		var mx: float = (p0x + p1x) * 0.5 - cx
		var mz: float = (p0z + p1z) * 0.5 - cz
		if nx * mx + nz * mz < 0.0:
			nx = -nx
			nz = -nz

		var n_sections: int = maxi(1, int(round(seg_len / SECTION_W)))
		var yaw: float = atan2(dx, dz)

		for si in n_sections:
			var t: float = (float(si) + 0.5) / float(n_sections)
			var fx: float = p0x + dx * t + nx * FENCE_OFFSET
			var fz: float = p0z + dz * t + nz * FENCE_OFFSET
			var fy: float = _loader._terrain_y(fx, fz)
			var basis := Basis(Vector3.UP, yaw)
			xforms.append(Transform3D(basis, Vector3(fx, fy, fz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(fence_mesh, null, xforms, "ReservoirFence")
	print("  Reservoir fence: %d sections around running track" % xforms.size())


# ---------------------------------------------------------------------------
# Playground equipment — swing sets + play structures at playground zones
# ---------------------------------------------------------------------------
func _build_playground_equipment(landuse: Array) -> void:
	var swing_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_swing_set.glb")
	var play_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_play_structure.glb")
	if swing_mesh == null and play_mesh == null:
		return

	var swing_xforms: Array = []
	var play_xforms: Array = []
	var rng := RandomNumberGenerator.new()

	for zone in landuse:
		if str(zone.get("type", "")) != "playground":
			continue
		var pts: Array = zone.get("points", [])
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

		if not _loader._in_boundary(cx, cz):
			continue

		rng.seed = int(cx * 73856.0 + cz * 19349.0) & 0x7FFFFFFF
		var yaw: float = rng.randf() * TAU
		var cy: float = _loader._terrain_y(cx, cz)

		# Place swing set offset from center
		if swing_mesh:
			var sx: float = cx + cos(yaw) * 4.0
			var sz: float = cz + sin(yaw) * 4.0
			var sy: float = _loader._terrain_y(sx, sz)
			swing_xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(sx, sy, sz)))

		# Place play structure at center
		if play_mesh:
			var py: float = cy
			play_xforms.append(Transform3D(Basis(Vector3.UP, yaw + PI * 0.5), Vector3(cx, py, cz)))

	if not swing_xforms.is_empty() and swing_mesh:
		_loader._spawn_multimesh(swing_mesh, null, swing_xforms, "SwingSets")
	if not play_xforms.is_empty() and play_mesh:
		_loader._spawn_multimesh(play_mesh, null, play_xforms, "PlayStructures")
	print("  Playground equipment: %d swing sets, %d play structures" % [swing_xforms.size(), play_xforms.size()])


# ---------------------------------------------------------------------------
# Sports equipment — backstops at baseball diamonds, hoops at basketball courts
# ---------------------------------------------------------------------------
func _build_sports_equipment(landuse: Array) -> void:
	var backstop_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_backstop.glb")
	var hoop_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_basketball_hoop.glb")
	if backstop_mesh == null and hoop_mesh == null:
		return

	var backstop_xforms: Array = []
	var hoop_xforms: Array = []
	var rng := RandomNumberGenerator.new()

	for zone in landuse:
		if str(zone.get("type", "")) != "pitch":
			continue
		var sport: String = str(zone.get("sport", ""))
		var pts: Array = zone.get("points", [])
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

		var cy: float = _loader._terrain_y(cx, cz)

		if sport == "baseball" and backstop_mesh:
			# Find "home plate" corner — typically the vertex farthest from centroid
			# of the infield diamond shape, or use first vertex as approximation
			var home_x: float = float(pts[0][0])
			var home_z: float = float(pts[0][1])
			# Find direction from home plate to centroid (outfield direction)
			var dx: float = cx - home_x
			var dz: float = cz - home_z
			var d: float = sqrt(dx * dx + dz * dz)
			if d > 0.1:
				# Backstop goes BEHIND home plate, facing outfield
				var yaw: float = atan2(dx, dz)
				var bx: float = home_x - dx / d * 3.0  # 3m behind home
				var bz: float = home_z - dz / d * 3.0
				var by: float = _loader._terrain_y(bx, bz)
				backstop_xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(bx, by, bz)))

		elif sport == "basketball" and hoop_mesh:
			# Place hoops at both ends of the court
			if pts.size() >= 4:
				# Find long axis by checking edge lengths
				var e0x: float = float(pts[1][0]) - float(pts[0][0])
				var e0z: float = float(pts[1][1]) - float(pts[0][1])
				var e1x: float = float(pts[2][0]) - float(pts[1][0])
				var e1z: float = float(pts[2][1]) - float(pts[1][1])
				var l0: float = sqrt(e0x * e0x + e0z * e0z)
				var l1: float = sqrt(e1x * e1x + e1z * e1z)

				var long_dx: float
				var long_dz: float
				var long_l: float
				if l0 > l1:
					long_dx = e0x; long_dz = e0z; long_l = l0
				else:
					long_dx = e1x; long_dz = e1z; long_l = l1

				if long_l > 0.1:
					var ndx: float = long_dx / long_l
					var ndz: float = long_dz / long_l
					var yaw: float = atan2(ndx, ndz)
					# Hoop at each end, 1.5m from edge
					for end_val in [-1.0, 1.0]:
						var end: float = float(end_val)
						var hx: float = cx + ndx * (long_l * 0.5 - 1.5) * end
						var hz: float = cz + ndz * (long_l * 0.5 - 1.5) * end
						var hy: float = _loader._terrain_y(hx, hz)
						var h_yaw: float = yaw + (PI if end > 0.0 else 0.0)
						hoop_xforms.append(Transform3D(Basis(Vector3.UP, h_yaw), Vector3(hx, hy, hz)))

	if not backstop_xforms.is_empty() and backstop_mesh:
		_loader._spawn_multimesh(backstop_mesh, null, backstop_xforms, "BaseballBackstops")
	if not hoop_xforms.is_empty() and hoop_mesh:
		_loader._spawn_multimesh(hoop_mesh, null, hoop_xforms, "BasketballHoops")
	# Tennis nets
	var net_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_tennis_net.glb")
	var net_xforms: Array = []

	if net_mesh:
		for zone in landuse:
			if str(zone.get("type", "")) != "pitch":
				continue
			var sport2: String = str(zone.get("sport", ""))
			if sport2 != "tennis":
				continue
			var pts2: Array = zone.get("points", [])
			if pts2.size() < 4:
				continue

			var cx2 := 0.0
			var cz2 := 0.0
			for pt in pts2:
				cx2 += float(pt[0])
				cz2 += float(pt[1])
			cx2 /= float(pts2.size())
			cz2 /= float(pts2.size())

			var cy2: float = _loader._terrain_y(cx2, cz2)

			# Find short axis (net runs along short axis at center)
			var e0x2: float = float(pts2[1][0]) - float(pts2[0][0])
			var e0z2: float = float(pts2[1][1]) - float(pts2[0][1])
			var e1x2: float = float(pts2[2][0]) - float(pts2[1][0])
			var e1z2: float = float(pts2[2][1]) - float(pts2[1][1])
			var l0: float = sqrt(e0x2 * e0x2 + e0z2 * e0z2)
			var l1: float = sqrt(e1x2 * e1x2 + e1z2 * e1z2)

			# Short axis direction = net direction
			var short_dx: float
			var short_dz: float
			if l0 < l1:
				short_dx = e0x2; short_dz = e0z2
			else:
				short_dx = e1x2; short_dz = e1z2
			var short_l: float = sqrt(short_dx * short_dx + short_dz * short_dz)
			if short_l < 0.1:
				continue
			var yaw: float = atan2(short_dx, short_dz)
			net_xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(cx2, cy2, cz2)))

	if not net_xforms.is_empty() and net_mesh:
		_loader._spawn_multimesh(net_mesh, null, net_xforms, "TennisNets")

	# Soccer goals
	var goal_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_soccer_goal.glb")
	var goal_xforms: Array = []

	if goal_mesh:
		for zone in landuse:
			if str(zone.get("type", "")) != "pitch":
				continue
			var sport3: String = str(zone.get("sport", ""))
			if not ("soccer" in sport3):
				continue
			var pts3: Array = zone.get("points", [])
			if pts3.size() < 4:
				continue

			var cx3 := 0.0
			var cz3 := 0.0
			for pt in pts3:
				cx3 += float(pt[0])
				cz3 += float(pt[1])
			cx3 /= float(pts3.size())
			cz3 /= float(pts3.size())
			var cy3: float = _loader._terrain_y(cx3, cz3)

			# Find short axis (goals at each end of long axis)
			var e0x3: float = float(pts3[1][0]) - float(pts3[0][0])
			var e0z3: float = float(pts3[1][1]) - float(pts3[0][1])
			var e1x3: float = float(pts3[2][0]) - float(pts3[1][0])
			var e1z3: float = float(pts3[2][1]) - float(pts3[1][1])
			var l0g: float = sqrt(e0x3 * e0x3 + e0z3 * e0z3)
			var l1g: float = sqrt(e1x3 * e1x3 + e1z3 * e1z3)

			var long_dx3: float
			var long_dz3: float
			var long_l3: float
			if l0g > l1g:
				long_dx3 = e0x3; long_dz3 = e0z3; long_l3 = l0g
			else:
				long_dx3 = e1x3; long_dz3 = e1z3; long_l3 = l1g
			if long_l3 < 1.0:
				continue
			var ndx3: float = long_dx3 / long_l3
			var ndz3: float = long_dz3 / long_l3

			for end_val3 in [-1.0, 1.0]:
				var end3: float = float(end_val3)
				var gx: float = cx3 + ndx3 * (long_l3 * 0.5 - 1.0) * end3
				var gz: float = cz3 + ndz3 * (long_l3 * 0.5 - 1.0) * end3
				var gy: float = _loader._terrain_y(gx, gz)
				# Goal faces inward toward center
				var g_yaw: float = atan2(ndx3, ndz3) + (PI if end3 > 0.0 else 0.0)
				goal_xforms.append(Transform3D(Basis(Vector3.UP, g_yaw), Vector3(gx, gy, gz)))

	if not goal_xforms.is_empty() and goal_mesh:
		_loader._spawn_multimesh(goal_mesh, null, goal_xforms, "SoccerGoals")

	# Handball walls
	var hwall_mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_handball_wall.glb")
	var hwall_xforms: Array = []

	if hwall_mesh:
		for zone in landuse:
			if str(zone.get("type", "")) != "pitch":
				continue
			if str(zone.get("sport", "")) != "american_handball":
				continue
			var pts_h: Array = zone.get("points", [])
			if pts_h.size() < 4:
				continue

			var cx_h := 0.0
			var cz_h := 0.0
			for pt in pts_h:
				cx_h += float(pt[0])
				cz_h += float(pt[1])
			cx_h /= float(pts_h.size())
			cz_h /= float(pts_h.size())
			var cy_h: float = _loader._terrain_y(cx_h, cz_h)

			# Find short axis (wall at one short end)
			var e0x_h: float = float(pts_h[1][0]) - float(pts_h[0][0])
			var e0z_h: float = float(pts_h[1][1]) - float(pts_h[0][1])
			var e1x_h: float = float(pts_h[2][0]) - float(pts_h[1][0])
			var e1z_h: float = float(pts_h[2][1]) - float(pts_h[1][1])
			var l0_h: float = sqrt(e0x_h * e0x_h + e0z_h * e0z_h)
			var l1_h: float = sqrt(e1x_h * e1x_h + e1z_h * e1z_h)

			var long_dx_h: float
			var long_dz_h: float
			var long_l_h: float
			if l0_h > l1_h:
				long_dx_h = e0x_h; long_dz_h = e0z_h; long_l_h = l0_h
			else:
				long_dx_h = e1x_h; long_dz_h = e1z_h; long_l_h = l1_h
			if long_l_h < 1.0:
				continue
			var ndx_h: float = long_dx_h / long_l_h
			var ndz_h: float = long_dz_h / long_l_h
			# Wall at one end of the long axis, facing inward
			var wx_h: float = cx_h + ndx_h * (long_l_h * 0.5 - 0.3)
			var wz_h: float = cz_h + ndz_h * (long_l_h * 0.5 - 0.3)
			var wy_h: float = _loader._terrain_y(wx_h, wz_h)
			# Short axis direction for wall alignment
			var short_dx_h: float
			var short_dz_h: float
			if l0_h < l1_h:
				short_dx_h = e0x_h; short_dz_h = e0z_h
			else:
				short_dx_h = e1x_h; short_dz_h = e1z_h
			var h_yaw: float = atan2(short_dx_h, short_dz_h)
			hwall_xforms.append(Transform3D(Basis(Vector3.UP, h_yaw), Vector3(wx_h, wy_h, wz_h)))

	if not hwall_xforms.is_empty() and hwall_mesh:
		_loader._spawn_multimesh(hwall_mesh, null, hwall_xforms, "HandballWalls")

	print("  Sports equipment: %d backstops, %d hoops, %d nets, %d goals, %d walls" % [backstop_xforms.size(), hoop_xforms.size(), net_xforms.size(), goal_xforms.size(), hwall_xforms.size()])


# ---------------------------------------------------------------------------
# Bridle path posts — split-rail wooden fence along horseback riding trails
# ---------------------------------------------------------------------------
func _build_bridle_posts(paths: Array) -> void:
	# Use a simple cylinder + rail from park_loader utilities
	# Bridle paths have wooden split-rail fencing every ~5m
	var wood_sh: Shader = _loader._get_shader("wood", "res://shaders/wood.gdshader")

	var verts := PackedVector3Array()
	var normals := PackedVector3Array()

	const POST_H := 1.0       # 1m tall posts
	const POST_R := 0.04      # 4cm radius
	const RAIL_R := 0.03      # 3cm radius rail
	const SPACING := 5.0      # 5m between posts
	const OFFSET := 1.2       # 1.2m from path centerline
	const SEGS := 6           # cylinder segments

	var post_count := 0
	for path in paths:
		if str(path.get("highway", "")) != "bridleway":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue

		# Walk along path placing posts on both sides
		var dist := 0.0
		for pi in range(pts.size() - 1):
			var ax: float = float(pts[pi][0])
			var az: float = float(pts[pi][2]) if len(pts[pi]) > 2 else float(pts[pi][1])
			var bx: float = float(pts[pi + 1][0])
			var bz: float = float(pts[pi + 1][2]) if len(pts[pi + 1]) > 2 else float(pts[pi + 1][1])
			var sdx: float = bx - ax
			var sdz: float = bz - az
			var seg_len: float = sqrt(sdx * sdx + sdz * sdz)
			if seg_len < 0.1:
				continue

			# Perpendicular for offset
			var px: float = -sdz / seg_len
			var pz: float = sdx / seg_len

			while dist < seg_len:
				var t: float = dist / seg_len
				var wx: float = ax + sdx * t
				var wz: float = az + sdz * t
				if not _loader._in_boundary(wx, wz):
					dist += SPACING
					continue
				var wy: float = _loader._terrain_y(wx, wz)

				# Place post on both sides
				for side_val in [-1.0, 1.0]:
					var side: float = float(side_val)
					var ppx: float = wx + px * OFFSET * side
					var ppz: float = wz + pz * OFFSET * side
					var ppy: float = _loader._terrain_y(ppx, ppz)
					# Simple cylinder post
					for si in SEGS:
						var a0: float = TAU * float(si) / float(SEGS)
						var a1: float = TAU * float(si + 1) / float(SEGS)
						var c0x: float = cos(a0) * POST_R
						var c0z: float = sin(a0) * POST_R
						var c1x: float = cos(a1) * POST_R
						var c1z: float = sin(a1) * POST_R
						var n0 := Vector3(cos(a0), 0, sin(a0))
						var n1 := Vector3(cos(a1), 0, sin(a1))
						# Two triangles for the side quad
						verts.append(Vector3(ppx + c0x, ppy, ppz + c0z))
						normals.append(n0)
						verts.append(Vector3(ppx + c1x, ppy, ppz + c1z))
						normals.append(n1)
						verts.append(Vector3(ppx + c1x, ppy + POST_H, ppz + c1z))
						normals.append(n1)
						verts.append(Vector3(ppx + c0x, ppy, ppz + c0z))
						normals.append(n0)
						verts.append(Vector3(ppx + c1x, ppy + POST_H, ppz + c1z))
						normals.append(n1)
						verts.append(Vector3(ppx + c0x, ppy + POST_H, ppz + c0z))
						normals.append(n0)
					post_count += 1
				dist += SPACING
			dist -= seg_len  # carry remainder to next segment

	if verts.is_empty():
		return

	# Build mesh with wood material
	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = Color(0.35, 0.22, 0.12)  # warm wood brown
	mat.roughness = 0.85
	mesh.surface_set_material(0, mat)
	if wood_sh:
		var wood_mat := ShaderMaterial.new()
		wood_mat.shader = wood_sh
		wood_mat.set_shader_parameter("wood_color", Vector3(0.35, 0.22, 0.12))
		mesh.surface_set_material(0, wood_mat)

	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "BridlePosts"
	_loader.add_child(mi)
	print("  Bridle path posts: %d along horseback trails" % post_count)


# ---------------------------------------------------------------------------
# Stone staircases — 250 OSM highway=steps paths built as stepped geometry
# ---------------------------------------------------------------------------
func _build_staircases(paths: Array) -> void:
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.52, 0.50, 0.46))

	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var col_verts := PackedVector3Array()
	var rail_verts := PackedVector3Array()
	var rail_normals := PackedVector3Array()
	var stair_count := 0

	for path in paths:
		if str(path.get("highway", "")) != "steps":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue
		var mx := (float(pts[0][0]) + float(pts[pts.size()-1][0])) * 0.5
		var mz := (float(pts[0][2]) + float(pts[pts.size()-1][2])) * 0.5
		if not _loader._in_boundary(mx, mz):
			continue
		_build_single_staircase(pts, path, verts, normals, col_verts,
			rail_verts, rail_normals)
		stair_count += 1

	if verts.is_empty():
		return

	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "Staircases"
	_loader.add_child(mi)

	# Iron handrails
	if not rail_verts.is_empty():
		var iron_sh: Shader = _loader._get_shader("cast_iron", "res://shaders/cast_iron.gdshader")
		var rail_mat := ShaderMaterial.new()
		rail_mat.shader = iron_sh
		rail_mat.set_shader_parameter("iron_color", Vector3(0.06, 0.06, 0.07))
		rail_mat.set_shader_parameter("base_roughness", 0.60)
		rail_mat.set_shader_parameter("base_metallic", 0.90)
		var rail_mesh: ArrayMesh = _loader._make_mesh(rail_verts, rail_normals)
		rail_mesh.surface_set_material(0, rail_mat)
		var rmi := MeshInstance3D.new()
		rmi.mesh = rail_mesh
		rmi.name = "StaircaseHandrails"
		_loader.add_child(rmi)
		print("  Staircase handrails: %d verts" % rail_verts.size())

	# Collision for staircases
	if not col_verts.is_empty():
		var body := StaticBody3D.new()
		body.name = "Staircase_Collision"
		var shape := ConcavePolygonShape3D.new()
		shape.set_faces(col_verts)
		var col := CollisionShape3D.new()
		col.shape = shape
		body.add_child(col)
		_loader.add_child(body)

	print("ParkLoader: staircases = %d (%d verts)" % [stair_count, verts.size()])


func _build_single_staircase(pts: Array, path: Dictionary,
		verts: PackedVector3Array, normals: PackedVector3Array,
		col_verts: PackedVector3Array,
		rail_verts: PackedVector3Array, rail_normals: PackedVector3Array) -> void:
	## Build stepped geometry for a single staircase path.
	## Standard Central Park granite steps: 15cm riser, 30cm tread.
	## Also generates iron handrails on both sides (for stairs with ≥4 steps).
	const RISER_H := 0.15  # metres
	const TREAD_D := 0.30  # metres (horizontal depth of each step)
	const HALF_THICK := 0.05  # half-thickness of tread slab

	# Get path width (steps usually 2-4m wide)
	var half_w: float = _loader._path_width(path) * 0.5
	half_w = clampf(half_w, 0.75, 5.0)

	# Compute total horizontal run and elevation change along the path
	var start_x := float(pts[0][0]); var start_z := float(pts[0][2])
	var end_x := float(pts[pts.size()-1][0]); var end_z := float(pts[pts.size()-1][2])
	var start_y: float = _loader._terrain_y(start_x, start_z)
	var end_y: float = _loader._terrain_y(end_x, end_z)

	var dy := end_y - start_y
	if absf(dy) < 0.1:
		return  # flat — no steps needed

	# Number of steps from elevation change
	var n_steps := maxi(1, int(round(absf(dy) / RISER_H)))
	# Clamp to reasonable range
	n_steps = mini(n_steps, 200)

	# Direction along the staircase (XZ plane)
	var dx := end_x - start_x
	var dz := end_z - start_z
	var run := sqrt(dx * dx + dz * dz)
	if run < 0.3:
		return

	var dir_x := dx / run
	var dir_z := dz / run
	# Perpendicular for width
	var perp_x := -dir_z
	var perp_z := dir_x

	# Step heights: go uphill or downhill
	var going_up := dy > 0.0
	var base_y := minf(start_y, end_y)
	# If going down, reverse iteration direction
	var step_dir := 1.0 if going_up else -1.0
	var origin_x := start_x if going_up else end_x
	var origin_z := start_z if going_up else end_z

	# Horizontal step spacing
	var step_run := run / float(n_steps)
	var step_rise := absf(dy) / float(n_steps)

	for si in n_steps:
		var t := float(si) / float(n_steps)
		# Step position along the run
		var cx := origin_x + dir_x * step_dir * step_run * (float(si) + 0.5)
		var cz := origin_z + dir_z * step_dir * step_run * (float(si) + 0.5)
		var step_top_y := base_y + step_rise * float(si + 1)

		# Four corners of the tread (top surface)
		var td := TREAD_D * 0.5  # half tread depth along run direction
		var fl_x := cx - dir_x * td + perp_x * half_w
		var fl_z := cz - dir_z * td + perp_z * half_w
		var fr_x := cx - dir_x * td - perp_x * half_w
		var fr_z := cz - dir_z * td - perp_z * half_w
		var bl_x := cx + dir_x * td + perp_x * half_w
		var bl_z := cz + dir_z * td + perp_z * half_w
		var br_x := cx + dir_x * td - perp_x * half_w
		var br_z := cz + dir_z * td - perp_z * half_w

		# Tread top face (horizontal)
		var tfl := Vector3(fl_x, step_top_y, fl_z)
		var tfr := Vector3(fr_x, step_top_y, fr_z)
		var tbl := Vector3(bl_x, step_top_y, bl_z)
		var tbr := Vector3(br_x, step_top_y, br_z)

		var tread := PackedVector3Array([tfl, tbl, tfr, tfr, tbl, tbr])
		verts.append_array(tread)
		col_verts.append_array(tread)
		for _j in 6: normals.append(Vector3.UP)

		# Riser face (vertical front of step)
		var riser_bot_y := step_top_y - step_rise
		var rfl := Vector3(fl_x, riser_bot_y, fl_z)
		var rfr := Vector3(fr_x, riser_bot_y, fr_z)
		var riser_n := Vector3(-dir_x, 0.0, -dir_z)

		var riser := PackedVector3Array([rfl, tfl, rfr, rfr, tfl, tfr])
		verts.append_array(riser)
		col_verts.append_array(riser)
		for _j in 6: normals.append(riser_n)

	# --- Iron handrails on both sides (only for staircases ≥ 4 steps) ---
	if n_steps < 4:
		return
	const RAIL_H := 0.90   # handrail height above step surface
	const RAIL_R := 0.025  # rail tube radius (25mm — standard pipe)
	const POST_R := 0.02   # post radius (20mm)
	const POST_SPACING := 4  # one post every N steps
	const RAIL_SEGS := 6   # cylinder segments

	# Rail offset slightly inside step edges
	var rail_offset := half_w - 0.05
	for side_val in [-1.0, 1.0]:
		var side: float = float(side_val)
		var rx_off := perp_x * rail_offset * side
		var rz_off := perp_z * rail_offset * side
		var out_n := Vector3(perp_x * side, 0, perp_z * side)

		# Top rail: continuous tube from bottom step to top step
		for si in n_steps:
			var cx0 := origin_x + dir_x * step_dir * step_run * float(si)
			var cz0 := origin_z + dir_z * step_dir * step_run * float(si)
			var y0 := base_y + step_rise * float(si + 1) + RAIL_H
			var cx1 := origin_x + dir_x * step_dir * step_run * float(si + 1)
			var cz1 := origin_z + dir_z * step_dir * step_run * float(si + 1)
			var y1 := base_y + step_rise * float(si + 2) + RAIL_H
			if si == n_steps - 1:
				y1 = base_y + step_rise * float(n_steps) + RAIL_H

			var p0 := Vector3(cx0 + rx_off, y0, cz0 + rz_off)
			var p1 := Vector3(cx1 + rx_off, y1, cz1 + rz_off)
			_add_rail_segment(p0, p1, RAIL_R, RAIL_SEGS, rail_verts, rail_normals)

		# Vertical posts at intervals
		for si in range(0, n_steps + 1, POST_SPACING):
			var pcx := origin_x + dir_x * step_dir * step_run * float(si)
			var pcz := origin_z + dir_z * step_dir * step_run * float(si)
			var pby: float
			if si < n_steps:
				pby = base_y + step_rise * float(si + 1)
			else:
				pby = base_y + step_rise * float(n_steps)
			var pty := pby + RAIL_H
			var p_base := Vector3(pcx + rx_off, pby, pcz + rz_off)
			var p_top := Vector3(pcx + rx_off, pty, pcz + rz_off)
			_add_rail_segment(p_base, p_top, POST_R, RAIL_SEGS, rail_verts, rail_normals)


func _add_rail_segment(p0: Vector3, p1: Vector3, radius: float, segs: int,
		verts: PackedVector3Array, normals: PackedVector3Array) -> void:
	## Add a cylindrical tube segment between two points.
	var axis := p1 - p0
	var length := axis.length()
	if length < 0.01:
		return
	var up := axis.normalized()
	# Find perpendicular vectors
	var arbitrary := Vector3.RIGHT if absf(up.dot(Vector3.RIGHT)) < 0.9 else Vector3.FORWARD
	var right := up.cross(arbitrary).normalized()
	var fwd := right.cross(up).normalized()

	for si in segs:
		var a0 := TAU * float(si) / float(segs)
		var a1 := TAU * float(si + 1) / float(segs)
		var n0 := right * cos(a0) + fwd * sin(a0)
		var n1 := right * cos(a1) + fwd * sin(a1)
		var b0 := p0 + n0 * radius
		var b1 := p0 + n1 * radius
		var t0 := p1 + n0 * radius
		var t1 := p1 + n1 * radius
		# Two triangles for cylinder quad
		verts.append(b0); normals.append(n0)
		verts.append(b1); normals.append(n1)
		verts.append(t1); normals.append(n1)
		verts.append(b0); normals.append(n0)
		verts.append(t1); normals.append(n1)
		verts.append(t0); normals.append(n0)


# ---------------------------------------------------------------------------
# Fitness stations — exercise equipment along running paths
# ---------------------------------------------------------------------------
func _build_fitness_stations(paths: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_fitness_station.glb")
	if mesh == null:
		return

	# Apply steel material
	var iron_sh: Shader = _loader._get_shader("cast_iron", "res://shaders/cast_iron.gdshader")
	if iron_sh:
		var mat := ShaderMaterial.new()
		mat.shader = iron_sh
		mat.set_shader_parameter("iron_color", Vector3(0.30, 0.28, 0.25))
		mat.set_shader_parameter("base_roughness", 0.55)
		mat.set_shader_parameter("base_metallic", 0.90)
		for si in mesh.get_surface_count():
			mesh.surface_set_material(si, mat)

	# Known fitness station locations along Central Park running paths
	# (North-south along the park, near the bridle path and loop drive)
	var stations: Array = [
		# North end
		[290, -1580],   # near North Meadow
		[180, -1200],   # near East Meadow
		# Upper park
		[-100, -800],   # near Reservoir east
		[-500, -600],   # near Reservoir west
		# Central
		[-200, -200],   # near Great Lawn east
		[-550, -50],    # near Tennis courts
		# South-central
		[-350, 400],    # near Ramble
		[-650, 600],    # near Lake west
		# South
		[-450, 1000],   # near Bethesda
		[-300, 1400],   # near Mall south
		# Far south
		[-500, 1650],   # near Heckscher
		[-100, 1700],   # near Wollman
	]

	var xforms: Array = []
	for st in stations:
		var wx: float = float(st[0])
		var wz: float = float(st[1])
		if not _loader._in_boundary(wx, wz):
			continue
		var wy: float = _loader._terrain_y(wx, wz)
		# Random orientation
		var rng := RandomNumberGenerator.new()
		rng.seed = int(wx * 73.0 + wz * 191.0) & 0x7FFFFFFF
		var yaw := rng.randf() * TAU
		xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(wx, wy, wz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "FitnessStations")
	print("  Fitness stations: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Mile markers — bronze distance markers along the loop drive
# ---------------------------------------------------------------------------
func _build_mile_markers(paths: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_mile_marker.glb")
	if mesh == null:
		return

	# Find the main loop drive paths (primary/secondary roads)
	# Place markers every ~400m (quarter mile) along drives
	const MARKER_SPACING := 400.0  # metres between markers
	var xforms: Array = []
	var placed_count := 0

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw != "primary" and hw != "secondary":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue

		# Walk along path placing markers
		var dist := 0.0
		for pi in range(pts.size() - 1):
			var ax: float = float(pts[pi][0])
			var az: float = float(pts[pi][2]) if len(pts[pi]) > 2 else float(pts[pi][1])
			var bx: float = float(pts[pi + 1][0])
			var bz: float = float(pts[pi + 1][2]) if len(pts[pi + 1]) > 2 else float(pts[pi + 1][1])
			var sdx: float = bx - ax
			var sdz: float = bz - az
			var seg_len: float = sqrt(sdx * sdx + sdz * sdz)
			if seg_len < 0.1:
				continue

			while dist < seg_len:
				var t: float = dist / seg_len
				var wx: float = ax + sdx * t
				var wz: float = az + sdz * t
				if not _loader._in_boundary(wx, wz):
					dist += MARKER_SPACING
					continue
				var wy: float = _loader._terrain_y(wx, wz)
				# Perpendicular offset (1.5m from path center)
				var px: float = -sdz / seg_len
				var pz: float = sdx / seg_len
				var mx: float = wx + px * 1.5
				var mz: float = wz + pz * 1.5
				var my: float = _loader._terrain_y(mx, mz)
				var yaw: float = atan2(sdx, sdz)
				xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(mx, my, mz)))
				placed_count += 1
				dist += MARKER_SPACING
			dist -= seg_len

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "MileMarkers")
	print("  Mile markers: %d placed" % placed_count)


# ---------------------------------------------------------------------------
# Balustrades — ornamental stone railings at formal terraces
# ---------------------------------------------------------------------------
func _build_balustrades() -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_balustrade.glb")
	if mesh == null:
		return

	# Apply stone material
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(
		rw_alb, rw_nrm, rw_rgh, Color(0.62, 0.60, 0.56))
	for si in mesh.get_surface_count():
		mesh.surface_set_material(si, stone_mat)

	# Balustrade sections at formal terrace locations
	# Each entry: [x, z, yaw, count] — count = sections along that edge
	# Bethesda Terrace — upper terrace edge (north, south, east, west sides)
	var sections: Array = [
		# Bethesda Terrace upper level — north edge (overlooking fountain)
		[-480, 1010, 0.0, 8],
		# Bethesda Terrace — east wing
		[-450, 1025, PI * 0.5, 4],
		# Bethesda Terrace — west wing
		[-510, 1025, PI * 0.5, 4],
		# Cherry Hill overlook — stone terrace edge
		[-550, 950, PI * 0.25, 3],
		# Belvedere Castle terrace — south overlook
		[-265, 600, 0.0, 4],
		# Belvedere Castle — east edge
		[-245, 615, PI * 0.5, 2],
		# Conservatory Garden — formal terrace edges
		[1100, -1180, 0.0, 6],
		[1100, -1250, 0.0, 6],
	]

	var xforms: Array = []
	const SECTION_W := 2.0  # matches model width
	for sec in sections:
		var base_x: float = float(sec[0])
		var base_z: float = float(sec[1])
		var yaw: float = float(sec[2])
		var count: int = int(sec[3])
		var dir_x := sin(yaw)
		var dir_z := cos(yaw)
		for i in count:
			var offset: float = (float(i) - float(count - 1) * 0.5) * SECTION_W
			var wx: float = base_x + dir_x * offset
			var wz: float = base_z + dir_z * offset
			var wy: float = _loader._terrain_y(wx, wz)
			xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(wx, wy, wz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "Balustrades")
	print("  Balustrades: %d sections at formal terraces" % xforms.size())


# ---------------------------------------------------------------------------
# Drive-side waste bins — wire mesh trash cans along loop drives
# ---------------------------------------------------------------------------
func _build_drive_waste_bins(paths: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_wire_trash_can.glb")
	if mesh == null:
		return

	const BIN_SPACING := 120.0  # one bin every ~120m along drives
	const PATH_OFFSET := 3.5    # 3.5m from path center (at edge of drive)
	var xforms: Array = []

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		# Only along drives (primary=East/West Drive, secondary=transverses)
		if hw != "primary" and hw != "secondary":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue

		var dist := 60.0  # start offset to stagger from mile markers
		for pi in range(pts.size() - 1):
			var ax: float = float(pts[pi][0])
			var az: float = float(pts[pi][2]) if len(pts[pi]) > 2 else float(pts[pi][1])
			var bx: float = float(pts[pi + 1][0])
			var bz: float = float(pts[pi + 1][2]) if len(pts[pi + 1]) > 2 else float(pts[pi + 1][1])
			var sdx: float = bx - ax
			var sdz: float = bz - az
			var seg_len: float = sqrt(sdx * sdx + sdz * sdz)
			if seg_len < 0.1:
				continue

			while dist < seg_len:
				var t: float = dist / seg_len
				var wx: float = ax + sdx * t
				var wz: float = az + sdz * t
				if not _loader._in_boundary(wx, wz):
					dist += BIN_SPACING
					continue
				# Perpendicular offset to edge
				var px: float = -sdz / seg_len
				var pz: float = sdx / seg_len
				var mx: float = wx + px * PATH_OFFSET
				var mz: float = wz + pz * PATH_OFFSET
				var my: float = _loader._terrain_y(mx, mz)
				var yaw: float = atan2(px, pz)  # face away from path
				xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(mx, my, mz)))
				dist += BIN_SPACING
			dist -= seg_len

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "DriveWasteBins")
	print("  Drive waste bins: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Retaining walls — low stone walls along steep terrain grade changes
# ---------------------------------------------------------------------------
func _build_retaining_walls(paths: Array) -> void:
	## Detect steep terrain grade changes alongside paths and build
	## low Manhattan schist retaining walls to hold the grade.
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var mat: Material = _loader._make_stone_material(rw_alb, rw_nrm, rw_rgh,
		Color(0.48, 0.46, 0.42))

	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var wall_count := 0

	const CHECK_DIST := 3.0    # metres from path center to check
	const MIN_DROP := 0.6      # minimum grade drop to trigger wall (0.6m)
	const WALL_THICK := 0.30   # wall thickness
	const SAMPLE_STEP := 4.0   # sample every 4m along path

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw == "steps" or hw == "bridleway":
			continue  # skip staircases and bridle paths
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue

		for pi in range(pts.size() - 1):
			var ax: float = float(pts[pi][0])
			var az: float = float(pts[pi][2]) if len(pts[pi]) > 2 else float(pts[pi][1])
			var bx: float = float(pts[pi + 1][0])
			var bz: float = float(pts[pi + 1][2]) if len(pts[pi + 1]) > 2 else float(pts[pi + 1][1])
			var sdx: float = bx - ax
			var sdz: float = bz - az
			var seg_len: float = sqrt(sdx * sdx + sdz * sdz)
			if seg_len < 1.0:
				continue
			var ndx := sdx / seg_len
			var ndz := sdz / seg_len
			# Perpendicular
			var px := -ndz
			var pz := ndx

			var dist := 0.0
			while dist < seg_len:
				var t: float = dist / seg_len
				var wx: float = ax + sdx * t
				var wz: float = az + sdz * t
				if not _loader._in_boundary(wx, wz):
					dist += SAMPLE_STEP
					continue
				var wy: float = _loader._terrain_y(wx, wz)

				# Check both sides for grade drop
				for side_val in [-1.0, 1.0]:
					var side: float = float(side_val)
					var cx: float = wx + px * CHECK_DIST * side
					var cz: float = wz + pz * CHECK_DIST * side
					var cy: float = _loader._terrain_y(cx, cz)
					var drop: float = wy - cy
					if drop < MIN_DROP:
						continue
					# Clamp wall height
					var wall_h: float = clampf(drop, MIN_DROP, 2.5)
					# Wall at the edge, facing outward
					var wall_x: float = wx + px * (CHECK_DIST - 0.5) * side
					var wall_z: float = wz + pz * (CHECK_DIST - 0.5) * side
					var wall_y: float = _loader._terrain_y(wall_x, wall_z)
					var out_nx := px * side
					var out_nz := pz * side
					var half_w := SAMPLE_STEP * 0.5
					# Wall face (4m wide segment)
					var fl := Vector3(wall_x - ndx * half_w, wall_y, wall_z - ndz * half_w)
					var fr := Vector3(wall_x + ndx * half_w, wall_y, wall_z + ndz * half_w)
					var tl := Vector3(fl.x, wall_y + wall_h, fl.z)
					var tr := Vector3(fr.x, wall_y + wall_h, fr.z)
					var face_n := Vector3(out_nx, 0, out_nz)
					verts.append_array(PackedVector3Array([fl, tl, fr, fr, tl, tr]))
					for _j in 6: normals.append(face_n)
					# Top face
					var tl2 := Vector3(fl.x - out_nx * WALL_THICK, tl.y, fl.z - out_nz * WALL_THICK)
					var tr2 := Vector3(fr.x - out_nx * WALL_THICK, tr.y, fr.z - out_nz * WALL_THICK)
					verts.append_array(PackedVector3Array([tl, tl2, tr, tr, tl2, tr2]))
					for _j in 6: normals.append(Vector3.UP)
					wall_count += 1
				dist += SAMPLE_STEP

	if verts.is_empty():
		return

	var mesh: ArrayMesh = _loader._make_mesh(verts, normals)
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "RetainingWalls"
	_loader.add_child(mi)
	print("  Retaining walls: %d segments (%d verts)" % [wall_count, verts.size()])


# ---------------------------------------------------------------------------
# Bollards — cast iron posts at park entrances and drive restrictions
# ---------------------------------------------------------------------------
func _build_bollards() -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_bollard.glb")
	if mesh == null:
		return

	# Apply cast iron material
	var iron_sh: Shader = _loader._get_shader("cast_iron", "res://shaders/cast_iron.gdshader")
	if iron_sh:
		var mat := ShaderMaterial.new()
		mat.shader = iron_sh
		mat.set_shader_parameter("iron_color", Vector3(0.06, 0.06, 0.07))
		mat.set_shader_parameter("base_roughness", 0.60)
		mat.set_shader_parameter("base_metallic", 0.85)
		for si in mesh.get_surface_count():
			mesh.surface_set_material(si, mat)

	# Bollard positions at park gate entrances — rows of 3-5 bollards
	# across path width. Gate positions from boundary_builder gate data.
	var gate_positions: Array = [
		# South gates
		[-835, 1812, 0.0],    # Merchants' Gate (Columbus Circle)
		[-680, 1872, PI*0.5], # Scholars' Gate (60th/5th Ave)
		[-545, 1830, 0.0],    # Artists' Gate (59th/6th Ave)
		# West side
		[-855, 1550, PI*0.5], # Women's Gate (72nd/CPW)
		[-880, 1170, PI*0.5], # Hunters' Gate (81st/CPW)
		[-850, 770, PI*0.5],  # Mariners' Gate (85th/CPW)
		[-810, 340, PI*0.5],  # Gate of All Saints (96th/CPW)
		[-700, -250, PI*0.5], # Boys' Gate (100th/CPW)
		[-620, -900, PI*0.5], # Strangers' Gate (106th/CPW)
		# East side
		[700, 1570, PI*0.5],  # Inventors' Gate (72nd/5th)
		[560, 1170, PI*0.5],  # Engineers' Gate (90th/5th)
		[400, 770, PI*0.5],   # Miners' Gate (79th/5th)
		[180, -250, PI*0.5],  # Woodmen's Gate (96th/5th)
		# North
		[-250, -1850, 0.0],   # Farmers' Gate (110th/5th)
		[-500, -1880, 0.0],   # Warriors' Gate (110th/CPW)
	]

	var xforms: Array = []
	const BOLLARD_SPACING := 1.2  # 1.2m between bollards
	const BOLLARDS_PER_GATE := 5  # row of 5 bollards

	for gp in gate_positions:
		var gx: float = float(gp[0])
		var gz: float = float(gp[1])
		var yaw: float = float(gp[2])
		# Direction perpendicular to path for row placement
		var row_dx := sin(yaw)
		var row_dz := cos(yaw)
		for bi in BOLLARDS_PER_GATE:
			var offset: float = (float(bi) - float(BOLLARDS_PER_GATE - 1) * 0.5) * BOLLARD_SPACING
			var bx: float = gx + row_dx * offset
			var bz: float = gz + row_dz * offset
			var by: float = _loader._terrain_y(bx, bz)
			xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(bx, by, bz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "Bollards")
	print("  Bollards: %d at %d gate entrances" % [xforms.size(), gate_positions.size()])


# ---------------------------------------------------------------------------
# Emergency call boxes — blue-light phones along paths
# ---------------------------------------------------------------------------
func _build_call_boxes(paths: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_call_box.glb")
	if mesh == null:
		return

	const SPACING := 250.0   # one call box every ~250m along drives
	const PATH_OFFSET := 2.5 # offset from path center
	var xforms: Array = []

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw != "primary" and hw != "secondary":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue

		var dist := 100.0  # start offset
		for pi in range(pts.size() - 1):
			var ax: float = float(pts[pi][0])
			var az: float = float(pts[pi][2]) if len(pts[pi]) > 2 else float(pts[pi][1])
			var bx: float = float(pts[pi + 1][0])
			var bz: float = float(pts[pi + 1][2]) if len(pts[pi + 1]) > 2 else float(pts[pi + 1][1])
			var sdx: float = bx - ax
			var sdz: float = bz - az
			var seg_len: float = sqrt(sdx * sdx + sdz * sdz)
			if seg_len < 0.1:
				continue

			while dist < seg_len:
				var t: float = dist / seg_len
				var wx: float = ax + sdx * t
				var wz: float = az + sdz * t
				if not _loader._in_boundary(wx, wz):
					dist += SPACING
					continue
				var px: float = -sdz / seg_len
				var pz: float = sdx / seg_len
				var mx: float = wx + px * PATH_OFFSET
				var mz: float = wz + pz * PATH_OFFSET
				var my: float = _loader._terrain_y(mx, mz)
				var yaw: float = atan2(-px, -pz)  # face path
				xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(mx, my, mz)))
				dist += SPACING
			dist -= seg_len

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "EmergencyCallBoxes")
	print("  Emergency call boxes: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Info kiosks — wayfinding map panels at major intersections
# ---------------------------------------------------------------------------
func _build_info_kiosks() -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_info_kiosk.glb")
	if mesh == null:
		return

	# Known kiosk locations at major park entrances and junctions
	var kiosk_positions: Array = [
		# South entrances
		[-835, 1815, PI],       # Columbus Circle
		[-680, 1870, PI*0.5],   # 5th Ave/60th
		[-540, 1835, PI],       # Artists' Gate
		# Major intersections
		[-480, 1050, 0.0],      # Bethesda Terrace
		[-650, 950, PI*0.25],   # Cherry Hill
		[-265, 620, PI*0.5],    # Belvedere Castle
		[-100, 170, 0.0],       # Great Lawn east
		[-550, -50, PI*0.5],    # Tennis Center
		# North
		[200, -1100, 0.0],      # near Conservatory Garden
		[-200, -1550, PI],      # near North Meadow
		[-400, -1850, 0.0],     # Harlem Meer
		# East side
		[700, 1570, PI*0.5],    # Inventors' Gate / 72nd
		[400, 770, PI*0.5],     # Engineers' Gate area
	]

	var xforms: Array = []
	for kp in kiosk_positions:
		var kx: float = float(kp[0])
		var kz: float = float(kp[1])
		var yaw: float = float(kp[2])
		var ky: float = _loader._terrain_y(kx, kz)
		xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(kx, ky, kz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "InfoKiosks")
	print("  Info kiosks: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Storm drain grates — flush with pavement on drives
# ---------------------------------------------------------------------------
func _build_drain_grates(paths: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_drain_grate.glb")
	if mesh == null:
		return

	# Apply cast iron material
	var iron_sh: Shader = _loader._get_shader("cast_iron", "res://shaders/cast_iron.gdshader")
	if iron_sh:
		var mat := ShaderMaterial.new()
		mat.shader = iron_sh
		mat.set_shader_parameter("iron_color", Vector3(0.10, 0.10, 0.11))
		mat.set_shader_parameter("base_roughness", 0.70)
		mat.set_shader_parameter("base_metallic", 0.85)
		for si in mesh.get_surface_count():
			mesh.surface_set_material(si, mat)

	const SPACING := 80.0    # one grate every ~80m along drives
	const PATH_OFFSET := 4.0 # at road edge (gutter)
	var xforms: Array = []

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw != "primary" and hw != "secondary":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue

		var dist := 20.0
		for pi in range(pts.size() - 1):
			var ax: float = float(pts[pi][0])
			var az: float = float(pts[pi][2]) if len(pts[pi]) > 2 else float(pts[pi][1])
			var bx: float = float(pts[pi + 1][0])
			var bz: float = float(pts[pi + 1][2]) if len(pts[pi + 1]) > 2 else float(pts[pi + 1][1])
			var sdx: float = bx - ax
			var sdz: float = bz - az
			var seg_len: float = sqrt(sdx * sdx + sdz * sdz)
			if seg_len < 0.1:
				continue

			while dist < seg_len:
				var t: float = dist / seg_len
				var wx: float = ax + sdx * t
				var wz: float = az + sdz * t
				if not _loader._in_boundary(wx, wz):
					dist += SPACING
					continue
				var px: float = -sdz / seg_len
				var pz: float = sdx / seg_len
				var mx: float = wx + px * PATH_OFFSET
				var mz: float = wz + pz * PATH_OFFSET
				var my: float = _loader._terrain_y(mx, mz) + 0.005
				var yaw: float = atan2(sdx, sdz)
				xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(mx, my, mz)))
				dist += SPACING
			dist -= seg_len

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "DrainGrates")
	print("  Drain grates: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Bicycle racks — inverted-U racks near facilities and entrances
# ---------------------------------------------------------------------------
func _build_bike_racks() -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_bike_rack.glb")
	if mesh == null:
		return

	# Bike rack clusters at facilities, playgrounds, and major entrances
	# Each entry: [x, z, yaw, count] — count = racks in a row
	var clusters: Array = [
		# Near Bethesda
		[-460, 1040, 0.0, 4],
		# Loeb Boathouse
		[-320, 850, PI*0.5, 3],
		# Tavern on the Green
		[-850, 1420, PI, 3],
		# Belvedere Castle
		[-280, 640, 0.0, 2],
		# Tennis Center
		[-560, -80, PI*0.5, 4],
		# Conservatory Garden
		[1100, -1150, 0.0, 3],
		# Columbus Circle entrance
		[-830, 1800, PI*0.5, 5],
		# 72nd/5th Ave entrance
		[690, 1560, 0.0, 4],
		# Dana Discovery Center
		[-200, -1700, PI, 3],
		# North Meadow Rec Center
		[300, -1400, PI*0.5, 3],
		# Wollman Rink
		[-100, 1680, 0.0, 3],
		# Central Park Zoo
		[450, 1720, PI*0.5, 4],
		# Heckscher Playground
		[-500, 1750, 0.0, 3],
		# Great Lawn area
		[-100, 100, PI*0.5, 2],
	]

	var xforms: Array = []
	const RACK_SPACING := 1.2  # 1.2m between racks in a row

	for cl in clusters:
		var base_x: float = float(cl[0])
		var base_z: float = float(cl[1])
		var yaw: float = float(cl[2])
		var count: int = int(cl[3])
		var row_dx := sin(yaw)
		var row_dz := cos(yaw)
		for i in count:
			var offset: float = (float(i) - float(count - 1) * 0.5) * RACK_SPACING
			var bx: float = base_x + row_dx * offset
			var bz: float = base_z + row_dz * offset
			var by: float = _loader._terrain_y(bx, bz)
			xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(bx, by, bz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "BikeRacks")
	print("  Bike racks: %d at %d locations" % [xforms.size(), clusters.size()])


# ---------------------------------------------------------------------------
# Tree pit grates — cast iron grates around street-side trees
# ---------------------------------------------------------------------------
func _build_tree_pit_grates(trees: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_tree_pit_grate.glb")
	if mesh == null:
		return

	# Apply cast iron material
	var iron_sh: Shader = _loader._get_shader("cast_iron", "res://shaders/cast_iron.gdshader")
	if iron_sh:
		var mat := ShaderMaterial.new()
		mat.shader = iron_sh
		mat.set_shader_parameter("iron_color", Vector3(0.10, 0.10, 0.11))
		mat.set_shader_parameter("base_roughness", 0.65)
		mat.set_shader_parameter("base_metallic", 0.85)
		for si in mesh.get_surface_count():
			mesh.surface_set_material(si, mat)

	# Tree pit grates only around trees adjacent to paved surfaces
	# Check atlas surface type at tree position and 2m radius
	var xforms: Array = []
	for tree in trees:
		var tpos: Array = tree.get("pos", [])
		if tpos.size() < 3:
			continue
		var tx: float = float(tpos[0])
		var tz: float = float(tpos[2])
		# Tree must be on or near paved path (atlas surface type 2)
		var surf: int = _loader._atlas_surface(tx, tz)
		if surf != 2:
			# Check 2m radius for nearby pavement
			var near_paved := false
			for off in [Vector2(2,0), Vector2(-2,0), Vector2(0,2), Vector2(0,-2)]:
				if _loader._atlas_surface(tx + off.x, tz + off.y) == 2:
					near_paved = true
					break
			if not near_paved:
				continue
		var ty: float = _loader._terrain_y(tx, tz) + 0.01  # slightly above ground
		var rng := RandomNumberGenerator.new()
		rng.seed = int(tx * 47.0 + tz * 131.0) & 0x7FFFFFFF
		var yaw := rng.randf() * TAU
		xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(tx, ty, tz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "TreePitGrates")
	print("  Tree pit grates: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Curb ramps — ADA accessible crossings where paths meet drives
# ---------------------------------------------------------------------------
func _build_curb_ramps(paths: Array) -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_curb_ramp.glb")
	if mesh == null:
		return

	# Find intersections between drives and pedestrian paths
	# by checking where footway/path endpoints are near primary/secondary
	var drive_cells: Dictionary = {}  # grid cell → true
	const CELL_SIZE := 8.0
	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw != "primary" and hw != "secondary":
			continue
		var pts: Array = path.get("points", [])
		for pt in pts:
			var px: float = float(pt[0])
			var pz: float = float(pt[2]) if len(pt) > 2 else float(pt[1])
			var ck := "%d_%d" % [int(floorf(px / CELL_SIZE)), int(floorf(pz / CELL_SIZE))]
			drive_cells[ck] = true

	var xforms: Array = []
	var placed: Dictionary = {}  # dedup

	for path in paths:
		var hw: String = str(path.get("highway", ""))
		if hw != "footway" and hw != "path" and hw != "pedestrian":
			continue
		var pts: Array = path.get("points", [])
		if pts.size() < 2:
			continue
		# Check endpoints for proximity to drives
		for ep_idx in [0, pts.size() - 1]:
			var ex: float = float(pts[ep_idx][0])
			var ez: float = float(pts[ep_idx][2]) if len(pts[ep_idx]) > 2 else float(pts[ep_idx][1])
			if not _loader._in_boundary(ex, ez):
				continue
			var ck := "%d_%d" % [int(floorf(ex / CELL_SIZE)), int(floorf(ez / CELL_SIZE))]
			if not drive_cells.has(ck):
				continue
			# Dedup within 5m
			var dk := "%d_%d" % [int(ex / 5.0), int(ez / 5.0)]
			if placed.has(dk):
				continue
			placed[dk] = true
			var ey: float = _loader._terrain_y(ex, ez)
			# Orient perpendicular to path direction
			var other_idx: int = 1 if ep_idx == 0 else pts.size() - 2
			var ox: float = float(pts[other_idx][0])
			var oz: float = float(pts[other_idx][2]) if len(pts[other_idx]) > 2 else float(pts[other_idx][1])
			var yaw: float = atan2(ex - ox, ez - oz)
			xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(ex, ey, ez)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "CurbRamps")
	print("  Curb ramps: %d placed" % xforms.size())


# ---------------------------------------------------------------------------
# Decorative stone urns — classical vases at formal terraces
# ---------------------------------------------------------------------------
func _build_stone_urns() -> void:
	var mesh : Mesh = _loader._load_first_mesh("res://models/furniture/cp_stone_urn.glb")
	if mesh == null:
		return

	# Apply stone material
	var rw_alb: Texture2D = _loader._load_tex("res://textures/rock_wall_diff.jpg")
	var rw_nrm: Texture2D = _loader._load_tex("res://textures/rock_wall_nrm.jpg")
	var rw_rgh: Texture2D = _loader._load_tex("res://textures/rock_wall_rgh.jpg")
	var stone_mat: Material = _loader._make_stone_material(
		rw_alb, rw_nrm, rw_rgh, Color(0.62, 0.60, 0.56))
	for si in mesh.get_surface_count():
		mesh.surface_set_material(si, stone_mat)

	# Stone urn positions at formal terraces and gardens
	var urn_positions: Array = [
		# Bethesda Terrace — pairs flanking each staircase
		[-465, 1030],  [-495, 1030],   # east wing
		[-465, 1010],  [-495, 1010],   # center
		[-510, 1035],  [-450, 1035],   # flanking
		# Bethesda Terrace upper level
		[-475, 995],   [-485, 995],
		# Cherry Hill
		[-540, 940],   [-560, 940],
		# Conservatory Garden — Italian section
		[1090, -1200], [1110, -1200],
		[1090, -1230], [1110, -1230],
		[1090, -1260], [1110, -1260],
		# Conservatory Garden — French section
		[1050, -1120], [1080, -1120],
		[1050, -1150], [1080, -1150],
		# Belvedere Castle terrace
		[-250, 605],   [-280, 605],
		# Wisteria Pergola
		[-550, 850],   [-530, 850],
		[-550, 870],   [-530, 870],
		# Naumburg Bandshell flanking
		[-560, 1300],  [-580, 1300],
		# Mall / Literary Walk entrance
		[-575, 1480],  [-610, 1480],
	]

	var xforms: Array = []
	for up in urn_positions:
		var ux: float = float(up[0])
		var uz: float = float(up[1])
		var uy: float = _loader._terrain_y(ux, uz)
		var rng := RandomNumberGenerator.new()
		rng.seed = int(ux * 53.0 + uz * 179.0) & 0x7FFFFFFF
		var yaw := rng.randf() * TAU
		xforms.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(ux, uy, uz)))

	if not xforms.is_empty():
		_loader._spawn_multimesh(mesh, null, xforms, "StoneUrns")
	print("  Stone urns: %d placed" % xforms.size())
