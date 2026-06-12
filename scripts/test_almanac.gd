extends SceneTree
## Headless validation of almanac.gd against known NYC values.
## Run: godot --headless -s scripts/test_almanac.gd --path .
##
## References (timeanddate.com, NYC 2026; tolerance ±0.15 h / ±1.5 deg):
## - Jun 21 (doy 171): sunrise ~5:25 EDT, sunset ~20:31, noon alt ~72.7
## - Dec 21 (doy 354): sunrise ~7:17 EST, sunset ~16:32, noon alt ~25.8
## - Mar 20 (doy 78):  sunrise ~7:00 EDT, sunset ~19:09, noon alt ~49.5
## - Moon: synodic anchor — new moons near Jan 18 / Feb 17 2026 grid
##   (29.53 d from the 2000-01-06 epoch); full moon ~Jan 3 2026.

const Almanac = preload("res://almanac.gd")

var fails := 0


func check(label: String, got: float, want: float, tol: float) -> void:
	var ok: bool = absf(got - want) <= tol
	if not ok:
		fails += 1
	print("%s %s: got %.2f want %.2f (tol %.2f)" % ["PASS" if ok else "FAIL", label, got, want, tol])


func season_for_doy(doy: float) -> float:
	return fposmod(doy - 59.0, 365.0) / 91.25


func _init() -> void:
	# --- Solar: solstices + equinox ---
	var st_jun: float = season_for_doy(171.0)  # Jun 21
	var ev: Dictionary = Almanac.sun_events(st_jun)
	check("Jun21 sunrise", ev.sunrise, 5.0 + 25.0 / 60.0, 0.15)
	check("Jun21 sunset", ev.sunset, 20.0 + 31.0 / 60.0, 0.15)
	check("Jun21 noon alt", Almanac.sun_horizontal(st_jun, ev.noon).x, 72.7, 1.0)

	var st_dec: float = season_for_doy(354.0)  # Dec 21
	ev = Almanac.sun_events(st_dec)
	check("Dec21 sunrise", ev.sunrise, 7.0 + 17.0 / 60.0, 0.15)
	check("Dec21 sunset", ev.sunset, 16.0 + 32.0 / 60.0, 0.15)
	check("Dec21 noon alt", Almanac.sun_horizontal(st_dec, ev.noon).x, 25.8, 1.0)

	var st_mar: float = season_for_doy(78.0)   # Mar 20
	ev = Almanac.sun_events(st_mar)
	check("Mar20 sunrise", ev.sunrise, 7.0 + 0.0 / 60.0, 0.2)
	check("Mar20 sunset", ev.sunset, 19.0 + 9.0 / 60.0, 0.2)
	check("Mar20 noon alt", Almanac.sun_horizontal(st_mar, ev.noon).x, 49.5, 1.0)

	# Azimuth sanity: June sunrise ENE (~58), noon ~due south, sunset WNW
	check("Jun21 sunrise az", Almanac.sun_horizontal(st_jun, 5.5).y, 58.0, 6.0)
	check("Jun21 13h az", Almanac.sun_horizontal(st_jun, 13.0).y, 180.0, 12.0)
	check("Jun21 sunset az", Almanac.sun_horizontal(st_jun, 20.4).y, 302.0, 6.0)

	# --- Lunar: phase from direction geometry vs the synodic grid ---
	# Full moon 2026-01-03 (doy 2): illum ~1. New moon 2026-01-18 (doy 17).
	var sun3: Vector3
	var moon3: Vector3
	sun3 = Almanac.dir_from_horizontal(Almanac.sun_horizontal(season_for_doy(2.0), 23.0))
	moon3 = Almanac.dir_from_horizontal(Almanac.moon_horizontal(season_for_doy(2.0), 23.0))
	check("Jan3 full illum", Almanac.moon_illum(sun3, moon3), 1.0, 0.06)
	sun3 = Almanac.dir_from_horizontal(Almanac.sun_horizontal(season_for_doy(17.0), 12.0))
	moon3 = Almanac.dir_from_horizontal(Almanac.moon_horizontal(season_for_doy(17.0), 12.0))
	check("Jan18 new illum", Almanac.moon_illum(sun3, moon3), 0.0, 0.06)
	# Quarter ~Jan 25 2026
	sun3 = Almanac.dir_from_horizontal(Almanac.sun_horizontal(season_for_doy(24.0), 20.0))
	moon3 = Almanac.dir_from_horizontal(Almanac.moon_horizontal(season_for_doy(24.0), 20.0))
	check("Jan25 quarter illum", Almanac.moon_illum(sun3, moon3), 0.5, 0.12)

	# Full moon roughly opposite the sun in azimuth at night
	var mh: Vector2 = Almanac.moon_horizontal(season_for_doy(2.0), 23.0)
	print("info Jan3 23h moon elev %.1f az %.1f (winter full moon rides HIGH)" % [mh.x, mh.y])
	check("Jan3 full moon high", mh.x, 70.0, 12.0)

	# --- Fractional-doy regression: the game default season_t=1.5 is
	# doy 195.875 — the .875 must NOT shift the diurnal curve (it once
	# added 21h to the JD on top of the hour: +3h sun, sunset at 23:18).
	ev = Almanac.sun_events(1.5 * 0.0 + season_for_doy(195.0))
	var ev_frac: Dictionary = Almanac.sun_events(1.5)
	check("frac-doy sunset", ev_frac.sunset, ev.sunset, 0.05)
	check("frac-doy 23h sun", Almanac.sun_horizontal(1.5, 23.0).x, -21.0, 4.0)

	# --- World mapping: noon sun must be southish = +Z-ish, up ---
	var d: Vector3 = Almanac.dir_from_horizontal(Vector2(55.0, 180.0))
	check("map south x", d.x, 0.0, 0.01)
	check("map south y", d.y, sin(deg_to_rad(55.0)), 0.01)
	check("map south z", d.z, cos(deg_to_rad(55.0)), 0.01)
	# East = -X
	d = Almanac.dir_from_horizontal(Vector2(0.0, 90.0))
	check("map east x", d.x, -1.0, 0.01)

	print("---")
	print("FAILS: %d" % fails)
	quit(1 if fails > 0 else 0)
