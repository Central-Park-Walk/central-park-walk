# eval_plot_builder.gd
# Vegetation model evaluation plot on the Great Lawn (--eval-plot CLI flag).
# A fixed, walkable specimen garden so model review never means hunting the
# park for wherever a species happened to crop up: every tree species runs
# through the REAL census pipeline (LOD tiers, wind, snag
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
const SPAWN := Vector3(-99.0, 360.0, 228.0)  # x, yaw_degrees, z — pulled back 2026-06-28 so all three TIER_MATCH columns (X -121..-77) frame without the impostor column clipping the right edge; still a short walk to any specimen

# Species a no-flag launch drops into (main.gd defaults --eval-plot to this when
# no mode/pos flag is given; user 2026-06-19). Update per session to the species
# under review. --park forces the plain park instead.
const DEFAULT_EVAL_SPECIES := "london_plane"  # 2026-06-28: TIER_MATCH cross-tier review (was oak)

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

# STAND single-tier pin (user 2026-06-24): when > 0, the size-graded stand row AND
# the 3×3 grove are ALL placed at this height instead of spanning the species'
# HEIGHT_RANGES, so every specimen resolves to ONE tier (tree_builder._get_tier).
# < oak's 12 m _s/_m bound → the whole garden is oak _s saplings. Set to 0.0
# to restore the size-graded s→l stand. (No effect outside stand mode.)
# 11.5 = oak_s.glb's NATIVE built height, so the model renders 1:1 with no runtime
# rescale — the 5 cm min branch diameter then reads at exactly 5 cm (at a smaller
# forced height the whole model, twigs included, scales down) (2026-06-24).
const STAND_FORCE_TIER_H := 11.5

# SOLO mode (user 2026-06-22): focus review on a SINGLE specimen — no size-graded
# row, no grove. Used while iterating one tier in isolation. SOLO_HEIGHT 9.0 →
# london_plane _s sapling (TIER_BOUNDS s/m bound = 13.0). Pair with the launch
# flag --tier-isolate=lod0 to see ONLY that one sapling's lod0 mesh. Set false to
# restore the full size-graded stand garden.
const SOLO_SPECIMEN := false   # 2026-06-22 s4b: review m & l too → size-graded s/m/l stand + grove (was true = single _s sapling)
const SOLO_HEIGHT := 9.0
# VARIANT ROW (user 2026-06-22): show ALL lod0 variants of the matched species in a
# single row at a fixed height, each forced to a distinct variant, so silhouettes can
# be compared side-by-side. Takes precedence over SOLO_SPECIMEN.
const VARIANT_ROW := false     # 2026-06-22 s4b: OFF so the size-graded s/m/l stand shows (was true = 7 _s variants only, hid m & l)
const VARIANT_ROW_N := 7        # london_plane _s has 7 variants
const VARIANT_ROW_DX := 8.0     # spacing (m) between specimens

# VARIANT GRID (user 2026-06-22 s4b): ALL variants of ALL sizes, organized by SIZE —
# one row per tier (s near the spawn → l furthest north), each row holding all N
# variants forced to distinct indices. Takes precedence over VARIANT_ROW/SOLO. The
# heights select the tier via TIER_BOUNDS (london_plane [13,25]); row Z + dx are spaced
# so the bigger tiers don't overlap and the shorter front rows don't block the back.
# 2026-06-24: OFF for oak _s review — the size-graded STAND branch (below) runs
# instead, pinned to one tier by STAND_FORCE_TIER_H. Flip back to true to compare
# london_plane's s/m/l variants for the impostor handoff.
const VARIANT_GRID := false
const GRID_TIERS := [
	# [tier_label, height(m), row_z, variant_spacing(m)]
	# Spacing widened 2026-06-24 (user) so crowns don't merge into a "wall" — a
	# clean per-specimen silhouette is needed to diagnose the impostor↔lod0 size/
	# density handoff (each gap ≳ one crown width at that tier's stature).
	["_s", 10.0, 200.0, 16.0],
	["_m", 15.0, 160.0, 30.0],   # BUCKET MIGRATION 2026-07-06: 22→15 (m-tier centre). docs/smla_bucket_migration.md §2
	["_l", 22.0, 110.0, 44.0],   # BUCKET MIGRATION 2026-07-06: 30→22 (l-tier centre)
]

# TIER MATCH garden (user 2026-06-28): one s/m/l of the matched species in EACH of
# the two LOD tiers (lod0 mesh · far impostor), grouped by tier in
# close proximity so textures/colours can be matched across tiers — the goal is a
# tree that reads the same at 8 m and at 800 m. Each specimen is force_tier-tagged
# so tree_builder renders exactly that tier at full opacity, distance-independent
# (no LOD fade, no distance cull). Takes precedence over VARIANT_GRID/VARIANT_ROW/
# SOLO. No effect outside single-species stand mode.
# LP V2 COMPARE (user 2026-07-02): side-by-side A/B of london_plane (v1, current)
# vs london_plane_v2 (parsimonious lod0) so Chris can judge whether v1's canopy is
# overdone — v1 reads near-opaque when backlit. Two columns (v1 left, v2 right),
# one row per size (s/m/l), every specimen forced to lod0 at full opacity so only
# the near mesh's leaf density is under review (no LOD fade). Both use the pinned
# approved variant (3) so trunk & branches are IDENTICAL — leaf coverage is the
# only variable. Takes precedence over TIER_MATCH/VARIANT_GRID/VARIANT_ROW/SOLO.
# Set false to restore the TIER_MATCH garden. Walk to the north side (or use a low
# --time sun) to put the sun behind the crowns and compare backlit opacity.
const LP_V2_COMPARE := false  # 2026-07-03: v2 densities approved + folded into london_plane; sandbox retired. TIER_MATCH garden restored.
const LPV2_A := "london_plane"       # left column (v1, current)
const LPV2_B := "london_plane_v2"    # right column (v2, parsimonious)
const LPV2_TIER := "lod0"            # the tier under review
const LPV2_VARIANT := 3              # pinned approved variant (both columns)
const LPV2_COL_DX := 30.0            # X gap between the v1 and v2 columns
# [size suffix, forced height m] — heights land in london_plane's tier bounds
# [13, 25] → _s (<13) / _m (<25) / _l (≥25). s nearest spawn, l farthest.
const LPV2_SIZES := [["s", 11.0], ["m", 19.0], ["l", 28.0]]
const LPV2_SIZE_Z := [196.0, 168.0, 136.0]

# SEASON/LOD garden (user 2026-07-04): show every SIZE tier (_s/_m/_l) in its NORMAL
# run-time LOD, in both seasons at once — a summer (July) and a winter (January) lod0
# specimen per tier, placed close so both read as the near mesh, then walked back to
# watch each hand off to its impostor at the size-appropriate distance. Nothing is
# force_tier'd: every specimen runs the ordinary distance fade (tree_builder
# lod0→impostor handoff, which scales with tree height — a short _s pops to impostor
# far sooner than a tall _l), so backing away transitions the tiers in size order,
# exactly as the shipping park does. The per-tree ABSOLUTE season rides in the census
# record ("season" key); tree_builder bakes it into the phenology timing offset, so
# both seasons coexist under the single global season_t. Layout: one receding ROW per
# size (short _s nearest the spawn so the tall _l behind never hides it), July on the
# left of centre and January on the right within each row. Row distances sit inside
# each tier's solid-lod0 band (screen-size LOD: _s ~20 m, _m ~34 m, _l ~51 m for
# london_plane) so all six read as lod0 from the spawn. Takes precedence over
# TIER_MATCH/LP_V2_COMPARE/VARIANT_*/SOLO. Stand mode only.
const SEASON_LOD := true
# [label, absolute season_t]. season_t: 0=spring 1=summer 2=autumn 3=winter (main.gd).
const SL_SEASONS := [["July", 1.5], ["January", 3.5]]
# [size suffix, height m, lateral ±offset from STAND_X, row Z]. Heights land in
# london_plane's TIER_BOUNDS [13, 25] → _s (<13) / _m (<25) / _l (≥25). Z counts north
# (−Z) from SPAWN (Z 228). The layout is a symmetric FAN per season: the small _s sits
# near centre, _m swings wider, _l widest — each at a DISTINCT azimuth so the three
# sizes never merge into one clump (an _l crown is ~20 m wide, so stacking them at one
# azimuth would hide the tiers). Each size's distance from spawn stays inside its own
# height-scaled solid-lod0 band (_s ~20 m, _m ~34 m, _l ~51 m), so every specimen reads
# as the near mesh at the spawn; backing away hands each to its impostor. July fills the
# left half (STAND_X − off), January the right (STAND_X + off).
const SL_TIERS := [
	["s", 11.0,  4.0, 213.0],   # ~16 m from spawn, ±15° (band ~20 m)
	["m", 19.0, 16.0, 200.0],   # ~32 m from spawn, ±30° (band ~34 m)
	["l", 28.0, 31.0, 191.0],   # ~48 m from spawn, ±40° (band ~51 m)
]

const TIER_MATCH := false          # 2026-07-04: superseded by SEASON_LOD (normal distance fade, July+January)
# SCULPT REVIEW (2026-07-17): young / mature / veteran authored stages on the empty
# Great Lawn. `garden` → --eval-plot=london_plane_sculpt. Takes precedence over
# SEASON_LOD when the matched set is the sculpt stages. Production london_plane
# s/m/l are unchanged — use --eval-plot=london_plane for those.
const SCULPT_REVIEW := true
const SCULPT_STAGES := [
	# [plaque, species key, height m]
	["young", "london_plane_sculpt_young", 12.0],
	["mature", "london_plane_sculpt_mature", 20.0],
	["veteran", "london_plane_sculpt_veteran", 26.0],
]
# Isosceles triangle (Chris 2026-07-18): young+mature on the near base, veteran (L)
# at the far north apex. Replaces the old 22 m E–W row so crowns no longer merge.
const SCULPT_BASE_HALF := 40.0    # |X| of young/mature from STAND_X → 80 m base
const SCULPT_BASE_Z := 190.0      # near base (spawn Z 228)
const SCULPT_APEX_Z := 145.0      # far corner — veteran (~45 m north of base)
const TM_TIERS := ["lod0", "impostor"]   # one column per tier (lod0 → impostor; no mid)
# [size suffix, forced height m]: heights land squarely in london_plane's tier
# bounds [13, 25] → _s (<13) / _m (<25) / _l (≥25).
const TM_SIZES := [["s", 11.0], ["m", 19.0], ["l", 28.0]]
const TM_TIER_DX := 22.0                          # X gap between tier columns
const TM_SIZE_Z := [192.0, 166.0, 136.0]          # rows: s nearest spawn → l farthest

# Display name, census species key. Order = stature, tallest rows northmost
# so no specimen hides behind a bigger neighbour when viewed from spawn.
# (zelkova has HEIGHT_RANGES but no GLB — excluded until a model exists.)
const TREE_SPECIES := [
	["Cathedral Elm", "cathedral_elm"],
	["American Elm", "elm"],
	["London Plane", "london_plane"],
	["Oak", "oak"],
	["Conifer (pine)", "conifer"],
	# "Deciduous (generic)" removed — the generic catch-all is now london_plane
	# (the deciduous model was retired 2026-06-26); see the "London Plane" row.
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
	# Tree-sculptor stages (matched by --eval-plot=london_plane_sculpt).
	["London Plane sculpt · young", "london_plane_sculpt_young"],
	["London Plane sculpt · mature", "london_plane_sculpt_mature"],
	["London Plane sculpt · veteran", "london_plane_sculpt_veteran"],
]

var _loader
var _sel_trees: Array = []   # entries from TREE_SPECIES
var _sel_ug: Array = []      # indices into UndergrowthScript.SPECIES
var _stand_mode := false     # exactly one species matched
var _sculpt_review := false  # young/mature/veteran stage row (garden → sculpt)
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
	elif s == "london_plane_sculpt" or s == "sculpt":
		# Explicit sculpt garden: the three authored stages, nothing else.
		for entry in TREE_SPECIES:
			if str(entry[1]).begins_with("london_plane_sculpt_"):
				_sel_trees.append(entry)
		_sculpt_review = SCULPT_REVIEW and not _sel_trees.is_empty()
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
		# Substring "london_plane_sculpt" also selects all three stages.
		if SCULPT_REVIEW and _sel_ug.is_empty() and not _sel_trees.is_empty():
			var all_sculpt := true
			for entry in _sel_trees:
				if not str(entry[1]).begins_with("london_plane_sculpt_"):
					all_sculpt = false
					break
			_sculpt_review = all_sculpt
	_stand_mode = (not _sculpt_review) and (_sel_trees.size() + _sel_ug.size() == 1)
	print("EvalPlot: %d tree species, %d undergrowth species%s%s" % [
		_sel_trees.size(), _sel_ug.size(),
		" (stand mode)" if _stand_mode else "",
		" (sculpt review)" if _sculpt_review else ""])


# Append synthetic census records — called by park_loader BEFORE
# _build_trees(trees) so eval specimens get the full pipeline.
func inject_trees(trees: Array) -> int:
	if _sel_trees.is_empty():
		return 0
	var added := 0
	if _sculpt_review:
		# Isosceles triangle: young (SW) + mature (SE) near base; veteran (L) far N apex.
		for stage in SCULPT_STAGES:
			var label: String = str(stage[0])
			var sp: String = str(stage[1])
			var h: float = float(stage[2])
			var sx: float = STAND_X
			var sz: float = SCULPT_APEX_Z
			if label == "young":
				sx = STAND_X - SCULPT_BASE_HALF
				sz = SCULPT_BASE_Z
			elif label == "mature":
				sx = STAND_X + SCULPT_BASE_HALF
				sz = SCULPT_BASE_Z
			# else veteran: apex at (STAND_X, SCULPT_APEX_Z)
			trees.append(_rec(sx, sz, sp, h))
			added += 1
			print("EvalPlot sculpt: %s at (%.1f, %.1f) h=%.0f" % [label, sx, sz, h])
			_labels.append(["%s · %dm" % [label, int(round(h))],
				Vector2(sx, sz + 8.0), 3.5, 0.018])
		_labels.append(["London Plane sculpt — young · mature · L far",
			Vector2(STAND_X, SCULPT_BASE_Z + 16.0), 11.0, 0.028])
		print("EvalPlot sculpt: isosceles base=%.0fm legs=%.0fm L at Z=%.0f" % [
			SCULPT_BASE_HALF * 2.0,
			sqrt(SCULPT_BASE_HALF * SCULPT_BASE_HALF
				+ (SCULPT_BASE_Z - SCULPT_APEX_Z) * (SCULPT_BASE_Z - SCULPT_APEX_Z)),
			SCULPT_APEX_Z])
		return added
	if _stand_mode and SEASON_LOD:
		# One receding row per size tier (_s/_m/_l); within each row a July (summer) and
		# a January (winter) lod0 specimen, side by side. No force_tier — the ordinary
		# distance fade renders them as the near mesh at spawn and hands each to its
		# impostor when walked away. "season" carries the absolute per-tree season
		# (tree_builder bakes the phenology offset relative to build-time season_t).
		var entry: Array = _sel_trees[0]
		for tier in SL_TIERS:
			var tsuf: String = str(tier[0])          # s / m / l
			var th: float = float(tier[1])           # height (selects the tier)
			var off: float = float(tier[2])          # lateral ± offset from centre
			var rz: float = float(tier[3])           # row Z
			for si in SL_SEASONS.size():
				var slabel: String = str(SL_SEASONS[si][0])
				var sval: float = float(SL_SEASONS[si][1])
				var sgn: float = -1.0 if si == 0 else 1.0   # July left, January right
				var px: float = STAND_X + sgn * off
				var rec: Dictionary = _rec(px, rz, entry[1], th)
				rec["season"] = sval    # absolute per-tree season (tree_builder)
				trees.append(rec)
				added += 1
				_labels.append(["%s · _%s" % [slabel, tsuf],
					Vector2(px, rz + th * 0.5 + 2.0), 2.6, 0.012])
		# Big season titles flanking the near (_s) row; garden title centred above it.
		var s_row_z: float = float(SL_TIERS[0][3])
		var s_off: float = float(SL_TIERS[0][2])
		_labels.append(["July",    Vector2(STAND_X - s_off - 8.0, s_row_z + 10.0), 9.0, 0.028])
		_labels.append(["January", Vector2(STAND_X + s_off + 8.0, s_row_z + 10.0), 9.0, 0.028])
		_labels.append(["%s — summer & winter lod0 per tier · walk back for impostors" % entry[0],
			Vector2(STAND_X, s_row_z + 17.0), 12.0, 0.03])
		return added
	if _stand_mode and LP_V2_COMPARE:
		# v1 vs v2 side-by-side: two columns (v1 left, v2 right), a row per size,
		# every specimen forced to lod0 so only near-mesh leaf density is judged.
		var cols := [[LPV2_A, "v1 (current)"], [LPV2_B, "v2 (parsimonious)"]]
		for ci in cols.size():
			var sp_key: String = cols[ci][0]
			var col_title: String = cols[ci][1]
			var cx: float = STAND_X + (float(ci) - 0.5) * LPV2_COL_DX
			for si in LPV2_SIZES.size():
				var sz: String = LPV2_SIZES[si][0]
				var h: float = float(LPV2_SIZES[si][1])
				var rz: float = LPV2_SIZE_Z[si]
				var rec: Dictionary = _rec(cx, rz, sp_key, h, LPV2_VARIANT)
				rec["force_tier"] = LPV2_TIER
				trees.append(rec)
				added += 1
				_labels.append(["%s · %dm" % [sz, int(round(h))],
					Vector2(cx, rz + 7.0), 2.6, 0.013])
			# Column title, raised above the near end of the column.
			_labels.append([col_title,
				Vector2(cx, float(LPV2_SIZE_Z[0]) + 11.0), 6.0, 0.024])
		_labels.append(["London Plane — lod0 density A/B (v1 vs v2)",
			Vector2(STAND_X, float(LPV2_SIZE_Z[0]) + 18.0), 9.0, 0.03])
		return added
	if _stand_mode and TIER_MATCH:
		# 3 sizes (s/m/l) × 2 tiers (lod0/impostor) = 6 specimens; one column per tier
		# (grouped by tier), one row per size (s nearest spawn → l farthest so the tall
		# trees never hide the short ones). Each tree carries force_tier so tree_builder
		# renders exactly that tier at full opacity (no distance fade) — letting the two
		# representations of the same tree be matched for texture and colour. The species
		# pin (tree_builder LP_SINGLE_VARIANT) keeps lod0/impostor the SAME variant, so
		# any difference is the tier, not the specimen.
		var entry: Array = _sel_trees[0]
		var n_t: int = TM_TIERS.size()
		for ti in n_t:
			var tier: String = TM_TIERS[ti]
			var cx: float = STAND_X + (float(ti) - float(n_t - 1) * 0.5) * TM_TIER_DX
			for si in TM_SIZES.size():
				var sz: String = TM_SIZES[si][0]
				var h: float = float(TM_SIZES[si][1])
				var rz: float = TM_SIZE_Z[si]
				var rec: Dictionary = _rec(cx, rz, entry[1], h)
				rec["force_tier"] = tier
				trees.append(rec)
				added += 1
				_labels.append(["%s · %s · %dm" % [tier, sz, int(round(h))],
					Vector2(cx, rz + 7.0), 2.6, 0.013])
			# Tier (column) title, raised above the near end of the column.
			_labels.append([tier.to_upper(),
				Vector2(cx, float(TM_SIZE_Z[0]) + 11.0), 6.0, 0.024])
		_labels.append(["%s — tier match (lod0 · impostor)" % entry[0],
			Vector2(STAND_X, float(TM_SIZE_Z[0]) + 18.0), 9.0, 0.03])
		return added
	if _stand_mode and VARIANT_GRID:
		# All N variants of every tier, in size-organized rows (s near → l far).
		var entry: Array = _sel_trees[0]
		var n: int = VARIANT_ROW_N
		for row in GRID_TIERS:
			var tlabel: String = row[0]
			var th: float = row[1]
			var rz: float = row[2]
			var dx: float = row[3]
			for i in n:
				var vx: float = STAND_X + (float(i) - float(n - 1) * 0.5) * dx
				trees.append(_rec(vx, rz, entry[1], th, i))
				added += 1
				_labels.append(["v%d" % i, Vector2(vx, rz + dx * 0.45), 2.5, 0.015])
			_labels.append(["%s · %s · all %d variants" % [entry[0], tlabel, n],
				Vector2(STAND_X, rz + dx * 0.9), 6.0, 0.022])
		return added
	if _stand_mode and VARIANT_ROW:
		# All N lod0 variants in a row, each forced to a distinct variant index
		# (same-80m-cell trees otherwise share one variant — tree_builder hash).
		var entry: Array = _sel_trees[0]
		var n: int = VARIANT_ROW_N
		for i in n:
			var vx: float = STAND_X + (float(i) - float(n - 1) * 0.5) * VARIANT_ROW_DX
			trees.append(_rec(vx, STAND_TREE_ROW_Z, entry[1], SOLO_HEIGHT, i))
			added += 1
			_labels.append(["v%d" % i, Vector2(vx, STAND_TREE_ROW_Z + 5.0), 3.0, 0.018])
		_labels.append(["%s · _s · all %d variants" % [entry[0], n],
			Vector2(STAND_X, STAND_TREE_ROW_Z + 9.0), 6.0, 0.024])
		return added
	if _stand_mode and SOLO_SPECIMEN:
		# One specimen only — a single 9m sapling at the ellipse centre, nothing
		# else in the garden (user 2026-06-22, focused _s lod0 review).
		var entry: Array = _sel_trees[0]
		trees.append(_rec(STAND_X, STAND_TREE_ROW_Z, entry[1], SOLO_HEIGHT))
		added += 1
		_labels.append(["%s · _s · %dm" % [entry[0], int(round(SOLO_HEIGHT))],
			Vector2(STAND_X, STAND_TREE_ROW_Z + 8.0), 5.0, 0.02])
		return added
	if _stand_mode:
		var entry: Array = _sel_trees[0]
		var hr: Array = TreeBuilderScript.HEIGHT_RANGES.get(entry[1], [10.0, 22.0])
		var tb: Array = TreeBuilderScript.TIER_BOUNDS.get(entry[1], [12.0, 20.0])
		# Size-graded row: 5 specimens spanning the species' height envelope.
		# Each specimen gets its own plaque (species + tier + height) like a
		# botanical-garden label (user 2026-06-19: "label each model").
		for i in 5:
			var h: float = lerpf(float(hr[0]), float(hr[1]), float(i) / 4.0)
			if STAND_FORCE_TIER_H > 0.0:
				h = STAND_FORCE_TIER_H   # pin every specimen to one tier (oak _s)
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
				if STAND_FORCE_TIER_H > 0.0:
					h = STAND_FORCE_TIER_H   # grove also pinned to one tier (oak _s)
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


func _rec(x: float, z: float, species: String, h: float, variant: int = -1) -> Dictionary:
	var d: Dictionary = {"pos": [x, 0.0, z], "species": species, "dbh": int(h),
		"lidar_h": h, "crown_a": 0, "eval": true}
	if variant >= 0:
		d["variant"] = variant   # eval-only: force this exact lod0 variant (tree_builder)
	return d


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
	# Scale reference (user 2026-06-22): a 1.8 m humanoid beside the row so leaf
	# size can be eyeballed against a real human head (~0.23 m tall). Stand mode
	# only (single-species review). Skipped in SEASON_LOD — that garden reviews the
	# distance LOD/season, not leaf size, and the figure (with its sub-pixel plaque)
	# would only clutter the mid-plot sightline to the far impostors.
	if _stand_mode and SCALE_FIGURE and not SEASON_LOD:
		_make_scale_figure(STAND_X + 4.0, STAND_TREE_ROW_Z)
	print("EvalPlot: %d undergrowth blocks, %d labels placed" % [
		_sel_ug.size(), _labels.size()])


# 1.8 m human scale reference built from primitives. Proportioned ~7.7 heads
# (head 0.23 m tall × 0.16 wide × 0.19 deep — real adult dimensions), feet on
# the terrain, head top at 1.80 m. Purpose: compare in-sim leaf/cluster size to
# a human head against a reference photo.
const SCALE_FIGURE := true

func _make_scale_figure(x: float, z: float) -> void:
	var root := Node3D.new()
	root.name = "ScaleFigure_1m8"
	root.position = Vector3(x, _loader._terrain_y(x, z), z)
	_loader.add_child(root)

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.62, 0.60, 0.58)   # neutral mannequin grey
	mat.roughness = 0.85

	# helper: add a mesh child at center y, optional x offset / per-axis scale
	var add := func(mesh: Mesh, cy: float, cx: float = 0.0, sx: float = 1.0,
			sy: float = 1.0, sz: float = 1.0) -> void:
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.material_override = mat
		mi.position = Vector3(cx, cy, 0.0)
		mi.scale = Vector3(sx, sy, sz)
		root.add_child(mi)

	# Legs — two capsules, ground (≈0.04) to hip (≈0.94)
	var leg := CapsuleMesh.new(); leg.radius = 0.085; leg.height = 0.92
	add.call(leg, 0.49, -0.10)
	add.call(leg, 0.49, 0.10)
	# Pelvis
	var pelvis := BoxMesh.new(); pelvis.size = Vector3(0.30, 0.20, 0.20)
	add.call(pelvis, 0.96)
	# Torso — box, hips (≈0.93) to shoulders (≈1.45)
	var torso := BoxMesh.new(); torso.size = Vector3(0.36, 0.54, 0.22)
	add.call(torso, 1.19)
	# Arms — capsules hanging from shoulder (≈1.44) to wrist (≈0.73)
	var arm := CapsuleMesh.new(); arm.radius = 0.046; arm.height = 0.74
	add.call(arm, 1.07, -0.245)
	add.call(arm, 1.07, 0.245)
	# Neck
	var neck := CapsuleMesh.new(); neck.radius = 0.052; neck.height = 0.14
	add.call(neck, 1.50)
	# Head — sphere scaled to 0.16 W × 0.23 H × 0.19 D, top at 1.80 m
	var head := SphereMesh.new(); head.radius = 0.10; head.height = 0.20
	add.call(head, 1.685, 0.0, 0.80, 1.15, 0.95)

	# Plaque
	var lbl := Label3D.new()
	lbl.text = "1.8 m human\n(head ≈ 0.23 m)"
	lbl.font_size = 64
	lbl.pixel_size = 0.004
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.modulate = Color(1.0, 0.95, 0.7, 0.95)
	lbl.outline_size = 10
	lbl.outline_modulate = Color(0.05, 0.05, 0.05, 0.9)
	lbl.position = Vector3(x, _loader._terrain_y(x, z) + 2.05, z)
	_loader.add_child(lbl)


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
