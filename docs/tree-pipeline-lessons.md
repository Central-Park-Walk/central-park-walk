# Tree & Leaf Pipeline — Lessons Learned

> **To BUILD a tree, read `docs/tree-pipeline-playbook.md` — the single live runbook.**
> This file is the *why* (method + war-stories); the playbook is the *what to do*.

Living document, appended after every species (per `tree-leaf-pipeline-brief.md`).
Promote *systematic* lessons into the playbook, the attach contract, or the skill.

---

## ⮕ CURRENT SETTLED DIRECTION (2026-06-22) — read this first

Tree leaves = **REAL-PHOTO CLUSTER CARDS at every tier.** Not procedural 3D leaf
geometry (Mtree superformula), not structural single-leaf meshes, not hand-rolled PIL
outlines — all three were tried and rejected (the dated lessons below are kept as the
historical record of *why*). The chain, as shipped for london_plane:

1. **Card texture** = a real leaf photo cut to RGBA. For london_plane this is Chris's
   own chroma-keyed **4-leaf twig sprig** (`reference_photos/london planetree/london-plane-tree-leaf.jpg`
   → `scripts/vegetation/make_leaf_cluster_from_photo.py` → `textures/leaves/london_plane_cluster.png`,
   plus an auto fall variant). This REPLACED the procedurally-scattered fan in
   `make_leaf_cluster_texture.py`, which is now superseded (both write the same output
   file; the hand-built card is the one that ships). The single-leaf cutout
   (`cut_leaf_texture.py` / `london_plane_real_albedo.png`) survives only as a *source*.
2. **Placement** = continuous-cladding branch-walk + the deterministic per-branch
   **leaf rule** (`_card_placements_per_branch` in `scripts/generate_trees_mtree.py`,
   `card_leaf_rule: True`): ≥1 tip-most cluster guaranteed on every branch so foliage
   reaches the ends. `cards_per_cluster: 1` — Chris's card already IS a 4-leaf sprig, so
   stacking copies just remade a "tight green ball".
3. **Generation** = `scripts/generate_trees_mtree.py` (NOT the old standalone
   `make_london_plane.py`), with `distribute_tiers: []` — the 3D distribute path is
   preserved in code but INACTIVE.
4. **Why cards, not geometry — render budget.** ~200–250 near-tier trees load at once in
   the Ramble (lod0 ≤ 80 m); a 664-vert structural leaf ⇒ ~460 M tris/frame, impossible
   on a 3060 Ti. Leaf SHAPE only resolves within ~30 m anyway, so a card's alpha
   silhouette distinguishes species, and COLOR comes from the shader's per-species
   `SUMMER_COLORS`/`FALL_COLORS`.
5. **Mtree's `LeafShapeGenerator` is at most a secondary VARIATION tool** whose output
   would BAKE to a card atlas — never the primary realism path. Used to emit visible 3D
   leaf geometry it produced asterisks/stars (its veins are a per-vertex `vein_distance`
   shader attribute, not geometry) and was stopped.

Memory: [[project-leaf-pipeline-mtree]], [[project-london-plane-sapling-sprig]],
[[reference_how_to_make_trees]] §0aa. **Where a dated lesson below conflicts with this
banner, the banner wins.**

---

## Cross-cutting lessons (not species-specific)

- **DERIVED TIERS ROT — bake from the tier you ship.** (2026-07-03, 5b2bed8/bc26b7c) The
  `_lod1` mid meshes were decimations of an *old* lod0; as lod0 evolved through the leaf-card
  redesign, nobody regenerated them. Impostors baked from those stale lod1s changed shape vs
  lod0 across octahedral angles ("l keeps changing shape") — a bug that read as an impostor
  defect but was a *pipeline provenance* defect. Resolution: the lod1 tier was REMOVED
  outright (chain = lod0 → impostor, impostors bake from lod0). General law: any derived
  asset (LOD, impostor, proxy) must either regenerate automatically with its source or not
  exist. The "far handoff where it's noticeable" job lod1 did is covered by the
  density-modulated handoff (`--density-lod`, openness baked per tree in cd.b at placement).
- **CALIBRATE CLASSIFIER THRESHOLDS TO THE MEASURED DISTRIBUTION, not intuition.**
  (2026-07-03, 0f1f42f) Density-LOD's "dense" threshold was 9 neighbours within 18 m — but
  the placed-tree histogram has mean 4.7, so woods trees classed "open" and the feature
  silently did nothing where it mattered (mean openness 0.66, zero fps movement). The
  feature *looked* on; only the histogram exposed the mis-tune. Recalibrated N_OPEN 2 /
  N_DENSE 7 → 431 fully dense. When a data-driven lever shows no effect, print the input
  distribution before touching the mechanism.
- **PER-LEAF SHADOW CASTING is the deep-forest perf killer — proxies cast, leaves never do.**
  (2026-07-02, rendering.md §3g) 37.7 M shadow-tris in the Ramble with per-leaf casting;
  the ≤300-tri trunk+hull proxy (SHADOWS_ONLY, alpha-test dapple) took it to 1.76 M and
  15→27 fps. Any new species inherits this: leaf material never casts.
- **THIN THE CROWN IN THE BAKE, NOT THE LIVE MESH — and drop cards EVENLY, not randomly.**
  (2026-07-03, 46f03b8 revert + 32e8a47) Runtime card-drop thinning of `_l` broke the
  mesh↔impostor crossfade (region-fade). And a random per-card drop in the bake clumped
  into an "oddly decimated" far crown; a spatially EVEN per-card keep (0.6) reads as
  uniform see-through density while preserving silhouette.

- **⮕ HARD BUILD LAWS (Chris, 2026-06-22) live in `docs/tree_skeleton_plan.md` §1b and are
  ABSOLUTE — they override anything below.** In brief: leaf card first then the small model;
  card = a 2–4-leaf twig sprig (leaves + stems + twig); branch diameter floor ≥ 0.05;
  skeleton orders = trunk + primary + secondary ONLY (no tertiary — `cap_skeleton_depth`
  `max_depth = 2`); cards attach to branches in real-data patterns (tip-concentrated vs
  along-branch); apex never bare unless the data says so; every leaf connects to the trunk
  through branches unless the data says so; **clear the tree cache + reimport after every
  Blender redesign.**

- **RAMIFICATION DEPTH can't be bounded by split-probability at scale — prune by the `hierarchy_depth` attribute instead.** (2026-06-22 s4, london_plane m/l) Mtree forks per branch-SEGMENT, so ramification depth grows ~exponentially with limb length. MEASURED: a 22m tree (`_m`, ~10.6m limbs) caps cleanly at hierarchy_depth ~3 with `sub_split_prob` 0.22; a 30m tree (`_l`, ~16.5m limbs) still ramifies to **depth 11** even at `sub_split_prob` 0.10 — ~9.5k leaf clusters, 53MB GLB, essentially unchanged from no cap. The fix (the user's "stem/twig redundancy" insight — the leaf CARD is a twig sprig that already paints its own terminal twig, so geometry past it is redundant AND pokes out bare past the cards) is `cap_skeleton_depth(obj, max_depth)` in `generate_trees_mtree.py`: after meshing, delete verts whose raw-integer `hierarchy_depth` attribute exceeds `max_depth`; card placement then runs on the capped mesh so cards sit at the true terminal tips. Opt-in per tier via `skeleton_max_depth` in the tier's `skeleton_overrides`. **[UPDATED 2026-06-22 — hard law 4: the cap TARGET is now SECONDARY (`max_depth = 2`) for EVERY tier, not tertiary. Skeletons carry trunk + primary + secondary only; the leaf-card twig is the visual tertiary. The depth-pruning MECHANISM here stands; only the value changes — `_l` is 2, not 4, and short tiers are capped to 2 as well rather than relying on split-prob.]** Height-independent, so it's the reusable lever for every big-tier tree. NOTE the **same trap is hidden in cluster COUNT**: the per-branch leaf RULE places ≥1 card per eligible branch, so over-ramification silently inflates the cluster count (and GPU cost) as much as the geometry — capping depth fixes both at once.
- **THE 5 mm `remove_doubles` WELD SILENTLY CULLS A SMALL TREE'S FINE TWIGS — a scale-dependent trap that hits every S-tier / sapling build.** (2026-07-04, london_plane s/m skeleton density fix) `clean_degenerate_geometry` runs `bmesh.ops.remove_doubles(dist=0.005)` — a **5 mm ABSOLUTE weld** — to fuse Mtree's separate branch tubes and kill zero-radius tip slivers. But a twig's radial cross-section ring (`radial_pts` points around circumference 2πr) has point spacing < 5 mm once radius r ⪅ 9 mm, so the WHOLE ring collapses to a line → the twig becomes degenerate → deleted. This scales with ABSOLUTE size, so it guts the smallest tier: MEASURED on london_plane, the 9 m `_s` build lost **~75–80 % of raw Mtree verts** here (raw 12,785 → 3,238 after cleanup), while the 24 m `_m` lost only ~34 %. **Consequence: cranking `sub_density` did NOTHING for the s crown** — every added twig was welded away before it could render, so the sapling stayed a sparse whip no matter the density lever (a full wrong-diagnosis loop until the per-stage vert count exposed it). **The order of operations hides it:** production runs `clean_degenerate_geometry` (culls thin twigs) BEFORE `enforce_min_twig_diameter` (thickens survivors to the 4 cm floor), so the floor never sees the culled twigs — it only thickens the few that survived. **THE LEVER: raise `sub_start_radius` (born twig radius, relative-to-parent) so twigs are ≥ ~9 mm at birth and survive the weld** — the min-twig floor then thickens all survivors to the uniform floor anyway, so a fatter birth radius costs nothing in final thickness; it only keeps more twigs alive. Measured: `sub_start_radius` 0.25→0.7 lifted s survival 2,215→4,043 verts. **CHECK THIS for any new thin-twig species (every sapling / `_s`, birch, willow whips): if the density levers don't move the crown, print the per-stage vert count (raw mesh → after clean_degenerate → after min-twig) BEFORE touching the density params — the twigs are dying at the weld, not failing to generate.** (Alternative fixes not taken, to keep the change to a single skeleton param: a per-tier `merge_dist` threaded into `clean_degenerate_geometry`, or reordering min-twig-floor before clean — both touch the shared foliage pipeline / every species.)
- **BUILD WORKFLOW: ONE Blender variant/candidate per invocation — NO batch loops.** (user, 2026-06-22) Headless Blender on this box has a strong tendency to **hang on shutdown** (the EEVEE_NEXT GL context does not release; the process sits alive at ~0% CPU forever *after* the work is done and the file is written). In a shell `for`-loop that spawns one `blender4 …` per candidate, the first hang blocks every subsequent run — a whole sweep silently stalls (cost ~48 min unnoticed once). **RULE: run skeleton-explore / regen / lod / bake one variant at a time, as separate invocations, and confirm each process actually EXITED before starting the next.** Mitigations when scripting a single run: end the script with `sys.stdout.flush(); os._exit(0)` after writing output (force-exit past the shutdown hang — added to `explore_skeleton.py`), and/or wrap the call in `timeout 150 blender4 …`. (A full `generate_trees_mtree.py --tier X` run that meshes all 7 variants inside ONE process is fine — it exits cleanly; the rule is about not chaining multiple Blender *processes* in a loop.)
- **REALISM PATH = real-leaf alpha-cutout CARDS, not procedural 3D geometry.** (2026-06-20, hard lesson) Per the deep-research report (`docs/research-game-ready-leaves.md` §1–2): industry-standard realistic leaves are alpha cards textured from a **photographed/scanned real leaf on white**, or CC0 leaf atlases (ambientCG). SpeedTree's primary leaf representation is cards with 1-bit alpha. A flat reference photo like `IMG_4070` *is* a finished leaf texture — cut it to RGBA (`scripts/vegetation/cut_leaf_texture.py`) and you have a real, correctly-veined, correctly-toothed, species-distinct leaf in one pass. **Do this before reaching for any generator.** Trying to procedurally generate the leaf shape with Mtree's superformula produced sweetgum-stars and burned a session. See [[feedback_do_the_research]] — we researched the method then ignored it. **Refinement (see banner):** "cards" finalized as real-photo **CLUSTER** cards (a 4-leaf twig sprig), not single-leaf cards; `cut_leaf_texture.py` is now only the *source* that feeds the cluster card.
- **Mtree veins are a `vein_distance` per-vertex attribute, not geometry.** They drive a shader / bake into the card texture. A plain BSDF on the raw mesh shows only `vein_displacement` ridges → reads as an "asterisk". If Mtree is used at all, it is a secondary VARIATION tool whose output bakes to the leaf atlas.


- **[SUPERSEDED as a realism path — see banner. Mtree is at most a secondary VARIATION tool whose output bakes to a card; it is NOT used to emit visible 3D leaf geometry, which produced asterisks. Kept for the API record only.]** **Use Mtree's `LeafShapeGenerator`, not hand-rolled outlines.** (2026-06-20) The project spent effort on a PIL parametric outline + scattered-card leaf system while Mtree already shipped a full procedural leaf creator: superformula contour (`m,a,b,n1,n2,n3,aspect_ratio`), `margin_type` + `tooth_count/depth/sharpness`, space-colonization **venation as real 3D geometry**, and **deformation** (`midrib_curvature, cross_curvature, vein_displacement, edge_curl`), with `seed`/`asymmetry_seed`. It is fully headless-scriptable:
  ```python
  gen = m_tree.LeafShapeGenerator()
  apply_preset_to_generator(gen, "MAPLE")   # or set params directly
  gen.seed = ...; gen.asymmetry_seed = ...
  cpp = gen.generate(); create_leaf_mesh_from_cpp(mesh, cpp)
  ```
  Because venation is real geometry, the painted-vein texture is largely unnecessary. Presets present: OAK, MAPLE, BIRCH, WILLOW, PINE.
  **Verified against installed m_tree 5.5.0** (2026-06-20, local source-check): `LeafShapeGenerator` (+`triangulate`/`compute_uvs`), all five presets, and the `mt_LeafShapeNode` node are all real. A deep-research run that "refuted" these was reading the stale **v4.x GitHub master** — web repo state ≠ installed binary; trust the `.so` on disk. **Unused capability also in the binary:** `LeafLODGenerator.generate_card` + `generate_billboard_cloud` (Mtree can emit leaf cards / billboard clouds itself — candidate for mid/far LOD; see `docs/research-game-ready-leaves.md`).
- **Best tool over improvisation; acquire the tool if missing.** General heuristic now in the brief addenda. Check the framework/addon before writing generation code.
- **Dossier first, then a blindspot audit.** Each species starts with a written dossier (`references/leaves/<species>.md`); then explicitly hunt blindspots / incomplete / contradictory data and resolve before modeling. Sources frequently disagree (see plane below) — flag, don't average blindly.
- **Read the addon's socket tooltips for parameter semantics — don't trust old code comments.** (2026-06-20) `leaf_shape_node.py` `PARAM_DESCRIPTIONS` is authoritative: `n1`=Roundness (LOW=puffy/broad, HIGH=thin/spiky), `n2`/`n3`=Lobe Shape (LOW=bulging/broad, HIGH=pinched/angular), `m`=lobe count, `aspect_ratio`=W:H. A stale comment in `build_plane_leaf.py` had `n1` inverted and cost several wasted sweeps producing sweetgum-stars. For a broad-lobed palmate leaf (plane/maple family): low-ish `n1`, moderate `n2`, lobes from the CONTOUR, and `DENTATE` (not `LOBED`) margin for the teeth.
- **Beware tracing the wrong reference.** (2026-06-20) An earlier traced "plane" outline was actually maple-like (deep narrow lobes) and dragged the model toward maple for several iterations. Trust flat herbarium-style photos + cited morphology over a trace of unknown provenance.

## Archetype: palmate lobed

- Members so far: maple (deep, rounded sinuses), **London plane** (broad, shallow-to-moderate, angular sinuses, wider-than-tall), sweetgum (star-sharp). Validate the base against the divergent pair (plane ↔ sweetgum) before mass use.

---

## Per-species

### London planetree (*Platanus × acerifolia*) — DONE (shipped as real-photo cluster cards)
> **The leaf-BUILD bullet below documents the abandoned Mtree-superformula attempt
> ("Gate-1 candidate"). That path was REJECTED.** The shipped leaf is the real-photo
> cluster card in the banner at the top of this file (`london_plane_cluster.png`,
> `card_leaf_rule`, `cards_per_cluster: 1`, `distribute_tiers: []`). The botany/dossier
> notes (proportions, sinus depth, fall color, distinctiveness-vs-trio) below remain
> valid; only the geometry-source conclusion is superseded.
- Dossier: `references/leaves/london_plane.md`. Consensus target (deep-research, adversarially verified): 5 lobes, **moderately-deep angular sinuses (~1/3 of blade**, deeper than sycamore / shallower than Oriental plane), **pointed-acuminate tips**, coarse sparse forward teeth, **broad blade ~as wide as long to slightly wider (L/W ≈ 0.8–1.0)**, dull yellow-brown fall.
- **Corrections to earlier single-source claims:** proportion is NOT W/L≈1.4 (refuted 1–2); sinuses are NOT "shallow" — they're moderate (deeper than sycamore). NC State's "rounded lobes" refuted 0–3; trust NC State only on sinus-depth-vs-sycamore.
- **Lesson — single secondary sources mislead:** the whole shallow-vs-deep / rounded-vs-pointed muddle dissolved only under multi-source credibility weighting; the hybrid's leaf is *intrinsically polymorphic*, so any one photo/source is a sample, not the truth.
- **IMG_4070 validated** as representative of the hybrid (high confidence) → usable as a Gate-1 visual cross-check, not as sole authority.
- Open: CP prominence/locations (verify in `convert_to_godot.py`); precise numeric L:W / tooth count (sources qualitative only — not build-blocking).
- **Leaf build (2026-06-20) — SOLVED the "pale green star". Root cause: the prior `build_plane_leaf.py` drove the superformula toward a SWEETGUM star (the species plane must be distinct from). Two compounding errors, both from trusting old code comments over the addon's own tooltips:**
  - **`n1` (Roundness): LOW = puffy/broad, HIGH = thin/spiky.** The old comment had it backwards (claimed n1<1 = star). Plane wants **n1 ≈ 0.85** (broad).
  - **`n2`/`n3` (Lobe Shape): LOW = bulging/broad, HIGH = pinched/angular.** Old build used n2=3–4.5 (spiky); plane wants **n2 ≈ 2.7** (broad moderate lobes). n2≈1.8 over-bulges into a toothed disc with no 5-lobe read; n2≈2.9 starts to deepen toward star. The 5-lobe palmate read lives in **n2 ≈ 2.4–2.9**.
  - **Margin must be `DENTATE`, not `LOBED`, for the teeth.** `LOBED` barely cuts at tooth_depth<0.45 (gave round blobs) AND consumes the single margin pass so there's no budget for teeth. With lobes coming from the CONTOUR (m=5 + n1/n2), `DENTATE` is free to supply the **coarse sparse forward teeth** — `tooth_count≈9, tooth_depth≈0.18, sharpness≈0.88` reads as coarse (count 12 / depth 0.10 = too-fine scalloping).
  - **General lesson (folded up top):** read the installed addon's socket tooltips for parameter semantics; do NOT trust prior code comments — they had `n1` inverted and cost several wasted sweeps. After 2 star-shaped sweeps the diagnosis (not the params) was wrong.
  - **Gate-1 candidate params:** `m=5, n1=0.85, n2=n3=2.7, aspect_ratio=1.08, DENTATE tooth_count=9 tooth_depth=0.18 tooth_sharpness=0.88`, venation Open, midrib_curvature=0.06 cross_curvature=0.10 vein_displacement=0.22 edge_curl=0.04. ~391v/702f. Measured dims W/L≈1.05 (matches consensus). Renders: `notes/london_plane_leaf/GATE1_v2_top.png` + `_3q.png`. **Awaiting Gate-1 review.**
  - **Distinctiveness confirmed vs the trio:** plane = broad lobes + angular sinuses + coarse teeth; maple = rounded (U) sinuses + vivid red/orange fall (new ref `reference_photos/Red Maple/fa29...jpg`); sweetgum = deep narrow star + fine serration + vivid crimson fall. Plane's drab yellow-brown fall is the autumn differentiator (material/season stage, not geometry).
- (Tree assembly, Gate 2, polycounts/VRAM — to be filled after Gate 1.)
