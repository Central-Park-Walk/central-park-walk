# BRIEF — Switchgrass (Panicum virgatum)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Grass_Switchgrass` — generator `make_switchgrass()` in
  `scripts/make_undergrowth.py:2325`; runtime `undergrowth_builder.gd` `SPECIES` **index 31**.
- **Layer:** grass (tall warm-season fountain bunchgrass, 1.2–2.0 m)
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)
- **Note:** this is the generic placeholder the wildflower-meadow memory wants replaced
  ([[reference-vegetation-inventory]] / [[project-native-wildflower-models]]) — keep it a
  REAL switchgrass (do not let it stand in for unmodeled species).

## Reference set
Present in CP in managed native-grass meadows / meadow edges per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§7. **Walk video helpful** for the fountain sway + airy panicle — the cloud-like panicle
streaming is the identity. CP is likely upland ecotype / cultivar (tighter clumps).

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §7
- [ ] **Fountain clump** (tall, vase, larger than little bluestem)
- [ ] **Panicle** (large airy diffuse "cloud" — the unmistakable feature)
- [ ] **Fall color** (warm golden — NOT little bluestem's copper)
- [ ] **Wind video** (fountain sway; panicle streams like a banner)

## 1. Habit — how it flows over itself
- **One-liner:** a **tall vase/FOUNTAIN clump** — stiff lower stems anchoring, upper stems
  and a **large, airy, diffuse panicle** arcing outward and streaming like a cloud above
  the foliage.
- **Overall form / crown shape:** fountain — tight cylindrical base widening dramatically
  upward; panicles well beyond the leaf silhouette.
- **Aspect (width : height):** large-framed (base 30–60 cm, crown 40–80 cm); 2× the size of
  little bluestem.
- **First branch / fork height:** stiff lower two-thirds; flexible arching upper third where
  panicle weight pulls it out.
- **Branch character:** 20–80 stems, robust 3–6 mm (thicker than bluestem); long arching
  8–15 mm blades.
- **Asymmetry:** the fountain arcs outward in all directions; airy and irregular at the top.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **meadow matrix of large fountains** — clumps stay discrete
  (bunchgrass / tight upland clumps) but are big, so the matrix is coarser and taller than
  little bluestem's; the airy panicles merge into a misty upper layer.
- **Target stand reading:** *a meadow reads as tall fountain clumps with a hazy diffuse
  panicle layer floating above the foliage, streaming together in wind — a coarse matrix of
  big fountains, not a fine lawn.* Place as discrete large clumps with forb gaps.

## 3. Density
- **Bucket:** open/airy — the diffuse panicle is misty; foliage moderately dense per clump.
- **Real number:** 20–80 stems/clump; meadow matrix (coarser than bluestem's 4–8/m² because
  clumps are larger) ([[reference-cp-botany-full]] / wetland doc §7).
- **Light transmission:** high through the panicle layer; moderate through foliage.

## 4. Detail
- **Bark / stem:** green (reddish/purple at nodes) → golden fall; robust 3–6 mm, round/hollow.
- **Leaf / cluster:** flat linear **8–15 mm** (wider/medium-textured vs bluestem's 3–6 mm),
  25–50 cm, long arching, **prominent pale midrib** on the upper surface; hairy ligule.
- **Summer color:** blue-green to green (cultivar-variable) · **Fall:** **warm GOLDEN
  yellow / amber (Oct) — NOT the copper/wine of little bluestem** (the key distinction).
  Winter: pale straw. · **Bloom:** `fc=[0,0,0]`; the feature is the **large diffuse open
  PANICLE (20–50 cm)** — repeatedly branching on hair-like pedicels, tiny spikelets, a
  misty/foggy cloud; green-purple → golden-tan (Jul–Aug), a diffuse purple-pink haze in
  peak flower; persists thinning through winter.

## 5. Behavior
- **Wind character:** **FOUNTAIN sway, stiffness 7/10 base / 3/10 panicle** (`flex=0.35` —
  consistent; the stiff base anchors while the top arcs and streams). The stiffness gradient
  is the identity: base stays put, **upper stems and panicle arc outward and stream
  leeward like a banner**. The large open panicle catches wind like a net — in even light
  wind it's in constant motion, fine branches vibrating/shimmering; in moderate wind it
  streams horizontally. Long wide blades stream and flutter (more movement than bluestem's
  tight tuft). Medium rustle with a soft "fizzing" from the panicle.
- **Seasonal timeline:** late emergence (late Apr–May — one of the last to green up) →
  robust blue-green growth (Jun) → panicles emerge, purple-pink haze (Jul–Aug) → seeds
  mature, panicle golden, fall color begins (Sep) → **golden-yellow peak, panicle in autumn
  light (Oct)** → straw standing structure, panicle thins (Nov–Feb, late to break dormancy).

## 6. The one unmistakable thing
The **fountain habit + large airy diffuse panicle (a cloud)** streaming like a banner above
the foliage — and warm **golden** (not copper) fall color.

## 7. Per-instance variation envelope
- **Varies across seeds:** clump size (20–80 stems), height (1.2–2.0 m), panicle fullness/
  stage, fall gold intensity, fountain arc.
- **Variant count:** 3–4 (large meadow clumps — variants prevent tiling); set `v=3..4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_switchgrass()` (`make_undergrowth.py:2325`) — **tall fountain clump**
  (stiff base → arching wide-bladed top), and the **large diffuse airy panicle** (hair-like
  branching, misty) extending well beyond the foliage. Author 3–4 variants spanning size.
  **Keep it a real switchgrass** — do not reuse as a generic meadow-grass stand-in.
- **Textures:** wide blade with pale midrib; misty diffuse panicle card (the cloud); golden
  fall via `fall`.
- **`SPECIES` row (idx 31):** **reconcile to brief** — `fc=[0,0,0]` correct, `bl=[1.0,2.0]`,
  `flex=0.35` correct; set `fall` golden; **add `v=3..4`.**
- **Placement:** re-wire into `ZONE_SPECIES[8]` **Wild Meadow (currently EMPTY [])** and
  `[2]` **North Meadow** — meadow; discrete large clumps with forb gaps (coarser matrix
  than little bluestem).
- **Perf:** chunk-MultiMesh + panicle overdraw; the **meadow matrix is the perf event**
  (with little bluestem) — calibrate clump density, then perf-gate Wild Meadow / North
  Meadow (60 open).

## 9. Definition of Done
- [ ] Thumbnail reads as switchgrass (fountain clump + airy diffuse panicle cloud).
- [ ] **Meadow capture** shows tall fountain clumps with a hazy panicle layer above.
- [ ] Fall capture: warm GOLDEN (distinct from little bluestem copper alongside it).
- [ ] Wind capture: fountain sway — stiff base, panicle streaming like a banner.
- [ ] Dense meadow matrix shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after Wild Meadow / North Meadow re-wire.
- [ ] User walk-around sign-off.
