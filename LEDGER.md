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
