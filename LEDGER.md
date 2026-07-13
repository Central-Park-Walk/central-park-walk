# LEDGER — cpw / london-plane

Append-only. One entry per unit of work: hypothesis → change → measurement → verdict.

---

## 2026-07-13 — iter-0: bind the thread (harness, not grower)

- **Hypothesis:** the grower's iterate-and-verify loop is the most expensive shape of work there is
  (context grows monotonically, each turn re-reads all of it), and it currently rebuilds its context
  from a 1400-line memory file every session. A thread with a ≤50-line STATE.md snapshot should make
  a `/clear` cheap enough to do every iteration.
- **Change:** bound the session to a new `cpw / london-plane` thread; seeded `STATE.md` from the
  running-state block at the top of `project_london_plane_crown_mould.md`. No grower code touched.
  Commit `5275fc6`.
- **Measurement:** none — this is a process change, not a grower change. Its test is whether iter-12
  can start cold from STATE.md alone without re-reading the memory file. Unverified until iter-12 runs.
- **Verdict: PENDING** (Chris to confirm the thread shape; the real check is the next session's cold start).

---

## 2026-07-13 — iter-0b: the cold start, verified

- **Hypothesis:** iter-0's real test was never "does the file look right" — it was whether a session
  that has *never seen* `project_london_plane_crown_mould.md` can pick the work up from `STATE.md`
  alone. If the snapshot lies or under-carries, a cold session will either ask a question already
  answered, or re-litigate a rail.
- **Change:** none. This session was the test instrument, not a change to the grower.
- **Measurement:** cold start after `/clear`. Three tool calls — bind, registry entry, `STATE.md` +
  ledger tail — reconstructed: the iter-11 refutation of the tip budget, the parameter-free test
  showing the two-sided caliber error survives a perfect tip count (1.36× / 0.87× / 0.68×), all
  three open defects, the six rails, and the iter-12 heartwood hypothesis. **The memory file was
  never opened.** No rail was re-litigated. The snapshot carries the project.
- **Verdict: PENDING** (Chris on the thread shape; the cold start itself is now CONFIRMED).

---
## 2026-07-13 — iter-12: HEARTWOOD = disused pipes (Shinozaki; Kubo 2022 branch thinning)

- **Hypothesis:** the pipe layer has no heartwood. Shinozaki sizes SAPWOOD by leaf area; the pipes of
  a dead branch are not reabsorbed — they stay in the stem as DISUSED pipes and wall off as
  heartwood. Kubo et al. 2022 (Tree Physiology 42:2174) predicts the whole heartwood profile from
  branch death alone, so the term costs NO new constant. If that is the missing size-dependent term,
  it must thicken `l` (a century of self-pruning) far more than `s` (15 yr, almost nothing shed).
- **Found (the real defect):** `ratchet()` summed only LIVE children into a `radius` array rebuilt
  from zero every year (`run()`), so the §5 "monotone max over history" was a **NO-OP across years**:
  a shed branch's wood *vanished* from its parent's cross-section. The trunk was pure sapwood at
  every age, and dead wood — which cannot dissolve — contributed nothing.
- **Change:** `ratchet()` now sums over ALL woody children — live ones at this year's pipe radius,
  dead ones FROZEN at the radius they carried at death (`self._r_hist`, which also makes the ratchet
  genuinely monotone across years). The sum is exactly conserved across a death: the term moves from
  the live side to the dead side. One function, no new constant.
- **Measurement** (`tmp/grower_calib_measure.py --tiers s m l --seeds 8`), DBH vs census:
      before:  s 1.96x  m 1.00x  l 0.73x   (splay s/l = 2.68x)
      after:   s 3.96x  m 2.49x  l 2.29x   (splay s/l = 1.73x)
      the heartwood MULTIPLIER per tier: 2.02x / 2.49x / 3.14x — **monotone in age.**
  ⇒ the term is REAL and SIZE-DEPENDENT, right sign, and **not a scalar** (that was the falsifier).
  It removes 35% of the two-sided splay. Re-centred on m it would read s 1.59 / m 1.00 / l 0.92 —
  `l` comes home from 0.73 to 0.92; `s` stays thick, which is defect 2 (the R_TIP floor), as predicted.
- **But it overshoots absolute girth ~2.5x**, because `DBH_CALIB` was fitted in a heartwood-free
  world. ⚠ And the implied sapwood fraction is now only 16% (m) / 10% (l) of basal area — **too
  little**: Platanus is noted for WIDE sapwood. Suspect the p=2.3 metric inflates the dead sum
  (summing disused pipes in a non-area metric is not area-conserving). See NEXT.
- **Verdict: PENDING**
