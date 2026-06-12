# BRIEF — Wild Grape (Vitis riparia / labrusca)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_WildGrape` — generator `build_wild_grape()` in
  `scripts/make_vine.py:387` (seed 4400); runtime `vine_builder.gd` (**DISABLED, ln 111**).
- **Layer:** vine (heavy woody tendril vine; native; drapes high canopy)
- **Tier coverage:** n/a (tree-attached; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Native, heavy old vines draping CP woodland-edge canopy per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. **Walk video helpful** for the big-leaf canopy drape and
shreddy-bark old stems.

- [ ] **Habit on a host** — heavy tendril vine draping into the high canopy
- [ ] **Leaf detail** (large, heart-shaped, 3-lobed, coarsely toothed)
- [ ] **Bark** (old stems shreddy/peeling — distinct from porcelain berry)
- [ ] **Fruit + fall** (green→purple grape clusters; yellow fall)

## 1. Habit — how it flows over itself
- **One-liner:** a heavy, woody, tendril-climbing vine that drapes thick **curtains of
  large heart-shaped leaves over the high canopy edge** — old stems are ropey and shreddy,
  the whole thing a hanging mantle off tree crowns.
- **Climbing mechanism:** **forked tendrils** gripping branches; old woody stems hang in
  ropes — drapes off the canopy (sprawl/drape over a host crown, with hanging festoons).
- **Asymmetry:** heavy irregular drapes following the canopy edge.

## 2. Interaction — how it meets its neighbors
- **On a host:** climbs high and drapes leaf curtains over the crown edge; old vines form
  thick ropey trunks hanging from the canopy.
- **Target stand reading:** a woodland-edge tree crown half-buried under hanging
  grape-leaf curtains, ropey woody stems descending.

## 3. Density
- **Bucket:** dense large-leaf curtain (big leaves, coarse texture).
- **Light transmission:** low under the drape.

## 4. Detail
- **Stem:** woody, ropey; **old bark shreddy/peeling in strips** (the ID vs porcelain berry's white pith).
- **Leaf:** **large (10–20 cm), heart-shaped, often 3-lobed, coarsely toothed**; medium green,
  paler/downy beneath.
- **Summer color:** medium green · **Fall:** yellow.
- **Bloom:** inconspicuous greenish panicles (late spring); fragrant; **green grape
  clusters ripening to dusty purple-black** (late summer–fall) — small wild grapes.

## 5. Behavior
- **Wind:** the big-leaf curtains flutter heavily and sway with the host canopy.
- **Seasonal timeline:** leaf-out (spring) → green canopy drape (summer) → green→purple
  grape clusters (late summer–fall) → **yellow fall** → leaf drop → bare ropey shreddy-bark
  stems hanging from the canopy (winter, deciduous).

## 6. The one unmistakable thing
Heavy **curtains of large heart-shaped grape leaves draping the high canopy** on ropey,
shreddy-barked woody stems, with small green-to-purple grape clusters.

## 7. Per-instance variation envelope
- **Varies across seeds:** drape mass/length, leaf size, stem ropiness, fruit load, host size.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `build_wild_grape()` — redesign to a **heavy canopy drape** with hanging
  large-leaf festoons (strand-card lessons transfer for the hanging curtains) + ropey
  shreddy-bark stems; large heart-shaped 3-lobed leaf cards; grape clusters.
- **Textures:** large heart-shaped 3-lobed grape leaf (green + yellow fall); shreddy bark;
  purple grape cluster.
- **Re-enable:** after GLB passes brief + perf gate.
- **Placement:** native — woodland-edge host crowns (zones 5/6, edge-boosted), heavier on big hosts.
- **Perf:** big-leaf drape = significant overdraw on the host; perf-gate after re-enable.

## 9. Definition of Done
- [ ] Reads as wild grape (big heart-leaf canopy curtains, ropey shreddy stems).
- [ ] Fall capture shows yellow leaves + purple grape clusters.
- [ ] On-host capture — draping the canopy edge (interaction).
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
