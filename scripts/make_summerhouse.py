"""Generate the Dene Summerhouse for Central Park Walk.

The Dene Summerhouse (1880s, restored) is a small rustic stone shelter
near the Dene, in the southeast section of Central Park. One of the
original Olmsted & Vaux rustic structures, built of Manhattan schist.

Key features:
  - Small open stone shelter, ~4m × 3m footprint
  - Thick rough schist walls on three sides (~0.6m thick, ~2.5m tall)
  - Open front facing south (no front wall)
  - Low-pitch gable roof of stone slab
  - Stone bench built into the back wall interior
  - Rough stone cap on top of walls
  - Sits at ground level in a small clearing

The shelter faces south (+Y direction, open front).
Origin at ground center.
Exports to models/furniture/cp_summerhouse.glb
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

schist    = make_mat("Schist",   (0.40, 0.38, 0.35), 0.90)
cap_stone = make_mat("CapStone", (0.48, 0.45, 0.42), 0.85)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Add a box centered at (cx, cy, cz) with half-extents (hx, hy, hz)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Dimensions ──
W    = 4.0   # width (X)
D    = 3.0   # depth (Y, front-to-back)
H    = 2.5   # wall height
T    = 0.60  # wall thickness (thick rustic schist)
OVHG = 0.35  # roof overhang past wall faces

hw = W / 2.0
hd = D / 2.0

# ════════════════════════════════════════════
# 1. STONE FLOOR SLAB — slightly raised platform
# ════════════════════════════════════════════
box("floor_slab", 0, 0, -0.08, hw + 0.15, hd + 0.15, 0.18, schist)

# ════════════════════════════════════════════
# 2. THREE WALLS — back (north) + two sides
#    Open front (south face) has no wall.
# ════════════════════════════════════════════
wall_z = H / 2.0   # center Z for a wall of height H starting at 0

# Back wall (north face, solid, full width)
box("wall_back",  0,       -hd + T / 2,  wall_z,  hw,       T / 2, H / 2, schist)

# Side walls (run full depth; flush with back wall outer face, open at front)
# Left side (negative X)
box("wall_left",  -hw + T / 2,  0,  wall_z,  T / 2,  hd,  H / 2, schist)
# Right side (positive X)
box("wall_right",  hw - T / 2,  0,  wall_z,  T / 2,  hd,  H / 2, schist)

# ════════════════════════════════════════════
# 3. ROUGH STONE CAPS on top of each wall
#    Slightly wider and taller than the wall face — rustic overhang
# ════════════════════════════════════════════
CAP_H  = 0.18   # cap slab height
CAP_EX = 0.08   # extra projection past wall face

# Back wall cap
box("cap_back",  0,       -hd + T / 2,  H + CAP_H / 2,
    hw + CAP_EX,  T / 2 + CAP_EX,  CAP_H / 2,  cap_stone)

# Left wall cap
box("cap_left",  -hw + T / 2,  0,  H + CAP_H / 2,
    T / 2 + CAP_EX,  hd + CAP_EX,  CAP_H / 2,  cap_stone)

# Right wall cap
box("cap_right",  hw - T / 2,  0,  H + CAP_H / 2,
    T / 2 + CAP_EX,  hd + CAP_EX,  CAP_H / 2,  cap_stone)

# Corner cap infill blocks (where side caps meet back cap — overlap corner zone)
for sx in (-1, 1):
    box(f"cap_corner_{sx}",
        sx * (hw - T / 2),  -hd + T / 2,  H + CAP_H / 2,
        T / 2 + CAP_EX,  T / 2 + CAP_EX,  CAP_H / 2,  cap_stone)

# ════════════════════════════════════════════
# 4. LOW-PITCH GABLE ROOF — stone slab construction
#    Ridge runs east-west (along X axis).
#    Front (south) and back (north) slopes are low-pitch.
#    Gable ends are open on the east-west sides (over the side walls).
# ════════════════════════════════════════════
roof_base_z = H + CAP_H     # bottom of roof sits on wall cap
RIDGE_RISE  = 0.55          # low pitch: ~20 degrees on 3m span

# Roof verts: 4 eave corners + 2 ridge endpoints
# Eave line at roof_base_z, running wall-outer-face + overhang
# South eave at  hd + OVHG  (front open face, roof extends forward)
# North eave at -hd - OVHG  (back exterior)
# East/west eave at ±(hw + OVHG)
# Ridge line centered front-to-back at Z = roof_base_z + RIDGE_RISE
rv = [
    (-hw - OVHG,  -hd - OVHG,  roof_base_z),          # 0 NW eave
    ( hw + OVHG,  -hd - OVHG,  roof_base_z),          # 1 NE eave
    ( hw + OVHG,   hd + OVHG,  roof_base_z),          # 2 SE eave
    (-hw - OVHG,   hd + OVHG,  roof_base_z),          # 3 SW eave
    (-hw - OVHG,   0.0,         roof_base_z + RIDGE_RISE),  # 4 ridge west
    ( hw + OVHG,   0.0,         roof_base_z + RIDGE_RISE),  # 5 ridge east
]
# Faces: north slope, south slope, west gable triangle, east gable triangle, soffit
rf = [
    (0, 1, 5, 4),   # north slope
    (3, 2, 5, 4),   # south slope  (winding: CCW from outside)
    (0, 3, 4),      # west gable triangle
    (2, 1, 5),      # east gable triangle
    (1, 0, 3, 2),   # soffit (underside)
]
rm = bpy.data.meshes.new("roof_mesh")
rm.from_pydata(rv, [], rf)
rm.update()
ro = bpy.data.objects.new("GableRoof", rm)
bpy.context.collection.objects.link(ro)
ro.data.materials.append(cap_stone)
all_parts.append(ro)

# Ridge cap — a flat stone slab capping the ridge peak
box("ridge_cap", 0, 0, roof_base_z + RIDGE_RISE + 0.06,
    hw + OVHG + 0.05,  0.14,  0.07,  cap_stone)

# ════════════════════════════════════════════
# 5. INTERIOR STONE BENCH — built into back wall
#    Runs the full interior width, low to the ground.
# ════════════════════════════════════════════
BENCH_H  = 0.46   # seat height
BENCH_D  = 0.38   # bench depth (Y)
BENCH_T  = 0.16   # seat slab thickness

bench_interior_x = hw - T - 0.06   # leaves a gap from side walls

# Bench support slab (masonry block under seat)
box("bench_support", 0,  -hd + T + BENCH_D / 2,  BENCH_H / 2 - BENCH_T / 2,
    bench_interior_x,  BENCH_D / 2,  (BENCH_H - BENCH_T) / 2,  schist)

# Bench seat slab (cap stone, slightly wider and proud)
box("bench_seat", 0,  -hd + T + BENCH_D / 2,  BENCH_H,
    bench_interior_x + 0.04,  BENCH_D / 2 + 0.04,  BENCH_T / 2,  cap_stone)

# ════════════════════════════════════════════
# 6. ENTRY STEP — single rough stone step at open front
# ════════════════════════════════════════════
box("entry_step", 0,  hd + 0.25,  -0.08,
    hw * 0.55,  0.28,  0.12,  schist)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "DeneSummerhouse"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_summerhouse.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Dene Summerhouse to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")
