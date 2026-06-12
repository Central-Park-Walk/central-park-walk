# BRIEF — Common Elderberry (Sambucus canadensis / nigra)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Shrub_Elderberry` — generator `make_elderberry()` in
  `scripts/make_undergrowth.py:1047`; runtime `undergrowth_builder.gd` `SPECIES` **index 4**.
- **Layer:** shrub / sub-canopy (large arching moist-edge shrub, 2–3.5 m)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP at moist woodland edges, stream/pond margins per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. Stills resolve the flat-flower-plate and drooping-berry
identity; a walk video helps for the arching/drooping habit in a moist-edge thicket.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (arching pithy canes)
- [ ] **In a moist-edge thicket** (arching masses overlapping)
- [ ] **Compound leaf detail** (pinnate, 5–11 serrate leaflets)
- [ ] **Flower plate** (huge flat creamy-white cyme — diagnostic) + **drooping berry cluster** (purple-black)
- [ ] **Fall color** (yellow-green, not showy)

## 1. Habit — how it flows over itself
- **One-liner:** large multi-stemmed shrub whose weak, **pithy stems arch outward and
  droop** under the weight of leaves, flat flower plates, and berry clusters — it
  cascades and layers (a coarser, larger-leaved cousin of the spicebush gesture), never
  upright-stiff.
- **Overall form:** broad, arching, slightly mounded; **2–3.5 m.**
- **Aspect (w:h):** ~1.1–1.3 (broader than tall, arching outward).
- **First fork height:** low, multi-stemmed from base.
- **Branch character:** **arching, drooping** weak pithy canes; tips bend down under load.
- **Asymmetry:** considerable — canes lean and droop unevenly.

## 2. Interaction — how it meets its neighbors
- **In a stand:** arching masses **overlap and layer** at moist edges, forming loose
  thickets where the drooping crowns of neighbors interleave (shares the spicebush
  cascade-interaction problem).
- **Target stand reading:** overlapping arching/drooping masses crowned with flat white
  flower plates, at a stream/pond edge — interleaving, not isolated balls.

## 3. Density
- **Bucket:** medium / open-ish (large compound leaves, open between canes).
- **Real number:** moderate; coarse-textured big compound leaves.
- **Light transmission:** medium.

## 4. Detail
- **Stem:** gray-brown, pithy, ridged with prominent lenticels; arching.
- **Leaf:** **pinnately compound**, 5–11 ovate serrate leaflets → `compound_mode`.
- **Summer color:** medium green · **Fall:** dull yellow-green (`fall=[0.55,0.50,0.12]`, not showy).
- **Bloom:** **huge flat-topped creamy-white cymes** (umbel-like plates, 15–25 cm across)
  early–mid summer (`bl=[0.8,1.3]`) held flat on top → then **drooping clusters of small
  purple-black berries** late summer (weigh the canes down further — model the droop).

## 5. Behavior
- **Wind:** flexible (`flex=0.35`) — arching weak canes sway and bounce; big compound
  leaves flutter; loaded flower/berry plates nod.
- **Seasonal:** flush → arching summer mass → **flat white flower plates (early-mid
  summer, the identity)** → drooping purple-black berries (late summer) → yellow-green
  drop → arching bare canes.

## 6. The one unmistakable thing
**Huge flat creamy-white flower plates** held on top of an **arching, drooping** pithy
shrub, becoming **drooping clusters of purple-black berries** — compound-leaved and cascading.

## 7. Per-instance variation envelope
- **Varies across seeds:** cane count, arch/droop amount, size (2–3.5 m), flower/berry presence.
- **Variant count:** 4 — moist-edge thickets, set `v=4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_elderberry()` is bespoke (5 arching stems) — **lift the arching/
  drooping habit** (the spicebush cascade + willow strand-card lessons transfer for the
  drooping load), `compound_mode` leaflets, **flat-topped flower plates** (not scattered
  cards), drooping berry clusters.
- **Textures:** pinnate serrate leaflet (compound), flat white cyme plate, purple-black berry cluster.
- **`SPECIES` row (idx 4):** `fc` white / `bl` early-summer correct; `flex=0.35` correct;
  `sc` gray-brown; **add `v=4`.**
- **Placement:** re-wire into `ZONE_SPECIES[7]` (Waterside — currently empty) and moist
  woodland edges (`[5]`/`[6]` near water) at MEDIUM density.
- **Perf:** medium; perf-gate waterside after re-wire.

## 9. Definition of Done
- [ ] Thumbnail reads as elderberry (arching, compound leaves, flat white plates).
- [ ] **Thicket capture** at a moist edge — arching/drooping masses interleave (interaction).
- [ ] Flat white cymes (early-mid summer) → drooping purple-black berries (late summer) fire correctly.
- [ ] Dense same-species stand shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
