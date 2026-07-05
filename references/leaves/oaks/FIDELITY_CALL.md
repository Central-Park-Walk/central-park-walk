# Oak per-LOD-tier fidelity call + build order (Phase 2 required deliverable)

> **AUDIT NOTE — Q. cerris population, RESOLVED (2026-07-04, supersedes earlier accent call).**
> There are **TWO independent datasets and they do not conflict** — do not collapse them:
> - **NYC Street Tree Census** (on-disk: `convert_to_godot.py` SPECIES_MAP + `park_data.json`):
>   maps STREET trees, **excludes the Central Park interior**, and aggregates *Quercus* to
>   genus (2,613) with **no per-species oak count**. cerris is correctly absent here — this
>   dataset simply cannot see park oaks by species. Nothing to fix on-disk.
> - **Central Park Entire field survey** (Chaya & Barnard 2013; 19,600+ trees field-mapped;
>   oak breakdown 2,854 oaks / 18 spp via R. Cameron, Intl Oak Society 2014-05-25 —
>   https://www.internationaloaksociety.org/content/new-map-new-york%27s-central-park):
>   **Turkey oak = 356, the 3rd most populous oak in the park** (after pin ≈half of 2,854
>   and red 584). Independent ground-truth field data, not modeled.
>
> **CONSEQUENCE — REVERSED:** Turkey oak is **NOT accent-tier and NOT a sawtooth re-skin.** At
> 356 individuals it is a genuinely populous park oak and **warrants its own distinct-geometry
> slot** (its own skeleton — large *Q. cerris* conical-young→broad-rounded-dense — plus the
> Cerris bristle-toothed leaf card and orange-fissured bark). The "fold Turkey into Skeleton A
> / re-skin sawtooth / accent" statements in the body below are **superseded by this note.**
> Fidelity basis = the *Central Park Entire* count (356), NOT the genus-aggregated street
> census. (Sawtooth is now out of the 3-oak roster; its dossier is archived.) The full per-tier
> 3-oak fidelity call is re-derived in the new Phase 2; this note fixes the Turkey tier now.

**Question (Chris, 2026-06-24):** for the park's oaks, decide *which skeletons* and *which
textures* to build to best represent them **on a 3060 Ti rendering a forest at >45 fps
@ 1080p** — and **where a difference can't be portrayed noticeably at gameplay distance,
consolidate.** Answer **per LOD tier** (near lod0 / mid lod1 / far impostor), not as one
global call. Roster + data: `ROSTER.md` + the 7 `oak_*.yaml` dossiers.

## Constraints that shape the call
- **ONE variant per skeleton per size tier** (Chris, until london plane's impostor path is
  fixed). So every distinct skeleton/card is a **flat, un-amortized tax** → strong
  consolidation bias, and **fewer distinct impostors directly de-risks the current impostor
  problem**.
- **Budget reality (`trees.md` §4f/g, `tree_model_redesign.md` §2):** trees are
  **fragment-shading-bound**, not geometry-bound. Extra branch tris are ~free; extra/larger
  **leaf cards + overdraw** and **extra impostor atlases (VRAM + bake)** are the real costs.
  Distinct *meshes* cost draw batches + VRAM + authoring + an impostor bake each.
- **What carries identity at each range** (`tree-pipeline-lessons.md` banner): leaf **shape
  resolves only < ~30 m**; mid distance = **crown silhouette + density + color**; far =
  **gross silhouette + color mass**. Impostor atlases are **per species-tier, not per
  variant** — variant diversity already vanishes at impostor range by design.

## The three natural clusters (from the dossiers)
| cluster | members | leaf | crown habit | fall |
|---|---|---|---|---|
| **Lobatae** | pin, red, scarlet | bristle-**lobed** (pin/scarlet deep, red moderate) | **pin = excurrent/narrow/drooping**; red & scarlet = rounded/open | red / russet / **scarlet** |
| **White group** | white, swamp white | **rounded-lobe, no bristle** (swamp white shallower + bicolor underside) | broad rounded; white = massive horizontal limbs | wine-brown / **golden-brown** |
| **Cerris** | sawtooth, Turkey(cerris) | narrow **bristle-toothed** (sawtooth serrate, Turkey shallow-lobed-toothed) | rounded dense (Turkey larger) | yellow-**gold**, **marcescent** |

---

## Per-tier decision

### NEAR — lod0 (0–100 m): leaf shape + bark resolve → spend here
- **3 leaf cards** earn their keep (the silhouettes are genuinely different < 30 m):
  1. **Lobatae bristle-lobed** (pin, red, scarlet)
  2. **White-group rounded-lobe** (white, swamp white)
  3. **Cerris bristle-toothed narrow** (sawtooth, Turkey)
  - *Hold in reserve:* a 4th **deep-sinus Lobatae** card (pin/scarlet) only if Gate-1 shows
    red's moderate sinus vs pin/scarlet's deep sinus reads once instanced. Default: one card,
    differentiate pin/scarlet by skeleton + fall color, not a second card.
- **Bark:** cheap per-species material (shader style + tint), not geometry. Worth doing where
  it reads: **white-oak pale flaky** and **Turkey-oak orange-fissured** are the two genuinely
  distinctive barks; pin/red/scarlet/sawtooth share the furrowed style.
- **Skeleton:** **pin's excurrent + drooping-lower-limb habit reads strongly overhead** →
  its own skeleton. Everything else on the shared rounded skeleton.

### MID — lod1 (90–200 m): leaf shape gone → crown silhouette + color only
- Leaf-card distinction **buys nothing** here. Identity = crown form + fall color.
- **Pin's narrow excurrent silhouette stays distinct** → keep Skeleton B.
- Red / scarlet / white / swamp white / sawtooth / Turkey are **all rounded crowns** →
  **not separable by shape**; separated only by **fall color** (red vs scarlet vs wine-brown
  vs gold) and density. → **shared skeleton + per-species fall texture/tint.** Strong
  consolidation. (White oak's wide horizontal limbs are the one *maybe* — see below.)

### FAR — impostor (>180 m): gross silhouette + color mass; minimize atlases
- Only two silhouette families survive: **pin (narrow excurrent)** and **rounded**.
- Within rounded, only **color mass** differs → ideally **one rounded-oak impostor atlas
  recolored per species via tint**, IF the runtime fall-color tint works through the impostor
  shader (the atlas bakes color in; a near-neutral tint like the existing `tier_brightness`
  calibration is the lever). Given the **active impostor difficulties**, this is also the
  safe play: **2 impostor silhouettes (pin, rounded)**, color by tint, and **defer
  per-species impostor atlases** until london plane's impostor path is settled.

---

## RECOMMENDATION

**Build 2 skeletons + 3 leaf cards; differentiate the 7 taxa by fall color + bark tint +
size tier + winter marcescence — all cheap (texture/material/runtime), not geometry.**

| asset | count | serves |
|---|---|---|
| **Skeleton A — rounded decurrent oak** | 1 (×s/m/l) | red (+ scarlet/white/swamp-white/sawtooth in the old 7-taxon plan; per-species crown-width/size tuning) |
| **Skeleton B — pin excurrent** (central leader, drooping lower limbs) | 1 (×s/m/l) | pin oak only |
| **Skeleton C — Turkey (Cerris)** — large conical-young → broad rounded dense | 1 (×m/l) | Turkey oak only (356 in park; distinct geometry per the audit note above — NOT folded into A) |
| **Leaf card — Lobatae bristle-lobed** | 1 | pin, red, scarlet |
| **Leaf card — white-group rounded-lobe** | 1 | white, swamp white |
| **Leaf card — Cerris bristle-toothed** | 1 | sawtooth, Turkey |
| per-species **fall-color texture + tint** | 7 | the primary differentiator at mid/far |
| per-species **bark tint/style** | (3 distinct: furrowed / pale-flaky / orange-fissured) | near only |
| **impostor atlases** | 2 (pin, rounded) + tint | far; deferred per-species atlases |

**This collapses 7 taxa → 2 skeletons + 3 cards.** It honors the one-variant tax (only two
skeleton authoring lines, two impostor bakes), de-risks the impostor work (fewer atlases),
and keeps card count/overdraw flat.

### Open splits to resolve at the gates (don't pre-build)
- **White oak → 3rd skeleton?** Its massive low horizontal limbs are the only rounded-crown
  habit that *might* read distinctly at mid range. Decide at the white-oak mid-tier review;
  default = Skeleton A tuned wider.
- **4th deep-sinus Lobatae card?** Decide at Lobatae Gate-1; default = one card.
- **Turkey oak — RESOLVED as distinct (see audit note).** At **356 individuals (3rd most
  populous park oak, Central Park Entire 2013)** it is NOT accent and NOT a sawtooth re-skin;
  it gets its own Skeleton C + Cerris card + orange-fissured bark. (Its absence from the
  on-disk NYC street census is a dataset-coverage artifact, not low abundance.)
- **Swamp white existence.** *(Out of the 3-oak roster — archived. Was: not confirmed in park
  data beyond the genus comment.)*
- **Intra-species cloning.** With one variant per skeleton/size, a dense same-species stand
  risks visible repeats. Lean on runtime per-instance yaw / non-uniform scale / slight lean +
  color/phenology jitter; accept some repetition as temporary until the variant count reopens.

---

## BUILD ORDER (Phase 3 — card first → S → approve in game → M/L; one color pass at a time)

1. **Skeleton A + Lobatae card → RED OAK** (the template). It's the most numerous oak, the
   broadleaf template, and *is* today's `oak` archetype (lowest risk). Card → red oak **_s**
   → **approve in game (Gate)** → **_m/_l**. *Also fix the mislabel:*
   `generate_trees_mtree.py:537` says "Pin Oak (Quercus palustris)" on red-oak params.
2. **Skeleton B → PIN OAK** (the hard net-new one — excurrent + drooping lower skirt; shares
   the Lobatae card). Do it early to de-risk: **_s → approve → _m/_l**.
3. **SCARLET OAK** — recolor pass on Skeleton A + Lobatae card; fall = vivid scarlet. (No new
   geometry; decide the deep-sinus card here.)
4. **White-group card + WHITE OAK** on Skeleton A (tuned wider) + pale flaky bark; decide the
   white-oak skeleton split at its mid-review. Then **SWAMP WHITE** as a recolor (golden fall
   + bicolor underside) — *only if park presence confirmed*.
5. **Cerris card + TURKEY OAK** — its own **Skeleton C** (large *Q. cerris*, conical-young →
   broad rounded dense), Cerris bristle-toothed card, orange-fissured bark, pale-gold late
   fall + winter marcescence. Distinct model is **justified by population** (356 / 3rd most
   populous park oak), not a placement guess. *(Sawtooth is out of the 3-oak roster — archived.)*
6. Downstream regen per `tree_model_redesign.md` §8 after each approved species; perf-gate ×5
   (60 open / 45 woodland).

**Validation that gates each consolidation:** for any "shared skeleton, color-only
difference" pair, capture the two side by side at the **mid and far** ranges; if they're not
distinguishable there (they shouldn't be by design), the consolidation is confirmed. If a pair
IS distinguishable and *should* be (e.g. pin vs red), that's the skeleton split working.
</content>
