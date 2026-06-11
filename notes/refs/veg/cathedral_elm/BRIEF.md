# BRIEF — Cathedral American Elm, Literary Walk (Ulmus americana)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md). Obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md) (this is the
> §5 hero / signature-convergence species).

- **Archetype key:** `cathedral_elm` (generator/runtime name; the Literary Walk allée specimens)
- **Layer:** canopy (emergent — the tallest layer of the Mall)
- **Tier coverage:** `_m` / `_l` only (TIER_BOUNDS; no `_s` — the allée trees are all mature). `_l` is the Literary Walk specimen and must read unmistakably grander than plain `elm_l`.
- **Brief written:** 2026-06-11 · **by:** Opus 4.8 (Fable-5-spec execution session)

## Reference set
Sourced in the user-confirmed order. iNaturalist CP confirms the population is real;
the **Literary Walk walk-through video is the primary habit + convergence reference**
(reminder 2 — the value is the crowns converging, which a still can't carry; a
walk-through shows the arch and how it reads in context).

- [x] **iNaturalist, CP-geofiltered** — API count: **75 research-grade _Ulmus americana_
  observations** inside the park bbox (40.764–40.800 N, −73.981 to −73.949 W). Confirms
  the actual Mall/Literary Walk population. (Web UI scraping 403s; API count only.)
- [x] **Walk-through video (PRIMARY)** — *"The Mall & Literary Walk, Central Park | Iconic
  Tree-Lined Promenade,"* Pinay New Yorker, 2025-11-17, 10:23, silent.
  claudetube `video_id=bCQ0TCUSuBA`. Frames inspected (medium q): **02:30** (the
  convergence — arching limbs from both rows meet over the centerline), **04:00** (bare-ish
  branch architecture, high vase fork), 01:30, 05:20, 06:30, 09:00 (Shakespeare statue,
  south end). Late-autumn capture → **doubles as the bare-structure reference** (gold,
  semi-translucent, heavy leaf drop — habit fully legible).
- [x] **Habit, summer mass** — authoritative form (Morton Arboretum, NCSU Extension,
  Wikipedia): vase/fountain, "branches like spreading fountains," cathedral ceiling.
- [x] **Winter bare structure** — video frames 02:30/04:00 (late-autumn semi-bare), plus
  Morton/Wikipedia ("silhouette open and graceful," vase prominent when bare).
- [x] **In a stand/allée (interaction)** — video, the whole length: four rows flanking the
  straight allée, opposite crowns reaching to the centerline.
- [x] **Bark detail** — NCSU/Clemson/Wikipedia (frames too low-res for bark): gray-brown,
  flattened ridges + furrows, interlacing on mature bark. (Style already `furrowed` family.)
- [x] **Leaf detail** — [[reference-tree-canopy-data]] §2: ovate-elliptic, doubly serrate,
  asymmetric base (diagnostic), **distichous / 2-ranked → flat spray-like branch planes**.
- [x] **Fall color** — video (gold/yellow, dropping by mid-Nov) + Morton ("yellow in fall").
- [n/a] **Bloom** — not showy (tiny reddish wind-pollinated flowers, pre-leaf; ignore).
- [x] **Wind/behavior** — video motion + canopy-data planar-spray note (see §5).

## 1. Habit — how it flows over itself
- **One-liner:** *tall, clean single trunk rising ~⅓ of height, then dividing into several
  major limbs that sweep UP and OUT and then ARCH over — a high vase/fountain whose outer
  branchlets and fine 2-ranked sprays droop at the tips; the ceiling is high overhead, you
  walk under it.*
- **Overall form / crown shape:** vase / fountain (wine-glass). Crown spread ≈ height on a
  mature open allée tree (9–18 m spread, 18–24 m tall — [[reference-tree-canopy-data]] §2).
- **Aspect (width : height):** ~1 : 1 to 1.2 : 1 (spread can equal or exceed height).
- **First branch / fork height:** **HIGH — ~0.30–0.45 of total height** (video: long clean
  trunks before the vase opens; these are pruned-up allée trees). **This is a correction:
  the current `cathedral_elm` `SPECIES` forks at `branch_start=0.14` — too low; the low fork
  makes a bush, not a cathedral ceiling you pass beneath.** Raise toward ~0.30–0.40.
- **Branch character:** several heavy ascending limbs (15–30 ft up on the real tree) that
  arch outward then over; angle wide (~55° from vertical at mid-limb); fine terminal twig
  sprays are pendulous and droop. Limbs taper gradually, not stubby.
- **Asymmetry:** allée trees lean their long axes toward the path (light + training); real
  rows are a mix of mature wide vases and younger narrower replants (post-DED), with gaps —
  drives the variation envelope (§7).

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** crowns interlace into a **continuous arched ceiling over the
  path** — the four rows' opposite limbs reach to the centerline and meet/overlap overhead
  (video 02:30/05:20 show the partial autumn tunnel; summer closes it). The single elm is
  not the asset — the convergence is.
- **Target stand reading:** *standing in the allée at summer noon, a continuous arched
  canopy tunnel overhead, crowns from facing rows meeting, dappled light on the pavement —
  a Gothic-arch nave, not a row of separate balls with sky between them.* (This is the §5
  hero DoD in `tree_model_redesign.md`.)

## 3. Density
- **Bucket:** opaque (one of the highest-shade deciduous; dense layered crown).
- **Real number:** LAI **4.5–6.0**; intercepts ~80–90% of direct sun at peak
  ([[reference-tree-canopy-data]] §2). Distichous planar sprays maximize interception.
- **Light transmission:** ~5–15% at peak foliage. (Autumn video reads thinner — seasonal.)

## 4. Detail
- **Bark:** gray-brown; flattened ridges with furrows, interlacing on mature trunks
  (`furrowed`-family style). Tall clean bole below the vase.
- **Leaf:** ovate-elliptic, doubly serrate, **asymmetric base** (diagnostic), 10–15 cm;
  borne the full length of branchlets (NOT tip-clustered), **2-ranked → flat sprays**.
- **Summer color:** dark green. · **Fall color + timing:** yellow / gold, dropping
  relatively early & cleanly (mid-Nov video already heavy drop). · **Bloom:** n/a (not showy).

## 5. Behavior
- **Wind character:** heavy arching limbs sway slowly and gracefully (stiff at the trunk,
  mobile toward the tips); the fine pendulous 2-ranked sprays flutter — a slow large-limb
  sway with a faster fine-spray shimmer. Tune the existing per-species wind toward
  "graceful slow arch sway," not the trembling-birch or stiff-oak extremes.
- **Seasonal timeline:** flush (Apr) → dense dark-green summer mass → yellow/gold fall
  (Oct–Nov) → relatively clean early drop → bare high vase in winter (the signature
  silhouette) → inconspicuous pre-leaf flowers (spring, ignore visually).

## 6. The one unmistakable thing
The **high fountain/vase form whose arching limbs from facing rows meet overhead into a
continuous Gothic-arch tunnel.** If the trunk forks low, or the crowns don't reach the
centerline and close, it is not a cathedral elm — it's a generic shade tree.

## 7. Per-instance variation envelope
- **Varies across seeds/instances:** fork height (0.28–0.45), crown width, lean magnitude &
  direction (toward path centerline ± jitter), limb asymmetry, height (DBH-driven), maturity
  (a few narrower younger-replant variants among the wide mature vases), density.
- **Variant count:** 5 (cathedral_elm is a low-census signature species — keep 5; spend the
  envelope on fork-height + lean spread, which carry the allée's read).

## 8. What this brief drives (build mapping)
- **Generator/params** (`generate_trees_mtree.py`, `cathedral_elm` @ ln 434): **raise
  `branch_start` 0.14 → ~0.30–0.40** (high clean trunk); keep/strengthen the up-then-arch
  profile (`branch_angle` 55, moderate `branch_up_attraction`, drooping `sub_*` for pendulous
  sprays); push main-branch length so limbs reach across the path. Respect the mesher crash
  ceiling (`sub_density ≤ 0.7` at 30 m). `_l` grander than `_m`.
- **Textures:** `furrowed` bark; elliptic leaf already present.
- **Builder/placement** (`tree_builder.gd` / placement data): **add path-aware orientation**
  at Literary Walk (X≈−600, Z≈1420) — instances on opposite sides lean their long axis toward
  the path centerline so crowns converge (`tree_model_redesign.md` §5b). This is half the hero
  task; the model is the other half.
- **Perf budget:** fragment-bound — gain the ceiling from limb geometry + placement
  convergence, NOT extra card overdraw (`tree_model_redesign.md` §2). Perf gate ×5, no
  regression; Ramble/North Woods are worst-case — Literary Walk is lighter but still gate it.

## 9. Definition of Done (captures that validate this brief)
- [ ] Thumbnail reads as a high-vase elm, distinct from plain `elm` and from `oak`/`linden`.
- [ ] **In-game allée capture at Literary Walk, summer noon** — continuous arched canopy
  tunnel overhead, facing crowns meeting, matching video 02:30. *The allée is the validation
  unit, not one tree.*
- [ ] Tier handoff (base↔lod2 60 m, mesh↔impostor 240 m) + crossfade walk
  (`tree_model_redesign.md` §9).
- [ ] Dense allée shows no tiling (§7 — fork-height/lean spread reads as varied).
- [ ] Perf gate ×5 equal-or-better.
- [ ] User walk-around sign-off (compare against this same Literary Walk video).
