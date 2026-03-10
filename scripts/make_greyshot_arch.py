"""Generate Greyshot Arch model for Central Park Walk.

Greyshot Arch — elegant elliptical stone arch near the southeast end of
the park (at about 62nd Street, west of the Dairy). Built 1860, designed
by Calvert Vaux. Carries a pedestrian path over the bridle path.

Key dimensions:
  OPENING_W   = 9.30m  (30 ft 6 in wide)
  OPENING_H   = 3.07m  (10 ft 1 in high)
  PASSAGE_L   = 18.0m  (~60 ft passage length, est.)
  Profile: Elliptical (wide, low)

Materials:
  Exterior: Westchester County variegated gneiss (whitish-gray with dark
            orange veins), irregular coursing
  Trim: New Brunswick sandstone moldings on arch ring and balustrade
  Interior: Philadelphia red brick barrel vault
  Above: Stone balustrade with fleur-de-lis motifs (south side)

Orientation (Blender Z-up):
  Tunnel runs along Y axis. Origin at tunnel center, Z=0 at ground level.

Exports to models/furniture/cp_greyshot_arch.glb
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

# Gneiss: whitish-gray with warm veins
gneiss = make_mat("Gneiss", (0.55, 0.52, 0.48), roughness=0.82)
# Sandstone trim: warm tan/brown
sandstone_trim = make_mat("SandstoneTrim", (0.62, 0.55, 0.44), roughness=0.78)
# Red brick interior
red_brick = make_mat("RedBrick", (0.55, 0.28, 0.20), roughness=0.85)
# Road surface above
road_mat = make_mat("RoadSurface", (0.35, 0.33, 0.30), roughness=0.90)
# Balustrade stone
balustrade_mat = make_mat("Balustrade", (0.58, 0.54, 0.48), roughness=0.78)

# ── Dimensions ──
OPENING_W = 9.30       # arch opening width (m)
HALF_W = OPENING_W / 2.0
OPENING_H = 3.07       # arch height at crown (m)
PASSAGE_L = 18.0       # tunnel passage length (m)
HALF_L = PASSAGE_L / 2.0
WALL_T = 1.0           # wall thickness (m)
ARCH_T = 0.60          # arch barrel thickness
ROAD_DECK_T = 0.30     # road surface thickness above arch
PARAPET_H = 1.0        # parapet/balustrade height above road
PARAPET_T = 0.40       # parapet thickness
GROUND_DEPTH = 0.5     # how far walls extend below ground

all_parts = []

N_ARC = 24  # arc subdivision


def elliptical_arc(half_w, height, n_pts):
    """Generate points for an elliptical arch.
    Returns [(x, z)] from -half_w to +half_w."""
    pts = []
    for i in range(n_pts + 1):
        t = i / n_pts
        angle = math.pi * (1.0 - t)  # pi to 0
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


# ── 1. Arch barrel vault (brick interior) ──
arc_pts = elliptical_arc(HALF_W, OPENING_H, N_ARC)

mesh = bpy.data.meshes.new("barrel_vault")
verts = []
faces = []
n_arc = len(arc_pts)

# Barrel vault along Y axis (tunnel length)
for px, pz in arc_pts:
    # Inner surface
    verts.append((px, -HALF_L, pz))
    verts.append((px,  HALF_L, pz))
    # Outer surface (above inner by arch thickness)
    # Scale outward from center for elliptical thickening
    if abs(px) < 0.01 and pz > OPENING_H * 0.9:
        # Crown
        ox, oz = px, pz + ARCH_T
    else:
        # Scale outward from ellipse center
        r = math.sqrt(px * px + pz * pz) if (px != 0 or pz != 0) else 1.0
        scale = (r + ARCH_T) / r if r > 0.1 else 1.0
        ox = px * scale
        oz = pz * scale
    verts.append((ox, -HALF_L, oz))
    verts.append((ox,  HALF_L, oz))

for i in range(n_arc - 1):
    b = i * 4
    nb = (i + 1) * 4
    # Inner surface (visible from inside tunnel)
    faces.append((b, b + 1, nb + 1, nb))
    # Outer surface (hidden under road/fill)
    faces.append((b + 2, nb + 2, nb + 3, b + 3))
    # End caps (tunnel entrance/exit faces)
    faces.append((b, nb, nb + 2, b + 2))
    faces.append((b + 1, b + 3, nb + 3, nb + 1))

mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new("barrel_vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(red_brick)
all_parts.append(obj)

# ── 2. Side walls (below arch springing, visible from inside) ──
# The arch springs from the ground, so walls go from ground to springing line
for side in (-1, 1):
    wx = side * HALF_W
    box(f"side_wall_{side}",
        wx + side * WALL_T / 2, 0, -GROUND_DEPTH / 2 + OPENING_H * 0.0,
        WALL_T / 2, HALF_L, (OPENING_H * 0.0 + GROUND_DEPTH) / 2,
        gneiss)
    # Actually, for an elliptical arch the springing starts at ground level
    # The inner wall face is just the bottom strip below where arch begins
    # For a full ellipse to ground, the arch starts at ground — no wall needed below

# ── 3. Exterior face walls (gneiss, visible from outside) ──
# The tunnel face on each end — the arch opening with stone surround
for end in (-1, 1):
    ey = end * HALF_L
    mesh = bpy.data.meshes.new(f"face_wall_{end}")
    verts = []
    faces = []

    # Outer rectangle of the face wall
    face_w = OPENING_W + 2 * WALL_T
    face_h = OPENING_H + ARCH_T + ROAD_DECK_T
    hw = face_w / 2

    # Bottom-left, bottom-right, top-right, top-left of outer rectangle
    verts.append((-hw, ey, -GROUND_DEPTH))                    # 0
    verts.append(( hw, ey, -GROUND_DEPTH))                    # 1
    verts.append(( hw, ey, face_h))                            # 2
    verts.append((-hw, ey, face_h))                            # 3

    # Arch opening cutout (elliptical) — approximate with polygon
    n_cut = 16
    for i in range(n_cut + 1):
        t = i / n_cut
        angle = math.pi * (1.0 - t)
        cx = HALF_W * math.cos(angle)
        cz = OPENING_H * math.sin(angle)
        verts.append((cx, ey, cz))  # indices 4..4+n_cut

    # For simplicity, just create the outer face as a single quad
    # and the arch trim ring
    # The face wall is complex (arch cutout in rectangle) — use a simpler approach
    # Just create solid wall panels on each side of the arch
    verts_out = []
    faces_out = []

    # Left wall panel (from left edge to arch springing)
    verts_out.append((-hw, ey, -GROUND_DEPTH))
    verts_out.append((-HALF_W, ey, -GROUND_DEPTH))
    verts_out.append((-HALF_W, ey, 0))
    verts_out.append((-hw, ey, face_h))
    faces_out.append((0, 1, 2, 3) if end > 0 else (0, 3, 2, 1))

    # Right wall panel
    base = len(verts_out)
    verts_out.append((HALF_W, ey, -GROUND_DEPTH))
    verts_out.append((hw, ey, -GROUND_DEPTH))
    verts_out.append((hw, ey, face_h))
    verts_out.append((HALF_W, ey, 0))
    faces_out.append((base, base+1, base+2, base+3) if end > 0 else (base, base+3, base+2, base+1))

    # Top panel (above arch crown)
    base = len(verts_out)
    verts_out.append((-hw, ey, OPENING_H + ARCH_T))
    verts_out.append((hw, ey, OPENING_H + ARCH_T))
    verts_out.append((hw, ey, face_h))
    verts_out.append((-hw, ey, face_h))
    faces_out.append((base, base+1, base+2, base+3) if end > 0 else (base, base+3, base+2, base+1))

    m = bpy.data.meshes.new(f"face_{end}")
    m.from_pydata(verts_out, [], faces_out)
    m.update()
    o = bpy.data.objects.new(f"face_{end}", m)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(gneiss)
    all_parts.append(o)

# ── 4. Arch ring trim (sandstone molding around opening) ──
for end in (-1, 1):
    ey = end * HALF_L
    mesh = bpy.data.meshes.new(f"arch_ring_{end}")
    verts = []
    faces = []
    ring_depth = 0.15  # protrusion of molding

    for i in range(N_ARC + 1):
        t = i / N_ARC
        angle = math.pi * (1.0 - t)
        # Inner edge of ring (at arch opening)
        ix = HALF_W * math.cos(angle)
        iz = OPENING_H * math.sin(angle)
        # Outer edge of ring (slightly larger)
        ox = (HALF_W + 0.15) * math.cos(angle)
        oz = (OPENING_H + 0.15) * math.sin(angle)
        verts.append((ix, ey + end * ring_depth, iz))
        verts.append((ox, ey + end * ring_depth, oz))
        verts.append((ix, ey, iz))
        verts.append((ox, ey, oz))

    for i in range(N_ARC):
        b = i * 4
        nb = (i + 1) * 4
        # Front face of ring
        faces.append((b, b + 1, nb + 1, nb))
        # Outer edge
        faces.append((b + 1, b + 3, nb + 3, nb + 1))

    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"arch_ring_{end}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(sandstone_trim)
    all_parts.append(obj)

# ── 5. Road deck above ──
road_w = OPENING_W + 2 * WALL_T + 1.0  # slightly wider than tunnel
road_h_base = OPENING_H + ARCH_T
box("road_deck", 0, 0, road_h_base + ROAD_DECK_T / 2,
    road_w / 2, HALF_L + 1.0, ROAD_DECK_T / 2, road_mat)

# ── 6. Parapets / balustrade above ──
for side in (-1, 1):
    px = side * (road_w / 2 - PARAPET_T / 2)
    box(f"parapet_{side}",
        px, 0, road_h_base + ROAD_DECK_T + PARAPET_H / 2,
        PARAPET_T / 2, HALF_L + 1.0, PARAPET_H / 2, balustrade_mat)

# ── 7. Tunnel floor ──
box("tunnel_floor", 0, 0, -GROUND_DEPTH / 2,
    HALF_W + 0.1, HALF_L, GROUND_DEPTH / 2, road_mat)

# ── 8. Retaining walls extending beyond tunnel ──
for end in (-1, 1):
    for side in (-1, 1):
        # Wing walls
        wy = end * (HALF_L + 2.0)
        wx = side * (HALF_W + WALL_T / 2 + 1.0)
        box(f"wing_{end}_{side}",
            wx, wy, road_h_base / 2,
            0.4, 2.0, road_h_base / 2, gneiss)


# ── Finalize ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

arch = bpy.context.active_object
arch.name = "GreyshotArch"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_greyshot_arch.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Greyshot Arch to {out_path}")
print(f"  Verts: {len(arch.data.vertices)}, Faces: {len(arch.data.polygons)}")
