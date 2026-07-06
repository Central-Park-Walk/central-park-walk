# Mtree Skeleton-Input Capability — Investigation (pre-wiring scoping)

> **Status:** INVESTIGATION ONLY — no wiring, no generation changes, clamp not touched
> (task §5 honored). **Headline: Mtree CANNOT consume an external skeleton.** Its `Tree`
> object is grown solely by executing a parametric function graph; the mesher takes that
> opaque `Tree`, not a node graph. Wiring real bucket forms therefore means the leaf-back
> skeleton **replaces** Mtree for London plane (skeleton *and* skinning), and needs a new
> skeleton→mesh path — a **substantial new subsystem, de-risked by Blender-native skinning
> + existing repo tooling**. Details + honest scope below. **Date:** 2026-07-06 · **By:**
> Opus 4.8 (1M). Follows [`smla_bucket_migration.md`](smla_bucket_migration.md) §8.

**How this was determined:** Mtree is a Blender extension at
`~/.config/blender/4.5/extensions/user_default/modular_tree`; its core is a compiled
pybind11 C++ module `m_tree 5.5.0` (`wheels/m_tree-5.5.0-…whl`). I unpacked the wheel and
**introspected the actual binding** with Blender's bundled Python 3.11 (`dir()` +
signatures on every class), plus read the addon's Python source (crown-shape formulas,
node wrappers, presets) and our own `generate_trees_mtree.py` usage. So the API surface
below is the real exported one, not inferred from our usage.

---

## Q1 — Can Mtree accept an externally-defined skeleton? **No.**

The entire public API of the `Tree` object is **three methods**:

```
Tree.set_trunk_function(TreeFunction)   # attach the root parametric function
Tree.get_trunk_function() -> TreeFunction
Tree.execute_functions()                # GROW the skeleton by running the function graph
```

That is the whole surface. There is:
- **no** `add_node` / `set_nodes` / `from_graph` / `import_skeleton` / `set_points`,
- **no** constructor taking positions or connectivity,
- **no getter for nodes either** (`get_nodes`, `get_skeleton`, `get_points` — none exist),
  so the internal skeleton is fully opaque in both directions.

A tree is assembled *only* by building a graph of **parametric generator functions** and
executing them:

| Class | Role (all parametric, no geometry input) |
|---|---|
| `TrunkFunction` | grows the trunk curve (length, radius, shape, up_attraction, resolution) |
| `BranchFunction` | grows branches (length, angle, `crown`, `gravity`, `split`, `distribution`, `flatness`, `break_chance`) |
| `GrowthFunction` | L-system-style iterative grower (iterations, apical_dominance, gravitropism, lateral_*) |
| `PipeRadiusFunction` | assigns radii by the pipe model (power, end_radius) |

Nodes are composed with `add_child(TreeFunction)` and produce geometry only when
`execute_functions()` runs the rules. **The skeleton is an emergent output of the
parametric process — there is no seam to inject a pre-built one.**

**The meshers confirm the lock.** Both take the opaque `Tree`, not a graph or point set:

```
ManifoldMesher.mesh_tree(Tree) -> Mesh      # our bark mesher (radial_n_points, smooth_iterations)
BasicMesher.mesh_tree(Tree) -> Mesh
```

So even if we wanted to keep *only* Mtree's bark skinning and feed it our own skeleton,
**we can't** — `mesh_tree` will only skin a `Tree` grown by Mtree's own functions. There
is no `mesh_from_nodes(vertices, edges, radii)` entry point.

**Conclusion:** Mtree grows skeleton and mesh together from parameters, with no separate
skeleton-input entry point at any stage. Question 2 (document the input format of such a
mode) is therefore **N/A**.

---

## Q2/Q3 — No external mode exists → what would need to be built

Because there is no injection seam, wiring real bucket forms means **the leaf-back
skeleton replaces Mtree entirely for London plane** — both the skeleton step (already
done) *and* the ManifoldMesher skinning step (which can't take our graph). We need a new
**"skeleton + radius → game-ready GLB"** path. Here is exactly what that path requires,
and which parts already exist.

### What Mtree currently provides in our LP pipeline (i.e. what we'd be replacing)
From `generate_trees_mtree.py`: `ManifoldMesher.mesh_tree(tree)` returns a `Mesh` of
watertight bark tubes carrying **per-vertex `radius` + `direction` attributes and UVs**
(`get_uvs`, `get_uv_loops`, `get_float_attribute`, `get_vector3_attribute`). Everything
after that is **already ours**: `clean_degenerate_geometry` (weld), `stitch_bark_islands`
(fuse the mesher's separate tubes at junctions), min-twig thickening, the card/leaf
placement path (reads the skeleton's `radius`/`hierarchy_depth`/`stem_id` attributes), and
GLB export via **Blender's** glTF exporter (not Mtree's). Mtree's own leaf generators
(`LeafLODGenerator`, `LeafShapeGenerator`) we mostly **don't** use — LP is on our card
path. So Mtree's real contribution is narrow: **skeleton growth + bark skinning + the
per-vertex radius/depth attributes the card path consumes.**

### The pieces of a replacement path, marked done / reuse / new

| # | Step | Status | Note |
|---|---|---|---|
| 1 | Skeleton (nodes + connectivity + hops) | **DONE** | leaf-back validated (`tmp/leafback_bucket_validation.py`) |
| 2 | Node-graph normalization | **NEW (small)** | leaf-back currently emits raw segment endpoints `(a,b,level)` + per-sprig hops — **no node IDs, no parent links, no radius**. Must dedupe endpoints → nodes, build parent/child edges, root at the trunk. Pure bookkeeping. |
| 3 | Per-node radius (pipe model) | **NEW (small)** | Mtree's `PipeRadiusFunction` is trivial to port: `r_parent^p = Σ r_child^p` (p≈2–2.5), seeded at leaf twigs. ~30 lines. |
| 4 | Skeleton → bark tube mesh (skinning) | **REUSE — Blender native** | **Not from scratch.** Blender's **Skin Modifier** skins a vert/edge graph with per-vert radius; or **Geometry-Nodes Curve-to-Mesh** bevels a circle along per-point-radius curves. Curve-bevel gives cleaner, predictable tube UVs (see #6). |
| 5 | Junction fusion (separate tubes → manifold) | **REUSE (light adapt)** | `stitch_bark_islands` + `clean_degenerate_geometry` were **written for exactly this** — fusing ManifoldMesher's separate tubes at junctions. Directly applicable to a curve-bevel/skin output. |
| 6 | Bark UVs | **NEW (moderate)** | Mtree handed us UVs. A curve-bevel tube yields predictable cylindrical UVs but they must match what `tree_bark.gdshader` expects (U around girth, V along length). This is the fiddliest new piece. |
| 7 | Min-twig thickening, degenerate cleanup | **REUSE** | exists, mesher-agnostic (operates on the Blender mesh). |
| 8 | Per-vertex skeleton attributes for the card path | **NEW (moderate)** | The card placement reads `radius` / `hierarchy_depth` / `stem_id` that ManifoldMesher wrote. We'd write these onto the new mesh ourselves (we already have radius from #3, depth = hop count from #1, stem_id from the graph). Wiring, not invention. |
| 9 | LOD mesh reduction | **REUSE / minimal** | we generate each tier independently and bake impostors separately — no Mtree LOD-decimation step to replace. |
| 10 | GLB export | **REUSE** | already Blender's exporter, not Mtree's. |

### Reusable tooling verdict
**Skeleton→mesh skinning is a solved problem** — Blender ships two native paths (Skin
Modifier, Geometry-Nodes Curve-to-Mesh with per-point radius), so #4 is **not** written
from scratch. And roughly half the downstream (#5, #7, #9, #10) **already exists in the
repo** and is largely mesher-agnostic — `stitch_bark_islands` in particular was purpose-built
for the separate-tube topology a bevel/skin also produces. The genuinely new work is the
graph+radius front-end (#2, #3 — small), bark UVs (#6 — moderate), and re-providing the
card path's skeleton attributes (#8 — moderate).

### Honest scope estimate — **substantial new subsystem, not a moderate wiring task**
This is bigger than the config migration: it replaces Mtree's core role (skeleton + bark
skinning) with an in-house path. But it is **assembling known pieces, not inventing a tree
generator** — the skeleton is validated, skinning is Blender-native, and the weld/stitch/
card/export tail already exists. Realistic shape of the work:

- **Phase A (spike, small):** leaf-back graph → pipe-radius → Blender curve-bevel → one
  raw bark mesh for a single Broad Dome specimen. Proves the skinning path end-to-end.
- **Phase B (moderate):** bark UVs matching `tree_bark`, junction fusion via the existing
  stitch/weld tools, min-twig floor — a bark mesh that reads as well as ManifoldMesher's.
- **Phase C (moderate):** write the `radius`/`hierarchy_depth`/`stem_id` attributes and
  run the **existing** card path on it; regenerate all three buckets; measure cards
  against the **real** lever (`card_rule_depth_keep`, per migration §8 Finding 1); re-bake
  impostors; verify the three forms read distinct.

**The main risk** is matching ManifoldMesher's junction cleanliness and bark-surface
quality — that mesher does non-trivial manifold work (hence our `stitch_bark_islands`
existing to patch even *its* separate-tube output). A curve-bevel path may need comparable
junction care. This is the part to prototype first (Phase A) before committing.

---

## Q4 — What the ~3.0–3.2 m width "clamp" actually is

**It is a design assumption baked into how Mtree models a crown — not a hardcoded 3.2 m
constant, and not a formula ceiling you can raise with a parameter.** There is **no
absolute-width, crown-radius, or aspect parameter anywhere in the API.**

Mtree's crown is a **normalized length-multiplier envelope**. From the addon's own
`viewport/shape_formulas.py` (a Python port of the C++ `CrownShape.hpp`):

```python
MIN_RATIO = 0.2;  RATIO_RANGE = 0.8
# get_shape_ratio(shape, ratio) returns a branch-LENGTH multiplier at height `ratio`:
Spherical:      0.2 + 0.8*sin(pi*ratio)      # widest (mult 1.0) at mid-height
Hemispherical:  0.2 + 0.8*sin(pi/2*ratio)
Conical:        0.2 + 0.8*ratio
...
```

So the crown does **not** carry a width — it carries a *shape* that scales branch length
by at most `1.0` at its widest band. `CrownParams` exposes only `{shape, base_size,
height, angle_variation}` — all **normalized/relative**; none is an absolute extent.
Consequently the tree's actual crown width is **emergent**: `branch_length × shape_ratio ×
how gravity/flatness distribute the branches × number of generations`. The widest the
normalized envelope ever reaches is multiplier 1.0, and the **aspect is fixed inside the
sin/linear formulas** (with `MIN_RATIO`/`RATIO_RANGE` hardcoded) — there is no knob to make
a crown fundamentally wider than the shape formula's built-in profile.

This matches our repo's empirical L863 finding exactly (2026-06-24: `crown_base_size`,
`up_attraction`, `branch_angle`, `length` all ~no-op on measured width) and I confirmed the
one plausible remaining lever is **already exercised**: `BranchFunction.flatness`
("Horizontal spread, 0=spherical…1=flat canopy") is set up to **0.5** across our species
(LP uses `branch_flatness 0.40`) and width still saturates ~3.2 m. So the clamp is **not**
an unused-parameter oversight.

**Why ~3.2 m specifically:** it's the horizontal reach the parametric grower saturates at
in our *stable* regime — branch length bounded, `sub_density < ~1.5` to avoid the
ManifoldMesher segfault band (documented in our code), gravity/up_attraction curling
growth vertical, and a fixed shape-ratio envelope. It is an **emergent equilibrium of the
growth model**, so it moves a little with parameters but cannot be *targeted* — there is no
input that says "make this crown 21 m wide (aspect 1.2)."

**Bearing on the decision:** even if we kept Mtree's skeleton step for something, it
**structurally cannot hit the Low-Forked Spread's aspect 1.2** — there is no aspect input
and the crown model tops out near square. This is the concrete reason the migration's
`aspect_wh` field had nowhere to plug in, and it is why "replace the skeleton" (not "feed
Mtree a target") is the only path to real bucket forms.

---

## Q5 — Compliance
No fix/bypass/route-around of the clamp was attempted; no mould wiring; no generation or
config changes. Read-only introspection + source reading only. The wheel was unpacked to a
scratchpad dir, not the repo.

---

## Recommendation (what this determines)
"Wire the mould into generation" is **not** a next-step wiring task — it is a **new
skeleton→mesh subsystem** (skeleton done, skinning Blender-native, ~half the tail reusable,
bark-UVs + attribute-wiring + junction-quality the real work). Recommend a **Phase-A spike
first** (leaf-back graph → pipe-radius → curve-bevel → one raw Broad Dome bark mesh) to
de-risk the junction/skinning quality against ManifoldMesher **before** committing to the
full build. Keeping Mtree is not an option for real bucket forms: it has no external-skeleton
input, and its crown model has no width/aspect target (Q4).

### Out of scope (unchanged)
- No wiring into `generate_trees_mtree.py`. No skeleton→mesh implementation. No oak work.
  No bucket/config changes.
