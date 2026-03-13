"""Generate Cherry Hill Fountain for Central Park Walk.

The Cherry Hill Fountain (1860s, Calvert Vaux) is a Victorian ornamental
fountain at Cherry Hill, originally designed as a watering trough for
carriage horses. One of Central Park's most elegant small monuments.

Key features:
  - Circular stone paved pad (~6m diameter, raised ~0.05m)
  - Octagonal stone basin at ground level (~4m diameter, ~0.5m tall)
  - Wide basin rim / lip (molded stone edge)
  - Central pedestal column (~0.4m diameter, ~2m tall) rising from basin
  - Decorative collar rings on pedestal
  - Upper bowl / receiver basin (~1.5m diameter, ~0.3m deep) on pedestal
  - Upper rim molding
  - Decorative urn / finial on top (~0.8m total height)
    — lower urn belly, neck, cap disc
  - Total height ~3.5m
  - Stone body, bronze-patinated iron decorative elements

Origin at ground center.
Exports to models/furniture/cp_cherry_hill_fountain.glb
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

stone  = make_mat("Stone",  (0.58, 0.55, 0.50), roughness=0.82)
bronze = make_mat("Bronze", (0.30, 0.35, 0.25), roughness=0.60, metallic=0.5)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Add a box centred at (cx,cy,cz) with half-extents (hx,hy,hz)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cylinder(name, cx, cy, cz_base, r, h, mat, segs=16):
    """Add a cylinder with its base at cz_base, top at cz_base+h."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=h, vertices=segs,
        location=(cx, cy, cz_base + h / 2))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cone(name, cx, cy, cz_base, r_bot, r_top, h, mat, segs=16):
    """Add a truncated cone (cylinder with scale taper) base at cz_base."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r_bot, depth=h, vertices=segs,
        location=(cx, cy, cz_base + h / 2))
    o = bpy.context.active_object
    o.name = name
    # Taper top vertices by scaling XY proportionally with Z
    mesh = o.data
    half_h = h / 2.0
    scale_ratio = r_top / r_bot
    for v in mesh.vertices:
        t = (v.co.z + half_h) / h          # 0 at bottom, 1 at top
        t = max(0.0, min(1.0, t))
        s = 1.0 + t * (scale_ratio - 1.0)
        v.co.x *= s
        v.co.y *= s
    mesh.update()
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ════════════════════════════════════════════
# DIMENSIONS
# ════════════════════════════════════════════
PAD_R       = 3.10   # circular stone pad radius
PAD_H       = 0.06   # pad height above grade

BASIN_R     = 2.05   # octagonal lower basin outer radius (vertex-to-center)
BASIN_H     = 0.50   # basin wall height (from pad top)
BASIN_T     = 0.18   # basin wall thickness
RIM_H       = 0.08   # top rim overhang thickness

PED_R       = 0.20   # pedestal radius
PED_BASE_R  = 0.32   # pedestal base plinth radius
PED_BASE_H  = 0.18   # pedestal base plinth height
PED_H       = 1.78   # pedestal shaft height (above plinth)

COLLAR_R    = 0.28   # decorative collar ring radius
COLLAR_H    = 0.07   # collar height

UPPER_R     = 0.76   # upper bowl outer radius
UPPER_H     = 0.30   # upper bowl depth
UPPER_T     = 0.10   # upper bowl wall thickness

URN_BELLY_R = 0.22   # urn belly radius
URN_BELLY_H = 0.30   # urn belly height
URN_NECK_R  = 0.10   # urn neck radius
URN_NECK_H  = 0.18   # urn neck height
URN_CAP_R   = 0.18   # urn cap disc radius
URN_CAP_H   = 0.06   # urn cap height
URN_SPIKE_R = 0.04   # thin spike / tip radius
URN_SPIKE_H = 0.18   # spike height

# Accumulated Z positions (all from ground = 0)
z0 = 0.0
z_pad_top    = PAD_H
z_basin_bot  = z_pad_top
z_basin_top  = z_basin_bot + BASIN_H
z_ped_base   = z_basin_top + 0.02    # plinth sits slightly inside basin on center
z_ped_shaft  = z_ped_base + PED_BASE_H
z_collar1    = z_ped_shaft + PED_H * 0.30
z_collar2    = z_ped_shaft + PED_H * 0.65
z_ped_top    = z_ped_shaft + PED_H
z_cap_ring   = z_ped_top              # transition ring under upper bowl
z_upper_bot  = z_ped_top + 0.06
z_upper_top  = z_upper_bot + UPPER_H
z_urn_bot    = z_upper_top + 0.04
z_urn_belly  = z_urn_bot
z_urn_neck   = z_urn_belly + URN_BELLY_H
z_urn_cap    = z_urn_neck + URN_NECK_H
z_spike      = z_urn_cap + URN_CAP_H

# ════════════════════════════════════════════
# 1. CIRCULAR STONE PAD
# ════════════════════════════════════════════
# Low circular platform of dressed stone
bpy.ops.mesh.primitive_cylinder_add(
    radius=PAD_R, depth=PAD_H, vertices=32,
    location=(0, 0, PAD_H / 2))
pad = bpy.context.active_object
pad.name = "pad"
pad.data.materials.append(stone)
all_parts.append(pad)

# Slight step / edge chamfer implied by a thin outer ring
bpy.ops.mesh.primitive_cylinder_add(
    radius=PAD_R + 0.04, depth=PAD_H * 0.40, vertices=32,
    location=(0, 0, PAD_H * 0.20))
pad_edge = bpy.context.active_object
pad_edge.name = "pad_edge"
pad_edge.data.materials.append(stone)
all_parts.append(pad_edge)

# ════════════════════════════════════════════
# 2. OCTAGONAL LOWER BASIN
# ════════════════════════════════════════════
# Outer basin wall — 8-sided cylinder (full height)
bpy.ops.mesh.primitive_cylinder_add(
    radius=BASIN_R, depth=BASIN_H, vertices=8,
    location=(0, 0, z_basin_bot + BASIN_H / 2))
basin_outer = bpy.context.active_object
basin_outer.name = "basin_outer"
basin_outer.data.materials.append(stone)
all_parts.append(basin_outer)

# Inner basin wall — slightly smaller 8-sided cylinder (hollow appearance)
basin_inner_r = BASIN_R - BASIN_T
basin_floor_h = 0.08
bpy.ops.mesh.primitive_cylinder_add(
    radius=basin_inner_r, depth=BASIN_H - basin_floor_h, vertices=8,
    location=(0, 0, z_basin_bot + basin_floor_h + (BASIN_H - basin_floor_h) / 2))
basin_inner = bpy.context.active_object
basin_inner.name = "basin_inner"
# Use same stone material — inner cavity is a recessed dark layer
basin_inner.data.materials.append(stone)
all_parts.append(basin_inner)

# Basin floor (solid disc inside)
bpy.ops.mesh.primitive_cylinder_add(
    radius=basin_inner_r - 0.02, depth=basin_floor_h, vertices=16,
    location=(0, 0, z_basin_bot + basin_floor_h / 2))
basin_floor = bpy.context.active_object
basin_floor.name = "basin_floor"
basin_floor.data.materials.append(stone)
all_parts.append(basin_floor)

# Top rim molding — wider disc overhanging basin top
bpy.ops.mesh.primitive_cylinder_add(
    radius=BASIN_R + 0.06, depth=RIM_H, vertices=8,
    location=(0, 0, z_basin_top + RIM_H / 2))
basin_rim = bpy.context.active_object
basin_rim.name = "basin_rim"
basin_rim.data.materials.append(stone)
all_parts.append(basin_rim)

# Under-rim soffit step
bpy.ops.mesh.primitive_cylinder_add(
    radius=BASIN_R + 0.02, depth=RIM_H * 0.5, vertices=8,
    location=(0, 0, z_basin_top - RIM_H * 0.25))
basin_rim_soffit = bpy.context.active_object
basin_rim_soffit.name = "basin_rim_soffit"
basin_rim_soffit.data.materials.append(stone)
all_parts.append(basin_rim_soffit)

# ════════════════════════════════════════════
# 3. CENTRAL PEDESTAL
# ════════════════════════════════════════════
# Square/round plinth at pedestal base (sits inside basin)
bpy.ops.mesh.primitive_cylinder_add(
    radius=PED_BASE_R, depth=PED_BASE_H, vertices=8,
    location=(0, 0, z_ped_base + PED_BASE_H / 2))
ped_base = bpy.context.active_object
ped_base.name = "ped_base"
ped_base.data.materials.append(stone)
all_parts.append(ped_base)

# Pedestal shaft — slightly tapered column
cone("ped_shaft", 0, 0, z_ped_shaft,
     r_bot=PED_R + 0.02, r_top=PED_R - 0.01, h=PED_H, mat=stone, segs=16)

# Decorative collar ring 1 (lower third)
bpy.ops.mesh.primitive_cylinder_add(
    radius=COLLAR_R, depth=COLLAR_H, vertices=16,
    location=(0, 0, z_collar1 + COLLAR_H / 2))
collar1 = bpy.context.active_object
collar1.name = "collar1"
collar1.data.materials.append(bronze)
all_parts.append(collar1)

# Collar fillet under ring 1
bpy.ops.mesh.primitive_cylinder_add(
    radius=COLLAR_R - 0.02, depth=COLLAR_H * 0.4, vertices=16,
    location=(0, 0, z_collar1 - COLLAR_H * 0.2))
collar1_bot = bpy.context.active_object
collar1_bot.name = "collar1_bot"
collar1_bot.data.materials.append(bronze)
all_parts.append(collar1_bot)

# Decorative collar ring 2 (upper two-thirds)
bpy.ops.mesh.primitive_cylinder_add(
    radius=COLLAR_R, depth=COLLAR_H, vertices=16,
    location=(0, 0, z_collar2 + COLLAR_H / 2))
collar2 = bpy.context.active_object
collar2.name = "collar2"
collar2.data.materials.append(bronze)
all_parts.append(collar2)

collar2_bot = bpy.context.active_object
bpy.ops.mesh.primitive_cylinder_add(
    radius=COLLAR_R - 0.02, depth=COLLAR_H * 0.4, vertices=16,
    location=(0, 0, z_collar2 - COLLAR_H * 0.2))
collar2_bot2 = bpy.context.active_object
collar2_bot2.name = "collar2_bot"
collar2_bot2.data.materials.append(bronze)
all_parts.append(collar2_bot2)

# Capital / transition disc at pedestal top
bpy.ops.mesh.primitive_cylinder_add(
    radius=PED_BASE_R, depth=0.10, vertices=12,
    location=(0, 0, z_ped_top + 0.05))
ped_capital = bpy.context.active_object
ped_capital.name = "ped_capital"
ped_capital.data.materials.append(stone)
all_parts.append(ped_capital)

# ════════════════════════════════════════════
# 4. UPPER DECORATIVE BOWL
# ════════════════════════════════════════════
# Outer upper bowl wall (flared at base slightly)
cone("upper_bowl_outer", 0, 0, z_upper_bot,
     r_bot=UPPER_R * 0.85, r_top=UPPER_R, h=UPPER_H, mat=stone, segs=24)

# Inner upper bowl (creates hollow)
bpy.ops.mesh.primitive_cylinder_add(
    radius=UPPER_R - UPPER_T, depth=UPPER_H - 0.06, vertices=24,
    location=(0, 0, z_upper_bot + 0.06 + (UPPER_H - 0.06) / 2))
upper_inner = bpy.context.active_object
upper_inner.name = "upper_inner"
upper_inner.data.materials.append(stone)
all_parts.append(upper_inner)

# Upper bowl rim molding
bpy.ops.mesh.primitive_cylinder_add(
    radius=UPPER_R + 0.04, depth=0.06, vertices=24,
    location=(0, 0, z_upper_top + 0.03))
upper_rim = bpy.context.active_object
upper_rim.name = "upper_rim"
upper_rim.data.materials.append(stone)
all_parts.append(upper_rim)

# Small support disc connecting pedestal top to underside of upper bowl
bpy.ops.mesh.primitive_cylinder_add(
    radius=PED_BASE_R * 0.75, depth=0.08, vertices=12,
    location=(0, 0, z_upper_bot - 0.04))
bowl_support = bpy.context.active_object
bowl_support.name = "bowl_support"
bowl_support.data.materials.append(stone)
all_parts.append(bowl_support)

# ════════════════════════════════════════════
# 5. DECORATIVE URN / FINIAL
# ════════════════════════════════════════════
# Urn base — short wide disc
bpy.ops.mesh.primitive_cylinder_add(
    radius=URN_BELLY_R * 0.90, depth=0.06, vertices=16,
    location=(0, 0, z_urn_bot + 0.03))
urn_base = bpy.context.active_object
urn_base.name = "urn_base"
urn_base.data.materials.append(bronze)
all_parts.append(urn_base)

# Urn belly — widest part, slightly bulging
cone("urn_belly", 0, 0, z_urn_belly + 0.04,
     r_bot=URN_BELLY_R * 0.75, r_top=URN_BELLY_R, h=URN_BELLY_H * 0.55,
     mat=bronze, segs=16)
cone("urn_belly_top", 0, 0, z_urn_belly + 0.04 + URN_BELLY_H * 0.55,
     r_bot=URN_BELLY_R, r_top=URN_BELLY_R * 0.70, h=URN_BELLY_H * 0.45,
     mat=bronze, segs=16)

# Urn neck — narrowing cylinder
cone("urn_neck", 0, 0, z_urn_neck,
     r_bot=URN_BELLY_R * 0.65, r_top=URN_NECK_R, h=URN_NECK_H,
     mat=bronze, segs=16)

# Urn cap — flared disc on top of neck
cone("urn_cap", 0, 0, z_urn_cap,
     r_bot=URN_NECK_R, r_top=URN_CAP_R, h=URN_CAP_H * 0.5,
     mat=bronze, segs=16)
bpy.ops.mesh.primitive_cylinder_add(
    radius=URN_CAP_R, depth=URN_CAP_H * 0.5, vertices=16,
    location=(0, 0, z_urn_cap + URN_CAP_H * 0.75))
urn_cap_disc = bpy.context.active_object
urn_cap_disc.name = "urn_cap_disc"
urn_cap_disc.data.materials.append(bronze)
all_parts.append(urn_cap_disc)

# Thin spike at very top
bpy.ops.mesh.primitive_cylinder_add(
    radius=URN_SPIKE_R, depth=URN_SPIKE_H, vertices=8,
    location=(0, 0, z_spike + URN_SPIKE_H / 2))
spike = bpy.context.active_object
spike.name = "spike"
spike.data.materials.append(bronze)
all_parts.append(spike)

# Spike tip cone
cone("spike_tip", 0, 0, z_spike + URN_SPIKE_H,
     r_bot=URN_SPIKE_R, r_top=0.005, h=0.08, mat=bronze, segs=8)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "CherryHillFountain"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_cherry_hill_fountain.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB',
    use_selection=True, export_apply=True)
print(f"Exported Cherry Hill Fountain to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")
