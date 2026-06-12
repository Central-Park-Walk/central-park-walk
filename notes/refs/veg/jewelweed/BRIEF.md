# BRIEF — Jewelweed / Spotted Touch-me-not (Impatiens capensis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Herb_Jewelweed` — generator `make_jewelweed()` in
  `scripts/make_undergrowth.py:1759`; runtime `undergrowth_builder.gd` `SPECIES` **index 17**.
- **Layer:** herb (succulent bushy ANNUAL of wet shade, 0.5–1.5 m)
- **Tier coverage:** n/a (single mesh + 200m fade, no impostor/LOD)
- **Brief written:** 2026-06-12 · **by:** Sonnet (research-doc conversion)

## Reference set
Present in CP along the Loch, Ravine, Gill, North Woods stream corridors, and wet areas
near the Pool per [[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Almost
always near water — a reliable wet-soil indicator. **Walk video helpful** for the
translucent-glow stem read and the constant restless motion (the two signatures, both lost
in a still).

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Winter bare structure** — NONE (frost-killed annual; collapses to nothing)
- [ ] **As a dense pure stand in wet shade** (the interaction)
- [ ] **Stem detail** (TRANSLUCENT pale-green succulent stems that glow in backlight — signature)
- [ ] **Leaf detail** (ovate crenate, silvery when wet — the "jewel")
- [ ] **Bloom** (orange spotted pendant flower with curled spur — the signature)

## 1. Habit — how it flows over itself
- **One-liner:** upright, loosely-branched, succulent and translucent — a lush, soft,
  pale-green bushy mass that seems to glow from within in shade, scattered with orange
  pendant flowers dangling on threadlike pedicels.
- **Overall form / crown shape:** irregular bushy mound; loose alternate branching.
- **Aspect (width : height):** ~0.6 : 1 (spread 30–60 cm at 0.5–1.5 m; colonies shoulder-high).
- **First branch / fork height:** low — branches alternate, moderately dense from low on the stem.
- **Branch character:** round smooth succulent stems (5–10 mm), water-filled, snap easily,
  swollen nodes; **pale translucent green — almost watery, glows in backlight.**
- **Asymmetry:** soft and irregular — a relaxed bushy form, never rigid.

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **dense pure stands** — jewelweed forms near-monoculture colonies
  in wet shade, a continuous lush pale-green mass distinctly lighter than surrounding
  woodland plants.
- **Target stand reading:** *a dense, lush, pale yellow-green stand filling a wet shaded
  hollow or stream corridor — the whole mass glowing translucent in dappled light, orange
  flowers dotted through it, rippling like a green wave in any breeze.* (Validate on a dense
  wet-shade stand.)

## 3. Density
- **Bucket:** dappled→full (lush colonies) but airy/soft, not opaque.
- **Real number:** 0.5–1.5 m, spread 30–60 cm, dense colonies; wet shade / stream corridors
  ([[reference-cp-botany-full]]). High placement density in wet-shade pockets.
- **Light transmission:** moderate, but the translucent stems/leaves transmit and glow
  rather than block (`sr=0.72` — keep the translucent/soft surface).

## 4. Detail
- **Bark / stem:** **the signature — pale, translucent, watery-green succulent stems that
  appear to glow from within in backlight;** reddish tints at swollen nodes. `sc=[0.35,0.50,0.18]`
  pale green is correct; honor translucency (`sr=0.72`).
- **Leaf / cluster:** alternate, ovate-elliptic (3–12 cm), **crenate (rounded teeth)**, thin
  and delicate, pale yellow-green (lighter than neighbors); silvery sheen when wet (the
  "jewel").
- **Summer color:** pale yellow-green · **Fall:** collapses (see §5) · **Bloom:** **the
  signature — orange (`fc=[0.90,0.50,0.08]`, correct) spotted pendant cornucopia flowers
  (2–3 cm) with a backward curled spur**, dangling on threadlike pedicels, bobbing in the
  slightest air. Explosive "touch-me-not" capsules follow.

## 5. Behavior
- **Wind character:** **very flexible — the most mobile herb in the set** (`flex=0.45`,
  correct). Succulent stems sway easily, thin leaves flutter, pendant flowers bob on
  threadlike pedicels; the whole colony ripples like a green wave — never still in any
  breeze.
- **Seasonal timeline:** germinate (May) → lush pale-green colonies (Jun) → orange flowers
  begin (Jul) → peak bloom + growth, exploding capsules (Aug–Sep) → **first frost KILLS the
  whole plant — collapses to black mush overnight** (Oct). **NO persistent winter structure
  — nothing above ground Nov–Mar, only seed bank.** The model must fully collapse at
  frost/late `season_t`, not just shrink.

## 6. The one unmistakable thing
**Translucent, glowing pale-green succulent stems + orange spotted pendant flowers with a
curled spur** — the watery glow and the dangling spurred flower together. If stems read
opaque/woody, the identity is lost.

## 7. Per-instance variation envelope
- **Varies across seeds:** height (0.5–1.5 m), branchiness, flower count, lean. Densely
  placed colony → vary visibly to avoid tiling.
- **Variant count:** 3–4 (`v=3`+) — dense wet-shade stands; the anti-tiling lever.

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_jewelweed()` (`scripts/make_undergrowth.py:1759`) — build the
  loose succulent bushy form with **translucent pale-green stems**, crenate ovate leaves, and
  **orange spotted pendant flowers with a curled spur** hung on threadlike pedicels; wire the
  **frost collapse** (full die-off at the cold end of `season_t`, not a shrink).
- **Textures:** ovate crenate pale-green leaf; orange spotted pendant flower; translucent
  succulent stem material.
- **`SPECIES` row (idx 17):** reconcile to this brief — `fc=[0.90,0.50,0.08]` orange spotted
  (correct), `bl=[1.0,1.8]`, `sc=[0.35,0.50,0.18]` translucent pale green (correct — the
  signature), `flex=0.45` very mobile (correct), `sr=0.72` translucent (correct — keep).
- **Placement:** currently UNPLACED — re-wire into `ZONE_SPECIES[5]`/`[6]` (North Woods /
  Ramble, **near water only**) and `[7]` (Waterside — **currently EMPTY, populated here**)
  at **high density in wet-shade pockets / stream corridors**. Add `v=3`. NOTE the annual
  collapse — it should be absent in winter captures.
- **Perf:** chunk-MultiMesh + overdraw; dense colony is the perf event — gain the lush glow
  from translucent leaf/stem material and placement density, not heavy cards. Perf-gate
  Waterside/woodland after re-wire (45 woodland).

## 9. Definition of Done
- [ ] Thumbnail reads as jewelweed (translucent glowing stems, orange spurred pendant flower).
- [ ] **Wet-shade stand capture** shows a dense pale-green glowing colony with orange flowers,
  rippling in wind. *The dense stand is the validation unit.*
- [ ] Stems read translucent/glowing, not opaque; restless wind motion (`flex=0.45`).
- [ ] **Frost collapse:** plant is ABSENT in the winter capture (annual — no skeleton).
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
