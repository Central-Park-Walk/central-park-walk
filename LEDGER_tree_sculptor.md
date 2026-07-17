# LEDGER — cpw / tree-sculptor

## WORK_PACKAGE ts-2026-07-17-sculptor-v1
- **thread:** tree-sculptor
- **classification:** MAINTENANCE + new capability (workstation)
- **hypothesis:** A visible Blender bridge + Bézier strand authority can replace Mtree/grower authorship and compile through the existing skinner/card/GLB path.
- **changed paths:**
  - `scripts/tree_sculpt/*` (bridge, ctl, core, review, create, compile, gates)
  - `docs/tree_sculptor.md`
  - `models/tree_sources/london_plane.blend` (+ `.gdignore`)
  - `models/trees/london_plane_sculpt_*.glb`
  - `tmp/.gdignore`, `tmp/tree_sculpt/*`
  - `STATE_tree_sculptor.md`, `LEDGER_tree_sculptor.md`
- **observed verification:**
  - Live bridge: revision-safe edit/undo/checkpoint/compile ACK ok with single Blender process.
  - Mature bark_connected_components=1 after junction weld.
  - Compile all five stages ~5s after card-cloud optimization (was ~10 min).
  - Contact sheets + reference overlay written under `tmp/tree_sculpt/`.
  - Dense-stand gate (240 lod0 Multimesh, shadows on, no impostor): 14→15 fps after thinning sprays 8→3; tris/mature 28724→14324.
  - Full-park `perf_gate.sh` asset-swap run: Auto-review blocked; not executed. Production GLBs left untouched.
- **deliverable:** sculptor workstation + first authored London-plane sculptures awaiting Chris appearance verdict.
- **git:** uncommitted
- **status:** awaiting_user_verdict

## Staged lessons
- Appearance gate first: sparse-card black starbursts were caught only by looking at the shipped foliated render.
- Card overdraw, not only triangle count, bounds woodland FPS; densify by secondaries, not spray multiplication.
- Blender undo rewrites scene custom props — keep revision counters outside the .blend undo stack.
