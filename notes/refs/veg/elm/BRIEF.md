# BRIEF — American Elm, general population (Ulmus americana)

> Falsifiable target the visual DoD is judged against. Method:
> [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md); obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md).
> **Sibling of [`cathedral_elm`](../cathedral_elm/BRIEF.md)** — same species; this archetype
> is the *ordinary* park-wide elm population (younger / smaller / not the Literary Walk allée).

- **Archetype key:** `elm` · **Layer:** canopy · **Tier coverage:** s/m/l (verify) · **Written:** 2026-06-11 by Opus 4.8

## Reference set
- [x] **iNat CP:** 96 research-grade _Ulmus_ in bbox.
- [x] **Authoritative + canopy numbers:** [[reference-tree-canopy-data]] §2; Morton/NCSU + the
  Mall video (`bCQ0TCUSuBA`) for general elm vase form (the same footage that grounds cathedral_elm).
- [ ] **In-stand video:** the allée video covers form; non-blocking.

## 1. Habit
- **One-liner:** *the elm vase/fountain — trunk rising then dividing into arching limbs that
  sweep up and out — but **a degree less grand than `cathedral_elm`**: smaller, narrower,
  more variable, NOT tuned for the converging Literary Walk ceiling.*
- **Form:** vase/fountain. **Aspect:** ~0.8–1 : 1 (9–18 m spread on 18–24 m). **Fork:**
  moderate (`branch_start` 0.22 — note: **lower than cathedral_elm's high ~0.30–0.40 allée
  fork**; that difference is what separates ordinary elm from the cathedral specimen).
  **Branch character:** arching, distichous 2-ranked sprays droop at tips. **Asymmetry:** higher
  than cathedral_elm — these are varied wild-population trees.

## 2. Interaction
- **Stand:** crowns interlace where close, but this archetype is **not** placement-converged —
  it's the scattered park elm, overlapping naturally rather than forming the Literary Walk tunnel
  (that is cathedral_elm's job). **Target reading:** graceful vase crowns overlapping at natural spacing.

## 3. Density
- **Bucket:** opaque (dense layered crown). **Real:** LAI **4.5–6.0**; transmission ~5–15%.

## 4. Detail
- **Bark:** gray-brown, flattened furrowed ridges, interlacing mature (`furrowed`).
- **Leaf:** ovate-elliptic, **doubly serrate, asymmetric base** (diagnostic), 2-ranked → flat
  sprays, 10–15 cm. **Summer:** dark green. **Fall:** yellow/gold, relatively clean (Oct–Nov). **Bloom:** inconspicuous (ignore).

## 5. Behavior
- **Wind:** graceful slow arch-sway with fine-spray flutter (like cathedral_elm, lesser scale).
- **Season:** flush (Apr) → dense summer → yellow fall → bare vase silhouette winter.

## 6. The one unmistakable thing
The **vase/fountain of arching limbs with drooping 2-ranked sprays** — but plainer than the
cathedral elm. Keep it clearly the *lesser* sibling so the Literary Walk specimen still reads as special.

## 7. Variation envelope
- **Varies:** vase width, fork height (0.18–0.30 — but capped below cathedral_elm), lean, asymmetry, height (DBH), density.
- **Count:** 5 (moderate census).

## 8. Build mapping
- **Params** (`elm` @ ln 383): vase via gravity/up_attraction (generator comment notes Mtree has
  no 'vase'); keep `branch_start` 0.22 (deliberately lower/plainer than cathedral_elm); arching sprays.
- **Textures:** `furrowed` bark; elliptic 2-ranked leaf. **Placement:** natural overlap (NOT path-convergence).
- **Perf:** opaque; fragment-bound. Gate ×5. **Keep distinct from cathedral_elm** (don't converge the params).

## 9. DoD
- [ ] Thumbnail: plain elm vase, clearly lesser than cathedral_elm. [ ] Yellow fall.
- [ ] In-stand: natural overlapping vases. [ ] Tier handoff + crossfade. [ ] No tiling. [ ] Gate ×5. [ ] User sign-off.
