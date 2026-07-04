# Tree Pipeline Playbook — how to build any typical tree

**This is the single runbook for making a Central Park Walk tree with Blender + Mtree
to project standard.** If you are about to build, rebuild, or tune a tree species, read
this file top to bottom first. It is *live instructions*, not a history log — every
line here is current. The deeper docs (below) explain *why*; this explains *what to do*.

- **Method + war-stories (why each rule exists):** `docs/tree-pipeline-lessons.md`
- **Process, gates, budget philosophy:** `docs/tree-leaf-pipeline-brief.md`
- **Which skeletons exist + the hard laws:** `docs/tree_skeleton_plan.md` §1b
- **Runtime tier/impostor spec:** `docs/trees.md`
- **Reference-first modelling discipline:** `docs/vegetation_modeling.md`

The two worked, shipped examples to copy from are **`london_plane`** (tip-bearing) and
**`oak`** (along-branch) in `scripts/generate_trees_mtree.py`. There is also a clean,
comment-only **`_TEMPLATE`** entry at the top of the `SPECIES` dict — copy that, not a
real species (a real entry carries species-specific history you don't want).

---

## 0. The mental model (internalise this before touching a lever)

1. **A skeleton earns a new GLB only by a distinct silhouette at 15–150 m.** Bark, leaf
   card, fall colour, crown density, bloom, clump-vs-single are all *parameters* on a
   shared skeleton. Most species are a fold onto an existing skeleton, not a new model.
2. **Leaves are real-photo CLUSTER CARDS at every tier** (`_s`/`_m`/`_l`). Not procedural
   Mtree leaves, not structural single-leaf meshes — both were tried and rejected on
   render budget (a structural leaf canopy = ~460 M tris/frame in the Ramble, impossible
   on a 3060 Ti). Leaf *shape* only resolves within ~30 m; past that a leaf is a coloured
   fleck. So identity rides the card's **alpha silhouette + colour**, which a 2-triangle
   card carries identically to a 1000-triangle mesh.
3. **The card is a 2–4-leaf twig sprig** (leaves + their stems + a joining twig), not a
   bare leaf. The card's twig *is* the terminal ramification — which is why the skeleton
   stops at secondary branches (see §4).
4. **Coherence is the law:** every leaf connects to the trunk through real branches. No
   floaters, no box-fill, no clusters on sub-visible twigs. Validate it, don't eyeball it.

---

## 1. The hard build laws (Chris, absolute — override everything else)

Canonical text in `docs/tree_skeleton_plan.md` §1b. In brief:

1. **Leaf card first (Gate 1), then the `_s` model first;** `_m`/`_l` derive from it.
2. **Card = a real twig sprig of 2–4 leaves + stems + a joining twig.** Never a bare leaf.
3. **Branch diameter floor ≥ 0.05 m on every tier** (`min_twig_diameter`, a scalar).
4. **Skeleton orders = trunk + primary + secondary only.** The card's twig is the visual
   tertiary. (A *sub-visible* thin depth-3 twig order — radius ≤ card_rule_max_radius,
   fully masked by its own cards — is allowed only to fill crown volume; heavy tertiary
   *forks* are banned. See the depth note in §4.)
5. **Cards attach in real-data patterns:** tip-concentrated (plane, cherry, birch) vs
   along-branch (oak, elm). Per-species, never uniform.
6. **Trunk apex never bare** (apex-band force-keep) unless the species data says otherwise.
7. **Every leaf connects to the trunk through branches** (`check_foliage_connectivity.py`)
   unless the data says otherwise.
8. **Clear the cache + reimport after EVERY Blender regen** (§6). A stale `.scn`/`.res`
   silently serves the OLD model — this has cost whole sessions.

---

## 2. Prerequisites (before any geometry)

- **Reference folder:** `reference_photos/<species>/`. Study it per `docs/vegetation_modeling.md`.
  Match each reference to what it can answer: model/wireframe/schematic refs are authoritative
  for **structure only** (how trunk→branch→twig divides, crown habit); trust real **photographs**
  + botanical authorities (FNA/USDA/FEIS) for **leaf shape, colour, translucency**. Do NOT trust
  the internal `docs/botany` BRIEFs for morphology.
- **A dossier** (`references/leaves/<species>.md`) with the §3 measurements cited, per the brief.
- **Chris's hand-built leaf sprig.** Chris composites the 2–4-leaf sprig himself in GIMP on a
  solid green background and saves it into the species reference folder. You convert it — you do
  not draw the leaf. (You *may* prepare the parts: extract clean flat leaves + a twig to a
  transparent PNG for him to assemble, e.g. `scripts/vegetation/extract_oak_parts.py`.)

---

## 3. The per-species MEASURE list (what you CANNOT copy)

Everything else is a copyable lever. These you must derive from references, per species,
or you will re-run the oak "floating pieces" / "sparse crown" loops:

| Measure | How | Feeds |
|---|---|---|
| **Crown silhouette** (aspect W/H, widest point, excurrent vs decurrent) | measure the 3-up size refs | skeleton levers (§4) |
| **Foliage pattern** (tip-bearing vs along-branch) | species habit from refs | `card_rule_depth_keep` |
| **Leaf blade proportions** (L:W, lobe/sinus, teeth) | flat leaf photo | the sprig Chris builds |
| **Fall colour** | real autumn photos | `FALL_COLORS` (shader-side) |
| **Card stem anchor** (UV of the drawn stem base in the cluster PNG) | open the built `<sp>_cluster.png`, read the pixel where the stem meets the twig, divide by texture size | `card_stem_anchor` — **wrong value = leaves float off the twig** |
| **Height range per tier** | census DBH distribution (`tree_builder.gd` HEIGHT_RANGES / TIER_BOUNDS) | `tiers` target_h / height_range |

---

## 4. The lever reference (annotated — default vs per-species)

Full param semantics: read the addon socket tooltips (`addons/.../leaf_shape_node.py`
`PARAM_DESCRIPTIONS`), never stale code comments. The load-bearing, non-obvious levers:

**Skeleton (Mtree)**
- `crown_base_size` — **default 0.0 is a narrow-cone clamp** (the hidden reason crowns read
  as poles). Set ~0.55–0.75 for a broad crown. *Caveat (oak 2026-06-24): on some configs this
  and up_attraction/branch_angle proved ~no-op on measured crown width — Mtree's C++ crown/
  gravity core clamps it. If a crown stays too narrow after setting these, that's the cause.*
- `trunk_randomness` ~0.18 = clean stout bole; higher = S-curve lean (hidden under leaves anyway).
- `up_attraction` — leader strength: high = excurrent (central leader, pin oak/conifer/tulip);
  low ~0.35–0.40 = decurrent rounded crown (red oak, plane).
- `branch_end` ~0.94–0.97 so branches reach and round the apex (clads the bare leader).
- **Ramification depth:** cap at secondary with `cap_skeleton_depth(obj, max_depth)` via the
  tier's `skeleton_max_depth`. **Long limbs (`_l`, 30 m) ramify to depth ~11 even at low
  split-prob** — split-probability CANNOT bound depth at scale; the depth cap can. Use
  `max_depth: 2` for the geometry ban, but allow a sub-visible depth-3 twig order (masked by
  cards) if the crown reads see-through (this is what fills volume — *more secondaries + cards*,
  not deeper forks).
- **`variant_spans` outrank `skeleton_overrides` outrank scalars** — a tier needs its OWN
  `variant_spans` or the species-level spans clobber it (precedence trap).

**Foliage placement (the card rule)**
- `foliage_distribute: True` + **`distribute_tiers: []`** — `[]` is critical; the default
  `["s","m","l"]` activates the inactive 3D-leaf path instead of cards.
- `card_leaf_rule: True` — ≥1 tip-most cluster guaranteed per branch (no bare ends).
- `cards_per_cluster: 1` — the card already IS a sprig; >1 rebuilds a "tight green ball".
- `card_rule_max_radius` ~0.05 — thin twigs only.
- `card_rule_depth_keep` — **the per-species foliage-pattern lever.** `{1:0.05, 2:0.60, 3:1.0}`
  = tip-biased (rare on primary, full on the terminal twig order: plane/cherry/birch). For
  along-branch species (oak/elm) raise the low-order keeps so foliage spreads down the limb.
  Depth (`hierarchy_depth`), NOT radius, is the discriminator — the min-twig floor clamps every
  branch to the same radius, so radius can't tell a primary from a twig.
- `card_rule_apex_band` ~0.18 — force-clad the top 18% so the growing apex is never bare.
- `card_stem_anchor` — **(u,v) of the sprig's drawn stem base** in the cluster PNG (§3). Absent =
  legacy centred card (leaves float if the sprig isn't centred). Measure it; don't guess.
- `card_size_floor` ~0.42 — keeps a small `_s` crown from going see-through, gate-safe.
- `tier_fraction` `{l:1.0, m:~0.40, s:~0.24}` — card budget per tier. Bump `s` to fill a young
  crown *without enlarging leaves*.

**Leaf card texture**
- `leaf_real_texture: "textures/leaves/<sp>_cluster.png"` — built by a per-species
  `make_<sp>_cluster_from_photo.py` (chroma-keys Chris's green-bg sprig → RGBA + a `_fall` variant).
- Fall HUE is **shader-side** (`FALL_COLORS` in the leaf shader), not baked — one card can serve a
  whole group (e.g. oak Lobatae serves red/scarlet/pin) with different fall hues.

**Min twig diameter (law 3)**
- `min_twig_diameter: 0.05` — **a SCALAR** so every tier gets it. A dict like `{"s":0.04}` floors
  only `_s` and lets `_m`/`_l` fall through to the `MIN_TWIG_DIAMETER` table (the exact oak bug).
  Every build's stdout must self-report the floor used + verts inflated.

**LOD / perf**
- **LOD chain = lod0 → impostor. There is NO lod1 mid tier** (removed 2026-07-03, 5b2bed8 —
  stale derived lod1s made impostors change shape; do NOT generate `_lod1`). Handoff is
  40–80 m (`_mesh_fade_end` 80, dither band [40, 80]), density-modulated per tree when
  `--density-lod` is on (openness baked in cd.b); impostors run to 800 m. `docs/trees.md` §1.
- Screen-size LOD (`_lod_scale` in `tree_builder.gd`) — handoffs scale with tree height so all
  trees switch at the same on-screen size.
- One impostor atlas per species-tier (median variant), shared by all variants, **baked from lod0**.
- Per-tree position-hash variant selection (local diversity, stable across the handoff).
- Trees never cast per-leaf shadows — the **shadow proxy** (trunk cylinder + crown hull,
  `SHADOWS_ONLY`) casts instead; per-leaf casting was the deep-forest perf killer (rendering.md §3g).
- `perf_gate.sh` on a real GPU before commit (llvmpipe software GL is unrepresentative; note
  `xvfb-run -a` DOES get the real NVIDIA card under Vulkan — verified 2026-07-02).

---

## 5. The build sequence (do these in order; STOP at each gate)

**Gate 1 comes before any skeleton.** Perfect the leaf card first.

1. **Card texture** — `python3 scripts/vegetation/make_<sp>_cluster_from_photo.py`
   → `textures/leaves/<sp>_cluster.png` + `_fall`. **▣ GATE 1: Chris reviews the leaf.** Stop.
2. **Copy `_TEMPLATE`** in `scripts/generate_trees_mtree.py` to a new `<sp>` entry. Set the §3
   measured values + the §4 levers. Set `distribute_tiers: []`, `min_twig_diameter: 0.05` (scalar),
   `card_stem_anchor` (measured), `card_rule_depth_keep` (per foliage pattern), `n_variants`.
3. **Build `_s` first, then `_m`, `_l`** — ONE tier per invocation, **no shell `for`-loops**
   (headless Blender hangs on shutdown; a loop stalls the whole sweep silently):
   `blender4 --background --python scripts/generate_trees_mtree.py -- --species <sp> --tier s`
   (then `m`, then `l` as separate commands; confirm each process EXITS).
4. ~~LODs~~ — **SKIP. No `_lod1` mid tier exists** (removed 2026-07-03; chain is lod0 →
   impostor). Do not run `generate_tree_lods.py`; a derived lod1 goes stale the moment
   lod0 evolves and poisons the impostor bake.
5. **Leaf DDS** (runtime prefers the DDS over the GLB-embedded PNG):
   `python3 scripts/generate_leaf_dds.py --species <sp>`.
6. **Import + clear cache** (law 8) — or just run `scripts/eval_capture.sh <sp>`, which does both:
   `godot --headless --import` then delete `cache/trees/<sp>_*.res` + `<sp>.cfg`.
7. **Impostor bake:** `"<godot>" --path . -- --bake-impostors=<sp>` then `godot --headless --import`
   (the new atlas PNGs need one import pass). Bakes **from lod0**. ONE Godot process per
   species — an all-species bake progressively hangs (GPU resource leak); flaky species
   (london_plane, magnolia) may hit the 180 s timeout, just retry. Details in `docs/trees.md` §2.
8. **Eval:** `garden` (interactive 3×3 tier×size grid) or `scripts/eval_capture.sh <sp>` (headless
   stills). Judge the lod0→impostor handoff and the natural-density stand, not a hero render.
   **▣ GATE 2: Chris reviews the tree.** Stop. Do not start the next species.
9. **Record lessons** in `docs/tree-pipeline-lessons.md`; promote anything *systematic* into this
   playbook or the `_TEMPLATE`, so species #20 is easier than species #2.

**Verification rule:** if before/after renders look identical, the asset on disk is NOT what's
rendering — you skipped step 6. Confirm the `.scn` mtime changed after `--import` and the `.res`
size changed. Never trust a regen you haven't seen reload.

---

## 6. Live traps (each one cost a wrong-diagnosis loop — obey, don't re-derive)

- **Stale cache/`.scn`** — the #1 time sink. Reimport + clear cache after every regen (law 8, step 6).
- **No batch Blender loops** — one process per variant; each hangs on shutdown and blocks the next.
- **`distribute_tiers` must be `[]`** for the card path — the default activates the dead 3D path.
- **`min_twig_diameter` is a scalar**, not a per-tier dict, or `_m`/`_l` silently under-floor.
- **`card_stem_anchor` = the DRAWN stem base**, measured from the PNG, not the texture corner —
  a wrong anchor floats every leaf ~0.3 m off the twig ("disjointed pieces floating").
- **Depth cap, not split-prob**, bounds ramification on long limbs; a see-through crown wants a
  sub-visible depth-3 twig order + more secondaries, NOT deeper forks or bigger leaves.
- **Crown width can be clamped by Mtree's core** — if `crown_base_size`/`up_attraction`/
  `branch_angle` all no-op on measured width, that's the cause (oak finding); the *foliated* crown
  reads wider than the skeleton bbox (cards extend past tips).
- **`check_foliage_connectivity.py` is necessary but not sufficient** — it can false-pass a cluster
  on a thin/near-invisible twig. Combine it with the min-twig floor and a look at the actual render.
- **Eval yaw `0.0` silently becomes 30°** — pass `0.01` for dead-north.
- **Headless captures need `--upscale=bilinear:1.0`** (FSR2 hangs `get_image()` under xvfb).

---

## 7. Definition of done

- **Leaf** — passes self-critique vs cited reference across seasonal states, is a proper twig
  sprig, and cleared Gate 1.
- **Tree** — full LOD chain (**lod0 + impostor**, every size; no mid tier since 2026-07-03)
  holds instanced across LOD transitions under AgX at gameplay distance, perf-gated on a real GPU,
  and cleared Gate 2.
- **Species** — tree done + lessons recorded + any systematic lesson folded back into this playbook.
</content>
</invoke>
