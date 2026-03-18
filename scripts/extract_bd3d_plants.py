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
# (BD3D name, our species name, max face count (0=keep), mirror X, target height m)
# Heights match the existing procedural models so SPECIES scale multipliers stay valid.

EXTRACTIONS = [
    # ── Shrubs ── BD3D "Deciduous bush A" → 7 species
    ("GS Deciduous bush A 1", "Shrub_Spicebush",          4000, False, 2.78),
    ("GS Deciduous bush A 3", "Shrub_WitchHazel",         4000, False, 3.70),
    ("GS Deciduous bush A 2", "Shrub_Viburnum",           4000, False, 2.44),
    ("GS Deciduous bush A 4", "Shrub_Sumac",              4500, False, 4.11),
    ("GS Deciduous bush A 3", "Shrub_Elderberry",         4000, True,  2.22),
    ("GS Deciduous bush A 1", "Shrub_SweetPepperbush",    4000, True,  2.17),
    ("GS Deciduous bush A 2", "Shrub_FloweringRaspberry", 4000, True,  1.73),

    # ── Ferns ── BD3D "Forest ferns" → 4 species
    ("GS Forest ferns A 01",  "Fern_Ostrich",             2000, False, 0.88),
    ("GS Forest ferns A 02",  "Fern_Cinnamon",            2000, False, 0.61),
    ("GS Forest ferns B 01",  "Fern_Christmas",           0,    False, 0.32),
    ("GS Forest ferns B 02",  "Fern_Sensitive",           0,    False, 0.45),
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

def extract_plant(bd3d_name, output_name, max_faces, mirror, target_h):
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

    # ── Center at base (min Z = 0, horizontal center at origin) ──
    cx, cy, min_z = get_mesh_center_base(dup)
    if abs(cx) > 0.001 or abs(cy) > 0.001 or abs(min_z) > 0.001:
        translate_mesh(dup, -cx, -cy, -min_z)

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
    for _, name, _, _, _ in EXTRACTIONS:
        for ext in ['.glb', '.gltf', '.bin']:
            src_path = os.path.join(OUTPUT_DIR, f"{name}{ext}")
            dst_path = os.path.join(BACKUP_DIR, f"{name}{ext}")
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
                backed += 1
    if backed:
        print(f"\nBacked up {backed} existing models to backup_procedural/")

    # Extract each plant
    success = 0
    for bd3d_name, output_name, max_faces, mirror, target_h in EXTRACTIONS:
        print(f"\n[{output_name}] ← '{bd3d_name}'"
              f"  target_f={max_faces or 'keep'}  mirror={mirror}  h={target_h:.2f}m")
        if extract_plant(bd3d_name, output_name, max_faces, mirror, target_h):
            success += 1

    print(f"\n{'=' * 60}")
    print(f"Done: {success}/{len(EXTRACTIONS)} extracted successfully")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
