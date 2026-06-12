"""
Render BARE BRANCH SKELETON (bark material only) of given tree variants.
Side orthographic-style view, white bg — to inspect branch architecture
(the brief: the bare skeleton is where habit is most legible).

Usage:
  blender --background --python scripts/render_skeleton.py -- cathedral_elm_l elm_l oak_l
Outputs /tmp/skel_<name>_v<i>.png  (variant 0 unless --all)
"""
import bpy, sys, os, math
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJ, "models", "trees")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
render_all = "--all" in argv
names = [a for a in argv if not a.startswith("--")]
SIZE = 640


def clear():
    for o in list(bpy.context.scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def setup():
    sc = bpy.context.scene
    sc.render.resolution_x = SIZE
    sc.render.resolution_y = SIZE
    sc.render.film_transparent = False
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    bpy.ops.object.camera_add()
    sc.camera = bpy.context.active_object
    return sc.camera


def strip_leaves(obj):
    """Delete faces assigned to the leaf material (slot >=1), keep bark (slot 0)."""
    import bmesh
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    leaf_faces = [f for f in bm.faces if f.material_index >= 1]
    bmesh.ops.delete(bm, geom=leaf_faces, context='FACES')
    bm.to_mesh(me)
    bm.free()


def fit_cam(cam, obj):
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
    max_x = max(abs(v.x) for v in bb)
    max_y = max(abs(v.y) for v in bb)
    h = max_z - min_z
    cz = (min_z + max_z) / 2
    dist = max(h, max(max_x, max_y) * 2) * 1.35
    cam.location = (0, -dist, cz)           # straight-on side view (−Y)
    d = Vector((0, 0, cz)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Z').to_euler()


def main():
    clear()
    cam = setup()
    for name in names:
        path = os.path.join(MODEL_DIR, f"{name}.glb")
        if not os.path.exists(path):
            print(f"SKIP {path}")
            continue
        # clear meshes between models
        for o in [x for x in bpy.context.scene.objects if x.type == 'MESH']:
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.ops.import_scene.gltf(filepath=path)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        meshes.sort(key=lambda o: o.name)
        idxs = range(len(meshes)) if render_all else [0]
        for vi in idxs:
            for o in meshes:
                o.hide_render = True
            obj = meshes[vi]
            obj.hide_render = False
            strip_leaves(obj)
            fit_cam(cam, obj)
            out = f"/tmp/skel_{name}_v{vi}.png"
            bpy.context.scene.render.filepath = out
            bpy.ops.render.render(write_still=True)
            nf = len(obj.data.polygons)
            print(f"  {out}  ({nf:,} bark faces)")
        for o in meshes:
            bpy.data.objects.remove(o, do_unlink=True)


main()
