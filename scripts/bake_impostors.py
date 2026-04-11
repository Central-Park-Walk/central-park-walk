"""Bake octahedral impostor atlases for all tree species in Blender.

Renders each tree model from 8×8 hemisphere viewing angles into three
2048×2048 atlas images: albedo (RGBA), normal (RGB), and depth (grayscale).
Compatible with the GodotImposter-style shader (hemisphere mode).

Run: blender4 --background --python scripts/bake_impostors.py
     blender4 --background --python scripts/bake_impostors.py -- --only=oak

Output per species in textures/impostors/:
  <species>_impostor_albedo.png  (RGBA, alpha = leaf mask)
  <species>_impostor_normal.png  (RGB, camera-space normals encoded 0-1)
  <species>_impostor_depth.png   (grayscale, 0=near 1=far)
  <species>_impostor_meta.json   (bounding sphere, clip range)
"""

import bpy
import os
import sys
import math
import json
import mathutils
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
TREE_DIR = os.path.join(PROJECT_DIR, "models", "trees")
OUT_DIR = os.path.join(PROJECT_DIR, "textures", "impostors")
os.makedirs(OUT_DIR, exist_ok=True)

FRAME_SIZE = 8          # 8×8 grid of views
ATLAS_RES = 2048        # total atlas resolution
FRAME_RES = ATLAS_RES // FRAME_SIZE  # 256px per frame
DILATE_PIXELS = 16      # edge dilation distance

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


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images]:
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def import_tree(species, tier=None):
    """Import tree GLB for atlas baking.

    When tier is specified (e.g. 's', 'm', 'l'), loads that exact tier.
    When tier is None, falls back to _m > _l > _s for compatibility."""
    if tier:
        glb_path = os.path.join(TREE_DIR, f"{species}_{tier}.glb")
        if not os.path.exists(glb_path):
            print(f"  WARNING: {species}_{tier}.glb not found")
            return None
    else:
        glb_path = os.path.join(TREE_DIR, f"{species}_m.glb")
        if not os.path.exists(glb_path):
            glb_path = os.path.join(TREE_DIR, f"{species}_l.glb")
        if not os.path.exists(glb_path):
            glb_path = os.path.join(TREE_DIR, f"{species}_s.glb")
        if not os.path.exists(glb_path):
            print(f"  WARNING: no GLB found for {species}")
            return None

    bpy.ops.import_scene.gltf(filepath=glb_path)
    imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not imported:
        print(f"  WARNING: no mesh objects in {os.path.basename(glb_path)}")
        return None

    parent = bpy.data.objects.new(species, None)
    bpy.context.scene.collection.objects.link(parent)
    for obj in imported:
        obj.parent = parent
    return parent


def get_available_tiers(species):
    """Return list of available tiers for a species (e.g. ['s','m','l'])."""
    tiers = []
    for t in ['s', 'm', 'l']:
        if os.path.exists(os.path.join(TREE_DIR, f"{species}_{t}.glb")):
            tiers.append(t)
    return tiers


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
    cam_pos = center + direction * radius * 2.0
    cam_obj.location = cam_pos
    look_dir = center - cam_pos
    rot = look_dir.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot.to_euler()
    bpy.context.scene.camera = cam_obj
    return cam_obj


def setup_albedo_render():
    """Configure for ambient-only albedo rendering.

    Uses uniform hemisphere lighting (no directional sun) so the atlas
    captures pure albedo without baked-in shadows. Runtime shader handles
    all lighting — baked shadows look wrong at different times of day."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = FRAME_RES
    scene.render.resolution_y = FRAME_RES
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Bright uniform ambient — no directional light, just hemisphere fill
    # so the atlas captures material color without shadows or highlights
    if not scene.world:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        bg.inputs[1].default_value = 2.5

    # Disable compositor (render direct)
    scene.use_nodes = False


def create_normal_capture_material():
    """Create a material that outputs camera-space normals as emission.

    Leaf alpha is handled by applying this material alongside the original
    mesh's alpha clip. The material itself is fully opaque — we rely on
    the original mesh's alpha-clip geometry (GLTF import sets it up).
    """
    mat = bpy.data.materials.new("NormCap")
    mat.use_nodes = True
    mat.use_backface_culling = False
    tree = mat.node_tree
    tree.nodes.clear()

    # Geometry normal → Vector Transform (World → Camera)
    geom = tree.nodes.new('ShaderNodeNewGeometry')
    vec_xf = tree.nodes.new('ShaderNodeVectorTransform')
    vec_xf.vector_type = 'NORMAL'
    vec_xf.convert_from = 'WORLD'
    vec_xf.convert_to = 'CAMERA'
    tree.links.new(geom.outputs['Normal'], vec_xf.inputs['Vector'])

    # Encode [-1,1] → [0,1]: (normal + 1) * 0.5
    # Use VectorMath ADD then SCALE
    add_node = tree.nodes.new('ShaderNodeVectorMath')
    add_node.operation = 'ADD'
    add_node.inputs[1].default_value = (1.0, 1.0, 1.0)
    tree.links.new(vec_xf.outputs['Vector'], add_node.inputs[0])

    scale_node = tree.nodes.new('ShaderNodeVectorMath')
    scale_node.operation = 'SCALE'
    scale_node.inputs['Scale'].default_value = 0.5
    tree.links.new(add_node.outputs['Vector'], scale_node.inputs[0])

    # Emission (unlit — normals should not be affected by scene lighting)
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.inputs['Strength'].default_value = 1.0
    tree.links.new(scale_node.outputs['Vector'], emission.inputs['Color'])

    output = tree.nodes.new('ShaderNodeOutputMaterial')
    tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])

    return mat


def setup_depth_compositor(clip_start, clip_end):
    """Configure compositor to output normalized depth as grayscale."""
    scene = bpy.context.scene
    scene.use_nodes = True
    # Enable Z pass in EEVEE
    scene.view_layers[0].use_pass_z = True

    tree = scene.node_tree
    tree.nodes.clear()

    rl = tree.nodes.new('CompositorNodeRLayers')
    # Map depth: clip_start→0, clip_end→1, clamp
    map_r = tree.nodes.new('CompositorNodeMapRange')
    map_r.inputs['From Min'].default_value = clip_start
    map_r.inputs['From Max'].default_value = clip_end
    map_r.inputs['To Min'].default_value = 0.0
    map_r.inputs['To Max'].default_value = 1.0
    map_r.use_clamp = True
    tree.links.new(rl.outputs['Depth'], map_r.inputs['Value'])

    composite = tree.nodes.new('CompositorNodeComposite')
    tree.links.new(map_r.outputs['Value'], composite.inputs['Image'])


def store_original_materials(tree_obj):
    """Store original materials from all mesh children."""
    originals = {}
    for child in [tree_obj] + list(tree_obj.children_recursive):
        if child.type != 'MESH':
            continue
        mats = []
        for i in range(len(child.data.materials)):
            mats.append(child.data.materials[i])
        originals[child.name] = mats
    return originals


def apply_material_override(tree_obj, mat):
    """Override all mesh materials with the given material."""
    for child in [tree_obj] + list(tree_obj.children_recursive):
        if child.type != 'MESH':
            continue
        for i in range(len(child.data.materials)):
            child.data.materials[i] = mat


def restore_materials(tree_obj, originals):
    """Restore original materials."""
    for child in [tree_obj] + list(tree_obj.children_recursive):
        if child.type != 'MESH':
            continue
        if child.name in originals:
            for i, m in enumerate(originals[child.name]):
                if i < len(child.data.materials):
                    child.data.materials[i] = m


def read_frame_pixels(tmp_path, channels=4):
    """Load rendered frame from disk as numpy array."""
    frame_img = bpy.data.images.load(tmp_path)
    pixels = np.array(frame_img.pixels[:], dtype=np.float32)
    bpy.data.images.remove(frame_img)
    pixels = pixels.reshape((FRAME_RES, FRAME_RES, 4))
    return pixels


def paste_frame(atlas, frame_pixels, ix, iy, channels=4):
    """Paste a frame into the atlas at grid position (ix, iy)."""
    ax = ix * FRAME_RES
    ay = iy * FRAME_RES
    atlas[ay:ay + FRAME_RES, ax:ax + FRAME_RES, :channels] = frame_pixels[:, :, :channels]


def dilate_atlas(atlas, alpha_channel=3, distance=DILATE_PIXELS):
    """Extend opaque pixels into transparent borders to prevent seam artifacts.

    For each transparent pixel within `distance` of an opaque pixel, copy the
    color of the nearest opaque pixel. Works per-frame within the atlas to
    avoid bleeding across frame boundaries.
    """
    h, w, c = atlas.shape
    has_alpha = c >= 4 and alpha_channel >= 0

    for fy in range(FRAME_SIZE):
        for fx in range(FRAME_SIZE):
            y0 = fy * FRAME_RES
            x0 = fx * FRAME_RES
            frame = atlas[y0:y0 + FRAME_RES, x0:x0 + FRAME_RES].copy()

            if has_alpha:
                mask = frame[:, :, alpha_channel] > 0.01
            else:
                # For normal/depth: assume fully black (0,0,0) is empty
                mask = np.any(frame[:, :, :3] > 0.01, axis=2)

            if not np.any(mask) or np.all(mask):
                continue

            result = frame.copy()
            for d in range(1, distance + 1):
                # Expand mask by 1 pixel per iteration
                expanded = np.zeros_like(mask)
                expanded[1:, :] |= mask[:-1, :]
                expanded[:-1, :] |= mask[1:, :]
                expanded[:, 1:] |= mask[:, :-1]
                expanded[:, :-1] |= mask[:, 1:]
                # Diagonals
                expanded[1:, 1:] |= mask[:-1, :-1]
                expanded[1:, :-1] |= mask[:-1, 1:]
                expanded[:-1, 1:] |= mask[1:, :-1]
                expanded[:-1, :-1] |= mask[1:, 1:]

                new_pixels = expanded & ~mask
                if not np.any(new_pixels):
                    break

                # For each new pixel, average from neighboring opaque pixels
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        shifted_mask = np.zeros_like(mask)
                        sy = max(0, -dy)
                        ey = FRAME_RES + min(0, -dy)
                        sx = max(0, -dx)
                        ex = FRAME_RES + min(0, -dx)
                        ty = max(0, dy)
                        tey = FRAME_RES + min(0, dy)
                        tx = max(0, dx)
                        tex = FRAME_RES + min(0, dx)
                        shifted_mask[ty:tey, tx:tex] = mask[sy:ey, sx:ex]
                        fill = new_pixels & shifted_mask
                        ys, xs = np.where(fill)
                        if len(ys) > 0:
                            src_ys = np.clip(ys - dy, 0, FRAME_RES - 1)
                            src_xs = np.clip(xs - dx, 0, FRAME_RES - 1)
                            result[ys, xs, :3] = frame[src_ys, src_xs, :3]

                mask = expanded
                frame = result.copy()

            atlas[y0:y0 + FRAME_RES, x0:x0 + FRAME_RES] = result


def save_atlas(atlas, path, mode='RGBA'):
    """Save numpy atlas array as PNG via Blender."""
    h, w, c = atlas.shape
    img = bpy.data.images.new("_tmp_atlas", width=w, height=h, alpha=(c >= 4))
    flat = atlas.flatten().tolist()
    if c == 3:
        # Expand to RGBA for Blender
        rgba = np.ones((h, w, 4), dtype=np.float32)
        rgba[:, :, :3] = atlas
        flat = rgba.flatten().tolist()
    img.pixels = flat
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def bake_species(species, tier=None):
    """Bake 8×8 hemisphere impostor atlas (albedo + normal + depth).

    When tier is specified, bakes that tier and names files species_tier_impostor_*.
    When tier is None, bakes with the default model fallback (legacy behavior)."""
    label = f"{species}_{tier}" if tier else species
    print(f"\n{'='*50}")
    print(f"Baking impostor: {label}")
    print(f"{'='*50}")

    clear_scene()
    setup_albedo_render()

    # No directional light — ambient-only rendering for pure albedo capture.
    # Runtime shader handles all lighting (sun direction, time of day, etc.)

    tree = import_tree(species, tier)
    if not tree:
        return False

    center, radius = get_bounding_sphere(tree)
    clip_start = 0.01
    clip_end = radius * 4.0
    print(f"  Bounding sphere: center={center}, radius={radius:.3f}")

    # Create normal capture material
    norm_mat = create_normal_capture_material()
    orig_mats = store_original_materials(tree)

    # Allocate atlas arrays (numpy, float32)
    albedo_atlas = np.zeros((ATLAS_RES, ATLAS_RES, 4), dtype=np.float32)
    normal_atlas = np.zeros((ATLAS_RES, ATLAS_RES, 4), dtype=np.float32)
    depth_atlas = np.zeros((ATLAS_RES, ATLAS_RES, 4), dtype=np.float32)

    tmp_path = os.path.join(OUT_DIR, f"_tmp_frame.png")
    frames_done = 0

    for ix in range(FRAME_SIZE):
        for iy in range(FRAME_SIZE):
            u = ix / (FRAME_SIZE - 1) if FRAME_SIZE > 1 else 0.5
            v = iy / (FRAME_SIZE - 1) if FRAME_SIZE > 1 else 0.5
            direction = hemisphere_octa(u, v)
            setup_camera(center, radius, direction)

            # --- Pass 1: Albedo (ambient-only, no directional light) ---
            restore_materials(tree, orig_mats)
            bpy.context.scene.use_nodes = False
            bpy.context.scene.render.filepath = tmp_path
            bpy.ops.render.render(write_still=True)
            pixels = read_frame_pixels(tmp_path)
            paste_frame(albedo_atlas, pixels, ix, iy)

            # --- Pass 2: Normals (material override, unlit) ---
            apply_material_override(tree, norm_mat)
            bpy.context.scene.use_nodes = False
            bpy.context.scene.render.filepath = tmp_path
            bpy.ops.render.render(write_still=True)
            npx = read_frame_pixels(tmp_path)
            # Copy alpha from albedo pass (normal material may not preserve it)
            npx[:, :, 3] = pixels[:, :, 3]
            paste_frame(normal_atlas, npx, ix, iy)

            # --- Pass 3: Depth (compositor) ---
            restore_materials(tree, orig_mats)
            setup_depth_compositor(clip_start, clip_end)
            bpy.context.scene.render.filepath = tmp_path
            bpy.ops.render.render(write_still=True)
            dpx = read_frame_pixels(tmp_path)
            # Alpha from albedo pass
            dpx[:, :, 3] = pixels[:, :, 3]
            paste_frame(depth_atlas, dpx, ix, iy)

            frames_done += 1
            if frames_done % 8 == 0:
                print(f"  Rendered {frames_done}/{FRAME_SIZE * FRAME_SIZE} frames "
                      f"(3 passes each)")

    # Dilation: extend opaque pixels into transparent borders
    print("  Dilating atlas edges...")
    dilate_atlas(albedo_atlas, alpha_channel=3)
    dilate_atlas(normal_atlas, alpha_channel=3)
    dilate_atlas(depth_atlas, alpha_channel=3)

    # Save atlases — include tier in filename when per-tier baking
    albedo_path = os.path.join(OUT_DIR, f"{label}_impostor_albedo.png")
    normal_path = os.path.join(OUT_DIR, f"{label}_impostor_normal.png")
    depth_path = os.path.join(OUT_DIR, f"{label}_impostor_depth.png")

    save_atlas(albedo_atlas, albedo_path)
    save_atlas(normal_atlas, normal_path)
    save_atlas(depth_atlas, depth_path)

    print(f"  Saved: {albedo_path}")
    print(f"  Saved: {normal_path}")
    print(f"  Saved: {depth_path}")

    # Clean up temp
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # Save metadata
    meta = {
        "species": label,
        "frame_size": FRAME_SIZE,
        "atlas_res": ATLAS_RES,
        "center": [center.x, center.y, center.z],
        "radius": radius,
        "scale": radius,
        "position_offset": [-center.x, -center.y, -center.z],
        "aabb_max": radius * 0.5,
        "clip_start": clip_start,
        "clip_end": clip_end,
    }
    meta_path = os.path.join(OUT_DIR, f"{label}_impostor_meta.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    for p in [albedo_path, normal_path, depth_path]:
        fsize = os.path.getsize(p) / 1024
        print(f"  {os.path.basename(p)}: {fsize:.0f} KB")
    print(f"  Meta: scale={radius:.3f}, clip=[{clip_start}, {clip_end:.2f}]")
    return True


def main():
    print("\n" + "=" * 60)
    print("Octahedral Impostor Baker — Central Park Walk Trees")
    print(f"Atlas: {ATLAS_RES}×{ATLAS_RES}, {FRAME_SIZE}×{FRAME_SIZE} frames")
    print(f"Passes: albedo + normal + depth (ambient-only lighting)")
    print(f"Output: {OUT_DIR}")
    print("=" * 60)

    filter_species = ""
    per_tier = True  # Bake each available tier separately for shape matching
    for arg in sys.argv:
        if arg.startswith("--only="):
            filter_species = arg.split("=", 1)[1]
        if arg == "--no-tiers":
            per_tier = False

    success = 0
    total = 0
    for species in SPECIES:
        if filter_species and species != filter_species:
            continue
        if per_tier:
            tiers = get_available_tiers(species)
            if not tiers:
                print(f"  WARNING: no tiers found for {species}")
                continue
            for tier in tiers:
                total += 1
                if bake_species(species, tier):
                    success += 1
            # Also bake a generic (no-tier) version for fallback
            total += 1
            if bake_species(species):
                success += 1
        else:
            total += 1
            if bake_species(species):
                success += 1

    print(f"\n{'='*60}")
    print(f"Done: {success}/{total} impostor atlases baked (3 textures each)")
    print("=" * 60)


if __name__ == "__main__":
    main()
