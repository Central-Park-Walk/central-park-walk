"""Generate basketball hoop for Central Park Walk.

Standard outdoor basketball hoop:
- Steel pole (4.6m to rim height)
- Backboard (1.8m × 1.1m)
- Rim (45cm diameter) at 3.05m

Exports to models/furniture/cp_basketball_hoop.glb
"""

import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

POLE_H = 3.5     # pole height to backboard bottom
POLE_R = 0.06    # 12cm diameter steel pole
RIM_H = 3.05     # regulation rim height
RIM_R = 0.225    # 45cm diameter
BOARD_W = 1.8
BOARD_H = 1.1
BOARD_THICK = 0.04

# --- Main pole ---
bpy.ops.mesh.primitive_cylinder_add(radius=POLE_R, depth=POLE_H, vertices=10)
pole = bpy.context.active_object
pole.name = "Pole"
pole.location = (0, POLE_H/2, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(pole)

# --- Backboard ---
bpy.ops.mesh.primitive_cube_add(size=1)
board = bpy.context.active_object
board.name = "Backboard"
board.scale = (BOARD_W/2, BOARD_H/2, BOARD_THICK/2)
board.location = (0, POLE_H + BOARD_H/2 - 0.2, 0.1)  # offset forward slightly
bpy.ops.object.transform_apply(location=True, scale=True)
objects.append(board)

# --- Rim (torus) ---
bpy.ops.mesh.primitive_torus_add(
    major_radius=RIM_R, minor_radius=0.01,
    major_segments=16, minor_segments=6
)
rim = bpy.context.active_object
rim.name = "Rim"
rim.location = (0, RIM_H, 0.1 + RIM_R + 0.05)  # extends forward from backboard
rim.rotation_euler = (math.pi/2, 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True)
objects.append(rim)

# --- Support arm (connects pole top to backboard) ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.4, vertices=8)
arm = bpy.context.active_object
arm.name = "Arm"
arm.rotation_euler = (math.pi/2, 0, 0)
arm.location = (0, POLE_H - 0.1, 0.2)
bpy.ops.object.transform_apply(location=True, rotation=True)
objects.append(arm)

# --- Materials ---
steel_mat = bpy.data.materials.new("Steel")
steel_mat.use_nodes = True
bsdf = steel_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.33, 1.0)
bsdf.inputs["Metallic"].default_value = 0.8
bsdf.inputs["Roughness"].default_value = 0.5

board_mat = bpy.data.materials.new("Backboard")
board_mat.use_nodes = True
bsdf2 = board_mat.node_tree.nodes["Principled BSDF"]
bsdf2.inputs["Base Color"].default_value = (0.85, 0.85, 0.85, 1.0)
bsdf2.inputs["Roughness"].default_value = 0.3

rim_mat = bpy.data.materials.new("RimOrange")
rim_mat.use_nodes = True
bsdf3 = rim_mat.node_tree.nodes["Principled BSDF"]
bsdf3.inputs["Base Color"].default_value = (0.8, 0.35, 0.05, 1.0)
bsdf3.inputs["Metallic"].default_value = 0.7
bsdf3.inputs["Roughness"].default_value = 0.45

for obj in objects:
    obj.data.materials.clear()
    if "Backboard" in obj.name:
        obj.data.materials.append(board_mat)
    elif "Rim" in obj.name:
        obj.data.materials.append(rim_mat)
    else:
        obj.data.materials.append(steel_mat)

# Join
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.active_object
obj.name = "BasketballHoop"

out_path = "/home/chris/central-park-walk/models/furniture/cp_basketball_hoop.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Basketball Hoop to {out_path} ({vcount} verts, {fcount} faces)")
