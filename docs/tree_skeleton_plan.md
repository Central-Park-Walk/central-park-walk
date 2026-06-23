# Tree skeleton plan — the smart roster + per-species representation

**Status:** plan of record (2026-06-22). Supersedes the ad-hoc 14-archetype roster.
**Source of truth for:** which tree *models* (skeletons) we build, and how every
census species is represented on them.

This document is the **what/which**. The **how** — the hard-won build method — lives in
`docs/tree-pipeline-lessons.md`, `docs/tree-leaf-pipeline-brief.md`, and
`docs/tree_model_redesign.md`. Don't restate those here; they will drift. This file
points at them.

---

## 1. The rule that decides everything

> **A skeleton (a GLB model set) is earned only by a distinct silhouette at gameplay
> range (~15–150 m). Bark, leaf-cutout, summer/fall color, crown density, bloom, and
> clump-vs-single are *parameters* on a shared skeleton — never a reason to build a new
> model.**

Why it holds (the london plane lesson, 2026-06-22): **leaf shape only resolves within
~30 m** — past that a leaf is a colored fleck, then sub-pixel. So beyond ~30 m a species
is read entirely from **crown shape (skeleton) + color**. A 2-triangle card carries the
alpha silhouette + color identically to a 1000-triangle mesh. Geometry buys nothing where
shape stops resolving; it only costs frame time on a 3060 Ti in thick forest.

In code this rule is already the architecture: `ARCHETYPE_MODEL` maps species-identity →
GLB skeleton, and `PHENOLOGY_INDEX` maps species-identity → seasonal color, independently
(`tree_builder.gd`). A **fold** = repoint one `ARCHETYPE_MODEL` entry at a shared skeleton
and keep its phenology + bark. The london plane fold is a one-line change.

---

## 1b. Hard build laws (Chris, 2026-06-22) — non-negotiable, apply to EVERY model

Absolute. Where **any** older guidance conflicts — including the §4 checklist below, the
dated lessons in `docs/tree-pipeline-lessons.md`, or the london plane build that predates
these — **these win.**

1. **Build order: leaf card first, then the small model.** Perfect the leaf card and clear
   Gate 1 before any skeleton exists. Then sculpt the `_s` (small) model first; `_m`/`_l`
   derive from it. No skeleton work begins on an unapproved leaf.
2. **Leaf card = a real twig sprig: 2–4 leaves + their stems + a joining twig.** Never a
   bare single leaf, never leaves without a twig. The card's twig **is** the terminal
   ramification (see law 4).
3. **Branch diameter floor ≥ 0.05** on every skeleton (`min_twig_diameter`). No twig thinner
   than the floor — a sub-floor twig reads as a floating clump even when graph-connected.
   *Reconcile the existing per-tier table up to this floor* — `MIN_TWIG_DIAMETER` s 2.2 cm /
   m 3.2 cm currently sit below the l-tier's 5 cm (= 0.05) and must rise to meet it. (Confirm
   the unit matches the generator's `min_twig_diameter` convention when implementing.)
4. **Skeleton branch orders = trunk + primary + secondary ONLY. No tertiary or beyond.**
   Cap ramification at secondary: `cap_skeleton_depth()` `max_depth = 2` (was 4); prune every
   mesh vert with `hierarchy_depth > 2`. The leaf-card twig supplies the *visual* tertiary, so
   skeleton geometry past secondary is redundant and pokes out bare past the cards. Crown
   density therefore comes from **more secondaries + cards distributed along them**, not from
   deeper forks. (This supersedes the `_l = max_depth 4` / `depth_keep{1,2,3}` rule.)
5. **Leaf-card twigs attach directly to the primary/secondary branches, in patterns
   consistent with real-world data** — concentrated toward branch tips for tip-bearing
   species (plane, cherry, birch); spread along the branch for along-branch species
   (oak, elm). The per-species pattern is data-driven, never uniform.
6. **The trunk apex must not be left bare** — clad the growing apex (apex-band force-keep) —
   **unless the species data says a bare/exposed apex is a real feature** of that tree.
7. **Every leaf must connect to the trunk through branches** (the coherence law; validate with
   `check_foliage_connectivity.py`) — **unless the data says otherwise** for that species.
8. **Clear the tree cache + reimport after EVERY Blender redesign.** After any GLB regen:
   run `godot --headless --import`, then delete the cached `cache/trees/<species>_*.res` +
   `.cfg`, before any walk/eval. A stale `.scn`/`.res` silently serves the OLD model — this
   has cost whole sessions of "my change did nothing".

---

## 2. The roster — nine skeletons, all full rebuilds

Every current model predates the london plane method, so **all nine are ground-up
rebuilds, not retentions** — they must each satisfy the rebuild checklist in §4. The
"foliage gate" and "leaf-rep" columns are the per-species deltas the method forces.

| # | Skeleton | Trees | Foliage-order gate (species-specific!) | Leaf representation | Distinctiveness deltas (bark / fall color / bloom) |
|---|----------|------:|----------------------------------------|---------------------|----------------------------------------------------|
| 1 | **broad_dome** (oak) | 5,664 | **along-branch** for oak/linden; tip-biased for london_plane guest | `_s` structural, `_m`/`_l` cards | oak (furrowed bark, russet) · london_plane (exfoliating camo bark, drab yellow-brown) · linden (dense, yellow) · **generic deciduous** (neutral, heavy per-instance jitter) |
| 2 | **rounded_oval** (maple) | 1,538 | intermediate (tip-clustered + along-branch) | `_s` struct, `_m`/`_l` cards | maple (U-sinus leaf, vivid red/orange) · sweetgum (star leaf, crimson) · ginkgo (fan leaf, gold) |
| 3 | **small_ornamental** (cherry) | 1,327 | tip-biased | `_s` struct, `_m`/`_l` cards | cherry (pink bloom) · callery_pear (white bloom, dense teardrop) · magnolia (pink saucer, large leaf) |
| 4 | **vase** (elm) | 883 | **along full branchlet** | `_s` struct, `_m`/`_l` cards, **`_xl` = cathedral elm** | elm / zelkova / hackberry / hornbeam — yellow fall, muscular bark. cathedral_elm folds in as the **XL size tier of elm** (see fold note) |
| 5 | **open_compound** (honeylocust) | 166 | along-branch, sparse | compound cluster card | airy see-through, dappled, yellow fall — hosts pagoda, locust, ash, coffeetree, goldenrain |
| 6 | **slender** (birch) | 136 | tip-biased | `_s` struct, `_m`/`_l` cards | white-bark param; multi-stem / clump flag; poplar guest |
| 7 | **conifer_spire** | 129 | needle sheath (own path) | needle cards | **near ground-up** — replaces the lumped junk conifer; spruce/fir/young-pine/baldcypress/dawn-redwood |
| 8 | **weeping** (willow) | 9 | cascading whip (own data-driven path, not Mtree) | whip cards | finish the in-progress fountain redesign to the new spec |
| 9 | **tall_excurrent** | (now in generic) | along-branch, high crown, central leader | `_s` struct, `_m`/`_l` cards | **net-new model** — tulip tree (biggest accuracy gap), sweetgum, pin oak |

**Total placed trees accounted for: 9,852** (broad_dome 5,664 + rounded_oval 1,538 +
small_ornamental 1,327 + vase 883 + open_compound 166 + slender 136 + conifer 129 +
weeping 9; the folds below are already counted in their host's total).

### Folds — become a recipe row + one-line `ARCHETYPE_MODEL` repoint, no model
- `london_plane` → **broad_dome** (exfoliating bark, drab fall) — the lesson case
- `linden` → **broad_dome** (dense preset, yellow fall)
- `callery_pear` → **small_ornamental** (dense teardrop, white bloom)
- `magnolia` → **small_ornamental** (saucer bloom, big leaf)
- `ginkgo` → **rounded_oval** (fan cutout, gold fall) — caveat: young ginkgos are columnar;
  first Tier-2 promotion if that reads wrong
- generic `deciduous` → **broad_dome** (neutral tint + heavy jitter; no own model)
- `cathedral_elm` → **elm as an `_xl` size tier**, not a separate model (Chris, 2026-06-22).
  *Why (record it, per "understand why later"):* the Mall / Literary Walk "cathedral elms"
  are American elms historically given a wide, high-arching vase — that's the **same vase
  skeleton at XL scale + age**, not a different silhouette. Fold = add an `_xl` tier to the
  elm rebuild, repoint `ARCHETYPE_MODEL["cathedral_elm"] → "elm"` (currently its own model),
  and have `CATHEDRAL_ELM_ZONE` (tree_builder.gd) force the `_xl` tier for the Mall rows.
  Phenology already shares elm (index 2). Do the code repoint during the elm rebuild, not
  before (no elm `_xl` model exists yet).

---

## 3. Species → skeleton map (extends `convert_to_godot.py` SPECIES_MAP)

The genus→archetype table in `convert_to_godot.py` is the data-side half. Two fixes the
roster requires:
- **`liriodendron` is currently absent** → falls through to generic `deciduous`. Route it
  to **tall_excurrent** (tulip tree is a signature tall park tree rendering as a blob today).
- Re-home **`liquidambar` (sweetgum)** and **pin oak** to **tall_excurrent** if their
  pyramidal habit reads better there than on rounded_oval / broad_dome.

Identity that shares a skeleton still differs by its **recipe**:
`{ skeleton, crown_preset (scale-xyz + shape), bark_set, leaf_cutout, summer_tint,
phenology_index, foliage_gate, density, bloom, clump }`. `skeleton`, `phenology_index`,
and `bark_set` are existing dictionaries; the rest are cheap per-species data.

---

## 4. Rebuild checklist — every skeleton must satisfy this

Condensed from `docs/tree-pipeline-lessons.md` (read it for the detail + the wrong-diagnosis
war stories). Each item is a thing the *pre-london-plane* models get wrong.
**The Hard build laws (§1b) are absolute and override any item here.**

**Skeleton (Mtree levers)**
- [ ] `crown_base_size` set (default 0.0 is a narrow-cone clamp → poles/plumes)
- [ ] `trunk_randomness` low (~0.18) for a clean stout bole, not an S-curve lean
- [ ] `branch_end` high (~0.94–0.97) so branches reach + round the apex and clad the bare leader
- [ ] ramification capped at **secondary** (law 4): orders = trunk + primary + secondary only, `cap_skeleton_depth()` `max_depth = 2`. The card twig is the terminal ramification; deeper forks are redundant + poke bare. Density = more secondaries, not deeper forks.
- [ ] per-tier `variant_spans` (age differentiation) — they outrank `skeleton_overrides`; without them the mature spans clobber `_s`/`_m`

**Foliage placement**
- [ ] continuous sheath on real branch verts — no scattered blobs / box-fill / floaters
- [ ] coherence law: unbroken trunk→branch→leaf line for every leaf; validate with `check_foliage_connectivity.py`
- [ ] min-twig-diameter floor **≥ 0.05** (law 3), self-reporting (thin twig reads as a floating clump even when connected)
- [ ] placement by branch order (`hierarchy_depth`), with the **per-species gate** from §2 (oak/elm along-branch; plane/cherry/birch tip-biased; maple intermediate)
- [ ] apex-band force-keep (top ~18% leafy regardless of order) to kill the bare-leader spike

**Leaf representation**
- [ ] `_m`/`_l` = real-photo cluster cards; `_s` = structural 3D leaves (small crown can afford them)
  — **[OPEN, flag 2026-06-22: laws 1–2 are card-centric ("perfect the leaf cards, then sculpt
  the small model"), which reads as `_s` wearing cards too. But `tree-pipeline-lessons` §0aaa
  made `_s` structural *because cards go see-through on a small crown*. Confirm with Chris
  whether the 2–4-leaf sprig card now also clothes `_s`, or `_s` keeps the structural hybrid.]**
- [ ] the card is a 2–4-leaf twig sprig (leaves + stems + joining twig) sitting at the tip (law 2)
- [ ] rebuild the `_leaf.dds` after any card change (runtime prefers the DDS over the GLB-embedded texture)

**LOD / perf**
- [ ] screen-size LOD (`_lod_scale`) — handoffs scale with tree height (~77 px switch size)
- [ ] one impostor atlas per species-tier (median variant), shared by all variants
- [ ] per-tree position-hash variant selection (local diversity, stable across handoff)
- [ ] `perf_gate.sh ×5` on a real GPU before commit (this headless box runs llvmpipe ~11 fps — not representative)

**Distinctiveness**
- [ ] deliberate, distinct fall color per species (the autumn payoff — never collapse them)
- [ ] distinct leaf-card silhouette per species (built to measured numbers, never reused)

---

## 5. Build order — by trees-rendered

The london plane paid the one-time cost of *building the pipeline* (the order gate, depth
cap, connectivity gate, screen-size LOD, cluster-card path, min-twig floor). Subsequent
rebuilds *reuse* that machinery — "study the reference folder, set the known levers, tune
the per-species gate + fall color, regen, perf-gate." Order by population so effort lands
where the trees are:

1. **broad_dome** — 57% of the forest **and** the generic fallback. Highest-value model in
   the project. Also the first test of the along-branch foliage gate (london plane proved
   the tip-biased gate).
2. rounded_oval → small_ornamental → vase  *(these four ≈ 90% of placed trees)*
3. open_compound → slender → conifer_spire (near ground-up) → tall_excurrent (net-new) → finish willow
4. Wire the six folds (one-line `ARCHETYPE_MODEL` repoints + recipe rows)
5. Extend `SPECIES_MAP`: `liriodendron` → tall_excurrent; re-home sweetgum / pin oak

---

## 6. Tier-2 promotion backlog (bespoke models later)

Fold now; promote to their own skeleton when iconicity / budget warrants and the shared
skeleton visibly fails them:
ginkgo (young columnar form) · sweetgum (own star-leaf + purple fall) · beech (smooth grey
bark, distinct dense dome) · london_plane (back to bespoke *if* its skeleton proves to read
distinct) · conifer_spread + conifer_columnar (Pinetum) · dawn redwood / bald cypress
(feathery deciduous conifer).
