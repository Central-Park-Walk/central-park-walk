"""Generate a Central Park comfort station (restroom building).

Central Park comfort stations are small stone buildings with:
  - Manhattan schist/granite walls (~4m tall to eave)
  - Gable roof with slate tiles (~2m rise)
  - Arched doorway openings on long sides
  - Stone quoins at corners
  - Approximate footprint: 8m × 5m

Origin at ground center of the building footprint.
Exports to models/furniture/cp_comfort_station.glb
"""

import bpy
import math
import os
from mathutils import Vector

# ── Clear scene ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ── Materials ──
def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

schist = make_mat("Schist", (0.42, 0.40, 0.36), 0.88)   # dark Manhattan schist
slate  = make_mat("Slate",  (0.35, 0.33, 0.30), 0.78)    # slate roof
trim   = make_mat("Trim",   (0.55, 0.52, 0.46), 0.82)    # lighter stone trim

# ── Dimensions ──
W = 8.0    # length (X)
D = 5.0    # depth (Z)
H = 4.0    # wall height to eave
RIDGE_H = 2.0  # additional height from eave to ridge
WALL_T = 0.45  # wall thickness
DOOR_W = 1.2   # doorway width
DOOR_H = 2.6   # doorway height
all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o


# ════════════════════════════════════════════
# 1. WALLS — four walls with doorway cutouts on long sides
# ════════════════════════════════════════════

hw = W / 2.0
hd = D / 2.0
wt = WALL_T

# Front wall — three sections around doorway opening
# Left of door
left_w = (W - DOOR_W) / 2.0
box("wall_front_l", -(DOOR_W/2 + left_w/2), hd - wt/2, H/2, left_w/2, wt/2, H/2, schist)
# Right of door
box("wall_front_r",  (DOOR_W/2 + left_w/2), hd - wt/2, H/2, left_w/2, wt/2, H/2, schist)
# Above door
above_h = H - DOOR_H
box("wall_front_top", 0, hd - wt/2, DOOR_H + above_h/2, DOOR_W/2, wt/2, above_h/2, schist)
# Back wall — same doorway layout
box("wall_back_l", -(DOOR_W/2 + left_w/2), -hd + wt/2, H/2, left_w/2, wt/2, H/2, schist)
box("wall_back_r",  (DOOR_W/2 + left_w/2), -hd + wt/2, H/2, left_w/2, wt/2, H/2, schist)
box("wall_back_top", 0, -hd + wt/2, DOOR_H + above_h/2, DOOR_W/2, wt/2, above_h/2, schist)
# Side walls (solid)
# Left wall
box("wall_front", 0, hd - wt/2, H/2, hw, wt/2, H/2, schist)
# Back wall
box("wall_back", 0, -hd + wt/2, H/2, hw, wt/2, H/2, schist)
# Left wall
box("wall_left", -hw + wt/2, 0, H/2, wt/2, hd, H/2, schist)
# Right wall
box("wall_right", hw - wt/2, 0, H/2, wt/2, hd, H/2, schist)


# ════════════════════════════════════════════
# 2. GABLE ROOF
# ════════════════════════════════════════════
# Two triangular gable walls + two rectangular roof planes

# Gable triangles (end walls extending above eave line)
# Using a simple prism approach for the roof

roof_verts = []
roof_faces = []

# Roof ridge runs along X (long axis)
# Left roof plane: from left eave to ridge
# Right roof plane: from right eave to ridge
eave_overhang = 0.3

# Vertices for roof solid
rv = [
    # Bottom rectangle (eave level)
    (-hw - eave_overhang, -hd - eave_overhang, H),   # 0: front-left eave
    ( hw + eave_overhang, -hd - eave_overhang, H),   # 1: front-right eave
    ( hw + eave_overhang,  hd + eave_overhang, H),   # 2: back-right eave
    (-hw - eave_overhang,  hd + eave_overhang, H),   # 3: back-left eave
    # Ridge line
    (-hw - eave_overhang, 0, H + RIDGE_H),            # 4: left ridge
    ( hw + eave_overhang, 0, H + RIDGE_H),            # 5: right ridge
]

rf = [
    # Front slope (facing -Y)
    (0, 1, 5, 4),
    # Back slope (facing +Y)
    (2, 3, 4, 5),
    # Left gable end
    (3, 0, 4),
    # Right gable end
    (1, 2, 5),
    # Underside (soffit) — two triangles
    (0, 3, 2, 1),
]

roof_mesh = bpy.data.meshes.new("roof_mesh")
roof_mesh.from_pydata(rv, [], rf)
roof_mesh.update()
roof_obj = bpy.data.objects.new("Roof", roof_mesh)
bpy.context.collection.objects.link(roof_obj)
roof_obj.data.materials.append(slate)
all_parts.append(roof_obj)

# Gable wall fill (triangular wall sections above eave on each end)
for side in (-1, 1):
    gv = [
        (-hw + wt * 0.5, side * (hd - wt), H),              # inner bottom left
        ( hw - wt * 0.5, side * (hd - wt), H),              # inner bottom right
        (0,              side * (hd - wt), H + RIDGE_H - 0.1),  # apex
    ]
    gf = [(0, 1, 2)] if side < 0 else [(0, 2, 1)]
    gmesh = bpy.data.meshes.new(f"gable_{side}")
    gmesh.from_pydata(gv, [], gf)
    gmesh.update()
    gobj = bpy.data.objects.new(f"Gable_{side}", gmesh)
    bpy.context.collection.objects.link(gobj)
    gobj.data.materials.append(schist)
    all_parts.append(gobj)


# ════════════════════════════════════════════
# 3. DOORWAY SURROUNDS — stone trim around entrances
# ════════════════════════════════════════════

# Door opening on front face (+Y side) — decorative stone surround
for side_y in (1, -1):  # front and back entrances
    dy = side_y * hd
    # Left jamb
    box(f"jamb_l_{side_y}", -DOOR_W/2 - 0.08, dy, DOOR_H/2,
        0.10, 0.06, DOOR_H/2, trim)
    # Right jamb
    box(f"jamb_r_{side_y}", DOOR_W/2 + 0.08, dy, DOOR_H/2,
        0.10, 0.06, DOOR_H/2, trim)
    # Lintel / arch keystone
    box(f"lintel_{side_y}", 0, dy, DOOR_H + 0.15,
        DOOR_W/2 + 0.15, 0.06, 0.18, trim)


# ════════════════════════════════════════════
# 4. CORNER QUOINS — alternating stone blocks at building corners
# ════════════════════════════════════════════

quoin_w = 0.20
quoin_d = 0.08
quoin_h = 0.40
n_quoins = int(H / (quoin_h * 2))

for cx_sign in (-1, 1):
    for cy_sign in (-1, 1):
        qx = cx_sign * hw
        qy = cy_sign * hd
        for qi in range(n_quoins):
            qz = quoin_h + qi * quoin_h * 2
            if qz + quoin_h > H:
                break
            # Alternate which face the quoin protrudes from
            if qi % 2 == 0:
                box(f"quoin_{cx_sign}_{cy_sign}_{qi}",
                    qx, qy + cy_sign * quoin_d/2, qz,
                    quoin_w/2, quoin_d/2, quoin_h/2, trim)
            else:
                box(f"quoin_{cx_sign}_{cy_sign}_{qi}",
                    qx + cx_sign * quoin_d/2, qy, qz,
                    quoin_d/2, quoin_w/2, quoin_h/2, trim)


# ════════════════════════════════════════════
# 5. FOUNDATION — visible stone base course
# ════════════════════════════════════════════
box("foundation", 0, 0, -0.15, hw + 0.10, hd + 0.10, 0.20, trim)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

station = bpy.context.active_object
station.name = "ComfortStation"

# Origin at ground center
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_comfort_station.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Comfort Station to {out_path}")
print(f"  Vertices: {len(station.data.vertices)}")
print(f"  Faces: {len(station.data.polygons)}")
