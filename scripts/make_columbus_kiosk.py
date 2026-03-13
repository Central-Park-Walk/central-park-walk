"""Generate Columbus Circle Information Kiosk for Central Park Walk.

The Columbus Circle Information Kiosk sits at the southwest entrance
to Central Park (59th St & Central Park West/8th Ave). It is a small
modern octagonal booth staffed by park rangers and volunteers, with
large glass information panels on most sides, a shallow conical
patinated-copper roof, and a stone/concrete base.

Key features:
  - Small octagonal structure, ~3m outer radius (hexagonal footprint ~3m dia)
  - ~3m wall height (floor to eave)
  - Glass panels with dark metal frames on all 8 sides
  - Shallow conical copper-green roof with narrow overhang
  - Slender metal finial
  - Stone/concrete octagonal plinth base (~0.3m step up)

Origin at ground center.
Exports to models/furniture/cp_columbus_kiosk.glb
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

concrete = make_mat("Concrete", (0.58, 0.55, 0.52), roughness=0.85)
glass    = make_mat("Glass",    (0.25, 0.30, 0.35), roughness=0.15, metallic=0.1)
copper   = make_mat("Copper",   (0.30, 0.48, 0.38), roughness=0.60, metallic=0.3)
frame    = make_mat("Frame",    (0.20, 0.20, 0.19), roughness=0.50, metallic=0.3)

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
N       = 8          # octagon
R       = 1.50       # outer wall radius (centre to face midpoint) → ~3m diameter
WALL_T  = 0.06       # thin glass-wall assembly thickness
H       = 3.00       # wall height (floor to eave)
BASE_H  = 0.30       # concrete plinth height
BASE_R  = R + 0.18   # plinth slightly proud of walls
ROOF_H  = 0.55       # conical roof rise (shallow)
OVERHANG = 0.20      # roof overhang beyond walls
FRAME_W = 0.06       # frame mullion half-width

# Pre-compute octagon face centres and segment lengths
faces = []      # (cx, cy, angle_of_outward_normal, face_halflen, tangent_angle)
for i in range(N):
    a1 = 2 * math.pi * i / N       # angle to corner i
    a2 = 2 * math.pi * (i + 1) / N
    # Corner positions
    x1 = math.cos(a1) * R / math.cos(math.pi / N)
    y1 = math.sin(a1) * R / math.cos(math.pi / N)
    x2 = math.cos(a2) * R / math.cos(math.pi / N)
    y2 = math.sin(a2) * R / math.cos(math.pi / N)
    # Face midpoint (at radius R from centre for regular octagon)
    am = (a1 + a2) / 2.0
    mx = math.cos(am) * R
    my = math.sin(am) * R
    # Segment half-length
    seg_half = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2.0
    # Tangent angle for box rotation (perpendicular to outward normal)
    tang = math.atan2(y2 - y1, x2 - x1)
    faces.append((mx, my, am, seg_half, tang))

# ════════════════════════════════════════════
# 1. CONCRETE OCTAGONAL PLINTH
# ════════════════════════════════════════════
# Approximate octagonal plinth as a single octagonal cylinder
bpy.ops.mesh.primitive_cylinder_add(
    radius=BASE_R, depth=BASE_H, vertices=N,
    location=(0, 0, BASE_H / 2))
plinth = bpy.context.active_object
plinth.name = "Plinth"
# Align flat face toward +Y (default cylinder has points at vertices; rotate so
# faces align with walls below)
plinth.rotation_euler = (0, 0, math.pi / N)
plinth.data.materials.append(concrete)
all_parts.append(plinth)

# Low step lip at edge
bpy.ops.mesh.primitive_cylinder_add(
    radius=BASE_R + 0.06, depth=0.06, vertices=N,
    location=(0, 0, 0.03))
lip = bpy.context.active_object
lip.name = "PlinthLip"
lip.rotation_euler = (0, 0, math.pi / N)
lip.data.materials.append(concrete)
all_parts.append(lip)

FLOOR_Z = BASE_H   # walls begin here

# ════════════════════════════════════════════
# 2. GLASS WALL PANELS WITH METAL FRAMES
# ════════════════════════════════════════════
# For each of the 8 faces:
#   - outer dark frame (full-height box, slightly proud)
#   - glass panel (recessed slightly inside frame)
#   - horizontal top + bottom rails
#   - two vertical mullions (left & right edge of glass)

GLASS_W   = 0.72   # half-width of glass insert (relative to face half-len minus mullions)
GLASS_H   = H - 0.22  # glass height (inset above sill, below top rail)
GLASS_Z   = FLOOR_Z + 0.12 + GLASS_H / 2  # glass centre Z

for i, (mx, my, norm_a, seg_half, tang) in enumerate(faces):
    # ── Outer frame surround (full segment width, full wall height) ──
    # Placed at radius R, rotated to face outward
    frame_cx = mx
    frame_cy = my
    frame_cz = FLOOR_Z + H / 2

    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(frame_cx, frame_cy, frame_cz))
    frm = bpy.context.active_object
    frm.name = f"frame_{i}"
    frm.scale = (seg_half, WALL_T + 0.015, H / 2)
    frm.rotation_euler = (0, 0, tang)
    frm.data.materials.append(frame)
    all_parts.append(frm)

    # ── Glass panel (slightly inside face, thinner) ──
    # Inset toward centre by a small amount
    inset = 0.008
    gx = mx - math.cos(norm_a) * inset
    gy = my - math.sin(norm_a) * inset

    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(gx, gy, GLASS_Z))
    gl = bpy.context.active_object
    gl.name = f"glass_{i}"
    gl.scale = (seg_half - FRAME_W, WALL_T * 0.6, GLASS_H / 2)
    gl.rotation_euler = (0, 0, tang)
    gl.data.materials.append(glass)
    all_parts.append(gl)

    # ── Horizontal bottom rail (sill) ──
    sill_z = FLOOR_Z + 0.06
    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(frame_cx, frame_cy, sill_z))
    sill = bpy.context.active_object
    sill.name = f"sill_{i}"
    sill.scale = (seg_half + 0.01, WALL_T + 0.02, 0.05)
    sill.rotation_euler = (0, 0, tang)
    sill.data.materials.append(frame)
    all_parts.append(sill)

    # ── Horizontal top rail ──
    top_rail_z = FLOOR_Z + H - 0.06
    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(frame_cx, frame_cy, top_rail_z))
    topr = bpy.context.active_object
    topr.name = f"top_rail_{i}"
    topr.scale = (seg_half + 0.01, WALL_T + 0.02, 0.05)
    topr.rotation_euler = (0, 0, tang)
    topr.data.materials.append(frame)
    all_parts.append(topr)

    # ── Left & right vertical edge mullions ──
    # In local face space: offset by ±(seg_half - FRAME_W/2) along tangent
    t_dx = math.cos(tang)
    t_dy = math.sin(tang)
    for side in (-1, 1):
        ox = frame_cx + side * (seg_half - FRAME_W / 2) * t_dx
        oy = frame_cy + side * (seg_half - FRAME_W / 2) * t_dy
        bpy.ops.mesh.primitive_cube_add(size=1.0,
            location=(ox, oy, frame_cz))
        mul = bpy.context.active_object
        mul.name = f"mullion_{i}_{side}"
        mul.scale = (FRAME_W / 2, WALL_T + 0.02, H / 2)
        mul.rotation_euler = (0, 0, tang)
        mul.data.materials.append(frame)
        all_parts.append(mul)

# ════════════════════════════════════════════
# 3. EAVE BAND — thin concrete/frame ring at top of walls
# ════════════════════════════════════════════
bpy.ops.mesh.primitive_cylinder_add(
    radius=R + 0.05, depth=0.10, vertices=N,
    location=(0, 0, FLOOR_Z + H + 0.05))
eave = bpy.context.active_object
eave.name = "EaveBand"
eave.rotation_euler = (0, 0, math.pi / N)
eave.data.materials.append(frame)
all_parts.append(eave)

# ════════════════════════════════════════════
# 4. SHALLOW CONICAL COPPER ROOF
# ════════════════════════════════════════════
ROOF_BASE_Z = FLOOR_Z + H + 0.08
roof_r = R + OVERHANG

# Build roof as custom mesh (octagonal cone)
rv = []
for i in range(N):
    a = 2 * math.pi * i / N + math.pi / N  # align with face midpoints
    rv.append((math.cos(a) * roof_r, math.sin(a) * roof_r, ROOF_BASE_Z))
rv.append((0, 0, ROOF_BASE_Z + ROOF_H))   # apex = index N

rf = []
for i in range(N):
    rf.append((i, (i + 1) % N, N))         # side triangles
rf.append(list(range(N - 1, -1, -1)))      # bottom cap (reversed for outward normal)

rm = bpy.data.meshes.new("roof_mesh")
rm.from_pydata(rv, [], rf)
rm.update()
ro = bpy.data.objects.new("ConicalRoof", rm)
bpy.context.collection.objects.link(ro)
ro.data.materials.append(copper)
all_parts.append(ro)

# ════════════════════════════════════════════
# 5. ROOF EDGE TRIM — thin frame ring at roof perimeter
# ════════════════════════════════════════════
bpy.ops.mesh.primitive_cylinder_add(
    radius=roof_r + 0.02, depth=0.05, vertices=N,
    location=(0, 0, ROOF_BASE_Z + 0.025))
edge_trim = bpy.context.active_object
edge_trim.name = "RoofEdgeTrim"
edge_trim.rotation_euler = (0, 0, math.pi / N)
edge_trim.data.materials.append(frame)
all_parts.append(edge_trim)

# ════════════════════════════════════════════
# 6. FINIAL
# ════════════════════════════════════════════
apex_z = ROOF_BASE_Z + ROOF_H

# Finial shaft
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.025, depth=0.50, vertices=6,
    location=(0, 0, apex_z + 0.25))
fin_shaft = bpy.context.active_object
fin_shaft.name = "FinialShaft"
fin_shaft.data.materials.append(frame)
all_parts.append(fin_shaft)

# Finial ball
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=0.05, segments=8, ring_count=6,
    location=(0, 0, apex_z + 0.52))
fin_ball = bpy.context.active_object
fin_ball.name = "FinialBall"
fin_ball.data.materials.append(copper)
all_parts.append(fin_ball)

# Finial tip spike
bpy.ops.mesh.primitive_cone_add(
    radius1=0.02, radius2=0.0, depth=0.18, vertices=6,
    location=(0, 0, apex_z + 0.66))
fin_tip = bpy.context.active_object
fin_tip.name = "FinialTip"
fin_tip.data.materials.append(frame)
all_parts.append(fin_tip)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "ColumbusCircleKiosk"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_columbus_kiosk.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Columbus Circle Kiosk to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")
