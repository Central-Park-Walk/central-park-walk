# London Plane — Crown-Shape Reference Data Audit

> **Status:** AUDIT ONLY. No mould built, no code written, no parameters changed.
> Awaiting Chris's sign-off before any next step.
> **Date:** 2026-07-06 · **By:** Opus 4.8
> **Scope:** inventory of reference material for building a London plane crown
> "mould" (target crown volume) from real data.

## Method
Walked `reference_photos/london planetree/` and visually inspected **every image
file** (28 files, excluding `.import` sidecars). Each tree/model/ambiguous image
was opened and read individually; the 7 pure leaf-macro shots were verified
together via a contact sheet (`tmp/lpt_audit_contactsheet.jpg`). No files were
classified on filename alone. Also confirmed there are **no loadable London
plane mesh files** in the reference set (the project's own generated
`models/trees/london_plane_{s,m,l}.glb` are outputs, not reference material).

## Totals

| Category | Count |
|---|---|
| **A — Whole-crown silhouette candidates** | **8** (3 strong, 5 marginal) |
| **B — 3D-mesh reference (all are 2D renders, not meshes)** | **6** (4 full-crown, 2 partial) |
| **C — Everything else (leaf / bark / detail / assets)** | **14** |
| **Total files reviewed** | **28** |

---

## Category A — Whole-crown silhouette candidates (8)

Per-photo detail. "Strong" = a single specimen whose full crown outline is
readable. "Marginal" = a row/cluster, a from-below shot, young nursery stock, or
a cropped/bare crown where the silhouette is only partly usable.

### Strong (3)

**`A149-03_hero_l.jpg`** — *best specimen in the set.*
- Angle: **front-on**, roughly eye-level.
- Framing: **entire crown in frame**, clean margin all round.
- Leaf state: **full leaf** (summer).
- Occlusion: **none** — isolated open-grown tree in open grass; small distant
  background trees do not touch the crown.
- Type: **open-grown specimen, natural full crown** — broad, rounded, dome. Not
  pruned/pollarded. Textbook mature form. (Filename `_hero_l` = already chosen as
  the `_l`-tier hero.)

**`london-plane-central-park-trees-great-trees-nyc11.jpg`** — *the CP specimen.*
- Angle: **oblique / three-quarter**, slight up-look.
- Framing: full crown **just fits**; apex near the top frame edge.
- Leaf state: **full leaf** (summer).
- Occlusion: crown edges lightly framed by adjacent CP woodland foliage (left +
  right); ~85% of the crown outline is clean against sky.
- Type: **open-grown park specimen**, natural full crown on a very high clear
  mottled bole. Tall vase→spreading form. Genuine Central Park tree.

**`image-3172802200_hero_l.jpg`** — *usable but flag as synthetic-suspect.*
- Angle: **front-on**.
- Framing: full crown, apex slightly soft/cropped at top.
- Leaf state: **full leaf**, early-autumn tinge.
- Occlusion: base skirted by garden shrubs; flanked by other trees at frame
  edges; walled English town-garden setting.
- Type: open-grown specimen, spreading rounded crown. **⚠ Strongly reads as an
  AI-generated / heavily-composited image** (dreamy backlight, over-perfect
  symmetry, `_hero_l` naming). Do **not** treat its proportions as measured
  ground truth.

### Marginal (5)

**`2619305_6ce1c233.jpg`** — pollarded **allée row**, oblique down a path.
- Full leaf; many trees; crowns merge into a continuous ceiling.
- **⚠ Pollarded / pruned-up street-park trees** (knuckled, high bare boles). No
  single crown outline is isolable. Good for *stand/allée* read, not single mould.

**`majestic-…_branch_structure.jpg`** — **from directly below** the trunk.
- Full leaf; shows the radiating primary→secondary **branch scaffold** superbly.
- **Crown silhouette is NOT readable** from this angle (underside view). Value is
  branch topology, not crown shape. Also looks HDR/enhanced, possibly synthetic.

**`os-lk-londonplane (6).JPG`** — cluster of ~5 **young** trees, autumn colour.
- Full (autumn) leaf; distance view; crowns partly overlap.
- **Young upright/pyramidal form**, not mature spreading. Street/park planting.

**`exclamation-…-nursery.webp`** — nursery catalogue, 3-panel with height pole.
- **Very young containerised nursery stock**, staked, narrow **columnar
  'Exclamation' cultivar** — atypically narrow form. Useful for scale + juvenile
  habit only.

**`Looking_across_…_Lincolns_Inn_Fields.webp`** — **bare winter**, large planes.
- Leafless; shows winter scaffold + massive multi-stem trunk + mottled bark high.
- **⚠ Crown is cropped** (top out of frame); near tree is multi-stemmed; other
  bare planes behind. Good for winter-structure, poor for crown outline.

**Distinct specimens / angles in A:** ~**3 clearly-isolable single specimens**
(A149, nyc11, image-3172 [synthetic-suspect]). **Every one is a single angle** —
**no specimen appears from 2+ angles.** The remaining 5 are rows, clusters,
from-below, or cropped/bare and do not add an isolable single-crown outline.

---

## Category B — 3D-mesh reference (6)

**Important distinction:** none of these is a loadable mesh. **All 6 are flat 2D
renders/screenshots** of commercial 3D-model products (marketplace previews).
You cannot extract a crown volume (mould) from them directly, and they are
generic commercial models, not tied to CP data. Classified below by whether the
render shows a full crown or only part.

### Full-crown renders (4)

- **`london-plane-tree-01-02.jpg`** — **wireframe** line-render, **front-on**,
  full crown. Single mature spreading tree; clean silhouette + internal topology.
- **`london-plane-tree-09-02.jpg`** — **wireframe** line-render, **oblique**,
  full crown. Different specimen (asymmetric, one low lateral limb).
- **`platanus-acerifolia-willd-…-45b8e7bbdc.webp`** — clay/AO render, side view,
  **three** full-crown model instances (young oval-upright crowns).
- **`platanus-acerifolia-willd-…-6e6cb11fdc.webp`** — textured render with a
  100–800 cm height scale, **three** full-crown instances (**young**, ~5–7 m,
  conical→oval). Good for juvenile proportions + scale.

### Partial renders (2)

- **`pollarded-london-planetree-10m-3d-model-…jpg`** — clay/wire close-up of a
  **pollarded** model's trunk + lower branch junctions, autumn leaves. **Cropped —
  trunk/branch only, no crown outline.**
- **`platanus-acerifolia-willd-…-3fb7dadc43.webp`** — textured close-up of the
  **upper foliage only** of the willd model. **Cropped — foliage detail, no whole
  crown.**

**Full-crown vs partial:** **4 full-crown, 2 partial.** But re-state the caveat:
these are *renders*, not meshes — usable as visual crown-shape reference at best,
not as geometry to sample.

---

## Category C — Everything else (14) — flagged & set aside, not discarded

All confirmed by inspection; nothing here shows a whole crown.

- **Leaf macros (9):** `IMG_4070-scaled-…jpg`, `close-up-…-2SA8J91.jpg`,
  `london-plane-leaves-wtml-…jpg`, `london-plane-tree-leaf.jpg`,
  `london-plane-tree-leaves-autumn-color-…104477646.jpg`,
  `london-plane-tree-platanus-hispanica-leaf-and-seed-head-…2WX2HGD.jpg`,
  `ref_leaf_flat_single.jpg`, `ref_leaf_on_snow.jpg`, `ref_leaf_single2.jpg`.
  (Single-leaf + seed-ball detail; summer, autumn, and on-snow variants.)
- **Leaf canopy close-up (1):** `colorful-leaves-big-platanus-…107600625.jpg`
  (looking up into autumn foliage — leaf colour, not crown).
- **Bark macro (1):** `Trees-HRPK-London-Planetree-Trunk.jpg` (the camouflage
  exfoliating bark — hero bark reference; §6 of the species BRIEF).
- **Comparison diagram (1):** `london-plane-vs-sycamore2-300x148.jpg` (tiny
  leaf ID diagram).
- **Project-made leaf-card assets (2):** `lpt big leaf card ca.jpg` +
  `.png` (a generated 8-leaf sprig card — our own asset, not reference).

---

## Coverage gaps for mould-building purposes — stated plainly

This is where the audit stops. **No mould-building recommendation is made.**
The gaps, in priority order:

1. **No multi-angle coverage of any single tree.** Every isolable specimen (3 of
   them) is a **single 2D view**. A crown *volume* cannot be triangulated from
   lone silhouettes — you need the same tree from ≥2 angles (ideally
   front + side + oblique).
2. **Thin single-specimen count.** Effectively **3** usable whole-crown photos,
   and **one of those is AI-suspect** (`image-3172…`). Realistically **2 trusted
   real specimens** (A149, nyc11) — and they are different forms (broad dome vs.
   tall vase-spread).
3. **No aerial / top-down (plan) view.** A crown mould benefits from the plan
   outline; the set has **zero** overhead shots.
4. **Form is inconsistent across the set.** Mature open-grown (A149, nyc11),
   young upright (os-lk, exclamation, the young 3D models), and pollarded (the
   allée row, the pollarded model) are all mixed, with **no repeat coverage of
   any one maturity/form class.** London planes are commonly pollarded — that
   changes crown shape drastically, and the data does not let us cleanly separate
   "natural specimen crown" from "pollarded crown."
5. **3D references are renders, not meshes** (Category B) — cannot be sampled as
   geometry, and are generic, not CP-derived.
6. **Only one bare-winter structure image, and it's cropped** — weak for the
   winter-scaffold target.

**Bottom line:** coverage is **thin for building a data-driven mould**. Two
trusted real single-crown photos, single-angle each, differing in form, plus a
scatter of rows/young/pollarded/render material. Sufficient to *sanity-check* a
crown shape; **not** sufficient to *reconstruct* a target crown volume with
confidence. Flagging the gap and stopping, per atomic-investigation discipline.

---

## Optional next step (flagged, NOT performed)

A broader web/reference pull would **plausibly** close gaps 1–3 cheaply:
- Open-grown *Platanus × acerifolia* specimens are common and well-photographed.
- **iNaturalist** research-grade observations (the BRIEF already found ~28
  *Platanus* obs in the CP bbox) often carry **2–3 photos per observation** —
  a realistic source of same-tree multi-angle coverage.
- Target: 3–5 mature open-grown specimens, each from ≥2 angles, plus 1–2 aerial
  outlines, explicitly separating natural vs. pollarded crowns.

This is **low-risk and fast**, but **not started** — awaiting Chris's go-ahead.

---

## Spot-check index (for Chris)

- **A, strong:** `A149-03_hero_l.jpg`, `london-plane-central-park-trees-great-trees-nyc11.jpg`, `image-3172802200_hero_l.jpg`
- **A, marginal:** `2619305_6ce1c233.jpg` (pollarded row), `Looking_across_…Lincolns_Inn_Fields.webp` (bare)
- **B, full-crown:** `london-plane-tree-01-02.jpg`, `london-plane-tree-09-02.jpg`, `platanus-acerifolia-willd-…-45b8e7bbdc.webp`
- **B, partial:** `pollarded-london-planetree-10m-3d-model-…jpg`, `platanus-acerifolia-willd-…-3fb7dadc43.webp`
- **C:** `Trees-HRPK-London-Planetree-Trunk.jpg` (bark), `london-plane-tree-leaf.jpg` (leaf), `lpt big leaf card ca.png` (our asset)

Contact sheet of the leaf set: `tmp/lpt_audit_contactsheet.jpg`.
