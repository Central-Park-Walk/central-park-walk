# BRIEF — Cinnamon Fern (Osmundastrum cinnamomeum)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Fern_Cinnamon` — generator `make_cinnamon_fern()` in
  `scripts/make_undergrowth.py:1913`; runtime `undergrowth_builder.gd` `SPECIES` **index 9**.
- **Layer:** floor / herb (large wet-woods clump fern, 0.9–1.5 m)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP wet/swampy woods and stream margins per [[reference-cp-botany-full]]; iNat
CP-bbox count TO CONFIRM. Stills resolve the central cinnamon fertile-frond identity; a
walk video helps for the wet-woods clump stand.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Spring/early-summer fertile fronds** (the upright cinnamon-stick spikes — diagnostic)
- [ ] **In a wet-woods stand** (big mounded clumps)
- [ ] **Frond detail** (bipinnate-ish, woolly tufts at pinna bases)

## 1. Habit — how it flows over itself
- **One-liner:** a large **vase clump** of bright green arching sterile fronds, with a
  cluster of erect **cinnamon-brown woolly fertile fronds standing in the center** in
  spring/early summer — coarser and clumpier than the ostrich fern's tidy shuttlecock.
- **Overall form:** broad vase clump / mound; **0.9–1.5 m.**
- **Aspect (w:h):** ~0.9–1.1 (vase, slightly broader than ostrich).
- **Frond arrangement:** radial clump (a true clump, **not a running colony** like ostrich).
- **Frond character:** arching, broad, somewhat coarse; the **central fertile fronds are
  the signature** — stiff, erect, covered in cinnamon-colored wool.
- **Asymmetry:** moderate; big mounded clumps lean.

## 2. Interaction — how it meets its neighbors
- **In a stand:** clumps cluster in wet/swampy woods and along stream/pond edges, forming
  big mounded fern masses (discrete clumps, not a continuous rhizome carpet).
- **Target stand reading:** big green fern mounds in wet shade, each with a tuft of
  upright cinnamon spikes in the center (spring/early summer).

## 3. Density
- **Bucket:** lush green vase; `trans=0.85` (translucent) correct.
- **Real number:** moderate-high per clump (a big leafy mound).
- **Light transmission:** medium.

## 4. Detail
- **Rachis:** green, with **persistent cinnamon woolly tufts** at the pinna bases.
- **Frond:** bipinnate-ish, broad, tapering; bright green.
- **Summer color:** bright medium green · **Fall:** yellow-brown (`fall=[0.60,0.50,0.12]`),
  dies back (`green=0`).
- **Fertile fronds:** **erect cinnamon-brown spikes in the clump center**, spring–early
  summer, then wither brown by midsummer (gone before fall). The defining feature.

## 5. Behavior
- **Wind:** moderate (`flex=0.35`) — broad fronds sway and flutter; central spikes stiffer.
- **Seasonal:** fiddleheads (woolly, spring) → **cinnamon fertile spikes (spring–early
  summer, the identity)** → green vase (summer) → yellow-brown die-back. Fertile fronds
  do NOT persist into winter (unlike ostrich) — they wither by midsummer.

## 6. The one unmistakable thing
**Upright cinnamon-stick fertile fronds standing in the center of a green vase** in
spring/early summer; cinnamon woolly tufts at the pinna bases.

## 7. Per-instance variation envelope
- **Varies across seeds:** clump size (0.9–1.5 m), frond count, fertile-frond presence/count, lean.
- **Variant count:** 3 — wet-woods clumps; set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_cinnamon_fern()` — model a **green vase clump** with a distinct
  **central cluster of cinnamon-colored fertile spikes** (a colored spike geometry, only
  present in the spring/early-summer `season_t` window) and woolly pinna-base tufts.
- **Textures:** broad bipinnate green frond; cinnamon woolly fertile spike.
- **`SPECIES` row (idx 9):** `flex=0.35`, `trans=0.85`, green rachis, `fall` yellow-brown
  correct; **add `v=3`**; ensure fertile-spike appearance is gated to spring–early summer.
- **Placement:** re-wire into `ZONE_SPECIES[7]` (Waterside — currently empty) + moist
  `[5]`/`[6]` woodland near water, MEDIUM density (clumps).
- **Perf:** translucent broad fronds; perf-gate waterside/woodland.

## 9. Definition of Done
- [ ] Thumbnail reads as a cinnamon-fern vase with central cinnamon fertile spikes.
- [ ] **Spring/early-summer capture** shows the cinnamon spikes (the identity); they're
      gone by fall.
- [ ] Wet-woods stand capture shows mounded clumps.
- [ ] Dense same-species stand shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
