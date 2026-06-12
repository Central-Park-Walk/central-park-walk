# BRIEF — Staghorn Sumac (Rhus typhina)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Shrub_Sumac` — generator `make_sumac()` in
  `scripts/make_undergrowth.py:987`; runtime `undergrowth_builder.gd` `SPECIES` **index 3**.
- **Layer:** shrub / sub-canopy (tall colony-forming edge shrub, 3–5 m)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP at woodland/meadow edges and disturbed sunny slopes per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **Walk video helpful** for
the **clonal colony** read — the graded-height dome of connected stems is the identity
and a single-plant still misses it.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (antler-fork branching, persistent fruit cones)
- [ ] **In a colony** (the graded-height clonal dome — essential)
- [ ] **Stem detail** (thick, densely velvety/hairy — "staghorn")
- [ ] **Compound leaf detail** (feathery pinnate, many leaflets, clustered at tips)
- [ ] **Fall color** (the spectacular scarlet — diagnostic) + **fruit cone** (crimson, upright)

## 1. Habit — how it flows over itself
- **One-liner:** flat-topped, open, **candelabra/antler-branched** shrub with thick
  velvety stems, carrying huge feathery compound leaves and upright crimson fruit cones
  at the tips — sparse and architectural, and it grows as a **clonal colony**, not a
  single plant.
- **Overall form:** open flat-topped; **3–5 m**; few, thick, forking limbs.
- **Aspect (w:h):** ~1.0; flat-topped (wider crown than mid-height).
- **First fork height:** mid — thick stems fork like antlers in the upper half.
- **Branch character:** few, thick, **velvety** limbs forking at wide angles (the
  "staghorn"); foliage and fruit concentrated at the very tips.
- **Asymmetry:** colony-driven — center stems tallest, edge stems shorter (a graded dome).

## 2. Interaction — how it meets its neighbors
- **In a stand:** **clonal colony** — a sumac patch is one connected genet of root
  suckers, tallest in the center and shorter toward the edges, forming a graded dome.
- **Target stand reading:** a domed thicket of connected antler-stemmed shrubs, height
  decreasing outward, with feathery crowns and crimson cones at the tips — read as ONE
  colony, not scattered individuals. **This is a placement lever** (graded height +
  suckering pattern), not just a model lever.

## 3. Density
- **Bucket:** open/lacy per stem (feathery compound leaves), but the colony reads as a mass.
- **Real number:** moderate; the feathery pinnate leaf gives a lacy texture — use
  `compound_mode` see-through fronds, don't fill solid.
- **Light transmission:** medium-high per plant; the colony shades the ground.

## 4. Detail
- **Stem:** thick, **densely velvety reddish-brown hairs** (the defining "staghorn"
  texture — `sr=0.95` rough is right); forking antler structure.
- **Leaf:** large **pinnately compound**, 11–31 lanceolate serrate leaflets, feathery,
  clustered at branch tips → use `compound_mode` (the honeylocust tool transfers).
- **Summer color:** medium green · **Fall:** **vivid scarlet/orange-red**
  (`fall=[0.85,0.15,0.05]` — correct; one of the best fall colors in the park).
- **Bloom:** `fc=[0,0,0]` (flowers inconspicuous); the showy feature is the **upright,
  fuzzy crimson fruit cone (drupe cluster)** at branch tips — model this, persists into winter.

## 5. Behavior
- **Wind:** stiff (`flex=0.20`) — thick stems barely move; feathery leaflets flutter; fruit cones still.
- **Seasonal:** flush → feathery summer → **scarlet fall (peak identity)** → leaf drop →
  bare antler skeleton **with persistent crimson cones through winter**.

## 6. The one unmistakable thing
**Velvety antler-forked stems + feathery compound leaves + upright fuzzy crimson fruit
cones**, blazing scarlet in fall — growing as a graded clonal colony dome.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (3–5 m, for the colony grade), fork count/angle, leaf
  cluster size, cone presence/size.
- **Variant count:** 4 — needed for the graded colony to not tile; set `v=4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_sumac()` is already bespoke (4 velvety stems, pinnate rows, fruit
  cone) — **lift it:** use `compound_mode` for real feathery fronds, sharpen the antler
  fork architecture, make the velvety stem texture read, keep the upright crimson cone.
- **Textures:** lanceolate serrate leaflet (compound), velvety bark, crimson fuzzy fruit cone.
- **`SPECIES` row (idx 3):** `fall` scarlet correct; `flex=0.20` correct; `sc`/`sr`
  velvety-brown correct; **add `v=4`.**
- **Placement:** re-wire at woodland/meadow **edges** and sunny disturbed slopes
  (`ZONE_SPECIES[2]` North Meadow edge, `[8]` Wild Meadow, woodland edge) — and place as
  **graded-height clusters** (colony pattern), not uniform scatter.
- **Perf:** lacy per plant; the colony is the cost — perf-gate the edge zones.

## 9. Definition of Done
- [ ] Thumbnail reads as staghorn sumac (velvety antler stems, feathery leaves, crimson cone).
- [ ] **Colony capture** shows a graded-height connected dome (the interaction).
- [ ] **Fall capture** shows the scarlet (the identity season).
- [ ] Persistent crimson cones in the bare-winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
