# BRIEF — Yellow Flag Iris (Iris pseudacorus)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Wetland_YellowIris` — generator `make_yellow_flag_iris()` in
  `scripts/make_undergrowth.py:2105`; runtime `undergrowth_builder.gd` `SPECIES` **index 26**.
- **Layer:** wetland (clumping water-margin perennial, 0.6–1.2 m). Invasive, managed.
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at managed pond/stream margins per [[reference-cp-botany-full]]; iNat CP-bbox
count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§2. CP presence is **managed** (invasive) — likely contained remnant clumps, not textbook
stands; ask the user for a clip if the CP form is unclear.

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §2
- [ ] **Equitant fan** (the flat sword-leaf fan — the unique habit)
- [ ] **Bloom** (bright butter-yellow iris flowers, late May–Jun)
- [ ] **Seed pod** (oblong capsule, prominent Jul–winter)
- [ ] **Wind video** (the fan sways as a coherent unit)

## 1. Habit — how it flows over itself
- **One-liner:** a **flat equitant FAN of sword-shaped leaves** radiating from the base —
  leaves fold and overlap edge-to-edge in one plane — with bright yellow iris flowers on
  stalks rising just above; the fan is the gesture.
- **Overall form / crown shape:** flat sheaf/fan, widest at mid-height, tapering to points;
  flower stalks 0.8–1.2 m slightly over the leaves.
- **Aspect (width : height):** a flat plane per fan; clumps splay outward in the upper half.
- **First branch / fork height:** none on leaves (rise straight from rhizome); flower stalk
  branches near the top into 2–3 flower branches.
- **Branch character:** **equitant** — leaves fold longitudinally at the base and clasp/
  overlap in a tight flat fan, each "riding" inside the one below; stiff base, flex in the
  upper third.
- **Asymmetry:** fans of a clump radiate at different angles → a rough star in plan view.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **clumping** (keeps discrete clump identity, unlike cattail's
  continuous mat) — 3–8 fans per mature clump; clumps can merge into 2–5 m stands along
  an edge but read as a series of distinct fans.
- **Target stand reading:** *a shallow-water margin reads as discrete flat fans of sword
  leaves, splaying, with yellow flowers standing above — not a continuous wall.* Place as
  clumps with gaps, not a uniform mat (distinguishes it from cattail/phragmites).

## 3. Density
- **Bucket:** dappled — broad blades but a clump is see-through between fans.
- **Real number:** 3–8 fans/clump (6–10 leaves each), clumps 30–60 cm diameter
  ([[reference-cp-botany-full]] / wetland doc §2).
- **Light transmission:** moderate — gaps between fans and clumps.

## 4. Detail
- **Bark / stem:** no true stem — leaves rise from a thick rhizome; flower stalk round,
  solid, green, 8–12 mm.
- **Leaf / cluster:** ensiform (sword) leaves **15–30 mm wide**, 50–100 cm, with a
  **prominent raised midrib on both surfaces**; glossy/waxy, firm, leathery; rich green
  with a slight blue-green cast.
- **Summer color:** medium-dark green, blue-green cast · **Fall:** no display — gradual
  brown, dead fans persist papery through winter. · **Bloom:** **bright butter-yellow**
  iris flowers (`fc=[0.88,0.82,0.10]` correct), 7–10 cm, 3 drooping falls + 3 erect
  standards, brown-purple throat veining; **late May–Jun**. Large oblong seed pods
  (4–8 cm) prominent Jul → winter.

## 5. Behavior
- **Wind character:** **coherent fan-unit sway, stiffness 6/10** (`flex=0.30` consistent —
  stiffer than grasses, less than cattail). The equitant base anchors the leaves; adjacent
  blades constrain each other so the **fan sways as a unit**, not as chaotic blades —
  elegant, slow ~0.3 Hz pendulum bending from the midpoint in a smooth arc. Flower/seed
  stalk is top-heavy, sways with a slow 2–3 s period. Near-silent (smooth waxy leaves).
- **Seasonal timeline:** pale fans emerge (Mar–Apr) → flower stalks rise (May) → yellow
  bloom peak (late May–Jun) → green seed pods swell (Jul–Aug) → pods brown and split,
  leaves yellow (Sep–Oct) → brown dead fans + split pods on dry stalks (Nov–Mar).

## 6. The one unmistakable thing
The **flat equitant fan** of sword leaves (unique among the wetland set) topped by
**bright butter-yellow iris flowers** in late spring.

## 7. Per-instance variation envelope
- **Varies across seeds:** fan count per clump, leaf height (0.6–1.2 m), bloom/seed-pod
  presence and stage, fan splay angle.
- **Variant count:** 3 (clumping, moderate density); set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_yellow_flag_iris()` (`make_undergrowth.py:2105`) — build the
  **equitant flat fan** (overlapping sword leaves in one plane, raised midrib), flower
  stalks with butter-yellow iris flowers above, oblong seed pods. Multiple fans per clump
  radiating at angles.
- **Textures:** glossy sword leaf with raised midrib; bright yellow iris flower (falls +
  standards) cluster card; brown oblong seed pod.
- **`SPECIES` row (idx 26):** **reconcile to brief** — `fc=[0.88,0.82,0.10]` yellow correct,
  `bl=[0.6,1.2]`, `flex=0.30` correct; confirm `v=3`.
- **Placement:** re-wire into `ZONE_SPECIES[7]` **Waterside (currently EMPTY [])** —
  **shallow water margins** (0–25 cm); place as **discrete clumps with gaps** (managed/
  contained), not a continuous mat.
- **Perf:** chunk-MultiMesh + card overdraw; lower density than cattail/phragmites
  (clumping, contained) — perf-gate Waterside (60 open).

## 9. Definition of Done
- [ ] Thumbnail reads as yellow iris (flat sword fan + yellow flower).
- [ ] **Clump capture** at a water margin shows discrete equitant fans with gaps.
- [ ] Bloom capture: bright butter-yellow flowers in the late-May–Jun window.
- [ ] Seed-pod capture: prominent oblong pods Jul–winter.
- [ ] Wind capture: the fan sways as a coherent unit (not chaotic blades).
- [ ] Perf gate ×5 equal-or-better after Waterside re-wire.
- [ ] User walk-around sign-off.
