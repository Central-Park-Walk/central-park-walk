# Leaf-Back Skeleton — Autonomous Three-Role Iteration Pipeline

> **Purpose.** Move the London-plane leaf-back skeleton work from manual human-in-the-loop
> iteration (Engineer + advising Claude + Chris every cycle) to a **reduced-supervision**
> autonomous loop of three procedurally-separate roles. Chris and the advising instance step
> back and review at **checkpoints**, not every cycle. **Date opened:** 2026-07-07 · Opus 4.8 (1M).
>
> This file defines the *machine*. It is not the design spec (that is the Planner's
> `leafback_tree_planner_spec.md`) and not a critique (those are `leafback_critique_<iter>.md`).

## The three roles (kept conceptually AND procedurally separate)

Each role runs in its **own agent context** and produces a **written artifact the next role
consumes** — the separation is real, not a self-review relabelling. Mechanism in this
environment:

| Role | Who runs it | Reads | Writes (the handoff artifact) |
|------|-------------|-------|-------------------------------|
| **1. Tree Planner** | a dedicated sub-agent (fresh context) | the prototype docs + latest Critic critique | `docs/leafback_tree_planner_spec.md` (single living spec) |
| **2. Image Reader / Critic** | a dedicated sub-agent (fresh context, reads the PNGs + reference photos) | Engineer's render set + metrics + the Planner spec + reference photos | `docs/leafback_critique_<iter>.md` (one per iteration) |
| **3. Engineer** | the main orchestrating instance (normal capacity) | the Planner spec + latest critique | code in `tmp/`, metric output, render set; a submission note appended to the critique input |

**Why sub-agents for Planner and Critic:** the point of the exercise is that the roles do not
collapse into one another. A fresh-context Planner cannot be tempted to "fix the defect in code"
(it has no code-writing mandate and does not see the generator internals unless it asks); a
fresh-context Critic cannot rubber-stamp its own prior metric reasoning because it never saw it —
it judges pixels against the spec and the reference photos only. The Engineer (this instance)
never overrules the Critic's visual verdict with metrics.

## The artifact flow (one iteration)

```
                    ┌─────────────────────────────────────────────┐
                    │ Planner spec  leafback_tree_planner_spec.md  │ (living; version-stamped)
                    └───────────────┬─────────────────────────────┘
                                    │ consumed by
                                    ▼
   ┌──────────┐  implements   ┌───────────┐  render set + metrics   ┌──────────┐
   │ Engineer │──────────────▶│ tmp/*.py  │────────────────────────▶│  Critic  │
   └────▲─────┘   against spec └───────────┘   (PNGs + measure out)  └────┬─────┘
        │                                                                 │
        │  FAIL w/ specific defects  ◀───────────────────────────────────┘
        │       └─ Engineer fixes & re-submits (next iteration)     writes
        │                                                    leafback_critique_<iter>.md
        │  "needs a design decision, not just a defect fix"                │
        └──────────────▶ escalate to Planner (spec revision) ◀────────────┘
                                                                   PASS ⇒ perf gate ⇒ converged
```

- **Engineer → Critic:** the Engineer runs the established metric checks
  (`leafback_trunkscaffold_measure.py`: valence, sibling angle, elbow bend, long-edge scan,
  node-collapse/min-edge, reachability, trunk taper, near-trunk density profile), renders in the
  **standard framings** (`leafback_trunkscaffold_render.py`: crown ×3 at az [0,60,120]°, trunk→
  scaffold transition ×2, two near-trunk "from trunk" shots, one "look up" money shot), and hands
  the Critic the PNG paths + the raw metric printout + a one-paragraph submission note.
- **Critic → Engineer / Planner:** verdict is **PASS**, **FAIL (specific defects)**, or
  **AMBIGUOUS (needs render angle X)**. FAIL with a defect the Engineer can fix without a design
  choice → Engineer fixes. FAIL/observation that implies a *design* question (e.g. "should apex
  get its own leader-continuation origin?") → **escalate to the Planner** to revise the spec, do
  not guess.

## The loop and the stopping condition

1. Engineer implements/renders against the **current** spec version.
2. Critic reviews → PASS / FAIL / AMBIGUOUS.
3. On FAIL: Engineer fixes (defect) **or** Planner revises spec (design decision). On AMBIGUOUS:
   Engineer re-renders the requested framing (not a new iteration number — same submission).
4. Repeat.

**Converged when BOTH hold:**
- Critic issues **PASS** against the full current spec, **and**
- **Performance holds > 45 fps at full forest density** on the reference benchmark positions —
  measured with the existing gate `scripts/perf_gate.sh` (real park `--park --all-london-plane`,
  6808 trees) at the two woodland positions **ramble** and **north_woods** (the 45 fps floor from
  `docs/vision.md`; the perf check is only meaningful once a skeleton is wired into generation, so
  it is run at/near convergence, not every iteration — see §perf below).

## Checkpoints (reduced supervision, NOT zero)

- **Mandatory checkpoint every 5 iterations OR every ~2 hours of wall-clock work, whichever comes
  first.** Produce a short **digest for Chris**: current spec version, current defect list, what
  changed since the last checkpoint, and the single most recent render set. **Pause for explicit
  go-ahead before continuing.**
- **20-iteration hard stop:** if 20 iterations pass without a PASS, stop and write a plain
  assessment of what is *fundamentally* unresolved (not another tuning note), for a human decision.

## Performance gate (how, and when)

- The generator is a **skeleton** stage; performance is only measurable once a candidate skeleton
  is baked into a tree model and placed at forest scale. So the perf gate is a **convergence
  gate**, run when the Critic is at or near PASS, not on every visual iteration.
- Procedure: wire the candidate generator into the tree build, regenerate the london_plane model,
  run `scripts/perf_gate.sh` (default REAL-PARK scene, 6808 trees), read median FPS at **ramble**
  and **north_woods**. Both must be **> 45 fps**. Node/edge count vs the current committed skeleton
  is tracked every iteration as a cheap early-warning proxy (skinning geometry ∝ node count).
- A skeleton that PASSes visually but busts the perf floor is **not converged** — it goes back to
  the Engineer (simplify) and, if simplification changes the design intent, to the Planner.

## Scope discipline (carried over — binding)

- **Design docs before code.** The Planner spec precedes any generator change.
- **Isolated new files** in `tmp/` (gitignored). The generator line C lives in
  `tmp/leafback_trunkscaffold*.py`.
- **Never modify a protected/shared file** without an explicit note: `leafback_graph.py`
  (`build_graph` attractor cloud), `leafback_graph_v2.py` (merge line A), `leafback_spacecol.py`
  (line B), and the three shared mesh functions in `scripts/generate_trees_mtree.py`
  (`clean_degenerate_geometry` / `enforce_min_twig_diameter` / `stitch_bark_islands`) stay
  untouched unless a **specific deficiency** is found and noted.
- **Nothing committed until a human reviews it.** All artifacts stay uncommitted in the working
  tree; the checkpoint digest is where a human decides what (if anything) gets committed.
- **Full honest reporting** of residual defects — never reconcile a visual failure away with a
  passing metric.

## Iteration ledger

| iter | spec ver | Engineer change | Critic verdict | perf | notes |
|------|----------|-----------------|----------------|------|-------|
| 1 | v1 | baseline: current line C, unchanged (metrics reproduced from actual measure output) | **MARGINAL PASS** — no blocking visual AC failed (AC-1…AC-7 ✓); AC-8 unmeasured (deferred) | not run | `leafback_critique_iter1.md`. Escalation → Planner (RESOLVED): spec gap on primary-limb **caliber**. Owner guidance: caliber is a life-stage/age property in the data (DBH budget + acropetal age gradient + bucket = life stage). → **spec v2, new blocking AC-14**. |
| 2 | v2 | ⚠ **PASS RESCINDED — Critic failure, see `leafback_critic_protocol.md`** (Critic missed a visible near-closed loop + a disconnected branch in `growth_crown_view1/2` it had read). Verdict below is INVALID pending re-review under the repaired protocol. · growth-order **capacity-constrained** crown partition (`partition_mode="growth"` in `leafback_trunkscaffold.py`): each primary's target tip-count ∝ (attractors-above-attachment)^(p/2) — the da Vinci area-above budget mapped through the pipe exponent, so base radius emerges ∝ √area with **no tuned steepness**. Pipe model + `_finish` unchanged; twigs stay at uniform r0 (thick low limb = more ramified, not fat twigs). Fast AC-14 metric check ran BEFORE render (owner instruction). | ~~PASS~~ → **CORRECTED: FAIL** (AC-5). Original PASS was a **Critic-process failure** (missed a real mesh disconnection); rescinded and re-reviewed under the repaired protocol (`leafback_critique_iter2_rerun.md`). Post-mesh integrity diagnostic (`leafback_integrity_diag.py`): **rendered mesh = 3 components → 2 disconnected orphan pieces** (190v @(-1.8,6.5,2.0); 169v @(3.0,7.0,1.5)) — a **blocking AC-5 FAIL**. The apparent "loop" is a **projection artifact** (near-loop=0; top-down shows no ring) — NOT a defect. AC-14 caliber looks improved but is **held, not cleared** (a visible break cannot PASS). | not run (needs integration) | `leafback_critique_iter2.md` (original, invalid) + `leafback_critique_iter2_rerun.md` (corrected). **AC-14 metrics:** lowest primary 0.34→**0.60·r_base** (band 0.55–0.70), gradient inverted→**monotone-decreasing** (115,117,102,77mm), primary/secondary 3.94→**4.42×**, reach 93.3%, nodes 1037→974. Renders `_growth_*`. Top residuals (non-blocking): secondary/twig tier compressed (1.35×); arcy read still mild (AC-9/11). **Near convergence — only AC-8 perf gate remains; needs wiring line C into shared generation → CHECKPOINT for Chris.** |
