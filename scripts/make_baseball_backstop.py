"""Generate baseball backstop for Central Park Walk.

Chain-link backstop (~5m tall, curved):
- 3 galvanized steel poles
- Chain-link fence panels between them
- Angled wing panels on each side

Exports to models/furniture/cp_backstop.glb
"""

import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

BACKSTOP_H = 5.0    # 16ft tall
CENTER_W = 6.0      # center panel width
WING_W = 4.0        # wing panel width
WING_ANGLE = 0.6    # ~35 degrees
POST_R = 0.04
WIRE_R = 0.005
N_VERT = 12
N_HORIZ = 10

# --- Posts ---
post_positions = [
    (0, 0),                                          # center
    (-CENTER_W/2, 0),                                # left center
    (CENTER_W/2, 0),                                 # right center
    (-CENTER_W/2 - math.cos(WING_ANGLE) * WING_W, math.sin(WING_ANGLE) * WING_W),   # left wing end
    (CENTER_W/2 + math.cos(WING_ANGLE) * WING_W, math.sin(WING_ANGLE) * WING_W),    # right wing end
]

for i, (px, pz) in enumerate(post_positions):
    bpy.ops.mesh.primitive_cylinder_add(radius=POST_R, depth=BACKSTOP_H, vertices=8)
    post = bpy.context.active_object
    post.name = f"Post_{i}"
    post.location = (px, BACKSTOP_H/2, pz)
    bpy.ops.object.transform_apply(location=True)
    objects.append(post)

# --- Wire mesh panels ---
# Build wire grids between post pairs
panel_pairs = [
    (1, 0),  # left center to center
    (0, 2),  # center to right center
    (3, 1),  # left wing end to left center
    (2, 4),  # right center to right wing end
]

for p0_idx, p1_idx in panel_pairs:
    p0x, p0z = post_positions[p0_idx]
    p1x, p1z = post_positions[p1_idx]
    dx = p1x - p0x
    dz = p1z - p0z
    panel_len = math.sqrt(dx**2 + dz**2)
    
    # Vertical wires
    for vi in range(N_VERT + 1):
        t = vi / N_VERT
        wx = p0x + dx * t
        wz = p0z + dz * t
        bpy.ops.mesh.primitive_cylinder_add(radius=WIRE_R, depth=BACKSTOP_H - 0.2, vertices=4)
        w = bpy.context.active_object
        w.name = f"VW_{p0_idx}_{vi}"
        w.location = (wx, BACKSTOP_H/2, wz)
        bpy.ops.object.transform_apply(location=True)
        objects.append(w)
    
    # Horizontal wires
    for hi in range(N_HORIZ + 1):
        t = hi / N_HORIZ
        wy = 0.2 + (BACKSTOP_H - 0.4) * t
        # Rotated cylinder along the panel direction
        angle = math.atan2(dz, dx)
        bpy.ops.mesh.primitive_cylinder_add(radius=WIRE_R, depth=panel_len, vertices=4)
        w = bpy.context.active_object
        w.name = f"HW_{p0_idx}_{hi}"
        w.rotation_euler = (0, 0, math.pi/2)
        # Align to panel direction
        mx = (p0x + p1x) / 2
        mz = (p0z + p1z) / 2
        w.location = (mx, wy, mz)
        w.rotation_euler = (0, -angle, math.pi/2)
        bpy.ops.object.transform_apply(location=True, rotation=True)
        objects.append(w)

# --- Top rail connecting all posts ---
for p0_idx, p1_idx in panel_pairs:
    p0x, p0z = post_positions[p0_idx]
    p1x, p1z = post_positions[p1_idx]
    dx = p1x - p0x
    dz = p1z - p0z
    length = math.sqrt(dx**2 + dz**2)
    angle = math.atan2(dz, dx)
    mx = (p0x + p1x) / 2
    mz = (p0z + p1z) / 2
    
    bpy.ops.mesh.primitive_cylinder_add(radius=POST_R * 0.8, depth=length, vertices=8)
    rail = bpy.context.active_object
    rail.name = f"TopRail_{p0_idx}_{p1_idx}"
    rail.location = (mx, BACKSTOP_H, mz)
    rail.rotation_euler = (0, -angle, math.pi/2)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    objects.append(rail)

# Material: galvanized chain link
mat = bpy.data.materials.new("ChainLink")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.45, 0.45, 0.42, 1.0)
bsdf.inputs["Metallic"].default_value = 0.7
bsdf.inputs["Roughness"].default_value = 0.55

for obj in objects:
    obj.data.materials.clear()
    obj.data.materials.append(mat)

# Join
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.active_object
obj.name = "Backstop"

out_path = "/home/chris/central-park-walk/models/furniture/cp_backstop.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Backstop to {out_path} ({vcount} verts, {fcount} faces)")
