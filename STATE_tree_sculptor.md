# STATE — cpw / tree-sculptor · updated 2026-08-25 (post W-42 + TS-1 verdict)

**Target:** Blender sculptor → game-ready London-plane GLBs.

## What just changed
**TS-1 verdict (Chris):** the repaired overlay is a "roughly ok" trace of the
mesh — but the comparison itself is uninformative while sculpt and photo
"have nothing to do with each other." Overlay lane **PARKED** (instrument
kept for later, when sculpt and reference are close enough to difference).
**Chris endorsed the TLS+QSM route → `TS-10` is NEXT.**
Also this session (W-42): **from-scratch principle** canonized in
`CLAUDE.md` §Taste (`01a6fec`) — never buy others' solutions; grass + sky
marked NOT done; representation call = mesh models ≥1 yr, splats deferred
(watch: splat-baked mid LOD vs card-confetti, ~6 mo).

## Where we are
Compile = `build_curve_bevel_bark`. Habit = `shape_fit.py`. Overlay
instrument repaired W-41 (registration ≤1px height / ≤2px bole, tripwire in
build) — parked, not discarded. Honest habit numbers stand: spread_ratio
young 1.03 · mature 1.625 (lower bound, review camera clips) · veteran
1.328; K6 naked mast + K7 menorah/streamers confirmed real.
⚠ scipy restored to user-site (numpy 2.5.2); tip-host counts frozen
(288/1920/1260).

## Budget (post W-39 bare / cards / tip_hosts)
young **62388** / **3720** / 155 · mature **126108** / **15864** / 661 ·
veteran **141768** / **17040** / 710.

## Open work
- `TS-10` **NEXT (Chris-endorsed)** · TLS ground truth: (a) verify a usable
  open TLS/photogrammetry point cloud of a real *Platanus × acerifolia*
  exists (open forestry datasets; prior art = TreeQSM/AdTree papers — read,
  don't adopt); (b) from-scratch QSM skeleton-fitter; (c) fitted skeleton →
  sculpt armature. From-scratch principle applies: data and papers in,
  bought/borrowed solutions out.
- `TS-1` habit · PARKED with instrument intact; resume differencing only
  once a TS-10-armatured sculpt is within shouting distance of reference.
- `KB-1` exam assembly · queued (exemplars + fault-injection + Chris fault
  lists + Qwen-VL; roster Fable 5/Opus 5/Qwen-VL).
- `TS-7` crotches PASS · `TS-6` garden shipped · `TS-9` elbows deferred ·
  `TS-5` bark dial · `TS-3` impostors · `TS-4` species

## ★ ONE NEXT HYPOTHESIS
> A branch skeleton fitted to a real London-plane point cloud, used as the
> sculpt armature, fixes the habit faults (K6 mast, K7 menorah, over-spread)
> **by construction** — measured fork topology replaces invented topology.
> Gate 1 is existence: find one usable open scan before writing any fitter.

## Look at
Nothing new — no renders this session. The parked overlay sheet stays at
`tmp/tree_sculpt/habit_refs/overlay_contact_sheet.png` for the record.
