"""Build the LOBATAE oak leaf CLUSTER CARD from Chris's hand-composited leaf sprig.

Mirrors make_leaf_cluster_from_photo.py (london plane), the SETTLED real-photo
cluster-card method (tree-pipeline-lessons.md banner). Chris composites a few
RED-OAK (Lobatae) leaves on a forking twig, tips outward, on a SOLID uniform green
background (~RGB 15,80,50), and saves it to SRC below. This chroma-keys that green to
alpha, despeckles, trims, and centres it on a square canvas → the Lobatae cluster card
that pin / red / scarlet oak all share (per references/leaves/oaks/FIDELITY_CALL.md).

IMPORTANT — LEAF MORPHOLOGY (oak_red.yaml / oak_pin.yaml): the leaves must be the
bristle-POINTED, deeply/moderately lobed AMERICAN red-oak leaf — NOT the rounded-lobe
European/white-oak leaf in reference_photos/pin oak/colored-fall-autumn-oak-leaves*.
Red oak: 7-9 lobes, sinus ~halfway to midrib, each lobe bristle-tipped.

COLOR: this card carries SHAPE + luminance only. Per-species fall HUE (red oak russet
vs scarlet oak vivid scarlet vs pin oak crimson) comes from the shader's per-species
FALL_COLORS — so the _fall variant here is a neutral desaturated russet-BROWN base the
shader tints, NOT a committed red. (This is exactly why one shared card serves all three.)

Run:  python3 scripts/vegetation/make_oak_cluster_from_photo.py
Out:  textures/leaves/oak_lobatae_cluster.png        (summer)
      textures/leaves/oak_lobatae_cluster_fall.png   (neutral russet-brown base)
      + *_preview.png over neutral grey
"""
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
TEXDIR = os.path.join(PROJ, "textures", "leaves")
# Chris fills this with the hand-composited Lobatae sprig on solid green bg:
SRC = os.path.join(PROJ, "reference_photos", "oak", "red_oak_sprig.jpg")

TEX = 1024
KEY_LO = 20.0       # colour-distance from bg <= LO  → fully transparent
KEY_HI = 48.0       # colour-distance from bg >= HI  → fully opaque (leaf/twig)
MARGIN = 0.05       # transparent border around the cropped sprig


def cut_sprig(src_path):
    """Chroma-key the uniform background → RGBA sprig cropped to its alpha bbox."""
    im = Image.open(src_path).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
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
    """Summer green → NEUTRAL russet-brown base (per-species hue is shader-side).
    Slightly redder than london plane's drab yellow-brown to suit the oak group, but
    intentionally desaturated so FALL_COLORS can push it to russet/scarlet/crimson."""
    arr = np.asarray(card).astype(np.float32)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    nr = np.clip(lum * 0.92 + 60, 0, 255)   # warm/red-leaning
    ng = np.clip(lum * 0.62 + 22, 0, 255)   # muted green → orange-brown
    nb = np.clip(lum * 0.34, 0, 255)        # low blue → brown
    return Image.fromarray(np.dstack([nr, ng, nb, a]).astype(np.uint8), "RGBA")


def save_with_preview(card, out_png, label):
    card.save(out_png)
    cov = (np.asarray(card)[..., 3] > 30).mean()
    print(f"wrote {out_png}  ({card.width}x{card.height}, coverage {cov*100:.1f}%, {label})")
    bg = Image.new("RGBA", card.size, (130, 132, 135, 255))
    bg.alpha_composite(card)
    bg.convert("RGB").save(out_png.replace(".png", "_preview.png"))


if __name__ == "__main__":
    if not os.path.exists(SRC):
        raise SystemExit(
            f"Source sprig not found: {SRC}\n"
            "Provide a hand-composited Lobatae (red-oak) leaf sprig on a SOLID green "
            "background (~RGB 15,80,50), like reference_photos/london planetree/"
            "london-plane-tree-leaf.jpg. See this script's docstring for the spec.")
    sprig = center_square(cut_sprig(SRC))
    save_with_preview(sprig, os.path.join(TEXDIR, "oak_lobatae_cluster.png"), "summer")
    save_with_preview(to_fall(sprig), os.path.join(TEXDIR, "oak_lobatae_cluster_fall.png"), "fall")
