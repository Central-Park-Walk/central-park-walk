"""
Render thumbnail images of every tree model variant.

Usage:
    blender4 --background --python scripts/render_tree_thumbnails.py

Outputs PNGs to models/trees/thumbnails/ — one per variant per tier.
"""

import bpy
import os
import math

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJ, "models", "trees")
OUT_DIR = os.path.join(MODEL_DIR, "thumbnails")
os.makedirs(OUT_DIR, exist_ok=True)

SPECIES = [
    "oak", "elm", "cathedral_elm", "maple", "pine", "cherry", "birch",
    "honeylocust", "callery_pear", "ginkgo", "london_plane", "linden",
    "willow", "magnolia", "deciduous", "dead",
]

TIERS = ["_l", "_m", "_s"]
THUMB_SIZE = 512


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def setup_render():
    scene = bpy.context.scene
    scene.render.resolution_x = THUMB_SIZE
    scene.render.resolution_y = THUMB_SIZE
    scene.render.film_transparent = True
    scene.render.engine = 'BLENDER_EEVEE_NEXT'

    # Light
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))

    # Camera
    bpy.ops.object.camera_add(location=(0, -8, 4))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(65), 0, 0)
    scene.camera = cam
    return cam


def fit_camera_to_object(cam, obj):
    """Adjust camera distance to frame the object."""
    # Get bounding box in world space
    bbox = [obj.matrix_world @ __import__('mathutils').Vector(c) for c in obj.bound_box]
    min_z = min(v.z for v in bbox)
    max_z = max(v.z for v in bbox)
    max_xy = max(max(abs(v.x) for v in bbox), max(abs(v.y) for v in bbox))
    height = max_z - min_z
    center_z = (min_z + max_z) / 2.0

    # Position camera to see the whole tree
    dist = max(height, max_xy * 2) * 1.4
    cam.location = (dist * 0.5, -dist * 0.8, center_z + height * 0.1)
    # Look at center
    direction = __import__('mathutils').Vector((0, 0, center_z)) - cam.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()


def render_glb(species, tier, glb_path, cam):
    """Import GLB, render each variant as a separate thumbnail."""
    clear_objects_only()

    if not os.path.exists(glb_path):
        print(f"  SKIP: {glb_path} not found")
        return

    bpy.ops.import_scene.gltf(filepath=glb_path)
    imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    if not imported:
        print(f"  SKIP: no meshes in {glb_path}")
        return

    # Hide all, then show one at a time for rendering
    for obj in imported:
        obj.hide_render = True
        obj.hide_viewport = True

    for vi, obj in enumerate(imported):
        obj.hide_render = False
        obj.hide_viewport = False

        fit_camera_to_object(cam, obj)

        tier_label = tier.strip('_') if tier else "single"
        filename = f"{species}_{tier_label}_v{vi}.png"
        filepath = os.path.join(OUT_DIR, filename)
        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        print(f"  {filename}")

        obj.hide_render = True
        obj.hide_viewport = True

    # Cleanup imported objects
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)


def clear_objects_only():
    """Remove mesh objects but keep camera and lights."""
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH':
            bpy.data.objects.remove(obj, do_unlink=True)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def main():
    print(f"\n=== Tree Thumbnail Renderer ===")
    print(f"Output: {OUT_DIR}\n")

    clear_scene()
    cam = setup_render()

    for species in SPECIES:
        tiers = TIERS if species != "dead" else [""]
        for tier in tiers:
            glb_path = os.path.join(MODEL_DIR, f"{species}{tier}.glb")
            print(f"\n{species}{tier}:")
            render_glb(species, tier, glb_path, cam)

    print(f"\n=== Done! Thumbnails in {OUT_DIR} ===")


if __name__ == "__main__":
    main()
