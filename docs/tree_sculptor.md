# Tree Sculptor — Blender-native authored trees for Central Park Walk

Editable authority: `models/tree_sources/<species>.blend`

Generated products (rebuildable):
- `models/trees/<species>_sculpt_<stage>.glb`
- `tmp/tree_sculpt/review_*/*.png`
- contact sheets under `tmp/tree_sculpt/`

## Launch the shared-visible session

```bash
blender4 models/tree_sources/london_plane.blend \
  --python scripts/tree_sculpt/live_bridge.py
```

Then from another terminal:

```bash
python3 scripts/tree_sculpt/ctl.py set_stage --revision "$(cat tmp/tree_sculpt/revision)" \
  --args '{"stage":"mature"}'
python3 scripts/tree_sculpt/ctl.py move_point --revision N \
  --args '{"strand_id":"west_low","index":3,"delta":[0.2,0,0],"stage":"mature"}'
python3 scripts/tree_sculpt/ctl.py compile --revision N --wait 30 \
  --args '{"stage":"mature"}'
python3 scripts/tree_sculpt/ctl.py render_review --revision N --wait 90 \
  --args '{"stage":"mature"}'
```

Allowed ops: `create_strand`, `delete_strand`, `move_point`, `set_radius`,
`transform_system`, `duplicate_system`, `set_emitter`, `set_stage`,
`checkpoint`, `undo`, `save`, `compile`, `render_review`.

## Rebuild authored London plane sources

```bash
# all stages + variants + reviews
blender4 --background --python scripts/tree_sculpt/create_london_plane.py

# one stage review only
TREE_SCULPT_REVIEW_STAGES=mature blender4 --background \
  --python scripts/tree_sculpt/create_london_plane.py

# compile from an existing .blend
blender4 --background models/tree_sources/london_plane.blend \
  --python scripts/tree_sculpt/compile_all.py
```

## Contract

- Source strands are the bare skeleton authority. Bézier curves carry custom properties:
  `species`, `stage`, `strand_id`, `parent_strand`, `branch_order`, `role`, `card_pattern`.
- Compiler converts authored beveled Bézier strands to mesh and joins them
  (`sculpt_core.build_curve_bevel_bark`). Forks are overlapping tubes — the same
  bifurcating-tube read as the Blender viewport — not `leafback_skinner` tube+weld
  (AC-15 pinch; W-14 / W-20 two-strike) and not Skin Modifier (sausage waists).
- Authored child bases already match parent radius at attach; compile does not
  add a parent-radius shoulder sausage.
- GIMP leaf cards attach at compile from `textures/leaves/london_plane_cluster.png`
  (Chris GIMP sprig), `cards_per_cluster=1`. Crown density comes from sprig cards,
  never fine-twig bark geometry.
- Structure is judged on bare skeleton reviews (`*_bare_review.png`).
- Appearance PASS still needs the foliated sheet next to reference.
- Do NOT densify by stacking cards; densify with more secondary / tertiary strands.
- Tertiary forks are short structural bark (order 3), not fine-twig geometry.
- Path A tip web: after scaffold authoring, `tip_web.grow_envelope_tip_hosts`
  grows thin `role=tip_host` / `branch_order=4` strands from outermost scaffold
  terminals toward a habit envelope shell (`_P_M` / `_P_L` retargeted W-34 —
  see § Habit targets). Not the deprecated leaf-attractor generator. Cards
  attach only on tip hosts (`card_pattern=cluster` — dense along-branch sprig
  stations + a lateral twin per station); scaffold orders 0–3 keep
  `card_pattern=none`. Compile uses cheaper bevel on tip hosts. Host *count*
  is frozen after W-29 (two densify strikes); further canopy fill is card
  clusters along hosts, not more hosts. Scaffold wood is unfrozen for habit
  (W-33/W-34). Elbows (`TS-9`) and fine bark defects stay deferred until
  canopy reads complete. Young upward-reach scaffold redesign is a separate
  work item.
- Thick primaries (`branch_order=1`), secondaries (`branch_order=2`), and
  structural tertiaries (`branch_order=3`) use `card_pattern=none`. Cards live
  only on Path A tip hosts (`role=tip_host`, `card_pattern=cluster`), never on
  thick scaffold wood.
- Card attach pins `CARD_STEM_ANCHOR` (measured UV of the painted petiole in
  `london_plane_cluster.png`) to the tip vertex — not the UV bottom-centre.
- Sprig size is tip-local (`CARD_SIZE_MATURE` / `CARD_SIZE_YOUNG`,
  `CARD_HALF_FACTOR=1.00`): garden scales the 5 m model to 12/20/26 m, so
  oversized cards read as floating stamps even when stem-pinned.

## Habit targets (sculptor acceptance)

> **W-39 method** (Chris on W-38: automated pipeline — no hand tracing; learn
> tier shape from photo corpus, draw skeleton *to* that shape — same problem as
> Mtree). W-36/W-37 procedural fans two-struck; W-38 hand Inkscape retired.
> Tip-host *shell counts* stay frozen (W-28/W-29 densify two-struck).
>
> **W-40 ref bar** (Chris on W-39): a good lock shows the *entire* tree, alone
> or easy to separate from its environment. Nursery-with-person, incomplete
> shells, and crowns that merge into background woodland are out.

Authority:
- **Locked habit refs** (one per stage) — edit
  `scripts/tree_sculpt/habit_refs.py` `STAGE_REFS` and this table
  together:
  | Stage | File | Why |
  |-------|------|-----|
  | **young** | `Platanus_xhispanica_habit.jpg` | Alone against sky; central leader; upright oval; no person/pots |
  | **mature** | `london_plane_geograph_7338525.jpg` | Alone in open field; full leafy crown; clean sky separation |
  | **veteran** | `london_plane_geograph_7373536.jpg` | Alone on bank; bare crown against sky; heavy low scaffold readable |
- **Shape corpus** — `habit_refs.CORPUS` additional whole-tree photos;
  measured in `tmp/tree_sculpt/habit_refs/shape_corpus.json`.
- **Automated primary fit** — `scripts/tree_sculpt/shape_fit.py`:
  segment locked plate → measure envelope → raycast named primaries onto the
  silhouette (tip length is an OUTPUT). Writes
  `{stage}_shape_fit.json` + `_shape_fit.png`.
- Overlays: `tmp/tree_sculpt/habit_refs/{stage}_habit_overlay.png`
  (`python3 scripts/tree_sculpt/ref_habit_overlay.py`).
- Form model still informs botany: `docs/london_plane_growth_architecture.md` §10.

### Chris W-31 / W-40 defects (still in play until photo-match PASS)

| Stage | What fails | What is *not* the ask |
|-------|------------|------------------------|
| **Mature** | Skeleton-to-shape on *new* alone-field plate | Hand SVG; procedural fan; tip densify; cluttered refs |
| **Veteran** | Same on winter bank plate | Trunk-only / woodland-merge refs; densify |
| **Young** | Same on alone habit plate | Nursery-with-person; hand edit |

### Target shapes (falsifiable — photo identity)

**Mature** — match geograph 7338525: alone-field broad rounded crown, full
silhouette against sky (not a muffin shell, not gnarled veteran).

**Veteran** — match geograph 7373536: large alone bank tree; heavy low scaffold
into a broad bare crown against sky; crest retained.

**Young** — match `Platanus_xhispanica_habit`: alone upright oval; central
leader; laterals reach up into an open young shell (no person/pot clutter).

### Verification

```bash
python3 scripts/tree_sculpt/shape_fit.py young mature veteran
TREE_SCULPT_REVIEW_STAGES=young,mature,veteran blender4 --background \
  --python scripts/tree_sculpt/create_london_plane.py
python3 scripts/tree_sculpt/ref_habit_overlay.py
# → tmp/tree_sculpt/habit_refs/{stage}_{shape_fit,habit_overlay}.png
garden   # eye authority for foliated habit after overlay looks close
```

## Eval garden

```bash
garden   # → --eval-plot=london_plane_sculpt
         #    isosceles: young+mature near base (80 m), L/veteran far north apex
```

Production `london_plane_{s,m,l}.glb` are untouched. For those:

```bash
$GODOT --path . -- --time 13 --eval-plot=london_plane
```
