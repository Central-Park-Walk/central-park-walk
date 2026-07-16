"""
Render a SKINNED grower skeleton (bark tube, LEAFLESS) — the iter-43 glue that finally puts a
tree grown by plane_grower.py on screen.

  grower --save skel.npz  ->  leafback_skinner.load_graph_npz + build_tube_mesh  ->  render.

Reuses render_skeleton.py's calibrated white-bg side-ortho camera + sun (imported, not copied).
The grower is Y-UP (Godot convention); Blender is Z-UP and fit_cam frames height on Z, so the
skinned object is rotated +90 deg about X (Y->Z) before framing — fit_cam reads matrix_world, so
the rotation is honored with no bake.

LEAFLESS / bark-only rail: the grower graph is ~76% foliage nodes (leaf-cluster positions, NOT
wood). Skinning those as bark tubes would smuggle foliage in as fake twiglets, against the F6
"leafless bark-only" scope. So by default we prune to the WOODY scaffold (~foliage) and reconnect
any dropped-parent to its nearest kept ancestor. `--all` skins every node (debug: see the fuzz).

Usage:
  blender --background --python scripts/render_skinned.py -- <skel.npz> [out.png] [--ring N] [--all]
Default output: <repo>/tmp/skinned_<npzstem>.png
"""
import bpy, sys, os, math, time
import numpy as np
_t0 = time.time()
def log(msg):
    print(f"[render_skinned +{time.time()-_t0:5.1f}s] {msg}", flush=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import leafback_skinner as sk
from render_skeleton import setup, fit_cam   # calibrated camera + sun (main() is guarded)

PROJ = os.path.dirname(SCRIPT_DIR)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ring = sk.DEFAULT_RING
if "--ring" in argv:
    _i = argv.index("--ring"); ring = int(argv[_i + 1]); argv = argv[:_i] + argv[_i + 2:]
skin_all = "--all" in argv
pos_args = [a for a in argv if not a.startswith("--")]
if not pos_args:
    raise SystemExit("need a skeleton .npz path")
npz = pos_args[0]
out = pos_args[1] if len(pos_args) > 1 else os.path.join(
    PROJ, "tmp", f"skinned_{os.path.splitext(os.path.basename(npz))[0]}.png")
os.makedirs(os.path.dirname(out), exist_ok=True)

# clear default scene, set up the calibrated view
for o in list(bpy.context.scene.objects):
    bpy.data.objects.remove(o, do_unlink=True)
cam = setup()

# ★ iter-43: EEVEE-Next under xvfb (llvmpipe, no GPU) stalls; Workbench solid-shading renders the
# bare habit fast and is the RIGHT tool for a form/silhouette read (cavity gives branch depth).
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.render_aa = '8'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.52, 0.47, 0.42)
sh.show_cavity = True; sh.cavity_type = 'BOTH'
sh.show_shadows = True
sh.background_type = 'VIEWPORT'; sh.background_color = (1.0, 1.0, 1.0)
log("scene + workbench ready")

def prune_to_mask(g, keep):
    """Keep only nodes where keep[i] is True; reconnect each kept node whose parent was dropped to
    its nearest kept ancestor. Returns a fresh skinner g (nodes/strand/children rebuilt)."""
    nodes, strand = g["nodes"], g["strand"]
    N = len(nodes)
    old2new = {}
    keep_idx = [i for i in range(N) if keep[i]]
    for ni, oi in enumerate(keep_idx):
        old2new[oi] = ni
    new_nodes, new_strand = [], []
    for oi in keep_idx:
        p = nodes[oi]["parent"]
        while p != -1 and not keep[p]:      # walk up to the nearest surviving ancestor
            p = nodes[p]["parent"]
        nd = dict(nodes[oi]); nd["parent"] = old2new[p] if p != -1 else -1
        new_nodes.append(nd); new_strand.append(strand[oi])
    return dict(nodes=new_nodes, strand=list(new_strand), children=sk._children(new_nodes))


g = sk.load_graph_npz(npz)
if not skin_all:
    foliage = np.load(npz)["foliage"].astype(bool)   # ride-along mask from the grower export
    g = prune_to_mask(g, ~foliage)                    # WOODY scaffold only (F6 leafless bark-only)
log(f"graph loaded: {len(g['nodes']):,} nodes (skin_all={skin_all})")
obj = sk.build_tube_mesh(g, ring=ring)
log(f"skinned: {len(obj.data.polygons):,} faces")
obj.rotation_euler = (math.radians(90), 0, 0)     # grower Y-up -> Blender Z-up
bpy.context.view_layer.update()                   # so matrix_world reflects the rotation

fit_cam(cam, obj)
sc.render.filepath = out
log("rendering...")
bpy.ops.render.render(write_still=True)
log(f"WROTE {out}  ({len(g['nodes']):,} nodes -> {len(obj.data.polygons):,} bark faces, ring_max={ring})")
