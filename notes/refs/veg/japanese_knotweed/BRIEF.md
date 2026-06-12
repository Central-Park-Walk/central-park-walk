# BRIEF — Japanese Knotweed (Reynoutria japonica, syn. Fallopia japonica)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_JapaneseKnotweed` — generator `make_japanese_knotweed()` in
  `scripts/make_undergrowth.py:1249`; runtime `undergrowth_builder.gd` `SPECIES` **index 12**.
- **Layer:** herb (tall bamboo-like cane forming thicket walls, 2–3 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP along the Loch/Ravine watercourse and riparian North Woods per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **INVASIVE & actively
managed** — Park maintenance removes it, so CP occurrences are **small remnant patches,
not textbook stands.** Walk video helpful to confirm the CP-specific small-patch read vs
the generic dense wall.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (tan hollow standing dead canes — the skeleton thicket)
- [ ] **As a small remnant patch** at a CP watercourse edge (the CP-specific interaction)
- [ ] **Stem detail** (hollow bamboo-like canes, swollen nodes, purple speckling)
- [ ] **Leaf detail** (broadly ovate, flat truncate base — ID feature)
- [ ] **Bloom** (frothy creamy-white axillary panicles, Aug–Sep)

## 1. Habit — how it flows over itself
- **One-liner:** strictly upright, unbranched hollow canes with swollen bamboo-like nodes,
  carrying short leafy laterals only in the upper half, packed into a rigid green wall with
  a flat-topped canopy — the visual unit is the patch, not the cane.
- **Overall form / crown shape:** bamboo-like upright canes; flat-topped colony canopy.
- **Aspect (width : height):** colony reads as a wall/hedge; individual cane is a strict
  vertical (2–3 m, sometimes 4 m).
- **First branch / fork height:** upper half — canes unbranched below, short lateral leafy
  branches only near the top, creating a layered tiered canopy.
- **Branch character:** rigid hollow round canes (1.5–3 cm), prominent raised nodes every
  10–15 cm; papery sheath (ochrea) clasping at each node.
- **Asymmetry:** little per-cane; the colony is a uniform packed stand.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **dense thicket wall** — canes pack at ~15–30/m² into a solid
  green mass that shades out everything beneath; individuals are indistinguishable within
  the colony. **In CP, however, managed down to SMALL remnant patches** (3–10 m or
  smaller), not the indefinite textbook stand.
- **Target stand reading:** *a small, dense, rigid patch of bamboo-like canes forming a
  contained green wall at a watercourse edge — read as a packed clump, deliberately modest
  in extent (a managed invasive remnant), not a sweeping monoculture.* (Validate as a small
  dense patch.)

## 3. Density
- **Bucket:** opaque (dense cane wall, solid green canopy).
- **Real number:** ~15–30 canes/m² within a patch; CP patches small/managed
  ([[reference-cp-botany-full]]). Place as small dense clumps, low overall coverage.
- **Light transmission:** low through the patch (shades the ground beneath).

## 4. Detail
- **Bark / stem:** hollow round canes, smooth glabrous, green speckled/streaked with
  **reddish-purple flecks** (more purple at base), prominent swollen nodes. `sc=[0.30,0.35,0.18]`
  green with purple nodes is correct — keep the node speckling.
- **Leaf / cluster:** broadly ovate (7–15 cm), **flat truncate (squared-off) base** — the
  primary ID feature — acuminate tip, entire slightly-wavy margin, dark green leathery,
  held on short upper laterals in tiers.
- **Summer color:** dark green · **Fall:** yellow (`fall` per row) · **Bloom:** tiny creamy
  -white tepals in branched axillary panicles (8–12 cm), Aug–Sep, giving the upper canopy a
  frothy white look (`fc` white — correct).

## 5. Behavior
- **Wind character:** **rigid, bamboo-like** (`flex=0.20` — correct). Hollow tubular canes
  resist bending — only slight lean in light wind; upper leafy laterals rustle, leaves
  flutter on petioles, canes themselves barely flex. Architectural/stiff. Dead winter canes
  rattle and click.
- **Seasonal timeline:** reddish-purple asparagus spears, explosive growth (Apr) → canopy
  closes (May–Jul) → frothy white bloom (Aug–Sep) → leaves yellow/drop (Oct) → **tan hollow
  standing dead canes = a skeleton thicket through winter** (Nov+), often snapped by snow.

## 6. The one unmistakable thing
**Hollow bamboo-like canes with swollen nodes, purple speckling, and flat truncate leaf
bases**, packed into a rigid flat-topped wall — and (CP-specific) deliberately a *small
managed remnant patch*, not a sweeping stand.

## 7. Per-instance variation envelope
- **Varies across seeds:** cane height (2–3 m), node spacing, purple-speckle intensity,
  upper-lateral leaf load, lean. Place as packed clumps (the colony does the work).
- **Variant count:** 2–3 canes (patch packing + yaw jitter carries variety; not a
  high-variant species).

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_japanese_knotweed()` (`scripts/make_undergrowth.py:1249`) —
  build strict upright hollow canes with **swollen speckled nodes** and **flat truncate
  leaf bases**; leafy laterals only upper-half; tiered canopy; creamy-white axillary
  bloom panicles.
- **Textures:** broadly-ovate truncate-base leaf; cane with purple-flecked nodes; frothy
  white panicle cluster.
- **`SPECIES` row (idx 12):** reconcile to this brief — `sc=[0.30,0.35,0.18]` green w/
  purple nodes (correct), `bl=[1.2,1.8]`, `fc` white (correct), `flex=0.20` rigid bamboo
  (correct — keep stiff).
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[7]` (Waterside, near
  Loch/Ravine — **currently an EMPTY array this work populates**) and `[5]` (North Woods
  riparian) as **SMALL dense remnant clumps at low overall coverage** (managed invasive —
  do not place sweeping monocultures).
- **Perf:** chunk-MultiMesh + overdraw; the dense patch is the cost — keep patches small
  and few. Gain the wall read from packed-cane form, not extra cards. Perf-gate after
  placement re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as knotweed (bamboo canes, swollen nodes, truncate leaf base).
- [ ] **Small-patch capture** at a Waterside/Loch edge shows a contained dense clump — a
  managed remnant, NOT a sweeping stand. *The small patch is the validation unit.*
- [ ] Rigid wind behavior (canes barely flex; `flex=0.20`).
- [ ] Tan hollow standing dead canes in the winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
