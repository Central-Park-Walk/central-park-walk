#!/usr/bin/env python3
"""Build side-by-side + silhouette overlays: bare front vs locked habit ref.

Authority for TS-1 habit PASS under the photo-match method (W-39):
automated silhouette raycast primaries (``shape_fit.py``) on one locked
photograph per stage. Needs Pillow + locked refs + bare fronts on disk.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from habit_refs import STAGE_REFS

PROJ = Path(__file__).resolve().parents[2]
REF_DIR = PROJ / "reference_photos" / "london planetree"
OUT_DIR = PROJ / "tmp" / "tree_sculpt" / "habit_refs"
BARE_DIR = PROJ / "tmp" / "tree_sculpt"


def _crop_frac(im: Image.Image, frac):
    w, h = im.size
    l, t, r, b = frac
    return im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))


def _content_bbox(im: Image.Image, thr: int = 32):
    gray = ImageOps.grayscale(im.convert("RGB"))
    mask = gray.point(lambda p: 255 if p > thr else 0)
    return mask.getbbox()


def _fit_box(im: Image.Image, size: int, thr: int = 28):
    """Contain into square; bottom-center the subject so bole bases share a line.

    Returns (plate, paste_box) — paste_box is the photo strip in plate coords.
    """
    rgb = im.convert("RGB")
    box = _content_bbox(rgb, thr=thr) or (0, 0, rgb.width, rgb.height)
    cropped = rgb.crop(box)
    fitted = ImageOps.contain(cropped, (size - 24, size - 40))
    out = Image.new("RGB", (size, size), (18, 20, 24))
    x = (size - fitted.width) // 2
    y = size - 12 - fitted.height
    out.paste(fitted, (x, y))
    return out, (x, y, x + fitted.width, y + fitted.height)


def _fit(im: Image.Image, size: int, thr: int = 28) -> Image.Image:
    return _fit_box(im, size, thr)[0]


def _thick_wood_mask(front: Image.Image) -> Image.Image:
    """Thick-wood mask (drops tip filigree) at the render's native resolution.

    The erosion severs 1px streamer connections, leaving speckle fragments that
    are artifacts, not geometry — drop components too small to be a limb chunk
    (large detached chunks stay: they are real spread and must remain visible).
    """
    import numpy as np
    from scipy import ndimage

    gray = ImageOps.grayscale(front.convert("RGB"))
    mask = gray.point(lambda p: 255 if p > 55 else 0)
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    arr = np.asarray(mask) > 127
    labeled, nlab = ndimage.label(arr)
    if nlab:
        sizes = ndimage.sum_labels(arr, labeled, range(1, nlab + 1))
        min_px = max(16, int(0.00015 * arr.size))  # ~40px on a 512 frame
        keep = np.zeros(nlab + 1, dtype=bool)
        keep[1:] = sizes >= min_px
        arr = keep[labeled]
    return Image.fromarray((arr * 255).astype(np.uint8), mode="L")


def _registered_silhouette(front: Image.Image, size: int, ref_env: dict) -> tuple[Image.Image, dict]:
    """Sculpt silhouette registered onto the photo's measured tree envelope.

    Similarity transform only — uniform scale (photo crown height / sculpt crown
    height) + translation (sculpt bole → photo bole). Width and shape stay free:
    a habit mismatch must remain readable as cyan spill / uncovered crown, so the
    registration may normalize height and ground point and NOTHING else.
    """
    import numpy as np

    # shape_fit imports _crop_frac/_fit from this module; import inside the
    # function so the two modules can share measurement code without a cycle.
    from shape_fit import measure_envelope

    mask = _thick_wood_mask(front)
    sculpt_env = measure_envelope(np.asarray(mask) > 127)

    scale = ref_env["crown_h_px"] / max(1, sculpt_env["crown_h_px"])
    sw = max(1, int(round(mask.width * scale)))
    sh = max(1, int(round(mask.height * scale)))
    scaled = mask.resize((sw, sh), Image.BILINEAR)
    # Re-binarize at the comparison scale (>=25% pixel coverage keeps a thin
    # stroke a stroke), then close so tips read as lines, not speckle.
    scaled = scaled.point(lambda p: 255 if p >= 64 else 0)
    scaled = scaled.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))

    ref_bx, ref_by = ref_env["bole_xy"]
    off_x = int(round(ref_bx - sculpt_env["bole_xy"][0] * scale))
    off_y = int(round(ref_by - sculpt_env["bole_xy"][1] * scale))

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rgba = Image.new("RGBA", scaled.size, (255, 255, 255, 0))
    rgba.putalpha(scaled)
    out.paste(rgba, (off_x, off_y), rgba)

    final_env = measure_envelope(np.asarray(out.split()[-1]) > 0)
    clipped = (
        final_env["bbox"][0] <= 0
        or final_env["bbox"][2] >= size - 1
        or final_env["bbox"][1] <= 0
    )
    reg = {
        "scale": round(scale, 4),
        "ref_bole_xy": [int(ref_bx), int(ref_by)],
        "ref_crown_h_px": int(ref_env["crown_h_px"]),
        "ref_crown_w_px": int(ref_env["crown_w_px"]),
        "sil_bole_xy": [int(final_env["bole_xy"][0]), int(final_env["bole_xy"][1])],
        "sil_crown_h_px": int(final_env["crown_h_px"]),
        "sil_crown_w_px": int(final_env["crown_w_px"]),
        "sil_bbox": [int(v) for v in final_env["bbox"]],
        # MEASUREMENT, not registration: >1 = sculpt crown wider than photo's
        # at matched height. A lower bound when clipped at the cell edge.
        "spread_ratio": round(final_env["crown_w_px"] / max(1, ref_env["crown_w_px"]), 3),
        "clipped_at_cell_edge": bool(clipped),
    }
    return out, reg


def _check_registration(reg: dict, size: int) -> None:
    """Tripwire on the registration invariants ONLY (height + bole pin).

    Horizontal spill is deliberately NOT checked — with bole and height pinned,
    width mismatch is the habit measurement the overlay exists to show.
    """
    h_err = abs(reg["sil_crown_h_px"] - reg["ref_crown_h_px"]) / reg["ref_crown_h_px"]
    bx_err = abs(reg["sil_bole_xy"][0] - reg["ref_bole_xy"][0]) / size
    by_err = abs(reg["sil_bole_xy"][1] - reg["ref_bole_xy"][1]) / size
    faults = []
    if h_err > 0.04:
        faults.append(f"crown height off {h_err:.1%} (>4%)")
    if bx_err > 0.02 or by_err > 0.02:
        faults.append(f"bole offset ({bx_err:.1%},{by_err:.1%}) (>2%)")
    if faults:
        raise RuntimeError("overlay registration failed: " + "; ".join(faults))


def _overlay(ref_rgb: Image.Image, sil_rgba: Image.Image) -> Image.Image:
    """Cyan silhouette over dimmed reference — mismatch reads as cyan outside wood."""
    base = ImageEnhance.Brightness(ref_rgb.convert("RGB")).enhance(0.55)
    base = ImageEnhance.Contrast(base).enhance(1.15)
    cyan = Image.new("RGBA", base.size, (40, 220, 255, 0))
    alpha = sil_rgba.split()[-1].point(lambda p: int(p * 0.55))
    cyan.putalpha(alpha)
    return Image.alpha_composite(base.convert("RGBA"), cyan).convert("RGB")


def build_stage(stage: str, cell: int = 640) -> dict:
    meta = STAGE_REFS[stage]
    ref_path = REF_DIR / meta["file"]
    bare_front = BARE_DIR / f"review_{stage}_bare" / "front.png"
    if not ref_path.is_file():
        raise FileNotFoundError(ref_path)
    if not bare_front.is_file():
        raise FileNotFoundError(bare_front)

    import numpy as np

    from shape_fit import measure_envelope, segment_tree  # lazy: avoids cycle

    ref, strip = _fit_box(_crop_frac(Image.open(ref_path), meta["crop_frac"]), cell)
    ref_env = measure_envelope(segment_tree(np.asarray(ref)))
    bare = _fit(Image.open(bare_front), cell)
    sil, reg = _registered_silhouette(Image.open(bare_front), cell, ref_env)
    _check_registration(reg, cell)
    over = _overlay(ref, sil)

    gap = 16
    title_h = 44
    label_h = 28
    canvas = Image.new("RGB", (cell * 3 + gap * 4, title_h + cell + label_h + gap * 2), (14, 16, 18))
    draw = ImageDraw.Draw(canvas)
    draw.text((gap, 14), f"habit photo-match · {stage} · bare front vs locked ref", fill=(235, 235, 235))
    panels = [
        (ref, "locked reference"),
        (bare, "sculpt bare front"),
        (over, "cyan = sculpt silhouette registered to ref (bole + height)"),
    ]
    x = gap
    y = title_h
    for im, label in panels:
        canvas.paste(im, (x, y))
        draw.text((x + 6, y + cell + 6), label, fill=(200, 200, 200))
        x += cell + gap

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUT_DIR / f"{stage}_habit_overlay.png"
    canvas.save(out_png)
    # Also save the cropped ref alone for Blender background plates.
    ref.save(OUT_DIR / f"{stage}_ref_plate.png")
    bare.save(OUT_DIR / f"{stage}_bare_front.png")
    return {
        "stage": stage,
        "ref_file": meta["file"],
        "why": meta["why"],
        "crop_frac": list(meta["crop_frac"]),
        "registration": reg,
        "photo_strip": list(strip),
        "overlay": str(out_png.relative_to(PROJ)),
        "ref_plate": str((OUT_DIR / f"{stage}_ref_plate.png").relative_to(PROJ)),
    }


def main():
    results = [build_stage(s) for s in ("young", "mature", "veteran")]
    manifest = OUT_DIR / "habit_refs.json"
    manifest.write_text(json.dumps({"stages": results}, indent=2) + "\n")
    print("HABIT_REFS", manifest)
    for r in results:
        reg = r["registration"]
        print(
            f"  {r['stage']}: {r['overlay']} REG scale={reg['scale']} "
            f"crown_h ref/sil={reg['ref_crown_h_px']}/{reg['sil_crown_h_px']} "
            f"bole ref/sil={reg['ref_bole_xy']}/{reg['sil_bole_xy']} "
            f"spread_ratio={reg['spread_ratio']}"
            + (" CLIPPED" if reg["clipped_at_cell_edge"] else "")
        )


if __name__ == "__main__":
    main()
