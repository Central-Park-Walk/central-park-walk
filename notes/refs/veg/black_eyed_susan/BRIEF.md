# BRIEF — Black-eyed Susan (Rudbeckia hirta)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).
> **No research doc** — written from general botanical knowledge; genus context from the
> cutleaf coneflower (*Rudbeckia laciniata*) in
> [`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §4. The key
> distinction is the **central cone color** (see §6).

- **Archetype key:** `Herb_BlackeyedSusan` — generator `make_black_eyed_susan()` in
  `scripts/make_undergrowth.py:2414`; runtime `undergrowth_builder.gd` `SPECIES` **index 34**.
- **Layer:** herb / meadow forb (short dry-meadow daisy, ~0.6–0.9 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP in dry sunny meadows and field edges per [[reference-cp-botany-full]]; iNat
CP-bbox count TO CONFIRM. A meadow walk would confirm the **scattered-daisy-over-grass**
read. (No species research doc — *Rudbeckia* genus context from herbs doc §4 cutleaf coneflower.)

- [ ] **Habit, bloom mass** — iNat CP; *Rudbeckia* genus (herbs doc §4)
- [ ] **In a dry-meadow stand** (yellow daisies scattered over grass matrix)
- [ ] **Flower detail** (yellow rays + DARK BROWN/BLACK raised central cone — the ID)
- [ ] **Leaf/stem detail** (hairy, coarse; lanceolate-to-ovate leaves)
- [ ] **Behavior** (daisy heads nodding on stems)

## 1. Habit — how it flows over itself
- **One-liner:** short, erect, hairy meadow daisy — a leafy clump sending up wiry stems
  each topped by a single golden-yellow daisy with a **dark raised central cone**, the
  flowers held aloft over a grassy matrix.
- **Overall form / crown shape:** low erect clump; flowers on single peduncles above foliage.
- **Aspect (width : height):** ~0.5 : 1.
- **First branch / fork height:** sparse branching in the upper portion to carry flower heads.
- **Branch character:** wiry, hairy stems; flowers held singly, nodding slightly.
- **Asymmetry:** modest; a loose clump, not architectural.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** clump-forming, short-lived (biennial/short-lived perennial) —
  reads as **yellow daisies scattered/dotted over a grass meadow matrix**, not a colony wall.
- **Target stand reading:** a dry sunny meadow reads as **golden daisy faces dotted above
  the grass**, each with a dark eye — a constellation of yellow over green, mixed into the
  meadow matrix rather than a pure patch.

## 3. Density
- **Bucket:** dappled/open (a clump with flowers on stalks); reads as dotted accents in the matrix.
- **Real number:** ~0.6–0.9 m tall (short — shorter than coneflower's 1.5–2 m), clump-forming
  ([[reference-cp-botany-full]]). No published LAI — bucket from habit.
- **Light transmission:** high (open clump, foliage at base, flowers on stalks).

## 4. Detail
- **Bark / stem:** round, **hairy/bristly** (the "hirta"), green, wiry.
- **Leaf / cluster:** alternate, lanceolate to ovate, coarsely toothed, **hairy/rough** on
  both surfaces (NOT deeply cut like coneflower's laciniate leaves) — basal and stem leaves.
- **Summer color:** medium green. · **Fall:** the bloom carries the summer-into-fall event.
  · **Bloom:** golden-yellow ray florets around a **dark brown-to-black raised central
  cone/disc** (`fc=[0.88,0.72,0.08]` yellow — correct; model the dark cone separately);
  6–10 cm heads, `bl=[1.0,1.8]`.

## 5. Behavior
- **Wind character:** moderately flexible (`flex=0.30`) — daisy heads nod on wiry stems,
  hairy leaves flutter at the base; a gentle bobbing of the flower faces.
- **Seasonal timeline:** rosette/clump (spring) → leafy clump (early summer) → yellow
  daisy bloom with dark eye (summer into fall) → dark conical seed heads → dead stems persist.

## 6. The one unmistakable thing
The **dark brown/black raised central cone** ringed by golden-yellow rays — this is the
distinction from the cutleaf coneflower, whose cone is **green/greenish-yellow**. Same
genus, but the eye color is the ID: black-eyed (Rudbeckia hirta) vs green-coned (R. laciniata).

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.6–0.9 m), flower count, cone prominence, clump fullness, lean.
- **Variant count:** 3–4 (dotted meadow accent; vary so the scatter doesn't tile).

## 8. What this brief drives (build mapping)
- **Generator:** `make_black_eyed_susan()` (`scripts/make_undergrowth.py:2414`) — model the
  short hairy clump, coarse hairy lanceolate-to-ovate leaves, and the yellow daisy with a
  **dark raised cone** (the distinction from coneflower's green cone). Replace any generic helper.
- **Textures:** hairy lanceolate/ovate leaf, yellow-ray daisy with dark-brown/black cone.
- **`SPECIES` row (idx 34):** reconcile to brief — `fc=[0.88,0.72,0.08]` yellow (dark cone
  modeled in geometry/texture, not `fc`), `bl=[1.0,1.8]`, `flex=0.30`; height short (~0.6–0.9 m).
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED; zone 8 currently
  empty) in dry sunny meadow — `[8]` Wild Meadow, `[2]` North Meadow. Place as **dotted
  accents in the meadow matrix**, not a pure patch.
- **Perf note:** chunk-MultiMesh; low per-plant overdraw — gain density from
  form/texture/placement. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as black-eyed Susan (yellow rays, DARK central cone, hairy clump).
- [ ] Dark cone clearly distinct from coneflower's green cone (§6).
- [ ] **Dry-meadow capture** shows daisies dotted over the grass matrix.
- [ ] Bloom fires at `bl=[1.0,1.8]`.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
