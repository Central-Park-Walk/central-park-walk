"""Generate Dalehead Arch model for Central Park Walk.

Dalehead Arch — long, low elliptical arch carrying the East Drive over a
pedestrian path near the south end of the Great Lawn. Built 1860-62 by
Calvert Vaux.

Key dimensions:
  SPAN        = 24.4m   (80 ft)
  HEIGHT      = 3.35m   (11 ft)
  DEPTH       = 7.3m    (24 ft passage depth)

Materials: Stone and brick masonry. Interior brick barrel vault.
Profile: Low elliptical (very wide, shallow — 7:1 span-to-height)

Exports to models/furniture/cp_dalehead_arch.glb
"""

import bpy
import math
import os

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

stone = make_mat("Stone", (0.50, 0.47, 0.43), roughness=0.82)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
parapet = make_mat("Parapet", (0.52, 0.49, 0.45), roughness=0.78)

SPAN = 24.4; HALF_S = SPAN / 2
HEIGHT = 3.35
PASS_L = 7.3; HALF_L = PASS_L / 2
WALL_T = 1.2; ARCH_T = 0.60; ROAD_T = 0.30
PARAPET_H = 1.0; PARAPET_T = 0.40
N_ARC = 28
all_parts = []

def elliptical_arc(hw, h, n):
    return [(hw * math.cos(math.pi * (1 - i/n)), h * math.sin(math.pi * (1 - i/n))) for i in range(n+1)]

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name
    o.scale = (hx*2, hy*2, hz*2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); all_parts.append(o); return o

# Barrel vault
arc_pts = elliptical_arc(HALF_S, HEIGHT, N_ARC)
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
obj.data.materials.append(brick); all_parts.append(obj)

# Face walls
for end in (-1, 1):
    ey = end * HALF_L
    vf = []; ff = []; hw = SPAN/2 + WALL_T; fh = HEIGHT + ARCH_T + ROAD_T
    vf += [(-hw, ey, -0.3), (-HALF_S, ey, -0.3), (-HALF_S, ey, 0), (-hw, ey, fh)]
    ff.append((0,1,2,3) if end>0 else (0,3,2,1))
    b = len(vf)
    vf += [(HALF_S, ey, -0.3), (hw, ey, -0.3), (hw, ey, fh), (HALF_S, ey, 0)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    b = len(vf)
    vf += [(-hw, ey, HEIGHT+ARCH_T), (hw, ey, HEIGHT+ARCH_T), (hw, ey, fh), (-hw, ey, fh)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    m = bpy.data.meshes.new(f"face_{end}"); m.from_pydata(vf, [], ff); m.update()
    o = bpy.data.objects.new(f"face_{end}", m); bpy.context.collection.objects.link(o)
    o.data.materials.append(stone); all_parts.append(o)

# Road, parapets, side walls, floor
road_w = SPAN + 2*WALL_T
road_top = HEIGHT + ARCH_T
box("road", 0, 0, road_top + ROAD_T/2, road_w/2, HALF_L+2, ROAD_T/2, road)
for s in (-1, 1):
    box(f"parapet_{s}", s*(road_w/2 - PARAPET_T/2), 0, road_top+ROAD_T+PARAPET_H/2,
        PARAPET_T/2, HALF_L+2, PARAPET_H/2, parapet)
    box(f"wall_{s}", s*(HALF_S+WALL_T/2), 0, (road_top+0.3)/2 - 0.3,
        WALL_T/2, HALF_L, (road_top+0.3)/2, stone)
box("floor", 0, 0, -0.15, HALF_S, HALF_L, 0.15, road)

# Wing walls
for e in (-1, 1):
    for s in (-1, 1):
        box(f"wing_{e}_{s}", s*(HALF_S+WALL_T+0.5), e*(HALF_L+1.5),
            road_top*0.6/2, 0.35, 1.5, road_top*0.6/2, stone)

# Finalize
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
arch = bpy.context.active_object; arch.name = "DaleheadArch"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_dalehead_arch.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Dalehead Arch to {out_path}")
print(f"  Verts: {len(arch.data.vertices)}, Faces: {len(arch.data.polygons)}")
