"""Generate 79th Street Maintenance Yard building for Central Park Walk.

Utilitarian park maintenance facility — low, functional concrete block
building used for equipment storage and park operations.

Origin at ground center.
Exports to models/furniture/cp_maintenance_yard.glb
"""

import bpy
import math
import os

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

concrete = make_mat("Concrete", (0.55, 0.53, 0.50), 0.90)
metal_door = make_mat("MetalDoor", (0.35, 0.35, 0.33), 0.65, 0.3)
trim = make_mat("Trim", (0.30, 0.28, 0.26), 0.80)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

W = 20.0; D = 10.0; H = 4.0; T = 0.30
hw = W / 2.0; hd = D / 2.0

# Foundation
box("foundation", 0, 0, 0.10, hw + 0.15, hd + 0.15, 0.20, concrete)
# Back wall
box("wall_back", 0, -hd + T/2, H/2 + 0.20, hw, T/2, H/2, concrete)
# Side walls
box("wall_left", -hw + T/2, 0, H/2 + 0.20, T/2, hd, H/2, concrete)
box("wall_right", hw - T/2, 0, H/2 + 0.20, T/2, hd, H/2, concrete)
# Front wall sections around 2 garage doors
garage_w = 4.0; garage_h = 3.5; gap = 2.0
d1l = -gap/2 - garage_w; d1r = -gap/2; d2l = gap/2; d2r = gap/2 + garage_w
# Left section
sw = (d1l - (-hw + T))
if sw > 0.1:
    box("front_l", -hw + T + sw/2, hd - T/2, H/2 + 0.20, sw/2, T/2, H/2, concrete)
# Center pier
box("front_mid", 0, hd - T/2, H/2 + 0.20, gap/2, T/2, H/2, concrete)
# Right section
sw2 = (hw - T) - d2r
if sw2 > 0.1:
    box("front_r", d2r + sw2/2, hd - T/2, H/2 + 0.20, sw2/2, T/2, H/2, concrete)
# Above doors
above_h = H - garage_h
for i, (dl, dr) in enumerate([(d1l, d1r), (d2l, d2r)]):
    mid = (dl + dr) / 2
    box(f"front_above_{i}", mid, hd - T/2, garage_h + 0.20 + above_h/2, garage_w/2, T/2, above_h/2, concrete)
# Garage doors
for i, (dl, dr) in enumerate([(d1l, d1r), (d2l, d2r)]):
    mid = (dl + dr) / 2
    box(f"garage_{i}", mid, hd - T*0.8, garage_h/2 + 0.20, garage_w/2 - 0.05, 0.03, garage_h/2 - 0.05, metal_door)
    box(f"gframe_l_{i}", dl + 0.08, hd - T/2, garage_h/2 + 0.20, 0.08, T/2 + 0.02, garage_h/2, trim)
    box(f"gframe_r_{i}", dr - 0.08, hd - T/2, garage_h/2 + 0.20, 0.08, T/2 + 0.02, garage_h/2, trim)
    box(f"gframe_t_{i}", mid, hd - T/2, garage_h + 0.20, garage_w/2, T/2 + 0.02, 0.08, trim)
# Flat roof + parapet
box("roof", 0, 0, H + 0.30, hw + 0.20, hd + 0.20, 0.15, concrete)
box("par_f", 0, hd + 0.10, H + 0.55, hw + 0.20, 0.12, 0.20, concrete)
box("par_b", 0, -hd - 0.10, H + 0.55, hw + 0.20, 0.12, 0.20, concrete)
box("par_l", -hw - 0.10, 0, H + 0.55, 0.12, hd + 0.20, 0.20, concrete)
box("par_r", hw + 0.10, 0, H + 0.55, 0.12, hd + 0.20, 0.20, concrete)
# Office door + window on east
box("office_door", hw - T*0.8, -hd + 2.0, 1.3, 0.03, 0.5, 1.1, metal_door)
box("office_win", hw - T*0.8, -hd + 4.0, 2.0, 0.03, 0.6, 0.5, metal_door)
# Loading step
box("step", 0, hd + 0.5, 0.15, 5.0, 0.4, 0.15, concrete)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
obj = bpy.context.active_object
obj.name = "MaintenanceYard"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
out_path = "/home/chris/central-park-walk/models/furniture/cp_maintenance_yard.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Maintenance Yard to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}, Faces: {len(obj.data.polygons)}")
