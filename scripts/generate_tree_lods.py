"""Generate decimated LOD variants of tree models for smooth LOD transitions.

Takes each existing tree GLB (e.g., oak_l.glb with 5 variants) and produces
decimated versions that preserve the tree's shape with fewer polygons:
  oak_l_lod1.glb — ~35% of original faces (medium distance)
  oak_l_lod2.glb — ~12% of original faces (far distance)

The decimated models share the exact same trunk/branch structure and leaf
placement as the original — they're the same tree, just with fewer triangles.
This ensures LOD transitions don't change the tree's identity.

Run: blender4 --background --python scripts/generate_tree_lods.py
     blender4 --background --python scripts/generate_tree_lods.py -- --only=oak_l
"""

import bpy
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(PROJECT_DIR, "models", "trees")

# Decimation ratios: fraction of faces to KEEP
LOD_RATIOS = {
    "lod1": 0.35,   # ~35% of faces — good at 90-200m
    "lod2": 0.12,   # ~12% of faces — good at 170-300m
}

SPECIES_TIERS = []
# Build list from existing GLB files
for f in sorted(os.listdir(MODEL_DIR)):
    if f.endswith(".glb") and "_lod" not in f:
        name = f.replace(".glb", "")
        # Skip non-tier files (e.g., "dead.glb" has no tier suffix)
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


def decimate_mesh_object(obj, ratio):
    """Apply Decimate modifier to a mesh object.

    Uses Collapse mode which intelligently removes vertices while
    minimizing visual change to the silhouette. Preserves UVs and
    material assignments.
    """
    if obj.type != 'MESH':
        return

    # Apply any existing modifiers first
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError:
            pass

    # Add and apply Decimate modifier
    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = ratio
    # Preserve UV seams to avoid texture artifacts
    mod.use_collapse_triangulate = False

    orig_faces = len(obj.data.polygons)
    try:
        bpy.ops.object.modifier_apply(modifier="Decimate")
    except RuntimeError as e:
        print(f"    WARNING: Decimate failed on {obj.name}: {e}")
        # Remove the modifier if apply failed
        if "Decimate" in obj.modifiers:
            obj.modifiers.remove(obj.modifiers["Decimate"])
        return

    new_faces = len(obj.data.polygons)
    print(f"    {obj.name}: {orig_faces} -> {new_faces} faces "
          f"({new_faces/max(orig_faces,1)*100:.0f}%)")


def process_model(model_name, lod_name, ratio):
    """Load a GLB, decimate all mesh objects, and export as a new GLB."""
    src_path = os.path.join(MODEL_DIR, f"{model_name}.glb")
    dst_path = os.path.join(MODEL_DIR, f"{model_name}_{lod_name}.glb")

    if not os.path.exists(src_path):
        print(f"  SKIP: {src_path} not found")
        return False

    clear_scene()

    # Import
    bpy.ops.import_scene.gltf(filepath=src_path)
    imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    if not imported:
        print(f"  SKIP: no mesh objects in {model_name}.glb")
        return False

    total_orig = sum(len(o.data.polygons) for o in imported)

    # Decimate each mesh object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in imported:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        decimate_mesh_object(obj, ratio)
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
        export_colors=True,
        export_yup=True,
    )

    fsize = os.path.getsize(dst_path) / 1024
    print(f"  -> {dst_path} ({fsize:.0f} KB, "
          f"{total_orig} -> {total_new} faces, "
          f"{total_new/max(total_orig,1)*100:.0f}%)")
    return True


def main():
    print("\n" + "=" * 60)
    print("Tree LOD Decimation — Central Park Walk")
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
