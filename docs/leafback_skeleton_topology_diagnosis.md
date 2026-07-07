# Leaf-Back Skeleton Branch-Topology — Diagnosis (read-only)

> **Read-only diagnosis. No code changed, no commit** (per task). Facts pulled from
> the actual generator `tmp/leafback_graph.py::build_graph()` + a read-only analysis of
> its output (`tmp/leafback_topo_diag.py`). **Date:** 2026-07-06 · **By:** Opus 4.8 (1M).
> Follows [`leafback_skin_spike_phaseA.md`](leafback_skin_spike_phaseA.md).

## The connection mechanism, step by step
`build_graph()` (leafback_graph.py:45-70) connects points like this:

1. Sprig points are seeded on the crown shell and thinned by min-distance. Each becomes a
   leaf node with `parent = -1`.
2. **Agglomerative grid-cell merge** (the whole connection logic): loop over levels L.
   At each level, every active node is dropped into an integer **grid cell**
   `k = (x//cs, y//cs, z//cs)` where the cell size `cs = 1.30 · 1.55^L` grows each level.
   **All nodes that land in the same cell are fused to ONE new parent node** placed at
   their **centroid**, pulled toward the trunk axis (`x,z *= 1-pa`) and down
   (`y -= pd·(y-CB)`). Every node in the cell gets `parent = <that new node's id>`.
   Singletons carry up unchanged. Repeat until ≤4 active nodes remain, which are wired to
   a FORK node, then to a ROOT node.
3. A `children` adjacency map, pipe-model `radius`, and `strand` (stem_id) are derived
   from the resulting parent links.

**So: the connection is decided purely by spatial proximity — grid-cell co-occupancy at a
geometrically growing scale.** There is no growth rule, no parent-direction reference, no
branching rule. It is agglomerative proximity clustering. It *does*, however, persist a
parent index per node (see Q3). The user's visual read — "nearest-neighbor connections, not
parent-child relationships" — is essentially correct: the parent-child links exist as data,
but they are **assigned by nearness**, so they behave like nearest-neighbor connections.

---

## Q1 — Explicit parent→child hierarchy, or proximity connection?
**Both, in a specific sense.** A **persistent parent→child graph is produced** (each node
carries a `parent` index; a `children` adjacency map and `strand` ids are built from it).
But the **connection decision is spatial proximity** (grid-cell centroid merge), not a
branch rule. So the hierarchy is real as a *data structure* but **proximity-derived** in
*meaning* — "child of" = "was in the same grid cell at merge time," not "grew from."

## Q2 — Intentional branching angles, or noise/emergent?
**No intentional angles exist.** No branching-angle distribution, no phyllotaxis, no
L-system, no sibling angular spacing anywhere in the code. A segment's direction is simply
`child_pos → parent_centroid` — an **incidental byproduct of where the shell points landed
and how the centroid got pulled.** Measured child-vs-parent-axis angle over 1046 segments:
median **35°**, p25 22°, p75 52° (mass in 15-52°). This is *not* uniform-random (which
would center ~90°) — but the clustering is an **artifact of the radial merge geometry**
(everything points outward/up from the pulled axis), **not** a rule. Critically, there is
**no angular relationship between siblings**: at a fork, N children point wherever their
source points were, with no even radial distribution or common plane.

## Q3 — Hierarchy metadata present?
**Yes, fully.** `nodes[i]["parent"]` (parent index per node), the `children` adjacency map,
and `strand`/stem_id per node all persist in the returned graph. "What is this stick's
parent branch?" is directly answerable. The information is **not** lost after point
generation — it is the graph's backbone. (A fix therefore does **not** need to invent
hierarchy tracking; it can operate on the existing graph.)

## Q4 — Shared code with the committed London-plane s/m skeleton work?
**No shared skeleton-generation code — zero regression risk to committed trees.** Verified:
- `tmp/leafback_graph.py` (the skeleton generator) imports **only numpy + math**. It uses
  **none** of the Mtree path (`generate_species_tier`, `TrunkFunction`, `BranchFunction`,
  `ManifoldMesher`) that produces the committed s/m trees.
- The **only** shared code is three **mesh post-processing** functions the *spike* borrows
  from `generate_trees_mtree.py`: `clean_degenerate_geometry`, `enforce_min_twig_diameter`,
  `stitch_bark_islands`. These are **skinning/weld steps, not skeleton generation**, and are
  used by both paths.
- The committed s/m work (continuous twig distribution via `card_rule_depth_keep`; the
  5 mm `remove_doubles` weld-trap fix + `sub_start_radius 0.7`; `stitch_bark_islands`) lives
  entirely in the **Mtree pipeline + those shared mesh steps.** A topology fix to
  `build_graph()` touches none of the Mtree skeleton path. **As long as the fix stays in the
  leaf-back generator and does not modify the three shared mesh functions, it cannot
  regress the committed trunk/branch work.**

## Q5 — Worst junctions traced to source data
The three highest-valence nodes (all in the lower-mid crown, y≈5.6-6.8 m, where the
`junction0` close-up was aimed), raw from the graph:

| node | pos (m) | r | valence | children (len · angle-vs-axis · r · strand) |
|---|---|---|---|---|
| **1002** | (-2.11, 6.63, -0.78) | 44 mm | **8** | 54cm·90°·11mm·s61 · 137cm·75°·11mm·s62 · 126cm·34°·14mm·s63 · **202cm·54°·23mm·s1** · 146cm·69°·17mm·s70 · 88cm·94°·19mm·s73 · 63cm·26°·23mm·s77 · 158cm·95°·19mm·s83 |
| **1005** | (0.70, 6.79, -2.24) | 43 mm | **8** | spans 23cm→180cm, angles 10°→90°, r 11→23 mm, 8 different strands |
| **814** | (-1.64, 5.57, 0.51) | 25 mm | **7** | spans 33cm→120cm, angles 18°→125°, all-11mm twigs, 7 different strands |

What this shows concretely: a single node sprays **7-8 branches**, in **7-8 different
strands**, of **wildly mixed length (23-202 cm), angle (10-125°), and thickness
(11-23 mm)**, all from one point. That is not a fork (a limb continuing + shedding a couple
of thin laterals); it is a **burst of many comparable-thickness sticks at scattered
angles** — the literal source of the "pile of sticks" render. Real 3-D tube
interpenetration between non-adjacent different-strand segments is present but **modest**
(25 hard crossings, ~1% of nearby pairs); the dominant defect is the **high-valence
scattered-angle spray**, amplified in the close-ups by 2-D projection of a dense radial
crown.

---

## Root-cause classification
**Closest to (a) — hierarchy exists but the angles are wrong — with one important caveat
that pushes it toward (d).** Precisely:

- Hierarchy **data structure**: present and intact (Q3) → not (b), not (c).
- Branching **angles**: no rule at all; directions are incidental (Q2) → the "angles are
  wrong" half of (a) holds strongly.
- **The caveat (why it's really (a)+(d)):** the hierarchy itself is **proximity-derived**
  (grid-cell centroid merge), which is *also* what produces the **excessive valence**
  (median 4, up to 8 — a real fork is 2-3) and the absence of angle control. So this is
  **not** "a good botanical hierarchy that just needs better angles painted on." Fixing
  angles alone will not help while the *parent-assignment method* (proximity merge) keeps
  bursting 8-way nodes. The connection method needs to become growth/hierarchy-aware
  (control valence, choose a dominant continuation + thin laterals, impose sibling angular
  spacing, and curve segments) — the hierarchy graph is a fine substrate to rebuild on, but
  the merge rule that populates it is the thing generating the bad topology.

**One-line recommendation:** treat it as **(a) with a (d) caveat** — the parent→child graph
and metadata exist and are reusable, but *both* the branching angles (none specified) *and*
the junction valence (proximity-merge bursts 8-way nodes) are wrong, so the fix is to
replace the proximity-centroid merge with a valence-capped, angle/curvature-aware
connection over the existing graph — **not** merely to add angles onto the current merge.

*Stop here for review before scoping any fix.*
