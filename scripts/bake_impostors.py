"""Bake octahedral impostor atlases for all tree species in Blender.

Renders each tree model from 8×8 hemisphere viewing angles into a single
2048×2048 RGBA atlas image. Compatible with the GodotImposter plugin's
ImpostorShader (hemisphere mode, frame_size=8).

Run: blender4 --background --python scripts/bake_impostors.py

Output: textures/impostors/<species>_impostor_albedo.png (one per species)
"""

import bpy
import os
import sys
import math
import json
import mathutils

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
TREE_DIR = os.path.join(PROJECT_DIR, "models", "trees")
OUT_DIR = os.path.join(PROJECT_DIR, "textures", "impostors")
os.makedirs(OUT_DIR, exist_ok=True)

FRAME_SIZE = 8          # 8×8 grid of views
ATLAS_RES = 2048        # total atlas resolution
FRAME_RES = ATLAS_RES // FRAME_SIZE  # 256px per frame

SPECIES = [
    "birch", "callery_pear", "cathedral_elm", "cherry", "deciduous",
    "elm", "ginkgo", "honeylocust", "linden", "london_plane",
    "magnolia", "maple", "oak", "pine", "willow",
]


def hemisphere_octa(u, v):
    """Convert UV [0,1] to hemisphere direction vector.
    Matches GodotImposter OctaUtils.hemisphere_octa() exactly."""
    x = u - v
    z = -1.0 + u + v
    y = 1.0 - abs(x) - abs(z)
    length = math.sqrt(x * x + y * y + z * z)
    if length < 0.001:
        return mathutils.Vector((0, 0, 1))
    return mathutils.Vector((x / length, y / length, z / length))


def setup_render_settings():
    """Configure Blender for impostor atlas rendering."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = FRAME_RES
    scene.render.resolution_y = FRAME_RES
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Simple lighting for clean albedo capture
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.8, 0.8, 0.85, 1.0)  # soft neutral sky
        bg.inputs[1].default_value = 1.5  # moderate strength


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images]:
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def import_tree(species):
    """Import the medium-tier tree GLB. Returns root object or None."""
    glb_path = os.path.join(TREE_DIR, f"{species}_m.glb")
    if not os.path.exists(glb_path):
        print(f"  WARNING: {glb_path} not found")
        return None

    bpy.ops.import_scene.gltf(filepath=glb_path)

    # Find imported objects
    imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not imported:
        print(f"  WARNING: no mesh objects in {species}_m.glb")
        return None

    # Create empty parent and parent all imported meshes
    parent = bpy.data.objects.new(species, None)
    bpy.context.scene.collection.objects.link(parent)
    for obj in imported:
        obj.parent = parent

    return parent


def get_bounding_sphere(obj):
    """Get center and radius of the bounding sphere for object + children."""
    min_c = mathutils.Vector((1e9, 1e9, 1e9))
    max_c = mathutils.Vector((-1e9, -1e9, -1e9))
    for child in [obj] + list(obj.children_recursive):
        if child.type != 'MESH' or child.data is None:
            continue
        for v in child.data.vertices:
            world_v = child.matrix_world @ v.co
            min_c.x = min(min_c.x, world_v.x)
            min_c.y = min(min_c.y, world_v.y)
            min_c.z = min(min_c.z, world_v.z)
            max_c.x = max(max_c.x, world_v.x)
            max_c.y = max(max_c.y, world_v.y)
            max_c.z = max(max_c.z, world_v.z)
    center = (min_c + max_c) * 0.5
    radius = (max_c - min_c).length * 0.5
    return center, max(radius, 0.01)


def setup_camera(center, radius, direction):
    """Position orthographic camera looking at center from direction."""
    cam_data = bpy.data.cameras.get("ImpostorCam")
    if not cam_data:
        cam_data = bpy.data.cameras.new("ImpostorCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = radius * 2.0
    cam_data.clip_start = 0.01
    cam_data.clip_end = radius * 4.0

    cam_obj = bpy.data.objects.get("ImpostorCamObj")
    if not cam_obj:
        cam_obj = bpy.data.objects.new("ImpostorCamObj", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.data = cam_data

    # Position camera
    cam_pos = center + direction * radius * 2.0
    cam_obj.location = cam_pos

    # Look at center
    look_dir = center - cam_pos
    rot = look_dir.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot.to_euler()

    bpy.context.scene.camera = cam_obj
    return cam_obj


def bake_species(species):
    """Bake 8×8 hemisphere impostor atlas for one tree species."""
    print(f"\n{'='*50}")
    print(f"Baking impostor: {species}")
    print(f"{'='*50}")

    clear_scene()
    setup_render_settings()

    # Add a sun light for consistent shading
    light_data = bpy.data.lights.new("Sun", 'SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new("Sun", light_data)
    light_obj.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30))
    bpy.context.scene.collection.objects.link(light_obj)

    tree = import_tree(species)
    if not tree:
        return False

    center, radius = get_bounding_sphere(tree)
    print(f"  Bounding sphere: center={center}, radius={radius:.3f}")

    # Create atlas image
    atlas = bpy.data.images.new(
        f"{species}_impostor",
        width=ATLAS_RES, height=ATLAS_RES,
        alpha=True, float_buffer=False)
    # Initialize fully transparent
    atlas.pixels = [0.0] * (ATLAS_RES * ATLAS_RES * 4)

    # Render from each octahedral direction
    frames_done = 0
    for ix in range(FRAME_SIZE):
        for iy in range(FRAME_SIZE):
            u = ix / (FRAME_SIZE - 1) if FRAME_SIZE > 1 else 0.5
            v = iy / (FRAME_SIZE - 1) if FRAME_SIZE > 1 else 0.5

            direction = hemisphere_octa(u, v)
            setup_camera(center, radius, direction)

            # Render to temp file
            tmp_path = os.path.join(OUT_DIR, f"_tmp_frame.png")
            bpy.context.scene.render.filepath = tmp_path
            bpy.ops.render.render(write_still=True)

            # Load rendered frame and paste into atlas
            frame_img = bpy.data.images.load(tmp_path)
            frame_pixels = list(frame_img.pixels)

            # Paste at grid position (ix, iy) — match ImpostorShader layout
            # x = column (left to right), y = row (bottom to top in Blender)
            atlas_x = ix * FRAME_RES
            atlas_y = iy * FRAME_RES

            atlas_pixels = list(atlas.pixels)
            for py in range(FRAME_RES):
                for px in range(FRAME_RES):
                    src_idx = (py * FRAME_RES + px) * 4
                    dst_x = atlas_x + px
                    dst_y = atlas_y + py
                    dst_idx = (dst_y * ATLAS_RES + dst_x) * 4
                    atlas_pixels[dst_idx + 0] = frame_pixels[src_idx + 0]
                    atlas_pixels[dst_idx + 1] = frame_pixels[src_idx + 1]
                    atlas_pixels[dst_idx + 2] = frame_pixels[src_idx + 2]
                    atlas_pixels[dst_idx + 3] = frame_pixels[src_idx + 3]

            atlas.pixels = atlas_pixels
            bpy.data.images.remove(frame_img)

            frames_done += 1
            if frames_done % 8 == 0:
                print(f"  Rendered {frames_done}/{FRAME_SIZE * FRAME_SIZE} frames")

    # Save atlas
    out_path = os.path.join(OUT_DIR, f"{species}_impostor_albedo.png")
    atlas.filepath_raw = out_path
    atlas.file_format = 'PNG'
    atlas.save()
    print(f"  Saved: {out_path}")

    # Clean up temp
    tmp_path = os.path.join(OUT_DIR, f"_tmp_frame.png")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # Save metadata (needed by Godot ImpostorShader: scale, positionOffset, aabb_max)
    meta = {
        "species": species,
        "frame_size": FRAME_SIZE,
        "atlas_res": ATLAS_RES,
        "center": [center.x, center.y, center.z],
        "radius": radius,
        "scale": radius,  # ortho half-size = radius
        "position_offset": [-center.x, -center.y, -center.z],
        "aabb_max": radius * 0.5,
    }
    meta_path = os.path.join(OUT_DIR, f"{species}_impostor_meta.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    # Report atlas size
    fsize = os.path.getsize(out_path) / 1024
    print(f"  Atlas: {ATLAS_RES}×{ATLAS_RES}, {FRAME_SIZE}×{FRAME_SIZE} frames, {fsize:.0f} KB")
    print(f"  Meta: scale={radius:.3f}, offset=({-center.x:.3f}, {-center.y:.3f}, {-center.z:.3f})")
    return True


def main():
    print("\n" + "=" * 60)
    print("Octahedral Impostor Baker — Central Park Walk Trees")
    print(f"Atlas: {ATLAS_RES}×{ATLAS_RES}, {FRAME_SIZE}×{FRAME_SIZE} frames")
    print(f"Output: {OUT_DIR}")
    print("=" * 60)

    # Optional filter
    filter_species = ""
    for arg in sys.argv:
        if arg.startswith("--only="):
            filter_species = arg.split("=", 1)[1]

    success = 0
    for species in SPECIES:
        if filter_species and species != filter_species:
            continue
        if bake_species(species):
            success += 1

    total = len(SPECIES) if not filter_species else 1
    print(f"\n{'='*60}")
    print(f"Done: {success}/{total} impostor atlases baked")
    print("=" * 60)


if __name__ == "__main__":
    main()
