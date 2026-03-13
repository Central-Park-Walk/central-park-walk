"""Generate stone weir/dam for Central Park Walk waterways.

Low masonry dam creating waterfalls between water bodies.
Origin at ground center. Exports to models/furniture/cp_stone_weir.glb
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

schist = make_mat("Schist", (0.38, 0.36, 0.33), 0.92)
wet = make_mat("WetStone", (0.28, 0.26, 0.24), 0.80)
cap_s = make_mat("CapStone", (0.45, 0.43, 0.40), 0.85)
all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name; o.scale = (hx*2, hy*2, hz*2)
    o.data.materials.append(mat); all_parts.append(o)
    return o

WW = 8.0; WH = 1.5; WT = 0.6; N = 10; ARC_R = 12.0
arc_half = math.asin(WW / (2 * ARC_R))

# Apron
box("apron", 0, 0.8, 0.08, WW/2 + 0.5, 1.0, 0.12, schist)
# Curved wall segments
for i in range(N):
    t = (i + 0.5) / N
    a = -arc_half + t * 2 * arc_half
    cx = ARC_R * math.sin(a); cy = ARC_R * (1 - math.cos(a))
    sw = WW / N; hv = WH + math.sin(i * 2.7) * 0.12
    o = box(f"weir_{i}", cx, cy, hv/2, sw/2 + 0.02, WT/2, hv/2, schist)
    o.rotation_euler = (0, 0, a)
# Wet face
for i in range(N):
    t = (i + 0.5) / N
    a = -arc_half + t * 2 * arc_half
    cx = ARC_R * math.sin(a); cy = ARC_R * (1 - math.cos(a)) + WT/2 + 0.02
    o = box(f"wet_{i}", cx, cy, WH*0.4, WW/N/2 + 0.02, 0.04, WH*0.45, wet)
    o.rotation_euler = (0, 0, a)
# Cap stones
for i in range(N):
    t = (i + 0.5) / N
    a = -arc_half + t * 2 * arc_half
    cx = ARC_R * math.sin(a); cy = ARC_R * (1 - math.cos(a))
    hv = WH + math.sin(i * 2.7) * 0.12
    o = box(f"cap_{i}", cx, cy, hv + 0.08, WW/N/2 + 0.04, WT/2 + 0.06, 0.10, cap_s)
    o.rotation_euler = (0, 0, a)
# Wing walls
for s in (-1, 1):
    wx = s * (WW/2 + 0.8)
    box(f"wing_{s}", wx, -0.5, WH*0.3, 0.30, 0.8, WH*0.35, schist)
    box(f"wing_cap_{s}", wx, -0.5, WH*0.6 + 0.06, 0.35, 0.85, 0.08, cap_s)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
obj = bpy.context.active_object; obj.name = "StoneWeir"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
out_path = "/home/chris/central-park-walk/models/furniture/cp_stone_weir.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Stone Weir to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}, Faces: {len(obj.data.polygons)}")
