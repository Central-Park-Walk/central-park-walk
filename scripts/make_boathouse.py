"""Generate Loeb Boathouse for Central Park Walk.

The Loeb Boathouse (1954) sits on the east shore of The Lake.
A modernist take on a lakeside pavilion — low-slung with
horizontal emphasis, large glass panels, and a distinctive
green copper roof. The building stretches along the waterfront
with a dining terrace extending over the water.

Key features:
  - Long rectangular building (~35m × 12m)
  - Low-profile hip roof with broad eaves
  - Copper-green standing seam roof
  - Fieldstone and glass facade
  - Lakeside terrace/deck extending over water
  - Covered dining pavilion on south end

Origin at ground center.
Exports to models/furniture/cp_boathouse.glb
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

def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

fieldstone = make_mat("Fieldstone", (0.50, 0.47, 0.42), 0.88)
copper     = make_mat("Copper",     (0.35, 0.52, 0.42), 0.65, 0.15)  # verdigris
glass_mat  = make_mat("Glass",      (0.30, 0.35, 0.38), 0.15, 0.0)
wood_deck  = make_mat("WoodDeck",   (0.45, 0.35, 0.25), 0.82)
concrete   = make_mat("Concrete",   (0.62, 0.60, 0.56), 0.90)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# Dimensions
W = 35.0    # length (X)
D = 12.0    # depth (Y)
H = 4.5     # wall height
ROOF_H = 1.5  # low hip roof rise
WALL_T = 0.35
DECK_D = 6.0  # waterside deck depth
DECK_W = 25.0  # deck width

hw = W / 2.0
hd = D / 2.0

# ════════════════════════════════════════════
# 1. FOUNDATION
# ════════════════════════════════════════════
box("foundation", 0, 0, 0.15, hw + 0.3, hd + 0.3, 0.30, concrete)

# ════════════════════════════════════════════
# 2. MAIN WALLS
# ════════════════════════════════════════════
# Back wall (fieldstone — solid)
box("wall_back", 0, -hd + WALL_T/2, H/2 + 0.30, hw, WALL_T/2, H/2, fieldstone)

# Side walls
box("wall_east", -hw + WALL_T/2, 0, H/2 + 0.30, WALL_T/2, hd, H/2, fieldstone)
box("wall_west",  hw - WALL_T/2, 0, H/2 + 0.30, WALL_T/2, hd, H/2, fieldstone)

# Front wall — mostly glass with stone piers
n_bays = 8
bay_w = W / n_bays
glass_h = H * 0.75
for i in range(n_bays):
    bx = -hw + (i + 0.5) * bay_w
    # Glass panel
    box(f"glass_{i}", bx, hd - 0.10, glass_h/2 + 0.30 + 0.5,
        bay_w/2 - 0.15, 0.05, glass_h/2 - 0.3, glass_mat)
# Stone piers between glass
for i in range(n_bays + 1):
    px = -hw + i * bay_w
    box(f"pier_{i}", px, hd - WALL_T/2, H/2 + 0.30,
        0.18, WALL_T/2, H/2, fieldstone)

# Solid wall above glass
box("wall_front_top", 0, hd - WALL_T/2, H + 0.30 - 0.3,
    hw, WALL_T/2, 0.35, fieldstone)

# ════════════════════════════════════════════
# 3. COPPER HIP ROOF
# ════════════════════════════════════════════
eave_z = H + 0.30
overhang = 1.0  # broad eaves

rv = [
    (-hw - overhang, -hd - overhang, eave_z),
    ( hw + overhang, -hd - overhang, eave_z),
    ( hw + overhang,  hd + overhang, eave_z),
    (-hw - overhang,  hd + overhang, eave_z),
    # Hip ridge (shorter than full width)
    (-hw * 0.4, 0, eave_z + ROOF_H),
    ( hw * 0.4, 0, eave_z + ROOF_H),
]
rf = [
    (0, 1, 5, 4),
    (2, 3, 4, 5),
    (3, 0, 4),
    (1, 2, 5),
    (0, 3, 2, 1),
]
rm = bpy.data.meshes.new("roof_mesh")
rm.from_pydata(rv, [], rf)
rm.update()
ro = bpy.data.objects.new("CopperRoof", rm)
bpy.context.collection.objects.link(ro)
ro.data.materials.append(copper)
all_parts.append(ro)

# ════════════════════════════════════════════
# 4. WATERSIDE DECK
# ════════════════════════════════════════════
deck_y = hd + DECK_D / 2
box("deck_platform", 0, deck_y, 0.22,
    DECK_W / 2, DECK_D / 2, 0.10, wood_deck)

# Deck railing (low wooden rail)
box("deck_rail_s", 0, hd + DECK_D, 0.70, DECK_W/2, 0.06, 0.40, wood_deck)
for side in (-1, 1):
    box(f"deck_rail_{side}", side * DECK_W/2, deck_y, 0.70,
        0.06, DECK_D/2, 0.40, wood_deck)

# Railing posts
for i in range(int(DECK_W / 2.5) + 1):
    px = -DECK_W/2 + i * 2.5
    box(f"deck_post_s_{i}", px, hd + DECK_D, 0.55, 0.05, 0.05, 0.40, wood_deck)

# Deck support pilings (visible from water side)
for i in range(0, int(DECK_W / 3) + 1):
    px = -DECK_W/2 + i * 3.0
    box(f"piling_{i}", px, hd + DECK_D * 0.6, -0.15,
        0.10, 0.10, 0.55, concrete)


# ════════════════════════════════════════════
# 5. COVERED PAVILION EXTENSION (south dining area)
# ════════════════════════════════════════════
pav_w = 10.0
pav_d = 5.0
pav_x = hw * 0.3  # offset toward one end
pav_y = hd + DECK_D + pav_d / 2
pav_h = 3.5

# Pavilion posts
for px_s in (-1, 1):
    for py_s in (-1, 1):
        ppx = pav_x + px_s * (pav_w / 2 - 0.15)
        ppy = pav_y + py_s * (pav_d / 2 - 0.15)
        box(f"pav_post_{px_s}_{py_s}", ppx, ppy, pav_h/2 + 0.22,
            0.10, 0.10, pav_h/2, fieldstone)

# Pavilion flat roof
box("pav_roof", pav_x, pav_y, pav_h + 0.22 + 0.12,
    pav_w/2 + 0.5, pav_d/2 + 0.5, 0.15, copper)

# Pavilion floor
box("pav_floor", pav_x, pav_y, 0.18,
    pav_w/2, pav_d/2, 0.08, wood_deck)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "LoebBoathouse"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_boathouse.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Loeb Boathouse to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")
