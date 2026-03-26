#!/usr/bin/env python3
"""
convert_gscatter_to_glb.py — Extract game-ready GLB meshes from Gscatter plant assets.

Gscatter .gscatter files are zip archives containing pre-realized Blender meshes
at multiple LOD levels. This script:
  1. Extracts each .gscatter zip
  2. Opens the data.blend file
  3. Reads meta/*.json to discover variant names
  4. Catalogs mesh objects by variant/LOD, auto-selects LOD matching tri budget
  5. Optionally decimates to meet budget, resizes textures to 1024px
  6. Exports individual plants as GLB

Usage (run via Blender):
    blender4 --background --factory-startup --python scripts/convert_gscatter_to_glb.py

Object naming in gscatter blends:
    {LatinName}_{id}_{Variant}_lod{N}_{suffix}[.NNN]
    e.g. PoaPratensis_7jcty_Big_lod2_OL.003
         AthyriumFilixFemina_9hda3_Big_lod0_0
"""

import bpy
import json
import os
import re
import sys
import tempfile
import zipfile
from collections import defaultdict

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(PROJECT_DIR, "tools", "gscatter_assets", "plants")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation", "gscatter")

# Target tri budget per individual plant mesh
TRI_BUDGET_UNDERGROWTH = 500
TRI_BUDGET_GRASS = 200

# Max texture resolution for exported GLBs (gscatter ships 4K+, way too big)
MAX_TEX_SIZE = 1024

# Priority species (filename prefix, output name, category)
PRIORITY_SPECIES = [
    ("Smooth Meadow-grass_PoaPratensis_7jcty", "PoaPratensis", "grass"),
    ("Red Fescue_FestucaRubra_gvgyu", "FestucaRubra", "grass"),
    ("Orchard Grass_DactylisGlomerata_bb1ly", "DactylisGlomerata_A", "grass"),
    ("Orchard Grass_DactylisGlomerata_hznoe", "DactylisGlomerata_B", "grass"),
    ("Lady Fern_AthyriumFilixFemina_9hda3", "LadyFern", "undergrowth"),
    ("White Clover_TrifoliumRepens_rmtkt", "WhiteClover", "undergrowth"),
    ("Common Ivy_HederaHelix_73gds", "CommonIvy", "undergrowth"),
    ("Bank Haircap Moss_PolytrichumFormosum_r678f", "BankHaircapMoss", "undergrowth"),
    ("Broadleaf Plantain_PlantagoMajor_932sp", "BroadleafPlantain_A", "undergrowth"),
    ("Broadleaf Plantain_PlantagoMajor_kthc2", "BroadleafPlantain_B", "undergrowth"),
    # Flowers
    ("Daffodil_NarcissusPseudonarcissus_g8fi3", "Daffodil", "undergrowth"),
    ("Snowdrop_GalanthusNivalis_y38rf", "Snowdrop", "undergrowth"),
    ("Spring Crocus_CrocusVernus_iy1yi", "Crocus", "undergrowth"),
    ("Tulip_TulipaPraestans_7m0f0", "Tulip", "undergrowth"),
]


# ── Helpers ────────────────────────────────────────────────────────────────

def find_gscatter_file(prefix):
    """Find the .gscatter file matching a prefix."""
    for f in os.listdir(ASSETS_DIR):
        if f.startswith(prefix) and f.endswith("_Blender.gscatter"):
            return os.path.join(ASSETS_DIR, f)
    return None


def extract_gscatter(gscatter_path, tmp_dir):
    """Extract .gscatter zip, return (blend_path, variant_names)."""
    with zipfile.ZipFile(gscatter_path, 'r') as zf:
        zf.extractall(tmp_dir)

    blend_path = None
    variant_names = []

    for root, dirs, files in os.walk(tmp_dir):
        for f in files:
            if f == "data.blend":
                blend_path = os.path.join(root, f)
        if os.path.basename(root) == "meta":
            for f in files:
                if f.endswith(".json"):
                    variant_names.append(f.replace(".json", ""))

    return blend_path, variant_names


def catalog_objects(known_variants):
    """Catalog all mesh objects by variant -> lod -> list of objects.
    Uses known_variants from meta/*.json to parse names correctly."""
    catalog = defaultdict(lambda: defaultdict(list))

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        name = obj.name
        matched_variant = None
        lod_num = None
        sub_index = 0

        # Try each known variant name
        for v in known_variants:
            # Pattern: _{Variant}_lod{N}_{suffix}[.NNN]
            pattern = rf'_{re.escape(v)}_lod(\d+)(?:_\w+)?(?:\.(\d+))?$'
            m = re.search(pattern, name)
            if m:
                matched_variant = v
                lod_num = int(m.group(1))
                sub_index = int(m.group(2)) if m.group(2) else 0
                break

            # Pattern without suffix: _{Variant}_lod{N}_{digit}
            pattern2 = rf'_{re.escape(v)}_lod(\d+)_(\d+)$'
            m2 = re.search(pattern2, name)
            if m2:
                matched_variant = v
                lod_num = int(m2.group(1))
                sub_index = int(m2.group(2))
                break

        if matched_variant is None:
            continue

        obj.data.calc_loop_triangles()
        catalog[matched_variant][lod_num].append({
            "obj": obj,
            "name": name,
            "tris": len(obj.data.loop_triangles),
            "verts": len(obj.data.vertices),
            "sub": sub_index,
        })

    # Sort by sub-index
    for variant in catalog:
        for lod in catalog[variant]:
            catalog[variant][lod].sort(key=lambda x: x["sub"])

    return catalog


def find_best_lod(lod_dict, tri_budget):
    """Find the lowest LOD number where avg individual tris <= budget.
    If none meets budget, return the highest LOD (most reduced).
    Returns (lod_num, avg_tris)."""
    max_lod = max(lod_dict.keys())
    max_lod_avg = sum(o["tris"] for o in lod_dict[max_lod]) / len(lod_dict[max_lod])

    for lod_num in sorted(lod_dict.keys()):
        objects = lod_dict[lod_num]
        avg = sum(o["tris"] for o in objects) / len(objects) if objects else 0
        if avg <= tri_budget:
            return lod_num, avg

    return max_lod, max_lod_avg


def resize_textures():
    """Downsize all packed images to MAX_TEX_SIZE to reduce GLB file size."""
    for img in bpy.data.images:
        if img.packed_file is None:
            continue
        if img.size[0] <= MAX_TEX_SIZE and img.size[1] <= MAX_TEX_SIZE:
            continue
        # Scale down
        old_w, old_h = img.size[0], img.size[1]
        ratio = MAX_TEX_SIZE / max(old_w, old_h)
        new_w = max(1, int(old_w * ratio))
        new_h = max(1, int(old_h * ratio))
        img.scale(new_w, new_h)
        img.pack()
        print(f"    Resized {img.name}: {old_w}x{old_h} -> {new_w}x{new_h}", flush=True)


def decimate_object(obj, target_tris):
    """Add decimate modifier to reduce tri count. Returns new tri count."""
    obj.data.calc_loop_triangles()
    current = len(obj.data.loop_triangles)
    if current <= target_tris:
        return current

    ratio = target_tris / current
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    mod.use_collapse_triangulate = True

    # Apply modifier
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def export_glb(obj, filepath):
    """Export a single object as GLB."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
    )


def process_species(gscatter_path, output_name, category, tmp_base):
    """Process one species: extract, catalog, export at best LOD."""
    print(f"\n{'='*60}", flush=True)
    print(f"Processing: {output_name} ({category})", flush=True)
    print(f"  Source: {os.path.basename(gscatter_path)}", flush=True)

    tri_budget = TRI_BUDGET_GRASS if category == "grass" else TRI_BUDGET_UNDERGROWTH

    # Extract
    tmp_dir = os.path.join(tmp_base, output_name)
    os.makedirs(tmp_dir, exist_ok=True)
    blend_path, variant_names = extract_gscatter(gscatter_path, tmp_dir)
    if not blend_path:
        print(f"  ERROR: No data.blend found!", flush=True)
        return []

    print(f"  Variants from meta: {variant_names}", flush=True)

    # Open blend
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    # Resize textures once (applies to all exports from this blend)
    resize_textures()

    # Catalog objects using known variant names
    catalog = catalog_objects(variant_names)
    if not catalog:
        print(f"  ERROR: No mesh objects matched variant names!", flush=True)
        return []

    print(f"  Matched variants: {list(catalog.keys())}", flush=True)

    results = []

    for variant in sorted(catalog.keys()):
        lod_dict = catalog[variant]
        lod_nums = sorted(lod_dict.keys())
        print(f"\n  Variant '{variant}': LODs {lod_nums}", flush=True)

        # Print tri summary per LOD
        for lod_num in lod_nums:
            objs = lod_dict[lod_num]
            avg = sum(o["tris"] for o in objs) / len(objs) if objs else 0
            print(f"    LOD {lod_num}: {len(objs)} objs, avg {avg:.0f} tris/obj", flush=True)

        # Find best LOD
        best_lod, avg_tris = find_best_lod(lod_dict, tri_budget)
        budget_met = avg_tris <= tri_budget
        print(f"    -> LOD {best_lod} (avg {avg_tris:.0f} tris, budget {tri_budget}, {'OK' if budget_met else 'OVER — will decimate'})", flush=True)

        objects = lod_dict[best_lod]

        # Export individual plants (pick up to 4 for variety, prefer lower tri count)
        objects_sorted = sorted(objects, key=lambda x: x["tris"])
        export_count = min(len(objects_sorted), 4)

        for i in range(export_count):
            info = objects_sorted[i]
            obj = info["obj"]

            # Decimate if over budget
            if info["tris"] > tri_budget:
                new_tris = decimate_object(obj, tri_budget)
                print(f"    Decimated {info['name']}: {info['tris']} -> {new_tris} tris", flush=True)
                info["tris"] = new_tris
                info["verts"] = len(obj.data.vertices)

            filename = f"{output_name}_{variant}_{i}.glb"
            filepath = os.path.join(OUTPUT_DIR, filename)
            export_glb(obj, filepath)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"    Exported: {filename} ({info['tris']} tris, {info['verts']} verts, {size_kb:.0f} KB)", flush=True)
            results.append({
                "file": filename,
                "variant": variant,
                "lod": best_lod,
                "tris": info["tris"],
                "verts": info["verts"],
                "size_kb": size_kb,
            })

    return results


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60, flush=True)
    print("Gscatter -> GLB Converter", flush=True)
    print(f"Assets dir: {ASSETS_DIR}", flush=True)
    print(f"Output dir: {OUTPUT_DIR}", flush=True)
    print(f"Texture max: {MAX_TEX_SIZE}px", flush=True)
    print("=" * 60, flush=True)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tmp_base = tempfile.mkdtemp(prefix="gscatter_conv_")
    print(f"Temp dir: {tmp_base}", flush=True)

    all_results = {}

    for prefix, output_name, category in PRIORITY_SPECIES:
        gscatter_path = find_gscatter_file(prefix)
        if not gscatter_path:
            print(f"\nWARNING: No .gscatter file found for '{prefix}'", flush=True)
            continue

        try:
            results = process_species(gscatter_path, output_name, category, tmp_base)
            if results:
                all_results[output_name] = results
        except Exception as e:
            print(f"\nERROR processing {output_name}: {e}", flush=True)
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n{'='*60}", flush=True)
    print("SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    total_files = 0
    for species, results in sorted(all_results.items()):
        avg_tris = sum(r["tris"] for r in results) / len(results) if results else 0
        avg_kb = sum(r["size_kb"] for r in results) / len(results) if results else 0
        total_files += len(results)
        print(f"  {species}: {len(results)} GLBs, avg {avg_tris:.0f} tris, avg {avg_kb:.0f} KB", flush=True)
    print(f"\nTotal: {total_files} GLB files exported to {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
    sys.exit(0)
