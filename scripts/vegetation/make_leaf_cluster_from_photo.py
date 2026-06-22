"""Convert Chris's hand-composited London-plane leaf-sprig into the CLUSTER CARD.

Chris built the sprig himself (4 leaves on a forking twig, tips outward — the
"leaves separated by twigs" structure) and saved it over
  reference_photos/london planetree/london-plane-tree-leaf.jpg
on a SOLID uniform green background (~RGB 15,80,50). This chroma-keys that green
to alpha, despeckles, trims, and centres it on a square TEX canvas so it drops
straight into the tree pipeline as textures/leaves/london_plane_cluster.png
(+ a drabber fall variant). Plain CPython/PIL (outside Blender).

Run:  python3 scripts/vegetation/make_leaf_cluster_from_photo.py
Out:  textures/leaves/london_plane_cluster.png        (summer)
      textures/leaves/london_plane_cluster_fall.png   (fall)
      + *_preview.png over neutral grey
"""
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
TEXDIR = os.path.join(PROJ, "textures", "leaves")
SRC = os.path.join(PROJ, "reference_photos", "london planetree",
                   "london-plane-tree-leaf.jpg")

TEX = 1024
KEY_LO = 20.0       # color-distance from bg <= LO  → fully transparent
KEY_HI = 48.0       # color-distance from bg >= HI  → fully opaque (leaf/twig)
MARGIN = 0.05       # transparent border around the cropped sprig


def cut_sprig(src_path):
    """Chroma-key the uniform background → RGBA sprig cropped to its alpha bbox."""
    im = Image.open(src_path).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    # Background colour = mean of the four corner patches (the fill is uniform).
    h, w, _ = rgb.shape
    c = 40
    corners = np.concatenate([
        rgb[:c, :c].reshape(-1, 3), rgb[:c, -c:].reshape(-1, 3),
        rgb[-c:, :c].reshape(-1, 3), rgb[-c:, -c:].reshape(-1, 3)])
    bg = corners.mean(0)

    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    alpha = np.clip((dist - KEY_LO) / (KEY_HI - KEY_LO), 0.0, 1.0)
    alpha = (alpha * 255.0).astype(np.uint8)

    out = Image.fromarray(np.dstack([rgb.astype(np.uint8), alpha]), "RGBA")
    # Despeckle the key, then close pinholes inside the blades (MaxFilter grows
    # opaque, MinFilter shrinks back → fills small interior holes without bloating).
    a = out.getchannel("A").filter(ImageFilter.MedianFilter(5))
    a = a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    out.putalpha(a)

    aarr = np.asarray(out)[..., 3]
    ys, xs = np.where(aarr > 24)
    if len(xs):
        out = out.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return out


def center_square(sprig, tex=TEX):
    avail = int(tex * (1.0 - 2 * MARGIN))
    s = min(avail / sprig.width, avail / sprig.height)
    w, h = max(1, int(sprig.width * s)), max(1, int(sprig.height * s))
    sp = sprig.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (tex, tex), (0, 0, 0, 0))
    canvas.alpha_composite(sp, ((tex - w) // 2, (tex - h) // 2))
    return canvas


def to_fall(card):
    """Summer green → London-plane drab yellow-brown (keeps alpha + the twig)."""
    arr = np.asarray(card).astype(np.float32)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    nr = np.clip(lum * 0.95 + 40, 0, 255)
    ng = np.clip(lum * 0.78 + 18, 0, 255)
    nb = np.clip(lum * 0.42, 0, 255)
    return Image.fromarray(np.dstack([nr, ng, nb, a]).astype(np.uint8), "RGBA")


def save_with_preview(card, out_png, label):
    card.save(out_png)
    cov = (np.asarray(card)[..., 3] > 30).mean()
    print(f"wrote {out_png}  ({card.width}x{card.height}, coverage {cov*100:.1f}%, {label})")
    bg = Image.new("RGBA", card.size, (130, 132, 135, 255))
    bg.alpha_composite(card)
    bg.convert("RGB").save(out_png.replace(".png", "_preview.png"))


if __name__ == "__main__":
    sprig = center_square(cut_sprig(SRC))
    save_with_preview(sprig, os.path.join(TEXDIR, "london_plane_cluster.png"), "summer")
    save_with_preview(to_fall(sprig), os.path.join(TEXDIR, "london_plane_cluster_fall.png"), "fall")
