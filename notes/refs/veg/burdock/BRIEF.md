# BRIEF — Common Burdock (Arctium minus)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_Burdock` — generator `make_burdock()` in
  `scripts/make_undergrowth.py:1641`; runtime `undergrowth_builder.gd` `SPECIES` **index 22**.
- **Layer:** herb (coarse biennial weed, yr2 to ~1.2 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP at disturbed edges, woodland margins, and near maintenance areas (Ramble
paths, North Woods edges) per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM.
Source: [`docs/botany/herbs_13species.md`](../../../docs/botany/herbs_13species.md) §12.

- [ ] **Habit, yr2 flowering plant** — iNat CP; herbs doc §12
- [ ] **Yr1 rosette** (huge heart-shaped basal leaves carpeting the ground)
- [ ] **As scattered coarse individuals** (NOT a colony — disturbed-edge weed)
- [ ] **Leaf detail** (enormous cordate, rhubarb-scale; WHITE-WOOLLY underside, rugose)
- [ ] **Bur detail** (hooked spiny globular heads, purple disc florets)

## 1. Habit — how it flows over itself
- **One-liner:** biennial — **year 1** a low broad rosette of **enormous heart-shaped
  leaves** carpeting the ground like elephant ears; **year 2** a coarse, bushy, untidy
  branching plant studded with **hooked spiny burs** at the branch tips.
- **Overall form / crown shape:** yr1 flat ground rosette; yr2 broad bushy weed.
- **Aspect (width : height):** yr1 ~2 : 1 (flat carpet); yr2 ~0.7 : 1.
- **First branch / fork height:** yr2 branches profusely and broadly from low down.
- **Branch character:** stout, ridged, gray-cobwebby stems; moderately stiff.
- **Asymmetry:** coarse and untidy — never a tidy specimen.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **scattered coarse individuals** — burdock does not form
  colonies; it appears as bold solitary or loosely-grouped plants at disturbed edges, the
  yr1 rosettes conspicuous for sheer leaf size.
- **Target stand reading:** a disturbed edge reads as **a few coarse, bold individuals**
  (a giant-leaved rosette here, a bur-studded yr2 plant there) — gaps between them, NOT a
  continuous mass. Place as scattered accents.

## 3. Density
- **Bucket:** opaque per plant (huge overlapping leaves); but sparse across the ground (scattered).
- **Real number:** yr1 rosette 30–50 cm tall × 60–90 cm; yr2 0.8–1.5 m tall, 0.6–1.0 m
  spread ([[reference-cp-botany-full]]; herbs doc §12). No LAI — bucket from habit.
- **Light transmission:** low through the leaf mass; high in the gaps between plants.

## 4. Detail
- **Bark / stem (yr2):** round, ridged/grooved, stout (10–20 mm), gray-cobwebby (arachnoid
  tomentum), green; long prominent petioles.
- **Leaf / cluster:** **enormous** broadly ovate-cordate basal leaves (30–50 cm,
  rhubarb-scale), wavy margin, quilted/rugose above, **densely gray-white woolly
  underside** (bicolor — model the white underside); deep heart-shaped base. Cauline leaves
  smaller upward but still large.
- **Summer color:** dull green. · **Fall:** browning. · **Bloom/fruit:** globular heads
  with **purple disc florets** above an involucre of **hooked bracts** (`fc=[0.60,0.30,0.55]`
  purple bur — correct); the heads become brown spiny **burs** that cling — the most
  enduring feature, persisting on dead stems. `bl=[1.0,1.6]`.

## 5. Behavior
- **Wind character:** heavy, minimal movement (`flex=0.25`) — big basal leaves rest on the
  ground and barely move; cauline leaves flap heavily; bur-heads bob at tips. Coarse, sluggish.
- **Seasonal timeline:** **yr1** seedling → large rosette expanding through summer →
  overwinters as taproot/partial rosette; **yr2** rosette re-emerges → flowering stem
  elongates → purple spiny heads (Aug–Sep) → burs mature/cling (Oct–Nov) → dead stems with
  burs persist into next year; plant dies after fruiting. Model **both** yr1 rosette and yr2
  flowering forms (per-instance variation).

## 6. The one unmistakable thing
**Enormous heart-shaped basal leaves + hooked clinging burs.** The rhubarb-scale leaves
(yr1) and the spiny purple-topped burs that stick to clothing/fur (yr2) — no other CP herb
combines them.

## 7. Per-instance variation envelope
- **Varies across seeds:** **life stage (yr1 rosette vs yr2 flowering — both needed)**,
  height, leaf size, bur count/maturity, branch spread.
- **Variant count:** 2–4 — must include a yr1 rosette variant and a yr2 flowering variant.

## 8. What this brief drives (build mapping)
- **Generator:** `make_burdock()` (`scripts/make_undergrowth.py:1641`) — model the
  **enormous cordate leaves with a white-woolly underside** and the **hooked spiny burs**;
  author both the **yr1 ground rosette** and the **yr2 branched flowering** forms. Replace
  any generic helper.
- **Textures:** giant rugose cordate leaf, gray-white woolly underside, hooked spiny bur head.
- **`SPECIES` row (idx 22):** reconcile to brief — `fc=[0.60,0.30,0.55]` purple bur,
  `bl=[1.0,1.6]`, `flex=0.25`.
- **Placement:** re-wire into `ZONE_SPECIES[...]` (currently UNPLACED) at disturbed edges —
  `[5]`/`[6]` woodland edges (North Woods / Ramble), `[2]` North Meadow. Place as
  **scattered coarse individuals**, not colonial scatter.
- **Perf note:** chunk-MultiMesh; big leaf cards add overdraw per plant but plants are
  sparse — gain density from form/texture/placement. Perf-gate after re-wire (60 open / 45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as burdock (giant cordate leaves, hooked burs).
- [ ] Both yr1 rosette and yr2 flowering forms present (§7).
- [ ] **Disturbed-edge capture** shows scattered bold individuals, gaps between.
- [ ] Burs persist on the dead-stem winter capture.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
