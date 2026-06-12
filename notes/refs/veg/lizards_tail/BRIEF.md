# BRIEF — Lizard's Tail (Saururus cernuus)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Wetland_LizardsTail` — generator `make_lizards_tail()` in
  `scripts/make_undergrowth.py:2151`; runtime `undergrowth_builder.gd` `SPECIES` **index 27**.
- **Layer:** wetland (loose colonial broadleaf herb, 0.5–1.0 m) — **shade** wetland.
- **Tier coverage:** n/a (single mesh + 200 m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at shaded stream margins per [[reference-cp-botany-full]]; iNat CP-bbox
count TO CONFIRM. Source research: [`docs/botany/wetland_grasses_9species.md`](../../../docs/botany/wetland_grasses_9species.md)
§3. **Walk video helpful** for the loose see-through colony read (it is the open
counter-example to cattail's wall).

- [ ] **Habit, summer mass** — iNat CP; wetland_grasses doc §3
- [ ] **In a colony** (loose, OPEN, see-through — you see between the stems)
- [ ] **Flower spike** (nodding white drooping "tail" — the unmistakable feature)
- [ ] **Leaf** (heart-shaped, palmate veins)
- [ ] **Wind video** (complex layered motion: stem sway + leaf flutter + spike bob)

## 1. Habit — how it flows over itself
- **One-liner:** a **loose, open colony of single upright stems**, each carrying a few
  large **heart-shaped leaves** and topped by a **nodding white drooping flower spike**
  (the "lizard's tail") — airy and see-through, the antithesis of the cattail wall.
- **Overall form / crown shape:** open, airy; single unbranched stems with broad leaves
  and a curved drooping flower tip.
- **Aspect (width : height):** narrow stems, 20–30 cm leaf spread each; the colony is loose.
- **First branch / fork height:** unbranched below the inflorescence; stem may fork into
  1–2 flower spikes at the top; first leaf 10–20 cm up.
- **Branch character:** stem slightly zigzag (jointed) between nodes; leaves alternate.
- **Asymmetry:** leaves splay at different angles; nodding spike droops to one side.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **loose OPEN colony** — stems arise singly from rhizomes,
  spaced 10–25 cm (much sparser than cattail), 8–20 stems/m². **You can see between the
  stems.**
- **Target stand reading:** *a shaded stream margin reads as a loose, see-through patch of
  upright broadleaf stems with white nodding tails — open, with visible gaps and dark wet
  ground between stems, not a dense wall.* This open/see-through read is the explicit
  contrast to cattail and phragmites and must come through.

## 3. Density
- **Bucket:** open/lacy — loose colony, see-through.
- **Real number:** 8–20 stems/m², loosely spaced; patches 1–3 m across
  ([[reference-cp-botany-full]] / wetland doc §3).
- **Light transmission:** high — an open colony.

## 4. Detail
- **Bark / stem:** green, sometimes reddish at nodes, 4–8 mm, round/solid, slightly zigzag.
- **Leaf / cluster:** **heart-shaped (cordate)** with a pointed tip and a notched base,
  8–15 cm long × 5–10 cm wide, **palmate venation** (5–7 veins from the base); medium-dark
  green, thin/translucent when backlit; 3–6 alternate leaves per stem. A broadleaf, not a
  blade.
- **Summer color:** rich medium-dark green · **Fall:** yellow then brown (Oct), dies back
  fully — **no winter presence.** · **Bloom:** **pure white nodding/drooping flower spike**
  (`fc=[0.96,0.96,0.90]` correct), 10–15 cm, gently curved and nodding like a tail; the
  white is from conspicuous stamens (no petals); **Jun–Aug** (long window).

## 5. Behavior
- **Wind character:** **independent-element motion, stiffness 3/10** (`flex=0.35` —
  consistent; one of the most mobile plants in the set). Even light wind sways the upper
  stem/leaves; in moderate wind the stem bends 20–30°. Heart-shaped leaves **flutter and
  twist on their petioles** showing pale undersides (flickering light/dark). The nodding
  spike **bobs at a different frequency** than the stem (pendulum tip). Net effect:
  **complex, layered multi-frequency motion** — stem sway + leaf flutter + spike bob —
  unlike the simple single-axis sway of grasses. Soft leafy rustle.
- **Seasonal timeline:** stems emerge, leaves unfurl (Apr–May) → growth, spikes emerge
  (Jun) → white drooping tails (Jun–Aug) → seeds ripen, foliage green (Sep) → leaves
  yellow, stems die back (Oct) → **fully dormant, no above-ground presence (Nov–Mar).**

## 6. The one unmistakable thing
The **nodding white drooping flower spike** ("lizard's tail" curve) above **heart-shaped
palmate-veined leaves**, in a **loose see-through** shaded-stream colony.

## 7. Per-instance variation envelope
- **Varies across seeds:** stem height (0.5–1.0 m), leaf count (3–6), spike presence/curve,
  leaf splay/twist.
- **Variant count:** 3 (loose colony, but enough to break repeat); set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_lizards_tail()` (`make_undergrowth.py:2151`) — single zigzag upright
  stem, 3–6 alternate **heart-shaped (cordate) palmate-veined** leaves, a **nodding/drooping
  white spike** at the top. Loose, NOT a dense card mass.
- **Textures:** cordate leaf with palmate veins (thin/translucent); white drooping spike.
- **`SPECIES` row (idx 27):** **reconcile to brief** — `fc=[0.96,0.96,0.90]` white correct,
  `bl=[0.8,1.4]`, `flex=0.35` correct; confirm `v=3`.
- **Placement:** re-wire into `ZONE_SPECIES[7]` **Waterside (currently EMPTY [])**, gated
  to **SHADED** stream margins (Loch banks, Ravine — high shade tolerance); place as a
  **loose open colony** (10–25 cm spacing, see-through), explicitly sparser than cattail.
- **Perf:** chunk-MultiMesh; **low density** (open colony) keeps overdraw down — perf-gate
  Waterside (60 open, but these are shaded woodland-edge wet chunks — watch the 45 budget).

## 9. Definition of Done
- [ ] Thumbnail reads as lizard's tail (heart leaves + nodding white tail).
- [ ] **Colony capture** at a shaded stream margin reads as LOOSE and see-through.
- [ ] Bloom capture: white nodding tails in the Jun–Aug window.
- [ ] Wind capture: layered motion (stem + leaf flutter + spike bob), not single-axis.
- [ ] Winter capture: fully absent (dies back) — verify season_t drop.
- [ ] Perf gate ×5 equal-or-better after Waterside re-wire.
- [ ] User walk-around sign-off.
