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
    """Load the REAL-silhouette plane leaf model (models/leaves/london_plane_leaf.glb,
    Gate-1 approved) and normalize to ~1u so distribute_leaves' scale applies.
    Replaces the old LeafShapeGenerator superformula leaf (read as a star)."""
    glb = os.path.abspath(os.path.join(HERE, "..", "models", "leaves", "london_plane_leaf.glb"))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    ob = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    h = max(ob.dimensions) or 1.0                      # GLB authored ~3u -> 1u
    ob.scale = (1.0 / h, 1.0 / h, 1.0 / h)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob, len(ob.data.vertices)


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
