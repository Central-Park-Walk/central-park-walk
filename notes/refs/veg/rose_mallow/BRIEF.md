# BRIEF — Rose Mallow / Swamp Hibiscus (Hibiscus moscheutos)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_RoseMallow` — generator `make_rose_mallow()` in
  `scripts/make_undergrowth.py:1587`; runtime `undergrowth_builder.gd` `SPECIES` **index 21**.
- **Layer:** herb (shrub-like wetland-margin perennial, 1.3–1.6 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at marsh/pond margins (Harlem Meer edges, the Pool, Turtle Pond, managed wet
gardens) per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Source:
[`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §11.

- [ ] **Habit, summer mass** — iNat CP; herbs doc §11
- [ ] **In a pond-edge stand** (shrub-like clumps dotted with giant saucers)
- [ ] **Bloom detail** (ENORMOUS 15–20 cm saucer; 5 crinkled petals; staminal column)
- [ ] **Leaf detail** (large, sometimes 3-lobed; WHITE-WOOLLY underside)
- [ ] **Stem detail** (stellate-hairy, gray-green, semi-woody)

## 1. Habit — how it flows over itself
- **One-liner:** upright, shrub-like, bushy perennial with a broad rounded open canopy,
  dotted with **enormous saucer flowers disproportionately large for the plant** — a
  medium-green wetland shrub carrying dinner-plate blooms.
- **Overall form / crown shape:** rounded, broad, shrub-like; as wide as tall.
- **Aspect (width : height):** ~0.7–1.0 : 1.
- **First branch / fork height:** branches from the lower third upward.
- **Branch character:** stems not stiff — the heavy flowers and big leaves make stems lean/sway.
- **Asymmetry:** moderate — bushy and open, not a tidy specimen.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** clump-forming (5–10 stems/clump) at the water's edge — clumps
  read as bushy shrub-like masses spaced along the margin, each studded with giant saucers.
- **Target stand reading:** a pond/marsh edge reads as **shrub-like green mounds dotted
  with oversized pink saucers** — the disproportionate flower size is the read, masses
  spaced along the wet margin rather than a continuous wall.

## 3. Density
- **Bucket:** dappled (large leaves, open canopy); the bloom dots dominate the read.
- **Real number:** 1.0–2.0 m tall, 0.8–1.2 m spread, 5–10 stems/clump
  ([[reference-cp-botany-full]]; herbs doc §11). No published LAI — bucket from habit.
- **Light transmission:** medium; broad-leaved but open.

## 4. Detail
- **Bark / stem:** round, 8–15 mm, **stellate-hairy** giving a gray-green velvety texture,
  semi-woody by late season, sometimes red-flushed at base.
- **Leaf / cluster:** alternate, large (10–22 cm), broadly ovate to shallowly 3-lobed,
  coarsely serrate-dentate; **densely WHITE-WOOLLY underside** (bicolor — model a distinct
  underside color, flashes in wind).
- **Summer color:** medium-to-dark green. · **Fall:** yellowing. · **Bloom:** **ENORMOUS
  15–20 cm (to 25 cm) saucer**, 5 broad crinkled crepe-paper petals, pink
  (`fc=[0.88,0.55,0.65]` pink — correct), often with a dark crimson eye; prominent 3–5 cm
  cream **staminal column** studded with yellow anthers (model it — Malvaceae signature).
  Each flower lasts one day; many over weeks. `bl=[1.0,1.8]`.

## 5. Behavior
- **Wind character:** moderately flexible (`flex=0.35`) — large leaves catch wind like
  sails, flower-laden stems lean and sway, thin crepe petals quiver. Moves more than its
  stems suggest, driven by leaf area.
- **Seasonal timeline:** late-breaking shoots (May, one of the last) → bushy big-leaved
  summer → spectacular giant-saucer bloom (Jul–Sep, peak Aug, one day each) → 5-valved
  capsules → dead stems with capsule clusters into winter → dormant.

## 6. The one unmistakable thing
The **enormous 15–20 cm saucer flower, disproportionately large for the plant** — five
crinkled petals with a dark crimson eye and a protruding cream staminal column, on a
shrub-like plant with white-woolly leaf undersides at the water's edge.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (1.0–2.0 m), stem count, flower count/position, petal
  color (white → deep pink, with/without crimson eye), leaf lobing (unlobed vs 3-lobed).
- **Variant count:** 3–4 (the giant flowers tile badly — vary placement and color).

## 8. What this brief drives (build mapping)
- **Generator:** `make_rose_mallow()` (`scripts/make_undergrowth.py:1587`) — model the
  shrub-like bushy form, large sometimes-3-lobed leaves with a **distinct white-woolly
  underside**, and the **oversized saucer flower with a staminal column**. Replace any
  generic helper.
- **Textures:** large broad/3-lobed leaf, white-woolly underside, giant 5-petal saucer +
  staminal column.
- **`SPECIES` row (idx 21):** reconcile to brief — `fc=[0.88,0.55,0.65]` pink,
  `bl=[1.0,1.8]`, `flex=0.35`.
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED; zone 7 currently
  empty) at marsh/pond edges — `[7]` Waterside. Place at the water margin, as spaced
  shrub-like clumps.
- **Perf note:** chunk-MultiMesh; the giant flower cards add overdraw — gain density from
  form/texture/placement, not card count. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as rose mallow (giant pink saucer, staminal column, woolly underside).
- [ ] **Pond-edge stand capture** shows shrub-like mounds dotted with oversized saucers.
- [ ] Bloom fires at `bl=[1.0,1.8]` at correct giant scale.
- [ ] White-underside flash reads in wind.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
