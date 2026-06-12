extends Node
## Noise-driven wind simulation with gusts and lulls.
##
## Self-contained: call update() each frame with time-of-day and weather.
## Reads nothing from parent — all state is local.
## Pushes wind_vec to global shader uniform automatically.

# Weather enum must match main.gd
enum Weather { CLEAR, RAIN, THUNDERSTORM, SNOW, FOG }

# Public state — read by main.gd and builders
var wind_vec := Vector2.ZERO
var wind_override := -1.0  # <0 = auto, >=0 = manual strength multiplier
var dir_override := NAN    # radians; NAN = auto (noise-driven wander)

# Internal state
var _wind_time := 0.0
var _gust_envelope := 0.0
var _dir_noise: FastNoiseLite
var _base_noise: FastNoiseLite
var _swell_noise: FastNoiseLite
var _gust_noise: FastNoiseLite


func _ready() -> void:
	_init_noise()


func _init_noise() -> void:
	_dir_noise = FastNoiseLite.new()
	_dir_noise.seed = randi()
	_dir_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_dir_noise.frequency = 0.003        # ~5 min direction drift cycle
	_dir_noise.fractal_octaves = 2

	_base_noise = FastNoiseLite.new()
	_base_noise.seed = randi()
	_base_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_base_noise.frequency = 0.006       # ~3 min breeze modulation
	_base_noise.fractal_octaves = 3

	_swell_noise = FastNoiseLite.new()
	_swell_noise.seed = randi()
	_swell_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_swell_noise.frequency = 0.02       # ~50s swells

	_gust_noise = FastNoiseLite.new()
	_gust_noise.seed = randi()
	_gust_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_gust_noise.frequency = 0.04        # ~25s gust opportunities
	_gust_noise.fractal_octaves = 3


func update(delta: float, time_of_day: float, weather: int) -> void:
	_wind_time += delta
	var t := _wind_time

	# Time-of-day strength: calm 17-22h so fireflies aren't blown away
	var tod_mult := 1.0
	if time_of_day >= 17.0 and time_of_day < 18.0:
		tod_mult = lerpf(1.0, 0.12, (time_of_day - 17.0))
	elif time_of_day >= 18.0 and time_of_day < 21.0:
		tod_mult = 0.12
	elif time_of_day >= 21.0 and time_of_day < 22.0:
		tod_mult = lerpf(0.12, 1.0, (time_of_day - 21.0))

	# Weather multiplier
	var wx := 1.0
	if weather == Weather.RAIN:
		wx = 1.8
	elif weather == Weather.THUNDERSTORM:
		wx = 2.8
	elif weather == Weather.SNOW:
		wx = 0.5
	elif weather == Weather.FOG:
		wx = 0.3

	# Direction: noise-driven wander
	var dir_primary := _dir_noise.get_noise_1d(t) * PI
	var dir_wobble := _dir_noise.get_noise_1d(t * 3.0 + 500.0) * 0.4
	var dir_angle := dir_primary + dir_wobble
	if not is_nan(dir_override):
		dir_angle = dir_override
	var wind_dir := Vector2(cos(dir_angle), sin(dir_angle))

	# Base breeze: noise-driven, range ~0.03-0.20
	var base_n := _base_noise.get_noise_1d(t)
	var breeze := remap(base_n, -1.0, 1.0, 0.03, 0.20)

	# Medium swells: ~25-50s variation
	var swell_n := _swell_noise.get_noise_1d(t)
	var medium := maxf(swell_n, 0.0) * 0.25

	# Gust events: two noise channels must align
	var gust_a := _gust_noise.get_noise_1d(t)
	var gust_b := _gust_noise.get_noise_1d(t * 1.7 + 1000.0)
	var gust_raw := maxf(gust_a, 0.0) * maxf(gust_b, 0.0)
	var gust_trigger := smoothstep(0.05, 0.25, gust_raw) * 0.40

	# Asymmetric envelope: fast rise (~0.3s), slow decay (~2.5s)
	if gust_trigger > _gust_envelope:
		_gust_envelope = lerpf(_gust_envelope, gust_trigger, minf(delta * 3.3, 1.0))
	else:
		_gust_envelope = lerpf(_gust_envelope, gust_trigger, minf(delta * 0.4, 1.0))

	# Gust cross-wind: slight lateral deviation
	var gust_cross := _dir_noise.get_noise_1d(t * 2.0 + 200.0) * 0.25
	var gust_dir := Vector2(
		wind_dir.x - wind_dir.y * gust_cross,
		wind_dir.y + wind_dir.x * gust_cross
	).normalized()

	# Combine
	var base_wind := wind_dir * (breeze + medium)
	var gust_wind := gust_dir * _gust_envelope
	wind_vec = (base_wind + gust_wind) * tod_mult * wx

	# Manual override
	if wind_override >= 0.0:
		wind_vec = wind_dir * wind_override * 0.55

	# Push to global shader uniform
	RenderingServer.global_shader_parameter_set("wind_vec", wind_vec)
