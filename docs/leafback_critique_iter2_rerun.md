# Leaf-Back London Plane — Critic Re-Review, Iteration 2 (growth partition)

**Reviewer:** Role 2 (Image Reader / Critic), adversarial stance · Opus 4.8 (1M) · 2026-07-07
**Protocol:** repaired Critic protocol R1–R7 (`docs/leafback_critic_protocol.md`), spec **v3**
(`docs/leafback_tree_planner_spec.md`). This supersedes and confirms the rescission of the original
iteration-2 PASS.

---

## OVERALL VERDICT: **FAIL**

**Reason (single sentence):** the rendered mesh contains **two disconnected orphan branch pieces**
(AC-5(iv), blocking, trace-first hard gate) — confirmed independently by the component-colored render,
the top-down orthographic render, a perspective close-up, **and** the post-mesh integrity metric
(connected components = 3). Grading of the aesthetic ACs is halted per the STEP-1 hard gate; the AC-14
caliber story does **not** clear this defect (protocol R2: a visible break is never cleared by a passing
metric, and here the metric agrees anyway).

The original iteration-2 PASS was wrong. The correct verdict on this exact render set is FAIL.

---

## STEP 1 — Integrity trace (leads; this is the verdict)

I traced every visibly-thick limb from the trunk outward on all perspective renders and, primarily, on
the two required diagnostic renders. Counts:

| Defect class | Count | Real / projection |
|---|---|---|
| (a) branch closing / near-closing a **loop** | **0 real** | apparent loops in perspective are **projection artifacts** (see resolution section) |
| (b) branch **stops mid-air**, geometry resumes across a **gap** | **2** | **REAL** (these are the two orphans below) |
| (c) **disconnected / orphan** segment (own color island) | **2** | **REAL** |
| (d) **rejoin** of two limbs | **0** | — |

**(b) and (c) are the same two pieces** — a segment that is disconnected necessarily reads as a mid-air
stop with a gap to its would-be parent. Two orphans, hard FAIL.

### Orphan 1 — RED island, upper-left crown
- **`..._diag_components.png`:** a red-colored curving segment high in the upper-left crown, a wholly
  separate color island from the tan main body. Unmistakable.
- **`..._diag_topdown.png`:** the same red segment appears on the upper-right of the top-down as an
  isolated colored strand not joined to any radial limb.
- **Metric corroboration:** one orphan piece of **190 verts near (-1.83, 6.50, 1.98)**.

### Orphan 2 — BLUE island, trunk→crown transition
- **`..._diag_components.png`:** a short blue arc floating just below/beside the trunk axis where it
  enters the crown — a second separate color island.
- **`..._diag_topdown.png`:** the same blue strand on the left side, isolated.
- **`..._growth_transition_1.png` (perspective!):** in the lower-left of this close-up sits a short
  cylinder with a **rounded free end connected to nothing** — the orphan is visible even in a beauty
  shot once you trace it. This is the "floating twig stub" the original review *saw* and wrongly
  dismissed as a low-priority twig; it is in fact a disconnected mesh piece.
- **Metric corroboration:** one orphan piece of **169 verts near (3.00, 7.00, 1.53)**.

### Post-mesh integrity metric (corroboration, per R3/R7 — not the verdict)
- **connected components of rendered mesh = 3** (PASS iff 1) → **2 orphan pieces**. Agrees with the eye.
- **near-loop proximity = 0** flagged non-twig pairs (incl. self-curl). Agrees with the projection
  finding below.

Because ≥1 disconnection was found, **the STEP-1 gate fails and aesthetic ACs are not graded to a
verdict.** (Observations retained below for the Engineer, but they do not lift the FAIL.)

---

## Is the apparent "loop" in the perspective crown views real or a projection artifact?

**Projection artifact — not a real loop.** Resolved with the two instruments the protocol requires for
exactly this ambiguity:

1. **Top-down orthographic (`..._diag_topdown.png`):** a real 3-D loop closing in the horizontal plane
   would read as a **closed ring** from directly above. It does not. The top-down shows a **radial /
   dendritic** structure — primaries sweep out from the central hub and curve around the shell, but each
   is an open arc; there is no closed circuit. The rings seen in `crown_view0/1/2` are two separate arcs
   at different heights/depths overlapping in perspective.
2. **near-loop proximity = 0** flagged pairs (post-mesh, incl. self-curl): no non-twig node comes within
   ε of a topologically-distant node — i.e. no branch curves back to *nearly* rejoin.

So I am **not** inventing a loop defect to match the process-failure narrative: the loop the earlier
protocol worried about is genuinely a projection overlap here. The **disconnection**, however, is
genuinely real — and that is the FAIL. (This is precisely the discrimination the repaired protocol was
built to make: pass the projection, catch the break.)

---

## STEP 2 — AC status (informational; gate already failed at AC-5)

Recorded for the Engineer; none of these lift the FAIL.

- **AC-5 — No structural artifacts — FAIL (blocking).** Sub-check (iv): 2 disconnected mesh components.
  This is a **mesh-stage** break (skeleton graph is connected-by-construction; the metric confirms the
  break is post-mesh), consistent with thin-twig culling / degenerate-edge cleanup severing pieces.
  Sub-checks (i)–(iii),(v) not separately failing on inspection, but moot given (iv).
- **AC-14 — Primary caliber / bold hierarchy — provisionally reads improved, NOT graded to PASS.** The
  transition and crown views do show a legible trunk→primary step-down and lower primaries reading
  heavier than upper (the metric's 0.60·r_base lowest primary, 4.42× primary/secondary, monotone-ish
  115/117/102/77 mm gradient are consistent). This is the intended iteration-2 improvement and looks
  directionally right — but a render with a visible disconnection cannot PASS, so AC-14 is **held**, not
  cleared.
- **AC-1/AC-2/AC-3/AC-4** — from the diagnostic + perspective set the central leader persists upward,
  scaffolds leave at separated heights, near-trunk reads sparse-ish with a bold hub, and density
  increases outward. All **held** pending a clean (1-component) rebake; none independently failing on
  inspection.
- **AC-9/AC-11 (known-acceptable):** primaries still read somewhat uniform in departure angle and the
  head-on frames still carry a mild meridian-arc read. Tuning residuals, not blocking.
- **AC-10 reachability 93.3 %** — above the ~90 % known-acceptable threshold; not blocking.

---

## Prioritized fix list

1. **[BLOCKING — highest priority] Eliminate the two mesh-stage disconnections.** The rendered mesh must
   be a **single connected component**. Root-cause the post-mesh step that severs the 190-vert piece
   near (-1.83, 6.50, 1.98) and the 169-vert piece near (3.00, 7.00, 1.53) — almost certainly thin-twig
   culling / degenerate-edge cleanup removing a bridging segment while leaving the graph nominally
   connected. Rebake and re-run `tmp/leafback_integrity_diag.py`; **connected-component count must = 1**
   before any re-submission. Re-ship the component-colored + top-down diagnostics so the fix is
   verifiable (a single color island; no isolated strands).
2. **[after re-gate] Re-submit for a full AC pass.** Once components = 1, the AC-14 caliber win and
   AC-1…AC-4 look positioned to clear; grade them then.
3. **[tuning, non-blocking] AC-9 emergence variety / AC-11 head-on arc** — per-scaffold emergence jitter
   + mild tropism to break the uniform-arc / meridian read.

---

### One-line handoff
FAIL on AC-5(iv): **2 real disconnected orphan branch pieces** (confirmed by component-colored,
top-down, `transition_1`, and metric components=3); the perspective "loops" are **projection
artifacts** (top-down shows radial arcs, near-loop=0). Highest-priority fix: make the rendered mesh a
single connected component, then re-submit.
