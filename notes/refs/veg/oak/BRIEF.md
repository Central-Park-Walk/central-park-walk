# BRIEF — Oak (Quercus, CP red-oak group — Pin/Red/Black/Scarlet)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md). Obeys
> [`docs/tree_model_redesign.md`](../../../docs/tree_model_redesign.md). **This is the
> deciduous-broadleaf template** (§6) — the worked example the other broadleaf species copy.

- **Archetype key:** `oak` (generator `name` = "Pin Oak (Quercus palustris)"; the runtime
  archetype covers CP's red-oak group — pin, red, black, scarlet, willow oak)
- **Layer:** canopy (the dominant North Woods / Ramble woodland canopy; ~2.6 k census trees)
- **Tier coverage:** `_s` / `_m` / `_l` (all three; verify against TIER_BOUNDS)
- **Brief written:** 2026-06-11 · **by:** Opus 4.8

## Reference set
- [x] **iNaturalist, CP-geofiltered** — API: **290 research-grade _Quercus_ observations**
  inside the park bbox. Confirms oak as the dominant native canopy genus.
- [x] **Walk-through video (in-stand canopy, North Woods)** — `250HlDgDVNw` (spring leaf-out),
  frames 45 / 360: closed oak-dominated woodland canopy with interlacing crowns and a layered
  sub-canopy — the broadleaf-template **stand** reference. *Honest caveat: the North Woods
  canopy is oak-dominated (red/black) but the frames aren't keyed plant-by-plant.*
- [x] **Habit / bark / fall / winter (authoritative)** — NCSU Extension, ODNR, Britannica,
  MO Dept. Conservation, [[reference-tree-canopy-data]] §1.
- [x] **Canopy numbers** — [[reference-tree-canopy-data]] §1 (LAI, leaf size, crown spread).

## 1. Habit — how it flows over itself
- **One-liner:** *a strong central trunk carried high into the crown (excurrent, unlike the
  elm's vase), with branches in tiers — **lower branches drooping, middle horizontal, upper
  ascending** — building a broad oval-to-rounded crown that is dense but reads in distinct
  branch layers.*
- **Overall form / crown shape:** pyramidal when young → broad oval / rounded at maturity;
  retains a discernible central leader (pin oak especially).
- **Aspect (width : height):** ~0.6–0.8 : 1 (taller than wide; 8–14 m spread on 18–25 m).
- **First branch / fork height:** low and persistent (pin oak keeps low drooping limbs;
  `branch_start` 0.16 is right) — but the trunk continues *through* the crown, it does not
  fork-and-vase.
- **Branch character:** the **three-tier droop/horizontal/ascend** signature; stiff, stout,
  somewhat crooked limbs; moderate taper.
- **Asymmetry:** woodland oaks lean and gap-reach toward light; open-grown ones are fuller
  and rounder — span both across the variants (§7).

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** crowns **interlace into a closed woodland ceiling** at census
  spacing; the central-leader form layers an emergent/canopy/sub-canopy structure rather than
  one flat top. This is the §5b forest-coherence template.
- **Target stand reading:** *a North Woods / Ramble oak stand reads as a continuous closed
  canopy with interlaced, layered crowns and dappled floor — not isolated balls with sky
  between them* (matches video frames 45/360).

## 3. Density
- **Bucket:** dappled (moderate) — denser than honeylocust, lighter than linden/elm.
- **Real number:** LAI **4.0–5.5**; deep U-sinus lobes add intrinsic gaps
  ([[reference-tree-canopy-data]] §1).
- **Light transmission:** ~15–25% — can see sky through the crown but not clearly.

## 4. Detail
- **Bark:** smooth reddish-gray when young → dark gray-brown with **shallow fissures /
  flat-topped ridges** mature (red-oak group; often shiny inner "ski-track" stripes).
  `furrowed`-family style; `bark_color (0.22,0.18,0.12)` reads right.
- **Leaf:** alternate, simple, **deeply lobed with wide U-sinuses, bristle-tipped lobes**
  (pin/red/scarlet); 7.5–15 cm; distributed along branches, not tip-clustered.
- **Summer color:** dark green. · **Fall color + timing:** **orange / bronze / russet-red**
  (Oct–Nov). · **Winter:** young oaks are **marcescent** — hold bronze/russet leaves through
  winter (drives the WINTER_RETENTION value + a distinct winter look; do NOT make oak
  cleanly bare). · **Bloom:** catkins, inconspicuous (ignore visually).

## 5. Behavior
- **Wind character:** **stiff** — oak is the canonical rigid crown
  ([[reference-vegetation-modeling]] wind ranking). Heavy limbs barely move; only the outer
  foliage shivers. Tune the per-species wind to the low-amplitude / stiff end.
- **Seasonal timeline:** flush (Apr–May) → dark-green summer → russet/bronze fall (Oct–Nov)
  → **marcescent winter hold (young trees)** → bare layered silhouette (old trees).

## 6. The one unmistakable thing
The **deeply-lobed bristle-tipped foliage on a tiered, central-leader crown** that turns
russet-bronze and (young) holds through winter. If it reads as a smooth featureless ball or
a vase, it's not an oak.

## 7. Per-instance variation envelope
- **Varies across seeds:** crown width, central-leader prominence, lower-limb droop, lean,
  asymmetry (woodland gap-reach vs open-grown round), height (DBH), density, fall timing.
- **Variant count:** **6–8** (oak is the highest-count broadleaf, ~2.6 k — tiling is most
  visible; confirm the variant picker + impostor loop handle >5 before committing —
  [`tree_model_redesign.md`](../../../docs/tree_model_redesign.md) §4).

## 8. What this brief drives (build mapping)
- **Generator/params** (`generate_trees_mtree.py`, `oak` @ ln 332): keep the low persistent
  `branch_start` 0.16 + central leader; ensure the **three-tier droop/horizontal/ascend**
  reads (lower-limb gravity, mid horizontal, upper up-attraction); keep LAI-tuned
  `leaf_density`. Widen the seed envelope to 6–8 (§7).
- **Textures:** `furrowed` bark; deeply-lobed bristle-tip leaf texture (`gen_leaf_textures`).
- **Builder/placement** (`tree_builder.gd`): woodland density/overlap so crowns interlace
  (§5b lever 2/3 — this is the template the coherence pass tunes on).
- **Perf budget:** highest-count species → worst-case for the gate; fragment-bound, gain
  density from texture/placement not card overdraw. Perf gate ×5, no regression.

## 9. Definition of Done (captures that validate this brief)
- [ ] Thumbnail reads as a lobed-leaf tiered oak, distinct from elm (vase) and linden.
- [ ] **In-game stand capture (North Woods / Ramble)** — interlaced closed woodland canopy,
  layered, dappled floor. *The stand is the validation unit.*
- [ ] Tier handoff + crossfade ([`tree_model_redesign.md`](../../../docs/tree_model_redesign.md) §9).
- [ ] Dense oak stand shows **no tiling** (§7 — 6–8 variants span the envelope).
- [ ] Marcescent winter hold reads (young trees keep russet leaves).
- [ ] Perf gate ×5 equal-or-better (mind: worst-case location for 60 fps).
- [ ] User walk-around sign-off.
