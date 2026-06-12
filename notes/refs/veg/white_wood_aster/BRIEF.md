# BRIEF — White Wood Aster (Eurybia divaricata, syn. Aster divaricatus)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).
> **WOODLAND-FORB GROUP HERO** (redesign §6 group 3): white wood aster is the worked hero
> for the drift/carpet pattern — it proves the woodland-floor *drift* reads correctly
> before the other forbs (white snakeroot, jewelweed, woodland-edge pokeweed/burdock) fan
> out. **Validate on a drift, not one plant.**

- **Archetype key:** `Herb_WhiteWoodAster` — generator `make_white_wood_aster()` in
  `scripts/make_undergrowth.py:1711`; runtime `undergrowth_builder.gd` `SPECIES` **index 16**.
- **Layer:** herb / woodland-floor drift (low colonizing groundcover, 0.3–0.6 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP throughout the Ramble (very common), North Woods, wooded areas around the
Gill, and Hallett Nature Sanctuary per [[reference-cp-botany-full]]; iNat CP-bbox count TO
CONFIRM. The defining autumn woodland-floor wildflower of the NE. **Walk video REQUESTED**
for the drift read — how a broad carpet of white daisies floats above dark stems under the
canopy is the whole point and a single-plant still cannot show it (method §3 / redesign §3
ask).

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (wiry dark stems persisting, breaking down slowly)
- [ ] **As a DRIFT/carpet under trees** (the interaction — essential, the hero validation)
- [ ] **Stem detail** (dark brown/blackish zigzag stems — the signature)
- [ ] **Leaf detail** (heart-shaped cordate basal leaves)
- [ ] **Bloom** (flat-topped sprays of small white daisies, Aug–Oct)

## 1. Habit — how it flows over itself
- **One-liner:** low wiry stems emerge upright then arch outward, branching into flat-topped
  sprays so a colony reads as a broad, low DRIFT of tiny white daisies floating above dark
  zigzagging stems — an airy woodland carpet, not a clump.
- **Overall form / crown shape:** low spreading mound → flat-topped to gently domed mass;
  the unit is the carpet.
- **Aspect (width : height):** spreading — clumps 30–60 cm wide at 0.3–0.6 m tall; colonies
  cover many m².
- **First branch / fork height:** upper portion — stems branch widely into a flat-topped
  corymb (the flower platform).
- **Branch character:** thin wiry stems (2–4 mm) that **zigzag between nodes** and arch
  outward; flexuous, gently bending.
- **Asymmetry:** every stem leans/arches differently — the drift reads as irregular, never a grid.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **drift / carpet** (rhizomatous, forms extensive patches) — the
  dominant late-season groundcover under deciduous canopy; adjacent clumps merge into a
  continuous low sheet of white over dark stems.
- **Target stand reading:** *a broad woodland-floor drift under trees — a low continuous
  carpet of small white daisies floating on dark wiry zigzag stems, masses flowing into each
  other, NOT spaced individual clumps.* **THIS IS THE HERO READ** — the whole woodland-forb
  group's drift/carpet pattern is proven here; validate on the drift, not the specimen
  (method §4).

## 3. Density
- **Bucket:** open/lacy per plant but the drift reads as a continuous low sheet.
- **Real number:** 0.3–0.6 m tall, clumps 30–60 cm spreading to many-m² colonies; dry-to-
  mesic woodland shade ([[reference-cp-botany-full]]). High placement density as a carpet —
  this is a drift species, place it as one.
- **Light transmission:** high per plant (wiry, airy); the carpet covers the floor.

## 4. Detail
- **Bark / stem:** **the signature — thin dark brown to blackish-purple wiry stems that
  zigzag between nodes;** strong contrast against green leaves. `sc=[0.22,0.15,0.10]` DARK
  is correct and is the identity — keep the stems dark.
- **Leaf / cluster:** basal/lower leaves **heart-shaped (cordate)** (5–10 cm) on long
  petioles, coarsely serrate; upper leaves smaller, sessile, lanceolate; lower leaves often
  gone by bloom (bare lower stem, leafy upper).
- **Summer color:** dark green · **Fall:** the bloom IS the fall event · **Bloom:**
  flat-topped corymbs (10–20 cm) of small (1.5–2 cm) white daisies — 5–10 white rays, disc
  aging yellow→reddish-purple; **late season (Aug–Oct), `bl=[1.5,2.5]`** is correct
  (late-season bloom window). `fc` white is correct.

## 5. Behavior
- **Wind character:** very flexible and airy (`flex=0.30`). Thin wiry stems and the flat
  flower platform sway and bounce in light breeze; heads bob on thin pedicels; the whole
  upper structure moves as a fluid wave. The drift should ripple as one mass with local
  per-stem variation (shared wind field).
- **Seasonal timeline:** shoots from rhizomes (Apr) → cordate basal leaves, stems elongate
  (May–Jun) → branching, lower leaves deteriorating (Jul) → white daisy sprays open (Aug) →
  **peak white carpet under trees** (Sep–Oct) → seeds disperse, stems brown (Nov) → wiry
  dark stems persist, breaking down slowly (Dec–Mar).

## 6. The one unmistakable thing
**Dark, near-black zigzag stems carrying flat sprays of small white daisies, drifting as a
late-season carpet across the woodland floor** — the dark stem against white bloom is the ID.

## 7. Per-instance variation envelope
*This is the hero — the drift MUST NOT tile (redesign §4). Widen the variants and lean on
stand composition.*
- **Varies across seeds:** clump height (0.3–0.6 m), arch amount, branch spread, flower-head
  count, basal-leaf presence, lean direction. Span the range so a dense carpet never repeats.
- **Variant count:** 4–5 (`v=4`+) — densely placed drift species; the anti-tiling lever.
  Confirm the builder variant picker handles >3 before committing.

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_white_wood_aster()` (`scripts/make_undergrowth.py:1711`) —
  build low arching wiry stems with **dark zigzag stem geometry**, flat-topped corymb
  sprays of small white daisies, cordate basal leaves; author 4–5 variants spanning §7.
- **Textures:** small white daisy (disc aging yellow→purple); cordate basal leaf; dark wiry
  stem material.
- **`SPECIES` row (idx 16):** reconcile to this brief — `sc=[0.22,0.15,0.10]` dark zigzag
  (correct — the signature, keep dark), `bl=[1.5,2.5]` late-season (correct), `fc` white
  (correct), `flex=0.30` (correct — airy). **Raise `v` to 4–5** (densely-placed drift).
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[5]` (North Woods) and
  `[6]` (Ramble) at **HIGH carpet density as a woodland-floor drift** (not scattered
  individuals) — this is the hero re-enable that proves the drift pattern; gate on the
  canopy buffer (shade).
- **Perf:** chunk-MultiMesh + overdraw; a dense drift is the perf event — gain the carpet
  from many low light-per-instance meshes placed as a sheet, NOT heavy per-plant cards.
  Perf-gate the Ramble/North Woods after placement re-wire (45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as white wood aster (dark zigzag stems, white daisy spray).
- [ ] **DRIFT capture (North Woods / Ramble floor)** — a continuous low white carpet over
  dark stems, masses merging. *The drift is the hero validation unit — proves the pattern
  for the whole woodland-forb group.*
- [ ] Dense drift shows NO tiling (§7 — variants visibly span the envelope).
- [ ] Late-season bloom (`bl=[1.5,2.5]`); wiry dark stems persist in the winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
