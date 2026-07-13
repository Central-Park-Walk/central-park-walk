# Standing Rules — the derivations

**The rules themselves now live in `~/.claude/CLAUDE.md` and `~/.claude/rules/`,** which load
automatically into every session of every project. You do not need to read this file to *know* the
rules — you already have them.

**This file is why they exist.** It holds the derivation, the evidence, and the worked examples
behind each one: what it cost us to learn, and the specific failure that made the rule necessary.
The global file states Rule 3 in two lines; the cost of ignoring it is documented here, in full.

Read the relevant section **when a rule is actually in play** — when you're about to fit a number to
a thin anchor, or skip a paper because the task looks obvious, or let a passing metric talk you out
of a defect you can see. The compressed rule will not stop you. The story behind it might.

Adding a rule is a deliberate act; rules leave only by explicit decision. If a rule here is
generalized to all projects, promote the *statement* to `~/.claude/CLAUDE.md` and leave the
*derivation* here.

---

## RULE 1 — The triumvirate. Three RESEARCHER-roles, permanently, on every project

**Revised 2026-07-09 (Chris).** The Critic seat is **retired**; the **Advisor** seat replaces it. The
Advisor is the role formerly played by the Claude chat window, **now moved into the terminal for every
project**. This rule is self-contained: it no longer depends on `leafback_pipeline.md`, which described
one project's machinery for a strategy that has since been deprecated.

The triumvirate, used **every time, on every project**:

| seat | is | owns | does NOT own |
|---|---|---|---|
| **Researcher / Planner–Evaluator** | head-researcher | the design, the decision, and the **PASS/FAIL verdict against spec** | writing the code |
| **Researcher / Engineer** | the builder | implementation, **and the mechanical hard gate** (below) in its definition of done | the design decision; the verdict |
| **Researcher / Advisor** | Chris's seat-side companion | keeping track, explaining what is going on, **and holding its own opinions** | build authority; **PASS authority** |

Research is **not a phase that ended** — it is part of each seat's standing identity. **Every role reads
before it acts.** The Planner researches before proposing; the Engineer researches before building; the
Advisor researches before advising. A role that skips the reading is not doing its job, however obvious
the task looks.

### 1a — Why the Critic was retired, and what must NOT be retired with it

The Critic conflated **two separable functions, and only one of them was unreliable:**

- **The mechanical gate** — trace every thick limb; component-count == 1; near-loop == 0; diagnostic
  renders (component-coloured, top-down ortho) shipped by default. This function **never rubber-stamped.**
  It is what caught the real 3-component mesh disconnection.
- **The subjective visual verdict** — this is what failed, twice and characteristically: *gestalt over
  trace* (grading the overall shape, never tracing a limb) and *metric-over-vision inversion* (deferring
  to a passing metric to rationalise away a defect it could see).

**So the gate survives the role.** It moves to the **Engineer's definition of done**, where it belongs,
because it is tooling and not judgment. Binding, unchanged:

> **Metrics may FAIL a render. Metrics may NEVER clear a defect a reviewer can see.**
> Run integrity checks on the **final post-mesh/post-render geometry**, never the pre-mesh graph — an
> acyclic-by-construction graph cannot see a near-loop or a mesh-stage disconnection.

*(Full derivation: `lessons_critic_role_pipeline.md` in memory. The lesson outlives the seat.)*

### 1b — Independent adversarial review is now DISPOSABLE, not a standing seat

Retiring the Critic costs something real, and it is named here rather than papered over: the Planner now
**grades its own spec.** The old pipeline deliberately used a fresh-context Critic so that no seat could
rubber-stamp its own prior reasoning.

The replacement is **not** a standing reviewer. It is **ephemeral, per-claim verifiers**: when a finding or
a PASS is load-bearing, spawn disposable sub-agents whose only instruction is to **refute** it, and let the
claim survive or die on their verdict. Independence comes from *fresh context and an adversarial prompt*,
not from a permanent chair. A standing critic accumulates the very context that makes it agreeable; a
disposable one cannot.

### 1c — The Advisor's failure mode is AGREEABLENESS

The Advisor exists to help Chris **track and understand** what is going on, and to **say what it thinks**.
It has no veto and no PASS authority — but "no authority" must never decay into "no opinion."

- It **escalates**: a disagreement with the Planner is stated plainly, not softened into a caveat.
- It reports **what actually happened**, including what was skipped, what failed, and what is unverified.
- An Advisor that mostly agrees is **malfunctioning**, exactly as a Critic that mostly passed was.

The Critic failed by rubber-stamping renders. An Advisor fails by rubber-stamping *Chris*. Same defect,
different surface.

---

## RULE 2 — Prior art first, forever, for everyone

**Any time the HOW of anything is not obvious, check prior art BEFORE proposing, building, or judging.**
This is fundamental. It applies to all three roles (Rule 1), on all projects, with no expiration.
(This is the generalization of the `feedback_check_prior_art_first` memory note, **promoted from a
feedback note to a standing rule**.)

**Why (terse, so it is not mistaken for bureaucracy):** the leaf-back "hollow lantern" crown that cost
multiple sessions of trial-and-error was **Runions, Lane & Prusinkiewicz 2007, Figure 7** — a *named,
published degenerate case with a published fix* (shell-only attractors → sparse surface-only crown; the
fix is filling the crown volume). The understanding already existed in the literature. The only gap was
that nobody read it first. **Reading prior art first is cheaper than rediscovering solved problems by
trial and error** — often by whole sessions.

Practically: when a task reuses or extends a named/known technique, download and read the seminal
paper(s) and key follow-ons *first*, then propose. Do not draft from search-result snippets and backfill
citations afterward. (For plant/tree generation the canonical source is the Algorithmic Botany group,
`algorithmicbotany.org`; `pdftotext <paper>.pdf` then reading the text is fast.)

---

## RULE 3 — Simulate the process; let appearance emerge

**The park's method is to demonstrate not just what the world looks like, but HOW IT COMES TO LOOK THAT WAY.**
Model the process that produces a thing, and let its appearance be a *consequence*. Do not model the appearance
directly and hope the process is implied.

**Why (terse):** **a process cannot be a convincing fake; a snapshot can.** The London plane "lollipop" was a
snapshot — a crown shape fitted to a thin anchor. It read wrong from every angle, and no amount of margin-noise
or clumping could rescue it, because nothing about it had been *produced* by anything. A tree that grows right
looks right, from every angle, at every distance, at every age — because appearance is downstream of mechanism.

**Practically:**
- Anything a real tree (or river, or sward, or sky) *derives*, we derive. If a quantity is a fact about a
  history — crown depth, clear bole, primary count, trunk caliber, branch-order depth — it is an **OUTPUT**, not
  a parameter. This project has now had to learn that lesson **five** separate times (`skeleton_max_depth`,
  `cb_frac`, `N_PRIMARIES`, `DBH`, and `N_def` — below). Expect a sixth; look for it early.

### 3a — THE FIFTH INSTANCE, and why it is the subtle one: OUTPUT-not-parameter is NECESSARY, NOT SUFFICIENT

**It arrived exactly where this file said to look, and it wore a disguise: it was already an output.**

The grower's crown saturated because the economy is scale-free in tips (income ∝ tips, cost ∝ tips — they
cancel, iter-14). The missing growth term had to come from a size-dependent `N_def`. Two honest attempts,
both **correctly** derived rather than fitted, both **refuted**:

- **iter-15 — `N_def` read from the live crown volume** (`V_crown`, the convex hull of the foliage cloud).
  A genuine output, not a parameter. **But income scales with `N_def`, and income buys the extension that
  grows the crown that `N_def` is read from.** That is a **positive feedback loop measured from its own
  product**. It was unstable in both directions: the `m` crown sprawled to 466 m³, then the `l` crown
  collapsed to 62 m³. Crown growth came out **x0.77** where the census demands **~x2.7**.
- **iter-16 — `N_def` read from the self-support capacity** (`r³/lever`: built, ratcheted, paid-for wood —
  *settled and exogenous*, which is precisely what iter-15 said the fix required). **Still a runaway.**
  Refuted analytically, *before it was coded*, in one page: the pipe sets `r ∝ T^0.435` while statics
  demands only `r ∝ T^0.33`, so a cantilever capacity `r³/lever ∝ T^1.30` **grows faster than the T^1.0
  load it carries.** Feed it back and it amplifies instead of regulating.

**⇒ The rule, sharpened (now promoted to `~/.claude/CLAUDE.md` §1):** "it is an OUTPUT, not a parameter" is
**necessary but not sufficient.** An output read from the very loop it then drives is a *fifth* way to get
the same class of error, and *"settled, earned, already-built"* does not save you either. The test is the
**LOOP GAIN**: if the capacity you feed back grows faster than the load it must bound, it cannot bound it.
**Compute the gain before you code the term.** It cost one probe, not one iteration — the cheapest
refutation this project has ever bought.

**And the mechanism survived its wiring.** iter-15's refutation moved an *unrelated* open defect — the
sapling's DBH, stuck for six iterations, went 5.15x → 1.15x of census. That is the mechanism saying *the
size-dependence itself is right; my numerator is not.* The idea was kept; only its input was re-sourced.
(Full story: `lessons_refutation_discipline.md`, `lessons_null_result_instrument_fault.md`.)
- Fitting a number to a thin anchor to make a shape come out right is the failure mode. When the number is not
  measured, **name the gap** (see Rule 2) rather than fitting it.
- **This is never-ending by design.** Realism grows with our understanding of the process and with the compute
  available to run it. There is no converged "done" state — there is a mechanism that gets more right as it gets
  better understood. Treat that as the feature, not as scope creep.

**Scope:** all species, all systems, all projects. It is the design philosophy, not a tree-modelling tactic.
Worked example and its full derivation: `docs/grower_reiterate_design.md` §13.0, and the developmental part model
in `docs/london_plane_part_model.md`.
