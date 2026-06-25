# Oak Pipeline — Roster & Scope (Phase 0 outcome)

Durable record so each phase is resumable from disk alone (context is cleared between
phases). Plan of record: `docs/oaks prompt.txt`.

## Phase 0 sign-off (Chris, 2026-06-24)

- **Turkey oak (Q. cerris)** is added as a research variant. Section **Cerris** —
  European; NOT *Q. laevis* (American scrub oak). Not in the NYC census.
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

Phase 1 schema: **FROZEN** 2026-06-24 (`SCHEMA.yaml`).

## Research roster — 7 taxa across 3 taxonomic sections

| key (dossier file)      | common       | binomial          | section          | in census | basis |
|-------------------------|--------------|-------------------|------------------|-----------|-------|
| `oak_pin.yaml`          | Pin oak      | Quercus palustris | Lobatae          | yes | zone lists (North Woods, Ramble, Hallett) + scatter |
| `oak_red.yaml`          | Red oak      | Quercus rubra     | Lobatae          | yes | zone lists + scatter (highest oak weight, ~0.15–0.22) |
| `oak_scarlet.yaml`      | Scarlet oak  | Quercus coccinea  | Lobatae          | yes | North Woods zone list + scatter (~0.08) |
| `oak_white.yaml`        | White oak    | Quercus alba      | Quercus (white)  | yes | SPECIES_MAP common-name list (1664) |
| `oak_swamp_white.yaml`  | Swamp white  | Quercus bicolor   | Quercus (white)  | weak | genus comment (1453) only — confirm presence |
| `oak_sawtooth.yaml`     | Sawtooth oak | Quercus acutissima| Cerris           | yes | Hallett & Pond zone list + scatter (~0.05) |
| `oak_cerris.yaml`       | Turkey oak   | Quercus cerris    | Cerris           | **no — added** | art target / accent; may double for sawtooth |

All currently fold to the single runtime `oak` archetype (`convert_to_godot.py:1453`,
genus `quercus → oak`, total **2,613**). Per-species split exists only as **scatter
weights**, not true counts — the schema's abundance field carries that caveat.

## Consolidation hypotheses to test in Phase 2 (not yet decided)
- **Lobatae** (pin/red/scarlet): likely one leaf-card family (bristle-pointed lobes),
  but pin's excurrent/central-leader habit vs red's rounded decurrent crown may need
  two skeletons. Scarlet ≈ pin or red on habit — TBD.
- **White group** (white/swamp white): rounded-lobe leaf card, distinct from Lobatae;
  habit broad/spreading. Two taxa, probably one skeleton + one leaf card.
- **Cerris** (sawtooth/Turkey): bristle-toothed narrow leaf card; one skeleton likely
  covers both. Turkey-oak model may serve as the in-census sawtooth too.

## Reference data
- `reference_photos/pin oak/` is a **mixed-oak grab-bag** (cerris, pin, red `redoak_09`,
  shingle, generic 3D renders) — sort per species before building Phase 2 image manifests.
</content>
</invoke>
