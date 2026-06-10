# Central Park Walk — Design Manual

A walk simulator set in New York City's Central Park, made to soothe.
Targets **1080p / 60fps on RTX 3060 Ti**.
**MIT licensed**, distributed free on Steam with donations.
Success = the natural environment of Central Park, faithfully interpreted in simulation.

## Read at session start
Every session begins by reading three things, in order:
1. **This file** (`DESIGN.md`)
2. **Memory** (`~/.claude/projects/-home-chris/memory/MEMORY.md`)
3. **The latest resume file** referenced in MEMORY.md's "Active project context"

Then state the session's target in one sentence before writing any code.

## Document map
*(Some of these are not yet written; they will be filled in as the manual is built out. The list is the table of contents for the full set.)*

- [`docs/vision.md`](docs/vision.md) — what this is, who it's for, what success means, what's NOT in scope.
- [`docs/architecture.md`](docs/architecture.md) — code layout, subsystem ownership, data flow end to end, debt register.
- `docs/data_pipeline.md` — OSM + LiDAR + NYC tree census → world. *(to be written; architecture.md §2 covers the summary)*
- [`docs/rendering.md`](docs/rendering.md) — measured frame anatomy, binding 16.6ms per-subsystem budgets, shadow policy, reduction plan.
- `docs/visual_style.md` — reference images, palette, lighting principles, tone, art bible. *(to be written)*
- `docs/conventions.md` — naming, file organization, shader patterns, comment policy. *(to be written)*
- [`docs/workflow.md`](docs/workflow.md) — session protocol, definition of done, iteration rules, enforcement.
- `docs/adrs/` — architectural decision records, dated and numbered. *(to be written)*
- `docs/glossary.md` — terms used across the codebase and docs (LOD0, MMI, atlas, zone, etc.). *(to be written)*

## Quality bar (non-negotiable)
- **1080p / 60fps on RTX 3060 Ti.** Per-subsystem performance budgets defined in `docs/rendering.md` are binding.
- **Faithful to source data.** Data-first, nature-first.
- **Natural environment is the priority** until v1.0; man-made is deferred to community contribution.
- **Visual changes are tested against reference images**, not against feeling. "Looks better" without a reference comparison does not count as done.

## Operating principles
- **Check, don't estimate.** If a number is on disk or in a uniform, measure it before reasoning from it. ([feedback](~/.claude/projects/-home-chris/memory/feedback_check_dont_estimate.md))
- **Diagnose before code.** Two failed iterations means the diagnosis is wrong — pause and re-investigate from evidence. ([feedback](~/.claude/projects/-home-chris/memory/feedback_think_then_code.md))
- **Definition of Done is documented** in `docs/workflow.md`. A fix is done when its DoD passes — not when it "feels right."
- **One foreground push per session**, at the end.
- **Commit after every successful edit.** Don't batch unrelated changes.
- **Performance is part of correctness.** A change that fixes visuals but breaks the perf budget is a regression.

## What this manual is *for*
This is not aspirational decoration. It is the **single source of truth** for what this codebase is supposed to be. Any change to the project's direction is a change to this manual first. Any code that contradicts this manual is wrong (one of the two needs to update). The manual exists so that any session — by me, by a contributor, by you in six months — opens with the same clear picture of what we're building and how it's supposed to work.
