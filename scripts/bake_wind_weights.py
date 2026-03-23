"""
Bake wind vertex colors onto existing tree GLBs for GPU wind animation.

Processes all tree GLBs in models/trees/ and adds per-vertex wind weights
as COLOR_0 vertex attribute. Works with existing models that lack MTree
attributes by computing weights from geometry.

Vertex color encoding (AAA Pivot Painter convention):
    R: Trunk sway weight — normalized height (cantilever bending proxy)
    G: Branch sway weight — horizontal distance from trunk axis (branch extension)
    B: Phase variation — position hash for per-branch sway offset
    A: 1.0

Run:
    ~/blender-4.5.8-linux-x64/blender --background --python scripts/bake_wind_weights.py
    ~/blender-4.5.8-linux-x64/blender --background --python scripts/bake_wind_weights.py -- --species oak
"""

import bpy
import bmesh
import os
import sys
import math
import numpy as np

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJ, "models", "trees")


def identify_bark_leaf_materials(obj):
    """Return sets of (bark_mat_indices, leaf_mat_indices) for the object."""
    bark_mats = set()
    leaf_mats = set()
    for mi, slot in enumerate(obj.material_slots):
        if slot.material:
            name = slot.material.name.lower()
            if "leaf" in name or "leaves" in name or "foliage" in name:
                leaf_mats.add(mi)
            else:
                bark_mats.add(mi)
        else:
            bark_mats.add(mi)
    return bark_mats, leaf_mats


def compute_trunk_axis(mesh, bark_mats):
    """Estimate trunk center axis from bottom 10% of bark vertices."""
    bark_verts = set()
    for poly in mesh.polygons:
        if poly.material_index in bark_mats:
            for vi in poly.vertices:
                bark_verts.add(vi)

    if not bark_verts:
        return 0.0, 0.0

    zs = [mesh.vertices[vi].co.z for vi in bark_verts]
    min_z = min(zs)
    max_z = max(zs)
    z_range = max(max_z - min_z, 0.01)
    threshold = min_z + z_range * 0.10

    base_xs = []
    base_ys = []
    for vi in bark_verts:
        v = mesh.vertices[vi]
        if v.co.z <= threshold:
            base_xs.append(v.co.x)
            base_ys.append(v.co.y)

    if not base_xs:
        return 0.0, 0.0
    return sum(base_xs) / len(base_xs), sum(base_ys) / len(base_ys)


def bake_wind_colors_geometry(obj):
    """Bake wind vertex colors from geometry analysis.

    For models without MTree attributes, computes weights from:
    - Height (trunk sway proxy)
    - Horizontal distance from trunk axis (branch extension proxy)
    - Position hash (per-branch phase)
    """
    mesh = obj.data
    n_verts = len(mesh.vertices)
    if n_verts == 0:
        return

    bark_mats, leaf_mats = identify_bark_leaf_materials(obj)
    trunk_cx, trunk_cy = compute_trunk_axis(mesh, bark_mats)

    # Compute vertex bounds
    zs = np.array([mesh.vertices[i].co.z for i in range(n_verts)])
    min_z = zs.min()
    max_z = zs.max()
    z_range = max(max_z - min_z, 0.01)

    # Horizontal distances from trunk axis
    h_dists = np.array([
        math.sqrt((mesh.vertices[i].co.x - trunk_cx) ** 2 +
                   (mesh.vertices[i].co.y - trunk_cy) ** 2)
        for i in range(n_verts)
    ])
    max_h_dist = max(h_dists.max(), 0.01)

    # Per-vertex wind weights
    trunk_weight = np.zeros(n_verts)    # R: height-based trunk sway
    branch_weight = np.zeros(n_verts)   # G: radial branch extension
    phase = np.zeros(n_verts)           # B: per-branch phase hash

    for i in range(n_verts):
        v = mesh.vertices[i]
        h_norm = (v.co.z - min_z) / z_range
        trunk_weight[i] = h_norm
        branch_weight[i] = h_dists[i] / max_h_dist
        # Golden ratio hash for good distribution
        phase[i] = math.fmod(
            abs(math.sin(v.co.x * 127.1 + v.co.y * 311.7 + v.co.z * 74.7) * 43758.5453),
            1.0
        )

    # Identify leaf vertices and boost their weights
    leaf_verts = set()
    for poly in mesh.polygons:
        if poly.material_index in leaf_mats:
            for vi in poly.vertices:
                leaf_verts.add(vi)

    for vi in leaf_verts:
        # Leaves are at branch tips — ensure high branch_weight
        branch_weight[vi] = max(branch_weight[vi], 0.85)
        # Leaves should have at least moderate trunk weight (they're in the crown)
        trunk_weight[vi] = max(trunk_weight[vi], 0.3)

    # Create or replace color attribute
    attr_name = "Col"
    if attr_name in mesh.color_attributes:
        mesh.color_attributes.remove(mesh.color_attributes[attr_name])
    color_attr = mesh.color_attributes.new(
        name=attr_name, type='BYTE_COLOR', domain='CORNER'
    )

    # Write per-loop (face corner) colors
    for poly in mesh.polygons:
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            vi = mesh.loops[li].vertex_index
            color_attr.data[li].color = (
                trunk_weight[vi],
                branch_weight[vi],
                phase[vi],
                1.0,
            )

    # Set as active/render color attribute
    idx = mesh.color_attributes.find(attr_name)
    mesh.color_attributes.active_color_index = idx
    mesh.color_attributes.render_color_index = idx


def bake_wind_colors_mtree(obj):
    """Bake wind vertex colors from MTree custom attributes.

    Uses hierarchy_depth, branch_extent, stem_id if available.
    Falls back to geometry-based computation for leaf vertices
    or if MTree attributes are missing.
    """
    mesh = obj.data
    n_verts = len(mesh.vertices)
    if n_verts == 0:
        return

    # Check for MTree attributes
    hd_attr = mesh.attributes.get("hierarchy_depth")
    be_attr = mesh.attributes.get("branch_extent")
    si_attr = mesh.attributes.get("stem_id")

    if not (hd_attr and be_attr and si_attr):
        # No MTree attributes — fall back to geometry
        print(f"    No MTree attributes, using geometry fallback")
        bake_wind_colors_geometry(obj)
        return

    # Read MTree attributes
    hierarchy_depth = np.zeros(n_verts)
    branch_extent = np.zeros(n_verts)
    stem_id = np.zeros(n_verts)

    hd_attr.data.foreach_get("value", hierarchy_depth)
    be_attr.data.foreach_get("value", branch_extent)
    si_attr.data.foreach_get("value", stem_id)

    # Normalize to 0-1
    max_depth = max(hierarchy_depth.max(), 1.0)
    hierarchy_depth /= max_depth
    max_extent = max(branch_extent.max(), 1.0)
    branch_extent /= max_extent

    # Stem ID → golden ratio hash for per-branch phase
    stem_hash = np.mod(stem_id * 0.61803398875, 1.0)

    # Identify leaf vertices (MTree attributes will be 0 on joined leaf cards)
    bark_mats, leaf_mats = identify_bark_leaf_materials(obj)
    leaf_verts = set()
    for poly in mesh.polygons:
        if poly.material_index in leaf_mats:
            for vi in poly.vertices:
                leaf_verts.add(vi)

    # Fix leaf vertices that have zero MTree data
    if leaf_verts:
        zs = np.array([mesh.vertices[i].co.z for i in range(n_verts)])
        min_z = zs.min()
        z_range = max(zs.max() - min_z, 0.01)

        for vi in leaf_verts:
            v = mesh.vertices[vi]
            h_frac = (v.co.z - min_z) / z_range
            # Leaves are deep in the hierarchy (branch tips)
            hierarchy_depth[vi] = max(hierarchy_depth[vi], h_frac * 0.85 + 0.15)
            # Leaves are at branch extent tips
            branch_extent[vi] = max(branch_extent[vi], 0.85)
            # Phase from position if no stem_id
            if stem_hash[vi] < 0.001:
                stem_hash[vi] = math.fmod(
                    abs(math.sin(v.co.x * 127.1 + v.co.y * 311.7 + v.co.z * 74.7) * 43758.5453),
                    1.0
                )

    # Create color attribute
    attr_name = "Col"
    if attr_name in mesh.color_attributes:
        mesh.color_attributes.remove(mesh.color_attributes[attr_name])
    color_attr = mesh.color_attributes.new(
        name=attr_name, type='BYTE_COLOR', domain='CORNER'
    )

    for poly in mesh.polygons:
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
    print(f"    Baked from MTree attributes ({n_verts} verts, {len(leaf_verts)} leaf)")


def process_glb(filepath):
    """Import a GLB, bake wind vertex colors, re-export."""
    basename = os.path.basename(filepath)
    print(f"\n  Processing {basename}...")

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

    # Import
    bpy.ops.import_scene.gltf(filepath=filepath)
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    if not objects:
        print(f"    WARNING: no meshes in {basename}")
        return

    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        # Try MTree attributes first, geometry fallback
        bake_wind_colors_mtree(obj)

    # Export (overwrite original)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
        export_vertex_color='ACTIVE',
    )
    sz = os.path.getsize(filepath) / 1024
    print(f"    → {basename} ({sz:.0f} KB)")


def main():
    # Parse CLI args (after --)
    argv = sys.argv
    species_filter = None
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        i = 0
        while i < len(args):
            if args[i] == "--species" and i + 1 < len(args):
                species_filter = args[i + 1]
                i += 2
            else:
                i += 1

    # Find all tree GLBs
    glb_files = sorted([
        f for f in os.listdir(MODEL_DIR)
        if f.endswith(".glb") and not f.startswith(".")
    ])

    if species_filter:
        glb_files = [f for f in glb_files if f.startswith(species_filter)]
        print(f"Filtering to species: {species_filter} ({len(glb_files)} files)")

    print(f"Baking wind vertex colors for {len(glb_files)} GLBs...")

    for glb_name in glb_files:
        glb_path = os.path.join(MODEL_DIR, glb_name)
        process_glb(glb_path)

    print(f"\nDone! Processed {len(glb_files)} GLBs.")


if __name__ == "__main__":
    main()
