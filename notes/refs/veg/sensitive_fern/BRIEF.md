# BRIEF — Sensitive Fern (Onoclea sensibilis)

> Per-species reference brief. The falsifiable target the visual DoD is judged against.
> Method: [`docs/vegetation_modeling.md`](../../../docs/vegetation_modeling.md);
> non-tree application: [`docs/undergrowth_model_redesign.md`](../../../docs/undergrowth_model_redesign.md).

- **Archetype key:** `Fern_Sensitive` — generator `make_sensitive_fern()` in
  `scripts/make_undergrowth.py:1950`; runtime `undergrowth_builder.gd` `SPECIES` **index 10**.
- **Layer:** floor / herb (coarse spreading wet-ground fern, 0.4–0.9 m)
- **Tier coverage:** n/a (single mesh + fade)
- **Brief written:** 2026-06-12 · **by:** Fable 5 (planning session)

## Reference set
Present in CP wet meadows, marshy ground, stream/pond edges (sun to part shade) per
[[reference-cp-botany-full]]; iNat CP-bbox count TO CONFIRM. Stills resolve the broad
netted-vein frond + bead-fern fertile frond; a walk video helps for the spreading patch
habit and the dramatic first-frost collapse.

- [ ] **Habit, summer mass** — iNat CP; USDA / extension
- [ ] **Frond detail** (broad triangular, deeply pinnatifid, winged rachis, **netted veins**)
- [ ] **Fertile "bead" fronds** (stiff, dark, bead-like spore clusters — persist into winter)
- [ ] **In a patch** (spreading individual fronds, see-through)
- [ ] **First-frost collapse** (the "sensitive" identity — dies instantly at frost)

## 1. Habit — how it flows over itself
- **One-liner:** coarse, **broad triangular** sterile fronds borne **individually** on
  long stalks from a creeping rhizome — spreading into a loose, somewhat sparse patch of
  separate big fronds, almost leaf-like rather than feathery.
- **Overall form:** spreading patch of individual fronds; **0.4–0.9 m.**
- **Aspect (w:h):** the *patch* is broad/spreading; each frond is a broad triangle.
- **Frond arrangement:** **separate fronds spaced along a rhizome** (NOT a vase or
  rosette) — the key habit contrast with ostrich/cinnamon/christmas.
- **Frond character:** broad triangular, **deeply pinnatifid** (lobes almost-but-not-quite
  separate, joined by a **winged rachis**), coarse; the veins form a **net** (not free) —
  un-fern-like, looks like a single big lobed leaf.
- **Asymmetry:** loose, irregular patch.

## 2. Interaction — how it meets its neighbors
- **In a stand:** spreading colony of individual coarse fronds in wet sunny/part-shade
  ground — a see-through patch, not a dense mass (you see ground between fronds).
- **Target stand reading:** a loose spread of broad, pale-green, net-veined fronds over
  marshy ground, with stiff dark "bead" fertile fronds poking up among them.

## 3. Density
- **Bucket:** medium / coarse, **see-through** (`trans=1.05` — the most translucent fern;
  fronds are thin and pale).
- **Real number:** low-moderate frond count, large individual frond area.
- **Light transmission:** high (sparse patch, thin pale fronds).

## 4. Detail
- **Rachis:** green, **winged** (the lobes connect along it).
- **Frond:** broad triangular, deeply pinnatifid, **netted venation**, pale yellow-green.
- **Summer color:** pale yellow-green (lighter than the other ferns) · **Fall:** yellow-brown
  (`fall=[0.65,0.55,0.12]`) — but really it's **killed instantly by first frost** (`green=0`).
- **Fertile fronds ("bead fern"):** separate, stiff, erect, with **bead-like dark spore
  clusters**; turn dark brown and **persist erect through winter** (the winter ID).

## 5. Behavior
- **Wind:** moderate (`flex=0.35`) — broad thin fronds flutter and twist easily.
- **Seasonal:** spring fiddleheads → broad pale fronds (summer) → bead fertile fronds
  (late summer) → **collapses at first frost** (sudden die-back, the "sensitive" trait) →
  bare ground with **persistent dark bead fronds** standing through winter.

## 6. The one unmistakable thing
The **broad triangular net-veined coarse frond** (looks like one big lobed leaf, not a
feathery fern) plus the stiff dark **bead-like fertile fronds** persisting in winter.

## 7. Per-instance variation envelope
- **Varies across seeds:** frond size, patch spread, frond count, bead-frond presence, lean.
- **Variant count:** 3 — spreading patches; set `v=3`.

## 8. What this brief drives (build mapping)
- **Generator:** `make_sensitive_fern()` — model the **broad triangular pinnatifid frond
  with a winged rachis** (distinct from the feathery ferns), borne as **separate spaced
  fronds** (spreading patch, not a vase), plus the bead fertile fronds.
- **Textures:** broad net-veined pinnatifid frond; bead-cluster fertile frond.
- **`SPECIES` row (idx 10):** `flex=0.35`, `trans=1.05`, green rachis, `fall` yellow-brown
  correct; **add `v=3`**; ensure the seasonal system does a **sudden first-frost collapse**.
- **Placement:** re-wire into `ZONE_SPECIES[7]` (Waterside) + `[8]` (Wild Meadow, wet
  parts) + marshy `[5]`/`[6]` edges, LOW-MEDIUM density (spreading patches).
- **Perf:** very translucent broad fronds = overdraw if dense; keep patches sparse,
  perf-gate after re-wire.

## 9. Definition of Done
- [ ] Thumbnail reads as sensitive fern (broad net-veined frond, NOT feathery) + bead fronds.
- [ ] **Patch capture** shows spreading individual fronds with ground visible between (see-through).
- [ ] Winter capture shows persistent dark bead fronds; first-frost collapse fires correctly.
- [ ] Dense same-species patch shows no tiling.
- [ ] Perf gate ×5 equal-or-better after placement re-wire.
- [ ] User walk-around sign-off.
