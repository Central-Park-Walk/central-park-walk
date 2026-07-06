# Leaf-Back Mould — Bucket Validation (Upright Ovoid + Low-Forked Spread)

> **Status:** VALIDATION COMPLETE. **Verdict: GO** for pipeline migration. The
> leaf-back method (sprig fill → agglomerative inward merge, emergent hop count)
> was run unchanged at both crown-type extremes; it generalizes across the full
> adopted bucket range with **no merge-parameter changes and no degenerate cases**.
> **Date:** 2026-07-06 · **By:** Opus 4.8 (1M). Follows
> [`docs/crown_type_buckets.md`](crown_type_buckets.md) and
> [`docs/first_mould_leafback_prototype.md`](first_mould_leafback_prototype.md)
> (the Broad Dome build). **No s/m/l pipeline code was touched** — this is validation.

---

## 0. What this tested and why

The mould method had only ever run on **one** specimen — the Broad Dome bucket
(v2, H 14.4 m). Before the (expensive) migration that rewires weld values,
`card_rule_depth_keep`, and LOD handoff onto the three buckets, we wanted the same
method actually run at the two **size extremes**, which span a far bigger shape range
than anything tested: a 7–12 m young tree and an 18–28 m veteran.

**The test discipline (this is the whole point):** the **merge machinery is frozen** —
`SPRIG_SPACE 0.65`, `SHELL_THICK 1.3`, `cell0 = 2·SPRIG_SPACE`, growth `×1.55/level`,
the same pull-to-axis / pull-down laws, stop-at-4. **Only the crown envelope changes**
(H, clear-bole → fork height, aspect → half-width, and the normalized width profile),
which is exactly "no parameter changes beyond what the envelope shape dictates."
Anything else that had to move would be printed as a FLAG. **Nothing had to move.**

Script: `tmp/leafback_bucket_validation.py` (builds all three + renders);
`tmp/leafback_edge_sweep.py` (7→28 m boundary sweep). Stats:
`tmp/leafback_bucket_validation.json`.

---

## 1. Specimens (from the adopted buckets)

Representative = bucket **centre**, envelope from the documented form fields
(`docs/crown_type_buckets.md` §2). `base = cb·H`, `CH = H−base`, `RX = aspect·CH/2`.
The normalized width profile differs per bucket by its **documented crown form** (an
envelope input, not a merge knob): ovoid widest ~0.55; dome widest ~0.50; spread
widest low ~0.33 with a fuller base (the veteran's near-horizontal low primaries).

| Specimen | H | DBH | clear-bole | aspect W/H | fork | width | profile widest |
|---|---|---|---|---|---|---|---|
| **Upright Ovoid** (bkt 1) | 10 m | ~7 in | 0.35 | 0.80 | 3.5 m | 5.2 m | ~0.55 (above mid) |
| **Broad Dome** (bkt 2, ref) | 14.4 m | 15 in | 0.30 | 1.00 | 4.3 m | 10.1 m | ~0.50 (mid) |
| **Low-Forked Spread** (bkt 3) | 22 m | ~28 in | 0.20 | 1.20 | 4.4 m | 21.1 m | ~0.33 (low, full base) |

(DBH affects only the drawn trunk cylinder, not the merge — young ~7 in, veteran ~28 in
are distribution-plausible for those heights.)

---

## 2. Results

| | Upright Ovoid | **Broad Dome (ref)** | Low-Forked Spread |
|---|---|---|---|
| sprig cards | **206** | 781 | **2865** |
| primaries at fork | **4** | 4 | **4** |
| primary sprig-load (desc) | 53/51/51/51 | 201/196/193/191 | 729/723/712/701 |
| load imbalance (max/min) | 1.04× | 1.05× | 1.04× |
| merge levels | L0–L4 (5) | L0–L5 (6) | L0–L7 (8) |
| **emergent hops** med (min–max) | **5 (3–5)** | 5 (2–6) | **8 (2–8)** |
| mean hops | 4.69 | 5.37 | 7.54 |
| degeneracy flags | **none** | none | **none** |

The Broad Dome column **reproduces last session** (781 sprigs, 4 primaries, med 5) —
same seed, same machinery, so the harness is sound.

### Structural sanity — visually confirmed
Renders: `tmp/leafback_bucket_validation.png` (plan-view wireframe, 3-panel, same style
as `leafback_v2_compare.png`), `tmp/leafback_bucket_sideelev.png` (side elevation — fork
height + primary rise), `tmp/leafback_bucket_envelopes.png` (silhouettes).

All three: **one clean trunk → fork at the documented height → exactly 4 balanced
primaries → an even sprig shell filling the envelope.** No single-sprig primary, no
lopsided merge, no collapsed or blown-out crown. The side elevations read correctly as
their forms — the ovoid is a compact high-forked upright crown, the dome balanced, the
spread a low-forked wide-spreading veteran. The three envelope silhouettes are
genuinely distinct forms, not one dome rescaled.

### Edge sweep — no cliff at either extreme
Running the frozen machinery across the whole adopted range (`leafback_edge_sweep.py`):

```
bucket @ H                cb   W/H  sprigs  prim  minLoad  hop med (min-max)
Ovoid FLOOR @7          0.35  0.80      92     4       21      4 (2-5)
Ovoid centre @10        0.35  0.80     221     4       50      5 (3-5)
Ovoid|Dome edge @12     0.32  0.90     426     4      103      5 (3-5)
Dome centre @14.4       0.30  1.00     781     4      191      5 (2-6)
Dome|Spread edge @18    0.25  1.10    1576     4      380      6 (2-8)
Spread centre @22       0.20  1.20    2843     4      704      7 (2-8)
Spread CEIL @28         0.20  1.25    4556     4     1129      8 (2-8)
```

Every height from 7 m to 28 m converges to **exactly 4 balanced primaries**, with the
smallest primary carrying **≥21 sprigs** even at the 7 m floor — nowhere near a
single-sprig degenerate. Hop median rises smoothly 4→8; max never exceeds 8. **Smooth
scaling, no discontinuity.** (The sweep uses one profile for simplicity — it tests the
*merge*'s scale-robustness, which is profile-independent.)

---

## 3. What actually happened — honest read

**The headline holds: depth is an emergent output.** Across a 3× height / 4× width
range, hop count tracked crown size with **zero parameters touched** — Ovoid 5, Dome 5,
Spread 8. A bigger crown funnels through more merge levels to reach the trunk; a small
one through fewer. This is the depth-as-output principle confirmed at the extremes, not
just interpolated near the dome.

**Two honest notes — neither is a method break, both are migration inputs:**

1. **Small-bucket depth doesn't *drop* much below the dome — its *range* narrows
   instead.** Ovoid median hops = 5, same as the dome's 5; what changes is the spread
   (3–5 vs the dome's 2–6). A compact young crown still needs ~5 merges from shell to
   trunk — it is simply more *uniform* in depth, not dramatically shallower. That is
   botanically fine (a 10 m plane genuinely has ~5 ramification orders) and it means the
   migration should **not** expect the young bucket to want a much smaller skeleton
   depth — it wants a *tighter* one. Only the 7 m floor dips to median 4.

2. **Raw sprig count scales steeply with size: 92 (7 m) → 781 (14 m) → 4556 (28 m).**
   For *skeleton derivation* this is correct and harmless (more crown surface = more
   sprigs). But the veteran's mould carries ~6× the dome's sprigs and ~50× the young
   tree's, so the **downstream card-thinning must scale per bucket** in the migration —
   `tier_fraction` + `card_rule_depth_keep` have to pull harder on Low-Forked Spread or
   its final LOD0 will carry a large absolute card count (a real geometry cost). This is
   a **tuning task on already-existing parameters**, not a gap in the method. Flagging it
   so the migration budgets for it rather than discovering it in a frame-time regression.

**No parameter had to change to force a good result.** The FLAG checks (primaries < 3,
any primary < 2 sprigs, median < 3, max > 10, load imbalance > 6×) came back empty for
all three specimens and every edge case.

---

## 4. Comparison against the Broad Dome baseline

| | Ovoid (H10) | Dome (H14.4) | Spread (H22) | trend |
|---|---|---|---|---|
| sprigs | 206 | 781 | 2865 | ↑ ~size² (surface) |
| primaries | 4 | 4 | 4 | **invariant** ✓ |
| min primary load | 51 | 191 | 701 | all ≫ 2 (no degeneracy) |
| hops median | 5 | 5 | 8 | ↑ with crown depth ✓ |
| hops range | 3–5 | 2–6 | 2–8 | widens with size ✓ |

The dome sits exactly where expected between the two extremes on every axis. Primary
count is invariant (the stop-at-4 rule holds cleanly at all scales); sprig count and
hop depth scale monotonically and plausibly. **The extremes bracket the validated
middle — they don't contradict it.**

---

## 5. Go / No-Go for pipeline migration

**GO.** The method generalizes across the full adopted bucket range (7–28 m) with no
merge-parameter fragility and no degenerate output. The two extremes — a much bigger
shape range than anything previously tested — produced structurally sane, form-correct
skeletons using the identical machinery that built the Broad Dome. The migration can
proceed on the assumption that leaf-back construction is bucket-agnostic.

**Carry into the migration (from §3, not blockers):**
- Expect the young bucket to want a *tighter* skeleton-depth range, not a shallower
  median — don't hand-set a low depth for it.
- Scale `tier_fraction` / `card_rule_depth_keep` per bucket so Low-Forked Spread's
  large raw sprig cloud thins to a sane LOD0 card count. Budget this as tuning.
- Migration scope itself is unchanged from `crown_type_buckets.md` §4 (medium: 3→3 slot
  rename + moved boundary + new form fields).

## Out of scope (unchanged)
- No s/m/l pipeline migration performed here — validation only.
- No oak work; held oak weld fix stays parked.
- No bucket changes; no generalized tooling (two more one-off concrete builds, as asked).
