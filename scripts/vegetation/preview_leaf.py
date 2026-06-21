"""Standalone single-leaf preview render (Blender headless).

Builds the london_plane leaf proto — the SAME parametric palmate outline + V-fold
+ opaque surface texture that build_distribute_leaf() in generate_trees_mtree.py
feeds into lod0 — and renders it from a 3/4 angle (form-revealing sun light) and
flat top-down (silhouette/veins). Fast visual check of SHAPE + 3D FORM + TEXTURE
before paying for a full tree regen. NOT the runtime look (the in-game leaf gets
SSS/translucency from tree_leaf.gdshader); this previews geometry + albedo only.

The outline math is kept in sync with _palmate_leaf_outline by copy — this is a
preview approximation; the authoritative build path is build_distribute_leaf.

Run: blender4 --background --python scripts/vegetation/preview_leaf.py -- [fold]
"""
import bpy
import math
import os
import sys

PROJ = "/home/chris/central-park-walk"
TEX = os.environ.get("LEAF_TEX",
    os.path.join(PROJ, "models/trees/leaf_textures/london_plane_leaf.png"))
OUT_DIR = "/tmp/leaf_preview"
os.makedirs(OUT_DIR, exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FOLD = float(argv[0]) if len(argv) > 0 else 0.15
TOOTH_AMP = float(argv[1]) if len(argv) > 1 else 0.028
TEETH_PER_EDGE = int(argv[2]) if len(argv) > 2 else 2
TAG = argv[3] if len(argv) > 3 else f"fold{FOLD}_t{TOOTH_AMP}_n{TEETH_PER_EDGE}"


sys.path.insert(0, os.path.join(PROJ, "scripts", "vegetation"))
from leaf_outline import palmate_outline  # shared single-source outline


def build_leaf(fold, tooth_amp=0.13, teeth_per_edge=2):
    bxy, buv, _tip, _base = palmate_outline(
        {"tooth_amp": tooth_amp, "teeth_per_edge": teeth_per_edge})
    base_len = 2.93
    ys = [p[1] for p in bxy]
    span = (max(ys) - min(ys)) or 1.0
    sc = base_len / span
    # Preview orients STEM-DOWN (petiole at bottom, apex up) to match how the
    # reference photos are framed — easier to compare. (The real build_distribute_leaf
    # keeps tip toward -Y for Mtree's attachment convention; orientation is cosmetic here.)
    coords = [(x * sc, y * sc, fold * abs(x * sc)) for (x, y) in bxy]
    area2 = sum(coords[i][0] * coords[(i + 1) % len(coords)][1]
                - coords[(i + 1) % len(coords)][0] * coords[i][1]
                for i in range(len(coords)))
    if area2 < 0:
        coords = list(reversed(coords))
        buv = list(reversed(buv))
    me = bpy.data.meshes.new("leafproto")
    me.from_pydata(coords, [], [list(range(len(coords)))])
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = buv[me.loops[li].vertex_index]
    ob = bpy.data.objects.new("leafproto", me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    tri = ob.modifiers.new("tri", type='TRIANGULATE')
    tri.ngon_method = 'BEAUTY'
    bpy.ops.object.modifier_apply(modifier="tri")
    bpy.ops.object.shade_smooth()
    ob.location.y = -base_len / 2.0  # centre the leaf on the origin so it frames
    mat = bpy.data.materials.new("leaf")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(TEX)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    me.materials.append(mat)
    return ob


def setup_and_render(name, cam_loc, cam_rot, sun_rot):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in \
        [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scn.render.resolution_x = 900
    scn.render.resolution_y = 900
    scn.render.film_transparent = False
    world = bpy.data.worlds.new("w") if not bpy.data.worlds else bpy.data.worlds[0]
    scn.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = cam_loc
    cam.rotation_euler = cam_rot
    scn.camera = cam
    sun_data = bpy.data.lights.new("sun", 'SUN')
    sun_data.energy = 4.0
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = sun_rot
    scn.render.filepath = os.path.join(OUT_DIR, name)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.objects.remove(sun, do_unlink=True)


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
build_leaf(FOLD, TOOTH_AMP, TEETH_PER_EDGE)
# 3/4 view — raking sun reveals the V-fold's graded shading across the blade.
setup_and_render(f"leaf_3q_{TAG}.png", (3.2, -3.2, 2.6),
                 (math.radians(58), 0, math.radians(45)),
                 (math.radians(38), math.radians(12), math.radians(20)))
# top-down — silhouette + palmate veins + teeth + texture.
setup_and_render(f"leaf_top_{TAG}.png", (0, 0, 5.2), (0, 0, 0),
                 (math.radians(25), math.radians(10), 0))
print(f"wrote previews to {OUT_DIR} (fold={FOLD} tooth_amp={TOOTH_AMP} teeth={TEETH_PER_EDGE})")
sys.stdout.flush()
os._exit(0)
