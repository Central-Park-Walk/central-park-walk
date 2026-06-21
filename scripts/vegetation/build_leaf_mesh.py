"""Build the London plane leaf as a real 3D MESH from the marching-squares silhouette
of the real leaf, textured opaquely with the real photo so veins/teeth/color are real.
This is STRUCTURAL leaf geometry (the blade shape IS the mesh), not a billboard card.

Reads scripts/vegetation/london_plane_outline_v2.json (boundary_img in photo pixels +
image_size) so the UVs map the photo (textures/leaves/london_plane_real_albedo.png)
exactly onto the leaf-shaped mesh. Adds a gentle V-fold + tip droop along the leaf's
principal axis, smooth normals, and vein relief via a bump from the photo.

Run: ~/.local/bin/blender4 --background --python scripts/vegetation/build_leaf_mesh.py
"""
import bpy, bmesh, json, os, sys, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
JSON = os.path.join(HERE, "london_plane_outline_v2.json")
TEX = os.path.join(PROJ, "textures/leaves/london_plane_real_albedo.png")
OUT = "/tmp/leaf_mesh"
os.makedirs(OUT, exist_ok=True)

d = json.load(open(JSON))
bnd = d["boundary_img"]                       # (col,row) pixels
Wimg, Himg = d["image_size"]

# image px -> world XY (y up), centred, scaled so the leaf ~3 units (Mtree-leaf scale)
cols = [p[0] for p in bnd]; rows = [p[1] for p in bnd]
cx = (min(cols) + max(cols)) / 2.0
cy = (min(rows) + max(rows)) / 2.0
span = max(max(cols) - min(cols), max(rows) - min(rows)) or 1.0
S = 3.0 / span


def to_world(col, row):
    return Vector(((col - cx) * S, -(row - cy) * S, 0.0))


def to_uv_from_world(x, y):
    col = x / S + cx
    row = -y / S + cy
    return (col / Wimg, 1.0 - row / Himg)


# --- build boundary ngon, triangulate, subdivide for fold resolution ---
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
me = bpy.data.meshes.new("london_plane_leaf")
bm = bmesh.new()
vs = [bm.verts.new(to_world(c, r)) for c, r in bnd]
try:
    bm.faces.new(vs)
except ValueError:
    # if self-touching, fall back to a fan; rare
    for i in range(1, len(vs) - 1):
        bm.faces.new([vs[0], vs[i], vs[i + 1]])
bmesh.ops.triangulate(bm, faces=bm.faces)
for _ in range(3):
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)

# principal axis (for the fold) from boundary verts in XY
import numpy as np
P = np.array([[v.co.x, v.co.y] for v in bm.verts])
c2 = P.mean(0); Q = P - c2
_, _, vt = np.linalg.svd(Q, full_matrices=False)
axis = vt[0]; perp = vt[1]
along = Q @ axis
perp_d = Q @ perp
along_n = (along - along.min()) / ((along.max() - along.min()) or 1.0)

# V-fold (edges droop down from the midrib) + slight tip droop, then smooth
for i, v in enumerate(bm.verts):
    z = -0.07 * abs(perp_d[i])                # taco/V along the length
    z += -0.12 * (along_n[i] ** 2)            # gentle droop toward one end (apex)
    v.co.z = z

uv_layer = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    f.smooth = True
    for loop in f.loops:
        loop[uv_layer].uv = to_uv_from_world(loop.vert.co.x, loop.vert.co.y)

bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new("london_plane_leaf", me)
bpy.context.collection.objects.link(ob)
print(f"  mesh: {len(me.vertices)}v {len(me.polygons)}f")

# --- material: real photo, opaque, vein relief via bump ---
mat = bpy.data.materials.new("plane_leaf_real"); mat.use_nodes = True
nt = mat.node_tree; nodes = nt.nodes; links = nt.links
bsdf = nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.5
img = bpy.data.images.load(TEX)
tex = nodes.new("ShaderNodeTexImage"); tex.image = img
links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
# vein relief: luminance -> bump
bw = nodes.new("ShaderNodeRGBToBW"); links.new(tex.outputs["Color"], bw.inputs["Color"])
bump = nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
bump.inputs["Distance"].default_value = 0.02
links.new(bw.outputs["Val"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
me.materials.append(mat)


def render(tag, loc, rot, ortho=2.0):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = scn.render.resolution_y = 1024
    w = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("w")
    scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.87, 0.9, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
    cam = bpy.data.objects.new("c", cam_d); bpy.context.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = rot
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 2.6
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(35), math.radians(18), 0)
    scn.render.filepath = os.path.join(OUT, tag)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.objects.remove(s)


render("leaf_face.png", (0, 0, 6), (0, 0, 0), ortho=3.4)
render("leaf_3q.png", (2.4, -2.4, 2.2), (math.radians(52), 0, math.radians(45)), ortho=3.6)
print("wrote", OUT)
sys.stdout.flush(); os._exit(0)
