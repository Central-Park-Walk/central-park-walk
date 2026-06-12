# §5b Forest-Coherence Pre-Diagnosis — findings (gate artifact)

Run 2026-06-11 (Sonnet, pure data analysis per
[`../tree_model_redesign.md`](../tree_model_redesign.md) §5b / §11 step 2). This is the
**gate** whose output sets the crown-width targets the hero models are built to. Headline:
**crown width is not the coherence lever** — the levers are crown *edge* density, species
distinctness, and branch architecture, all model-geometry work.

## Measured findings (file:line cited in source analysis)

1. **Crown width vs census spacing — NOT the problem.** North Woods median nearest-neighbour
   spacing 4.86 m (Ramble 5.52 m); per-species same-genus median 5.9 m (oak) / 6.8 m (maple)
   / 8.1 m (cherry). Model crown radii (`branch_length_ratio × desired_h`, models normalised
   to ~5.0 m GLB height, runtime `sx=sy`): oak_l ~7.5 m, oak_m ~5.4 m, maple_l ~7.5 m,
   cherry_l ~7.6 m. Each already **exceeds half the neighbour distance** → crowns geometrically
   interpenetrate (+2 to +4.5 m). **Do NOT widen crowns to fix coherence.** Validation targets
   (match real spread): oak_l 7–8 m, oak_m 5–6 m, maple_l 7–9 m, cherry_l 5–7 m — already
   approximated. What matters is the **crown edge is dense**, not wider.

2. **Height layering — present.** North Woods (N=991) inverse-J: 7% sapling (0–8 m), 15%
   sub-canopy (8–14 m), 19% lower-canopy (14–18 m), 42% canopy (18–25 m), 17% emergent
   (25–35 m), median 19.1 m. DBH→height map `tree_builder.gd:454-471` (oak [15,30], maple
   [14,26], cherry [10,22]). Sub-canopy is a touch thin (~15% vs ideal ~30%) but the
   mechanism works — not a primary lever.

3. **Dedup / scatter — permits overlap.** `DEDUP_DIST=3.0` (`convert_to_godot.py:1508`,
   Chebyshev, OSM-vs-census only); scatter `MIN_TREE_SPACING=3.5` (`:1649/:2016`). 3–3.5 m
   trunk separation vs 5–7 m crown radii → crowns interpenetrate 2–4 m. Not a tidy grid; not
   the problem.

4. **Per-instance yaw — already applied** (`tree_builder.gd:615-622`, `y_rot = rng.randf()*TAU`;
   per-tree seed `:530`). **Do NOT re-add yaw.** `sx=sy` (no width jitter) except `cathedral_elm`
   gets `sx = sy×1.5` (`:613`). Safe to ADD later: ±10% XZ-scale jitter + small per-instance
   lean (1–5°) — neither exists today.

5. **Shared wind field — correct.** `wind_phase(origin) = origin.x*0.04 + origin.z*0.06`
   (`shaders/include/wind.gdshaderinc:46-48`), read from world-space tree origin in
   `tree_leaf.gdshader:177-181` and `tree_bark.gdshader:55`. World-XZ spatial gradient → a
   coherent travelling wave across a stand, NOT independent per-instance phases. The §5b
   "independent phase" worry does not apply. (It is a *linear* plane wave, not a noise field —
   acceptable; a future organic-turbulence upgrade is optional, not a coherence fix.)

## Implication for the hero loop
The realism + coherence work is **branch architecture, crown-edge density, and species
distinctness** — model geometry — NOT crown width, placement, or wind. Per trees.md §4e/§7 the
opaque-pass + near-sparsity fixes already restored edge density: **verify in a woodland capture
before assuming the edge is still thin.** Cathedral_elm's crown width is likewise already met
(0.52 ratio + runtime ×1.5); its hero problem is the **high-vase branch architecture** (fork
height + arching reach) and **allée placement convergence**, not width.
