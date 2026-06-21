"""Build the London plane leaf as a real 3D MESH from the marching-squares silhouette
of the real leaf, textured opaquely with the real photo (veins/teeth/color are real).
STRUCTURAL leaf geometry (the blade shape IS the mesh), not a billboard card.

Geometry is built in the CANONICAL frame straight from the extractor's boundary_xy
(petiole base at origin, apex +Y, face +Z -- the attach contract). UVs map the photo
(textures/leaves/london_plane_real_albedo.png) via an affine fit between boundary_xy
and the photo pixel coords (exact: extract used a similarity), so the texture stays
locked to the geometry even on subdivided interior verts. Gentle V-fold + tip droop,
vein relief via bump, smooth normals. Decimated to budget, exported to models/leaves.

Run: ~/.local/bin/blender4 --background --python scripts/vegetation/build_leaf_mesh.py
"""
import bpy, bmesh, json, os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
JSON = os.path.join(HERE, "london_plane_outline_v2.json")
TEX = os.path.join(PROJ, "textures/leaves/london_plane_real_albedo.png")
OUT = "/tmp/leaf_mesh"
os.makedirs(OUT, exist_ok=True)
LEAF_H = 3.0

d = json.load(open(JSON))
XY = np.array(d["boundary_xy"], float)            # canonical: petiole(0,0)->apex(~,1)
Wimg, Himg = d["image_size"]
UV = np.array([[c / Wimg, 1.0 - r / Himg] for c, r in d["boundary_img"]], float)
# affine fit  UV ~ [x, y, 1] @ A   (A: 3x2); exact since extract was a similarity
A, *_ = np.linalg.lstsq(np.column_stack([XY, np.ones(len(XY))]), UV, rcond=None)


def uv_of(xw, yw):
    return tuple((np.array([xw / LEAF_H, yw / LEAF_H, 1.0]) @ A).tolist())


# --- build canonical boundary, triangulate, subdivide for fold resolution ---
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
me = bpy.data.meshes.new("london_plane_leaf")
bm = bmesh.new()
vs = [bm.verts.new((x * LEAF_H, y * LEAF_H, 0.0)) for x, y in XY]
try:
    bm.faces.new(vs)
except ValueError:
    for i in range(1, len(vs) - 1):
        bm.faces.new([vs[0], vs[i], vs[i + 1]])
bmesh.ops.triangulate(bm, faces=bm.faces)
for _ in range(2):
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)

# V-fold about the midrib (Y axis) + gentle droop toward the apex; smooth.
P = np.array([[v.co.x, v.co.y] for v in bm.verts])
along = P[:, 1]
along_n = (along - along.min()) / ((along.max() - along.min()) or 1.0)
for i, v in enumerate(bm.verts):
    v.co.z = -0.06 * abs(v.co.x) - 0.18 * (along_n[i] ** 2)

uv_layer = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    f.smooth = True
    for loop in f.loops:
        loop[uv_layer].uv = uv_of(loop.vert.co.x, loop.vert.co.y)

bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new("london_plane_leaf", me)
bpy.context.collection.objects.link(ob)
print(f"  mesh: {len(me.vertices)}v {len(me.polygons)}f")

# --- material: real photo, opaque, vein relief via bump ---
mat = bpy.data.materials.new("plane_leaf_real"); mat.use_nodes = True
nt = mat.node_tree; nodes = nt.nodes; links = nt.links
bsdf = nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 0.5
img = bpy.data.images.load(TEX)
tex = nodes.new("ShaderNodeTexImage"); tex.image = img
links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
bw = nodes.new("ShaderNodeRGBToBW"); links.new(tex.outputs["Color"], bw.inputs["Color"])
bump = nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
bump.inputs["Distance"].default_value = 0.02
links.new(bw.outputs["Val"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
me.materials.append(mat)

# --- decimate to budget: COLLAPSE keeps the fold; boundary teeth mostly preserved ---
dec = ob.modifiers.new("dec", "DECIMATE")
dec.decimate_type = 'COLLAPSE'; dec.ratio = 0.30
bpy.context.view_layer.objects.active = ob
bpy.ops.object.modifier_apply(modifier="dec")
print(f"  after decimate: {len(me.vertices)}v {len(me.polygons)}f")

glb = os.path.join(PROJ, "models", "leaves", "london_plane_leaf.glb")
os.makedirs(os.path.dirname(glb), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format='GLB')
print("exported", glb)

# --- render (camera aimed at the leaf bbox centre) ---
vco = np.array([v.co[:] for v in me.vertices])
bc = (vco.min(0) + vco.max(0)) / 2.0
ext = float(max(vco[:, 0].ptp(), vco[:, 1].ptp())) * 1.25


def render(tag, offset, rot):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
    scn.render.resolution_x = scn.render.resolution_y = 1024
    w = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("w")
    scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.87, 0.9, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ext
    cam = bpy.data.objects.new("c", cam_d); bpy.context.collection.objects.link(cam)
    cam.location = (bc[0] + offset[0], bc[1] + offset[1], bc[2] + offset[2])
    cam.rotation_euler = rot
    scn.camera = cam
    s_d = bpy.data.lights.new("s", 'SUN'); s_d.energy = 2.6
    s = bpy.data.objects.new("s", s_d); bpy.context.collection.objects.link(s)
    s.rotation_euler = (math.radians(35), math.radians(18), 0)
    scn.render.filepath = os.path.join(OUT, tag)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.objects.remove(s)


render("leaf_face.png", (0, 0, 6), (0, 0, 0))
render("leaf_3q.png", (ext * 0.5, -ext * 0.5, ext * 0.5), (math.radians(52), 0, math.radians(45)))
print("wrote", OUT)
sys.stdout.flush(); os._exit(0)
