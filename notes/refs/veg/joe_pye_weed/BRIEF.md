# BRIEF — Joe-Pye Weed (Eutrochium purpureum, syn. Eupatorium purpureum)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_JoePyeWeed` — generator `make_joe_pye_weed()` in
  `scripts/make_undergrowth.py:1312`; runtime `undergrowth_builder.gd` `SPECIES` **index 13**.
- **Layer:** herb (tall stately columnar perennial, 1.2–2.1 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at moist meadow edges and stream banks (Pool, Ravine, Harlem Meer margins,
North Meadow wet edges) per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM.
Native — a welcome presence. **Walk video helpful** for how the pink domes read above a
moist-meadow-edge clump.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (standing dead stems with fuzzy brown seed heads)
- [ ] **In a clump at a moist edge** (3–8 stems, the interaction)
- [ ] **Stem detail** (purple-tinged nodes; whorled-leaf tiers)
- [ ] **Whorled leaf detail** (3–5 per node — pagoda tiers — the ID feature)
- [ ] **Bloom** (pink-mauve flat domed corymb crowning the plant — the signature)

## 1. Habit — how it flows over itself
- **One-liner:** a tall, strict, columnar stem ringed with whorled leaf tiers (pagoda-like)
  and crowned by a soft pink-mauve dome — stately and architectural, standing erect rather
  than leaning.
- **Overall form / crown shape:** columnar to slightly vase-shaped; flat/domed pink crown.
- **Aspect (width : height):** ~0.4 : 1 (tall and narrow; spread 0.6–1.2 m at 1.2–2.1 m).
- **First branch / fork height:** unbranched stem; the only "fork" is the terminal corymb
  splitting into the flower dome.
- **Branch character:** single/few sturdy solid stems (1–2 cm) from a clump; **whorled
  leaves in tiers of 3–5** create the regular pagoda look; stems do not lodge.
- **Asymmetry:** minimal — strict and upright; clump of 3–8 stems gives mass.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **clump-forming** (3–8 stems from a woody rootstock) at moist
  edges — stately verticals standing in a loose group, pink domes hovering at one height,
  not a dense thicket or a carpet.
- **Target stand reading:** *a loose stand of tall columnar stems at a stream bank or wet
  meadow edge, their pink-mauve domes forming a soft floating layer above whorled foliage —
  read as a group of distinct architectural verticals.* (Validate on a moist-edge clump.)

## 3. Density
- **Bucket:** open/columnar per plant; the dome is the visual mass.
- **Real number:** 1.2–2.1 m, spread 0.6–1.2 m, 3–8 stems/clump; moist meadow edges/stream
  banks ([[reference-cp-botany-full]]). Moderate placement density at wet edges.
- **Light transmission:** high along the bare lower stem; the dome and whorled tiers read as
  the mass.

## 4. Detail
- **Bark / stem:** green stem **conspicuously flushed purple at the nodes** (sometimes
  wholly purple-tinged), finely puberulent; vanilla-scented when broken. `sc` purple-node
  is correct.
- **Leaf / cluster:** **whorls of 3–5 (typically 4)** — the pagoda-tier ID feature —
  lance-ovate (10–25 cm), coarsely serrate, matte dull green, sandpapery above,
  purple-tinged midrib.
- **Summer color:** dull dark green · **Fall:** yellowing/browning · **Bloom:** **the
  signature — a large domed compound corymb (15–30 cm), dusty pink to mauve-purple**, soft
  cotton-candy texture from the protruding fuzzy florets. `fc=[0.72,0.42,0.58]` pink-mauve
  dome is correct. Fades to dingy gray-white fuzzy pappus seed heads.

## 5. Behavior
- **Wind character:** stiff-but-top-sways (`flex=0.35` — correct). Stem stays erect; the
  large flower dome acts like a sail and sways slightly, upper whorled leaves flutter; only
  strong wind leans the whole stem. Stately, not bouncy.
- **Seasonal timeline:** reddish-purple shoots (Apr–May) → rapid columnar growth, whorls
  expanding (Jun) → green-purple bud clusters (Jul) → **pink domes peak, butterflies**
  (Aug) → fading to white-pappus seed heads (Sep) → standing dead stems with fuzzy brown
  heads persist (Oct–Dec).

## 6. The one unmistakable thing
**The pink-mauve domed corymb crowning a tall columnar stem ringed with whorled leaf
tiers** — a soft floating dome over a pagoda of whorled foliage, purple at the nodes.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (1.2–2.1 m), stem count per clump (3–8), dome size, whorl
  count (3–5), node-purple intensity, lean. Moderate density at wet edges → 3 variants
  spans it.
- **Variant count:** 3 (`v=3`) — moist-edge groups want some variety without tiling.

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_joe_pye_weed()` (`scripts/make_undergrowth.py:1312`) — build
  the strict columnar stem with **whorled leaf tiers (3–5/node)** and a **domed pink-mauve
  terminal corymb**; purple-tinged nodes.
- **Textures:** lance-ovate serrate whorl leaf; soft fuzzy pink-mauve corymb cluster;
  gray-white pappus seed-head variant.
- **`SPECIES` row (idx 13):** reconcile to this brief — `fc=[0.72,0.42,0.58]` pink-mauve
  (correct), `bl=[1.0,1.8]`, `sc` purple-node (correct), `flex=0.35` (correct).
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[7]` (Waterside, stream
  banks — **currently EMPTY, populated by this work**) and `[8]` (Wild Meadow, moist edges
  — **also EMPTY**) at moderate density along moist edges. Add `v=3` for the stands.
- **Perf:** chunk-MultiMesh + overdraw; gain the dome read from a cluster-card corymb, not
  many single florets. Perf-gate after placement re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as Joe-Pye weed (whorled tiers, pink-mauve dome, purple nodes).
- [ ] **Moist-edge clump capture** shows a loose stand of columnar stems with domes at one
  floating height. *The clump is the validation unit.*
- [ ] Whorled leaf tiers and the pink dome read clearly at bloom (`bl=[1.0,1.8]`).
- [ ] Standing dead stems with fuzzy brown seed heads in the winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
