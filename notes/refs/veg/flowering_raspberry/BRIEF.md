# BRIEF — Flowering Raspberry (Rubus odoratus)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Shrub_FloweringRaspberry` — generator `make_flowering_raspberry()`
  in `scripts/make_undergrowth.py:1148`; runtime `undergrowth_builder.gd` `SPECIES` **index 6**.
- **Layer:** shrub (loose arching woodland-edge shrub, 1–2 m; big-leaf coarse texture)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP at shaded moist woodland edges per [[reference-cp-botany-full]]; iNat
CP-bbox count TO CONFIRM. Stills resolve the maple-like-leaf + magenta-flower identity;
a walk video helps for the loose arching/sprawling thicket habit.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (arching canes, shreddy peeling bark)
- [ ] **In a loose thicket** (sprawling, big leaves overlapping)
- [ ] **Leaf detail** (large, soft, 3–5 lobed maple-like — diagnostic)
- [ ] **Flower detail** (rose-purple/magenta 5-petal, wild-rose-like — diagnostic)
- [ ] **Fall color** (yellow-brown, not showy)

## 1. Habit — how it flows over itself
- **One-liner:** loose, **sprawling, arching** multi-stemmed thornless shrub with large
  soft maple-like leaves and rose-purple flowers — open and coarse-textured, canes
  arching and leaning into neighbors.
- **Overall form:** loose, broad, arching/sprawling; **1–2 m.**
- **Aspect (w:h):** ~1.2–1.5 (wider than tall, sprawling).
- **First fork height:** low; multi-cane from base.
- **Branch character:** **arching, sprawling** canes with **shreddy/peeling bark**;
  thornless (unusual for a Rubus); big leaves on long petioles.
- **Asymmetry:** high — sprawls unevenly toward light.

## 2. Interaction — how it meets its neighbors
- **In a stand:** loose **thickets** in moist shade; the large leaves and arching canes
  overlap into a coarse-textured continuous mass.
- **Target stand reading:** a sprawling tangle of big-leaved arching canes dotted with
  magenta flowers, in dappled woodland-edge shade.

## 3. Density
- **Bucket:** medium / coarse (few but very large leaves).
- **Real number:** moderate leaf count, large leaf area — coarse texture, not fine.
- **Light transmission:** medium (big leaves cast big shadows but canes are open).

## 4. Detail
- **Stem:** brown with **shreddy, peeling bark**; arching; no thorns.
- **Leaf:** **large (10–25 cm), soft, palmately 3–5 lobed — maple-like** (the texture
  signature); fine-toothed margin.
- **Summer color:** soft medium green · **Fall:** dull yellow-brown (`fall=[0.60,0.45,0.08]`).
- **Bloom:** **rose-purple / magenta 5-petal flowers** (~4 cm, like a wild rose),
  through summer (`bl=[0.8,1.5]`, `fc=[0.75,0.25,0.55]` correct). Small dry reddish
  raspberry fruit (not showy).

## 5. Behavior
- **Wind:** flexible (`flex=0.35`); arching canes and big leaves sway and flutter (big leaf area catches wind).
- **Seasonal:** flush → big-leaf summer sprawl → **magenta flowers through summer (the
  identity)** → yellow-brown drop → arching bare canes with shreddy bark.

## 6. The one unmistakable thing
**Big soft maple-like leaves + rose-purple (magenta) wild-rose flowers** on a thornless,
shreddy-barked, arching/sprawling cane shrub.

## 7. Per-instance variation envelope
- **Varies across seeds:** cane count, sprawl/arch amount, size (1–2 m), leaf size, flower count.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_flowering_raspberry()` — model **large palmate maple-like leaf
  cards** (distinct from every other shrub's leaf), arching sprawling canes with shreddy
  bark, magenta 5-petal flowers.
- **Textures:** large 3–5-lobed maple-like leaf; magenta 5-petal flower.
- **`SPECIES` row (idx 6):** `fc` magenta / `bl` summer correct; `fall` yellow-brown;
  `flex=0.35`; `sr=0.88`; **add `v=3`.**
- **Placement:** re-wire into `ZONE_SPECIES[5]`/`[6]` (North Woods / Ramble) shaded moist
  **edges** at LOW-MEDIUM density (loose thickets, not a screen).
- **Perf:** medium (few large cards); perf-gate woodland after re-wire.

## 9. Definition of Done
- [ ] Thumbnail reads as flowering raspberry (big maple-like leaves, magenta flowers, arching canes).
- [ ] **Loose-thicket capture** in dappled shade — big leaves overlapping (interaction).
- [ ] Magenta flowers fire through summer at the right `season_t`.
- [ ] Dense same-species stand shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
