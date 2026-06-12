# Undergrowth & Non-Tree Plant Model Redesign — implementation spec

Written 2026-06-12 (Fable 5 planning session). This is the plan a cheaper model
(Opus 4.8 / Sonnet 4.6) executes. It is the non-tree companion to
[`tree_model_redesign.md`](tree_model_redesign.md): same reference-first discipline,
same "lift to very realistic" goal, applied to **every plant that is not a tree** —
shrubs, ferns, herbaceous forbs, grasses, sedges, wetland specialists, vines, and the
ground-cover floor layer.

Read [`vegetation_modeling.md`](vegetation_modeling.md), [`workflow.md`](workflow.md),
and [`grass.md`](grass.md) first. **The method doc is load-bearing** — it defines the
reference-first discipline (habit / interaction / behavior), diagnoses *why* the
current models fail (wrong habit, no interaction, no ecological coherence), and names
the canonical failure this whole effort exists to fix: the spicebush that makes a **V**
instead of *flowing over itself*. This doc is the non-tree application of that method.
Every change is bound by the `workflow.md` Definition of Done and the `DESIGN.md`
quality bar (1080p, **60 fps open / 45 fps woodland** on an RTX 3060 Ti, faithful to
data, validated against reference not feeling).

---

## 0. The situation, stated plainly — this is a re-enablement, not just a remodel

**Today the park's understory is spicebush and nothing else.** Read
`undergrowth_builder.gd` `ZONE_SPECIES` / `WOODLAND_SPECIES` (ln 156–181): every zone
that gets any undergrowth places **only index 0, `Shrub_Spicebush`**. The other 34
species in the `SPECIES` array (ln 56–143) are *loaded into memory but never placed.*
They were retired from placement on 2026-05-08 with this note in the file:

> "All remaining helper-based procedurals retired … only Spicebush meets the bespoke
> quality bar. Data gap over fake — see Task 14 bespoke queue."

That decision was correct under [[feedback-project-soul]] (a bare-but-honest park beats
a park dressed in `make_crossed_planes` stick-cards). But it means the deliverable here
is **two coupled jobs per species, not one:**

1. **Lift the model to the spicebush quality bar** (reference-first habit → density →
   behavior → variants), and
2. **Re-wire it back into placement** — add it to `ZONE_SPECIES` / `WOODLAND_SPECIES`
   with a real, data-calibrated density, and (for wetland/meadow) populate the zones
   that are currently empty arrays (`7: []` Waterside, `8: []` Wild Meadow).

A species is not "done" when its thumbnail looks good. It is done when it is **placed,
visible in its real zone in-game at a calibrated density, validated on a stand, and
perf-gated.** Until step 2, the work is invisible to the player — the most common way
this program can quietly fail is to remodel 34 GLBs and never re-enable them.

### The four pipelines this spec governs

| Pipeline | Generator | Runtime builder | Placement driver | Notes |
|---|---|---|---|---|
| **Undergrowth** (shrubs, ferns, herbs, grasses, wetland) — 35 species | `scripts/make_undergrowth.py` (one `make_<species>()` per plant) | `undergrowth_builder.gd` | `ZONE_SPECIES` + `WOODLAND_SPECIES` by atlas zone | The bulk of the work. No impostors; chunk-MultiMesh + distance fade. |
| **Vines** — 7 species | `scripts/make_vine.py` | `vine_builder.gd` | tree-attached, bark affinity | **Disabled** (`vine_builder.gd:111`) — all 7 are stick-card primitives. Full redesign required before re-enable. |
| **Ground cover** — 10 floor models | `scripts/make_ground_cover.py` (turf tiles) + the `GroundCover_*.glb` set | `ground_cover_builder.gd` | chunk, woodland zones | Litter / moss / twigs / seedlings — floor *ephemera*, lighter treatment (§8). **Verify GLB provenance** (§8). |
| **Turf / lawn blades** | `scripts/make_ground_cover.py` `build_turf_tile` | grass particle system | — | **Out of scope here** — owned by [`grass.md`](grass.md). Do not touch turf in this program except where a meadow grass (little bluestem, switchgrass) is a *placed undergrowth instance*, which is this spec's job. |

The **35-species undergrowth roster** (`SPECIES` array, with the generator function and
the index the runtime uses):

- **Shrubs (0–6):** spicebush*, witch_hazel, viburnum, sumac, elderberry,
  sweet_pepperbush, flowering_raspberry
- **Ferns (7–10):** ostrich, christmas (evergreen), cinnamon, sensitive
- **Herbs (11–23, 34):** pokeweed, japanese_knotweed, joe_pye_weed, coneflower,
  cardinal_flower, white_wood_aster, jewelweed, mugwort, white_snakeroot, ironweed,
  rose_mallow, burdock, goldenrod (Flower_Goldenrod, idx 23), black_eyed_susan (idx 34)
- **Grasses / sedges (24, 30–33):** bottlebrush, little_bluestem, switchgrass,
  tussock_sedge, pa_sedge
- **Wetland (25–28):** cattail, yellow_iris, lizards_tail, phragmites
- **Accent flower (29):** aster (Symphyotrichum)

(* spicebush already has a `BRIEF.md` and is the worked hero — §5.)

---

## 1. The pipelines as they exist (don't reinvent these)

### 1a. Undergrowth generation chain

| Stage | File | Produces |
|---|---|---|
| Geometry | `scripts/make_undergrowth.py` — `make_<species>()`, Blender `bmesh` | `models/vegetation/<Name>.glb` (and `_0.._N-1` for variant species) |
| Shared geometry helpers | same file: `make_tube`, `make_leaf_card`, `make_crossed_planes`, `make_frond`, `make_pinnate_frond`, `_make_shrub`, `_scatter_cluster_cards`, `_make_branch` | the building blocks every species composes |
| Leaf-card geometry/material (shared with trees) | `scripts/leaf_card_utils.py` — `make_leaf_cards`, `create_leaf_material`, **`compound_mode`** (pinnate fronds with see-through gaps), **`create_strand_cards_at_positions`** (hung weeping/drooping cards — the willow curtain) | reusable card placement |
| Leaf textures | `scripts/vegetation/gen_leaf_textures.py`, `gen_fern_textures.py`, `scripts/vegetation/gen_cluster_textures.py` | leaf / frond / flower-cluster PNGs; shared `textures/leaf_atlas.png` (4×7 grid, `ATLAS_COLS/ROWS`) |

Runtime: `undergrowth_builder.gd`. The key facts that shape every brief:

- **Chunk-based MultiMesh, 20 m chunks** (`CHUNK = 20.0`). `LOAD_RANGE 160` /
  `UNLOAD_RANGE 180`; visibility fades out by `VIS_END = 200` over `VIS_FADE_MARGIN
  30`. **There is no impostor tier and no discrete LOD** — a species is one mesh, drawn
  by MultiMesh within ~200 m and culled beyond. So a brief's "tier coverage" is **n/a**;
  the realism budget is the single near-field mesh, and the only distance behaviour is
  the fade. (If a species ever needs a far-field cheap form, that's new
  infrastructure — flag it, don't assume it.)
- **`SPECIES` array carries per-species runtime metadata** already (ln 56–143):
  `name`, `v` (variant count), `s` (scale-multiplier range), `flex` (wind sway 0–1),
  `green` (1 = evergreen), `fall` (fall-color RGB), `fc` (flower-color RGB; `0,0,0` =
  none), `bl` (bloom `season_t` range), `sc` (stem color), `sr` (stem roughness),
  and optionally `trans`/`rough`/`spec`. **The brief's job is to make these values
  *true to the reference* and to make the geometry match them** — they are the wiring
  between the model and the shaders.
- **Variants** use the `v` key: meshes `<Name>_0 … _(v-1).glb`, picked per chunk for
  variety (only spicebush uses this today, `v=3`). Adding variants is the per-instance
  anti-tiling lever (§4).
- **Placement is zone-driven and data-first** (`ZONE_SPECIES`, `WOODLAND_SPECIES`),
  keyed to the atlas zone type (0 SheepMeadow, 1 GreatLawn, 2 NorthMeadow, 3
  FormalGarden, 4 SportsTurf, 5 NorthWoods, 6 Ramble, 7 Waterside, 8 WildMeadow, 9
  OpenLawn) and to `WOODLAND_Z_RANGES` for chunks lacking pre-baked data. **Densities
  are per-100 m².** A canopy buffer (L8, 0 = open sky … 255 = dense canopy) gates
  shade placement.
- **`season_t` drives appearance** (updated per frame by `main.gd`): leaf-out, summer
  mass, fall color (`fall`), drop, bloom window (`bl`). `rain_wetness` too. Any change
  to a species' leaf/flower geometry must be checked across the season_t range, exactly
  as trees recalibrate `WINTER_RETENTION` (§9).

### 1b. Vines — `make_vine.py` → `Vine_*.glb` → `vine_builder.gd`

Seven species (`VINE_SPECIES`): Virginia creeper, English ivy, bittersweet, porcelain
berry, wild grape, honeysuckle, wisteria. Four climbing-mechanism builders exist
(`make_vine_strand`, `make_spiral_wrap`, `make_climbing_pad`, `make_ground_runner`).
The runtime already has the ecology: `BARK_AFFINITY` per host species, forest-edge
boost, zone gating, per-tree attachment. **But the whole system is disabled**
(`vine_builder.gd:104–111`): the GLBs are "stick-card primitives below the bar." Vines
are a full reference-first redesign **plus** a re-enable, and they're the lowest
priority group (§6) — the user has repeatedly deprioritised them and they were the first
thing turned off.

### 1c. Ground cover — `ground_cover_builder.gd` `COVER_MODELS`

Ten floor models: `GroundCover_DeadLeaves_01/02` (seasonal=2, autumn),
`GroundCover_ForestLeaves_01/02` (year-round litter), `GroundCover_Moss_01/02`,
`GroundCover_Branch_01/02` (fallen twigs), `GroundCover_Seedling_01/02` (deciduous /
conifer). Chunk-MultiMesh, extends `chunk_builder.gd`. These are **floor ephemera**
(connective tissue, [[feedback-project-soul]] "only ephemera are procedural") and get a
lighter treatment than a hero shrub (§8) — but two things must be checked: their
**seasonal wiring** (litter should appear with leaf-drop, not in spring) and their
**provenance** — confirm each `GroundCover_*.glb` is an original/distributable asset and
not an unattributed import ([[feedback-distributable-assets]]); if any came from the
gscatter/photogrammetry library it must be replaced with an original before v1.0.

---

## 2. The quality bar and the perf budget it lives inside

**The bar is the spicebush LOD0 and the trees' LOD0** — the project's two best assets
([[project-asset-quality-ground-truth]]). "Very realistic" for a non-tree plant means
the same three things the method names, at plant scale:

1. **Right habit** (§1 of the method) — the single biggest lever and the current
   models' worst failure. A real *Lindera* cascades; a real ostrich fern is a tight
   vase shuttlecock; a real little bluestem is a dense vertical tuft that flares at the
   tip; a real cattail is a strict vertical strap-leaf colony. The generic
   `make_crossed_planes` / `_make_shrub` helpers produce none of these — they produce a
   billboard bush. **Habit comes from modeling the gesture from reference, not from a
   helper.** This is why the work cannot be a parameter sweep on the existing helpers.
2. **Interaction** — shrubs form **thickets** (overlapping cascading masses), wetland
   plants form **dense colonies/stands** (a wall of cattail, a reed bed), woodland
   forbs form **drifts/carpets** (white wood aster, PA sedge), meadow grasses form a
   **matrix**. The validation unit is the stand/thicket/colony, never one instance (§10,
   method §4).
3. **Behavior** — wind (`flex`) and season (`season_t`) tuned to the reference, not
   left at a generic default. The wetland research doc (`wetland_grasses_9species.md`)
   gives a per-species wind signature table — use it; "wind doesn't flow" is a standing
   user complaint.

### Perf budget (different from trees — measure, don't assume)

Trees are fragment-shading-bound (canopy overdraw). Undergrowth is **smaller per
instance but placed at high count over chunks**, so its costs are: (a) **MultiMesh chunk
build time** (`undergrowth_builder.gd` tracks `_peak_build_us` / `_last_build_us` — watch
it; a heavy per-instance mesh or a too-dense zone stalls chunk loads and causes hitches
as the player walks), (b) **transparent-card overdraw** where many instances overlap
(thickets, colonies — exactly the interaction we want, so it must be paid for carefully),
and (c) total instance count × tris.

Rules:

- **Gain density from form, texture, and placement — not from raw card count.** Same
  rule as trees (§2 there). A thicket reads as dense because the *masses overlap and
  cascade*, not because each shrub has 3× the cards. Cluster-card textures
  (`gen_cluster_textures.py`) put many leaves in one card — prefer them to many single
  leaf cards.
- **Stay near the current per-species tri counts** (the generator docstrings cite
  ~1500–2500 faces for shrubs; spicebush variants are 33–50 k tris and are the
  *upper* bound, justified by its dominance). A 1.1 m fern or a 0.4 m aster does not get
  a spicebush budget.
- **Re-enabling placement is the real perf event, not the model.** Adding a species
  back to `ZONE_SPECIES` at density D multiplies its cost across every chunk in that
  zone. Calibrate D to the real field density (the briefs cite stems/m² or cover %),
  then **perf-gate the zone** (Ramble/North Woods for woodland; the wetland/meadow
  locations for those). The woodland floor is already the tightest frame budget
  (45 fps) — every placed understory species spends into it.
- `perf_gate.sh` ×5 locations, per-location targets (60 open / 45 woodland), no
  regression — same gate as trees.

### 2b. Seasonal state and bloom — a first-class requirement, not an afterthought

Non-tree plants are **far more seasonal than trees**: most are herbaceous and either
die back completely, collapse at frost, or stand as dead structure through winter, and
their **bloom is often the entire identity** (cardinal flower *is* a scarlet spike in
August; goldenrod *is* a golden autumn plume; witch hazel *is* yellow ribbons in
November; little bluestem *is* copper-and-silver in October). A model that's only right
in summer green is wrong three seasons out of four. So every brief states, and every
model and `SPECIES`-row must honor, the full **seasonal timeline** — and the runtime
already has the hooks for it (`undergrowth_builder.gd` `season_t` per frame; per-species
`fall` color, `green` evergreen flag, `fc` flower color, `bl` bloom `season_t` window).

Each species must be correct in **five seasonal states**, validated by the seasonal-sweep
DoD (§10):

1. **Spring flush / emergence** — fiddleheads (ferns), red shoots (knotweed/pokeweed),
   the basal rosette (biennials like burdock; cardinal flower's overwintering rosette).
2. **Summer mass** — full foliage, the baseline.
3. **Bloom** — fired in the species' real **`bl` window** with the right `fc` color, and
   *staggered* so a stand doesn't all flower on one frame (§4). Bloom timing is wildly
   species-specific and must match the brief: spring (yellow iris, PA/tussock sedge,
   cinnamon-fern fertile fronds), early–mid summer (elderberry, viburnum), mid–late
   summer (most forbs, sweet pepperbush, cattail spike browning), **autumn** (goldenrod,
   the asters, little bluestem seed-silver, and the outlier **witch hazel**, which blooms
   on bare branches in late fall).
4. **Fall** — the `fall` color (and for some the *bloom is the fall event* — asters,
   goldenrod) or the showy fall foliage (sumac scarlet, little bluestem copper/wine,
   viburnum wine-purple); fruit/seed-head states (sumac crimson cones, viburnum
   blue-black berries, elderberry purple berries, milkweed/teasel-like persistent heads).
5. **Winter** — the decisive split the brief must declare for each species:
   - **Evergreen / semi-evergreen** — stays green (`green=1`): christmas fern (reclining
     but green), PA sedge (semi-evergreen base).
   - **Frost-collapse annual/tender** — vanishes suddenly at first frost: jewelweed,
     sensitive fern (no winter presence at all — must disappear, not brown-in-place).
   - **Standing dead structure** — persists as a recognizable winter skeleton/seed-head:
     spicebush twiggy skeleton, knotweed tan canes, ironweed stiff stalks, phragmites
     silver plumes, cattail brown spikes bursting to fluff, ostrich/sensitive-fern dark
     fertile fronds, goldenrod fluffy plumes.

Because foliage geometry and card counts change during this redesign, any
season-dependent value baked into the model or the seasonal system (leaf-drop fractions,
the trees' `WINTER_RETENTION` analog, fertile-frond/bloom gating windows) is **silently
invalidated by a model change and must be recalibrated per species** — exactly the trees'
gotcha (§9 step 5, tree spec §6 step 6). A species is not done until its five states are
captured and correct.

---

## 3. Reference sets and briefs (do this before touching any species)

Follow [`vegetation_modeling.md`](vegetation_modeling.md) §3 exactly: sourcing order
**iNaturalist CP-geofiltered → claudetube walk/time-lapse video → Conservancy/NYBG/
extension → user-supplied.** Per species, a board under `notes/refs/veg/<species>/`
(gitignored bulk; tracked one-page `BRIEF.md` from `BRIEF_TEMPLATE.md`). The brief is
the **falsifiable target** the DoD is judged against.

**We start with a large head-start that trees did not have:** two thorough research
documents already exist and cover 22 of the 35 undergrowth species —
[`docs/botany/herbs_13species.md`](botany/herbs_13species.md) and
[`docs/botany/wetland_grasses_9species.md`](botany/wetland_grasses_9species.md). These
are *text* references (habit, dimensions, color, wind, seasonal timeline, CP habitat)
assembled from USDA/extension/field-botany sources. **They are inputs to the briefs,
not substitutes for them** — convert each into the falsifiable `BRIEF.md` format
(one-line habit, interaction, the one unmistakable thing, the build mapping), and still
gather the **visual** reference the text can't give: iNaturalist photos of the *Central
Park* population (confirms it's actually here and what it looks like here) and, where
habit/wind/season is unclear from stills, a **walk video** (the user supplies these on
request — ask).

The shrubs (7), ferns (4), vines (7), the aster, and the ground-cover floor set have
**no research doc** — those briefs are written from scratch against the reference set,
and they are the judgment-heavy ones (§6 ordering puts the structural shrubs first).

**When to ask the user for more material** (the user offered): ask for a walk video or
photos when —
- a species' **habit in a stand** is unclear from stills (how a spicebush thicket
  layers; how a phragmites bed reads as a wall; how white wood aster drifts under
  trees), or
- its **wind behavior** matters and isn't legible (the grasses especially — the
  shimmer of little bluestem, the fountain-stream of switchgrass, the carpet-ripple of
  PA sedge), or
- its **CP-specific** form differs from the generic (urban-nutrient cattail height,
  managed/controlled invasives like phragmites/knotweed/yellow iris that may be small
  remnant patches rather than textbook stands).

State the specific question when asking ("a Ramble spicebush *thicket* in leaf, and a
North Woods fern *stand* on the slope — I have isolated-plant stills but not the
in-stand layering"), so the user can grab the right clip.

---

## 4. Per-instance and per-stand variation

Undergrowth tiles worse than trees because it's denser and lower (the player walks
*through* it). Anti-tiling levers, in order:

1. **Mesh variants** (`v` key). Spicebush uses `v=3`. Give every **placed at high
   density** species 3–5 variants spanning the real range (age, sun/shade, size) per
   [[feedback-research-before-generator]] — the brief's §7 sets the envelope. Low-density
   scattered accents (a lone pokeweed at a woodland edge) can stay at 1–2.
2. **Runtime scale/rotation jitter.** The builder already applies the `s` scale-range
   and per-instance yaw. Verify (don't double-apply); widen `s` for species with a wide
   real size range (cattail 1.5–3 m, knotweed canes).
3. **Seasonal + flower variation** via `season_t` / `fc` / `bl` — bloom should not all
   fire on the same frame; stagger if the shader allows.
4. **Stand-level composition.** Coherence is a *placement* property: a real thicket is
   not a grid of identical shrubs but a few large overlapping masses with smaller infill.
   Where the density and dedup logic forces a tidy grid, that's a placement bug to fix in
   `undergrowth_builder.gd`, not a model bug (mirror trees §5b).

DoD for variation: a dense same-species stand (spicebush thicket, cattail colony, aster
drift) shows no visible repeat at walking distance.

---

## 5. Spicebush — the worked hero (kill the V)

Spicebush is the canonical named failure and the first species done, exactly as
cathedral_elm was for trees. It already has a complete `BRIEF.md`
(`notes/refs/veg/spicebush/BRIEF.md`) and a dedicated section in the tree spec
([`tree_model_redesign.md`](tree_model_redesign.md) §7) — **read both; do not duplicate
them here.** The essentials:

- **Habit first.** Real *Lindera benzoin* is multi-stemmed; primary stems arch and
  secondary growth droops and layers over itself into a **mound/cascade — never a V.**
  The generator (`make_spicebush()`, `make_undergrowth.py:844`) literally builds "a vase
  shape wider than tall" with stems "leaning strongly outward" — that *is* the V, by
  design. Replace the radiating-stems construction with **arching primaries + drooping
  layered secondaries.** The willow **`create_strand_cards_at_positions`** lesson (hung,
  gravity-following cards) and **`compound_mode`** are the transferable tools from the
  tree work — spicebush foliage is simple-leaved but the *drooping layered* card
  placement is the same problem the strand system solved.
- **Winter ≠ mound.** The brief's winter reference is explicit: bare, it's a sparse,
  fine, twiggy, leggy arching **skeleton** low on the slope, *see-through* — the cascade
  is a summer-foliage read. Recalibrate the seasonal leaf-drop accordingly.
- **Validate on a thicket** (North Woods / Ramble), not one shrub — overlapping
  cascading masses are the whole point.
- Widen from `v=3` toward `v=4–6` for the dominant woodland shrub.

Spicebush is **already placed** (it's the only thing placed), so its re-enable is free —
this is the one species where step 2 of §0 is already done. Everything learned here
(arching/drooping card placement, thicket validation, season recalibration) is the
template the other six shrubs copy.

---

## 6. Per-group work order and the tuning loop

Per species, the loop (judgment work — see §11 for who leads):

1. **Gather reference + write/finish `BRIEF.md`** (§3). For the 22 research-doc species,
   convert the doc; for the rest, write from scratch. No geometry before the brief.
2. **Re-baseline.** Render the *current* GLB (or note it's a retired stick-card) against
   the brief — record what's actually wrong. Check, don't estimate.
3. **Model habit first** in the `make_<species>()` function — the gesture/flow before any
   detail. This usually means *replacing* a `make_crossed_planes`/`_make_shrub` call with
   bespoke geometry, the way spicebush is bespoke. The generic helpers are the problem.
4. **Density + detail** to the brief's bucket (cluster-card textures, leaf/frond/blade
   shape, flower clusters) within the perf budget (§2).
5. **Behavior** — set `flex` and the seasonal `fall`/`fc`/`bl` from the reference (the
   wetland doc's wind table is a direct source); verify across `season_t`.
6. **Variants** — author `_0.._N-1` and set `v` (§4).
7. **Reconcile the `SPECIES` array row** — make `sc`/`sr`/`fall`/`fc`/`bl`/`s`/`flex`
   true to the brief. These are live shader inputs.
8. **Re-render + compare to board** (summer / fall / winter, the season where habit is
   most legible) as side-by-side composites. Two failed iterations ⇒ diagnosis is wrong,
   stop and re-look (workflow.md §3).
9. **Re-wire placement** (§0 step 2, §9) — add to `ZONE_SPECIES`/`WOODLAND_SPECIES` at a
   calibrated density; populate empty wetland/meadow zones.
10. **Validate on the stand + perf-gate** (§10), then commit. Commit per verified species
    (no batching).

**Group order** (each group's hero proves the pattern, then the group fans out):

1. **Shrubs (hero: spicebush, done) → witch_hazel, viburnum, sumac, elderberry,
   sweet_pepperbush, flowering_raspberry.** Do these first: they are the sub-canopy
   layer in the North Woods / Ramble validation stands, the most visible non-tree mass,
   and the closest in kind to the worked spicebush. **Viburnum** (dense screen) and
   **elderberry** (arching, like spicebush) are the natural second/third after spicebush.
2. **Ferns → ostrich (hero), christmas (evergreen — winter floor), cinnamon, sensitive.**
   The woodland floor layer in the same validation stands. Habit is distinctive and
   un-helper-able (the ostrich shuttlecock vase, the christmas-fern evergreen rosette).
   `compound_mode` / `make_pinnate_frond` is the shared tool.
3. **Woodland forbs → white_wood_aster (hero — the drift), white_snakeroot, jewelweed,
   the woodland-edge of pokeweed/burdock.** These thicken the same stands and are mostly
   covered by the herbs research doc.
4. **Meadow grasses + forbs → little_bluestem (hero — the signature meadow grass),
   switchgrass, bottlebrush (shade grass), goldenrod, aster, black_eyed_susan, joe_pye,
   coneflower, ironweed, mugwort, knotweed.** These populate `WildMeadow (8)` and meadow
   edges, currently empty. The grass habit (dense tuft, fountain, shimmer) is the lever.
5. **Wetland → cattail (hero — the colony wall), yellow_iris, lizards_tail, phragmites,
   rose_mallow, cardinal_flower, tussock_sedge, pa_sedge.** Populate `Waterside (7)`,
   currently empty. Colony/stand interaction dominates; the wetland doc covers the cores.
6. **Vines (lowest priority) → full redesign + re-enable (§7).**
7. **Ground cover floor (alongside, low effort) → seasonal + provenance pass (§8).**

**USER CHECKPOINT** after the **shrubs** group (spicebush already approved; get a
walk-around on witch_hazel + viburnum + elderberry before fanning out the rest) — same
cheap insurance as the trees' cathedral_elm+oak checkpoint.

---

## 7. Vines — redesign + re-enable (lowest priority)

The system is off and the user has repeatedly deprioritised it; do it last, and only
after the woodland/wetland groups land. When it's time:

- The **runtime ecology is sound** — keep `vine_builder.gd`'s `BARK_AFFINITY`,
  forest-edge boost, per-tree attachment, and the four climbing-mechanism builders.
  The defect is purely the **geometry** ("stick-card primitives").
- Redesign each vine's geometry against its **climbing mechanism + habit**, reference-
  first: Virginia creeper & ivy *cling flat to bark* (`make_climbing_pad` — a sheet of
  leaves on the trunk, palmate vs cordate), bittersweet & wisteria & honeysuckle *twine*
  (`make_spiral_wrap` — a helix up the host, wisteria with pendant flower racemes),
  wild grape & porcelain berry *sprawl with tendrils* over the canopy edge, and several
  *run along the ground* (`make_ground_runner`) before they find a host.
- The hard part is the same as the willow curtain: cards that **drape and follow the
  host surface / hang in festoons**, not flat billboards. Reuse
  `create_strand_cards_at_positions` for pendant wisteria; reuse the bark-conforming
  idea for the climbing pads.
- Re-enable by deleting the early `return` at `vine_builder.gd:111` only after the GLBs
  pass their briefs and a perf gate (vines add overdraw on every hosted tree).

---

## 8. Ground-cover floor — ephemera pass (low effort, do early and in parallel)

This is connective tissue, not a hero. Two concrete jobs:

1. **Provenance audit (blocking for v1.0).** Confirm every `GroundCover_*.glb`
   (DeadLeaves, ForestLeaves, Moss, Branch, Seedling) is an original, distributable
   asset. If any trace to the imported gscatter/photogrammetry library
   ([[reference-vegetation-inventory]]), they must be regenerated as originals in
   `make_ground_cover.py` (extend it beyond turf tiles) before release
   ([[feedback-distributable-assets]]). Record the finding either way.
2. **Seasonal + placement correctness.** `COVER_MODELS` already carries a `seasonal`
   flag (0 year-round, 1 seedling, 2 autumn litter). Verify it fires correctly against
   `season_t` (dead leaves appear at/after leaf-drop and clear by late spring; moss is
   year-round; seedlings are a spring/summer read), and that litter concentrates under
   the canopy buffer (you don't get deep oak-leaf litter on an open lawn). These are the
   floor of the same woodland stands the shrubs/ferns validate on — they thicken
   coherence (method §4) but cannot supply it.

A brief here is a single shared "ground-cover floor" brief describing the litter/moss/
seedling *look and seasonal behavior* (and an iNat/field note on real CP woodland-floor
composition), not seven separate species briefs.

---

## 9. Downstream regeneration + re-wiring (per species, in order)

Undergrowth has **no impostor / no LOD2 / no crown-AO chain** — it's far simpler than
trees. After a species' `make_<species>()` + textures are approved:

1. **Regenerate the GLB(s)** — run `make_undergrowth.py` for that species (one Blender
   process; watch for the Blender-4.5 `--background` teardown hang — `os._exit(0)` like
   the tree LOD generator, [[lessons-technical]]). Write all `_0.._N-1` variants.
2. **Reimport in Godot** — `godot --headless --import`. **Game runs never reimport**;
   skipping this loads stale geometry (the recurring tree gotcha,
   [[lessons-impostor-bake]], [[lessons-technical]]).
3. **Re-wire placement** — add/adjust the species' row in `ZONE_SPECIES` /
   `WOODLAND_SPECIES` with a density calibrated to the brief's real field number;
   populate empty zones (`7` Waterside, `8` WildMeadow) as their groups land. This is the
   step that makes the work visible.
4. **Reconcile the `SPECIES` row** (§6 step 7) if not already done.
5. **Recalibrate seasonal** — verify `fall`/`fc`/`bl` and any leaf-drop across the
   `season_t` range (the undergrowth analog of `WINTER_RETENTION` recalibration).

Back up GLBs to `~/cpw_backups/` before regenerating (the tree program's habit).

---

## 10. Validation / Definition of Done (per species, then group)

Use the existing harness ([[feedback-right-tools]] — the tree program built it):

- **Thumbnail vs board** — reads as the species, matches §1–§6 of its brief, in the
  season where habit is most legible (summer mass + the diagnostic season: fall color
  for sumac/bluestem, bloom for cardinal flower/iris, winter skeleton for spicebush).
- **In-game placed capture at the species' real zone** (`--shots=x,z,yaw[,pitch[,hour]]`
  multi-pose bot; memory "Key test locations" + the wetland/meadow coords). The species
  must actually appear at a believable density — this is the re-enablement check.
- **Stand / thicket / colony capture** (the validation unit, method §4): a spicebush
  *thicket*, a cattail *colony wall*, a white-wood-aster *drift*, a little-bluestem
  *meadow matrix* — judged for overlapping/interlocking mass, not one instance.
- **Behavior** — a short in-game wind capture reads as the brief's wind character; the
  stand moves as one mass with local variation (shared wind field), not on independent
  phases.
- **Seasonal sweep** — leaf-out / summer / fall / drop / bloom fire at the right
  `season_t`; evergreens (christmas fern) stay green in winter; frost-killed annuals
  (jewelweed, sensitive fern) collapse correctly.
- **Per-instance variation** — dense same-species stand shows no tiling (§4).
- **Perf gate** ×5, per-location targets, equal-or-better — run it **after re-wiring
  placement**, not just after the model (placement is the perf event, §2). Beware the
  documented thermal-drift / warm-run trap — use a same-state A/B (trees.md §6c).
- **User walk-around** — final sign-off, ground truth ([[feedback-real-world-observation]]).

**Validation-order dependency:** judging a woodland *stand* is contaminated until the
trees above it are the redesigned models rendered through the current pipeline (the tree
program's tier-approach/fog state). Sequence woodland undergrowth stands *after* the tree
redesign is visible in those stands, or judge near/thumbnail only until then.

---

## 11. Model allocation — who runs what

Per `workflow.md` §6: stronger model leads judgment/architecture and proves each
group's hero; cheaper model fans out the proven pattern.

**Opus 4.8 (judgment-heavy, leads):**
- The shrub group hero work and the spicebush cascade (§5) — the bespoke habit modeling
  that replaces the generic helpers. Each group's **hero** (spicebush, ostrich fern,
  white wood aster, little bluestem, cattail) — proving the loop for that morphological
  family.
- Any change to shared geometry helpers (`leaf_card_utils` card geometry, new bespoke
  helpers analogous to `compound_mode`/strand cards, e.g. a "drooping layered cascade"
  helper the shrubs share) and to `undergrowth_builder.gd` placement logic (§4 stand
  composition, re-wiring densities).
- The vine redesign (§7) — bespoke, the festoon/cling geometry is hard.

**Sonnet 4.6 (mechanical, executes a proven spec):**
- Converting the 22 research-doc species into `BRIEF.md` (research already done — §3) —
  follow the worked example; flag any species whose habit the doc can't resolve.
- The tuning loop (§6) for the **non-hero** members of each group once the hero exists.
  Escalate a species that fights the pattern (anything needing a new geometry helper).
- The downstream regen + reimport + re-wiring batches (§9), perf-gate sweeps, capture
  batches, the ground-cover ephemera pass (§8).

**Rule of thumb:** "does this look like the reference / like a real <plant>?" → Opus.
"run this generator across these N species, reimport, re-wire, report numbers" → Sonnet.
When Sonnet hits a judgment call the brief doesn't answer, stop and hand up — don't guess
([[feedback-no-guessing]]).

---

## 12. Sequence summary + brief status

1. ~~Spicebush brief~~ — **DONE** (`notes/refs/veg/spicebush/BRIEF.md`).
2. **Shrub briefs** (witch_hazel, viburnum, sumac, elderberry, sweet_pepperbush,
   flowering_raspberry) — write from scratch (no research doc).
3. **Fern briefs** (ostrich, christmas, cinnamon, sensitive) — write from scratch.
4. **Herb + wetland/grass briefs** (22) — convert the two research docs to template.
5. **Vine + ground-cover briefs** — vines (7, climbing-mechanism-centric); one shared
   ground-cover floor brief.
6. **Opus:** spicebush cascade redesign (§5) — the worked hero; proves the loop + any
   shared cascade helper.
7. **Opus:** shrub group (viburnum, elderberry first) → **USER CHECKPOINT.**
8. **Sonnet:** remaining shrubs, then ferns following the ostrich hero.
9. **Opus heroes + Sonnet fan-out:** woodland forbs → meadow grasses/forbs → wetland,
   each group hero-first, **re-wiring placement and populating the empty zones as each
   group lands** (§0 step 2 — the work is invisible until this happens).
10. **Vines** (§7) and the **ground-cover ephemera pass** (§8).
11. **User walk-around** sign-off; the reference-first method
    ([`vegetation_modeling.md`](vegetation_modeling.md)) governs every remaining plant
    in the post-sprint model-redo program.

Throughout: commit after every verified species, **re-wire its placement in the same
commit** (a remodel that isn't placed is not done), perf-gate any placement change, and
update this doc and the briefs if reality diverges from the spec (workflow.md §2).

Relates to [[project-tree-model-redesign-plan]], [[mission-fable5-sprint]] (D12-13
model-redo program), [[project-asset-quality-ground-truth]],
[[reference-vegetation-inventory]], [[reference-cp-botany-full]],
[[reference-vegetation-modeling]], [[feedback-research-before-generator]],
[[feedback-distributable-assets]].
