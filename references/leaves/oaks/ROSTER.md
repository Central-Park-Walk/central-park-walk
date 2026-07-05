# Oak Pipeline — Roster & Scope (Phase 0 outcome)

Durable record so each phase is resumable from disk alone (context is cleared between
phases). Plan of record: `docs/oaks prompt.txt`.

## Phase 0 sign-off (Chris, 2026-06-24)

- **Turkey oak (Q. cerris)** — section **Cerris**, European; NOT *Q. laevis* (American
  scrub oak). **Populous park oak: 356 individuals, 3rd most populous** (Central Park Entire
  field survey, 2013 — see Data provenance below). Absent from the on-disk NYC Street Tree
  Census only because that dataset excludes the park interior — NOT because it is rare.
- **Add Sawtooth oak and every oak currently in the census** to the research set.
- **Pin and red MAY diverge at the skeleton level** (not just leaf textures).
- **Purpose of the research step (Phase 2):** decide *which skeletons* and *which
  textures* to build to best represent the park's oaks **within a 3060 Ti rendering a
  forest at >45 fps @ 1080p**. **If a difference can't be portrayed noticeably at
  gameplay distance, consolidate.** Distinct vs shared is a per-LOD-tier call.
- Pin/red MUST be untangled: the live `oak` model is **named pin, parameterized red**
  (`generate_trees_mtree.py:537` "Pin Oak (Quercus palustris)" but red-oak crown params).
  `scripts/make_oak.py` ("Red Oak") is a **dead standalone** (the oak analog of the
  superseded `make_london_plane.py`) — do not trust/edit it.
- Worked template to copy = **london_plane** (only species on the new cluster-card
  skeleton method), NOT cathedral_elm (which `tree_model_redesign.md` §11 still implies).

## Constraint (Chris, 2026-06-24): ONE variant per skeleton per size tier
London plane has **7 variants per size tier** and is hitting impostor difficulties;
Chris + another session are testing whether **one variant** makes impostors work. Until
london plane has a good full LOD set, **oaks plan for ONE variant of each skeleton per
size tier** (not the 5–8 seed envelope `tree_model_redesign.md` §4 describes).
Implications folded into Phase 2:
- Every distinct skeleton / leaf card is now a **flat un-amortized tax** (no variant
  spread to dilute it) → **stronger bias to consolidate** when a difference isn't legible.
- Intra-species crown variation must come from **runtime per-instance transforms**
  (yaw, non-uniform scale, slight lean) + color/phenology jitter — NOT seed variants —
  for now. A one-variant stand risks visible cloning; note it as accepted-temporary.
- Revisit variant count once london plane's impostor path is settled (may reopen 5–8).

Phase 1 schema: **PROPOSED** 2026-07-04 (re-run, 3-oak scope; `SCHEMA.yaml`). NOT frozen —
awaiting Chris approval. (Supersedes the 2026-06-24 7-taxon freeze.)

## Research roster — 3 oaks (per `docs/oaks prompt.txt`)

Park-survey counts are from *Central Park Entire* (2013) — see Data provenance.

| key (dossier file)      | common       | binomial          | section  | park count (2013) | basis |
|-------------------------|--------------|-------------------|----------|-------------------|-------|
| `oak_pin.yaml`          | Pin oak      | Quercus palustris | Lobatae  | ~half of 2,854 (most populous) | dominant park oak; zone lists + scatter |
| `oak_red.yaml`          | Red oak      | Quercus rubra     | Lobatae  | 584 (2nd)         | Lobatae baseline; highest on-disk scatter weight |
| `oak_cerris.yaml`       | Turkey oak   | Quercus cerris    | Cerris   | **356 (3rd)**     | populous park oak → **distinct geometry** (not accent, not a sawtooth re-skin) |

*Superseded (out of 3-oak scope, dossiers archived → `_superseded_7taxon/`):* scarlet
(*Q. coccinea* 16), white (*Q. alba*), swamp white (*Q. bicolor*), sawtooth
(*Q. acutissima*).

## Data provenance — TWO datasets, keep distinct (2026-07-04 audit; never collapse)
- **NYC Street Tree Census** — the ON-DISK data (`convert_to_godot.py` SPECIES_MAP +
  `park_data.json`). Maps STREET trees, **EXCLUDES the Central Park interior**, aggregates
  *Quercus* to genus (**2,613**, `:1457`) with **no per-species oak count**. The on-disk
  per-species split is hand-authored **scatter weights**, not counts.
- **Central Park Entire** — Ken Chaya & Edward Sibley Barnard, *Central Park Entire: The
  Definitive Illustrated Map* (2013): 19,600+ trees / 173 spp field-mapped over 2 yr.
  Oak breakdown **2,854 oaks / 18 spp** via Roderick Cameron, "A New Map of New York's
  Central Park," International Oak Society, 2014-05-25:
  https://www.internationaloaksociety.org/content/new-map-new-york%27s-central-park —
  pin ≈half, red 584, **Turkey 356 (3rd)**, willow/black 100+, etc. Independent field
  ground-truth (not modeled); a 2013 point-in-time census (predates later loss/planting).
  **This is the source for the per-species fidelity call, NOT the street census.**

## Consolidation hypotheses to test in Phase 2 (not yet decided)
- **Lobatae** (pin/red/scarlet): likely one leaf-card family (bristle-pointed lobes),
  but pin's excurrent/central-leader habit vs red's rounded decurrent crown may need
  two skeletons. Scarlet ≈ pin or red on habit — TBD.
- **White group** (white/swamp white): rounded-lobe leaf card, distinct from Lobatae;
  habit broad/spreading. Two taxa, probably one skeleton + one leaf card.
- **Cerris** (Turkey oak, standalone in the 3-oak scope): bristle-toothed narrow leaf card;
  **its own distinct skeleton** (large *Q. cerris*) — justified by the 356/3rd-most-populous
  park count, not consolidated. (Sawtooth, the other Cerris oak, is archived out of scope.)

## Reference data
- `reference_photos/pin oak/` is a **mixed-oak grab-bag** (cerris, pin, red `redoak_09`,
  shingle, generic 3D renders) — sort per species before building Phase 2 image manifests.
</content>
</invoke>
