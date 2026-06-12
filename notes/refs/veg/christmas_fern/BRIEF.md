# BRIEF — Christmas Fern (Polystichum acrostichoides)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Fern_Christmas` — generator `make_christmas_fern()` in
  `scripts/make_undergrowth.py:1889`; runtime `undergrowth_builder.gd` `SPECIES` **index 8**.
- **Layer:** floor / herb (low **evergreen** woodland-floor fern, 0.3–0.6 m)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
The most common fern of CP's dry-to-mesic woodland slopes (Ramble, North Woods) per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. **The winter reference is
the point** — it's the green fern still on the woodland floor under snow; the cached
**winter North Woods walk** ([[project-tree-model-redesign-plan]], `jak1DISt1uU`) should
show evergreen fronds against snow.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **WINTER green/flattened state** (MOST important — the evergreen identity)
- [ ] **On a slope** (scattered crowns, the typical stand)
- [ ] **Frond + pinna detail** (once-pinnate; the "Christmas-stocking" pinna with a basal lobe)

## 1. Habit — how it flows over itself
- **One-liner:** a low, arching **rosette/fountain** of stiff, leathery, glossy dark
  green fronds radiating from a central crown — and it **stays green all winter**, the
  older fronds reclining flat on the ground.
- **Overall form:** low arching rosette/fountain; **0.3–0.6 m** (the shortest fern here).
- **Aspect (w:h):** ~1.3–1.8 (much wider than tall — fronds splay out and down).
- **Frond arrangement:** radial rosette from one crown; fronds arch outward, outer/older
  ones lie down (especially in winter).
- **Asymmetry:** the reclining-frond winter habit is asymmetric and floor-hugging.

## 2. Interaction — how it meets its neighbors
- **In a stand:** discrete crowns scattered over woodland slopes (NOT a dense running
  colony like ostrich) — a dotting of dark-green rosettes, with the key role of being
  the **green winter floor cover** when everything else is bare.
- **Target stand reading:** dark glossy rosettes scattered on a leaf-littered slope,
  conspicuously **still green in winter** while the deciduous ferns are gone.

## 3. Density
- **Bucket:** medium; **leathery, glossy** (low translucency — `trans=0.40`, `spec=0.20`,
  `rough=0.52` are correct: this is the one fern with a glossy, non-papery frond).
- **Real number:** moderate frond count per crown.
- **Light transmission:** low (thick leathery fronds).

## 4. Detail
- **Rachis:** green, scaly.
- **Frond:** **once-pinnate**, leathery, glossy; each pinna shaped like a tiny
  **Christmas stocking / mitten** — an asymmetric basal lobe ("toe") near the rachis is
  the diagnostic pinna shape.
- **Summer color:** dark glossy green · **Winter:** **stays green** (`green=1` — keep!),
  fronds reclining. `fall=[0.05,0.18,0.04]` (stays dark green, not yellow).
- **Bloom:** none (`fc=0`); fertile frond tips are narrowed/contracted (upper pinnae).

## 5. Behavior
- **Wind:** stiff (`flex=0.25`) — leathery fronds barely flex; gentle rosette sway.
- **Seasonal:** spring fiddleheads → glossy rosette (summer) → **stays green through fall
  and winter**, older fronds reclining flat. No die-back.

## 6. The one unmistakable thing
**Evergreen** — a dark, glossy, leathery fern rosette still green (and flattened) on the
winter woodland floor; the stocking-shaped once-pinnate pinnae.

## 7. Per-instance variation envelope
- **Varies across seeds:** frond count, rosette spread, reclining amount, size (0.3–0.6 m).
- **Variant count:** 3 — scattered, moderate visibility; set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_christmas_fern()` — model a **low arching once-pinnate leathery
  rosette** with the stocking-shaped pinna and a **winter reclining/evergreen** state
  (the seasonal system must keep it green, `green=1`).
- **Textures:** glossy leathery once-pinnate frond with stocking pinnae (gen_fern_textures,
  glossier than the deciduous ferns).
- **`SPECIES` row (idx 8):** `green=1`, `trans=0.40`, `spec=0.20`, `rough=0.52`, `flex=0.25`
  all correct — **verify the seasonal shader honors `green=1` (stays green in winter)**;
  add `v=3`.
- **Placement:** re-wire into `WOODLAND_SPECIES` + `ZONE_SPECIES[5]`/`[6]` on dry-mesic
  **slopes** at MEDIUM density (the most common woodland-floor fern) — and it should be
  the visible winter floor cover.
- **Perf:** low translucency = cheaper than deciduous ferns; perf-gate woodland after re-wire.

## 9. Definition of Done
- [ ] Thumbnail reads as a glossy leathery once-pinnate rosette (stocking pinnae).
- [ ] **Winter capture stays green** and reclining (the identity) — not dead/brown.
- [ ] Slope stand capture shows scattered dark-green rosettes.
- [ ] Dense same-species group shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
