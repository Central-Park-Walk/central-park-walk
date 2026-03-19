#!/usr/bin/env python3
"""Convert heightmap.bin to EXR for Terrain3D import.

Reads our custom heightmap.bin (4-byte header + 8192x8192 float32)
and writes a 32-bit float EXR that Terrain3D can import via import_images().

Output: data/terrain3d_heightmap.exr
"""
import struct
import numpy as np
import imageio
import os

HEIGHTMAP_BIN = os.path.join(os.path.dirname(os.path.dirname(__file__)), "heightmap.bin")
OUTPUT_EXR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "terrain3d_heightmap.exr")


def main():
    # Read heightmap.bin
    with open(HEIGHTMAP_BIN, "rb") as f:
        width = struct.unpack("i", f.read(4))[0]
        depth = struct.unpack("i", f.read(4))[0]
        world_size = struct.unpack("f", f.read(4))[0]
        origin_height = struct.unpack("f", f.read(4))[0]
        data = np.frombuffer(f.read(), dtype=np.float32).reshape((depth, width))

    print(f"Heightmap: {width}x{depth}, world_size={world_size}m, origin_h={origin_height:.2f}m")
    print(f"Height range: {data.min():.2f} to {data.max():.2f} meters")
    print(f"Cell size: {world_size / (width - 1):.4f}m")

    # Terrain3D expects RGB float EXR (not greyscale).
    # Height goes in the red channel; green and blue are zero.
    rgb = np.zeros((depth, width, 3), dtype=np.float32)
    rgb[:, :, 0] = data  # R = height in meters

    os.makedirs(os.path.dirname(OUTPUT_EXR), exist_ok=True)
    imageio.imwrite(OUTPUT_EXR, rgb)
    file_size_mb = os.path.getsize(OUTPUT_EXR) / (1024 * 1024)
    print(f"Written: {OUTPUT_EXR} ({file_size_mb:.1f} MB)")
    print()
    print("Terrain3D import settings:")
    print(f"  vertex_spacing = {world_size / (width - 1):.6f}")
    print(f"  import_position = Vector3({-world_size/2}, 0, {-world_size/2})")
    print(f"  height_offset = 0.0")
    print(f"  import_scale = 1.0")


if __name__ == "__main__":
    main()
