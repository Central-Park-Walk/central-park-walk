"""Lay out oak leaf-card PARTS for Chris to connect in GIMP.

Per Chris (2026-06-24): pick one flat/complete leaf I like, make it + 3 size-jittered
copies, REUSE his london-plane twig, and drop the leaves + twig into ONE transparent
PNG. He connects them in GIMP.

  leaf  : reference_photos/oak/_sources/cand3.jpg  (Quercus rubra-(EU), flat green leaf
          on white — keyed to alpha here)
  twig  : extracted from reference_photos/london planetree/london-plane-tree-leaf.jpg
          (Chris's sprig: key the green bg, then isolate the yellow-brown twig from the
          green leaves)
Out: reference_photos/oak/oak_card_parts.png   (transparent; 4 leaves + 1 twig, spaced)
"""
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
LEAF_SRC = os.path.join(PROJ, "reference_photos", "oak", "_sources", "cand3.jpg")
LP_SRC = os.path.join(PROJ, "reference_photos", "london planetree", "london-plane-tree-leaf.jpg")
OUT = os.path.join(PROJ, "reference_photos", "oak", "oak_card_parts.png")

JITTER = [1.00, 0.90, 1.07, 0.84]   # 4 leaves, a little size variation


def key_white(path):
    """Green leaf on white → RGBA by the min-channel (white bg has high min, leaf low)."""
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    mn = rgb.min(-1)                                   # white≈high, leaf≈low
    alpha = np.clip((225.0 - mn) / 55.0, 0.0, 1.0)     # opaque <170, clear >225
    a = (alpha * 255).astype(np.uint8)
    out = Image.fromarray(np.dstack([rgb.astype(np.uint8), a]), "RGBA")
    aa = out.getchannel("A").filter(ImageFilter.MedianFilter(3))
    aa = aa.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    out.putalpha(aa)
    return trim(out)


def extract_twig(path):
    """Chris's LP sprig → just the yellow-brown twig (drop green leaves + green bg)."""
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # background: uniform dark green sampled from corners
    c = 40
    corners = np.concatenate([rgb[:c, :c].reshape(-1, 3), rgb[:c, -c:].reshape(-1, 3),
                              rgb[-c:, :c].reshape(-1, 3), rgb[-c:, -c:].reshape(-1, 3)])
    bg = corners.mean(0)
    not_bg = np.sqrt(((rgb - bg) ** 2).sum(-1)) > 55
    # twig is yellow-brown: R >= G and clearly warmer than the green leaves (G>R there)
    twig = not_bg & (r >= g - 6) & (b < g + 30) & (r > 70)
    a = (twig * 255).astype(np.uint8)
    out = Image.fromarray(np.dstack([rgb.astype(np.uint8), a]), "RGBA")
    aa = out.getchannel("A").filter(ImageFilter.MedianFilter(5))
    aa = aa.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(5))  # despeckle, drop flecks
    out.putalpha(aa)
    return trim(out)


def trim(im):
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > 24)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)) if len(xs) else im


def layout(parts, gap=60, margin=50):
    h = max(p.height for p in parts) + 2 * margin
    w = sum(p.width for p in parts) + gap * (len(parts) - 1) + 2 * margin
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = margin
    for p in parts:
        canvas.alpha_composite(p, (x, (h - p.height) // 2))
        x += p.width + gap
    return canvas


def main():
    leaf = key_white(LEAF_SRC)
    leaves = []
    for i, s in enumerate(JITTER):
        lf = leaf if i % 2 == 0 else leaf.transpose(Image.FLIP_LEFT_RIGHT)  # vary 2
        lf = lf.resize((max(1, int(lf.width * s)), max(1, int(lf.height * s))), Image.LANCZOS)
        leaves.append(lf)
    twig = extract_twig(LP_SRC)
    canvas = layout(leaves + [twig])
    canvas.save(OUT)
    # grey preview for inspection
    bg = Image.new("RGBA", canvas.size, (130, 132, 135, 255))
    bg.alpha_composite(canvas)
    bg.convert("RGB").save(OUT.replace(".png", "_preview.png"))
    print(f"wrote {OUT}  {canvas.size}  ({len(leaves)} leaves + twig, transparent)")
    print(f"  leaf keyed {leaf.size}, twig {twig.size}")


if __name__ == "__main__":
    main()
