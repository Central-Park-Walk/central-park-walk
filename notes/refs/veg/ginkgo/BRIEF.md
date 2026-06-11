# BRIEF — Ginkgo (Ginkgo biloba)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).

- **Archetype key:** `ginkgo` (~1.8 k census) · **Layer:** canopy · **Tier coverage:** s/m/l (verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 43 research-grade _Ginkgo biloba_ in bbox; census ~1.8 k (common street tree).
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §12; Morton/NCSU.
- [ ] **In-stand video:** none — non-blocking; iconic, well documented.

## 1. Habit
- **One-liner:** *distinctly **irregular and angular when young** — sparse, stiff, ascending
  branches with open space between them — broadening to a spreading, somewhat irregular crown
  with age; never tidy, always architectural.*
- **Form:** irregular/angular → broadly pyramidal-to-spreading. **Aspect:** ~0.6 : 1
  (10–15 m spread on 15–23 m). **Fork:** moderately high (`branch_start` 0.28). **Branch
  character:** stiff, ascending, **angular and well-separated** (open, you see the structure);
  short spur-shoots bear leaf clusters. **Asymmetry:** high — ginkgos are characterfully
  irregular; lean and gaps read.

## 2. Interaction
- **Stand:** open angular crowns **overlap loosely**, not a tight ceiling — architectural
  gaps persist. **Target reading:** sculptural, open, gold-in-fall — distinct from dense domes.

## 3. Density
- **Bucket:** open/moderate. **Real:** LAI **2.5–4.0**; transmission ~20–35% (CANOPY_OPACITY ~0.6).

## 4. Detail
- **Bark:** gray-brown, furrowed/corky ridged with age. **Leaf:** **fan-shaped (flabellate),
  often notched**, 5–10 cm, on thin petioles, clustered on spur shoots. **Summer:** medium green.
  **Fall:** **brilliant clear GOLD, then drops almost all at once** (the signature event) — Nov.
  **Bloom:** none showy (ignore).

## 5. Behavior
- **Wind:** leaves **flutter** on thin petioles (flat blade); stiff angular branches move little —
  a fluttering foliage over a rigid skeleton.
- **Season:** flush (Apr) → green summer → **brilliant gold (Nov) → synchronous mass drop** → bare angular skeleton (very legible — model it well).

## 6. The one unmistakable thing
**Fan-shaped leaves + brilliant synchronous-gold fall on an angular, open, sculptural crown.**
If it reads as a smooth dense ball, it's wrong — the open angular architecture is the species.

## 7. Variation envelope
- **Varies:** crown irregularity/angularity, width, height (DBH), lean, branch separation, density.
- **Count:** **6–8** (high census; the irregularity makes tiling obvious; confirm picker >5).

## 8. Build mapping
- **Params** (`ginkgo` @ ln 954): preserve the **angular, open, well-separated branch**
  architecture (don't over-fill); `branch_start` 0.28; low `leaf_density`. Mind the documented
  mesher crash (ginkgo dense+highres at large scale — keep workaround).
- **Textures:** fan-shaped leaf; clear-gold fall recolor + synchronous-drop phenology.
- **Placement:** loose overlap (not closure). **Perf:** open crown → fewer cards; fragment-bound. Gate ×5.

## 9. DoD
- [ ] Thumbnail: fan leaves, angular open crown. [ ] Brilliant gold synchronous-drop fall.
- [ ] In-stand: open architectural read. [ ] Tier handoff + crossfade. [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
