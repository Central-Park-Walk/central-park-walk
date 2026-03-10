"""Generate Winterdale Arch model for Central Park Walk.

Winterdale Arch — the largest stone-span arch in Central Park. Built 1860s,
designed by Calvert Vaux. Very flat elliptical profile. Carries West Drive
over a pedestrian path near the Great Lawn.

Key dimensions:
  SPAN        = 13.87m  (45 ft 6 in — largest stone span in CP)
  HEIGHT      = 3.73m   (12 ft 3 in)
  PASSAGE_L   = 18.0m   (~60 ft est. — road width + walls)

Materials:
  Facing: Smooth Maine granite (light gray, precisely cut ashlar)
  Trim: Regular ashlar sandstone moldings following arch contour
  Interior: Brick barrel vault (assumed, standard for CP arches)

Profile: Very flat elliptical (span:height ~ 3.7:1)

Orientation (Blender Z-up):
  Tunnel runs along Y axis. Origin at tunnel center, Z=0 at ground.

Exports to models/furniture/cp_winterdale_arch.glb
"""

import bpy
import bmesh
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
def make_mat(name, color, roughness=0.80, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

# Maine granite: light gray, smooth-cut
granite = make_mat("Granite", (0.62, 0.60, 0.58), roughness=0.72)
# Sandstone trim
sandstone = make_mat("SandstoneTrim", (0.60, 0.53, 0.43), roughness=0.78)
# Red brick interior
red_brick = make_mat("RedBrick", (0.55, 0.28, 0.20), roughness=0.85)
# Road surface
road_mat = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
# Parapet
parapet_mat = make_mat("Parapet", (0.60, 0.58, 0.55), roughness=0.75)

# ── Dimensions ──
SPAN = 13.87         # arch span (m)
HALF_SPAN = SPAN / 2.0
HEIGHT = 3.73        # arch height (m)
PASSAGE_L = 18.0     # passage length (m)
HALF_L = PASSAGE_L / 2.0
WALL_T = 1.0         # wall thickness
ARCH_T = 0.55        # barrel thickness
ROAD_T = 0.30        # road deck thickness
PARAPET_H = 1.0      # parapet height
PARAPET_T = 0.35     # parapet thickness
GROUND_D = 0.3       # below-ground extension

N_ARC = 28
all_parts = []


def elliptical_arc(half_w, height, n_pts):
    """Elliptical arch from -half_w to +half_w."""
    pts = []
    for i in range(n_pts + 1):
        t = i / n_pts
        angle = math.pi * (1.0 - t)
        x = half_w * math.cos(angle)
        z = height * math.sin(angle)
        pts.append((x, z))
    return pts


def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o


# ── 1. Brick barrel vault (interior) ──
arc_pts = elliptical_arc(HALF_SPAN, HEIGHT, N_ARC)

mesh = bpy.data.meshes.new("barrel_vault")
verts = []
faces = []
n_arc = len(arc_pts)

for px, pz in arc_pts:
    # Inner surface
    verts.append((px, -HALF_L, pz))
    verts.append((px,  HALF_L, pz))
    # Outer surface
    r = math.sqrt(px * px / (HALF_SPAN * HALF_SPAN) + pz * pz / (HEIGHT * HEIGHT)) if (abs(px) > 0.01 or abs(pz) > 0.01) else 1.0
    # Offset along the ellipse normal direction
    # For simplicity, radially outward from center
    dist = math.sqrt(px * px + pz * pz)
    if dist > 0.1:
        ox = px * (1.0 + ARCH_T / dist)
        oz = pz * (1.0 + ARCH_T / dist)
    else:
        ox = px
        oz = pz + ARCH_T
    verts.append((ox, -HALF_L, oz))
    verts.append((ox,  HALF_L, oz))

for i in range(n_arc - 1):
    b = i * 4
    nb = (i + 1) * 4
    # Inner surface
    faces.append((b, b + 1, nb + 1, nb))
    # Outer surface
    faces.append((b + 2, nb + 2, nb + 3, b + 3))
    # Side edges
    faces.append((b, nb, nb + 2, b + 2))
    faces.append((b + 1, b + 3, nb + 3, nb + 1))

mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new("barrel_vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(red_brick)
all_parts.append(obj)

# ── 2. Exterior face walls (granite) ──
for end in (-1, 1):
    ey = end * HALF_L
    verts_f = []
    faces_f = []
    face_w = SPAN + 2 * WALL_T
    face_h = HEIGHT + ARCH_T + ROAD_T
    hw = face_w / 2

    # Left panel
    verts_f.append((-hw, ey, -GROUND_D))          # 0
    verts_f.append((-HALF_SPAN, ey, -GROUND_D))   # 1
    verts_f.append((-HALF_SPAN, ey, 0))            # 2
    verts_f.append((-hw, ey, face_h))              # 3
    faces_f.append((0, 1, 2, 3) if end > 0 else (0, 3, 2, 1))

    # Right panel
    b = len(verts_f)
    verts_f.append((HALF_SPAN, ey, -GROUND_D))
    verts_f.append((hw, ey, -GROUND_D))
    verts_f.append((hw, ey, face_h))
    verts_f.append((HALF_SPAN, ey, 0))
    faces_f.append((b, b+1, b+2, b+3) if end > 0 else (b, b+3, b+2, b+1))

    # Top panel (above arch crown)
    b = len(verts_f)
    verts_f.append((-hw, ey, HEIGHT + ARCH_T))
    verts_f.append((hw, ey, HEIGHT + ARCH_T))
    verts_f.append((hw, ey, face_h))
    verts_f.append((-hw, ey, face_h))
    faces_f.append((b, b+1, b+2, b+3) if end > 0 else (b, b+3, b+2, b+1))

    m = bpy.data.meshes.new(f"face_{end}")
    m.from_pydata(verts_f, [], faces_f)
    m.update()
    o = bpy.data.objects.new(f"face_{end}", m)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(granite)
    all_parts.append(o)

# ── 3. Arch ring molding (sandstone) ──
for end in (-1, 1):
    ey = end * HALF_L
    mesh = bpy.data.meshes.new(f"ring_{end}")
    verts = []
    faces = []
    ring_d = 0.12

    for i in range(N_ARC + 1):
        t = i / N_ARC
        angle = math.pi * (1.0 - t)
        ix = HALF_SPAN * math.cos(angle)
        iz = HEIGHT * math.sin(angle)
        ox = (HALF_SPAN + 0.12) * math.cos(angle)
        oz = (HEIGHT + 0.12) * math.sin(angle)
        verts.append((ix, ey + end * ring_d, iz))
        verts.append((ox, ey + end * ring_d, oz))
        verts.append((ix, ey, iz))
        verts.append((ox, ey, oz))

    for i in range(N_ARC):
        b = i * 4
        nb = (i + 1) * 4
        faces.append((b, b + 1, nb + 1, nb))
        faces.append((b + 1, b + 3, nb + 3, nb + 1))

    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"ring_{end}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(sandstone)
    all_parts.append(obj)

# ── 4. Road deck ──
road_w = SPAN + 2 * WALL_T + 0.5
road_top = HEIGHT + ARCH_T
box("road_deck", 0, 0, road_top + ROAD_T / 2,
    road_w / 2, HALF_L + 1.5, ROAD_T / 2, road_mat)

# ── 5. Parapets ──
for side in (-1, 1):
    px = side * (road_w / 2 - PARAPET_T / 2)
    box(f"parapet_{side}",
        px, 0, road_top + ROAD_T + PARAPET_H / 2,
        PARAPET_T / 2, HALF_L + 1.5, PARAPET_H / 2, parapet_mat)

# ── 6. Tunnel floor ──
box("floor", 0, 0, -GROUND_D / 2,
    HALF_SPAN, HALF_L, GROUND_D / 2, road_mat)

# ── 7. Side walls below springing ──
for side in (-1, 1):
    wx = side * (HALF_SPAN + WALL_T / 2)
    wall_h = HEIGHT + ARCH_T + ROAD_T + GROUND_D
    box(f"wall_{side}",
        wx, 0, wall_h / 2 - GROUND_D,
        WALL_T / 2, HALF_L, wall_h / 2, granite)

# ── 8. Wing walls ──
for end in (-1, 1):
    for side in (-1, 1):
        wy = end * (HALF_L + 1.5)
        wx = side * (HALF_SPAN + WALL_T + 0.5)
        wh = (HEIGHT + ARCH_T + ROAD_T) * 0.7
        box(f"wing_{end}_{side}",
            wx, wy, wh / 2,
            0.35, 1.5, wh / 2, granite)


# ── Finalize ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

arch = bpy.context.active_object
arch.name = "WinterdaleArch"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_winterdale_arch.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Winterdale Arch to {out_path}")
print(f"  Verts: {len(arch.data.vertices)}, Faces: {len(arch.data.polygons)}")
