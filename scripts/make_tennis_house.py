"""Generate Tennis House for Central Park Walk.

The Tennis House (1930) is the headquarters building of the Central Park
Tennis Center, near 96th Street. Tudor Revival style with half-timber
upper walls, red brick lower level, and steep gable roof with cross-gable
over the arched main entrance.

Key features:
  - Rectangular building ~15m × 8m footprint
  - Tudor Revival: red brick ground floor, stucco + dark timber upper floor
  - 2 stories, ~7m to eave
  - Steep gable roof with slate tiles (~3.5m rise)
  - Cross-gable projecting from front face (entrance bay)
  - Arched main entrance in cross-gable
  - Multi-pane windows with timber surrounds
  - Horizontal + diagonal half-timber framing on upper floor
  - Brick chimney on rear slope

Origin at ground center.
Exports to models/furniture/cp_tennis_house.glb
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

brick   = make_mat("Brick",   (0.52, 0.28, 0.20), 0.88)
stucco  = make_mat("Stucco",  (0.78, 0.74, 0.68), 0.82)
timber  = make_mat("Timber",  (0.25, 0.18, 0.12), 0.80)
slate   = make_mat("Slate",   (0.32, 0.32, 0.34), 0.78)

# ── Building dimensions ──
W  = 15.0    # length along X axis
D  =  8.0    # depth along Y axis
H1 =  3.5    # ground floor height (brick)
H2 =  3.5    # upper floor height (stucco + timber)
H  = H1 + H2 # total wall height to eave = 7.0
RIDGE_H = 3.5 # main ridge above eave
WALL_T  = 0.35

hw = W / 2.0
hd = D / 2.0
eave_z = H
overhang = 0.40

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
# 1. FOUNDATION / PLINTH
# ════════════════════════════════════════════
box("foundation", 0, 0, -0.20, hw + 0.15, hd + 0.15, 0.25, brick)

# ════════════════════════════════════════════
# 2. GROUND FLOOR — red brick
# ════════════════════════════════════════════
# Front wall with entrance bay cutout (cross-gable projection handled later)
# For base brick: full solid ground floor walls
box("gf_front", 0, hd - WALL_T/2, H1/2, hw, WALL_T/2, H1/2, brick)
box("gf_back",  0, -hd + WALL_T/2, H1/2, hw, WALL_T/2, H1/2, brick)
box("gf_left",  -hw + WALL_T/2, 0, H1/2, WALL_T/2, hd, H1/2, brick)
box("gf_right",  hw - WALL_T/2, 0, H1/2, WALL_T/2, hd, H1/2, brick)

# Brick string course at floor transition
box("string_course", 0, 0, H1 + 0.06, hw + 0.04, hd + 0.04, 0.08, brick)

# ════════════════════════════════════════════
# 3. UPPER FLOOR — stucco panels
# ════════════════════════════════════════════
uf_base = H1
box("uf_front", 0, hd - WALL_T/2, uf_base + H2/2, hw, WALL_T/2, H2/2, stucco)
box("uf_back",  0, -hd + WALL_T/2, uf_base + H2/2, hw, WALL_T/2, H2/2, stucco)
box("uf_left",  -hw + WALL_T/2, 0, uf_base + H2/2, WALL_T/2, hd, H2/2, stucco)
box("uf_right",  hw - WALL_T/2, 0, uf_base + H2/2, WALL_T/2, hd, H2/2, stucco)

# ════════════════════════════════════════════
# 4. HALF-TIMBER FRAMING — upper floor
# ════════════════════════════════════════════
# Timber thickness (protrudes slightly from stucco face)
TT = 0.06   # timber strip thickness
TW = 0.12   # timber strip width (half-depth)
face_y_f = hd + TT / 2   # front face timber protrusion
face_y_b = -hd - TT / 2  # back face

# -- FRONT face timber framing --
# Horizontal rail at mid-height (Tudor band)
box("tf_front_mid",   0, face_y_f, uf_base + H2 * 0.50, hw, TT/2, TW/2, timber)
# Horizontal rail at top (eave plate)
box("tf_front_top",   0, face_y_f, uf_base + H2 - TW/2, hw, TT/2, TW/2, timber)
# Horizontal rail at bottom (sill plate)
box("tf_front_bot",   0, face_y_f, uf_base + TW/2,       hw, TT/2, TW/2, timber)
# Vertical corner studs
for cx in (-hw, hw):
    box(f"tf_front_corner_{cx}", cx, face_y_f, uf_base + H2/2, TW/2, TT/2, H2/2, timber)
# Vertical studs (evenly spaced, skip centre where cross-gable will be)
for stud_x in (-hw * 0.66, -hw * 0.33, hw * 0.33, hw * 0.66):
    box(f"tf_front_stud_{stud_x:.2f}", stud_x, face_y_f, uf_base + H2/2,
        TW/2, TT/2, H2/2, timber)
# Diagonal braces between studs (k-brace pattern, left panels)
for i, (x1, x2) in enumerate([(-hw, -hw * 0.66), (-hw * 0.66, -hw * 0.33),
                                ( hw * 0.33,  hw * 0.66), ( hw * 0.66,  hw)]):
    mx = (x1 + x2) / 2
    seg_len = abs(x2 - x1)
    diag_len = math.sqrt(seg_len**2 + (H2 * 0.5)**2)
    ang = math.atan2(H2 * 0.5, (x2 - x1))
    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(mx, face_y_f, uf_base + H2 * 0.25))
    d = bpy.context.active_object
    d.name = f"tf_front_diag_{i}"
    d.scale = (diag_len / 2, TT / 2, TW / 2)
    d.rotation_euler = (0, -ang, 0)
    d.data.materials.append(timber)
    all_parts.append(d)

# -- BACK face framing (simpler — 3 vertical studs + 2 horizontals) --
box("tf_back_top", 0, face_y_b, uf_base + H2 - TW/2, hw, TT/2, TW/2, timber)
box("tf_back_bot", 0, face_y_b, uf_base + TW/2,       hw, TT/2, TW/2, timber)
for cx in (-hw, 0, hw):
    box(f"tf_back_stud_{cx}", cx, face_y_b, uf_base + H2/2, TW/2, TT/2, H2/2, timber)

# -- SIDE faces: left & right (vertical studs + horizontal rails) --
for side_x, side_sign in ((-hw, -1), (hw, 1)):
    face_x = side_x - side_sign * TT / 2
    box(f"tf_side_{side_sign}_top", face_x, 0, uf_base + H2 - TW/2, TT/2, hd, TW/2, timber)
    box(f"tf_side_{side_sign}_bot", face_x, 0, uf_base + TW/2,       TT/2, hd, TW/2, timber)
    box(f"tf_side_{side_sign}_mid", face_x, 0, uf_base + H2 * 0.50,  TT/2, hd, TW/2, timber)
    for wy in (-hd * 0.55, 0, hd * 0.55):
        box(f"tf_side_{side_sign}_stud_{wy:.2f}", face_x, wy, uf_base + H2/2,
            TT/2, TW/2, H2/2, timber)

# ════════════════════════════════════════════
# 5. MAIN GABLE ROOF — steep Tudor pitch
# ════════════════════════════════════════════
# Ridge runs along X (long axis); front/back slopes face ±Y
rv = [
    (-hw - overhang, -hd - overhang, eave_z),      # 0 back-left eave
    ( hw + overhang, -hd - overhang, eave_z),      # 1 back-right eave
    ( hw + overhang,  hd + overhang, eave_z),      # 2 front-right eave
    (-hw - overhang,  hd + overhang, eave_z),      # 3 front-left eave
    (-hw - overhang, 0, eave_z + RIDGE_H),          # 4 ridge west end
    ( hw + overhang, 0, eave_z + RIDGE_H),          # 5 ridge east end
]
rf = [
    (0, 1, 5, 4),  # back slope
    (2, 3, 4, 5),  # front slope
    (3, 0, 4),     # west gable
    (1, 2, 5),     # east gable
    (0, 3, 2, 1),  # soffit
]
rmesh = bpy.data.meshes.new("roof_mesh")
rmesh.from_pydata(rv, [], rf)
rmesh.update()
robj = bpy.data.objects.new("MainRoof", rmesh)
bpy.context.collection.objects.link(robj)
robj.data.materials.append(slate)
all_parts.append(robj)

# Ridge board
box("ridge_board", 0, 0, eave_z + RIDGE_H + 0.05, hw + overhang, 0.05, 0.07, timber)

# Gable triangles (stucco + timber infill above eave on end walls)
for side_x, sign in ((-1, -1), (1, 1)):
    gx = sign * hw
    gv = [
        (gx, -(hd - WALL_T), eave_z),
        (gx, +(hd - WALL_T), eave_z),
        (gx,  0,              eave_z + RIDGE_H - 0.1),
    ]
    gf_w = [(0, 2, 1)] if sign < 0 else [(0, 1, 2)]
    gm = bpy.data.meshes.new(f"gable_end_{side_x}")
    gm.from_pydata(gv, [], gf_w)
    gm.update()
    go = bpy.data.objects.new(f"GableEnd_{side_x}", gm)
    bpy.context.collection.objects.link(go)
    go.data.materials.append(stucco)
    all_parts.append(go)
    # Timber diagonal on gable end
    mid_z = eave_z + RIDGE_H * 0.5
    for brace_y in (-hd * 0.45, hd * 0.45):
        brace_len = math.sqrt((hd - WALL_T - abs(brace_y))**2 + (RIDGE_H * 0.5)**2)
        brace_ang = math.atan2(RIDGE_H * 0.5, (hd - WALL_T - abs(brace_y)))
        side_mul = 1.0 if brace_y > 0 else -1.0
        bpy.ops.mesh.primitive_cube_add(size=1.0,
            location=(gx, brace_y * 0.5, eave_z + RIDGE_H * 0.25))
        br = bpy.context.active_object
        br.name = f"gable_brace_{side_x}_{brace_y:.2f}"
        br.scale = (TT / 2, brace_len / 2, TW / 2)
        br.rotation_euler = (side_mul * brace_ang, 0, 0)
        br.data.materials.append(timber)
        all_parts.append(br)

# ════════════════════════════════════════════
# 6. CROSS-GABLE — front entrance projection
# ════════════════════════════════════════════
# The cross-gable projects from the centre of the front (Y+) face
CG_W  = 4.5   # cross-gable width (X)
CG_D  = 1.2   # projection depth (Y) beyond main front wall
CG_H  = H     # same eave height as main building
CG_RH = 3.0   # cross-gable ridge rise above eave

cg_hw = CG_W / 2
# Project front wall face
cg_front_y = hd + CG_D

# Cross-gable walls (brick ground floor, stucco upper — same as main body)
# Ground floor projecting walls
box("cg_front_gf", 0, cg_front_y - WALL_T/2, H1/2, cg_hw, WALL_T/2, H1/2, brick)
box("cg_left_gf",  -cg_hw + WALL_T/2, hd + CG_D/2, H1/2, WALL_T/2, CG_D/2, H1/2, brick)
box("cg_right_gf",  cg_hw - WALL_T/2, hd + CG_D/2, H1/2, WALL_T/2, CG_D/2, H1/2, brick)

# Upper floor projection
box("cg_front_uf", 0, cg_front_y - WALL_T/2, uf_base + H2/2, cg_hw, WALL_T/2, H2/2, stucco)
box("cg_left_uf",  -cg_hw + WALL_T/2, hd + CG_D/2, uf_base + H2/2, WALL_T/2, CG_D/2, H2/2, stucco)
box("cg_right_uf",  cg_hw - WALL_T/2, hd + CG_D/2, uf_base + H2/2, WALL_T/2, CG_D/2, H2/2, stucco)

# Cross-gable timber framing on front face
box("cg_tf_top", 0, cg_front_y, uf_base + H2 - TW/2, cg_hw, TT/2, TW/2, timber)
box("cg_tf_bot", 0, cg_front_y, uf_base + TW/2,       cg_hw, TT/2, TW/2, timber)
for cx in (-cg_hw, 0, cg_hw):
    box(f"cg_tf_stud_{cx}", cx, cg_front_y, uf_base + H2/2, TW/2, TT/2, H2/2, timber)
# Diagonal k-braces on cross-gable upper face
for i, (x1, x2) in enumerate([(-cg_hw, 0), (0, cg_hw)]):
    mx = (x1 + x2) / 2
    seg_len = abs(x2 - x1)
    diag_len = math.sqrt(seg_len**2 + (H2 * 0.5)**2)
    ang = math.atan2(H2 * 0.5, (x2 - x1))
    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(mx, cg_front_y, uf_base + H2 * 0.25))
    d = bpy.context.active_object
    d.name = f"cg_tf_diag_{i}"
    d.scale = (diag_len / 2, TT / 2, TW / 2)
    d.rotation_euler = (0, -ang, 0)
    d.data.materials.append(timber)
    all_parts.append(d)

# Cross-gable roof (ridge perpendicular to main ridge — runs Y)
cg_eave_z = eave_z
cg_ridge_y = cg_front_y  # apex lines up with front face
cg_overhang = 0.30
cgv = [
    (-cg_hw - cg_overhang, hd - cg_overhang,          cg_eave_z),  # 0 inner-left
    ( cg_hw + cg_overhang, hd - cg_overhang,          cg_eave_z),  # 1 inner-right
    ( cg_hw + cg_overhang, cg_front_y + cg_overhang,  cg_eave_z),  # 2 outer-right
    (-cg_hw - cg_overhang, cg_front_y + cg_overhang,  cg_eave_z),  # 3 outer-left
    (0, hd - cg_overhang,         cg_eave_z + CG_RH),               # 4 ridge inner
    (0, cg_front_y + cg_overhang, cg_eave_z + CG_RH),               # 5 ridge outer
]
cgf = [
    (3, 2, 1, 0),  # soffit
    (3, 0, 4, 5),  # left slope
    (1, 2, 5, 4),  # right slope
    (0, 1, 4),     # inner gable
    (2, 3, 5),     # outer gable (front face)
]
cgm = bpy.data.meshes.new("cross_gable_roof")
cgm.from_pydata(cgv, [], cgf)
cgm.update()
cgo = bpy.data.objects.new("CrossGableRoof", cgm)
bpy.context.collection.objects.link(cgo)
cgo.data.materials.append(slate)
all_parts.append(cgo)

# Cross-gable stucco triangle (front face gable above eave)
cgtriv = [
    (-cg_hw + WALL_T, cg_front_y - WALL_T, cg_eave_z),
    ( cg_hw - WALL_T, cg_front_y - WALL_T, cg_eave_z),
    (0,               cg_front_y - WALL_T, cg_eave_z + CG_RH - 0.1),
]
cgtrim = bpy.data.meshes.new("cg_gable_tri")
cgtrim.from_pydata(cgtriv, [], [(0, 2, 1)])
cgtrim.update()
cgtrio = bpy.data.objects.new("CGGableTri", cgtrim)
bpy.context.collection.objects.link(cgtrio)
cgtrio.data.materials.append(stucco)
all_parts.append(cgtrio)

# Cross-gable ridge board
box("cg_ridge_board", 0, (hd + cg_front_y) / 2,
    cg_eave_z + CG_RH + 0.05, 0.05, CG_D / 2 + cg_overhang, 0.07, timber)

# ════════════════════════════════════════════
# 7. ARCHED MAIN ENTRANCE — in the cross-gable
# ════════════════════════════════════════════
# Arch represented as brick jambs + semicircular arch voussoirs (box slices)
ARCH_W = 1.8    # opening width
ARCH_H = 2.4    # doorway clear height (bottom of arch)
ARCH_R = ARCH_W / 2  # arch radius
N_ARCH = 8      # arch segments
arch_y = cg_front_y - WALL_T * 0.5  # at front face of cross-gable

# Left jamb
box("arch_jamb_l", -ARCH_W/2 - 0.18, arch_y, ARCH_H/2,
    0.20, 0.20, ARCH_H/2, brick)
# Right jamb
box("arch_jamb_r",  ARCH_W/2 + 0.18, arch_y, ARCH_H/2,
    0.20, 0.20, ARCH_H/2, brick)
# Flat head / impost under arch
box("arch_impost", 0, arch_y, ARCH_H + 0.08, ARCH_W/2 + 0.28, 0.18, 0.10, brick)

# Semicircular arch — box slices
arch_center_z = ARCH_H + ARCH_R
for i in range(N_ARCH):
    a1 = math.pi * i / N_ARCH
    a2 = math.pi * (i + 1) / N_ARCH
    am = (a1 + a2) / 2
    # Voussoir centre
    vx = math.cos(math.pi - am) * (ARCH_R + 0.10)
    vz = arch_center_z + math.sin(am) * (ARCH_R + 0.10)
    vlen = math.pi * (ARCH_R + 0.10) / N_ARCH + 0.04
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(vx, arch_y, vz))
    v = bpy.context.active_object
    v.name = f"arch_voussoir_{i}"
    v.scale = (vlen / 2, 0.18, 0.14)
    v.rotation_euler = (0, am - math.pi / 2, 0)
    v.data.materials.append(brick)
    all_parts.append(v)

# ════════════════════════════════════════════
# 8. WINDOWS — multi-pane, on both floors
# ════════════════════════════════════════════
# Window frame helper
def window(name_prefix, wx, wy, wz, win_w, win_h, face_axis='y'):
    """Place window frame at (wx, wy, wz) on a wall face.
    face_axis: 'y' for front/back walls, 'x' for side walls.
    """
    tt = 0.06
    if face_axis == 'y':
        # Top rail
        box(f"{name_prefix}_t",  wx, wy, wz + win_h/2 + tt/2, win_w/2 + tt, tt/2, tt/2, timber)
        # Bottom rail
        box(f"{name_prefix}_b",  wx, wy, wz - win_h/2 - tt/2, win_w/2 + tt, tt/2, tt/2, timber)
        # Left stile
        box(f"{name_prefix}_l",  wx - win_w/2 - tt/2, wy, wz, tt/2, tt/2, win_h/2 + tt, timber)
        # Right stile
        box(f"{name_prefix}_r",  wx + win_w/2 + tt/2, wy, wz, tt/2, tt/2, win_h/2 + tt, timber)
        # Mid muntin (vertical)
        box(f"{name_prefix}_mv", wx, wy, wz, tt/4, tt/2, win_h/2, timber)
        # Mid muntin (horizontal)
        box(f"{name_prefix}_mh", wx, wy, wz, win_w/2, tt/2, tt/4, timber)
    else:  # face_axis == 'x'
        box(f"{name_prefix}_t",  wx, wy, wz + win_h/2 + tt/2, tt/2, win_w/2 + tt, tt/2, timber)
        box(f"{name_prefix}_b",  wx, wy, wz - win_h/2 - tt/2, tt/2, win_w/2 + tt, tt/2, timber)
        box(f"{name_prefix}_l",  wx, wy - win_w/2 - tt/2, wz, tt/2, tt/2, win_h/2 + tt, timber)
        box(f"{name_prefix}_r",  wx, wy + win_w/2 + tt/2, wz, tt/2, tt/2, win_h/2 + tt, timber)
        box(f"{name_prefix}_mv", wx, wy, wz, tt/2, tt/4, win_h/2, timber)
        box(f"{name_prefix}_mh", wx, wy, wz, tt/2, win_w/2, tt/4, timber)

# Ground floor windows (brick) — front + back, tall arched-head style
# Simulated with slightly taller proportions
GF_WIN_W = 0.90
GF_WIN_H = 1.60
gf_win_z = H1 * 0.50  # centred on ground floor

fy = hd  # front face
by = -hd
for wx in (-hw * 0.58, -hw * 0.20, hw * 0.20, hw * 0.58):
    if abs(wx) < cg_hw + 0.5:
        continue  # skip cross-gable zone on front
    window(f"win_gf_f_{wx:.2f}", wx, fy, gf_win_z, GF_WIN_W, GF_WIN_H, 'y')
    window(f"win_gf_b_{wx:.2f}", wx, by, gf_win_z, GF_WIN_W, GF_WIN_H, 'y')

# Upper floor windows (stucco zone) — front + back
UF_WIN_W = 0.85
UF_WIN_H = 1.30
uf_win_z = H1 + H2 * 0.50  # centred on upper floor

for wx in (-hw * 0.60, -hw * 0.25, hw * 0.25, hw * 0.60):
    window(f"win_uf_f_{wx:.2f}", wx, fy, uf_win_z, UF_WIN_W, UF_WIN_H, 'y')
    window(f"win_uf_b_{wx:.2f}", wx, by, uf_win_z, UF_WIN_W, UF_WIN_H, 'y')

# Side wall windows (ground floor — 2 per side, upper floor — 2 per side)
lx = -hw
rx =  hw
for wy in (-hd * 0.40, hd * 0.40):
    window(f"win_gf_l_{wy:.2f}", lx, wy, gf_win_z, GF_WIN_W, GF_WIN_H, 'x')
    window(f"win_gf_r_{wy:.2f}", rx, wy, gf_win_z, GF_WIN_W, GF_WIN_H, 'x')
    window(f"win_uf_l_{wy:.2f}", lx, wy, uf_win_z, UF_WIN_W, UF_WIN_H, 'x')
    window(f"win_uf_r_{wy:.2f}", rx, wy, uf_win_z, UF_WIN_W, UF_WIN_H, 'x')

# Cross-gable upper window (above arch, in gable triangle)
window("win_cg_upper", 0, cg_front_y, uf_win_z, 1.0, 1.0, 'y')

# ════════════════════════════════════════════
# 9. CHIMNEY — brick, on back slope near east end
# ════════════════════════════════════════════
# Chimney base is behind the main ridge on the back slope
CHM_X = hw * 0.55   # east side
CHM_W = 0.55
CHM_D = 0.50
# Chimney emerges from roof; base at eave level, top above ridge
CHM_BOT = H1 + 0.5  # starts inside building
CHM_TOP = eave_z + RIDGE_H + 1.2  # above ridge
box("chimney_stack", CHM_X, -0.15, (CHM_BOT + CHM_TOP) / 2,
    CHM_W/2, CHM_D/2, (CHM_TOP - CHM_BOT) / 2, brick)
# Chimney cap
box("chimney_cap", CHM_X, -0.15, CHM_TOP + 0.10,
    CHM_W/2 + 0.08, CHM_D/2 + 0.08, 0.10, slate)
# Pots (two cylinders)
for px_off in (-0.10, 0.10):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.06, depth=0.35, vertices=8,
        location=(CHM_X + px_off, -0.15, CHM_TOP + 0.38))
    pot = bpy.context.active_object
    pot.name = f"chimney_pot_{px_off}"
    pot.data.materials.append(brick)
    all_parts.append(pot)

# ════════════════════════════════════════════
# 10. EAVE DETAILS
# ════════════════════════════════════════════
# Fascia boards along eave
box("fascia_front", 0, hd + overhang + 0.03, eave_z - 0.08,
    hw + overhang, 0.05, 0.10, timber)
box("fascia_back",  0, -hd - overhang - 0.03, eave_z - 0.08,
    hw + overhang, 0.05, 0.10, timber)
box("fascia_left",  -hw - overhang - 0.03, 0, eave_z - 0.08,
    0.05, hd + overhang, 0.10, timber)
box("fascia_right",  hw + overhang + 0.03, 0, eave_z - 0.08,
    0.05, hd + overhang, 0.10, timber)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "TennisHouse"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_tennis_house.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Tennis House to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")
