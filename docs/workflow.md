# Workflow

How work happens on this project. These rules are binding, not aspirational. Where a rule can be enforced mechanically (hooks, scripts), it is — see §5.

## 1. Session protocol

1. Read `DESIGN.md`, then memory (`MEMORY.md`), then the active mission file it points to.
2. State the session's target in one sentence before writing any code.
3. At session end: update the mission file's checklist, resolve/supersede stale memories, push once in the foreground.

## 2. Definition of Done

A change is done when its class's checklist passes. "It feels right" and "the general scene looks fine" are not checklist items.

### Visual change
- [ ] **Before coding:** a written expectation — what feature changes, where on screen, in what direction (one sentence is fine, but it must be falsifiable).
- [ ] Verification tracks **the specific feature** across before/after screenshots at a named test location (not overall scene vibes).
- [ ] Where the quality bar references data or reference images, the comparison is against them.
- [ ] Perf gate run if the change touches anything rendered per-frame (shaders, instance counts, shadows, environment).

### Performance change
- [ ] **Before coding:** a profile or measurement identifying the cost being attacked. No fixing hypotheses (architecture.md §7 lists which numbers are still hypotheses).
- [ ] Before/after numbers from the perf benchmark at all 5 test locations.
- [ ] No visual regression at those locations (spot-check screenshots).
- [ ] **No fps number ships or is quoted without a tree/instance count proving the scene actually built fully.** `perf_gate.sh` logs the lod0/impostor count per location and fails a run whose count is <75% of expected — a run measuring a partial scene is worse than no number (it reads as evidence while being wrong; the 2026-07-01 "ramble 73" was a 1892-tree scene misread as the 6808-tree park for weeks). This binds to any hand-rolled capture too, not just the gate.

### Pipeline change
- [ ] Affected artifacts regenerated, runtime loads them, and one in-game spot-check at a location the data affects.
- [ ] If a binary format changed: writer and reader updated in the same commit (debt D7).

### Any change
- [ ] Committed immediately after verification (no batching).
- [ ] If it contradicts `DESIGN.md`/`docs/`, the doc is updated in the same commit — or the change is wrong.
- [ ] **Measured vs. inferred is stated explicitly in the report.** If a safety/quality claim ("perf-neutral", "sorting-safe", "identical under FSR2", "should work") rests on *by-construction* reasoning rather than a measurement, say so in those words — and measure it anyway whenever measuring is cheap. This project has been burned specifically by architecture-implies-safe reasoning that turned out false; "by construction" is a hypothesis label, not a verdict. (A single 3-sample perf run once showed a phantom +2 ms that vanished at 55 samples — cheap to check, so it got checked.)

### Vegetation model change
- [ ] Reviewed on the **Great Lawn evaluation plot** (`--eval-plot=<species>`), not by hunting park placements. Single-species mode gives a size-graded specimen row plus a natural-density stand — judge both (vegetation_modeling.md §4: the stand is the validation unit).
- [ ] Trees: walk the row backwards to check LOD tier handoffs and the impostor transition on the actual specimens (eval trees run the full census pipeline).

## 3. Iteration rules

- **Two failed iterations means the diagnosis is wrong.** Stop. Re-investigate from captured evidence (actual error output, actual pixel values, actual profiler numbers). Do not write a third fix for the same theory.
- **Check, don't estimate.** If a number exists on disk, in a uniform, or in a profiler, read it before reasoning from it. Estimating a checkable number is a process violation.
- **Research → implement what the research says.** Don't survey the right approach and then build a different one for expedience.
- A fix is verified only when the new code is confirmed to actually be loaded and running (cache cleared, scene reloaded, bake regenerated).
- **Investigate and cite before overriding a past decision — especially one recorded as deliberate or previously disproved.** When a change would reverse something memory/docs flag as intentional (e.g. impostors kept opaque for shadow-casting) or as already-tried-and-failed (e.g. the transparent-queue attempt), surface the documented reason with its citation and *stop for a decision* — do not silently re-attempt a disproved approach and re-derive why it fails. Overriding is allowed; overriding *without acknowledging the recorded reason* is the violation.
- **In-engine evidence beats narrative description.** "The crown looks darker and richer", "the handoff is smoother" is not evidence until there is an actual before/after image (or a measured pixel value) the user has looked at. A claim about how something renders is unverified until it is shown, not described.

## 4. Git discipline

- Commit after every successful, verified edit. Small commits, present-tense subjects.
- **One push per session, at the end, in the foreground.** Never background-push, never concurrent pushes.
- GitHub-facing docs (README) updated when behavior they describe changes. Exactly 4 screenshots live in the repo — the 4 README references; all others are gitignored.

## 5. Enforcement (mechanical, not memory)

| Rule | Mechanism | Status |
|---|---|---|
| Perf benchmark at 5 test locations, single-command | `scripts/perf_gate.sh` (stationary capture, last-10-sample stats, contamination detection) | **live** |
| Scene actually built before trusting fps | `perf_gate.sh` defaults to the real park (`--park --all-london-plane`, ~6808 trees), logs lod0/impostor counts per location, and fails a run whose count is <75% of expected (`PERF_GATE_LIGHT=1` for the old 1892-tree diagnostic scene only) | **live** |
| Perf gate on perf-relevant commits | run `scripts/perf_gate.sh`, quote numbers in the commit message | manual (rule binds) |
| No background push / single push | PreToolUse hook in `.claude/settings.json` denies backgrounded `git push` | **live** |
| Screenshot count = 4 | gitignore + pre-commit check | gitignore done; check to build |

Until a mechanism row says "live," the rule binds manually. When a mechanism exists, bypassing it is itself a violation.

## 6. Spending model budget wisely

Sessions on a stronger model go to architecture, diagnosis, specs, and the hardest implementation. Mechanical content work (model variants, parameter sweeps, doc formatting) is queued for cheaper sessions and must be specified well enough here and in `docs/` that a weaker model can execute it without judgment calls.
