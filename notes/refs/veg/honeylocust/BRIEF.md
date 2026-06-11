# BRIEF — Honeylocust (Gleditsia triacanthos var. inermis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md). Obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md). **Hero for the
> lacy / compound canopy** (§6) — the worked example for fine-textured, see-through crowns.

- **Archetype key:** `honeylocust` (~6 k combined incl. pagoda/ash-type fallbacks — high count)
- **Layer:** canopy (open, airy — casts dappled shade; common along drives/edges)
- **Tier coverage:** `_s` / `_m` / `_l` (verify against TIER_BOUNDS)
- **Brief written:** 2026-06-11 · **by:** Opus 4.8

## Reference set
- [x] **iNaturalist, CP-geofiltered** — API: **217 research-grade _Gleditsia triacanthos_**
  observations in the park bbox. Population real and abundant. CP plantings are the **thornless
  `inermis`** cultivars (Shademaster/Skyline etc.).
- [x] **Habit / leaf / fall / behavior (authoritative)** — Morton Arboretum (thornless
  honey-locust), NCSU Extension, Missouri Botanical, [[reference-tree-canopy-data]] §7.
- [ ] **Walk-through / in-stand video** — NOT gathered (not prominent in the Mall/North Woods
  videos). **Non-blocking:** the lacy open canopy is well-documented and is fundamentally a
  *texture/density* problem, not a habit-mystery. Offer-of-more-videos noted; not needed here.

## 1. Habit — how it flows over itself
- **One-liner:** *a broad, open, spreading tree on a fairly high bole; ascending then
  wide-spreading limbs in a slightly zigzag (angular) pattern carry a sparse, lacy, ferny
  canopy you can see straight through — graceful and airy, never a solid mass.*
- **Overall form / crown shape:** broad, spreading, rounded; **open and airy** (the defining
  quality); delicate.
- **Aspect (width : height):** ~0.5–0.7 : 1 (9–14 m spread on 18–24 m).
- **First branch / fork height:** fairly high clear bole (`branch_start` 0.28 right);
  cultivars trained to a clean trunk.
- **Branch character:** ascending then wide-spreading; **slightly zigzag / angular**;
  `branch_angle` 48 + short `branch_length_ratio` 0.28 → the open architecture is visible
  *through* the foliage (the branch skeleton reads even in summer).
- **Asymmetry:** graceful, irregular spread; open enough that lean and gaps read clearly.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** even grouped, honeylocusts **do NOT close into a ceiling** — the
  lacy crowns overlap into a soft dappled veil with sky/light showing through. Coherence here
  is *airy overlap*, not closure.
- **Target stand reading:** *a honeylocust group reads as a luminous, see-through, dappled
  canopy — filtered light reaching the ground, branch skeletons visible through fine foliage —
  distinct from the solid oak/linden ceiling.*

## 3. Density
- **Bucket:** **open / lacy** — among the lightest shade of any large tree (the defining bucket).
- **Real number:** LAI **2.0–3.5** (lowest of large deciduous shade trees); compound
  architecture creates intrinsic gaps ([[reference-tree-canopy-data]] §7). Already encoded:
  `CANOPY_OPACITY` 0.45.
- **Light transmission:** **~30–50%** — grass grows underneath; even single leaves are see-through.

## 4. Detail
- **Bark:** gray-brown; narrow ridges, somewhat scaly/plated; rough trunk. (`bark_color`
  `(0.35,0.28,0.20)`.) Thornless cultivars — no trunk thorns.
- **Leaf:** alternate, **pinnately / bipinnately compound**, 15–30 tiny oval leaflets
  (1.4–3.6 cm each), ferny/lacy texture. **Currently a single-plane compound-leaf
  approximation** ([[reference-tree-canopy-data]] §7) — the §6 lacy-canopy task is to make
  this read as fine ferny foliage via **texture + card placement**, not solid cards.
- **Summer color:** light/medium green (bright, translucent). · **Fall:** **clear yellow**,
  early (Oct). · **Bloom:** inconspicuous greenish (ignore). · **Fruit:** long twisted
  brown pods (optional detail; can hang into winter).

## 5. Behavior
- **Wind character:** the fine compound foliage **flutters and sways readily** — among the
  more mobile broadleaf crowns (lots of small leaflets catch wind); limbs themselves moderate.
  Tune toward a light, lively shimmer (more mobile than oak, less than birch).
- **Seasonal timeline:** **late to leaf out** (May) → light airy green summer → **clear-yellow,
  early drop** (short foliated season; Oct) → bare open zigzag skeleton + twisted pods in winter.
  (Short season → distinct WINTER_RETENTION / phenology timing — leafless longer than its neighbors.)

## 6. The one unmistakable thing
The **see-through lacy ferny canopy casting dappled shade** — you read the branch skeleton and
the ground through it. If the crown is a solid opaque mass, it is wrong; openness *is* the species.

## 7. Per-instance variation envelope
- **Varies across seeds:** crown width, openness/density (within the lacy bucket), zigzag
  angularity, bole height, lean, height (DBH), leaf-out/drop timing.
- **Variant count:** **6–8** (high combined count; confirm picker handles >5).

## 8. What this brief drives (build mapping)
- **Generator/params** (`generate_trees_mtree.py`, `honeylocust` @ ln 690): keep open
  architecture (`branch_angle` 48, short branches, high bole); ensure the **branch skeleton
  reads through the foliage** (don't over-fill). Low `leaf_density`. Widen to 6–8 variants.
- **Textures — the hero deliverable:** make the compound leaf read **lacy/ferny** via a
  fine-leaflet leaf/cluster texture + sparse card placement (§6 lacy-canopy proof the cheaper
  model copies). Keep `CANOPY_OPACITY` 0.45.
- **Builder/placement** (`tree_builder.gd`): airy overlap, NOT closure (§2).
- **Perf budget:** *lacy = fewer/sparser cards* — naturally within the fragment budget; do not
  compensate openness with overdraw. Texture richness is ~free
  ([`trees.md`](../../../docs/trees.md) §4g). Perf gate ×5, no regression.

## 9. Definition of Done (captures that validate this brief)
- [ ] Thumbnail reads as a lacy, see-through honeylocust — branch skeleton visible through foliage.
- [ ] **In-game stand capture** — dappled, luminous, see-through canopy; filtered light on the
  ground; distinct from the oak/linden ceiling. *Openness is the validation criterion.*
- [ ] Tier handoff + crossfade ([`tree_model_redesign.md`](../../../docs/tree_model_redesign.md) §9)
  — note the impostor must preserve the see-through read, not bake a solid blob.
- [ ] Dense stand shows **no tiling** (§7).
- [ ] Seasonal: late leaf-out + clear-yellow early drop + long bare-skeleton winter.
- [ ] Perf gate ×5 equal-or-better.
- [ ] User walk-around sign-off.
