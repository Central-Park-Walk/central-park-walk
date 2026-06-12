# BRIEF — Bottlebrush Grass (Elymus hystrix, syn. Hystrix patula)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Grass_Bottlebrush` — generator `make_bottlebrush_grass()` in
  `scripts/make_undergrowth.py:1988`; runtime `undergrowth_builder.gd` `SPECIES` **index 24**.
- **Layer:** grass (sparse cool-season SHADE bunchgrass, 0.6–1.2 m)
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP in woodland understory (Ramble, North Woods) per [[reference-cp-botany-full]];
iNat CP-bbox count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§5. Unusual: a **shade** grass (most are sun-lovers) — model as a low-density woodland-floor
accent, not a meadow mass.

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §5
- [ ] **Seed head** (the bottlebrush/porcupine spike — the unmistakable feature)
- [ ] **Sparse open clump** (2–6 stems, NOT a dense tuft)
- [ ] **Woodland understory context** (scattered, under canopy)
- [ ] **Wind video** (loose bob/wobble; spikes dance independently)

## 1. Habit — how it flows over itself
- **One-liner:** a **sparse, open vase-shaped tuft** of 2–6 slightly-arching stems, each
  topped by a distinctive **bottlebrush/porcupine seed head** (spikelets at 90° with long
  awns) — an airy woodland-floor accent, never a dense clump.
- **Overall form / crown shape:** open vase; few arching stems; bristly spikes nodding at
  the tips.
- **Aspect (width : height):** open and loose; clump 20–35 cm base.
- **First branch / fork height:** unbranched culms; seed-head weight causes slight nodding
  in the upper third.
- **Branch character:** slender stems (2–4 mm) erect but flexing easily in the upper third;
  lax arching leaves.
- **Asymmetry:** each stem arches outward freely from a small base — loose and irregular.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **sparse, scattered** — NOT stand-forming. Scattered individuals
  or very small groups 0.5–2 m apart in woodland; never dense meadow.
- **Target stand reading:** *a woodland-floor accent — individual small open clumps
  scattered through the understory with bare floor and litter between them, the bristly
  spikes catching a shaft of light — never a continuous grass mass.* The low-density
  scatter is the read; placement must keep gaps.

## 3. Density
- **Bucket:** open/lacy — sparse clumps, open habit.
- **Real number:** 2–6 stems/clump (sparse), clumps 0.5–2 m apart
  ([[reference-cp-botany-full]] / wetland doc §5).
- **Light transmission:** high — an open shade-adapted grass.

## 4. Detail
- **Bark / stem:** green / yellowish-green, slender 2–4 mm, round/hollow.
- **Leaf / cluster:** flat, lax, arching, **8–15 mm wide**, thin shade-adapted blades,
  medium green (yellow-green in deep shade); auricles clasping the stem (Elymus feature).
- **Summer color:** medium green · **Fall:** pale gold/straw (Sep), drops quickly — **weak
  winter persistence** (mostly gone by mid-winter). · **Bloom:** `fc=[0,0,0]`; the feature
  is the **bottlebrush SPIKE** — spikelets in pairs spreading at **90° to the axis with
  long 2–4 cm awns** (the porcupine look), 8–15 cm long, green (Jun) → straw (Aug), then
  **shatters** to a bare zigzag rachis (NOT persistent like little bluestem).

## 5. Behavior
- **Wind character:** **independent-element motion, stiffness 3/10** (`flex=0.40` —
  consistent, one of the most flexible/loose-bodied; the highest flex of the grasses here
  fits the slender stems + open clump). Broad thin shade-leaves flutter in even light air.
  The **bottlebrush spikes bob and wobble independently** on slender stems — the spreading
  awns catch air and make the spike rotate and dance irregularly (very different from the
  steady back-and-forth of dense grass heads). Each stem moves freely (open clump, no
  neighbor constraint). Very quiet.
- **Seasonal timeline:** early green growth (Mar–Apr, cool-season) → lush green (May) →
  bottlebrush spikes at peak (Jun–Jul) → spikes shatter, foliage yellows (Aug) → straw,
  senesces (Sep–Oct) → minimal winter presence (Nov–Mar).

## 6. The one unmistakable thing
The **bottlebrush/porcupine seed head** — paired spikelets spreading at right angles with
long awns — on a **sparse open clump** in woodland shade (a grass where you'd least expect one).

## 7. Per-instance variation envelope
- **Varies across seeds:** stem count (2–6), height (0.6–1.2 m), spike stage (green/straw/
  shattered/bare rachis), arch amount.
- **Variant count:** 2–3 (low-density scattered accent — fewer variants acceptable); set `v=2..3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_bottlebrush_grass()` (`make_undergrowth.py:1988`) — sparse open vase
  of 2–6 arching slender culms, lax broad leaves, and the **bottlebrush spike (90° spikelets,
  long awns)** at each tip. Keep it open, NOT a dense tuft.
- **Textures:** lax broad shade-blade; bristly awned spike (spikelet card).
- **`SPECIES` row (idx 24):** **reconcile to brief** — `fc=[0,0,0]` correct, `bl=[1.0,2.0]`,
  `flex=0.40` correct (the loosest grass); set `v=2..3`.
- **Placement:** re-wire into `ZONE_SPECIES[5]` **North Woods** and `[6]` **Ramble**
  woodland understory (shade grass — unusual placement); **low-density scattered** accent
  (0.5–2 m apart, gaps), gated by the canopy buffer to shaded chunks.
- **Perf:** chunk-MultiMesh; **low density** keeps cost down, but these are woodland (45 fps)
  chunks — perf-gate Ramble/North Woods (45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as bottlebrush grass (porcupine awned spike + sparse open clump).
- [ ] **Understory capture** (Ramble/North Woods) shows scattered open clumps with gaps — NOT a meadow.
- [ ] Seed-head capture: spikelets at 90° with long awns; later a bare zigzag rachis.
- [ ] Wind capture: spikes bob/wobble independently on slender stems.
- [ ] Perf gate ×5 equal-or-better after woodland re-wire.
- [ ] User walk-around sign-off.
