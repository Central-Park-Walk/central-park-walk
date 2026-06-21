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
SPECIES = argv[argv.index("--species") + 1] if "--species" in argv else "cathedral_elm"
HEIGHT = float(argv[argv.index("--height") + 1]) if "--height" in argv else 30.0
SEED = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 108
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

    # --- London plane: DECURRENT vase/candelabra (ref: london-plane-tree-01-02.jpg
    #     wireframe + Lincoln's Inn bare-winter). Current SPECIES is a bottlebrush:
    #     up_attraction 0.6 (dominant leader) + short branches (0.38) + low
    #     angle_variation (0.25) + weak flatness (0.25). Goal: stout trunk forks
    #     into a FEW thick crooked major limbs -> broad rounded crown, clear
    #     hierarchy (NOT a pole with sticks). Levers below explored one at a time.
    "lp_base": {},   # render the current SPECIES london_plane as-is for A/B
    # kill leader dominance + long spreading limbs + vase arch + lateral spread
    "lp_decurrent": {"up_attraction": 0.35, "branch_length_ratio": 0.58,
                     "branch_angle_variation": 0.55, "branch_flatness": 0.45,
                     "branch_end": 0.80, "branch_angle": 58, "crown_shape": "Spherical"},
    # decurrent + fork lower into a candelabra (open-grown CP plane forks low)
    "lp_low_fork":  {"up_attraction": 0.32, "branch_length_ratio": 0.60,
                     "branch_angle_variation": 0.55, "branch_flatness": 0.45,
                     "branch_end": 0.80, "branch_angle": 58, "crown_shape": "Spherical",
                     "branch_start": 0.22, "trunk_frac": 0.24},
    # FEWER, THICKER major limbs (plane has heavy scaffold, not a fine fountain)
    "lp_thick_few": {"up_attraction": 0.35, "branch_length_ratio": 0.58,
                     "branch_angle_variation": 0.55, "branch_flatness": 0.45,
                     "branch_end": 0.80, "branch_angle": 58, "crown_shape": "Spherical",
                     "branch_density": 0.8, "branch_start_radius": 0.64,
                     "branch_split_prob": 0.6, "branch_split_angle": 45.0},
    # crooked sinuous limbs (plane "elbows") via gravity + randomness, ascending
    "lp_crooked":   {"up_attraction": 0.38, "branch_length_ratio": 0.58,
                     "branch_angle_variation": 0.6, "branch_flatness": 0.45,
                     "branch_end": 0.80, "branch_angle": 55, "crown_shape": "Spherical",
                     "branch_density": 0.85, "branch_start_radius": 0.62,
                     "branch_gravity": 9.0, "trunk_randomness": 0.6,
                     "branch_split_prob": 0.6, "branch_split_angle": 48.0},
    # --- refined from lp_thick_few: straighter stout bole + clearer thick-limb
    #     hierarchy (fewer, heavier primaries; finer twig haze) ---
    "lp_candelabra": {"up_attraction": 0.35, "branch_length_ratio": 0.60,
                      "branch_angle_variation": 0.55, "branch_flatness": 0.48,
                      "branch_end": 0.78, "branch_angle": 58, "crown_shape": "Spherical",
                      "branch_density": 0.70, "branch_start_radius": 0.72,
                      "branch_split_prob": 0.58, "branch_split_angle": 46.0,
                      "trunk_randomness": 0.32, "branch_start": 0.26, "trunk_frac": 0.28,
                      "sub_density": 0.9},
    # bifurcated Y-fork (ref 09-02): low fork, very few heavy primaries, strong split
    "lp_bifurcated": {"up_attraction": 0.33, "branch_length_ratio": 0.62,
                      "branch_angle_variation": 0.5, "branch_flatness": 0.50,
                      "branch_end": 0.78, "branch_angle": 56, "crown_shape": "Spherical",
                      "branch_density": 0.55, "branch_start_radius": 0.78,
                      "branch_split_prob": 0.7, "branch_split_angle": 52.0,
                      "trunk_randomness": 0.30, "branch_start": 0.20, "trunk_frac": 0.22,
                      "sub_density": 0.95},
}


def render(obj, out):
    sc = bpy.context.scene
    sc.render.resolution_x = SIZE
    sc.render.resolution_y = SIZE
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.eevee.taa_render_samples = 8   # bark-only habit silhouette — 64 is wasteful (~4min/render CPU)
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
