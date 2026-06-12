# BRIEF — Goldenrod (Solidago spp. — canadensis / altissima / rugosa / juncea)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Flower_Goldenrod` — runtime `undergrowth_builder.gd` `SPECIES`
  **index 23**. **Generator TBD** (see §8).
- **Layer:** herb / meadow forb (colonial autumn meadow perennial, 0.8–1.0 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at meadow margins and field edges (North Meadow margins, less-mown Great Lawn
edges, field edges near the Pool) per [[reference-cp-botany-full]]; iNat CP-bbox count TO
CONFIRM. **Walk video helpful** for the **colony-wave** behavior — the synchronized swaying
of many plumes is the autumn read. Source:
[`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §13.

- [ ] **Habit, autumn bloom mass** — iNat CP; herbs doc §13
- [ ] **In a colony** (golden patches — the signature; many arching plumes as one mass)
- [ ] **Plume detail** (pyramidal, one-sided/secund, arching like a golden fountain)
- [ ] **Leaf detail** (lanceolate, densely leafy stem, triple-nerved in S. canadensis)
- [ ] **Wind/behavior video** (plumes nodding in unison — the golden sea)

## 1. Habit — how it flows over itself
- **One-liner:** upright, densely leafy, colonial perennial topped by a **pyramidal,
  one-sided (secund) golden plume that arches gracefully to one side** like a golden
  fountain — and grows in clones, so a patch reads as massed golden plumes.
- **Overall form / crown shape:** densely-leafy erect stem + arching terminal plume.
- **Aspect (width : height):** ~0.3 : 1 per stem; the colony spreads widely.
- **First branch / fork height:** unbranched below the inflorescence; densely leafy stem to the top.
- **Branch character:** moderately stiff stem; the plume's branches curve up then arch out
  one-sidedly (the diagnostic shape).
- **Asymmetry:** the secund (one-sided) plume IS the asymmetry — model it; not a symmetric spire.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **colonial golden patches** — rhizomatous clones form extensive
  patches; the visual unit is the patch of massed arching plumes, the signature of the
  Northeast autumn meadow.
- **Target stand reading:** a meadow edge in Sep–Oct reads as **a colony of golden arching
  plumes massed into a glowing patch**, nodding in unison in wind — read as one golden
  patch, not scattered single stems. This is a placement lever (rhizomatous patch).

## 3. Density
- **Bucket:** opaque mass at the plume layer; densely leafy below.
- **Real number:** 0.5–1.5 m tall (S. altissima to 2 m), 30–60 cm/clump, colonial via
  rhizomes ([[reference-cp-botany-full]]; herbs doc §13). No published LAI — bucket from habit.
- **Light transmission:** low at the plume crown; the colony is dense.

## 4. Detail
- **Bark / stem:** round, solid, 4–8 mm, green, pubescent (S. canadensis/altissima) to
  smooth-below (S. juncea); **densely leafy from base to inflorescence** — no bare zone.
- **Leaf / cluster:** alternate, lanceolate to linear-lanceolate (narrow, grass-like),
  serrate to entire, triple-nerved in S. canadensis, closely spaced, smaller upward.
- **Summer color:** medium green. · **Fall:** the bloom IS the autumn event. · **Bloom:**
  **warm true golden-yellow** (`fc=[0.85,0.75,0.10]` golden — correct), thousands of tiny
  heads massed into the arching plume; autumn, `bl=[1.5,2.5]`. Plumes go fluffy silver-gray
  as seed develops.

## 5. Behavior
- **Wind character:** the **arching plume nods and sways gracefully** (`flex=0.35`) — in a
  colony the many plumes wave in unison like a golden sea (a key autumn spectacle); the
  leafy stem below is stiffer. Dead winter stalks moderately persistent, fluffy silver-gray.
- **Seasonal timeline:** rhizome shoots / basal rosette (Apr–May) → densely-leafy stem
  (Jun–Jul, green plume buds) → golden plume bloom (Aug–Oct, peak Sep–Oct, the event) →
  fluffy silver-gray seed plumes → standing dead stalks through winter.

## 6. The one unmistakable thing
The **golden, one-sided arching plume** — a pyramidal secund inflorescence nodding to one
side like a golden fountain, massed into glowing colonial patches in the autumn meadow.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.5–1.5 m, to 2 m), plume size and arch amount, stem
  leafiness, species form (more vs less arching) — wide envelope so the colony doesn't tile.
- **Variant count:** 3–5 (densely-placed colonial species — set `v=3`).

## 8. What this brief drives (build mapping)
- **Generator:** **TBD — locate the `Flower_Goldenrod` builder or add `make_goldenrod()`
  to `scripts/make_undergrowth.py`** (there is no `make_goldenrod()` in the current function
  list). Then model the densely-leafy stem and the **one-sided arching golden plume** —
  the secund plume shape is the identity; replace any generic helper / placeholder.
- **Textures:** narrow lanceolate leaf, massed tiny golden-head plume cluster.
- **`SPECIES` row (idx 23):** reconcile to brief — `fc=[0.85,0.75,0.10]` golden,
  `bl=[1.5,2.5]` (autumn), `flex=0.35`; **add `v=3`** (densely-placed colonial).
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED; zone 8 currently
  empty) at meadow / field edges — `[8]` Wild Meadow, `[2]` North Meadow edges. Place as
  **colonial rhizomatous patches**, not uniform scatter.
- **Perf note:** chunk-MultiMesh; the plume + dense colony add overdraw — gain density from
  form/texture/placement, not card count. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as goldenrod (densely-leafy stem, one-sided arching golden plume).
- [ ] **Colony capture** shows a massed golden patch (the interaction).
- [ ] Bloom fires at `bl=[1.5,2.5]` in autumn, warm true gold.
- [ ] **Wind capture** shows plumes nodding in unison (the golden sea).
- [ ] Dense colony shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
