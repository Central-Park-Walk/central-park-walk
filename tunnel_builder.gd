# tunnel_builder.gd
# Tunnel geometry: barrel vault ceilings, staircases, portal arches, interior lighting
# Extracted from park_loader.gd — shared utilities accessed via _loader reference.

var _loader  # Reference to park_loader for shared utilities


func _init(loader) -> void:
	_loader = loader


func _build_tunnel(path: Dictionary) -> void:
	# Below-grade underpass: floor at terrain - TUNNEL_H, ceiling at terrain level.
	# Staircases at each end connect surface to tunnel floor (like real CP underpasses).
	var hw:   String = str(path.get("highway", "path"))
	var surf: String = str(path.get("surface", ""))
	var pts:  Array  = path["points"]
	if pts.size() < 2:
		return
	pts = _loader._subdivide_pts(pts, 3.0)
	# Snap Y to rendered terrain surface
	for i in range(pts.size()):
		pts[i] = [pts[i][0], _loader._terrain_y(float(pts[i][0]), float(pts[i][2])), pts[i][2]]

	var width: float = _loader._path_width(path)
	var hw2   := width * 0.5
	var hw2_ext := hw2 + 3.0  # floor/ceiling extend beyond walls to cover depression

	# CC0 concrete texture for ceiling / walls
	var cw_alb: ImageTexture = _loader._load_tex("res://textures/concrete_wall_diff.jpg")
	var cw_nrm: ImageTexture = _loader._load_tex("res://textures/concrete_wall_nrm.jpg")
	var cw_rgh: ImageTexture = _loader._load_tex("res://textures/concrete_wall_rgh.jpg")
	var tun_mat: Material = _loader._make_stone_material(cw_alb, cw_nrm, cw_rgh, Color(0.72, 0.71, 0.70))

	var all_verts   := PackedVector3Array()
	var all_normals := PackedVector3Array()
	var all_uvs     := PackedVector2Array()
	var col_faces   := PackedVector3Array()
	var u_c := 0.0
	var u_w := 0.0
	var u_f := 0.0

	# --- Tunnel body: floor, ceiling, walls ---
	for i in range(pts.size() - 1):
		var x1 := float(pts[i][0]);   var ty1 := float(pts[i][1]);   var z1 := float(pts[i][2])
		var x2 := float(pts[i+1][0]); var ty2 := float(pts[i+1][1]); var z2 := float(pts[i+1][2])

		var ceil_y1: float = ty1 + _loader.PATH_Y        # ceiling at terrain level
		var ceil_y2: float = ty2 + _loader.PATH_Y
		var floor_y1: float = ceil_y1 - _loader.TUNNEL_H   # floor below terrain
		var floor_y2: float = ceil_y2 - _loader.TUNNEL_H

		var seg2 := Vector2(x2 - x1, z2 - z1)
		if seg2.length_squared() < 0.0001:
			continue
		var seg_len := seg2.length()
		var dv := seg2 / seg_len
		var nv := Vector2(-dv.y, dv.x)

		# Floor (faces up) — wider than walls to cover terrain depression
		var u2_f := u_f + seg_len / width
		var fa := Vector3(x1 + nv.x * hw2_ext, floor_y1, z1 + nv.y * hw2_ext)
		var fb := Vector3(x1 - nv.x * hw2_ext, floor_y1, z1 - nv.y * hw2_ext)
		var fc := Vector3(x2 + nv.x * hw2_ext, floor_y2, z2 + nv.y * hw2_ext)
		var fd := Vector3(x2 - nv.x * hw2_ext, floor_y2, z2 - nv.y * hw2_ext)
		all_verts.append_array(PackedVector3Array([fa, fb, fc, fb, fd, fc]))
		for _fi in range(6):
			all_normals.append(Vector3.UP)
		all_uvs.append_array(PackedVector2Array([
			Vector2(u_f, 0.0), Vector2(u_f, 1.0), Vector2(u2_f, 0.0),
			Vector2(u_f, 1.0), Vector2(u2_f, 1.0), Vector2(u2_f, 0.0),
		]))
		col_faces.append_array(PackedVector3Array([fa, fb, fc, fb, fd, fc]))
		u_f = u2_f

		# Barrel vault ceiling — semicircular arch cross-section
		# Vault springs from wall tops, rises to center
		var vault_rise: float = _loader.TUNNEL_H * 0.35  # arch rise proportion
		var spring_y1: float = ceil_y1  # spring line = top of walls = terrain level
		var spring_y2: float = ceil_y2
		var vault_segs := 8  # arch segments across width
		var u2_c := u_c + seg_len / width

		for ai in range(vault_segs):
			var t0 := float(ai) / float(vault_segs)
			var t1 := float(ai + 1) / float(vault_segs)
			var a0 := PI * t0  # 0 at +side, PI at -side
			var a1 := PI * t1
			var lat0 := hw2 * cos(a0)  # lateral offset
			var lat1 := hw2 * cos(a1)
			var rise0 := vault_rise * sin(a0)  # height above spring line
			var rise1 := vault_rise * sin(a1)
			# 4 corners: 2 cross-section points × 2 path points
			var v0 := Vector3(x1 + nv.x * lat0, spring_y1 + rise0, z1 + nv.y * lat0)
			var v1 := Vector3(x1 + nv.x * lat1, spring_y1 + rise1, z1 + nv.y * lat1)
			var v2 := Vector3(x2 + nv.x * lat1, spring_y2 + rise1, z2 + nv.y * lat1)
			var v3 := Vector3(x2 + nv.x * lat0, spring_y2 + rise0, z2 + nv.y * lat0)
			# Normal points inward (down toward walker)
			var mid_a := (a0 + a1) * 0.5
			var vault_n := Vector3(
				-nv.x * cos(mid_a),
				-sin(mid_a),
				-nv.y * cos(mid_a)).normalized()
			all_verts.append_array(PackedVector3Array([v0, v1, v2, v0, v2, v3]))
			for _ci in range(6):
				all_normals.append(vault_n)
			all_uvs.append_array(PackedVector2Array([
				Vector2(u_c, t0), Vector2(u_c, t1), Vector2(u2_c, t1),
				Vector2(u_c, t0), Vector2(u2_c, t1), Vector2(u2_c, t0),
			]))
			col_faces.append_array(PackedVector3Array([v0, v1, v2, v0, v2, v3]))

		# Flat ceiling extensions beyond walls (cover terrain depression)
		for side_ext in [-1.0, 1.0]:
			var se: float = float(side_ext)
			var inner := hw2 * se
			var outer := hw2_ext * se
			var ea := Vector3(x1 + nv.x * inner, spring_y1, z1 + nv.y * inner)
			var eb := Vector3(x1 + nv.x * outer, spring_y1, z1 + nv.y * outer)
			var ec := Vector3(x2 + nv.x * outer, spring_y2, z2 + nv.y * outer)
			var ed := Vector3(x2 + nv.x * inner, spring_y2, z2 + nv.y * inner)
			all_verts.append_array(PackedVector3Array([ea, ec, eb, ea, ed, ec]))
			for _ci in range(6):
				all_normals.append(Vector3.DOWN)
			all_uvs.append_array(PackedVector2Array([
				Vector2(u_c, 0.0), Vector2(u2_c, 0.0), Vector2(u_c, 1.0),
				Vector2(u_c, 1.0), Vector2(u2_c, 0.0), Vector2(u2_c, 1.0),
			]))
			col_faces.append_array(PackedVector3Array([ea, ec, eb, ea, ed, ec]))
		u_c = u2_c

		# Side walls (floor to spring line) — faces inward
		var u2_w: float = u_w + seg_len / _loader.TUNNEL_H
		for side in [-1.0, 1.0]:
			var s: float = side
			var ox := nv.x * hw2 * s
			var oz := nv.y * hw2 * s
			var wa := Vector3(x1 + ox, floor_y1, z1 + oz)
			var wb := Vector3(x2 + ox, floor_y2, z2 + oz)
			var wc := Vector3(x2 + ox, spring_y2, z2 + oz)
			var wd := Vector3(x1 + ox, spring_y1, z1 + oz)
			var wall_n := Vector3(-nv.x * s, 0.0, -nv.y * s)
			all_verts.append_array(PackedVector3Array([wa, wb, wc, wa, wc, wd]))
			for _wj in range(6):
				all_normals.append(wall_n)
			all_uvs.append_array(PackedVector2Array([
				Vector2(u_w, 0.0), Vector2(u2_w, 0.0), Vector2(u2_w, 1.0),
				Vector2(u_w, 0.0), Vector2(u2_w, 1.0), Vector2(u_w, 1.0),
			]))
			col_faces.append_array(PackedVector3Array([wa, wb, wc, wa, wc, wd]))

		# Crown molding — horizontal ledge at spring line (wall-vault transition)
		var molding_h := 0.10  # molding height
		var molding_d := 0.08  # how far it protrudes inward
		for side in [-1.0, 1.0]:
			var s: float = side
			var wall_ox := nv.x * hw2 * s
			var wall_oz := nv.y * hw2 * s
			var inner_ox := nv.x * (hw2 - molding_d) * s
			var inner_oz := nv.y * (hw2 - molding_d) * s
			var m_bot1: float = spring_y1 - molding_h
			var m_bot2: float = spring_y2 - molding_h
			# Bottom face of molding
			var ma := Vector3(x1 + wall_ox, m_bot1, z1 + wall_oz)
			var mb := Vector3(x2 + wall_ox, m_bot2, z2 + wall_oz)
			var mc := Vector3(x2 + inner_ox, m_bot2, z2 + inner_oz)
			var md := Vector3(x1 + inner_ox, m_bot1, z1 + inner_oz)
			all_verts.append_array(PackedVector3Array([ma, mb, mc, ma, mc, md]))
			for _mj in range(6):
				all_normals.append(Vector3.DOWN)
			all_uvs.append_array(PackedVector2Array([
				Vector2(u_w, 0.0), Vector2(u2_w, 0.0), Vector2(u2_w, 0.1),
				Vector2(u_w, 0.0), Vector2(u2_w, 0.1), Vector2(u_w, 0.1),
			]))
			# Inner vertical face of molding
			var mia := Vector3(x1 + inner_ox, m_bot1, z1 + inner_oz)
			var mib := Vector3(x2 + inner_ox, m_bot2, z2 + inner_oz)
			var mic := Vector3(x2 + inner_ox, spring_y2, z2 + inner_oz)
			var mid := Vector3(x1 + inner_ox, spring_y1, z1 + inner_oz)
			var mold_n := Vector3(-nv.x * s, 0.0, -nv.y * s)
			all_verts.append_array(PackedVector3Array([mia, mib, mic, mia, mic, mid]))
			for _mj in range(6):
				all_normals.append(mold_n)
			all_uvs.append_array(PackedVector2Array([
				Vector2(u_w, 0.0), Vector2(u2_w, 0.0), Vector2(u2_w, 0.1),
				Vector2(u_w, 0.0), Vector2(u2_w, 0.1), Vector2(u_w, 0.1),
			]))
		u_w = u2_w

	# --- Staircases at each end ---
	var n_steps: int = int(ceil(_loader.TUNNEL_H / _loader.STEP_RISE))
	var stair_run: float = float(n_steps) * _loader.STEP_DEPTH  # total horizontal distance

	for end_idx in [0, pts.size() - 1]:
		var other_idx := 1 if end_idx == 0 else pts.size() - 2
		var pe := Vector3(float(pts[end_idx][0]), float(pts[end_idx][1]), float(pts[end_idx][2]))
		var po := Vector3(float(pts[other_idx][0]), float(pts[other_idx][1]), float(pts[other_idx][2]))
		# Direction pointing outward from tunnel
		var out_dir := Vector2(pe.x - po.x, pe.z - po.z).normalized()
		var right_dir := Vector2(-out_dir.y, out_dir.x)

		# Sample terrain at stair top (where player enters from surface)
		var top_x := pe.x + out_dir.x * stair_run
		var top_z := pe.z + out_dir.y * stair_run
		var top_ty: float = _loader._terrain_y(top_x, top_z)
		var top_y: float = top_ty + _loader.PATH_Y  # surface level at stair entrance
		var floor_y: float = pe.y + _loader.PATH_Y - _loader.TUNNEL_H  # tunnel floor at entrance end
		var total_rise := top_y - floor_y
		var actual_steps: int = maxi(2, int(ceil(total_rise / _loader.STEP_RISE)))
		var actual_run: float = float(actual_steps) * _loader.STEP_DEPTH
		var actual_rise_per := total_rise / float(actual_steps)

		# Steps: treads + risers with per-step collision
		for si in range(actual_steps):
			var step_y := floor_y + float(si) * actual_rise_per
			var d_start: float = float(si) * _loader.STEP_DEPTH
			var d_end: float = d_start + _loader.STEP_DEPTH
			var sx1 := pe.x + out_dir.x * d_start
			var sz1 := pe.z + out_dir.y * d_start
			var sx2 := pe.x + out_dir.x * d_end
			var sz2 := pe.z + out_dir.y * d_end

			# Tread (horizontal top face)
			var ta := Vector3(sx1 + right_dir.x * hw2, step_y + actual_rise_per, sz1 + right_dir.y * hw2)
			var tb := Vector3(sx1 - right_dir.x * hw2, step_y + actual_rise_per, sz1 - right_dir.y * hw2)
			var tc := Vector3(sx2 + right_dir.x * hw2, step_y + actual_rise_per, sz2 + right_dir.y * hw2)
			var td := Vector3(sx2 - right_dir.x * hw2, step_y + actual_rise_per, sz2 - right_dir.y * hw2)
			var tread_tris := PackedVector3Array([ta, tb, tc, tb, td, tc])
			all_verts.append_array(tread_tris)
			col_faces.append_array(tread_tris)
			for _si in range(6):
				all_normals.append(Vector3.UP)
			all_uvs.append_array(PackedVector2Array([
				Vector2(0.0, 0.0), Vector2(0.0, 1.0), Vector2(0.3, 0.0),
				Vector2(0.0, 1.0), Vector2(0.3, 1.0), Vector2(0.3, 0.0),
			]))

			# Riser (vertical front face)
			var ra := Vector3(sx1 + right_dir.x * hw2, step_y, sz1 + right_dir.y * hw2)
			var rb := Vector3(sx1 - right_dir.x * hw2, step_y, sz1 - right_dir.y * hw2)
			var rc := Vector3(sx1 - right_dir.x * hw2, step_y + actual_rise_per, sz1 - right_dir.y * hw2)
			var rd := Vector3(sx1 + right_dir.x * hw2, step_y + actual_rise_per, sz1 + right_dir.y * hw2)
			var riser_n := Vector3(out_dir.x, 0.0, out_dir.y)
			var riser_tris := PackedVector3Array([ra, rb, rc, ra, rc, rd])
			all_verts.append_array(riser_tris)
			col_faces.append_array(riser_tris)
			for _ri in range(6):
				all_normals.append(riser_n)
			all_uvs.append_array(PackedVector2Array([
				Vector2(0.0, 0.0), Vector2(1.0, 0.0), Vector2(1.0, 0.17),
				Vector2(0.0, 0.0), Vector2(1.0, 0.17), Vector2(0.0, 0.17),
			]))

		# Stairwell side walls (retaining walls alongside stairs)
		var wall_top_y: float = maxf(top_y, pe.y + _loader.PATH_Y)  # wall height = whichever end is higher
		for side in [-1.0, 1.0]:
			var s: float = side
			var wox := right_dir.x * hw2 * s
			var woz := right_dir.y * hw2 * s
			var wa := Vector3(pe.x + wox, floor_y, pe.z + woz)
			var wb := Vector3(top_x + wox, floor_y, top_z + woz)
			var wc := Vector3(top_x + wox, wall_top_y, top_z + woz)
			var wd := Vector3(pe.x + wox, wall_top_y, pe.z + woz)
			var wall_n := Vector3(-right_dir.x * s, 0.0, -right_dir.y * s)
			all_verts.append_array(PackedVector3Array([wa, wb, wc, wa, wc, wd]))
			for _wj in range(6):
				all_normals.append(wall_n)
			all_uvs.append_array(PackedVector2Array([
				Vector2(0.0, 0.0), Vector2(actual_run / _loader.TUNNEL_H, 0.0),
				Vector2(actual_run / _loader.TUNNEL_H, 1.0),
				Vector2(0.0, 0.0), Vector2(actual_run / _loader.TUNNEL_H, 1.0),
				Vector2(0.0, 1.0),
			]))
			col_faces.append_array(PackedVector3Array([wa, wb, wc, wa, wc, wd]))

		# Export terrain depression for this stairwell
		_loader.tunnel_depressions.append({
			"x": pe.x, "z": pe.z,
			"dx": out_dir.x, "dz": out_dir.y,
			"length": actual_run, "hw": hw2 + 1.0,
			"max_depth": total_rise + 1.0,
		})

	# Export tunnel body as polyline for terrain depression
	var body_pts: Array = []
	for i in range(pts.size()):
		body_pts.append([float(pts[i][0]), float(pts[i][2])])
	_loader.tunnel_depressions.append({
		"polyline": body_pts, "hw": hw2 + 3.0,  # extra 3m beyond walls
		"max_depth": _loader.TUNNEL_H + 1.0, "body": true  # extra 1m below floor
	})

	# --- Create visual mesh ---
	if not all_verts.is_empty():
		var mesh: ArrayMesh = _loader._make_mesh(all_verts, all_normals, all_uvs)
		mesh.surface_set_material(0, tun_mat)
		var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.name = "Tunnel_Structure"
		_loader.add_child(mi)

	# --- Collision ---
	if not col_faces.is_empty():
		var tun_body := StaticBody3D.new()
		tun_body.name = "Tunnel_Collision"
		var tun_shape := ConcavePolygonShape3D.new()
		tun_shape.set_faces(col_faces)
		var tun_col := CollisionShape3D.new()
		tun_col.shape = tun_shape
		tun_body.add_child(tun_col)
		_loader.add_child(tun_body)

	# Portal arches at each end
	_build_tunnel_portals(pts, width, _loader.TUNNEL_H, tun_mat)

	# Lights inside tunnel — warm amber, every ~8m along ceiling
	var cum_d := 0.0
	var light_spacing := 8.0
	var next_light := light_spacing * 0.5  # first light at midpoint
	for i in range(pts.size() - 1):
		var lx1 := float(pts[i][0]); var ly1 := float(pts[i][1]); var lz1 := float(pts[i][2])
		var lx2 := float(pts[i+1][0]); var ly2 := float(pts[i+1][1]); var lz2 := float(pts[i+1][2])
		var lseg := Vector2(lx2 - lx1, lz2 - lz1).length()
		while cum_d + lseg >= next_light:
			var t := (next_light - cum_d) / lseg
			var lx := lerpf(lx1, lx2, t)
			var ly := lerpf(ly1, ly2, t)
			var lz := lerpf(lz1, lz2, t)
			var light := OmniLight3D.new()
			light.position = Vector3(lx, ly + _loader.PATH_Y - 0.3, lz)  # just below ceiling
			light.light_color = Color(1.0, 0.85, 0.55)  # warm amber
			light.light_energy = 2.0
			light.omni_range = 6.0
			light.omni_attenuation = 1.5
			light.shadow_enabled = false
			light.name = "TunnelLight"
			_loader.add_child(light)
			next_light += light_spacing
		cum_d += lseg

	# Portal lights at each tunnel entrance — brighter, wider range
	for end_i in [0, pts.size() - 1]:
		var px := float(pts[end_i][0])
		var py := float(pts[end_i][1])
		var pz := float(pts[end_i][2])
		var portal_light := OmniLight3D.new()
		portal_light.position = Vector3(px, py + _loader.PATH_Y - _loader.TUNNEL_H * 0.3, pz)
		portal_light.light_color = Color(1.0, 0.95, 0.85)  # warm white
		portal_light.light_energy = 2.5
		portal_light.omni_range = 12.0
		portal_light.omni_attenuation = 2.0
		portal_light.shadow_enabled = false
		portal_light.name = "TunnelPortalLight"
		_loader.add_child(portal_light)
		_loader._portal_lights.append(portal_light)


func _build_tunnel_portals(pts: Array, width: float, height: float, mat: Material) -> void:
	# Stone arch face at each end of the tunnel — matches barrel vault profile
	var hw2    := width * 0.5
	var n_steps := 8   # arch segments
	var vault_rise := height * 0.35  # must match barrel vault rise in _build_tunnel

	for end_i in [0, pts.size() - 1]:
		var other_i := 1 if end_i == 0 else pts.size() - 2
		var pe  := Vector3(float(pts[end_i][0]),   float(pts[end_i][1]),   float(pts[end_i][2]))
		var po  := Vector3(float(pts[other_i][0]), float(pts[other_i][1]), float(pts[other_i][2]))
		var seg2  := Vector2(po.x - pe.x, po.z - pe.z).normalized()
		# Outward normal of the portal face
		var face_n := -Vector3(seg2.x, 0.0, seg2.y)
		var right  := Vector2(-seg2.y, seg2.x)

		# Portal frame: floor below grade, arch springs from terrain level
		var floor_y: float = pe.y + _loader.PATH_Y - height
		var spring_y: float = pe.y + _loader.PATH_Y  # vault springs from terrain level (wall top)

		var arch_verts   := PackedVector3Array()
		var arch_normals := PackedVector3Array()

		# Left and right vertical jambs (from floor to spring line)
		for side in [-1.0, 1.0]:
			var s: float = side
			var ox := right.x * hw2 * s
			var oz := right.y * hw2 * s
			# Jamb quad: floor → spring line
			var ja := Vector3(pe.x + ox, floor_y,  pe.z + oz)
			var jb := Vector3(pe.x + ox, spring_y, pe.z + oz)
			# Outer edge of jamb (slightly wider)
			var jao := Vector3(pe.x + right.x*(hw2 + 0.6)*s, floor_y,  pe.z + right.y*(hw2 + 0.6)*s)
			var jbo := Vector3(pe.x + right.x*(hw2 + 0.6)*s, spring_y, pe.z + right.y*(hw2 + 0.6)*s)
			arch_verts.append_array(PackedVector3Array([ja, jb, jbo, ja, jbo, jao]))
			for _j in range(6):
				arch_normals.append(face_n)

		# Arch from left spring to right spring — matches barrel vault profile
		for ai in range(n_steps):
			var a1 := PI * float(ai)     / float(n_steps)   # 0 → π (left→right)
			var a2 := PI * float(ai + 1) / float(n_steps)
			# Inner arch edge — uses vault_rise (not full semicircle)
			var ix1 := pe.x + right.x * (-cos(a1) * hw2)
			var iz1 := pe.z + right.y * (-cos(a1) * hw2)
			var iy1 := spring_y + sin(a1) * vault_rise
			var ix2 := pe.x + right.x * (-cos(a2) * hw2)
			var iz2 := pe.z + right.y * (-cos(a2) * hw2)
			var iy2 := spring_y + sin(a2) * vault_rise
			# Outer arch edge (0.6m thick voussoir ring)
			var ring_r := hw2 + 0.6
			var ox1 := pe.x + right.x * (-cos(a1) * ring_r)
			var oz1 := pe.z + right.y * (-cos(a1) * ring_r)
			var oy1 := spring_y + sin(a1) * (vault_rise + 0.3)
			var ox2 := pe.x + right.x * (-cos(a2) * ring_r)
			var oz2 := pe.z + right.y * (-cos(a2) * ring_r)
			var oy2 := spring_y + sin(a2) * (vault_rise + 0.3)
			var vi := Vector3(ix1, iy1, iz1); var vi2 := Vector3(ix2, iy2, iz2)
			var vo := Vector3(ox1, oy1, oz1); var vo2 := Vector3(ox2, oy2, oz2)
			arch_verts.append_array(PackedVector3Array([vi, vi2, vo2, vi, vo2, vo]))
			for _j in range(6):
				arch_normals.append(face_n)

		# Keystone at arch crown — protruding block at the top center
		var ks_hw := 0.20  # keystone half-width
		var ks_relief := 0.08  # how far it protrudes
		var ks_base_y := spring_y + vault_rise - 0.15
		var ks_top_y := spring_y + vault_rise + 0.3 + ks_relief
		var ks_cx := pe.x
		var ks_cz := pe.z
		# Front face of keystone
		var ka := Vector3(ks_cx + right.x * ks_hw, ks_base_y, ks_cz + right.y * ks_hw)
		var kb := Vector3(ks_cx - right.x * ks_hw, ks_base_y, ks_cz - right.y * ks_hw)
		var kc := Vector3(ks_cx - right.x * ks_hw * 0.7, ks_top_y, ks_cz - right.y * ks_hw * 0.7)
		var kd := Vector3(ks_cx + right.x * ks_hw * 0.7, ks_top_y, ks_cz + right.y * ks_hw * 0.7)
		arch_verts.append_array(PackedVector3Array([ka, kb, kc, ka, kc, kd]))
		for _j in range(6):
			arch_normals.append(face_n)

		if not arch_verts.is_empty():
			var mesh: ArrayMesh = _loader._make_mesh(arch_verts, arch_normals)
			mesh.surface_set_material(0, mat)
			var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.name = "Tunnel_Portal"
			_loader.add_child(mi)
