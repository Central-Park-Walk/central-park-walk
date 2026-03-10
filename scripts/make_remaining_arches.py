"""Generate remaining arch models for Central Park Walk.

Builds GLBs for arches that share the common stone-arch pattern
(barrel vault interior, face walls, parapets) but differ in dimensions,
materials, and arch profile.

Each arch is built separately and exported to its own GLB file.

Arches built here:
  - Driprock Arch: 8.23m×3.51m, segmental, sandstone+brick, Gothic detail
  - Denesmouth Arch: ~8m×3m est., elliptical, sandstone
  - Green Gap Arch: ~6m×3m est. (dimensions less documented)
  - Riftstone Arch: 9.14m×3.61m, rustic/rough, Manhattan schist
  - Oak Bridge: 18.3m×7.6m, rustic wood, steel+aluminum (2009 rebuild)
  - Balcony Bridge: 8.23m×3.51m, segmental, sandstone/cast stone/schist/greywacke
  - Eaglevale Bridge: 45.7m×11m, double arch, gneiss

Exports to models/furniture/cp_<name>.glb
"""

import bpy
import math
import os
import random

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for b in bpy.data.meshes:
        if b.users == 0: bpy.data.meshes.remove(b)
    for b in bpy.data.materials:
        if b.users == 0: bpy.data.materials.remove(b)

def make_mat(name, color, roughness=0.80, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

def seg_arc(hw, rise, n):
    R = (rise*rise + hw*hw)/(2*rise); cz = rise - R
    return [(-hw + i/n*2*hw, cz + math.sqrt(max(R*R - (-hw+i/n*2*hw)**2, 0))) for i in range(n+1)]

def ellip_arc(hw, h, n):
    return [(hw*math.cos(math.pi*(1-i/n)), h*math.sin(math.pi*(1-i/n))) for i in range(n+1)]

def box(name, cx, cy, cz, hx, hy, hz, mat, parts):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name
    o.scale = (hx*2, hy*2, hz*2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); parts.append(o); return o

def build_standard_arch(name, width, height, passage_l, wall_t, arch_t, road_t,
                        parapet_h, parapet_t, arc_fn, stone_mat, interior_mat,
                        road_mat, parapet_mat, na=24):
    """Build a standard stone arch with barrel vault, face walls, road, parapets."""
    parts = []
    hw = width/2; hl = passage_l/2

    # Barrel vault
    arc = arc_fn(hw, height, na)
    mesh = bpy.data.meshes.new("vault"); verts = []; faces = []
    for px, pz in arc:
        verts.append((px, -hl, pz)); verts.append((px, hl, pz))
        d = math.sqrt(px*px + pz*pz)
        if d > 0.1: ox, oz = px*(1+arch_t/d), pz*(1+arch_t/d)
        else: ox, oz = px, pz+arch_t
        verts.append((ox, -hl, oz)); verts.append((ox, hl, oz))
    for i in range(len(arc)-1):
        b = i*4; nb = (i+1)*4
        faces += [(b,b+1,nb+1,nb), (b+2,nb+2,nb+3,b+3), (b,nb,nb+2,b+2), (b+1,b+3,nb+3,nb+1)]
    mesh.from_pydata(verts, [], faces); mesh.update()
    obj = bpy.data.objects.new("vault", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(interior_mat); parts.append(obj)

    # Face walls
    for end in (-1, 1):
        ey = end*hl; vf = []; ff = []; fhw = width/2+wall_t; fh = height+arch_t+road_t
        vf += [(-fhw,ey,-0.3),(-hw,ey,-0.3),(-hw,ey,0),(-fhw,ey,fh)]
        ff.append((0,1,2,3) if end>0 else (0,3,2,1))
        b = len(vf)
        vf += [(hw,ey,-0.3),(fhw,ey,-0.3),(fhw,ey,fh),(hw,ey,0)]
        ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
        b = len(vf)
        vf += [(-fhw,ey,height+arch_t),(fhw,ey,height+arch_t),(fhw,ey,fh),(-fhw,ey,fh)]
        ff.append((b,b+1,b+2,b+3) if end>0 else (b,b+3,b+2,b+1))
        m = bpy.data.meshes.new(f"face_{end}"); m.from_pydata(vf, [], ff); m.update()
        o = bpy.data.objects.new(f"face_{end}", m); bpy.context.collection.objects.link(o)
        o.data.materials.append(stone_mat); parts.append(o)

        # Arch ring
        mesh = bpy.data.meshes.new(f"ring_{end}"); verts = []; faces = []
        for i in range(na+1):
            px, pz = arc[i]
            d = math.sqrt(px*px + pz*pz)
            if d > 0.1: ox, oz = px*(1+0.12/d), pz*(1+0.12/d)
            else: ox, oz = px, pz+0.12
            verts += [(px,ey+end*0.10,pz),(ox,ey+end*0.10,oz),(px,ey,pz),(ox,ey,oz)]
        for i in range(na):
            b = i*4; nb = (i+1)*4
            faces += [(b,b+1,nb+1,nb), (b+1,b+3,nb+3,nb+1)]
        mesh.from_pydata(verts, [], faces); mesh.update()
        obj = bpy.data.objects.new(f"ring_{end}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(stone_mat); parts.append(obj)

    # Road, walls, parapets, floor
    rw = width+2*wall_t; rt = height+arch_t
    box("road", 0, 0, rt+road_t/2, rw/2, hl+1.5, road_t/2, road_mat, parts)
    for s in (-1,1):
        box(f"par_{s}", s*(rw/2-parapet_t/2), 0, rt+road_t+parapet_h/2, parapet_t/2, hl+1.5, parapet_h/2, parapet_mat, parts)
        box(f"wall_{s}", s*(hw+wall_t/2), 0, (rt+0.3)/2-0.3, wall_t/2, hl, (rt+0.3)/2, stone_mat, parts)
    box("floor", 0, 0, -0.15, hw, hl, 0.15, road_mat, parts)
    for e in (-1,1):
        for s in (-1,1):
            box(f"w_{e}_{s}", s*(hw+wall_t+0.4), e*(hl+1.2), rt*0.5, 0.3, 1.2, rt*0.5, stone_mat, parts)
    return parts

def finalize_and_export(parts, obj_name, out_path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    a = bpy.context.active_object; a.name = obj_name
    bpy.context.scene.cursor.location = (0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=True, export_apply=True)
    print(f"Exported {obj_name} to {out_path}")
    print(f"  Verts: {len(a.data.vertices)}, Faces: {len(a.data.polygons)}")

BASE = "/home/chris/central-park-walk/models/furniture"

# ── Driprock Arch ──
# 27ft wide × 11'6" high × 65ft passage. Segmental. Red brick + NJ sandstone, Gothic detail.
clear_scene()
stone = make_mat("Sandstone", (0.56, 0.48, 0.38), roughness=0.82)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
par = make_mat("Parapet", (0.54, 0.46, 0.38), roughness=0.78)
parts = build_standard_arch("DriprockArch", 8.23, 3.51, 19.81, 0.90, 0.50, 0.30, 1.0, 0.35,
                            seg_arc, stone, brick, road, par)
finalize_and_export(parts, "DriprockArch", f"{BASE}/cp_driprock_arch.glb")

# ── Denesmouth Arch ──
# Elliptical. Sandstone. Dimensions less precisely documented. ~30ft wide × ~10ft high est.
clear_scene()
stone = make_mat("Sandstone", (0.55, 0.48, 0.39), roughness=0.83)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
par = make_mat("Parapet", (0.53, 0.47, 0.40), roughness=0.78)
parts = build_standard_arch("DenesmouthArch", 9.14, 3.05, 16.0, 0.90, 0.50, 0.30, 1.0, 0.35,
                            ellip_arc, stone, brick, road, par)
finalize_and_export(parts, "DenesmouthArch", f"{BASE}/cp_denesmouth_arch.glb")

# ── Green Gap Arch ──
# Less documented. Estimated ~20ft wide × ~10ft high. Stone/brick segmental.
clear_scene()
stone = make_mat("Stone", (0.50, 0.47, 0.42), roughness=0.84)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
par = make_mat("Parapet", (0.52, 0.48, 0.43), roughness=0.80)
parts = build_standard_arch("GreenGapArch", 6.10, 3.05, 15.0, 0.85, 0.45, 0.30, 0.90, 0.35,
                            seg_arc, stone, brick, road, par)
finalize_and_export(parts, "GreenGapArch", f"{BASE}/cp_green_gap_arch.glb")

# ── Riftstone Arch ──
# 30ft wide × 11'10" high. Manhattan schist, rustic/rough. "Rustic" classification.
clear_scene()
schist = make_mat("Schist", (0.32, 0.30, 0.28), roughness=0.90)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
par = make_mat("Parapet", (0.34, 0.32, 0.29), roughness=0.88)
parts = build_standard_arch("RiftstoneArch", 9.14, 3.61, 16.0, 1.0, 0.55, 0.30, 0.90, 0.40,
                            seg_arc, schist, brick, road, par, na=20)
finalize_and_export(parts, "RiftstoneArch", f"{BASE}/cp_riftstone_arch.glb")

# ── Balcony Bridge ──
# 27ft wide × 11'6" high × 65ft passage. Segmental. Sandstone/cast stone/schist/greywacke.
# Has balcony overlooks (cantilevered viewing platforms on each side).
clear_scene()
stone = make_mat("MixedStone", (0.50, 0.46, 0.40), roughness=0.82)
greywacke = make_mat("Greywacke", (0.42, 0.40, 0.38), roughness=0.84)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
par = make_mat("Parapet", (0.48, 0.44, 0.40), roughness=0.80)
parts = build_standard_arch("BalconyBridge", 8.23, 3.51, 19.81, 0.90, 0.50, 0.30, 1.0, 0.35,
                            seg_arc, stone, brick, road, par)
# Add balcony overlooks (cantilevered platforms on each side at midpoint)
for side in (-1, 1):
    bx = side * (8.23/2 + 0.90 + 0.8)
    box(f"balcony_{side}", bx, 0, 3.51+0.50+0.30+0.05,
        0.8, 1.5, 0.08, greywacke, parts)
    # Balcony railing
    box(f"balcony_rail_{side}", bx, 0, 3.51+0.50+0.30+0.6,
        0.04, 1.5, 0.5, par, parts)
finalize_and_export(parts, "BalconyBridge", f"{BASE}/cp_balcony_bridge.glb")

# ── Oak Bridge ──
# 60ft × 25ft × 12ft. Rebuilt 2009 with steel frame, cast aluminum railings, white oak deck.
# Rustic-style bridge spanning Bank Rock Bay (water crossing, not tunnel).
clear_scene()
oak_wood = make_mat("WhiteOak", (0.45, 0.35, 0.22), roughness=0.80)
steel = make_mat("Steel", (0.35, 0.35, 0.36), roughness=0.50, metallic=0.90)
aluminum = make_mat("Aluminum", (0.55, 0.55, 0.58), roughness=0.40, metallic=0.70)
stone_abut = make_mat("StoneAbutment", (0.48, 0.46, 0.42), roughness=0.82)
parts = []
# Oak Bridge is a flat deck bridge over water — not a tunnel arch
# Steel beam structure with wood deck and rustic-style aluminum railings
SPAN = 18.29; HS = SPAN/2  # 60ft
DECK_W = 7.62; HW = DECK_W/2  # 25ft
DECK_H = 3.66  # 12ft above water
DECK_T = 0.20
BEAM_H = 0.40; BEAM_W = 0.15
RAIL_H = 1.10; RAIL_T = 0.06
# Deck (white oak planks)
box("deck", 0, 0, DECK_H, HS, HW, DECK_T/2, oak_wood, parts)
# Steel beams underneath (3 longitudinal beams)
for beam_y in [-HW+0.3, 0, HW-0.3]:
    box(f"beam_{beam_y:.1f}", 0, beam_y, DECK_H-DECK_T/2-BEAM_H/2,
        HS, BEAM_W/2, BEAM_H/2, steel, parts)
# Cross beams
n_cross = 8
for i in range(n_cross):
    cx = -HS + (i+1)*SPAN/(n_cross+1)
    box(f"xbeam_{i}", cx, 0, DECK_H-DECK_T/2-BEAM_H/2,
        BEAM_W/2, HW, BEAM_H/2, steel, parts)
# Aluminum railings (rustic X-pattern panels)
for side in (-1, 1):
    ry = side * HW
    box(f"rail_{side}", 0, ry, DECK_H+RAIL_H/2,
        HS, RAIL_T/2, RAIL_H/2, aluminum, parts)
    box(f"toprail_{side}", 0, ry, DECK_H+RAIL_H+0.03,
        HS, RAIL_T/2+0.02, 0.04, aluminum, parts)
    box(f"botrail_{side}", 0, ry, DECK_H+0.02,
        HS, RAIL_T/2+0.02, 0.03, aluminum, parts)
# Stone abutments at each end
for end in (-1, 1):
    ax = end * (HS + 1.0)
    box(f"abut_{end}", ax, 0, DECK_H/2, 1.5, HW+0.3, DECK_H/2, stone_abut, parts)
finalize_and_export(parts, "OakBridge", f"{BASE}/cp_oak_bridge.glb")

# ── Eaglevale Bridge ──
# 150ft × 36ft. Double arch — west arch 13'6" × 31ft, east arch 18ft × 33'6".
# Gneiss rock-face random ashlar. Built 1890.
clear_scene()
gneiss = make_mat("Gneiss", (0.48, 0.45, 0.42), roughness=0.84)
brick = make_mat("Brick", (0.55, 0.28, 0.20), roughness=0.85)
road = make_mat("Road", (0.35, 0.33, 0.30), roughness=0.90)
par = make_mat("Parapet", (0.50, 0.47, 0.43), roughness=0.80)
parts = []

TOTAL_L = 45.72; HL = TOTAL_L/2  # 150ft
TOTAL_W = 10.97; HW = TOTAL_W/2  # 36ft
ROAD_T = 0.35; PAR_H = 1.0; PAR_T = 0.40

# West arch: 31ft wide × 13'6" high (bridle path)
W_ARCH_W = 9.45; W_ARCH_H = 4.11
# East arch: 33'6" wide × 18ft high (pedestrian/lake arm)
E_ARCH_W = 10.21; E_ARCH_H = 5.49
# Central pier between the two arches
PIER_W = 2.5

# West arch barrel vault
w_arc = seg_arc(W_ARCH_W/2, W_ARCH_H, 20)
mesh = bpy.data.meshes.new("w_vault"); verts = []; faces = []
# Offset west arch to left side of bridge
w_offset = -(PIER_W/2 + W_ARCH_W/2)
for px, pz in w_arc:
    verts.append((px+w_offset, -HL, pz)); verts.append((px+w_offset, HL, pz))
    d = math.sqrt(px*px + pz*pz)
    at = 0.55
    if d > 0.1: ox, oz = px*(1+at/d), pz*(1+at/d)
    else: ox, oz = px, pz+at
    verts.append((ox+w_offset, -HL, oz)); verts.append((ox+w_offset, HL, oz))
for i in range(len(w_arc)-1):
    b = i*4; nb = (i+1)*4
    faces += [(b,b+1,nb+1,nb), (b+2,nb+2,nb+3,b+3), (b,nb,nb+2,b+2), (b+1,b+3,nb+3,nb+1)]
mesh.from_pydata(verts, [], faces); mesh.update()
obj = bpy.data.objects.new("w_vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(brick); parts.append(obj)

# East arch barrel vault
e_arc = seg_arc(E_ARCH_W/2, E_ARCH_H, 20)
mesh = bpy.data.meshes.new("e_vault"); verts = []; faces = []
e_offset = PIER_W/2 + E_ARCH_W/2
for px, pz in e_arc:
    verts.append((px+e_offset, -HL, pz)); verts.append((px+e_offset, HL, pz))
    d = math.sqrt(px*px + pz*pz)
    at = 0.55
    if d > 0.1: ox, oz = px*(1+at/d), pz*(1+at/d)
    else: ox, oz = px, pz+at
    verts.append((ox+e_offset, -HL, oz)); verts.append((ox+e_offset, HL, oz))
for i in range(len(e_arc)-1):
    b = i*4; nb = (i+1)*4
    faces += [(b,b+1,nb+1,nb), (b+2,nb+2,nb+3,b+3), (b,nb,nb+2,b+2), (b+1,b+3,nb+3,nb+1)]
mesh.from_pydata(verts, [], faces); mesh.update()
obj = bpy.data.objects.new("e_vault", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(brick); parts.append(obj)

# Central pier
max_h = max(W_ARCH_H, E_ARCH_H) + 0.55 + ROAD_T
box("pier", 0, 0, max_h/2, PIER_W/2, HL, max_h/2, gneiss, parts)

# Side walls
left_edge = w_offset - W_ARCH_W/2 - 1.0
right_edge = e_offset + E_ARCH_W/2 + 1.0
box("wall_l", left_edge-0.5, 0, max_h/2, 0.5, HL, max_h/2, gneiss, parts)
box("wall_r", right_edge+0.5, 0, max_h/2, 0.5, HL, max_h/2, gneiss, parts)

# Road deck above everything
deck_top = max_h
total_bridge_w = right_edge - left_edge + 2.0
box("road", (left_edge+right_edge)/2, 0, deck_top+ROAD_T/2,
    total_bridge_w/2, HL+2, ROAD_T/2, road, parts)

# Parapets
for side_x in [left_edge - 0.5, right_edge + 0.5]:
    box(f"par_{side_x:.0f}", side_x, 0, deck_top+ROAD_T+PAR_H/2,
        PAR_T/2, HL+2, PAR_H/2, par, parts)

# Balconies between arches (on buttresses)
for end in (-1, 1):
    bx = 0
    by = end * (HL + 1.0)
    box(f"buttress_{end}", bx, by, deck_top/2, PIER_W/2+0.5, 1.5, deck_top/2, gneiss, parts)

# Face walls for each end
for end in (-1, 1):
    ey = end * HL
    # Simplified: just the spandrel above each arch
    for arch_offset, arch_w, arch_h in [(w_offset, W_ARCH_W, W_ARCH_H), (e_offset, E_ARCH_W, E_ARCH_H)]:
        b = len(parts)
        vf = []; ff = []
        hw = arch_w/2
        vf += [(arch_offset-hw-0.5, ey, arch_h+0.55), (arch_offset+hw+0.5, ey, arch_h+0.55),
               (arch_offset+hw+0.5, ey, deck_top+ROAD_T), (arch_offset-hw-0.5, ey, deck_top+ROAD_T)]
        ff.append((0,1,2,3) if end>0 else (0,3,2,1))
        m = bpy.data.meshes.new(f"spandrel_{end}_{arch_offset:.0f}")
        m.from_pydata(vf, [], ff); m.update()
        o = bpy.data.objects.new(f"spandrel_{end}_{arch_offset:.0f}", m)
        bpy.context.collection.objects.link(o)
        o.data.materials.append(gneiss); parts.append(o)

# Floors for each tunnel
box("floor_w", w_offset, 0, -0.15, W_ARCH_W/2, HL, 0.15, road, parts)
box("floor_e", e_offset, 0, -0.15, E_ARCH_W/2, HL, 0.15, road, parts)

finalize_and_export(parts, "EaglevaleBridge", f"{BASE}/cp_eaglevale_bridge.glb")

print("\n=== All remaining arches exported ===")
