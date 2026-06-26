extends Node
## Day/night cycle: 5-keyframe interpolation controlling sky, sun, fog,
## ambient, SSAO, color grading, volumetric fog, cloud coverage.
##
## Self-contained: receives environment objects at init, called with
## current state each frame. Pushes global shader parameters.

# Weather enum must match main.gd
enum Weather { CLEAR, RAIN, THUNDERSTORM, SNOW, FOG }

const ALM := preload("res://almanac.gd")

# Environment objects — set by main.gd after _setup_environment()
var env: Environment
var sky_mat: ShaderMaterial
var vol_sky = null  # clayjohn volumetric cloud sky (if loaded)
var sun: DirectionalLight3D

# Facade materials — set by main.gd after park_loader finishes
var facade_materials: Array = []

# Internal state
var _keyframes: Array = []
var _last_applied_tod: float = -999.0
var _last_night_factor: float = -1.0


func _ready() -> void:
	_build_keyframes()


func apply(time_of_day: float, weather: int, wind_vec: Vector2,
		lightning_flash: float, user_gamma: float, season_t: float) -> void:
	if not env or not sky_mat or not sun:
		return
	# Only update when time actually changes (~0.01h threshold)
	if absf(time_of_day - _last_applied_tod) < 0.01 and _last_applied_tod >= 0.0:
		return
	_apply(time_of_day, weather, wind_vec, lightning_flash, user_gamma, season_t)


func force_apply(time_of_day: float, weather: int, wind_vec: Vector2,
		lightning_flash: float, user_gamma: float, season_t: float) -> void:
	_last_applied_tod = -999.0
	_apply(time_of_day, weather, wind_vec, lightning_flash, user_gamma, season_t)


func get_lamp_emission() -> float:
	## Returns interpolated lamp emission for SpotLight3D pool.
	return _lamp_emission

var _lamp_emission: float = 0.0

# Sky calibration (2026-06-10, measured sweep vs real-photo targets — see
# docs/rendering.md sky calibration). These are the FULL-DAY values; they
# blend to 1.0 (upstream demo behavior) as the sun drops below the horizon,
# because the flat multipliers turn night into daylight-overcast (measured:
# 22:00 sky median 52 at x1 vs 121 at x5).
const SKY_CAL_BG := 5.0     # background-atmosphere LUT multiplier
const SKY_CAL_SUN := 20.0   # cloud-march direct-sun multiplier
const SKY_CAL_AMB := 6.0    # cloud-march ambient multiplier
# --sky-cal=bg:sun:amb sets exact values for calibration sweeps (bypasses
# the sun-elevation blend). -1 components = unset.
var sky_cal_override := Vector3(-1.0, -1.0, -1.0)
# Ground-light calibration (2026-06-11, docs/grass.md §6): the sky
# calibration above brightened the rendered sky ~1.2-1.5 stops, but the
# DirectionalLight that lights the ground was never recalibrated against
# it — sunlit turf measured lawn/sky 0.49 vs ~1.0 in reference footage
# (scripts/turf_luminance_check.py). SUN_CAL multiplies sun.light_energy,
# day-blended like the sky cal so night/dusk are untouched. The
# cloud-march direct-sun term multiplies LIGHT_ENERGY (clouds.glsl:171),
# so cal_sun is divided by the same factor — the calibrated sky stays
# fixed by construction. Ambient is NOT scaled: raising direct only moves
# the direct:diffuse ratio from the keyframes' ~2:1 toward the physical
# ~5:1 of a clear noon (reference: "shadow pools are very dark").
# Measured sweep 2026-06-11 (hero pose, fixed cloud seed): lawn luma
# 92→128/255 (reference band 126–149); direct:diffuse lands ~4.9:1
# (physical clear-noon). Sky compensation verified: dark-cloud fraction
# flat across the sweep (16.8%→15.6%); +10 sky median = background mie
# term (physical sun-side haze). Full record: docs/grass.md §6.
# 2026-06-12: trimmed 3.0 -> 2.3 with the almanac sun — June noon
# elevation rose 55->73 deg (real), lifting flat-lawn NdotL ~17%; lawn
# median measured 160/255 at 3.0 and 154 at 2.6 vs the 126-149
# reference band (turf_luminance_check.py, same hero pose/protocol);
# 2.3 lands ~149. Response is shallower than the direct:diffuse ratio
# predicts (sheen + ambient share) — measure, don't extrapolate.
const SUN_CAL := 2.3
# --sun-cal=mult sets the exact multiplier (bypasses the day blend).
var sun_cal_override := -1.0
# Aerial-perspective / fog-veil calibration (rendering.md §6c,
# COMPARISON.md #5). The volumetric-fog sun in-scatter term multiplies
# sun.light_energy, so SUN_CAL tripled it without compensation (the same
# coupling the cloud direct-sun term got via cal_sun / sun_mult) — the
# distant tree line measured +48% warm-grey wash at ~400 m vs the real
# ~10% slightly-blue veil (scripts/fog_veil_check.py). The volumetric
# energy is divided by sun_mult here (day-blended, night untouched), then
# the FOG_CAL_* constants calibrate each in-scatter source on top.
# Shipped values measured 2026-06-11 (hero pose, fixed cloud seed 7):
# /sun_mult compensation alone took the veil +48%→+20%; component zeroing
# showed the sun term owns ~95% of the remainder → SUNVOL 0.4 (blended to
# 1.0 at low sun via sun_low_factor — god rays keep full strength) + the
# sky-blue emission floor ×7 (day-blended, night keeps 0.06) lands the
# tree-line veil at +10% of unfogged, ΔRGB +9/+8/+16 (blue-led). Targets
# and full record: rendering.md §6c.
const FOG_VOL_ENERGY_BASE := 5.0   # sun.light_volumetric_fog_energy (god rays)
const FOG_CAL_SUNVOL := 0.4   # × sun volumetric energy, AFTER /sun_mult
const FOG_CAL_AMB := 1.0      # × volumetric_fog_ambient_inject (base 0.12)
const FOG_CAL_EMIS := 7.0     # × volumetric_fog_emission_energy (base 0.06)
const FOG_CAL_DENSITY := 1.0  # × keyframed vol_fog_density
const FOG_CAL_GI := 1.0       # × volumetric_fog_gi_inject (base 0.25)
# --fog-cal=sunvol:amb:emis:density:gi sets exact multipliers for sweeps.
var fog_cal_override: Array = [-1.0, -1.0, -1.0, -1.0, -1.0]
# --diag-hide=cloudshadows: zero the procedural ground cloud-shadow term
# for attribution A/Bs (visible volumetric clouds unaffected).
var cloud_shadow_disabled := false

# Weather-state -> weather-map table (sky.md §2.6). CLEAR additionally
# swaps to broken_dramatic on scheduled mornings/evenings (see
# _clear_sky_map). FOG shares the stratus deck — the existing fog volumes
# carry the at-ground look.
const WEATHER_MAP := {
	Weather.CLEAR: "fair_cumulus",
	Weather.RAIN: "stratus_overcast",
	Weather.THUNDERSTORM: "storm_congestus",
	Weather.SNOW: "stratocumulus_sheet",
	Weather.FOG: "stratus_overcast",
}
const WEATHER_MAP_FADE := 30.0  # seconds; fronts arrive, not pop
# --cloud-map=name forces a specific map regardless of weather state;
# --sky-dramatic forces the dramatic schedule on (1) or off (0). -1 unset.
var cloud_map_override := ""
var dramatic_override := -1
# High ice layer opacities (sky.md P2). -1 = data-driven schedule below;
# --high-clouds=cir:cs:ac forces them for capture/calibration.
var high_clouds_override := Vector3(-1.0, -1.0, -1.0)

# Live cloud state, published each _apply for the in-game cloud panel
# (cloud_debug.gd) — the actual values the schedule produced, so a sky
# that looks wrong shows its real numbers instead of guessed ones.
var live_cir := 0.0
var live_cs := 0.0
var live_ac := 0.0
var live_canon := 0.0
var live_map := "fair_cumulus"
# Manual cloud mode (cloud panel): freeze coverage/density to these and
# take the map/high-cloud overrides above instead of the schedule.
var manual_clouds := false
var manual_cover := 0.30
var manual_density := 0.05


# Dramatic-sky schedule (sky.md §2.6 "CLEAR -> dramatic"): a few mornings/
# evenings per game-month swap CLEAR's cumulus for broken_dramatic — big
# torn sheets that low sun paints. Deterministic per game-day so a given
# date always has the same sky character.
func _clear_sky_map(canon_hour: float, season_t: float) -> String:
	var in_window: bool = (canon_hour >= 17.0 and canon_hour <= 21.0) \
			or (canon_hour >= 5.0 and canon_hour <= 7.5)
	if dramatic_override == 0:
		return "fair_cumulus"
	if dramatic_override == 1 and in_window:
		return "broken_dramatic"
	if not in_window:
		return "fair_cumulus"
	var day: int = int(floor(59.0 + season_t * 91.25))
	var h: float = fposmod(sin(float(day) * 12.9898) * 43758.5453, 1.0)
	return "broken_dramatic" if h < 0.18 else "fair_cumulus"


func _apply(time_of_day: float, weather: int, wind_vec: Vector2,
		lightning_flash: float, user_gamma: float, season_t: float) -> void:
	# --- Celestial almanac (docs/sky.md 2.5) ---------------------------
	# True sun/moon positions for the game date+time. The keyframes keep
	# owning color/energy/mood, but are indexed by a CANONICAL hour: a
	# piecewise-linear remap anchored on the date's real solar events, so
	# "sunset keyframe colors" happen at the actual sunset (16:32 in
	# December, 20:31 in June) instead of a fixed wall-clock hour. All
	# hour windows below run on canonical time.
	var sun_ev: Dictionary = ALM.sun_events(season_t)
	var canon: float = _canonical_hour(time_of_day, sun_ev)
	var sun_h: Vector2 = ALM.sun_horizontal(season_t, time_of_day)
	var moon_h: Vector2 = ALM.moon_horizontal(season_t, time_of_day)
	var sun_dir3: Vector3 = ALM.dir_from_horizontal(sun_h)
	var moon_dir3: Vector3 = ALM.dir_from_horizontal(moon_h)
	var moon_k: float = ALM.moon_illum(sun_dir3, moon_dir3)

	var pair: Array = _find_keyframe_pair(canon)
	var a: Dictionary = pair[0]
	var b: Dictionary = pair[1]
	var t: float = float(pair[2])

	# Cloud properties
	var cc_val: float = _lerp_kf("cloud_coverage", a, b, t)
	var cs_val: float = _lerp_kf("cloud_speed", a, b, t)
	# Day factor for the sky + ground-light calibrations. sun_pitch can NOT
	# be the day signal — the keyframes repurpose the light as a high moon
	# at night (21:00 pitch −65). sun_energy is the honest one: 0.9–0.95 in
	# daylight, 0.05 at night.
	var day_f: float = smoothstep(0.15, 0.65, _lerp_kf("sun_energy", a, b, t))
	# Twilight window factor: the background-sky calibration (cal_bg) must
	# stay up while the celestial sun (computed below) is rendering real
	# twilight — day_f tracks sun_energy, which fades exactly when the LUT
	# needs its AgX exposure correction most (the below-horizon LUT is
	# already dark; un-calibrating it too turned dusk near-black,
	# 2026-06-11). Falls to 0 in step with the celestial->moon blend so
	# the accepted night sky stays exact.
	var twilight_f: float = 0.0
	if canon >= 19.0 and canon < 21.0:
		twilight_f = 1.0 - smoothstep(20.55, 21.0, canon)
	elif canon >= 5.0 and canon < 6.5:
		twilight_f = smoothstep(5.0, 5.3, canon)
	var sky_f: float = maxf(day_f, twilight_f)
	var sun_mult: float = lerpf(1.0, SUN_CAL, day_f)
	if sun_cal_override > 0.0:
		sun_mult = sun_cal_override
	if vol_sky:
		vol_sky.cloud_coverage = clampf(cc_val, 0.20, 0.50)
		vol_sky.density = clampf(_lerp_kf("cloud_density", a, b, t) * 0.08, 0.02, 0.10)
		# Day-blended sky calibration (constants above).
		var cal_bg: float = lerpf(1.0, SKY_CAL_BG, sky_f)
		var cal_sun: float = lerpf(1.0, SKY_CAL_SUN, day_f)
		var cal_amb: float = lerpf(1.0, SKY_CAL_AMB, day_f)
		if sky_cal_override.x > 0.0: cal_bg = sky_cal_override.x
		if sky_cal_override.y > 0.0: cal_sun = sky_cal_override.y
		if sky_cal_override.z > 0.0: cal_amb = sky_cal_override.z
		# Compensate the SUN_CAL ground-light raise: the cloud direct-sun
		# term multiplies LIGHT_ENERGY, so divide it back out here.
		vol_sky.sun_scale = cal_sun / sun_mult
		vol_sky.ambient_scale = cal_amb
		sky_mat.set_shader_parameter("sky_brightness", cal_bg)
	else:
		var sky_top: Color = _lerp_kf("sky_top", a, b, t)
		var sky_hor: Color = _lerp_kf("sky_horizon", a, b, t)
		var gnd_bot: Color = _lerp_kf("gnd_bottom", a, b, t)
		var gnd_hor: Color = _lerp_kf("gnd_horizon", a, b, t)
		sky_mat.set_shader_parameter("sky_top_color", Vector3(sky_top.r, sky_top.g, sky_top.b))
		sky_mat.set_shader_parameter("sky_horizon_color", Vector3(sky_hor.r, sky_hor.g, sky_hor.b))
		sky_mat.set_shader_parameter("ground_bottom_color", Vector3(gnd_bot.r, gnd_bot.g, gnd_bot.b))
		sky_mat.set_shader_parameter("ground_horizon_color", Vector3(gnd_hor.r, gnd_hor.g, gnd_hor.b))
		sky_mat.set_shader_parameter("cloud_coverage", cc_val)
		sky_mat.set_shader_parameter("cloud_density", _lerp_kf("cloud_density", a, b, t))
		var cc_top: Color = _lerp_kf("cloud_color_top", a, b, t)
		var cc_bot: Color = _lerp_kf("cloud_color_bottom", a, b, t)
		sky_mat.set_shader_parameter("cloud_color_top", Vector3(cc_top.r, cc_top.g, cc_top.b))
		sky_mat.set_shader_parameter("cloud_color_bottom", Vector3(cc_bot.r, cc_bot.g, cc_bot.b))
		sky_mat.set_shader_parameter("cloud_speed", cs_val)
	# cloud_coverage_g feeds ONLY the procedural ground cloud-shadow path
	# (hash_noise.gdshaderinc cloud_shadow consumers) — zeroing it kills
	# ground shadow bands without touching the visible volumetric clouds.
	RenderingServer.global_shader_parameter_set("cloud_coverage_g",
		0.0 if cloud_shadow_disabled else cc_val)
	RenderingServer.global_shader_parameter_set("cloud_speed_g", cs_val)

	# Ambient
	env.ambient_light_color  = _lerp_kf("ambient_color", a, b, t)
	env.ambient_light_energy = _lerp_kf("ambient_energy", a, b, t)

	# Tonemapping
	env.tonemap_exposure = _lerp_kf("exposure", a, b, t)
	env.tonemap_white    = _lerp_kf("white", a, b, t)

	# SSAO
	env.ssao_radius    = _lerp_kf("ssao_radius", a, b, t)
	env.ssao_intensity = _lerp_kf("ssao_intensity", a, b, t)
	env.ssao_power     = _lerp_kf("ssao_power", a, b, t)

	# Colour grading
	env.adjustment_saturation = _lerp_kf("saturation", a, b, t)
	env.adjustment_contrast   = _lerp_kf("contrast", a, b, t)
	env.adjustment_brightness = _lerp_kf("brightness", a, b, t) * user_gamma
	if lightning_flash > 0.01:
		env.adjustment_brightness *= (1.0 + lightning_flash * 0.8)

	# Volumetric fog (FOG_CAL_*: aerial-perspective calibration above).
	# pitch_val is the REAL solar elevation (negated, light convention) —
	# the keyframed sun_pitch is no longer read anywhere.
	var pitch_val: float = -sun_h.x
	var sun_low_factor: float = smoothstep(-25.0, -5.0, pitch_val) * smoothstep(5.0, -5.0, pitch_val)
	# sunvol blends back to 1.0 as the sun drops: the high-sun veil is what
	# we calibrate down; low-sun forward scatter IS the god rays — keep it.
	# The outer day_f blend keeps night exact (sun_low_factor reads 0 at
	# night because the light doubles as a HIGH moon, pitch -65 at 21:00).
	# emis is the blue-skylight floor: it fades in with sun ELEVATION (a
	# day_f gate alone turned 6:30 golden-hour mist blue — keyframe
	# sun_energy is already 0.90 at dawn), and day_f keeps night exact
	# (the high moon, pitch -65, would otherwise read as elevation 1.0).
	var cal_fog_sunvol: float = lerpf(1.0, lerpf(FOG_CAL_SUNVOL, 1.0, sun_low_factor), day_f)
	var cal_fog_amb: float = FOG_CAL_AMB
	var high_sun_f: float = day_f * smoothstep(15.0, 40.0, -pitch_val)
	var cal_fog_emis: float = lerpf(1.0, FOG_CAL_EMIS, high_sun_f)
	var cal_fog_density: float = FOG_CAL_DENSITY
	var cal_fog_gi: float = FOG_CAL_GI
	# The veil calibration is a CLEAR-SKY aerial-perspective fix. Heavy
	# weather is its own look (absolute density overrides below) — the
	# bright sun in-scatter IS the white of a fog bank, and a blue
	# skylight floor under overcast is wrong. /sun_mult compensation
	# stays (it restores the long-standing pre-SUN_CAL weather look).
	if weather != Weather.CLEAR:
		cal_fog_sunvol = 1.0
		cal_fog_emis = 1.0
	if fog_cal_override[0] > 0.0: cal_fog_sunvol = fog_cal_override[0]
	if fog_cal_override[1] > 0.0: cal_fog_amb = fog_cal_override[1]
	if fog_cal_override[2] > 0.0: cal_fog_emis = fog_cal_override[2]
	if fog_cal_override[3] > 0.0: cal_fog_density = fog_cal_override[3]
	if fog_cal_override[4] > 0.0: cal_fog_gi = fog_cal_override[4]
	# Compensate the SUN_CAL ground-light raise out of the fog sun
	# in-scatter (it multiplies LIGHT_ENERGY), same construction as the
	# cloud direct-sun term.
	sun.light_volumetric_fog_energy = FOG_VOL_ENERGY_BASE * cal_fog_sunvol / sun_mult
	env.volumetric_fog_ambient_inject = 0.12 * cal_fog_amb
	env.volumetric_fog_emission_energy = 0.06 * cal_fog_emis
	env.volumetric_fog_gi_inject = 0.25 * cal_fog_gi
	env.volumetric_fog_density = _lerp_kf("vol_fog_density", a, b, t) * cal_fog_density
	var base_aniso: float = _lerp_kf("vol_fog_anisotropy", a, b, t)
	env.volumetric_fog_anisotropy = lerpf(base_aniso, 0.88, sun_low_factor * 0.5)

	# Weather overrides
	if weather == Weather.FOG:
		env.volumetric_fog_density = 0.005
		env.adjustment_saturation = 0.45
		env.adjustment_brightness = 0.90
		if vol_sky:
			vol_sky.cloud_coverage = 0.60
			vol_sky.density = 0.08
		else:
			sky_mat.set_shader_parameter("cloud_coverage", 0.75)
			sky_mat.set_shader_parameter("cloud_density", 0.80)
			sky_mat.set_shader_parameter("cloud_type", 1.0)
	elif weather == Weather.RAIN:
		env.volumetric_fog_density = 0.004
		env.adjustment_saturation *= 0.7
		env.adjustment_brightness *= 0.88
		if vol_sky:
			vol_sky.cloud_coverage = 0.58
			vol_sky.density = 0.07
		else:
			sky_mat.set_shader_parameter("cloud_coverage", 0.72)
			sky_mat.set_shader_parameter("cloud_density", 0.78)
			sky_mat.set_shader_parameter("cloud_type", 1.0)
	elif weather == Weather.THUNDERSTORM:
		env.volumetric_fog_density = 0.008
		env.adjustment_saturation *= 0.50
		env.adjustment_brightness *= 0.75
		if vol_sky:
			vol_sky.cloud_coverage = 0.68
			# Denser than the keyframe clamp (0.10): storm_congestus towers
			# read friendly-white at 0.10 — extinction darkens the bases.
			vol_sky.density = 0.14
		else:
			sky_mat.set_shader_parameter("cloud_coverage", 0.82)
			sky_mat.set_shader_parameter("cloud_density", 0.85)
			sky_mat.set_shader_parameter("cloud_type", 2.0)
	elif weather == Weather.SNOW:
		env.volumetric_fog_density = 0.003
		env.adjustment_saturation *= 0.75
		if vol_sky:
			vol_sky.cloud_coverage = 0.55
			vol_sky.density = 0.06
		else:
			sky_mat.set_shader_parameter("cloud_coverage", 0.70)
			sky_mat.set_shader_parameter("cloud_density", 0.72)
			sky_mat.set_shader_parameter("cloud_type", 1.0)

	# Wind reduces volumetric fog slightly
	var wind_str: float = wind_vec.length()
	if wind_str > 0.1:
		env.volumetric_fog_density *= lerpf(1.0, 0.85, clampf(wind_str * 0.3, 0.0, 1.0))

	# Sky reflection color for water surfaces
	var sky_r: Color = _lerp_kf("fog_color", a, b, t)
	var sun_c: Color = _lerp_kf("sun_color", a, b, t)
	var reflect := sky_r.lerp(sun_c, 0.2)
	reflect = Color(reflect.r * 0.75, reflect.g * 0.85, reflect.b * 1.1)
	RenderingServer.global_shader_parameter_set("sky_reflect_color",
		Vector3(reflect.r, reflect.g, reflect.b))

	# Morning dew
	var dew := 0.0
	if canon >= 4.5 and canon <= 8.5:
		if canon <= 6.0:
			dew = smoothstep(4.5, 6.0, canon)
		else:
			dew = 1.0 - smoothstep(6.0, 8.5, canon)
	if weather != Weather.CLEAR:
		dew = 0.0
	RenderingServer.global_shader_parameter_set("dew_amount", dew)

	# Dawn mist — peaks just AFTER sunrise (5.75) as golden mist. The old
	# 5.5 peak filled the pre-dawn twilight window with warm-grey soup and
	# erased the deep-blue + amber stratification the celestial sun now
	# produces (references: notes/refs/sky_2026_06_11/sunrise_01).
	if weather == Weather.CLEAR:
		var dawn_mist := 0.0
		if canon >= 5.6 and canon <= 7.5:
			if canon <= 6.3:
				dawn_mist = smoothstep(5.6, 6.3, canon)
			else:
				dawn_mist = 1.0 - smoothstep(6.3, 7.5, canon)
			env.volumetric_fog_density += dawn_mist * 0.0012
			env.adjustment_saturation *= (1.0 - dawn_mist * 0.10)

	# Seasonal fog and atmosphere modulation
	var s_autumn := smoothstep(1.5, 2.5, season_t) * (1.0 - smoothstep(2.5, 3.5, season_t))
	var s_winter := smoothstep(2.5, 3.5, season_t)
	if s_autumn > 0.01:
		env.volumetric_fog_density *= (1.0 + s_autumn * 0.12)
	if s_winter > 0.01:
		env.volumetric_fog_density *= (1.0 + s_winter * 0.15)
		env.adjustment_saturation *= (1.0 - s_winter * 0.2)

	# Monthly cloud coverage from NOAA data
	var monthly_cover: Array = [0.47, 0.45, 0.44, 0.36, 0.31, 0.30,
		0.34, 0.41, 0.37, 0.47, 0.43, 0.47]
	var month_idx: int = int(season_t * 3.0 + 2.0) % 12  # season_t=0 is March (almanac); array is Jan-first
	var month_next: int = (month_idx + 1) % 12
	var month_frac: float = fmod(season_t * 3.0, 1.0)
	var data_cover: float = lerpf(monthly_cover[month_idx], monthly_cover[month_next], month_frac)
	if weather == Weather.CLEAR:
		if vol_sky:
			vol_sky.cloud_coverage = maxf(lerpf(vol_sky.cloud_coverage, data_cover, 0.7), 0.25)
			# Dramatic torn-sheet skies want more presence than the NOAA
			# fair-weather number (the map's own gaps keep blue visible).
			if _clear_sky_map(canon, season_t) == "broken_dramatic":
				vol_sky.cloud_coverage = maxf(vol_sky.cloud_coverage, 0.42)
		else:
			var cc: float = sky_mat.get_shader_parameter("cloud_coverage")
			sky_mat.set_shader_parameter("cloud_coverage", lerpf(cc, data_cover, 0.7))
			if s_winter > 0.3:
				sky_mat.set_shader_parameter("cloud_type", lerpf(0.0, 1.0, s_winter))

	# Weather-map selection + crossfade (sky.md P1): each weather state
	# gets its meteorologically correct cloud structure instead of
	# "denser cumulus". set_weather_map no-ops when already targeting.
	if vol_sky:
		var map_name: String = cloud_map_override
		if map_name == "":
			map_name = _clear_sky_map(canon, season_t) \
					if weather == Weather.CLEAR else WEATHER_MAP[weather]
		vol_sky.set_weather_map(map_name, WEATHER_MAP_FADE)
		live_map = map_name
	live_canon = canon

	# High ice layer presence (sky.md P2 / §2.6): cirrus/cirrostratus/
	# altocumulus opacity by weather state, season (more ice aloft in
	# winter), and the dramatic schedule (the dusk mackerel hero sky).
	if vol_sky:
		var cir := 0.0
		var cs := 0.0
		var ac := 0.0
		if weather == Weather.CLEAR:
			# Deterministic per-day cirrus presence — some days carry wispy
			# high cloud, others are bald blue; winter runs icier.
			var day_i: int = int(floor(59.0 + season_t * 91.25))
			var hh: float = fposmod(sin(float(day_i) * 7.13 + 2.0) * 43758.5453, 1.0)
			cir = smoothstep(0.45, 0.90, hh) * (0.25 + 0.35 * s_winter)
			if _clear_sky_map(canon, season_t) == "broken_dramatic":
				# The dusk showcase: mackerel altocumulus + a cirrostratus veil
				# catch the low sun (the salmon-pink-on-periwinkle reference).
				# Kept moderate — a full-strength mackerel deck reads busy.
				cs = 0.40
				ac = 0.0  # altocumulus "pill" clouds disabled for now (Chris 2026-06-26); was 0.45
				cir = maxf(cir, 0.35)
		elif weather == Weather.SNOW:
			cs = 0.60          # cirrostratus ahead of/with snow fronts
			cir = 0.30
		elif weather == Weather.THUNDERSTORM:
			cir = 0.50         # anvil cirrus shelf (P3 refines)
			cs = 0.20
		# RAIN / FOG: none — the low deck hides anything above it.
		if high_clouds_override.x >= 0.0: cir = high_clouds_override.x
		if high_clouds_override.y >= 0.0: cs = high_clouds_override.y
		if high_clouds_override.z >= 0.0: ac = high_clouds_override.z
		sky_mat.set_shader_parameter("cirrus_amount", cir)
		sky_mat.set_shader_parameter("cirrostratus_amount", cs)
		sky_mat.set_shader_parameter("altocumulus_amount", ac)
		live_cir = cir
		live_cs = cs
		live_ac = ac
		if OS.is_stdout_verbose():
			print("[HICLOUD] wall=%.1f canon=%.1f season_t=%.2f weather=%d map=%s cir=%.2f cs=%.2f ac=%.2f"
					% [time_of_day, canon, season_t, weather, live_map, cir, cs, ac])
		# Manual cloud mode (in-game panel): hold coverage/density steady so
		# the schedule doesn't fight the sliders. Map + high-cloud amounts
		# come through the *_override fields the panel already set above.
		if manual_clouds:
			vol_sky.cloud_coverage = manual_cover
			vol_sky.density = manual_density

	# Sun / moon directional light (SUN_CAL: ground-light calibration
	# above). Direction comes from the ALMANAC (real seasonal path);
	# keyframes — indexed by canonical hour — keep owning energy/color.
	# The shadow light's elevation floors at 2 deg while the sun is up
	# (shadow stability); the celestial sun below carries the real
	# horizon crossing for the sky systems.
	var sun_light_dir: Vector3 = ALM.dir_from_horizontal(
			Vector2(maxf(sun_h.x, 2.0), sun_h.y))

	# Night: the light becomes the MOON at its true position, with energy
	# scaled by phase (full keeps the accepted night look; new moon drops
	# to a sky-glow floor). The handover spans the twilight canon windows
	# where keyframed energy is fading to 0.05 — shadows are near-
	# invisible, so the direction swing cannot pop. When the moon is set,
	# the floor keeps a dim high "sky-glow" light instead of lighting
	# from below the horizon.
	var moon_f: float = 0.0
	if canon >= 20.3 or canon < 5.7:
		if canon >= 20.3 and canon < 21.0:
			moon_f = smoothstep(20.3, 21.0, canon)
		elif canon >= 5.0 and canon < 5.7:
			moon_f = 1.0 - smoothstep(5.0, 5.7, canon)
		else:
			moon_f = 1.0
	var energy_scale: float = 1.0
	var light_dir3: Vector3 = sun_light_dir
	if moon_f > 0.0:
		var moon_up: float = smoothstep(-4.0, 6.0, moon_h.x)
		# Perceptual phase curve: quarter moon ~25% of full (real is ~8%,
		# but the game still needs a readable night).
		var phase_e: float = 0.08 + 0.92 * pow(moon_k, 2.2)
		var skyglow_dir: Vector3 = ALM.dir_from_horizontal(Vector2(65.0, 220.0))
		var moon_light_dir: Vector3 = ALM.dir_from_horizontal(
				Vector2(maxf(moon_h.x, 5.0), moon_h.y)).slerp(
				skyglow_dir, 1.0 - moon_up).normalized()
		light_dir3 = sun_light_dir.slerp(moon_light_dir, moon_f).normalized()
		energy_scale = lerpf(1.0, maxf(phase_e * moon_up, 0.06), moon_f)

	sun.light_energy    = _lerp_kf("sun_energy", a, b, t) * sun_mult * energy_scale
	sun.light_color     = _lerp_kf("sun_color", a, b, t)
	# basis*+Z must point TOWARD the body (FrameData.update_light_data).
	sun.transform.basis = Basis.looking_at(-light_dir3, Vector3.UP)
	sun.directional_shadow_max_distance = _lerp_kf("shadow_dist", a, b, t)

	# Celestial sun for the sky systems (atmosphere LUT, cloud march, sky
	# shader): the TRUE almanac sun — it crosses the horizon for real, so
	# the Hillaire LUT's sunrise/sunset band (0 to -6 deg, where ALL the
	# color lives) is reached on every date at its actual event times.
	# Below -6 deg it hands over to the night light (= the moon), keeping
	# the moonlit-clouds/night-sky construction.
	var night_celest: float = smoothstep(-6.0, -10.0, sun_h.x)
	var cel_dir: Vector3 = sun_dir3.slerp(light_dir3, night_celest).normalized()
	if vol_sky:
		vol_sky.celestial_direction = cel_dir
	sky_mat.set_shader_parameter("celestial_dir", cel_dir)

	# Moon + sun disk rendering inputs (sky.md 2.5): true sun for the
	# disk/blaze + the moon's terminator, moon direction/phase, and the
	# perceptual apparent-size drive — bodies swell ~1.6x near the
	# horizon (the classic perceptual moon illusion, art-directed),
	# shrink slightly toward zenith; refraction squashes the disk
	# vertically within ~2 deg of the horizon.
	sky_mat.set_shader_parameter("true_sun_dir", sun_dir3)
	sky_mat.set_shader_parameter("moon_dir", moon_dir3)
	var moon_vis: float = smoothstep(-1.5, 2.0, moon_h.x)
	var moon_scale: float = 1.8 * (1.0 + 0.6 * smoothstep(10.0, 0.0, moon_h.x)) \
			* (1.0 - 0.12 * smoothstep(30.0, 60.0, moon_h.x))
	var moon_squash: float = 1.0 - 0.22 * smoothstep(4.0, -0.5, moon_h.x)
	sky_mat.set_shader_parameter("moon_params",
			Vector4(moon_k, moon_scale, moon_vis, moon_squash))
	if vol_sky:
		vol_sky.sun_disk_scale = 2.5 * (1.0 + 0.5 * smoothstep(10.0, 0.0, sun_h.x)) \
				* (1.0 - 0.15 * smoothstep(40.0, 70.0, sun_h.x))
	sky_mat.set_shader_parameter("sun_disk_squash",
			1.0 - 0.22 * smoothstep(4.0, -0.5, sun_h.x))

	# Lamp emission
	_lamp_emission = _lerp_kf("lamp_emission", a, b, t)
	RenderingServer.global_shader_parameter_set("lamp_glow", clampf(_lamp_emission / 5.0, 0.0, 1.0))

	# Building window night_factor (canonical: tracks real dusk/dawn)
	var nf: float = 0.0
	if canon >= 18.0 and canon < 21.0:
		nf = (canon - 18.0) / 3.0
	elif canon >= 21.0 or canon < 5.0:
		nf = 1.0
	elif canon >= 5.0 and canon < 7.0:
		nf = 1.0 - (canon - 5.0) / 2.0
	if absf(nf - _last_night_factor) > 0.005:
		_last_night_factor = nf
		for fm in facade_materials:
			if fm is ShaderMaterial:
				fm.set_shader_parameter("night_factor", nf)

	_last_applied_tod = time_of_day


# Wall-clock -> canonical keyframe hour (sky.md 2.5). The keyframes were
# authored against June-ish anchor times (5.0 night-end .. 5.75 sunrise ..
# 12.0 noon .. 20.2 sunset .. 21.0 night); this piecewise-linear remap
# pins those anchors to the date's REAL solar events, so keyframe colors,
# fog, dew, lamps and the twilight windows all track the seasons. The
# night span (sunset+0.8 .. sunrise-0.75) stretches across canon 21->29.
func _canonical_hour(wall: float, ev: Dictionary) -> float:
	var aw: Array = [ev.sunrise - 0.75, ev.sunrise, ev.sunrise + 0.75,
			ev.noon, ev.sunset - 1.2, ev.sunset, ev.sunset + 0.8]
	var ac: Array = [5.0, 5.75, 6.5, 12.0, 19.0, 20.2, 21.0]
	var n: int = aw.size()
	var w: float = wall
	if w < aw[0]:
		w += 24.0
	for i in n:
		var a0: float = aw[i]
		var a1: float = (aw[0] + 24.0) if i == n - 1 else aw[i + 1]
		var c0: float = ac[i]
		var c1: float = (ac[0] + 24.0) if i == n - 1 else ac[i + 1]
		if w >= a0 and w < a1:
			return fposmod(c0 + (w - a0) / maxf(a1 - a0, 0.001) * (c1 - c0), 24.0)
	return wall


func _find_keyframe_pair(hour: float) -> Array:
	var n: int = _keyframes.size()
	for i in n:
		var ha: float = float(_keyframes[i]["hour"])
		var j: int = (i + 1) % n
		var hb: float = float(_keyframes[j]["hour"])
		var span: float
		var off: float
		if hb <= ha:
			span = (hb + 24.0) - ha
			if hour >= ha:
				off = hour - ha
			else:
				off = (hour + 24.0) - ha
		else:
			span = hb - ha
			off = hour - ha
		if off >= 0.0 and off < span:
			var t: float = off / span
			return [_keyframes[i], _keyframes[j], t]
	return [_keyframes[0], _keyframes[0], 0.0]


func _lerp_kf(key: String, a: Dictionary, b: Dictionary, t: float):
	var va = a[key]
	var vb = b[key]
	if va is Color:
		return (va as Color).lerp(vb as Color, t)
	else:
		return lerpf(float(va), float(vb), t)


# NOTE (sky.md 2.5): keyframe hours are CANONICAL (June-anchored event
# times — see _canonical_hour). sun_pitch/sun_yaw fields are retained in
# the data but no longer drive the light direction (the almanac does);
# sun_pitch=-2 entries still document the intended low-sun moments.
func _build_keyframes() -> void:
	_keyframes.append({"hour": 5.0, "sky_top": Color(0.02, 0.02, 0.06), "sky_horizon": Color(0.14, 0.11, 0.20), "gnd_bottom": Color(0.02, 0.02, 0.035), "gnd_horizon": Color(0.10, 0.07, 0.12), "ambient_color": Color(0.16, 0.14, 0.22), "ambient_energy": 0.45, "exposure": 1.05, "white": 6.0, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 0.75, "contrast": 1.02, "brightness": 0.96, "fog_color": Color(0.12, 0.10, 0.14), "fog_energy": 0.20, "fog_scatter": 0.05, "fog_density": 0.0005, "fog_aerial": 0.20, "fog_sky_affect": 0.6, "sun_energy": 0.05, "sun_color": Color(0.65, 0.72, 0.95), "sun_pitch": -10.0, "sun_yaw": -100.0, "shadow_dist": 250.0, "lamp_emission": 5.0, "vol_fog_density": 0.0004, "vol_fog_anisotropy": 0.45, "cloud_coverage": 0.24, "cloud_density": 0.55, "cloud_color_top": Color(0.42, 0.40, 0.44), "cloud_color_bottom": Color(0.16, 0.14, 0.18), "cloud_speed": 0.00003})
	# 5.75 sunrise moment (2026-06-11 dawn/dusk vibrancy): the sun light dips
	# to 2 deg elevation, deep orange, while the celestial sun (sky systems)
	# crosses the horizon. References: notes/refs/sky_2026_06_11/.
	_keyframes.append({"hour": 5.75, "sky_top": Color(0.10, 0.16, 0.40), "sky_horizon": Color(1.0, 0.52, 0.08), "gnd_bottom": Color(0.05, 0.04, 0.04), "gnd_horizon": Color(0.30, 0.20, 0.14), "ambient_color": Color(0.42, 0.34, 0.28), "ambient_energy": 0.55, "exposure": 1.0, "white": 5.8, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 1.08, "contrast": 1.02, "brightness": 0.98, "fog_color": Color(0.67, 0.42, 0.24), "fog_energy": 0.40, "fog_scatter": 0.18, "fog_density": 0.0005, "fog_aerial": 0.18, "fog_sky_affect": 0.4, "sun_energy": 0.35, "sun_color": Color(1.0, 0.55, 0.28), "sun_pitch": -2.0, "sun_yaw": -98.0, "shadow_dist": 300.0, "lamp_emission": 2.0, "vol_fog_density": 0.00035, "vol_fog_anisotropy": 0.85, "cloud_coverage": 0.25, "cloud_density": 0.52, "cloud_color_top": Color(1.0, 0.68, 0.11), "cloud_color_bottom": Color(0.82, 0.34, 0.11), "cloud_speed": 0.00005})
	_keyframes.append({"hour": 6.5, "sky_top": Color(0.18, 0.32, 0.62), "sky_horizon": Color(0.84, 0.51, 0.18), "gnd_bottom": Color(0.10, 0.08, 0.06), "gnd_horizon": Color(0.46, 0.34, 0.22), "ambient_color": Color(0.48, 0.38, 0.26), "ambient_energy": 0.75, "exposure": 0.95, "white": 5.5, "ssao_radius": 1.5, "ssao_intensity": 1.5, "ssao_power": 1.5, "saturation": 1.0, "contrast": 1.02, "brightness": 1.0, "fog_color": Color(0.55, 0.41, 0.27), "fog_energy": 0.45, "fog_scatter": 0.18, "fog_density": 0.0005, "fog_aerial": 0.18, "fog_sky_affect": 0.30, "sun_energy": 0.90, "sun_color": Color(1.0, 0.75, 0.50), "sun_pitch": -12.0, "sun_yaw": -95.0, "shadow_dist": 350.0, "lamp_emission": 0.0, "vol_fog_density": 0.0003, "vol_fog_anisotropy": 0.80, "cloud_coverage": 0.25, "cloud_density": 0.50, "cloud_color_top": Color(1.0, 0.77, 0.35), "cloud_color_bottom": Color(0.66, 0.39, 0.22), "cloud_speed": 0.00005})
	_keyframes.append({"hour": 12.0, "sky_top": Color(0.12, 0.28, 0.65), "sky_horizon": Color(0.55, 0.60, 0.68), "gnd_bottom": Color(0.12, 0.12, 0.10), "gnd_horizon": Color(0.38, 0.36, 0.32), "ambient_color": Color(0.50, 0.46, 0.38), "ambient_energy": 0.95, "exposure": 1.0, "white": 6.0, "ssao_radius": 2.0, "ssao_intensity": 1.3, "ssao_power": 1.4, "saturation": 1.0, "contrast": 1.01, "brightness": 1.0, "fog_color": Color(0.62, 0.60, 0.56), "fog_energy": 0.5, "fog_scatter": 0.06, "fog_density": 0.00015, "fog_aerial": 0.12, "fog_sky_affect": 0.30, "sun_energy": 0.95, "sun_color": Color(0.95, 0.92, 0.85), "sun_pitch": -55.0, "sun_yaw": -20.0, "shadow_dist": 400.0, "lamp_emission": 0.0, "vol_fog_density": 0.0001, "vol_fog_anisotropy": 0.45, "cloud_coverage": 0.28, "cloud_density": 0.50, "cloud_color_top": Color(0.95, 0.95, 0.93), "cloud_color_bottom": Color(0.68, 0.68, 0.66), "cloud_speed": 0.00006})
	_keyframes.append({"hour": 19.0, "sky_top": Color(0.18, 0.14, 0.38), "sky_horizon": Color(0.82, 0.50, 0.28), "gnd_bottom": Color(0.10, 0.07, 0.04), "gnd_horizon": Color(0.48, 0.35, 0.20), "ambient_color": Color(0.48, 0.42, 0.32), "ambient_energy": 0.88, "exposure": 0.95, "white": 5.5, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 1.0, "contrast": 1.02, "brightness": 0.98, "fog_color": Color(0.55, 0.45, 0.35), "fog_energy": 0.45, "fog_scatter": 0.18, "fog_density": 0.0005, "fog_aerial": 0.18, "fog_sky_affect": 0.30, "sun_energy": 0.95, "sun_color": Color(1.0, 0.72, 0.45), "sun_pitch": -12.0, "sun_yaw": 95.0, "shadow_dist": 350.0, "lamp_emission": 0.0, "vol_fog_density": 0.0003, "vol_fog_anisotropy": 0.80, "cloud_coverage": 0.28, "cloud_density": 0.50, "cloud_color_top": Color(0.85, 0.55, 0.38), "cloud_color_bottom": Color(0.55, 0.30, 0.18), "cloud_speed": 0.00005})
	# 20.2 sunset moment (2026-06-11): mirror of 5.75 — sun light at 2 deg,
	# deep red-orange; the celestial sun crosses the horizon here and the
	# post-sunset window 20.2-20.8 carries the reference pinks/corals.
	_keyframes.append({"hour": 20.2, "sky_top": Color(0.086, 0.116, 0.179), "sky_horizon": Color(0.81, 0.48, 0.28), "gnd_bottom": Color(0.06, 0.045, 0.035), "gnd_horizon": Color(0.34, 0.22, 0.13), "ambient_color": Color(0.45, 0.36, 0.30), "ambient_energy": 0.55, "exposure": 0.95, "white": 5.5, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 1.08, "contrast": 1.02, "brightness": 0.96, "fog_color": Color(0.47, 0.39, 0.32), "fog_energy": 0.40, "fog_scatter": 0.18, "fog_density": 0.0005, "fog_aerial": 0.18, "fog_sky_affect": 0.35, "sun_energy": 0.35, "sun_color": Color(1.0, 0.48, 0.22), "sun_pitch": -2.0, "sun_yaw": 97.0, "shadow_dist": 300.0, "lamp_emission": 1.5, "vol_fog_density": 0.00035, "vol_fog_anisotropy": 0.85, "cloud_coverage": 0.26, "cloud_density": 0.50, "cloud_color_top": Color(1.0, 0.51, 0.52), "cloud_color_bottom": Color(0.65, 0.24, 0.27), "cloud_speed": 0.00005})
	# 20.7 civil-twilight (2026-06-26 measured pass): sun ~ -4.5 deg. Real
	# civil dusk keeps a deep-blue dome + a thin amber horizon strip + mauve
	# fading clouds — the previous 20.2->21.0 lerp cut to near-black too fast.
	# Colors from notes/refs/sky_2026_06_11/ (dusk_24-00/29-20); non-color
	# fields lerped 0.625 between the 20.2 and 21.0 keyframes.
	_keyframes.append({"hour": 20.7, "sky_top": Color(0.048, 0.048, 0.076), "sky_horizon": Color(0.486, 0.178, 0.047), "gnd_bottom": Color(0.035, 0.026, 0.019), "gnd_horizon": Color(0.178, 0.120, 0.074), "ambient_color": Color(0.700, 0.541, 0.363), "ambient_energy": 0.244, "exposure": 0.919, "white": 5.81, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 0.718, "contrast": 1.014, "brightness": 0.91, "fog_color": Color(0.291, 0.167, 0.114), "fog_energy": 0.275, "fog_scatter": 0.105, "fog_density": 0.00038, "fog_aerial": 0.161, "fog_sky_affect": 0.381, "sun_energy": 0.163, "sun_color": Color(0.812, 0.667, 0.708), "sun_pitch": -41.4, "sun_yaw": 61.4, "shadow_dist": 268.75, "lamp_emission": 3.69, "vol_fog_density": 0.00044, "vol_fog_anisotropy": 0.538, "cloud_coverage": 0.223, "cloud_density": 0.50, "cloud_color_top": Color(0.379, 0.284, 0.379), "cloud_color_bottom": Color(0.201, 0.140, 0.201), "cloud_speed": 0.00004})
	_keyframes.append({"hour": 21.0, "sky_top": Color(0.011, 0.011, 0.017), "sky_horizon": Color(0.08, 0.05, 0.03), "gnd_bottom": Color(0.02, 0.015, 0.01), "gnd_horizon": Color(0.08, 0.06, 0.04), "ambient_color": Color(0.85, 0.65, 0.40), "ambient_energy": 0.06, "exposure": 0.90, "white": 6.0, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 0.50, "contrast": 1.01, "brightness": 0.88, "fog_color": Color(0.08, 0.06, 0.04), "fog_energy": 0.20, "fog_scatter": 0.06, "fog_density": 0.0003, "fog_aerial": 0.15, "fog_sky_affect": 0.4, "sun_energy": 0.05, "sun_color": Color(0.70, 0.78, 1.00), "sun_pitch": -65.0, "sun_yaw": 40.0, "shadow_dist": 250.0, "lamp_emission": 5.0, "vol_fog_density": 0.0005, "vol_fog_anisotropy": 0.35, "cloud_coverage": 0.20, "cloud_density": 0.50, "cloud_color_top": Color(0.14, 0.12, 0.18), "cloud_color_bottom": Color(0.06, 0.05, 0.08), "cloud_speed": 0.00003})
