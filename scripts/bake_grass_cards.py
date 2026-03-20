"""Bake BD3D grass models into alpha-cutout texture cards for GPU instancing.

Renders each BD3D grass model from 4 orthogonal side views, composites
into a single RGBA texture, then creates a crossed-quad mesh (3 planes
at 60° intervals = 12 tris) with that texture applied.

Output per grass type:
  - textures/grass/<name>_card.png  (RGBA alpha-cutout texture)
  - models/vegetation/<name>_card.glb (crossed-quad mesh with texture)

Run: blender4 --background --python scripts/bake_grass_cards.py
"""

import bpy
import bmesh
import os
import sys
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LIBRARY_PATH = os.path.join(PROJECT_DIR, "assets/plant_library/geoscatter_plantlibrary.blend")
TEX_DIR = os.path.join(PROJECT_DIR, "textures", "grass")
MESH_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(TEX_DIR, exist_ok=True)
os.makedirs(MESH_DIR, exist_ok=True)

# Resolution per card texture
CARD_RES = 512

# BD3D source → output name, target width (m), target height (m)
# Width/height define the crossed-quad dimensions in world space.
GRASS_CARDS = [
    # Mowed lawn variants — short, dense, upright
    {"bd3d": "GS Lawn mowed 01", "name": "GrassCard_Lawn",      "width": 0.15, "height": 0.06},
    {"bd3d": "GS Lawn mowed 02", "name": "GrassCard_Lawn_B",    "width": 0.12, "height": 0.05},
    {"bd3d": "GS Lawn mowed 03", "name": "GrassCard_Lawn_C",    "width": 0.15, "height": 0.06},
    # Medium clumps — park grass with some length
    {"bd3d": "GS Grass Clump 01", "name": "GrassCard_Clump",    "width": 0.25, "height": 0.20},
    {"bd3d": "GS Grass Clump 02", "name": "GrassCard_Clump_B",  "width": 0.25, "height": 0.22},
    {"bd3d": "GS Grass Clump 03", "name": "GrassCard_Clump_C",  "width": 0.30, "height": 0.18},
    # Wild/tall grass — nature reserve, unmowed
    {"bd3d": "GS Grass Wild Clump 01", "name": "GrassCard_Wild",   "width": 0.40, "height": 0.35},
    {"bd3d": "GS Grass Wild Clump 02", "name": "GrassCard_Wild_B", "width": 0.35, "height": 0.30},
    {"bd3d": "GS Grass 01",            "name": "GrassCard_Tall",   "width": 0.30, "height": 0.30},
    {"bd3d": "GS Grass 02",            "name": "GrassCard_Tall_B", "width": 0.30, "height": 0.25},
    # Woodland floor — sparse, short
    {"bd3d": "GS Grass Duo 01",  "name": "GrassCard_Duo",       "width": 0.18, "height": 0.10},
    {"bd3d": "GS Grass Duo 02",  "name": "GrassCard_Duo_B",     "width": 0.20, "height": 0.12},
    {"bd3d": "GS Grass tiny 01", "name": "GrassCard_Tiny",      "width": 0.15, "height": 0.06},
    # Dry/seasonal
    {"bd3d": "GS Dryland grass small",  "name": "GrassCard_Dry",      "width": 0.18, "height": 0.12},
    {"bd3d": "GS Dryland grass medium", "name": "GrassCard_Dry_Med",  "width": 0.25, "height": 0.25},
    {"bd3d": "GS Grass Dry 01",         "name": "GrassCard_Dead",     "width": 0.25, "height": 0.25},
]


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.cameras, bpy.data.lights]:
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = CARD_RES
    scene.render.resolution_y = CARD_RES
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    # Neutral lighting for clean albedo
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.7, 0.75, 0.8, 1.0)
        bg.inputs[1].default_value = 2.0


def get_bounds(obj):
    """Get world-space AABB for object and all children."""
    import mathutils
    min_v = mathutils.Vector((1e9, 1e9, 1e9))
    max_v = mathutils.Vector((-1e9, -1e9, -1e9))
    for child in [obj] + list(obj.children_recursive):
        if child.type != 'MESH' or child.data is None:
            continue
        for v in child.data.vertices:
            wv = child.matrix_world @ v.co
            min_v.x = min(min_v.x, wv.x)
            min_v.y = min(min_v.y, wv.y)
            min_v.z = min(min_v.z, wv.z)
            max_v.x = max(max_v.x, wv.x)
            max_v.y = max(max_v.y, wv.y)
            max_v.z = max(max_v.z, wv.z)
    return min_v, max_v


def render_side_view(obj, angle_deg, out_path):
    """Render the object from a side angle (rotating around Y axis)."""
    import mathutils
    min_v, max_v = get_bounds(obj)
    center = (min_v + max_v) * 0.5
    size = max_v - min_v
    # Camera distance based on object size
    radius = max(size.x, size.y, size.z) * 0.7
    if radius < 0.01:
        radius = 0.5

    # Position camera
    angle_rad = math.radians(angle_deg)
    cam_x = center.x + math.sin(angle_rad) * radius * 2.0
    cam_z = center.z + math.cos(angle_rad) * radius * 2.0
    cam_y = center.y  # eye level with center

    cam_data = bpy.data.cameras.get("GrassCardCam")
    if not cam_data:
        cam_data = bpy.data.cameras.new("GrassCardCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(size.x, size.z, size.y) * 1.1
    cam_data.clip_start = 0.001
    cam_data.clip_end = radius * 5.0

    cam_obj = bpy.data.objects.get("GrassCardCamObj")
    if not cam_obj:
        cam_obj = bpy.data.objects.new("GrassCardCamObj", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.data = cam_data
    cam_obj.location = (cam_x, cam_y, cam_z)

    # Look at center
    direction = mathutils.Vector((center.x - cam_x, center.y - cam_y, center.z - cam_z))
    rot = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot.to_euler()

    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)


def _make_normal_capture_material():
    """Create a material that renders world-space normals as RGB emission."""
    mat = bpy.data.materials.new("NormalCapture")
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Geometry node → Normal output → map from [-1,1] to [0,1] → Emission
    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-400, 0)

    # Map normal from [-1,1] to [0,1]: (N * 0.5) + 0.5
    multiply = nodes.new('ShaderNodeVectorMath')
    multiply.operation = 'SCALE'
    multiply.inputs[3].default_value = 0.5
    multiply.location = (-200, 0)

    add = nodes.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    add.inputs[1].default_value = (0.5, 0.5, 0.5)
    add.location = (0, 0)

    emission = nodes.new('ShaderNodeEmission')
    emission.location = (200, 0)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    links.new(geom.outputs['Normal'], multiply.inputs[0])
    links.new(multiply.outputs[0], add.inputs[0])
    links.new(add.outputs[0], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    return mat


def _override_materials(obj, override_mat):
    """Override all materials on obj and children with the given material."""
    saved = {}
    for child in [obj] + list(obj.children_recursive):
        if child.type != 'MESH':
            continue
        saved[child.name] = []
        for i in range(len(child.data.materials)):
            saved[child.name].append(child.data.materials[i])
            child.data.materials[i] = override_mat
    return saved


def _restore_materials(obj, saved):
    """Restore original materials from saved dict."""
    for child in [obj] + list(obj.children_recursive):
        if child.type != 'MESH' or child.name not in saved:
            continue
        for i, mat in enumerate(saved[child.name]):
            if i < len(child.data.materials):
                child.data.materials[i] = mat


def composite_views(view_paths, out_path):
    """Composite 4 side views into one texture by taking max alpha per pixel."""
    images = []
    for p in view_paths:
        img = bpy.data.images.load(p)
        images.append(list(img.pixels))
        bpy.data.images.remove(img)

    w, h = CARD_RES, CARD_RES
    result = [0.0] * (w * h * 4)

    for y in range(h):
        for x in range(w):
            idx = (y * w + x) * 4
            best_alpha = 0.0
            best_view = 0
            for vi, pix in enumerate(images):
                a = pix[idx + 3]
                if a > best_alpha:
                    best_alpha = a
                    best_view = vi
            if best_alpha > 0.01:
                src = images[best_view]
                result[idx + 0] = src[idx + 0]
                result[idx + 1] = src[idx + 1]
                result[idx + 2] = src[idx + 2]
                result[idx + 3] = best_alpha

    out_img = bpy.data.images.new("composite", w, h, alpha=True)
    out_img.pixels = result
    out_img.filepath_raw = out_path
    out_img.file_format = 'PNG'
    out_img.save()
    bpy.data.images.remove(out_img)


def make_crossed_quad_glb(card_cfg, tex_path):
    """Create a crossed-quad mesh (3 planes at 60°) with the baked texture."""
    name = card_cfg["name"]
    w = card_cfg["width"]
    h = card_cfg["height"]

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # 3 quads at 0°, 60°, 120°
    for qi in range(3):
        angle = math.radians(qi * 60.0)
        dx = math.cos(angle) * w * 0.5
        dz = math.sin(angle) * w * 0.5
        # Slight inward tilt for cup shape
        tilt = 0.08
        v0 = bm.verts.new((-dx, 0, -dz))
        v1 = bm.verts.new((dx, 0, dz))
        v2 = bm.verts.new((dx * (1 - tilt), h, dz * (1 - tilt)))
        v3 = bm.verts.new((-dx * (1 - tilt), h, -dz * (1 - tilt)))
        bm.verts.ensure_lookup_table()

        f1 = bm.faces.new([v0, v1, v2])
        f2 = bm.faces.new([v0, v2, v3])

        for f in [f1, f2]:
            for loop in f.loops:
                if loop.vert == v0:
                    loop[uv_layer].uv = (0.0, 0.0)
                elif loop.vert == v1:
                    loop[uv_layer].uv = (1.0, 0.0)
                elif loop.vert == v2:
                    loop[uv_layer].uv = (1.0, 1.0)
                elif loop.vert == v3:
                    loop[uv_layer].uv = (0.0, 1.0)

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Load texture
    tex_img = bpy.data.images.load(tex_path)

    # Material
    mat = bpy.data.materials.new(f"mat_{name}")
    mat.use_nodes = True
    mat.blend_method = 'CLIP'
    mat.alpha_threshold = 0.4
    mat.use_backface_culling = False

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Roughness'].default_value = 0.75
    bsdf.inputs['Specular IOR Level'].default_value = 0.08

    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = tex_img
    tex_node.location = (-300, 0)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)

    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    mesh.materials.append(mat)

    # Export
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    out_path = os.path.join(MESH_DIR, f"{name}.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
        export_image_format='AUTO',
    )
    size_kb = os.path.getsize(out_path) // 1024
    print(f"  Mesh: {out_path} ({size_kb} KB, 12 tris)")
    return out_path


def bake_grass_card(card_cfg):
    """Bake one BD3D grass model into a texture card."""
    name = card_cfg["name"]
    bd3d_name = card_cfg["bd3d"]

    print(f"\n{'='*50}")
    print(f"Baking grass card: {name} ← {bd3d_name}")

    # Find the BD3D object
    src = bpy.data.objects.get(bd3d_name)
    if not src:
        print(f"  WARNING: '{bd3d_name}' not found — skipping")
        return False

    # Duplicate into scene root
    dup = src.copy()
    dup.data = src.data.copy()
    bpy.context.scene.collection.objects.link(dup)

    # Also duplicate children (grass models often have child meshes)
    for child in src.children:
        child_dup = child.copy()
        child_dup.data = child.data.copy()
        child_dup.parent = dup
        bpy.context.scene.collection.objects.link(child_dup)

    # Add sun light
    light_data = bpy.data.lights.new("GrassSun", 'SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new("GrassSun", light_data)
    light_obj.rotation_euler = (math.radians(55), math.radians(15), math.radians(-20))
    bpy.context.scene.collection.objects.link(light_obj)

    setup_render()

    # Render from 4 side angles (0°, 90°, 180°, 270°)
    tmp_dir = os.path.join(TEX_DIR, "_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    view_paths = []
    for i, angle in enumerate([0, 90, 180, 270]):
        tmp_path = os.path.join(tmp_dir, f"{name}_v{i}.png")
        render_side_view(dup, angle, tmp_path)
        view_paths.append(tmp_path)

    # Composite best-alpha from 4 views (albedo)
    tex_path = os.path.join(TEX_DIR, f"{name}_card.png")
    composite_views(view_paths, tex_path)
    tex_kb = os.path.getsize(tex_path) // 1024
    print(f"  Albedo: {tex_path} ({tex_kb} KB)")

    # --- Normal pass: override materials, re-render same 4 angles ---
    normal_mat = _make_normal_capture_material()
    saved_mats = _override_materials(dup, normal_mat)

    # Disable scene lighting for clean normals (emission-only)
    scene = bpy.context.scene
    old_bg_strength = 0.0
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        old_bg_strength = bg.inputs[1].default_value
        bg.inputs[1].default_value = 0.0
    light_obj.hide_render = True

    normal_view_paths = []
    for i, angle in enumerate([0, 90, 180, 270]):
        tmp_path = os.path.join(tmp_dir, f"{name}_n{i}.png")
        render_side_view(dup, angle, tmp_path)
        normal_view_paths.append(tmp_path)

    # Restore lighting + materials
    if bg:
        bg.inputs[1].default_value = old_bg_strength
    light_obj.hide_render = False
    _restore_materials(dup, saved_mats)
    bpy.data.materials.remove(normal_mat)

    # Composite normal views (same max-alpha approach — uses albedo alpha for coverage)
    # We need to use the albedo alpha to mask the normal map
    nrm_path = os.path.join(TEX_DIR, f"{name}_normal.png")
    composite_views(normal_view_paths, nrm_path)
    nrm_kb = os.path.getsize(nrm_path) // 1024
    print(f"  Normal: {nrm_path} ({nrm_kb} KB)")

    # Clean up all temp renders
    for p in view_paths + normal_view_paths:
        if os.path.exists(p):
            os.remove(p)
    try:
        os.rmdir(tmp_dir)
    except OSError:
        pass

    # Remove BD3D objects from scene
    for child in list(dup.children):
        bpy.data.objects.remove(child, do_unlink=True)
    bpy.data.objects.remove(dup, do_unlink=True)
    bpy.data.objects.remove(light_obj, do_unlink=True)

    # Create crossed-quad GLB with the baked texture
    # Need a clean scene for the export
    clear_scene()
    make_crossed_quad_glb(card_cfg, tex_path)

    # Clean up
    clear_scene()
    return True


def main():
    print("\n" + "=" * 60)
    print("BD3D Grass → Alpha-Cutout Texture Cards")
    print(f"Texture: {CARD_RES}x{CARD_RES} RGBA")
    print(f"Mesh: 3 crossed quads = 12 tris per card")
    print("=" * 60)

    # Optional filter
    filter_name = ""
    for arg in sys.argv:
        if arg.startswith("--only="):
            filter_name = arg.split("=", 1)[1]

    # Open BD3D library
    print(f"\nOpening BD3D library...")
    bpy.ops.wm.open_mainfile(filepath=LIBRARY_PATH)
    print(f"Loaded {len(bpy.data.objects)} objects")

    try:
        bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    except Exception as e:
        print(f"  (unpack: {e})")

    success = 0
    for card_cfg in GRASS_CARDS:
        if filter_name and filter_name not in card_cfg["name"]:
            continue
        if bake_grass_card(card_cfg):
            success += 1
        # Re-open library for next card (bake_grass_card clears scene)
        bpy.ops.wm.open_mainfile(filepath=LIBRARY_PATH)
        try:
            bpy.ops.file.unpack_all(method='WRITE_LOCAL')
        except:
            pass

    total = len(GRASS_CARDS) if not filter_name else sum(
        1 for c in GRASS_CARDS if filter_name in c["name"])
    print(f"\n{'='*60}")
    print(f"Done: {success}/{total} grass cards baked")
    print("=" * 60)


if __name__ == "__main__":
    main()
