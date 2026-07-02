"""
Generate tree models for Central Park Walk using Mtree (Modular Tree).

Creates scale-aware tree variants with size-appropriate branch density.
Trees are generated at real-world heights, then normalized to 5m model
space for the existing Godot pipeline. Each tier (s/m/l) is generated
independently for authentic silhouettes — no derive pathway.

Leaf cluster cards are placed via branch-walk algorithm: walking along
all branches using Mtree's radius/depth/extent/stem_id attributes, with
cluster counts calibrated against published LAI data per species.

Requires: Blender 4.5+ with Modular Tree addon installed.
Run:  blender4 --background --python scripts/generate_trees_mtree.py
      blender4 --background --python scripts/generate_trees_mtree.py -- --species oak
      blender4 --background --python scripts/generate_trees_mtree.py -- --species oak --tier l
"""

import bpy
import bmesh
import sys
import os
import math
import random
import shutil
import time
import numpy as np
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Setup paths and imports
# ---------------------------------------------------------------------------
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from leaf_card_utils import create_leaf_material, make_leaf_cards

# Enable Mtree addon
bpy.ops.preferences.addon_enable(module='bl_ext.user_default.modular_tree')
ADDON_DIR = os.path.expanduser(
    "~/.config/blender/4.5/extensions/user_default/modular_tree"
)
sys.path.insert(0, ADDON_DIR)
from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_mesh_from_cpp, create_leaf_mesh_from_cpp
from python_classes.resources.node_groups import distribute_leaves, LEAVES_MODIFIER_NAME
from python_classes.presets.leaf_presets import apply_preset_to_generator
# NOTE: the single-leaf texture is painted with PIL, which is NOT in Blender's
# bundled Python — so it is generated via a subprocess to system python3
# (see build_distribute_leaf), never imported here.

MODEL_DIR = os.path.join(PROJ, "models", "trees")
MODEL_H = 5.0       # Normalized model height for Godot pipeline
N_VARIANTS = 5       # Variants per tier
RADIAL_PTS = 24      # Radial segments for trunk/branch cylinders (15° per face)
SMOOTH_ITER = 2      # Mesh smoothing iterations

# Default foliage parameters for branch-walk placement.
# Species override individual keys as needed.
FOLIAGE_DEFAULTS = {
    "foliage_radius_threshold": 0.14,
    "foliage_min_depth": 1,
    "foliage_extent_range": (0.20, 0.95),
    "placement_interval_factor": 0.04,
    "sparse_branch_boost": 1.0,
    "cards_per_cluster": 35,
    "droop_factor": 0.0,
}


def bake_wind_vertex_colors(obj):
    """Bake MTree attributes into vertex colors for GPU wind animation.

    Reads hierarchy_depth, branch_extent, stem_id from MTree's mesher output
    and packs them into COLOR_0 vertex attribute for GLTF export.

    Vertex color encoding (AAA Pivot Painter convention):
        R: Normalized hierarchy depth (trunk=0 → branch tip=1) — trunk sway
        G: Normalized branch extent (branch base=0 → tip=1) — branch sway
        B: Stem ID hash (golden ratio) — per-branch phase variation
        A: 1.0

    Leaf card vertices (from joined leaf geometry) get position-based fallbacks.
    """
    mesh = obj.data
    n_verts = len(mesh.vertices)
    if n_verts == 0:
        return

    # Read MTree attributes (present on bark verts, zero on joined leaf cards)
    hierarchy_depth = np.zeros(n_verts)
    branch_extent = np.zeros(n_verts)
    stem_id = np.zeros(n_verts)

    hd_attr = mesh.attributes.get("hierarchy_depth")
    be_attr = mesh.attributes.get("branch_extent")
    si_attr = mesh.attributes.get("stem_id")

    has_mtree = bool(hd_attr and be_attr and si_attr)
    if has_mtree:
        hd_attr.data.foreach_get("value", hierarchy_depth)
        be_attr.data.foreach_get("value", branch_extent)
        si_attr.data.foreach_get("value", stem_id)

        max_depth = max(hierarchy_depth.max(), 1.0)
        hierarchy_depth /= max_depth
        max_extent = max(branch_extent.max(), 1.0)
        branch_extent /= max_extent
        stem_hash = np.mod(stem_id * 0.61803398875, 1.0)
    else:
        # Geometry fallback: use height and horizontal distance
        zs = np.array([mesh.vertices[i].co.z for i in range(n_verts)])
        min_z, max_z = zs.min(), zs.max()
        z_range = max(max_z - min_z, 0.01)
        hierarchy_depth = (zs - min_z) / z_range

        # Trunk axis from bottom 10%
        base_thresh = min_z + z_range * 0.1
        base_xs = [mesh.vertices[i].co.x for i in range(n_verts) if zs[i] <= base_thresh]
        base_ys = [mesh.vertices[i].co.y for i in range(n_verts) if zs[i] <= base_thresh]
        cx = sum(base_xs) / max(len(base_xs), 1)
        cy = sum(base_ys) / max(len(base_ys), 1)
        for i in range(n_verts):
            v = mesh.vertices[i]
            branch_extent[i] = math.sqrt((v.co.x - cx)**2 + (v.co.y - cy)**2)
        max_ext = max(branch_extent.max(), 0.01)
        branch_extent /= max_ext
        stem_hash = np.array([
            math.fmod(abs(math.sin(mesh.vertices[i].co.x * 127.1 +
                                    mesh.vertices[i].co.y * 311.7 +
                                    mesh.vertices[i].co.z * 74.7) * 43758.5453), 1.0)
            for i in range(n_verts)
        ])

    # Identify leaf vertices and fix their zero MTree data
    leaf_verts = set()
    for poly in mesh.polygons:
        mat = obj.material_slots[poly.material_index].material \
              if poly.material_index < len(obj.material_slots) else None
        if mat and "leaf" in mat.name.lower():
            for vi in poly.vertices:
                leaf_verts.add(vi)

    if leaf_verts and has_mtree:
        # Inherit wind data from nearest bark vertex so leaf cards animate
        # in sync with their parent branch (prevents clip-through oscillation).
        # Grid hash: O(n) — each leaf gets wind data from a nearby bark vertex.
        bark_idx_arr = np.array([i for i in range(n_verts) if i not in leaf_verts])
        if len(bark_idx_arr) > 0:
            vert_coords = np.zeros(n_verts * 3)
            mesh.vertices.foreach_get("co", vert_coords)
            vert_coords = vert_coords.reshape(n_verts, 3)

            # Build grid: one representative bark vertex per cell (first wins)
            cell_size = 0.3
            grid = {}  # (cx,cy,cz) → bark vertex index
            for bi in bark_idx_arr:
                key = (int(vert_coords[bi, 0] / cell_size),
                       int(vert_coords[bi, 1] / cell_size),
                       int(vert_coords[bi, 2] / cell_size))
                if key not in grid:
                    grid[key] = bi

            # Each leaf vertex gets wind data from the bark vertex in its cell
            # (or nearest occupied cell via expanding search)
            fallback_bi = bark_idx_arr[0]
            for vi in leaf_verts:
                key = (int(vert_coords[vi, 0] / cell_size),
                       int(vert_coords[vi, 1] / cell_size),
                       int(vert_coords[vi, 2] / cell_size))
                bi = grid.get(key)
                if bi is None:
                    # Search 3x3x3 neighborhood
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            for dz in range(-1, 2):
                                bi = grid.get((key[0]+dx, key[1]+dy, key[2]+dz))
                                if bi is not None:
                                    break
                            if bi is not None:
                                break
                        if bi is not None:
                            break
                if bi is None:
                    bi = fallback_bi
                hierarchy_depth[vi] = hierarchy_depth[bi]
                branch_extent[vi] = branch_extent[bi]
                if stem_hash[vi] < 0.001:
                    stem_hash[vi] = stem_hash[bi]

    # Create vertex color attribute (COLOR_0 in GLTF)
    attr_name = "Col"
    if attr_name in mesh.color_attributes:
        mesh.color_attributes.remove(mesh.color_attributes[attr_name])
    color_attr = mesh.color_attributes.new(
        name=attr_name, type='BYTE_COLOR', domain='CORNER'
    )

    # Write per-loop colors, fixing branch junction faces.
    # Junction faces span two branches (different stem_ids), causing the wind
    # shader to tear the face as branches sway at different phases. For these
    # faces, unify wind data at the loop level so the face moves as one unit.
    for poly in mesh.polygons:
        verts_in_face = [mesh.loops[li].vertex_index
                         for li in range(poly.loop_start, poly.loop_start + poly.loop_total)]

        # Check for junction: large stem_hash variance across face
        is_junction = False
        if has_mtree and not any(vi in leaf_verts for vi in verts_in_face):
            hashes = [stem_hash[vi] for vi in verts_in_face]
            h_min, h_max = min(hashes), max(hashes)
            spread = min(h_max - h_min, 1.0 - (h_max - h_min))
            is_junction = spread > 0.08

        if is_junction:
            # Unify: average depth/extent, pick first vertex's hash
            n = len(verts_in_face)
            avg_d = sum(hierarchy_depth[vi] for vi in verts_in_face) / n
            avg_e = sum(branch_extent[vi] for vi in verts_in_face) / n
            pick_h = stem_hash[verts_in_face[0]]
            for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
                color_attr.data[li].color = (avg_d, avg_e, pick_h, 1.0)
        else:
            for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
                vi = mesh.loops[li].vertex_index
                color_attr.data[li].color = (
                    hierarchy_depth[vi],
                    branch_extent[vi],
                    stem_hash[vi],
                    1.0,
                )

    idx = mesh.color_attributes.find(attr_name)
    mesh.color_attributes.active_color_index = idx
    mesh.color_attributes.render_color_index = idx


def clean_nan_vertices(obj):
    """Remove NaN/inf vertices from mesh and return (height, width) of valid bbox."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    to_remove = []
    valid_xs, valid_ys, valid_zs = [], [], []
    for v in bm.verts:
        if (math.isnan(v.co.x) or math.isnan(v.co.y) or math.isnan(v.co.z) or
                math.isinf(v.co.x) or math.isinf(v.co.y) or math.isinf(v.co.z)):
            to_remove.append(v)
        else:
            valid_xs.append(v.co.x)
            valid_ys.append(v.co.y)
            valid_zs.append(v.co.z)

    if to_remove:
        bmesh.ops.delete(bm, geom=to_remove, context='VERTS')

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    if not valid_zs:
        return 0.0, 0.0

    h = max(valid_zs) - min(valid_zs)
    w = max(valid_xs) - min(valid_xs)
    return h, w


def clean_degenerate_geometry(obj, merge_dist=0.005, min_face_area=1e-5):
    """Remove degenerate branch-tip geometry from Mtree mesh.

    Mtree generates tapered branch cylinders that collapse to zero radius at
    tips, creating thousands of zero-area sliver triangles per tree. The wind
    shader displaces vertices by height-dependent offsets, inflating these
    invisible slivers into visible triangular artifacts with bark texture.

    Steps:
      1. Dissolve degenerate edges (zero-length collapsed edges)
      2. Merge vertices converging at branch tips (within merge_dist)
      3. Remove faces below min_face_area (remaining slivers)
      4. Remove loose vertices/edges left behind
      5. Recalculate outward-facing normals
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    n_verts_before = len(bm.verts)
    n_faces_before = len(bm.faces)

    # Dissolve zero-length edges (collapsed branch segments)
    bmesh.ops.dissolve_degenerate(bm, dist=merge_dist * 0.2, edges=bm.edges[:])

    # Merge vertices converging at branch tips (radius → 0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=merge_dist)

    # Remove remaining sliver faces
    bm.faces.ensure_lookup_table()
    degenerate = [f for f in bm.faces if f.calc_area() < min_face_area]
    if degenerate:
        bmesh.ops.delete(bm, geom=degenerate, context='FACES')

    # Remove loose vertices (no connected faces)
    bm.verts.ensure_lookup_table()
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')

    # Ensure consistent outward-facing normals
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    n_verts_after = len(bm.verts)
    n_faces_after = len(bm.faces)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    removed_v = n_verts_before - n_verts_after
    removed_f = n_faces_before - n_faces_after
    if removed_v > 0 or removed_f > 0:
        print(f"    Mesh cleanup: {removed_v} verts, {removed_f} faces removed "
              f"({n_faces_before} → {n_faces_after})")


def cap_skeleton_depth(obj, max_depth):
    """Delete branch geometry beyond hierarchy_depth `max_depth` (the RAMIFICATION
    CAP, user's stem/twig-redundancy insight 2026-06-22 s4).

    WHY the split-prob cap alone is insufficient on big tiers (MEASURED): Mtree
    forks per branch-SEGMENT, so ramification depth grows ~exponentially with limb
    length. A 30m london_plane has ~16.5m primary limbs and still ramifies to
    hierarchy_depth 11 even at sub_split_prob 0.10 — the same setting keeps a 22m
    tree at depth ~3 (its limbs are ~10m). So lowering split probability cannot
    bound depth at scale; pruning by the depth ATTRIBUTE is height-independent and
    is the literal expression of "cap the skeleton at ~tertiary."

    The leaf card is a 4-leaf twig SPRIG that already paints its own terminal twig,
    so geometry past the card is doubly wrong: redundant with the painted twig AND
    a bare filament poking past the cards. Capping removes it → big perf/size win +
    the card sits at the true terminal tip. Card placement runs AFTER this on the
    capped mesh, so cards land on the new (depth<=max_depth) tips.

    Reads the raw integer `hierarchy_depth` vertex attribute (0=trunk, 1=primary,
    2=secondary, 3=tertiary, ...). bmesh preserves the custom-data layers the
    downstream card path reads (stem_id/radius/direction/branch_extent). Returns
    the vert count deleted (reported for governance, like the min-twig floor).
    """
    mesh = obj.data
    hd = mesh.attributes.get("hierarchy_depth")
    if hd is None or max_depth is None:
        return 0
    depths = np.zeros(len(mesh.vertices))
    hd.data.foreach_get("value", depths)
    di = np.rint(depths).astype(int)
    over = np.where(di > int(max_depth))[0]
    if over.size == 0:
        return 0
    over_set = set(int(i) for i in over)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    to_del = [v for v in bm.verts if v.index in over_set]
    bmesh.ops.delete(bm, geom=to_del, context='VERTS')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(to_del)


# Minimum twig DIAMETER (metres, real-world) below which a branch tube is
# inflated so it still READS on-screen. WHY (user, 2026-06-21): Mtree tapers
# every twig to ~0 radius, so a leaf cluster can be perfectly CONNECTED in the
# data (check_foliage_connectivity passes) yet sit on a twig too thin to render
# — it reads as a FLOATING clump (the london_plane sapling defect). The pixel
# floor is unforgiving: at 1080p/70° a feature subtends ~1px only at diameter
# ≈ 0.0011 × distance, so a load-bearing twig must read at the tier's review
# distance (s≈15-25m, m≈20-50m, l up to the 80m impostor handoff). These are a
# DELIBERATE thickening past botanical reality (real plane twig ~3-6mm) — the
# price of a visible trunk->branch->leaf line. Per-species override via
# sp["min_twig_diameter"] (scalar metres or {tier: metres}).
MIN_TWIG_DIAMETER = {"s": 0.022, "m": 0.032, "l": 0.050}

# Absolute last-resort floor. Enforcing a min twig diameter is an UNSKIPPABLE
# part of every tree build (user 2026-06-21): a build must NEVER ship a twig at
# ~0 radius. If a tier has no table entry and no species override, we fall back
# to this floor with a loud warning rather than silently skipping. The resolver
# is therefore guaranteed to return a positive diameter for any tier.
MIN_TWIG_DIAMETER_ABS_FLOOR = 0.020  # 2cm

MIN_TWIG_RATIONALE_DEFAULT = (
    "pixel-visibility floor — a load-bearing twig must subtend ~2px at its tier "
    "review distance (s 15-25m, m 20-50m, l up to the 80m impostor handoff); "
    "diameter ~= 0.0011 x distance per px at 1080p/70deg FOV. Deliberately past "
    "botanical reality to keep the trunk->branch->leaf line solid, not floating.")


def _min_twig_diameter(sp, tier_name):
    """Resolve (diameter_m, rationale) for this species + tier.

    NEVER returns 0: a min twig diameter is unskippable (user 2026-06-21). A
    missing per-species value falls back to the MIN_TWIG_DIAMETER table, then to
    MIN_TWIG_DIAMETER_ABS_FLOOR with a warning. The rationale travels with the
    value so every build report can state WHY this floor was chosen.
    """
    rationale = sp.get("min_twig_rationale", MIN_TWIG_RATIONALE_DEFAULT)
    ov = sp.get("min_twig_diameter")
    val = None
    if isinstance(ov, dict):
        val = ov.get(tier_name)
    elif ov is not None:
        val = ov
    if val is None:
        val = MIN_TWIG_DIAMETER.get(tier_name)
    if val is None or float(val) <= 0.0:
        print(f"  WARNING: no min twig diameter configured for tier "
              f"'{tier_name}' — falling back to absolute floor "
              f"{MIN_TWIG_DIAMETER_ABS_FLOOR * 100:.1f}cm")
        val = MIN_TWIG_DIAMETER_ABS_FLOOR
    return float(val), rationale


def enforce_min_twig_diameter(obj, min_diam_m, actual_h):
    """Inflate sub-floor branch tubes to a minimum DIAMETER so thin twigs read.

    Mesher-agnostic: the ManifoldMesher writes a per-vertex 'radius' attribute
    and tube-surface vertex normals point radially OUTWARD from the branch axis,
    so any vertex with radius < floor is pushed out along its own normal by
    (floor - radius). This fattens the thinnest twigs to the floor without
    needing ring/centerline topology, and leaves every above-floor branch
    untouched (trunk>>limb>>twig hierarchy preserved). Run AFTER
    clean_degenerate_geometry (so collapsed tips are already merged) and BEFORE
    foliage placement (so clusters anchor to the thickened twig).

    Mesh is in real metres at this stage (built at target_h, normalized to
    MODEL_H only later), so min_diam_m is a real-world diameter that survives
    end-to-end and rescales back to the same metres in-game.

    JUNCTION SAFETY (2026-06-21): Mtree exports each branch as a SEPARATE tube
    that only GEOMETRICALLY OVERLAPS its parent (no welded edges) — connectivity
    relies on those overlaps being within ~WELD_EPS (0.01u in MODEL_H space).
    A blind normal-push separates the two tubes at a junction (opposing pushes
    can open the gap past WELD_EPS), disconnecting whole branches → floating
    foliage (observed: 1/7 saplings went 0%→10.9%). So we NEVER inflate a vertex
    that sits in an overlap region: a vert is a junction vert if another vert in
    a DIFFERENT mesh ISLAND lies within the weld distance. Those stay put; only
    free twig SPANS (the part that reads as an invisible thread) inflate.
    """
    if min_diam_m <= 0.0:
        return {"min_diam_m": min_diam_m, "inflated": 0, "skipped_junction": 0}
    import mathutils
    min_r = min_diam_m * 0.5
    # Weld distance in REAL metres: the checker welds at 0.01u in MODEL_H(5u)
    # space, so 0.01u == 0.01 * actual_h / MODEL_H metres here. A junction vert
    # has a different-island neighbour within ~1.5x that (margin for the push).
    weld_real = 0.01 * actual_h / MODEL_H
    junction_eps = weld_real * 1.5
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    radius_layer = bm.verts.layers.float.get("radius")
    if radius_layer is None:
        bm.free()
        # No radius attribute → cannot floor. Report it loudly: an unskippable
        # step that found nothing to act on is a data problem, not a silent pass.
        print("    WARNING: mesh has no 'radius' attribute — min twig diameter "
              "could NOT be enforced")
        return {"min_diam_m": min_diam_m, "inflated": 0, "skipped_junction": 0,
                "no_radius": True}
    bm.verts.ensure_lookup_table()
    bm.normal_update()

    # --- Island id per vertex (union-find over the mesh edges) ---
    # Separate Mtree tubes are separate islands; ring neighbours share an island.
    parent = list(range(len(bm.verts)))

    def _find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in bm.edges:
        a, b = _find(e.verts[0].index), _find(e.verts[1].index)
        if a != b:
            parent[a] = b
    island = [_find(i) for i in range(len(bm.verts))]

    # --- KD-tree over all verts to find cross-island (junction) neighbours ---
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    inflated = 0
    skipped_junction = 0
    for v in bm.verts:
        r = v[radius_layer]
        # r > 0 guard: skip caps/degenerate verts that report 0 radius; only
        # inflate genuine thin tube surface (a positive radius below the floor).
        if not (0.0 < r < min_r):
            continue
        my_island = island[v.index]
        is_junction = any(
            idx != v.index and island[idx] != my_island
            for (_co, idx, _d) in kd.find_range(v.co, junction_eps)
        )
        if is_junction:
            skipped_junction += 1
            continue
        v.co += v.normal * (min_r - r)
        v[radius_layer] = min_r
        inflated += 1
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    if inflated or skipped_junction:
        print(f"    Min twig Ø {min_diam_m * 100:.1f}cm: inflated {inflated} "
              f"sub-floor verts ({skipped_junction} junction verts preserved)")
    return {"min_diam_m": min_diam_m, "inflated": inflated,
            "skipped_junction": skipped_junction}


def stitch_bark_islands(obj, actual_h, tol_u=0.006, min_twig_m=0.0,
                        stray_max_verts=30, verbose=True):
    """Fuse Mtree's branch tubes at their junctions so no branch (or the leaf card
    riding it) floats detached from the tree.

    ROOT CAUSE (user 2026-07-02, all six london_plane tiers): the ManifoldMesher
    emits every branch as a SEPARATE tube that only geometrically OVERLAPS its
    parent — no shared verts. clean_degenerate_geometry's 5 mm remove_doubles
    fuses the tightest overlaps into one mesh ISLAND, but where a child tube's
    base sits ~1-5 cm from its parent it welds only a vertex or two → the branch
    is topologically connected yet a visible SURFACE GAP remains and it reads as
    floating near the limb. A handful of twigs (esp. on saplings) generate fully
    detached, up to ~0.8 m off. Both were hidden under v1's dense canopy; v2's
    airier crown exposes them.

    FIX, in bark-only REAL-METRE space (mesh built at actual_h, normalised to
    MODEL_H later), run AFTER enforce_min_twig_diameter (thicker twigs overlap
    more) and BEFORE foliage placement (a card can then only anchor to trunk-wood):
      A. CROSS-STEM WELD — snap each vert onto its nearest vert on a DIFFERENT
         BRANCH within `tol`, but only when it is the THINNER (child) side (radius
         <, index tie-break) so the child base collapses onto the parent surface
         and the trunk/limb never moves. "Different branch" = different Mtree
         `stem_id` (falls back to mesh island if the attribute is absent) — this
         is the key: it closes the child-base-to-parent gap even when the two are
         ALREADY one mesh island via a stray point-weld (which an island test
         misses). Same-branch pairs are never touched, so twig ring cross-sections
         survive (a blind remove_doubles at this tol pinches every twig — ring
         spacing is ~1.4 cm). remove_doubles(1e-5) then fuses the coincident verts.
      B. DELETE STRAYS — any mesh island still unconnected to the main structure
         and small (≤ stray_max_verts) is a generation stray; drop it (a bigger
         orphan is kept + logged, never silently deleted).

    tol_u is in MODEL_H(5u) units (scales with tree height); ~0.006u closes the
    measured junction gaps while staying under the ~0.01u ceiling that would start
    bridging genuinely separate branches. Preserves the Mtree per-vertex attributes
    foliage placement reads (bmesh keeps point-attribute layers through the round-trip).
    """
    import mathutils
    # tol in real metres: the height-scaled value, but never below one twig
    # DIAMETER — if a child base sits closer to its parent than a twig is thick,
    # they should read as touching, so weld them. This floor is what lets small
    # trees (whose height-scaled tol is tiny, e.g. 1.2 cm on a 10 m sapling)
    # close their proportionally-larger junction gaps.
    tol = max(tol_u * actual_h / MODEL_H, min_twig_m)
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    n0 = len(bm.verts)
    if n0 == 0:
        bm.free()
        return {"welded": 0, "strays_deleted": 0, "islands_before": 0, "islands_after": 0}
    radius_layer = bm.verts.layers.float.get("radius")
    stem_layer = (bm.verts.layers.int.get("stem_id")
                  or bm.verts.layers.float.get("stem_id"))

    # --- island id per vertex (union-find over mesh edges) ---
    def _islands():
        parent = list(range(len(bm.verts)))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for e in bm.edges:
            ra, rb = find(e.verts[0].index), find(e.verts[1].index)
            if ra != rb:
                parent[ra] = rb
        return [find(i) for i in range(len(bm.verts))]

    island = _islands()
    islands_before = len(set(island))
    # "branch" key for the weld: prefer Mtree stem_id (a logical branch, catches
    # gaps inside one mesh island), else fall back to the mesh island.
    if stem_layer is not None:
        branch = [int(round(v[stem_layer])) for v in bm.verts]
        stem_based = True
    else:
        branch = island
        stem_based = False

    # --- A. cross-branch weld: snap the thinner (child) side onto the thicker ---
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()
    snap_to = {}   # vert index → target co (all reads are pre-write = original coords)
    for v in bm.verts:
        my = branch[v.index]
        best_idx, best_d = -1, tol
        for (_co, idx, d) in kd.find_range(v.co, tol):
            if idx == v.index or branch[idx] == my:
                continue
            if d < best_d:
                best_d, best_idx = d, idx
        if best_idx < 0:
            continue
        rv = v[radius_layer] if radius_layer else 0.0
        ru = bm.verts[best_idx][radius_layer] if radius_layer else 0.0
        # weld the thinner (child) vert onto the thicker (parent); index tie-break
        if rv < ru or (rv == ru and v.index > best_idx):
            snap_to[v.index] = bm.verts[best_idx].co.copy()
    for i, co in snap_to.items():
        bm.verts[i].co = co
    welded = len(snap_to)
    if welded:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bm.verts.ensure_lookup_table()

    # --- B. delete small strays still unconnected to the main structure ---
    island = _islands()
    islands_after_weld = len(set(island))
    counts = {}
    for lab in island:
        counts[lab] = counts.get(lab, 0) + 1
    root = max(counts, key=counts.get)     # largest island = trunk + all welded branches
    stray_verts, kept_orphans = [], 0
    for lab, c in counts.items():
        if lab == root:
            continue
        if c <= stray_max_verts:
            stray_verts.extend(v for v in bm.verts if island[v.index] == lab)
        else:
            kept_orphans += 1
    strays_deleted = 0
    if stray_verts:
        strays_deleted = len(stray_verts)
        bmesh.ops.delete(bm, geom=stray_verts, context='VERTS')

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    islands_after = islands_after_weld - (len([1 for lab, c in counts.items()
                                               if lab != root and c <= stray_max_verts]))
    if verbose and (welded or strays_deleted):
        note = (f"    Bark stitch ({'stem' if stem_based else 'island'}-based): "
                f"welded {welded} junction verts, deleted "
                f"{strays_deleted} stray-island verts "
                f"(islands {islands_before}→~{max(1, islands_after)}"
                + (f", {kept_orphans} large orphans KEPT+flagged" if kept_orphans else "")
                + f"; tol {tol*100:.1f}cm) — fuses ManifoldMesher's separate tubes so "
                "no branch/card floats off the trunk")
        print(note)
    return {"welded": welded, "strays_deleted": strays_deleted,
            "islands_before": islands_before, "kept_orphans": kept_orphans}


# ===========================================================================
# SPECIES CONFIGURATIONS
# ===========================================================================
# Each species defines botanical parameters mapped to Mtree's API.
# Height tiers: s=small, m=medium, l=large with real-world target heights.
# Branch density and sub-branch density scale naturally with tree size.
#
# >>> BUILDING A NEW SPECIES? READ docs/tree-pipeline-playbook.md FIRST, then
#     copy the _TEMPLATE entry below (NOT a real species — real entries carry
#     species-specific history you don't want). london_plane (tip-bearing) and
#     oak (along-branch) are the two worked, shipped reference builds. <<<
# ===========================================================================

# ---------------------------------------------------------------------------
# _TEMPLATE — clean copy-paste starting point for a new species (the current
# cluster-card method). Levers marked [MEASURE] must be derived from references
# per species (playbook §3); everything else is a copyable default. NOT built
# (leading underscore is skipped by the build loop). Delete comments you don't need.
# ---------------------------------------------------------------------------
SPECIES = {
  "_TEMPLATE": {
    "name": "Common Name (Genus species)",
    # --- SKELETON (silhouette; playbook §4) ---
    "crown_shape": "Spherical",       # Mtree crown envelope
    "up_attraction": 0.40,            # HIGH=excurrent central leader, LOW~0.35=decurrent rounded  [MEASURE habit]
    "trunk_randomness": 0.18,         # ~0.18 = clean stout bole; higher = S-curve lean
    "branch_start": 0.24,
    "branch_end": 0.95,               # ~0.94-0.97 so branches reach + round the apex
    "branch_density": 1.2,
    "branch_length_ratio": 0.37,      # crown breadth  [MEASURE aspect W/H]
    "branch_start_radius": 0.55,      # limb stoutness
    "branch_angle": 55,
    "branch_angle_variation": 0.4,
    "branch_split_prob": 0.55,
    "sub_density": 1.2,               # more secondaries fill the crown (stay < ~1.5 crash band)
    "sub_split_prob": 0.3,
    "crown_base_size": 0.65,          # DEFAULT 0.0 IS A NARROW-CONE CLAMP — always set (~0.55-0.75)
    "bark_color": (0.22, 0.18, 0.12),
    "bark_roughness": 0.92,
    # --- MIN TWIG DIAMETER (hard law 3) ---
    "min_twig_diameter": 0.05,        # 5cm floor, SCALAR (a dict floors only the listed tier — the oak bug)
    # --- LEAF CARD (real-photo cluster card; hard laws 1-2) ---
    "leaf_real_texture": "textures/leaves/TEMPLATE_cluster.png",  # built by make_<sp>_cluster_from_photo.py
    "card_stem_anchor": (0.25, 0.12), # [MEASURE] UV of the DRAWN stem base in the cluster PNG — wrong value floats leaves off the twig
    "foliage_distribute": True,
    "distribute_tiers": [],           # [] IS CRITICAL — the default ["s","m","l"] activates the dead 3D-leaf path
    "card_leaf_rule": True,           # >=1 tip cluster per branch
    "cards_per_cluster": 1,           # the card already IS a sprig; >1 = green ball
    "card_rule_max_radius": 0.05,     # thin twigs only
    "card_rule_min_per_branch": 1,
    "card_rule_spacing": 0.55,
    "card_rule_isolation_prune": False,
    "card_rule_apex_band": 0.18,      # clad the top 18% (apex never bare, hard law 6)
    "card_rule_depth_keep": {1: 0.05, 2: 0.60, 3: 1.0},  # [MEASURE pattern] tip-biased shown; along-branch (oak/elm) raises low-order keeps
    "card_size_floor": 0.42,          # keep a small _s crown from going see-through
    "tier_fraction": {"l": 1.0, "m": 0.40, "s": 0.24},
    "target_cluster_count_l": 700,
    # --- VARIANTS + SEEDS ---
    "n_variants": 1,                  # 1 until the impostor path is settled; reopen toward 7 for high-census species
    "base_seed": 100,                 # bump if the Mtree mesher crashes at a tier (fork-test picks safe seeds)
    "seed_step": 23,
    "variant_spans": {                # per-tier variant_spans OUTRANK these; tiers need their own or these clobber them
        "branch_angle": [45, 60],
        "up_attraction": [0.40, 0.60],
    },
    # --- TIERS (heights from census DBH: tree_builder.gd HEIGHT_RANGES / TIER_BOUNDS) ---
    "tiers": {
        "s": {"target_h": 10, "height_range": [8, 12], "skeleton_overrides": {
            # richer young skeleton to clad, straight leader, gentle droop:
            "branch_density": 1.0, "branch_split_prob": 0.55, "sub_density": 1.2,
            "branch_end": 0.95, "trunk_randomness": 0.18,
            "skeleton_max_depth": 3}},   # sub-visible depth-3 twig order fills the crown (masked by cards)
        "m": {"target_h": 18, "height_range": [12, 20], "skeleton_overrides": {
            "branch_split_prob": 0.45, "sub_density": 1.0}},
        "l": {"target_h": 25, "height_range": [20, 30]},
    },
  },

    # ----- Deciduous broad-crowned -----
    "oak": {
        "name": "Red Oak (Quercus rubra)",
        # SKELETON A — rounded DECURRENT broadleaf oak (oak_red.yaml; FIDELITY_CALL.md).
        # Red oak: broad, open, somewhat irregular ROUNDED dome, NO persistent central
        # leader (decurrent), stout heavy limbs, fork at moderate height. This is the
        # shared oak skeleton (red/scarlet/white/swamp-white/sawtooth/Turkey differ by
        # leaf card + fall color, not geometry). Pin oak's EXCURRENT central-leader form
        # is a separate Skeleton B, added later. (Was mislabeled "Pin Oak" + tuned
        # excurrent — corrected 2026-06-24.)
        "crown_shape": "Spherical",
        "trunk_frac": 0.28,        # red oak: moderate fork height (broad open crown), not pin's 0.18
        "trunk_shape": 0.5,       # Radius falloff curve
        "up_attraction": 0.40,    # WEAK leader — decurrent rounded crown (was 0.6 excurrent)
        "trunk_randomness": 0.35,  # stout straight-ish bole
        "branch_start": 0.24,     # fork at moderate height (decurrent), not the low pin fork
        "branch_end": 0.95,
        "branch_density": 1.2,
        "branch_length_ratio": 0.37,  # broad oval/rounded crown — aspect 0.6-0.8 (BRIEF §1);
                                      # the red-oak group is broader than compact pin oak (0.30)
        "branch_start_radius": 0.55,  # STOUT heavy oak limbs (data: stiff, stout — BRIEF §1)
        "branch_angle_variation": 0.4,  # tiered droop->horizontal->ascend, gentle enough that
                                        # the upper ascend doesn't pinch the crown narrow
        "branch_angle": 55,
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.28,  # let mid limbs spread horizontal (broad crown, was 0.4)
        "branch_split_prob": 0.55,
        "branch_split_angle": 40.0,
        "branch_flatness": 0.30,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 1.6,            # Red oak: dense rounded crown (was 1.5)
        "sub_length_ratio": 0.15,
        "sub_angle": 50,
        "sub_gravity": 12.0,
        "sub_stiffness": 0.1,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.3,
        "sub_split_angle": 35.0,
        "sub_flatness": 0.4,
        "sub_resolution": 1.0,
        "bark_color": (0.22, 0.18, 0.12),
        "bark_roughness": 0.92,
        "leaf_shape": "lobed",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 881,
        "leaf_scale": 1.3,  # red oak ~12-23cm blade (oak_red.yaml)
        "leaf_cluster_size_range": (0.38, 0.83),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.6,  # red oak LAI 3.5-5 → moderate-dense
        "crown_base_size": 0.75,   # broad rounded mature dome (Mtree default 0.0 clamps to a narrow cone)
        "min_twig_diameter": 0.05,  # 5cm MINIMUM branch diameter, EVERY tier (Chris 2026-06-24: every branch of every tree must read as solid wood, not a thread). Scalar → s/m/l all get 5cm (was {"s":0.04}, which floored ONLY _s at 4cm and let _m/_l fall through to the 0.032/0.050 table).
        # ---- LEAF PATH = REAL-PHOTO CLUSTER CARDS (london-plane method; hard laws 1-2,
        #      tree-pipeline-lessons.md banner). The Lobatae card is Chris's GIMP-assembled
        #      red-oak sprig → textures/leaves/oak_lobatae_cluster.png. Serves pin/red/
        #      scarlet; per-species fall HUE is shader-side (FALL_COLORS). ----
        "leaf_real_texture": "textures/leaves/oak_lobatae_cluster.png",
        "card_stem_anchor": (0.25, 0.12),  # UV of the DRAWN stem base in oak_lobatae_cluster.png (measured: bottom band centroid px(260,891)/1024 → u0.25,v0.12). NOT the texture corner — the sprig is centred with a 5% margin, so pinning (0,0) left the stem (and all leaves) floating ~0.3m off the twig (Chris 2026-06-24 "disjointed pieces floating"). Pinning the real stem base puts leaf→stem→twig→branch→trunk on one unbroken line.
        "foliage_distribute": True,
        "distribute_tiers": [],            # CARD path (NOT the 3D distribute path); [] is critical — default is ["s","m","l"]
        "card_leaf_rule": True,            # >=1 tip cluster per branch, no bare branches
        "cards_per_cluster": 1,            # the card already IS a 4-leaf sprig — 1 (default 35 = green ball)
        "card_rule_max_radius": 0.05,      # thin twigs only
        "card_rule_min_per_branch": 1,
        "card_rule_spacing": 0.55,
        "card_rule_isolation_prune": False,
        "card_rule_apex_band": 0.18,       # clad the leafy apex (no bare leader spike; hard law 6)
        "card_rule_depth_keep": {1: 0.05, 2: 0.60, 3: 1.0},  # london-plane-proven distribution: rare on primary, partial on secondary, FULL on the thin depth-3 twig order (the terminal, card-bearing order). Restored depth-3 2026-06-24 — the depth-2 cap left long bare secondaries (see-through crown); a SUB-VISIBLE thin-twig order (radius<=card_rule_max_radius 0.05, masked by its own cards) fills the crown volume the way LP does, distinct from the heavy depth-5 forks Chris banned.
        "card_size_floor": 0.42,           # sapling crown not see-through (gate-safe)
        "tier_fraction": {"l": 1.0, "m": 0.40, "s": 0.24},  # _s bumped 0.18→0.24 (~122→163 cards) to fill the young crown without enlarging leaves (2026-06-24)
        "target_cluster_count_l": 680,
        "base_seed": 105,   # shifted from 100 to avoid Mtree mesher crash at _m tier
        "seed_step": 23,
        # ONE variant per skeleton/size tier (Chris 2026-06-24) until london plane's
        # impostor path is settled. (Reopen toward 7 — highest census ~2.6k, tiling
        # most visible — once the impostor work lands; see project_oak_pipeline.)
        "n_variants": 1,
        # Variants span the real oak form (±~1 SD): woodland gap-reach narrow ↔
        # open-grown round, and weak ↔ strong central-leader prominence (BRIEF §7).
        "variant_spans": {
            "branch_angle": [45, 60],     # crown spread: narrow woodland ↔ round open-grown
            "up_attraction": [0.45, 0.72],  # central-leader prominence
        },
        "tiers": {
            # YOUNG red oak (sapling): broad DENSE upright-conical crown on a clear bole,
            # straight leader (no lean). Mirrors the london-plane _s lesson — the card rule
            # needs a RICH skeleton (many branches/twigs) to clad, so build the structure UP
            # then let ~1 cluster/branch fill it. (First _s was a sparse leaning whip: the old
            # override LOWERED density to 0.7/0.30/0.4 → only 32 branches/56 clusters.)
            "s": {"target_h": 10, "height_range": [8, 12], "skeleton_overrides": {
                "branch_density": 1.0,         # richer primary count (was 0.7)
                "branch_split_prob": 0.55,     # more forks → more tips to clad (was 0.30)
                "sub_density": 1.2,            # more twigs (was 0.4; held below the ~1.5 crash band)
                "branch_end": 0.95,            # branches reach near the apex (clad the top)
                "branch_angle_variation": 0.50,
                "branch_flatness": 0.40,       # baseline (reset 2026-06-24 single-var test)
                "branch_start_radius": 0.45,   # finer young limbs
                "crown_base_size": 0.55,       # baseline (crown.base_size proven a NO-OP on measured width in this config 2026-06-24)
                "branch_gravity": 4.0,         # gentle (was species 8.0)
                "sub_gravity": 4.0,            # was species 12.0 — heavy droop caused the lean
                "trunk_randomness": 0.18,      # straight young leader (kill the lean)
                "up_attraction": 0.38,         # baseline. NOTE 2026-06-24: crown width is clamped ~3.3m (asp~0.29) by Mtree crown/gravity internals — crown_base_size, up_attraction, branch_angle & length all proved ~no-op on measured width in single-var tests. Skeleton bbox under-reads the VISUAL crown (leaf cards extend ~0.5-1m past tips). Revisit via Mtree C++ crown control if foliated crown still too narrow vs ref.
                "branch_length_ratio": 0.52,   # baseline (reset)
                "branch_angle": 55,            # baseline (reset)
                "branch_up_attraction": 0.12,  # baseline (reset)
                # DEPTH (Chris 2026-06-24, revised): NO heavy tertiary forks — but a
                # thin depth-3 TWIG order (sub-visible, radius<=0.05, masked by its own
                # cards) is restored to fill the crown the way london_plane does. The
                # depth-2 cap left long bare secondaries (see-through young crown). 3, not
                # the old uncapped depth-5 chunky ramification.
                "skeleton_max_depth": 3}},
            "m": {"target_h": 18, "height_range": [12, 20], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.45, "sub_density": 1.0}},
            "l": {"target_h": 25, "height_range": [20, 30]},
        },
    },

    "elm": {
        "name": "American Elm (Ulmus americana)",
        # The classic vase/fountain: trunk forks at moderate height into ascending
        # arching limbs that sweep UP then arch outward. The general park population
        # — plainer than cathedral_elm (lower fork, more variable, NOT the Literary
        # Walk allée). Target model aspect ~0.90-1.10 (build width INTO the model
        # since sx=sy — no runtime 1.5x stretch). LAI 4.5-6, opaque dense shade.
        # (BRIEF: vase fountain, clearly LESSER sibling to cathedral_elm.)
        "crown_shape": "Spherical",    # Mtree has no vase; shaped via angle+gravity
        "trunk_frac": 0.25,
        "trunk_shape": 0.55,
        "up_attraction": 0.45,         # Let the crown spread (less vertical pull than cathedral)
        "trunk_randomness": 0.5,
        "branch_start": 0.22,          # Lower fork than cathedral_elm — ordinary elm
        "branch_end": 0.90,
        "branch_density": 1.3,
        "branch_length_ratio": 0.62,   # Long limbs — build the vase width into model
                                       # (no runtime stretch; need aspect ~0.90-1.10)
        "branch_start_radius": 0.44,   # Fine-to-medium elm branchlets (fountain, not
                                       # heavy oak-style limbs)
        "branch_angle_variation": 0.42, # Moderate vase variation
        "branch_angle": 72,            # Very wide spreading angle for broad vase
        "branch_gravity": 3.0,         # Minimal gravity — limbs spread outward wide
        "branch_stiffness": 0.22,
        "branch_up_attraction": 0.18,  # Very low upward pull — spreads wide
        "branch_split_prob": 0.55,
        "branch_split_angle": 40.0,
        "branch_flatness": 0.45,       # Strong lateral spread → 2-ranked spray habit
        "branch_break_chance": 0.02,
        "branch_resolution": 0.7,      # Size lever (keeps _l under ~100MB)
        "radial_pts": 16,              # Size lever — smooth trunk w/ smooth_iter=2
        "sub_density": 0.18,           # Lean sub-branch count — keeps _l under 100MB
                                       # (curtain character from gravity/droop not count)
        "sub_length_ratio": 0.16,
        "sub_angle": 55,
        "sub_gravity": 14.0,           # Heavy droop — hanging spray curtain
        "sub_stiffness": 0.07,
        "sub_up_attraction": -0.25,    # Sub-branches droop down
        "sub_split_prob": 0.30,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.30,
        "sub_resolution": 0.8,
        "bark_color": (0.30, 0.25, 0.18),
        "bark_roughness": 0.88,
        "leaf_shape": "elliptic",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 777,
        "leaf_scale": 1.05,  # American elm ~12cm
        "leaf_cluster_size_range": (0.40, 0.88),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.80,  # LAI 4.5-6 → opaque shade tree
        "target_cluster_count_l": 720,
        "base_seed": 42,
        "seed_step": 17,
        # 5 variants (moderate census); spans: fork height + crown spread (±~1SD).
        "variant_spans": {
            "branch_start": [0.18, 0.28],   # fork height: low ↔ moderate (below cathedral's 0.34)
            "branch_angle": [62, 80],        # narrow young vase ↔ broad old fountain
        },
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.30, "sub_density": 0.2}},
            "m": {"target_h": 20, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.42, "sub_density": 0.4}},
            "l": {"target_h": 28, "height_range": [22, 30]},
        },
    },

    "cathedral_elm": {
        "name": "Cathedral American Elm (Literary Walk)",
        "crown_shape": "Spherical",    # round ~1:1 vase aspect (skeleton sweep 2026-06-11)
        # HIGH vase: the Mall allée elms have a tall clean bole (~⅓ height) before
        # the crown opens — you walk UNDER the ceiling (BRIEF §1; the old 0.14 fork
        # made a low bush, the §2.1 distinctness defect). Skeleton sweep "thick_av"
        # recipe: high fork + thick ascending limbs + Spherical crown = wide full vase.
        "trunk_frac": 0.34,            # tall clean bole (was 0.16)
        "trunk_shape": 0.5,
        "up_attraction": 0.4,          # Less vertical pull — let branches spread
        "trunk_randomness": 0.4,
        "branch_start": 0.34,          # fork HIGH (was 0.14) — cathedral ceiling overhead
        "branch_end": 0.85,
        "branch_density": 1.0,         # DENSE — American elm is a fountain of MANY fine
                                       # ascending branches (LAI 4.5-6, BRIEF §3), not a few
                                       # heavy limbs. Branch count is a species trait, not a
                                       # size knob (user 2026-06-11): GLB size comes from
                                       # radial_pts + branch_resolution below, NOT fewer branches.
        "branch_length_ratio": 0.56,   # crown aspect ~0.78 model → ~1.16 in-game w/ runtime
                                       # ×1.5 — within the brief's 1:1–1.2:1 allée target
        "branch_start_radius": 0.44,   # FINE elm branchlets (fountain), not thick oak limbs
        "radial_pts": 16,              # 16-sided branches (vs global 24) — size lever, no
                                       # architecture change; smooth_iter=2 keeps trunks round
        "branch_resolution": 0.7,      # size lever (was 0.8), no architecture change
        "branch_angle_variation": 0.6, # limbs sweep UP — the ascending fountain/vase
        # Variants span the real population's FORM (±~1 SD): young narrow high-fork
        # replants ↔ old wide low-fork vases (BRIEF §7; user: variants reflect the data).
        "variant_spans": {
            "branch_start": [0.28, 0.42],         # fork height across the allée's age mix
            "branch_angle": [48, 62],             # crown spread: upright-narrow young ↔
                                                  # wide-arching old (the dominant width lever)
            "branch_length_ratio": [0.50, 0.62],  # limb reach (secondary structural variety)
        },
        "branch_angle": 55,            # Wide vase angle (was 40) — 55° creates arch
        "branch_gravity": 6.0,         # Less gravity — branches sweep UP then out
        "branch_stiffness": 0.20,
        "branch_up_attraction": 0.35,  # Moderate upward pull for vase arch shape
        "branch_split_prob": 0.55,
        "branch_split_angle": 50.0,    # Wide secondary splits (was 45)
        "branch_flatness": 0.50,       # Strong lateral spread (was 0.35)
        "branch_break_chance": 0.01,
        "sub_density": 0.20,            # Canopy curtain (1.5→…→0.7→0.20, controls bark vert count — keeps GLB <100MB)
        "sub_length_ratio": 0.16,
        "sub_angle": 55,               # Sub-branches spread wide too
        "sub_gravity": 16.0,           # Heavy droop — canopy curtain hangs down
        "sub_stiffness": 0.06,
        "sub_up_attraction": -0.4,     # Strong downward pull for drooping curtain
        "sub_split_prob": 0.30,
        "sub_split_angle": 35.0,
        "sub_flatness": 0.35,
        "sub_resolution": 0.8,
        "bark_color": (0.28, 0.23, 0.16),
        "bark_roughness": 0.90,
        "leaf_shape": "elliptic",
        "leaf_n": 52,
        "leaf_tex_size": 1024,
        "leaf_seed": 888,
        "leaf_scale": 1.05,  # American elm ~12cm
        "leaf_cluster_size_range": (0.45, 0.90),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.75,  # canopy density (0-1, from real-world LAI) — reduced for <100MB
        "target_cluster_count_l": 950,
        "base_seed": 101,
        "seed_step": 23,
        "tiers": {
            "m": {"target_h": 22, "height_range": [18, 26], "skeleton_overrides": {
                "branch_density": 0.85, "branch_split_prob": 0.45, "sub_density": 0.12}},
            "l": {"target_h": 30, "height_range": [26, 35]},
        },
    },

    "maple": {
        "name": "Sugar Maple (Acer saccharum)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.6,
        "trunk_randomness": 0.5,
        "branch_start": 0.22,
        "branch_end": 0.95,
        "branch_density": 1.4,
        "branch_length_ratio": 0.36,  # rounded-to-oval dense crown; spread 10-18m vs
                                      # H 20-27m → aspect ~0.6-0.7 (canopy data §3)
        "branch_start_radius": 0.48,  # heavy-wood maple: stout primary limbs
        "branch_angle_variation": 0.35,  # gentle tiering into a dense rounded-oval crown
        "branch_angle": 45,
        "branch_gravity": 6.0,
        "branch_stiffness": 0.25,
        "branch_up_attraction": 0.45,
        "branch_split_prob": 0.5,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,       # More oval than flat
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 1.6,
        "sub_length_ratio": 0.13,
        "sub_angle": 45,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.15,
        "sub_up_attraction": 0.3,
        "sub_split_prob": 0.3,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.38, 0.32, 0.26),
        "bark_roughness": 0.88,
        "leaf_shape": "palmate",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 552,
        "leaf_scale": 1.35,  # Sugar maple ~16cm, among largest
        "leaf_cluster_size_range": (0.33, 0.75),
        "leaf_flatten_range": (0.45, 0.60),
        "leaf_density": 0.9,  # LAI 5-7, "essentially opaque" (~1.3%% transmittance, §3)
        "target_cluster_count_l": 1000,  # LAI 5-7; sugar maple denser than oak
        "base_seed": 300,
        "seed_step": 29,
        # Woodland mass (~29%% of North Woods/Ramble via sweetgum/tupelo → maple) — high
        # census, so widen the seed envelope to 7 to kill stand tiling. Variants span
        # the rounded↔oval form within ~1 SD of the real population.
        "n_variants": 7,
        "variant_spans": {
            "branch_angle": [40, 55],       # upright-oval ↔ rounded-spreading crown
            "up_attraction": [0.45, 0.65],  # central-leader prominence
        },
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.30, "sub_density": 0.4}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.1, "branch_split_prob": 0.40, "sub_density": 1.0}},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Conifers -----
    "pine": {
        "name": "Austrian Pine (Pinus nigra)",
        "crown_shape": "Conical",
        "trunk_frac": 0.25,            # Clear lower trunk (USDA Silvics)
        "trunk_shape": 1.0,           # Straighter conifer trunk
        "up_attraction": 0.7,
        "trunk_randomness": 0.3,
        "branch_start": 0.22,         # Branches begin higher
        "branch_end": 0.95,
        "branch_density": 2.0,         # Dense whorled branches
        "branch_length_ratio": 0.32,   # Moderate branch length; spread 7.5-10.5m vs H 12-18m
                                       # → crown aspect ~0.6 (canopy data §4)
        "branch_start_radius": 0.40,   # tapering conifer limbs, stout at the whorl
        "branch_angle_variation": 0.3, # whorled profile: lower branches spread/downsweep,
                                       # upper whorls ascend (the conifer silhouette lever)
        "branch_angle": 70,            # Austrian pine: notably horizontal (60-80°)
        "branch_gravity": 6.0,         # Stiff horizontal, not drooping
        "branch_stiffness": 0.25,      # Pine branches are rigid
        "branch_up_attraction": 0.0,
        "branch_split_prob": 0.4,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.5,
        "branch_break_chance": 0.01,
        "branch_resolution": 1.4,
        "sub_density": 2.5,
        "sub_length_ratio": 0.12,
        "sub_angle": 45,
        "sub_gravity": 14.0,
        "sub_stiffness": 0.1,
        "sub_up_attraction": 0.0,
        "sub_split_prob": 0.3,
        "sub_split_angle": 35.0,
        "sub_flatness": 1.0,          # Flat needle tiers
        "sub_resolution": 1.0,
        "bark_color": (0.28, 0.22, 0.18),
        "bark_roughness": 0.92,
        "leaf_shape": "needle",
        "leaf_n": 60,
        "leaf_tex_size": 1024,
        "leaf_seed": 601,
        "leaf_scale": 1.0,  # needle (fascicle) — unaffected by leaf_scale
        "leaf_cluster_size_range": (0.42, 0.83),
        "leaf_flatten_range": (0.40, 0.60),
        "leaf_density": 0.72,  # "among the densest pines" — light transmission only 10-20%
                               # (canopy data §4); needle mass, not the old bare-sticks pine
        "target_cluster_count_l": 720,
        "foliage_extent_range": (0.10, 0.95),
        "base_seed": 400,
        "seed_step": 29,
        # Austrian pine's natural variation IS its age transform: pyramidal/narrow when
        # young → broadly rounded / flat-topped with age (canopy data §4). Span that axis
        # within ~1 SD of the park population (mix of mid-age specimens).
        "n_variants": 5,
        "variant_spans": {
            "branch_angle": [62, 78],          # steep narrow-conical young ↔ flat-spreading old
            "branch_length_ratio": [0.28, 0.40],  # short young ↔ long lower limbs (broad old)
        },
        "tiers": {
            "m": {"target_h": 14, "height_range": [10, 18], "skeleton_overrides": {
                "branch_density": 1.6, "branch_split_prob": 0.35, "sub_density": 1.5}},
            "l": {"target_h": 20, "height_range": [18, 25]},
        },
    },

    # ----- Deciduous small ornamental -----
    "cherry": {
        "name": "Yoshino Cherry (Prunus x yedoensis)",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.20,            # Low branching (ISA data)
        "trunk_shape": 0.6,
        "up_attraction": 0.5,
        "trunk_randomness": 0.6,
        "branch_start": 0.18,          # Matches low trunk_frac
        "branch_end": 0.90,
        "branch_density": 1.3,
        "branch_length_ratio": 0.52,   # broad spreading — Yoshino is "wider than tall"
                                       # (spread 9-12m vs H 9-15m → aspect ~0.85-1.0,
                                       # canopy data §5); no runtime stretch so it's in-model
        "branch_start_radius": 0.38,   # slender ornamental limbs, not heavy-wood
        "branch_angle_variation": 0.25,  # layered horizontal-spreading tiers
        "branch_angle": 50,
        "branch_gravity": 9.0,
        "branch_stiffness": 0.15,
        "branch_up_attraction": 0.22,  # horizontal spread → broad flat-rounded crown
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.35,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 1.5,
        "sub_length_ratio": 0.14,
        "sub_angle": 50,
        "sub_gravity": 12.0,
        "sub_stiffness": 0.1,
        "sub_up_attraction": 0.1,
        "sub_split_prob": 0.25,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.35,
        "sub_resolution": 1.0,
        "bark_color": (0.35, 0.20, 0.14),
        "bark_roughness": 0.72,
        "leaf_shape": "elliptic",
        "leaf_n": 48,
        "leaf_tex_size": 1024,
        "leaf_seed": 443,
        "leaf_scale": 0.85,  # Yoshino cherry ~10cm
        "leaf_cluster_size_range": (0.30, 0.68),
        "leaf_flatten_range": (0.50, 0.75),
        "leaf_density": 0.55,  # Cherry LAI 3.0-4.0 → moderate, dappled shade
        "target_cluster_count_l": 600,  # LAI 3-4 moderate canopy
        "base_seed": 200,
        "seed_step": 19,
        # Woodland understory mass (~14%% via black-cherry/dogwood → cherry). Variants
        # span the spreading form within ~1 SD of the 9-12m-spread population.
        "n_variants": 6,
        "variant_spans": {
            "branch_length_ratio": [0.46, 0.58],  # tighter ↔ broad open-grown spread
            "branch_angle": [46, 60],             # more upright ↔ more spreading
        },
        "tiers": {
            "s": {"target_h": 7, "height_range": [5, 9], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.25, "sub_density": 0.4}},
            "m": {"target_h": 12, "height_range": [9, 16], "skeleton_overrides": {
                "branch_density": 1.1, "branch_split_prob": 0.35, "sub_density": 1.0}},
            "l": {"target_h": 18, "height_range": [16, 22]},
        },
    },

    # ----- Multi-stem / white bark -----
    "birch": {
        "name": "Gray Birch (Betula populifolia)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.35,            # Longer clear trunk (IFAS ST-099)
        "trunk_shape": 0.7,
        "up_attraction": 0.6,
        "trunk_randomness": 0.7,
        "branch_start": 0.33,          # Matches higher trunk_frac
        "branch_end": 0.95,
        "branch_density": 1.0,
        "branch_length_ratio": 0.25,   # Short branches → narrow crown (spread ratio 0.50)
        "branch_angle": 40,            # Ascending branches (30-50°), not spreading
        "branch_gravity": 7.0,         # Ascending, not heavily drooping
        "branch_stiffness": 0.12,
        "branch_up_attraction": 0.3,
        "branch_split_prob": 0.4,
        "branch_split_angle": 30.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.03,
        "branch_resolution": 1.2,
        "sub_density": 1.2,
        "sub_length_ratio": 0.12,
        "sub_angle": 55,
        "sub_gravity": 14.0,
        "sub_stiffness": 0.08,
        "sub_up_attraction": -0.15,    # Drooping branchlets
        "sub_split_prob": 0.2,
        "sub_split_angle": 25.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.82, 0.78, 0.72),
        "bark_roughness": 0.65,
        "leaf_shape": "elliptic",
        "leaf_n": 45,
        "leaf_tex_size": 1024,
        "leaf_seed": 551,
        "leaf_scale": 0.6,  # Gray birch ~7cm, small triangular
        "leaf_cluster_size_range": (0.27, 0.60),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.5,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 600,  # LAI 3-4; corrects sparser-than-honeylocust bug
        "foliage_radius_threshold": 0.28,  # Few thin branches → include more of them
        "foliage_extent_range": (0.20, 0.95),
        "base_seed": 300,
        "seed_step": 23,
        "tiers": {
            "m": {"target_h": 9, "height_range": [8, 12], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.30, "sub_density": 0.8}},
            "l": {"target_h": 14, "height_range": [12, 16]},
        },
    },

    # ----- Compound leaves / airy -----
    "honeylocust": {
        "name": "Honeylocust (Gleditsia triacanthos)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.30,            # Taller clear bole (Silvics)
        "trunk_shape": 0.6,
        "up_attraction": 0.55,
        "trunk_randomness": 0.6,
        "branch_start": 0.28,          # Matches higher trunk_frac
        "branch_end": 0.95,
        "branch_density": 1.0,
        "branch_length_ratio": 0.32,   # short-ish (open crown) but broad-spreading aspect
                                       # ~0.55 in the brief's 0.5-0.7 (openness from leaf_density
                                       # + ferny texture, NOT a narrow crown)
        "branch_start_radius": 0.42,   # moderate limbs (open frame reads through foliage)
        "branch_angle_variation": 0.3, # ascending then wide-spreading (BRIEF §1)
        "branch_angle": 48,
        "branch_gravity": 7.0,
        "branch_stiffness": 0.18,
        "branch_up_attraction": 0.30,  # let limbs spread (broad open crown)
        "branch_split_prob": 0.5,
        "branch_split_angle": 38.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.2,
        "sub_density": 1.2,
        "sub_length_ratio": 0.12,
        "sub_angle": 48,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.15,
        "sub_split_prob": 0.25,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.35, 0.28, 0.20),
        "bark_roughness": 0.88,
        "leaf_shape": "compound",
        "leaf_n": 55,
        "leaf_tex_size": 1024,
        "leaf_seed": 661,
        "leaf_scale": 1.0,  # compound leaflets — unaffected by leaf_scale
        "leaf_cluster_size_range": (0.30, 0.63),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.35,  # Honeylocust LAI 2.0-2.5 → very airy, dappled light
        "target_cluster_count_l": 420,
        "placement_interval_factor": 0.050,
        "base_seed": 400,
        "seed_step": 29,
        # High combined count (~6k) → widen to 7; variants span openness + bole height
        # (the lacy bucket's natural spread) per the real population (BRIEF §7).
        "n_variants": 7,
        "variant_spans": {
            "branch_angle": [42, 55],     # crown spread / openness
            "branch_start": [0.24, 0.34],  # bole height
        },
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.6, "branch_split_prob": 0.30, "sub_density": 0.3}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.40, "sub_density": 0.8}},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Tight pyramidal -----
    "callery_pear": {
        "name": "Callery Pear (Pyrus calleryana)",
        "crown_shape": "Spherical",  # Changed from Conical — Conical triggers Mtree 5.5 mesher crash
        # Bradford-type: narrow UPRIGHT dense oval, steeply ascending branches packed
        # around a strong central leader (BRIEF §1). H 9–15m, spread 6–10m → aspect
        # ~0.5–0.6. Shape the columnar read via high up_attraction + low branch_angle,
        # NOT a conical crown (mesher crashes on Conical).
        "trunk_frac": 0.20,
        "trunk_shape": 0.8,           # Strong central leader
        "up_attraction": 0.8,         # Strong vertical pull = upright habit
        "trunk_randomness": 0.3,
        "branch_start": 0.18,
        "branch_end": 0.95,
        "branch_density": 1.2,         # Reduced from 1.5 to avoid Mtree mesher crash
        "branch_length_ratio": 0.50,   # Long branches needed to get spread → target aspect 0.50
        "branch_start_radius": 0.40,   # Moderate limb thickness (dense fine-branch oval)
        "branch_angle_variation": 0.30,  # Tight upswept oval — crown stays narrow top→bottom
        "branch_angle": 25,            # Slightly wider than minimum narrow crotch to achieve spread
        "branch_gravity": 5.0,
        "branch_stiffness": 0.3,
        "branch_up_attraction": 0.55,
        "branch_split_prob": 0.4,     # Reduced from 0.5
        "branch_split_angle": 30.0,
        "branch_flatness": 0.15,
        "branch_break_chance": 0.01,
        "branch_resolution": 1.4,
        "sub_density": 1.2,            # Reduced from 1.8 to avoid Mtree mesher crash
        "sub_length_ratio": 0.12,
        "sub_angle": 40,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.2,
        "sub_up_attraction": 0.4,
        "sub_split_prob": 0.3,
        "sub_split_angle": 25.0,
        "sub_flatness": 0.2,
        "sub_resolution": 1.0,
        "sub_min_height": 16,          # Sub-branches crash mesher at _m height (14m)
        "bark_color": (0.42, 0.36, 0.28),
        "bark_roughness": 0.82,
        "leaf_shape": "ovate",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 557,
        "leaf_scale": 0.55,  # Callery pear ~6cm, small glossy
        "leaf_cluster_size_range": (0.33, 0.72),
        "leaf_flatten_range": (0.50, 0.70),
        "leaf_density": 0.8,  # canopy density (0-1, from real-world LAI) LAI 4.0-6.0
        "target_cluster_count_l": 630,
        "base_seed": 362,     # Shifted from 351 to avoid Mtree mesher crash at _m tier
        "seed_step": 23,
        # High census (~2k); widen to 6 variants spanning the Bradford oval ↔ Chanticleer
        # columnar spread (branch_angle + up_attraction, BRIEF §7).
        "n_variants": 6,
        "variant_spans": {
            "branch_angle": [20, 30],        # oval (slightly wider) ↔ columnar (tighter)
            "branch_up_attraction": [0.48, 0.62],  # crown height emphasis variation
        },
        "tiers": {
            "s": {"target_h": 8, "height_range": [6, 10], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.25, "sub_density": 0.3}},
            "m": {"target_h": 14, "height_range": [10, 18], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.35, "sub_density": 0.8}},
            "l": {"target_h": 20, "height_range": [18, 24]},
        },
    },

    # ----- Weeping -----
    "willow": {
        "name": "Weeping Willow (Salix babylonica)",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.20,            # Short trunk, forks very low (Silvics)
        "trunk_shape": 0.4,
        "up_attraction": 0.7,
        "trunk_randomness": 0.5,
        "branch_start": 0.18,          # Matches low trunk_frac
        # The parametric fountain (create_willow_branchlets) now provides the
        # crown + weep, so the Mtree skeleton is just an interior trunk/limb
        # frame hidden under the crown shell. Keep its branching SPARSE and LOW
        # so no bare twig pokes through the foliage (the "disconnected branches"
        # / "gathered as they arch over" defects).
        "branch_end": 0.74,
        "branch_density": 0.6,
        "branch_length_ratio": 0.62,   # Broad weeping dome — spread 12-18m vs H 9-15m,
                                       # "often wider than tall" (canopy data §9) → aspect
                                       # ~1.0-1.2; willow gets no runtime stretch so the
                                       # width must live in the model.
        "branch_start_radius": 0.45,   # stout scaffold limbs off a stout short trunk
        "branch_angle_variation": 0.2, # mild: lower scaffolds spread, the weep is sub-driven
        "branch_angle": 50,
        "branch_gravity": 10.0,        # Scaffold branches arch and droop significantly
        "branch_stiffness": 0.4,
        "branch_up_attraction": 0.5,   # rise, then arch out into the dome
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.01,
        "branch_resolution": 1.4,
        # Mtree sub-branches are now redundant (the fountain whips ARE the weep)
        # and only add bare twigs poking through — keep them minimal.
        "sub_density": 0.2,
        "sub_length_ratio": 0.45,      # LONG drooping strands (was 0.30 — too short to read
                                       # as curtains); length+density drive the visible weep
                                       # since sub_gravity is capped (>30 crashes Mtree core)
        "sub_angle": 65,
        "sub_gravity": 26.0,           # Strong droop, just under the mesher crash cap (~30)
        "sub_stiffness": 0.05,
        "sub_up_attraction": -0.45,    # Downward pull (−0.8 crashed Mtree; stay above it)
        "sub_split_prob": 0.05,
        "sub_split_angle": 20.0,
        "sub_flatness": 0.0,
        "sub_resolution": 1.0,
        "bark_color": (0.40, 0.35, 0.28),
        "bark_roughness": 0.88,
        "leaf_shape": "lanceolate",
        "leaf_n": 55,
        "leaf_tex_size": 1024,
        "leaf_seed": 801,
        "leaf_scale": 0.95,  # Willow ~12cm long but narrow (aspect via lanceolate)
        "leaf_cluster_size_range": (0.27, 0.60),
        "leaf_flatten_range": (0.55, 0.75),
        "leaf_density": 0.45,  # Willow LAI 2.5-3.5 → curtain, not solid mass
        # The crown clusters only cap the dome top (willow_crown_placements thins
        # them to the upper crown); the weep itself is real drooping branchlet
        # geometry (create_willow_branchlets), not tiled cards.
        "target_cluster_count_l": 900,
        "cards_per_cluster": 30,
        "droop_factor": 0.5,           # extra downshift on cluster placement
        "branchlet_foliage": True,     # real drooping twig GEOMETRY weep — fine
                                       # tapering tubes + small leaf tufts hung
                                       # from the outer crown to the ground
                                       # (create_willow_branchlets). Replaces the
                                       # old hanging-card curtain (read as bars).
        "sub_min_height": 14,          # Sub-branches only on mature willows
        "base_seed": 50,
        "seed_step": 41,
        # Willow's natural variation: dome breadth (open-grown wide ↔ tighter) and
        # scaffold rise — within ~1 SD of the 12-18m-spread / 9-15m-tall population.
        "n_variants": 5,
        "variant_spans": {
            "branch_length_ratio": [0.55, 0.68],  # tighter ↔ broad open-grown dome
            "branch_angle": [44, 58],             # more upright ↔ more spreading scaffolds
        },
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.5, "branch_split_prob": 0.20, "sub_density": 0.15}},
            "m": {"target_h": 16, "height_range": [14, 20], "skeleton_overrides": {
                "branch_density": 0.6, "branch_split_prob": 0.25, "sub_density": 0.2}},
        },
    },

    # ----- Dense symmetrical -----
    "linden": {
        "name": "Linden (Tilia americana)",
        # Pyramidal-young → broadly-rounded dome. VERY DENSE opaque crown (LAI 5-7,
        # ~3-8% light transmission). Target aspect (w/h) ~0.55-0.65 at _l tier
        # (spread 9-15 m on H 18-24 m). Dense like maple, orderly not wild.
        # (BRIEF: dense tidy heart-leaved dome, distinct from oak tiers / elm vase.)
        "crown_shape": "Spherical",
        "trunk_frac": 0.26,
        "trunk_shape": 0.65,
        "up_attraction": 0.60,
        "trunk_randomness": 0.3,       # Very straight, orderly linden character
        "branch_start": 0.24,
        "branch_end": 0.95,
        "branch_density": 1.4,
        "branch_length_ratio": 0.46,   # Wide rounded dome: aspect 0.55-0.65 (was 0.30 → too narrow)
        "branch_start_radius": 0.46,   # Stout limbs — linden has thick main branches
        "branch_angle_variation": 0.35, # Young narrow-pyramidal → old broad-spreading
        "branch_angle": 45,
        "branch_gravity": 7.0,
        "branch_stiffness": 0.22,
        "branch_up_attraction": 0.38,
        "branch_split_prob": 0.5,
        "branch_split_angle": 32.0,
        "branch_flatness": 0.22,
        "branch_break_chance": 0.01,
        "branch_resolution": 1.4,
        "sub_density": 1.6,            # High density — opaque crown (LAI 5-7)
        "sub_length_ratio": 0.14,
        "sub_angle": 45,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.15,
        "sub_up_attraction": 0.25,
        "sub_split_prob": 0.3,
        "sub_split_angle": 28.0,
        "sub_flatness": 0.25,
        "sub_resolution": 1.0,
        "bark_color": (0.35, 0.30, 0.24),
        "bark_roughness": 0.85,
        "leaf_shape": "ovate",
        "leaf_n": 48,
        "leaf_tex_size": 1024,
        "leaf_seed": 773,
        "leaf_scale": 1.5,  # Linden ~19cm, 100-200cm2 — largest
        "leaf_cluster_size_range": (0.33, 0.72),
        "leaf_flatten_range": (0.45, 0.60),
        "leaf_density": 0.85,  # Linden LAI 5-7 → opaque dense shade tree
        "target_cluster_count_l": 880,
        "placement_interval_factor": 0.032,
        "base_seed": 500,
        "seed_step": 37,
        # High census (~1.75k) → 6 variants (free downstream, §4). Spans: crown
        # width (narrow-young → broad-old) + up_attraction (orderly vs open-grown).
        "n_variants": 6,
        "variant_spans": {
            "branch_angle": [40, 52],       # narrow young-pyramidal ↔ broad old dome
            "up_attraction": [0.55, 0.75],  # compact-upright ↔ spreading
        },
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.30, "sub_density": 0.5}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.1, "branch_split_prob": 0.40, "sub_density": 1.1}},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Tall open -----
    "london_plane": {
        "name": "London Plane (Platanus x acerifolia)",
        "crown_shape": "Spherical",
        # DECURRENT CANDELABRA habit (2026-06-21, skeleton sweep lp_candelabra vs
        # the wireframe refs london-plane-tree-01-02/09-02.jpg + Lincoln's Inn
        # bare-winter). The old params made a single-leader BOTTLEBRUSH — a
        # dominant central whip (up_attraction 0.6) with a confusion of short
        # equal sticks (length 0.38, angle_var 0.25, flatness 0.25) all the way up
        # the leader (branch_end 0.95). Real open-grown plane: stout trunk forks
        # into a FEW thick scaffold limbs → broad rounded crown, clear
        # trunk≫limb≫twig taper. Levers: kill leader dominance + long spreading
        # limbs + vase arch + fewer/heavier primaries (user: "branches should make
        # sense, not a confusion of sticks").
        "trunk_frac": 0.28,
        "trunk_shape": 0.6,
        "up_attraction": 0.35,         # was 0.6 — let the trunk give way to spreading limbs (decurrent)
        "trunk_randomness": 0.18,      # was 0.32 — the bare l skeleton LEANED/S-curved at some seeds (the leafed thumbnail hid it; explore lp_l_* seed 108/300, 2026-06-22 s4). 0.18 = a clean stout bole consistently across seeds (matches the approved _s value).
        "branch_start": 0.24,          # scalar fallback; m/l actually take branch_start from variant_spans
        "branch_end": 0.95,            # was 0.78→0.88→0.95. Branches must EMERGE near the apex (95% of trunk) or the top ~12% is a bare leader spike (the s4b "top-stick" — 0.88 left too much bare leader on m/l). At 0.95 the apex branches exist and the apex-cladding gate (card_rule_apex_band) leafs them → rounded, clad dome top (A149-03/nyc11), only a tiny apex nub bare. branch_length_top_factor 0.4 keeps these apex branches short so they clad tightly to the leader.
        "branch_density": 0.70,        # was 1.1 — FEWER but heavier primary scaffold limbs
        "branch_length_ratio": 0.55,   # scalar fallback; m/l take it from variant_spans. 0.55 = broad mature dome (A149-03); 0.60 sprawled (old l.glb→428MB)
        # NATURAL-GROWTH LENGTH GRADIENT (user 2026-06-21 PM: "longer branches come from
        # lower on the trunk... the larger the heavier, the heavier the less upward, thus
        # creating the teardrop"). Lower branches are older→longer→heavier→droop (less
        # upward); upper are younger→shorter→lighter→ascend. branch_length_top_factor =
        # the TOP branch length as a fraction of the BASE (long) length; power>1 keeps the
        # lower-middle long and tapers only near the apex. The droop itself comes from
        # gravity acting on the now-longer lower branches (longer lever = more sag).
        "branch_length_top_factor": 0.4,
        "branch_length_power": 1.5,
        "branch_start_radius": 0.72,   # was 0.52 — THICK scaffold limbs (clear hierarchy vs twigs)
        "crown_base_size": 0.75,       # was UNSET (Mtree default 0.0 = a narrow-cone clamp that pulls tips inward — reference_how_to_make_trees §8). This was the hidden reason the bare l crown read as a tall oval and m as a narrow pole. 0.75 opens the broad mature dome (A149-03); m overrides it down to ~0.62 for a narrower young-adult oval.
        "min_twig_diameter": {"s": 0.04},  # 4cm sapling-twig floor: the 12cm diagnostic (2026-06-21) proved the sapling floater is a THIN connecting twig (fattening it attached the clusters to visible wood), not off-bark placement. 4cm reads at the ~15-25m sapling review distance (~2-3px) without the cartoon look of 12cm.
        "branch_angle_variation": 0.55,  # was 0.25 — limbs sweep up/out into a vase arch
        "branch_angle": 60,            # scalar fallback; m/l take it from variant_spans. London plane: notably horizontal (50-70°, Silvics)
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "radial_pts": 11,              # was 16 — DECIMATE lod0: candelabra's longer/thicker limbs
                                       # ×7 variants blew l.glb to 428MB; bark is shader-painted
                                       # (triplanar) so cross-section roundness can drop w/o bark loss
        "branch_split_prob": 0.45,     # RAMIFICATION CAP (2026-06-22 s4): was 0.58. MEASURED — the l skeleton ramified to hierarchy_depth 11, vert mass peaking at depth 4-5, ~10-14k clusters & 90-129k verts/variant (55MB GLB). The leaf card IS the terminal 4-leaf twiglet, so depths 5-11 are bare filaments redundant with the card's painted twig. Lowering the per-segment fork chance caps primary over-forking. (m/s override this higher — the cap value is scale-appropriate: l's long limbs ramify exponentially more than m's/s's shorter ones, so l needs the hardest cap.)
        "branch_split_angle": 46.0,    # was 40 — wider secondary splits build the candelabra spread
        "branch_flatness": 0.48,       # was 0.25 — strong lateral spread (broad crown, not a plume)
        "branch_break_chance": 0.02,
        "branch_resolution": 0.78,     # was 1.0 — size lever (fewer segments along each limb)
        "sub_density": 0.7,            # was 1.1 — finer twig haze so the thick limbs read clearly + size
        "sub_length_ratio": 0.14,
        "sub_angle": 50,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.10,        # RAMIFICATION CAP (2026-06-22 s4): was 0.30. This is the MAIN driver of the redundant deep-filament haze (depth 5-11) measured on l — twig sub-sub-sub division. 0.10 stops the twig ramification ~tertiary so the card sits at the terminal tip and there are no bare filaments poking past the cards. Big perf + size win (the deep haze was most of the 55MB). m overrides to 0.22, s to 0.24 (shorter limbs ramify far less, so they need a lighter cap or they go sparse).
        "sub_split_angle": 35.0,
        "sub_flatness": 0.3,
        "sub_resolution": 0.72,        # was 1.0 — size lever (sub-branch detail) for lod0 budget
        "bark_color": (0.48, 0.45, 0.36),
        "bark_roughness": 0.75,
        "leaf_shape": "plane",  # broad palmate, wider-than-tall, shallow 5-lobe (was "lobed"=oak edge fn — wrong, 2026-06-19)
        "leaf_n": 48,
        "leaf_tex_size": 1024,
        "leaf_seed": 447,
        "leaf_scale": 1.4,  # London plane ~15cm x 18 wide, palmate
        "leaf_cluster_size_range": (0.38, 0.83),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.85,  # LAI 4-6, "largest leaf area of any inner-London tree" — heavy shade (BRIEF §3)
        # Structural-leaf SPRIG (foliage_distribute path, _s tier): the distributed
        # proto is a 4-leaf twig (ref close-up-...-2SA8J91), not a single leaf, so the
        # canopy reads as natural leaf CLUSTERS instead of fur on the branches. Leaves
        # stagger 0.62·base_len along the twig, golden-angle splay, ~52° outward tilt.
        "leaf_cfg": {"cluster_n": 3, "cluster_stem": 0.62, "cluster_tilt": 38.0},  # 3 leaves/cluster (user 2026-06-21 PM: "only 2 or 3 leaves per cluster") — 4 read CLUMPY; fewer leaves per sprig de-clumps each cluster. Paired with ~1.15x more clusters (spacing 0.26 below). Leaf SIZE right (scale 0.13). cluster_tilt = forward sweep of each blade toward the branch tip (twig runs +Z = outward)
        "foliage_continuous": True,  # clad branches as a continuous sheath (ref: pro Platanus model), not discrete scattered blobs — 2026-06-20
        # LEAF PATH = REAL-PHOTO CLUSTER CARDS (reverted from distribute_leaves,
        # 2026-06-20 PM). The 2026-06-20 AM "true-3D distribute" switch was
        # disproved by the render-budget analysis: at Ramble density ~200-250
        # trees carry full near-tier leaves at once (park_data.json, lod0≤80m),
        # so a near "leaf" can afford only ~2-12 tris — the 664-vert structural
        # leaf is ~460M tris/frame, impossible on a 3060 Ti. Both the recovered
        # AAA/SpeedTree research and the Godot/Blender community converge on
        # 50-200 cluster CARDS per canopy, leaves distinguished by the card's
        # alpha SILHOUETTE + COLOR (which is all that resolves past ~30m anyway),
        # not by geometry (docs/research-game-ready-leaves.md §1). So: keep the
        # continuous-cladding branch-walk placement (structural, on-twig — NOT
        # scattered/floating), but feed it a cluster card composited from the
        # REAL london-plane cutout (real veins/teeth/palmate outline/drab fall),
        # distinct from maple/sweetgum. distribute_leaves stays available for a
        # future hero/closeup tier only.
        # HYBRID FOLIAGE (user rule 2026-06-21: "real 3D leaves when within
        # budget"). The _s SAPLING uses STRUCTURAL 3D leaves (foliage_distribute):
        # flat cluster cards go see-through on a small crown and every densify
        # lever hit a wall (connectivity gate / mesher crash / cluster cap) — but
        # a sapling's crown is small enough (~1.7k leaves) to afford real geometry,
        # which fills densely like the nursery ref (exclamation-...-morton-circle)
        # and is coherent BY CONSTRUCTION (leaves instanced on bark → no floaters).
        # m/l keep cluster cards (a 30m crown's ~59k leaves would melt the 3060 Ti).
        # The 90m sapling LOD handoff bounds the structural-leaf cost to near-field.
        # CARDS AT EVERY TIER (user 2026-06-21 PM: "we're going to have to give up
        # the 3d leaves. the cards just look better.") — the structural 3D-leaf _s
        # was the GROUND-TRUTH "what right looks like" reference, but in-game the
        # real-photo cluster cards read better than the geometry even up close, AND
        # the heavy structural _s tanked fps when m/l-sized trees fell on it. So _s
        # now uses the same continuous-clad cluster-CARD path as m/l (tuned via
        # card_size_floor 0.42 + tier_fraction.s 0.18 below, set for the sapling).
        # foliage_distribute stays True but distribute_tiers is empty: the 3D path
        # is preserved (symmetric — "we can switch back if we absolutely must") but
        # inactive. The leaf RULE (every branch >=1 tip cluster, no bare branches)
        # is carried by the continuous-clad branch-walk, which clads ALL eligible
        # thin-branch verts tips-first (extract_leaf_positions, foliage_continuous).
        "foliage_distribute": True,
        "distribute_tiers": [],
        "tier_distribute": {
            # Dense small crown: high leaf density, ~16cm plane leaf, clad twigs
            # up to 9cm (the min-twig floor leaves twigs >=4cm). Tune to the ref.
            # LESSON (2026-06-21, user: "covered in leaves — trunk, branches, everything,
            # green fuzz"): max_radius is NOT a leaf-sheath thickness — it is a branch-RADIUS
            # THRESHOLD. The leaf geom-nodes modifier deletes leaf points where the sampled
            # branch radius >= max_radius ("remove points on thick branches", node_groups.py
            # L297). So BIG max_radius = leaves creep onto thick limbs + the trunk = fuzz on a
            # stick; SMALL max_radius = leaves only on the fine periphery, bare trunk + inner
            # limbs (the natural look). Measured radius on this skeleton: median 4.2mm, p95
            # 38mm, trunk base 99mm. 0.035 keeps leaves on twigs/sub-branch tips only.
            #
            # SIZE×COUNT (user 2026-06-21: "leaves must not interfere — spaced apart, on twigs;
            # appropriate size for coverage + realism, compromised with 3060ti"). The engineer's
            # compromise: FEWER, BIGGER, SPACED leaves — a plane leaf is large (15-25cm), so a
            # few big cards cover the crown with natural spacing AND far fewer instances than a
            # haze of tiny ones (450 density made ~40k leaves/tree — a GPU sink). scale 0.24
            # makes a realistically large, coverage-efficient leaf. proto base_len=2.93, so
            # on-tree leaf ≈ 2.93·0.24·(runtime height scale) — judged against the specimen
            # in-render, not in the abstract.
            # CLUSTER SPRIG (leaf_cfg.cluster_n=4): each distributed instance is now a 4-leaf
            # twig, so density is per-SPRIG. 95→26 keeps a similar total leaf count (~8k) but
            # CLUSTERED — natural spacing between sprigs, far fewer distribution points.
            # TIP BIAS + APEX (user 2026-06-21): max_radius 0.028 keeps clusters on the finest
            # twigs (so they gather at branch ENDS) while still catching the leader apex tip
            # (radius ~0.0275) so the TOP carries clusters. density 12 = "slightly sparser
            # leaves on more branches" — the richer branch/twig skeleton shows through.
            "s": {"density": 12.0, "scale": 0.13, "max_radius": 0.05, "spacing": 0.7, "leaves_per_branch_min": 1},  # THE LEAF RULE (user 2026-06-21 PM): every branch gets >=1 cluster at its TIP (no bare branches), placed deterministically per stem_id. "Too many leaves" at spacing 0.4 → 0.7 (near-zero extras, essentially just the guaranteed 1/branch). Each cluster = 3 leaves. If still dense, the floor is the BRANCH COUNT (reduce sub_density), since 1/branch is the rule's minimum.  # spacing = Poisson Distance Min (m): widened 0.35->0.45 (2026-06-21) — the smoother high-res skeleton exposed more fine-twig surface under max_radius, which inflated cluster count ~60% (a GPU cost the user did NOT ask for); 0.45 holds total leaves back at the prior ~6-7k while the WOOD carries the extra smoothness. Clusters stay even, not clumped.
        },
        "leaf_real_texture": "textures/leaves/london_plane_cluster.png",
        "target_cluster_count_l": 850,  # was 1080; on the sparser candelabra crown the high target forced the supplemental fill to add clusters OFF the bark (floaters) — lowered so most clusters ride the continuous-clad branches (2026-06-21)
        # SAPLING FILL (2026-06-21): two coupled levers. (1) card_size_floor lifts
        # the h/25≈0.36× card shrink so a small crown isn't see-through — but 0.52
        # pushed leaf-card corners past the connectivity gate (3-4% floaters), so
        # capped at a gate-safe 0.42. (2) tier_fraction s 0.15→0.18 (~128→153) for
        # a modest budget bump. The DOMINANT fix is the skeleton override below:
        # the size-chart ref (6e6cb11fdc) shows a young plane as a BROAD DENSE cone
        # with foliage from ~1.5m — not the narrow bare-trunked pole the old
        # override produced (aspect 0.16). m/l fractions unchanged.
        "card_size_floor": 0.42,
        "tier_fraction": {"l": 1.0, "m": 0.40, "s": 0.18},
        # THE LEAF RULE on cards (user 2026-06-21 PM: clusters "are not all the way
        # out to the tips... remember what we learned with the 3d model"). Place a
        # cluster card at every branch's tip-most vertex (guaranteed, tip-weighted)
        # via _card_placements_per_branch, instead of the continuous-clad walk that
        # bunched clusters inboard. max_radius 0.05 = thin twigs only; spacing 0.4
        # adds a few extras down each branch for fullness.
        "card_leaf_rule": True,
        "card_rule_max_radius": 0.05,
        "card_rule_min_per_branch": 1,
        "card_rule_spacing": 0.55,   # was 0.40 — extras 0.40m apart overlapped at 2x card size ("clumps"); widen so the guaranteed tip dominates and inboard extras de-clump
        # ISOLATION PRUNE OFF (user 2026-06-22, cpw_004/007/010: "leaves but not at
        # or near the tip"). The prune dropped any cluster with <2 neighbours within
        # 0.72m — which is exactly a twig-TIP sprig out at the crown periphery, so it
        # was stripping the outermost foliage (12-30 clusters/variant, mostly tips).
        # Its original job (kill lone floaters on low laterals) is now done by the
        # branch-order gate — those laterals are primary/secondary, mostly gated.
        "card_rule_isolation_prune": False,
        # BRANCH-ORDER GRADIENT (user 2026-06-22, cpw_000-002: "leaves should very
        # rarely emerge from primary branches, more from secondary, more yet from
        # tertiary"). hierarchy_depth is the true branch order (verified by the
        # in-code [diag]: 0=trunk, 1=primary, 2=secondary, 3+=tertiary & finer — it
        # increments on every fork, NOT just the trunk→br→sub function levels). This
        # maps a branch's order to the probability it bears ANY leaf; orders above
        # the max key inherit it (all tertiary+ = 1.0). Soft gradient keeps a few
        # leaves low while massing foliage on the outer crown shell (canopy data §11
        # "concentrated in outer crown shell / layered parasol effect"). Replaces the
        # radius gate as the order discriminator — the 4cm min_twig_diameter floor
        # clamps every branch ≥depth1 to 20mm radius, so radius cannot tell a primary
        # from a twig; depth can.
        "card_rule_depth_keep": {1: 0.05, 2: 0.60, 3: 1.0},  # secondary 0.35→0.60 (user 2026-06-22: "many bare or nearly bare", "some variants more evenly leafed than others") — 0.35 left too many secondaries bare and made variant coverage uneven; 0.60 fills + evens while keeping primaries rare
        # APEX CLADDING (user 2026-06-22 s4b: "top-sticks rising above their canopies").
        # Force-keep any depth>=1 branch whose tip is in the top 18% of the crown, so
        # the leafy growing apex isn't gated bare by the branch-order rule (which would
        # otherwise leave a bare leader spike). Paired with a higher branch_end so
        # branches actually REACH the apex to be clad (see tiers). Applies to all tiers.
        "card_rule_apex_band": 0.18,
        # ONE SPRIG per cluster (user 2026-06-22: "2-4 leaves per cluster"). Chris's
        # hand-built card IS a 4-leaf twig sprig (london_plane_cluster.png), so a
        # single card per placement = his 2-4 leaves. Stacking N cards (default 35,
        # or even 4) re-creates the "tight green ball". The leaf RULE already puts a
        # sprig at every branch tip, so the crown fills from many single sprigs at
        # varied orientations, not from packing each placement into a sphere.
        "cards_per_cluster": 1,
        "trunk_radius_factor": 1.12,  # stout, heavy plane bole (BRIEF §1)
        "base_seed": 200,
        "seed_step": 31,
        # High census (~1.7k, formal rows) → tiling visible; widen to 7. Variants span
        # crown width + bole height (free-form ↔ pollarded-knuckled span, BRIEF §7).
        # Camouflage bark = the hero identity, wired as tree_bark.gdshader Style 2
        # (london_plane→bstyle 2 in tree_builder.gd); patch scale/coverage tuned 2026-06-19.
        # n_variants kept at 7 as the SPANNING DENOMINATOR; pin_variant ships only the
        # approved v3 form so each tier's GLB is single-mesh → runtime n_variants=1 →
        # no second variant can populate (fixes the LOD see-through band at the asset
        # level; [[project_tree_lod_disappearance_bug]]). v3 = the user-confirmed good
        # model (the new design, not the older bare-apex variants 0-2).
        "n_variants": 7,
        "pin_variant": 3,
        # SPECIES variant_spans = the MATURE (l) ranges (s and m define their OWN
        # tier variant_spans; only l falls through to these). Span the mature
        # decurrent candelabra FORM: low fork, broad spreading crown, weak leader.
        # Centred on the verified lp_l_final recipe (explore_skeleton, 2026-06-22 s4).
        "variant_spans": {
            "branch_angle": [56, 64],            # crown spread (mature = horizontal)
            "branch_start": [0.20, 0.28],        # fork/bole height — mature forks LOW
            "branch_length_ratio": [0.50, 0.60], # limb reach → broad mature crown width
            "up_attraction": [0.30, 0.40],       # weak leader ↔ spreading scaffold (decurrent)
        },
        "tiers": {
            # Young street/lawn planes are ~1/3 of the census (327 <6" DBH, 222
            # 6-12"; 2026-06-19). A young plane is UPRIGHT PYRAMIDAL/CONICAL with a
            # still-dominant leader that forks HIGHER and spreads into the broad
            # decurrent candelabra only with age (size-chart ref 6e6cb11fdc). So
            # the sapling override pulls the new spreading base BACK toward an
            # upright conical young habit — but DENSE (not a sparse whip): the ref
            # 3D model shows juveniles clad with twigs from low trunk to a leafy
            # apex. Tier ramps leader-dominance down + spread up s→m→l.
            "s": {"target_h": 9, "height_range": [7, 13],
                # REFERENCE-GROUNDED PROPORTION (2026-06-21, size-chart 6e6cb11fdc):
                # a real young plane is a BROAD DENSE cone (aspect ~0.4-0.45) clad
                # from ~1.5-2m, trunk mostly hidden — NOT the narrow (aspect 0.16)
                # bare-trunked pole the old override built. The broadening params
                # (branch_start/length_ratio/up_attraction/angle) MUST live in a
                # tier variant_spans, not skeleton_overrides: the species spans
                # otherwise clobber them back to the mature ranges (the bug found
                # this session). None touch sub_density → no mesher-crash risk.
                "variant_spans": {
                    # REFERENCE-MEASURED RETUNE (2026-06-21). Trustworthy renders (post
                    # --import fix) + a leaf-mass histogram on london_plane_s.glb proved
                    # the old spans made a NARROW LEANING COLUMN: 71-93% of leaf mass sat
                    # inside a 1m radius, foliage skirted to the ground (Y 0.00), and the
                    # crown leaned to one side. Refs (size-chart 6e6cb11fdc + nursery
                    # morton-circle) want a BROAD upright-conical young crown on a CLEAR
                    # BOLE. Fix = firmer leader (kill lean) + longer/flatter laterals
                    # (push mass into the 1-3m rings) + higher branch_start (bare bole).
                    "branch_start": [0.16, 0.26],        # bole ~16-26% (refs show foliage from ~1.5m on a 9m young tree); [0.24,0.34] read TOO top-heavy
                    "branch_length_ratio": [0.60, 0.74], # KEEP length (user 2026-06-21 PM: "keep the branches about as long"); narrow the crown by WINDING UP, not shortening
                    # NARROW UPRIGHT YOUNG HABIT (user 2026-06-21 PM, morton-circle 3-part
                    # nursery ref): young planes wind their limbs STEEPLY UPWARD into a
                    # narrow crown, not spread horizontally. The total-tree diameter was
                    # reading too wide for that habit. Supersedes the older 6e6cb11fdc
                    # size-chart "broad young cone" call. Steepen + wind up, same length:
                    "up_attraction": [0.46, 0.58],       # moderate upward arc — enough to wind the limbs up into the teardrop, not so much it spikes into a narrow column (the [0.52,0.64] over-steepened to a sparse spike)
                    "branch_angle": [50, 62],            # moderate (was [58,72] too wide, [44,56] too steep/spiky) — lower-middle limbs reach out to give the teardrop its BODY; the Flame crown + angle_variation taper the apex
                },
                "skeleton_overrides": {
                    "crown_shape": "Conical",      # TEARDROP via Conical (user 2026-06-21 PM, refs 6e6cb11fdc + morton-circle): Conical = BROAD base tapering to apex = the teardrop's broad lower-middle + tapered top, foliage from low. (Tried "Flame" — it bulged top-heavy with a bare lower crown, the OPPOSITE of a teardrop. The teardrop fix is moderate WIDTH + DENSITY, not the crown-shape enum.)
                    "branch_end": 0.97,            # branches almost to the apex so the TOP carries leaf clusters (user 2026-06-21: "the top of the tree must get clusters"); 0.92 left a bare leader spike
                    "branch_angle_variation": 0.55,  # was 0.46 — stronger height envelope: top limbs steepen (taper the apex), lower limbs stay broad → the teardrop taper
                    "branch_flatness": 0.45,       # was 0.30 — KEY breadth lever: laterals spread sideways into a full crown
                    "crown_base_size": 0.5,        # moderate teardrop body (0.6 too wide, 0.35 too narrow/sparse) — gives the Flame crown a broad rounded lower-middle without the old horizontal sprawl
                    "branch_gravity": 4.0,         # 2.5->4.0 (user 2026-06-21 PM weight model): the length gradient now makes the LOWER branches longer, so gravity sags THEM more (longer lever) → "heavier, less upward" droop that rounds the teardrop's broad lower-middle, while the short upper branches stay ascending. (Earlier the lean came from one-sided droop; the rounder radial spread of branch_angle_variation 0.55 + straight leader should keep this even — verify in winter.)
                    "sub_gravity": 4.0,            # was species 10.0 — heavy sub-branch droop was the main source of the one-sided lean
                    "trunk_randomness": 0.18,      # was species 0.32 — straighter young leader (less curve → less lean)
                    "branch_start_radius": 0.50,   # finer young limbs
                    # RICHER SKELETON, SPARSER LEAVES (user 2026-06-21: "more branches
                    # running to more twigs, but not as many leaf clusters total"). Build out
                    # the branch→twig hierarchy so the STRUCTURE shows (like the nursery ref),
                    # then distribute fewer clusters on it. More forks (branch_split_prob
                    # 0.5→0.62) + more twigs (sub_density 1.15→1.35, longer via sub_length_ratio
                    # 0.18) + a touch more primaries (branch_density 0.95→1.0). Held below the
                    # known crash band (sub_density 1.5 / branch_density 1.05 each crashed 2/7).
                    # MORE BRANCHES fill the gaps (user 2026-06-21: "the gaps can get filled
                    # in by more branches"; "same number of leaves on more branches"). Push the
                    # skeleton denser — branch_density 1.0→1.1, branch_split_prob 0.62→0.70,
                    # sub_density 1.35→1.45 (just under the 1.5 crash point) — and DROP leaf
                    # density (below) so total clusters stay ~constant, just spread over more
                    # branches. The fork-test auto-dodges any seed the denser skeleton crashes.
                    # NATURAL DISTRIBUTION (user 2026-06-22, screenshots cpw_000-003 +
                    # wireframe ref london-plane-tree-09-02): the prior 1.1/0.70/1.45
                    # made "not many main branches, but the ones there have a confusion
                    # of sub- and sub-sub-branches". The real plane (wireframe + size-
                    # chart 6e6cb11fdc) = a FEW-to-MANY CLEAN scaffold limbs off the
                    # trunk, each ramifying into fine twigs only toward the PERIPHERY —
                    # clean main limbs, leafy shell at the ends. Fix = MORE primaries
                    # off the trunk (branch_density 1.1→1.3), CLEANER primaries (split
                    # 0.70→0.50 so a limb is a distinct limb, not a fork-tangle), and
                    # FAR FEWER confused secondaries (sub_density 1.45→0.85, back near
                    # the species "finer twig haze so the thick limbs read clearly" 0.7;
                    # sub_split stays the species 0.3 = minimal sub-sub). The big
                    # sub_density drop frees mesher headroom for the higher branch_density
                    # (net topology ≈ lower), so crash risk does not rise.
                    "branch_density": 1.3, "branch_split_prob": 0.50, "sub_density": 0.85,
                    # RAMIFICATION CAP on _s (user 2026-06-22 s4 "all tiers incl. s"):
                    # was inheriting species sub_split_prob (now the hard 0.10 l cap).
                    # _s limbs are shortest (~9m × 0.6-0.7) so they ramify the least —
                    # the hard cap would thin the APPROVED sapling crown to see-through
                    # (the small-crown lesson). 0.24 (down from the old 0.30) is a LIGHT
                    # cap: applies the principle species-wide while keeping _s close to
                    # its approved density. Re-review _s after regen; push harder only if
                    # the user wants more cap.
                    "sub_split_prob": 0.24,
                    "sub_length_ratio": 0.18,
                    "sub_dist_start": 0.05,  # twigs emerge near the branch base/interior (user 2026-06-21: "twigs come off the branches closer to the interior"), not just the outer 80% (was 0.2)
                    # Saplings are proportionally SLENDER (trunk dia scales faster than
                    # height): a 9m young plane is ~6-8" DBH, not the ~14" the 1.12
                    # mature factor gives. 0.55 → ~7" DBH at 9m (user 2026-06-19).
                    "trunk_radius_factor": 0.55,
                    # ORGANIC BRANCH CURVE (user 2026-06-21, in-game: "the branches
                    # are all straight lines... need to look more organic"). resolution
                    # = SEGMENTS PER METRE, so a sapling sub-branch (~2m) at the
                    # species sub_resolution 0.72 gets only ~1-2 segments = a literal
                    # straight line with nothing to bend. Raise resolution so short
                    # limbs/twigs carry enough segments to curve, and lift the
                    # per-segment randomness (now per-species, defaults 0.5/0.6) so
                    # they wander organically instead of ruler-straight. _s is the
                    # cheap tier (~11-20k verts) so the added segments are within
                    # budget; resolution grows verts LINEARLY without the topological
                    # mesher-crash risk of density/splits (the fork-test still dodges
                    # any seed that crashes).
                    # SMOOTHER (user 2026-06-21: "make them smoother if that doesn't
                    # cost too much gpu"). The first pass (1.3/2.0) curved the limbs
                    # but the curve read as a KINKED POLYLINE — too few segments per
                    # arc. Push resolution higher (2.2/3.2) so each bend resolves as a
                    # smooth arc; with the same per-segment randomness, more segments
                    # means each takes a smaller step => smoother wander, not jitter.
                    # _s stayed ~10-19k verts (the near-tier sapling), so even doubled
                    # this is well within the 3060 Ti budget.
                    "branch_resolution": 2.2, "sub_resolution": 3.2,
                    "branch_randomness": 0.7, "sub_randomness": 0.85}},  # closes skeleton_overrides + "s" tier
            # YOUNG-ADULT (~22m, transitional, 2026-06-22 s4 redesign): leader giving
            # way, crown opening to an oval/vase, higher cleaner bole, NARROWER + more
            # upright than the mature l (aspect ~0.6-0.7). The stale pre-s4 m read too
            # narrow/sparse/leaning with an S-curved bole — root causes: crown_base_size
            # was the unset-0.0 narrow-cone clamp, trunk_randomness 0.32 + sub_gravity
            # 10 drove the lean, and the species (mature) variant_spans clobbered its
            # skeleton_overrides. Fix: own variant_spans (younger ranges) + width/bole/
            # density overrides. Form verified via explore lp_m_full.
            "m": {"target_h": 22, "height_range": [15, 25],
                "variant_spans": {
                    "branch_angle": [52, 60],            # more upright than mature l
                    "branch_start": [0.26, 0.34],        # higher, cleaner young-adult bole
                    "branch_length_ratio": [0.44, 0.52], # narrower oval crown (vs l's 0.50-0.60)
                    "up_attraction": [0.40, 0.50],       # leader still GIVING WAY (vs l's weak 0.30-0.40)
                },
                "skeleton_overrides": {
                    "crown_base_size": 0.62,       # narrower oval than mature l's 0.75
                    "branch_end": 0.94,            # branches reach near the apex so the apex-cladding gate can leaf the top (0.86 left a bare leader spike — the s4b top-stick)
                    "branch_density": 0.95,        # denser young primaries (more body); under the ~1.05 mesher crash band
                    "sub_density": 0.92,           # fuller young twig structure
                    "sub_split_prob": 0.22,        # CAP, scale-appropriate: lighter than l's 0.10. m's shorter limbs ramify far less, so l's hard cap left m too sparse (explore lp_m_final ~8k faces); 0.22 keeps a full crown while still capping the deep haze.
                    "branch_split_prob": 0.52,     # CAP, lighter than l's 0.45
                    "trunk_randomness": 0.20,      # straight young bole (kill the old S-curve/lean)
                    "sub_gravity": 6.0,            # less one-sided lean (species 10.0 drove it on the stale m)
                }},
            # full decurrent candelabra = species base + species variant_spans
            # (verified lp_l_final). PLUS the hard RAMIFICATION CAP: at 30m the
            # split-prob lever can't bound depth (MEASURED: still ramified to depth
            # 11, ~9.5k clusters, 53MB even at sub_split 0.10 — forking is per-segment
            # so depth grows exponentially with the 16.5m limb length). skeleton_max_depth
            # prunes geometry past tertiary/quaternary directly (height-independent),
            # so the card sits at the terminal tip with no bare filaments past it.
            # m/s don't need it — their shorter limbs are already capped by split-prob.
            "l": {"target_h": 30, "height_range": [25, 35],
                  # L-TIER = PARSIMONIOUS (v2) DENSITY (Chris 2026-07-02): the big
                  # crowns get the thinner, less-backlit-opaque canopy while s/m keep
                  # the fuller v1 look. These 3 card levers override the species-level
                  # (v1) values for the l tier only (foliage reads them from sp_variant).
                  # Mirrors london_plane_v2's parsimony levers. In-situ park test.
                  "skeleton_overrides": {"skeleton_max_depth": 4,
                      "card_rule_depth_keep": {1: 0.04, 2: 0.40, 3: 0.62},  # v1 {1:.05,2:.60,3:1.0}
                      "card_half_factor": 1.00,                             # v1 implicit 1.20
                      "card_rule_spacing": 0.72}},                          # v1 0.55
        },
    },

    # ----- Columnar / spur shoots -----
    "ginkgo": {
        "name": "Ginkgo (Ginkgo biloba)",
        "crown_shape": "Conical",
        # Upright, irregular/angular when young → broader with age (BRIEF §1).
        # H 15–25m, spread 6–12m → aspect ~0.5–0.7. Stiff ascending branches,
        # well-separated (open architecture). Mesher known to crash at dense+highres
        # large scale — keep branch_density ≤ 0.8 and sub_min_height=999.
        "trunk_frac": 0.30,
        "trunk_shape": 0.8,
        "up_attraction": 0.8,         # Strong central leader (upright habit)
        "trunk_randomness": 0.3,
        "branch_start": 0.28,
        "branch_end": 0.95,
        "branch_density": 0.8,         # Reduced from 1.2 (crashes mesher at large scale)
        "branch_length_ratio": 0.46,   # Reach for 0.5-0.7 aspect (BRIEF §1); spans widen further
        "branch_start_radius": 0.42,   # Stiff angular limbs (ginkgo branches are notable)
        "branch_angle_variation": 0.35,  # Irregular ascending → spreading with age
        "branch_angle": 44,            # Slightly wider base for spread; spans cover 36-52°
        "branch_gravity": 5.0,
        "branch_stiffness": 0.3,
        "branch_up_attraction": 0.5,
        "branch_split_prob": 0.4,
        "branch_split_angle": 30.0,
        "branch_flatness": 0.15,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 1.3,
        "sub_length_ratio": 0.08,      # Short spur shoots
        "sub_angle": 55,
        "sub_gravity": 6.0,
        "sub_stiffness": 0.2,
        "sub_up_attraction": 0.1,
        "sub_split_prob": 0.15,
        "sub_split_angle": 25.0,
        "sub_flatness": 0.2,
        "sub_resolution": 1.0,
        "bark_color": (0.38, 0.34, 0.28),
        "bark_roughness": 0.90,
        "leaf_shape": "fan",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 557,
        "leaf_scale": 0.65,  # Ginkgo ~7cm fan
        "leaf_cluster_size_range": (0.27, 0.60),
        "leaf_flatten_range": (0.50, 0.70),
        "leaf_density": 0.55,  # canopy density (0-1, from real-world LAI) LAI 2.5-4.0
        "target_cluster_count_l": 600,  # LAI 3-4; ginkgo fan cluster tops
        "foliage_radius_threshold": 0.40,  # No sub-branches → main branches are thick
        "foliage_min_depth": 0,
        "foliage_extent_range": (0.15, 0.95),
        "sparse_branch_boost": 2.0,
        "sub_min_height": 999,          # Spur shoots crash mesher; use primary-only
        "base_seed": 50,
        "seed_step": 31,
        # High census (~1.8k), irregular tiling very visible; widen to 6 variants.
        # Spans the young-narrow-angular ↔ old-broader age axis (BRIEF §7):
        # branch_angle (ascending-tight young ↔ wider spreading old) +
        # branch_length_ratio (shorter sparse young ↔ longer fuller old).
        "n_variants": 6,
        "variant_spans": {
            "branch_angle": [40, 58],          # narrow ascending young ↔ wider spreading old
            "branch_length_ratio": [0.50, 0.72],  # shorter young ↔ longer older crown
        },
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.5, "branch_split_prob": 0.25, "sub_density": 0.3}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 0.7, "branch_split_prob": 0.35, "sub_density": 0.8}},
            "l": {"target_h": 22, "height_range": [20, 25]},
        },
    },

    # ----- Large-leaved ornamental -----
    "magnolia": {
        "name": "Saucer Magnolia",
        # Low-branching, BROAD spreading — _s-only (sub-canopy ornamental). Often
        # multi-stemmed from near the base. Target aspect ~0.80-1.00 (spread 6-9m
        # on H 6-9m): WIDER THAN TALL or equal. Smooth light-gray bark, large
        # obovate leaves. (BRIEF: low multi-stem, wider than tall, sculptural bare.)
        # NOTE: do NOT add m/l tiers — runtime requests _s only (TIER_BOUNDS).
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.12,            # Very low branching / near-ground fork
        "trunk_shape": 0.45,
        "up_attraction": 0.30,         # Little vertical pull — spread outward
        "trunk_randomness": 0.65,      # Multi-stem character (gnarled, asymmetric)
        "branch_start": 0.10,          # Near-ground start — very low fork
        "branch_end": 0.88,
        "branch_density": 1.3,
        "branch_length_ratio": 0.65,   # LONG spreading limbs — aspect 0.80-1.0
        "branch_start_radius": 0.42,   # Stout smooth limbs (sculptural character)
        "branch_angle_variation": 0.20, # Low spreading, not strongly upright
        "branch_angle": 65,            # Wide spread angle for broad crown
        "branch_gravity": 4.5,         # Low gravity — stiff horizontal spread
        "branch_stiffness": 0.28,
        "branch_up_attraction": 0.18,  # Mostly spread outward, slight upward tendency
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.30,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.2,
        "sub_density": 1.1,
        "sub_length_ratio": 0.14,
        "sub_angle": 50,
        "sub_gravity": 8.0,
        "sub_stiffness": 0.14,
        "sub_up_attraction": 0.15,
        "sub_split_prob": 0.25,
        "sub_split_angle": 28.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.68, 0.65, 0.60),  # Light gray smooth bark (feature)
        "bark_roughness": 0.62,
        "leaf_shape": "ovate",
        "leaf_n": 45,
        "leaf_tex_size": 1024,
        "leaf_seed": 663,
        "leaf_scale": 1.25,  # Magnolia ~14cm obovate
        "leaf_cluster_size_range": (0.52, 1.00),  # Large clusters for big obovate leaves
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.80,  # LAI 3.5-5 → moderate-dense; thick waxy leaves
        "target_cluster_count_l": 700,   # _s tier gets 15% = 105 clusters (was 72)
        "base_seed": 500,
        "seed_step": 29,
        # 5-6 variants (high census, _s-only is cheap). Spans: crown width + lean.
        "n_variants": 6,
        "variant_spans": {
            "branch_angle": [58, 73],       # moderate spread ↔ wide/flat crown
            "trunk_randomness": [0.45, 0.75], # upright-trunked ↔ multi-stem lean
        },
        "tiers": {
            "s": {"target_h": 7, "height_range": [5, 9]},
        },
    },

    # ----- Generic fallback -----
    "deciduous": {
        "name": "Generic Deciduous",
        "crown_shape": "Spherical",
        # Catch-all for unmapped census genera (BRIEF §1): a believable AVERAGE
        # rounded broadleaf — moderate everything, wide variation envelope so a
        # cluster never tiles. Aspect ~0.6–0.7 (like oak template). LAI 4.0-5.0.
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.55,
        "trunk_randomness": 0.6,
        "branch_start": 0.22,
        "branch_end": 0.95,
        "branch_density": 1.2,
        "branch_length_ratio": 0.38,   # moderate spread → aspect ~0.6-0.7
        "branch_start_radius": 0.45,   # mid-weight limbs (believable average)
        "branch_angle_variation": 0.30,  # ascending-then-spreading (unremarkable broadleaf)
        "branch_angle": 50,
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.5,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 1.4,
        "sub_length_ratio": 0.14,
        "sub_angle": 48,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.3,
        "sub_split_angle": 32.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.32, 0.27, 0.20),
        "bark_roughness": 0.85,
        "leaf_shape": "elliptic",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 700,
        "leaf_scale": 1.0,  # generic average broadleaf
        "leaf_cluster_size_range": (0.33, 0.75),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.75,  # canopy density (0-1, from real-world LAI) LAI 4.0-5.0
        "target_cluster_count_l": 600,
        "base_seed": 700,
        "seed_step": 31,
        # Wide variation envelope (BRIEF §7): can cluster anywhere, tiling risk high.
        # Spans crown spread + vertical emphasis — every instance looks different.
        "n_variants": 6,
        "variant_spans": {
            "branch_angle": [44, 58],          # crown spread: ascending-narrow ↔ spreading
            "branch_up_attraction": [0.28, 0.45],  # vertical emphasis variation
        },
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.7, "branch_split_prob": 0.30, "sub_density": 0.4}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.40, "sub_density": 1.0}},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },
}

# ---------------------------------------------------------------------------
# london_plane_v2 — PARSIMONY A/B (2026-07-02, Chris). A thinner, less-opaque
# lod0 of the London plane to test whether v1's canopy is overdone: v1 reads
# almost fully OPAQUE when backlit (sun directly behind → no dappled light).
# Built as a shallow copy of london_plane so it shares the IDENTICAL skeleton
# (same base_seed/pin_variant/n_variants → same trunk & branches), bark, leaf
# card texture, and variant pin — ONLY the leaf-card DENSITY levers differ. So a
# side-by-side in the garden isolates coverage/opacity as the single variable,
# and v2 auto-tracks any future v1 change (nested dicts shared read-only).
# Levers (all reduce canopy coverage so backlight dapples through):
#   • card_rule_depth_keep — fewer branches bear cards → sky-gaps between clumps
#     (the naturalistic thinning: removes whole sprigs, not laces every card).
#   • card_half_factor — smaller cards → less neighbour overlap → light leaks.
#   • card_rule_spacing — wider inboard spacing → the guaranteed tip sprig
#     dominates, fewer fill cards down each branch.
# Skeleton, apex_band (apex never bare), cards_per_cluster are UNCHANGED.
SPECIES["london_plane_v2"] = {
    **SPECIES["london_plane"],
    "name": "London Plane v2 (parsimonious)",
    "card_rule_depth_keep": {1: 0.04, 2: 0.40, 3: 0.62},  # v1 {1:0.05, 2:0.60, 3:1.0}
    "card_half_factor": 1.00,                              # v1 implicit 1.20
    "card_rule_spacing": 0.72,                             # v1 0.55
}

# Crown shape name -> Mtree CrownShape enum
CROWN_MAP = {
    "Spherical": "Spherical",
    "Conical": "Conical",
    "Hemispherical": "Hemispherical",
    "Cylindrical": "Cylindrical",
    "Flame": "Flame",
    "TaperedCylindrical": "TaperedCylindrical",
    "InverseConical": "InverseConical",
    "TendFlame": "TendFlame",
}


# ===========================================================================
# TREE GENERATION
# ===========================================================================

def _test_seed_safe(sp, height, seed):
    """Fork a child process to test if this seed crashes Mtree's mesher.

    The Mtree ManifoldMesher segfaults at certain seed+height+parameter
    combinations. Since SIGSEGV kills the process, we fork a throwaway
    child to probe the seed. If the child exits cleanly, the seed is safe.
    If it crashes, the parent survives and can try another seed.

    Returns True if seed is safe, False if it crashes.
    """
    pid = os.fork()
    if pid == 0:
        # Child process — try generating the skeleton
        try:
            tree = _build_mtree(sp, height, seed)
            mesher = m_tree.ManifoldMesher()
            mesher.radial_n_points = sp.get("radial_pts", RADIAL_PTS)
            mesher.smooth_iterations = SMOOTH_ITER
            mesher.mesh_tree(tree)
            os._exit(0)
        except Exception:
            os._exit(1)
    else:
        # Parent — wait for child
        _, status = os.waitpid(pid, 0)
        if os.WIFSIGNALED(status):
            return False  # child killed by signal (segfault)
        return os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0


def _build_mtree(sp, height, seed):
    """Build the Mtree tree object (no meshing). Used by both test and generate."""
    tree = m_tree.Tree()

    trunk = m_tree.TrunkFunction()
    trunk.seed = seed
    trunk.length = height
    # Per-species bole stoutness (default 1.0). London plane reads as a stout,
    # heavy bole; thin-trunk species leave it at 1.0.
    trunk_rf = sp.get("trunk_radius_factor", 1.0)
    trunk.start_radius = height * 0.018 * trunk_rf
    trunk.end_radius = height * 0.005 * trunk_rf
    trunk.shape = sp["trunk_shape"]
    trunk.up_attraction = sp["up_attraction"]
    trunk.resolution = sp["branch_resolution"]
    trunk.randomness = sp["trunk_randomness"]

    br = m_tree.BranchFunction()
    br.seed = seed + 1
    br.distribution.start = sp["branch_start"]
    br.distribution.end = sp["branch_end"]
    br.distribution.density = sp["branch_density"]
    br.distribution.phillotaxis = 137.5
    br.gravity.strength = sp["branch_gravity"]
    br.gravity.stiffness = sp["branch_stiffness"]
    br.gravity.up_attraction = sp["branch_up_attraction"]
    br.split.probability = sp["branch_split_prob"]
    br.split.angle = sp["branch_split_angle"]
    br.split.radius = 0.8
    br.flatness = sp["branch_flatness"]
    br.break_chance = sp["branch_break_chance"]
    br.resolution = sp["branch_resolution"]
    # Branch LENGTH gradient up the trunk (user 2026-06-21 PM): lower branches are
    # OLDER -> longer, upper branches are YOUNGER -> shorter. This is the signature of
    # natural growth — the teardrop/conical taper should EMERGE from the length
    # gradient, not be imposed by the crown envelope. SimpleCurveProperty maps the
    # branch's attach-position along the trunk (t=0 base -> t=1 top) to a length:
    # y_min at the base (long), y_max at the top (short), shaped by power (>1 keeps
    # the lower-middle long and tapers only near the apex -> teardrop). Falls back to
    # the legacy ConstantProperty when a species doesn't set branch_length_top_factor.
    _blr = sp["branch_length_ratio"]
    _bl_top = sp.get("branch_length_top_factor")
    if _bl_top is not None:
        _len_curve = m_tree.SimpleCurveProperty()
        _len_curve.y_min = height * _blr                      # trunk base: full length (long, old)
        _len_curve.y_max = height * _blr * float(_bl_top)     # trunk top: shortened (young)
        _len_curve.power = float(sp.get("branch_length_power", 1.5))
        _lw = m_tree.PropertyWrapper()
        _lw.set_simple_curve_property(_len_curve)
        br.length = _lw
    else:
        br.length = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(height * _blr)
        )
    # Branch base radius RELATIVE TO PARENT (Mtree semantics). 0.4 = thin twigs
    # off a dominant central spire (the "pole + twigs" defect); higher reads as
    # major tapering limbs. Per-species via branch_start_radius (default 0.4).
    br.start_radius = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(sp.get("branch_start_radius", 0.4)))
    br.randomness = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(sp.get("branch_randomness", 0.5)))
    br.start_angle = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(float(sp["branch_angle"]))
    )
    crown_name = CROWN_MAP.get(sp["crown_shape"], "Spherical")
    br.crown.shape = getattr(m_tree.CrownShape, crown_name)
    # Height-based branch-angle envelope: positive = limbs sweep UP at the top,
    # droop at the base (oak's tiered droop→horizontal→ascend; the elm vase's
    # ascending limbs). Default 0 = uniform (legacy behaviour, no regression).
    br.crown.angle_variation = sp.get("branch_angle_variation", 0.0)
    # Crown WIDTH attractor. Mtree's crown.base_size defaults to 0.0 — a narrow
    # cone that pulls branch tips inward regardless of branch_length/angle (this
    # is why long horizontal limbs still produced a thin plume; measured 2026-06-21).
    # Raising it widens the crown envelope: base_size 0.0→asp~0.50, ≥1.0→asp~0.80
    # (saturates). Only set when a species opts in, so existing trees are unchanged.
    _cbs = sp.get("crown_base_size")
    if _cbs is not None:
        br.crown.base_size = float(_cbs)

    sub_min_h = sp.get("sub_min_height", 0)
    if sp["sub_density"] > 0 and height >= sub_min_h:
        sub = m_tree.BranchFunction()
        sub.seed = seed + 2
        sub.distribution.start = sp.get("sub_dist_start", 0.2)  # how far along the parent the twigs begin; low = twigs emerge near the interior/base
        sub.distribution.end = sp.get("sub_dist_end", 0.95)
        sub.distribution.density = sp["sub_density"]
        sub.gravity.strength = sp["sub_gravity"]
        sub.gravity.stiffness = sp["sub_stiffness"]
        sub.gravity.up_attraction = sp["sub_up_attraction"]
        sub.split.probability = sp["sub_split_prob"]
        sub.split.angle = sp["sub_split_angle"]
        sub.flatness = sp["sub_flatness"]
        sub.resolution = sp["sub_resolution"]
        sub.length = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(height * sp["sub_length_ratio"])
        )
        sub.start_radius = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(sp.get("sub_start_radius", 0.25)))
        sub.randomness = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(sp.get("sub_randomness", 0.6)))
        sub.start_angle = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(float(sp["sub_angle"]))
        )
        br.add_child(sub)

    trunk.add_child(br)
    tree.set_trunk_function(trunk)
    tree.execute_functions()
    return tree


def generate_tree_skeleton(sp, height, seed):
    """Generate trunk + branches mesh using Mtree. Returns C++ mesh."""
    tree = _build_mtree(sp, height, seed)
    mesher = m_tree.ManifoldMesher()
    mesher.radial_n_points = sp.get("radial_pts", RADIAL_PTS)
    mesher.smooth_iterations = SMOOTH_ITER
    return mesher.mesh_tree(tree)


def _extract_leaf_positions_tips(mesh_obj, sp, target_height, rng, tier="l"):
    """Fallback: tip-only leaf placement when branch attributes are unavailable.

    Uses the 'radius' vertex attribute: small radius = branch tip.
    Clusters nearby tips and returns placement positions + sizes.
    """
    mesh = mesh_obj.data
    verts = mesh.vertices
    n = len(verts)
    if n == 0:
        return []

    radius_attr = mesh.attributes.get("radius")
    if not radius_attr:
        return []

    radii = [radius_attr.data[i].value for i in range(n)]
    tip_threshold = 0.015 + target_height * 0.0005
    tip_positions = []
    for i in range(n):
        if radii[i] < tip_threshold:
            v = verts[i].co
            if math.isnan(v.x) or math.isnan(v.y) or math.isnan(v.z):
                continue
            if math.isinf(v.x) or math.isinf(v.y) or math.isinf(v.z):
                continue
            tip_positions.append(Vector((v.x, v.y, v.z)))

    if not tip_positions:
        return []

    density = sp.get("leaf_density", 0.75)
    base_cell = target_height * 0.035
    cell_size = base_cell / max(density, 0.3)

    clusters = {}
    for pos in tip_positions:
        key = (
            int(pos.x / cell_size),
            int(pos.y / cell_size),
            int(pos.z / cell_size),
        )
        if key not in clusters:
            clusters[key] = []
        clusters[key].append(pos)

    # Card size: uniform across all tiers (age/size variants, not LOD tiers)
    size_mult = 1.4

    placements = []
    lo, hi = sp["leaf_cluster_size_range"]
    flo, fhi = sp["leaf_flatten_range"]
    for cell_tips in clusters.values():
        cx = sum(p.x for p in cell_tips) / len(cell_tips)
        cy = sum(p.y for p in cell_tips) / len(cell_tips)
        cz = sum(p.z for p in cell_tips) / len(cell_tips)
        size = rng.uniform(lo, hi) * (target_height / 25.0) * size_mult
        flatten = rng.uniform(flo, fhi)
        placements.append((Vector((cx, cy, cz)), size, flatten))

    return placements


def extract_leaf_positions(mesh_obj, sp, target_height, rng, tier="l"):
    """Branch-walk placement: place leaf clusters along branch surfaces.

    Uses Mtree vertex attributes (radius, hierarchy_depth, branch_extent,
    stem_id) to place clusters at intervals along all qualifying branches,
    with density calibrated against published LAI data.

    Falls back to tip-only placement if branch attributes are unavailable.
    """
    mesh = mesh_obj.data
    n = len(mesh.vertices)
    if n == 0:
        return []

    # Check for Mtree attributes
    radius_attr = mesh.attributes.get("radius")
    hd_attr = mesh.attributes.get("hierarchy_depth")
    be_attr = mesh.attributes.get("branch_extent")
    si_attr = mesh.attributes.get("stem_id")

    if not radius_attr:
        return []

    has_branch_attrs = all([hd_attr, be_attr, si_attr])
    if not has_branch_attrs:
        return _extract_leaf_positions_tips(mesh_obj, sp, target_height, rng, tier)

    # Read attributes into numpy arrays
    radii = np.zeros(n)
    depths = np.zeros(n)
    extents = np.zeros(n)
    stems = np.zeros(n)
    radius_attr.data.foreach_get("value", radii)
    hd_attr.data.foreach_get("value", depths)
    be_attr.data.foreach_get("value", extents)
    si_attr.data.foreach_get("value", stems)

    # Read vertex positions
    coords = np.zeros(n * 3)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(n, 3)

    # Filter NaN/inf
    valid = np.all(np.isfinite(coords), axis=1)

    # Species foliage parameters (with defaults)
    r_thresh = sp.get("foliage_radius_threshold",
                      FOLIAGE_DEFAULTS["foliage_radius_threshold"])
    min_depth = sp.get("foliage_min_depth",
                       FOLIAGE_DEFAULTS["foliage_min_depth"])
    ext_start, ext_end = sp.get("foliage_extent_range",
                                FOLIAGE_DEFAULTS["foliage_extent_range"])
    interval_frac = sp.get("placement_interval_factor",
                           FOLIAGE_DEFAULTS["placement_interval_factor"])
    droop = sp.get("droop_factor", FOLIAGE_DEFAULTS["droop_factor"])
    boost = sp.get("sparse_branch_boost",
                   FOLIAGE_DEFAULTS["sparse_branch_boost"])

    # Target cluster count — fewer clusters on lower tiers since each card
    # is much larger (3× for _m, 7× for _s) and covers more canopy volume.
    # Per-species `tier_fraction` override lets a species lift its sapling
    # foliage budget (coverage-conserving sapling fill, 2026-06-21).
    target_l = sp.get("target_cluster_count_l", 600)
    tier_fraction = sp.get("tier_fraction", {"l": 1.0, "m": 0.40, "s": 0.15})
    target_count = int(target_l * tier_fraction.get(tier, 1.0))

    # Card-size height factor. Cards scale with tree height (a big tree's leaf
    # patch is physically bigger), but the linear (h/25) factor shrinks a 9m
    # sapling's cards to ~0.36× — which, combined with the ~128-cluster cap,
    # reads see-through. A per-species `card_size_floor` lifts that factor for
    # small trees so the AAA "fewer-but-BIGGER cards" rule fills the crown
    # without multiplying overdraw (2026-06-21). Drives cladding spacing, the
    # isolation-prune radius, AND the card render size below so all three stay
    # consistent (bigger cards must be spaced + pruned as bigger cards).
    hscale = target_height / 25.0
    _csfloor = sp.get("card_size_floor")
    if _csfloor is not None:
        hscale = max(hscale, float(_csfloor))

    # Eligible vertices: valid, thin branches, sufficient depth
    eligible = valid & (radii < r_thresh) & (depths >= min_depth)
    eligible_idx = np.where(eligible)[0]

    if len(eligible_idx) == 0:
        print(f"    No eligible vertices for branch-walk, falling back to tips")
        return _extract_leaf_positions_tips(mesh_obj, sp, target_height, rng, tier)

    # Cluster card size in metres (mesh is in metres here) — also drives the
    # continuous-cladding spacing and the isolation prune below.
    _clo, _chi = sp["leaf_cluster_size_range"]
    csize = 0.5 * (_clo + _chi) * hscale * 1.4

    candidates = []
    if sp.get("foliage_continuous"):
        # --- Continuous branch cladding ---
        # Learned from a professional Platanus acerifolia model (ref images in
        # reference_photos/london planetree/): foliage is a DENSE SHEATH running
        # the whole length of every twig, packed so the crown reads as one solid
        # mass that tapers to a leafy apex — not discrete blobs scattered at
        # sampled points (my old probabilistic walk, which gapped badly: it used
        # ~7 of 470 eligible branch verts on a sapling, then padded the rest with
        # floating fill). Here we greedily clad ALL eligible thin-branch verts at
        # a fixed minimum spacing (clusters overlap → continuous), tips first so
        # density rises slightly toward branch ends as in the reference. Because
        # every cluster sits on a twig and neighbours another, there are no gaps
        # and no isolated islands by construction. A spatial-hash grid keeps the
        # min-distance test O(n) for the dense large tier.
        ec = coords[eligible_idx]
        order = np.argsort(-extents[eligible_idx])      # high extent (tips) first
        # Clusters are kept tight to the twig (scatter 0.5), so clad densely
        # enough that the tighter blobs still overlap into a continuous canopy.
        spacing = csize * 0.55
        sp2 = spacing * spacing
        cell = spacing
        grid = {}

        def _too_close(p):
            gx, gy, gz = int(p[0] // cell), int(p[1] // cell), int(p[2] // cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for q in grid.get((gx + dx, gy + dy, gz + dz), ()):
                            if ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
                                    + (q[2] - p[2]) ** 2) <= sp2:
                                return True
            return False

        for k in order:
            p = ec[k]
            if not _too_close(p):
                grid.setdefault((int(p[0] // cell), int(p[1] // cell),
                                 int(p[2] // cell)), []).append(p)
                candidates.append(Vector((p[0], p[1],
                                  p[2] - droop * target_height * 0.05)))
    else:
        # --- Legacy per-stem probabilistic walk (unreviewed species) ---
        stem_ids_arr = stems[eligible_idx].astype(int)
        unique_stems = np.unique(stem_ids_arr)
        for sid in unique_stems:
            mask = eligible & (stems.astype(int) == sid)
            idx = np.where(mask)[0]
            if len(idx) == 0:
                continue
            ext_vals = extents[idx]
            sort_order = np.argsort(ext_vals)
            idx = idx[sort_order]
            ext_sorted = ext_vals[sort_order]
            next_extent = ext_start
            for ii in range(len(idx)):
                e = ext_sorted[ii]
                if e < next_extent:
                    continue
                next_extent = e + interval_frac
                t = (e - ext_start) / max(ext_end - ext_start, 0.001)
                t = max(0.0, min(1.0, t))
                prob = t * t * (3.0 - 2.0 * t) * boost
                if rng.random() < prob:
                    nearby = idx[np.abs(ext_sorted - e) < interval_frac * 0.3]
                    if len(nearby) > 0:
                        centroid = coords[nearby].mean(axis=0)
                    else:
                        centroid = coords[idx[ii]]
                    candidates.append(Vector((centroid[0], centroid[1],
                                  centroid[2] - droop * target_height * 0.05)))

    # Trim to target count if over
    if len(candidates) > int(target_count * 1.2):
        rng.shuffle(candidates)
        candidates = candidates[:target_count]

    # Branch-anchored supplement — if the probabilistic walk under-fills (it is
    # very conservative on young/open crowns: measured 7 of 162 on london_plane
    # _s despite 470 eligible branch verts across 22 stems), top up by sampling
    # the REAL eligible branch verts, weighted toward branch tips where leaves
    # concentrate. Every cluster therefore sits on an actual twig.
    #
    # This REPLACES the old convex-hull "crown-fill", which scattered points in
    # the crown's bounding BOX — on sparse saplings that put ~70% of clusters in
    # empty space, so leaves rendered as blobs floating with no visible branch
    # (user 2026-06-19; sanity check measured 16-30% of _s leaf verts >1.8m from
    # any bark vert, max ~6m). Foliage must attach to geometry; a young plane's
    # crown is simply more open, not padded with floaters.
    if len(candidates) < target_count:
        need = target_count - len(candidates)
        ext_e = extents[eligible_idx]
        w = np.clip((ext_e - ext_start) / max(ext_end - ext_start, 1e-3),
                    0.03, 1.0) ** 1.5
        w = w / w.sum()
        nrng = np.random.default_rng(rng.randint(0, 2**31 - 1))
        pick = nrng.choice(eligible_idx, size=need, p=w)
        # Jitter is SIZE-RELATIVE (was a fixed ±0.10m): fixed metres over-jitter
        # small trees — on a 9m sapling ±0.10m is ~3x larger in MODEL_H-normalised
        # units than on a 30m tree, throwing supplemental cards off-bark (the
        # connectivity gate is normalised, so saplings failed worst). 2026-06-21.
        jit = 0.06 * (target_height / 25.0)  # was 0.10 — jittered centers' outer card corners still cleared the connectivity gate on saplings (2026-06-21)
        for vidx in pick:
            c = coords[vidx]
            candidates.append(Vector((
                c[0] + rng.uniform(-jit, jit),
                c[1] + rng.uniform(-jit, jit),
                c[2] - droop * target_height * 0.05)))

    # --- Upper-crown envelope (replaces the old single-tip apical cap) ---
    # Clothe the woody crown TOP so no bare leader spike or scaffold limb pokes
    # above/through the foliage. The top of a live tree is prime sunlight real
    # estate; bare wood at the apex only reads as winter/dead, not high summer
    # (user 2026-06-19).
    #
    # EVIDENCE (2026-06-19, london_plane _s, instrumented regen): branch-walk
    # finds only ~6 of 162 foliage candidates on sparse young crowns, so the
    # crown is built almost entirely from the synthetic crown-fill above — and
    # that fill samples the convex hull of those few candidates, which tops out
    # at the highest *foliated* branch (eligBranchZmax). That leaves a 0.6-1.3m
    # bare LEADER SPIKE (16-32 bark verts) above the foliage line. Prior apical
    # caps (v1-v3) added only ~5 clusters at the single top vertex and never
    # filled this spike — which is why the bare stick survived every time.
    #
    # FIX: place clusters directly ON the upper-crown bark verts (incl. the
    # depth-0 leader, which the foliage filter excludes), weighted toward the top
    # and biased to sit on/above the wood. Foliage then tracks the real woody
    # envelope, buries the spike, and tapers to the apex. General to all tiers.
    if n > 0:
        zc = coords[:, 2]
        wood_top = float(zc.max())
        wood_bot = float(zc.min())
        crown_h = max(wood_top - wood_bot, 0.5)
        # Band = upper ~40% of the crown's woody height: overlaps the existing
        # foliage line and extends up over the bare leader spike.
        band_lo = wood_top - 0.40 * crown_h
        band = np.where(zc >= band_lo)[0]
        if len(band) > 0:
            # numpy RNG seeded from the python rng → vectorized weighted sampling,
            # still deterministic per variant.
            nrng = np.random.default_rng(rng.randint(0, 2**31 - 1))
            band_z = zc[band]
            # Weight verts toward the top: the leader spike is the sparsest wood
            # and must be fully buried; the lower band only needs touch-up since
            # the branch-walk/crown-fill already covers it.
            w = (band_z - band_lo) ** 1.5 + 0.06 * crown_h
            w = w / w.sum()
            # Count scales with crown height → opaque cap at every tier.
            n_env = max(28, int(round(crown_h * 8)))
            sel = nrng.choice(band, size=n_env, p=w)
            # Size-relative jitter (was fixed ±0.12m xy, +0.18m z): on a sapling
            # those fixed metres pushed envelope cards well above the apex bark
            # (off the connectivity gate). Scale with tree size; keep the small
            # upward bias so the leader spike still gets buried. 2026-06-21.
            ejit = 0.06 * (target_height / 25.0)  # was 0.12 — keep envelope cards tight to apex bark (sapling connectivity)
            ezup = 0.07 * (target_height / 25.0)  # was 0.12 — small upward bias still buries the leader, without floating off it
            for vi in sel:
                candidates.append(Vector((
                    coords[vi, 0] + rng.uniform(-ejit, ejit),
                    coords[vi, 1] + rng.uniform(-ejit, ejit),
                    coords[vi, 2] + rng.uniform(0.0, ezup))))   # sit ON/above the wood, tight

    # --- Prune isolated foliage islands ---
    # A clump of cluster(s) alone on a thin outlying twig reads as foliage
    # floating in open sky, even though it is technically attached to a
    # (near-invisible) branch (user 2026-06-20: lone clump on a hair-thin twig
    # against the sky). Real crowns hold foliage as one CONTIGUOUS canopy, so
    # proximity-to-bark is not enough and a simple neighbour count misses small
    # islands that are dense within themselves. Build the connectivity graph of
    # clusters (edge = within ~2.6 cluster sizes) and drop any connected
    # component too small to be part of the canopy. Coordinates are in metres.
    if len(candidates) > 24:
        pts = np.array([[p.x, p.y, p.z] for p in candidates], dtype=float)
        clo, chi = sp["leaf_cluster_size_range"]
        csize = 0.5 * (clo + chi) * hscale * 1.4
        nb_r = csize * 2.6
        d2 = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1)
        adj = d2 < nb_r * nb_r
        # Connected components via union-find over the adjacency edges.
        nC = len(candidates)
        parent = list(range(nC))

        def _find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        ii, jj = np.where(np.triu(adj, 1))
        for a, b in zip(ii.tolist(), jj.tolist()):
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[ra] = rb
        roots = np.array([_find(i) for i in range(nC)])
        uniq, cnts = np.unique(roots, return_counts=True)
        size_of = dict(zip(uniq.tolist(), cnts.tolist()))
        comp_size = np.array([size_of[r] for r in roots])
        # Keep the main canopy + any substantial lobe; drop small floating islands.
        min_comp = max(12, int(0.05 * nC))
        keep = comp_size >= min_comp
        # Always keep the largest component (safety against an over-strict floor).
        keep |= (comp_size == comp_size.max())
        n_pruned = int((~keep).sum())
        if n_pruned:
            candidates = [c for c, k in zip(candidates, keep) if k]
            print(f"    Pruned {n_pruned} clusters in isolated islands "
                  f"(< {min_comp}-cluster components, edge {nb_r:.2f}m)")

    # Build placements with size and flatten
    lo, hi = sp["leaf_cluster_size_range"]
    flo, fhi = sp["leaf_flatten_range"]
    # Card size: uniform across all tiers. The _s/_m/_l are age/size
    # variants that render simultaneously, not LOD tiers — they all
    # need the same per-cluster detail level.
    size_mult = 1.4

    placements = []
    for pos in candidates:
        size = rng.uniform(lo, hi) * hscale * size_mult
        flatten = rng.uniform(flo, fhi)
        placements.append((pos, size, flatten))

    return placements


def _card_placements_per_branch(mesh_obj, sp, target_height, rng, tier="l"):
    """THE LEAF RULE, for CARDS (user 2026-06-21 PM: "the leaf clusters... are not
    all the way out to the tips. we need to remember what we learned about leaf
    placement with the 3d model").

    Mirrors _distribute_foliage_per_branch's deterministic tip-weighted per-stem
    selection — but emits cluster-CARD placements (pos, size, flatten) instead of
    instancing 3D leaf protos. For each stem_id, sort its eligible (thin) verts
    tip-first (branch_extent desc), GUARANTEE the min_per_branch tip-most clusters,
    then add spaced extras down the branch. No branch tip can be bare, and the
    guaranteed clusters are the tip-most → reaches the ends, tip-weighted. This
    replaces extract_leaf_positions' continuous-clad walk, whose cap/shuffle +
    crown-box supplement bunched clusters INBOARD (the "not out to the tips" read).
    Returns None if the Mtree branch attributes are absent (caller falls back).
    """
    mesh = mesh_obj.data
    n = len(mesh.vertices)
    radius_attr = mesh.attributes.get("radius")
    be_attr = mesh.attributes.get("branch_extent")
    si_attr = mesh.attributes.get("stem_id")
    if not (radius_attr and be_attr and si_attr) or n == 0:
        return None
    max_radius = sp.get("card_rule_max_radius", 0.05)
    min_per_branch = int(sp.get("card_rule_min_per_branch", 1))
    spacing = sp.get("card_rule_spacing", 0.4)
    # CLUSTER PLACEMENT RULE (user 2026-06-22): clusters only on SECONDARY or later
    # branches (no clusters crowding the primary scaffold limbs), and only where the
    # twig is at least a minimum diameter (a sprig needs real wood to sit on, not a
    # sub-pixel filament). min_depth gates hierarchy_depth (trunk=0, primary=1,
    # secondary=2, …); min_tip_radius is the twig-radius floor (metres).
    min_depth = int(sp.get("card_rule_min_depth", 0))
    min_tip_radius = float(sp.get("card_rule_min_tip_radius", 0.0))
    dir_attr = mesh.attributes.get("direction")  # branch growth dir → orient the sprig card's twig outward (same attr the distribute modifier uses)
    depth_attr = mesh.attributes.get("hierarchy_depth")
    radii = np.zeros(n); radius_attr.data.foreach_get("value", radii)
    extents = np.zeros(n); be_attr.data.foreach_get("value", extents)
    stems = np.zeros(n); si_attr.data.foreach_get("value", stems)
    coords = np.zeros(n * 3); mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(n, 3)
    if dir_attr is not None:
        dirs = np.zeros(n * 3); dir_attr.data.foreach_get("vector", dirs)
        dirs = dirs.reshape(n, 3)
    else:
        dirs = None
    if depth_attr is not None:
        depths = np.zeros(n); depth_attr.data.foreach_get("value", depths)
        depths_i = np.rint(depths).astype(int)
    else:
        depths_i = None
    finite = np.all(np.isfinite(coords), axis=1)
    # DIAGNOSTIC (user 2026-06-22): report the depth/radius structure so the gate
    # thresholds are set from the actual skeleton, not a guess.
    if sp.get("card_leaf_rule") and depths_i is not None:
        print("    [diag] hierarchy_depth × radius (finite verts):")
        for dl in np.unique(depths_i[finite]):
            m = finite & (depths_i == dl)
            rr = radii[m] * 1000.0
            if rr.size:
                print(f"      depth {dl}: {int(m.sum()):6d} verts | "
                      f"r p10={np.percentile(rr,10):5.1f} med={np.percentile(rr,50):5.1f} "
                      f"p90={np.percentile(rr,90):6.1f} mm")
    eligible = finite & (radii < max_radius) & (radii >= min_tip_radius)
    if depths_i is not None and min_depth > 0:
        eligible &= (depths_i >= min_depth)
    if not eligible.any():
        print(f"    [warn] card rule: no eligible verts "
              f"(min_depth={min_depth}, min_tip_radius={min_tip_radius}, max_radius={max_radius})")
        return None
    stems_i = stems.astype(int)
    # DEPTH-GRADIENT BRANCH-ORDER GATE (user 2026-06-22): roll, per BRANCH, whether
    # it bears any leaf at all, from card_rule_depth_keep[order]. A branch's order is
    # the median hierarchy_depth of its strand (a stem_id is one fork-generation, so
    # depth is ~constant along it). Trunk strands (depth 0) never bear leaves; orders
    # above the max key inherit the max (all tertiary+ = 1.0). Deterministic via rng.
    depth_keep = sp.get("card_rule_depth_keep")
    stem_bears = None
    if depth_keep is not None and depths_i is not None:
        mk = max(depth_keep)
        # APEX CLADDING (user 2026-06-22 s4b: "top-sticks rising above their canopies
        # — weight towards ends not right yet"). The pure branch-ORDER gate strips the
        # upper crown bare: the apex branches are low-order (depth-1, off the leader)
        # so depth_keep[1]=0.05 gates them out, leaving a bare leader spike poking
        # above the foliage. But the growing apex of a real tree is leafy regardless
        # of branch order (foliage rides the OUTER/UPPER shell, which near the top is
        # made of young low-order tips). So force-keep any depth>=1 branch whose tip
        # reaches the top `card_rule_apex_band` fraction of the crown — clads the top.
        apex_band = float(sp.get("card_rule_apex_band", 0.0))
        apex_z = None
        if apex_band > 0.0 and finite.any():
            zf = coords[finite, 2]
            apex_z = zf.max() - apex_band * (zf.max() - zf.min())
        stem_bears = {}
        for sid in np.unique(stems_i[finite]):
            smask = finite & (stems_i == sid)
            sd = depths_i[smask]
            if sd.size == 0:
                continue
            d = int(round(float(np.median(sd))))
            if d <= 0:
                stem_bears[sid] = False     # trunk/leader strand: never leaf the bole
                continue
            if apex_z is not None and coords[smask, 2].max() >= apex_z:
                stem_bears[sid] = True       # upper-crown growing tip → always clad
                continue
            stem_bears[sid] = (rng.random() < depth_keep.get(min(d, mk), 0.0))
    uniq = np.unique(stems_i[eligible])
    sp2 = spacing * spacing
    chosen = []
    n_gated = 0
    for sid in uniq:
        if stem_bears is not None and not stem_bears.get(sid, True):
            n_gated += 1                               # branch order gated it bare
            continue
        idx = np.where(eligible & (stems_i == sid))[0]
        if len(idx) == 0:
            continue
        idx = idx[np.argsort(-extents[idx])]          # tip (high branch_extent) first
        placed = []
        for vi in idx:
            p = coords[vi]
            if len(placed) < min_per_branch:           # GUARANTEED tip-most N
                chosen.append(vi); placed.append(p)
            elif all(((p - q) ** 2).sum() >= sp2 for q in placed):  # spaced extras
                chosen.append(vi); placed.append(p)
    if not chosen:
        return None
    # ISOLATION PRUNE (user 2026-06-22: "prune isolated tip clusters"). The leaf rule
    # guarantees a tip cluster on EVERY branch, including thin short low laterals that
    # reach into open space — those single sprigs read as floating (the connecting twig
    # is sub-pixel at review distance). Drop any chosen cluster with too few sibling
    # clusters within a small radius (local-density outlier = a sprig alone in space),
    # keeping crown clusters (which are dense with neighbours) untouched. Capped so a
    # legitimately sparse young crown is not gutted.
    if sp.get("card_rule_isolation_prune", False) and len(chosen) > 12:
        C = coords[np.array(chosen)]                       # (M,3)
        M = len(chosen)
        R = max(0.6, target_height * 0.08)                 # ~0.72 m on a 9 m sapling
        d2 = ((C[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        neigh = (d2 <= R * R).sum(1) - 1                   # neighbours within R (exclude self)
        min_nb = int(sp.get("card_rule_isolation_min_neighbors", 2))
        floater = neigh < min_nb
        n_flag = int(floater.sum())
        cap = int(M * 0.15)                                # never drop > 15% (sparse-crown guard)
        if n_flag > 0:
            if n_flag <= cap:
                drop = set(np.where(floater)[0].tolist())
            else:                                          # too many flagged → drop only the most isolated
                drop = set(np.argsort(neigh)[:cap].tolist())
            chosen = [vi for j, vi in enumerate(chosen) if j not in drop]
            print(f"    isolation prune: dropped {len(drop)} floating clusters "
                  f"(<{min_nb} neighbours within {R:.2f}m)")
    # Card size — same scheme as extract_leaf_positions (height-scaled, with the
    # per-species sapling floor so a small crown is not see-through).
    hscale = target_height / 25.0
    csf = sp.get("card_size_floor")
    if csf is not None:
        hscale = max(hscale, float(csf))
    lo, hi = sp["leaf_cluster_size_range"]
    flo, fhi = sp["leaf_flatten_range"]
    size_mult = 1.4
    placements = []
    for vi in chosen:
        c = coords[vi]
        pos = Vector((float(c[0]), float(c[1]), float(c[2])))
        size = rng.uniform(lo, hi) * hscale * size_mult
        flatten = rng.uniform(flo, fhi)
        # Emit the branch growth direction so the card is built as a sprig riding
        # the twig (twig along +Z = outward), not a free-floating randomly-rotated
        # quad. 4-tuple → create_leaf_cards_at_positions takes the aligned path.
        if dirs is not None:
            d = dirs[vi]
            dvec = Vector((float(d[0]), float(d[1]), float(d[2])))
            placements.append((pos, size, flatten, dvec))
        else:
            placements.append((pos, size, flatten))
    msg = (f"    card per-branch (RULE): {len(chosen)} clusters across {len(uniq)} "
           f"branches (>= {min_per_branch}/branch, tip-weighted"
           f"{', dir-aligned' if dirs is not None else ''})")
    if stem_bears is not None and chosen and depths_i is not None:
        cd = depths_i[np.array(chosen)]
        hist = {int(d): int((cd == d).sum()) for d in np.unique(cd)}
        msg += (f"\n    branch-order gate: {n_gated} branches left bare; "
                f"clusters by order {hist}")
    print(msg)
    return placements


def _sprig_cards(bm, uv_layer, pos, size, pdir, n_quads, rng, gidx, stem_anchor=None,
                 half_factor=1.20):
    """Build n_quads SPRIG cards riding a twig (london_plane card path).

    Fixes the tiny / floating / randomly-rotated cards (user 2026-06-22, cpw_000-003):
    each card is the 4-leaf sprig texture, so it is built BIG, anchored AT the branch
    vertex (no positional scatter → never floats off the limb), with its +Z (texture-up
    = twig base→tip) aligned to the branch growth 'direction' via to_track_quat('Z','Y')
    — the identical orientation the 3D distribute path uses, so the twig runs outward and
    the leaves open away from the trunk. A per-card golden-angle roll about the twig axis
    gives crossed sprigs (n_quads>1) and crown-wide variation without detaching.
    """
    import mathutils
    GA = math.radians(137.5)
    d = pdir if pdir.length > 1e-6 else mathutils.Vector((0.0, 0.0, 1.0))
    track = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
    half = size * half_factor   # EVAL 2026-06-22: backed off from 1.60 — l-tier leaf density read too heavy (user); 1.20 thins the cluster cover. Now a per-species lever (card_half_factor, default 1.20) so a parsimony variant can shrink cards to let backlight through (london_plane_v2, 2026-07-02).
    zoff = -half * 0.10    # anchor INBOARD so the card body OVERLAPS the twig (no floating); leaves still extend modestly outward (user 2026-06-22: "floating clusters")
    # STEM ANCHOR (user 2026-06-24): when the card art has its stem in a known spot
    # (e.g. oak's bottom-left, card_stem_anchor=(0.0,0.0)), pin THAT texture point to
    # the branch vertex so the sprig grows FROM the twig — instead of the twig passing
    # through the card centre with the drawn stem dangling in open space ("ensure the
    # leaf cards are attaching at the stem"). UV→local: u→X (0→-hw,1→+hw), v→Z (0→-hh
    # base,1→+hh tip; +Z is twig base→tip, aligned outward). None = legacy centred card
    # (london_plane unchanged). A small inboard tuck embeds the stem in the wood.
    tuck = half * 0.06
    for q in range(max(1, n_quads)):
        roll = GA * (gidx * n_quads + q) + rng.uniform(-0.25, 0.25)
        tilt = (mathutils.Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, 'X')
                @ mathutils.Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, 'Y'))
        M = (mathutils.Matrix.Translation(pos) @ track
             @ mathutils.Matrix.Rotation(roll, 4, 'Z') @ tilt)
        hw = half * rng.uniform(0.9, 1.1)
        hh = half * rng.uniform(0.9, 1.1)
        if stem_anchor is None:
            ox, oz = 0.0, zoff
        else:
            su, sv = stem_anchor
            ox = (1.0 - 2.0 * su) * hw          # shift so texture-u=su lands on the twig axis
            oz = (1.0 - 2.0 * sv) * hh - tuck   # shift so texture-v=sv lands at the branch vertex (tucked in)
        local = [(-hw + ox, 0.0, -hh + oz), (hw + ox, 0.0, -hh + oz),
                 (hw + ox, 0.0,  hh + oz), (-hw + ox, 0.0,  hh + oz)]
        verts = [bm.verts.new(M @ mathutils.Vector(c)) for c in local]
        face = bm.faces.new(verts)
        for loop, uv in zip(face.loops, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]):
            loop[uv_layer].uv = uv


def create_leaf_cards_at_positions(placements, leaf_mat, rng, tier="l", n_cards=6,
                                   cluster_scatter=1.0, stem_anchor=None,
                                   card_half_factor=1.20):
    """Create dense leaf card clusters using AAA scatter approach.

    Instead of a few large crossed-quads, each cluster gets many small quads
    scattered within a spheroidal volume. Each quad has individual random
    orientation (full yaw, wide pitch range) and position jitter. This
    produces dense, convincing foliage that reads correctly from all angles
    and distances, matching SpeedTree/Far Cry quality standards.

    Target: 25-40 quads per L-tier cluster (vs 9 in the old system),
    each ~1/3 the size. Total leaf geometry per tree: 15K-40K quads,
    matching Far Cry 4 production budgets (44K-169K leaf vertices).

    Returns a list of bmesh objects to be joined into the tree mesh.
    """
    # Quads per cluster — uniform across all tiers. The _s/_m/_l are
    # age/size variants that coexist in the scene, not LOD tiers.
    n_quads = n_cards

    all_objects = []
    for _pi, _plc in enumerate(placements):
        # 4-tuple (pos,size,flatten,dir) → sprig-on-twig aligned card (london_plane,
        # _card_placements_per_branch); 3-tuple → legacy spheroidal scatter (other
        # species / fallback). When aligned, the scatter loop below runs 0 times.
        _aligned = len(_plc) >= 4
        pos, size, flatten = _plc[0], _plc[1], _plc[2]
        cluster_radius = size * cluster_scatter  # scatter radius (tight for cladding)
        card_size = size * 0.55      # individual card ~55% of cluster size

        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")

        if _aligned:
            _sprig_cards(bm, uv_layer, pos, size, _plc[3], n_quads, rng, _pi, stem_anchor,
                         half_factor=card_half_factor)

        for q in range(0 if _aligned else n_quads):
            # Random position within cluster sphere (bias toward surface)
            r = cluster_radius * (0.3 + 0.7 * rng.random() ** 0.5)
            theta = rng.uniform(0, math.pi * 2)
            phi = rng.uniform(-0.6, 0.8)  # bias upward (more canopy top)
            jx = r * math.cos(theta) * math.cos(phi)
            jy = r * math.sin(theta) * math.cos(phi)
            jz = r * math.sin(phi) * flatten

            # Random orientation: full yaw, wide pitch (±60° from vertical)
            yaw = rng.uniform(0, math.pi * 2)
            pitch = rng.uniform(-1.05, 1.05)  # ±60°
            # Some cards near-horizontal (canopy fill from above)
            if rng.random() < 0.25:
                pitch = rng.uniform(1.1, 1.4)  # 63-80° from vertical = near horizontal

            # Per-quad size variation (80-120%)
            w = card_size * rng.uniform(0.80, 1.20)
            h = w * flatten * rng.uniform(0.75, 1.15)
            half_w = w * 0.5
            half_h = h * 0.5

            # Build oriented quad: local corners → rotated by yaw+pitch
            cy, sy = math.cos(yaw), math.sin(yaw)
            cp, sp_val = math.cos(pitch), math.sin(pitch)

            local_corners = [
                (-half_w, 0, -half_h),
                ( half_w, 0, -half_h),
                ( half_w, 0,  half_h),
                (-half_w, 0,  half_h),
            ]
            corners = []
            for lx, ly, lz in local_corners:
                # Rotate around Z (yaw)
                rx = lx * cy - ly * sy
                ry = lx * sy + ly * cy
                rz = lz
                # Rotate around local X (pitch)
                ry2 = ry * cp - rz * sp_val
                rz2 = ry * sp_val + rz * cp
                corners.append(Vector((rx + jx, ry2 + jy, rz2 + jz)) + pos)

            bm_verts = [bm.verts.new(c) for c in corners]
            face = bm.faces.new(bm_verts)
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv

        mesh = bpy.data.meshes.new("leaf_cards")
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new("leaf_cards", mesh)
        obj.data.materials.append(leaf_mat)
        bpy.context.collection.objects.link(obj)
        all_objects.append(obj)

    return all_objects


def create_strand_cards_at_positions(placements, strand_mat, rng, target_height):
    """Willow weeping curtain — a continuous fountain skirt.

    The signature weeping willow read is a *continuous draping curtain* of fine
    branchlets sweeping from a broad dome to the ground, with an open interior
    that lets the stout short trunk show through. The previous version hung a
    handful of narrow near-vertical strands from scattered crown points, which
    read as discrete green ropes with gaps between them — not a curtain.

    This builds the skirt as overlapping wide leaf-strip panels around the OUTER
    crown (the dome shoulder), each panel a small fan of 2-3 strands so adjacent
    panels merge into a single screen. Strands flare slightly outward toward the
    ground (the fountain spread) and sweep to near ground level. The interior
    (rad < 0.4·crown) is deliberately left open so the trunk reads. A handful of
    placement-driven interior strands add depth without filling the centre.

    Strands are crossed quad pairs with the cluster leaf texture tiled along
    their length (the branchlet+leaf pattern runs the full pendulous drop) — the
    part of the weep the gravity-capped Mtree skeleton can't make (sub_gravity
    crashes the mesher above ~30, far short of a true vertical weep).
    """
    if not placements:
        return []
    cx = sum(p[0].x for p in placements) / len(placements)
    cy = sum(p[0].y for p in placements) / len(placements)
    zs = [p[0].z for p in placements]
    zmin, zmax = min(zs), max(zs)
    crown_h = max(zmax - zmin, 0.1)
    maxr = max(0.5, max(math.hypot(p[0].x - cx, p[0].y - cy) for p in placements))
    # Willow open-grown spread ~1.1-1.3·H (radius ~0.55-0.65·H). Guarantee a
    # broad skirt even when the Mtree crown comes out tight, but don't inflate so
    # far past the actual crown that curtains appear to hang from empty air.
    dome_r = max(maxr, 0.42 * target_height)
    dome_r = min(dome_r, maxr * 1.5)
    shoulder_z = zmin + 0.50 * crown_h   # curtains hang from the lower-outer crown
    print(f"    [willow] crown maxr={maxr:.2f} dome_r={dome_r:.2f} "
          f"crown_h={crown_h:.2f} (target_h={target_height:.1f})")

    all_objects = []

    def add_strand(bm, uv_layer, top, bottom_z, width, sway_scale=1.0):
        """One crossed-quad pendulous strand from `top` down to `bottom_z`,
        flaring slightly outward (fountain spread) with a gentle sway."""
        strand_len = top.z - bottom_z
        if strand_len < 0.12 * target_height:
            return False
        out = Vector((top.x - cx, top.y - cy, 0.0))
        if out.length > 1e-4:
            out.normalize()
        else:
            a0 = rng.uniform(0, math.tau)
            out = Vector((math.cos(a0), math.sin(a0), 0.0))
        flare = rng.uniform(0.04, 0.20) * strand_len * sway_scale
        sway_ang = rng.uniform(0, math.tau)
        sway = rng.uniform(0.03, 0.12) * strand_len * sway_scale
        bottom = Vector((top.x + out.x * flare + math.cos(sway_ang) * sway,
                         top.y + out.y * flare + math.sin(sway_ang) * sway,
                         bottom_z))
        v_rep = max(2.0, strand_len / max(width, 0.12))
        base_ang = rng.uniform(0, math.pi)
        for c in range(2):  # crossed pair → reads from all azimuths
            a = base_ang + c * math.pi / 2
            hdir = Vector((math.cos(a), math.sin(a), 0.0)) * (width * 0.5)
            corners = [top - hdir, top + hdir, bottom + hdir, bottom - hdir]
            vts = [bm.verts.new(v) for v in corners]
            face = bm.faces.new(vts)
            uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, v_rep), (0.0, v_rep)]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv
        return True

    def emit(bm):
        if len(bm.faces) == 0:
            bm.free()
            return
        mesh = bpy.data.meshes.new("willow_strands")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("willow_strands", mesh)
        obj.data.materials.append(strand_mat)
        bpy.context.collection.objects.link(obj)
        all_objects.append(obj)

    LEAF_TILE = 0.62   # model-space size of one tiled leaf-cluster cell

    def add_panel(bm, uv_layer, ang, r_top, top_z, bottom_z, width):
        """A wide tangential curtain panel: a vertical sheet spanning `width`
        tangentially at radius r_top, draping from top_z to bottom_z and flaring
        outward + widening at the base (the fountain bell). UVs tile the leaf
        texture in BOTH axes so the sheet reads as a dappled foliage wall, not a
        stretched clump or a single rope. Returns True if built."""
        if top_z - bottom_z < 0.12 * target_height:
            return False
        tang = Vector((-math.sin(ang), math.cos(ang), 0.0))
        radial = Vector((math.cos(ang), math.sin(ang), 0.0))
        half = width * 0.5
        flare = rng.uniform(0.05, 0.18) * (top_z - bottom_z)
        top_c = Vector((cx + radial.x * r_top, cy + radial.y * r_top, top_z))
        base_c = Vector((cx + radial.x * (r_top + flare),
                         cy + radial.y * (r_top + flare), bottom_z))
        half_b = half * rng.uniform(1.0, 1.3)   # bell out at the ground
        tl, tr = top_c - tang * half, top_c + tang * half
        br, bl = base_c + tang * half_b, base_c - tang * half_b
        u_rep = max(1.0, width / LEAF_TILE)
        v_rep = max(2.0, (top_z - bottom_z) / LEAF_TILE)
        vts = [bm.verts.new(v) for v in (tl, tr, br, bl)]
        face = bm.faces.new(vts)
        uvs = [(0.0, 0.0), (u_rep, 0.0), (u_rep, v_rep), (0.0, v_rep)]
        for loop, uv in zip(face.loops, uvs):
            loop[uv_layer].uv = uv
        return True

    # --- 1. Perimeter fountain skirt: overlapping wide curtain panels ---
    # Two concentric rings of tangential panels, each wide enough to overlap its
    # neighbours into a continuous draping wall (a single panel per slot would
    # read as a rope; overlap + the dappled leaf alpha give a real curtain).
    # The leaf texture's transparent gaps keep it from looking like a solid sock.
    for ring_i, (r_mul, n_div, w_over) in enumerate(
            [(1.00, 30, 1.55), (0.82, 24, 1.6)]):
        ring_r = dome_r * r_mul
        spacing = (2.0 * math.pi * ring_r) / n_div
        width = spacing * w_over
        for pidx in range(n_div):
            ang = (pidx / n_div) * math.tau + rng.uniform(-0.05, 0.05) \
                + ring_i * (math.pi / n_div)   # stagger the inner ring
            r = ring_r * rng.uniform(0.92, 1.05)
            top_z = shoulder_z + rng.uniform(-0.08, 0.14) * crown_h \
                - 0.10 * crown_h * r_mul
            bottom_z = rng.uniform(-0.30, 0.05 * target_height)  # sweep to ground
            bm = bmesh.new()
            uv_layer = bm.loops.layers.uv.new("UVMap")
            if add_panel(bm, uv_layer, ang, r, top_z, bottom_z,
                         width * rng.uniform(0.9, 1.15)):
                emit(bm)
            else:
                bm.free()

    # --- 1b. Fine perimeter strands: break the panel silhouette at the edge ---
    n_fine = int(2.0 * math.pi * dome_r / 0.7)
    n_fine = max(16, min(n_fine, 64))
    for fidx in range(n_fine):
        ang = (fidx / n_fine) * math.tau + rng.uniform(-0.10, 0.10)
        r = dome_r * rng.uniform(0.96, 1.12)   # just outside the panel wall
        top_z = shoulder_z + rng.uniform(-0.05, 0.10) * crown_h
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        top = Vector((cx + math.cos(ang) * r, cy + math.sin(ang) * r,
                      top_z + rng.uniform(-0.12, 0.12)))
        if add_strand(bm, uv_layer, top,
                      rng.uniform(-0.30, 0.05 * target_height),
                      rng.uniform(0.40, 0.66)):
            emit(bm)
        else:
            bm.free()

    # --- 2. Interior depth strands from the outer canopy placements ---
    # Keep the trunk/interior open (rad gate) so the short stout trunk reads.
    for pos, size, flatten in placements:
        rad = math.hypot(pos.x - cx, pos.y - cy)
        if rad < 0.40 * dome_r:
            continue
        zfrac = (pos.z - zmin) / crown_h
        p_hang = (0.18 + 0.45 * (rad / maxr)) * (1.0 - 0.6 * max(0.0, zfrac - 0.6) / 0.4)
        if rng.random() > p_hang:
            continue
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        made = False
        for _s in range(rng.randint(1, 2)):
            top = Vector((pos.x + rng.uniform(-size, size),
                          pos.y + rng.uniform(-size, size),
                          pos.z + rng.uniform(-size * 0.3, size * 0.3)))
            made |= add_strand(bm, uv_layer, top, rng.uniform(-0.3, 1.6),
                               rng.uniform(0.38, 0.62))
        if made:
            emit(bm)
        else:
            bm.free()

    return all_objects


# --- Weeping Willow (Salix babylonica) canopy data ---------------------------
# Source: reference_tree_canopy_data §9 (NCSU / Morton Arb / USDA Silvics).
# Every willow form parameter — crown width, branch count / length / thickness,
# leaf count / density, and the young↔mature age differences — DERIVES from
# these constants, not hand-tuned magic numbers. Absolute geometry counts are
# bounded by WILLOW_TUFT_CAP: a stated perf budget (willows are a sparse,
# waterside species, never in the woodland that governs the 45fps floor), so the
# data sets the *relationships* and the cap sets the affordable absolute scale.
WILLOW_CANOPY = {
    "height_m": (9.0, 15.0),               # mature height (occasionally to 18)
    "spread_m": (12.0, 18.0),              # crown spread — often WIDER than tall
    "lai": (3.0, 5.0),                     # individual-tree leaf area index
    "curtain_transmission": (0.15, 0.25),  # light through the outer curtain
    "leaf_area_cm2": 8.0,                  # one linear-lanceolate leaf (5-12 cm²)
    "twig_diam_cm": (0.6, 1.4),            # pendulous whip (multi-year) diameter
    "fork_frac": 0.18,                     # low fork (Silvics; branch_start 0.18)
}
WILLOW_TUFT_CAP = 4200   # max leaf-tuft cards on a mature willow (perf budget)


def _wlerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


def _wbezier(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (p0 * (u * u * u) + p1 * (3.0 * u * u * t)
            + p2 * (3.0 * u * t * t) + p3 * (t * t * t))


def _willow_form(height, age01):
    """Derive a willow's geometry from canopy data + age (0=young, 1=mature).

    `height` is the actual tree height (the Mtree crown top, so the fountain is
    self-consistent regardless of any Mtree overshoot). Young willows are upright
    and narrow; they broaden into the wide weeping dome with age (Silvics), so
    age01 drives crown width, branch count / length / thickness and leaf density
    together — the s (young) and m (mature) tiers are genuinely different ages.
    """
    d = WILLOW_CANOPY
    # Crown width: spread/height ratio climbs narrow-young → wide-mature.
    # Data: spread 12-18 m on H 9-15 m → mature ratio ~1.0-1.3 (wider than tall).
    spread_ratio = _wlerp(0.72, 1.22, age01)
    dome_r = 0.5 * height * spread_ratio
    lai = _wlerp(d["lai"][0] + 0.3, d["lai"][1], age01)        # denser with age
    # Whip thickness from twig-diameter data, scaled to model size; limbs thicker.
    twig_cm = _wlerp(d["twig_diam_cm"][0], d["twig_diam_cm"][1], age01)
    whip_r = (twig_cm / 100.0) * 0.5 * (height / 12.0)
    limb_r = whip_r * _wlerp(4.5, 6.5, age01)
    n_limbs = int(round(_wlerp(5, 8, age01)))
    # Leaf-tuft (clump) card size from the real leaf footprint, scaled with age.
    tuft_sz = _wlerp(0.17, 0.30, age01) * (height / 12.0)
    whip_reach = _wlerp(0.74, 0.96, age01)   # whips sweep to ground (data)
    # Leaves "along the full length" → clump tufts spaced down each whip; spacing
    # from the tuft footprint. Whip count then follows from the LAI-scaled leaf
    # budget so the curtain density tracks LAI (denser, older = fuller).
    leaf_spacing = tuft_sz * 1.0   # tufts overlap down the whip (continuous curtain)
    avg_whip_len = whip_reach * 0.85 * height
    avg_leaves = max(3.0, avg_whip_len / leaf_spacing)
    tuft_budget = WILLOW_TUFT_CAP * (0.40 + 0.60 * age01) * (lai / 4.0)
    circ = 2.0 * math.pi * dome_r
    n_whips = int(max(10, min(tuft_budget / avg_leaves, circ / (tuft_sz * 0.6))))
    return {
        "dome_r": dome_r, "lai": lai, "whip_r": whip_r, "limb_r": limb_r,
        "n_limbs": n_limbs, "tuft_sz": tuft_sz, "whip_reach": whip_reach,
        "leaf_spacing": leaf_spacing, "n_whips": n_whips,
        "tuft_budget": int(tuft_budget), "fork_frac": d["fork_frac"],
    }


def willow_crown_placements(placements, rng):
    """Thin the cluster-card placements for a weeping willow to the UPPER crown
    only. A willow's interior is open (you see the trunk and sky through the
    weeping curtain) — the dense full-volume scatter every other tree uses reads
    as a solid 'bush inside the curtain'. The hanging branchlets supply the rest
    of the foliage; these clusters just cap the dome so it reads from above and
    at distance."""
    if not placements:
        return []
    zs = [p[0].z for p in placements]
    zmin, zmax = min(zs), max(zs)
    zr = max(zmax - zmin, 0.1)
    kept = []
    for pos, size, flatten in placements:
        zf = (pos.z - zmin) / zr
        # keep almost none of the lower interior, most of the dome top
        keep_p = max(0.0, min(1.0, 0.05 + 1.5 * (zf - 0.45)))
        if rng.random() < keep_p:
            kept.append((pos, size, flatten))
    return kept


def create_willow_branchlets(trunk_obj, placements, leaf_mat, bark_mat, rng,
                             target_height, age01):
    """The weeping willow as REAL geometry: a data-driven arching fountain.

    A few primary limbs leave the low fork, rise and arch OUT to a broad dome
    (crown width from canopy data), then fine tapering whips cascade from the
    outer limbs to the ground with leaf tufts along their full length. The
    pendulous geometry IS the weep — Mtree's gravity-capped skeleton can't make
    it (sub_gravity crashes the mesher above ~30, far short of a true vertical
    fall), and earlier tiled-card curtains always read as hard vertical green
    bars. Branch count / length / thickness, leaf density and the young↔mature
    differences ALL come from _willow_form (canopy data + age), not magic numbers.

    Perf: thin 3-sided tubes + a leaf-tuft budget (WILLOW_TUFT_CAP) keep the tri
    count bounded; willows are sparse, waterside, never in the 45fps woodland.

    Wind: each tube carries Mtree-style float attributes (hierarchy_depth/
    branch_extent/stem_id) scaled to the scaffold so bake_wind_vertex_colors
    animates the pendulous tips (limbs stiffer, whip tips flexible); the leaf
    tufts inherit wind from the nearest tube vertex via the existing grid step.

    Returns [tube_object, leaf_object] (either may be absent).
    """
    src = trunk_obj.data
    nsrc = len(src.vertices)
    if nsrc == 0:
        return []

    def _attr_max(name):
        at = src.attributes.get(name)
        if not at:
            return 1.0
        arr = np.zeros(nsrc)
        at.data.foreach_get("value", arr)
        return max(float(arr.max()), 1.0)
    hd_max = _attr_max("hierarchy_depth")
    be_max = _attr_max("branch_extent")

    # Trunk axis + height from the Mtree trunk — the fountain hangs off this.
    coords = np.zeros(nsrc * 3)
    src.vertices.foreach_get("co", coords)
    coords = coords.reshape(nsrc, 3)
    Hc = float(coords[:, 2].max())
    base_mask = coords[:, 2] < 0.12 * Hc
    if base_mask.any():
        cx = float(coords[base_mask, 0].mean())
        cy = float(coords[base_mask, 1].mean())
    else:
        cx = float(coords[:, 0].mean())
        cy = float(coords[:, 1].mean())

    f = _willow_form(Hc, age01)
    dome_r = f["dome_r"]
    fork_z = f["fork_frac"] * Hc
    # The leafy crown reaches nearly the full tree height so it BURIES the Mtree
    # leader/upper branches instead of leaving them poking out the top (the
    # "central bare stick" defect); foliage starts at crown_base and the lower
    # centre stays open (the willow "room underneath").
    dome_top = _wlerp(0.86, 0.96, age01) * Hc
    crown_base = _wlerp(0.42, 0.52, age01) * Hc
    rise = max(dome_top - fork_z, 0.5)
    tuft_sz = f["tuft_sz"]

    tube_bm = bmesh.new()
    ext_vals, sid_vals, hd_vals = [], [], []
    leaf_bm = bmesh.new()
    leaf_uv = leaf_bm.loops.layers.uv.new("UVMap")
    tuft_count = [0]
    SEG = 6

    def add_tube(pts, r0, r1, sid_val, hd_val):
        n = len(pts)
        rings = []
        for i, pt in enumerate(pts):
            t = i / (n - 1)
            r = r0 + (r1 - r0) * t
            fwd = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            if fwd.length < 1e-5:
                fwd = Vector((0, 0, -1))
            fwd.normalize()
            ref = Vector((0, 0, 1)) if abs(fwd.z) < 0.95 else Vector((1, 0, 0))
            side = fwd.cross(ref).normalized()
            up = side.cross(fwd).normalized()
            ring = []
            for j in range(3):
                a = 2.0 * math.pi * j / 3.0
                off = side * (math.cos(a) * r) + up * (math.sin(a) * r)
                ring.append(tube_bm.verts.new(pt + off))
                ext_vals.append(t * be_max)
                sid_vals.append(float(sid_val))
                hd_vals.append(hd_val)
            rings.append(ring)
        for i in range(len(rings) - 1):
            for j in range(3):
                j2 = (j + 1) % 3
                tube_bm.faces.new([rings[i][j], rings[i][j2],
                                   rings[i + 1][j2], rings[i + 1][j]])

    def add_leaf_tuft(center, scale):
        tuft_count[0] += 1
        yaw = rng.uniform(0, math.tau)
        pitch = rng.uniform(-1.2, -0.2)          # tilt downward (pendulous)
        for c in range(2):                       # crossed pair → all azimuths
            a = yaw + c * math.pi / 2
            ca, sa = math.cos(a), math.sin(a)
            cp, sp_ = math.cos(pitch), math.sin(pitch)
            hw = scale * rng.uniform(0.9, 1.25) * 0.5
            hh = scale * rng.uniform(0.95, 1.3) * 0.5  # ~round so tufts fill, not streak
            local = [(-hw, 0.0, -hh), (hw, 0.0, -hh), (hw, 0.0, hh), (-hw, 0.0, hh)]
            verts = []
            for lx, ly, lz in local:
                rx = lx * ca - ly * sa
                ry = lx * sa + ly * ca
                ry2 = ry * cp - lz * sp_
                rz2 = ry * sp_ + lz * cp
                verts.append(leaf_bm.verts.new(center + Vector((rx, ry2, rz2))))
            fc = leaf_bm.faces.new(verts)
            for loop, uv in zip(fc.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
                loop[leaf_uv].uv = uv

    sid = 7000
    # --- Primary arching limbs: the structural frame (mostly hidden under the
    # crown shell) + the bark the crown/whips ride for wind. They diverge
    # outward early (p1 at 0.42·limb_r) so they don't gather into a central
    # bundle (the "branches gathered as they arch over" defect). ---
    for L in range(f["n_limbs"]):
        az = (L + rng.uniform(-0.25, 0.25)) / f["n_limbs"] * math.tau
        dd = Vector((math.cos(az), math.sin(az), 0.0))
        limb_r = dome_r * rng.uniform(0.85, 1.05)
        p0 = Vector((cx, cy, fork_z))
        p1 = Vector((cx + dd.x * 0.42 * limb_r, cy + dd.y * 0.42 * limb_r,
                     fork_z + 0.55 * rise))
        p2 = Vector((cx + dd.x * 0.85 * limb_r, cy + dd.y * 0.85 * limb_r, dome_top))
        p3 = Vector((cx + dd.x * 1.00 * limb_r, cy + dd.y * 1.00 * limb_r,
                     dome_top - 0.30 * rise))
        npt = 9
        lp = [_wbezier(p0, p1, p2, p3, i / (npt - 1)) for i in range(npt)]
        add_tube(lp, f["limb_r"], f["limb_r"] * 0.30, sid, hd_max * 0.35)
        sid += 1

    # --- Crown shell: a dense leafy dome cap over the WHOLE upper crown (centre
    # included), so the trunk/leader and the bare Mtree branches are BURIED
    # under foliage instead of poking through. Hemisphere profile from
    # crown_base up to dome_top, area-uniform scatter with inward thickness. ---
    cap_h = max(dome_top - crown_base, 0.3)
    n_crown = int(f["tuft_budget"] * 0.45)
    for _k in range(n_crown):
        rr = dome_r * math.sqrt(rng.uniform(0.0, 1.0))      # area-uniform
        aa = rng.uniform(0, math.tau)
        prof = math.sqrt(max(0.0, 1.0 - (rr / dome_r) ** 2))
        zz = crown_base + cap_h * prof - rng.uniform(0.0, 0.30) * cap_h
        c = Vector((cx + math.cos(aa) * rr, cy + math.sin(aa) * rr, zz))
        add_leaf_tuft(c, tuft_sz * rng.uniform(1.0, 1.6))

    # Apex cap: a few tufts up the central axis from dome_top toward the very
    # top, so the bare Mtree trunk tip above the dome is hidden, not poking out.
    n_apex = max(5, int(n_crown * 0.05))
    for _k in range(n_apex):
        rr = dome_r * rng.uniform(0.0, 0.20)
        aa = rng.uniform(0, math.tau)
        zz = rng.uniform(dome_top - 0.04 * Hc, min(dome_top + 0.06 * Hc, Hc))
        add_leaf_tuft(Vector((cx + math.cos(aa) * rr, cy + math.sin(aa) * rr, zz)),
                      tuft_sz * rng.uniform(1.1, 1.7))

    # --- Pendulous whips cascading from the dome rim to the ground (the skirt).
    # Hung around the lower-outer dome, not from a single limb, so the curtain
    # is continuous; the lower centre is left open (the room underneath). ---
    n_whips = f["n_whips"]
    for w in range(n_whips):
        if tuft_count[0] >= f["tuft_budget"]:
            break
        aa = (w + rng.uniform(-0.4, 0.4)) / n_whips * math.tau
        rr = dome_r * rng.uniform(0.58, 1.02)
        dd = Vector((math.cos(aa), math.sin(aa), 0.0))
        prof = math.sqrt(max(0.0, 1.0 - (min(rr, dome_r) / dome_r) ** 2))
        # hang from the rim underside; inner whips start a little higher
        top_z = crown_base + cap_h * prof * rng.uniform(0.2, 0.7)
        apos = Vector((cx + dd.x * rr, cy + dd.y * rr, top_z))
        # Vary length: most sweep near the ground, some shorter — an irregular
        # soft hem, not a flat picket-fence of equal bars.
        whip_len = f["whip_reach"] * apos.z * rng.uniform(0.62, 1.04)
        if whip_len < 0.12 * Hc:
            continue
        perp = Vector((-dd.y, dd.x, 0.0))
        out_reach = rng.uniform(0.04, 0.16) * whip_len
        sway_phase = rng.uniform(0, math.tau)
        sway_amp = rng.uniform(0.015, 0.05) * whip_len
        jit = Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 0.0))
        pts = []
        for i in range(SEG + 1):
            t = i / SEG
            horiz = out_reach * (1.0 - (1.0 - t) ** 2)   # reach out then ease
            vert = -whip_len * (t ** 1.5)                # gravity accelerates
            wob = math.sin(sway_phase + t * 4.0) * sway_amp * t
            p = apos + dd * horiz + perp * wob + jit * t
            p.z = apos.z + vert
            pts.append(p)
        add_tube(pts, f["whip_r"], f["whip_r"] * 0.25, sid, hd_max * 0.92)
        sid += 1
        # leaf tufts down the full whip length (spacing from leaf-clump data)
        n_leaf = max(3, int(whip_len / f["leaf_spacing"]))
        for li in range(n_leaf):
            t = (li + rng.uniform(0.15, 0.85)) / n_leaf
            idx = min(int(t * SEG), SEG)
            off = Vector((rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07),
                          rng.uniform(-0.05, 0.05)))
            add_leaf_tuft(pts[idx] + off, tuft_sz * rng.uniform(0.8, 1.3))

    objs = []
    if len(tube_bm.faces) > 0:
        tmesh = bpy.data.meshes.new("willow_branchlet")
        tube_bm.to_mesh(tmesh)
        tube_bm.free()
        nv = len(tmesh.vertices)
        hd = tmesh.attributes.new("hierarchy_depth", 'FLOAT', 'POINT')
        be = tmesh.attributes.new("branch_extent", 'FLOAT', 'POINT')
        si = tmesh.attributes.new("stem_id", 'FLOAT', 'POINT')
        hd.data.foreach_set("value", np.array(hd_vals[:nv], dtype=np.float64))
        be.data.foreach_set("value", np.array(ext_vals[:nv], dtype=np.float64))
        si.data.foreach_set("value", np.array(sid_vals[:nv], dtype=np.float64))
        tobj = bpy.data.objects.new("willow_branchlet", tmesh)
        tobj.data.materials.append(bark_mat)
        bpy.context.collection.objects.link(tobj)
        objs.append(tobj)
    else:
        tube_bm.free()
    if len(leaf_bm.faces) > 0:
        lmesh = bpy.data.meshes.new("willow_leaf_tufts")
        leaf_bm.to_mesh(lmesh)
        leaf_bm.free()
        lobj = bpy.data.objects.new("willow_leaf_tufts", lmesh)
        lobj.data.materials.append(leaf_mat)
        bpy.context.collection.objects.link(lobj)
        objs.append(lobj)
    else:
        leaf_bm.free()
    return objs


def create_crown_fill_cards(placements, leaf_mat, rng, target_height):
    """LOD1 (tier _m): fill the crown volume with large overlapping cards.

    AAA approach (SpeedTree LOD1): instead of placing small cards along
    branches, scatter large "frond" cards throughout the crown bounding
    ellipsoid. At 130-350m viewing distance, individual branch structure
    is invisible — you need solid green mass in the right shape.

    ~80-120 cards per tree, each 0.8-1.5m wide, overlapping to create
    dense canopy coverage from any viewing angle.
    """
    if not placements:
        return []

    # Compute crown bounding ellipsoid from branch-walk placements
    xs = [p[0].x for p in placements]
    ys = [p[0].y for p in placements]
    zs = [p[0].z for p in placements]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    cz = (min(zs) + max(zs)) * 0.5
    rx = max((max(xs) - min(xs)) * 0.5, 0.5)
    ry = max((max(ys) - min(ys)) * 0.5, 0.5)
    rz = max((max(zs) - min(zs)) * 0.5, 0.5)
    center = Vector((cx, cy, cz))

    # Card sizing: must subtend ≥5px at 250m (mid LOD1 range)
    # 250m × 5px / 1663 px_per_m_at_1m ≈ 0.75m minimum
    # Use 0.9-1.6m for good overlap
    base_card = target_height * 0.06  # ~1.2m for a 20m tree
    n_fronds = max(int(100 * (rx * rz) / 4.0), 60)  # scale with crown area
    n_fronds = min(n_fronds, 200)

    all_objects = []
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    for i in range(n_fronds):
        # Scatter within ellipsoid, bias toward the surface (where leaves are)
        u = rng.random()
        r_frac = 0.4 + 0.6 * (u ** 0.3)  # bias toward surface
        theta = rng.uniform(0, math.pi * 2)
        phi = rng.uniform(-0.7, 0.9)  # slight upward bias
        px = cx + rx * r_frac * math.cos(theta) * math.cos(phi)
        py = cy + ry * r_frac * math.sin(phi)
        pz = cz + rz * r_frac * math.sin(theta) * math.cos(phi)

        # Card size with variation
        w = base_card * rng.uniform(0.75, 1.35)
        h = w * rng.uniform(0.6, 1.0)

        # Random orientation: full yaw, moderate pitch
        yaw = rng.uniform(0, math.pi * 2)
        pitch = rng.uniform(-0.8, 0.8)
        # 40% near-horizontal for overhead coverage (critical for aerial views)
        if rng.random() < 0.40:
            pitch = rng.uniform(1.0, 1.45)

        half_w, half_h = w * 0.5, h * 0.5
        cy_r, sy_r = math.cos(yaw), math.sin(yaw)
        cp, sp_val = math.cos(pitch), math.sin(pitch)

        local_corners = [
            (-half_w, 0, -half_h),
            ( half_w, 0, -half_h),
            ( half_w, 0,  half_h),
            (-half_w, 0,  half_h),
        ]
        corners = []
        for lx, ly, lz in local_corners:
            rx2 = lx * cy_r - ly * sy_r
            ry2 = lx * sy_r + ly * cy_r
            rz2 = lz
            ry3 = ry2 * cp - rz2 * sp_val
            rz3 = ry2 * sp_val + rz2 * cp
            corners.append(Vector((rx2 + px, ry3 + py, rz3 + pz)))

        bm_verts = [bm.verts.new(c) for c in corners]
        face = bm.faces.new(bm_verts)
        for loop, uv in zip(face.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop[uv_layer].uv = uv

    mesh = bpy.data.meshes.new("crown_fill")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("crown_fill", mesh)
    obj.data.materials.append(leaf_mat)
    bpy.context.collection.objects.link(obj)
    all_objects.append(obj)
    return all_objects


def create_crossed_billboard_cards(placements, leaf_mat, rng, target_height):
    """LOD2 (tier _s): a few large crossed billboard quads filling the crown.

    AAA approach (SpeedTree LOD2): 6-8 large quads at different rotations
    spanning the entire crown volume. At 300-600m viewing distance, this
    reads as a solid canopy mass. Classic crossed-billboard pattern used
    by every AAA engine for distant vegetation.
    """
    if not placements:
        return []

    # Crown bounding box from placements
    xs = [p[0].x for p in placements]
    ys = [p[0].y for p in placements]
    zs = [p[0].z for p in placements]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    cz = (min(zs) + max(zs)) * 0.5
    half_w = max((max(xs) - min(xs)) * 0.5, 0.8)
    half_h = max((max(ys) - min(ys)) * 0.5, 0.8)
    half_d = max((max(zs) - min(zs)) * 0.5, 0.8)

    # 8 crossed quads at 22.5° increments around Y axis
    n_planes = 8
    angle_step = math.pi / n_planes  # 22.5°

    all_objects = []
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    for i in range(n_planes):
        angle = i * angle_step + rng.uniform(-0.1, 0.1)  # slight jitter
        cos_a, sin_a = math.cos(angle), math.sin(angle)

        # Quad spans the full crown width and height
        w = max(half_w, half_d) * 2.0 * rng.uniform(0.85, 1.0)
        h = half_h * 2.0 * rng.uniform(0.85, 1.0)
        hw, hh = w * 0.5, h * 0.5

        # Slight random offset from center for natural variation
        ox = rng.uniform(-half_w * 0.15, half_w * 0.15)
        oz = rng.uniform(-half_d * 0.15, half_d * 0.15)

        # 4 corners of a vertical quad rotated around Y
        corners = [
            Vector((cx + ox - hw * cos_a, cy - hh, cz + oz - hw * sin_a)),
            Vector((cx + ox + hw * cos_a, cy - hh, cz + oz + hw * sin_a)),
            Vector((cx + ox + hw * cos_a, cy + hh, cz + oz + hw * sin_a)),
            Vector((cx + ox - hw * cos_a, cy + hh, cz + oz - hw * sin_a)),
        ]

        bm_verts = [bm.verts.new(c) for c in corners]
        face = bm.faces.new(bm_verts)
        for loop, uv in zip(face.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop[uv_layer].uv = uv

    # Horizontal crown-cap cards: 2-3 near-horizontal quads at the top of
    # the crown. Without these, overhead views see through all vertical
    # planes. Essential for the "green carpet" look from aerial perspectives.
    for cap_i in range(3):
        cap_y = cy + half_h * rng.uniform(0.5, 0.9)
        cap_r = max(half_w, half_d) * rng.uniform(0.7, 1.1)
        cap_angle = rng.uniform(0, math.pi * 2)  # random yaw
        cap_tilt = rng.uniform(-0.15, 0.15)       # slight tilt for natural look
        cos_ca, sin_ca = math.cos(cap_angle), math.sin(cap_angle)
        cos_ct, sin_ct = math.cos(cap_tilt), math.sin(cap_tilt)

        local = [
            (-cap_r, 0, -cap_r),
            ( cap_r, 0, -cap_r),
            ( cap_r, 0,  cap_r),
            (-cap_r, 0,  cap_r),
        ]
        cap_corners = []
        for lx, ly, lz in local:
            rx2 = lx * cos_ca - lz * sin_ca
            rz2 = lx * sin_ca + lz * cos_ca
            ry2 = ly * cos_ct - rz2 * sin_ct
            rz3 = ly * sin_ct + rz2 * cos_ct
            cap_corners.append(Vector((cx + rx2, cap_y + ry2, cz + rz3)))

        bm_verts = [bm.verts.new(c) for c in cap_corners]
        face = bm.faces.new(bm_verts)
        for loop, uv in zip(face.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop[uv_layer].uv = uv

    mesh = bpy.data.meshes.new("crossed_billboards")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("crossed_billboards", mesh)
    obj.data.materials.append(leaf_mat)
    bpy.context.collection.objects.link(obj)
    all_objects.append(obj)
    return all_objects


def _palmate_leaf_outline(leaf_cfg):
    """Parametric palmate (Platanus) leaf outline + planar UVs.

    Returns (boundary_xy, boundary_uv): a single ordered boundary loop walked
    clockwise from the right base corner, over the apex, to the left base corner,
    in normalised coords (base attachment at (0,0), tip toward +Y, height ~1.06).
    Five broad triangular lobes (central/lateral/basal) with moderate sinuses and
    coarse outward marginal teeth — verified as a plane-leaf silhouette via PIL
    before use (user 2026-06-20). Tunable via leaf_cfg["palmate"].
    """
    p = leaf_cfg.get("palmate", {})
    lobe_angles = p.get("lobe_angles_deg", (0.0, 38.0, 68.0))
    lobe_radius = p.get("lobe_radius", (1.06, 0.96, 0.78))
    sinus_frac = p.get("sinus_frac", 0.63)
    base_width = p.get("base_width", 0.20)
    width_scale = p.get("width_scale", 0.97)
    teeth_per_edge = p.get("teeth_per_edge", 2)
    tooth_amp = p.get("tooth_amp", 0.028)

    lobes = []
    for a, r in zip(lobe_angles, lobe_radius):
        lobes.append((a, r))
        if a != 0.0:
            lobes.append((-a, r))
    lobes.sort(key=lambda t: -t[0])  # clockwise: right base -> apex -> left base

    def polar(a_deg, r):
        a = math.radians(a_deg)
        return (math.sin(a) * r * width_scale, math.cos(a) * r)

    pts = [(base_width, 0.0)]
    for i, (a, r) in enumerate(lobes):
        tip = polar(a, r)
        prev = pts[-1]
        for k in range(1, teeth_per_edge + 1):
            t = k / (teeth_per_edge + 1)
            x = prev[0] + (tip[0] - prev[0]) * t
            y = prev[1] + (tip[1] - prev[1]) * t
            ox, oy = x - 0.0, y - 0.40  # bump away from leaf centroid -> tooth
            L = math.hypot(ox, oy) or 1.0
            pts.append((x + ox / L * tooth_amp, y + oy / L * tooth_amp))
        pts.append(tip)
        if i < len(lobes) - 1:
            na, nr = lobes[i + 1]
            pts.append(polar((a + na) / 2.0, sinus_frac * min(r, nr)))
    pts.append((-base_width, 0.0))

    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    half_w = max(abs(min(xs)), abs(max(xs))) or 1.0
    ymin, ymax = min(ys), max(ys)
    span = (ymax - ymin) or 1.0
    uvs = [(0.5 + x / (2.0 * half_w), 1.0 - (y - ymin) / span) for (x, y) in pts]
    return pts, uvs


def build_distribute_leaf(species_name, png_path, leaf_cfg):
    """Build the true-3D leaf object used by Mtree's native leaf distribution.

    The leaf IS its own silhouette (real lobed geometry from LeafShapeGenerator),
    so it carries a FULLY-OPAQUE single-leaf surface texture — NOT an alpha-cutout
    cluster card. (Cluster cards punched their transparent gaps as holes through
    solid leaves and showed white shards; user 2026-06-20.) Geometry venation is
    OFF — veins live in the texture, saving polys. Returns the leaf object; its
    first material is named `{species}_leaf` so tree_builder.gd maps it to the
    leaf shader + per-species DDS by name and bake_wind_vertex_colors tags it.
    """
    # Paint the opaque single-leaf surface texture via system python3 (PIL is
    # absent from Blender's bundled Python). Idempotent — skip if it exists.
    if not os.path.exists(png_path):
        import subprocess
        gen_script = os.path.join(PROJ, "scripts", "vegetation", "gen_single_leaf_tex.py")
        py3 = shutil.which("python3") or "/usr/bin/python3"
        subprocess.run([py3, gen_script, "--species", species_name, "--out", png_path],
                       check=True)
    # Deterministic palmate (Platanus) silhouette — the leaf IS its own outline.
    # The MAPLE superformula contour produced a rounded pentagonal BLOB (m=5 gives
    # shallow bumps, never the deep sinuses of a plane leaf); a parametric
    # star-shaped outline gives true broad triangular lobes. The silhouette was
    # tuned and verified as a plane leaf via PIL plot before porting (W/L 1.32,
    # 5 pointed lobes, moderate sinuses; user 2026-06-20). ~21 boundary verts —
    # cheaper than the old 36-vert decimated proto, so the wind bake stays fast.
    bxy, buv = _palmate_leaf_outline(leaf_cfg)
    base_len = leaf_cfg.get("base_len", 2.93)  # match the prior approved leaf size
    ys = [p[1] for p in bxy]
    span = (max(ys) - min(ys)) or 1.0
    sc = base_len / span
    # Base at origin, tip toward -Y (matches the Mtree leaf-proto convention so
    # distribute_leaves attaches petiole-end to the branch).
    # Gentle cross-midrib V-fold: z rises with distance from the midrib (x=0) so
    # the leaf is NOT a dead-flat plane. A flat plane lights as one hard facet →
    # the "shard"/chunky-clump look that made our canopy read like the flawed
    # 3D-model refs (user 2026-06-20). A slight fold + smooth normals (below) give
    # graded, soft shading per leaf. fold_amp is a fraction of leaf scale; tunable.
    fold = leaf_cfg.get("fold_amp", 0.15)
    # Base blade with its LENGTH along +X (base at origin, tip at +X), width along Y,
    # +Z normal. CRITICAL ORIENTATION (user 2026-06-21: "branches look placed backwards,
    # the open part of the Y is toward the trunk" + "bare branch ends"): the leaf
    # modifier aligns the proto's +Z axis to the branch growth 'direction'. The old proto
    # ran its twig along -Y, so sprigs stuck out sideways/backward and never reached the
    # tips. Building the sprig twig along +Z (below) makes it run OUTWARD along the branch
    # toward the tip, leaves fanning forward — so clusters open away from the trunk and
    # cover the branch ends. (bxy: x=width, y=0→1 base→tip.)
    blade = [(y * sc, x * sc, fold * abs(x * sc)) for (x, y) in bxy]
    # Guarantee a +Z face normal (CCW winding) via the shoelace signed area in XY.
    area2 = sum(blade[i][0] * blade[(i + 1) % len(blade)][1]
                - blade[(i + 1) % len(blade)][0] * blade[i][1]
                for i in range(len(blade)))
    if area2 < 0:
        blade = list(reversed(blade))
        buv = list(reversed(buv))
    n_blade = len(blade)

    # LEAF-CLUSTER SPRIG (user 2026-06-21, ref close-up-...-2SA8J91): the atomic
    # foliage unit is a TWIG bearing several palmate leaves spaced along it — NOT a
    # single leaf. Distributing single leaves studs the branch surface like fur
    # ("branches are furry with leaves"); distributing a sprig gives natural
    # clustering with space BETWEEN clusters, covers more crown per instance (so
    # density drops → far fewer instances → kinder to the 3060 Ti), and still reads
    # as real 3D leaves. The twig runs along +Z (= branch direction after alignment);
    # K leaves stagger ALONG it, each rolled by the golden angle (spiral) and swept
    # forward toward the tip, so the cluster opens outward like the reference.
    import mathutils
    K = int(leaf_cfg.get("cluster_n", 1))
    stem_len = leaf_cfg.get("cluster_stem", 0.62) * base_len
    tilt = math.radians(leaf_cfg.get("cluster_tilt", 38.0))  # forward sweep of each blade toward the tip
    if K <= 1:
        xforms = [mathutils.Matrix.Rotation(-tilt, 4, 'Y')]
    else:
        xforms = []
        for k in range(K):
            t = (k + 1) / (K + 1)                 # position fraction along the twig (+Z)
            roll = math.radians(137.5 * k)        # phyllotactic spiral around the twig
            s = 1.0 - 0.14 * t                    # leaves taper slightly toward the tip
            xforms.append(
                mathutils.Matrix.Translation((0.0, 0.0, t * stem_len))  # stagger along the +Z twig
                @ mathutils.Matrix.Rotation(roll, 4, 'Z')               # spiral around the twig
                @ mathutils.Matrix.Rotation(-tilt, 4, 'Y')              # sweep blade up/out toward the tip
                @ mathutils.Matrix.Scale(s, 4))
    coords, faces, all_uv = [], [], []
    for M in xforms:
        off = len(coords)
        for (vx, vy, vz) in blade:
            co = M @ mathutils.Vector((vx, vy, vz))
            coords.append((co.x, co.y, co.z))
        faces.append([off + i for i in range(n_blade)])  # one n-gon per leaf
        all_uv.extend(buv)
    me = bpy.data.meshes.new(f"{species_name}_leafproto")
    me.from_pydata(coords, [], faces)
    me.update()
    uv_layer = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv_layer.data[li].uv = all_uv[vi]
    ob = bpy.data.objects.new(f"{species_name}_leafproto", me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    # Triangulate the concave n-gon deterministically (don't rely on the glTF
    # exporter's tessellation of a lobed concave polygon).
    tri = ob.modifiers.new("tri", type='TRIANGULATE')
    tri.ngon_method = 'BEAUTY'
    bpy.ops.object.modifier_apply(modifier="tri")
    # Smooth (per-vertex) normals so the V-fold reads as a soft curve, not facets
    # — the graded normal across the leaf is what kills the flat-shard lighting.
    bpy.ops.object.shade_smooth()
    print(f"  palmate leaf {len(me.vertices)} verts {len(me.polygons)} tris (fold={fold})")
    mat = bpy.data.materials.new(f"{species_name}_leaf")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png_path)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.6
    # Alpha-CLIP so the glTF exports alphaMode=MASK → Godot import enables
    # transparency → tree_builder.gd classifies the surface as LEAF (it keys on
    # transparency) and applies the leaf shader (wind/SSS/seasonal). The texture
    # is opaque (alpha=1) so the clip is a no-op; the geometry is the silhouette.
    mat.blend_method = 'CLIP'
    mat.alpha_threshold = 0.5
    mat.diffuse_color = (0.30, 0.46, 0.20, 1.0)  # Workbench thumbnail green
    me.materials.append(mat)
    return ob


def _distribute_foliage_per_branch(trunk_obj, leaf_proto, max_radius, scale,
                                   min_per_branch, spacing):
    """THE LEAF RULE (user 2026-06-21 PM): "every branching of every branch must
    have at least a certain number of leaves, weighted to the tip."

    Poisson distribution (the legacy path below) is STOCHASTIC — it cannot
    guarantee that any given branch, let alone its tip, receives a cluster, so
    branch ends gap. This places clusters DETERMINISTICALLY per branch: for each
    stem_id, sort its eligible (thin, radius<max_radius) vertices tip-first
    (branch_extent desc), GUARANTEE the min_per_branch tip-most clusters, then add
    spaced extras down the branch for fullness. No bare branch is possible by
    construction, and the guaranteed clusters are the tip-most → tip-weighted.

    Each sprig is oriented by aligning its +Z to the per-vertex 'direction'
    attribute — identical to what the distribute_leaves modifier does — so the
    twig runs outward along the branch and the leaves open away from the trunk.
    """
    import bmesh, mathutils
    mesh = trunk_obj.data
    n = len(mesh.vertices)
    radius_attr = mesh.attributes.get("radius")
    be_attr = mesh.attributes.get("branch_extent")
    si_attr = mesh.attributes.get("stem_id")
    dir_attr = mesh.attributes.get("direction")
    if not (radius_attr and be_attr and si_attr and dir_attr) or n == 0:
        print("    per-branch foliage: missing Mtree attrs — skipped")
        return
    radii = np.zeros(n); radius_attr.data.foreach_get("value", radii)
    extents = np.zeros(n); be_attr.data.foreach_get("value", extents)
    stems = np.zeros(n); si_attr.data.foreach_get("value", stems)
    dirs = np.zeros(n * 3); dir_attr.data.foreach_get("vector", dirs)
    dirs = dirs.reshape(n, 3)
    coords = np.zeros(n * 3); mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(n, 3)
    finite = np.all(np.isfinite(coords), axis=1)
    eligible = finite & (radii < max_radius)
    stems_i = stems.astype(int)
    uniq = np.unique(stems_i[eligible]) if eligible.any() else np.array([], dtype=int)

    chosen = []
    sp2 = spacing * spacing
    for sid in uniq:
        idx = np.where(eligible & (stems_i == sid))[0]
        if len(idx) == 0:
            continue
        idx = idx[np.argsort(-extents[idx])]      # tip (high branch_extent) first
        placed = []
        for vi in idx:
            p = coords[vi]
            if len(placed) < min_per_branch:       # GUARANTEED tip-most N
                chosen.append(vi); placed.append(p)
            elif all(((p - q) ** 2).sum() >= sp2 for q in placed):  # spaced extras
                chosen.append(vi); placed.append(p)
    if not chosen:
        print("    per-branch foliage: no eligible thin branches — skipped")
        return

    proto = leaf_proto.data
    proto_uv = proto.uv_layers.active
    proto_polys = [[(proto.loops[li].vertex_index, li) for li in poly.loop_indices]
                   for poly in proto.polygons]
    proto_co = [v.co.copy() for v in proto.vertices]

    out_bm = bmesh.new()
    uvl = out_bm.loops.layers.uv.new("UVMap")
    GA = math.radians(137.5)                       # golden-angle roll → per-cluster variation
    for k, vi in enumerate(chosen):
        pos = mathutils.Vector((float(coords[vi][0]), float(coords[vi][1]), float(coords[vi][2])))
        d = mathutils.Vector((float(dirs[vi][0]), float(dirs[vi][1]), float(dirs[vi][2])))
        if d.length < 1e-6:
            d = mathutils.Vector((0.0, 0.0, 1.0))
        M = (mathutils.Matrix.Translation(pos)
             @ d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
             @ mathutils.Matrix.Rotation(GA * k, 4, 'Z')
             @ mathutils.Matrix.Scale(scale, 4))
        # WELD: one out-vert per proto VERTEX per placement (faces reference by
        # index), not one per loop — the proto is triangulated, so per-loop creation
        # tripled the leaf vert count (~57 vs ~21 verts/leaf).
        vmap = [out_bm.verts.new(M @ co) for co in proto_co]
        for poly in proto_polys:
            try:
                face = out_bm.faces.new([vmap[pvi] for (pvi, _li) in poly])
            except ValueError:
                continue
            if proto_uv:
                for loop, (_pvi, li) in zip(face.loops, poly):
                    loop[uvl].uv = proto_uv.data[li].uv

    leaf_mesh = bpy.data.meshes.new("dist_leaves")
    out_bm.to_mesh(leaf_mesh); out_bm.free()
    leaf_obj = bpy.data.objects.new("dist_leaves", leaf_mesh)
    leaf_obj.data.materials.append(proto.materials[0])
    bpy.context.collection.objects.link(leaf_obj)
    bpy.ops.object.select_all(action='DESELECT')
    trunk_obj.select_set(True); leaf_obj.select_set(True)
    bpy.context.view_layer.objects.active = trunk_obj
    bpy.ops.object.join()
    print(f"    per-branch foliage (RULE): {len(chosen)} clusters across "
          f"{len(uniq)} branches (guaranteed >={min_per_branch}/branch, tip-weighted)")


def distribute_foliage(trunk_obj, leaf_proto, sp, tier_name):
    """Instance the true-3D leaf phyllotactically onto the branch skeleton via
    Mtree's native distribute_leaves, then realize it into trunk_obj.

    Coherent BY CONSTRUCTION — every leaf sits on the branch mesh via the
    radius/direction attributes, so there are no floating clusters (the whole
    reason for the card→distribution switch, user-approved 2026-06-20). Must run
    AFTER clean_degenerate_geometry (bark only) and BEFORE join/normalise so the
    scale param stays in metres like the validated prototype.
    """
    td = sp.get("tier_distribute", {}).get(tier_name, sp.get("distribute_defaults", {}))
    density = td.get("density", 150.0)
    scale = td.get("scale", 0.14)
    max_radius = td.get("max_radius", 0.06)
    spacing = td.get("spacing")  # Poisson Distance Min (m, skeleton space); None=legacy RANDOM
    # THE LEAF RULE: when leaves_per_branch_min is set, place clusters
    # deterministically per branch (guaranteed coverage, tip-weighted) instead of
    # the stochastic Poisson below (which gaps branch ends).
    min_per_branch = td.get("leaves_per_branch_min")
    if min_per_branch is not None:
        _distribute_foliage_per_branch(
            trunk_obj, leaf_proto, max_radius=max_radius, scale=scale,
            min_per_branch=int(min_per_branch), spacing=(spacing or 0.3))
        return
    bpy.ops.object.select_all(action='DESELECT')
    trunk_obj.select_set(True)
    bpy.context.view_layer.objects.active = trunk_obj
    distribute_leaves(
        trunk_obj, leaf_object=leaf_proto,
        distribution_mode=1, phyllotaxis_angle=137.5,
        density=density, scale=scale, max_radius=max_radius,
        billboard_mode="OFF", enable_normal_transfer=True)
    # EVEN SPACING (user 2026-06-21: "clusters more evenly spaced along the smaller
    # sub-branches"). The addon distributes points with distribute_method=RANDOM
    # (node_groups.py:269) — random sampling CLUMPS (Poisson-process gaps + knots);
    # distribution_mode 0/1 only changes leaf ROTATION, not spacing. Switch the
    # distribute node to POISSON-disk so clusters hold a minimum distance apart.
    # Only london_plane _s uses this node group, so the in-place edit is contained.
    if spacing:
        mod = trunk_obj.modifiers.get(LEAVES_MODIFIER_NAME)
        ng = mod.node_group if mod else None
        if ng:
            for n in ng.nodes:
                if n.bl_idname == "GeometryNodeDistributePointsOnFaces":
                    n.distribute_method = "POISSON"
                    if "Distance Min" in n.inputs:
                        n.inputs["Distance Min"].default_value = spacing
                    # In POISSON mode the wrapper's "Density" link feeds Density Max;
                    # set it as a generous cap so Distance Min governs the spacing.
                    if "Density Max" in n.inputs:
                        n.inputs["Density Max"].default_value = max(density, 50.0)
                    break
    bpy.ops.object.modifier_apply(modifier="leaves")


def generate_species_tier(species_name, tier_name, sp, tier_cfg, skip_fork_test=False):
    """Generate all variants for one species at one size tier.

    Creates a GLB with N_VARIANTS variants, each containing trunk+branches
    from Mtree plus leaf cards at branch tips, normalized to MODEL_H.
    """
    target_h = tier_cfg["target_h"]
    out_path = os.path.join(MODEL_DIR, f"{species_name}_{tier_name}.glb")

    print(f"\n{'='*60}")
    print(f"  {sp['name']} — tier {tier_name} ({target_h}m)")
    print(f"  Output: {out_path}")
    print(f"{'='*60}")

    # Create leaf material (shared across variants).
    # All tiers use the same dense texture (60-80% alpha coverage).
    # Industry standard: high coverage works at all distances.
    fascicle = sp["leaf_shape"] == "needle"
    compound = sp["leaf_shape"] == "compound"  # lacy/ferny pinnate frond (honeylocust)

    # --- True-3D Mtree-distributed leaves (foliage_distribute) ---
    # Replaces the volumetric card scatter entirely: real lobed leaf geometry
    # instanced phyllotactically on the branches, opaque single-leaf surface
    # texture (no alpha-cutout cluster card). Built once per tier, reused across
    # variants. (User-approved full switch, 2026-06-20.)
    # HYBRID (user-approved 2026-06-20): true-3D distributed leaves on the tiers
    # in `distribute_tiers` (small/near trees, where you SEE individual leaves);
    # the card path (poly-cheap dense cluster mass) on the rest (big crowns seen
    # high/far). Per-tier so the sapling can be data-true while m/l stay dense.
    leaf_proto = None
    use_distribute = (sp.get("foliage_distribute")
                      and tier_name in sp.get("distribute_tiers", ["s", "m", "l"]))
    if use_distribute:
        png_dir = os.path.join(MODEL_DIR, "leaf_textures")
        os.makedirs(png_dir, exist_ok=True)
        # All tiers share one opaque single-leaf texture/DDS (london_plane_leaf).
        png_path = os.path.join(png_dir, f"{species_name}_leaf.png")
        leaf_proto = build_distribute_leaf(species_name, png_path, sp.get("leaf_cfg", {}))
        leaf_mat = leaf_proto.data.materials[0]
        print(f"  Leaf (true-3D distribute): {png_path}")

    if leaf_proto is None:
        # Real-photo cluster card (leaf_real_texture): a pre-composited RGBA
        # cluster built from the species' real-leaf cutout
        # (make_leaf_cluster_texture.py) replaces the procedural edge-fn painting
        # — real veins/teeth/silhouette/color, distinct per species. London plane.
        real_tex = sp.get("leaf_real_texture")
        real_tex_path = os.path.join(PROJ, real_tex) if real_tex else None
        leaf_mat = create_leaf_material(
            f"{species_name}_leaf",
            leaf_shape=sp["leaf_shape"],
            n_leaves=sp["leaf_n"],
            tex_size=sp["leaf_tex_size"],
            seed=sp["leaf_seed"],
            fascicle_mode=fascicle,
            compound_mode=compound,
            leaf_scale=sp.get("leaf_scale", 1.0),  # per-species real leaf size (blade-length
                                                   # normalised, oak≈1.0; canopy data §each)
            real_texture=real_tex_path,
        )
        # Viewport display color for Workbench thumbnail renderer
        if fascicle:
            leaf_mat.diffuse_color = (0.17, 0.35, 0.20, 1.0)  # Austrian pine: very dark needle green
        else:
            leaf_mat.diffuse_color = (0.38, 0.62, 0.30, 1.0)  # deciduous green

        # Export leaf texture as PNG for DDS pipeline (coverage-preserving mipmaps).
        # Only needs to happen once per species (all tiers share the same texture).
        png_dir = os.path.join(MODEL_DIR, "leaf_textures")
        os.makedirs(png_dir, exist_ok=True)
        png_path = os.path.join(png_dir, f"{species_name}_leaf.png")
        if real_tex_path:
            # Real-photo cluster: the source PNG IS the DDS-pipeline texture —
            # copy it deterministically (bpy image.save on a loaded file is
            # unreliable across tiers), so generate_leaf_dds picks it up.
            shutil.copy(real_tex_path, png_path)
            print(f"  Leaf texture (real cluster): {png_path}")
        elif not os.path.exists(png_path) or tier_name == "l":
            leaf_img = leaf_mat.node_tree.nodes["Image Texture"].image
            leaf_img.filepath_raw = png_path
            leaf_img.file_format = 'PNG'
            leaf_img.save()
            print(f"  Leaf texture: {png_path}")

    # Create bark material
    bark_mat = bpy.data.materials.new(f"{species_name}_bark")
    bark_mat.use_nodes = True
    bsdf = bark_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*sp["bark_color"], 1.0)
    bsdf.inputs["Roughness"].default_value = sp["bark_roughness"]
    bark_mat.diffuse_color = (*sp["bark_color"], 1.0)

    variant_objects = []

    # Per-tier seed offset avoids Mtree mesher crash seeds that only
    # trigger at specific height+seed combinations (since all tiers now
    # generate independently instead of deriving from _l).
    tier_seed_offset = {"s": 3, "m": 37, "l": 7}  # s:0 produced a disconnected-branch skeleton on v2 (seed 262); nudge to dodge it (2026-06-21)

    # Per-species variant count: high-census species (oak ~2.6k, etc.) widen the
    # seed envelope to 6-8 to kill stand tiling (tree_model_redesign.md §4). The
    # runtime picker is count-agnostic (tree_builder.gd:587) and impostor atlases
    # are per species-tier, so >5 is free downstream.
    n_variants = sp.get("n_variants", N_VARIANTS)

    # ASSET-LEVEL SINGLE-VARIANT PIN (user 2026-06-26, "go to extremes"). A species
    # may declare `pin_variant: <idx>` to ship ONLY its one approved variant. We then
    # iterate just that index but KEEP n_variants as the spanning denominator, so the
    # emitted mesh reproduces the pinned variant's EXACT form: identical seed
    # (base_seed + idx*seed_step + tier_offset, deterministic fork-test) AND identical
    # variant_spans interpolation. The GLB therefore holds ONE mesh, so the runtime
    # (tree_builder.gd:713 `n_variants = meshes.size()`) computes variant_idx =
    # hash % 1 = 0 for EVERY tree — it is physically impossible to populate a second
    # variant. This kills the LOD "see-through band" at its source (variant mismatch
    # between mesh and the single-variant impostor), belt-and-suspenders over the
    # runtime LP_SINGLE_VARIANT pin. NOTE: a naive n_variants:1 does NOT do this — it
    # trips the `n_variants > 1` spanning gate OFF and shifts the seed, yielding an
    # untuned scalar-fallback tree instead of the approved variant.
    _pin = sp.get("pin_variant")
    _gen_indices = [_pin] if _pin is not None else list(range(n_variants))

    for _out_idx, vi in enumerate(_gen_indices):
        base_seed = sp["base_seed"] + vi * sp["seed_step"] + tier_seed_offset.get(tier_name, 0)

        # Tier-specific skeleton overrides
        sp_tier = sp
        tier_overrides = tier_cfg.get("skeleton_overrides")
        if tier_overrides:
            sp_tier = {**sp, **tier_overrides}

        # --- Per-variant DATA-SPANNING ---
        # Variants must reflect the real population spread (user 2026-06-11:
        # "models and variants should reflect the data, within ~1 SD of the
        # mean"), not 5 near-identical seeds. Each param in `variant_spans`
        # cycles its [lo,hi] range across the variants, offset per param so no
        # single variant is uniformly extreme (a young narrow high-fork tree and
        # an old wide low-fork tree both appear, decorrelated). Ranges are set in
        # the SPECIES dict to ±~1 SD of the species' real form distribution.
        # Default: no spans → legacy seed-only variation.
        sp_variant = sp_tier
        # Tier-aware spans: a tier may define its OWN variant_spans, else the
        # species-level spans apply. Without this, species spans (tuned for the
        # mature form) silently CLOBBER a tier's skeleton_overrides for any
        # spanned param — e.g. the young plane's low branch_start / broad limbs
        # were overwritten by the mature [0.22,0.32]/[0.46,0.58] ranges, so the
        # sapling stayed a narrow pole no matter the override (found 2026-06-21).
        spans = tier_cfg.get("variant_spans", sp.get("variant_spans"))
        if spans and n_variants > 1:
            sp_variant = dict(sp_tier)
            for pi, (pname, (lo, hi)) in enumerate(spans.items()):
                t = ((vi + pi) % n_variants) / (n_variants - 1)
                sp_variant[pname] = lo + (hi - lo) * t

        # --- Find a safe seed via fork-test, then generate ---
        seed = base_seed
        if not skip_fork_test:
            MAX_SEED_RETRIES = 8
            for attempt in range(MAX_SEED_RETRIES):
                if _test_seed_safe(sp_variant, target_h, seed):
                    break
                print(f"  v{vi} seed={seed} crashed Mtree mesher, retrying with seed={seed + 1}")
                seed += 1
            else:
                print(f"  WARNING: v{vi} — all {MAX_SEED_RETRIES} seeds crashed, skipping variant")
                continue

        rng = random.Random(seed)
        t0 = time.time()
        cpp_mesh = generate_tree_skeleton(sp_variant, target_h, seed)

        # Name by OUTPUT index (not the source `vi`): a pinned single variant ships
        # as `_v0` so the GLB's lone mesh is index 0, matching the runtime picker.
        mesh = bpy.data.meshes.new(f"{species_name}_{tier_name}_v{_out_idx}")
        trunk_obj = bpy.data.objects.new(f"{species_name}_{tier_name}_v{_out_idx}", mesh)
        bpy.context.collection.objects.link(trunk_obj)
        create_mesh_from_cpp(mesh, cpp_mesh)
        trunk_obj.data.materials.append(bark_mat)

        # --- Clean NaN vertices and get bbox ---
        actual_h, actual_w = clean_nan_vertices(trunk_obj)

        # --- RAMIFICATION CAP (user 2026-06-22 s4 stem/twig redundancy) ---
        # Delete branch geometry beyond `skeleton_max_depth` so the leaf card (the
        # terminal twig sprig) sits at the real tip. Height-independent — the only
        # lever that bounds depth on long-limbed tiers where split-prob can't (see
        # cap_skeleton_depth). Opt-in per tier/species; no-op when unset.
        _max_depth = sp_tier.get("skeleton_max_depth")
        if _max_depth is not None:
            _capped = cap_skeleton_depth(trunk_obj, _max_depth)
            actual_h, actual_w = clean_nan_vertices(trunk_obj)  # bbox after the cut
            if _capped:
                print(f"    ramification cap: depth <= {_max_depth}, "
                      f"{_capped} verts removed beyond tertiary")

        # Min twig diameter is UNSKIPPABLE (user 2026-06-21): resolve it for this
        # tier up front so it runs on EVERY foliage path and is reported below.
        _twig_d, _twig_why = _min_twig_diameter(sp, tier_name)
        _twig_stats = {}

        # --- True-3D Mtree-distributed foliage (foliage_distribute) ---
        # Coherent by construction; bypasses card scatter entirely. Clean the
        # bark first (removes degenerate tip slivers), then instance leaves onto
        # the remaining branches and realise them into trunk_obj.
        if leaf_proto is not None:
            clean_degenerate_geometry(trunk_obj)
            _twig_stats = enforce_min_twig_diameter(trunk_obj, _twig_d, actual_h)
            distribute_foliage(trunk_obj, leaf_proto, sp, tier_name)
            placements = []
            leaf_objs = []
            n_leaf_verts = sum(
                1 for p in trunk_obj.data.polygons
                if p.material_index < len(trunk_obj.material_slots)
                and "leaf" in trunk_obj.material_slots[p.material_index].material.name.lower())
            _do_foliage = False
        else:
            _do_foliage = True

        # --- Place leaf cards ---
        if _do_foliage:
            # CLEAN FIRST, then place (user 2026-06-21). Previously foliage was
            # extracted from the RAW mesh and clean_degenerate_geometry ran AFTER
            # — but the cleanup removes thin branch-tip geometry, orphaning every
            # cluster anchored to a tip that no longer existed. On thin saplings
            # this deleted whole twigs and left big foliage masses floating
            # 0.3-0.7m from bark (check_foliage_connectivity: saplings 5/7 FAIL,
            # l/m fine). Cleaning the bark BEFORE extraction means clusters can
            # only anchor to surviving branches → coherent by construction. The
            # Mtree per-vertex attributes (radius/hierarchy_depth/branch_extent/
            # stem_id) that extract_leaf_positions reads survive the bmesh
            # round-trip (custom point-attribute layers are preserved).
            clean_degenerate_geometry(trunk_obj)
            _twig_stats = enforce_min_twig_diameter(trunk_obj, _twig_d, actual_h)
            # Fuse the ManifoldMesher's separate branch tubes at their junctions +
            # drop stray fragments, so no branch (or the card that would ride it)
            # floats detached (user 2026-07-02). AFTER the min-twig floor (thicker
            # twigs overlap more) and BEFORE foliage (cards anchor to trunk-wood).
            _stitch_stats = stitch_bark_islands(trunk_obj, actual_h, min_twig_m=_twig_d)
            placements = None
            if sp_variant.get("card_leaf_rule"):
                # THE LEAF RULE on cards: deterministic tip-weighted per-branch
                # placement (clusters reach every branch tip). Falls back to the
                # continuous-clad walk if branch attrs are missing.
                placements = _card_placements_per_branch(
                    trunk_obj, sp_variant, target_h, rng, tier=tier_name)
            if placements is None:
                placements = extract_leaf_positions(trunk_obj, sp_variant, target_h, rng, tier=tier_name)

        # --- Create foliage geometry (same strategy for all tiers) ---

        # All tiers use AAA scatter — the _s/_m/_l are age/size variants
        # that render simultaneously, not LOD tiers. Each needs full-quality
        # leaf cards. Smaller trees naturally get fewer clusters (fewer
        # branch tips), but each cluster gets the same detail level.
        if _do_foliage:
          n_cards = sp.get("cards_per_cluster", FOLIAGE_DEFAULTS["cards_per_cluster"])
          if sp.get("branchlet_foliage"):
            # Willow: the data-driven fountain (create_willow_branchlets) supplies
            # ALL foliage — a dense crown shell over the upper dome plus the
            # cascading whip skirt. No Mtree cluster cards: they formed a central
            # foliage column above the weep ("the bush inside the curtain").
            # _s and _m are age variants: young vs mature (form from _willow_form).
            age01 = {"s": 0.12, "m": 0.70, "l": 1.0}.get(tier_name, 0.5)
            leaf_objs = create_willow_branchlets(
                trunk_obj, placements, leaf_mat, bark_mat, rng, target_h, age01)
          else:
            # Continuous-cladding species keep foliage TIGHT to the twigs (small
            # scatter) so every leaf traces a continuous line to the trunk — a
            # sprawling cluster floats free of its branch (check_foliage_
            # connectivity.py; user 2026-06-20). Others keep the legacy spread.
            _scatter = 0.20 if sp.get("foliage_continuous") else 1.0  # tighter (was 0.5→0.25): outer cards of each cluster were sprawling past the connectivity gate (2026-06-21)
            leaf_objs = create_leaf_cards_at_positions(
                placements, leaf_mat, rng, tier=tier_name, n_cards=n_cards,
                cluster_scatter=_scatter, stem_anchor=sp.get("card_stem_anchor"),
                card_half_factor=sp_variant.get("card_half_factor", 1.20))  # sp_variant → tier-overridable (per-tier density, e.g. london_plane l = v2)
            # Legacy hanging-card curtain (superseded by branchlet geometry).
            if sp.get("strand_foliage"):
                leaf_objs += create_strand_cards_at_positions(
                    placements, leaf_mat, rng, target_h)

        # --- Join all objects ---
        bpy.ops.object.select_all(action='DESELECT')
        trunk_obj.select_set(True)
        for lo in leaf_objs:
            lo.select_set(True)
        bpy.context.view_layer.objects.active = trunk_obj
        if leaf_objs:
            bpy.ops.object.join()

        # --- Normalize to MODEL_H ---
        if actual_h > 0.1:
            scale = MODEL_H / actual_h
            for v in trunk_obj.data.vertices:
                v.co *= scale
            trunk_obj.data.update()
            actual_w *= scale

        # --- Center at origin (base at z=0) ---
        min_z = min(
            (v.co.z for v in trunk_obj.data.vertices), default=0.0
        )
        if abs(min_z) > 0.001:
            for v in trunk_obj.data.vertices:
                v.co.z -= min_z
            trunk_obj.data.update()

        # --- Bake wind vertex colors from MTree attributes ---
        bake_wind_vertex_colors(trunk_obj)

        dt = time.time() - t0
        n_leaves = (n_leaf_verts // 2) if leaf_proto is not None else len(placements)
        n_verts = len(trunk_obj.data.vertices)
        n_faces = len(trunk_obj.data.polygons)
        label = "leaves" if leaf_proto is not None else "leaf clusters"
        print(f"  v{vi} seed={seed}: {n_verts:,} verts, {n_faces:,} faces, "
              f"{n_leaves} {label}, h={actual_h:.1f}m w={actual_w:.1f}m ({dt:.1f}s)")
        # UNSKIPPABLE build-report line: every built model states the min twig
        # diameter it shipped with, how many verts it inflated, and WHY (user
        # 2026-06-21). A 0-inflated report is still required — it proves the
        # floor was checked and the model was already above it, not skipped.
        print(f"    min twig Ø {_twig_d * 100:.2f}cm "
              f"[inflated {_twig_stats.get('inflated', 0)} verts, "
              f"{_twig_stats.get('skipped_junction', 0)} junctions preserved] "
              f"— {_twig_why}")

        variant_objects.append(trunk_obj)

    # --- Export all variants in one GLB ---
    bpy.ops.object.select_all(action='DESELECT')
    for obj in variant_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = variant_objects[0]

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
        export_vertex_color='ACTIVE',
    )

    sz = os.path.getsize(out_path) / 1024
    print(f"  → {out_path} ({sz:.0f} KB)")

    # --- Render thumbnail ---
    render_thumbnail(variant_objects, species_name, tier_name)

    # --- Cleanup for next tier ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


# ===========================================================================
# DEAD TREE (no leaves, special handling)
# ===========================================================================

def generate_dead_tree():
    """Generate dead tree snags — broken tops, no foliage."""
    out_path = os.path.join(MODEL_DIR, "dead.glb")
    print(f"\n{'='*60}")
    print(f"  Dead Tree (snag)")
    print(f"  Output: {out_path}")
    print(f"{'='*60}")

    bark_mat = bpy.data.materials.new("dead_bark")
    bark_mat.use_nodes = True
    bsdf = bark_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.42, 0.38, 0.34, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92

    variant_objects = []
    for vi in range(N_VARIANTS):
        seed = 600 + vi * 37
        rng = random.Random(seed)

        tree = m_tree.Tree()
        trunk = m_tree.TrunkFunction()
        trunk.seed = seed
        trunk.length = rng.uniform(8, 14)
        trunk.start_radius = rng.uniform(0.15, 0.28)
        trunk.end_radius = rng.uniform(0.05, 0.10)
        trunk.shape = 0.45                  # Natural taper
        trunk.up_attraction = 0.7           # Mostly vertical (dead wood doesn't bend further)
        trunk.resolution = 0.6
        trunk.randomness = 0.4              # Subtle irregularity, not chaos

        # Short broken stubs — dead branches are stiff and short
        br = m_tree.BranchFunction()
        br.seed = seed + 1
        br.distribution.start = 0.2
        br.distribution.end = rng.uniform(0.6, 0.85)   # Broken top
        br.distribution.density = rng.uniform(0.25, 0.5)  # Sparse — most branches have fallen
        br.gravity.strength = 2.0           # Dead wood is stiff, minimal droop
        br.gravity.stiffness = 0.6          # Rigid branches
        br.gravity.up_attraction = 0.1      # Slight upward tendency (grew up when alive)
        br.split.probability = 0.05         # Almost no splitting (broken off)
        br.flatness = 0.15                  # Slight planar tendency
        br.break_chance = 0.25              # Many branches snap off
        br.resolution = 0.5
        br.length = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(rng.uniform(0.8, 2.5))  # Short stubs
        )
        br.start_radius = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.3))
        br.randomness = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.3))
        br.start_angle = m_tree.PropertyWrapper(
            m_tree.ConstantProperty(rng.uniform(50, 80))    # Angled up (natural growth direction)
        )

        trunk.add_child(br)
        tree.set_trunk_function(trunk)
        tree.execute_functions()

        mesher = m_tree.ManifoldMesher()
        mesher.radial_n_points = 6
        mesher.smooth_iterations = 1
        cpp_mesh = mesher.mesh_tree(tree)

        mesh = bpy.data.meshes.new(f"dead_v{vi}")
        obj = bpy.data.objects.new(f"dead_v{vi}", mesh)
        bpy.context.collection.objects.link(obj)
        create_mesh_from_cpp(mesh, cpp_mesh)
        obj.data.materials.append(bark_mat)

        # Clean NaN, then remove degenerate branch-tip geometry
        actual_h, _ = clean_nan_vertices(obj)
        clean_degenerate_geometry(obj)
        # Unskippable for dead snags too — bare branch stubs are exactly the
        # thin-twig case the floor exists for. Explicit 3cm floor (snags read at
        # mid distance; no foliage to hide a thin tip behind).
        _dead_sp = {"min_twig_diameter": 0.03,
                    "min_twig_rationale": "dead snag — bare stubs have no "
                    "foliage to mask a thin tip; 3cm keeps every stub readable"}
        _twig_d, _twig_why = _min_twig_diameter(_dead_sp, "dead")
        _twig_stats = enforce_min_twig_diameter(obj, _twig_d, actual_h)
        if actual_h > 0.1:
            scale = MODEL_H / actual_h
            for v in obj.data.vertices:
                v.co *= scale
            obj.data.update()
        min_z = min((v.co.z for v in obj.data.vertices), default=0.0)
        if abs(min_z) > 0.001:
            for v in obj.data.vertices:
                v.co.z -= min_z
            obj.data.update()

        # Bake wind vertex colors (dead trees = bark only, no leaves)
        bake_wind_vertex_colors(obj)

        print(f"  v{vi}: {len(obj.data.vertices):,} verts, h={actual_h:.1f}m")
        print(f"    min twig Ø {_twig_d * 100:.2f}cm "
              f"[inflated {_twig_stats.get('inflated', 0)} verts] — {_twig_why}")
        variant_objects.append(obj)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in variant_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = variant_objects[0]
    bpy.ops.export_scene.gltf(
        filepath=out_path, use_selection=True,
        export_format='GLB', export_apply=True,
        export_vertex_color='ACTIVE',
    )
    sz = os.path.getsize(out_path) / 1024
    print(f"  → {out_path} ({sz:.0f} KB)")

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def render_thumbnail(variant_objects, species_name, tier_name):
    """Render a thumbnail preview of the first variant after GLB export."""
    thumb_dir = os.path.join(PROJ, "models", "trees", "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, f"{species_name}_{tier_name}.png")

    # Hide all variants except the first for a clean render
    for obj in variant_objects[1:]:
        obj.hide_render = True

    # Camera — frame a MODEL_H (5m) tree from a 3/4 angle
    cam = bpy.data.cameras.new("ThumbCam")
    cam_obj = bpy.data.objects.new("ThumbCam", cam)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    cam_obj.location = (8, -8, 3.5)
    cam.lens = 50

    # Point camera at tree center
    track = cam_obj.constraints.new('TRACK_TO')
    target = bpy.data.objects.new("ThumbTarget", None)
    target.location = (0, 0, MODEL_H * 0.45)
    bpy.context.collection.objects.link(target)
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    # Key light (sun)
    sun = bpy.data.lights.new("ThumbSun", 'SUN')
    sun_obj = bpy.data.objects.new("ThumbSun", sun)
    bpy.context.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(50), 0, math.radians(30))
    sun.energy = 3.0

    # Fill light (softer, from opposite side) so foliage isn't underexposed
    fill = bpy.data.lights.new("ThumbFill", 'SUN')
    fill_obj = bpy.data.objects.new("ThumbFill", fill)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(70), 0, math.radians(-150))
    fill.energy = 1.2

    # Render settings — Workbench with material color for accurate textures
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.studio_light = 'Default'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.film_transparent = True
    scene.render.filepath = thumb_path
    scene.render.image_settings.file_format = 'PNG'

    try:
        bpy.ops.render.render(write_still=True)
        print(f"  Thumbnail: {thumb_path}")
    except Exception as e:
        print(f"  Thumbnail render failed: {e}")

    # Cleanup render objects
    bpy.data.objects.remove(target, do_unlink=True)
    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.objects.remove(sun_obj, do_unlink=True)
    bpy.data.objects.remove(fill_obj, do_unlink=True)
    bpy.data.cameras.remove(cam)
    bpy.data.lights.remove(sun)
    bpy.data.lights.remove(fill)

    for obj in variant_objects[1:]:
        obj.hide_render = False


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    # Parse CLI args (after --)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    filter_species = None
    filter_tier = None
    skip_fork_test = False
    for i, arg in enumerate(argv):
        if arg == "--species" and i + 1 < len(argv):
            filter_species = argv[i + 1]
        if arg == "--no-fork-test":
            skip_fork_test = True
        if arg == "--tier" and i + 1 < len(argv):
            filter_tier = argv[i + 1]

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    os.makedirs(MODEL_DIR, exist_ok=True)

    t_start = time.time()
    total_species = 0
    total_tiers = 0

    # Generate all tiers independently (no derive — each tier has authentic silhouette)
    for sp_name, sp in SPECIES.items():
        if sp_name.startswith("_"):
            continue  # underscore-prefixed keys (e.g. _TEMPLATE) are scaffolding, never built
        if filter_species and sp_name != filter_species:
            continue

        for tier_name, tier_cfg in sp["tiers"].items():
            if filter_tier and tier_name != filter_tier:
                continue

            generate_species_tier(sp_name, tier_name, sp, tier_cfg,
                                  skip_fork_test=skip_fork_test)
            total_tiers += 1

        total_species += 1

    # Generate dead trees
    if not filter_species or filter_species == "dead":
        if not filter_tier:
            generate_dead_tree()

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  COMPLETE: {total_species} species, {total_tiers} tiers")
    print(f"  Total time: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
    # Force exit — Blender 4.5 --background can hang during cleanup.
    sys.stdout.flush()
    sys.stderr.flush()
    import os as _os
    _os._exit(0)
