"""Smoke test: drive Mtree's native LeafShapeGenerator headless.

Proves the procedural leaf creator (superformula contour + margin + space-
colonization venation + 3D deformation) is usable from a background Blender,
dumps its real settable parameter list, and renders the MAPLE preset as a
sanity check. This is the tool we should be using for plane/maple/sweetgum
(user 2026-06-20), not the hand-rolled PIL outline.

Run: blender4 --background --python scripts/vegetation/mtree_leaf_smoketest.py
"""
import bpy, os, sys, math

PROJ = "/home/chris/central-park-walk"
OUT = "/tmp/leaf_mtree"
os.makedirs(OUT, exist_ok=True)

bpy.ops.preferences.addon_enable(module='bl_ext.user_default.modular_tree')
ADDON = os.path.expanduser("~/.config/blender/4.5/extensions/user_default/modular_tree")
sys.path.insert(0, ADDON)
from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_leaf_mesh_from_cpp
from python_classes.presets.leaf_presets import apply_preset_to_generator


def build_leaf(name, preset=None, params=None):
    gen = m_tree.LeafShapeGenerator()
    if preset:
        apply_preset_to_generator(gen, preset)
    for k, v in (params or {}).items():
        if hasattr(gen, k):
            setattr(gen, k, v)
        else:
            print(f"  [warn] generator has no attr {k!r}")
    gen.seed = 1234
    gen.asymmetry_seed = 7
    cpp = gen.generate()
    me = bpy.data.meshes.new(name)
    create_leaf_mesh_from_cpp(me, cpp)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    print(f"  {name}: {len(me.vertices)} verts, {len(me.polygons)} faces")
    return ob


def dump_params():
    gen = m_tree.LeafShapeGenerator()
    attrs = [a for a in dir(gen) if not a.startswith("_")]
    print("=== LeafShapeGenerator settable params ===")
    for a in attrs:
        try:
            print(f"  {a} = {getattr(gen, a)!r}")
        except Exception as e:
            print(f"  {a} (method/err: {e})")


def render(ob, tag):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = scn.render.resolution_y = 700
    scn.render.film_transparent = False
    w = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("w")
    scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.65, 0.72, 1)
    # frame the leaf
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    dim = max(ob.dimensions.x, ob.dimensions.y, 0.5)
    cam_d = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, 0, dim * 2.6); cam.rotation_euler = (0, 0, 0)
    cam_d.ortho_scale = dim * 1.4; cam_d.type = 'ORTHO'
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 4
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(25), math.radians(12), 0)
    scn.render.filepath = os.path.join(OUT, tag)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.objects.remove(s)


bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
dump_params()
print("=== building MAPLE preset (sanity) ===")
mp = build_leaf("maple_preset", preset="MAPLE")
render(mp, "maple_preset.png")
bpy.data.objects.remove(mp)
print(f"rendered to {OUT}")
sys.stdout.flush()
os._exit(0)
