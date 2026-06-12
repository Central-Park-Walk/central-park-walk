# BRIEF — Witch Hazel (Hamamelis virginiana)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Shrub_WitchHazel` — generator `make_witch_hazel()` in
  `scripts/make_undergrowth.py:939`; runtime `undergrowth_builder.gd` `SPECIES` **index 1**.
- **Layer:** shrub / sub-canopy (woodland mid-story, larger than spicebush)
- **Tier coverage:** n/a (undergrowth: single mesh + 200 m distance fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Sourcing order per method §3. **Present in CP woodlands** per
[[reference-cp-botany-full]] (Ramble, North Woods, Hallett); exact iNat CP-bbox count
TO CONFIRM (API query like spicebush's 283). **Walk video requested** if the
late-autumn flowering-on-bare-branch read is unclear from stills — it's the whole
identity and stills rarely catch the simultaneous yellow-leaf + yellow-flower moment.

- [ ] **Habit, summer mass** — iNat CP; Morton/Missouri Bot/NCSU extension
- [ ] **Winter / late-autumn bare structure** (the zigzag skeleton + ribbon flowers — MOST important)
- [ ] **In a stand** (open mid-story, not isolated)
- [ ] **Bark / twig zigzag detail**
- [ ] **Leaf detail** (obovate, wavy-scalloped margin, asymmetric base)
- [ ] **Fall color + the autumn bloom** (the diagnostic season)

## 1. Habit — how it flows over itself
- **One-liner:** large multi-stemmed shrub/small tree, low-forking, with ascending
  then widely spreading **zigzag (flexuous) branches** that build an open, irregular,
  layered crown — airy and see-through, never a solid ball.
- **Overall form:** irregular open vase to broad rounded; **3–5 m** (taller than spicebush).
- **Aspect (w:h):** ~1.0–1.2 (as wide as tall, often wider).
- **First fork height:** low — multi-stemmed from near the base (~0.1–0.2 h).
- **Branch character:** the signature is the **zigzag twig** (each node bends ~30–40°)
  and a tiered, horizontally-spreading layering of the outer branches.
- **Asymmetry:** strongly asymmetric / lopsided reaching toward light gaps — it leans.

## 2. Interaction — how it meets its neighbors
- **In a stand:** open mid-story; loose groups or scattered individuals, crowns do NOT
  merge into a screen (contrast viburnum). Light passes between and through.
- **Target stand reading:** a few airy, layered, leaning shrubs in the understory shade
  with visible structure between them — not a dense thicket.

## 3. Density
- **Bucket:** open / dappled.
- **Real number:** low leaf density for its size (open crown); generator `leaf_density=40`
  is in range — keep open, don't fill.
- **Light transmission:** high — you see branch architecture through it.

## 4. Detail
- **Stem/bark:** smooth gray-brown, thin; the **zigzag twig habit** is the detail that matters.
- **Leaf:** alternate, obovate, **wavy-scalloped (crenate) margin**, distinctly
  **asymmetric (oblique) base**; 8–13 cm; medium green.
- **Summer color:** medium green · **Fall:** clean butter-yellow (`fall=[0.75,0.65,0.12]`).
- **Bloom:** **LATE AUTUMN (Oct–Dec), `bl=[2.2,3.0]` — correct and unusual.** Spidery
  flowers with 4 narrow crinkled ribbon-like yellow petals, in small clusters along the
  bare/yellowing branches.

## 5. Behavior
- **Wind:** gentle (`flex=0.25`) — open woody crown, moderate sway, leaves flutter on petioles.
- **Seasonal:** flush → summer mass → **yellow leaves + yellow ribbon flowers together in
  late autumn** → leaf drop (may hold some marcescent leaves) → open zigzag winter skeleton.

## 6. The one unmistakable thing
Spidery yellow ribbon-petalled flowers blooming on a leafless **zigzag** shrub in late
fall — often *with* the last yellow leaves still on. Nothing else in the woods does this.

## 7. Per-instance variation envelope
- **Varies across seeds:** lean direction/amount, crown openness, stem count (4–7),
  height 3–5 m, layering tier count.
- **Variant count:** 3 (mid-story density, moderate visibility) — set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_witch_hazel()` — **replace the generic `_make_shrub(zigzag=True)`
  call** with bespoke open-crown geometry: real zigzag branch walk, tiered spreading
  layers, ribbon-petal flower clusters on bare branches for the autumn `bl` window.
- **Textures:** obovate scalloped leaf (gen_leaf_textures), ribbon-petal flower cluster
  (gen_cluster_textures).
- **`SPECIES` row (idx 1):** `fc`/`bl` autumn-bloom already correct; verify `fall` yellow,
  `flex=0.25`; **add `v=3`.**
- **Placement:** re-wire into `WOODLAND_SPECIES` + `ZONE_SPECIES[5]` (North Woods) and
  `[6]` (Ramble) at LOW density (open mid-story accent, ~0.5–1.0/100 m²) — not thicket density.
- **Perf:** open crown = cheap; low placement density. Perf-gate woodland after re-wire.

## 9. Definition of Done
- [ ] Thumbnail reads as witch hazel (zigzag, open, asymmetric), matches §1–§6.
- [ ] **Autumn capture** shows ribbon flowers on bare/yellow branches (the identity).
- [ ] In-game North Woods/Ramble capture — placed, open mid-story, NOT a ball.
- [ ] Dense same-species group shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
