# BRIEF — Common Reed / Phragmites (Phragmites australis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Wetland_Phragmites` — generator `make_phragmites()` in
  `scripts/make_undergrowth.py:2214`; runtime `undergrowth_builder.gd` `SPECIES` **index 28**.
- **Layer:** wetland (towering colonial reed, 2–4 m). Invasive, managed → contained patches.
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at disturbed wet margins / Harlem Meer periphery per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§4. **Walk video helpful** for the wind-wave read — the dramatic traveling waves are the
signature and stills miss them. Note CP presence is **controlled** (invasive) → contained
peripheral patches, not the thousand-m² stands of a tidal marsh.

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §4
- [ ] **In a stand** (dense impenetrable monoculture WALL, towering)
- [ ] **Plume** (large purple→silver feathery panicle)
- [ ] **Winter** (pale tan canes + fluffy silver-white plumes — very distinctive)
- [ ] **Wind video** (THE wind species — traveling waves across the stand)

## 1. Habit — how it flows over itself
- **One-liner:** a **towering wall of straight, rigid cane-like stems** (2–4 m, among the
  tallest non-woody plants here) topped by a **large purple-to-silver feathery plume** —
  a dense impenetrable monoculture that **waves dramatically** in wind.
- **Overall form / crown shape:** tall vertical cane, unbranched, bamboo-like, terminal
  plume; the mass is a wall.
- **Aspect (width : height):** very tall and narrow per stem; the stand is deep (3–15 m).
- **First branch / fork height:** none — unbranched single cane with a terminal panicle.
- **Branch character:** leaves at each node extend out 30–45° then arc down; stream
  leeward in wind; prominent swollen nodes.
- **Asymmetry:** stem-straight; variation is height and plume stage across the stand.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **dense impenetrable monoculture** — the most densely packed
  species in the set, 80–200 stems/m², ~7–10 cm spacing. **You cannot see through a mature
  stand.**
- **Target stand reading:** *a disturbed wet margin reads as a towering, opaque tan/green
  wall of canes topped by a continuous silver-purple plume canopy — a reed bed, contained
  to a managed patch, not scattered stems.* The impenetrable wall is the identity; place at
  the real high stem density within a bounded patch (managed extent).

## 3. Density
- **Bucket:** opaque — the densest stand in the set.
- **Real number:** 80–200 stems/m² in mature stands ([[reference-cp-botany-full]] / wetland
  doc §4); rhizomes extend 1–2 m/yr (so a CP patch is bounded by management, not biology).
- **Light transmission:** essentially zero through a mature stand.

## 4. Detail
- **Bark / stem:** green growing-season → pale straw/tan dried; hollow with solid darker/
  purplish nodes (bamboo-like), 8–15 mm, 10–20 nodes. (`sc` tan correct.)
- **Leaf / cluster:** flat linear-lanceolate, **broad 20–40 mm** (one of the widest grasses),
  20–50 cm, **gray-green / blue-green (cool-toned, slightly silvery — NOT cattail's bright
  green)**, glaucous underside; hairy ligule fringe (ID).
- **Summer color:** gray-green / blue-green · **Fall:** golden-tan → straw (Oct), dead canes
  persist all winter. · **Bloom:** `fc=[0,0,0]`; the showy feature is the **large terminal
  panicle (20–40 cm)** — **dark purple/maroon emerging (Aug) → silvery-tan (Sep–Oct) →
  fluffy grayish-white silky plume (winter)**, persistent all winter, a major visual.

## 5. Behavior
- **Wind character:** **THE most dramatic wind species. Split signature: rigid stem sway
  8/10 + streaming/shimmering plume 4/10** (`flex=0.35` — a stand-level average; the model
  must show stiff lower canes pivoting at the base while the plumes stream and shimmer).
  Tall stiff canes lean 15–30° in synchrony; **traveling waves visibly cross the stand**
  as gusts pass (the signature). Large feathery plumes catch wind like sails, stream
  leeward, the silky hairs **shimmer/sparkle** at a faster frequency than the stems.
  Leaves stream leeward showing pale undersides (silvery sweep). Dry "shushing/whispering"
  sound; canes clack in strong wind.
- **Seasonal timeline:** asparagus-like shoots (Apr–May) → rapid growth to 2–3 m (Jun–Jul) →
  dark purple panicles emerge (Aug) → silvery-tan, seeds mature (Sep) → golden leaves +
  fluffy silver-white plumes (Oct) → pale tan canes + silver plumes persist (Nov–Mar).

## 6. The one unmistakable thing
**Sheer height + the large purple-to-silver feathery plume** atop bamboo-noded canes,
forming a dense wall that **waves in dramatic traveling waves** — and the pale-tan +
silver-plume winter silhouette.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (2–4 m — wide `s` range), plume stage (purple/silver/
  fluffy), node count, leaf lean.
- **Variant count:** 3–4 (dense wall — variants prevent the monoculture from tiling); set `v=3..4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_phragmites()` (`make_undergrowth.py:2214`) — tall straight cane with
  prominent nodes, blue-green/gray-green leaves arcing down, a **large feathery terminal
  panicle** (purple→silver per season). Author variants spanning height/plume stage.
- **Textures:** broad gray-green blade (glaucous underside); feathery plume (purple→silver→
  fluffy across season).
- **`SPECIES` row (idx 28):** **reconcile to brief** — `fc=[0,0,0]` correct, `bl=[1.0,2.0]`,
  `sc` tan correct, `flex=0.35` correct; **add `v=3..4`.**
- **Placement:** re-wire into `ZONE_SPECIES[7]` **Waterside (currently EMPTY [])** — disturbed
  wet / Harlem Meer periphery; place as **dense but CONTAINED patches** (managed invasive),
  not a park-wide spread.
- **Perf:** chunk-MultiMesh + heavy overdraw; the **dense monoculture is the perf event** (with
  cattail, the two heaviest wetland placements) — calibrate density toward the real 80–200
  stems/m² *within a small bounded patch* to control cost, then perf-gate Waterside (60 open).

## 9. Definition of Done
- [ ] Thumbnail reads as phragmites (towering noded cane + feathery plume).
- [ ] **Stand capture** shows a dense, impenetrable, towering reed wall (contained patch).
- [ ] Winter capture: pale tan canes + fluffy silver-white plumes.
- [ ] Wind capture: rigid canes + streaming/shimmering plumes + traveling waves across the stand.
- [ ] Dense stand shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after Waterside re-wire.
- [ ] User walk-around sign-off.
