# BRIEF — Pokeweed (Phytolacca americana)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_Pokeweed` — generator `make_pokeweed()` in
  `scripts/make_undergrowth.py:1182`; runtime `undergrowth_builder.gd` `SPECIES` **index 11**.
- **Layer:** herb (large coarse semi-shrubby perennial, 1.5–3 m — a bold individual, not a mat)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at disturbed woodland edges/margins (Ramble, North Woods, near the Loch)
per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **Walk video helpful**
for the late-summer magenta-stem read — the color intensifies through the season and a
spring still misses the signature.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (collapsed/standing dead magenta-black stems)
- [ ] **As scattered bold individuals** at a woodland edge (NOT a colony — the interaction)
- [ ] **Stem detail** (the vivid magenta/crimson stem — the signature)
- [ ] **Leaf detail** (large smooth-margined ovate, semi-glossy, pink-tinged veins)
- [ ] **Fruit raceme** (dark berries on magenta rachis, mixed ripeness — iconic) + bloom (white)

## 1. Habit — how it flows over itself
- **One-liner:** a single trunk-like base that branches dichotomously into a broad,
  top-heavy, candelabra/vase mass — a lush, coarse, almost tropical bush dominating its
  patch, with drooping berry racemes hung off vivid magenta stems.
- **Overall form / crown shape:** broad vase / candelabra; top-heavy; lush and weedy.
- **Aspect (width : height):** ~0.6 : 1 (taller than wide; spread 0.9–1.5 m at 1.5–3 m tall).
- **First branch / fork height:** mid — single-stemmed when young; mature plants branch
  heavily from a central trunk-like base, branches diverging at 30–45°.
- **Branch character:** stout succulent stems (2–5 cm base), branching alternate; heavy,
  the top-heavy canopy leans and sways as a slow unit.
- **Asymmetry:** irregularly spreading / dichotomous — each plant a distinct sprawling individual.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **scattered bold individuals** — pokeweed is a dominant single
  plant at a disturbed edge, not a colony or thicket; it stands out, lush and out of place
  in a temperate woodland, with gaps between specimens.
- **Target stand reading:** *a few large, top-heavy, magenta-stemmed bushes punctuating a
  woodland edge or gap — bold accents with air around them, each reading as one heavy
  individual, never a uniform mass.* (Validate as a scatter of distinct individuals, not a
  thicket.)

## 3. Density
- **Bucket:** open per plant (large leaves, broad spacing) but visually heavy/dominant.
- **Real number:** 1.5–3 m, spread 0.9–1.5 m; disturbed woodland edges/gaps
  ([[reference-cp-botany-full]]). Scattered, low placement density.
- **Light transmission:** moderate — large leaves but open candelabra branching.

## 4. Detail
- **Bark / stem:** **the signature — vivid magenta-pink to deep reddish-purple stems** by
  mid-summer (green when young, color intensifies base-upward with age). `sc=[0.55,0.15,0.25]`
  MAGENTA is correct and is this plant's whole identity — keep it bold.
- **Leaf / cluster:** large (10–30 cm), ovate to elliptic-lanceolate, **smooth entire
  margin** (no serration — an ID feature at this size), semi-glossy waxy upper surface,
  midrib/veins often pink-tinged. Carried alternately, not clustered.
- **Summer color:** medium-dark green · **Fall:** yellow then pinkish-purple
  (`fall=[0.65,0.20,0.30]` — correct, pink-purple) · **Bloom:** small white/greenish-white
  racemes (`fc=[0.90,0.85,0.88]` white — correct), borne *opposite a leaf* at the node;
  ripen to drooping dark purple-black berries on a magenta rachis (the iconic image).

## 5. Behavior
- **Wind character:** moderately flexible (`flex=0.40`) — the thick succulent stems sway as
  a heavy whole unit; large leaves flutter and twist; berry racemes droop and swing
  pendulously. Feels heavy and sluggish, not springy.
- **Seasonal timeline:** reddish-green asparagus spears (Apr) → rapid green growth (May) →
  full height, stems pinking (Jun) → white bloom + magenta stems (Jul) → dark berries on
  magenta rachis (Aug–Sep) → pink-purple leaves, collapsing (Oct) → dead magenta-black
  stems standing into winter.

## 6. The one unmistakable thing
**The vivid magenta stems** carrying drooping racemes of glossy purple-black berries on a
magenta rachis — a coarse, top-heavy, almost tropical bush. If the stems read green/brown,
the identity is lost.

## 7. Per-instance variation envelope
- **Varies across seeds:** single-stem young (1.5 m) vs heavily-branched mature (3 m),
  branch count/spread, stem color saturation (greener young → full magenta), berry-raceme
  load, lean. Low-density scatter — modest variant count is fine.
- **Variant count:** 2–3 (scattered accent; per redesign §4 low-density species don't need
  the full 3–5).

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_pokeweed()` (`scripts/make_undergrowth.py:1182`) — build the
  candelabra/vase trunk-and-fork habit; **make the magenta stem read** (its signature);
  add drooping berry racemes on a magenta rachis and white bloom racemes borne opposite
  leaves; large smooth-margined ovate leaf cards.
- **Textures:** large entire-margined ovate leaf with pink-tinged veins; dark-berry raceme
  cluster on magenta rachis; small white flower raceme.
- **`SPECIES` row (idx 11):** reconcile to this brief — `sc=[0.55,0.15,0.25]` magenta
  (correct, keep bold), `fc=[0.90,0.85,0.88]` white (correct), `bl=[0.8,1.5]`,
  `fall=[0.65,0.20,0.30]` pink-purple (correct), `flex=0.40` (correct — heavy sway).
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[5]` (North Woods),
  `[6]` (Ramble edges), `[2]` (North Meadow edge) at **low scatter density** (disturbed
  edges/gaps, not interiors); these zones gain a bold edge accent.
- **Perf:** undergrowth is chunk-MultiMesh + overdraw — gain the lush look from form and
  leaf-card texture, not raw cards; low placement density keeps cost minimal. Perf-gate
  after placement re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as pokeweed (magenta stems, candelabra, dark berry racemes).
- [ ] **Edge scatter capture** (North Woods / Ramble margin) shows distinct bold
  individuals with air between them — NOT a thicket. *The scatter is the validation unit.*
- [ ] Magenta stems read clearly by mid/late season; berries + magenta rachis present.
- [ ] Dead magenta-black stems persist in the winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
