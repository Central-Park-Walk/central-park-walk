"""
Fast skeleton-architecture sweep for a species. Builds the Mtree skeleton
(no leaves, no full export) for one candidate param set and renders a bark-only
side view — to find a branch-architecture recipe cheaply before a full regen.

One candidate per process (mesher can segfault on bad combos).
  blender --background --python scripts/explore_skeleton.py -- --cand vase_flame
Outputs /tmp/explore_<cand>.png
"""
import bpy, sys, os, math
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
import generate_trees_mtree as gtm  # safe: main() is __main__-guarded

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
cand = argv[argv.index("--cand") + 1] if "--cand" in argv else "base"
SPECIES = "cathedral_elm"
HEIGHT = 30.0
SEED = 108
SIZE = 600

# --- candidate overrides on top of SPECIES[SPECIES] ---
CANDS = {
    "base": {},
    # high fork + thick limbs + ascending envelope, sweep the crown shape
    "vase_flame":   {"trunk_frac": 0.34, "branch_start": 0.34, "crown_shape": "Flame",
                     "branch_start_radius": 0.62, "branch_angle_variation": 0.5,
                     "branch_length_ratio": 0.58},
    "vase_conical": {"trunk_frac": 0.34, "branch_start": 0.34, "crown_shape": "Conical",
                     "branch_start_radius": 0.62, "branch_angle_variation": 0.5,
                     "branch_length_ratio": 0.58},
    "vase_hemi":    {"trunk_frac": 0.34, "branch_start": 0.34, "crown_shape": "Hemispherical",
                     "branch_start_radius": 0.62, "branch_angle_variation": 0.5,
                     "branch_length_ratio": 0.58},
    "vase_tcyl":    {"trunk_frac": 0.34, "branch_start": 0.34, "crown_shape": "TaperedCylindrical",
                     "branch_start_radius": 0.62, "branch_angle_variation": 0.5,
                     "branch_length_ratio": 0.58},
    # isolate the thick-limb + angle effect, keep Spherical crown
    "thick_av":     {"trunk_frac": 0.34, "branch_start": 0.34, "crown_shape": "Spherical",
                     "branch_start_radius": 0.65, "branch_angle_variation": 0.6,
                     "branch_length_ratio": 0.58},
    # stronger up-then-arch: less gravity droop low, more up-attraction
    "vase_arch":    {"trunk_frac": 0.34, "branch_start": 0.34, "crown_shape": "Flame",
                     "branch_start_radius": 0.62, "branch_angle_variation": 0.55,
                     "branch_length_ratio": 0.60, "branch_up_attraction": 0.55,
                     "branch_gravity": 8.0, "branch_angle": 50},
}


def render(obj, out):
    sc = bpy.context.scene
    sc.render.resolution_x = SIZE
    sc.render.resolution_y = SIZE
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    bpy.ops.object.light_add(type='SUN')
    bpy.context.active_object.data.energy = 4.0
    bpy.context.active_object.rotation_euler = (math.radians(55), 0, math.radians(35))
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    sc.camera = cam
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
    max_xy = max(max(abs(v.x) for v in bb), max(abs(v.y) for v in bb))
    h = max_z - min_z
    cz = (min_z + max_z) / 2
    dist = max(h, max_xy * 2) * 1.3
    cam.location = (0, -dist, cz)
    d = Vector((0, 0, cz)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Z').to_euler()
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)


def main():
    for o in list(bpy.context.scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sp = {**gtm.SPECIES[SPECIES], **CANDS[cand]}
    cpp = gtm.generate_tree_skeleton(sp, HEIGHT, SEED)
    me = bpy.data.meshes.new(cand)
    obj = bpy.data.objects.new(cand, me)
    bpy.context.collection.objects.link(obj)
    gtm.create_mesh_from_cpp(me, cpp)
    mat = bpy.data.materials.new("bark")
    mat.diffuse_color = (0.30, 0.22, 0.15, 1)
    me.materials.append(mat)
    nf = len(me.polygons)
    out = f"/tmp/explore_{cand}.png"
    render(obj, out)
    print(f"EXPLORE_OK {cand}: {nf:,} faces -> {out}")


main()
