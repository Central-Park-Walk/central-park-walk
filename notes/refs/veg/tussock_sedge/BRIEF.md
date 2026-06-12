# BRIEF — Tussock Sedge (Carex stricta)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Grass_TussockSedge` — generator `make_tussock_sedge()` in
  `scripts/make_undergrowth.py:2372`; runtime `undergrowth_builder.gd` `SPECIES` **index 32**.
- **Layer:** grass / sedge (tussock-forming wetland sedge; leaves 0.4–0.8 m above the mound)
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at marsh / wet-meadow / lake margins (standing water) per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§8. The tussock pedestal is the whole identity — confirm the raised-mound read from CP
stills/clip.

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §8
- [ ] **Tussock pedestal** (the raised root/peat mound — the unmistakable feature)
- [ ] **Scattered mounds** (the stand read — pedestals proud of the water)
- [ ] **Winter** (straw thatch skirt draping the mound)
- [ ] **Wind video** (arch + stream: the leaf fountain "pours" downwind, base immobile)

## 1. Habit — how it flows over itself
- **One-liner:** a raised **TUSSOCK PEDESTAL** (a dense root/peat mound 15–50 cm above the
  water) from whose top a **fountain of narrow arching leaves** sprays outward and down —
  a fountain-on-a-pedestal.
- **Overall form / crown shape:** brown mound base + green arching leaf fountain (50–80 cm
  canopy, often wider than the mound) with triangular flowering culms.
- **Aspect (width : height):** mound 20–50 cm wide × 15–50 cm tall; leaves arch out beyond it.
- **First branch / fork height:** leaves emerge erect from the mound top, then arch outward/
  downward with tips near the water.
- **Branch character:** narrow 2–5 mm leaves; **triangular culms** ("sedges have edges"),
  stiffer than round grass stems of the same size.
- **Asymmetry:** the leaf fountain sprays in all directions; dead thatch drapes the sides.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **scattered raised mounds** — discrete tussocks proud of the
  surrounding water/mud, creating microtopography; not a continuous mat. Each mound is its
  own pedestal with open water/mud between.
- **Target stand reading:** *a marsh reads as a field of distinct brown pedestals each
  topped by a green leaf fountain, standing up out of the water with dark water/mud between
  them — scattered mounds, not a uniform sward.* The raised-mound spacing is the read; place
  as discrete tussocks with gaps, each sitting **proud of** the surface.

## 3. Density
- **Bucket:** dense per mound (fountain of leaves); the stand is scattered mounds with gaps.
- **Real number:** 20–60+ culms/tussock, 10–30 growing points/mound; mounds discrete
  ([[reference-cp-botany-full]] / wetland doc §8).
- **Light transmission:** moderate per fountain; open water between mounds.

## 4. Detail
- **Bark / stem:** flowering culms **TRIANGULAR**, solid, 1.5–3 mm, green with reddish-purple
  base; **dark reddish-brown basal sheaths** at the mound top (distinctive). The mound itself
  is brown/dark-brown root+peat.
- **Leaf / cluster:** linear, narrow **2–5 mm**, 30–60 cm, channeled (M-section), scabrous
  margins, long-attenuate tips; arching fountain spray; medium-dark true green.
- **Summer color:** medium-dark green · **Fall:** yellow-bronze (Oct–Nov). Winter: pale
  straw; **old leaves drape the mound sides as a thatch skirt**; reddish-brown basal sheaths
  remain. · **Bloom:** `fc=[0,0,0]`; modest 3–5 cylindrical spikes per culm, greenish-brown,
  **early (Apr–Jun)**, not showy, not persistent.

## 5. Behavior
- **Wind character:** **arch + stream (fountain pours), stiffness 4/10 leaves / 6/10 culms**
  (`flex=0.30` — consistent; the solid mound base is immobile, the triangular culms add
  stiffness, the leaves carry the motion). All movement is in the leaf canopy: the **arching
  leaves stream directionally** — windward leaves press down, leeward leaves stream out,
  giving a "windswept" asymmetric fountain that **pours downwind** (~0.8 Hz). The **mound is
  motionless** (a solid pedestal). High-pitched scratchy hiss (rough margins).
- **Seasonal timeline:** bright green leaves + early flowering culms (Mar–Apr) → flowering
  (Apr–Jun, early) → full arching leaf canopy (Jun–Aug) → yellow-bronze (Sep–Oct) → straw
  thatch draping the mound, tussock structure fully visible (Nov–Mar).

## 6. The one unmistakable thing
The **raised tussock PEDESTAL** standing proud of the water, topped by an **arching leaf
fountain** with a dead-straw **thatch skirt** and **triangular culms**.

## 7. Per-instance variation envelope
- **Varies across seeds:** mound height (15–50 cm) and diameter (20–50 cm), leaf-canopy
  fullness, thatch-skirt amount, culm count.
- **Variant count:** 3 (scattered discrete mounds — variants prevent identical pedestals);
  set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_tussock_sedge()` (`make_undergrowth.py:2372`) — build the **brown
  pedestal mound** (sits proud of the surface), a **fountain of narrow arching leaves** from
  the top, **triangular culms**, and a draping **dead-straw thatch skirt** on the sides.
  Reddish-brown basal sheaths. Author 3 variants spanning mound size.
- **Textures:** narrow channeled green blade (scabrous); brown mound/thatch; reddish basal
  sheath; modest cylindrical spike.
- **`SPECIES` row (idx 32):** **reconcile to brief** — `fc=[0,0,0]` correct, `bl=[1.0,2.0]`,
  `flex=0.30` correct; set `v=3`. (Note its layer is sedge — triangular, not grass.)
- **Placement:** re-wire into `ZONE_SPECIES[7]` **Waterside (currently EMPTY [])** —
  marsh / wet-meadow standing water; place as **discrete raised tussocks with open-water
  gaps**, each proud of the surface (NOT a continuous mat — distinct from cattail/phragmites).
- **Perf:** chunk-MultiMesh; moderate density (scattered mounds) — perf-gate Waterside
  (60 open).

## 9. Definition of Done
- [ ] Thumbnail reads as tussock sedge (raised pedestal + arching leaf fountain + triangular culms).
- [ ] **Marsh capture** shows scattered distinct mounds proud of the water with gaps.
- [ ] Winter capture: straw thatch skirt draping the mound; tussock structure visible.
- [ ] Wind capture: arch + stream — leaf fountain pours downwind, mound base immobile.
- [ ] Scattered mounds show no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after Waterside re-wire.
- [ ] User walk-around sign-off.
