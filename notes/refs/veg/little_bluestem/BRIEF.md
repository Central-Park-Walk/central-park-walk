# BRIEF — Little Bluestem (Schizachyrium scoparium)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).
> **MEADOW-GRASS GROUP HERO** — the species that proves the dense-tuft + shimmer +
> meadow-matrix pattern. Validate on a meadow matrix, never a single clump.

- **Archetype key:** `Grass_LittleBluestem` — generator `make_little_bluestem()` in
  `scripts/make_undergrowth.py:2279`; runtime `undergrowth_builder.gd` `SPECIES` **index 30**.
- **Layer:** grass (dense warm-season meadow bunchgrass, 0.6–1.0 m)
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP in managed native meadows / dry sunny slopes per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§6 (the doc's own "signature meadow grass"). **Walk video helpful** for the fall shimmer —
the silver-over-copper glow in afternoon wind is the identity and stills under-sell it.

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §6
- [ ] **Meadow matrix** (a field of tufts — the hero stand read)
- [ ] **Fall color** (copper/mahogany/wine — diagnostic) + **silver seed-head halo**
- [ ] **Wind video** (THE shimmer — silky awns sparkle in any breeze)
- [ ] **Tuft detail** (dense vertical tuft, blue-green, purple-tinged base)

## 1. Habit — how it flows over itself
- **One-liner:** a **dense, tight, upright blue-green TUFT** that flares slightly at the
  blade tips, exploding in fall to **copper/wine** foliage with a **silver fluffy seed-head
  halo** that shimmers in any breeze.
- **Overall form / crown shape:** dense vertical column / slight vase — wider at the top
  (arching tips) than the base.
- **Aspect (width : height):** tight (base 15–30 cm, widening to 25–40 cm at tips).
- **First branch / fork height:** stems branch at upper nodes, each branch a single raceme;
  only bends in the upper quarter.
- **Branch character:** 15–50+ slender stems per clump, erect, self-supporting; fine 3–6 mm
  blades.
- **Asymmetry:** older clumps (5+ yr) can develop a dead center (doughnut) — a natural
  aging variation.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **meadow MATRIX** — 4–8 distinct clumps/m², the structural
  matrix grass into which meadow forbs are woven; clumps stay discrete (bunchgrass, not a
  lawn).
- **Target stand reading:** *a dry sunny meadow reads as a matrix of dense upright blue-green
  tufts with forbs threaded between — and in October a sea of copper/wine clumps under a
  shimmering silver seed-head haze, glowing when backlit.* **This is the hero validation:**
  the meadow matrix of tufts (not one clump) is the unit, and the fall shimmer is the
  diagnostic capture.

## 3. Density
- **Bucket:** dense per tuft; the meadow reads as a matrix of tufts with forb gaps.
- **Real number:** 4–8 clumps/m² in natural meadow; 15–50+ stems/clump
  ([[reference-cp-botany-full]] / wetland doc §6).
- **Light transmission:** low through a tuft; the meadow is airy between tufts.

## 4. Detail
- **Bark / stem:** green with a **strong blue-purple tint at base and nodes** (the
  "bluestem"); slender 1.5–3 mm; flattened, keeled, purplish lower sheaths.
- **Leaf / cluster:** narrow **3–6 mm** (fine-textured), 15–30 cm, flat to folded, often
  curling at the tip; **blue-green / gray-green** with a glaucous bloom.
- **Summer color:** **blue-green / gray-green** (cool-toned — the blue is visible) ·
  **Fall:** **THE GLORY — brilliant copper, mahogany, wine-red, burnt orange (Oct)**,
  varying clump to clump; one of the best native-grass fall colors. Winter: warm straw/tawny
  with reddish tones, persists well. · **Bloom:** `fc=[0,0,0]`; the feature is the **silvery-
  white fluffy seed head** — silky awn hairs expand to a **sparkling silver halo** above the
  copper foliage (Aug–Sep, persists Oct–Feb).

## 5. Behavior
- **Wind character:** **coherent tuft sway + seed-head SHIMMER, stiffness 6/10 tuft /
  4/10 stems** (`flex=0.35` — consistent; the dense tuft leans as a unit). The narrow dense
  blades move together (whole tuft leans, ~0.7 Hz); blade tips flutter to **shimmer** as
  blue-green surfaces catch light at varied angles. **THE SHIMMER is the signature:** the
  silky seed-head hairs catch the slightest breeze in a constant **sparkling** effect, the
  racemes vibrating independently (high-freq, low-amplitude). This species "glows" in
  afternoon sun with wind — **model the shimmer.** Soft high whisper.
- **Seasonal timeline:** slow emergence over straw top (late Apr–May) → blue-green growth
  (Jun) → flowering stems, silver hairs expand (Jul–Aug) → fall color begins, silver halo
  (Sep) → **PEAK: copper/wine + silver, transcendent backlit (Oct)** → warm straw + persistent
  seed heads (Nov–Feb).

## 6. The one unmistakable thing
The **dense blue-green tuft → spectacular copper/wine fall color under a shimmering silver
seed-head halo** — the glow in afternoon wind.

## 7. Per-instance variation envelope
- **Varies across seeds:** clump size (15–50+ stems), height (0.6–1.0 m), fall hue (copper →
  deep burgundy — vary clump to clump), dead-center aging (doughnut), seed-head density.
- **Variant count:** 3–4 (dense meadow matrix — variants prevent tiling and vary fall hue);
  set `v=3..4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_little_bluestem()` (`make_undergrowth.py:2279`) — **dense upright tuft**
  (15–50 stems from a tight crown, fine blue-green blades flaring at the tips), purple-tinged
  base, and the **silver fluffy seed-head halo** above (fall/winter). Author 3–4 variants
  spanning size and **fall hue**.
- **Textures:** fine blue-green blade (purplish base); silver silky seed-head card (the
  shimmer source); copper/wine fall via `fall`.
- **`SPECIES` row (idx 30):** **reconcile to brief** — `fc=[0,0,0]` correct, `bl=[1.0,2.0]`,
  `flex=0.35` correct; set `fall` to copper/wine; **add `v=3..4`.**
- **Placement:** re-wire into `ZONE_SPECIES[8]` **Wild Meadow (currently EMPTY [])** and
  `[2]` **North Meadow** — dry sunny meadow; place as a **matrix of clumps** (4–8/m²,
  discrete with forb gaps), the structural grass other meadow forbs weave through.
- **Perf:** chunk-MultiMesh + tuft overdraw; the **meadow matrix is the perf event** (with
  switchgrass, the meadow-grass cost) — calibrate to the real 4–8 clumps/m², then perf-gate
  Wild Meadow / North Meadow (60 open).

## 9. Definition of Done
- [ ] Thumbnail reads as little bluestem (dense blue-green tuft → copper fall + silver halo).
- [ ] **Meadow-matrix capture** (hero) shows a field of discrete tufts with forb gaps.
- [ ] Fall capture: copper/wine foliage under a shimmering silver seed-head haze, backlit.
- [ ] Wind capture: tuft leans as a unit; seed heads SHIMMER/sparkle.
- [ ] Dense meadow matrix shows no tiling, with fall-hue variation (§7).
- [ ] Perf gate ×5 equal-or-better after Wild Meadow / North Meadow re-wire.
- [ ] User walk-around sign-off.
