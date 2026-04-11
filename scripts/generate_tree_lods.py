"""Generate leaf-aware LOD variants of tree models (SpeedTree approach).

Instead of generic mesh decimation (which destroys leaf card UVs and creates
canopy holes), this script:
  1. Separates leaf geometry from bark by material name ("leaf")
  2. Keeps bark geometry IDENTICAL across all LODs
  3. Randomly removes entire leaf card quads (not edge-collapse)
  4. Scales surviving cards UP to maintain constant canopy coverage density

The scale factor is 1/sqrt(keep_ratio):
  LOD1 (50% cards): each card 1.41× larger → same total leaf area
  LOD2 (25% cards): each card 2.0× larger → same total leaf area

For bark-only models (e.g., dead trees), falls back to Blender Decimate.

Run: blender4 --background --python scripts/generate_tree_lods.py
     blender4 --background --python scripts/generate_tree_lods.py -- --only=oak_l
"""

import bpy
import bmesh
import math
import os
import random
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(PROJECT_DIR, "models", "trees")

# Fraction of leaf cards to KEEP at each LOD tier.
LOD_RATIOS = {
    "lod1": 0.50,   # 50% of cards, each scaled 1.41×
    "lod2": 0.25,   # 25% of cards, each scaled 2.0×
}

SPECIES_TIERS = []
for f in sorted(os.listdir(MODEL_DIR)):
    if f.endswith(".glb") and "_lod" not in f:
        name = f.replace(".glb", "")
        if any(name.endswith(s) for s in ("_s", "_m", "_l")):
            SPECIES_TIERS.append(name)
        elif name == "dead":
            SPECIES_TIERS.append(name)


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.armatures]:
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def find_leaf_material_index(mesh):
    """Return the material index for the leaf material, or -1 if none."""
    for i, mat in enumerate(mesh.materials):
        if mat and "leaf" in mat.name.lower():
            return i
    return -1


def find_leaf_islands(bm, leaf_mat_idx):
    """Find connected components among faces with the leaf material.

    Returns a list of islands, each island being a list of face indices.
    Uses Union-Find for efficiency on large meshes.
    """
    # Build mapping: vertex -> set of leaf face indices that use it
    vert_to_faces = {}
    for f in bm.faces:
        if f.material_index == leaf_mat_idx:
            for v in f.verts:
                vert_to_faces.setdefault(v.index, []).append(f.index)

    # Union-Find
    parent = {}
    rank = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    leaf_face_indices = set()
    for f in bm.faces:
        if f.material_index == leaf_mat_idx:
            fi = f.index
            leaf_face_indices.add(fi)
            parent[fi] = fi
            rank[fi] = 0

    # Union faces that share a vertex (both must be leaf faces)
    for vert_idx, face_list in vert_to_faces.items():
        if len(face_list) < 2:
            continue
        first = face_list[0]
        for other in face_list[1:]:
            union(first, other)

    # Group by root
    groups = {}
    for fi in leaf_face_indices:
        root = find(fi)
        groups.setdefault(root, []).append(fi)

    return list(groups.values())


def leaf_aware_lod(obj, keep_ratio, seed):
    """SpeedTree-style leaf card reduction.

    Leaf cards are individually scattered quads (AAA scatter placement),
    each an independent mesh island. We randomly remove whole quads and
    scale survivors up by 1/sqrt(keep_ratio) to maintain coverage density.

    - Bark geometry: untouched (identical across all LODs)
    - Leaf geometry: random quad removal + survivor scaling
    """
    mesh = obj.data
    leaf_mat_idx = find_leaf_material_index(mesh)

    if leaf_mat_idx == -1:
        # Bark-only model (e.g., dead tree) — apply gentle decimation
        decimate_bark_only(obj, keep_ratio)
        return

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    islands = find_leaf_islands(bm, leaf_mat_idx)
    n_total = len(islands)

    if n_total == 0:
        bm.free()
        return

    # Deterministic shuffle so LOD variants are reproducible
    rng = random.Random(seed)
    rng.shuffle(islands)

    n_keep = max(1, round(n_total * keep_ratio))
    keep_islands = islands[:n_keep]
    remove_islands = islands[n_keep:]

    # Scale surviving cards around each card's centroid
    scale_factor = 1.0 / math.sqrt(keep_ratio)
    for island_faces in keep_islands:
        # Collect unique vertices in this island
        island_verts = set()
        for fi in island_faces:
            for v in bm.faces[fi].verts:
                island_verts.add(v)

        # Compute centroid
        cx = sum(v.co.x for v in island_verts) / len(island_verts)
        cy = sum(v.co.y for v in island_verts) / len(island_verts)
        cz = sum(v.co.z for v in island_verts) / len(island_verts)

        # Scale each vertex away from centroid
        for v in island_verts:
            v.co.x = cx + (v.co.x - cx) * scale_factor
            v.co.y = cy + (v.co.y - cy) * scale_factor
            v.co.z = cz + (v.co.z - cz) * scale_factor

    # Delete removed leaf cards
    faces_to_delete = []
    for island_faces in remove_islands:
        for fi in island_faces:
            faces_to_delete.append(bm.faces[fi])
    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

    # Clean up orphaned vertices
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    kept_faces = sum(len(isl) for isl in keep_islands)
    removed_faces = sum(len(isl) for isl in remove_islands)
    print(f"    {obj.name}: {n_total} cards → kept {n_keep} "
          f"({n_keep/n_total*100:.0f}%), scaled {scale_factor:.2f}×, "
          f"removed {removed_faces} faces, kept {kept_faces} faces")


def decimate_bark_only(obj, ratio):
    """Fallback: Blender Decimate for bark-only models (e.g., dead trees)."""
    if obj.type != 'MESH':
        return

    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError:
            pass

    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = ratio
    mod.use_collapse_triangulate = False

    orig_faces = len(obj.data.polygons)
    try:
        bpy.ops.object.modifier_apply(modifier="Decimate")
    except RuntimeError as e:
        print(f"    WARNING: Decimate failed on {obj.name}: {e}")
        if "Decimate" in obj.modifiers:
            obj.modifiers.remove(obj.modifiers["Decimate"])
        return

    new_faces = len(obj.data.polygons)
    print(f"    {obj.name}: {orig_faces} -> {new_faces} faces "
          f"({new_faces/max(orig_faces,1)*100:.0f}%) [bark decimate]")


def process_model(model_name, lod_name, ratio):
    """Load a GLB, apply leaf-aware LOD reduction, and export."""
    src_path = os.path.join(MODEL_DIR, f"{model_name}.glb")
    dst_path = os.path.join(MODEL_DIR, f"{model_name}_{lod_name}.glb")

    if not os.path.exists(src_path):
        print(f"  SKIP: {src_path} not found")
        return False

    clear_scene()

    bpy.ops.import_scene.gltf(filepath=src_path)
    imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    if not imported:
        print(f"  SKIP: no mesh objects in {model_name}.glb")
        return False

    total_orig = sum(len(o.data.polygons) for o in imported)

    # Use model name + lod name as seed for reproducibility
    seed = hash(f"{model_name}_{lod_name}")

    for obj in imported:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        leaf_aware_lod(obj, ratio, seed)
        obj.select_set(False)

    total_new = sum(len(o.data.polygons) for o in imported if o.type == 'MESH')

    # Export
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=dst_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_materials='EXPORT',
        export_yup=True,
    )

    fsize = os.path.getsize(dst_path) / 1024
    print(f"  -> {dst_path} ({fsize:.0f} KB, "
          f"{total_orig} -> {total_new} faces, "
          f"{total_new/max(total_orig,1)*100:.0f}%)")
    return True


def main():
    print("\n" + "=" * 60)
    print("Tree LOD — Leaf-Aware Card Reduction (SpeedTree approach)")
    print(f"Models: {MODEL_DIR}")
    print(f"LOD levels: {list(LOD_RATIOS.keys())}")
    print("=" * 60)

    # Parse --only filter
    filter_model = ""
    for arg in sys.argv:
        if arg.startswith("--only="):
            filter_model = arg.split("=", 1)[1]

    success = 0
    total = 0

    for model_name in SPECIES_TIERS:
        if filter_model and model_name != filter_model:
            continue

        print(f"\n{'─'*40}")
        print(f"  {model_name}")
        print(f"{'─'*40}")

        for lod_name, ratio in LOD_RATIOS.items():
            total += 1
            t0 = time.time()
            if process_model(model_name, lod_name, ratio):
                success += 1
                dt = time.time() - t0
                print(f"  {lod_name} done in {dt:.1f}s")

    print(f"\n{'='*60}")
    print(f"Done: {success}/{total} LOD models generated")
    print("=" * 60)


if __name__ == "__main__":
    main()
