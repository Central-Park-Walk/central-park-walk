# Standing Rules — project-wide, all-projects, no expiration

These are **permanent** operating rules. They are not scoped to one task, one subsystem, or one
project — they apply to every Claude, every role, every project, forever. A fresh Claude should read
these at session start (linked from `CLAUDE.md`). Adding a rule here is a deliberate act; rules leave
only by explicit decision.

---

## RULE 1 — The three roles are RESEARCHER-roles, permanently

The three-role pipeline (defined operationally in [`docs/leafback_pipeline.md`](leafback_pipeline.md))
is a pipeline of **researchers**:

- **Planner = the HEAD-RESEARCHER / Planner.**
- **Engineer = the RESEARCHER / Engineer.**
- **Critic = the RESEARCHER / Critic.**

Research is **not a phase that ended** — it is part of each role's standing identity. **Every role
reads before it acts.** The Planner researches before proposing; the Engineer researches before
building; the Critic researches before judging. A role that skips the reading is not doing its job,
regardless of how obvious the task looks.

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
