# LEDGER — cpw / tree-sculptor

## WORK_PACKAGE ts-2026-07-17-sculptor-v1
- **thread:** tree-sculptor
- **classification:** MAINTENANCE + new capability (workstation)
- **hypothesis:** A visible Blender bridge + Bézier strand authority can replace Mtree/grower authorship and compile through the existing skinner/card/GLB path.
- **changed paths:**
  - `scripts/tree_sculpt/*` (bridge, ctl, core, review, create, compile, gates)
  - `docs/tree_sculptor.md`
  - `models/tree_sources/london_plane.blend` (+ `.gdignore`)
  - `models/trees/london_plane_sculpt_*.glb`
  - `tmp/.gdignore`, `tmp/tree_sculpt/*`
  - `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **observed verification:**
  - Live bridge: revision-safe edit/undo/checkpoint/compile ACK ok with single Blender process.
  - Mature bark_connected_components=1 after junction weld.
  - Compile all five stages ~5s after card-cloud optimization (was ~10 min).
  - Contact sheets + reference overlay written under `tmp/tree_sculpt/`.
  - Dense-stand gate (240 lod0 Multimesh, shadows on, no impostor): 14→15 fps after thinning sprays 8→3; tris/mature 28724→14324.
  - Full-park `perf_gate.sh` asset-swap run: Auto-review blocked; not executed. Production GLBs left untouched.
- **deliverable:** sculptor workstation + first authored London-plane sculptures awaiting Chris appearance verdict.
- **git:** uncommitted
- **status:** awaiting_user_verdict

## Staged lessons
- Appearance gate first: sparse-card black starbursts were caught only by looking at the shipped foliated render.
- Card overdraw, not only triangle count, bounds woodland FPS; densify by secondaries, not spray multiplication.
- Blender undo rewrites scene custom props — keep revision counters outside the .blend undo stack.
- Chris's GIMP sprig already IS the foliage unit — `cards_per_cluster>1` rebuilds a green ball that reads as sculpted-in foliage.
- Junction weld must be stem_id-aware (cross-strand only). Blind `remove_doubles` at a distance ≥ tip diameter collapses tube rings into ribbons and invents a fake low tri-count.

## VERDICT on ts-2026-07-17-sculptor-v1
- **from:** Chris
- **said:** Skeletons look promising; leaf cards look sculpted into the model; cheaper FPS to sculpt skeleton bare and add GIMP leaf cards.
- **status:** accepted_direction — continue with bare-authority + card attach

## WORK_PACKAGE ts-2026-07-17-bare-cards
- **thread:** tree-sculptor
- **classification:** REPRODUCED_DEFECT
- **worklist:** TS-1 (redirect), TS-2 (method change)
- **hypothesis:** Stacked spray×cross cards (3×2) read as sculpted green volume; one GIMP sprig per emitter + bare review authority will match the FPS-cheap production pattern.
- **changed paths:**
  - `scripts/tree_sculpt/sculpt_core.py` (cards_per_cluster=1, twig-aligned sprig, foliage= flag)
  - `scripts/tree_sculpt/review_rig.py` (bare + foliated dual contact sheets)
  - `scripts/tree_sculpt/live_bridge.py` (foliage arg)
  - `docs/tree_sculptor.md` (contract)
  - `tmp/tree_sculpt/london_plane_mature_{bare_,}review.png` + manifests/GLB
  - `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **observed verification:**
  - Mature bare: 5684 tris, 0 leaf faces, foliage=false → `london_plane_mature_bare_review.png`
  - Mature foliated: 6694 tris, 505 leaf faces, card_anchors=card_sprays=505 (1:1) → `london_plane_mature_review.png`
  - Prior dense path was ~14324 tris after spray thin; now +1010 tris for cards.
- **deliverable:** bare-skeleton sculpt authority + GIMP single-sprig card attach; dual mature reviews for Chris.
- **git:** uncommitted
- **status:** awaiting_user_verdict



## WORK_PACKAGE `tree-sculptor-W-20260717-02` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`, `TS-2`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** Stacked spray×cross cards (3×2) read as sculpted green volume; one GIMP sprig per emitter plus bare-skeleton review authority matches the FPS-cheap production pattern.
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `scripts/tree_sculpt/review_rig.py`, `scripts/tree_sculpt/live_bridge.py`, `docs/tree_sculptor.md`, `tmp/tree_sculpt/london_plane_mature_bare_review.png`, `tmp/tree_sculpt/london_plane_mature_review.png`, `tmp/tree_sculpt/review_mature/`, `tmp/tree_sculpt/review_mature_bare/`, `models/trees/london_plane_sculpt_mature.glb`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Recompiled mature from existing `models/tree_sources/london_plane.blend`. Bare: 5684 tris, 0 leaf faces, foliage=false → `tmp/tree_sculpt/london_plane_mature_bare_review.png`. Foliated: 6694 tris, 505 leaf faces, card_anchors=card_sprays=505 (1:1) → `tmp/tree_sculpt/london_plane_mature_review.png`. Card cost +1010 tris vs prior dense path ~14324 tris.
- **Deliverable:** `tmp/tree_sculpt/london_plane_mature_bare_review.png` (structure authority) and `tmp/tree_sculpt/london_plane_mature_review.png` (bare skeleton + GIMP leaf cards)
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-02`
- **from:** Chris
- **said:** Going by visual only — need more secondary branches and more ramification; unsure 3060 Ti can afford it; depends on eventual bark budget.
- **status:** accepted_direction — densify secondaries + ramification; measure bark tris for budget judgment

## WORK_PACKAGE `tree-sculptor-W-20260717-03` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-2`, `TS-5` (measure only)
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** Sparse order-2 coverage and no order-3 forks make the bare skeleton under-ramified; denser secondaries plus short structural tertiaries will fill the scaffold, and measured bark tris will bound 3060 Ti affordability before a FPS gate.
- **Changed paths:** `scripts/tree_sculpt/create_london_plane.py`, `scripts/tree_sculpt/review_rig.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_mature.glb`, `tmp/tree_sculpt/london_plane_mature_bare_review.png`, `tmp/tree_sculpt/london_plane_mature_review.png`, `tmp/tree_sculpt/review_mature/`, `tmp/tree_sculpt/review_mature_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuilt mature via `TREE_SCULPT_REVIEW_STAGES=mature blender4 --background --python scripts/tree_sculpt/create_london_plane.py`. Bare: 7797 tris, 0 leaf faces, foliage=false, bark_cc=1. Foliated: 10679 tris, 1441 cards (1:1). Strand counts: order2 80, order3 74 (was 50 / 0). Bark +2113 tris (+37%) vs prior bare 5684; still ~54% of prior dense-stand mesh (~14324) that held ~14–15 fps @ 240 lod0.
- **Deliverable:** denser mature bare + foliated reviews; bark budget number for Chris
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-03`
- **from:** Chris
- **said:** We have an evaluation garden — type `garden`, see models under consideration in an otherwise empty park. Want that with the current (sculpt) model.
- **status:** accepted_direction — wire sculpt stages into the eval garden path

## WORK_PACKAGE `tree-sculptor-W-20260717-04` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-6` (garden wiring), `TS-1` (view path)
- **Classification:** `MAINTENANCE`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** If `garden` selects `london_plane_sculpt` and tree_builder loads the three untiered stage GLBs, Chris sees young/mature/veteran on the empty Great Lawn instead of production london_plane.
- **Changed paths:** `tree_builder.gd`, `eval_plot_builder.gd`, `docs/tree_sculptor.md`, `scripts/garden`, `/home/chris/bin/garden`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** `timeout 120 xvfb-run … /home/chris/bin/garden` → EvalPlot sculpt review; 3 specimens injected; loaded `london_plane_sculpt_{young,mature,veteran}` (1 variant each); placed 12 m / 20 m / 26 m. Log: `tmp/tree_sculpt/garden_sculpt_launch.log`. Production GLBs untouched.
- **Deliverable:** `garden` opens the current sculpt models under consideration on the empty Great Lawn.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`


## VERDICT on `tree-sculptor-W-20260717-04`
- **from:** Chris
- **said:** Scale is finally what it ought to be; veteran is breathtaking/majestic and makes the reference look small and young. Skeleton impressive, but leaves sit on it like wool — carriage wrong. Agreed with advisor: skeleton/scale PASS; foliage carriage FAIL (pompoms on thick wood vs reference tip-islands on a fine web). Evidence: interactive garden shots `screenshots/cpw_000.png`–`cpw_002.png` vs `reference_photos/london planetree/majestic-london-plane-tree-urban-architectural-photography-showcase-greenery-cityscape-captivating-photograph-353509813_branch_structure.jpg`.
- **status:** accepted_direction — keep scale/skeleton; densify tip/emitter periphery and keep cards off thick wood; do not stack cards or re-do global scale


## VERDICT (budget question before tip densify)
- **from:** Chris
- **said:** Are we sure the length and number of secondary and further ramifications are about as right as the graphics card can handle in a game?
- **status:** answered_in `tree-sculptor-W-20260717-05` — no, not at ceiling; tip densify still affordable vs production m

## WORK_PACKAGE `tree-sculptor-W-20260717-05` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-5`
- **Classification:** `MAINTENANCE`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** If sculpt mature bark+card tris sit well below production `london_plane_m` that already ships in the lod0→impostor park chain, then current order-2/3 count and length are not at the 3060 Ti ceiling; the 15 fps dense-stand probe is a pathological all-lod0 stress test, not the game budget.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md` (measurement only; no mesh/code change)
- **Verification:**
  - Mature blend: 160 strands — order2=80, order3=74; secondary lengths ~2.0–3.4 (tertiaries 0.32–0.42× when length≥2.0).
  - Bare bark 7,797 tris; foliated 10,679 (1,441 cards 1:1).
  - Production `london_plane_{s,m,l}`: 17,266 / 27,031 / 19,197 tris — sculpt mature ≈ 40% of m.
  - `dense_stand_gate.json`: 240 lod0 MultiMesh, no impostor → median 15 fps (fails ≥45); note says not the 6808-tree park.
  - Park chain: lod0 0–80 m → impostor; woodland floor 45 fps on 3060 Ti (`docs/rendering.md` / `docs/trees.md`).
- **Deliverable:** TS-5 closed for current densify — not GPU-maxed; re-measure only if tip work pushes mature past ~production m (~27k).
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`


## WORK_PACKAGE `tree-sculptor-W-20260717-06` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-5`
- **Classification:** `MAINTENANCE`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** Sculpt mature bark+card tris well below production `london_plane_m` means order-2/3 count and length are not at the 3060 Ti ceiling; the 15 fps dense-stand probe is pathological all-lod0, not the park lod0→impostor budget.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Counted mature blend strands (order2=80, order3=74); read `tmp/tree_sculpt/review_mature_bare/manifest.json` (7797 tris) and `review_mature/manifest.json` (10679 tris, 1441 cards); counted production GLB tris s/m/l=17266/27031/19197; read `tmp/tree_sculpt/dense_stand_gate.json` (240 lod0, median 15 fps); checked park chain lod0→impostor and 45 fps woodland floor in `docs/trees.md`/`docs/rendering.md`. Verdict: sculpt mature ≈40% of production m — not GPU-maxed.
- **Deliverable:** Budget answer in `STATE_tree_sculptor.md` Budget table; evidence paths above (no new mesh).
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-06`
- **from:** Chris
- **said:** Agree we tip densify.
- **status:** accepted_direction — proceed TS-1 tip/emitter periphery; cards off thick wood

## WORK_PACKAGE `tree-sculptor-W-20260717-07` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris: agree we tip densify)
- **Hypothesis:** Wool was cards on thick primaries (`along`); strip primary emitters to `none` and add true-tip order-3 hosts on every secondary so sprigs read as terminal islands, still under production m tris.
- **Changed paths:** `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_*.glb`, `tmp/tree_sculpt/london_plane_mature_{bare_,}review.png`, `tmp/tree_sculpt/review_mature/`, `tmp/tree_sculpt/review_mature_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild mature exit 0. Strands order2=80 order3=154 (was 74); card_pattern along=0 none=6 tip=234. Bare 7959 tris / 0 cards; foliated 12171 tris / 2106 cards (1:1). ≈45% of production m (27031). Young along=0. Contact sheets + garden GLBs young/mature/veteran updated. Headless sheets show tip clusters not primary-along wool; garden eye is authority.
- **Deliverable:** `tmp/tree_sculpt/london_plane_mature_review.png` + bare sheet; `garden` loads tip-densified sculpt stages.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-07`
- **from:** Chris
- **said:** Many garden screenshots (`screenshots/cpw_000.png`–`cpw_016.png`). Still wool. Leaf cards fairly randomly thrown at thin-enough branches rather than rooted to the connecting point of the twig. Compared to reference photos: too few and too short secondaries and ramifications — asked not to take amateur word; verify vs refs.
- **status:** rejected_fix — tip densify did not clear wool; structure still under-ramified vs refs; card attach mid-strand

## WORK_PACKAGE `tree-sculptor-W-20260717-08` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** Wool + "thrown" cards come from `tip` fanning anchors along the outer half of every tip strand (including order-2), while order-2/3 wood is still shorter/sparser than the ref tip-web — so foliage reads as mid-twig spray and pompoms on stubs. True-tip-only anchors, cards only on order-3, and longer denser order-2/3 move sprigs to terminal junctions on a finer scaffold.
- **Evidence (Chris + refs):** garden `screenshots/cpw_000`–`cpw_016` vs `reference_photos/london planetree/majestic-…_branch_structure.jpg`, `os-lk-londonplane (6).JPG`, winter canopy ref — Chris's secondary/ramify read confirmed; code showed tip fan from sample 55%→end.
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/london_plane_mature_{bare_,}review.png`, `tmp/tree_sculpt/review_mature/`, `tmp/tree_sculpt/review_mature_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild exit 0. Mature strands order2=90 order3=358 (was 80/154); card_pattern tip only on order-3; anchors=358 1:1 (was 2106 mid-fan). Bare 10038 tris / 0 cards; foliated 10754 / 358. ≈40% of production m (27031). Godot `--import` reimported sculpt GLBs. Headless sheets + garden path updated; garden eye is authority.
- **Deliverable:** tip-rooted cards on longer denser order-2/3 scaffold; `garden` loads updated stages.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-08`
- **from:** Chris
- **said:** yeah, continue
- **status:** accepted_direction — proceed next hypothesis (tip-junction sprig size/orientation; lengthen order-3 only if skeleton still short)

## WORK_PACKAGE `tree-sculptor-W-20260717-09` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris: yeah continue)
- **Hypothesis:** Cards look thrown because `london_plane_cluster.png` paints its petiole at UV ~(0.28, 0.055) while the sculpt path pinned the UV bottom-centre (transparent) to the tertiary tip; pinning the measured stem UV puts leaf→stem→twig on one line.
- **Evidence:** W-07 Chris "not rooted to the connecting point"; measured opaque stem base px(286,971)/1024; prior `_append_sprig_card` used base-at-junction with UV (0,0) edge centred on tip (u=0.5).
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/london_plane_mature_{bare_,}review.png`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild exit 0 (`TREE_SCULPT_REVIEW_STAGES=young,mature,veteran`). Mature foliated 10754 tris / 358 cards 1:1; bare 10038 / 0; orders 2=90 3=358; bark_cc=1. Godot `--import` reimported sculpt GLBs (exit 0). Tris unchanged vs W-08 (orientation-only). Garden eye is authority for junction rooting.
- **Deliverable:** stem-pinned sprig cards on tip-only order-3; `garden` loads updated stages.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-09`
- **from:** Chris (delegated: "I took many screenshots. draw your own conclusions.")
- **evidence:** garden `screenshots/cpw_000.png`–`cpw_014.png` (21:43–21:44, post stem-pin) + refs `majestic-…_branch_structure.jpg`
- **said (agent judgment):** Stem pin did **not** clear the defect. Close-ups still show discrete leaf stamps floating off thin wood; full-tree young/mature/veteran still under-filled tip islands vs ref tip-web. Scale/identity still PASS (London-plane bark, stage labels, veteran mass). Measured cause supporting size-next: authoring cards 0.42–0.58×CARD_HALF_FACTOR=1.20 then ×(5/real_h)×garden height → ~1.3–1.6 m world quads on 358 sparse tips (mature) / 28 (young) — stem UV pin is invisible under that mass.
- **status:** rejected_fix — UV stem pin insufficient; next is sprig **size** (STATE hypothesis), not another UV tweak

## WORK_PACKAGE `tree-sculptor-W-20260717-10` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris delegated visual judgment on W-09 screenshots)
- **Hypothesis:** Stem-pinned cards still read as floating stamps because authoring size 0.42–0.58 × HALF 1.20, after MODEL_HEIGHT normalize and garden 12/20/26 m scale, becomes ~1.3–1.6 m world quads on sparse tips — halving size + HALF=1.00 makes leaf→stem→twig tip-local.
- **Evidence:** W-09 rejected on `screenshots/cpw_000`–`cpw_014`; mature leaf_area was 57.97 model-m².
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/london_plane_*_review.png`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild exit 0 (`TREE_SCULPT_REVIEW_STAGES=young,mature,veteran`). Mature foliated 10754 tris / 358 cards 1:1; bare 10038 / 0; leaf_area_model_m2 **9.84** (was 57.97). Young 28 cards area 0.67; veteran 208 / 10.79. Godot `--import` reimported sculpt GLBs (exit 0). Tris unchanged (size-only). Garden eye is authority.
- **Deliverable:** tip-local smaller sprigs on existing tip-only order-3 scaffold; `garden` loads updated stages.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`


## VERDICT on `tree-sculptor-W-20260717-10`
- **from:** Chris
- **said:** Consult screenshots and references — limbs are ribbons, some missing triangles; leaf cards tumble in midair often; overall look very sparse. Asked what agent sees.
- **evidence:** garden `screenshots/cpw_000.png`–`cpw_010.png` (21:53–21:54, post size-shrink) + headless `tmp/tree_sculpt/review_mature{,_bare}/front.png` + ref `majestic-…_branch_structure.jpg`
- **status:** rejected_fix — size shrink did not clear carriage; exposed bark mesh failure as dominant defect

## WORK_PACKAGE `tree-sculptor-W-20260717-11` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1` (reclassify), `TS-7` (bark mesh integrity — new)
- **Classification:** `REPRODUCED_DEFECT` (diagnosis only; no mesh/code change)
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** Size shrink made the real defects readable: thin-order tubes are non-volumetric (ribbons / missing faces / floating bark shards) in both garden and bare review; tumbling cards are secondary to broken tip hosts; sparsity vs ref tip-web remains but must not be treated with another card size/UV tweak (two-strike on W-09 + W-10).
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification (looked, not measured):**
  - Garden close-ups (`cpw_000`–`001`, `005`–`006`, `008`): flat bark ribbons, holes, detached bark triangles, sprig quads in open sky casting isolated shadows.
  - Full-tree (`cpw_002`–`003`, `009`): young/mature/veteran all see-through scaffolds; trunk more solid than canopy wood.
  - Bare review `review_mature_bare/front.png`: same ribbon/hole bark without blaming cards.
  - Ref `majestic-…_branch_structure.jpg`: continuous cylindrical limbs + dense tip-island canopy — opposite of current read.
- **Deliverable:** visual diagnosis + next hypothesis (bark tube integrity first).
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## WORK_PACKAGE `tree-sculptor-W-20260717-12` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`, `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required`
- **Hypothesis:** Post-W-10 garden and bare-review images show thin-order bark as ribbons/holes/floating shards; tumbling cards and sparsity are secondary until tip hosts are solid tubes — no further card size/UV tweak (two-strike W-09+W-10).
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Inspected garden `screenshots/cpw_000.png`–`cpw_010.png` (21:53–21:54), headless `tmp/tree_sculpt/review_mature/front.png` + `review_mature_bare/front.png`, and ref `reference_photos/london planetree/majestic-london-plane-tree-urban-architectural-photography-showcase-greenery-cityscape-captivating-photograph-353509813_branch_structure.jpg`; observed flat bark ribbons, missing faces, detached bark triangles, sprig quads in open sky, see-through young/mature/veteran vs continuous cylindrical ref limbs.
- **Deliverable:** diagnosis in `STATE_tree_sculptor.md` (TS-7 bark blocking; next = tube integrity); evidence paths above
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-12`
- **from:** Chris
- **said:** fix branch tubes first
- **status:** accepted_direction — proceed TS-7 bark tube integrity; no card size/UV tweaks

## WORK_PACKAGE `tree-sculptor-W-20260717-13` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris: fix branch tubes first)
- **Hypothesis:** Blind `remove_doubles` at distance 0.12 merges opposite sides of thin tubes (tip diameter ~0.05), producing ribbons/holes/floating shards; stem_id-aware cross-strand-only weld keeps rings volumetric while still joining forks.
- **Evidence:** W-10/W-12 garden+bare ribbons; manifest `junction_vertices_welded=67801`, `bark_non_manifold_edges=7006`.
- **Changed paths:** `scripts/tree_sculpt/pipeline_common.py`, `scripts/tree_sculpt/sculpt_core.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/london_plane_*_review.png`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild young/mature/veteran exit 0. Mature bare: tris 102866 (was 10038), weld 24318 (was 67801), non-manifold 542 (was 7006), bark_cc=1. Foliated: 103582 / 358 cards 1:1 area 9.84. Bare front/30m/branch_roles show continuous cylindrical limbs (no ribbon collapse). Godot `--import` reimported sculpt GLBs. Garden eye is authority.
- **Deliverable:** volumetric bark tubes; `garden` loads updated stages; look at bare/foliated sheets + garden for solid wood.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260717-13`
- **from:** Chris
- **said:** Took several more screenshots. Branches better, but not yet good, esp on s model. Joints of branches seem to be meeting at narrowed points. Very few leaves. Asked what agent sees.
- **evidence:** garden `screenshots/cpw_000.png`–`cpw_011.png` (22:06–22:07, post W-13)
- **status:** partial_accept — mid-strand tubes PASS (no ribbons); fork collars FAIL (pinched/hourglass); foliage sparse (expected under tip-only + small cards; parked until collars solid)

## WORK_PACKAGE `tree-sculptor-W-20260717-14` · 2026-07-17

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris partial_accept on W-13; pinched joints + sparse leaves)
- **Hypothesis:** Fixed absolute child bases + absolute 0.12 cross-strand weld collapse thin fork collars into narrowed points; inherit parent radius at child base (incl. young primaries) and radius-limit weld so collars stay fat.
- **Evidence:** garden `screenshots/cpw_000`–`cpw_011` (22:06–22:07); W-13 metrics weld=24318 nm=542.
- **Changed paths:** `scripts/tree_sculpt/pipeline_common.py`, `scripts/tree_sculpt/sculpt_core.py`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/london_plane_*_review.png`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild young/mature/veteran exit 0. Mature bare tris 118332 weld 16949 nm 849 (was 102866/24318/542). Young bare 12726/1352/86; foliated cards still 28/358/208. Compiled young forks c/p ≥0.55, 0 bulges. Godot `--import` exit 0. Garden eye is authority for collar continuity.
- **Deliverable:** inherited fork radii + radius-aware weld; `garden` loads updated stages — look for non-pinched joints esp. on S/young.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Absolute weld distance on thin forks pinches collars into points even when stem_id-aware; limit by local radius. Child base radius must inherit parent radius at attach — fixed tip-thin bases read as cones meeting tip-to-tip.

## VERDICT on `tree-sculptor-W-20260717-14`
- **from:** Chris
- **said:** We now have Inkscape. Could that be helpful? Maybe we trace a reference tree?
- **status:** question_new_direction — collar eye still unanswered; evaluate Inkscape as authoring aid before more mesh tweaks

## WORK_PACKAGE `tree-sculptor-W-20260718-15` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-8` (Inkscape ref guide — new), `TS-7` (still open)
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `LOW` (investigation only; no mesh/pipeline change)
- **Approval:** `required` before adding SVG/trace into the sculptor contract
- **Hypothesis:** Inkscape helps as a **2D authoring guide** (hand-drawn limb centerlines or bitmap silhouette from a structure ref → Blender background/curve overlay for proportion), not as a fix for W-14 fork collars or 3D tip/card topology. Auto "trace the whole tree into a 3D skeleton" is underdetermined from one photo.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md` (docs only)
- **Verification:**
  - Flatpak `org.inkscape.Inkscape` **1.4.4** installed; bare `inkscape` not on PATH (`sudo apt` stub only).
  - Bundles `potrace` inside the Flatpak; Trace Bitmap is a GUI action (no clean headless action found in a quick probe).
  - No existing Inkscape/SVG/trace path under `scripts/tree_sculpt/` — contact sheets only juxtapose a JPEG ref (`A149-03_hero_l.jpg`).
  - Best structure refs for tracing: `reference_photos/london planetree/majestic-…_branch_structure.jpg`, `os-lk-londonplane (6).JPG` (leafy summer heroes are poor Trace Bitmap inputs).
- **Deliverable:** recommendation below; **no** SVG authored, **no** Blender import wired — waiting on Chris.
- **Recommendation:**
  1. **Do use Inkscape** for *manual centerline* paths (trunk + primaries + sample secondaries) over a structure photo; export SVG; load as Blender Empty-image + guide curves while editing `london_plane.blend`. That attacks the recurring "under-ramified vs ref" gap with measured 2D proportions.
  2. **Do not** expect Trace Bitmap silhouettes to become strand graphs, fix pinched collars, or place tip cards.
  3. **Still need** Chris's eye on W-14 garden collars (pinched joints) — Inkscape does not clear TS-7.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`


## WORK_PACKAGE `tree-sculptor-W-20260718-16` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-8`
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `MEDIUM`
- **Approval:** `required — awaiting Chris authorize Inkscape centerline guide vs Trace-Bitmap→3D`
- **Hypothesis:** Inkscape helps as a 2D centerline/silhouette authoring guide from structure refs, not as a fix for W-14 fork collars or auto 3D strand graphs.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** ran `flatpak run org.inkscape.Inkscape --version` → Inkscape 1.4.4; `command -v inkscape` missing (apt stub only); Flatpak ships bundled potrace; `rg` under `scripts/tree_sculpt` found no svg/trace/inkscape path (contact sheets only JPEG-juxtapose `A149-03_hero_l.jpg`); structure refs present: `reference_photos/london planetree/majestic-…_branch_structure.jpg`, `os-lk-londonplane (6).JPG`.
- **Deliverable:** recommendation in `STATE_tree_sculptor.md` (manual centerlines yes; Trace-Bitmap→3D no; W-14 collar eye still needed) — no SVG authored, no Blender import wired.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`


## VERDICT on `tree-sculptor-W-20260717-14`
- **from:** Chris
- **said:** Took a few screenshots. Pinching is still happening. Trees are sparse. Let's try using Inkscape on majestic-…_branch_structure.jpg to see if that teaches how to build trees.
- **evidence:** garden `screenshots/cpw_000.png`–`cpw_003.png` (2026-07-18 12:15)
- **status:** rejected_on_collars — W-14 did not clear pinched joints; sparse confirmed; TS-8 authorized (manual centerline / structure learning, not Trace→3D)

## VERDICT on `tree-sculptor-W-20260718-15` / `tree-sculptor-W-20260718-16`
- **from:** Chris
- **said:** (same turn) authorize Inkscape on the majestic branch_structure ref
- **status:** accepted — proceed TS-8 structure guide

## WORK_PACKAGE `tree-sculptor-W-20260718-17` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-8`
- **Classification:** `REPRODUCED_DEFECT` (structure learning from ref; pinching/sparsity confirmed in garden) — investigation deliverable, no mesh change
- **Risk:** `LOW`
- **Approval:** `granted` (Chris: try Inkscape on majestic branch_structure)
- **Hypothesis:** Tracing the majestic ref in Inkscape (potrace silhouette + hand centerlines + measured fork diameters) will show crotch-as-shoulder-disk and outer-tip foliage shell, explaining W-14 pinching FAIL and sparse read without another weld/radius knob.
- **Changed paths:**
  - `tmp/tree_sculpt/inkscape/*` (guide SVG/PNG, potrace, lessons)
  - `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:**
  - Flatpak Inkscape 1.4.4 `object-trace` → `trace_auto.svg`; bundled potrace → `majestic_potrace.svg`.
  - Guide export: `flatpak run org.inkscape.Inkscape … --export-filename=majestic_structure_guide.png` exit 0.
  - Measured primary fork Ø median 42.8px, secondary 18.6px; 5 primaries traced (= sculpt count).
  - Garden eye already confirmed pinching + sparse (`cpw_000`–`003`); lessons L1–L5 in `STRUCTURE_LESSONS.md`.
- **Deliverable:** `tmp/tree_sculpt/inkscape/majestic_structure_guide.svg` (+ `.png`, `STRUCTURE_LESSONS.md`) — open in Inkscape / use as Blender overlay; next collar approach = parent-radius tube through join, not W-14-style inherit+weld alone.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Inkscape/potrace is a 2D crotch-continuity + proportion guide; it is not a 3D strand extractor.
- Ref primary count matching sculpt means sparse ≠ missing order-1; spend on tip web.
- W-14 radius inherit can still leave hourglass joints — crotch must stay a filled shoulder volume through the join.


## WORK_PACKAGE `tree-sculptor-W-20260718-18` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-8`
- **Classification:** `MAINTENANCE`
- **Risk:** `LOW`
- **Approval:** `Chris approved 2026-07-18 — try Inkscape on majestic branch_structure`
- **Hypothesis:** An Inkscape guide (potrace silhouette + hand centerlines + measured fork diameters) on majestic-…_branch_structure.jpg will show crotch-as-shoulder-disk and outer-tip foliage shell, explaining W-14 pinching FAIL and sparse garden read without another weld/radius tweak.
- **Changed paths:** `tmp/tree_sculpt/inkscape/build_structure_guide.py`, `tmp/tree_sculpt/inkscape/majestic_structure_guide.svg`, `tmp/tree_sculpt/inkscape/majestic_structure_guide.png`, `tmp/tree_sculpt/inkscape/STRUCTURE_LESSONS.md`, `tmp/tree_sculpt/inkscape/majestic_vs_sculpt_lessons.json`, `tmp/tree_sculpt/inkscape/majestic_potrace.svg`, `tmp/tree_sculpt/inkscape/trace_auto.svg`, `tmp/tree_sculpt/inkscape/majestic_branch_structure.png`, `tmp/tree_sculpt/inkscape/majestic_wood_for_trace.png`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Ran `python3 tmp/tree_sculpt/inkscape/build_structure_guide.py` then `flatpak run org.inkscape.Inkscape … --export-filename=majestic_structure_guide.png` exit 0; primary fork Ø median 42.8px, secondary 18.6px, 5 primaries traced; garden `screenshots/cpw_000.png`–`cpw_003.png` (2026-07-18 12:15) show pinching still + sparse; lessons L1–L5 written in `STRUCTURE_LESSONS.md`.
- **Deliverable:** `tmp/tree_sculpt/inkscape/majestic_structure_guide.svg` (Inkscape layers) + `tmp/tree_sculpt/inkscape/majestic_structure_guide.png` + `tmp/tree_sculpt/inkscape/STRUCTURE_LESSONS.md`
- **Git:** `uncommitted` (HEAD `f7fceca`; record + inkscape artifacts not committed)
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260718-17` / `tree-sculptor-W-20260718-18`
- **from:** Chris
- **said:** ok, let's implement those lessons
- **status:** accepted — proceed L1 parent-radius shoulder through join (not W-14 inherit+weld); tip-web densify (L2/L4) after collars

## WORK_PACKAGE `tree-sculptor-W-20260718-19` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `granted` (Chris: implement those lessons — L1 shoulder through join)
- **Hypothesis:** Hourglass forks are child tubes starting thinner than the parent at the join (W-14 0.55·parent floor + inherit+weld); holding a parent-radius tube segment through each fork (plus parent-radius skinner emergence ring) makes crotches read as filled shoulder disks.
- **Evidence:** Inkscape L1 (`STRUCTURE_LESSONS.md`); W-14 garden pinching FAIL; two-strike on inherit+weld (W-13 partial / W-14 reject).
- **Changed paths:**
  - `scripts/tree_sculpt/sculpt_core.py` (`_shoulder_radii` + compile_graph)
  - `scripts/leafback_skinner.py` (emergence ring uses parent radius)
  - `scripts/tree_sculpt/create_london_plane.py` (near-parent authored bases + shoulder taper)
  - `docs/tree_sculptor.md`
  - `models/tree_sources/london_plane.blend`
  - `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`
  - `tmp/tree_sculpt/review_{young,mature,veteran}/`, `*_bare/`, contact sheets
  - `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:**
  - Rebuild young/mature/veteran exit 0 (`TREE_SCULPT_CREATED`).
  - Fork c/p at child starts: young/mature/veteran all **min=med=max=1.000** (was floored 0.55).
  - Mature bare tris 141471 weld 34546 nm 2151 cc=1 (was 118332/16949/849); young bare 15467/3789/197; veteran bare 101253/16080/2091.
  - Cards unchanged (28/358/208).
  - Godot `--import` exit 0; garden loads young/mature/veteran sculpt GLBs.
  - Garden eye is authority for collar continuity (esp. S/young whorls).
- **Deliverable:** parent-radius shoulder collars; look at bare reviews + `garden` for non-hourglass joints. Tip-web densify (L2/L4 / TS-1) deferred until collars PASS.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## WORK_PACKAGE `tree-sculptor-W-20260718-20` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris approved 2026-07-18 — implement those lessons (L1 shoulder)`
- **Hypothesis:** Hourglass forks are child tubes starting thinner than the parent at the join; holding a parent-radius tube segment through each fork (plus parent-radius skinner emergence) makes crotches read as filled shoulder disks.
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `scripts/leafback_skinner.py`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_young.glb`, `models/trees/london_plane_sculpt_mature.glb`, `models/trees/london_plane_sculpt_veteran.glb`, `tmp/tree_sculpt/review_young/`, `tmp/tree_sculpt/review_young_bare/`, `tmp/tree_sculpt/review_mature/`, `tmp/tree_sculpt/review_mature_bare/`, `tmp/tree_sculpt/review_veteran/`, `tmp/tree_sculpt/review_veteran_bare/`, `tmp/tree_sculpt/london_plane_young_review.png`, `tmp/tree_sculpt/london_plane_young_bare_review.png`, `tmp/tree_sculpt/london_plane_mature_review.png`, `tmp/tree_sculpt/london_plane_mature_bare_review.png`, `tmp/tree_sculpt/london_plane_veteran_review.png`, `tmp/tree_sculpt/london_plane_veteran_bare_review.png`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Ran `TREE_SCULPT_REVIEW_STAGES=young,mature,veteran blender4 --background --python scripts/tree_sculpt/create_london_plane.py` → exit 0 and `TREE_SCULPT_CREATED`; fork c/p at child starts young/mature/veteran all min=med=max=1.000 (was 0.55 floor); mature bare tris=141471 weld=34546 nm=2151 cc=1 (was 118332/16949/849); young bare 15467/3789/197; veteran bare 101253/16080/2091; cards still 28/358/208; Godot `--import` exit 0; inspected `tmp/tree_sculpt/review_{young,mature}_bare/{front,stood_under,30m_read,branch_roles}.png` — garden eye remains authority for collar continuity.
- **Deliverable:** `models/trees/london_plane_sculpt_{young,mature,veteran}.glb` + bare reviews under `tmp/tree_sculpt/review_*_bare/` — look in `garden` for non-hourglass joints (esp. S/young). Tip-web densify (TS-1) deferred until collars PASS.
- **Git:** `uncommitted` (HEAD `f7fceca`)
- **Status:** `awaiting_user_verdict`


## VERDICT on `tree-sculptor-W-20260718-19` / `tree-sculptor-W-20260718-20`
- **from:** Chris
- **said:** I took a few screenshots. Crotches still pinched. Limbs look weird.
- **evidence:** garden `screenshots/cpw_000.png`–`cpw_002.png` (2026-07-18 12:37–12:38, post W-20 shoulder)
- **status:** rejected_fix — parent-radius shoulder through join did not clear pinched crotches; limbs still weird

## WORK_PACKAGE `tree-sculptor-W-20260718-21` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `DECISION_REQUIRED` (two-strike on radius/weld/shoulder; diagnosis only — no mesh change)
- **Risk:** `n/a`
- **Approval:** `required` before next collar implementation
- **Hypothesis:** Pinched crotches persist after W-14 inherit+weld AND W-20 parent-radius shoulder because `leafback_skinner` joins are child-tube-on-parent-surface + weld (AC-15 residual), which cannot fill a crotch disk no matter how radii match; "weird limbs" are the same interpenetrating/faceted tubes at garden distance (sculpt `ring=16`, no smooth pass), worsened by sausage shoulder hold. ★ Two-strike: forbidden to tweak radius/weld/shoulder again.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:**
  - Looked at garden `screenshots/cpw_000`–`cpw_002` (12:37–12:38): V/star pinched forks, faceted/knife limbs, stretched bark at joins.
  - Bare `tmp/tree_sculpt/review_mature_bare/front.png` + `review_young_bare/stood_under.png`: same pinch + sausage/angular wood without cards.
  - W-20 metrics still c/p min=med=max=1.000 at child starts — radius match held; visual still FAIL → radius was not the cause.
  - Project brief: `docs/leafback_tree_planner_spec.md` AC-15 — skinner = raw tube interpenetration, no filleted collar; ManifoldMesher does collars; intended residual remedy was RING≈24 + smoothing (sculpt still compiles at `ring=16`, no smooth).
  - Inkscape L1 already listed explicit collar mesh as the alternative to radius-hold; W-20 only did radius-hold.
- **Deliverable:** re-derived diagnosis + Chris choice below (no GLB change).
- **Choices for Chris:**
  1. **ManifoldMesher** on the authored node graph (production-style filleted collars; architectural — not Mtree authorship).
  2. **Explicit crotch collar** in leafback (loft/boolean fill at each fork; keep Bézier authority).
  3. **Park-distance accept** AC-15 for now; move to tip-web densify (TS-1 / L2/L4) and judge collars only at walk distance.
- **Git:** `uncommitted` (HEAD `f7fceca`)
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Two radius/weld/shoulder passes (W-14, W-20) failed collars while c/p already = 1.0 — crotch fill is a meshing topology problem (AC-15), not a radius parameter.

## WORK_PACKAGE `tree-sculptor-W-20260718-22` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `LOW`
- **Approval:** `required — awaiting Chris pick: ManifoldMesher | explicit crotch collar | accept AC-15 → tip-web`
- **Hypothesis:** Pinched crotches persist after W-14 inherit+weld and W-20 parent-radius shoulder (c/p=1.0) because leafback tube+weld cannot fill a crotch disk (AC-15); radius/weld/shoulder knobs are two-struck; Chris must choose the meshing path before further collar work.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Inspected garden `screenshots/cpw_000.png`–`cpw_002.png` (2026-07-18 12:37–12:38): V/star pinched forks, faceted/knife limbs; bare `tmp/tree_sculpt/review_mature_bare/front.png` + `review_young_bare/stood_under.png` show same pinch without cards; W-20 fork c/p still min=med=max=1.000 so radius match held while visual FAIL; read `docs/leafback_tree_planner_spec.md` AC-15 (skinner = raw tube interpenetration; ManifoldMesher does collars); sculpt compile still `ring=16` with no smooth pass.
- **Deliverable:** `STATE_tree_sculptor.md` diagnosis + three collar-path choices for Chris (no GLB/mesh change this package)
- **Git:** `uncommitted` (HEAD `f7fceca`)
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260718-21` / `tree-sculptor-W-20260718-22`
- **from:** Chris
- **said:** why are joints/crotches pinching? it's not difficult to draw a bifurcating tube in blender. maybe we're making a simple thing overly complicated.
- **status:** accepted_direction — collar path = Blender-native bifurcating tube (Skin Modifier on the vert/edge graph), not another leafback radius/weld/shoulder knob or ManifoldMesher; prior options reframed as overcomplication

## WORK_PACKAGE `tree-sculptor-W-20260718-23` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris 2026-07-18 — Blender-native bifurcating tube; stop overcomplicating`
- **Hypothesis:** Pinched crotches are leafback child-on-parent tube+weld (AC-15), not a radius knob; compiling the authored beveled Bézier curves as mesh (viewport tubes joined, no weld) restores continuous limb tubes with overlapping fork volumes. Skin Modifier was probed and rejected (sausage waists).
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `docs/tree_sculptor.md`, `models/trees/london_plane_sculpt_{young,mature,veteran,mature_open,mature_upright}.glb`, `tmp/tree_sculpt/review_*`, `tmp/tree_sculpt/london_plane_*_review.png`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:**
  - Skin probe first: Y-fork OK, but mature Skin → sausage waists + cc≈19; not shipped.
  - Curve-bevel compile+reviews exit 0; Godot `--import` exit 0.
  - Bare tris/cc: young 21888/50; mature 197856/454; veteran 115776/265; weld=0.
  - Headless bare `stood_under`/`front` show continuous tubes with intersection crotches (not welded star-pinch); garden eye is authority.
- **Deliverable:** `garden` loads curve-bevel sculpt stages — look for non-pinched tube crotches vs W-20 welded hourglass.
- **Git:** `uncommitted` (HEAD `f7fceca`)
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Skin Modifier on a dense sampled graph sausage-waists every joint — not a drop-in for authored tree forks.
- The viewport beveled Bézier *is* the bifurcating tube; re-skinning through leafback/Skin was the overcomplication.

## WORK_PACKAGE `tree-sculptor-W-20260718-24` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris approved 2026-07-18 — Blender-native bifurcating tube; stop overcomplicating`
- **Hypothesis:** Pinched crotches are leafback tube+weld (AC-15), not a radius knob; meshing the authored beveled Bézier curves (viewport tubes joined, no weld) restores continuous limbs with overlapping fork volumes — Skin was probed and rejected (sausage waists).
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/trees/london_plane_sculpt_young.glb`, `models/trees/london_plane_sculpt_mature.glb`, `models/trees/london_plane_sculpt_veteran.glb`, `models/trees/london_plane_sculpt_mature_open.glb`, `models/trees/london_plane_sculpt_mature_upright.glb`, `tmp/tree_sculpt/review_young_bare/`, `tmp/tree_sculpt/review_mature_bare/`, `tmp/tree_sculpt/review_veteran_bare/`, `tmp/tree_sculpt/london_plane_mature_bare_review.png`, `tmp/tree_sculpt/london_plane_young_bare_review.png`, `tmp/tree_sculpt/london_plane_veteran_bare_review.png`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** `blender4 --factory-startup -b models/tree_sources/london_plane.blend --python scripts/tree_sculpt/compile_all.py` exit 0; `review_rig.render_contact_sheet` young/mature/veteran exit 0; Godot `--import` exit 0; bare manifests weld=0 tris/cc young 21888/50 mature 197856/454 veteran 115776/265; Skin probe rejected (mature cc≈19 sausage waists); inspected `tmp/tree_sculpt/review_mature_bare/{front,stood_under}.png` + young/veteran bare sheets — tubes continuous, crotches = intersections not welded stars; garden eye remains authority.
- **Deliverable:** `models/trees/london_plane_sculpt_{young,mature,veteran}.glb` + `tmp/tree_sculpt/london_plane_*_bare_review.png` — open `garden` and judge crotch fill vs W-20 hourglass.
- **Git:** `uncommitted` (HEAD `f7fceca`)
- **Status:** `awaiting_user_verdict`


## VERDICT on `tree-sculptor-W-20260718-23` / `tree-sculptor-W-20260718-24`
- **from:** Chris
- **said:** Took a few screenshots. Joints are good. Elbows have gaps. Overall the best looking skeleton so far. Now need ramifications out from here to the leaf cards. Thinking leaf-back from here might work so long as we don't change the skeleton we have now (except repairing the elbows). Asked what to propose for decent-skeleton → full canopy shell.
- **status:** accepted_skeleton — crotches/joints PASS (curve-bevel); elbows FAIL (gaps); freeze skeleton except elbow repair; canopy path = DECISION_REQUIRED this package

## WORK_PACKAGE `tree-sculptor-W-20260718-25` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-7` (close joints; open elbows as TS-9), `TS-1` / canopy shell path
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `n/a` (proposal only; no mesh/code change)
- **Approval:** `required — Chris pick canopy path + confirm freeze`
- **Hypothesis:** Curve-bevel skeleton is now the structural authority (joints PASS); remaining canopy gap is missing tip-web hosts to an outer leaf shell (Inkscape L2/L4), not another crotch mesher. Full deprecated leaf-back grower stays dead; what survives is envelope targets + tip growth *from* this frozen scaffold.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Recorded Chris garden verdict (joints good / elbows gaps / best skeleton); two-strike still holds on radius/weld/shoulder and on card size/UV; leafback_DEPRECATED.md still forbids leaves-as-attractors generator; contract already says cards densify crown, not fine-twig bark.
- **Deliverable:** proposal in STATE (path A/B/C + phased plan); await Chris pick.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Curve-bevel join (overlapping viewport tubes) cleared crotches where radius/weld/shoulder could not — keep that bark path for structural wood.
- "Leaf-back from here" means envelope-guided tip hosts on a frozen scaffold, not resurrecting the deprecated leaf-attractor generator.


## WORK_PACKAGE `tree-sculptor-W-20260718-26` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1` (canopy-shell path decision only)
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `LOW`
- **Approval:** `required — Chris pick path A|B|C and elbows-first Y/N`
- **Hypothesis:** Joints PASS on curve-bevel (Chris W-24 verdict) freezes structural wood; canopy shell needs a chosen tip-web path (A envelope-guided / B authored order-3 / C cards-on-envelope) before any mesh work — not another crotch mesher. Elbows tracked separately as `TS-9` (not in this package).
- **Note:** Supersedes W-25 ledger shape (invalid Risk `n/a`; illegal multi-item batch mixing TS-7 closeout with TS-1). Prior VERDICT on W-23/24 unchanged.
- **Changed paths:**
  - `STATE_tree_sculptor.md`
  - `LEDGER_tree_sculptor.md`
- **Observed verification:**
  - Chris verdict text recorded under VERDICT on W-23/24 (joints good; elbows gaps; best skeleton; ask for skeleton→canopy proposal).
  - No mesh/GLB/blend change this package.
  - Confirmed freeze constraints against `docs/tree_sculptor.md` contract (curve-bevel bark; no leafback_skinner on scaffold) and `docs/leafback_DEPRECATED.md` (generator dead; envelopes may survive as targets).
  - Budget numbers left as post–W-24 manifests (mature bare 197856 tris / 358 cards) — tip path must stay cheap.
- **Deliverable evidence:**
  - Proposal A/B/C + freeze rules + phased plan in `STATE_tree_sculptor.md`
  - Path A recommended (envelope-guided tip hosts from secondary tips → tip cards 1:1)
- **Git:** `uncommitted` (HEAD `f7fceca`; this package touches only STATE + LEDGER)
- **Status:** `awaiting_user_verdict`


## WORK_PACKAGE `tree-sculptor-W-20260718-27` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `LOW`
- **Approval:** `required — Chris pick path A|B|C and elbows-first Y/N`
- **Hypothesis:** Joints PASS on curve-bevel freezes structural wood; canopy shell needs a chosen tip-web path (A/B/C) before mesh work — elbows stay `TS-9` outside this package.
- **Changed paths:** `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Recorded Chris W-23/24 garden verdict (joints good; elbows gaps; best skeleton; ask skeleton→canopy proposal). No mesh/GLB/blend change. Checked freeze against `docs/tree_sculptor.md` (curve-bevel bark; no leafback_skinner on scaffold) and `docs/leafback_DEPRECATED.md` (generator dead; envelopes may be tip targets). Post–W-24 budget left as mature bare 197856 tris / 358 cards. Supersedes W-25/W-26 ledger field shape only (W-26 used non-schema labels `Observed verification` / `Deliverable evidence`).
- **Deliverable:** `STATE_tree_sculptor.md` proposal A|B|C + freeze rules + Path A recommended (envelope-guided tip hosts → tip cards 1:1); await Chris pick.
- **Git:** `uncommitted` (HEAD `f7fceca`)
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260718-27`
- **from:** Chris
- **said:** Path A. Elbows first N. Skeleton is shippable; elbows and a central hollow bark circle on the L model are fine-tuning not apparent to a typical walker — handle after the complete tree.
- **status:** accepted — Path A canopy (envelope-guided tip hosts); defer TS-9 elbows and L hollow-bark fine-tune until after complete canopy

## WORK_PACKAGE `tree-sculptor-W-20260718-28` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris 2026-07-18 — Path A; elbows first N; fine-tune after complete tree`
- **Hypothesis:** Thin curve-bevel tip hosts from scaffold terminals toward a frozen-envelope shell, with one GIMP sprig per tip host, produce an outer canopy rim without rewriting structural wood or repairing elbows.
- **Changed paths:** `scripts/tree_sculpt/tip_web.py`, `scripts/tree_sculpt/sculpt_core.py`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/london_plane_*_review.png`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild `TREE_SCULPT_REVIEW_STAGES=young,mature,veteran` exit 0. Tip hosts young/mature/veteran = 35/512/335 (terminals 28/358/208). Mature bare tris 253152 / cards 512 1:1 / cc 966 (was 197856/358/454); young bare 25668/35/85; veteran bare 151956/335/600. Scaffold strand roles unchanged (mature: 5 primaries, 90 secondaries, 358 tertiaries). Godot `--import` exit 0. Headless sheets show tip filigree + tip cards on rim; garden eye is authority for shell density.
- **Deliverable:** Path A tip-web on frozen scaffold; `garden` loads updated young/mature/veteran — judge outer canopy shell vs prior sparse stubs.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`


## VERDICT on `tree-sculptor-W-20260718-28`
- **from:** Chris
- **said:** still very sparse.
- **status:** rejected_density — Path A tip-web under-filled outer shell; densify tip-host count / shell samples (STATE hypothesis); not scaffold rewrite, not elbows


## WORK_PACKAGE `tree-sculptor-W-20260718-29` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `not_required` (Chris W-28: still very sparse — densify per STATE hypothesis)
- **Hypothesis:** Raising Path A shell sample counts ~3× and per-terminal host cap 4→8 (outer-skin samples only) fills the canopy rim with tip hosts + 1:1 cards without rewriting frozen scaffold wood.
- **Changed paths:** `scripts/tree_sculpt/tip_web.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/london_plane_*_review.png`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild `TREE_SCULPT_REVIEW_STAGES=young,mature,veteran` exit 0 (`tmp/tree_sculpt/rebuild_w29_tip_dense.log`). Tip hosts young/mature/veteran = 124/1593/1035 (was 35/512/335); shells 288/1920/1260. Mature bare tris 369900 / cards 1593 1:1 / cc 2047; young bare 35280/124/174; veteran bare 227556/1035/1300. Scaffold terminals unchanged (28/358/208). Godot `--import` exit 0 (`godot_import_w29.log`). Headless mature contact sheet shows denser outer tip filigree + more rim cards vs W-28; garden eye is authority.
- **Deliverable:** denser Path A tip-web; `garden` loads updated young/mature/veteran — judge outer canopy fill vs prior sparse rim.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260718-29`
- **from:** Chris
- **said:** Took a few screenshots. Still very sparse, though the m is getting there. Need to space trees farther apart; arrange as isosceles triangle with L on the far corner.
- **status:** partial — mature canopy improving; density still short (two densify passes done — do not densify again this package); layout FAIL (row too tight) → triangle spacing next

## WORK_PACKAGE `tree-sculptor-W-20260718-30` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-6` (garden layout)
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris W-29: space farther; isosceles with L far)
- **Hypothesis:** Crowns collide in a 22 m E–W row; placing young+mature on an 80 m near base and veteran at the far north apex (isosceles legs ~60 m) separates silhouettes for review without another tip densify (W-28+W-29 two-struck).
- **Changed paths:** `eval_plot_builder.gd`, `docs/tree_sculptor.md`, `tmp/tree_sculpt/garden_w30_layout.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** `timeout 90 xvfb-run … /home/chris/bin/garden` log lines: young (−139.0, 190.0), mature (−59.0, 190.0), veteran (−99.0, 145.0); isosceles base=80m legs=60m L at Z=145; 3 species sculpt review; 4 labels. Math check: equal legs.
- **Deliverable:** `garden` opens sculpt stages as isosceles triangle with L on far corner — judge spacing (not canopy densify).
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## VERDICT on `tree-sculptor-W-20260718-30` (+ canopy status after W-29 densify)
- **from:** Chris
- **said:** Mature and veteran models are pretty much done. New tip branches connect skeleton to end leaves — just need to place leaf cards along those new branches in clusters. Expect over GPU budget; learn the right growth first, efficiency later. Young is still a design problem: branches reach *down* to leaves (arch-up-then-down is for old/heavy wood; wrong on young). Skeleton must reach *up* to leaf cards — failed before for lack of skeleton growth skill; now we know how.
- **status:** accepted_direction — mature/veteran finish = along-branch card clusters on tip hosts (not another host densify); young = separate upward-reach skeleton redesign; budget overshoot allowed for method proof



## WORK_PACKAGE `tree-sculptor-W-20260718-31` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris 2026-07-18 — m/L pretty much done; cards along tip branches in clusters; budget overshoot OK; young = separate upward redesign`
- **Hypothesis:** One tip-pin sprig per tip host leaves the outer shell sparse; dense along-branch cluster stations on frozen tip hosts (no further host densify — W-28+W-29 two-struck) fill mature/veteran canopy the right way first.
- **Changed paths:** `scripts/tree_sculpt/sculpt_core.py`, `scripts/tree_sculpt/tip_web.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/london_plane_*_review.png`, `tmp/tree_sculpt/rebuild_w31_cluster.log`, `tmp/tree_sculpt/godot_import_w31.log`, `tmp/tree_sculpt/garden_w31.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Recompile from frozen blend (scaffold unrecreated) exit 0. Tip hosts unchanged 124/1593/1035. Cards young/mature/veteran **2976 / 38232 / 24840** (was 124/1593/1035). Bare tris unchanged. Mature foliated 446364 tris. Godot `--import` exit 0. `garden` loaded all three sculpt stages at isosceles positions. Headless m/L sheets show much denser outer foliage along tip filigree vs W-29 tip-pin; garden eye is authority. Young droop habit unchanged (next package).
- **Deliverable:** along-branch card clusters on Path A tip hosts; `garden` for m/L canopy verdict.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- After tip-host densify is two-struck, canopy fill is card *coverage along hosts*, not more hosts.

## VERDICT on `tree-sculptor-W-20260718-31`
- **from:** Chris
- **said:** Mature and veteran are genuinely good-looking, but not the right shapes. Questions leaf placement targets and/or skeleton adaptations that chase them. Veteran loses its peak as branches bend under weight. Mature is the most convincing London plane of the bunch but more rounded at the bottom than any refs. Want target shapes grounded in photographs and the tree life/growth model before further sculpt.
- **status:** rejected_shape — m/L appearance ≠ habit PASS; establish target shapes before retarget (not another densify/cluster pass)

## WORK_PACKAGE `tree-sculptor-W-20260718-32` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1` (habit acceptance)
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `LOW` (brief only; no mesh/code change)
- **Approval:** `required — accept habit criteria; pick retarget order A|B|C`
- **Hypothesis:** Mature bottom-bulb and veteran peak-loss match what Path A tip hosts and scaffold droop aim at (legacy tip_web `_P_M` mid-sphere and `_P_L` below-mid-widest / tip 0.15); locking sculptor PASS to photo+§10 habit (high open mature underside; veteran peak retained under gravity-bent outer wood) will redefine the next retarget away from card densify.
- **Changed paths:** `docs/tree_sculptor.md`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Read Chris W-31 garden verdict; two-strike check (W-28/W-29 densify already two-struck — this is not densify); compared bare+foliated reviews (`tmp/tree_sculpt/london_plane_{mature,veteran}_{bare_,}review.png`) to habit refs (`A149-03_hero_l.jpg`, `london-plane-central-park-trees-great-trees-nyc11.jpg`, `Looking_across_at_the_large_London_Plane_trees_in_Lincolns_Inn_Fields.webp`, majestic branch_structure); confirmed tip_web still copies leafback `_P_M`/`_P_L`; confirmed create_london_plane mature/veteran authored droop; cross-checked `docs/london_plane_growth_architecture.md` §10 (taller-to-balanced mature; weeping tips ≠ lost peak).
- **Deliverable:** Habit acceptance section in `docs/tree_sculptor.md` — await Chris accept + A/B/C retarget order.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Good-looking foliage can still fail habit; shape PASS is photo+growth form, not card density.

## WORK_PACKAGE `tree-sculptor-W-20260718-33` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `DECISION_REQUIRED`
- **Risk:** `LOW`
- **Approval:** `required — Chris accept habit criteria; pick retarget order A|B|C`
- **Hypothesis:** Mature bottom-bulb and veteran peak-loss match what Path A tip hosts and scaffold droop aim at (legacy tip_web `_P_M` mid-sphere and `_P_L` below-mid-widest / tip 0.15); locking sculptor PASS to photo+§10 habit (high open mature underside; veteran peak retained under gravity-bent outer wood) will redefine the next retarget away from card densify.
- **Changed paths:** `docs/tree_sculptor.md`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Read Chris W-31 garden verdict; two-strike check (W-28/W-29 densify already two-struck — this is not densify); compared bare+foliated reviews (`tmp/tree_sculpt/london_plane_{mature,veteran}_{bare_,}review.png`) to habit refs (`A149-03_hero_l.jpg`, `london-plane-central-park-trees-great-trees-nyc11.jpg`, `Looking_across_at_the_large_London_Plane_trees_in_Lincolns_Inn_Fields.webp`, majestic branch_structure); confirmed tip_web still copies leafback `_P_M`/`_P_L`; confirmed create_london_plane mature/veteran authored droop; cross-checked `docs/london_plane_growth_architecture.md` §10 (taller-to-balanced mature; weeping tips ≠ lost peak). No mesh/GLB/blend change.
- **Deliverable:** Habit acceptance section in `docs/tree_sculptor.md` § Habit targets — await Chris accept + A/B/C retarget order.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`
- **Note:** Supersedes W-32 ledger Risk field only (`LOW` plus parenthetical failed schema-v2 exact-token check). Prior VERDICT on W-31 and W-32 substance unchanged.

## VERDICT on `tree-sculptor-W-20260718-33`
- **from:** Chris
- **said:** continue, unfreeze skeletons
- **status:** accepted — habit criteria PASS/FAIL locked; unfreeze scaffold wood; retarget order **C** (envelope tables + scaffold droop/peak together); tip-host *count* still frozen (W-28/W-29 densify two-struck)

## WORK_PACKAGE `tree-sculptor-W-20260718-34` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris 2026-07-18 — continue, unfreeze skeletons (habit C)`
- **Hypothesis:** Mature bottom-bulb and veteran peak-loss come from mid-sphere `_P_M` / tip-collapsed `_P_L` plus heavy scaffold droop; unfreezing and retargeting both (order C) raises the mature crown base / opens the underside and restores a veteran crest in bare+foliated reviews.
- **Changed paths:** `scripts/tree_sculpt/tip_web.py`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{mature,veteran}.glb`, `tmp/tree_sculpt/review_{mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/london_plane_{mature,veteran}_{bare_,}review.png`, `tmp/tree_sculpt/rebuild_w34_habit.log`, `tmp/tree_sculpt/godot_import_w34.log`, `tmp/tree_sculpt/garden_w34.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild `TREE_SCULPT_REVIEW_STAGES=mature,veteran` exit 0. Tip hosts mature/veteran 1132/1050 (terminals 358/256; shells 1920/1260 unchanged). Mature bare 320112 tris / cards 27168 / cc 1586 / clear_bole_model_m 1.523 (foliated); veteran bare 255816 / 25200 / 1376. Godot `--import` exit 0. `garden` loaded sculpt m/L at isosceles positions. Headless bare sheets show raised mature low limbs + veteran `v_crown`; garden eye is habit authority vs W-31 bottom-bulb / lost-peak.
- **Deliverable:** habit order-C retarget; `garden` for m/L shape verdict.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Habit PASS is photo+§10 form; card density can look good while shape still fails (W-31→W-33).


## VERDICT on `tree-sculptor-W-20260718-34`
- **from:** Chris
- **said:** Let's try this: find a reference photo representative of each tier; use Inkscape or any tools we have (or say what to install); end product should have the same shape and apparent skeleton as the reference.
- **status:** accepted_direction — abandon abstract envelope-habit grinding; lock one photo per stage; photo-match shape + apparent skeleton (overlay-verified)

## WORK_PACKAGE `tree-sculptor-W-20260718-35` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `Chris 2026-07-18 — photo per tier; match shape + apparent skeleton`
- **Hypothesis:** If one locked photograph per stage is habit authority and overlays compare bare-front silhouette to that photo, then reshaping scaffold (starting with veteran toward Lincolns Inn upright leaders) will move cyan onto the photo's primary forks — not another tip-densify or abstract `_P_*` pass.
- **Changed paths:** `scripts/tree_sculpt/ref_habit_overlay.py`, `scripts/tree_sculpt/create_london_plane.py`, `scripts/tree_sculpt/tip_web.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/habit_refs/*`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/london_plane_*_review.png`, `tmp/tree_sculpt/rebuild_w35_habit.log`, `tmp/tree_sculpt/godot_import_w35.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Overlay script exit 0 → `tmp/tree_sculpt/habit_refs/{young,mature,veteran}_habit_overlay.png`. Rebuild `TREE_SCULPT_REVIEW_STAGES=young,mature,veteran` exit 0. Tip hosts 124/1132/826 (shell 288/1920/1260 unchanged). Veteran bare 231624 tris / cards 19824 (was umbrella hang). Godot `--import` exit 0. **Observed:** veteran cyan still goblet-fills vs Lincolns Inn few heavy ascending limbs — scaffold identity not PASS; method + locked refs are the deliverable for verdict.
- **Deliverable:** locked per-stage habit refs + Pillow overlay pipeline; veteran first upright retarget for eye; Inkscape not installed (optional).
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Habit photo-match needs primary-fork identity on the overlay; tip-shell fill can look "close" in silhouette while the apparent skeleton is still wrong.

## VERDICT on `tree-sculptor-W-20260718-35`
- **from:** Chris
- **said:** Veteran reference doesn't tell you anything about the tree's shape. Mature reference looks more like a veteran tree. Small is getting there; may have branches too thick.
- **status:** rejected_refs — Lincolns Inn FAIL (no whole-tree shape); nyc11 reclassified as veteran-like; young keep + thin wood; swap locked refs before next m/L retarget

## WORK_PACKAGE `tree-sculptor-W-20260718-36` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris W-35: swap refs; thin young)
- **Hypothesis:** Dropping Lincolns Inn (trunk crop), promoting nyc11 to veteran, locking image-3172802200 as mature, and thinning young laterals will give whole-tree habit plates and a less clubby young cyan overlay — without another tip densify or m/L scaffold retarget yet.
- **Changed paths:** `scripts/tree_sculpt/habit_refs.py`, `scripts/tree_sculpt/ref_habit_overlay.py`, `scripts/tree_sculpt/create_london_plane.py`, `scripts/tree_sculpt/tip_web.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/habit_refs/*`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/rebuild_w36_habit.log`, `tmp/tree_sculpt/godot_import_w36.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild exit 0; tip hosts still 124/1132/826. Overlays rewritten with new plates. Young primary attach 0.95→0.55, tip_frac 0.28→0.22, secondary ×0.70. Bare tris y/m/L 35280/320112/231624; cards 2976/27168/19824. Godot `--import` exit 0. Observed: new mature/veteran plates show full crowns; young cyan still thicker than nursery stem (one thin pass — eye is authority).
- **Deliverable:** W-36 locked refs + overlays; thinned young for eye.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- A trunk close-up cannot be a habit lock — whole-tree shape must be visible in the plate.

## VERDICT on `tree-sculptor-W-20260718-36`
- **from:** Chris
- **said:** Mature reference is not a complete shell, but imagination can fill it in. L and M overlays show how poorly they fit the references.
- **status:** partial_refs_ok_fit_fail — keep W-36 mature plate (incomplete shell OK); m/L scaffolds FAIL photo-match on overlays; retarget primary forks next (not ref swap, not densify)

## WORK_PACKAGE `tree-sculptor-W-20260718-37` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `not_required` (Chris W-36: keep mature plate; m/L overlays FAIL fit)
- **Hypothesis:** Mature/veteran cyan fails because thick scaffold is still a bushy mid-sphere / wide mushroom that does not follow the locked photos' few long primary limbs; rewriting those primaries (longer low mature reach, taller nyc11 V-fan, softer secondary lift) moves cyan onto the photo forks without densify or ref swap.
- **Changed paths:** `scripts/tree_sculpt/create_london_plane.py`, `scripts/tree_sculpt/tip_web.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{mature,veteran}.glb`, `tmp/tree_sculpt/review_{mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/london_plane_{mature,veteran}_{bare_,}review.png`, `tmp/tree_sculpt/habit_refs/*`, `tmp/tree_sculpt/rebuild_w37_habit.log`, `tmp/tree_sculpt/godot_import_w37.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Rebuild `TREE_SCULPT_REVIEW_STAGES=mature,veteran` exit 0. Tip hosts mature/veteran 1182/686 (shell 1920/1260 unchanged; was 1132/826). Mature bare 239976 tris / cards 28368 / cc 1438; veteran bare 185400 / 16464 / 940. Godot `--import` exit 0. Overlays regenerated. Observed: mature bare shows longer low spread + less mid kink vs W-36 flat-top bush; veteran narrower ascending V vs prior mushroom — garden/overlay eye is habit authority for fork identity.
- **Deliverable:** W-37 m/L photo-match retarget; judge `tmp/tree_sculpt/habit_refs/{mature,veteran}_habit_overlay.png`.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Incomplete canopy in a locked plate can still be habit authority if whole-tree shape and primary forks are readable (Chris W-36).

## VERDICT on `tree-sculptor-W-20260718-37`
- **from:** Chris
- **said:** not matching at all. maybe we should use inkscape on the references. we do have inkscape installed.
- **status:** rejected_fit — W-37 procedural photo-match FAIL; two-strike with W-36; next = Inkscape traces of locked plates (not another global scaffold tweak)

## WORK_PACKAGE `tree-sculptor-W-20260718-38` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `not_required` (Chris W-37: use Inkscape on refs; flatpak Inkscape 1.4.4 present)
- **Hypothesis:** If named primary polylines are hand-traced in Inkscape on the locked mature/veteran plates and scaffold is rebuilt from those paths (not another procedural fan), cyan thick wood will land on the photo's visible forks.
- **Changed paths:** `scripts/tree_sculpt/inkscape_habit.py`, `scripts/tree_sculpt/traces/{mature,veteran}_primaries.svg`, `scripts/tree_sculpt/create_london_plane.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{mature,veteran}.glb`, `tmp/tree_sculpt/habit_refs/*`, `tmp/tree_sculpt/review_{mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/rebuild_w38_habit.log`, `tmp/tree_sculpt/godot_import_w38.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** `flatpak run org.inkscape.Inkscape --version` → 1.4.4. `inkscape_habit.py mature veteran --export-png --json` exit 0. Rebuild `TREE_SCULPT_REVIEW_STAGES=mature,veteran` exit 0. Tip hosts 832/606 (shell 1920/1260 unchanged). Mature bare 152496 tris / cards 19968; veteran bare 135144 / 14544. Godot `--import` exit 0. Overlays regenerated. Observed: bare fronts show high fork + sparse primaries under tip-host nest; eye on inkscape_trace + habit_overlay is authority for fork identity vs W-37.
- **Deliverable:** Inkscape trace pipeline + first m/L primary SVGs wired into create; judge overlays.
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- After two procedural photo-match fails, primary-fork authority is Inkscape path traces on the locked plate — not another create_london_plane fan tweak.

## VERDICT on `tree-sculptor-W-20260718-38`
- **from:** Chris
- **said:** We are working on an automated pipeline for tree models; London plane is first; doing any part by hand is out of the question. Look at enough examples (internet or local) to understand what shape each tier ought to have. Already know how to draw a good skeleton — now learn to draw the skeleton *to the shape*. Same problem as Mtree.
- **status:** rejected_hand_method — Inkscape hand traces out; automated corpus→shape→skeleton-fit is the method

## WORK_PACKAGE `tree-sculptor-W-20260718-39` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `MEDIUM`
- **Approval:** `not_required` (Chris W-38: automated pipeline; no hand; skeleton-to-shape)
- **Hypothesis:** If primary tips are placed on the locked-plate crown silhouette measured from a multi-photo corpus (tip length an OUTPUT of the envelope, not a hand SVG or fan parameter), cyan thick wood will terminate on the photo crown edge instead of an independent scaffold.
- **Changed paths:** `scripts/tree_sculpt/shape_fit.py`, `scripts/tree_sculpt/habit_refs.py`, `scripts/tree_sculpt/create_london_plane.py`, `scripts/tree_sculpt/ref_habit_overlay.py`, `docs/tree_sculptor.md`, `models/tree_sources/london_plane.blend`, `models/trees/london_plane_sculpt_{young,mature,veteran}.glb`, `tmp/tree_sculpt/habit_refs/*`, `tmp/tree_sculpt/review_{young,mature,veteran}/`, `tmp/tree_sculpt/review_*_bare/`, `tmp/tree_sculpt/rebuild_w39_shape.log`, `tmp/tree_sculpt/godot_import_w39.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** `python3 scripts/tree_sculpt/shape_fit.py young mature veteran` exit 0 — envelopes crown_h≈599/581/599 px (was ~52px fragment before segment fix); tip hosts 155/661/710 shell still 288/1920/1260. Rebuild Blender exit 0. Godot `--import` exit 0. Overlays rewritten. Bare tris y/m/L 62388/126108/141768; cards 3720/15864/17040. Observed: `{stage}_shape_fit.png` primaries reach plate silhouette; garden/overlay eye is habit authority for fork identity vs W-38 empty SVG method.
- **Deliverable:** automated corpus shape measure + silhouette raycast/envelope primary fit; judge `tmp/tree_sculpt/habit_refs/{young,mature,veteran}_{shape_fit,habit_overlay}.png`
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Automated species pipeline forbids hand-authored skeleton authority (Inkscape paths, manual Bézier edits); tip length must be an OUTPUT of a measured photo silhouette, or you are back in the Mtree parameter-grind.


## VERDICT on `tree-sculptor-W-20260718-39`
- **from:** Chris
- **said:** You need better references for all three tiers. A good reference shows the entire tree, alone or easy to separate from its environment.
- **status:** rejected_refs — W-39 locks FAIL isolation bar (nursery+person; incomplete/cluttered mature; nyc11 crown merges into woodland); swap all three before judging shape_fit

## WORK_PACKAGE `tree-sculptor-W-20260718-40` · 2026-07-18

- **Thread:** `cpw/tree-sculptor`
- **Items:** `TS-1`
- **Classification:** `REPRODUCED_DEFECT`
- **Risk:** `LOW`
- **Approval:** `not_required` (Chris W-39: better alone/whole-tree refs for all three tiers)
- **Hypothesis:** Current locked plates fail the isolation bar (person/clutter/overlapping crowns); locking three alone whole-tree photographs will make silhouette measure and overlays readable against a clean crown edge — without another scaffold retarget yet.
- **Changed paths:** `scripts/tree_sculpt/habit_refs.py`, `scripts/tree_sculpt/shape_fit.py` (comments), `docs/tree_sculptor.md`, `credits.txt`, `reference_photos/london planetree/{Platanus_xhispanica_habit.jpg,london_plane_geograph_7338525.jpg,london_plane_geograph_7373536.jpg,london_plane_geograph_7923058.jpg,platanus_hispanica_poznan_dendrological_2.JPG}`, `tmp/tree_sculpt/habit_refs/*`, `tmp/tree_sculpt/rebuild_w40_refs.log`, `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **Verification:** Downloaded/copied CC BY-SA Commons/Geograph whole-tree photos; `shape_fit.py young mature veteran` exit 0 (aspects 0.62/0.71/0.68); `ref_habit_overlay.py` exit 0. Observed plates: young alone vs sky (no person); mature alone in field vs sky; veteran bare crown vs sky (houses behind bole only). Scaffold/GLB unchanged — cyan mismatch on new plates is expected until accepted locks.
- **Deliverable:** W-40 locked alone plates + overlays at `tmp/tree_sculpt/habit_refs/{young,mature,veteran}_{ref_plate,habit_overlay}.png`
- **Git:** `uncommitted`
- **Status:** `awaiting_user_verdict`

## Staged lessons
- Habit lock bar: entire tree, alone or easy to separate from its environment — person/nursery clutter, incomplete shells, and crowns that merge into background woodland fail before any scaffold fit is judged.

## 2026-08-25 — DESIGN turn: sculpt_kb / botany knowledge base (no sculpt work)
- **Hypothesis:** Claude's tree-judging failure is protocol, not perception — fixable at our
  level via retrieval: exemplar meshes (human sculpts that pass Chris's instant look) are
  measurable ground truth; treeness is CATEGORICAL (binary verdict + named giveaway, no
  scores); envelope derived from exemplars, never dialed; two gates (treeness → plane-ness).
- **Change:** wrote `docs/sculpt_kb/DESIGN.md` (commit `f234e5c`) — specimen cards (photo +
  mesh + skeleton stats.json + turntable + in-game captures + part↔part correspondence
  sheets), pooled ENVELOPE/PRINCIPLES/TRANSLATION layers, first unit = ONE specimen
  end-to-end with Chris verdicting the card FORMAT.
- **Measurement:** none — design only, no render, no bar touched.
- **Verdict:** PENDING — Chris sign-off on DESIGN.md (canonical change: new KB umbrella).

## 2026-08-25 (later) — DESIGN amendment: three-subject blind pre-test gates the KB
- **Hypothesis:** the KB's perceptual half ("reference improves a judge") is unproven; a
  provenance-keyed blind treeness exam answers it without building. Chris's addition:
  grade **Qwen-VL vs frontier Claude vs Chris himself** on identical items — his score is
  the human ceiling + exam validity check + exemplar curation in one pass.
- **Change:** `docs/sculpt_kb/DESIGN.md` § "Pre-test" added; specimen-card build now
  explicitly gated behind it. First unit of work redefined = assemble answer-keyed exam +
  pull a Qwen-VL (8 GB, llama.cpp mtmd) — grind lane's Qwen3-Coder has no vision.
- **Measurement:** none — design only.
- **Verdict:** PENDING — Chris sign-off on amended DESIGN.md.

## 2026-08-25 (later still) — DESIGN amendment: delegated library expansion
- **Hypothesis:** exam needs more keyed items; collection is grind → serial sonnet
  subagents with manifest deliverables. Risks pinned: (1) open-web AI/render "photos"
  poison the pass-side key → provenance-trustworthy sources only (iNat research-grade,
  Wikimedia+EXIF, FNA/USDA/FEIS); (2) Chris must NOT see candidate exemplars during
  curation (text lists only) or his exam blindness dies; (3) in-app browser default,
  his Chrome only for login-gated downloads on an approved list.
- **Change:** DESIGN.md pre-test § "Library expansion" added. Recon: `reference_photos/`
  already holds ~550 files / ~24 species incl. london planetree — audit + provenance-check
  it FIRST (legacy items have no recorded source).
- **Measurement:** none — design only.
- **Verdict:** PENDING — Chris sign-off on amended DESIGN.md.
