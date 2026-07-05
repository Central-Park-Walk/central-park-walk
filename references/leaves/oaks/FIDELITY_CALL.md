# Oak per-LOD-tier fidelity call — 3-oak roster (Phase 2 deliverable)

> **Scope: THREE oaks** — Pin (*Q. palustris*), Red (*Q. rubra*), Turkey (*Q. cerris*).
> This is the re-derived 3-oak call. It **supersedes** the earlier 7-taxon version (which
> carried scarlet/white/swamp-white/sawtooth and an accent-tier Turkey call from the on-disk
> street census). Source dossiers: `oak_red.yaml` (Lobatae baseline), `oak_pin.yaml` (deltas
> vs red), `oak_cerris.yaml` (standalone Cerris baseline). Population ground-truth: *Central
> Park Entire* (Chaya & Barnard 2013; oak breakdown via Cameron, Intl Oak Society 2014-05-25),
> **not** the NYC street census — which excludes the park interior and gives only a genus
> count, so it cannot source any per-species oak call.

**Question (Chris, 2026-06-24):** for the park's oaks, decide *which skeletons* and *which
textures* to build to best represent them **on a 3060 Ti rendering a forest at >45 fps
@ 1080p** — and **where a difference can't be portrayed noticeably at gameplay distance,
consolidate.** Answer **per LOD tier** (near lod0 / mid lod1 / far impostor), not as one
global call.

## The three oaks (from the dossiers)
| oak | park (2013) | section | habit | leaf card | bark | fall |
|---|---|---|---|---|---|---|
| **Pin** | ≈half of 2,854 (**1st**) | Lobatae | **excurrent** — central leader, narrow (H:S ~1.6), drooping lower skirt | Lobatae bristle-lobed (deep sinus 0.75) | furrowed (generic) | russet→crimson |
| **Red** | 584 (**2nd**) | Lobatae | **decurrent** — broad rounded dome (H:S ~1.0), open | Lobatae bristle-lobed (moderate sinus 0.5) | furrowed (generic) | brick-red / russet |
| **Turkey** | 356 (**3rd**) | Cerris | **large** (25–40 m) conical-young → broad rounded **dense** | Cerris bristle-**toothed** narrow | **orange-fissured** (distinctive) | **pale gold**, marcescent |

All three are **stood-under** park oaks (populous enough to be encountered up close) → all get
full s/m/l + LOD0 + LOD1 + impostor. No accent tier among these three.

## Constraints that shape the call
- **ONE variant per skeleton per size tier** (Chris, until london plane's impostor path is
  fixed). Every distinct skeleton / leaf card is a **flat, un-amortized tax** → strong
  consolidation bias, and **fewer distinct impostors directly de-risks the impostor problem.**
- **Budget reality** (`trees.md` §4f/g, `tree_model_redesign.md` §2): trees are
  **fragment-shading-bound**, not geometry-bound. Extra branch tris are ~free; extra/larger
  **leaf cards + overdraw** and **extra impostor atlases (VRAM + bake)** are the real costs.
- **What carries identity at each range** (`tree-pipeline-lessons.md`): leaf **shape resolves
  only < ~30 m**; mid = **crown silhouette + density + color**; far = **gross silhouette +
  color mass**. Impostor atlases are **per species-tier, not per variant.**

---

## Per-tier decision

### NEAR — lod0 (0–~40 m): leaf shape + bark resolve → spend here
Everything that distinguishes these oaks is legible here, so near range is fully distinct.
- **3 skeletons** — all three habits read overhead and none can be faked from another:
  - **A — rounded decurrent** (red): broad open dome, no leader.
  - **B — excurrent** (pin): central leader + drooping lower skirt — reads unmistakably from
    below; the hard net-new skeleton.
  - **C — large Cerris** (turkey): big, conical-young → dense broad-rounded.
- **2 leaf cards:**
  1. **Lobatae bristle-lobed** — shared by **pin + red**. Pin's sinus is deeper (0.75) than
     red's (0.5), but both are bristle-lobed; **default one shared card**, differentiate
     pin/red by skeleton + fall, not a second card. *Hold in reserve:* a deep-sinus pin card,
     built only if Gate-1 shows the deep-vs-moderate sinus reads once instanced at near range.
  2. **Cerris bristle-toothed narrow** — turkey only (narrow oblong, shallow-lobed triangular
     teeth; genuinely different silhouette from the lobed card).
- **2 bark styles** (cheap material/tint, near-only): **furrowed** (pin + red, non-distinctive)
  and **orange-fissured** (turkey — the one genuinely distinctive oak bark, worth a per-species
  tint).
- **Near verdict:** distinct geometry for all three (A/B/C); pin+red **share** the Lobatae card
  and furrowed bark; turkey is fully distinct (own card + bark).

### MID — lod1 (~40–~180 m): leaf shape gone → crown silhouette + density + color only
- Leaf card and bark **buy nothing** here.
- **Pin stays distinct by SHAPE** — its narrow taller-than-wide excurrent silhouette + central
  leader + drooping skirt is the one oak form that separates on silhouette alone. Skeleton B
  earns its keep at mid.
- **Red vs Turkey are NOT separable by crown shape** — both are rounded crowns; turkey is
  larger and denser, but size is already carried by the s/m/l + height scaling and density by a
  leaf-density tweak. Their legible separator at mid is **FALL COLOR: red-russet (red) vs pale
  gold (turkey)** — a strong, opposite-hue difference — plus turkey's greater density/mass.
  Geometry is already distinct (Skeleton C exists for near+population reasons), but **the mid
  discriminator is color, not shape.** Turkey also holds **gold marcescent** leaves into winter
  while red goes bare — a mid/far winter cue red can't carry.
- **Mid verdict:** pin distinct on shape; red/turkey = same rounded silhouette family, read
  apart by fall color (russet vs gold) + density + winter marcescence.

### FAR — impostor (>~80 m): gross silhouette + color mass; minimize atlases
- Only two silhouette families survive: **pin (narrow excurrent)** and **rounded** (red, turkey).
- **2 impostor atlases: pin (excurrent) + rounded**, color the rounded mass per species by tint
  (red-russet vs gold). This is also the safe play given the **active impostor difficulties** —
  fewer atlases, fewer bakes.
- **Gate-flag (the one caveat):** the rounded atlas is baked from red's russet foliage; tinting
  it to turkey's **pale gold is a larger hue stretch** than a red→scarlet nudge, and turkey's
  **winter marcescence** (still gold-foliated when red is bare) can't be expressed by a shared
  bare-winter impostor. If the gold tint doesn't carry cleanly through the impostor shader, or
  the marcescent winter read matters, **turkey gets its own rounded-gold impostor atlas** (a 3rd
  atlas). Decide at the impostor gate; **default = shared rounded atlas + tint.**

---

## RECOMMENDATION — 3 skeletons, 2 leaf cards, 2 bark styles, 2 impostor atlases

Unlike the old 7-taxon plan (which consolidated 7→2 skeletons), the 3-oak roster **cannot
consolidate on geometry**: each habit is genuinely distinct *and* independently justified
(pin = most populous + unique excurrent form; red = Lobatae baseline; turkey = 356 / distinct
Cerris section). The consolidation that *does* apply is on **cards, bark, and impostors**.

| asset | count | serves |
|---|---|---|
| **Skeleton A — rounded decurrent** (×s/m/l) | 1 | red |
| **Skeleton B — pin excurrent** (central leader, drooping skirt) (×s/m/l) | 1 | pin |
| **Skeleton C — large Cerris** (conical-young → broad rounded dense) (×s/m/l) | 1 | turkey |
| **Leaf card — Lobatae bristle-lobed** | 1 | pin + red (reserve: deep-sinus pin card) |
| **Leaf card — Cerris bristle-toothed** | 1 | turkey |
| **Bark style** | 2 | furrowed (pin+red) · orange-fissured (turkey) |
| per-species **fall-color tint** | 3 | primary mid/far differentiator (russet · russet-crimson · gold) |
| **impostor atlas** | 2 (+tint) | pin excurrent · rounded (red+turkey) — 3rd only if the gold/marcescence gate fails |

**Consolidation summary:** near = fully distinct (spend); mid = pin distinct on shape,
red/turkey separated by color not shape; far = 2 silhouette families, color by tint.

### Turkey oak tier note — s/m/l, NOT m/l-only (resolved 2026-07-04)
Full s/m/l, matching pin/red — a *default-to-consistency* call, not a data-backed omission:
- **No park size/age distribution exists** for the 356 Turkey oaks; the dossier's 25–40 m are
  botanical *mature* values, not a park distribution. Nothing says they're all mature.
- The earlier "m/l only" was a **carried-over artifact** of the dead 7-taxon plan (sawtooth was
  to cover the small end of a shared Cerris skeleton). Sawtooth is archived → that reason is gone.
- **Keep `_s`:** `tree_builder.gd` routes any oak < 12 m to `_s`, and a Turkey sapling reads
  distinct from a red sapling near-range via the Cerris card + strong **young-tree marcescence**
  (gold held into winter, strongest at small size). Cost = one flat variant. Revisit only if a
  future *Central Park Entire* size breakdown shows the 356 are effectively all mature.

### Open splits to resolve at the gates (don't pre-build)
- **Deep-sinus pin leaf card?** Decide at Lobatae Gate-1; default = one shared card. **↳ Red Gate-1
  (2026-07-04) flagged that the shared card's bottom-right leaf already reads deeper (~pin range) —
  it may partially serve pin's silhouette on the shared card. See `CARD_GATE1_RED.md` ⚑.**
- **Turkey's own gold impostor atlas?** Decide at the impostor gate; default = shared rounded
  atlas + gold tint (see FAR gate-flag).
- **Intra-species cloning.** With one variant per skeleton/size, a dense same-species stand
  risks visible repeats. Lean on runtime per-instance yaw / non-uniform scale / slight lean +
  color/phenology jitter; accept some repetition as temporary until the variant count reopens.

---

## BUILD ORDER (Phase 3 — card first → S → approve in game → M/L; one color pass at a time)
*(Reference only — do NOT start modeling until Chris signs off this fidelity call.)*

1. **Skeleton A + Lobatae card → RED OAK** (the template): most stable, is today's `oak`
   archetype, the broadleaf baseline. Card → red **_s** → **approve in game (Gate)** → **_m/_l**.
   *Also fix the mislabel:* `generate_trees_mtree.py:537` says "Pin Oak (Quercus palustris)" on
   red-oak params.
2. **Skeleton B → PIN OAK** (the hard net-new one — excurrent + drooping skirt; shares the
   Lobatae card). Do it early to de-risk: **_s → approve → _m/_l**.
3. **Cerris card + TURKEY OAK** — its own **Skeleton C** (large *Q. cerris*), Cerris
   bristle-toothed card, orange-fissured bark, pale-gold late fall + winter marcescence.
   Distinct model justified by population (356 / 3rd most populous), not a placement guess.
4. Downstream regen per `tree_model_redesign.md` §8 after each approved species; perf-gate ×5
   (60 open / 45 woodland).

**Validation that gates each consolidation:** for any "shared card / shared impostor, color-only
difference" pair (pin↔red on the Lobatae card; red↔turkey on the rounded impostor), capture the
two side by side at the relevant range; if they're indistinguishable there (they should be, by
design), the consolidation holds. If a pair IS distinguishable and *should* be (pin vs red crown
at mid), that's the skeleton split working.
