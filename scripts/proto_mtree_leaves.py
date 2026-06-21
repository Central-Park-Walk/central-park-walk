"""PROTOTYPE: Mtree-native distribution of a TRUE 3D plane leaf (LeafShapeNode).

Generates the broad palmate Platanus leaf via m_tree.LeafShapeGenerator (MAPLE
preset base, tuned), instances it phyllotactically on the branch skeleton, assigns
a green leaf material, realizes, exports + reports poly cost.

Run: blender4 --background --python scripts/proto_mtree_leaves.py -- --tier s
"""
import bpy, sys, os, importlib.util

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
tier = argv[argv.index("--tier") + 1] if "--tier" in argv else "s"

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gtm", os.path.join(HERE, "generate_trees_mtree.py"))
gtm = importlib.util.module_from_spec(spec); spec.loader.exec_module(gtm)

from python_classes.m_tree_wrapper import lazy_m_tree as m_tree
from python_classes.mesh_utils import create_mesh_from_cpp, create_leaf_mesh_from_cpp
from python_classes.resources.node_groups import distribute_leaves
from python_classes.presets.leaf_presets import apply_preset_to_generator

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)


def make_plane_leaf():
    """Broad palmate Platanus acerifolia leaf (maple-leaved): 3-5 shallow lobes,
    coarse teeth, ~as wide as long."""
    gen = m_tree.LeafShapeGenerator()
    apply_preset_to_generator(gen, "MAPLE", _m_tree=m_tree)
    # Plane tweaks vs maple: slightly wider than long, shallower broader lobes.
    gen.aspect_ratio = 1.08
    gen.n1 = 1.7
    gen.seed = 7
    gen.asymmetry_seed = 3
    cpp = gen.generate()
    me = bpy.data.meshes.new("plane_leaf")
    create_leaf_mesh_from_cpp(me, cpp)
    ob = bpy.data.objects.new("plane_leaf", me)
    bpy.context.collection.objects.link(ob)
    # Green leaf material with translucency (stand-in for the project SSS shader).
    m = bpy.data.materials.new("plane_leaf_mat"); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.13, 0.32, 0.08, 1)
    b.inputs["Roughness"].default_value = 0.6
    me.materials.append(m)
    return ob, len(me.vertices)


leaf, leaf_v = make_plane_leaf()
print("PLANE LEAF verts=%d  dims=%.3f x %.3f" % (leaf_v, leaf.dimensions.x, leaf.dimensions.y))

sp = gtm.SPECIES["london_plane"]
tcfg = sp["tiers"][tier]; target_h = tcfg["target_h"]
sp_tier = dict(sp); sp_tier.update(tcfg.get("skeleton_overrides", {}))
cpp_mesh = gtm.generate_tree_skeleton(sp_tier, target_h, 200)
mesh = bpy.data.meshes.new(f"plane_{tier}")
obj = bpy.data.objects.new(f"plane_{tier}", mesh)
bpy.context.collection.objects.link(mesh and obj)
create_mesh_from_cpp(mesh, cpp_mesh)

bpy.context.view_layer.objects.active = obj
obj.select_set(True)
# Leaf base size ~1u from generator → scale to a real ~0.18m plane leaf.
distribute_leaves(
    obj, leaf_object=leaf,
    distribution_mode=1, phyllotaxis_angle=137.5,
    density=120.0, scale=0.16, max_radius=0.05,
    billboard_mode="OFF", enable_normal_transfer=True)
bpy.ops.object.modifier_apply(modifier="leaves")
print("TREE+LEAVES verts=%d  mats=%s" % (
    len(obj.data.vertices), [m.name if m else None for m in obj.data.materials]))

out = "/tmp/proto_plane_%s.glb" % tier
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_format="GLB")
print("EXPORTED", out, os.path.getsize(out) // 1024, "KB")
