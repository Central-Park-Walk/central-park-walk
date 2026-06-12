# BRIEF — Pennsylvania Sedge (Carex pensylvanica)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Grass_PASedge` — generator `make_pa_sedge()` in
  `scripts/make_undergrowth.py:2393`; runtime `undergrowth_builder.gd` `SPECIES` **index 33**.
- **Layer:** grass / sedge (very low carpet-forming woodland groundcover, 10–25 cm)
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP on deciduous woodland floor (Ramble, North Woods, under oaks) per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Source research:
[`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§9. The "woodland lawn" carpet read is the identity — and see the §8 open question (this
may belong in the turf/grass system, not as discrete undergrowth instances).

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §9
- [ ] **The carpet** (continuous low woodland-floor mat — the unmistakable read)
- [ ] **Fine hair-like leaves** (1–3 mm, finest in the set)
- [ ] **Semi-evergreen winter** (some green persists at the base under snow/litter)
- [ ] **Wind video** (carpet ripple — traveling waves over the surface)

## 1. Habit — how it flows over itself
- **One-liner:** a **very low (10–25 cm), fine hair-like CARPET** — a continuous soft green
  woodland floor (the woodland lawn), not discrete clumps.
- **Overall form / crown shape:** low continuous mat; individual tufts barely distinguishable.
- **Aspect (width : height):** essentially a ground layer — spreads horizontally via
  rhizomes (10–20 cm/yr), height 10–25 cm.
- **First branch / fork height:** n/a — countless tiny tillers, each a fan of 3–5 leaves.
- **Branch character:** wiry fine flowering culms (0.5–1.5 mm) barely above the leaves;
  soft pliable overall.
- **Asymmetry:** none meaningful — a uniform low texture.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **continuous CARPET** — colonial via rhizomes, tillers every
  3–8 cm, merging into a seamless mat over 1–100+ m²; NOT tussock-forming, NOT discrete
  clumps.
- **Target stand reading:** *a woodland floor under oaks reads as a soft, uniform, low green
  carpet — a fine woodland lawn knitting the ground between tree trunks — not a field of
  individual plants.* The seamlessness is the read; this is a floor texture, not a set of
  instances (see §8).

## 3. Density
- **Bucket:** dense and continuous (a carpet), but very low and fine.
- **Real number:** 50–100+ tillers per 0.1 m² (very high); carpets 1–100+ m²
  ([[reference-cp-botany-full]] / wetland doc §9).
- **Light transmission:** n/a as a floor layer — reads as solid low green texture.

## 4. Detail
- **Bark / stem:** wiry fine culm 0.5–1.5 mm, triangular (a Carex, but too fine to feel);
  **dark reddish-brown basal sheaths** at ground level.
- **Leaf / cluster:** **extremely narrow 1–3 mm (hair-like — the finest in the set)**,
  10–20 cm, soft matte; medium neutral green; the carpet texture is like fine hair / low-pile.
- **Summer color:** medium green (may go slightly brown in hot dry spells — summer
  semi-dormancy) · **Fall:** tan/straw above (late Oct–Nov) **but SEMI-EVERGREEN** — some
  green persists at the base through winter, especially under snow/litter. · **Bloom:**
  `fc=[0,0,0]`; tiny inconspicuous spike (1–3 cm), **very early (Apr–May)**, easily
  overlooked, not persistent.

## 5. Behavior
- **Wind character:** **carpet RIPPLE, stiffness 3/10** (`flex=0.20` — consistent and the
  LOWEST flex of the set: soft and flexible but very short, so minimal movement amplitude).
  Not individual-plant motion — the whole **ground surface ripples** as wind passes, like
  fur being stroked or wind on a lawn: subtle, low-amplitude, high-frequency (~2 Hz)
  **traveling waves**. Nearly silent (quietest in the set).
- **Seasonal timeline:** early green growth (Mar) → flowering, carpet thickens (Apr–May) →
  full green carpet, possible summer semi-dormancy (Jun–Aug) → green persists (Sep–Oct) →
  tan above, **green at base, semi-evergreen under snow/litter (Nov–Feb).**

## 6. The one unmistakable thing
The **continuous, very-low, fine hair-like carpet** — a soft "woodland lawn" under the
trees, semi-evergreen, that **ripples** in wind rather than swaying as plants.

## 7. Per-instance variation envelope
- **Varies across seeds:** minor — patch density, slight height (10–25 cm), green vs
  summer-dormant tone. (A carpet wants subtle, not dramatic, variation.)
- **Variant count:** 2 (carpet — low variation; or treat as a continuous layer per §8);
  set `v=2`.

## 8. What this brief drives (build mapping)
- **OPEN QUESTION FOR THE EXECUTOR (flag, do not silently model as discrete meshes):** the
  research doc (§9) recommends handling PA sedge as a **continuous grass-shader / particle
  CARPET**, not individual mesh instances — "at 3D model scale it might be best handled as a
  grass-like shader/particle system rather than individual meshes." It may therefore belong
  in the **turf/grass system ([`docs/grass.md`](../../../docs/grass.md))** rather than as a
  discrete `undergrowth_builder.gd` instance. **Resolve this with the user / grass.md owner
  before building** — note that `make_ground_cover.py` turf tiles are explicitly out of scope
  for this program (undergrowth_model_redesign.md §1, table). If kept as undergrowth, model
  as a low fine-blade carpet tile; if moved, hand off to grass.md.
- **Generator (if kept as undergrowth):** `make_pa_sedge()` (`make_undergrowth.py:2393`) —
  very low fine hair-like blade carpet (1–3 mm blades, 10–25 cm), semi-evergreen tone.
- **Textures:** fine hair-like blade; reddish-brown basal sheath.
- **`SPECIES` row (idx 33):** **reconcile to brief** — `fc=[0,0,0]` correct, `bl=[1.0,2.0]`,
  `flex=0.20` correct (lowest — carpet ripple); set `v=2`; consider `green=1` (semi-evergreen).
- **Placement (if kept as undergrowth):** re-wire into `ZONE_SPECIES[5]` **North Woods** and
  `[6]` **Ramble** woodland floor — high-shade groundcover (gated by canopy buffer); place as
  a **continuous low carpet**, not scattered clumps.
- **Perf:** chunk-MultiMesh; a continuous low carpet at high tiller density is an overdraw/
  instance-count risk on the tight woodland (45 fps) budget — **this is the strongest case
  for the grass-shader/particle route (§8 open question)**; if kept as instances, calibrate
  carefully and perf-gate Ramble/North Woods (45 woodland).

## 9. Definition of Done
- [ ] **§8 open question resolved** (undergrowth carpet vs grass.md particle system) before geometry.
- [ ] Thumbnail/floor reads as a fine low woodland-lawn carpet.
- [ ] **Woodland-floor capture** (Ramble/North Woods) reads as a continuous green carpet, not clumps.
- [ ] Winter capture: semi-evergreen (green at base under snow/litter), tan above.
- [ ] Wind capture: carpet ripple / traveling waves, not individual sway.
- [ ] Perf gate ×5 equal-or-better after woodland re-wire (or after grass.md integration).
- [ ] User walk-around sign-off.
