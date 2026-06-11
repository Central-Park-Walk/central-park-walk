# BRIEF — Gray Birch (Betula populifolia)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `birch` · **Layer:** sub-canopy (small, often clumped) · **Tier coverage:** m/l (no `_s` — verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 52 research-grade _Betula_ in bbox.
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §6; Morton/NCSU.
- [ ] **In-stand video:** none specific; non-blocking (a winter woodland walk would show the white-bark clumps well — see the winter video being processed).

## 1. Habit
- **One-liner:** *a small, slender, **narrow open pyramidal** tree — often in multi-stemmed
  clumps — with slim, somewhat drooping branches and an airy see-through crown; white-barked and delicate.*
- **Form:** narrow, pyramidal, **open/airy, irregular**. **Aspect:** ~0.6 : 1 (4.5–7.5 m
  spread on 6–9 m). **Fork:** higher/slim (`branch_start` 0.33); often clumped multi-stem.
  **Branch character:** **slender, somewhat drooping**, fine-twigged. **Asymmetry:** moderate, leaning slim stems.

## 2. Interaction
- **Stand:** slim white stems and airy crowns **read as a bright open thicket/clump**, not a
  closed ceiling. **Target reading:** luminous white-stemmed open grove, see-through.

## 3. Density
- **Bucket:** open/airy. **Real:** LAI **2.5–3.5**; transmission **~15–30%** (CANOPY_OPACITY ~0.6).

## 4. Detail
- **Bark — a feature:** **chalky white-to-gray, non-peeling, with black chevron/triangle marks
  below branch scars**; slim trunks. **Leaf:** alternate, **triangular, long-pointed tip**,
  doubly serrate, 5–10 cm. **Summer:** bright green. **Fall:** clear **yellow** (Oct). **Bloom:** catkins (subtle).

## 5. Behavior
- **Wind:** **trembling** — birch is the canonical trembling/quaking crown
  ([[reference-vegetation-modeling]]); slim branches and long-petioled leaves shiver in the
  lightest breeze. Tune to the most responsive end.
- **Season:** flush (Apr) → bright airy summer → clear-yellow fall → slim white-stemmed bare clump (striking winter).

## 6. The one unmistakable thing
**Slim white-gray stems (black chevrons) + airy trembling crown.** If the bark isn't white or
the crown reads dense/heavy, it's wrong.

## 7. Variation envelope
- **Varies:** stem count (single ↔ clump), crown width, droop, height, lean, density.
- **Count:** 5 (lower census).

## 8. Build mapping
- **Params** (`birch` @ ln 638): keep slim open crown, `branch_start` 0.33, drooping fine
  branches, low `leaf_density`; support multi-stem clumps.
- **Textures:** **white-gray birch bark with chevrons** (distinct bark style); triangular leaf;
  yellow fall. **Wind:** trembling biomechanics (per-species wind shader).
- **Placement:** clumped, open overlap. **Perf:** open crown → fewer cards; fragment-bound. Gate ×5.

## 9. DoD
- [ ] Thumbnail: slim white birch, airy crown. [ ] Trembling wind reads. [ ] Yellow fall + white winter stems.
- [ ] In-stand: luminous open clump. [ ] Tier handoff + crossfade. [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
