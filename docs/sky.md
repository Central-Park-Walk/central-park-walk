# Sky — cloud taxonomy, lighting depth, and optical effects

Spec written 2026-06-11 (Fable 5) from the user's walk-around verdict:
*"we need all the different types of clouds … stratus, cumulonimbus,
mammatus, sundogs … the clouds lack detail and depth … different parts
should reflect or pass light differently … static even at max wind …
with only cumulus we never get the dramatic expanses of varying color."*

Companion records: `rendering.md` §6b (sky calibration) and §6d (cloud
shape/flow/twilight). References: `notes/refs/sky_2026_06_11/`.

**2026-07-01: full sky/sun/moon/cloud audit in §6 — measured symptoms,
root causes, and the redesign plan of record. Read §6 before sky work.**

## 0. Charter

The sky is a primary emotional surface of the walk and must be
**data-first like everything else**: cloud types follow NYC weather
climatology (NOAA monthly coverage already drives the global scale), the
state machine's weather modes each get a *meteorologically correct* sky,
and rare/dramatic formations appear at realistic frequencies — a
mackerel-sky morning or a winter sundog should be something you *catch*,
not a slider.

## 1. Current state (after 2026-06-12: P1 + §2.5 + P2 SHIPPED)

- **P2 is live** (high ice layer): `clouds.gdshader` now renders a flat
  ice deck (cirrus/cirrostratus/altocumulus) the view ray pierces at ~8 km
  scale, composited onto the atmosphere UNDER the volumetric shell. Three
  types gated by per-weather opacity — cirrus fibrous streaks (anisotropic
  ridged fBm), cirrostratus milky veil (smooth fBm), altocumulus mackerel
  cells (Worley with per-cell underside shading). Advected by the upper
  wind (`high_cloud_offset`, integrated per-frame in `cloud_sky.gd` at
  ×2.5 the deck wind). **Twilight interplay:** the deck's sun is lifted
  ~+4° (horizon dip at altitude), lit colour = transmittance LUT (reddens
  when low) over the sky-LUT ambient → ice stays sunlit past ground sunset
  (salmon-pink-on-periwinkle). Opacity set in `day_night_cycle.gd` per
  §2.6: CLEAR deterministic-per-day wisps (icier in winter), dramatic-dusk
  mackerel hero, snow cirrostratus, storm anvil cirrus. CLI
  `--high-clouds=cir:cs:ac`. Early-outs when all amounts are 0 → the
  clear-noon perf gate is unchanged by construction; worst case (all three
  forced 0.8 over the open dome) measured ~1–2 ms GPU at Great Lawn.


- One volumetric layer (1.5–4 km shell) marching a Schneider density
  field. **P1 is live**: five per-weather-state maps
  (`gen_weather_map.py --type`, §2.1 table) crossfade at runtime —
  `clouds.glsl` binds current+target maps (set 1 binding 2/3) and lerps
  by `weather_mix` (pad3 push-constant float); `cloud_sky.gd
  set_weather_map()` fades over 30 s (bots `snap_weather_fade()`).
  Weather→map table + the dramatic-sky schedule (deterministic per
  game-day hash, ~18% of dawn/dusk windows) live in `day_night_cycle.gd`.
  CLI: `--cloud-map=name`, `--sky-dramatic=0|1`.
- The height-gradient profiles were RESCALED for the tower-rescaled hf
  (weather.g owns thickness; profiles only shape base/top edges — the
  Schneider stratus original would squeeze an overcast deck to ~60 m).
- **§2.5 is live**: `almanac.gd` computes true NYC solar/lunar
  positions + moon phase (validated headless by
  `scripts/test_almanac.gd`, 23 checks vs published values). The
  keyframes are indexed by a CANONICAL hour — piecewise-linear remap
  anchored to each date's real sunrise/solar-noon/sunset
  (`_canonical_hour`), so keyframe mood + every hour window (twilight,
  dew, dawn mist, lamps, building windows) track the seasons. The
  shadow light follows the almanac sun (2° elevation floor); at night
  it becomes the real moon, energy scaled by phase (full = the
  accepted night look; moonless floor 0.06×). The celestial sun is the
  TRUE sun (crosses the horizon at real event times), handing over to
  the moon below −6°. The moon renders as a phase-shaded sphere lit by
  the true sun direction (geometric terminator + earthshine), through
  atmospheric transmittance + in-scatter (pale day moon for free).
  Perceptual disk sizing: both bodies swell ~1.6× near the horizon,
  shrink toward zenith, refraction-squash within ~2°. The old night
  "always-full moon" was the SUN DISK drawn at the night light's
  position — gone (disk follows `true_sun_dir`).
- SUN_CAL trimmed 3.0→2.6: the real June noon sun (73° vs keyframed
  55°) lifted lawn NdotL ~17%; turf re-centered in the 126–149 band.
- Lighting: multi-scatter octave approximation (3 octaves, per-octave
  phase), front-lit-gated powder, within-cloud ambient gradient with
  interior occlusion (shipped 2026-06-11).
- Flow: one world-space wind offset; `wind_speed` is true m/s at cloud
  altitude (main.gd maps surface wind 4→24 m/s; winds aloft never zero).
- Twilight: celestial sun crosses the horizon; cloud undersides sample
  the sun LUT lifted +2°.

## 2. Architecture for the taxonomy

### 2.1 Layer 1 — volumetric low/mid deck (exists; extend)

Per-weather-state **weather maps**, generated offline by
`gen_weather_map.py --type=<name>` and all loaded at init:

| map | R (type) | G (tower) | B (coverage) | reads as |
|---|---|---|---|---|
| `fair_cumulus` (current) | 0.45–1.0 | 0.15–0.5 domes | discrete cells, 58% zeros | humilis/mediocris field |
| `stratocumulus_sheet` | ~0.4 | ~0.3 uniform ± ripple | 0.7–0.9 with hole noise | lumpy grey sheet, blue gaps |
| `stratus_overcast` | ~0.05 | ~0.25 flat | 0.9–1.0 | featureless veil (RAIN/drizzle) |
| `storm_congestus` | 1.0 | 0.6–1.0, big cells | large merged cells | cumulonimbus bases (THUNDERSTORM) |
| `broken_dramatic` | 0.3–0.7 mixed | 0.3–0.6 | big torn sheets + gaps | the dusk "dramatic expanses" sky |

Runtime selection: weather state machine picks target map; **crossfade**
by binding current+target maps and a `weather_mix` scalar (the push
constant has 2 spare floats in `pad3`) — `weather_at()` lerps the two
samples. Transition over minutes of game time, so fronts *arrive* rather
than pop. (Uniform-set per map pair, or a 2-texture set + mix.)

### 2.2 Layer 2 — high ice layer (new, cheap, huge twilight payoff)

Cirrus / cirrostratus / altocumulus live at 6–12 km — far above the
volumetric shell — and are optically thin. Implement as **2D scrolling
layers in `clouds.gdshader`** (the dead legacy `shaders/cloud_sky.gdshader`
had a primitive version — resurrect properly):

- Cirrus streaks + cirrostratus veil: textures or procedural fBm ridges,
  advected by a separate (faster) upper wind; opacity per weather state.
- **Twilight interplay is the point**: ice clouds catch the sun BEFORE
  dawn and AFTER dusk (they're lit while low clouds are in shadow) — the
  pink-ceiling reference frames (dusk walking tour) are mostly
  altocumulus/cirrus. Tint from the celestial sun via the same
  golden/blaze machinery, sampling the sky LUT at the layer's lifted
  horizon (+~4° at 8 km).
- Altocumulus "herd of pigs" / mackerel sky: cellular (worley) 2D layer
  with per-cell pseudo-shading (normal from the cell field), occasional
  by weather schedule.

### 2.3 Cumulonimbus + mammatus (THUNDERSTORM)

- `storm_congestus` map gives the towers; raise the shell top
  (`sky_t_radius`) for storm states so G=1.0 reaches ~8 km visually.
- **Anvil**: in `density()`, when R ≈ 1 and G > ~0.8, widen effective
  coverage as hf → 1 (horizontal shelf spread) — a one-term gradient.
- **Mammatus**: pouches hang BELOW the base under the anvil shelf —
  allow density at hf slightly < 0 there, modulated by inverted low-freq
  worley (pouch field), only where the storm map flags it. Lit by the
  ambient-ground term → the eerie underlit look comes free at dusk.

### 2.4 Optical effects (winter / ice)

- **22° halo + sundogs (parhelia)**: additive screen-space ring/spots in
  `clouds.gdshader` at ±22° from the celestial sun, gated on: cirrus
  layer opacity > threshold, winter season (ice crystals), sun elevation
  < ~30°, and CLEAR/partly states. Brightness from the transmittance LUT.
- **Sun pillar**: vertical smear above a rising/setting sun under the
  same gating, dawn/dusk windows.
- These are cheap, high-delight, and seasonal — exactly the "unusual
  weather event formations" asked for.

### 2.5 Celestial bodies (user walk-around 2026-06-11)

User: *"the sun and moon don't change apparent size horizon→overhead;
the moon is always full; the sun should move through the seasons."*

- **Astronomical almanac module**: compute true solar position
  (elevation/azimuth) for the park's lat/lon from date + time — NYC noon
  sun is ~26° in December vs ~73° in June; sunrise/sunset times and
  azimuths swing accordingly. This REPLACES the fixed keyframed
  pitch/yaw path (keyframes keep owning color/energy/mood, re-keyed to
  solar elevation rather than wall-clock hour). The celestial-sun
  decoupling (rendering.md §6d) is the natural seam: the almanac feeds
  the same `celestial` direction. Moon: real lunar ephemeris (position
  AND phase — synodic 29.53 d), so the moon rises/sets correctly and is
  only sometimes full.
- **Moon phases**: shade the disk by sun–moon geometry (terminator from
  the phase angle), not a texture swap; earthshine on the dark limb at
  crescent. Moonlight energy scales with phase (full ≈ 0.25 lux, new ≈ 0).
- **Apparent size**: physically the angular diameter is constant — the
  horizon-moon effect is PERCEPTUAL (plus refraction flattening). We
  render the *perception*: scale the disk up smoothly near the horizon
  (~1.5–2× below 10° elevation, classic art direction), shrink + brighten
  toward zenith (`sun_disk_scale` already exists as the knob; drive it
  from elevation). Add refraction flattening (vertical squash) within 2°
  of the horizon for the fat setting sun.

### 2.6 Weather-state mapping (data-driven)

| state | layer 1 map | layer 2 | extras |
|---|---|---|---|
| CLEAR | fair_cumulus @ NOAA coverage | cirrus wisps (occasional) | sundogs possible (winter) |
| CLEAR→dramatic schedule | broken_dramatic (a few evenings/mornings per game-month) | cirrostratus sheet | the vibrant-dusk showcase |
| RAIN | stratus_overcast | none (hidden) | drizzle veil via fog |
| THUNDERSTORM | storm_congestus | anvil cirrus shelf | mammatus, lightning |
| SNOW | stratocumulus_sheet (low) | cirrostratus | halo/sundogs before fronts |
| FOG | stratus at deck height | none | existing fog volumes |

## 3. Lighting depth — remaining work

Shipped: multi-scatter octaves, gated powder, in-cloud ambient gradient
+ interior occlusion. Remaining levers, in order:
1. Calibrate `SKY_CAL_SUN` against the octave sum (sweep at noon —
   target cumulus faces p50 ≈ 190–210 sRGB, shaded bases intact).
2. Height-dependent scattering tint: ice-glaciated tops slightly
   blue-white, warm liquid bases — small per-sample tint by hf.
3. Ambient sky-occlusion: cheap vertical-beam approximation (density
   above the sample point attenuates the sky ambient).

## 4. Perf budget + DoD

- The march cost scales with coverage: overcast (B≈1 everywhere) is the
  worst case — measure `stratus_overcast` at the gate locations BEFORE
  shipping map switching; budget: clouds remain within the §6d floor
  measurements (cloud compute was measured innocent at the frame floor).
- Per-type DoD: side-by-side vs a cloud-atlas reference photo of the
  type (capture poses in `scripts/sky_captures.sh`), plus one full
  day-cycle sweep confirming twilight interplay.
- Flow DoD: `scripts/cloud_flow_check.sh` — visible coherent drift at
  default wind within 30 s; shape identity preserved.

## 5. Phasing (post-Fable sessions can execute 2.2→2.4 mechanically)

- **P1: DONE 2026-06-12** (see §1). Per-type DoD passed by capture:
  stratus = featureless veil, stratocu = lumpy sheet with blue gaps,
  storm = dark mass + congestus towers (density 0.14), dramatic dusk =
  torn salmon sheets. Worst-case march (full-coverage stratus) measured
  85 fps at Great Lawn — no perf impact.
- **§2.5: DONE 2026-06-12** (see §1). Almanac + canonical-hour remap +
  moon phases + perceptual disk sizing.
- **P2: DONE 2026-06-12** (see §1). High ice layer shipped:
  cirrus/cirrostratus/altocumulus flat sheet, twilight-lit, per-weather
  opacity. Altocumulus reworked to organic mackerel rows (domain-warped
  Worley + cloud-street ripple) after the uniform-dot-grid v1 read busy.
  Also shipped this session: the in-game **cloud control panel** (C —
  `cloud_debug.gd`) and a fix for a stale high-cloud latch (apply()
  throttles when the clock is paused → T/N now force_apply).
- **P3**: cumulonimbus anvil + mammatus (2.3).
- **P4**: halos/sundogs/pillars (2.4).
- **P5**: altocumulus cellular layer; rarities (lenticular over the
  reservoir on strong-wind autumn days).

### Capture protocol (learned 2026-07-01, the hard way)
- **`.glsl` edits need a reimport before game-run captures**: compute
  shaders go through the import cache (`.godot/imported/*.res`), and
  `godot --path .` game runs do NOT reimport — three successive
  calibration edits ran with a stale 16:01 SPIR-V. Run
  `Godot --headless --path . --import` after ANY clouds.glsl change.
  (`.gd`/`.gdshader` load from source — no reimport needed.)
- **Sky state needs convergence repeats**: the sky texture rebuilds over
  64 frames ×3-texture blend and the LUT cycles 3 textures per swap, so
  after a time jump the first ~2-4 shots at 3 s settle are contaminated
  by the previous state. Repeat each pose 5-7x in the --shots spec and
  read the tail (adjacent-identical = converged).
- **Serialize with other Godot sessions**: concurrent runs (other Claude
  sessions use this repo too) starve the GPU and freeze convergence —
  check `pgrep -x Xvfb` before capturing.

## 6. 2026-07-01 audit — measured symptoms, root causes, redesign plan

Chris's walk-around verdict (2026-07-01): *"odd light, then dark, then
light again sunrise/sunset effects … cumulus tend to be bun-like … cirrus
look like a sky full of contrails … oversized sun and moon, huge in the
lower quarter of the sky … a faint bright spot in the night sky that is
not the moon … difficult to ever see the moon … realistic clouds for all
weathers/hours/seasons, dramatic night skies, breath-taking dawns and
dusks, sparing of the 3060 Ti."*

Evidence: 23-shot headless sweep, `tmp/skysweep/` (Great Lawn, seed 7,
default season_t=1.5 = Jul 15). Sky-region mean luma (0-255):

| wall hour | 19.5 | 20.0 | 20.5 | 20.75 | 21.0 | 21.25 | 21.5 | 22.0 | 23.0 |
|---|---|---|---|---|---|---|---|---|---|
| luma | 187 | 185 | 187 | 168 | 114 | 46 | **3.5** | **3.3** | **40** |

Sky is PITCH BLACK at 21:30 (sun −9°, real NYC nautical twilight still
glows) then RE-BRIGHTENS to 40 by 23:00 with warm cream sunlit-looking
clouds at 1 AM. Dawn mirrors it: night steady-state ~70 → 152 at 05:12
(pre-sunrise) → 113 at 05:48 → 106 at 06:12 (brighter *before* sunrise
than after). Light→dark→light confirmed at both ends.

### 6.1 Root causes (each verified in code + capture)

1. **The night LUT sun is a lie, and the handover double-dips.**
   `day_night_cycle.gd` slerps `cel_dir` from the real sun to
   `light_dir3` over sun elev −6°→−10° (`night_celest`). `light_dir3` at
   night is the moon — or, when the moon is down/new, a FIXED "skyglow"
   direction (elev 65°, az 220). The Hillaire LUT has no energy input —
   it renders a full daylight atmosphere for whatever direction it's
   given. Sequence at dusk: real-sun LUT darkens to near-black at −6..−10°
   (deepened by cal_bg 5→1 over canon 20.55–21.0), THEN the slerp hoists
   the LUT sun to +65° and the sky re-brightens into a dim blue day.
   Consequences: the black trough, the re-brightening, **the faint
   bright spot** (the LUT's forward-scatter lobe around az 220 / elev 65
   — present every night at the default date), and golden-lit cream
   clouds at 1 AM (the march's `atmosphere_sun`/ambient sample this fake
   daylight LUT — `clouds.glsl` does NOT divide the LUT by 50).
2. **Default date has a new moon.** season_t=1.5 → Jul 15 2026: moon
   illum 0.01–0.04, below horizon ALL night (elev −22..−28 at 0–5 h),
   only up in daytime. So at defaults the moon is *never* visible at
   night, and the one sighting is the thin crescent near the setting sun
   (elev 7–18° at 20–21 h) — exactly Chris's report. Almanac is CORRECT;
   the presentation (invisible-by-default moon + fake skyglow) is wrong.
3. **No stars anywhere in the live path.** `cloud_sky/clouds.gdshader`
   has no starfield/light-pollution terms (those exist only in the dead
   fallback `shaders/cloud_sky.gdshader`). Night sky = LUT + moon only.
4. **Bun cumulus**: `gen_weather_map.py` cell_field makes near-circular
   discs; tower-rescaled density gives each a smooth dome → uniform
   rounded buns, no flat shaded bases, no wind shear, no size anarchy.
   Confirmed in shot_03/shot_20 captures.
5. **Cirrus = contrails**: `high_clouds()` cirrus is anisotropic fBm
   ridges ALL stretched along one axis (`q=(0.22x, 1.7y)`), thresholded
   thin → a field of parallel straight streaks. Real cirrus: hooked
   uncinus filaments, orientation variance, patchy density.
6. **Clouds vanish at the horizon**: `clouds.gdshader` line ~369 blends
   to clean background below EYEDIR.y≈0.4 (+ the glsl 0–0.05 fade). Real
   skies stack/compress cloud at the skyline; ours dissolve — part of the
   "not realistic" read.
7. **Disk sizes too timid for the art direction**: sun 2.5×→3.75× at
   horizon, moon 1.8×→2.88×; swell starts only below 10° elevation.
   Chris wants "pretty huge" through the lower QUARTER (≲25°).
8. **Edge pixelation**: 768² octahedral sky texture shows hard stair-step
   cloud edges at 1080p (shot_19/20).

### 6.2 Redesign plan (priority order)

- **P0 — honest night sky: SHIPPED 2026-07-01 (a0d9314)**, verified by
  converged sweeps (tmp/skysweep2/4, skynight): dusk monotonic
  187→97→19→4.5, dawn mirror, noon unchanged, stars + LP dome live,
  1AM clouds amber above the dome. Design as specified:
  celestial/LUT sun = the REAL sun always (LUT owns dawn→dusk and goes
  properly dark; kill the `night_celest` slerp and the fake skyglow dir).
  Night background = additive on the dark LUT in `clouds.gdshader`:
  NYC light-pollution amber dome (port from the dead fallback shader,
  data-true Bortle 8-9 but art-directable), star field gated by sun elev
  (art-directed brighter than strict Bortle — "dramatic night skies"),
  moon disk unchanged (already correct). Cloud march at night: keep the
  moon as the LIGHT direction when up (phase-scaled energy), but its
  sun/ambient terms must come from a night-scaled source, not the raw
  daylight LUT — plus a city-glow amber underside term (real NYC
  overcast nights glow amber from below; dramatic AND true). Twilight
  cal windows (`twilight_f`, cal_bg blend) re-derived after this — the
  LUT then darkens monotonically and the keyframes only shape mood.
- **P1 — celestial presentation: SHIPPED 2026-07-01 (a0d9314)** — swell
  from 25°, sun ~5x / moon ~4.6x at horizon; vnoise maria + night halo;
  full-moon verify (season 1.97 = Aug 27, moonrise 20:30 ESE) renders
  moon+halo+stars+moonlit clouds (tmp/skymoon). Sun disk confirmed
  rendering from a 120 m camera (at ground level the CPW towers really do
  occlude the low sun from Great Lawn). Moon albedo TEXTURE + brightness
  polish + a moonlit-sky floor (full-moon nights wash the sky a little)
  remain open art-direction knobs for a GPU walk. Original spec:
  swell curves start at ~25° elevation, reach ~4.5–5× at the horizon for
  BOTH bodies (keep refraction squash); verify the setting sun disk is
  actually visible/huge at the skyline by capture. Moon: brightness up
  at night, real albedo texture for maria (sin-mottling won't survive
  5×), subtle halo. Consider defaulting season_t off the new-moon date
  or simply accept per-date phases (data-first) — but the moon must be
  *seeable* when up: verify a full-moon date end-to-end.
- **P2 — cumulus de-bunning**: weather-map cells get wind elongation,
  cluster merging, wide size distribution (gen_weather_map.py); glsl
  gets stronger top erosion/curl tearing, flatter bases with darker
  shading, slight base-noise anisotropy along wind. Iterate by capture
  against cloud-atlas refs (humilis/mediocris). Then measure 1024²
  texture cost on the 3060 Ti (amortized over 64 frames) for the edge
  pixelation; only ship if the perf gate passes.
- **P3 — cirrus rework**: orientation-varying, domain-warped hooked
  filaments (uncinus) + patchy density; kill the parallel-streak field.
  Same flat-sheet machinery, still ~free.
- **P4 — horizon cloud band**: soften/remove the y<0.4 background blend
  (banding it masked is now handled by adaptive step count + IGN dither
  — re-verify), so decks stack at the skyline.
- **P5 — dawn/dusk drama pass** (after P0 changes the substrate):
  re-tune blaze/golden + keyframe colors against `notes/refs/
  sky_2026_06_11/`; port earth-shadow + Belt of Venus terms from the
  dead fallback shader (cheap analytic, east-sky payoff); verify the
  canonical windows at both solstices by sweep.
- **P6 — perf gate + seasonal breadth**: worst-case sweeps (overcast map,
  full high-cloud, night with stars) at the gate locations; keep 64-frame
  amortization; then per-season/per-weather capture matrix.

Non-goals: don't replace the Hillaire LUT / Schneider march (standard,
calibrated — see feedback-standard-over-novel-graphics); no new
render passes; everything rides existing shaders/textures.
