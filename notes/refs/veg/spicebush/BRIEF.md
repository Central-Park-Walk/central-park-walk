# BRIEF — Northern Spicebush (Lindera benzoin)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md). This is the
> **canonical named-failure case** (`tree_model_redesign.md` §7): the current model is
> V-shaped; the real plant cascades.

- **Archetype key:** `spicebush` — generator `make_spicebush()` in
  `scripts/make_undergrowth.py:844`; placed by `undergrowth_builder.gd` (entry @ ln 60).
  **Not** the tree impostor chain.
- **Layer:** shrub / sub-canopy understory (the dominant Central Park woodland understory shrub)
- **Tier coverage:** n/a (undergrowth: 3 seed variants `Shrub_Spicebush_{0,1,2}.glb`, billboard/LOD per `undergrowth_builder.gd` — confirm mechanism before editing)
- **Brief written:** 2026-06-11 · **by:** Opus 4.8 (Fable-5-spec execution session)

## Reference set
Sourced in the user-confirmed order. iNaturalist CP confirms the population; authoritative
institutional sources give form/season; **a CP woodland (North Woods / Ramble) walk video is
REQUESTED** — the in-stand cascade, the winter skeleton, and the thicket read are the whole
point here and are the fields stills/text leave thin (method §3 step 2: ask on species one).

- [x] **iNaturalist, CP-geofiltered** — API count: **283 research-grade _Lindera benzoin_
  observations** inside the park bbox — by far the dominant understory shrub, confirmed in
  *this* park. (Web UI 403s; API count only — individual photos not visually inspected.)
- [x] **Walk-through video (North Woods, PRIMARY for in-context habit)** — user-supplied
  *North Woods walking tour*, YouTube `250HlDgDVNw`, ~7:39, late-spring leaf-out (bright
  green, spring ephemerals on the floor; the Loch/Ravine + Glen Span Arch). claudetube
  URL/audio path failed (video-only stream, silent tour) → downloaded local + **ffmpeg
  frames** at 45/90/135/180/225/**228/232**/270/315/360/**400**/405 s. Frames inspected.
  *Covers in-stand habit, thicket interaction, leaf-out, behavior. Does NOT cover the bare
  winter skeleton (spring footage) — winter habit taken from the authoritative bud/twig
  description below; a late-fall/winter walk would refine it but is no longer blocking.*
  **Honest scope:** the frames show the dominant North Woods shade-form understory shrub
  layer read *as a mass* (the user identifies it as spicebush-dominated); habit/interaction
  observed at the stand level, not botanically keyed plant-by-plant from frames.
- [x] **Habit (authoritative)** — Morton Arboretum, Missouri Botanical (Kemper), NCSU
  Extension, PSU Extension, ODNR, Wikipedia: multi-stemmed; rounded to irregular, broad;
  **arching branches**; "tolerates full shade, but **habit becomes more open and
  wide-spreading**" (CP understory = the shade form).
- [x] **Winter structure (authoritative, needs in-context video)** — knobby **paired floral
  buds** on **olive-green twigs**; greenish-tan stems with pale lenticels; mature bark dark
  brown with a green tint; "good winter interest… persistent branch structure."
- [x] **Colonial/thicket (interaction)** — "colonial… reproduces by root suckers, forming
  clumps or thickets" (NCSU/PSU). Thicket-forming is authoritative; the *visual* read of a
  CP thicket is the video ask.
- [x] **Leaf** — alternate, simple, obovate-elliptic, thin, aromatic, to ~15 cm; not lobed.
- [x] **Fall color** — clear/bright **yellow** (Morton/Missouri Bot), best in sun; muted to
  chartreuse-yellow in deep shade.
- [x] **Bloom** — tiny **greenish-yellow** clusters, **March, pre-leaf**, hugging the bare
  twigs; showy *en masse* as a soft yellow haze in the bare woods. Red drupes (female, ~½",
  fall, hidden until leaf drop).
- [x] **Wind ranking** — [[reference-vegetation-modeling]]: mid-flexibility
  (Sweet Pepperbush > **Spicebush** > Sumac) — whole arching stems bounce moderately.

## 1. Habit — how it flows over itself
- **One-liner:** *multi-stemmed shrub; several primary stems arch up and outward, then the
  secondary growth droops and layers over itself so the whole plant cascades into a soft,
  open, rounded mound — it flows over itself; **it is never a V/vase.*** (User ground truth
  2026-06-11 + authoritative "arching, rounded, open & wide-spreading in shade.")
- **Overall form / crown shape:** mounding / broad-rounded, open & wide-spreading (shade
  form). Width ≈ or > height.
- **Aspect (width : height):** ~1 : 1 to 1.3 : 1 (often wider than tall in shade).
- **First branch / fork height:** low — multi-stemmed from a wide root crown; **foliage
  carried in the upper ½–⅔, lower stems visibly bare/leggy** (confirmed across North Woods
  frames 225/228/232/400 — shade form: open, see-through at the base, mass held aloft).
- **Branch character:** primary stems **arch** (not straight-out radial); secondaries
  **droop and layer** into soft overlapping masses (frame 232: arching multi-stem with
  layered foliage above a leggy base); zigzag (sympodial) twig pattern; fine, airy in shade.
- **Asymmetry:** strongly irregular/lopsided in shade as stems reach for light gaps — wide
  envelope (§7).

> **The named failure (do not repeat):** `make_spicebush()` currently builds "5–8 stems
> leaning **strongly outward** to form a **vase shape wider than tall**" (lines 894–897, 905)
> — that is the V the user flagged. Replace the straight outward-lean rule with **arch +
> droop + layer into a mound** (method §1; redesign §7).

## 2. Interaction — how it meets its neighbors
- **Behavior in a stand:** **thicket-forming** (root-suckering colonial) — adjacent plants'
  cascading masses overlap into a continuous, layered understory thicket, not spaced specimens.
- **Target stand reading:** *a North Woods / Ramble thicket reads as overlapping cascading
  mounds, masses flowing into each other and layering front-to-back under the canopy — not a
  field of identical isolated bushes.* (Validate on a thicket capture, not one shrub —
  method §4.) **Confirmed in reference:** North Woods frames 232 & 400 (Glen Span Arch) show
  the path flanked by continuous overlapping understory shrub masses — leggy-open at the
  base, layered foliage above, thickets merging into each other. That is the target read.

## 3. Density
- **Bucket:** dappled → open/lacy in shade (airy, leggy); fuller in sun.
- **Real number:** woodland understory; CP botany ref: 2–4 m, 3 zones, dominant understory.
  (No published LAI — density bucket from habit, confirm against video.)
- **Light transmission:** moderate-to-high in the shade form (open, see-through between stems).

## 4. Detail
- **Bark / stem:** young twigs **olive-green** with pale lenticels; older stems greenish-tan
  → mature dark-brown-with-green; smooth, slender (2–3.5 cm). (Current model bark olive-brown
  base → greener tips — keep the green cast.)
- **Leaf / cluster:** obovate-elliptic, alternate, aromatic; carried along upper branches and
  layered, NOT tight tip-balls. Cards should read as drooping layered foliage, not a sphere.
- **Summer color:** medium green (spectral `(0.303,0.456,0.244)` already in generator). ·
  **Fall:** clear yellow (sun) / chartreuse-yellow (shade). · **Bloom:** greenish-yellow
  haze, March pre-leaf; red drupes fall.

## 5. Behavior
- **Wind character:** mid-flexibility — whole **arching stems bounce** moderately; drooping
  secondaries sway with a soft pendulous lag. Not stiff (oak), not a curtain (willow) — a
  springy bounce on the arching stems.
- **Seasonal timeline:** greenish-yellow bloom-haze (Mar, bare) → leaf flush (Apr) → green
  summer mound → clear-yellow fall (Oct) → red drupes revealed at leaf drop → bare arching
  multi-stem skeleton with paired buds on olive twigs (winter).

## 6. The one unmistakable thing
The **arch-and-droop cascade**: primary stems arch and secondary growth layers over itself
into a soft mounding shrub that "flows over itself." If it reads as a vase / V / radiating
star, it is wrong — that is the exact defect being fixed.

## 7. Per-instance variation envelope
*The 3 current variants look too alike ([[feedback-research-before-generator]] — the
cautionary tale is literally this plant). Widen substantially.*
- **Varies across seeds:** stem count (single-stem 1.5 m sapling → 10–12-stem 4 m mound),
  arch radius & droop amount, leggy shade-form vs fuller sun-form, asymmetry/lean, height,
  density.
- **Variant count:** raise **3 → 4–6** (confirm `undergrowth_builder.gd` variant picker
  handles >3 before committing — check, don't assume).

## 8. What this brief drives (build mapping)
- **Generator/params:** `make_spicebush()` (`scripts/make_undergrowth.py:844`) — **replace
  the outward-lean vase rule (ln 894–923) with arch-then-droop-and-layer**; add drooping
  secondaries; widen seed envelope (§7).
- **Textures:** keep spectral leaf/cluster colors + olive-green bark; cards sized to read as
  layered drooping foliage (current 0.20 m cards OK; tune placement, not raw count).
- **Builder/placement:** `undergrowth_builder.gd` — thicket density/overlap so masses merge
  (interaction §2); confirm LOD/billboard mechanism before editing.
- **Perf budget:** undergrowth budget — gain the cascade from form/placement, not card
  overdraw. Re-run `perf_gate.sh`.

## 9. Definition of Done (captures that validate this brief)
- [ ] Thumbnail reads as an arching, drooping, mounding shrub — **not a V/vase**.
- [ ] **In-game thicket capture (North Woods / Ramble)** — overlapping cascading masses,
  layered; matches the requested walk video. *The thicket is the validation unit.*
- [ ] Dense thicket shows no tiling (§7 — variants visibly span the envelope).
- [ ] Seasonal pass: clear-yellow fall, bare arching winter skeleton, March bloom-haze.
- [ ] Perf gate ×5 equal-or-better.
- [ ] User walk-around sign-off.

---
**Reference set status (2026-06-11):** COMPLETE enough to model. Habit (arch + droop +
layered mound), leggy shade-form base, and thicket interaction are confirmed from the
user-supplied North Woods walk (`250HlDgDVNw`, spring leaf-out) + authoritative form/season.
**Remaining gap (non-blocking):** the bare-stem **winter skeleton** in context — spring
footage can't show it; modeled from the authoritative olive-twig/paired-bud description. A
late-fall or winter North Woods walk would refine the winter state but does not block
habit-first geometry (the named-failure fix is the cascade, which is now referenced).
