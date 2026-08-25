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

## First unit of work (one session)

ONE specimen, end-to-end: pick one free human-sculpted deciduous tree that passes Chris's
instant look → run the full card pipeline → Chris verdicts the CARD FORMAT (not just the
tree). Prove the format before scaling. Cost announce: Blender headless + Godot captures.

## Non-goals

- No treeness score, ever. No image-ML, no training. No scraping beyond license-recorded
  downloads. Exemplar meshes are reference material, not game assets (Gate 2 stands: none
  are credible London planes).
