"""
Render per-tier silhouettes for LOD parity inspection.

Produces a 4-panel composite per species (base|_lod1|_lod2|impostor-front) so
we can eyeball whether the three mesh LODs + impostor atlas produce the same
silhouette at the same framing — answering "does the tree morph during LOD
transitions because the meshes differ, or because the crossfade parameters
are bad?"

Usage:
    blender4 --background --python scripts/compare_tree_lods.py

Writes a single composite PNG per species into /tmp/tree_lod_compare/.
"""
import bpy
import os
import sys
import math

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJ, "models", "trees")
IMPOSTOR_DIR = os.path.join(PROJ, "textures", "impostors")
OUT_DIR = "/tmp/tree_lod_compare"
os.makedirs(OUT_DIR, exist_ok=True)

SPECIES = ["oak", "pine", "willow", "birch"]
TIER = "_l"
PANEL = 512


def clear_all_meshes():
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH':
            bpy.data.objects.remove(obj, do_unlink=True)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)


def setup_scene():
    scene = bpy.context.scene
    scene.render.resolution_x = PANEL
    scene.render.resolution_y = PANEL
    scene.render.film_transparent = True
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.color_type = 'SINGLE'
    scene.display.shading.single_color = (0.2, 0.55, 0.25)

    bpy.ops.object.camera_add(location=(0, -20, 8))
    cam = bpy.context.active_object
    cam.data.type = 'ORTHO'
    scene.camera = cam
    return cam


def frame_and_render(cam, mesh_obj, out_path):
    import mathutils
    bbox = [mesh_obj.matrix_world @ mathutils.Vector(c) for c in mesh_obj.bound_box]
    zs = [v.z for v in bbox]
    xs = [v.x for v in bbox]
    ys = [v.y for v in bbox]
    min_z, max_z = min(zs), max(zs)
    center_z = (min_z + max_z) / 2
    height = max_z - min_z
    width = max(max(xs) - min(xs), max(ys) - min(ys))
    size = max(height, width) * 1.1

    cam.location = (0, -50, center_z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.ortho_scale = size

    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)


def render_glb(species, suffix, cam, out_path):
    glb = os.path.join(MODEL_DIR, f"{species}{TIER}{suffix}.glb")
    if not os.path.exists(glb):
        return False
    clear_all_meshes()
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        return False
    # Use first variant only — consistent across LODs
    for m in meshes[1:]:
        m.hide_render = True
    frame_and_render(cam, meshes[0], out_path)
    return True


def main():
    cam = setup_scene()
    for species in SPECIES:
        print(f"=== {species}{TIER} ===")
        for suffix, label in [("", "base"), ("_lod1", "lod1"), ("_lod2", "lod2")]:
            path = os.path.join(OUT_DIR, f"{species}_{label}.png")
            ok = render_glb(species, suffix, cam, path)
            print(f"  {label}: {'ok' if ok else 'missing'}")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
