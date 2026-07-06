# Phase-A Skeleton→Mesh Spike — Broad Dome (result + go/no-go)

> **Status:** SPIKE COMPLETE. **Read:** the skinning *primitive* works, but junction
> quality does **NOT** hold up against ManifoldMesher on the current leaf-back skeleton —
> and the blocker is the **skeleton**, not the skinning tooling. **Recommendation:
> qualified NO-GO on proceeding straight to the full mesh subsystem** (bark UVs /
> attribute re-provision / integration); a **leaf-back skeleton branch-topology
> refinement** task should come first, then re-spike. **Date:** 2026-07-06 · **By:** Opus
> 4.8 (1M). Follows [`mtree_skeleton_input_investigation.md`](mtree_skeleton_input_investigation.md).
> Not production code — spike scripts + renders in `tmp/`.

## What was built
The full proposed pipeline, end to end, for the exact Broad Dome validation specimen
(H 14.4 m, DBH 15 in):

1. **Leaf-back skeleton → node graph** (`tmp/leafback_graph.py`): the frozen merge
   machinery, extended to emit a **rooted parent-linked graph** (the genuinely-new
   front-end), plus **pipe-model radius** per node (`r_parent^2.3 = Σ r_child^2.3`,
   seeded 4 mm at tips, scaled so the trunk = DBH/2 → 190 mm ✓) and **strand
   decomposition** (thickest-child continuation = Mtree-style `stem_id`).
2. **Manual per-strand tube mesher** (`tmp/leafback_skin_spike.py`): rings along each
   strand, writing the per-vertex **`radius` + `stem_id` attributes and outward normals**
   — the exact contract ManifoldMesher provides, so the existing steps apply unchanged.
3. **The existing, mesher-agnostic steps, imported from `generate_trees_mtree.py`**
   (not reimplemented): `clean_degenerate_geometry` → `enforce_min_twig_diameter` →
   `stitch_bark_islands`.
4. Raw bark GLB (`tmp/leafback_bark_spike.glb`) + renders (`leafback_bark_view{0,1,2}.png`,
   `leafback_bark_junction{0,1}.png`).

## Measured results
| stage | verts | faces | note |
|---|---|---|---|
| raw tube mesh (781 strands) | 19,061 | 18,280 | 1048 nodes, 781 sprigs |
| after `clean_degenerate` | 17,295 | 18,280 | welded coincident ring verts |
| after `min-twig` (Ø3.2 cm) | — | — | inflated 10,945 sub-floor verts, **2,898 junction verts preserved** ✓ |
| after `stitch` (tol 3.2 cm) | 13,350 | 18,158 | welded 3,980; islands 209→~18 |

**The existing steps all applied and behaved correctly** on the new mesh — the min-twig
junction-safety preserved 2,898 overlap verts, and stitch fused the separate tubes exactly
as it does for ManifoldMesher's output. So **items #5, #7 from the investigation's
reuse list are confirmed reusable.**

### Front-end finding (positive): surface-emergence base placement is essential
First attempt placed each child strand's base at the **parent axis** → thick branches sat
~(parent_r − child_r) deep inside the trunk, far beyond stitch's surface-weld tolerance →
**154 large orphan islands** (fragmented mesh). Correcting to **surface-emergence**
placement (child base on the parent tube surface along the emergence direction) + passing
the twig floor to stitch dropped that to **17 orphans** (209→~18 connected components, ~92%
connected). This is a real, cheap front-end detail the full subsystem must get right — and
it shows the existing stitch tooling *does* fuse leaf-back tubes when bases are placed
correctly.

## Junction quality — honest assessment (the actual risk being tested)
**It does not hold up against ManifoldMesher.** The gross structure reads (trunk → fork →
primaries → broad dome crown — the correct Broad Dome envelope), but **in close-up the
junctions are a pile of interpenetrating straight sticks, not organic forks**
(`leafback_bark_junction0/1.png`):

- **High-valence, sharp-angle nodes.** The merge converges many strands at each node from
  many directions; tubes meet at abrupt random angles with heavy interpenetration, not the
  smooth low-valence Y-forks ManifoldMesher produces.
- **Interior strand-crossing.** Because the merge pulls nodes toward the trunk axis, long
  twigs from different crown regions cross the interior and their tubes pass *through* each
  other (X-crossings) without being connected — visual clutter that no weld step fixes
  (they aren't parent-child).
- **No branch hierarchy.** The crown is a near-uniform **radial spray of straight,
  equal-thickness twigs** (`view1.png`), not a hardwood's trunk→primary→secondary→twig
  taper cascade. Segments are perfectly straight (no curvature) — the merge outputs
  line segments between centroids.
- **17 residual orphans** still float free (tunable, but nonzero).

**Root cause is the SKELETON, not the skinning.** The tube mesher + Blender-native
skinning + existing weld/stitch/min-twig faithfully skinned whatever they were given; they
performed as the investigation predicted. What the spike reveals is that the **leaf-back
skeleton — validated for crown *envelope* and emergent *hop count*, explicitly NOT for
branch topology** (validation doc: *"Does not yet establish… real branch topology"*) — is
**not yet a skinnable branch structure.** Any skinner will show these crossings and
sharp junctions because they are in the graph.

## Go / No-Go
**Qualified NO-GO on committing to the full mesh subsystem (bark UVs, attribute
re-provisioning, pipeline integration) as the next step.** Rationale: those are polish and
plumbing on top of a mesh that does not yet read as a tree. The spike did its job — it
found the real blocker early, one level upstream of where the investigation expected it.

**What the spike *did* prove (banked):**
- Blender-native tube skinning + the existing `clean_degenerate`/`min-twig`/`stitch` steps
  produce a connected, correctly-attributed, correctly-tapered bark mesh from a leaf-back
  graph. The skinning half of the subsystem is low-risk.
- The front-end (graph + pipe-radius + strands + surface-emergence bases) works and is small.

**Recommended next task (before any subsystem build): leaf-back skeleton branch-topology
refinement** — the item validation deferred, now a concrete visual blocker. Needs:
- **Curved segments** (splines / smoothing) instead of straight centroid-to-centroid lines.
- **Valence capping** at merge nodes (a real fork is 2–3 children, not 5–8).
- **Anti-crossing strand routing** — route merges *down existing limbs* / along the crown
  shell rather than straight to the pulled centroid, so twigs don't cross the interior.
- **Enforced hierarchy** — a few thick primaries carrying progressively finer orders, so
  the pipe-radius taper reads as trunk→limb→twig, not a uniform spray.

Then **re-run this exact spike** on the refined skeleton (cheap — the harness exists) and,
only if junctions read cleanly, proceed to bark UVs → attribute re-provisioning → integration.

### Out of scope (unchanged)
- No bark UVs, no card-path attribute re-provisioning, no impostor/LOD/atlas, no production
  wiring into `generate_trees_mtree.py`. No oak. Spike scripts live in `tmp/`.
