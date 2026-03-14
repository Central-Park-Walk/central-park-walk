"""Generate formal garden fountains for Central Park Walk.

Three distinct fountain types for the Conservatory Garden:

1. Untermyer Fountain — ornate tiered circular fountain with 
   Three Dancing Maidens bronze sculpture (south/Italian garden)
2. Burnett Fountain — circular basin with girl & boy bronze figures
   from The Secret Garden (north/English garden)  
3. Center Fountain — single jet fountain in large circular basin
   (center/Italian garden)

Each is a separate object in the GLB.
Exports to models/furniture/cp_garden_fountain.glb
"""

import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

# ============================================================
# UNTERMYER FOUNTAIN — ornate tiered (south end)
# ============================================================
# Large outer basin (3m radius)
bpy.ops.mesh.primitive_cylinder_add(radius=3.0, depth=0.6, vertices=24)
u_basin = bpy.context.active_object
u_basin.name = "UntermyerBasin"
u_basin.location = (0, 0.3, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(u_basin)

# Basin rim (torus)
bpy.ops.mesh.primitive_torus_add(major_radius=3.0, minor_radius=0.12, major_segments=24, minor_segments=8)
u_rim = bpy.context.active_object
u_rim.name = "UntermyerRim"
u_rim.location = (0, 0.6, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(u_rim)

# Central pedestal
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.5, vertices=12)
u_ped = bpy.context.active_object
u_ped.name = "UntermyerPedestal"
u_ped.location = (0, 0.6 + 0.75, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(u_ped)

# Upper bowl
bpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=0.3, vertices=16)
u_bowl = bpy.context.active_object
u_bowl.name = "UntermyerBowl"
u_bowl.location = (0, 2.1 + 0.15, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(u_bowl)

# Three Dancing Maidens (3 simplified figures on top)
for i in range(3):
    angle = i * 2 * math.pi / 3
    mx = math.cos(angle) * 0.5
    mz = math.sin(angle) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.8, vertices=6)
    maiden = bpy.context.active_object
    maiden.name = f"Maiden_{i}"
    maiden.location = (mx, 2.4 + 0.4, mz)
    bpy.ops.object.transform_apply(location=True)
    objects.append(maiden)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, segments=6, ring_count=4)
    head = bpy.context.active_object
    head.name = f"MaidenHead_{i}"
    head.location = (mx, 2.4 + 0.85, mz)
    bpy.ops.object.transform_apply(location=True)
    objects.append(head)

# ============================================================
# BURNETT FOUNTAIN — Secret Garden (offset north)  
# ============================================================
OFF_N = 30.0  # offset north for separate placement

# Circular basin
bpy.ops.mesh.primitive_cylinder_add(radius=2.0, depth=0.5, vertices=20)
b_basin = bpy.context.active_object
b_basin.name = "BurnettBasin"
b_basin.location = (0, 0.25, OFF_N)
bpy.ops.object.transform_apply(location=True)
objects.append(b_basin)

# Basin rim
bpy.ops.mesh.primitive_torus_add(major_radius=2.0, minor_radius=0.10, major_segments=20, minor_segments=8)
b_rim = bpy.context.active_object
b_rim.name = "BurnettRim"
b_rim.location = (0, 0.5, OFF_N)
bpy.ops.object.transform_apply(location=True)
objects.append(b_rim)

# Central pedestal with children figure
bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=1.0, vertices=10)
b_ped = bpy.context.active_object
b_ped.name = "BurnettPedestal"
b_ped.location = (0, 0.5 + 0.5, OFF_N)
bpy.ops.object.transform_apply(location=True)
objects.append(b_ped)

# Bird basin on top
bpy.ops.mesh.primitive_cylinder_add(radius=0.45, depth=0.08, vertices=12)
b_bird = bpy.context.active_object
b_bird.name = "BirdBasin"
b_bird.location = (0, 1.5 + 0.04, OFF_N)
bpy.ops.object.transform_apply(location=True)
objects.append(b_bird)

# Girl figure (standing by basin)
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.6, vertices=6)
girl = bpy.context.active_object
girl.name = "GirlFigure"
girl.location = (0.25, 1.5 + 0.3, OFF_N)
bpy.ops.object.transform_apply(location=True)
objects.append(girl)

# Boy figure (sitting)
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.4, vertices=6)
boy = bpy.context.active_object
boy.name = "BoyFigure"
boy.location = (-0.25, 1.5 + 0.2, OFF_N)
bpy.ops.object.transform_apply(location=True)
objects.append(boy)

# ============================================================
# CENTER JET FOUNTAIN (offset south)
# ============================================================
OFF_S = -30.0

# Large circular basin
bpy.ops.mesh.primitive_cylinder_add(radius=4.0, depth=0.5, vertices=28)
c_basin = bpy.context.active_object
c_basin.name = "CenterBasin"
c_basin.location = (0, 0.25, OFF_S)
bpy.ops.object.transform_apply(location=True)
objects.append(c_basin)

# Basin rim
bpy.ops.mesh.primitive_torus_add(major_radius=4.0, minor_radius=0.15, major_segments=28, minor_segments=8)
c_rim = bpy.context.active_object
c_rim.name = "CenterRim"
c_rim.location = (0, 0.5, OFF_S)
bpy.ops.object.transform_apply(location=True)
objects.append(c_rim)

# Central jet nozzle
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.3, vertices=8)
c_jet = bpy.context.active_object
c_jet.name = "JetNozzle"
c_jet.location = (0, 0.5 + 0.15, OFF_S)
bpy.ops.object.transform_apply(location=True)
objects.append(c_jet)

# ============================================================
# MATERIALS
# ============================================================
stone_mat = bpy.data.materials.new("FountainStone")
stone_mat.use_nodes = True
bsdf = stone_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.62, 0.58, 0.52, 1.0)
bsdf.inputs["Roughness"].default_value = 0.70

bronze_mat = bpy.data.materials.new("FountainBronze")
bronze_mat.use_nodes = True
bsdf2 = bronze_mat.node_tree.nodes["Principled BSDF"]
bsdf2.inputs["Base Color"].default_value = (0.22, 0.18, 0.10, 1.0)
bsdf2.inputs["Metallic"].default_value = 0.85
bsdf2.inputs["Roughness"].default_value = 0.50

for obj in objects:
    obj.data.materials.clear()
    if any(k in obj.name for k in ["Maiden", "Girl", "Boy", "Head"]):
        obj.data.materials.append(bronze_mat)
    else:
        obj.data.materials.append(stone_mat)

# DON'T join — keep separate for individual placement
# Instead, export as-is with multiple objects
# Actually, for _load_glb_meshes we need named meshes
# Let's export the whole scene

out_path = "/home/chris/central-park-walk/models/furniture/cp_garden_fountain.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
total_verts = sum(len(o.data.vertices) for o in objects)
print(f"Exported Garden Fountains to {out_path} ({total_verts} total verts, {len(objects)} objects)")
