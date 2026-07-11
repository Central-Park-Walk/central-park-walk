# Critic Role — Failure Analysis & Repaired Protocol

> **Why this exists.** In iteration 2 the Critic issued a **PASS** (incl. AC-5 "no loops/rejoins") on a
> render set that contains two large, obvious defects — a branch curling into a near-closed **loop** and
> a **disconnected** branch (mid-air stop → gap → resume) — both plainly visible in
> `leafback_trunkscaffold_growth_crown_view1.png` and `_view2.png`. The Critic is the load-bearing part of
> the three-role pipeline: it substitutes for human visual review so the loop can run with reduced
> supervision. A Critic that rubber-stamps is a broken tool. This document records the evidence-based
> root cause and the repaired Critic protocol that every future species review must use. **Date:**
> 2026-07-07 · Opus 4.8 (1M). **Nothing about the generator bugs is addressed here — this is the Critic
> role only.**

## Findings (evidence, not assumption)

**F1 — The Critic reviewed the exact defective images, at full resolution. NOT a handoff bug.**
The iteration-2 Critic sub-agent transcript
(`~/.claude/projects/.../subagents/agent-a422186112f616480.jsonl`) shows it `Read` **all 8** growth
renders **including `growth_crown_view1.png` and `growth_crown_view2.png`**, plus the baseline
counterparts and the reference photos — 14 image reads, the complete set. The `Read` tool presents the
full image (verified: the advising instance opened the same two files and both defects are large and
immediately visible). So the render set was complete, correct, and actually inspected. The failure is
**judgment/process, not access or resolution.**

**F2 — The critique inspected those images but read gestalt, not topology.** `leafback_critique_iter2.md`
references `growth_crown_view1/2` by name (§2, §4), describing them as "bold arcing primaries [that] read
as structural limbs" and a "nest of arcs" — i.e. it registered the overall shape. But it explicitly
concluded "**no new loop or self-rejoin**" (§3 AC-5, §5) and did not identify the closed loop or the
disconnection. It caught exactly one unrelated anomaly — "one floating twig stub, `growth_transition_1`
lower-left" — and dismissed it as a low-priority twig. So it **saw the region and misjudged it**: it
evaluated the crown's aesthetic gestalt and never traced individual limbs end-to-end.

**F3 — AC-5(iv) was never operationalized as a concrete, enforced check. Spec-writing gap.** The spec's
AC-5(iv) offers the metric "graph is acyclic — 0 cycles" and a vague visual "no closed loop in the
wireframe." In iteration 1 the Critic *did* notice a ring, deferred to the acyclic metric, and **requested
a loop-confirm render** (top-down / component-colored). It was never produced. In iteration 2 it again
noted it wanted that render (§6) but **issued PASS without it**. The confirm step stayed a "nice-to-have,"
never a gate; a PASS was allowed while the Critic explicitly lacked evidence it said it needed.

**F4 — Structural reasons a sub-agent Critic misses this defect class (three, compounding):**
1. **Gestalt-over-trace.** LLM visual reasoning latches onto salient *global* features (here: bold
   primaries, "nest of arcs," the AC-14 success story it was asked to judge first) and under-weights
   *local* topological anomalies unless explicitly forced to hunt them branch-by-branch.
2. **Metric-over-vision inversion (the deepest cause).** The acyclic-graph metric reports "no loops" — and
   the Critic deferred to it. But the two visible defects are precisely the cases that metric **cannot**
   detect: (a) a **near-loop** — a branch that curves back to *nearly* rejoin is topologically acyclic yet
   visually closed; (b) a **mesh disconnection** — the skeleton graph is connected by construction (single
   root, every node has a parent), so a floating branch is a *mesh-stage* break (thin-twig culling /
   degenerate-edge cleanup), which leaves the graph acyclic-and-connected. The spec paired a visual defect
   class with a metric structurally incapable of seeing it, giving false comfort, and the Critic let the
   metric override its eyes — the exact inversion of the spec's own rule that **visual judgment overrides
   metrics.**
3. **Single-scale full-frame viewing** of fine tube geometry (1100²) with no component-colored, top-down,
   or cropped views — the views on which a loop or an orphan is trivial to see.

**Net:** the Critic is not incompetent at seeing — it is mis-directed. It was pointed at "grade the ACs /
confirm the caliber win," reasoned holistically, and trusted a metric that was wrong for the question.

---

## Repaired Critic protocol (general — binding for every species, not a London-plane patch)

### R1 — Integrity trace FIRST, before any aesthetic/AC judgment (hard gate)
For **each** render, before evaluating caliber, density, or any aesthetic AC, the Critic must perform and
write up an explicit **branch-tracing pass**:
> "Trace every visibly-thick limb from the trunk outward to its tip. Explicitly flag, with image location:
> (a) any branch that curves back to close or **nearly close a loop**; (b) any branch that **stops mid-air**
> with a free rounded end and geometry resuming across a gap; (c) any segment **not connected** to a parent;
> (d) any two limbs that **merge/rejoin**. State the count of each. If any are found, the verdict is **FAIL**
> (or **AMBIGUOUS** pending the diagnostic render in R3) — do NOT proceed to grade aesthetic ACs."
Front-loading connectivity prevents the salient aesthetic story from crowding it out.

### R2 — A passing metric may FAIL a render but may NEVER clear a visible defect
Encode explicitly: *"If you SEE a closed/near-closed loop, a discontinuity, or a rejoin, a passing
acyclic/connectivity/reachability METRIC does not resolve it. Those metrics measure the skeleton graph, not
the rendered mesh and not near-misses; a near-loop and a mesh break both pass them. Treat what you see as
ground truth (visual judgment overrides metrics). Never rationalise a visible anomaly as 'projection
overlap' or 'metric says acyclic' — either FAIL, or mark AMBIGUOUS and require the R3 render."*

### R3 — AC-5(iv) is a hard gate with a REQUIRED diagnostic render; no PASS with a request outstanding
If the Critic suspects any loop / near-loop / disconnection / rejoin, it issues **AMBIGUOUS** and the
Engineer must produce the disambiguating render(s) **before a PASS is possible**:
- a **component-colored** wireframe (each scaffold subtree / connected piece a distinct color) — a loop is a
  same-color ring; a disconnected piece is an orphan color;
- and/or a **top-down orthographic** wireframe — removes the projection ambiguity a perspective beauty-shot
  introduces.
**A PASS may not be issued while a Critic-requested confirm render is outstanding.** (This closes the exact
iteration-1→2 hole: requested twice, passed anyway.)

### R4 — Submissions include diagnostic views by default, not only beauty shots
The Engineer's standard render set must add, alongside the perspective crown/transition/near-trunk shots, at
least one **component-colored** and one **top-down orthographic** wireframe. Integrity (R1) is judged on
these; the perspective shots are for the aesthetic ACs. This is cheap, general tooling that makes the
hard-to-see defect class easy-to-see for every species.

### R5 — Crop the dense regions and re-inspect
After the full-frame trace, the Critic zooms/crops the densest 2–3 regions of each crown render and
re-inspects at higher effective resolution for gaps/loops/orphans (fine tubes under-resolve in a busy
1100² full frame).

### R6 — Adversarial stance
The Critic is prompted as a skeptic whose job is to **find the reason to reject**, defaulting to FAIL on any
integrity doubt — not to confirm the Engineer's success story. (Mirrors the project's adversarial-verify
pattern.)

### R7 — Defense in depth: close the metric gap so the Critic isn't the only guard
The metric suite currently reports only *graph* acyclicity/reachability, which is necessary-but-insufficient.
Add cheap Engineer-run checks (process fix, not a generator fix): **(i) rendered-mesh connected-component
count** (must be 1 — catches mesh-stage disconnection); **(ii) near-loop proximity** (flag any node whose
position comes within ε of a non-ancestor node — catches a branch curving back on itself). These give the
Critic corroborating data and stop a single missed judgment from producing a false PASS.

## Status — ADOPTED (2026-07-07, owner-approved)
R1–R7 are **binding** for every Critic review from now on. Realized as:
- **Critic prompt template:** `docs/leafback_critic_prompt_template.md` (R1–R7 baked in; every Critic
  dispatch uses it verbatim + the per-iteration submission block).
- **Spec:** `docs/leafback_tree_planner_spec.md` **v3** — AC-5 rewritten so loop/disconnection is a
  trace-first hard gate, the acyclic-graph metric is marked necessary-but-insufficient, and the R3/R4
  diagnostic renders are required before any PASS.
- **Tooling (R4/R7):** `tmp/leafback_integrity_diag.py` (Blender) — runs the connected-component count +
  near-loop proximity on the **final post-mesh/post-stitch geometry that is actually rendered** (not the
  pre-mesh graph, which is connected-by-construction and would miss exactly this defect), and emits the
  component-colored perspective + scaffold-colored top-down orthographic diagnostic renders.

Iteration 2's PASS is **rescinded**; it is re-reviewed under this protocol in
`docs/leafback_critique_iter2_rerun.md`. The generator defects themselves are diagnosed separately and
remain out of scope here.
