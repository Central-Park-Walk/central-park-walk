"""Extract a CLEAN London plane leaf silhouette from the real-leaf cutout alpha,
using marching squares (robust on concave lobes/sinuses) — replaces the buggy
nearest-neighbour boundary walk in trace_leaf.py that spiked.

Output: scripts/vegetation/london_plane_outline_v2.json  (ordered boundary in a
canonical frame: petiole base at origin (0,0), apex +Y, real proportions kept)
and /tmp/leaf_outline_v2.png viz for eyeball verification BEFORE any mesh.

Run: python3 scripts/vegetation/extract_leaf_outline.py
"""
import json, os
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(PROJ, "textures/leaves/london_plane_real_albedo.png")
OUT_JSON = os.path.join(HERE, "london_plane_outline_v2.json")
VIZ = "/tmp/leaf_outline_v2.png"


def resample_closed(contour, n=220):
    """Evenly resample a CLOSED contour by arc length to n points (preserves the
    coarse teeth; avoids Douglas-Peucker's collapse on equal-endpoint loops)."""
    c = np.asarray(contour, float)
    if np.allclose(c[0], c[-1]):
        c = c[:-1]
    loop = np.vstack([c, c[0]])
    seg = np.r_[0.0, np.cumsum(np.hypot(np.diff(loop[:, 0]), np.diff(loop[:, 1])))]
    total = seg[-1] or 1.0
    targets = np.linspace(0.0, total, n, endpoint=False)
    out = np.empty((n, 2))
    for k, t in enumerate(targets):
        j = np.searchsorted(seg, t) - 1
        j = min(max(j, 0), len(c) - 1)
        f = (t - seg[j]) / ((seg[j + 1] - seg[j]) or 1.0)
        out[k] = loop[j] * (1 - f) + loop[j + 1] * f
    return out


def main():
    im = Image.open(SRC)
    alpha = np.asarray(im)[..., 3].astype(float) / 255.0
    # marching squares contour at 0.5
    cs = plt.contour(alpha, levels=[0.5])
    segs = [s for s in cs.allsegs[0]]
    contour = max(segs, key=len)              # (N,2) in (x=col, y=row)
    # resample in IMAGE space (keep for mesh+UV: texture maps exactly onto geometry)
    img_contour = resample_closed(contour, 220)
    H_img, W_img = alpha.shape
    # image coords -> leaf frame: x right, y UP  (for the orientation viz only)
    pts = np.column_stack([img_contour[:, 0], -img_contour[:, 1]]).astype(float)

    # Orient: apex = farthest contour point from centroid (central lobe is longest).
    c = pts.mean(0)
    q = pts - c
    d = np.hypot(q[:, 0], q[:, 1])
    apex_dir = q[int(np.argmax(d))]
    ang = np.pi / 2 - np.arctan2(apex_dir[1], apex_dir[0])   # apex -> +Y
    ca, sa = np.cos(ang), np.sin(ang)
    R = np.array([[ca, -sa], [sa, ca]])
    pr = q @ R.T
    # petiole base = lowest contour point near the central axis (|x| small)
    halfw = max(abs(pr[:, 0].min()), abs(pr[:, 0].max())) or 1.0
    central = np.where(np.abs(pr[:, 0]) < 0.18 * halfw)[0]
    base_i = central[np.argmin(pr[central, 1])] if len(central) else int(np.argmin(pr[:, 1]))
    pr = pr - pr[base_i]                       # petiole base -> origin
    scale = pr[:, 1].max() or 1.0
    pr /= scale                                # apex ~ y=1
    W = pr[:, 0].max() - pr[:, 0].min()
    H = pr[:, 1].max() - pr[:, 1].min()

    data = {"source": os.path.basename(SRC), "n_verts": len(pr),
            "w_over_h": round(float(W / H), 3),
            "image_size": [int(W_img), int(H_img)],
            "boundary_img": [[float(x), float(y)] for x, y in img_contour],  # (col,row) px
            "boundary_xy": [[float(x), float(y)] for x, y in pr]}
    with open(OUT_JSON, "w") as f:
        json.dump(data, f)
    print(f"wrote {OUT_JSON}: {len(pr)} verts, W/H={data['w_over_h']}")

    # viz
    fig, ax = plt.subplots(figsize=(5, 5))
    poly = np.vstack([pr, pr[0]])
    ax.fill(poly[:, 0], poly[:, 1], color=(0.30, 0.46, 0.18), alpha=0.5)
    ax.plot(poly[:, 0], poly[:, 1], color=(0.10, 0.25, 0.06), lw=1.5)
    ax.plot(0, 0, "ro")                       # petiole base
    ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
    ax.set_title(f"W/H={data['w_over_h']}  n={len(pr)}")
    fig.savefig(VIZ, dpi=90); print(f"wrote {VIZ}")


main()
