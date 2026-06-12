# BRIEF — Wisteria (Wisteria sinensis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md) §7 (vines).

- **Archetype key:** `Vine_Wisteria` — generator `build_wisteria()` in
  `scripts/make_vine.py:427` (seed 4600); runtime `vine_builder.gd` (**DISABLED, ln 111**).
- **Layer:** vine (massive woody twiner; ornamental/escaped; pendant-bloom hero of the vine set)
- **Tier coverage:** n/a (tree-attached / pergola; no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
On CP pergolas/structures and escaped onto edge trees per [[reference-cp-botany-full]]
(and Conservatory Garden wisteria, [[reference-conservatory-garden-plants]]); iNat CP-bbox
count TO CONFIRM. **The pendant lavender racemes are the whole identity** — a walk/photo of
a blooming wisteria is the key reference.

- [ ] **Habit** — massive woody twining trunk; drapes a pergola/host
- [ ] **BLOOM** (dramatic pendant lavender-purple racemes, late spring — diagnostic)
- [ ] **Leaf detail** (pinnately compound, many leaflets)
- [ ] **Bare winter** (thick gnarled woody twining trunk; seed pods)

## 1. Habit — how it flows over itself
- **One-liner:** a massive, woody, **twining** trunk that climbs and drapes a host or
  pergola, hung in late spring with **long pendant racemes of lavender-purple flowers**
  cascading downward — the bloom is the entire identity.
- **Climbing mechanism:** **heavy twining** (`make_spiral_wrap`) — a thick gnarled
  spiraling woody trunk; the flowers and foliage **hang down** from the support.
- **Asymmetry:** drapes from whatever it climbs; pendant.

## 2. Interaction — how it meets its neighbors
- **On a host/structure:** wraps and drapes a pergola or smothers an edge tree; the
  pendant racemes hang in a curtain beneath the support.
- **Target stand reading:** a structure/crown draped in cascading lavender flower
  curtains in late spring; a gnarled woody twiner the rest of the year.

## 3. Density
- **Bucket:** medium foliage; the **pendant flower curtain** is the visual mass in spring.
- **Light transmission:** medium (open compound foliage).

## 4. Detail
- **Stem:** thick, woody, gnarled, twining.
- **Leaf:** **pinnately compound** (7–13 leaflets, the foliage opens with/after bloom) →
  `compound_mode`.
- **Summer color:** medium green · **Fall:** yellow (not showy).
- **Bloom:** **dramatic pendant racemes (20–40 cm) of lavender-purple pea-flowers**, in
  **late spring** (`bl` ~[0.6,1.0], with or just before leaf-out — so the flower curtain
  hangs on a nearly bare twining frame), faintly fragrant; flattened velvety seed pods after.

## 5. Behavior
- **Wind:** the pendant racemes and compound leaves sway/dangle; the woody trunk is rigid.
- **Seasonal timeline:** bare gnarled twiner (winter) → **pendant lavender racemes on the
  nearly-bare frame (late spring, the identity)** → pinnate foliage opens (late spring–
  summer) → green summer drape → yellow fall + velvety seed pods → bare gnarled woody
  trunk with persistent pods (winter, deciduous).

## 6. The one unmistakable thing
**Long pendant racemes of lavender-purple flowers cascading down** from a gnarled woody
twining trunk in late spring.

## 7. Per-instance variation envelope
- **Varies across seeds:** trunk gnarl/extent, drape mass, raceme count/length, host/pergola.
- **Variant count:** 2–3 — fewer placements (ornamental/structure-tied); set `v=2` or `3`.

## 8. What this brief drives (build mapping)
- **Generator:** `build_wisteria()` — redesign to a **heavy twining woody trunk**
  (`make_spiral_wrap`) with **pendant flower racemes** (the willow/elderberry strand-card
  + `create_strand_cards_at_positions` lesson is the right tool for the hanging racemes)
  and `compound_mode` pinnate foliage.
- **Textures:** pinnate compound leaflet; pendant lavender pea-flower raceme; gnarled bark.
- **Re-enable:** after GLB passes brief + perf gate.
- **Placement:** ornamental — pergolas/structures + escaped onto a few edge host trees
  (low count). NOTE: structure placement may be a man-made-layer tie-in (deprioritized);
  the escaped-on-trees form can go on woodland-edge hosts now.
- **Perf:** pendant racemes + compound foliage; low placement count keeps it cheap;
  perf-gate after re-enable.

## 9. Definition of Done
- [ ] Reads as wisteria (gnarled twiner + pendant lavender racemes).
- [ ] **Late-spring bloom capture** shows the cascading lavender flower curtains (the identity).
- [ ] On-host/structure drape capture (interaction).
- [ ] Perf gate ×5 equal-or-better after vine re-enable.
- [ ] User walk-around sign-off.
