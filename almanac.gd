class_name Almanac
## Astronomical almanac for Central Park (docs/sky.md §2.5).
##
## True solar + lunar positions from game date/time, replacing the fixed
## keyframed sun path: NYC noon sun is ~26° in December vs ~73° in June,
## sunrise/sunset times and azimuths swing with the seasons, and the moon
## rises/sets and changes phase on the real synodic cycle (29.53 d).
##
## Conventions:
## - season_t (game): 0 = March 1, 1 unit = 91.25 days; year fixed 2026.
## - hour: local clock time 0-24 (DST applied by day-of-year).
## - Horizontal coords: elevation deg above horizon, azimuth deg from
##   north going east (0 N, 90 E, 180 S, 270 W).
## - World axes (verified against park data): east = -X, north = -Z.
## - Light euler: pitch = -elevation, yaw = 180 + azimuth (Godot
##   DirectionalLight basis*+Z points TOWARD the body).
##
## Algorithms: low-precision Meeus/Astronomical-Almanac series — sun
## ~0.01°, moon ~0.3°, plenty for rendering. No topocentric parallax.

const LAT_DEG := 40.7829          # Central Park
const LON_DEG := -73.9654         # east-positive
const JD_2026_JAN1 := 2461041.5   # 2026-01-01 00:00 UTC
const DAYS_MAR1 := 59.0           # 2026 is not a leap year

# Cached per-day sun events (numeric solve); key = int day-of-year
static var _events_cache := {}


static func doy_from_season(season_t: float) -> float:
	return fposmod(DAYS_MAR1 + season_t * 91.25, 365.0)


# UTC offset for NYC by day-of-year: EDT (-4) roughly Mar 8 - Nov 1.
static func _utc_offset(doy: float) -> float:
	return -4.0 if (doy >= 66.0 and doy < 305.0) else -5.0


static func _julian_day(doy: float, hour_local: float) -> float:
	var hour_utc: float = hour_local - _utc_offset(doy)
	return JD_2026_JAN1 + doy + hour_utc / 24.0


# Geocentric solar ecliptic longitude (deg) + distance-free bits we need.
static func _sun_ecliptic_lon(n: float) -> float:
	var L: float = fposmod(280.460 + 0.9856474 * n, 360.0)
	var g: float = deg_to_rad(fposmod(357.528 + 0.9856003 * n, 360.0))
	return fposmod(L + 1.915 * sin(g) + 0.020 * sin(2.0 * g), 360.0)


static func _obliquity(n: float) -> float:
	return deg_to_rad(23.439 - 0.0000004 * n)


# Equatorial (RA, dec) -> horizontal (elev, az) at the park.
static func _equatorial_to_horizontal(ra: float, dec: float, n: float) -> Vector2:
	var gmst_deg: float = fposmod(280.46061837 + 360.98564736629 * n, 360.0)
	var lst: float = deg_to_rad(fposmod(gmst_deg + LON_DEG, 360.0))
	var h: float = lst - ra  # hour angle, rad
	var phi: float = deg_to_rad(LAT_DEG)
	var sin_a: float = sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(h)
	var elev: float = rad_to_deg(asin(clampf(sin_a, -1.0, 1.0)))
	var az: float = rad_to_deg(atan2(-cos(dec) * sin(h),
			sin(dec) * cos(phi) - cos(dec) * sin(phi) * cos(h)))
	return Vector2(elev, fposmod(az, 360.0))


## Solar (elevation deg, azimuth deg) for game date/time.
static func sun_horizontal(season_t: float, hour: float) -> Vector2:
	var doy: float = doy_from_season(season_t)
	var n: float = _julian_day(doy, hour) - 2451545.0
	var lam: float = deg_to_rad(_sun_ecliptic_lon(n))
	var eps: float = _obliquity(n)
	var ra: float = atan2(cos(eps) * sin(lam), cos(lam))
	var dec: float = asin(sin(eps) * sin(lam))
	return _equatorial_to_horizontal(ra, dec, n)


## Lunar (elevation deg, azimuth deg) for game date/time.
static func moon_horizontal(season_t: float, hour: float) -> Vector2:
	var doy: float = doy_from_season(season_t)
	var n: float = _julian_day(doy, hour) - 2451545.0
	var t: float = n / 36525.0
	# Astronomical Almanac low-precision lunar series (deg)
	var lam_deg: float = 218.32 + 481267.883 * t \
		+ 6.29 * sin(deg_to_rad(134.9 + 477198.85 * t)) \
		- 1.27 * sin(deg_to_rad(259.2 - 413335.38 * t)) \
		+ 0.66 * sin(deg_to_rad(235.7 + 890534.23 * t)) \
		+ 0.21 * sin(deg_to_rad(269.9 + 954397.70 * t)) \
		- 0.19 * sin(deg_to_rad(357.5 + 35999.05 * t)) \
		- 0.11 * sin(deg_to_rad(186.6 + 966404.05 * t))
	var beta: float = deg_to_rad( \
		5.13 * sin(deg_to_rad(93.3 + 483202.03 * t)) \
		+ 0.28 * sin(deg_to_rad(228.2 + 960400.87 * t)) \
		- 0.28 * sin(deg_to_rad(318.3 + 6003.18 * t)) \
		- 0.17 * sin(deg_to_rad(217.6 - 407332.20 * t)))
	var lam: float = deg_to_rad(fposmod(lam_deg, 360.0))
	var eps: float = _obliquity(n)
	# Ecliptic -> equatorial
	var x: float = cos(beta) * cos(lam)
	var y: float = cos(beta) * sin(lam) * cos(eps) - sin(beta) * sin(eps)
	var z: float = cos(beta) * sin(lam) * sin(eps) + sin(beta) * cos(eps)
	var ra: float = atan2(y, x)
	var dec: float = asin(clampf(z, -1.0, 1.0))
	return _equatorial_to_horizontal(ra, dec, n)


## World-space unit direction TOWARD a body (east = -X, north = -Z, up = +Y).
static func dir_from_horizontal(h: Vector2) -> Vector3:
	var e: float = deg_to_rad(h.x)
	var a: float = deg_to_rad(h.y)
	return Vector3(-cos(e) * sin(a), sin(e), -cos(e) * cos(a))


## Illuminated fraction of the moon from the two body directions:
## k = (1 - cos(elongation)) / 2. Geometry only — no ecliptic phase math.
static func moon_illum(sun_dir: Vector3, moon_dir: Vector3) -> float:
	return clampf((1.0 - sun_dir.dot(moon_dir)) * 0.5, 0.0, 1.0)


## Sun event times (local clock hours) for the game date:
## {sunrise, sunset, noon}. Numeric solve at 5-minute resolution with
## linear refinement; rise/set at standard -0.833 deg (refraction + limb).
static func sun_events(season_t: float) -> Dictionary:
	var doy: int = int(doy_from_season(season_t))
	if _events_cache.has(doy):
		return _events_cache[doy]
	# doy is the day's MIDNIGHT origin — hour carries the time of day.
	# (+0.5 here once shifted every JD in the solve by 12 h.)
	var fdoy: float = float(doy)
	var step: float = 1.0 / 12.0
	var prev_elev: float = _elev_at(fdoy, 0.0)
	var sunrise := 6.0
	var sunset := 18.0
	var noon := 12.0
	var best_elev := -90.0
	var hour := step
	while hour <= 24.0 + 0.001:
		var elev: float = _elev_at(fdoy, hour)
		# Linear refinement works for both crossings: the fraction
		# (elev + 0.833)/(elev - prev) measures back from `hour`.
		if prev_elev < -0.833 and elev >= -0.833:
			sunrise = hour - step * (elev + 0.833) / maxf(elev - prev_elev, 0.001)
		elif prev_elev >= -0.833 and elev < -0.833:
			sunset = hour - step * (elev + 0.833) / minf(elev - prev_elev, -0.001)
		if elev > best_elev:
			best_elev = elev
			noon = hour
		prev_elev = elev
		hour += step
	var ev := {"sunrise": sunrise, "sunset": sunset, "noon": noon}
	_events_cache[doy] = ev
	return ev


static func _elev_at(doy: float, hour: float) -> float:
	# season_t from doy (inverse of doy_from_season, same year wrap)
	var st: float = fposmod(doy - DAYS_MAR1, 365.0) / 91.25
	return sun_horizontal(st, hour).x
