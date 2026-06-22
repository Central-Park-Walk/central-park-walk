# Tree & Spicebush Model Redesign — implementation spec

Written 2026-06-11 (Fable 5 planning session). This is the plan a cheaper model
(Opus 4.8 / Sonnet 4.6) executes. It covers **model geometry and art direction
only** — the rendering tiers, runtime-lit impostors, shadow proxies, crown AO, and
their budgets are already solved and specified in [`trees.md`](trees.md); this spec
feeds new/better source meshes into that same downstream chain.

Read [`vegetation_modeling.md`](vegetation_modeling.md), [`trees.md`](trees.md), and
[`workflow.md`](workflow.md) first. **The method doc is load-bearing here** — it
defines the reference-first discipline (habit / interaction / behavior) that this tree
work is the first application of, and it diagnoses *why* the current models fail (wrong
habit, no crown interaction, no ecological coherence). This doc is the tree-specific
application of that method. Every change is bound by the workflow.md Definition of Done
and the `DESIGN.md` quality bar (**1080p / 60fps on RTX 3060 Ti**, faithful to data,
validated against reference images not feeling).

---

## 0. Direction decision — refine the procedural pipeline; do NOT switch to image-to-3D

The suggestion was: have Claude generate 2D still images of each tree, then convert
those to 3D models. **Rejected as the geometry source. Adopted as the art-direction
and validation layer.** Reasoning (this is load-bearing — do not relitigate it
mid-implementation):

- **The goal "every instance looks different" requires parametric control.** A mesh
  reconstructed from one image is a single frozen object. The current pipeline already
  produces per-instance variation: 5 independent seed variants per size-tier per
  species, picked per chunk at runtime. That axis is the answer to the user's request,
  and image-to-3D throws it away.
- **"Cathedral elms whose enormous branches converge over Literary Walk" requires
  shaping the skeleton**, not capturing one. We tune branch angle / gravity /
  up-attraction / length to make the arch, and we orient/pair instances across the
  path. A photogrammetric blob can't be made to lean toward its neighbor.
- **Image-to-3D (TripoSR / InstantMesh / Meshy / Tripo etc.) produces topology hostile
  to this engine:** watertight blobs with baked-in foliage, no separable leaf cards, no
  bark/leaf material split, no clean decimation path, and no wind vertex colors (the
  `R=hierarchy_depth, G=branch_extent, B=stem_id` encoding the wind shaders depend on).
  The whole hard-won downstream chain in trees.md (opaque-pass leaf cards, octahedral
  impostor bake, lathe-fit shadow proxies, per-vertex crown AO) assumes the current
  card+branch representation.
- **Distributability / MIT.** Assets must ship free under MIT with no manual
  third-party download ([[feedback-distributable-assets]], [[feedback-right-tools]]).
  AI-mesh-gen outputs carry unsettled licensing and often need an external service. The
  Mtree pipeline is fully in-repo and reproducible.
- **Data-first soul.** The project renders from data ([[feedback-project-soul]]). A
  parametric tree driven by per-species LAI / crown / DBH data is on-charter; a
  hallucinated mesh is not.

**Where 2D images DO belong:** as the *target* for each species — a reference board
that defines the silhouette, branch character, crown density, bark, and seasonal color
we are tuning the generator to match, and against which the visual DoD is judged
(workflow.md requires comparison to reference, not vibes). Prefer **real photographs**
of the actual Central Park / NYC specimens (data-first); AI-generated images are an
acceptable *art target* only where a clean reference photo can't be found, and are
never traced into geometry. See §3.

The one case worth a footnote: a genuinely unique hero landmark tree (e.g. a single
famous specimen) is the only place a bespoke one-off mesh could be justified. We have
none scoped, distributability still bites, so this stays out of scope. Mentioned only
so it isn't rediscovered as a surprise.

---

## 1. The pipeline as it exists today (don't reinvent these)

Generation chain, in order. Touch these; do not replace them.

| Stage | File | Produces |
|---|---|---|
| Skeleton + leaf cards | `scripts/generate_trees_mtree.py` (2181 ln, `SPECIES` dict @ ln 330) | `models/trees/{species}_{s,m,l}.glb`, 5 variants each, normalized 5 m height, wind vertex colors baked |
| Leaf-card geometry/material helper | `scripts/leaf_card_utils.py` (`make_leaf_cards`, `create_leaf_material`) | branch-walk card placement used by the generator |
| Leaf textures | **(SETTLED 2026-06-22: real-photo CLUSTER CARDS — `make_leaf_cluster_from_photo.py` / `make_leaf_cluster_texture.py` → DDS; see `tree-pipeline-lessons.md` banner.)** Old parametric path `scripts/vegetation/gen_leaf_textures.py` (14 species), `scripts/gen_cluster_textures.py` | leaf/cluster PNGs |
| → DDS | `scripts/generate_leaf_dds.py` | runtime leaf atlases (binary-alpha at mip 0 — see trees.md §7) |
| Crown interior AO | `scripts/bake_crown_ao.py` | per-vertex `rho` in COLOR_0.alpha (direct GLB surgery; glTF export drops vertex alpha) |
| lod1 | `scripts/generate_tree_lods.py` | `{species}_{s,m,l}_lod1.glb` (adaptive card prune + bark decimation; ≤ ~12 k tris) |
| Impostor atlases | `scripts/impostor_baker.gd` (Godot) + `scripts/premultiply_impostors.py` | runtime-lit octahedral albedo/normal/depth atlases, 2048² |
| Thumbnails (review) | `scripts/render_tree_thumbnails.py` | one PNG per variant per tier → `models/trees/thumbnails/` |
| Orchestrator | `scripts/regen_all_trees.sh` | one Blender process per species×tier (Mtree mesher segfaults if batched) |

Runtime: `tree_builder.gd` (`SPECIES`/`TIER_BOUNDS` @ ln 111; near tier (lod0) = full
base model since trees.md §7; the old 4-tier 50 %-card near mesh was retired — NOT to
be confused with today's `_lod1`, which is the *mid* tier). Shaders: `tree_leaf.gdshader`,
`tree_bark.gdshader`, `tree_impostor.gdshader`, `tree_shadow_proxy.gdshader`,
`tree_species.gdshaderinc`.

**Species archetypes (15 + dead).** The census maps every genus to one of these
(`convert_to_godot.py` `SPECIES_MAP` @ ln 1437): `oak, elm, cathedral_elm, maple,
pine, cherry, birch, honeylocust, callery_pear, willow, linden, london_plane, ginkgo,
magnolia, deciduous` (+ `dead`). Note the data archetype `conifer` renders with the
`pine` models. Tier coverage is uneven by census reality (TIER_BOUNDS): e.g. magnolia
is `_s`-only, willow has no `_l`, birch/london_plane/conifer have no `_s`,
cathedral_elm is `_m`/`_l` only. **Honor the existing tier coverage** — don't generate
tiers the runtime never requests.

**Known Mtree mesher crashes** (memory `mtree_pipeline`): willow `sub_gravity>30`,
ginkgo dense+highres at large scale, cathedral_elm `sub_density>1.0` at 30 m, callery
pear conical crown, some seeds (e.g. 800 @ 10 m). The current `SPECIES` params already
encode workarounds; when re-tuning, keep one Blender process per species×tier and a
`timeout` so one crash doesn't kill the batch.

---

## 2. "Very realistic" — the quality bar, and the budget it must live inside

Realism here is **silhouette + branch architecture + canopy density + bark + seasonal
color matching the reference board**, at three scales: distant silhouette (impostor),
mid crown mass (lod1), and near branch/leaf detail (base model). The current LOD0 trees
are the project's best assets ([[project-asset-quality-ground-truth]]) and the user
called them "really good" on 2026-06-11 — so this is a *lift to "very realistic,"* not a
rescue. The biggest realism wins, in priority order:

1. **Species distinctness.** Elm vs cathedral_elm vs linden vs oak must read as
   different trees from 50 m. The 2026-04-01 thumbnail review flagged
   "elm/cathedral indistinguishable" and broken pine/ginkgo — **re-baseline first**
   (§6 step 1); that review is stale, trust fresh thumbnails not the memory.
2. **Branch architecture you can see near.** Real branch tapering and forking, not
   leaf-clouds on stubs. Foliage should be **60–89% of tree geometry** (AAA norm,
   [[reference-aaa-tree-techniques]]); audit each species — heavy-bark species
   (cathedral_elm_l was 84% bark) have it inverted. **Fix the inversion by cutting
   wasted bark tris** (the measured 31 k three-tri twig-stub islands), **never by
   adding leaf cards to hit the ratio** — that's the §2 overdraw budget violated from
   the other direction.
3. **Canopy density calibrated to LAI** ([[reference-tree-canopy-data]]): opaque
   linden/maple (LAI 5–7, ~1–8% transmission) vs lacy honeylocust (LAI 2–3.5,
   30–50% transmission) vs open birch/ginkgo. The per-species `leaf_density` and
   `CANOPY_OPACITY[]` arrays already encode this — verify they match the reference.
4. **Bark** (`tree_bark.gdshader` styles + bark textures): plane-bark for
   london_plane (mottled, pale inner bark), furrowed oak, smooth young cherry/birch,
   exfoliating. Distinct per style, not one brown tube.
5. **Per-instance variation** (§4): no two neighbors identical in height, lean, crown
   width, or color.

### Budgets (hard — these keep 60fps; from trees.md measurement)

| Tier | Budget per variant | Notes |
|---|---|---|
| Base (near, 0–60 m) | leaf cards are the cost driver; **keep card count at/near the current May-19 LAI-tuned counts** | post-opaque, tree cost is *canopy fragment shading*, not vertex count (trees.md §4f) — so don't inflate card overlap/overdraw. Geometry tri count is NOT the lever; **card area × overlap is.** |
| lod1 (60–250 m) | ≤ ~12 k tris (+1 k slack) | `generate_tree_lods.py` enforces adaptively; re-run after any base change |
| impostor (190 m+) | 2048² atlas, baked from base | re-bake after any base change (per-species wrapper, §8) |

**The single most important budget rule:** trees are **fragment-shading-bound**, not
geometry-bound, at 1080p on this GPU (trees.md §4f/§4g). More realistic branch geometry
(more tris) is ~free; more/larger/more-overlapping leaf cards is NOT — it adds canopy
overdraw, the thing that costs frames. Spend realism on **branch geometry and
texture/normal detail** (texture-latency-bound shaders ride ALU and extra fetches
nearly free, trees.md §4g) and on **smarter card placement**, not on raw card count.
Every species change must pass `scripts/perf_gate.sh` ×5 with no regression.

---

## 3. Reference boards (do this before touching any species)

Follow [`vegetation_modeling.md`](vegetation_modeling.md) §3 for the full method and
sourcing order (iNaturalist CP-geofiltered → claudetube walk/time-lapse video →
Conservancy/NYBG → user-supplied). Per archetype, the board lives under
`notes/refs/veg/{species}/` (gitignored bulk; tracked one-page `BRIEF.md`) and must
capture not just the silhouette but the three things the current models miss:

- **Habit** — the tree's gesture: how branches reach, arch, and droop, where it forks,
  how asymmetric a real competing-for-light specimen is. The **winter bare-structure**
  image is the most important single reference (the skeleton is where habit lives) and
  the current models' weakest point ("branches occupy a cylinder").
- **Interaction** — at least one image of the species *in a stand/grove growing into
  its neighbors*, not an isolated specimen on a lawn. This is the target for the §6.5
  forest-coherence work.
- **Detail + behavior + season** — bark close-up, leaf/cluster close-up, fall color,
  and (from video) how the crown moves in wind.

`BRIEF.md` states, in falsifiable terms: crown shape + aspect, branch arch character +
first-branch height, **interaction behavior** (crowns merge into a ceiling / solitary),
canopy density bucket tied to the LAI number, bark style, wind character, summer + fall
color, and the one sentence that makes the species unmistakable. Pull numbers from
[[reference-tree-canopy-data]] / [[reference-vegetation-modeling]] — don't re-estimate.
Without the board, "looks better" is not a checklist item (workflow.md §2).

Cathedral elm gets its own board emphasizing the **Literary Walk arch** — the four
rows of mature American elms meeting overhead. This is the project's signature view,
and the purest example of the interaction failure: the value isn't the single elm, it's
the crowns *converging*.

---

## 4. Per-instance variation strategy

Today: 5 seed variants × {s,m,l} per species, plus runtime per-instance color jitter
and (now) per-tree height from census DBH. Push it further so a stand never tiles:

1. **Widen the seed envelope.** Per [[feedback-research-before-generator]], survey the
   species' real variation (age, sun vs shade, soil) and set the 5 variants to span it
   — not 5 near-identical draws. Vary crown width, lean, asymmetry, first-branch
   height, and density across the 5, within the species silhouette. Consider raising to
   **6–8 variants** for the high-count species (oak 2.6 k, london_plane 1.7 k, linden
   1.75 k, honeylocust ~6 k combined, callery_pear 2 k, ginkgo 1.8 k) where tiling is
   most visible; keep 5 for rare ones. **Plumbing verified (2026-06-11): >5 variants is
   free.** The runtime picker is count-agnostic (`tree_builder.gd:587` hashes mod
   `meshes.size()`; the `.res` cache stores `n_variants` and self-invalidates when the
   GLB mtime is newer, `tree_builder.gd:153-160`); impostor atlases are **per
   species-tier, not per variant** (`tree_builder.gd:1185-1255`), so extra variants add
   zero impostor VRAM or bake time. Corollary: variant diversity vanishes at impostor
   distance (every billboard of a species-tier shows the same bake) — acceptable, since
   tiling is only legible at near/mid tiers.
2. **Runtime per-instance transforms** (`tree_builder.gd`): small random yaw,
   non-uniform scale (±height already from DBH — add slight crown-width jitter), and a
   tiny per-instance lean. What's already applied (yaw?) is settled during the §5b
   pre-diagnosis — verify before adding (don't double-apply).
3. **Per-instance color/phenology jitter** already exists (5 cm seed, fall timing) —
   keep, and make sure widened seed variants don't fight it.

DoD for variation: a capture of a dense same-species stand (e.g. oaks in the North
Woods) shows no visible repeat pattern at walking distance.

---

## 5. Cathedral elm — the signature convergence (hero task)

The user's explicit want: "enormous branches that converge over the Literary Walk."
Two halves, both required:

**(a) Model shape.** The `cathedral_elm` `SPECIES` entry (generate_trees_mtree.py
@ ln 434) already aims at a wide vase (low fork ~0.14, `branch_angle` 55,
`branch_length_ratio` 0.52, reduced gravity). Lift it to "enormous arching branches":
push main-branch length and the upsweep-then-arch profile so the crown genuinely
reaches *across*, not just *out*. Respect the mesher crash ceiling (`sub_density ≤ 0.7`
at 30 m). Validate against the cathedral board's arch reference. The `_l` variant is
the Literary Walk specimen — make it unmistakably grander than plain `elm_l`.

**(b) Placement convergence** (`tree_builder.gd` / placement data). Branches converging
over the path is a *placement + orientation* result, not just a model result: the
Literary Walk elms are four rows flanking a straight allée; instances on opposite sides
must be oriented so their long axes lean toward the path centerline so the crowns meet
overhead. Check how cathedral_elm is currently placed (Literary Walk is a special
location — see memory test coords X≈−600 Z≈1420) and add path-aware orientation if it
isn't there. This is the one view most worth getting right.

DoD: a capture standing in the Literary Walk allée at summer noon shows a continuous
arched canopy tunnel overhead, crowns meeting, matching the reference board — plus the
existing tier/handoff/perf DoD.

---

## 5b. Forest coherence — a woodland, not a tree-farm

The user's core complaint: "the forest seems made up of individual trees, rather than
being a coherent ecological feature." This is **emergent** — it is the relationship
between trees, not a property of any one — so it has its own treatment and its own
validation unit: **the stand, not the specimen**
([`vegetation_modeling.md`](vegetation_modeling.md) §4). The test capture is a North
Woods / Ramble stand, judged for canopy closure, crown interlace, and layered
structure. A tree that passes its thumbnail but reads as an isolated ball in the stand
has failed.

**Pre-diagnosis — run this FIRST, before any hero modeling (Sonnet-capable, pure data
analysis, ~a session):** sample actual inter-tree distances in North Woods / Ramble
chunks vs the model crown radii (lever 2); histogram the height distribution in a
woodland chunk (lever 4); confirm what `DEDUP_DIST` and the scatter actually permit
(lever 3); and settle the §4 open question (is per-instance yaw already applied?). Its
output sets the **crown-width targets the hero models are built to** — doing it after
the heroes risks rebuilding them. Also **verify the "shared wind field" claim below in
code** before relying on it: if trees actually sway on independent per-instance phases,
that alone breaks stand coherence and no crown geometry fixes it.

**Stand composition (measured 2026-06-11, scatter weights `convert_to_godot.py:1697` ×
`SPECIES_MAP`):** North Woods is ~42% oak-mapped, ~29% maple-mapped (red/sugar maple +
sweetgum + tupelo), ~14% cherry-mapped (black cherry + dogwood); Ramble is similar.
**London plane and honeylocust are essentially absent from the validation stands** —
they're street/allée trees. So the coherence *visual* pass requires **oak, maple, and
cherry** to be redesigned first (see §6 ordering); judging crown fullness on a stand
that's 60–75% old models proves nothing.

Coherence is built from four levers, together — diagnose which are actually broken
before turning knobs (check, don't estimate):

1. **Crown fullness to the silhouette edge.** Two crowns read as merged only if each is
   dense at its *edge*, not just its core. The opaque-pass + near-sparsity fixes
   (trees.md §4e/§7) already restored edge density — **verify in a woodland capture
   before assuming this is still broken.** If edges read thin, the canopy shell needs
   more card coverage at the rim (not more total cards — perf budget, §2).
2. **Crown width vs real spacing.** Census tree positions are authoritative and, in
   woodland, genuinely close. Crowns that should overlap will overlap *only if the
   model's crown radius matches the species' real spread* ([[reference-tree-canopy-data]]
   crown-spread column). **Check:** sample actual inter-tree distances in a North Woods
   chunk against the model crown radii — if models are narrower than the spacing,
   widen the crown (within habit); if placement dedup is culling the closeness, that's
   lever 3.
3. **Placement density + overlap permission.** `convert_to_godot.py` (`DEDUP_DIST = 3.0`
   m, woodland scatter ~150 trees/ha). Confirm the dedup and scatter actually permit
   crown overlap at woodland density and aren't spacing trees onto a tidy grid. The
   goal is real ecological density, not a plantation.
4. **Height layering.** A real woodland is emergent + canopy + sub-canopy + (shrub +
   herb + floor). DBH-driven height + the s/m/l tiers should already spread heights —
   **verify the height distribution in a woodland chunk spans layers** rather than
   clustering at one canopy height. If it's flat, vary it (more spread in the DBH→height
   map, or ensure sub-canopy species/tiers are present). The shrub/herb/floor layers
   are connective tissue (undergrowth) — they thicken coherence but the canopy layering
   must carry it; undergrowth alone will not (user, explicit).

Also feeding coherence: **asymmetric, interlocking per-instance variation** (§4 — lean,
crown asymmetry, gap-seeking growth so neighbors mesh instead of tile) and a **shared
wind field** so the whole canopy moves as one mass with local variation
([[reference-aaa-wind]], [[project-species-wind]]) — a stand that sways coherently
reads as one feature; trees waving on independent phases read as separate objects.

This work is judgment-heavy and cross-cutting (placement code + crown width + height
map + variation) — **Opus**, after the woodland-dominant species exist (oak, maple,
cherry — see stand composition above) so the crown-fullness lever is judged on good
models. **Perf policy (user decision 2026-06-11, vision.md):** the woodland gate is
**≥45 fps** at ramble/north_woods (60 stays the target in open areas) — this is the
headroom that makes coherence work possible at all, since every lever here adds canopy
overdraw exactly where the frame is most expensive. `perf_gate.sh` enforces the
per-location targets. DoD: North Woods + Ramble stand captures show a closed,
interlaced, layered canopy vs the current "balls with air between them," perf gate ×5
passes (60 open / 45 woodland).

---

## 6. Per-species work order — the tuning loop

For each species, the loop (this is judgment work → stronger model writes/leads it;
see §10):

1. **Re-baseline.** Run `render_tree_thumbnails.py`; look at the *current* output for
   this species, all tiers/variants. Record what's actually wrong vs the board (the
   2026-04 review is stale). This is "check, don't estimate."
2. **Tune the skeleton** in the `SPECIES` dict (branch angle/gravity/length/density,
   trunk fraction, sub-branch params) toward the board's branch architecture. One
   Blender process per species×tier; watch for mesher crashes.
3. **Tune foliage**: `leaf_density`, cluster counts, card size/placement
   (`leaf_card_utils.py`), and the **leaf texture** — now a **real-photo cluster card**
   (`make_leaf_cluster_from_photo.py`/`make_leaf_cluster_texture.py` → `generate_leaf_dds.py`;
   the old parametric `gen_leaf_textures.py` is superseded) toward the board's density
   bucket and leaf shape. Keep card
   *count/overlap* within the perf budget (§2) — gain density from texture/placement,
   not raw overdraw.
4. **Tune bark**: assign/adjust the `tree_bark.gdshader` style and bark color/texture
   for the species' bark character.
5. **Tune behavior**: the species' wind biomechanics
   ([[project-species-wind]] — the per-species params already exist in the shaders)
   against the board's **video** reference. Behavior is one of the method's three
   pillars (vegetation_modeling.md §2) and "wind doesn't flow" is a standing user
   complaint — don't skip this step because it isn't geometry.
6. **Check the seasons**: the seasonal thinning system stores **literal card
   fractions** (`WINTER_RETENTION`, e.g. oak 0.18) — any change to card count or
   placement silently invalidates them. Recalibrate per species, and verify fall color
   against the board.
7. **Re-thumbnail, compare to board, iterate** — render **summer + fall + winter**
   thumbnails (the winter skeleton is where habit is most legible — every BRIEF says
   so; a summer-only check validates the least informative season). Emit
   **side-by-side composites** (board photo | render in one image) so the comparison is
   actually made, not vibed ([[feedback-screenshot-review]]). Two failed iterations ⇒
   the diagnosis is wrong, stop and re-look (workflow.md §3).
8. **Commit the base model + params** for that species, then move on. Downstream regen
   (§8) is batched after a group of species is approved, not per species.

**Hero-first ordering** (prove the loop + the toolchain on these, then fan out):

1. **cathedral_elm** (§5 — signature, hardest, defines the convergence treatment)
2. **oak** (most numerous, 2.6 k; defines the deciduous-broadleaf template)
3. **london_plane** (1.7 k; distinctive mottled bark — proves the bark workflow)
4. **honeylocust** (~6 k combined incl. pagoda/ash/etc.; proves the lacy/compound
   canopy — currently a single-plane compound-leaf approximation, see
   [[reference-tree-canopy-data]] §7)

Then **maple and cherry first** — they are the woodland mass (~29% + ~14% of the
North Woods / Ramble stands via `SPECIES_MAP`: sweetgum/tupelo → maple, black
cherry/dogwood → cherry) and the §5b coherence pass cannot run until they exist.
Then the rest by census count: linden, callery_pear, ginkgo, elm,
pine/conifer (the old "bare sticks" species — needs needle-mass work), magnolia,
birch, willow, and `deciduous` (the generic fallback — make it a believable average
broadleaf), `dead` (bare structure; no foliage, no impostor by design — trees.md /
memory architecture note).

---

## 7. Spicebush redesign

Spicebush (`models/vegetation/Shrub_Spicebush_{0,1,2}.glb`, 3 seed variants,
50/45/33 k tris) is the other asset at the quality bar
([[project-asset-quality-ground-truth]], [[reference-vegetation-inventory]] §B). It is
placed by `undergrowth_builder.gd` (entry @ ln 60; dominant in North Woods / Ramble).
Its generator is the bespoke `make_spicebush()` path with custom cluster-card textures,
spectral colors, and the 3 seed variants — **confirmed (2026-06-11):
`scripts/make_undergrowth.py:844` (`make_spicebush`)**, whose stem comment (line ~896)
literally says "leaning strongly outward to form a vase shape wider than tall" — the V
is by design, which is exactly the §1 rule-not-reference failure.

**The named failure is habit: it looks V-shaped instead of "flowing over itself"**
(user, 2026-06-11). This is the canonical example of the
[`vegetation_modeling.md`](vegetation_modeling.md) §2 habit problem — the generator
built stems radiating up-and-out (a vase) instead of modeling the real plant. *Lindera
benzoin* is a multi-stemmed shrub whose **primary stems arch and whose secondary growth
droops and layers over itself into a mound** — it cascades, it never makes a V. Fixing
that is the priority, and it requires building from the reference set (iNat CP photos +
a walk video for the drooping habit and how thickets read), not from rules.

Scope: same reference-first lift as the trees, at shrub scale. **Habit first** (arching
multi-stem + drooping layered secondaries → mounding cascade), then density/detail/
behavior, then a wider seed envelope (consider 4–6 variants from the current 3, per
[[feedback-research-before-generator]]). Validate on a **thicket capture** (North Woods
/ Ramble), not one isolated shrub — spicebush is thicket-forming and the overlapping
cascading masses are the point ([`vegetation_modeling.md`](vegetation_modeling.md) §4).
It does **not** use the tree impostor chain; confirm how undergrowth LODs/billboards
work (`undergrowth_builder.gd`) before assuming. Keep it within the undergrowth perf
budget and re-run `perf_gate.sh`.

The 6 other shrubs (witch hazel, viburnum, sumac, elderberry, sweet pepperbush,
flowering raspberry) are procedural placeholders below the bar
([[reference-vegetation-inventory]] §B) — **out of scope here**; they belong to the
broader post-sprint model-redo program, after trees + spicebush land.

---

## 8. Downstream regeneration (already specified — just run it, in order)

After a species' base model + textures are approved, regenerate its full chain. The
order and the gotchas are non-negotiable (each cost a debugging session before):

1. `scripts/bake_crown_ao.py` on the new base GLB(s) — writes crown `rho` to
   COLOR_0.alpha (direct GLB surgery; **Blender glTF export drops vertex alpha**, hence
   the surgery — do not "fix" it by re-exporting). Back up models first
   (`~/cpw_backups/`).
2. `scripts/generate_tree_lods.py` for the species — regenerates `_lod1` from the new
   base (adaptive recipe; Blender 4.5 `--background` hangs at teardown → the script
   `os._exit(0)`s, expected).
3. **Reimport in Godot** — `godot --headless --import`. **Game runs never reimport**;
   skipping this means the game loads stale geometry (trees.md, [[lessons-technical]],
   [[lessons-impostor-bake]] — this has burned multiple sessions).
4. **Re-bake impostors** via the per-species wrapper — one Godot process per species
   (~12 s; all-at-once hangs, [[lessons-impostor-bake]]), then
   `premultiply_impostors.py`, then **reimport the atlases again**.

The old 4-tier 50 %-card **near** mesh is retired (trees.md §7) — do **not** add a
card-pruned near tier; near tier (lod0) = full base model. (Today's `_lod1` is the
*mid* tier and IS regenerated — step 2 above.)

---

## 9. Validation / Definition of Done (per species, then whole-set)

Use the harness that already exists — don't invent new validation
([[feedback-right-tools]]):

- **Thumbnail vs board** (`render_tree_thumbnails.py`): the species reads as itself,
  matches the board's silhouette/density/bark/color — in **summer, fall, AND winter**
  (§6 step 7), as side-by-side composites against the board.
- **Behavior**: a short in-game wind capture (moving frames, not a still) reads as the
  board video's wind character; the stand sways as one mass with local variation, not
  on independent phases.
- **In-game near capture** at a location the species dominates (memory "Key test
  locations"): branch architecture and canopy density correct close up; no near-tree
  sparsity regression (trees.md §7 mechanism — discard threshold follows
  `textureQueryLod`, not camera distance; don't reintroduce distance-ramped discard).
- **Tier handoff** (`scripts/tier_handoff_check.sh`, env `TIER_A`/`TIER_B`,
  `EXTRA_ARGS`): base↔lod1 at 60 m and mesh↔impostor at 240 m, mean |ΔRGB| < 0.05, no
  hue flip (mind the documented backdrop artifact that inflates the raw 240 m metric —
  trees.md §4f/§5).
- **Crossfade walk**: slow walk across the boundary, compare per-frame canopy
  *statistics* (raw pixel deltas on a moving camera measure parallax, not steps —
  trees.md §7 protocol note).
- **Per-instance variation**: dense same-species stand shows no tiling (§4).
- **Perf gate** (`scripts/perf_gate.sh`) ×5 locations: equal-or-better vs the canonical
  baseline. Beware the documented thermal-drift trap — single warm-run anomalies need a
  same-state sandwich A/B before they're real (trees.md §6c, mission Jun-10 notes).
- **Cathedral elm**: the Literary Walk arch capture (§5 DoD).
- **User walk-around**: final sign-off (the user is ground truth,
  [[feedback-real-world-observation]]).

**Validation-order dependency:** any *distance/stand* judgment (impostor-range reads,
§5b captures) is contaminated until the **tier-approach continuity pass** lands
(sprint open item: impostor re-bake through current shaders + fog/crossfade
attribution — mesh tiers got denser after the Jun-11 mip-threshold fix while impostor
atlases weren't re-baked, and the §6c fog veil colors everything past ~200 m). Near
and thumbnail validation are unaffected. Don't tune a species against a distant read
before that pass is done — you'd be tuning against a known-broken pipeline stage.

---

## 10. Model allocation — who runs what

Per workflow.md §6: stronger model does architecture/spec/hardest implementation +
proves the pattern; cheaper model executes the proven pattern across the rest. Concrete
split:

**Opus 4.8 (judgment-heavy, leads):**
- Build the reference-board system and write all 15 + spicebush `BRIEF.md` art briefs
  (§3) — this is the art-direction backbone.
- The cathedral_elm hero task end to end (§5), including the placement-convergence code.
- The per-species tuning loop (§6) for the **hero species** (cathedral_elm, oak,
  london_plane, honeylocust) — proving the loop, the bark workflow, the lacy-canopy
  approach, and the variation envelope. Each hero species, once approved, becomes a
  worked example the cheaper model copies.
- Any change to `leaf_card_utils.py` card geometry, the variation-count plumbing (§4
  step 1), or shader work (`tree_leaf`/`tree_bark`) — these ripple across all species.
- The spicebush redesign (§7) — bespoke, judgment-heavy.

**Sonnet 4.6 (mechanical, executes a proven spec):**
- The §5b **pre-diagnosis** (spacing/height/dedup/yaw/wind-field data analysis) — run
  it before hero modeling starts and report numbers.
- The tuning loop (§6) for the **remaining species** once the hero examples exist,
  following the worked pattern and each species' BRIEF.md. (Escalate to Opus if a
  species fights the template — e.g. pine needle-mass, willow strands.)
- The full downstream regen batch (§8) for any approved group — bake AO, LOD, reimport,
  impostor re-bake, reimport. Purely mechanical, high-volume, exactly the "queued for
  cheaper sessions" work.
- Running the validation harness (§9) and reporting numbers; perf-gate sweeps.
- Re-thumbnail / capture batches.

**Fable 5 (this tier):** not needed for execution — this spec is the Fable 5
contribution. Re-engage only if the direction in §0 turns out wrong (e.g. the
procedural pipeline genuinely can't hit the realism bar on a species after honest
iteration) and the plan needs rearchitecting.

**Rule of thumb:** if the task is "does this look like the reference / like a real
tree?" → Opus. If the task is "run this script across these 12 files and report the
numbers" → Sonnet. When Sonnet hits a judgment call the BRIEF.md doesn't answer, stop
and hand back up, don't guess ([[feedback-no-guessing]]).

---

## 11. Sequence summary

1. ~~**Opus:** reference boards + BRIEF.md for all species (§3)~~ — **DONE 2026-06-11**
   (all 16 briefs committed under `notes/refs/veg/`).
2. **Sonnet:** §5b **pre-diagnosis** (crown width vs census spacing, height histogram,
   dedup behavior, yaw check, shared-wind-field verification) — pure data analysis;
   its output sets the crown-width targets for everything below.
3. **Opus:** any shared `leaf_card_utils` / variation-plumbing / shader groundwork
   (§4, §2).
4. **Opus:** cathedral_elm hero (§5) — model + convergence placement + full chain +
   DoD. Proves the whole loop on the signature view.
5. **Opus:** oak (§6) — the broadleaf template and the biggest woodland species.
6. **USER CHECKPOINT** — walk-around on cathedral_elm + oak before anything fans out.
   One walk here is cheap insurance against replicating a wrong template 14 times.
7. **Opus:** london_plane, honeylocust (§6) — bark workflow + lacy canopy templates.
8. **Sonnet:** **maple + cherry** (§6 — woodland mass, follows the oak template;
   escalate judgment calls).
9. **Opus:** forest-coherence pass (§5b) — now the validation stands are majority new
   models (oak + maple + cherry ≈ 85% of North Woods). Requires the tier-approach
   continuity pass landed first (§9 validation-order dependency). Perf gate: 60 open /
   45 woodland (vision.md).
10. **Sonnet:** remaining species (§6) following the worked examples; escalate the
    awkward ones (pine, willow) to Opus.
11. **Opus:** spicebush (§7) — habit-first (kill the V), validate on a thicket capture.
12. **Sonnet:** downstream regen for every approved group (§8) + validation harness (§9).
13. **User walk-around** sign-off; then resume the broader plan
    ([[mission-fable5-sprint]] / post-sprint model-redo program). The reference-first
    method ([`vegetation_modeling.md`](vegetation_modeling.md)) then governs every
    remaining plant.

Throughout: commit after every verified species (no batching), perf-gate any
per-frame-touching change, update this doc and `trees.md` if reality diverges from the
spec — or the change is wrong (workflow.md §2).
