"""Generate Glen Span Arch model for Central Park Walk.

Glen Span Arch — tall stone arch in the North Woods, carrying the West
Drive over a pedestrian path and the Loch stream. Built 1860s by Calvert
Vaux. Original upper portion was wood, replaced with stone in 1885.

Key dimensions:
  LENGTH      = 15.24m  (50 ft)
  WIDTH       = 4.88m   (16 ft)
  HEIGHT      = 5.64m   (18 ft 6 in — tall, near semicircular)
  SIDEWALLS   = 19.81m  (65 ft)

Materials:
  Exterior: Large-sized light-gray gneiss, roughly dressed, laid in ashlar
  Interior: Grottoes (recessed alcoves in walls)
  Profile: Tall arch — width:height ratio of 16:18.5, slightly taller
           than semicircular

Exports to models/furniture/cp_glen_span_arch.glb
"""

import bpy
import math
import os
import random

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0: bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0: bpy.data.materials.remove(block)

def make_mat(name, color, roughness=0.80, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

# Light gray gneiss, roughly dressed
gneiss = make_mat("Gneiss", (0.50, 0.48, 0.45), roughness=0.85)
gneiss_dark = make_mat("GneissDark", (0.40, 0.38, 0.35), roughness=0.88)
# Grotto interior — darker, damp stone
grotto = make_mat("Grotto", (0.32, 0.30, 0.28), roughness=0.90)
# Road surface
road_mat = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
# Path
path_mat = make_mat("Path", (0.40, 0.37, 0.32), roughness=0.88)

WIDTH = 4.88; HALF_W = WIDTH / 2
HEIGHT = 5.64
# Passage length is the 50ft "length" dimension
PASS_L = 15.24; HALF_L = PASS_L / 2
WALL_T = 1.2      # thick stone walls
ARCH_T = 0.65     # barrel thickness
ROAD_T = 0.35     # road surface above
PARAPET_H = 1.0   # stone parapet
PARAPET_T = 0.40
N_ARC = 24
all_parts = []

random.seed(73)


def tall_arch(half_w, height, n_pts):
    """Tall arch profile — slightly taller than semicircular.
    Uses an ellipse with height > width."""
    pts = []
    for i in range(n_pts + 1):
        t = i / n_pts
        angle = math.pi * (1.0 - t)
        x = half_w * math.cos(angle)
        z = height * math.sin(angle)
        pts.append((x, z))
    return pts


def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name
    o.scale = (hx*2, hy*2, hz*2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); all_parts.append(o); return o


# Barrel vault
arc_pts = tall_arch(HALF_W, HEIGHT, N_ARC)

mesh = bpy.data.meshes.new("vault"); verts = []; faces = []
for px, pz in arc_pts:
    verts.append((px, -HALF_L, pz)); verts.append((px, HALF_L, pz))
    d = math.sqrt(px*px + pz*pz)
    if d > 0.1: ox, oz = px*(1+ARCH_T/d), pz*(1+ARCH_T/d)
    else: ox, oz = px, pz+ARCH_T
    verts.append((ox, -HALF_L, oz)); verts.append((ox, HALF_L, oz))
for i in range(len(arc_pts)-1):
    b = i*4; nb = (i+1)*4
    faces.append((b, b+1, nb+1, nb))
    faces.append((b+2, nb+2, nb+3, b+3))
    faces.append((b, nb, nb+2, b+2))
    faces.append((b+1, b+3, nb+3, nb+1))
mesh.from_pydata(verts, [], faces); mesh.update()
obj = bpy.data.objects.new("vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(gneiss_dark); all_parts.append(obj)

# Face walls
for end in (-1, 1):
    ey = end * HALF_L
    vf = []; ff = []; hw = WIDTH/2 + WALL_T; fh = HEIGHT + ARCH_T + ROAD_T
    vf += [(-hw, ey, -0.5), (-HALF_W, ey, -0.5), (-HALF_W, ey, 0), (-hw, ey, fh)]
    ff.append((0,1,2,3) if end>0 else (0,3,2,1))
    b = len(vf)
    vf += [(HALF_W, ey, -0.5), (hw, ey, -0.5), (hw, ey, fh), (HALF_W, ey, 0)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    b = len(vf)
    vf += [(-hw, ey, HEIGHT+ARCH_T), (hw, ey, HEIGHT+ARCH_T), (hw, ey, fh), (-hw, ey, fh)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    m = bpy.data.meshes.new(f"face_{end}"); m.from_pydata(vf, [], ff); m.update()
    o = bpy.data.objects.new(f"face_{end}", m); bpy.context.collection.objects.link(o)
    o.data.materials.append(gneiss); all_parts.append(o)

    # Arch ring
    mesh = bpy.data.meshes.new(f"ring_{end}"); verts = []; faces = []
    for i in range(N_ARC + 1):
        px, pz = arc_pts[i]
        d = math.sqrt(px*px + pz*pz)
        if d > 0.1: ox, oz = px*(1+0.15/d), pz*(1+0.15/d)
        else: ox, oz = px, pz+0.15
        verts.append((px, ey+end*0.12, pz))
        verts.append((ox, ey+end*0.12, oz))
        verts.append((px, ey, pz))
        verts.append((ox, ey, oz))
    for i in range(N_ARC):
        b = i*4; nb = (i+1)*4
        faces.append((b, b+1, nb+1, nb))
        faces.append((b+1, b+3, nb+3, nb+1))
    mesh.from_pydata(verts, [], faces); mesh.update()
    obj = bpy.data.objects.new(f"ring_{end}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(gneiss); all_parts.append(obj)

# Grotto recesses — shallow alcoves in the side walls
# Glen Span has interior grottoes (small recessed niches)
for side in (-1, 1):
    for gi in range(3):
        gy = -HALF_L * 0.6 + gi * (PASS_L * 0.3)
        gx = side * (HALF_W - 0.1)  # slightly inset from wall
        # Small recessed alcove
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(gx + side * 0.3, gy, HEIGHT * 0.4))
        g = bpy.context.active_object
        g.name = f"grotto_{side}_{gi}"
        g.scale = (0.6, 0.8, 1.0)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        g.data.materials.append(grotto)
        all_parts.append(g)

# Side walls
for side in (-1, 1):
    wx = side * (HALF_W + WALL_T/2)
    wall_h = HEIGHT + ARCH_T + ROAD_T + 0.5
    box(f"wall_{side}", wx, 0, wall_h/2 - 0.5, WALL_T/2, HALF_L, wall_h/2, gneiss)

# Road deck
road_top = HEIGHT + ARCH_T
road_w = WIDTH + 2*WALL_T + 0.5
box("road", 0, 0, road_top+ROAD_T/2, road_w/2, HALF_L+2, ROAD_T/2, road_mat)

# Parapets
for side in (-1, 1):
    box(f"parapet_{side}", side*(road_w/2 - PARAPET_T/2), 0,
        road_top+ROAD_T+PARAPET_H/2, PARAPET_T/2, HALF_L+2, PARAPET_H/2, gneiss)

# Floor
box("floor", 0, 0, -0.25, HALF_W, HALF_L, 0.25, path_mat)

# Wing walls (extending sidewalls for approach)
for end in (-1, 1):
    for side in (-1, 1):
        box(f"wing_{end}_{side}", side*(HALF_W+WALL_T+0.5), end*(HALF_L+1.5),
            road_top*0.5, 0.4, 1.5, road_top*0.5, gneiss)

# Finalize
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
arch = bpy.context.active_object; arch.name = "GlenSpanArch"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_glen_span_arch.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Glen Span Arch to {out_path}")
print(f"  Verts: {len(arch.data.vertices)}, Faces: {len(arch.data.polygons)}")
