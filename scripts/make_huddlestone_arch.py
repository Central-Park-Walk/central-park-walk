"""Generate Huddlestone Arch model for Central Park Walk.

Huddlestone Arch — Cyclopean stone arch at the entrance to the Ravine in
the North Woods. Built 1866 by Calvert Vaux. Massive Manhattan schist
boulders held by gravity alone — NO mortar. One boulder reportedly weighs
over 100 tons. The roughest, most primitive structure in the park.

Key dimensions:
  WIDTH       = 6.71m   (22 ft)
  HEIGHT      = 3.05m   (10 ft)
  PASSAGE_L   = ~12m    (est. — relatively short passage)

Materials: Massive Manhattan schist boulders, rough-hewn, no mortar.
Profile: Rough, irregular — approximately semicircular but following
         the natural shape of the boulders.

The arch's character comes from its massive, irregular stone blocks.
We model this with displaced/jittered vertices to suggest rough-cut
cyclopean masonry rather than smooth curves.

Exports to models/furniture/cp_huddlestone_arch.glb
"""

import bpy
import math
import os
import random

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0: bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0: bpy.data.materials.remove(block)

def make_mat(name, color, roughness=0.80, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

# Manhattan schist: dark gray-green, very rough
schist_dark = make_mat("SchistDark", (0.28, 0.27, 0.25), roughness=0.92)
# Lighter schist for variety
schist_light = make_mat("SchistLight", (0.35, 0.33, 0.30), roughness=0.90)
# Path surface
path_mat = make_mat("DirtPath", (0.40, 0.35, 0.28), roughness=0.92)

WIDTH = 6.71; HALF_W = WIDTH / 2
HEIGHT = 3.05
PASS_L = 12.0; HALF_L = PASS_L / 2
WALL_T = 1.5    # thick walls — massive boulders
ARCH_T = 0.80   # thick barrel
ROAD_T = 0.40   # earth/rubble fill above
PARAPET_H = 0.80 # low rough stone wall above
N_ARC = 20
all_parts = []

random.seed(42)  # reproducible roughness


def rough_semicircular_arc(half_w, height, n_pts, roughness=0.15):
    """Semicircular arch with irregular jitter to suggest rough-cut stone."""
    pts = []
    for i in range(n_pts + 1):
        t = i / n_pts
        angle = math.pi * (1.0 - t)
        x = half_w * math.cos(angle)
        z = height * math.sin(angle)
        # Add roughness — more at mid-height, less at crown and base
        jitter = roughness * math.sin(angle) * (random.random() - 0.5) * 2
        x += jitter * 0.5
        z += abs(jitter) * 0.3
        pts.append((x, z))
    return pts


def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name
    o.scale = (hx*2, hy*2, hz*2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); all_parts.append(o); return o


# Generate multiple slightly different arch profiles along the tunnel length
# to create the irregular, boulder-like appearance
n_slices = 8  # number of cross-sections along tunnel

mesh = bpy.data.meshes.new("cyclopean_vault")
verts = []
faces = []

slice_profiles = []
for s in range(n_slices + 1):
    # Each slice has slightly different roughness
    random.seed(42 + s * 7)
    profile = rough_semicircular_arc(HALF_W, HEIGHT, N_ARC, roughness=0.20)
    slice_profiles.append(profile)

# Build mesh: for each pair of adjacent slices, create quads
for s in range(n_slices + 1):
    sy = -HALF_L + s * (PASS_L / n_slices)
    profile = slice_profiles[s]
    for px, pz in profile:
        # Inner surface
        verts.append((px, sy, pz))
        # Outer surface (offset outward, also rough)
        d = math.sqrt(px*px + pz*pz)
        if d > 0.1:
            jit = random.random() * 0.08
            ox = px * (1 + (ARCH_T + jit) / d)
            oz = pz * (1 + (ARCH_T + jit) / d)
        else:
            ox, oz = px, pz + ARCH_T
        verts.append((ox, sy, oz))

n_pts = N_ARC + 1
for s in range(n_slices):
    for i in range(n_pts - 1):
        # Inner surface
        b0 = s * n_pts * 2 + i * 2
        b1 = s * n_pts * 2 + (i + 1) * 2
        b2 = (s + 1) * n_pts * 2 + (i + 1) * 2
        b3 = (s + 1) * n_pts * 2 + i * 2
        faces.append((b0, b3, b2, b1))
        # Outer surface
        faces.append((b0 + 1, b1 + 1, b2 + 1, b3 + 1))

mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new("cyclopean_vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(schist_dark)
all_parts.append(obj)

# Massive boulder-like blocks for the face walls
# Instead of smooth face panels, place individual rough blocks
for end in (-1, 1):
    ey = end * HALF_L
    # Create several large "boulders" around the arch opening
    random.seed(100 + (1 if end > 0 else 0))
    n_boulders = 14
    for bi in range(n_boulders):
        # Position boulders around the arch perimeter
        t = bi / n_boulders
        angle = math.pi * (1.0 - t)
        # On the arch ring, outside the opening
        base_x = (HALF_W + WALL_T * 0.5) * math.cos(angle)
        base_z = (HEIGHT + ARCH_T * 0.3) * math.sin(angle)
        # Random size for each boulder
        bw = 0.4 + random.random() * 0.8  # 0.4-1.2m
        bh = 0.3 + random.random() * 0.6
        bd = 0.3 + random.random() * 0.4
        # Slight position jitter
        jx = (random.random() - 0.5) * 0.15
        jz = (random.random() - 0.5) * 0.10
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(base_x + jx, ey + end * bd/2, base_z + jz))
        boulder = bpy.context.active_object
        boulder.name = f"boulder_{end}_{bi}"
        boulder.scale = (bw, bd, bh)
        # Slight rotation for irregularity
        boulder.rotation_euler.x = (random.random() - 0.5) * 0.15
        boulder.rotation_euler.y = (random.random() - 0.5) * 0.10
        boulder.rotation_euler.z = (random.random() - 0.5) * 0.20
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        mat = schist_dark if random.random() > 0.4 else schist_light
        boulder.data.materials.append(mat)
        all_parts.append(boulder)

# Side walls — thick, rough boulder walls
for side in (-1, 1):
    wx = side * (HALF_W + WALL_T / 2)
    wall_h = HEIGHT + ARCH_T + ROAD_T
    box(f"wall_{side}", wx, 0, wall_h/2, WALL_T/2, HALF_L, wall_h/2, schist_dark)

# Road fill above (earth/rubble, not paved)
road_top = HEIGHT + ARCH_T
road_w = WIDTH + 2 * WALL_T
box("road_fill", 0, 0, road_top + ROAD_T/2, road_w/2, HALF_L + 1.0, ROAD_T/2, path_mat)

# Low rough parapet walls
for side in (-1, 1):
    px = side * (road_w/2 - 0.3)
    box(f"parapet_{side}", px, 0, road_top+ROAD_T+PARAPET_H/2,
        0.4, HALF_L + 1.0, PARAPET_H/2, schist_dark)

# Floor
box("floor", 0, 0, -0.15, HALF_W, HALF_L, 0.15, path_mat)

# Finalize
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()
arch = bpy.context.active_object; arch.name = "HuddlestoneArch"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_huddlestone_arch.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
print(f"Exported Huddlestone Arch to {out_path}")
print(f"  Verts: {len(arch.data.vertices)}, Faces: {len(arch.data.polygons)}")
