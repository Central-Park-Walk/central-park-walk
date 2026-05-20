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
from python_classes.mesh_utils import create_mesh_from_cpp

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


# ===========================================================================
# SPECIES CONFIGURATIONS
# ===========================================================================
# Each species defines botanical parameters mapped to Mtree's API.
# Height tiers: s=small, m=medium, l=large with real-world target heights.
# Branch density and sub-branch density scale naturally with tree size.
# ===========================================================================

SPECIES = {
    # ----- Deciduous broad-crowned -----
    "oak": {
        "name": "Pin Oak (Quercus palustris)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.18,        # Pin oak: very low first branches (USDA Silvics)
        "trunk_shape": 0.5,       # Radius falloff curve
        "up_attraction": 0.5,
        "trunk_randomness": 0.8,
        "branch_start": 0.16,     # Matches low trunk_frac
        "branch_end": 0.95,
        "branch_density": 1.2,
        "branch_length_ratio": 0.30,  # Pin oak: compact crown, 0.25-0.35 of height
        "branch_angle": 55,
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.4,
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
        "leaf_cluster_size_range": (0.38, 0.83),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.55,  # Pin oak LAI 3.0-4.5 → moderate, not dense
        "target_cluster_count_l": 680,
        "base_seed": 105,   # shifted from 100 to avoid Mtree mesher crash at _m tier
        "seed_step": 23,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 12], "skeleton_overrides": {
                "branch_density": 0.7, "branch_split_prob": 0.30, "sub_density": 0.4}},
            "m": {"target_h": 18, "height_range": [12, 20], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.45, "sub_density": 1.0}},
            "l": {"target_h": 25, "height_range": [20, 30]},
        },
    },

    "elm": {
        "name": "American Elm (Ulmus americana)",
        "crown_shape": "Spherical",   # Mtree doesn't have 'vase'; we shape via gravity/up_attraction
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.7,          # Elm trunks grow straight up
        "trunk_randomness": 0.5,
        "branch_start": 0.22,
        "branch_end": 0.92,
        "branch_density": 1.3,
        "branch_length_ratio": 0.45,   # Longer arching branches
        "branch_angle": 35,            # More upright then arching
        "branch_gravity": 12.0,        # Strong gravity creates droop
        "branch_stiffness": 0.15,
        "branch_up_attraction": 0.6,   # Branches go UP first, then arch
        "branch_split_prob": 0.5,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 0.7,            # Reduced: full resolution at sub_density 1.0 → 111MB
        "sub_length_ratio": 0.15,
        "sub_angle": 55,
        "sub_gravity": 15.0,           # Heavy droop on sub-branches
        "sub_stiffness": 0.08,
        "sub_up_attraction": -0.2,     # Sub-branches droop
        "sub_split_prob": 0.3,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.25,
        "sub_resolution": 1.0,
        "bark_color": (0.30, 0.25, 0.18),
        "bark_roughness": 0.88,
        "leaf_shape": "elliptic",
        "leaf_n": 50,
        "leaf_tex_size": 1024,
        "leaf_seed": 777,
        "leaf_cluster_size_range": (0.38, 0.83),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.8,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 700,  # LAI 4-5; American elm is iconic dense shade
        "base_seed": 42,
        "seed_step": 17,
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.30, "sub_density": 0.2}},
            "m": {"target_h": 20, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.1, "branch_split_prob": 0.40, "sub_density": 0.5}},
            "l": {"target_h": 28, "height_range": [22, 30]},
        },
    },

    "cathedral_elm": {
        "name": "Cathedral American Elm (Literary Walk)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.16,            # Short trunk — fork low for vase shape
        "trunk_shape": 0.5,
        "up_attraction": 0.4,          # Less vertical pull — let branches spread
        "trunk_randomness": 0.4,
        "branch_start": 0.14,          # Fork very low (typical mature elm)
        "branch_end": 0.85,
        "branch_density": 1.1,
        "branch_length_ratio": 0.52,   # Longer main branches to reach across path
        "branch_angle": 55,            # Wide vase angle (was 40) — 55° creates arch
        "branch_gravity": 6.0,         # Less gravity — branches sweep UP then out
        "branch_stiffness": 0.20,
        "branch_up_attraction": 0.35,  # Moderate upward pull for vase arch shape
        "branch_split_prob": 0.55,
        "branch_split_angle": 50.0,    # Wide secondary splits (was 45)
        "branch_flatness": 0.50,       # Strong lateral spread (was 0.35)
        "branch_break_chance": 0.01,
        "branch_resolution": 0.8,
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
        "leaf_cluster_size_range": (0.45, 0.90),
        "leaf_flatten_range": (0.40, 0.70),
        "leaf_density": 0.75,  # canopy density (0-1, from real-world LAI) — reduced for <100MB
        "target_cluster_count_l": 950,
        "base_seed": 101,
        "seed_step": 23,
        "tiers": {
            "m": {"target_h": 22, "height_range": [18, 26], "skeleton_overrides": {
                "branch_density": 0.9, "branch_split_prob": 0.45, "sub_density": 0.12}},
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
        "branch_length_ratio": 0.30,  # Sugar maple: compact dense crown
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
        "leaf_cluster_size_range": (0.33, 0.75),
        "leaf_flatten_range": (0.45, 0.60),
        "leaf_density": 0.9,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 1000,  # LAI 5-7; sugar maple denser than oak
        "base_seed": 300,
        "seed_step": 29,
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
        "branch_length_ratio": 0.32,   # Moderate branch length
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
        "leaf_cluster_size_range": (0.42, 0.83),
        "leaf_flatten_range": (0.40, 0.60),
        "leaf_density": 0.65,  # Austrian pine LAI ~4.0 → moderate for conifer
        "target_cluster_count_l": 720,
        "foliage_extent_range": (0.10, 0.95),
        "base_seed": 400,
        "seed_step": 29,
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
        "branch_length_ratio": 0.42,   # Graceful spreading
        "branch_angle": 50,
        "branch_gravity": 9.0,
        "branch_stiffness": 0.15,
        "branch_up_attraction": 0.3,
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
        "leaf_cluster_size_range": (0.30, 0.68),
        "leaf_flatten_range": (0.50, 0.75),
        "leaf_density": 0.55,  # Cherry LAI 3.0-4.0 → moderate, dappled shade
        "target_cluster_count_l": 600,  # LAI 3-4 moderate canopy
        "base_seed": 200,
        "seed_step": 19,
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
        "branch_length_ratio": 0.28,   # Shorter branches → open, airy crown
        "branch_angle": 48,
        "branch_gravity": 7.0,
        "branch_stiffness": 0.18,
        "branch_up_attraction": 0.35,
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
        "leaf_cluster_size_range": (0.30, 0.63),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.35,  # Honeylocust LAI 2.0-2.5 → very airy, dappled light
        "target_cluster_count_l": 420,
        "placement_interval_factor": 0.050,
        "base_seed": 400,
        "seed_step": 29,
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
        "trunk_frac": 0.20,
        "trunk_shape": 0.8,           # Strong central leader
        "up_attraction": 0.8,
        "trunk_randomness": 0.3,
        "branch_start": 0.18,
        "branch_end": 0.95,
        "branch_density": 1.2,         # Reduced from 1.5 to avoid Mtree mesher crash
        "branch_length_ratio": 0.30,
        "branch_angle": 22,            # Notorious narrow crotches (ISA data: 15-30°)
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
        "leaf_cluster_size_range": (0.33, 0.72),
        "leaf_flatten_range": (0.50, 0.70),
        "leaf_density": 0.8,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 630,
        "base_seed": 362,     # Shifted from 351 to avoid Mtree mesher crash at _m tier
        "seed_step": 23,
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
        "branch_end": 0.90,
        "branch_density": 1.2,
        "branch_length_ratio": 0.55,   # Very long scaffold branches (spread ratio ~1.0)
        "branch_angle": 50,
        "branch_gravity": 10.0,        # Scaffold branches arch and droop significantly
        "branch_stiffness": 0.4,
        "branch_up_attraction": 0.5,
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.01,
        "branch_resolution": 1.4,
        # Willow sub-branches: long, drooping curtains
        "sub_density": 1.2,
        "sub_length_ratio": 0.30,      # Long drooping strands
        "sub_angle": 65,
        "sub_gravity": 25.0,           # Strong droop (reduced from 200 — crashed Mtree core)
        "sub_stiffness": 0.05,
        "sub_up_attraction": -0.4,     # Downward tendency (reduced from -0.8)
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
        "leaf_cluster_size_range": (0.27, 0.60),
        "leaf_flatten_range": (0.55, 0.75),
        "leaf_density": 0.45,  # Willow LAI 2.5-3.5 → curtain, not solid mass
        "target_cluster_count_l": 720,
        "cards_per_cluster": 45,
        "droop_factor": 0.3,
        "sub_min_height": 14,          # Sub-branches only on mature willows
        "base_seed": 50,
        "seed_step": 41,
        "tiers": {
            "s": {"target_h": 12, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.7, "branch_split_prob": 0.25, "sub_density": 0.3}},
            "m": {"target_h": 16, "height_range": [14, 20], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.35, "sub_density": 0.8}},
        },
    },

    # ----- Dense symmetrical -----
    "linden": {
        "name": "Linden (Tilia americana)",
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.26,
        "trunk_shape": 0.65,
        "up_attraction": 0.65,
        "trunk_randomness": 0.3,       # Very straight
        "branch_start": 0.24,
        "branch_end": 0.95,
        "branch_density": 1.4,
        "branch_length_ratio": 0.30,   # Compact symmetrical crown (Silvics)
        "branch_angle": 45,
        "branch_gravity": 6.0,
        "branch_stiffness": 0.25,
        "branch_up_attraction": 0.4,
        "branch_split_prob": 0.5,
        "branch_split_angle": 32.0,
        "branch_flatness": 0.20,
        "branch_break_chance": 0.01,
        "branch_resolution": 1.4,
        "sub_density": 1.6,
        "sub_length_ratio": 0.13,
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
        "leaf_cluster_size_range": (0.33, 0.72),
        "leaf_flatten_range": (0.45, 0.60),
        "leaf_density": 0.85,  # Linden LAI 4.5-5.5 → very dense shade tree
        "target_cluster_count_l": 840,
        "placement_interval_factor": 0.032,
        "base_seed": 500,
        "seed_step": 37,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.8, "branch_split_prob": 0.30, "sub_density": 0.4}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.1, "branch_split_prob": 0.40, "sub_density": 1.0}},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },

    # ----- Tall open -----
    "london_plane": {
        "name": "London Plane (Platanus x acerifolia)",
        "crown_shape": "Spherical",
        "trunk_frac": 0.30,
        "trunk_shape": 0.6,
        "up_attraction": 0.6,
        "trunk_randomness": 0.5,
        "branch_start": 0.28,
        "branch_end": 0.95,
        "branch_density": 1.1,
        "branch_length_ratio": 0.38,
        "branch_angle": 60,            # London plane: notably horizontal (50-70°, Silvics)
        "branch_gravity": 8.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.55,
        "branch_split_angle": 40.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.4,
        "sub_density": 1.1,            # Reduced: full resolution at 1.6 → 102MB
        "sub_length_ratio": 0.14,
        "sub_angle": 50,
        "sub_gravity": 10.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.3,
        "sub_split_angle": 35.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.48, 0.45, 0.36),
        "bark_roughness": 0.75,
        "leaf_shape": "lobed",
        "leaf_n": 48,
        "leaf_tex_size": 1024,
        "leaf_seed": 447,
        "leaf_cluster_size_range": (0.38, 0.83),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.8,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 900,  # LAI 5-6; major shade canopy, was dramatically undersized
        "base_seed": 200,
        "seed_step": 31,
        "tiers": {
            "m": {"target_h": 22, "height_range": [15, 25], "skeleton_overrides": {
                "branch_density": 0.9, "branch_split_prob": 0.45, "sub_density": 0.7}},
            "l": {"target_h": 30, "height_range": [25, 35]},
        },
    },

    # ----- Columnar / spur shoots -----
    "ginkgo": {
        "name": "Ginkgo (Ginkgo biloba)",
        "crown_shape": "Conical",
        "trunk_frac": 0.30,
        "trunk_shape": 0.8,
        "up_attraction": 0.8,         # Strong central leader
        "trunk_randomness": 0.3,
        "branch_start": 0.28,
        "branch_end": 0.95,
        "branch_density": 0.8,         # Reduced from 1.2 (crashes mesher at large scale)
        "branch_length_ratio": 0.28,
        "branch_angle": 42,
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
        "leaf_cluster_size_range": (0.27, 0.60),
        "leaf_flatten_range": (0.50, 0.70),
        "leaf_density": 0.55,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 600,  # LAI 3-4; ginkgo fan cluster tops
        "foliage_radius_threshold": 0.40,  # No sub-branches → main branches are thick
        "foliage_min_depth": 0,
        "foliage_extent_range": (0.15, 0.95),
        "sparse_branch_boost": 2.0,
        "sub_min_height": 999,          # Spur shoots crash mesher; use primary-only
        "base_seed": 50,
        "seed_step": 31,
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
        "crown_shape": "Hemispherical",
        "trunk_frac": 0.15,            # Very low branching, often multi-stemmed
        "trunk_shape": 0.5,
        "up_attraction": 0.5,
        "trunk_randomness": 0.6,
        "branch_start": 0.13,          # Matches very low trunk_frac
        "branch_end": 0.90,
        "branch_density": 1.2,
        "branch_length_ratio": 0.42,   # Wide spreading relative to modest height
        "branch_angle": 48,
        "branch_gravity": 7.0,
        "branch_stiffness": 0.2,
        "branch_up_attraction": 0.35,
        "branch_split_prob": 0.45,
        "branch_split_angle": 35.0,
        "branch_flatness": 0.25,
        "branch_break_chance": 0.02,
        "branch_resolution": 1.2,
        "sub_density": 1.3,
        "sub_length_ratio": 0.13,
        "sub_angle": 48,
        "sub_gravity": 9.0,
        "sub_stiffness": 0.12,
        "sub_up_attraction": 0.2,
        "sub_split_prob": 0.25,
        "sub_split_angle": 30.0,
        "sub_flatness": 0.3,
        "sub_resolution": 1.0,
        "bark_color": (0.42, 0.38, 0.32),
        "bark_roughness": 0.78,
        "leaf_shape": "ovate",
        "leaf_n": 45,
        "leaf_tex_size": 1024,
        "leaf_seed": 663,
        "leaf_cluster_size_range": (0.38, 0.83),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.7,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 550,  # LAI 3-4; saucer magnolia thick waxy leaves
        "base_seed": 500,
        "seed_step": 29,
        "tiers": {
            "s": {"target_h": 7, "height_range": [5, 9], "skeleton_overrides": {
                "branch_density": 0.7, "branch_split_prob": 0.25, "sub_density": 0.3}},
        },
    },

    # ----- Generic fallback -----
    "deciduous": {
        "name": "Generic Deciduous",
        "crown_shape": "Spherical",
        "trunk_frac": 0.25,
        "trunk_shape": 0.6,
        "up_attraction": 0.55,
        "trunk_randomness": 0.6,
        "branch_start": 0.22,
        "branch_end": 0.95,
        "branch_density": 1.2,
        "branch_length_ratio": 0.38,
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
        "leaf_cluster_size_range": (0.33, 0.75),
        "leaf_flatten_range": (0.45, 0.65),
        "leaf_density": 0.75,  # canopy density (0-1, from real-world LAI)
        "target_cluster_count_l": 600,
        "base_seed": 700,
        "seed_step": 31,
        "tiers": {
            "s": {"target_h": 10, "height_range": [8, 14], "skeleton_overrides": {
                "branch_density": 0.7, "branch_split_prob": 0.30, "sub_density": 0.4}},
            "m": {"target_h": 18, "height_range": [14, 22], "skeleton_overrides": {
                "branch_density": 1.0, "branch_split_prob": 0.40, "sub_density": 1.0}},
            "l": {"target_h": 25, "height_range": [22, 28]},
        },
    },
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
    trunk.start_radius = height * 0.018
    trunk.end_radius = height * 0.005
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
    br.length = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(height * sp["branch_length_ratio"])
    )
    br.start_radius = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.4))
    br.randomness = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.5))
    br.start_angle = m_tree.PropertyWrapper(
        m_tree.ConstantProperty(float(sp["branch_angle"]))
    )
    crown_name = CROWN_MAP.get(sp["crown_shape"], "Spherical")
    br.crown.shape = getattr(m_tree.CrownShape, crown_name)

    sub_min_h = sp.get("sub_min_height", 0)
    if sp["sub_density"] > 0 and height >= sub_min_h:
        sub = m_tree.BranchFunction()
        sub.seed = seed + 2
        sub.distribution.start = 0.2
        sub.distribution.end = 0.95
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
        sub.start_radius = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.25))
        sub.randomness = m_tree.PropertyWrapper(m_tree.ConstantProperty(0.6))
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
    target_l = sp.get("target_cluster_count_l", 600)
    tier_fraction = {"l": 1.0, "m": 0.40, "s": 0.15}
    target_count = int(target_l * tier_fraction.get(tier, 1.0))

    # Eligible vertices: valid, thin branches, sufficient depth
    eligible = valid & (radii < r_thresh) & (depths >= min_depth)
    eligible_idx = np.where(eligible)[0]

    if len(eligible_idx) == 0:
        print(f"    No eligible vertices for branch-walk, falling back to tips")
        return _extract_leaf_positions_tips(mesh_obj, sp, target_height, rng, tier)

    # Group eligible vertices by stem_id
    stem_ids_arr = stems[eligible_idx].astype(int)
    unique_stems = np.unique(stem_ids_arr)

    # Walk each stem and collect candidate positions
    candidates = []
    for sid in unique_stems:
        mask = eligible & (stems.astype(int) == sid)
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue

        # Sort by extent (base → tip)
        ext_vals = extents[idx]
        sort_order = np.argsort(ext_vals)
        idx = idx[sort_order]
        ext_sorted = ext_vals[sort_order]

        # Walk at interval_frac spacing in extent-space
        next_extent = ext_start
        for ii in range(len(idx)):
            e = ext_sorted[ii]
            if e < next_extent:
                continue
            next_extent = e + interval_frac

            # Smoothstep probability based on extent position
            t = (e - ext_start) / max(ext_end - ext_start, 0.001)
            t = max(0.0, min(1.0, t))
            prob = t * t * (3.0 - 2.0 * t) * boost

            if rng.random() < prob:
                # Average nearby vertices at similar extent (centroid of
                # the tube ring) for a position inside the branch volume
                nearby = idx[np.abs(ext_sorted - e) < interval_frac * 0.3]
                if len(nearby) > 0:
                    centroid = coords[nearby].mean(axis=0)
                else:
                    centroid = coords[idx[ii]]

                pos = Vector((centroid[0], centroid[1],
                              centroid[2] - droop * target_height * 0.05))
                candidates.append(pos)

    # Trim to target count if over
    if len(candidates) > int(target_count * 1.2):
        rng.shuffle(candidates)
        candidates = candidates[:target_count]

    # Supplement with tip placement if branch-walk found too few
    if len(candidates) < target_count * 0.3:
        print(f"    Branch-walk found {len(candidates)} candidates "
              f"(target {target_count}), supplementing with tip placement")
        tip_placements = _extract_leaf_positions_tips(
            mesh_obj, sp, target_height, rng, tier)
        for pos, _sz, _fl in tip_placements:
            if len(candidates) >= target_count:
                break
            candidates.append(pos)

    # Crown-fill fallback: if branch-walk + tips still can't reach target,
    # sample random positions within the convex hull of existing placements.
    # Represents canopy volume on species with sparse branch geometry.
    if len(candidates) > 0 and len(candidates) < target_count * 0.5:
        existing = np.array([[p.x, p.y, p.z] for p in candidates])
        cmin = existing.min(axis=0)
        cmax = existing.max(axis=0)
        # Slight inward padding so clusters sit inside the crown, not on edges
        pad = (cmax - cmin) * 0.08
        cmin += pad
        cmax -= pad
        n_fill = target_count - len(candidates)
        print(f"    Crown-fill: adding {n_fill} synthetic placements "
              f"(had {len(candidates)}/{target_count})")
        for _ in range(n_fill):
            pos = Vector((
                rng.uniform(cmin[0], cmax[0]),
                rng.uniform(cmin[1], cmax[1]),
                rng.uniform(cmin[2], cmax[2]),
            ))
            candidates.append(pos)

    # Build placements with size and flatten
    lo, hi = sp["leaf_cluster_size_range"]
    flo, fhi = sp["leaf_flatten_range"]
    # Card size: uniform across all tiers. The _s/_m/_l are age/size
    # variants that render simultaneously, not LOD tiers — they all
    # need the same per-cluster detail level.
    size_mult = 1.4

    placements = []
    for pos in candidates:
        size = rng.uniform(lo, hi) * (target_height / 25.0) * size_mult
        flatten = rng.uniform(flo, fhi)
        placements.append((pos, size, flatten))

    return placements


def create_leaf_cards_at_positions(placements, leaf_mat, rng, tier="l", n_cards=6):
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
    for pos, size, flatten in placements:
        cluster_radius = size * 1.0  # scatter radius
        card_size = size * 0.55      # individual card ~55% of cluster size

        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")

        for q in range(n_quads):
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
    leaf_mat = create_leaf_material(
        f"{species_name}_leaf",
        leaf_shape=sp["leaf_shape"],
        n_leaves=sp["leaf_n"],
        tex_size=sp["leaf_tex_size"],
        seed=sp["leaf_seed"],
        fascicle_mode=fascicle,
    )
    # Viewport display color for Workbench thumbnail renderer
    if fascicle:
        leaf_mat.diffuse_color = (0.28, 0.52, 0.22, 1.0)  # dark forest green
    else:
        leaf_mat.diffuse_color = (0.38, 0.62, 0.30, 1.0)  # deciduous green

    # Export leaf texture as PNG for DDS pipeline (coverage-preserving mipmaps).
    # Only needs to happen once per species (all tiers share the same texture).
    png_dir = os.path.join(MODEL_DIR, "leaf_textures")
    os.makedirs(png_dir, exist_ok=True)
    png_path = os.path.join(png_dir, f"{species_name}_leaf.png")
    if not os.path.exists(png_path) or tier_name == "l":
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
    tier_seed_offset = {"s": 0, "m": 37, "l": 7}

    for vi in range(N_VARIANTS):
        base_seed = sp["base_seed"] + vi * sp["seed_step"] + tier_seed_offset.get(tier_name, 0)

        # Tier-specific skeleton overrides
        sp_tier = sp
        tier_overrides = tier_cfg.get("skeleton_overrides")
        if tier_overrides:
            sp_tier = {**sp, **tier_overrides}

        # --- Find a safe seed via fork-test, then generate ---
        seed = base_seed
        if not skip_fork_test:
            MAX_SEED_RETRIES = 8
            for attempt in range(MAX_SEED_RETRIES):
                if _test_seed_safe(sp_tier, target_h, seed):
                    break
                print(f"  v{vi} seed={seed} crashed Mtree mesher, retrying with seed={seed + 1}")
                seed += 1
            else:
                print(f"  WARNING: v{vi} — all {MAX_SEED_RETRIES} seeds crashed, skipping variant")
                continue

        rng = random.Random(seed)
        t0 = time.time()
        cpp_mesh = generate_tree_skeleton(sp_tier, target_h, seed)

        mesh = bpy.data.meshes.new(f"{species_name}_{tier_name}_v{vi}")
        trunk_obj = bpy.data.objects.new(f"{species_name}_{tier_name}_v{vi}", mesh)
        bpy.context.collection.objects.link(trunk_obj)
        create_mesh_from_cpp(mesh, cpp_mesh)
        trunk_obj.data.materials.append(bark_mat)

        # --- Clean NaN vertices and get bbox ---
        actual_h, actual_w = clean_nan_vertices(trunk_obj)

        # --- Place leaf cards ---
        placements = extract_leaf_positions(trunk_obj, sp, target_h, rng, tier=tier_name)

        # --- Clean degenerate branch-tip geometry ---
        # Must run after leaf position extraction (uses Mtree vertex attributes)
        # but before join (so only bark mesh is affected).
        clean_degenerate_geometry(trunk_obj)

        # --- Create foliage geometry (same strategy for all tiers) ---
        # All tiers use AAA scatter — the _s/_m/_l are age/size variants
        # that render simultaneously, not LOD tiers. Each needs full-quality
        # leaf cards. Smaller trees naturally get fewer clusters (fewer
        # branch tips), but each cluster gets the same detail level.
        n_cards = sp.get("cards_per_cluster", FOLIAGE_DEFAULTS["cards_per_cluster"])
        leaf_objs = create_leaf_cards_at_positions(placements, leaf_mat, rng, tier=tier_name, n_cards=n_cards)

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
        n_leaves = len(placements)
        n_verts = len(trunk_obj.data.vertices)
        n_faces = len(trunk_obj.data.polygons)
        print(f"  v{vi} seed={seed}: {n_verts:,} verts, {n_faces:,} faces, "
              f"{n_leaves} leaf clusters, h={actual_h:.1f}m w={actual_w:.1f}m ({dt:.1f}s)")

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
