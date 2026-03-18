"""Batch-upgrade furniture model scripts to use PBR materials.

For each script listed below, this:
1. Adds the pbr_utils import
2. Replaces flat bpy.data.materials.new() calls with make_pbr_material()
3. Adds export_image_format='JPEG' to GLB export
4. Re-runs the script with Blender 4.5 to regenerate the GLB

Run: blender4 --background --python scripts/batch_upgrade_pbr.py
"""

import os
import sys
import re
import subprocess

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = "/home/chris/blender-4.5.8-linux-x64/blender"

# Scripts to upgrade: (filename_without_make_, primary_material_set, tint_rgb, tint_strength)
UPGRADES = [
    # Cast iron items
    ("wire_trash_can",    "cast_iron", (0.08, 0.08, 0.09), 0.6),
    ("drain_grate",       "cast_iron", (0.10, 0.10, 0.10), 0.7),
    ("tree_pit_grate",    "cast_iron", (0.08, 0.08, 0.08), 0.7),
    ("call_box",          "cast_iron", (0.06, 0.06, 0.07), 0.6),
    ("dog_run_fence",     "cast_iron", (0.12, 0.12, 0.10), 0.5),
    ("reservoir_fence",   "cast_iron", (0.05, 0.05, 0.06), 0.7),
    ("flagpole",          "cast_iron", (0.06, 0.06, 0.06), 0.65),
    ("baseball_backstop", "cast_iron", (0.12, 0.12, 0.10), 0.5),
    ("basketball_hoop",   "cast_iron", (0.08, 0.08, 0.09), 0.6),
    ("soccer_goal",       "cast_iron", (0.85, 0.85, 0.82), 0.4),  # white painted
    ("tennis_net",        "cast_iron", (0.10, 0.12, 0.08), 0.5),  # green painted
    ("swing_set",         "cast_iron", (0.08, 0.08, 0.09), 0.6),
    ("play_structure",    "cast_iron", (0.15, 0.10, 0.08), 0.5),
    ("fitness_station",   "cast_iron", (0.08, 0.08, 0.09), 0.6),
    ("water_tower",       "cast_iron", (0.35, 0.28, 0.22), 0.5),  # wood + iron
    # Stone items
    ("curb_ramp",         "concrete", (0.55, 0.53, 0.50), 0.4),
    ("stone_urn",         "granite",  (0.52, 0.50, 0.47), 0.35),
    ("mile_marker",       "granite",  (0.52, 0.50, 0.47), 0.35),
    ("balustrade",        "granite",  (0.52, 0.50, 0.47), 0.35),
    ("stone_weir",        "granite",  (0.45, 0.42, 0.38), 0.4),
    ("handball_wall",     "concrete", (0.55, 0.53, 0.50), 0.4),
    # Wood items
    ("dana_pier",         "weathered_wood", (0.40, 0.30, 0.20), 0.4),
    ("info_kiosk",        "cast_iron", (0.06, 0.06, 0.07), 0.6),
]


def upgrade_script(script_name, tex_set, tint, tint_str):
    """Patch a make_*.py script to use PBR materials and re-run it."""
    path = os.path.join(PROJ, "scripts", f"make_{script_name}.py")
    if not os.path.isfile(path):
        print(f"  SKIP {script_name}: script not found")
        return False

    with open(path, 'r') as f:
        code = f.read()

    # Already upgraded?
    if 'pbr_utils' in code:
        print(f"  SKIP {script_name}: already has pbr_utils")
        return True

    # Add imports after existing imports
    import_block = (
        f'\nimport sys as _sys\n'
        f'_sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname('
        f'__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "scripts"))\n'
        f'from pbr_utils import make_pbr_material\n'
    )

    # Find the last import line
    lines = code.split('\n')
    last_import = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            last_import = i

    # Insert PBR import after last import
    lines.insert(last_import + 1, import_block)

    # Replace material creation calls
    # Pattern: mat = bpy.data.materials.new("XXX")  -> mat = make_pbr_material(...)
    tint_s = f"({tint[0]}, {tint[1]}, {tint[2]})"
    new_code = '\n'.join(lines)

    # Find all material creation blocks and replace first one
    mat_pattern = re.compile(
        r'(\w+)\s*=\s*bpy\.data\.materials\.new\(["\'](\w+)["\']\)\s*\n'
        r'\1\.use_nodes\s*=\s*True\s*\n'
        r'(\w+)\s*=\s*\1\.node_tree\.nodes\["Principled BSDF"\]\s*\n'
        r'(?:.*?inputs\[".*?"\]\.default_value\s*=.*?\n)*',
        re.MULTILINE
    )

    def replace_mat(match):
        var_name = match.group(1)
        mat_name = match.group(2)
        return (f'{var_name} = make_pbr_material("{mat_name}", "{tex_set}", '
                f'tint={tint_s}, tint_strength={tint_str})\n')

    new_code = mat_pattern.sub(replace_mat, new_code)

    # Add JPEG export if not present
    new_code = new_code.replace(
        "export_format='GLB')",
        "export_format='GLB', export_image_format='JPEG', export_image_quality=85)"
    )
    # Fix double-add if already had it
    new_code = new_code.replace(
        "export_image_format='JPEG', export_image_quality=85, export_image_format='JPEG', export_image_quality=85)",
        "export_image_format='JPEG', export_image_quality=85)"
    )

    with open(path, 'w') as f:
        f.write(new_code)

    return True


def run_script(script_name):
    """Run a make_*.py script with Blender 4.5."""
    path = os.path.join(PROJ, "scripts", f"make_{script_name}.py")
    result = subprocess.run(
        [BLENDER, "--background", "--python", path],
        capture_output=True, text=True, timeout=60
    )
    # Look for export confirmation
    for line in result.stdout.split('\n'):
        if 'Exported' in line or 'exported' in line:
            print(f"  {line.strip()}")
            return True
    if result.returncode != 0:
        # Check stderr for errors
        for line in result.stderr.split('\n'):
            if 'Error' in line or 'Traceback' in line:
                print(f"  ERROR in {script_name}: {line.strip()}")
                return False
    print(f"  {script_name}: generated (no export message found)")
    return True


# Run as standalone (not in Blender)
if __name__ == "__main__":
    print(f"Batch PBR upgrade: {len(UPGRADES)} scripts")
    print(f"=" * 60)

    upgraded = 0
    failed = 0
    for script_name, tex_set, tint, tint_str in UPGRADES:
        print(f"\n--- {script_name} ---")
        if upgrade_script(script_name, tex_set, tint, tint_str):
            if run_script(script_name):
                upgraded += 1
            else:
                failed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Done: {upgraded} upgraded, {failed} failed")
