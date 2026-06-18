# BRIEF — Broadleaf Cattail (Typha latifolia)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).
> **WETLAND-GROUP HERO** — the species that proves the dense-colony-wall interaction.
> Validate on a colony, never a single shoot.

- **Archetype key:** `Wetland_Cattail` — generator `make_cattail()` in
  `scripts/make_undergrowth.py:2038`; runtime `undergrowth_builder.gd` `SPECIES` **index 25**.
- **Layer:** wetland (emergent water-margin colonist, 1.5–3 m)
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at pond/lake/stream margins per [[reference-cp-botany-full]]; iNat CP-bbox
count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§1. **Walk video helpful** for the colony-wall read — a single-shoot still misses the
dense vertical-strap stand that is the whole identity.

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §1
- [ ] **In a colony** (the dense vertical-strap WALL at water's edge — essential, hero read)
- [ ] **Brown spike detail** ("hotdog" cylinder, no gap male/female — *T. latifolia* ID)
- [ ] **Winter** (brown spike on bare stalk above shredded tan leaves)
- [ ] **Wind video** (broadside twist showing pale undersides; colony rolling wave)

## 1. Habit — how it flows over itself
- **One-liner:** a **strictly vertical, unbranched strap-leaf shoot** topped by a single
  brown cylindrical "hotdog" spike on a bare stalk — never arching, never bending; the
  identity is the rigid vertical and the dense COLONY wall it forms.
- **Overall form / crown shape:** strict vertical column; flat strap leaves 1.0–1.8 m.
  **Correction (2026-06-17, from `reference_photos/`):** the leaves **overtop the brown
  spike** (or roughly equal it) — the spike sits AMONG the foliage at ~65–80% of leaf
  height, NOT on a bare stalk rising above it. (Prior "spike-stalk rising 30–60 cm above"
  was wrong; real-world photos are ground truth.) The clump is **columnar**, not a
  bottom-heavy tussock/cone — blades hold near-full width most of the way up.
- **Aspect (width : height):** narrow — a single tall vertical with strap leaves splaying
  modestly; the *mass* is the colony, not the shoot.
- **First branch / fork height:** none — unbranched single terminal spike per shoot.
- **Branch character:** strap leaves are 2-ranked (distichous), clasping the stem with
  long sheaths; stiff base, flexible tips.
- **Asymmetry:** minimal per shoot; variation lives in height and spike maturity across
  the colony.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **dense colonial WALL** — not clumping. Shoots arise singly
  from spreading rhizomes every 10–20 cm, 15–30 shoots/m², forming a nearly impenetrable
  monoculture that reads as a solid wall of vertical green.
- **Target stand reading:** *a pond/lake edge reads as a continuous vertical green wall of
  strap leaves with brown spikes scattered through it — not spaced individual plants.*
  **This is the hero validation:** the colony wall (not one shoot) is the unit, and the
  density (place shoots at 10–20 cm intervals in patches, not discrete tussocks) is a
  placement lever as much as a model lever.

## 3. Density
- **Bucket:** opaque as a colony (the stand is a wall); each shoot is a few wide blades.
- **Real number:** 15–30 shoots/m² in dense patches; clones spread 0.5–0.7 m/yr,
  3–5 m diameter ([[reference-cp-botany-full]] / wetland doc §1).
- **Light transmission:** very low through a mature stand — you cannot see through it.

## 4. Detail
- **Bark / stem:** pale green where leaf-sheathed, light tan at the waterline base; spongy
  aerenchyma, 10–20 mm. (`sc` green is correct.)
- **Leaf / cluster:** flat, linear, strap-like, **very wide 10–25 mm** (broadest of any
  grass-like wetland plant — the broadleaf ID); matte green above, glaucous gray-green
  below; D-shaped cross-section; tapers to a point.
- **Summer color:** true medium grass-green · **Fall:** straw-yellow → brown (Oct);
  dead leaves persist upright then shred. · **Bloom:** `fc=[0,0,0]` — the showy feature is
  the **brown cylindrical spike** (10–20 cm, no gap male/female), green June → dark
  chocolate-brown Jul–Aug, persisting and bursting to cotton fluff through winter.

## 5. Behavior
- **Wind character:** **rigid vertical sway, stiffness 7/10** (`flex=0.30` — consistent;
  stiffer than most grasses but leaves flex more than stems). Base stays rigid; upper
  leaf tips wave with a slow ~0.5 Hz sinuous oscillation, leaning 15–25° in moderate wind.
  The wide flat blades catch wind broadside and **twist to show pale undersides** (a color
  shimmer). The stiff spike-stalk holds the brown cylinder nearly motionless. Colony sways
  in unison as a rolling "field of green." Papery clacking sound.
- **Seasonal timeline:** pale shoots (Apr) → full height, green spike (May–Jun) → male
  pollen then brown female spike (Jul–Aug) → leaves yellow (Sep–Oct) → dead tan leaves +
  persistent brown spike bursting to fluff (Nov–Mar).

## 6. The one unmistakable thing
The brown **"hotdog" cylinder spike** (with no gap between male and female sections —
*T. latifolia*) rising on a bare stalk above a **strict-vertical, very-wide strap-leaf
colony wall** at the water's edge.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (1.5–3 m — wide `s` range), spike maturity/presence
  (green vs brown vs bursting), leaf count, blade lean, dead-leaf admixture.
- **Variant count:** 3–4 (dense colony — needs variants so the wall doesn't tile); set `v=3..4`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_cattail()` (`make_undergrowth.py:2038`) — strict-vertical unbranched
  shoot, very wide strap leaves (D-section), single terminal brown cylinder on a bare
  stalk above the foliage. No arch. Author 3–4 variants spanning height/spike-stage.
- **Textures:** wide matte strap leaf (glaucous underside for the twist-shimmer), brown
  cylinder spike texture.
- **`SPECIES` row (idx 25):** **reconcile to brief** — `fc=[0,0,0]` correct (no flower);
  `bl=[1.0,2.0]`, `sc` green, `flex=0.30` correct; **add `v=3..4`.**
- **Placement:** re-wire into `ZONE_SPECIES[7]` **Waterside (currently EMPTY [])** —
  pond/lake/stream edge standing water; place as **dense colony patches** (10–20 cm shoot
  spacing → high density), not uniform scatter.
- **Perf:** chunk-MultiMesh + transparent-card overdraw; the **dense colony is the perf
  event** — calibrate placement density to the real 15–30 shoots/m², then perf-gate
  Waterside (60 open target).

## 9. Definition of Done
- [ ] Thumbnail reads as cattail (vertical strap leaves + brown no-gap spike).
- [ ] **Colony capture** (hero) shows a dense vertical-strap WALL at a water edge — the interaction.
- [ ] Winter capture: brown spike on bare stalk above shredded tan leaves.
- [ ] Wind capture: rigid base, twisting blades showing pale undersides, colony rolls in unison.
- [ ] Dense colony shows no tiling (§7).
- [ ] Perf gate ×5 equal-or-better after Waterside re-wire.
- [ ] User walk-around sign-off.
