#!/usr/bin/env python3
"""Generate DDS textures with coverage-preserving mipmaps for tree foliage.

Standard mipmap generation averages alpha values, destroying coverage at
each level: a texture with 70% opaque pixels at mip 0 might have only 40%
at mip 3. With alpha_to_coverage or alpha_scissor, this makes trees vanish
at distance.

Coverage-preserving mipmaps (Castano 2010, "The Witness") rescale the alpha
channel at each mip level so that the same alpha threshold produces the same
fraction of passing pixels as the base level.

Also performs RGB color bleeding into transparent areas to prevent dark
fringing when mipmaps average transparent (black) pixels with opaque ones.

Usage:
    # From GLBs (auto-extract + convert):
    python3 scripts/generate_leaf_dds.py

    # From existing PNGs:
    python3 scripts/generate_leaf_dds.py --src models/trees/leaf_textures

    # Single species:
    python3 scripts/generate_leaf_dds.py --species oak
"""

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageFilter
import numpy as np


# DDS format constants
DDS_MAGIC = 0x20534444  # "DDS "
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDPF_RGBA = 0x41  # DDPF_RGB | DDPF_ALPHAPIXELS
DDSD_PITCH = 0x8
DDSCAPS_TEXTURE = 0x1000
DDSCAPS_MIPMAP = 0x400000
DDSCAPS_COMPLEX = 0x8


def extract_textures_from_glbs(glb_dir: str, out_dir: str) -> list[str]:
    """Extract leaf textures from GLB files. Returns list of species names."""
    os.makedirs(out_dir, exist_ok=True)
    species_found = []

    for glb_file in sorted(Path(glb_dir).glob("*_l.glb")):
        species = glb_file.stem.replace("_l", "")
        out_path = os.path.join(out_dir, f"{species}_leaf.png")

        try:
            with open(glb_file, "rb") as f:
                magic, version, length = struct.unpack("<III", f.read(12))
                if magic != 0x46546C67:
                    continue
                chunk_len, chunk_type = struct.unpack("<II", f.read(8))
                json_data = json.loads(f.read(chunk_len).decode("utf-8"))
                chunk_len2, chunk_type2 = struct.unpack("<II", f.read(8))
                bin_data = f.read(chunk_len2)

            for img in json_data.get("images", []):
                bv_idx = img.get("bufferView")
                if bv_idx is None:
                    continue
                bv = json_data["bufferViews"][bv_idx]
                offset = bv.get("byteOffset", 0)
                length = bv["byteLength"]
                mime = img.get("mimeType", "")
                if "png" not in mime:
                    continue
                with open(out_path, "wb") as of:
                    of.write(bin_data[offset : offset + length])
                species_found.append(species)
                break
        except Exception as e:
            print(f"  WARN: Failed to extract {glb_file}: {e}")

    print(f"Extracted {len(species_found)} textures from GLBs")
    return species_found


def bleed_colors(img: Image.Image, iterations: int = 8) -> Image.Image:
    """Dilate RGB values into transparent areas to prevent dark mipmap fringe.

    When mipmapping, transparent pixels (RGBA = 0,0,0,0) average with opaque
    green pixels, producing dark-edged leaves. Color bleeding fills the RGB
    of transparent pixels with the color of nearby opaque pixels, so the
    average stays green even where alpha drops.
    """
    arr = np.array(img).astype(np.float32)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    # Mask of opaque pixels
    mask = (alpha > 0).astype(np.float32)

    # Iteratively spread RGB into transparent areas
    for _ in range(iterations):
        # For each transparent pixel, take the average of its opaque neighbors
        # Using a 3x3 box filter on (color * mask) and (mask), then dividing
        rgb_weighted = rgb * mask[:, :, np.newaxis]

        # Pad for convolution
        rgb_pad = np.pad(rgb_weighted, ((1, 1), (1, 1), (0, 0)), mode="edge")
        mask_pad = np.pad(mask, ((1, 1), (1, 1)), mode="edge")

        # 3x3 sum
        rgb_sum = np.zeros_like(rgb)
        mask_sum = np.zeros_like(mask)
        for dy in range(3):
            for dx in range(3):
                h, w = rgb.shape[:2]
                rgb_sum += rgb_pad[dy : dy + h, dx : dx + w]
                mask_sum += mask_pad[dy : dy + h, dx : dx + w]

        # Where mask_sum > 0, compute average color; else keep previous
        valid = mask_sum > 0
        for c in range(3):
            new_rgb = np.where(valid, rgb_sum[:, :, c] / np.maximum(mask_sum, 1), rgb[:, :, c])
            # Only update transparent pixels
            rgb[:, :, c] = np.where(mask > 0, rgb[:, :, c], new_rgb)

        # Expand mask to include newly colored pixels
        mask = np.where(valid, 1.0, mask)

    arr[:, :, :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def measure_coverage(alpha: np.ndarray, threshold: float) -> float:
    """Fraction of pixels where alpha > threshold (0-1 scale)."""
    return float(np.mean(alpha > threshold))


def rescale_alpha_for_coverage(
    alpha: np.ndarray, threshold: float, target_coverage: float
) -> np.ndarray:
    """Binary search for alpha scale factor that produces target_coverage."""
    if target_coverage <= 0 or target_coverage >= 1:
        return alpha

    lo, hi = 0.1, 8.0
    for _ in range(16):
        mid = (lo + hi) / 2.0
        scaled = np.clip(alpha * mid, 0, 1)
        cov = measure_coverage(scaled, threshold)
        if cov < target_coverage:
            lo = mid
        else:
            hi = mid

    factor = (lo + hi) / 2.0
    return np.clip(alpha * factor, 0, 1)


def generate_coverage_preserving_mipmaps(
    img: Image.Image, threshold: float = 0.5
) -> list[Image.Image]:
    """Generate mipmap chain with coverage-preserving alpha."""
    arr = np.array(img).astype(np.float32) / 255.0
    base_alpha = arr[:, :, 3]
    base_coverage = measure_coverage(base_alpha, threshold)
    print(f"  Base coverage at threshold {threshold}: {base_coverage:.1%}")

    mipmaps = [img]
    w, h = img.size

    level = 0
    while w > 1 or h > 1:
        level += 1
        w = max(w // 2, 1)
        h = max(h // 2, 1)

        # Downsample from BASE image (not cascaded) for better quality
        mip = img.resize((w, h), Image.LANCZOS)

        # Rescale alpha to preserve coverage
        mip_arr = np.array(mip).astype(np.float32) / 255.0
        mip_alpha = mip_arr[:, :, 3]
        cov_before = measure_coverage(mip_alpha, threshold)

        mip_alpha_fixed = rescale_alpha_for_coverage(
            mip_alpha, threshold, base_coverage
        )
        mip_arr[:, :, 3] = mip_alpha_fixed
        mip_fixed = Image.fromarray((mip_arr * 255).astype(np.uint8), "RGBA")
        cov_after = measure_coverage(mip_alpha_fixed, threshold)

        if level <= 6:
            print(
                f"  Mip {level} ({w}x{h}): {cov_before:.1%} -> {cov_after:.1%}"
            )

        mipmaps.append(mip_fixed)

    return mipmaps


def write_dds_uncompressed(path: str, mipmaps: list[Image.Image]):
    """Write uncompressed RGBA8 DDS with pre-built mipmaps."""
    w, h = mipmaps[0].size
    mip_count = len(mipmaps)
    pitch = w * 4

    with open(path, "wb") as f:
        f.write(struct.pack("<I", DDS_MAGIC))

        # DDS_HEADER (124 bytes)
        flags = (
            DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH
            | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_PITCH
        )
        f.write(struct.pack("<I", 124))
        f.write(struct.pack("<I", flags))
        f.write(struct.pack("<I", h))
        f.write(struct.pack("<I", w))
        f.write(struct.pack("<I", pitch))
        f.write(struct.pack("<I", 0))            # depth
        f.write(struct.pack("<I", mip_count))
        f.write(b"\x00" * 44)                    # reserved

        # PIXELFORMAT (32 bytes)
        f.write(struct.pack("<I", 32))
        f.write(struct.pack("<I", DDPF_RGBA))
        f.write(struct.pack("<I", 0))            # fourCC
        f.write(struct.pack("<I", 32))           # bits
        f.write(struct.pack("<I", 0x000000FF))   # R
        f.write(struct.pack("<I", 0x0000FF00))   # G
        f.write(struct.pack("<I", 0x00FF0000))   # B
        f.write(struct.pack("<I", 0xFF000000))   # A

        # Caps
        caps = DDSCAPS_TEXTURE | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
        f.write(struct.pack("<I", caps))
        f.write(b"\x00" * 16)                    # caps2-4 + reserved2

        for mip in mipmaps:
            f.write(mip.tobytes("raw", "RGBA"))

    size_kb = os.path.getsize(path) // 1024
    print(f"  -> {path} ({size_kb} KB, {mip_count} mips)")


def process_species(
    species: str, src_dir: str, dst_dir: str, threshold: float
) -> bool:
    """Process one species: read PNG, bleed colors, generate mipmaps, write DDS."""
    png_path = os.path.join(src_dir, f"{species}_leaf.png")
    if not os.path.exists(png_path):
        print(f"  SKIP {species}: not found")
        return False

    print(f"\n  {species}")
    print(f"  {'─' * 40}")

    img = Image.open(png_path).convert("RGBA")
    print(f"  Source: {img.size[0]}x{img.size[1]}")

    # Bleed RGB into transparent areas to prevent dark mipmap fringe
    img = bleed_colors(img)

    mipmaps = generate_coverage_preserving_mipmaps(img, threshold)

    os.makedirs(dst_dir, exist_ok=True)
    dds_path = os.path.join(dst_dir, f"{species}_leaf.dds")
    write_dds_uncompressed(dds_path, mipmaps)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate DDS with coverage-preserving mipmaps"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Alpha threshold for coverage preservation (default 0.5)",
    )
    parser.add_argument("--species", type=str, default=None)
    parser.add_argument(
        "--src", type=str, default="models/trees/leaf_textures",
    )
    parser.add_argument("--dst", type=str, default="textures/leaves")
    parser.add_argument(
        "--extract", action="store_true",
        help="Auto-extract textures from GLB files first",
    )
    parser.add_argument(
        "--glb-dir", type=str, default="models/trees",
        help="GLB directory for --extract",
    )
    args = parser.parse_args()

    # Auto-extract from GLBs if requested or if no PNGs exist
    src_has_pngs = (
        os.path.isdir(args.src)
        and any(f.endswith("_leaf.png") for f in os.listdir(args.src))
    )
    if args.extract or not src_has_pngs:
        print("Extracting textures from GLBs...")
        extracted = extract_textures_from_glbs(args.glb_dir, args.src)
        if not extracted:
            print("No GLBs found. Run generate_trees_mtree.py first.")
            sys.exit(1)

    # Build species list
    if args.species:
        species_list = [args.species]
    else:
        species_list = sorted(
            f.replace("_leaf.png", "")
            for f in os.listdir(args.src)
            if f.endswith("_leaf.png")
        )

    if not species_list:
        print(f"No leaf textures in {args.src}")
        sys.exit(1)

    print(f"\nCoverage-preserving DDS generation")
    print(f"  Threshold: {args.threshold}")
    print(f"  Species:   {len(species_list)}")

    count = 0
    for species in species_list:
        if process_species(species, args.src, args.dst, args.threshold):
            count += 1

    print(f"\nDone: {count} DDS files in {args.dst}/")


if __name__ == "__main__":
    main()
