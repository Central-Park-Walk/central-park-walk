"""Build London plane leaf candidates with Mtree's native LeafShapeGenerator.

Consensus target (references/leaves/london_plane.md, deep-research verified):
5 lobes, moderately-deep ANGULAR sinuses (~1/3 of blade — deeper than sycamore,
shallower than maple/Oriental plane), pointed-acuminate tips, coarse sparse
forward teeth, broad blade (~as wide as long to slightly wider). Built by
varying the MAPLE preset's deltas: shallower tooth_depth, sharper tooth_sharpness,
slightly wider aspect_ratio.

Renders each candidate top-down (petiole up, to match IMG_4070) on a paper-white
background with flat light so the SILHOUETTE reads, for Gate-1 comparison.

Run: blender4 --background --python scripts/vegetation/build_plane_leaf.py
"""
import bpy, os, sys, math

OUT = "/tmp/leaf_mtree"
os.makedirs(OUT, exist_ok=True)
bpy.ops.preferences.addon_enable(module='bl_ext.user_default.modular_tree')
ADDON = os.path.expanduser("~/.config/blender/4.5/extensions/user_default/modular_tree")
sys.path.insert(0, ADDON)
from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_leaf_mesh_from_cpp

# CORRECTED model (per official Mtree tooltips, verified by n1xn2 sweep 2026-06-20):
#   m       = lobe count (5)
#   n1      = roundness: LOW=puffy/broad, HIGH=thin/spiky  -> 0.85 (broad)
#   n2=n3   = lobe shape: LOW=bulging/broad, HIGH=pinched/angular -> 2.7 (broad moderate)
#   DENTATE margin (NOT Lobed) supplies the coarse forward teeth; tooth_count low +
#   tooth_depth high = coarse & sparse (plane signature), not fine serration.
# This replaces the prior n1<1 + LOBED approach, which produced a sweetgum-like star.
BASE = dict(m=5.0, a=1.0, b=1.0, n1=0.85, n2=2.7, n3=2.7,
            vein_density=900.0, kill_distance=0.025,
            attraction_distance=0.08, growth_step_size=0.01,
            midrib_curvature=0.06, cross_curvature=0.1, vein_displacement=0.22,
            edge_curl=0.04)

# The LOBED margin alone only scallops a round superformula. Clean palmate lobes
# come from the CONTOUR: m=5 sets 5-fold symmetry; n1<1 makes the sinuses CONCAVE
# (star points) instead of MAPLE's inflated n1=1.5 round pentagon. Sweep n1 and
# n2=n3 to find clean 5-lobed shape, then refine depth/sharpness.
# Lobing needs n2=n3>=4 (e3 blobs at any n1). n1=0.7,e4 = deep star; RAISE n1 at
# e4 to broaden lobes / shallow the sinuses toward the moderate plane look.
# Moderate plane lobing lives in n1 in [0.7 (deep star) .. 1.0 (faint)] at e4.
# Narrow in for 5 broad lobes, sinuses ~1/3-2/5 toward centre.
CANDIDATES = {
    "n078_e4": dict(n1=0.78, n2=4.0, n3=4.0, tooth_depth=0.45, tooth_sharpness=0.72, aspect_ratio=1.10),
    "n084_e4": dict(n1=0.84, n2=4.0, n3=4.0, tooth_depth=0.45, tooth_sharpness=0.72, aspect_ratio=1.10),
    "n090_e4": dict(n1=0.90, n2=4.0, n3=4.0, tooth_depth=0.45, tooth_sharpness=0.72, aspect_ratio=1.10),
}


def leaf_material():
    m = bpy.data.materials.new("planeleaf"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.19, 0.37, 0.12, 1.0)
    b.inputs["Roughness"].default_value = 0.7
    return m


def build(tag, params, venation=False):
    gen = m_tree.LeafShapeGenerator()
    for k, v in {**BASE, **params}.items():
        setattr(gen, k, v)
    gen.margin_type = m_tree.MarginType.Dentate
    gen.enable_venation = venation
    if venation:
        gen.venation_type = m_tree.VenationType.Open
    gen.seed = 1234
    gen.asymmetry_seed = 3
    cpp = gen.generate()
    me = bpy.data.meshes.new(tag)
    create_leaf_mesh_from_cpp(me, cpp)
    ob = bpy.data.objects.new(tag, me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(leaf_material())
    print(f"  {tag}: {len(me.vertices)}v {len(me.polygons)}f  dims={tuple(round(d,2) for d in ob.dimensions)}")
    return ob


def render(ob, tag):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = scn.render.resolution_y = 1080
    w = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("w")
    scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.88, 0.89, 0.92, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.55
    # centre + frame; petiole-up => look down -Z with the leaf rotated so its
    # long axis points DOWN in frame (match IMG_4070 framing).
    bb = [ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box]
    cx = sum(v.x for v in bb) / 8; cy = sum(v.y for v in bb) / 8
    dim = max(ob.dimensions.x, ob.dimensions.y, 0.3)
    cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = dim * 1.35
    cam = bpy.data.objects.new("c", cam_d); bpy.context.collection.objects.link(cam)
    cam.location = (cx, cy, dim * 3); cam.rotation_euler = (0, 0, 0)
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 2.4
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(22), math.radians(12), 0)
    scn.render.filepath = os.path.join(OUT, tag)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.objects.remove(s)


def orient_apex_down(ob):
    """Rotate about Z so the longest lobe tip points -Y (apex down, petiole at the
    top sinus) — matches IMG_4070 framing and makes the 5-fold blade read as a
    palmate leaf rather than a starfish."""
    import mathutils
    me = ob.data
    cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
    cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
    tip = max(me.vertices, key=lambda v: (v.co.x - cx) ** 2 + (v.co.y - cy) ** 2)
    theta = math.atan2(tip.co.y - cy, tip.co.x - cx)
    ob.rotation_euler = (0, 0, -math.pi / 2 - theta)  # bring tip to -Y
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(rotation=True)


def render_3q(ob, tag):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = scn.render.resolution_y = 1080
    w = bpy.data.worlds[0]
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
    dim = max(ob.dimensions.x, ob.dimensions.y, 0.3)
    cam_d = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = (dim * 1.6, -dim * 1.6, dim * 1.3)
    cam.rotation_euler = (math.radians(58), 0, math.radians(45))
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 3.5
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(40), math.radians(15), 0)
    scn.render.filepath = os.path.join(OUT, tag)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.objects.remove(s)


def build_maple_anchor():
    from python_classes.presets.leaf_presets import apply_preset_to_generator
    gen = m_tree.LeafShapeGenerator()
    apply_preset_to_generator(gen, "MAPLE")
    gen.enable_venation = False
    gen.seed = 1234; gen.asymmetry_seed = 3
    cpp = gen.generate()
    me = bpy.data.meshes.new("maple_anchor")
    create_leaf_mesh_from_cpp(me, cpp)
    ob = bpy.data.objects.new("maple_anchor", me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(leaf_material())
    print(f"  maple_anchor: {len(me.vertices)}v {len(me.polygons)}f")
    return ob


FINAL = dict(tooth_count=9, tooth_depth=0.18, tooth_sharpness=0.88, aspect_ratio=1.08)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
ob = build("plane_FINAL", FINAL, venation=True)
orient_apex_down(ob)
# recenter mesh on centroid so the ortho/3q cameras frame it correctly
_me = ob.data
_cx = sum(v.co.x for v in _me.vertices) / len(_me.vertices)
_cy = sum(v.co.y for v in _me.vertices) / len(_me.vertices)
for _v in _me.vertices:
    _v.co.x -= _cx; _v.co.y -= _cy
bpy.context.view_layer.update()
render(ob, "plane_FINAL_top.png")
render_3q(ob, "plane_FINAL_3q.png")
print("FINAL params:", {**BASE, **FINAL})
print(f"rendered {len(CANDIDATES)} candidates to {OUT}")
sys.stdout.flush()
os._exit(0)
