"""Build grass CARD meshes — the mid/far LOD tier for the lawn system.

Each card is 3 crossed quads (a star in plan view) textured with a baked tuft
silhouette (`textures/grass/Blade_*_card.png`, RGBA alpha cutout). At ~8 tris it
is ~30x cheaper than the near-field geometry clump (`make_blade_mesh.py`, ~260
tris), so it can blanket the 16–120 m band that today falls back to flat terrain
albedo — the "hard cutoff line" in the Bethesda meadow shots (cpw_001/002).

Pipeline: these GLBs are instanced by the SAME GPUParticles path as the geometry
tufts (`main.gd` GRASS_CARDS → `_setup_grass_particles` → `grass_particle_render.gdshader`).
The render shader reads alpha from the `grass_albedo` uniform (the card PNG), so
the mesh carries no embedded texture — only geometry + UVs (0=base → 1=tip, for
the root→tip wind bend and colour gradient) + an outward-fanned normal.

Card dimensions are matched to the near tuft heights (Blade_* in make_blade_mesh.py
× typical instance scale) so the geometry→card crossfade has no height pop. Width
is deliberately wide (one card spans a clump-sized patch) because the silhouette,
not tight packing, provides coverage at distance.

Run: blender4 --background --python scripts/make_grass_card.py
"""

import bpy
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)

# height_m / width_m per biome. Heights track the near geometry clumps
# (Blade_Lawn 0.11, Shade 0.15, Wild 0.30, Sedge 0.19) so the crossfade is
# height-seamless; width spans a clump (the alpha silhouette is many blades).
CARD_TYPES = [
    {"name": "Card_Lawn",  "height": 0.12, "width": 0.30, "quads": 3,
     "tex": "Blade_Lawn_card.png"},
    {"name": "Card_Shade", "height": 0.16, "width": 0.30, "quads": 3,
     "tex": "Blade_Shade_card.png"},
    {"name": "Card_Wild",  "height": 0.30, "width": 0.34, "quads": 3,
     "tex": "Blade_Wild_card.png"},
    {"name": "Card_Sedge", "height": 0.20, "width": 0.30, "quads": 3,
     "tex": "Blade_Sedge_card.png"},
]


def make_card(cfg):
    """3 crossed vertical quads forming a star in plan view. Recovered from the
    retired grass_cluster_builder._make_cluster_mesh — reads as a clump from any
    horizontal angle without per-frame billboarding (no rotation pop)."""
    import bmesh
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UV")

    h = cfg["height"]
    w = cfg["width"]
    n = cfg["quads"]

    for i in range(n):
        angle = float(i) / float(n) * math.pi  # 0°, 60°, 120°
        dx = math.cos(angle) * w * 0.5
        dz = math.sin(angle) * w * 0.5

        # Four corners of the quad: base spans (-dx,-dz)..(dx,dz), rises to h.
        bl = bm.verts.new((-dx, -dz, 0.0))
        br = bm.verts.new((dx, dz, 0.0))
        tr = bm.verts.new((dx, dz, h))
        tl = bm.verts.new((-dx, -dz, h))

        face = bm.faces.new([bl, br, tr, tl])
        face.smooth = True
        # UV.x across the card width, UV.y 0=base→1=tip.
        uvs = {bl: (0.0, 0.0), br: (1.0, 0.0), tr: (1.0, 1.0), tl: (0.0, 1.0)}
        for loop in face.loops:
            loop[uv_layer].uv = uvs[loop.vert]

    name = cfg["name"]
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    # Per-quad normals are left as-is; the render shader up-blends card normals
    # toward world up (see grass.md §6b root #2) so lighting is ambient-dominated.

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print(f"Building {len(CARD_TYPES)} grass card meshes...")

for cfg in CARD_TYPES:
    obj = make_card(cfg)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    filepath = os.path.join(OUT_DIR, cfg["name"] + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_normals=True,
        export_apply=True,
    )
    vc = len(obj.data.vertices)
    fc = len(obj.data.polygons)
    print(f"  {cfg['name']}: {vc} verts, {fc} faces -> {filepath}")
    bpy.ops.object.delete(use_global=False)

print("Done.")
