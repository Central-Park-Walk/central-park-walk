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


def _fit(im: Image.Image, size: int, thr: int = 28) -> Image.Image:
    """Contain into square; bottom-center the subject so bole bases share a line."""
    rgb = im.convert("RGB")
    box = _content_bbox(rgb, thr=thr) or (0, 0, rgb.width, rgb.height)
    cropped = rgb.crop(box)
    fitted = ImageOps.contain(cropped, (size - 24, size - 40))
    out = Image.new("RGB", (size, size), (18, 20, 24))
    x = (size - fitted.width) // 2
    y = size - 12 - fitted.height
    out.paste(fitted, (x, y))
    return out


def _bare_silhouette(front: Image.Image, size: int) -> Image.Image:
    """Thick-wood mask (drops tip filigree) for scaffold habit compare."""
    gray = ImageOps.grayscale(front.convert("RGB"))
    # Higher threshold + erode: keep bole/scaffold, lose wispy tip shell.
    mask = gray.point(lambda p: 255 if p > 55 else 0)
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    box = mask.getbbox() or (0, 0, front.width, front.height)
    rgba = Image.new("RGBA", front.size, (0, 0, 0, 0))
    rgba.putalpha(mask)
    cropped = rgba.crop(box)
    fitted = ImageOps.contain(cropped, (size - 24, size - 40))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - fitted.width) // 2
    y = size - 12 - fitted.height
    out.paste(fitted, (x, y), fitted)
    a = out.split()[-1].filter(ImageFilter.GaussianBlur(0.5))
    out.putalpha(a)
    return out


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

    ref = _fit(_crop_frac(Image.open(ref_path), meta["crop_frac"]), cell)
    bare = _fit(Image.open(bare_front), cell)
    sil = _bare_silhouette(Image.open(bare_front), cell)
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
        (over, "cyan = sculpt silhouette on ref"),
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
        "overlay": str(out_png.relative_to(PROJ)),
        "ref_plate": str((OUT_DIR / f"{stage}_ref_plate.png").relative_to(PROJ)),
    }


def main():
    results = [build_stage(s) for s in ("young", "mature", "veteran")]
    manifest = OUT_DIR / "habit_refs.json"
    manifest.write_text(json.dumps({"stages": results}, indent=2) + "\n")
    print("HABIT_REFS", manifest)
    for r in results:
        print(f"  {r['stage']}: {r['overlay']}")


if __name__ == "__main__":
    main()
