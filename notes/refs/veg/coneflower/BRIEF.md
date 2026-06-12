# BRIEF — Cutleaf Coneflower (Rudbeckia laciniata)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_Coneflower` — generator `make_coneflower()` in
  `scripts/make_undergrowth.py:1368`; runtime `undergrowth_builder.gd` `SPECIES` **index 14**.
- **Layer:** herb (tall loosely-branching perennial, 1.0–3.0 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP along the Loch/Ravine, the Gill, wet edges of the Pool, and North Woods
stream corridors per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Native.
**Walk video helpful** for the dancing-flower wind read (the airy upper canopy is the
character and a still misses it).

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** (standing dead stems with elongated dark brown cones)
- [ ] **In a loose stream-bank stand** (the interaction)
- [ ] **Stem detail** (smooth glaucous blue-green stems)
- [ ] **Cutleaf detail** (deeply pinnately dissected lower leaves — "laciniata")
- [ ] **Bloom** (drooping yellow rays + GREEN cone — the signature) 

## 1. Habit — how it flows over itself
- **One-liner:** a tall green column of deeply-cut foliage that branches loosely in the
  upper third into wiry stems, each carrying a single yellow daisy with drooping rays — a
  loose, airy, dancing candelabra of flowers, far more open than Joe-Pye weed.
- **Overall form / crown shape:** tall column below, open airy candelabra above.
- **Aspect (width : height):** ~0.4 : 1 (tall, 1.0–3.0 m; spread 0.6–1.0 m).
- **First branch / fork height:** upper third — branches diverge 30–45° to carry flowers on
  long wiry peduncles.
- **Branch character:** smooth glaucous (blue-green waxy) stems, tapering from 1–2 cm base
  to 3–5 mm in the flowering upper portion; moderately flexible.
- **Asymmetry:** loose and graceful — flowers scatter on long peduncles, a dancing constellation.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **loose colony** (spreads by short rhizomes) along wet ground —
  tall stems with airy upper canopies, flowers dancing above; more open and graceful than a
  packed stand, gaps of light through the upper structure.
- **Target stand reading:** *a loose stand of tall coneflowers along a stream bank, the
  drooping-ray yellow flowers scattered like a dancing constellation on long wiry stems
  above deeply-cut foliage.* (Validate on a stream-bank stand.)

## 3. Density
- **Bucket:** open/lacy (airy upper canopy, dissected leaves).
- **Real number:** 1.0–3.0 m, spread 0.6–1.0 m; moist/wet stream banks
  ([[reference-cp-botany-full]]). Moderate density at wet edges.
- **Light transmission:** high through the open upper structure.

## 4. Detail
- **Bark / stem:** smooth glabrous, **glaucous blue-green** (subtly waxy); solid.
- **Leaf / cluster:** lower leaves **deeply pinnately dissected** — 3–7 lobed/cut leaflets,
  "torn" look (15–40 cm) — the ID feature; upper leaves progressively simpler (3-lobed →
  ovate). Complex shadowed foliage mass.
- **Summer color:** medium green · **Fall:** yellowing; cones brown · **Bloom:** **the
  signature — 6–10 cm daisy with 6–12 yellow rays that DROOP/reflex downward (a yellow
  shuttlecock) and a distinctive GREEN-to-greenish-yellow center cone** (not dark brown like
  other Rudbeckia). `fc=[0.85,0.72,0.10]` yellow is correct; the drooping rays + green cone
  must read.

## 5. Behavior
- **Wind character:** flexible and graceful (`flex=0.35` — correct). The tall branching
  upper stems sway independently, each flower head nodding on its long peduncle, drooping
  rays fluttering — the whole upper canopy dances while the lower leaves stay stable. Looks
  alive in a breeze.
- **Seasonal timeline:** basal cut leaves emerge (Apr) → large dramatic lower leaves, stem
  elongation (May–Jun) → branching, first buds (Jul) → **yellow drooping-ray flowers
  dancing, peak** (Aug) → green-brown cones forming (Sep) → standing dead stems with dark
  elongated cones, leaves fallen (Oct–Nov).

## 6. The one unmistakable thing
**Drooping/reflexed yellow rays around a GREEN center cone** on long dancing stems — the
green cone (not black/brown) plus the shuttlecock droop is the diagnostic combination.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (wide — 1.0–3.0 m), branch/flower count, dissection of
  lower leaves, cone elongation stage, lean. Wide height range → vary it visibly.
- **Variant count:** 3 (`v=3`) — moderate stream-bank density wants variety.

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_coneflower()` (`scripts/make_undergrowth.py:1368`) — build the
  tall column + loose upper candelabra; **deeply pinnately dissected lower leaves**;
  flowers with **drooping rays and a green center cone** on long wiry peduncles; glaucous stem.
- **Textures:** cutleaf dissected leaf; drooping-ray yellow daisy with green cone; brown
  elongated-cone seed-head variant.
- **`SPECIES` row (idx 14):** reconcile to this brief — `fc=[0.85,0.72,0.10]` yellow
  (correct), `bl=[1.0,1.8]`, `flex=0.35` (correct — dancing). Stem color should read glaucous.
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[7]` (Waterside, stream
  banks — **currently EMPTY, populated here**) and `[8]` (Wild Meadow, moist — **also
  EMPTY**) at moderate density on moist/wet ground. Add `v=3`.
- **Perf:** chunk-MultiMesh + overdraw; the lacy form is cheap per plant — gain the look
  from dissected-leaf and drooping-ray cards, not raw count. Perf-gate after placement
  re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as cutleaf coneflower (drooping yellow rays, green cone, cut leaves).
- [ ] **Stream-bank stand capture** shows tall stems with dancing flowers above cut foliage.
  *The stand is the validation unit.*
- [ ] Drooping rays + green cone read clearly at bloom; dancing wind behavior.
- [ ] Standing dead stems with dark elongated cones in the winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
