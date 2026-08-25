# Sculpting Knowledge Bases — DESIGN

**Status:** DRAFT 2026-08-25 — awaiting Chris sign-off (canonical design change: new KB umbrella).
**Owner thread:** cpw / tree-sculptor. First KB: `botany/`. Future KBs (rock, water-edge,
man-made, …) are siblings under `docs/sculpt_kb/` as we learn to sculpt them.

## Purpose

Give any session a **retrieval-grounded eye**: judgments about sculpted botany are made by
comparison against known-good exemplars and their measured geometry — never from imagination.
Precedent: the music KB (`~/docs/music/`) — grep-able topics, `PRINCIPLES.md` read before the
craft is practiced, staged lessons distilled after each shipped unit.

## Foundational stances (from the 2026-08-25 design conversation)

1. **Treeness is categorical, not graded.** The human verdict is an instant tree/not-tree
   classification. The KB never produces a "treeness score"; ranking within the fail region
   invites polish where only structural jumps cross the cliff (AVO lesson). The two useful
   judge outputs are the **binary verdict** and the **named giveaway**.
2. **Exemplars are MESH ground truth, not image ground truth.** Human-sculpted models that
   pass Chris's instant look are geometry we can measure exactly (skeleton + distributions).
   The acceptable-value **envelope is derived from exemplars**, never dialed by hand —
   simulate-the-process applied to aesthetics. Generalizability tell: one envelope must
   constrain any deciduous tree; a value that only fits one exemplar is noise.
3. **Two gates, in order.** Gate 1 = treeness (generic, envelope-checkable). Gate 2 =
   species-ness (London plane vs generic deciduous; botany refs + photos). Gate 2 is
   meaningless until Gate 1 passes. The 44-iteration failure conflated them.
4. **Features may FAIL a sculpt, never CLEAR it.** The envelope is a cheap pre-filter that
   kills out-of-envelope iterations before an eye is spent. Chris's glance (or a blind
   fresh-context look) holds the only PASS authority. Verdicts are **per viewing condition**
   (20 m / 40 m / impostor range) — the cliff is distance-dependent (LEDGER 47).

## The unit: a SPECIMEN CARD

One tree, all modalities aligned, in `botany/specimens/<id>/`:

- `card.md` — species, age/tier, source + **license** (record always; distributable-license
  required only if an asset ever ships), Chris verdict + conditions, giveaways/notes.
- `photos/` — multiple angles; leaf-on and leaf-off where available.
- `mesh/` — the GLB + extracted skeleton (curve or JSON polyline set).
- `stats.json` — measured distributions: branch angles by order, child/parent radius ratios
  (pipe model), taper continuity, internode spacing, tortuosity, crown dims/occupancy.
- `renders/` — (a) Blender turntable contact sheet; (b) **in-game captures through the real
  pipeline** (LODs, cards, impostors) at the standard distances, deterministic capture
  protocol (`--cloud-seed`, `--diag-hide=cloudshadows`, `--screenshot-file`).
- `correspondence/` — color-coded sheets: skeleton rendered with branch orders in flat
  colors beside the matched photo/render view, annotated part-to-part.

Cards cover both **exemplars** (pass-side ground truth: human sculpts, and photo-only cards
for species reference) and **our own iterations** (fail-side, with the giveaway named — the
failure lineage is data too).

## The pooled layer

- `botany/ENVELOPE.md` + `envelope.json` — feature envelopes pooled across pass-side
  exemplars; each feature names its source specimens. This is Gate 1, mechanical.
- `botany/PRINCIPLES.md` — durable sculpting rules, distilled. Read before any botany
  sculpting session (rule to be added to CPW `CLAUDE.md` once the KB has content).
- `botany/TRANSLATION.md` — photo→in-game translation notes: what the pipeline does to
  foliage (card confetti onset distance, shell-hug, alpha dithering, impostor flattening…),
  each claim backed by a paired same-specimen photo/capture.
- `botany/16_lessons.md` — staging ledger; `/distill` promotes into PRINCIPLES/ENVELOPE.

## Capability → mechanism map

| Wanted | Mechanism |
| --- | --- |
| photo → mesh | nearest specimen card → its skeleton + stats.json |
| mesh → photo | compute stats → match envelope → that specimen's photo set |
| how it looks in 3D | GLB + turntable sheet on the card |
| photo → in-game prediction | paired same-specimen photo/in-game renders + TRANSLATION.md |
| part ↔ part | correspondence sheets (order-colored skeleton beside photo) |

A KB gives **retrieval, not perception** — it replaces "does this feel treelike" with
"compare against the nearest exemplar and read its numbers." That is the whole design.

## Build pipeline (becomes a skill once proven)

`specimen_card.py` (Blender headless): import GLB → extract skeleton → compute stats.json →
turntable + order-colored renders. Then the CPW capture protocol for in-game shots. The
procedure is a **skill, not a memory**, per the routing table — after the format survives
one real specimen.

## Pre-test v2 — the DIAGNOSIS exam (rev 2026-08-25; Chris falsified v1 pre-run)

**v1 (binary treeness vs a provenance key) is DEAD as a primary measure:** every subject —
Chris, frontier Claude, Qwen-VL — ceilings a photo / mesh-render / missculpt-render sort
(renders betray themselves via lighting/materials before treeness matters), and the real
fail-side library is thin (44 iterations ≈ one failure family). Binary detection was never
scarce: Chris does it instantly, free, with total confidence. Null pairs survive (they test
invented differences). The measured question is now his:
**how good is each model at naming WHAT is bad about a sculpted tree** — scored against
**Chris's fault lists, which are ground truth.** He is KEY AUTHOR, not a graded subject.

- **Key source A — Chris's blind fault lists on real renders** (44-lineage + current
  tiers): irreplaceable; the obvious-to-him fault may be one we have never correctly NAMED.
- **Key source B — synthetic fault injection:** break a good exemplar mesh in controlled
  known ways (taper, branch-angle uniformization, shell inflation, card overscale, density).
  Keyed BY CONSTRUCTION, unlimited items, zero labeling burden. Chris sights each once
  only to confirm the fault is visible (invisible → invalid item). Limit: synthetics can
  only contain faults we can name — source A covers the unnamed.
- **Task, two tiers per item** (+ clean control items to measure hallucinated faults):
  **T1 FREE-LIST** — name the faults, localized, ranked by salience.
  **T2 MULTIPLE-CHOICE** — his real faults + plausible distractors; pick which apply.
- **Scoring:** recall of his faults (weighted toward his #1), precision vs clean controls,
  salience rank agreement. Matching free-list wording to the key is a language task (any
  model can grade it); the perception under test is in *producing* the list.
- **THE FORK (weights vs protocol), separated by the tiers:**
  fails T1 / passes T2 → perception present, vocabulary+attention missing → scaffolding
  (the KB fault lexicon) can rescue; the KB's perceptual half lives.
  Fails T2 on faults obvious to Chris → **WEIGHTS.** No protocol fixes it.
- **If weights: the exam becomes a STANDING TRIPWIRE** — re-sat by each new model
  generation (frontier + local VL) at near-zero cost. "Technology caught up" becomes a
  score crossing Chris's ceiling, not a vibe. Why weights is plausible (honest basis):
  caption-style VLM training barely encodes within-category *quality* judgments, and
  vision tokenization destroys high-frequency self-similar detail — twig-scale structure
  dies at encoder resolution. Trees are near worst-case for current encoders.
- **Salvage either way:** the keyed fault lists = the **FAULT LEXICON** — the highest-value
  KB content regardless of any model's score.
- **Blinding (unchanged):** the assembling session never sits the exam; the key lives in a
  file judge sessions must not read.
- **Pre-registered predictions (frontier Claude, 2026-08-25, to be graded):** all subjects
  ceiling the v1 provenance sort. T1: Claude recovers coarse defect classes (confetti-,
  shell-hug-family), misses/mis-ranks the habit faults loudest to Chris. Qwen-VL markedly
  worse; ~chance on T2 beyond gross defects. Chris ceilings synthetic validation.
- **Step zero:** the grind lane's Qwen3-Coder has no vision — pull a Qwen-VL variant
  quantized for 8 GB under llama.cpp multimodal, smoke-test it, before exam day.
- **Library expansion (delegated grind):** **sonnet subagents, strictly ONE at a time**,
  each a bounded task returning a manifest (URL · license · provenance class · metadata),
  never "a topic". Audit `reference_photos/` FIRST — a per-species library already exists.
  Photos only from provenance-trustworthy sources (iNaturalist research-grade, Wikimedia
  with camera EXIF, FNA/USDA/FEIS) — ⚠ the open web is thick with AI-generated and
  rendered "photos"; ONE mislabeled pass-side item corrupts the answer key, so provenance
  class must be certain, not plausible. Exemplar meshes: CC0/CC-BY human sculpts (clean
  topology → also envelope input) plus photogrammetry scans (real-tree geometry; exam
  pass-side, poor for skeleton stats). In-app browser by default; Chris's Chrome ONLY
  where a login gates a download, on a list he approves. **Candidate exemplars stay
  UNSEEN by Chris until exam day** — he approves text lists (title/license/size), never
  turntables or previews, or his exam blindness dies at the curation table.
- **Ripening path:** captured verdicts (image + binary + giveaway, per condition) are
  stored in trainable form — the KB accumulates the dataset a future local LoRA would
  need, as a side effect of normal work.

## First unit of work (one session)

Assemble the diagnosis exam: acquire 1–2 exemplar meshes + build the fault-injection rig +
capture Chris's fault lists on the real fail-side renders + pull the VL model (step zero).
The specimen-card pipeline (below) runs only after the fork says the perceptual half is
alive; if it says WEIGHTS, the exam parks as the standing tripwire and only the mechanical
half proceeds.
THEN: ONE specimen, end-to-end: pick one free human-sculpted deciduous tree that passes
Chris's instant look → run the full card pipeline → Chris verdicts the CARD FORMAT (not
just the tree). Prove the format before scaling. Cost announce: Blender + Godot captures.

## Non-goals

- No treeness score, ever. No image-ML, no training. No scraping beyond license-recorded
  downloads. Exemplar meshes are reference material, not game assets (Gate 2 stands: none
  are credible London planes).
