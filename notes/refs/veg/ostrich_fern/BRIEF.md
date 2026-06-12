# BRIEF — Ostrich Fern (Matteuccia struthiopteris)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Fern_Ostrich` — generator `make_ostrich_fern()` in
  `scripts/make_undergrowth.py:1853`; runtime `undergrowth_builder.gd` `SPECIES` **index 7**.
- **Layer:** floor / herb (tall woodland-floor fern, 0.9–1.5 m — the **fern-group hero**)
- **Tier coverage:** n/a (single mesh + 200 m fade; ferns have no flowers, `fc=0`)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP moist/floodplain woods (North Woods Loch/Ravine, Ramble stream edges) per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **Walk video requested** for
the colony read — a moist-woods ostrich-fern stand is "a forest of vases," and that
in-stand repetition is the identity; the North Woods walk videos already cached for the
trees ([[project-tree-model-redesign-plan]]) may show it.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **In a colony** (the dense stand of vases — the validation unit)
- [ ] **Frond detail** (once-pinnate, broadest above the middle, plume-tapered both ends)
- [ ] **Central fertile fronds** (stiff, dark brown, erect — persist into winter)
- [ ] **Spring fiddleheads** (tight green crosiers — a seasonal read)

## 1. Habit — how it flows over itself
- **One-liner:** a tight circular crown of large sterile fronds standing erect at the
  base and arching gracefully outward at the tips into a symmetrical **vase /
  shuttlecock** — broadest above the middle, tapering to both ends like an ostrich plume.
- **Overall form:** symmetrical funnel/vase; **0.9–1.5 m**, the tallest fern here.
- **Aspect (w:h):** ~0.7–0.9 (taller than wide; the vase flares at the top).
- **Frond arrangement:** **circular rosette from one crown** — this tight radial vase is
  the whole habit. NOT scattered individual fronds.
- **Frond character:** erect lower third, then arching outward; once-pinnate, fine-cut.
- **Asymmetry:** low per plant (it's strikingly symmetric) — variation comes between plants.

## 2. Interaction — how it meets its neighbors
- **In a stand:** **colony-forming** via rhizomes — dense stands of vases in moist
  floodplain woods, crowns nearly touching, reading as a continuous waist-high fern field.
- **Target stand reading:** a "forest of shuttlecocks" — many vases packed together,
  arching tips interleaving, on moist woodland floor.

## 3. Density
- **Bucket:** lush fronds, but the vase is **open in the center** (don't fill the funnel).
- **Real number:** moderate per frond; `trans=0.90` (translucent fronds) is right.
- **Light transmission:** medium — backlit fronds glow.

## 4. Detail
- **Rachis:** green, not bark-like (`sc` green, `sr=0.85`).
- **Frond:** once-pinnate, many narrow pinnae, **broadest above the middle**, plume-shaped.
- **Summer color:** fresh medium-bright green · **Fall:** yellow-brown (`fall=[0.55,0.45,0.10]`),
  dies back (not evergreen, `green=0`).
- **Fertile fronds:** distinct, shorter, **stiff dark-brown erect spikes in the center**
  of the vase, appearing late summer and **persisting through winter** (the winter ID).
- **Spring:** tight green **fiddleheads** (crosiers) emerging from the crown.

## 5. Behavior
- **Wind:** flexible (`flex=0.40`) — the arching plume tips sway and bounce; the whole
  vase moves as a soft unit.
- **Seasonal:** fiddleheads (spring) → vase of green plumes (summer) → central dark
  fertile fronds (late summer) → yellow-brown die-back → bare crown with **persistent
  erect dark fertile fronds** in winter.

## 6. The one unmistakable thing
The **symmetrical vase/shuttlecock** of plume fronds with a cluster of stiff dark
**fertile fronds standing erect in the center**.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.9–1.5 m), vase flare, frond count, fertile-frond
  presence/count, crown lean.
- **Variant count:** 4 — placed in dense colonies, tiling is very visible; set `v=4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_ostrich_fern()` (uses `make_frond`/`make_pinnate_frond`) — model
  the **tight radial vase crown** (the habit), plume fronds broadest-above-middle, and a
  distinct central fertile-frond cluster. This is the fern-group worked example.
- **Textures:** once-pinnate plume frond (gen_fern_textures); dark fertile-frond spike.
- **`SPECIES` row (idx 7):** `flex=0.40`, `trans=0.90`, green rachis, `fall` yellow-brown
  correct; **add `v=4`.**
- **Placement:** re-wire into `WOODLAND_SPECIES` + `ZONE_SPECIES[5]`/`[6]` near moist/
  stream areas at MEDIUM-HIGH density (colonies) — the woodland floor layer.
- **Perf:** translucent fronds = overdraw in dense colonies; perf-gate North Woods/Ramble.

## 9. Definition of Done
- [ ] Thumbnail reads as a symmetric ostrich-fern vase with central fertile fronds.
- [ ] **Colony capture** — a stand of vases interleaving (the interaction).
- [ ] Winter capture shows persistent erect dark fertile fronds; spring shows fiddleheads.
- [ ] Dense same-species colony shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
