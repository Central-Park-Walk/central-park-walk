# eval_plot_builder.gd
# Vegetation model evaluation plot on the Great Lawn (--eval-plot CLI flag).
# A fixed, walkable specimen garden so model review never means hunting the
# park for wherever a species happened to crop up: every tree species runs
# through the REAL census pipeline (LOD tiers, impostor handoff, wind, snag
# guard via eval=true) and every undergrowth species renders through the REAL
# chunk meshes/materials (undergrowth_builder.build_eval_block), each block
# labelled with a Label3D.
#
# Modes (main.gd parses --eval-plot[=spec] into park_loader.eval_plot):
#   --eval-plot / --eval-plot=all   full lineup, trees north + undergrowth south
#   --eval-plot=trees / =undergrowth  one section only
#   --eval-plot=spicebush,oak       comma list, case-insensitive substring match
#   single match → STAND MODE: a size-graded specimen row plus a
#   natural-density stand at plot centre (docs/vegetation_modeling.md §4 —
#   the stand, not the specimen, is the validation unit).
#
# Site: Great Lawn oval (polygon X -221..23, Z 31..315; north = -Z).
# Ball-field markings are suppressed during eval runs (infrastructure_builder
# .skip_great_lawn_markings) so the lawn is a clean ground plane.

const TreeBuilderScript := preload("res://tree_builder.gd")
const UndergrowthScript := preload("res://undergrowth_builder.gd")

# main.gd default spawn for eval runs. Sits in the CENTRAL Great Lawn ellipse
# (oval center ≈ X-99 Z173), a short viewing distance south of the stand-mode
# clusters, facing north. User 2026-06-19: eval models live at the ellipse
# centre and that central area is the default spawn (was the far south edge
# Z308, 158m from the specimens). Single-species STAND mode is the primary
# use; in grid (--eval-plot=all) mode this puts the camera mid-lineup.
const SPAWN := Vector3(-99.0, 360.0, 213.0)  # x, yaw_degrees, z

# Species a no-flag launch drops into (main.gd defaults --eval-plot to this when
# no mode/pos flag is given; user 2026-06-19). Update per session to the species
# under review. --park forces the plain park instead.
const DEFAULT_EVAL_SPECIES := "london_plane"

# Grid-mode layout
const TREE_ROW_Z0 := 50.0      # northernmost tree row
const TREE_ROW_DZ := 21.0
const TREE_COL_X := [-160.0, -45.0]  # two species blocks per row
const TREE_DX := 15.0          # specimen spacing within a block (s, m, l)
const UG_ROW_Z0 := 252.0       # undergrowth rows south of the trees
const UG_ROW_DZ := 11.0
const UG_COLS := 8
const UG_COL_X0 := -179.0
const UG_COL_DX := 26.0

# Stand-mode layout (single matched species) — clustered at the ellipse centre
# (Z≈173), viewed from SPAWN (Z213) facing north. Trees + undergrowth stand
# bands never coexist (single-species mode), so both centre on the same spot.
const STAND_TREE_ROW_Z := 173.0    # 5 size-graded specimens — ellipse centre
const STAND_TREE_GROVE_Z := 145.0  # 3×3 grove behind (north of) the row
const STAND_UG_ROW_Z := 196.0      # 5 size-graded specimens, near (17m from spawn)
const STAND_UG_STAND_Z := 174.0    # natural-density stand behind them
const STAND_X := -99.0

# Display name, census species key. Order = stature, tallest rows northmost
# so no specimen hides behind a bigger neighbour when viewed from spawn.
# (zelkova has HEIGHT_RANGES but no GLB — excluded until a model exists.)
const TREE_SPECIES := [
	["Cathedral Elm", "cathedral_elm"],
	["American Elm", "elm"],
	["London Plane", "london_plane"],
	["Oak", "oak"],
	["Conifer (pine)", "conifer"],
	["Deciduous (generic)", "deciduous"],
	["Maple", "maple"],
	["Honeylocust", "honeylocust"],
	["Linden", "linden"],
	["Ginkgo", "ginkgo"],
	["Cherry", "cherry"],
	["Birch", "birch"],
	["Willow", "willow"],
	["Callery Pear", "callery_pear"],
	["Magnolia", "magnolia"],
	["Dead Snag", "dead"],
]

var _loader
var _sel_trees: Array = []   # entries from TREE_SPECIES
var _sel_ug: Array = []      # indices into UndergrowthScript.SPECIES
var _stand_mode := false     # exactly one species matched
var _labels: Array = []      # [text, Vector2 xz, height_m, pixel_size]


func _init(loader) -> void:
	_loader = loader


func resolve(spec: String) -> void:
	var s := spec.strip_edges().to_lower()
	if s == "" or s == "all":
		_sel_trees = TREE_SPECIES.duplicate()
		for i in UndergrowthScript.SPECIES.size():
			_sel_ug.append(i)
	elif s == "trees":
		_sel_trees = TREE_SPECIES.duplicate()
	elif s == "undergrowth" or s == "shrubs":
		for i in UndergrowthScript.SPECIES.size():
			_sel_ug.append(i)
	else:
		for tok in s.split(","):
			var t: String = tok.strip_edges()
			if t.is_empty():
				continue
			for entry in TREE_SPECIES:
				if (str(entry[1]).contains(t) or str(entry[0]).to_lower().contains(t)) \
						and entry not in _sel_trees:
					_sel_trees.append(entry)
			for i in UndergrowthScript.SPECIES.size():
				var nm: String = str(UndergrowthScript.SPECIES[i].name).to_lower()
				if nm.contains(t) and i not in _sel_ug:
					_sel_ug.append(i)
			if _sel_trees.is_empty() and _sel_ug.is_empty():
				print("EvalPlot: no species matches '%s'" % t)
	_stand_mode = _sel_trees.size() + _sel_ug.size() == 1
	print("EvalPlot: %d tree species, %d undergrowth species%s" % [
		_sel_trees.size(), _sel_ug.size(), " (stand mode)" if _stand_mode else ""])


# Append synthetic census records — called by park_loader BEFORE
# _build_trees(trees) so eval specimens get the full pipeline.
func inject_trees(trees: Array) -> int:
	if _sel_trees.is_empty():
		return 0
	var added := 0
	if _stand_mode:
		var entry: Array = _sel_trees[0]
		var hr: Array = TreeBuilderScript.HEIGHT_RANGES.get(entry[1], [10.0, 22.0])
		var tb: Array = TreeBuilderScript.TIER_BOUNDS.get(entry[1], [12.0, 20.0])
		# Size-graded row: 5 specimens spanning the species' height envelope.
		# Each specimen gets its own plaque (species + tier + height) like a
		# botanical-garden label (user 2026-06-19: "label each model").
		for i in 5:
			var h: float = lerpf(float(hr[0]), float(hr[1]), float(i) / 4.0)
			var sx: float = STAND_X + (float(i) - 2.0) * 18.0
			trees.append(_rec(sx, STAND_TREE_ROW_Z, entry[1], h))
			added += 1
			# Short per-specimen plaque (tier · height); species name is the title.
			# Alternate height a little so adjacent plaques don't visually collide.
			var tier: String = "_s" if h <= float(tb[0]) else ("_m" if h <= float(tb[1]) else "_l")
			_labels.append(["%s · %dm" % [tier, int(round(h))],
				Vector2(sx, STAND_TREE_ROW_Z + 6.0), 3.0 + float(i % 2) * 1.6, 0.018])
		# Big species title, raised above the row
		_labels.append([entry[0],
			Vector2(STAND_X, STAND_TREE_ROW_Z + 13.0), 11.0, 0.028])
		# 3×3 grove at near-natural spacing — forest-coherence check
		for gx in 3:
			for gz in 3:
				var h: float = lerpf(float(hr[0]), float(hr[1]),
					0.35 + 0.3 * fmod(float(gx * 3 + gz) * 0.37, 1.0))
				trees.append(_rec(STAND_X + (float(gx) - 1.0) * 9.0,
					STAND_TREE_GROVE_Z + (float(gz) - 1.0) * 9.0, entry[1], h))
				added += 1
		_labels.append(["%s grove (9m pitch)" % entry[0],
			Vector2(STAND_X, STAND_TREE_GROVE_Z + 16.0), 6.0, 0.015])
	else:
		for n in _sel_trees.size():
			var entry: Array = _sel_trees[n]
			var bx: float = TREE_COL_X[n % TREE_COL_X.size()]
			var bz: float = TREE_ROW_Z0 + float(n / TREE_COL_X.size()) * TREE_ROW_DZ
			var hr: Array = TreeBuilderScript.HEIGHT_RANGES.get(entry[1], [10.0, 22.0])
			var heights := [float(hr[0]), (float(hr[0]) + float(hr[1])) * 0.5, float(hr[1])]
			for i in 3:
				trees.append(_rec(bx + (float(i) - 1.0) * TREE_DX, bz, entry[1], heights[i]))
				added += 1
			_labels.append(["%s — %d…%dm" % [entry[0], int(hr[0]), int(hr[1])],
				Vector2(bx, bz + 10.0), 5.0, 0.012])
	return added


func _rec(x: float, z: float, species: String, h: float) -> Dictionary:
	return {"pos": [x, 0.0, z], "species": species, "dbh": int(h), "lidar_h": h,
		"crown_a": 0, "eval": true}


# Place undergrowth blocks + all labels — called by park_loader AFTER
# _build_undergrowth() (meshes/materials must be loaded).
func build(ug_builder) -> void:
	var missing: Array = []
	for n in _sel_ug.size():
		var sp_idx: int = _sel_ug[n]
		var sp: Dictionary = UndergrowthScript.SPECIES[sp_idx]
		var is_shrub: bool = sp_idx <= 6
		var s_lo: float = sp.s[0]
		var s_hi: float = sp.s[1]
		var rng := RandomNumberGenerator.new()
		rng.seed = sp_idx * 7919 + 13
		var pts: Array = []
		var scales: Array = []
		if _stand_mode:
			# Size-graded specimen row near spawn
			var step: float = 6.0 if is_shrub else 3.0
			for i in 5:
				pts.append(Vector2(STAND_X + (float(i) - 2.0) * step, STAND_UG_ROW_Z))
				scales.append(lerpf(s_lo, s_hi, float(i) / 4.0))
			# Natural-density stand behind the row — the validation unit
			var count: int = 30 if is_shrub else 40
			var radius: float = 9.0 if is_shrub else 7.0
			for i in count:
				var a: float = rng.randf() * TAU
				var r: float = sqrt(rng.randf()) * radius
				pts.append(Vector2(STAND_X + cos(a) * r, STAND_UG_STAND_Z + sin(a) * r))
				scales.append(clampf(rng.randfn(s_lo + (s_hi - s_lo) * 0.4,
					(s_hi - s_lo) * 0.2), s_lo, s_hi))
			_labels.append([_ug_display(sp), Vector2(STAND_X, STAND_UG_ROW_Z + 5.0), 2.0, 0.005])
			_labels.append(["%s stand" % _ug_display(sp),
				Vector2(STAND_X, STAND_UG_STAND_Z + float(radius) + 3.0), 2.6, 0.005])
		else:
			var cx: float = UG_COL_X0 + float(n % UG_COLS) * UG_COL_DX
			var cz: float = UG_ROW_Z0 + float(n / UG_COLS) * UG_ROW_DZ
			# One isolated specimen at the front (south), small stand behind it
			pts.append(Vector2(cx, cz + 3.5))
			scales.append(s_lo + (s_hi - s_lo) * 0.85)
			var count: int = 6 if is_shrub else 8
			var radius: float = 3.0 if is_shrub else 1.8
			for i in count:
				var a: float = rng.randf() * TAU
				var r: float = sqrt(rng.randf()) * radius
				pts.append(Vector2(cx + cos(a) * r, cz - 1.5 + sin(a) * r))
				scales.append(lerpf(s_lo, s_hi, float(i) / float(maxi(count - 1, 1))))
			_labels.append([_ug_display(sp), Vector2(cx, cz + 5.5), 2.0, 0.0045])
		if not ug_builder.build_eval_block(sp_idx, pts, scales, "eval_%d" % sp_idx):
			missing.append(sp.name)
	if not missing.is_empty():
		print("EvalPlot: no mesh for %s — labels placed anyway" % str(missing))
	for lb in _labels:
		_make_label(lb[0], lb[1], lb[2], lb[3])
	print("EvalPlot: %d undergrowth blocks, %d labels placed" % [
		_sel_ug.size(), _labels.size()])


func _ug_display(sp: Dictionary) -> String:
	# "Shrub_Spicebush" -> "Spicebush", "Herb_JoePyeWeed" -> "JoePyeWeed"
	var nm: String = str(sp.name)
	var us := nm.find("_")
	return nm.substr(us + 1) if us >= 0 else nm


func _make_label(text: String, xz: Vector2, height: float, pixel_size: float) -> void:
	var lbl := Label3D.new()
	lbl.text = text
	lbl.font_size = 64
	lbl.pixel_size = pixel_size
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.render_priority = 1
	lbl.modulate = Color(0.95, 0.95, 0.90, 0.85)
	lbl.outline_size = 10
	lbl.outline_modulate = Color(0.05, 0.08, 0.05, 0.85)
	lbl.position = Vector3(xz.x, _loader._terrain_y(xz.x, xz.y) + height, xz.y)
	_loader.add_child(lbl)
