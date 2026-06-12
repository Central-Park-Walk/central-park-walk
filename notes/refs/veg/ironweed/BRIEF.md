# BRIEF — New York Ironweed (Vernonia noveboracensis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_Ironweed` — generator `make_ironweed()` in
  `scripts/make_undergrowth.py:1542`; runtime `undergrowth_builder.gd` `SPECIES` **index 20**.
- **Layer:** herb (tall stiff wet-meadow perennial, 1.5–2.0 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at wet meadow margins and watercourse edges (Pool, Harlem Meer, moist North
Meadow edges) per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Source:
[`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §10.

- [ ] **Habit, summer/bloom mass** — iNat CP; herbs doc §10
- [ ] **In a wet-meadow stand** (rigid columns crowned with deep purple)
- [ ] **Bloom detail** (extraordinarily deep saturated purple flat-topped corymb; dark phyllaries)
- [ ] **Leaf detail** (narrow lanceolate, ~5:1, finely serrate, closely spaced)
- [ ] **Behavior video** (stiffness — stands firm while neighbors sway)

## 1. Habit — how it flows over itself
- **One-liner:** tall, **iron-stiff**, soldier-straight columnar perennial, leafy and
  unbranched below, crowned only at the very top by a flat-topped cluster of
  extraordinarily **deep saturated purple** — rigid where neighbors sway.
- **Overall form / crown shape:** columnar to narrowly vase; single flat corymb crown.
- **Aspect (width : height):** ~0.4 : 1 (narrow, erect).
- **First branch / fork height:** only at the very top, to form the corymb.
- **Branch character:** stems notably rigid (tough — the "iron" — barely break by hand);
  no lateral branching below the crown.
- **Asymmetry:** minimal — strictly upright, soldier-like posture.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** clump-forming (3–6 stems/clump) at wet margins — clumps stand
  as a row of rigid purple-topped columns along the water edge.
- **Target stand reading:** a wet-meadow / stream-margin stand reads as **stiff vertical
  green columns crowned with vivid dark-purple corymbs**, holding rigid while softer
  neighbors move — the rigidity is part of the read.

## 3. Density
- **Bucket:** dappled per plant (narrow leaves along an erect stem); the stand is a vertical matrix.
- **Real number:** 1.0–2.5 m tall, 0.5–0.8 m spread, 3–6 stems/clump
  ([[reference-cp-botany-full]]; herbs doc §10). No published LAI — bucket from habit.
- **Light transmission:** medium per plant (narrow leaves, erect stem).

## 4. Detail
- **Bark / stem:** round, solid, **stiff**, 6–12 mm, green tinged purple-brown, finely
  appressed-hairy.
- **Leaf / cluster:** alternate, lanceolate to narrowly elliptic, ~5:1 long:wide, finely
  serrate, closely spaced at ~45° — willow-like and full along the stem.
- **Summer color:** dark green. · **Fall:** yellowing, no showy color. · **Bloom:**
  **extraordinarily deep, saturated red-purple/violet** flat-topped corymb
  (`fc=[0.50,0.15,0.55]` deep purple — the signature; the darkest purple of any common
  wildflower here), `bl=[1.0,1.8]`; dark-purple-to-black awl-tipped phyllaries below the heads.

## 5. Behavior
- **Wind character:** **very stiff** (`flex=0.30` set very low intentionally) — light wind
  barely moves it; only the top corymb sways and leaves flutter; springs straight back.
  The stiffness is a visual signature. Dead stems are the most rigid/persistent of these herbs.
- **Seasonal timeline:** stiff upright shoots (Apr–May) → rapid leafy column (Jun–Jul) →
  vivid deep-purple corymb bloom (Aug–Sep, the event) → tawny pappus seed → stiff brown
  stems holding posture through winter.

## 6. The one unmistakable thing
The **darkest, most saturated purple corymb of any common wildflower** atop a rigid,
unbending, soldier-straight column. Deep red-purple/violet — not lilac, not lavender —
crowning a stem that stands firm while everything around it sways.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (1.5–2.0 m typical, to 2.5 m), stem count per clump,
  corymb size, slight lean.
- **Variant count:** 2–4 (a tall accent at wet margins; modest scatter).

## 8. What this brief drives (build mapping)
- **Generator:** `make_ironweed()` (`scripts/make_undergrowth.py:1542`) — model the
  rigid soldier-straight column, narrow closely-spaced lanceolate leaves, and the deep-purple
  flat-topped corymb with dark phyllaries. Replace any generic helper.
- **Textures:** narrow lanceolate serrate leaf, deep-purple fuzzy corymb cluster.
- **`SPECIES` row (idx 20):** reconcile to brief — `fc=[0.50,0.15,0.55]` deep saturated
  purple (signature), `bl=[1.0,1.8]`, `flex=0.30` (very stiff, "iron" — keep low).
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED; zones 7/8 currently
  empty) at wet meadow / stream margins — `[7]` Waterside, `[8]` Wild Meadow. Place at
  moist edges, not dry open lawn.
- **Perf note:** chunk-MultiMesh; low overdraw per plant (narrow) — gain density from
  form/texture/placement, not card count. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as ironweed (rigid column, deep-purple corymb, narrow leaves).
- [ ] **Wet-margin stand capture** shows the row of stiff purple-crowned columns.
- [ ] **Wind capture** shows it holding rigid while neighbors sway.
- [ ] Bloom fires at `bl=[1.0,1.8]` in the signature deep purple.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
