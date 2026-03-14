"""Burnett Memorial Fountain — Secret Garden. Conservatory Garden north end."""
import bpy, math
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
objects = []

bpy.ops.mesh.primitive_cylinder_add(radius=2.0, depth=0.5, vertices=20)
o = bpy.context.active_object; o.name="Basin"; o.location=(0,0.25,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

bpy.ops.mesh.primitive_torus_add(major_radius=2.0, minor_radius=0.10, major_segments=20, minor_segments=8)
o = bpy.context.active_object; o.name="Rim"; o.location=(0,0.5,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=1.0, vertices=10)
o = bpy.context.active_object; o.name="Ped"; o.location=(0,1.0,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

bpy.ops.mesh.primitive_cylinder_add(radius=0.45, depth=0.08, vertices=12)
o = bpy.context.active_object; o.name="BirdBath"; o.location=(0,1.54,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.6, vertices=6)
o = bpy.context.active_object; o.name="Girl"; o.location=(0.25,1.8,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.4, vertices=6)
o = bpy.context.active_object; o.name="Boy"; o.location=(-0.25,1.7,0)
bpy.ops.object.transform_apply(location=True); objects.append(o)

stone = bpy.data.materials.new("Stone"); stone.use_nodes=True
stone.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.62,0.58,0.52,1)
bronze = bpy.data.materials.new("Bronze"); bronze.use_nodes=True
bronze.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.22,0.18,0.10,1)
bronze.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value=0.85
for o in objects:
    o.data.materials.clear()
    o.data.materials.append(bronze if o.name in ("Girl","Boy") else stone)

bpy.ops.object.select_all(action='DESELECT')
for o in objects: o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]; bpy.ops.object.join()
bpy.context.active_object.name="BurnettFountain"
bpy.ops.export_scene.gltf(filepath="/home/chris/central-park-walk/models/furniture/cp_burnett_fountain.glb", export_format='GLB')
print("Exported Burnett Fountain")
