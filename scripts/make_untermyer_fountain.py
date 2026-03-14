"""Untermyer Fountain — Three Dancing Maidens. Conservatory Garden south end."""
import bpy, math
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
objects = []

# Large outer basin (3m radius)
bpy.ops.mesh.primitive_cylinder_add(radius=3.0, depth=0.6, vertices=24)
o = bpy.context.active_object; o.name="Basin"; o.location=(0,0.3,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

# Basin rim
bpy.ops.mesh.primitive_torus_add(major_radius=3.0, minor_radius=0.12, major_segments=24, minor_segments=8)
o = bpy.context.active_object; o.name="Rim"; o.location=(0,0.6,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

# Central pedestal
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.5, vertices=12)
o = bpy.context.active_object; o.name="Pedestal"; o.location=(0,1.35,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

# Upper bowl
bpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=0.3, vertices=16)
o = bpy.context.active_object; o.name="Bowl"; o.location=(0,2.25,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

# Three Dancing Maidens
for i in range(3):
    a = i * 2 * math.pi / 3
    mx, mz = math.cos(a)*0.5, math.sin(a)*0.5
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.8, vertices=6)
    o = bpy.context.active_object; o.name=f"M{i}"; o.location=(mx,2.8,mz)
    bpy.ops.object.transform_apply(location=True); objects.append(o)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, segments=6, ring_count=4)
    o = bpy.context.active_object; o.name=f"H{i}"; o.location=(mx,3.25,mz)
    bpy.ops.object.transform_apply(location=True); objects.append(o)

stone = bpy.data.materials.new("Stone"); stone.use_nodes=True
stone.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.62,0.58,0.52,1)
stone.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=0.70
bronze = bpy.data.materials.new("Bronze"); bronze.use_nodes=True
bronze.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.22,0.18,0.10,1)
bronze.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value=0.85
for o in objects:
    o.data.materials.clear()
    o.data.materials.append(bronze if o.name.startswith(("M","H")) else stone)

bpy.ops.object.select_all(action='DESELECT')
for o in objects: o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]; bpy.ops.object.join()
bpy.context.active_object.name="UntermyerFountain"
bpy.ops.export_scene.gltf(filepath="/home/chris/central-park-walk/models/furniture/cp_untermyer_fountain.glb", export_format='GLB')
print("Exported Untermyer Fountain")
