"""
View active grass models side-by-side in Blender.

Usage:
    blender --python scripts/view_grass_models.py

Shows only the 20 models actually used in-game:
  - 16 blade GLBs (4 species x 4 variants) for GPU grass
  - 4 tuft GLBs for medium-distance chunks
"""

import bpy
import os
import math

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "models", "vegetation")

BLADE_SPECIES = ["Lawn", "Shade", "Wild", "Sedge"]
BLADE_VARIANTS = ["", "_Thin", "_Wide", "_Curved"]

TUFTS = [
    ("Tuft_Tiny",     "Lawn\n(Tuft_Tiny)"),
    ("Tuft_Woodland", "Shade\n(Tuft_Woodland)"),
    ("Tuft_Wild",     "Wild\n(Tuft_Wild)"),
    ("Tuft_Meadow",   "Sedge\n(Tuft_Meadow)"),
]

BLADE_SPACING = 0.4
TUFT_SPACING = 1.2
SECTION_GAP = 2.5


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def import_glb(filepath):
    if not os.path.exists(filepath):
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    after = set(bpy.data.objects)
    return list(after - before)


def create_text_label(text, location, size=0.08):
    bpy.ops.object.text_add(location=location)
    txt = bpy.context.active_object
    txt.data.body = text
    txt.data.size = size
    txt.data.align_x = 'CENTER'
    txt.rotation_euler = (math.radians(90), 0, 0)
    return txt


def move_objects(objects, offset):
    roots = [o for o in objects if o.parent is None or o.parent not in objects]
    for obj in roots:
        obj.location.x += offset[0]
        obj.location.y += offset[1]
        obj.location.z += offset[2]


def main():
    print("\n=== Active Grass Model Viewer (20 models) ===\n")
    clear_scene()

    cursor_y = 0.0

    # ---- Section 1: Blades (4 species x 4 variants = 16) ----
    print("Importing 16 blade models...")
    create_text_label("GPU GRASS BLADES", (BLADE_SPACING * 1.5, cursor_y + 0.4, 0), size=0.14)

    variant_labels = ["Base", "Thin", "Wide", "Curved"]
    for col, label in enumerate(variant_labels):
        x = col * BLADE_SPACING
        create_text_label(label, (x, cursor_y + 0.2, 0), size=0.06)

    for row, species in enumerate(BLADE_SPECIES):
        y = cursor_y - row * BLADE_SPACING
        create_text_label(species, (-0.35, y, 0), size=0.06)
        for col, variant in enumerate(BLADE_VARIANTS):
            x = col * BLADE_SPACING
            filename = f"Blade_{species}{variant}.glb"
            filepath = os.path.join(MODELS_DIR, filename)
            objs = import_glb(filepath)
            if objs:
                move_objects(objs, (x, y, 0))
                print(f"  OK: {filename}")
            else:
                print(f"  MISSING: {filename}")

    cursor_y -= len(BLADE_SPECIES) * BLADE_SPACING + SECTION_GAP

    # ---- Section 2: Tufts (4) ----
    print("Importing 4 tuft models...")
    create_text_label("TUFTS (Medium Distance)", (TUFT_SPACING * 1.5, cursor_y + 0.5, 0), size=0.14)

    for i, (filename, label) in enumerate(TUFTS):
        x = i * TUFT_SPACING
        filepath = os.path.join(MODELS_DIR, f"{filename}.glb")
        objs = import_glb(filepath)
        if objs:
            move_objects(objs, (x, cursor_y, 0))
            print(f"  OK: {filename}.glb")
        else:
            print(f"  MISSING: {filename}.glb")
        create_text_label(label, (x, cursor_y - 0.5, 0), size=0.08)

    # ---- Lighting ----
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    bpy.context.active_object.data.energy = 3.0

    bpy.ops.object.light_add(type='AREA', location=(0, -3, 2))
    fill = bpy.context.active_object
    fill.data.energy = 50.0
    fill.data.size = 10.0

    # Set viewport to orthographic
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'ORTHO'
            break

    print("\n=== Done! 20 active models loaded. ===")
    print("Tip: Numpad 7 = top view, Numpad 1 = front view")
    print("     Z > Material Preview to see colors\n")


if __name__ == "__main__":
    main()
