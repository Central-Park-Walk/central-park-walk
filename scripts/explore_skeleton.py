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

    # ===== 2026-06-22 s4: m & l redesign (skeletons-first) =====
    # Render each at its tier height: --height 30 for l_*, --height 22 for m_*.
    # l = MATURE DECURRENT CANDELABRA (ref A149-03 hero + nyc11 + wireframe 09-02):
    #   broad rounded dome (aspect ~0.85-1.0), stout trunk forks low into a FEW heavy
    #   scaffolds, fine twiggy shell at periphery, weak leader.
    "lp_l_base": {},   # current species base (= l tier, no overrides) for A/B
    # KEY FIX: species never set crown_base_size -> Mtree default 0.0 = narrow-cone
    # clamp (reference_how_to_make_trees §8). Raise to open the broad mature dome.
    "lp_l_dome": {"crown_base_size": 0.65},
    # + RAMIFICATION CAP (stem/twig redundancy): MEASURED 2026-06-22 — current l
    # ramifies to depth 11, vert mass peaks at depth 4-5, ~10-14k clusters & ~90-129k
    # verts/variant (55MB GLB). The leaf card IS the terminal 4-leaf twiglet, so the
    # skeleton must stop ~tertiary; depths 5-11 are bare filaments redundant with the
    # card's painted twig. Cap = lower the split probabilities (per-segment fork chance)
    # that drive the deep haze. Sweep to find where the candelabra still reads but the
    # deep filaments are gone. face count printed = geometry-weight proxy.
    "lp_l_dome_cap_soft": {"crown_base_size": 0.65,
                           "sub_split_prob": 0.15, "branch_split_prob": 0.50},
    "lp_l_dome_cap_med":  {"crown_base_size": 0.65,
                           "sub_split_prob": 0.10, "branch_split_prob": 0.45},
    "lp_l_dome_cap_hard": {"crown_base_size": 0.65,
                           "sub_split_prob": 0.06, "branch_split_prob": 0.40},
    # REFINED l: dome + ramification cap + STRAIGHTER STOUT BOLE (trunk_randomness
    # 0.32->0.18 — the base skeletons leaned/S-curved with a one-sided crown; the
    # leafed thumbnail hid it). _soft keeps a denser shell (more twig tips -> more
    # cards), _med is lighter. Test both at 2 seeds for lean consistency.
    "lp_l_v2_soft": {"crown_base_size": 0.65, "trunk_randomness": 0.18,
                     "sub_split_prob": 0.15, "branch_split_prob": 0.50},
    "lp_l_v2_med":  {"crown_base_size": 0.65, "trunk_randomness": 0.18,
                     "sub_split_prob": 0.10, "branch_split_prob": 0.45},
    # v2_med read as a tall oval (~0.55 aspect); the mature open-grown plane (A149-03
    # hero) is a BROAD DOME (~0.85-1.0). Widen: bigger crown_base_size, longer limbs,
    # lower fork, more horizontal lower limbs (angle_var rounds the dome top).
    "lp_l_wide":    {"crown_base_size": 0.82, "trunk_randomness": 0.18,
                     "sub_split_prob": 0.10, "branch_split_prob": 0.45,
                     "branch_length_ratio": 0.56, "branch_start": 0.22,
                     "branch_angle": 60, "branch_angle_variation": 0.55},
    # CANDIDATE l recipe: broad dome (crown_base_size 0.75, length 0.55, low fork) with
    # the top ROUNDED by raising branch_end 0.78->0.88 (branches reach near the apex and
    # arch over, subsuming the bare leader spike) + cap + straight bole.
    "lp_l_final":   {"crown_base_size": 0.75, "trunk_randomness": 0.18,
                     "sub_split_prob": 0.10, "branch_split_prob": 0.45,
                     "branch_length_ratio": 0.55, "branch_start": 0.24,
                     "branch_end": 0.88, "branch_angle": 60,
                     "branch_angle_variation": 0.55},

    # m = YOUNG-ADULT TRANSITIONAL (ref size-chart middle + nyc11 oval): leader giving
    #   way, crown opening to an oval/vase, higher cleaner bole, broader than s but
    #   NARROWER/more upright than the mature l (aspect ~0.6-0.7). Fix the stale m:
    #   too narrow (crown_base_size 0.0 clamp), sparse, S-curved leaning bole.
    "lp_m_cur": {"up_attraction": 0.42, "branch_start": 0.28,
                 "branch_length_ratio": 0.48, "branch_density": 0.78,
                 "branch_split_prob": 0.55, "sub_density": 0.68},
    "lp_m_new": {"up_attraction": 0.42, "branch_start": 0.30,
                 "branch_length_ratio": 0.48, "branch_density": 0.78,
                 "branch_split_prob": 0.55, "sub_density": 0.68,
                 "crown_base_size": 0.50,      # open an oval crown (was 0.0 clamp)
                 "trunk_randomness": 0.24,     # straighter bole (kill the S-curve; species 0.32 too curvy at 22m)
                 "sub_gravity": 6.0},          # less one-sided lean (species 10.0 caused it on s)
    "lp_m_new_cap": {"up_attraction": 0.42, "branch_start": 0.30,
                     "branch_length_ratio": 0.48, "branch_density": 0.78,
                     "branch_split_prob": 0.55, "sub_density": 0.68,
                     "crown_base_size": 0.50, "trunk_randomness": 0.24,
                     "sub_gravity": 6.0, "sub_split_prob": 0.18},
    # CANDIDATE m recipe (young-adult): narrower/more upright than l (oval ~0.6-0.7),
    # higher cleaner bole, leader still giving way (up_attraction 0.42 > l's 0.35).
    # Same cap + straight-bole + rounded-top fixes as l, scaled younger.
    "lp_m_final":   {"crown_base_size": 0.55, "trunk_randomness": 0.20,
                     "sub_split_prob": 0.10, "branch_split_prob": 0.45,
                     "branch_length_ratio": 0.48, "branch_start": 0.30,
                     "branch_end": 0.85, "branch_angle": 56,
                     "branch_angle_variation": 0.55, "up_attraction": 0.42,
                     "branch_density": 0.78, "sub_density": 0.70,
                     "sub_gravity": 6.0},
    # lp_m_final was too SPARSE (~8k faces) — l's hard cap over-thins m's shorter limbs
    # (ramification is exponential in limb length). Lighter cap + a touch more density
    # for a full young-adult crown. Scale-appropriate cap: m softer than l, s softer yet.
    "lp_m_final2":  {"crown_base_size": 0.55, "trunk_randomness": 0.20,
                     "sub_split_prob": 0.20, "branch_split_prob": 0.52,
                     "branch_length_ratio": 0.48, "branch_start": 0.30,
                     "branch_end": 0.85, "branch_angle": 56,
                     "branch_angle_variation": 0.55, "up_attraction": 0.42,
                     "branch_density": 0.85, "sub_density": 0.80,
                     "sub_gravity": 6.0},
    # m still sparse — add structural BODY via more primaries (branch_density) + twigs
    # + width, keeping a moderate cap. branch_density<=0.95 stays under the ~1.05 crash band.
    "lp_m_full":    {"crown_base_size": 0.62, "trunk_randomness": 0.20,
                     "sub_split_prob": 0.22, "branch_split_prob": 0.52,
                     "branch_length_ratio": 0.50, "branch_start": 0.28,
                     "branch_end": 0.86, "branch_angle": 56,
                     "branch_angle_variation": 0.55, "up_attraction": 0.42,
                     "branch_density": 0.95, "sub_density": 0.92,
                     "sub_gravity": 6.0},
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
    sys.stdout.flush()


main()
# Headless EEVEE_NEXT does not release its GL context on this box, so Blender hangs
# on shutdown AFTER the work is done (process sits at 0% CPU forever, blocking any
# batch loop). Force-exit immediately once the png is written. 2026-06-22.
os._exit(0)
