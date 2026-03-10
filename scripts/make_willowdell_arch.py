"""Generate Willowdell Arch model for Central Park Walk.

Willowdell Arch — segmental stone arch carrying a path over the bridle
path near the south end of the park. Built 1860s by Calvert Vaux.

Key dimensions:
  WIDTH       = 4.52m   (14 ft 10 in)
  HEIGHT      = 3.00m   (9 ft 10 in)
  PASSAGE_L   = 14.94m  (49 ft)
  Profile: Segmental

Materials: Sandstone + brick

Exports to models/furniture/cp_willowdell_arch.glb
"""

import bpy, math, os

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for b in bpy.data.meshes:
    if b.users == 0: bpy.data.meshes.remove(b)
for b in bpy.data.materials:
    if b.users == 0: bpy.data.materials.remove(b)

def make_mat(name, color, roughness=0.80, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

sandstone = make_mat("Sandstone", (0.58, 0.50, 0.40), roughness=0.82)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
parapet_m = make_mat("Parapet", (0.55, 0.48, 0.40), roughness=0.78)

W = 4.52; HW = W/2; H = 3.00
PL = 14.94; HL = PL/2
WT = 0.90; AT = 0.50; RT = 0.30
PH = 1.0; PT = 0.35; NA = 24
all_parts = []

def seg_arc(hw, rise, n):
    R = (rise*rise + hw*hw)/(2*rise); cz = rise - R
    pts = []
    for i in range(n+1):
        t = i/n; x = -hw + t*2*hw
        inner = R*R - x*x
        z = cz + math.sqrt(max(inner, 0))
        pts.append((x, z))
    return pts

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name
    o.scale = (hx*2, hy*2, hz*2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); all_parts.append(o); return o

arc = seg_arc(HW, H, NA)
mesh = bpy.data.meshes.new("vault"); verts = []; faces = []
for px, pz in arc:
    verts.append((px, -HL, pz)); verts.append((px, HL, pz))
    d = math.sqrt(px*px + pz*pz)
    if d > 0.1: ox, oz = px*(1+AT/d), pz*(1+AT/d)
    else: ox, oz = px, pz+AT
    verts.append((ox, -HL, oz)); verts.append((ox, HL, oz))
for i in range(len(arc)-1):
    b = i*4; nb = (i+1)*4
    faces += [(b,b+1,nb+1,nb), (b+2,nb+2,nb+3,b+3), (b,nb,nb+2,b+2), (b+1,b+3,nb+3,nb+1)]
mesh.from_pydata(verts, [], faces); mesh.update()
obj = bpy.data.objects.new("vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(brick); all_parts.append(obj)

for end in (-1, 1):
    ey = end*HL; vf = []; ff = []; hw = W/2+WT; fh = H+AT+RT
    vf += [(-hw,ey,-0.3),(-HW,ey,-0.3),(-HW,ey,0),(-hw,ey,fh)]
    ff.append((0,1,2,3) if end>0 else (0,3,2,1))
    b = len(vf)
    vf += [(HW,ey,-0.3),(hw,ey,-0.3),(hw,ey,fh),(HW,ey,0)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    b = len(vf)
    vf += [(-hw,ey,H+AT),(hw,ey,H+AT),(hw,ey,fh),(-hw,ey,fh)]
    ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
    m = bpy.data.meshes.new(f"face_{end}"); m.from_pydata(vf, [], ff); m.update()
    o = bpy.data.objects.new(f"face_{end}", m); bpy.context.collection.objects.link(o)
    o.data.materials.append(sandstone); all_parts.append(o)

rw = W+2*WT; rt = H+AT
box("road", 0, 0, rt+RT/2, rw/2, HL+1.5, RT/2, road)
for s in (-1,1):
    box(f"par_{s}", s*(rw/2-PT/2), 0, rt+RT+PH/2, PT/2, HL+1.5, PH/2, parapet_m)
    box(f"wall_{s}", s*(HW+WT/2), 0, (rt+0.3)/2-0.3, WT/2, HL, (rt+0.3)/2, sandstone)
box("floor", 0, 0, -0.15, HW, HL, 0.15, road)
for e in (-1,1):
    for s in (-1,1):
        box(f"w_{e}_{s}", s*(HW+WT+0.4), e*(HL+1.2), rt*0.5, 0.3, 1.2, rt*0.5, sandstone)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
a = bpy.context.active_object; a.name = "WillowdellArch"
bpy.context.scene.cursor.location = (0,0,0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
out = "/home/chris/central-park-walk/models/furniture/cp_willowdell_arch.glb"
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Willowdell Arch to {out}")
print(f"  Verts: {len(a.data.vertices)}, Faces: {len(a.data.polygons)}")
