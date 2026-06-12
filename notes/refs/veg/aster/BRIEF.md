# BRIEF — Aster (Symphyotrichum spp. — New England / smooth aster)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).
> **No research doc** — written from general botanical knowledge. This is the bushy,
> showy-purple meadow/edge aster (*Symphyotrichum*, e.g. New England / smooth aster) —
> **distinct from the woodland white wood aster** (*Eurybia divaricata*, herbs doc §6), which
> is a low white-flowered forest carpet. Different genus, different role.

- **Archetype key:** `Flower_Aster` — runtime `undergrowth_builder.gd` `SPECIES`
  **index 29**. **Generator TBD** (see §8).
- **Layer:** herb / meadow forb (bushy fall-blooming aster, ~0.8–1.2 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP in meadows and woodland edges, a signature fall-color forb, per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **Walk video helpful** for the
**bushy-mass-of-purple** fall read. (No species research doc; not to be confused with the
woodland white wood aster, herbs doc §6 — different genus and role.)

- [ ] **Habit, fall bloom mass** — iNat CP
- [ ] **In a stand** (bushy masses smothered in small purple daisies)
- [ ] **Flower detail** (small purple/violet daisy, yellow center; massed)
- [ ] **Leaf/stem detail** (narrow lanceolate, leafy bushy stems)
- [ ] **Behavior** (whole bushy mass swaying in fall wind)

## 1. Habit — how it flows over itself
- **One-liner:** bushy, leafy, much-branched perennial that in fall is **smothered in
  masses of small purple/violet daisies with yellow centers** — a dense mounded bush of color.
- **Overall form / crown shape:** bushy, branched mound; fuller and rounder than the tall single-spire forbs.
- **Aspect (width : height):** ~0.7 : 1.
- **First branch / fork height:** branches freely from low-to-mid, building a bushy framework.
- **Branch character:** many leafy lateral branches each ending in clustered flower heads.
- **Asymmetry:** modest; a full rounded bush, not architectural.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** clump/colony-forming — adjacent bushy plants merge into
  **bushy masses of purple** at meadow and woodland edges, a signature of the fall meadow.
- **Target stand reading:** a meadow or woodland edge in fall reads as **bushy mounds
  smothered in small purple daisies**, masses merging into a violet band — read as a
  flowering mass, not scattered single daisies.

## 3. Density
- **Bucket:** opaque at bloom (smothered in flowers); leafy/bushy below.
- **Real number:** ~0.8–1.2 m tall (New England aster to ~1.5 m), bushy clump/colony
  ([[reference-cp-botany-full]]). No published LAI — bucket from habit.
- **Light transmission:** low at the flowering mass; the bush is dense.

## 4. Detail
- **Bark / stem:** round, leafy, branched, green (often purple-tinged in New England aster);
  fine-hairy.
- **Leaf / cluster:** alternate, narrow lanceolate, entire to slightly toothed, leafy along
  the branched stems (small, clasping in New England aster).
- **Summer color:** medium green. · **Fall:** the bloom IS the fall event. · **Bloom:**
  masses of small daisies — **purple/violet rays** with **yellow centers** (`fc=[0.60,0.40,0.72]`
  purple/violet — correct; white forms also occur), fall, `bl=[1.5,2.5]`.

## 5. Behavior
- **Wind character:** moderately flexible (`flex=0.30`) — the whole bushy mass sways and
  the many small daisy heads bob; a soft full-bush movement, not a single nodding spire.
- **Seasonal timeline:** clump/rosette (spring) → bushy leafy growth (summer) → mass purple
  daisy bloom (fall, the event) → fluffy pappus seed → dead stems persist into winter.

## 6. The one unmistakable thing
**Masses of small purple/violet daisies with yellow centers smothering a bushy mound** in
fall — the bushy purple-aster mass (Symphyotrichum), not the low white woodland carpet of
the white wood aster.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.8–1.5 m), bushiness/branch count, flower density,
  ray color (purple/violet, occasional white), lean — wide envelope so the mass doesn't tile.
- **Variant count:** 3–5 (densely-placed colonial fall forb — set `v=3`).

## 8. What this brief drives (build mapping)
- **Generator:** **TBD — locate the `Flower_Aster` builder or add `make_aster()`** (there is
  no `make_aster()` in the current function list). Then model the **bushy branched mound
  smothered in small purple-yellow daisies**; replace any generic helper / placeholder.
- **Textures:** narrow lanceolate leaf, small purple-violet daisy with yellow center (massed cluster).
- **`SPECIES` row (idx 29):** reconcile to brief — `fc=[0.60,0.40,0.72]` purple/violet,
  `bl=[1.5,2.5]` (fall bloom), `flex=0.30`; **add `v=3`** (densely-placed colonial).
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED; zone 8 currently
  empty) at meadow + woodland edge for fall color — `[8]` Wild Meadow, `[5]`/`[6]` woodland
  edges (North Woods / Ramble). Place as **bushy masses/colonies**, not uniform scatter.
- **Perf note:** chunk-MultiMesh; the flower-smothered bushy mass adds overdraw — gain
  density from form/texture/placement, not card count. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as a bushy purple aster (small purple/yellow daisies massed) — NOT the white wood aster.
- [ ] **Stand capture** shows bushy mounds smothered in purple at the meadow/woodland edge.
- [ ] Bloom fires at `bl=[1.5,2.5]` in fall.
- [ ] Dense mass shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
