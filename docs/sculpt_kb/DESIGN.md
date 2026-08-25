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

## Pre-test — GATES the specimen-card build (added 2026-08-25)

The KB's perceptual half assumes reference material improves a judge. Test that premise
before building (blind-the-premise): a **blind, answer-keyed treeness exam, three subjects
on identical items** — local Qwen-VL · frontier Claude · **Chris**.

- **Key = provenance, not opinion:** we objectively know which images are real photos,
  human-sculpted exemplar renders, or our iterations. All three subjects are gradeable
  against it — including Chris.
- **Chris is subject AND ceiling.** Items he fails blind are invalid items or imperceptible
  conditions → excluded from model scoring. His blind pass doubles as exemplar curation:
  a "known-good" sculpt he flags not-tree is ejected from the pass side.
- **Items:** shuffled, unlabeled, per viewing condition (20 m / 40 m / impostor), few at a
  time; ringers (real photos) + **null pairs** (same render twice — finding differences in
  the null = instrument fault, any subject).
- **Response format, all subjects:** instant binary tree/not-tree + ONE named giveaway.
  No descriptions; prose is deleted before scoring. It is a treeness exam (Gate 1), not a
  London-plane exam.
- **Blinding:** the session that assembles the exam never takes it; the key lives in a file
  the judge session must not read. Chris gets held-back angles/seeds; items he would
  recognize are flagged contaminated, not pretended blind.
- **Scoring:** accuracy per condition with binomial noise bounds — cell sizes chosen so the
  differences we care about exceed ~2·SEM (instrument-resolution rule).
- **Outcomes → decisions:** local ≈ ceiling → free local judge, KB unnecessary for judging.
  Frontier ≫ local → judge stays frontier; re-run frontier WITH exemplar context to test
  the KB thesis directly. Everyone ≪ Chris → perceptual half of the KB is dead; only the
  mechanical half (envelope, per-defect detectors, shape_fit targets) proceeds.
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

Assemble the answer-keyed exam + pull the VL model (step zero). The specimen-card
pipeline (below) runs only after the pre-test says the perceptual half is alive.
THEN: ONE specimen, end-to-end: pick one free human-sculpted deciduous tree that passes
Chris's instant look → run the full card pipeline → Chris verdicts the CARD FORMAT (not
just the tree). Prove the format before scaling. Cost announce: Blender + Godot captures.

## Non-goals

- No treeness score, ever. No image-ML, no training. No scraping beyond license-recorded
  downloads. Exemplar meshes are reference material, not game assets (Gate 2 stands: none
  are credible London planes).
