"""Generate Central Park Zoo entrance/main building complex for Central Park Walk.

The Central Park Zoo (rebuilt 1988, Kevin Roche John Dinkeloo & Associates)
is a small urban zoo with a distinctive modernist vocabulary in red brick with
limestone trim. The entrance faces East 64th Street.

Key features:
  - Main entrance building: ~20m × 8m, red brick, large central arch
    (5m wide, 4m tall) with limestone voussoir surround
  - Clock tower above entrance: hexagonal shaft + copper conical cap,
    ~12m total height from ground
  - Two flanking wing buildings (each ~12m × 8m) set slightly back
  - Limestone trim bands at sill height and cornice
  - Flat parapet roofline (modernist), wings with low brick parapet
  - U-shaped courtyard implied by setback relationship

Origin at ground center of the overall complex footprint.
Exports to models/furniture/cp_zoo.glb
"""

import bpy
import math
import os

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

brick      = make_mat("Brick",     (0.52, 0.30, 0.22), roughness=0.88)
limestone  = make_mat("Limestone", (0.72, 0.68, 0.62), roughness=0.82)
copper     = make_mat("Copper",    (0.35, 0.55, 0.45), roughness=0.65, metallic=0.4)
dark_metal = make_mat("DarkMetal", (0.10, 0.10, 0.09), roughness=0.55, metallic=0.6)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Key dimensions ──
# Main entrance block
MB_W  = 20.0   # main building width (X)
MB_D  = 8.0    # main building depth (Y)
MB_H  = 7.0    # main building wall height to parapet base

# Flanking wings — set back 3m in Y relative to entrance face
WING_W  = 12.0   # each wing width (X)
WING_D  = 8.0    # wing depth (Y)
WING_H  = 5.5    # wing wall height (lower than central block)
WING_SETBACK = 2.0  # wings' front face set back from entrance face

# Arch
ARCH_W   = 5.0    # arch clear width
ARCH_H   = 4.0    # arch clear height (to intrados crown)

# Clock tower
CT_W     = 3.0    # hexagonal tower circumradius (to flat)
CT_SHAFT = 8.5    # shaft height above main building parapet
CT_CAP_H = 1.8    # copper cone height above shaft

# Derived
MB_HW = MB_W / 2.0
MB_HD = MB_D / 2.0
WING_HW = WING_W / 2.0
WING_HD = WING_D / 2.0

# Wings are offset in X so their outer edges align with overall complex.
# Left wing center X: -(MB_HW + WING_HW)  right wing: +(MB_HW + WING_HW)
WING_X_L = -(MB_HW + WING_HW)
WING_X_R =  (MB_HW + WING_HW)

# Y positioning: front face of main building at Y = +MB_HD
# Wings set back → their front face at Y = MB_HD - WING_SETBACK
# Wing center Y = wing front face + WING_HD/2 from its own geometry... wait:
# wing front at Y_f = MB_HD - WING_SETBACK
# wing back  at Y_b = Y_f - WING_D
# wing center Y = Y_f - WING_HD = (MB_HD - WING_SETBACK) - WING_HD
WING_Y_FRONT = MB_HD - WING_SETBACK
WING_Y_CEN   = WING_Y_FRONT - WING_HD   # center of wing in world Y

WALL_T = 0.35   # wall thickness

# ════════════════════════════════════════════
# 1. GROUND PLANE / STEPS — entrance plaza
# ════════════════════════════════════════════
# Broad entry step slab in front of main entrance
box("plaza_step_1", 0, MB_HD + 0.80, 0.10,  MB_HW * 0.7, 0.80, 0.10, limestone)
box("plaza_step_2", 0, MB_HD + 0.30, 0.20,  MB_HW * 0.55, 0.30, 0.10, limestone)

# ════════════════════════════════════════════
# 2. MAIN ENTRANCE BUILDING
# ════════════════════════════════════════════

# Foundation plinth
box("main_plinth", 0, 0, 0.18, MB_HW + 0.15, MB_HD + 0.15, 0.18, limestone)

# -- Front wall (south face, Y = +MB_HD) with central arch opening --
# Wall is split: left pier, arch, right pier, and solid lintel above arch.
# Arch clear width = ARCH_W, so pier widths = (MB_W - ARCH_W) / 2
PIER_W = (MB_W - ARCH_W) / 2.0   # 7.5 m each

# Left pier (arch left side)
box("main_front_left",
    -(ARCH_W/2 + PIER_W/2), MB_HD - WALL_T/2, MB_H/2 + 0.18,
    PIER_W/2, WALL_T/2, MB_H/2, brick)

# Right pier
box("main_front_right",
    +(ARCH_W/2 + PIER_W/2), MB_HD - WALL_T/2, MB_H/2 + 0.18,
    PIER_W/2, WALL_T/2, MB_H/2, brick)

# Spandrel / wall above arch up to parapet
box("main_front_spandrel",
    0, MB_HD - WALL_T/2, ARCH_H + 0.18 + (MB_H - ARCH_H)/2,
    ARCH_W/2, WALL_T/2, (MB_H - ARCH_H)/2, brick)

# -- Back wall (north face, Y = -MB_HD) --
box("main_back", 0, -MB_HD + WALL_T/2, MB_H/2 + 0.18, MB_HW, WALL_T/2, MB_H/2, brick)

# -- Side walls --
box("main_side_l", -MB_HW + WALL_T/2, 0, MB_H/2 + 0.18, WALL_T/2, MB_HD, MB_H/2, brick)
box("main_side_r",  MB_HW - WALL_T/2, 0, MB_H/2 + 0.18, WALL_T/2, MB_HD, MB_H/2, brick)

# -- Parapet cap on main building --
PARAPET_H = 0.6
box("main_parapet_front",
    0, MB_HD, MB_H + 0.18 + PARAPET_H/2,
    MB_HW + 0.05, 0.12, PARAPET_H/2, limestone)
box("main_parapet_back",
    0, -MB_HD, MB_H + 0.18 + PARAPET_H/2,
    MB_HW + 0.05, 0.12, PARAPET_H/2, limestone)
box("main_parapet_l",
    -MB_HW, 0, MB_H + 0.18 + PARAPET_H/2,
    0.12, MB_HD + 0.05, PARAPET_H/2, limestone)
box("main_parapet_r",
     MB_HW, 0, MB_H + 0.18 + PARAPET_H/2,
    0.12, MB_HD + 0.05, PARAPET_H/2, limestone)

# -- Limestone trim band at sill (~1m) and cornice (~5.5m) --
for band_z, label in [(1.0, "sill"), (5.5, "cornice")]:
    box(f"trim_{label}_front", 0, MB_HD,     band_z + 0.18, MB_HW + 0.05, 0.06, 0.10, limestone)
    box(f"trim_{label}_back",  0, -MB_HD,    band_z + 0.18, MB_HW + 0.05, 0.06, 0.10, limestone)
    box(f"trim_{label}_l",    -MB_HW, 0,     band_z + 0.18, 0.06, MB_HD + 0.06, 0.10, limestone)
    box(f"trim_{label}_r",     MB_HW, 0,     band_z + 0.18, 0.06, MB_HD + 0.06, 0.10, limestone)

# -- Arch surround (limestone voussoir band) --
# Represented as a limestone frame around the arch opening face.
# Outer frame: surround the arch rect plus limestone depth strips on sides/top.
ARCH_SURR = 0.30   # surround width
# Side jambs of arch surround
box("arch_surr_l",
    -(ARCH_W/2 + ARCH_SURR/2), MB_HD - WALL_T/2 - 0.04,
    ARCH_H/2 + 0.18,
    ARCH_SURR/2, WALL_T/2 + 0.04, ARCH_H/2, limestone)
box("arch_surr_r",
    +(ARCH_W/2 + ARCH_SURR/2), MB_HD - WALL_T/2 - 0.04,
    ARCH_H/2 + 0.18,
    ARCH_SURR/2, WALL_T/2 + 0.04, ARCH_H/2, limestone)
# Arch crown band (keystone strip at top of opening)
box("arch_surr_top",
    0, MB_HD - WALL_T/2 - 0.04,
    ARCH_H + 0.18 + ARCH_SURR/2,
    ARCH_W/2 + ARCH_SURR, WALL_T/2 + 0.04, ARCH_SURR/2, limestone)

# Arch soffit (under-arch ceiling strip — shallow box representing barrel soffit)
SOFFIT_T = 0.25
box("arch_soffit",
    0, MB_HD - SOFFIT_T/2,
    ARCH_H + 0.18 - 0.10,
    ARCH_W/2, SOFFIT_T/2, 0.12, limestone)

# -- Flat roof slab on main building --
box("main_roof",
    0, 0, MB_H + 0.18 + PARAPET_H/2,
    MB_HW, MB_HD, 0.15, limestone)

# ════════════════════════════════════════════
# 3. CLOCK TOWER (hexagonal, above entrance centre)
# ════════════════════════════════════════════
# Base Z: top of main building parapet
TOWER_BASE_Z = MB_H + 0.18 + PARAPET_H

# Hexagonal shaft — 6-sided cylinder standing on the entrance building
N_HEX = 6
HEX_R = CT_W / 2.0   # circumradius

bpy.ops.mesh.primitive_cylinder_add(
    radius=HEX_R,
    depth=CT_SHAFT,
    vertices=N_HEX,
    location=(0, 0, TOWER_BASE_Z + CT_SHAFT / 2))
tower_shaft = bpy.context.active_object
tower_shaft.name = "tower_shaft"
tower_shaft.data.materials.append(brick)
all_parts.append(tower_shaft)

# Limestone belt course mid-tower
belt_z = TOWER_BASE_Z + CT_SHAFT * 0.45
bpy.ops.mesh.primitive_cylinder_add(
    radius=HEX_R + 0.12,
    depth=0.20,
    vertices=N_HEX,
    location=(0, 0, belt_z))
belt = bpy.context.active_object
belt.name = "tower_belt"
belt.data.materials.append(limestone)
all_parts.append(belt)

# Tower cap / cornice ring (limestone)
TOWER_TOP_Z = TOWER_BASE_Z + CT_SHAFT
bpy.ops.mesh.primitive_cylinder_add(
    radius=HEX_R + 0.25,
    depth=0.30,
    vertices=N_HEX,
    location=(0, 0, TOWER_TOP_Z + 0.15))
cap_ring = bpy.context.active_object
cap_ring.name = "tower_cap_ring"
cap_ring.data.materials.append(limestone)
all_parts.append(cap_ring)

# Clock faces — 6 thin limestone panels on tower shaft (one per face)
# Each panel is inset slightly and shows as a lighter square
CLOCK_Z = TOWER_BASE_Z + CT_SHAFT * 0.62
for i in range(N_HEX):
    angle = (2 * math.pi * i / N_HEX)
    # Centre of each hex face
    face_r = HEX_R * math.cos(math.pi / N_HEX)   # apothem
    cx = math.cos(angle + math.pi / N_HEX) * (face_r + 0.02)
    cy = math.sin(angle + math.pi / N_HEX) * (face_r + 0.02)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, CLOCK_Z))
    face = bpy.context.active_object
    face.name = f"clock_face_{i}"
    face.scale = (0.55, 0.55, 0.55)
    face.rotation_euler = (0, 0, angle + math.pi / N_HEX)
    face.data.materials.append(limestone)
    all_parts.append(face)

# Conical copper cap
CAP_BASE_Z = TOWER_TOP_Z + 0.30
HEX_CAP_R  = HEX_R + 0.20
cv = []
for i in range(N_HEX):
    a = 2 * math.pi * i / N_HEX
    cv.append((math.cos(a) * HEX_CAP_R, math.sin(a) * HEX_CAP_R, CAP_BASE_Z))
cv.append((0, 0, CAP_BASE_Z + CT_CAP_H))
cf = []
for i in range(N_HEX):
    cf.append((i, (i + 1) % N_HEX, N_HEX))
cf.append(list(range(N_HEX)))
cm = bpy.data.meshes.new("tower_cap_cone")
cm.from_pydata(cv, [], cf)
cm.update()
co_obj = bpy.data.objects.new("TowerCopperCap", cm)
bpy.context.collection.objects.link(co_obj)
co_obj.data.materials.append(copper)
all_parts.append(co_obj)

# Finial spike atop cap
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.05, depth=0.5, vertices=6,
    location=(0, 0, CAP_BASE_Z + CT_CAP_H + 0.25))
fin = bpy.context.active_object
fin.name = "tower_finial"
fin.data.materials.append(dark_metal)
all_parts.append(fin)

# ════════════════════════════════════════════
# 4. FLANKING WING BUILDINGS
# ════════════════════════════════════════════
for side, wx_cen in (("L", WING_X_L), ("R", WING_X_R)):
    wy_cen = WING_Y_CEN

    # Plinth
    box(f"wing_{side}_plinth",
        wx_cen, wy_cen, 0.12,
        WING_HW + 0.10, WING_HD + 0.10, 0.12, limestone)

    # Front wall (faces courtyard / street side)
    box(f"wing_{side}_front",
        wx_cen, wy_cen + WING_HD - WALL_T/2, WING_H/2 + 0.12,
        WING_HW, WALL_T/2, WING_H/2, brick)

    # Back wall
    box(f"wing_{side}_back",
        wx_cen, wy_cen - WING_HD + WALL_T/2, WING_H/2 + 0.12,
        WING_HW, WALL_T/2, WING_H/2, brick)

    # Outer side wall (facing away from centre)
    sign = -1 if side == "L" else +1
    box(f"wing_{side}_outer",
        wx_cen + sign * (WING_HW - WALL_T/2), wy_cen, WING_H/2 + 0.12,
        WALL_T/2, WING_HD, WING_H/2, brick)

    # Inner side wall (facing the courtyard gap) — just a WALL_T thick face
    # The gap between wing inner edge and main block outer edge is open courtyard.
    inner_x = wx_cen - sign * (WING_HW - WALL_T/2)
    box(f"wing_{side}_inner",
        inner_x, wy_cen, WING_H/2 + 0.12,
        WALL_T/2, WING_HD, WING_H/2, brick)

    # Flat parapet cap
    WING_PARAPET = 0.45
    box(f"wing_{side}_par_front",
        wx_cen, wy_cen + WING_HD, WING_H + 0.12 + WING_PARAPET/2,
        WING_HW + 0.05, 0.10, WING_PARAPET/2, limestone)
    box(f"wing_{side}_par_back",
        wx_cen, wy_cen - WING_HD, WING_H + 0.12 + WING_PARAPET/2,
        WING_HW + 0.05, 0.10, WING_PARAPET/2, limestone)
    box(f"wing_{side}_par_outer",
        wx_cen + sign * WING_HW, wy_cen, WING_H + 0.12 + WING_PARAPET/2,
        0.10, WING_HD + 0.05, WING_PARAPET/2, limestone)
    box(f"wing_{side}_par_inner",
        inner_x, wy_cen, WING_H + 0.12 + WING_PARAPET/2,
        0.10, WING_HD + 0.05, WING_PARAPET/2, limestone)

    # Limestone trim band at sill and cornice on wings
    for band_z, lbl in [(0.95, "sill"), (4.5, "cor")]:
        # front + back bands
        box(f"wing_{side}_tb_{lbl}_f",
            wx_cen, wy_cen + WING_HD, band_z + 0.12,
            WING_HW + 0.05, 0.05, 0.09, limestone)
        box(f"wing_{side}_tb_{lbl}_b",
            wx_cen, wy_cen - WING_HD, band_z + 0.12,
            WING_HW + 0.05, 0.05, 0.09, limestone)
        box(f"wing_{side}_tb_{lbl}_o",
            wx_cen + sign * WING_HW, wy_cen, band_z + 0.12,
            0.05, WING_HD, 0.09, limestone)

    # Roof slab
    box(f"wing_{side}_roof",
        wx_cen, wy_cen, WING_H + 0.12 + WING_PARAPET/2,
        WING_HW, WING_HD, 0.12, limestone)

    # Window trim on wing front face (2 window bays)
    WIN_W = 1.8
    WIN_H = 2.0
    win_z = WING_H * 0.40 + 0.12
    for bay_i, bx_off in enumerate((-WING_HW * 0.45, WING_HW * 0.45)):
        box(f"wing_{side}_win_{bay_i}",
            wx_cen + bx_off, wy_cen + WING_HD,
            win_z,
            WIN_W/2 + 0.07, 0.06, WIN_H/2 + 0.07, limestone)

    # Window trim on back face (2 bays)
    for bay_i, bx_off in enumerate((-WING_HW * 0.45, WING_HW * 0.45)):
        box(f"wing_{side}_winB_{bay_i}",
            wx_cen + bx_off, wy_cen - WING_HD,
            win_z,
            WIN_W/2 + 0.07, 0.06, WIN_H/2 + 0.07, limestone)

# ════════════════════════════════════════════
# 5. CONNECTING WALL — low brick wall closing courtyard at front
# ════════════════════════════════════════════
# A low screen wall runs between the outer edge of each wing and the main
# entrance piers to hint at the courtyard enclosure.
SCREEN_H = 2.5
SCREEN_T = 0.25
# Gap between main building outer edge and wing inner edge on each side
# main outer edge X: ±MB_HW;  wing inner edge X: ±(MB_HW + WALL_T)
# So there's essentially no gap — wings abut main block.
# Instead: a low screen wall caps the courtyard at the front
# running from main building front face (Y=+MB_HD) at wing inner edge,
# and along front Y plane between blocks.
# Just do a pair of short pilasters flanking the arch on the entrance face
# as a symbolic entry marker at the transition to each wing.
for side_s, sx in (("L", -1), ("R", +1)):
    px = sx * (MB_HW + 0.20)
    box(f"entry_pilaster_{side_s}",
        px, MB_HD - WALL_T/2, SCREEN_H/2 + 0.18,
        0.22, 0.22, SCREEN_H/2, limestone)
    # Cap
    box(f"entry_pilaster_{side_s}_cap",
        px, MB_HD - WALL_T/2, SCREEN_H + 0.18 + 0.10,
        0.28, 0.28, 0.10, limestone)

# ════════════════════════════════════════════
# 6. MAIN BUILDING WINDOW TRIM
# ════════════════════════════════════════════
# Two windows flanking the arch on the front face
# Each window sits in the pier zone
WIN_ZOO_W = 1.6
WIN_ZOO_H = 2.2
WIN_ZOO_Z = MB_H * 0.38 + 0.18
for side_s, wx_off in (("l", -(ARCH_W/2 + PIER_W/2)), ("r", +(ARCH_W/2 + PIER_W/2))):
    box(f"main_win_front_{side_s}",
        wx_off, MB_HD,
        WIN_ZOO_Z,
        WIN_ZOO_W/2 + 0.07, 0.06, WIN_ZOO_H/2 + 0.07, limestone)

# Back face — 4 window surrounds
for i, bx_off in enumerate((-MB_HW*0.65, -MB_HW*0.25, MB_HW*0.25, MB_HW*0.65)):
    box(f"main_win_back_{i}",
        bx_off, -MB_HD,
        WIN_ZOO_Z,
        WIN_ZOO_W/2 + 0.07, 0.06, WIN_ZOO_H/2 + 0.07, limestone)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "CentralParkZoo"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_zoo.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB',
    use_selection=True, export_apply=True)
print(f"Exported Central Park Zoo to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")
