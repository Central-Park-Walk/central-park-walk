#!/usr/bin/env python3
"""Generate DDS textures with coverage-preserving mipmaps for tree foliage.

Standard mipmap generation averages alpha values, destroying coverage at
each level: a texture with 70% opaque pixels at mip 0 might have only 40%
at mip 3. With alpha_to_coverage or alpha_scissor, this makes trees vanish
at distance.

Coverage-preserving mipmaps (Castano 2010, "The Witness") rescale the alpha
channel at each mip level so that the same alpha threshold produces the same
fraction of passing pixels as the base level.

Usage:
    python3 scripts/generate_leaf_dds.py [--threshold 0.5] [--species oak]

Reads PNG from models/trees/leaf_textures/{species}_leaf.png
Writes DDS to textures/leaves/{species}_leaf.dds
"""

import argparse
import os
import struct
import sys
from pathlib import Path

from PIL import Image
import numpy as np


# DDS format constants
DDS_MAGIC = 0x20534444  # "DDS "
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDSD_LINEARSIZE = 0x80000
DDPF_FOURCC = 0x4
DDSCAPS_TEXTURE = 0x1000
DDSCAPS_MIPMAP = 0x400000
DDSCAPS_COMPLEX = 0x8
DDS_FOURCC_DXT5 = 0x35545844  # "DXT5" = BC3

# Uncompressed RGBA
DDPF_RGBA = 0x41  # DDPF_RGB | DDPF_ALPHAPIXELS
DDSD_PITCH = 0x8


def measure_coverage(alpha: np.ndarray, threshold: float) -> float:
    """Fraction of pixels where alpha > threshold (0-1 scale)."""
    return np.mean(alpha > threshold)


def rescale_alpha_for_coverage(alpha: np.ndarray, threshold: float,
                                target_coverage: float) -> np.ndarray:
    """Binary search for alpha scale factor that produces target_coverage."""
    if target_coverage <= 0 or target_coverage >= 1:
        return alpha

    lo, hi = 0.1, 8.0
    for _ in range(16):  # 16 iterations = precision ~0.00005
        mid = (lo + hi) / 2.0
        scaled = np.clip(alpha * mid, 0, 1)
        cov = measure_coverage(scaled, threshold)
        if cov < target_coverage:
            lo = mid
        else:
            hi = mid

    factor = (lo + hi) / 2.0
    return np.clip(alpha * factor, 0, 1)


def generate_coverage_preserving_mipmaps(img: Image.Image,
                                          threshold: float = 0.5
                                          ) -> list[Image.Image]:
    """Generate mipmap chain with coverage-preserving alpha.

    At each mip level, alpha values are rescaled so that the fraction of
    pixels passing `alpha > threshold` matches the base level's fraction.
    """
    arr = np.array(img).astype(np.float32) / 255.0
    base_alpha = arr[:, :, 3]
    base_coverage = measure_coverage(base_alpha, threshold)
    print(f"  Base coverage at threshold {threshold}: {base_coverage:.1%}")

    mipmaps = [img]
    current = img
    w, h = img.size

    level = 0
    while w > 1 or h > 1:
        level += 1
        w = max(w // 2, 1)
        h = max(h // 2, 1)

        # Downsample with high-quality filter
        mip = current.resize((w, h), Image.LANCZOS)

        # Rescale alpha to preserve coverage
        mip_arr = np.array(mip).astype(np.float32) / 255.0
        mip_alpha = mip_arr[:, :, 3]
        mip_cov_before = measure_coverage(mip_alpha, threshold)

        mip_alpha_fixed = rescale_alpha_for_coverage(
            mip_alpha, threshold, base_coverage)

        mip_arr[:, :, 3] = mip_alpha_fixed
        mip_fixed = Image.fromarray((mip_arr * 255).astype(np.uint8), 'RGBA')
        mip_cov_after = measure_coverage(mip_alpha_fixed, threshold)

        if level <= 6:
            print(f"  Mip {level} ({w}x{h}): coverage {mip_cov_before:.1%}"
                  f" -> {mip_cov_after:.1%}")

        mipmaps.append(mip_fixed)
        current = mip_fixed

    return mipmaps


def write_dds_uncompressed(path: str, mipmaps: list[Image.Image]):
    """Write uncompressed RGBA8 DDS with pre-built mipmaps."""
    base = mipmaps[0]
    w, h = base.size
    mip_count = len(mipmaps)

    # Calculate pitch for base level
    pitch = w * 4  # 4 bytes per pixel (RGBA8)

    with open(path, 'wb') as f:
        # Magic
        f.write(struct.pack('<I', DDS_MAGIC))

        # DDS_HEADER (124 bytes)
        flags = (DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH |
                 DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_PITCH)
        f.write(struct.pack('<I', 124))          # dwSize
        f.write(struct.pack('<I', flags))         # dwFlags
        f.write(struct.pack('<I', h))             # dwHeight
        f.write(struct.pack('<I', w))             # dwWidth
        f.write(struct.pack('<I', pitch))         # dwPitchOrLinearSize
        f.write(struct.pack('<I', 0))             # dwDepth
        f.write(struct.pack('<I', mip_count))     # dwMipMapCount
        f.write(b'\x00' * 44)                     # dwReserved1[11]

        # DDS_PIXELFORMAT (32 bytes)
        f.write(struct.pack('<I', 32))            # dwSize
        f.write(struct.pack('<I', DDPF_RGBA))     # dwFlags (RGB + Alpha)
        f.write(struct.pack('<I', 0))             # dwFourCC (not used)
        f.write(struct.pack('<I', 32))            # dwRGBBitCount
        f.write(struct.pack('<I', 0x000000FF))    # dwRBitMask
        f.write(struct.pack('<I', 0x0000FF00))    # dwGBitMask
        f.write(struct.pack('<I', 0x00FF0000))    # dwBBitMask
        f.write(struct.pack('<I', 0xFF000000))    # dwABitMask

        # Caps
        caps = DDSCAPS_TEXTURE | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
        f.write(struct.pack('<I', caps))          # dwCaps
        f.write(struct.pack('<I', 0))             # dwCaps2
        f.write(struct.pack('<I', 0))             # dwCaps3
        f.write(struct.pack('<I', 0))             # dwCaps4
        f.write(struct.pack('<I', 0))             # dwReserved2

        # Write mip level data
        for mip in mipmaps:
            data = mip.tobytes('raw', 'RGBA')
            f.write(data)

    total_size = os.path.getsize(path)
    print(f"  Written: {path} ({total_size // 1024} KB, {mip_count} mips)")


def process_species(species: str, src_dir: str, dst_dir: str,
                    threshold: float):
    """Process one species: read PNG, generate mipmaps, write DDS."""
    png_path = os.path.join(src_dir, f"{species}_leaf.png")
    if not os.path.exists(png_path):
        print(f"  SKIP {species}: {png_path} not found")
        return False

    print(f"\n{'='*50}")
    print(f"  {species}")
    print(f"{'='*50}")

    img = Image.open(png_path).convert('RGBA')
    print(f"  Source: {img.size[0]}x{img.size[1]}")

    mipmaps = generate_coverage_preserving_mipmaps(img, threshold)

    os.makedirs(dst_dir, exist_ok=True)
    dds_path = os.path.join(dst_dir, f"{species}_leaf.dds")
    write_dds_uncompressed(dds_path, mipmaps)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate DDS with coverage-preserving mipmaps")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Alpha threshold for coverage preservation")
    parser.add_argument("--species", type=str, default=None,
                        help="Process only this species (default: all)")
    parser.add_argument("--src", type=str,
                        default="models/trees/leaf_textures",
                        help="Source PNG directory")
    parser.add_argument("--dst", type=str,
                        default="textures/leaves",
                        help="Output DDS directory")
    args = parser.parse_args()

    if args.species:
        species_list = [args.species]
    else:
        # Find all *_leaf.png files
        species_list = []
        if os.path.isdir(args.src):
            for f in sorted(os.listdir(args.src)):
                if f.endswith("_leaf.png"):
                    species_list.append(f.replace("_leaf.png", ""))

    if not species_list:
        print(f"No leaf textures found in {args.src}")
        print("Run generate_trees_mtree.py first to export PNGs.")
        sys.exit(1)

    print(f"Coverage-preserving DDS generation")
    print(f"  Threshold: {args.threshold}")
    print(f"  Species: {len(species_list)}")

    count = 0
    for species in species_list:
        if process_species(species, args.src, args.dst, args.threshold):
            count += 1

    print(f"\nDone: {count} DDS files generated in {args.dst}/")


if __name__ == "__main__":
    main()
