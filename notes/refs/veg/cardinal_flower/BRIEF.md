# BRIEF — Cardinal Flower (Lobelia cardinalis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_CardinalFlower` — generator `make_cardinal_flower()` in
  `scripts/make_undergrowth.py:1435`; runtime `undergrowth_builder.gd` `SPECIES` **index 15**.
- **Layer:** herb (slender single-stemmed streamside spire, 0.6–1.2 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP streamside along the Loch, the Gill, Ravine edges, and North Woods stream
banks per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **Walk video
helpful** for how the scarlet spikes read in a small wet-edge group (the color is the
whole point and must read against dark wet shade).

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (dead stem with capsule raceme; green overwintering rosette)
- [ ] **In a small streamside group** (3–8 stems — the interaction)
- [ ] **Stem detail** (single unbranched, often red-purple tinged)
- [ ] **Leaf detail** (lanceolate, finely serrate, leggy base)
- [ ] **Bloom** (BRILLIANT SCARLET terminal raceme — the signature)

## 1. Habit — how it flows over itself
- **One-liner:** a single, strictly upright, unbranched green spire topped by an
  unmistakable scarlet flame — an exclamation point, narrow and columnar, often leggy at
  the base.
- **Overall form / crown shape:** narrow columnar spire; terminal red spike.
- **Aspect (width : height):** very narrow, ~0.2 : 1 (15–30 cm spread at 0.6–1.2 m).
- **First branch / fork height:** none — single unbranched stem below the flower spike.
- **Branch character:** single round solid stem (4–8 mm), moderately rigid, green to
  red-purple tinged in sun; no lateral branching.
- **Asymmetry:** little — a straight spire; lower leaves often drop, leaving a leggy base.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **small groups** (3–8 stems) rather than large colonies — slender
  scarlet spires clustered at a wet edge, each a distinct vertical, gaps between.
- **Target stand reading:** *a small group of scarlet spires standing at the water's edge,
  the brilliant red reading vividly against dark wet shade — distinct exclamation points,
  not a mass.* (Validate on a small streamside group.)

## 3. Density
- **Bucket:** open (narrow single stems, sparse foliage).
- **Real number:** 0.6–1.2 m, spread only 15–30 cm, groups of 3–8; streamside/wet
  ([[reference-cp-botany-full]]). Low placement density, clustered at water edges.
- **Light transmission:** high (narrow, leggy stems).

## 4. Detail
- **Bark / stem:** single unbranched, green to red-purple tinged (more in sun), smooth to
  finely hairy.
- **Leaf / cluster:** lanceolate to elliptic (5–15 cm), finely serrate, sessile/clasping,
  dark green; lower leaves wilt by bloom → leggy base.
- **Summer color:** dark green · **Fall:** yellowing · **Bloom:** **the signature — a
  terminal raceme (15–30 cm) of intense PURE SCARLET zygomorphic flowers (3–4 cm),** opening
  bottom-to-top, with a protruding staminal column; one of the most vivid reds in the NA
  flora. `fc=[0.85,0.08,0.08]` brilliant scarlet is correct — this color is the identity.

## 5. Behavior
- **Wind character:** moderate single-stem oscillation (`flex=0.30` — correct). The narrow
  spike sways as a unit in a slow graceful arc; flowers firmly attached (don't shatter);
  strong wind leans the whole plant 30–45°. A gentle top-weighted sway.
- **Seasonal timeline:** green basal rosette (Mar–Apr) → leafy stem elongates (May–Jun) →
  green bud cluster at tip (Jul) → **scarlet spike peak, hummingbirds** (late Jul–Aug) →
  upper flowers opening as lower set capsules (Sep) → dead stem with capsule raceme; **green
  rosette overwinters** (Oct–Nov).

## 6. The one unmistakable thing
**The brilliant pure-scarlet terminal spike** on a slender unbranched stem — no other
wildflower in range is this vivid red. If the red reads dull or pink, the identity is lost.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.6–1.2 m), spike length/flower count, stem red-tint,
  legginess, lean. Low-density clustered accent.
- **Variant count:** 2–3 (low-density streamside accent; modest count suffices).

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_cardinal_flower()` (`scripts/make_undergrowth.py:1435`) — build
  the slender unbranched spire with a **brilliant scarlet terminal raceme** (zygomorphic
  flowers opening bottom-up, protruding staminal column); leggy lower stem.
- **Textures:** lanceolate serrate leaf; scarlet zygomorphic flower spike cluster; brown
  capsule-raceme winter variant.
- **`SPECIES` row (idx 15):** reconcile to this brief — `fc=[0.85,0.08,0.08]` scarlet
  (correct — its signature, keep saturated), `bl=[1.0,1.6]`, `flex=0.30` (correct).
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[7]` (Waterside,
  streamside/wet — **currently EMPTY, populated here**) at **low density clustered at water
  edges** (small groups, always near water).
- **Perf:** chunk-MultiMesh + overdraw; cheap per plant (narrow spire) — gain the punch from
  the scarlet flower-spike card and low clustered placement. Perf-gate after placement
  re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as cardinal flower (slender scarlet spire, bottom-up bloom).
- [ ] **Streamside group capture** shows clustered scarlet spires at a water edge, vivid
  against shade. *The small group is the validation unit.*
- [ ] The scarlet reads pure and brilliant at bloom (`bl=[1.0,1.6]`).
- [ ] Dead capsule raceme + green overwintering rosette in the cold-season capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
