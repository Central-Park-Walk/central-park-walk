"""Generate Dana Pier at Harlem Meer for Central Park Walk.

Stone viewing/fishing platform extending into Harlem Meer.
Origin at shore end. Exports to models/furniture/cp_dana_pier.glb
"""
import bpy, math, os

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for b in bpy.data.meshes:
    if b.users == 0: bpy.data.meshes.remove(b)
for b in bpy.data.materials:
    if b.users == 0: bpy.data.materials.remove(b)

def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

stone = make_mat("Stone", (0.52, 0.50, 0.46), 0.88)
cap = make_mat("CapStone", (0.58, 0.55, 0.50), 0.82)
all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name; o.scale = (hx*2, hy*2, hz*2)
    o.data.materials.append(mat); all_parts.append(o)
    return o

L = 10.0; W = 3.0; H = 0.6; PH = 0.9; PT = 0.25; hw = W/2.0

# Deck
box("deck", 0, L/2, H/2, hw, L/2, H/2, stone)
box("deck_cap", 0, L/2, H + 0.03, hw - PT + 0.05, L/2 - PT + 0.05, 0.04, cap)
# Parapets
for s in (-1, 1):
    px = s * (hw - PT/2)
    box(f"par_{s}", px, L/2, H + PH/2, PT/2, L/2, PH/2, stone)
    box(f"par_cap_{s}", px, L/2, H + PH + 0.04, PT/2 + 0.04, L/2 + 0.04, 0.05, cap)
# End parapet
box("par_end", 0, L - PT/2, H + PH/2, hw, PT/2, PH/2, stone)
box("par_end_cap", 0, L - PT/2, H + PH + 0.04, hw + 0.04, PT/2 + 0.04, 0.05, cap)
# Shore step
box("shore", 0, -0.20, H * 0.4, hw + 0.2, 0.30, H * 0.45, stone)
# Corner bollards
for sx in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.50, vertices=8,
        location=(sx*(hw - PT/2), L - PT/2, H + PH + 0.30))
    b = bpy.context.active_object; b.name = f"boll_{sx}"
    b.data.materials.append(cap); all_parts.append(b)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.06, vertices=8,
        location=(sx*(hw - PT/2), L - PT/2, H + PH + 0.58))
    bc = bpy.context.active_object; bc.name = f"bcap_{sx}"
    bc.data.materials.append(cap); all_parts.append(bc)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
obj = bpy.context.active_object; obj.name = "DanaPier"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
out_path = "/home/chris/central-park-walk/models/furniture/cp_dana_pier.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Dana Pier to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}, Faces: {len(obj.data.polygons)}")
