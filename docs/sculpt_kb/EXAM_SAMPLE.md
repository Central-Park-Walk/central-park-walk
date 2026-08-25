# Diagnosis exam — worked sample (item #0)

Purpose: make pre-test v2 (DESIGN.md) concrete for Chris's sign-off. **Item #0 is a FORMAT
DEMO** — it was discussed openly on 2026-08-25, so every party is contaminated on it; it is
never scored for real. A real item differs only in that the subject sees *nothing but the
image and the prompts*.

## A sitting, end to end

1. **Assembler** (one session) builds items + keys. Keys live in `exam/keys/` — subject
   sessions never read that path. The assembler never sits the exam.
2. **Subject** (fresh-context frontier Claude · local Qwen-VL) gets ONE image + the T1
   prompt. T1 answer locks before T2 options are shown (else the options leak the key).
3. **Grader** matches T1 wording to the key (a language task, perception not required),
   scores T2 mechanically. Prose beyond the required format is deleted before scoring.
4. **Chris** receives a score table (per subject × condition) + raw transcripts. Faults a
   subject names that are NOT in the key default to precision errors — unless Chris
   confirms them, which *extends the key* (this is how the fault lexicon grows).

## Item #0 (demo) — `tmp/tree_sculpt/habit_refs/mature_habit_overlay.png`

Condition: overlay QA (registration + habit) · mature tier · fail-side (our pipeline).

**T1 prompt (verbatim):** "List what is wrong in this image, most salient first. Give a
location for each fault. If nothing is wrong, say 'nothing wrong'."

**KEY (Chris, 2026-08-25 — his message, near-verbatim):**
K1 drawn lines not aligned with the photo, often not even close ·
K2 sometimes unintelligible ·
K3 fill in blanks (cover where the photo has nothing) ·
K4 leave areas uncovered (miss actual crown) ·
K5 (summary) not made with regard to the photo.
**Key extended by author confirmation (Chris, 2026-08-25 — "r4 and r5 are on-point"):**
K6 naked central mast to apex; real mature plane forks into ascending leaders ~¼ height ·
K7 near-horizontal "menorah" limbs + drooping streamer tips vs stiff ascending branching.

**Sample T1 response (frontier Claude — SIGHTED, demo only):**
R1 cyan silhouette spills beyond the photo strip on both sides, onto letterbox (scale/
aspect misregistration) · R2 upper + interior crown has no cyan while cyan floats over
sky/letterbox · R3 tips rasterize to disconnected speckle, unreadable as branches ·
R4 sculpt keeps a naked central mast to apex; photo forks into multiple ascending leaders
at ~¼ height · R5 limbs near-horizontal "menorah" hooks with drooping streamer tips vs
the photo's stiff ascending fine branching.

**Demo grading:** recall — R1→K1, R2→K3+K4, R3→K2: 4/4 named-fault families recovered
(K5 is a summary). Rank agreement: R1 first matches Chris's lead complaint. Precision —
R4, R5 were NOT in the key; **the key author confirmed both (2026-08-25) → key extended
as K6, K7 and entered into `FAULT_LEXICON.md`** — the lexicon-growth mechanic's first
real exercise. Had he denied them, they would stand as precision errors: a judge earns
credit only against ground truth, and ground truth grows only by his ruling.

**T2 (demo) — which of these apply? (his faults + distractors):**
A silhouette extends past the photo frame **[TRUE — K1]** ·
B trunk lean mismatched by ~15° [distractor] ·
C tip regions unreadable speckle **[TRUE — K2]** ·
D real crown regions have no silhouette coverage **[TRUE — K4]** ·
E foliage color is wrong for the season [distractor — irrelevant to a habit overlay] ·
F silhouette covers regions where the photo shows no tree **[TRUE — K3]** ·
G nothing is wrong [FALSE — and the clean-control catch for hallucination runs the other
way on genuinely clean items].

## What the real exam adds beyond this demo

Clean control items (measuring invented faults) · synthetic fault-injection items keyed by
construction (DESIGN.md, key source B) · per-condition cells (20 m / 40 m / impostor)
sized so differences exceed ~2·SEM · the weights-vs-protocol fork read from the T1/T2
split · re-sittings per model generation (the standing tripwire).
