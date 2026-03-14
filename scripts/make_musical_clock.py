"""Generate the Delacorte Musical Clock for Central Park Walk.

The Delacorte Musical Clock (1965) sits atop the Central Park Zoo entrance:
- Hexagonal brick base (~3m diameter, 2m tall)
- Ornate clock face on each of 4 sides
- Bronze bell housing at top (~4m total height)
- 6 bronze animal figures on a rotating platform
  (bear with tambourine, hippo with violin, goat with pipes,
   penguin with drum, kangaroo with horns, elephant with accordion)
- Simplified here as: brick tower + clock faces + bell dome + animal silhouettes

Height ~4m. Sited on arch above Zoo entrance.

Exports to models/furniture/cp_musical_clock.glb
"""

import bpy
import bmesh
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

BASE_R = 1.5      # hexagonal base radius
BASE_H = 2.0      # base height
CLOCK_R = 0.45     # clock face radius
DOME_R = 0.8       # dome/bell radius  
DOME_H = 1.2       # dome height
TOTAL_H = BASE_H + DOME_H + 0.3

# --- Hexagonal brick base ---
bpy.ops.mesh.primitive_cylinder_add(radius=BASE_R, depth=BASE_H, vertices=6)
base = bpy.context.active_object
base.name = "Base"
base.location = (0, BASE_H/2, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(base)

# --- Cornice ring at top of base ---
bpy.ops.mesh.primitive_cylinder_add(radius=BASE_R * 1.08, depth=0.15, vertices=6)
cornice = bpy.context.active_object
cornice.name = "Cornice"
cornice.location = (0, BASE_H, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(cornice)

# --- Clock faces (4 circles on alternating hex faces) ---
for i in range(4):
    angle = i * math.pi / 2  # N, E, S, W
    fx = math.cos(angle) * (BASE_R * 0.85)
    fz = math.sin(angle) * (BASE_R * 0.85)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=CLOCK_R, depth=0.05, vertices=16)
    face = bpy.context.active_object
    face.name = f"ClockFace_{i}"
    face.location = (fx, BASE_H * 0.65, fz)
    face.rotation_euler = (math.pi/2, 0, -angle + math.pi/2)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    objects.append(face)

# --- Bell dome on top ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=DOME_R, segments=12, ring_count=8)
dome = bpy.context.active_object
dome.name = "Dome"
# Scale to make it dome-shaped (flatten bottom half)
dome.scale = (1, 0.7, 1)
dome.location = (0, BASE_H + 0.15 + DOME_R * 0.4, 0)
bpy.ops.object.transform_apply(location=True, scale=True)
objects.append(dome)

# --- Bell at very top ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.4, vertices=8)
bell = bpy.context.active_object
bell.name = "Bell"
bell.location = (0, TOTAL_H - 0.1, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(bell)

# --- Animal figures (6 simplified cylinders on rotating platform) ---
ANIMAL_R = 0.12
PLATFORM_R = BASE_R * 0.75
PLATFORM_H = BASE_H + 0.2

for i in range(6):
    angle = i * math.pi / 3
    ax = math.cos(angle) * PLATFORM_R
    az = math.sin(angle) * PLATFORM_R
    
    # Simple upright cylinder as animal silhouette
    bpy.ops.mesh.primitive_cylinder_add(radius=ANIMAL_R, depth=0.5, vertices=6)
    animal = bpy.context.active_object
    animal.name = f"Animal_{i}"
    animal.location = (ax, PLATFORM_H + 0.25, az)
    bpy.ops.object.transform_apply(location=True)
    objects.append(animal)

# --- Materials ---
brick_mat = bpy.data.materials.new("Brick")
brick_mat.use_nodes = True
bsdf = brick_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.55, 0.28, 0.18, 1.0)  # warm brick red
bsdf.inputs["Roughness"].default_value = 0.85

bronze_mat = bpy.data.materials.new("Bronze")
bronze_mat.use_nodes = True
bsdf2 = bronze_mat.node_tree.nodes["Principled BSDF"]
bsdf2.inputs["Base Color"].default_value = (0.30, 0.22, 0.12, 1.0)  # patina bronze
bsdf2.inputs["Metallic"].default_value = 0.85
bsdf2.inputs["Roughness"].default_value = 0.45

clock_mat = bpy.data.materials.new("ClockFace")
clock_mat.use_nodes = True
bsdf3 = clock_mat.node_tree.nodes["Principled BSDF"]
bsdf3.inputs["Base Color"].default_value = (0.85, 0.82, 0.75, 1.0)  # cream/ivory
bsdf3.inputs["Roughness"].default_value = 0.3

for obj in objects:
    obj.data.materials.clear()
    if "Clock" in obj.name:
        obj.data.materials.append(clock_mat)
    elif "Animal" in obj.name or "Dome" in obj.name or "Bell" in obj.name:
        obj.data.materials.append(bronze_mat)
    else:
        obj.data.materials.append(brick_mat)

# Join
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.active_object
obj.name = "MusicalClock"

out_path = "/home/chris/central-park-walk/models/furniture/cp_musical_clock.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Musical Clock to {out_path} ({vcount} verts, {fcount} faces)")
