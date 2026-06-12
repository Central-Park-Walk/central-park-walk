# BRIEF — English Ivy (Hedera helix)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_EnglishIvy` — generator `build_english_ivy()` in
  `scripts/make_vine.py:327` (seed 4100); runtime `vine_builder.gd` (**DISABLED, ln 111**).
- **Layer:** vine (evergreen; climbs bark + carpets ground; invasive, managed)
- **Tier coverage:** n/a (tree-attached; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Common climbing tree trunks and carpeting ground in CP wooded/edge areas per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Invasive and managed.

- [ ] **Habit on a host** — clings flat to bark by rootlets; carpets ground
- [ ] **Leaf detail** (dark glossy, 3–5 lobed juvenile leaves; evergreen)
- [ ] **EVERGREEN winter state** (stays green — a winter presence on bare trunks)
- [ ] **Mature flowering/fruit form** (rounded unlobed leaves, fall umbels, black berries)

## 1. Habit — how it flows over itself
- **One-liner:** an **evergreen** dark glossy mat that clings flat to bark by adventitious
  rootlets, climbing a trunk as a solid green skin and carpeting the ground around it.
- **Climbing mechanism:** **adventitious rootlets** clinging flat (`make_climbing_pad`) —
  a dense conforming sheet, denser/more opaque than Virginia creeper; plus a ground carpet.
- **Asymmetry:** conforms to host; dense even sheet.

## 2. Interaction — how it meets its neighbors
- **On a host:** dense green skin up the trunk + a continuous ground carpet at the base;
  it reads as smothering the host (its invasive character).
- **Target stand reading:** a trunk encased in glossy dark-green ivy with a matching
  ground carpet — solid, evergreen, even in winter.

## 3. Density
- **Bucket:** dense/opaque (glossy leaves overlap into a solid skin).
- **Light transmission:** low.

## 4. Detail
- **Stem:** woody runner pressed to bark with fuzzy rootlets.
- **Leaf:** **dark glossy, 3–5 lobed** (juvenile climbing form); leathery; mature form has
  rounded unlobed leaves.
- **Summer color:** dark glossy green (often pale-veined).
- **Bloom:** greenish-yellow **umbels in autumn** (only on mature, high growth), then
  **black berries** in winter/spring.

## 5. Behavior
- **Wind:** very low (clinging mat); minimal movement.
- **Seasonal timeline:** **evergreen — stays glossy dark green year-round** (`green=1`),
  including a conspicuous green presence on bare winter trunks; autumn umbel flowers on
  mature growth → black berries (winter–spring). No leaf-drop.

## 6. The one unmistakable thing
An **evergreen** glossy dark-green lobed-leaf skin clinging flat up a trunk (and
carpeting the ground) — green when everything around it is bare.

## 7. Per-instance variation envelope
- **Varies across seeds:** climb height, sheet density, ground-carpet extent, host size.
- **Variant count:** 3 — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `build_english_ivy()` — bark-conforming **dense evergreen sheet**
  (`make_climbing_pad`) + ground carpet runner; glossy lobed leaf cards.
- **Textures:** dark glossy 3–5-lobed leaf (pale-veined).
- **`SPECIES`/runtime:** mark **evergreen (`green=1`)** so winter keeps it green.
- **Re-enable:** delete `vine_builder.gd:111` return after the GLB passes brief + perf gate.
- **Placement:** wooded trunks + edges (zones 5/6) — invasive, so place as
  smothering patches on some hosts, not uniformly.
- **Perf:** densest vine sheet = most overdraw; perf-gate woodland after re-enable.

## 9. Definition of Done
- [ ] Reads as ivy (dense glossy lobed sheet clinging flat) + ground carpet.
- [ ] **Winter capture stays green** (the evergreen identity).
- [ ] On-host capture — smothering trunk skin (interaction).
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
