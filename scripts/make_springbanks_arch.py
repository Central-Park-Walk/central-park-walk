"""Generate Springbanks Arch model for Central Park Walk.

Springbanks Arch — semicircular stone arch in the North Woods. Built 1860s
by Calvert Vaux. A natural spring still flows audibly underneath.

Key dimensions:
  PASSAGE_L   = 21.64m  (71 ft underpass length)
  HEIGHT      = 2.79m   (9 ft 2 in)
  WIDTH       = 5.31m   (17 ft 5 in passageway width)

Materials:
  Exterior: Wedged rough Hudson Valley stone in segmented radiating voussoirs
  Interior: Red brick lined
  Railing: Cast iron, 15.44m (50 ft 8 in) on south side only

Profile: Semicircular — bordered by radiating voussoir pattern

Exports to models/furniture/cp_springbanks_arch.glb
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

stone = make_mat("HudsonStone", (0.48, 0.45, 0.40), roughness=0.85)
brick = make_mat("RedBrick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
iron = make_mat("CastIron", (0.22, 0.22, 0.23), roughness=0.65, metallic=0.85)
parapet_mat = make_mat("Parapet", (0.50, 0.47, 0.42), roughness=0.82)

WIDTH = 5.31; HALF_W = WIDTH / 2
HEIGHT = 2.79
PASS_L = 21.64; HALF_L = PASS_L / 2
WALL_T = 1.0; ARCH_T = 0.55; ROAD_T = 0.30
PARAPET_H = 1.0; PARAPET_T = 0.35
RAILING_H = 1.10; RAILING_T = 0.06
N_ARC = 24
all_parts = []

def semicircular_arc(hw, h, n):
    # True semicircle — radius = half_width, height may differ
    # For Springbanks, height (2.79m) < half_width (2.655m), so slightly squashed
    return [(hw * math.cos(math.pi * (1 - i/n)), h * math.sin(math.pi * (1 - i/n))) for i in range(n+1)]

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name
    o.scale = (hx*2, hy*2, hz*2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); all_parts.append(o); return o

# Barrel vault (brick interior)
arc_pts = semicircular_arc(HALF_W, HEIGHT, N_ARC)
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
    vf = []; ff = []; hw = WIDTH/2 + WALL_T; fh = HEIGHT + ARCH_T + ROAD_T
    vf += [(-hw, ey, -0.3), (-HALF_W, ey, -0.3), (-HALF_W, ey, 0), (-hw, ey, fh)]
    ff.append((0,1,2,3) if end>0 else (0,3,2,1))
    b = len(vf)
    vf += [(HALF_W, ey, -0.3), (hw, ey, -0.3), (hw, ey, fh), (HALF_W, ey, 0)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    b = len(vf)
    vf += [(-hw, ey, HEIGHT+ARCH_T), (hw, ey, HEIGHT+ARCH_T), (hw, ey, fh), (-hw, ey, fh)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    m = bpy.data.meshes.new(f"face_{end}"); m.from_pydata(vf, [], ff); m.update()
    o = bpy.data.objects.new(f"face_{end}", m); bpy.context.collection.objects.link(o)
    o.data.materials.append(stone); all_parts.append(o)

    # Voussoir arch ring (radiating stones)
    mesh = bpy.data.meshes.new(f"ring_{end}"); verts = []; faces = []
    for i in range(N_ARC + 1):
        px, pz = arc_pts[i]
        d = math.sqrt(px*px + pz*pz)
        if d > 0.1: ox, oz = px*(1+0.20/d), pz*(1+0.20/d)
        else: ox, oz = px, pz+0.20
        verts.append((px, ey+end*0.15, pz))
        verts.append((ox, ey+end*0.15, oz))
        verts.append((px, ey, pz))
        verts.append((ox, ey, oz))
    for i in range(N_ARC):
        b = i*4; nb = (i+1)*4
        faces.append((b, b+1, nb+1, nb))
        faces.append((b+1, b+3, nb+3, nb+1))
    mesh.from_pydata(verts, [], faces); mesh.update()
    obj = bpy.data.objects.new(f"ring_{end}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(stone); all_parts.append(obj)

# Road, parapets, walls, floor
road_top = HEIGHT + ARCH_T
road_w = WIDTH + 2*WALL_T
box("road", 0, 0, road_top+ROAD_T/2, road_w/2, HALF_L+2, ROAD_T/2, road)
for s in (-1, 1):
    box(f"wall_{s}", s*(HALF_W+WALL_T/2), 0, (road_top+0.3)/2-0.3,
        WALL_T/2, HALF_L, (road_top+0.3)/2, stone)
box("floor", 0, 0, -0.15, HALF_W, HALF_L, 0.15, road)

# South side: stone parapet + cast iron railing
# North side: just stone parapet
box("parapet_south", -(road_w/2 - PARAPET_T/2), 0, road_top+ROAD_T+PARAPET_H/2,
    PARAPET_T/2, HALF_L+2, PARAPET_H/2, parapet_mat)
box("parapet_north", (road_w/2 - PARAPET_T/2), 0, road_top+ROAD_T+PARAPET_H/2,
    PARAPET_T/2, HALF_L+2, PARAPET_H/2, parapet_mat)

# Cast iron railing on south side (15.44m = 50'8")
railing_l = 15.44 / 2
box("railing_south", -(road_w/2 + 0.05), 0, road_top+ROAD_T+RAILING_H/2,
    RAILING_T/2, railing_l, RAILING_H/2, iron)

# Wing walls
for e in (-1, 1):
    for s in (-1, 1):
        box(f"wing_{e}_{s}", s*(HALF_W+WALL_T+0.5), e*(HALF_L+1.5),
            road_top*0.6/2, 0.35, 1.5, road_top*0.6/2, stone)

# Finalize
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
arch = bpy.context.active_object; arch.name = "SpringbanksArch"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_springbanks_arch.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Springbanks Arch to {out_path}")
print(f"  Verts: {len(arch.data.vertices)}, Faces: {len(arch.data.polygons)}")
