"""Understand the Mtree leaf creator: render shipped presets WITH a vein-aware
material, because veins are a per-vertex `vein_distance` attribute (not geometry).

Prior renders used a flat green BSDF that ignored vein_distance, so only the harsh
vein_displacement ridges showed -> the "asterisk". This script:
  1. builds MAPLE, OAK presets UNMODIFIED + the current PLANE candidate,
  2. prints vein_distance stats per leaf (so the ColorRamp can be tuned to real range),
  3. paints veins by reading the vein_distance attribute in the material,
  4. lowers vein_displacement so geometry is near-flat and veins come from the shader.

Run: ~/.local/bin/blender4 --background --python scripts/vegetation/inspect_mtree_leaves.py
"""
import bpy, os, sys, math

OUT = "/tmp/leaf_inspect"
os.makedirs(OUT, exist_ok=True)
bpy.ops.preferences.addon_enable(module='bl_ext.user_default.modular_tree')
ADDON = os.path.expanduser("~/.config/blender/4.5/extensions/user_default/modular_tree")
sys.path.insert(0, ADDON)
from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_leaf_mesh_from_cpp
from python_classes.presets.leaf_presets import apply_preset_to_generator

PLANE = dict(m=5.0, a=1.0, b=1.0, n1=0.85, n2=2.7, n3=2.7, aspect_ratio=1.08,
             margin="Dentate", tooth_count=9, tooth_depth=0.18, tooth_sharpness=0.88,
             vein_density=900.0, kill_distance=0.025, attraction_distance=0.08,
             growth_step_size=0.01,
             midrib_curvature=0.06, cross_curvature=0.1, vein_displacement=0.04,
             edge_curl=0.04)


def vein_material():
    m = bpy.data.materials.new("vein"); m.use_nodes = True
    nt = m.node_tree; nodes = nt.nodes; links = nt.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.65
    attr = nodes.new("ShaderNodeAttribute"); attr.attribute_name = "vein_distance"
    ramp = nodes.new("ShaderNodeValToRGB")
    # vein_distance ~ 0 ON a vein, larger in blade interior. Small band = vein color.
    e = ramp.color_ramp.elements
    e[0].position = 0.0;  e[0].color = (0.08, 0.16, 0.05, 1)   # vein (dark)
    e[1].position = 0.12; e[1].color = (0.27, 0.46, 0.15, 1)   # blade (green)
    links.new(attr.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def stats(me):
    if "vein_distance" not in me.attributes:
        return "NO vein_distance attr"
    vals = [d.value for d in me.attributes["vein_distance"].data]
    if not vals:
        return "vein_distance EMPTY"
    n = len(vals)
    vals_s = sorted(vals)
    return f"vein_distance n={n} min={min(vals):.4f} max={max(vals):.4f} median={vals_s[n//2]:.4f}"


def build(tag, spec, x):
    gen = m_tree.LeafShapeGenerator()
    if isinstance(spec, str):
        apply_preset_to_generator(gen, spec)
    else:
        for k, v in spec.items():
            if k == "margin":
                gen.margin_type = getattr(m_tree.MarginType, v)
            elif hasattr(gen, k):
                setattr(gen, k, v)
        gen.enable_venation = True
        gen.venation_type = m_tree.VenationType.Open
    gen.seed = 1234; gen.asymmetry_seed = 3
    cpp = gen.generate()
    me = bpy.data.meshes.new(tag)
    create_leaf_mesh_from_cpp(me, cpp)
    ob = bpy.data.objects.new(tag, me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(vein_material())
    print(f"  {tag}: {len(me.vertices)}v {len(me.polygons)}f  {stats(me)}")
    # recenter on centroid
    cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
    cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
    for v in me.vertices:
        v.co.x -= cx; v.co.y -= cy
    d = max(ob.dimensions.x, ob.dimensions.y, 1e-4)
    ob.scale = (1.0 / d, 1.0 / d, 1.0 / d)
    bpy.context.view_layer.update()
    ob.location = (x, 0, 0)
    return ob


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    items = [("MAPLE", "MAPLE"), ("OAK", "OAK"), ("PLANE_mine", PLANE)]
    sp = 1.25
    for i, (tag, spec) in enumerate(items):
        build(tag, spec, (i - 1) * sp)

    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = 1800; scn.render.resolution_y = 650
    w = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("w")
    scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.91, 0.93, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 3 * sp * 1.05
    cam = bpy.data.objects.new("c", cam_d); bpy.context.collection.objects.link(cam)
    cam.location = (0, 0, 8); cam.rotation_euler = (0, 0, 0)
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 2.2
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(10), math.radians(6), 0)
    scn.render.filepath = os.path.join(OUT, "presets_veins.png")
    bpy.ops.render.render(write_still=True)
    print("ORDER: MAPLE | OAK | PLANE_mine")
    print("wrote", os.path.join(OUT, "presets_veins.png"))
    sys.stdout.flush(); os._exit(0)


main()
