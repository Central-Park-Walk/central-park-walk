# CLAUDE.md — Central Park Walk

> # ✅ ACTIVE — resumed by Chris, 2026-07-24. (Suspended 2026-07-16; lifted.)
>
> **Trees are still the blocker, and still the only thing open.** 44 iterations produced not one credible
> London plane by any method, and that has not changed — trees ARE the project, so nothing downstream is
> worth doing first. The backlog (Ramble, perf, release, README, maple + sweetgum) stays deferred.
> ⛔ no mtree · ⛔ no SpeedTree · ⛔ no fine-twig geometry — binding, not re-opened by the resume.
> The first two are instances of the **from-scratch principle** (see Taste) — never buy or adopt
> someone else's solution to a creative problem; study it, then build our own.
> **Start from the deliverable: render a finished, foliated tree AS IT SHIPS and look at it, first.**
> Read `STATE.md` and `LEDGER.md ## 45` before the first unit of work.

A real-time 3D walking simulation of all 843 acres of Central Park, built from public
data (NYC LiDAR, OpenStreetMap, NYC Tree Census, building footprints) and interpreted by
Claude. Godot 4.6.1, Forward+, GDScript. Branch **master**. No objectives — just a place.

## Read at session start (in order)
Your standing rules — token discipline, the Triumvirate (Planner-Evaluator / Engineer / **Advisor**),
prior-art-first, simulate-the-process — load automatically from `~/.claude/CLAUDE.md` and
`~/.claude/rules/`. They are **not repeated here**, so this file can't contradict them. Auto memory
(the `MEMORY.md` index plus its topic files) loads on its own too; no path to chase.

1. **[`index_cpw.md`](../.claude/projects/-home-chris/memory/index_cpw.md)** — **THE CPW MEMORY
   INDEX. Read it FIRST.** Every CPW memory, one line each. It is deliberately **not** in `MEMORY.md`
   (4.4 KB × every tool call × every session, useful to one project), so `MEMORY.md` keeps only a
   pointer — which means **nothing auto-loads it. You must open it.**
2. **`DESIGN.md`** — the single source of truth for what this project is supposed to be.
3. **The active resume/plan** + the memory topic file for whatever you're touching — both found via
   the index above.
4. **[`docs/standing_rules.md`](docs/standing_rules.md)** — read the relevant section **when a rule
   is in play.** It holds the *derivations* behind the global rules: why the Critic seat was retired
   and what had to survive it, the published Fig. 7 that cost us multiple sessions of trial-and-error,
   and the **five** separate times this project re-learned that a derived quantity is an **OUTPUT, not
   a parameter** (§3a: the fifth was *already an output* — read from the loop it drove. Expect a
   sixth; look for it early). ⚠ **§3b — the 44-iteration lesson:** "let appearance emerge" is not
   "assume appearance emerged". **Look at the thing FIRST, rendered AS IT SHIPS.**

Then state the session's target in one sentence before writing any code.

`DESIGN.md` maps the full doc set. The binding specs (code that contradicts them is wrong,
or the doc updates in the same commit):
- [`docs/vision.md`](docs/vision.md) — scope, success, what's NOT in scope.
- [`docs/architecture.md`](docs/architecture.md) — code layout, data flow, debt register.
- [`docs/rendering.md`](docs/rendering.md) — measured frame budgets, shadow policy, perf plan.
- [`docs/trees.md`](docs/trees.md) — tree tier spec (the hardest subsystem; the authority).
- [`docs/grass.md`](docs/grass.md) — turf spec (terrain-only baked sward, §0y is current).
- [`docs/sky.md`](docs/sky.md) — cloud taxonomy, lighting, weather-state sky mapping.
- [`docs/workflow.md`](docs/workflow.md) — session protocol, definition of done.

## Quality bar (non-negotiable)
- **1080p / 60fps on RTX 3060 Ti** in open areas; **≥45fps in deep woodland** (Ramble,
  North Woods). Per-subsystem budgets in `docs/rendering.md` are binding.
- **Data-first, nature-first.** Render from data or don't render; gaps stay visible.
  Natural environment is the priority until v1.0; man-made is deferred to contribution.
- **Visual changes are tested against reference images, not feeling.** "Looks better"
  without a reference comparison is not done.

## Taste and sources (this project's, not global)
- **★ FROM SCRATCH IS THE POINT (Chris, 2026-08-25).** Never buy someone else's solution to one
  of this project's creative problems — no Grove, no SpeedTree, no asset packs; that is the real
  reason behind the mtree/SpeedTree ⛔. Finding prior art and building our own equivalent is
  encouraged; purchasing the finished answer is not. Godot itself is tolerated infrastructure,
  not an exception — Chris would replace it too once that's cheap enough. **Showing off what was
  made from scratch is the entire point of a game like this.**
- **Post-processing look:** soft contrast, naturalistic saturation, haze for depth. Keep tone
  mapping **data-driven** rather than stylized by feel.
- **Verify botany against PRIMARY sources** — FNA, USDA, FEIS, `reference_photos/`. Never against
  our own older docs: they may have inherited an error.
- **Decline deep research here** — low ROI. Reserve it for external facts we genuinely can't derive.
- **README stays concise**; only 4 screenshots in the repo.
- **Headless captures have an LOD confound** — when a headless capture and an interactive one
  disagree, **trust the interactive one**. (→ `feedback_headless_capture_lod_confound.md`)

## Operating rules
- **Investigate before you code.** State what was investigated, the evidence, the cause —
  no "likely/probably" before evidence. Two failed iterations means the diagnosis is wrong.
- **Check, don't estimate.** If a number is on disk or in a uniform, read it.
- **Verify everything.** Test the change, look at the output, clear caches before "done".
  Screenshots the user reports are ground truth.
- **Commit after every successful edit.** One **foreground** push at session end (never
  background/concurrent). Update GitHub-facing docs in the same commit.
- **Temp outputs → `tmp/`** (this repo's `tmp/` is gitignored; the user watches it live).
  Not `/tmp`, not scratchpad.
- **Keep docs + memory clean** as part of every task: trim the index, archive long logs,
  fix broken links, de-stale on sight, no duplicates.
- **Only distributable assets** ship; never require manual third-party downloads. Established
  free tooling is fine as *infrastructure*; **creative solutions are built from scratch** (see
  Taste) — the global "prefer established tools" rule yields to that principle here.

## Run it
```bash
GODOT="/home/chris/godot 4/Godot_v4.6.1-stable_linux.x86_64"   # note the space in the dir name; no godot4 symlink exists

$GODOT --path . -- --park          # walk the park
$GODOT --path .                    # NO flag → the model-evaluation garden (Great Lawn), not the park
$GODOT --path . -- --eval-plot=spicebush   # one species: size-graded row + natural stand
```
Headless captures run under `xvfb-run -a -s "-screen 0 1920x1080x24"`. After editing a
`.glsl`/shader-include or regenerating geometry, run Godot with `--import` before capturing.
Useful flags: `--pos "x,z,yaw"`, `--time noon`, `--weather rain`, `--season autumn`,
`--walk`, `--no-blades` (perf-gate the near blade band), `--particle-grass` (legacy grass).

## Build from source
`README.md` → "Build from Source" has the full pipeline (download scripts →
`convert_to_godot.py` → Mtree model generation). No paid APIs; all data is public.

## Where things live
Root `*.gd` files are the runtime (`main.gd` is the ~4.2k-line orchestrator; `park_loader.gd`
runs the builders in a load-bearing order). Python `download_*.py` + `convert_to_godot.py`
are the offline data pipeline. `docs/` is the manual. `scripts/` holds Blender/bake tools.
`reference_photos/<species>/` feeds the per-species modeling loop. `notes/` and `tmp/` are
gitignored working areas.
