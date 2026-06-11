extends Node
## Day/night cycle: 5-keyframe interpolation controlling sky, sun, fog,
## ambient, SSAO, color grading, volumetric fog, cloud coverage.
##
## Self-contained: receives environment objects at init, called with
## current state each frame. Pushes global shader parameters.

# Weather enum must match main.gd
enum Weather { CLEAR, RAIN, THUNDERSTORM, SNOW, FOG }

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

const _KF_HOURS: Array = [5.0, 6.5, 12.0, 19.0, 21.0]


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
const SUN_CAL := 3.0
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


func _apply(time_of_day: float, weather: int, wind_vec: Vector2,
		lightning_flash: float, user_gamma: float, season_t: float) -> void:
	var pair: Array = _find_keyframe_pair(time_of_day)
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
	var sun_mult: float = lerpf(1.0, SUN_CAL, day_f)
	if sun_cal_override > 0.0:
		sun_mult = sun_cal_override
	if vol_sky:
		vol_sky.cloud_coverage = clampf(cc_val, 0.20, 0.50)
		vol_sky.density = clampf(_lerp_kf("cloud_density", a, b, t) * 0.08, 0.02, 0.10)
		# Day-blended sky calibration (constants above).
		var cal_bg: float = lerpf(1.0, SKY_CAL_BG, day_f)
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

	# Volumetric fog (FOG_CAL_*: aerial-perspective calibration above)
	var pitch_val: float = _lerp_kf("sun_pitch", a, b, t)
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
			vol_sky.density = 0.10
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
	if time_of_day >= 4.5 and time_of_day <= 8.5:
		if time_of_day <= 6.0:
			dew = smoothstep(4.5, 6.0, time_of_day)
		else:
			dew = 1.0 - smoothstep(6.0, 8.5, time_of_day)
	if weather != Weather.CLEAR:
		dew = 0.0
	RenderingServer.global_shader_parameter_set("dew_amount", dew)

	# Dawn mist
	if weather == Weather.CLEAR:
		var dawn_mist := 0.0
		if time_of_day >= 4.5 and time_of_day <= 7.5:
			if time_of_day <= 5.5:
				dawn_mist = smoothstep(4.5, 5.5, time_of_day)
			else:
				dawn_mist = 1.0 - smoothstep(5.5, 7.5, time_of_day)
			env.volumetric_fog_density += dawn_mist * 0.002
			env.adjustment_saturation *= (1.0 - dawn_mist * 0.15)

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
	var month_idx: int = int(season_t * 3.0) % 12
	var month_next: int = (month_idx + 1) % 12
	var month_frac: float = fmod(season_t * 3.0, 1.0)
	var data_cover: float = lerpf(monthly_cover[month_idx], monthly_cover[month_next], month_frac)
	if weather == Weather.CLEAR:
		if vol_sky:
			vol_sky.cloud_coverage = maxf(lerpf(vol_sky.cloud_coverage, data_cover, 0.7), 0.25)
		else:
			var cc: float = sky_mat.get_shader_parameter("cloud_coverage")
			sky_mat.set_shader_parameter("cloud_coverage", lerpf(cc, data_cover, 0.7))
			if s_winter > 0.3:
				sky_mat.set_shader_parameter("cloud_type", lerpf(0.0, 1.0, s_winter))

	# Sun / moon directional light (SUN_CAL: ground-light calibration above)
	sun.light_energy    = _lerp_kf("sun_energy", a, b, t) * sun_mult
	sun.light_color     = _lerp_kf("sun_color", a, b, t)
	var pitch: float    = _lerp_kf("sun_pitch", a, b, t)
	var yaw: float      = _lerp_kf("sun_yaw", a, b, t)
	sun.rotation_degrees = Vector3(pitch, yaw, 0.0)
	sun.directional_shadow_max_distance = _lerp_kf("shadow_dist", a, b, t)

	# Lamp emission
	_lamp_emission = _lerp_kf("lamp_emission", a, b, t)
	RenderingServer.global_shader_parameter_set("lamp_glow", clampf(_lamp_emission / 5.0, 0.0, 1.0))

	# Building window night_factor
	var nf: float = 0.0
	if time_of_day >= 18.0 and time_of_day < 21.0:
		nf = (time_of_day - 18.0) / 3.0
	elif time_of_day >= 21.0 or time_of_day < 5.0:
		nf = 1.0
	elif time_of_day >= 5.0 and time_of_day < 7.0:
		nf = 1.0 - (time_of_day - 5.0) / 2.0
	if absf(nf - _last_night_factor) > 0.005:
		_last_night_factor = nf
		for fm in facade_materials:
			if fm is ShaderMaterial:
				fm.set_shader_parameter("night_factor", nf)

	_last_applied_tod = time_of_day


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


func _build_keyframes() -> void:
	_keyframes.append({"hour": 5.0, "sky_top": Color(0.02, 0.02, 0.06), "sky_horizon": Color(0.14, 0.11, 0.20), "gnd_bottom": Color(0.02, 0.02, 0.035), "gnd_horizon": Color(0.10, 0.07, 0.12), "ambient_color": Color(0.16, 0.14, 0.22), "ambient_energy": 0.45, "exposure": 1.05, "white": 6.0, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 0.75, "contrast": 1.02, "brightness": 0.96, "fog_color": Color(0.12, 0.10, 0.14), "fog_energy": 0.20, "fog_scatter": 0.05, "fog_density": 0.0005, "fog_aerial": 0.20, "fog_sky_affect": 0.6, "sun_energy": 0.05, "sun_color": Color(0.65, 0.72, 0.95), "sun_pitch": -10.0, "sun_yaw": -100.0, "shadow_dist": 250.0, "lamp_emission": 5.0, "vol_fog_density": 0.0004, "vol_fog_anisotropy": 0.45, "cloud_coverage": 0.24, "cloud_density": 0.55, "cloud_color_top": Color(0.42, 0.40, 0.44), "cloud_color_bottom": Color(0.16, 0.14, 0.18), "cloud_speed": 0.00003})
	_keyframes.append({"hour": 6.5, "sky_top": Color(0.18, 0.32, 0.62), "sky_horizon": Color(0.75, 0.52, 0.35), "gnd_bottom": Color(0.10, 0.08, 0.06), "gnd_horizon": Color(0.46, 0.34, 0.22), "ambient_color": Color(0.48, 0.38, 0.26), "ambient_energy": 0.75, "exposure": 0.95, "white": 5.5, "ssao_radius": 1.5, "ssao_intensity": 1.5, "ssao_power": 1.5, "saturation": 1.0, "contrast": 1.02, "brightness": 1.0, "fog_color": Color(0.50, 0.42, 0.34), "fog_energy": 0.45, "fog_scatter": 0.18, "fog_density": 0.0005, "fog_aerial": 0.18, "fog_sky_affect": 0.30, "sun_energy": 0.90, "sun_color": Color(1.0, 0.75, 0.50), "sun_pitch": -12.0, "sun_yaw": -95.0, "shadow_dist": 350.0, "lamp_emission": 0.0, "vol_fog_density": 0.0003, "vol_fog_anisotropy": 0.80, "cloud_coverage": 0.25, "cloud_density": 0.50, "cloud_color_top": Color(0.95, 0.85, 0.72), "cloud_color_bottom": Color(0.52, 0.42, 0.32), "cloud_speed": 0.00005})
	_keyframes.append({"hour": 12.0, "sky_top": Color(0.12, 0.28, 0.65), "sky_horizon": Color(0.55, 0.60, 0.68), "gnd_bottom": Color(0.12, 0.12, 0.10), "gnd_horizon": Color(0.38, 0.36, 0.32), "ambient_color": Color(0.50, 0.46, 0.38), "ambient_energy": 0.95, "exposure": 1.0, "white": 6.0, "ssao_radius": 2.0, "ssao_intensity": 1.3, "ssao_power": 1.4, "saturation": 1.0, "contrast": 1.01, "brightness": 1.0, "fog_color": Color(0.62, 0.60, 0.56), "fog_energy": 0.5, "fog_scatter": 0.06, "fog_density": 0.00015, "fog_aerial": 0.12, "fog_sky_affect": 0.30, "sun_energy": 0.95, "sun_color": Color(0.95, 0.92, 0.85), "sun_pitch": -55.0, "sun_yaw": -20.0, "shadow_dist": 400.0, "lamp_emission": 0.0, "vol_fog_density": 0.0001, "vol_fog_anisotropy": 0.45, "cloud_coverage": 0.28, "cloud_density": 0.50, "cloud_color_top": Color(0.95, 0.95, 0.93), "cloud_color_bottom": Color(0.68, 0.68, 0.66), "cloud_speed": 0.00006})
	_keyframes.append({"hour": 19.0, "sky_top": Color(0.18, 0.14, 0.38), "sky_horizon": Color(0.82, 0.50, 0.28), "gnd_bottom": Color(0.10, 0.07, 0.04), "gnd_horizon": Color(0.48, 0.35, 0.20), "ambient_color": Color(0.48, 0.42, 0.32), "ambient_energy": 0.88, "exposure": 0.95, "white": 5.5, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 1.0, "contrast": 1.02, "brightness": 0.98, "fog_color": Color(0.55, 0.45, 0.35), "fog_energy": 0.45, "fog_scatter": 0.18, "fog_density": 0.0005, "fog_aerial": 0.18, "fog_sky_affect": 0.30, "sun_energy": 0.95, "sun_color": Color(1.0, 0.72, 0.45), "sun_pitch": -12.0, "sun_yaw": 95.0, "shadow_dist": 350.0, "lamp_emission": 0.0, "vol_fog_density": 0.0003, "vol_fog_anisotropy": 0.80, "cloud_coverage": 0.28, "cloud_density": 0.50, "cloud_color_top": Color(0.85, 0.55, 0.38), "cloud_color_bottom": Color(0.55, 0.30, 0.18), "cloud_speed": 0.00005})
	_keyframes.append({"hour": 21.0, "sky_top": Color(0.015, 0.01, 0.01), "sky_horizon": Color(0.08, 0.05, 0.03), "gnd_bottom": Color(0.02, 0.015, 0.01), "gnd_horizon": Color(0.08, 0.06, 0.04), "ambient_color": Color(0.85, 0.65, 0.40), "ambient_energy": 0.06, "exposure": 0.90, "white": 6.0, "ssao_radius": 2.0, "ssao_intensity": 1.4, "ssao_power": 1.5, "saturation": 0.50, "contrast": 1.01, "brightness": 0.88, "fog_color": Color(0.08, 0.06, 0.04), "fog_energy": 0.20, "fog_scatter": 0.06, "fog_density": 0.0003, "fog_aerial": 0.15, "fog_sky_affect": 0.4, "sun_energy": 0.05, "sun_color": Color(0.70, 0.78, 1.00), "sun_pitch": -65.0, "sun_yaw": 40.0, "shadow_dist": 250.0, "lamp_emission": 5.0, "vol_fog_density": 0.0005, "vol_fog_anisotropy": 0.35, "cloud_coverage": 0.20, "cloud_density": 0.50, "cloud_color_top": Color(0.14, 0.12, 0.18), "cloud_color_bottom": Color(0.06, 0.05, 0.08), "cloud_speed": 0.00003})
