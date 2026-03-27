"""
Resize embedded textures in a GLB file to a target resolution.

Usage:
  blender4 --background --python scripts/resize_glb_textures.py -- input.glb [max_size]

Default max_size is 2048. Images larger than max_size are resized (preserving aspect ratio).
Output overwrites the input file.
"""
import bpy
import sys
import os

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if not argv:
    print("Usage: blender4 --background --python resize_glb_textures.py -- input.glb [max_size]")
    sys.exit(1)

glb_path = os.path.abspath(argv[0])
max_size = int(argv[1]) if len(argv) > 1 else 2048

# Clear scene
bpy.ops.wm.read_homefile(use_empty=True)

# Import GLB
bpy.ops.import_scene.gltf(filepath=glb_path)

resized = 0
for img in bpy.data.images:
    if img.size[0] == 0 or img.size[1] == 0:
        continue
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        print(f"  Resizing {img.name}: {w}x{h} -> {new_w}x{new_h}")
        img.scale(new_w, new_h)
        img.pack()
        resized += 1

print(f"Resized {resized} images (max {max_size}px)")

# Export GLB
bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format='GLB',
    export_image_format='AUTO',
    export_draco_mesh_compression_enable=False,
)
print(f"Saved: {glb_path}")
