# Sky — cloud taxonomy, lighting depth, and optical effects

Spec written 2026-06-11 (Fable 5) from the user's walk-around verdict:
*"we need all the different types of clouds … stratus, cumulonimbus,
mammatus, sundogs … the clouds lack detail and depth … different parts
should reflect or pass light differently … static even at max wind …
with only cumulus we never get the dramatic expanses of varying color."*

Companion records: `rendering.md` §6b (sky calibration) and §6d (cloud
shape/flow/twilight). References: `notes/refs/sky_2026_06_11/`.

## 0. Charter

The sky is a primary emotional surface of the walk and must be
**data-first like everything else**: cloud types follow NYC weather
climatology (NOAA monthly coverage already drives the global scale), the
state machine's weather modes each get a *meteorologically correct* sky,
and rare/dramatic formations appear at realistic frequencies — a
mackerel-sky morning or a winter sundog should be something you *catch*,
not a slider.

## 1. Current state (after 2026-06-11)

- One volumetric layer (1.5–4 km shell) marching a Schneider density
  field; weather map (`gen_weather_map.py`) = fair-weather cumulus cells
  with per-column tower heights (G), type (R), coverage (B).
- The Schneider `densityHeightGradient` ALREADY blends three profiles
  (stratus / stratocumulus / cumulus) from the R channel — we only ever
  feed it R ≈ 0.45–1.0. Stratus support is latent, unused.
- Weather presets (RAIN/FOG/SNOW/THUNDERSTORM) merely raise
  coverage/density of the SAME cumulus cell field — overcast currently
  renders as "more/denser cumulus", which is wrong.
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

## 5. Phasing (post-Fable sessions can execute 2.1→2.4 mechanically)

- **P1**: map set + crossfade switching + weather-state table (2.1, 2.6).
  Biggest payoff: overcast stops being "dense cumulus"; dramatic skies.
- **P2**: high ice layer + twilight interplay (2.2). Unlocks the pink
  cloud-ceiling reference look.
- **P3**: cumulonimbus anvil + mammatus (2.3).
- **P4**: halos/sundogs/pillars (2.4).
- **P5**: altocumulus cellular layer; rarities (lenticular over the
  reservoir on strong-wind autumn days).
