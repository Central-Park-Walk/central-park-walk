# BRIEF — Sweet Pepperbush (Clethra alnifolia)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Shrub_SweetPepperbush` — generator `make_sweet_pepperbush()` in
  `scripts/make_undergrowth.py:1118`; runtime `undergrowth_builder.gd` `SPECIES` **index 5**.
- **Layer:** shrub (moist-edge / wetland-margin understory, 1–2.5 m)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP at moist/wetland edges per [[reference-cp-botany-full]]; iNat CP-bbox count
TO CONFIRM. Stills resolve the upright white flower-spike identity; a walk video helps
for how it forms suckering colonies at pond/stream margins.

- [ ] **Habit, summer mass** — iNat CP; CPC / Missouri Bot / extension
- [ ] **Winter bare structure** (rounded twiggy, persistent dry seed spikes)
- [ ] **In a colony** (suckering patch at a moist edge)
- [ ] **Leaf detail** (alternate, obovate, serrate, glossy)
- [ ] **Flower spike** (erect white bottlebrush raceme — diagnostic, fragrant)
- [ ] **Fall color** (yellow-brown)

## 1. Habit — how it flows over itself
- **One-liner:** dense, rounded, upright multi-stemmed shrub (suckering into colonies)
  whose erect **white bottlebrush flower spikes stand above the foliage** in mid-late summer.
- **Overall form:** rounded, fairly dense, upright; **1–2.5 m** (smaller than the other shrubs).
- **Aspect (w:h):** ~0.9–1.1.
- **First fork height:** low; suckering multi-stem clump.
- **Branch character:** upright slender stems, dense twiggy infill, erect flower spikes at tips.
- **Asymmetry:** mild — a full rounded clump.

## 2. Interaction — how it meets its neighbors
- **In a stand:** **suckering colonies / patches** at moist woodland edges and pond
  margins; clumps merge into a soft rounded mass studded with white spikes.
- **Target stand reading:** a patch of rounded shrubs at a water edge, upright white
  flower spikes rising all across the top in mid-late summer.

## 3. Density
- **Bucket:** medium-dense.
- **Real number:** moderate-high leaf density (rounded full clump).
- **Light transmission:** low-medium.

## 4. Detail
- **Stem:** gray-brown, slender, upright.
- **Leaf:** alternate, obovate, serrate, glossy medium-dark green.
- **Summer color:** glossy green · **Fall:** yellow-brown (`fall=[0.70,0.55,0.10]`).
- **Bloom:** **erect white bottlebrush racemes** (cylindrical flower spikes, 5–15 cm,
  held vertically above the foliage), mid-late summer (`bl=[1.0,1.6]`); fragrant. Dry
  brown seed spikes persist into winter.

## 5. Behavior
- **Wind:** moderate (`flex=0.30`); upright spikes nod, leaves flutter.
- **Seasonal:** flush → dense summer clump → **erect white flower spikes (mid-late
  summer, the identity)** → yellow-brown fall → persistent dry seed spikes on bare twiggy clump.

## 6. The one unmistakable thing
**Erect white bottlebrush flower spikes** standing up above a rounded moist-edge shrub
in mid-late summer (and the dry brown spikes that persist after).

## 7. Per-instance variation envelope
- **Varies across seeds:** size (1–2.5 m), clump roundness, stem count, spike count/length.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_sweet_pepperbush()` — model the **vertical bottlebrush flower
  spikes** (the defining feature) and a rounded dense clump; obovate glossy leaf.
- **Textures:** obovate serrate glossy leaf; vertical white raceme/spike cluster.
- **`SPECIES` row (idx 5):** `fc` white / `bl` mid-late summer correct; `fall` yellow-brown;
  `flex=0.30`; **add `v=3`.**
- **Placement:** re-wire into `ZONE_SPECIES[7]` (Waterside — currently empty) and moist
  woodland edges at MEDIUM density (forms patches).
- **Perf:** medium; perf-gate waterside after re-wire.

## 9. Definition of Done
- [ ] Thumbnail reads as sweet pepperbush (rounded clump + erect white spikes).
- [ ] **Colony/patch capture** at a water edge with spikes across the top (interaction).
- [ ] White spikes fire mid-late summer; dry seed spikes persist in winter capture.
- [ ] Dense same-species patch shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
