#!/usr/bin/env python3
"""
Extract BD3D Plant Library meshes as GLBs for undergrowth replacement.

Run: blender4 --background --python scripts/extract_bd3d_plants.py

Pulls real 3D foliage from the BD3D Plant Library (170+ temperate species),
decimates to MultiMesh-friendly poly counts, normalizes to reference heights
matching the existing procedural models, and exports as GLBs with embedded
PBR textures.  The undergrowth shader's `use_texture` mode reads the albedo +
alpha directly from the GLB materials.
"""

import bpy
import os
import sys
import shutil
import math

# ── Paths ──────────────────────────────────────────────────────────────────────

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath or __file__)))
if not os.path.isdir(os.path.join(PROJECT_DIR, "models")):
    PROJECT_DIR = "/home/chris/central-park-walk"
LIBRARY_PATH = os.path.join(PROJECT_DIR, "assets/plant_library/geoscatter_plantlibrary.blend")
OUTPUT_DIR   = os.path.join(PROJECT_DIR, "models/vegetation")
BACKUP_DIR   = os.path.join(OUTPUT_DIR, "backup_procedural")

# ── Extraction map ─────────────────────────────────────────────────────────────
# (BD3D name, our species name, max face count (0=keep), mirror X, target height m, sink fraction)
# Heights match the existing procedural models so SPECIES scale multipliers stay valid.
# sink_frac: fraction of height to push below origin (hides bare stems in grass).
#   Shrubs have ~25-30% bare stem before foliage; sinking 20% hides the gap.
#   Ferns have ~10-20% gap; sinking 8-10% is enough.

EXTRACTIONS = [
    # ── Shrubs ── BD3D "Deciduous bush A" → 7 species
    # Central Park shrubs are maintained/trimmed — use 4-5ft range, not wild max.
    # Builder jitter 0.65-1.25x makes these span roughly 3-6ft in-game.
    ("GS Deciduous bush A 1", "Shrub_Spicebush",          4000, False, 2.50, 0.15),  # real 2-4m, dominant understory
    ("GS Deciduous bush A 3", "Shrub_WitchHazel",         4000, False, 3.00, 0.15),  # real 3-5m
    ("GS Deciduous bush A 2", "Shrub_Viburnum",           4000, False, 2.00, 0.15),  # real 2-3m
    ("GS Deciduous bush A 4", "Shrub_Sumac",              4500, False, 3.00, 0.12),  # real 3-5m, flat-topped
    ("GS Deciduous bush A 3", "Shrub_Elderberry",         4000, True,  2.20, 0.15),  # real 2-3.5m
    ("GS Deciduous bush A 1", "Shrub_SweetPepperbush",    4000, True,  1.60, 0.18),  # real 1-2.5m
    ("GS Deciduous bush A 2", "Shrub_FloweringRaspberry", 4000, True,  1.40, 0.18),  # real 1-2m

    # ── Ferns ── BD3D "Forest ferns" → 4 species
    # Use lower end of real range — builder scale jitter (0.40-1.45x) pushes them up further.
    # These are understory plants, should be knee-to-waist height, never overhead.
    ("GS Forest ferns A 01",  "Fern_Ostrich",             2000, False, 1.20, 0.08),  # real 1-1.8m, tallest fern
    ("GS Forest ferns A 02",  "Fern_Cinnamon",            2000, False, 0.80, 0.08),  # real 0.6-1.2m
    ("GS Forest ferns B 01",  "Fern_Christmas",           0,    False, 0.32, 0.06),  # real 0.3-0.6m, stays
    ("GS Forest ferns B 02",  "Fern_Sensitive",           0,    False, 0.45, 0.06),  # real 0.3-1m, use low

    # ── Tall herbs ── BD3D "Autumn plant" series → tall upright herbs
    # Heights calibrated to real botanical midpoints
    ("GS Autumn plant A 05",  "Herb_Pokeweed",            2500, False, 1.50, 0.12),  # real 1.2-3m; use low-mid (jitter amplifies)
    ("GS Autumn plant B 01",  "Herb_JapaneseKnotweed",    4000, False, 2.20, 0.15),  # real 2-4.5m; tallest herb, keep big
    ("GS Autumn plant A 04",  "Herb_JoePyeWeed",          1800, False, 1.50, 0.12),  # real 1.2-3m; shoulder height base
    ("GS Autumn plant A 04",  "Herb_Ironweed",            1800, True,  1.40, 0.12),  # real 1.2-2.4m

    # ── Medium herbs ── smaller leafy forms (waist height and below)
    ("GS Autumn plant A 03",  "Herb_Mugwort",             1200, False, 0.80, 0.10),  # real 0.6-1.5m
    ("GS Autumn plant A 02",  "Herb_WhiteSnakeroot",      900,  False, 0.90, 0.10),  # real 0.5-1.5m, taller than wood aster
    ("GS Autumn plant B 01",  "Herb_Burdock",             4000, True,  0.80, 0.15),  # real 0.6-1.5m

    # ── Flowering herbs ── BD3D meadow flowers
    ("GS Dryland meadow flower 01", "Herb_Coneflower",    1400, False, 2.00, 0.08),  # real 1.5-3m; stands above most wildflowers
    ("GS Dryland meadow flower 02", "Herb_CardinalFlower", 900, False, 0.70, 0.08),  # real 0.6-1m
    ("GS PaperWhite",         "Herb_RoseMallow",          3000, False, 1.20, 0.10),  # real 1-2m

    # ── Low herbs ── BD3D nettles for woodland floor species
    ("GS Nettle 02",          "Herb_WhiteWoodAster",      1800, False, 0.45, 0.06),  # real 0.3-0.6m, sprawling
    ("GS Nettle 01",          "Herb_Jewelweed",           2500, False, 0.80, 0.08),  # real 0.6-1.5m

    # ── Grass ── BD3D grass clump for bottlebrush
    ("GS Grass Clump 01",     "Grass_Bottlebrush",        3000, False, 0.70, 0.04),  # real 0.6-1.4m, use low end

    # ── Wetland ── BD3D upright plants for emergent aquatic species
    ("GS type D plant 01",    "Wetland_Cattail",          4000, False, 2.20, 0.10),  # real 1.5-3m, sword leaves + catkins
    ("GS type D plant 02",    "Wetland_YellowIris",       4000, False, 1.00, 0.08),  # real 0.6-1.5m, sword leaves
    ("GS Dryland meadow flower 01", "Wetland_LizardsTail", 1400, True, 0.80, 0.06), # real 0.6-1.2m, drooping spikes
    ("GS Grass Wild Clump Dry 01",  "Wetland_Phragmites", 5000, False, 3.50, 0.08), # real 2-5m, feathery plumes

    # ── Forest floor ── seedlings and ground cover for woodland enrichment
    ("GS Forest seedlings 01", "ForestFloor_Seedling_A",  0,    False, 0.16, 0.02),
    ("GS Forest seedlings 02", "ForestFloor_Seedling_B",  0,    False, 0.23, 0.02),
    ("GS Forest seedlings 03", "ForestFloor_Seedling_C",  0,    False, 0.26, 0.02),

    # ── Lawn/meadow grass ── BD3D grass clumps for Terrain3D instancer
    ("GS Grass Clump 01",      "Grass_Clump_01",          1500, False, 0.20, 0.02),
    ("GS Grass Clump 02",      "Grass_Clump_02",          1500, False, 0.22, 0.02),
    ("GS Grass Clump 03",      "Grass_Clump_03",          1500, False, 0.18, 0.02),
    ("GS Grass Duo 01",        "Grass_Duo_01",            0,    False, 0.15, 0.01),
    ("GS Grass Duo 02",        "Grass_Duo_02",            1500, False, 0.18, 0.01),
    ("GS Grass tiny 01",       "Grass_Tiny_01",           0,    False, 0.08, 0.01),
    ("GS Grass 01",            "Grass_Tall_01",           2000, False, 0.35, 0.03),
    ("GS Grass 02",            "Grass_Tall_02",           2000, False, 0.30, 0.03),
    ("GS Grass Wild Clump 01", "Grass_Wild_Clump_01",     2500, False, 0.45, 0.04),
    ("GS Grass Wild Clump 02", "Grass_Wild_Clump_02",     2000, False, 0.40, 0.04),
    ("GS Dryland grass small",  "Grass_Dryland_Small",    2000, False, 0.15, 0.02),
    ("GS Dryland grass medium", "Grass_Dryland_Medium",   3000, False, 0.30, 0.03),
    ("GS Grass Dry 01",        "Grass_Dry_01",           2000, False, 0.30, 0.03),  # seasonal dead grass

    # ── Mowed lawn ── manicured park lawn (formal areas, sports fields)
    ("GS Lawn mowed 01",       "Lawn_Mowed_01",           0,   False, 0.04, 0.00),
    ("GS Lawn mowed 02",       "Lawn_Mowed_02",           0,   False, 0.03, 0.00),
    ("GS Lawn mowed 03",       "Lawn_Mowed_03",           0,   False, 0.04, 0.00),

    # ── Clovers ── lawn and woodland ground cover
    ("GS Clovers 01",          "Clover_Lawn_01",          1500, False, 0.06, 0.01),
    ("GS Clovers 02",          "Clover_Lawn_02",          1500, False, 0.06, 0.01),
    ("GS Forest clover 01",    "Clover_Forest_01",        0,    False, 0.05, 0.01),
    ("GS Forest clover 02",    "Clover_Forest_02",        1500, False, 0.08, 0.01),

    # ── Dandelions ── common lawn weeds
    ("GS Dandelion 01",        "Dandelion_01",            0,    False, 0.10, 0.01),
    ("GS Dandelion 02",        "Dandelion_02",            1500, False, 0.12, 0.01),

    # ── Particle-grade grass ── heavily decimated for Terrain3D GPU particles
    # Same BD3D sources at ~100-300 faces for mass instancing at 0.2-0.5m spacing.
    # Lawn variants (maintained grass zones)
    ("GS Lawn mowed 01",       "Tuft_Lawn",               200, False, 0.05, 0.01),
    ("GS Lawn mowed 02",       "Tuft_Lawn_B",             200, False, 0.04, 0.01),
    ("GS Lawn mowed 03",       "Tuft_Lawn_C",             200, False, 0.05, 0.01),
    # Meadow/clump variants (accent on maintained lawns)
    ("GS Grass Clump 01",      "Tuft_Meadow",             250, False, 0.18, 0.02),
    ("GS Grass Clump 02",      "Tuft_Meadow_B",           250, False, 0.20, 0.02),
    ("GS Grass Clump 03",      "Tuft_Meadow_C",           250, False, 0.16, 0.02),
    # Wild/tall variants (nature reserve, unmowed areas)
    ("GS Grass Wild Clump 01", "Tuft_Wild",               300, False, 0.35, 0.03),
    ("GS Grass Wild Clump 02", "Tuft_Wild_B",             300, False, 0.40, 0.03),
    ("GS Grass 01",            "Tuft_Tall",               200, False, 0.30, 0.02),
    ("GS Grass 02",            "Tuft_Tall_B",             200, False, 0.25, 0.02),
    # Woodland floor variants (sparse forest grass)
    ("GS Grass Duo 01",        "Tuft_Woodland",           150, False, 0.08, 0.01),
    ("GS Grass Duo 02",        "Tuft_Woodland_B",         150, False, 0.07, 0.01),
    ("GS Grass tiny 01",       "Tuft_Tiny",               100, False, 0.06, 0.01),
    # Clover patches (lawn accent, spring-summer)
    ("GS Clovers 01",          "Tuft_Clover",             200, False, 0.05, 0.01),
    ("GS Clovers 02",          "Tuft_Clover_B",           200, False, 0.05, 0.01),
    ("GS Forest clover 01",    "Tuft_Clover_Forest",      150, False, 0.04, 0.01),
    # Dandelion (lawn weed accent, spring)
    ("GS Dandelion 01",        "Tuft_Dandelion",          200, False, 0.08, 0.01),
    ("GS Dandelion 02",        "Tuft_Dandelion_B",        200, False, 0.10, 0.01),
    # Dry/seasonal (autumn-winter accent)
    ("GS Dryland grass small",  "Tuft_Dry_Small",         150, False, 0.12, 0.01),
    ("GS Dryland grass medium", "Tuft_Dry_Medium",        200, False, 0.25, 0.02),
    ("GS Grass Dry 01",        "Tuft_Dead",               200, False, 0.25, 0.02),

    # ── Fallen leaves ── seasonal ground litter
    ("GS Forest dead leaves 01", "DeadLeaves_Forest_01",  0,    False, 0.03, 0.00),
    ("GS Forest dead leaves 02", "DeadLeaves_Forest_02",  2000, False, 0.04, 0.00),
    ("GS Autumn dead leaves 01", "DeadLeaves_Autumn_01",  0,    False, 0.03, 0.00),
    ("GS Autumn dead leaves 02", "DeadLeaves_Autumn_02",  0,    False, 0.04, 0.00),
    ("GS Leaves 01",            "Leaves_Scattered_01",    0,    False, 0.02, 0.00),

    # ── Fallen branches ── woodland floor debris
    ("GS Forest branches 01",  "Branch_Forest_01",        0,    False, 0.08, 0.00),
    ("GS Forest branches 02",  "Branch_Forest_02",        0,    False, 0.10, 0.00),
    ("GS Dryland branches 01", "Branch_Dry_01",           0,    False, 0.08, 0.00),

    # ── Moss ── rock and tree base cover
    ("GS Forest moss 01",      "Moss_Forest_01",          0,    False, 0.03, 0.00),
    ("GS Forest moss 02",      "Moss_Forest_02",          0,    False, 0.04, 0.00),

    # ── Small weeds ── path edges and disturbed ground
    ("GS Weed 01",             "Weed_Small_01",           0,    False, 0.08, 0.01),
    ("GS Weed 02",             "Weed_Small_02",           0,    False, 0.10, 0.01),
    ("GS type A weed 01",      "Weed_TypeA_01",           0,    False, 0.06, 0.01),
    ("GS type A weed 02",      "Weed_TypeA_02",           0,    False, 0.08, 0.01),

    # ── Young trees ── woodland understory saplings
    ("GS Forest young A 01",   "Sapling_Deciduous_01",    1500, False, 0.50, 0.04),
    ("GS Forest young A 02",   "Sapling_Deciduous_02",    2500, False, 0.90, 0.06),
    ("GS Forest young B 01",   "Sapling_Conifer_01",      2000, False, 0.60, 0.04),
    ("GS Forest young B 02",   "Sapling_Conifer_02",      3000, False, 1.00, 0.06),
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def deselect_all():
    """Deselect all objects."""
    for obj in bpy.data.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def get_mesh_height(obj):
    """Height of the object's bounding box in local Z."""
    bb = obj.bound_box
    zs = [v[2] for v in bb]
    return max(zs) - min(zs)


def get_mesh_center_base(obj):
    """Returns (center_x, center_y, min_z) from bounding box."""
    bb = obj.bound_box
    xs = [v[0] for v in bb]
    ys = [v[1] for v in bb]
    zs = [v[2] for v in bb]
    return (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)


def apply_transforms(obj):
    """Apply location, rotation, scale transforms."""
    deselect_all()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def translate_mesh(obj, dx, dy, dz):
    """Move all vertices by offset (in edit mode for clean transforms)."""
    deselect_all()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.transform.translate(value=(dx, dy, dz))
    bpy.ops.object.mode_set(mode='OBJECT')


# ── Material helpers ────────────────────────────────────────────────────────────

def _find_node(mat, node_type):
    """Find first node of given type in material."""
    if mat and mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == node_type:
                return node
    return None


def _trace_back_to_image(node_tree, socket, depth=0):
    """Recursively trace from an input socket back through the node chain
    to find the first TEX_IMAGE node.  BD3D materials chain through
    HueSatVal, ColorRamp, Mix, etc. before reaching the BSDF."""
    if depth > 10:
        return None
    for link in node_tree.links:
        if link.to_socket == socket:
            from_node = link.from_node
            if from_node.type == 'TEX_IMAGE' and from_node.image:
                return from_node.image
            # Keep tracing through intermediate nodes
            for inp in from_node.inputs:
                if inp.type in ('RGBA', 'VALUE', 'VECTOR'):
                    result = _trace_back_to_image(node_tree, inp, depth + 1)
                    if result:
                        return result
    return None


def _find_source_image(mat):
    """Find the albedo source image in a (possibly complex) BD3D material.
    Traces from each Principled BSDF's Base Color input back through
    the node chain.  Falls back to finding ANY TEX_IMAGE in the tree."""
    if not mat or not mat.use_nodes:
        return None
    tree = mat.node_tree
    # Try tracing from each BSDF's Base Color input
    for node in tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bc_input = node.inputs.get('Base Color')
            if bc_input:
                img = _trace_back_to_image(tree, bc_input)
                if img:
                    return img
    # Fallback: first TEX_IMAGE with reasonable dimensions (likely the albedo)
    best = None
    best_pixels = 0
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            pixels = node.image.size[0] * node.image.size[1]
            if pixels > best_pixels:
                best = node.image
                best_pixels = pixels
    return best


# ── Core extraction ────────────────────────────────────────────────────────────

def extract_plant(bd3d_name, output_name, max_faces, mirror, target_h, sink_frac=0.0):
    """Extract, decimate, normalize, and export one plant as GLB."""

    src = bpy.data.objects.get(bd3d_name)
    if not src:
        print(f"  !! '{bd3d_name}' not found — skipping")
        return False

    # Duplicate object + mesh data
    dup = src.copy()
    dup.data = src.data.copy()
    dup.name = output_name

    # Simplify materials: keep only albedo texture (for leaf alpha cutout),
    # strip all PBR channels (normal, roughness, metallic) to keep GLB small.
    # Our custom Godot shader handles all shading — we just need color + alpha.
    for i, slot in enumerate(src.material_slots):
        if slot.material:
            orig = slot.material
            simple = bpy.data.materials.new(name=f"{output_name}_mat{i}")
            simple.use_nodes = True
            tree = simple.node_tree
            bsdf = tree.nodes.get("Principled BSDF")
            if bsdf is None:
                bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")

            # Trace through BD3D node chains to find the source image texture.
            # BD3D materials go: TexImage → HueSatVal → HueSatVal → BSDF Base Color
            src_img = _find_source_image(orig)
            if src_img:
                # Copy and downsize for GLB efficiency (1024 max)
                img_copy = src_img.copy()
                max_dim = 1024
                if img_copy.size[0] > max_dim or img_copy.size[1] > max_dim:
                    aspect = img_copy.size[0] / max(img_copy.size[1], 1)
                    if img_copy.size[0] > img_copy.size[1]:
                        img_copy.scale(max_dim, int(max_dim / aspect))
                    else:
                        img_copy.scale(int(max_dim * aspect), max_dim)
                tex_node = tree.nodes.new("ShaderNodeTexImage")
                tex_node.image = img_copy
                tree.links.new(tex_node.outputs['Color'],
                               bsdf.inputs['Base Color'])
                tree.links.new(tex_node.outputs['Alpha'],
                               bsdf.inputs['Alpha'])
                simple.blend_method = 'CLIP'
                simple.alpha_threshold = 0.4
            else:
                # No texture found — use base color from original BSDF
                orig_bsdf = _find_node(orig, 'BSDF_PRINCIPLED')
                if orig_bsdf:
                    bc = orig_bsdf.inputs['Base Color'].default_value
                    bsdf.inputs['Base Color'].default_value = bc

            dup.data.materials[i] = simple

    # Link to scene root collection (not a BD3D sub-collection)
    bpy.context.scene.collection.objects.link(dup)
    apply_transforms(dup)

    # ── Mirror (creates distinct variant from same base) ──
    if mirror:
        dup.scale.x = -1.0
        apply_transforms(dup)
        # Fix flipped normals from negative scale
        deselect_all()
        bpy.context.view_layer.objects.active = dup
        dup.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')

    # ── Triangulate first (GLB is always triangulated anyway) ──
    deselect_all()
    bpy.context.view_layer.objects.active = dup
    dup.select_set(True)
    tri_mod = dup.modifiers.new("Tri", 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=tri_mod.name)

    # ── Decimate ──
    orig_faces = len(dup.data.polygons)
    if max_faces > 0 and orig_faces > max_faces:
        ratio = max_faces / orig_faces
        mod = dup.modifiers.new("Decimate", 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        deselect_all()
        bpy.context.view_layer.objects.active = dup
        dup.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        new_faces = len(dup.data.polygons)
        # Second pass if still over target (triangulation can inflate count)
        if new_faces > max_faces * 1.15:
            ratio2 = max_faces / new_faces
            mod2 = dup.modifiers.new("Decimate2", 'DECIMATE')
            mod2.decimate_type = 'COLLAPSE'
            mod2.ratio = ratio2
            bpy.ops.object.modifier_apply(modifier=mod2.name)
            new_faces = len(dup.data.polygons)
        print(f"  Decimated {orig_faces:,} → {new_faces:,} faces (target {max_faces:,})")

    # ── Normalize height ──
    cur_h = get_mesh_height(dup)
    if cur_h > 0.001 and target_h > 0:
        scale = target_h / cur_h
        dup.scale = (scale, scale, scale)
        apply_transforms(dup)

    # ── Center at base, then sink into ground ──
    # min_z → 0, then shift down by sink_frac of total height so bare stems
    # disappear into the grass layer instead of floating above their shadow.
    cur_h = get_mesh_height(dup)
    sink_amount = cur_h * sink_frac
    cx, cy, min_z = get_mesh_center_base(dup)
    translate_mesh(dup, -cx, -cy, -min_z + sink_amount)
    if sink_amount > 0.001:
        print(f"  Sunk {sink_amount:.2f}m ({sink_frac*100:.0f}% of {cur_h:.2f}m) into ground")

    # ── Export GLB ──
    out_path = os.path.join(OUTPUT_DIR, f"{output_name}.glb")

    # Ensure depsgraph is up to date after all edits
    bpy.context.view_layer.update()

    # Deselect everything, then select ONLY our target
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = dup
    dup.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        use_selection=True,
        export_format='GLB',
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
        export_vertex_color='ACTIVE',
        export_apply=True,
    )

    final_faces = len(dup.data.polygons)
    final_verts = len(dup.data.vertices)
    final_h = get_mesh_height(dup)
    fsize = os.path.getsize(out_path) / 1024

    print(f"  → {output_name}.glb  {fsize:.0f} KB  v={final_verts:,}  f={final_faces:,}  h={final_h:.2f}m")

    # Clean up
    bpy.data.objects.remove(dup, do_unlink=True)
    return True


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("BD3D Plant Library → Central Park Walk GLB Extraction")
    print("=" * 60)
    print(f"Library : {LIBRARY_PATH}")
    print(f"Output  : {OUTPUT_DIR}")

    if not os.path.isfile(LIBRARY_PATH):
        print(f"\n!! Library not found: {LIBRARY_PATH}")
        sys.exit(1)

    # Open the BD3D library
    print("\nOpening BD3D library (1.2 GB) ...")
    bpy.ops.wm.open_mainfile(filepath=LIBRARY_PATH)
    print(f"Loaded {len(bpy.data.objects)} objects, {len(bpy.data.materials)} materials")

    # Unpack all images so GLB exporter can embed them
    print("Unpacking images for GLB embedding ...")
    try:
        bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    except Exception as e:
        print(f"  (unpack note: {e} — continuing with packed images)")

    # Backup existing models
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backed = 0
    for entry in EXTRACTIONS:
        name = entry[1]
        for ext in ['.glb', '.gltf', '.bin']:
            src_path = os.path.join(OUTPUT_DIR, f"{name}{ext}")
            dst_path = os.path.join(BACKUP_DIR, f"{name}{ext}")
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
                backed += 1
    if backed:
        print(f"\nBacked up {backed} existing models to backup_procedural/")

    # Optional filter: blender4 --background --python extract_bd3d_plants.py -- --only=Tuft_
    filter_prefix = ""
    for arg in sys.argv:
        if arg.startswith("--only="):
            filter_prefix = arg.split("=", 1)[1]
    if filter_prefix:
        print(f"\nFilter: only extracting names starting with '{filter_prefix}'")

    # Extract each plant
    success = 0
    skipped = 0
    entries = EXTRACTIONS
    for entry in entries:
        bd3d_name, output_name, max_faces, mirror, target_h = entry[:5]
        sink_frac = entry[5] if len(entry) > 5 else 0.0
        if filter_prefix and not output_name.startswith(filter_prefix):
            skipped += 1
            continue
        print(f"\n[{output_name}] ← '{bd3d_name}'"
              f"  target_f={max_faces or 'keep'}  mirror={mirror}  h={target_h:.2f}m  sink={sink_frac:.0%}")
        if extract_plant(bd3d_name, output_name, max_faces, mirror, target_h, sink_frac):
            success += 1

    total = len(entries) - skipped
    print(f"\n{'=' * 60}")
    print(f"Done: {success}/{total} extracted successfully" +
          (f" ({skipped} skipped by filter)" if skipped else ""))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
