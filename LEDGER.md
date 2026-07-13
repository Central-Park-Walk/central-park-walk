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
