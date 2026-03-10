"""Generate a Central Park Conservancy recycling receptacle.

The actual trash cans in Central Park are the Landor/Landscape Forms aluminum
recycling system (2013). Cylindrical body with vertical slats inspired by the
1939 World's Fair bench, domed lid with circular aperture, cast aluminum base.
Triple powder-coat finish. ~30 gallon capacity.

NOT the old wire mesh basket — that was replaced throughout the park.

Dimensions: ~0.61m diameter, ~0.91m tall.
One material: 'Aluminum' (dark charcoal powder coat).
Exports to models/furniture/cp_trash_can.glb
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# --- Material ---
alum_mat = bpy.data.materials.new(name="Aluminum")
alum_mat.use_nodes = True
bsdf = alum_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.18, 0.19, 0.17, 1.0)  # dark charcoal powder coat
bsdf.inputs["Metallic"].default_value = 0.4
bsdf.inputs["Roughness"].default_value = 0.55

# --- Dimensions (metres) ---
CAN_R = 0.305         # body radius (24" diameter)
CAN_H = 0.70          # body height (slat area)
BASE_H = 0.08         # cast base height
LID_H = 0.06          # lid rim height
LID_DOME_H = 0.07     # dome rise above rim
APERTURE_R = 0.15     # waste aperture radius (12" = largest type)
SLAT_COUNT = 24       # number of vertical slats
SLAT_W = 0.030        # slat width (face width)
SLAT_T = 0.004        # slat thickness
TOTAL_H = BASE_H + CAN_H + LID_H + LID_DOME_H  # ~0.91m

CIRC_SEGS = 24


def make_base():
    """Cast aluminum base — heavy disc for stability."""
    objs = []
    # Wider foot disc
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CAN_R + 0.02, depth=0.02, vertices=CIRC_SEGS,
        location=(0, 0, 0.01)
    )
    foot = bpy.context.active_object
    foot.name = "base_foot"
    foot.data.materials.append(alum_mat)
    objs.append(foot)

    # Tapered base body
    bpy.ops.mesh.primitive_cone_add(
        radius1=CAN_R + 0.01, radius2=CAN_R - 0.005,
        depth=BASE_H - 0.02, vertices=CIRC_SEGS,
        location=(0, 0, 0.02 + (BASE_H - 0.02) / 2)
    )
    base = bpy.context.active_object
    base.name = "base_body"
    base.data.materials.append(alum_mat)
    objs.append(base)

    return objs


def make_slat_body():
    """Vertical slats forming the cylindrical body — the signature visual element.
    Slats have a very subtle spiral/twist inspired by the World's Fair bench."""
    objs = []

    for i in range(SLAT_COUNT):
        angle = 2 * math.pi * i / SLAT_COUNT
        # Slight twist: top of slat rotates ~5 degrees from bottom
        twist = math.radians(5)

        # Build slat as a thin box at the cylinder surface
        bm = bmesh.new()
        n_segs = 6  # vertical segments for the twist
        rings = []
        for j in range(n_segs + 1):
            t = j / n_segs
            z = BASE_H + t * CAN_H
            a = angle + t * twist
            # Center of slat on cylinder surface
            cx = math.cos(a) * CAN_R
            cy = math.sin(a) * CAN_R
            # Tangent direction (perpendicular to radius in XY plane)
            tx = -math.sin(a)
            ty = math.cos(a)
            # Normal direction (outward)
            nx = math.cos(a)
            ny = math.sin(a)
            # Four corners of slat cross-section
            hw = SLAT_W / 2
            ht = SLAT_T / 2
            corners = [
                Vector((cx - tx * hw - nx * ht, cy - ty * hw - ny * ht, z)),
                Vector((cx + tx * hw - nx * ht, cy + ty * hw - ny * ht, z)),
                Vector((cx + tx * hw + nx * ht, cy + ty * hw + ny * ht, z)),
                Vector((cx - tx * hw + nx * ht, cy - ty * hw + ny * ht, z)),
            ]
            ring = [bm.verts.new(c) for c in corners]
            rings.append(ring)

        bm.verts.ensure_lookup_table()
        for j in range(n_segs):
            for k in range(4):
                k2 = (k + 1) % 4
                bm.faces.new([rings[j][k], rings[j][k2], rings[j+1][k2], rings[j+1][k]])

        # Cap top and bottom
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])

        mesh = bpy.data.meshes.new(f"slat_{i}")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"slat_{i}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(alum_mat)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        objs.append(obj)

    # Inner liner (thin cylinder behind the slats — the actual container wall)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CAN_R - 0.01, depth=CAN_H, vertices=CIRC_SEGS,
        location=(0, 0, BASE_H + CAN_H / 2)
    )
    liner = bpy.context.active_object
    liner.name = "liner"
    liner.data.materials.append(alum_mat)
    objs.append(liner)

    # Top and bottom rings (reinforcement bands)
    for z in [BASE_H, BASE_H + CAN_H]:
        bpy.ops.mesh.primitive_torus_add(
            major_radius=CAN_R, minor_radius=0.008,
            major_segments=CIRC_SEGS, minor_segments=6,
            location=(0, 0, z)
        )
        ring = bpy.context.active_object
        ring.name = f"ring_{z:.2f}"
        ring.data.materials.append(alum_mat)
        objs.append(ring)

    return objs


def make_lid():
    """Domed lid with circular aperture."""
    objs = []
    lid_z = BASE_H + CAN_H

    # Lid rim — short cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CAN_R + 0.005, depth=LID_H, vertices=CIRC_SEGS,
        location=(0, 0, lid_z + LID_H / 2)
    )
    rim = bpy.context.active_object
    rim.name = "lid_rim"
    rim.data.materials.append(alum_mat)
    objs.append(rim)

    # Domed top — flattened hemisphere with aperture hole
    # Create as UV sphere, flatten, then boolean-subtract aperture
    bm = bmesh.new()
    dome_z = lid_z + LID_H
    n_rings = 8
    n_segs = CIRC_SEGS

    # Build dome vertices
    rings = []
    for i in range(n_rings + 1):
        t = i / n_rings  # 0 = edge, 1 = top
        phi = t * math.pi / 2  # 0 to 90 degrees
        r = CAN_R * math.cos(phi)
        z = dome_z + LID_DOME_H * math.sin(phi)

        if r < APERTURE_R and i > 0:
            # Stop at aperture edge
            break

        ring = []
        for j in range(n_segs):
            theta = 2 * math.pi * j / n_segs
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            ring.append(bm.verts.new(Vector((x, y, z))))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    # Connect rings
    for i in range(len(rings) - 1):
        for j in range(n_segs):
            j2 = (j + 1) % n_segs
            bm.faces.new([rings[i][j], rings[i][j2], rings[i+1][j2], rings[i+1][j]])

    mesh = bpy.data.meshes.new("lid_dome")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("lid_dome", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(alum_mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    objs.append(obj)

    # Aperture rim ring
    bpy.ops.mesh.primitive_torus_add(
        major_radius=APERTURE_R + 0.01, minor_radius=0.01,
        major_segments=16, minor_segments=6,
        location=(0, 0, dome_z + LID_DOME_H * 0.85)
    )
    ap_ring = bpy.context.active_object
    ap_ring.name = "aperture_ring"
    ap_ring.data.materials.append(alum_mat)
    objs.append(ap_ring)

    return objs


# --- Build the trash can ---
all_parts = []
all_parts.extend(make_base())
all_parts.extend(make_slat_body())
all_parts.extend(make_lid())

# Apply all transforms
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Join all parts
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

can = bpy.context.active_object
can.name = "CP_TrashCan"

# Set origin so bottom is at Z=0
bbox = [can.matrix_world @ Vector(corner) for corner in can.bound_box]
min_z = min(v.z for v in bbox)
can.location.z -= min_z
bpy.ops.object.transform_apply(location=True)

# Export GLB
out_path = "/home/chris/central-park-walk/models/furniture/cp_trash_can.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)

bbox2 = [can.matrix_world @ Vector(corner) for corner in can.bound_box]
height = max(v.z for v in bbox2) - min(v.z for v in bbox2)
print(f"Exported CP trash receptacle to {out_path}")
print(f"  Height: {height:.2f}m  ({height * 39.37:.1f} in)")
print(f"  Faces: {len(can.data.polygons)}")
