# BRIEF — Mugwort (Artemisia vulgaris)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_Mugwort` — generator `make_mugwort()` in
  `scripts/make_undergrowth.py:1807`; runtime `undergrowth_builder.gd` `SPECIES` **index 18**.
- **Layer:** herb (colonial weedy perennial, ~1 m, woody base)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at disturbed margins, path edges, and the perimeters of maintained turf per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **Walk video helpful** for the
**silver-flash-in-wind** behavior — the bicolor leaf-flicker is the identity and a still
misses it. Source: [`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §8.

- [ ] **Habit, summer mass** — iNat CP; herbs doc §8
- [ ] **In a colonial stand** (dense gray-green weedy thicket — essential)
- [ ] **Leaf detail** (deeply pinnately lobed, chrysanthemum-like; SILVER-WHITE underside)
- [ ] **Wind/behavior video** (leaves flip to flash silver undersides)
- [ ] **Stem detail** (ridged, gray-brown, woody at base, fine white wool)

## 1. Habit — how it flows over itself
- **One-liner:** upright, bushy, multi-stem colonial perennial forming a dense gray-green
  weedy mass, woody/stiff at the base, branching diffusely in the upper half into hazy
  brownish flower panicles — the whole stand flickers **silver** as leaves flip in wind.
- **Overall form / crown shape:** bushy upright mass, shrub-like; the colony reads as a thicket.
- **Aspect (width : height):** ~0.5 : 1 per stem; colonial spread is unbounded.
- **First branch / fork height:** branches profusely in the upper half; lower stem leafy, woody.
- **Branch character:** stiff, woody-based stems; many short lateral flower branches above.
- **Asymmetry:** weedy and untidy — irregular, not a tidy specimen; reaches into gaps.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **colonial weedy stand** — rhizomatous, forms dense pure
  patches that crowd out neighbors; the visual unit is the gray-green stand, not the plant.
- **Target stand reading:** a continuous, slightly paler/grayer weedy thicket along a
  disturbed edge that **flickers silver** when wind turns the leaves — read as ONE colony
  mass, not scattered individuals. This is a placement lever (rhizomatous patch, not scatter).

## 3. Density
- **Bucket:** opaque (dense leafy mass); the colony shades the ground.
- **Real number:** 0.6–1.5 m tall, individual plants 30–60 cm, colonial via rhizomes
  ([[reference-cp-botany-full]]; herbs doc §8). No published LAI — bucket from habit.
- **Light transmission:** low within the stand; foliage-dense.

## 4. Detail
- **Bark / stem:** round-to-ridged, 5–10 mm, woody/tough at base, gray-brown with purplish
  tints and fine gray-white wool (`sc=[0.30,0.24,0.16]` gray-brown ridged woody — correct).
- **Leaf / cluster:** deeply pinnately lobed (chrysanthemum-like), dark green ABOVE,
  **densely silver-white woolly BELOW** — model as a distinct underside color so the
  bicolor flash reads. Uppermost leaves near flowers simple/narrow.
- **Summer color:** gray-green (the silver undersides dust the whole plant). · **Fall:**
  browning, no showy color. · **Bloom:** none showy — `fc=[0,0,0]`; flower panicles are
  inconspicuous dull yellow-green to brown, hazy spikes (model as dusty brown panicles, not color).

## 5. Behavior
- **Wind character:** moderately stiff (`flex=0.25`) — woody base resists bending; the
  signature is the **leaves flipping to flash silver undersides** (the colony's most
  dynamic quality), not whole-stem sway. Dead winter stems are rigid and rattle.
- **Seasonal timeline:** silvery soft flush (Apr) → dense gray-green summer mass → hazy
  brown flower panicles (Jul–Oct, inconspicuous) → browning foliage → bare brown woody
  stems standing rigid through winter.

## 6. The one unmistakable thing
**Silver-white woolly leaf undersides that flash when the wind flips the leaves** — the
gray-green, sage-dusty colony that flickers silver. If the undersides aren't modeled as a
distinct color, the identity is lost.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.6–1.5 m), stem count, panicle development, leaf-lobe
  depth, lean — wide envelope so the colony doesn't tile.
- **Variant count:** 3–5 (densely-placed colonial species — set `v=3`).

## 8. What this brief drives (build mapping)
- **Generator:** `make_mugwort()` (`scripts/make_undergrowth.py:1807`) — model deeply
  pinnately lobed leaves with a **distinct silver-white underside color**; woody-based
  multi-stem upright form; dusty brown flower panicles in the upper half. Replace any
  generic helper with bespoke bicolor-leaf geometry.
- **Textures:** chrysanthemum-lobed leaf, silver-white woolly underside, dusty brown panicle.
- **`SPECIES` row (idx 18):** reconcile to brief — `fc=[0,0,0]` (no showy flower),
  `bl=[1.0,2.0]`, `sc=[0.30,0.24,0.16]` gray-brown ridged woody, `flex=0.25`; **add `v=3`.**
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED) at disturbed
  edges / meadow perimeters — `[2]` North Meadow, `[8]` Wild Meadow (currently empty),
  `[9]` Open Lawn edges. Place as **colonial rhizomatous patches**, not uniform scatter.
- **Perf note:** chunk-MultiMesh; overdraw rises in the dense colony — gain density from
  form/texture/placement, not card count. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as mugwort (gray-green, lobed leaves, silver undersides, woody base).
- [ ] **Colony capture** (disturbed edge) reads as one gray-green weedy stand.
- [ ] **Wind capture** shows the silver-underside flash (the identity behavior).
- [ ] Dense colony shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
