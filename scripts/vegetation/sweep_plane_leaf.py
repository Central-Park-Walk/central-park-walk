"""Disentangling sweep for the London plane leaf silhouette.

Problem (Gate-1 review): the prior build_plane_leaf.py used superformula n1<1, which
makes the CONTOUR a concave star, then added a LOBED margin on top -> thin spiky star
that reads as SWEETGUM (the species plane must be distinct from). It also had NO coarse
teeth because the single margin pass was spent making the 5 lobes.

This sweep tests two ways to get the real plane look — BROAD moderate lobes + COARSE
SPARSE forward teeth (refs: reference_photos/london planetree/IMG_4070, ref_leaf_single2):

  Family A (lobes from MARGIN): convex contour (n1>=1.3, round pentagon) + LOBED margin
    cuts the 5 lobes. Vary tooth_depth = lobe depth. Limitation: no separate teeth.
  Family B (lobes from CONTOUR, teeth from MARGIN): m=5 contour with n1 near 1.0 makes
    moderate broad lobes; DENTATE margin then adds the coarse forward teeth ON the edges.

All candidates rendered TOP-DOWN on white in one grid image for a single comparison.

Run: ~/.local/bin/blender4 --background --python scripts/vegetation/sweep_plane_leaf.py
"""
import bpy, os, sys, math, mathutils

OUT = "/tmp/leaf_sweep"
os.makedirs(OUT, exist_ok=True)
bpy.ops.preferences.addon_enable(module='bl_ext.user_default.modular_tree')
ADDON = os.path.expanduser("~/.config/blender/4.5/extensions/user_default/modular_tree")
sys.path.insert(0, ADDON)
from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_leaf_mesh_from_cpp

BASE = dict(m=5.0, a=1.0, b=1.0, vein_density=900.0, kill_distance=0.025,
            attraction_distance=0.08, growth_step_size=0.01,
            midrib_curvature=0.05, cross_curvature=0.1, vein_displacement=0.25,
            edge_curl=0.0)

# tag -> (contour/margin params, margin_type)
# Family A: convex contour + LOBED margin makes the lobes (maple-like, shallower).
# Family B: contour makes lobes, DENTATE margin adds coarse forward teeth.
# Disentangling grid per official tooltips: n1=roundness (low=puffy, high=spiky),
# n2=lobe bulge (low=bulging/broad, high=pinched/angular). Plane = broad bulging
# moderate lobes => expect lowish n1 + low n2. DENTATE margin adds coarse teeth.
# Grid: n1 in {0.7,1.0,1.3} x n2 in {1.8,2.6}.
# Refine around the winning cell: n1~0.85, n2~2.6 (broad 5-lobe). Dial lobe
# definition (n2) and COARSEN/SPARSEN the teeth (lower count, deeper) toward the
# plane's coarse forward teeth.
def _c(n2, tc, td):
    return dict(n1=0.85, n2=n2, n3=n2, aspect_ratio=1.08,
                margin="Dentate", tooth_count=tc, tooth_depth=td, tooth_sharpness=0.88)
CAND = {
    "n2_23_t10_d14": _c(2.3, 10, 0.14),
    "n2_26_t10_d14": _c(2.6, 10, 0.14),
    "n2_29_t10_d14": _c(2.9, 10, 0.14),
    "n2_26_t9_d18":  _c(2.6,  9, 0.18),
    "n2_26_t12_d11": _c(2.6, 12, 0.11),
    "n2_29_t9_d18":  _c(2.9,  9, 0.18),
}


def leaf_material():
    m = bpy.data.materials.new("planeleaf"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.27, 0.42, 0.16, 1.0)
    b.inputs["Roughness"].default_value = 0.75
    return m


def orient_apex_down(ob):
    me = ob.data
    cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
    cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
    tip = max(me.vertices, key=lambda v: (v.co.x - cx) ** 2 + (v.co.y - cy) ** 2)
    theta = math.atan2(tip.co.y - cy, tip.co.x - cx)
    ob.rotation_euler = (0, 0, -math.pi / 2 - theta)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(rotation=True)


def build(tag, p, x, y, mat):
    params = {k: v for k, v in p.items() if k not in ("margin",)}
    gen = m_tree.LeafShapeGenerator()
    for k, v in {**BASE, **params}.items():
        setattr(gen, k, v)
    gen.margin_type = getattr(m_tree.MarginType, p["margin"])
    gen.enable_venation = True
    gen.venation_type = m_tree.VenationType.Open
    gen.seed = 1234; gen.asymmetry_seed = 3
    cpp = gen.generate()
    me = bpy.data.meshes.new(tag)
    create_leaf_mesh_from_cpp(me, cpp)
    ob = bpy.data.objects.new(tag, me)
    bpy.context.collection.objects.link(ob)
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(mat)
    orient_apex_down(ob)
    # recenter mesh on its own centroid so grid placement is exact (was clipping)
    cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
    cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
    for v in me.vertices:
        v.co.x -= cx; v.co.y -= cy
    # normalize to ~unit cell, then place on grid
    d = max(ob.dimensions.x, ob.dimensions.y, 1e-4)
    ob.scale = (1.0 / d, 1.0 / d, 1.0 / d)
    bpy.context.view_layer.update()
    ob.location = (x, y, 0)
    print(f"  {tag}: {len(me.vertices)}v {len(me.polygons)}f")
    return ob


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    mat = leaf_material()
    cols = 3
    sp = 1.3
    tags = list(CAND.keys())
    for i, tag in enumerate(tags):
        col = i % cols; row = i // cols
        x = (col - (cols - 1) / 2) * sp
        y = -(row) * sp
        build(tag, CAND[tag], x, y, mat)

    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = 1650; scn.render.resolution_y = 1150
    w = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("w")
    scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.93, 0.95, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.1
    # frame the whole grid
    rows = (len(tags) + cols - 1) // cols
    cx = 0; cy = -(rows - 1) * sp / 2
    cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'
    cam_d.ortho_scale = cols * sp * 1.0
    cam = bpy.data.objects.new("c", cam_d); bpy.context.collection.objects.link(cam)
    cam.location = (cx, cy, 8); cam.rotation_euler = (0, 0, 0)
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 3.0
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(12), math.radians(6), 0)
    scn.render.filepath = os.path.join(OUT, "sweep_grid.png")
    bpy.ops.render.render(write_still=True)
    print("GRID ORDER (left->right, top->bottom):", tags)
    print("wrote", os.path.join(OUT, "sweep_grid.png"))
    sys.stdout.flush()
    os._exit(0)


main()
