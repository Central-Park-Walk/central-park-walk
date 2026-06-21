#!/usr/bin/env python3
"""One-time: trace a real flat-leaf reference into a normalised outline data file.

The london_plane leaf is DESIGNED FROM THE REFERENCE, not synthesised — the
parametric polar approach could never land the ~23 irregular marginal teeth the
real leaf has (user 2026-06-20). This segments the leaf from the white
background, trims the petiole, simplifies the contour, normalises it (base at
(0,0), apex toward +Y), and writes the boundary + planar UVs + the 5 main
lobe-tip UVs (for the texture's veins) to a JSON the pure-Python leaf_outline
loader reads. Re-run only if the reference or simplification changes.

Run: python3 scripts/vegetation/trace_leaf.py
"""
import json
import os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(PROJ, "reference_photos", "london planetree", "ref_leaf_flat_single.jpg")
OUT_JSON = os.path.join(HERE, "london_plane_leaf_outline.json")
OUT_VIZ = "/tmp/leaf_trace_final.png"


def dp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    L = np.hypot(*ab) or 1.0
    d = np.abs(np.cross(ab, pts - a)) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([dp(pts[:i + 1], eps)[:-1], dp(pts[i:], eps)])
    return np.array([a, b])


def main():
    im = Image.open(SRC).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    mask = a.mean(2) < a.mean(2).max() * 0.62
    mask = ndimage.binary_fill_holes(mask)
    lab, n = ndimage.label(mask)
    if n > 1:
        s = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        mask = lab == (1 + int(np.argmax(s)))

    # Trim the petiole by horizontal EXTENT (not pixel count): the stem is a
    # narrow central strip, but the two basal lobes sit low and OFF-centre, so a
    # row through them spans a wide extent even with a petiole gap between. Scan
    # up from the bottom; the first row whose extent exceeds 18% of the widest
    # row is the basal-lobe level — attach the base there, drop the petiole below.
    H = mask.shape[0]
    ext = np.zeros(H)
    for y in range(H):
        c = np.where(mask[y])[0]
        if len(c):
            ext[y] = c.max() - c.min()
    maxext = ext.max() or 1.0
    rows = np.where(mask.any(axis=1))[0]
    ybot, ytop = rows.max(), rows.min()
    ybase = ybot
    for y in range(ybot, ytop - 1, -1):
        if ext[y] > 0.26 * maxext:
            ybase = y
            break
    mask[ybase + 1:, :] = False
    base_cols = np.where(mask[ybase])[0]
    base_x = float(base_cols.mean()) if len(base_cols) else mask.shape[1] / 2

    # Ordered boundary loop (nearest-neighbour walk on the 1px boundary).
    B = mask & ~ndimage.binary_erosion(mask)
    ys, xs = np.where(B)
    pts = set(zip(xs.tolist(), ys.tolist()))
    start = min(pts, key=lambda p: (p[1], p[0]))
    cur = start
    order = [start]
    pts.discard(start)
    while pts:
        cx, cy = cur
        best, bd = None, 9
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                q = (cx + dx, cy + dy)
                if q in pts and dx * dx + dy * dy < bd:
                    bd = dx * dx + dy * dy
                    best = q
        if best is None:
            best = min(pts, key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2)
            if (best[0] - cx) ** 2 + (best[1] - cy) ** 2 > 400:
                break
        order.append(best)
        pts.discard(best)
        cur = best
    poly = np.array(order, float)

    # Light smooth (kill pixel jaggies) then simplify.
    k = 3
    sm = np.copy(poly)
    for i in range(len(poly)):
        sm[i] = poly[max(0, i - k):i + k + 1].mean(axis=0)
    simp = dp(sm, 2.5)
    if len(simp) > 2 and np.allclose(simp[0], simp[-1]):
        simp = simp[:-1]

    # Normalise: base attachment -> origin; image-y(down) -> leaf-y(up).
    base = np.array([base_x, ybase], float)
    rel = simp - base
    rel[:, 1] = -rel[:, 1]            # flip to y-up

    # ONE canonical frame + SYMMETRY (user 2026-06-20): rotate the stem->apex axis
    # to vertical, then mirror the right half onto the left so the leaf is
    # symmetric and centred about x=0 — the stem at the origin, apex straight up.
    # (A literal trace of one real lopsided leaf made "centred/symmetric" unreadable
    # and is why the veins looked off-axis.)
    apex = rel[int(np.argmax(rel[:, 1]))]
    rot = np.pi / 2 - np.arctan2(apex[1], apex[0])
    c, s = np.cos(rot), np.sin(rot)
    rel = rel @ np.array([[c, s], [-s, c]])          # apex -> +Y, base stays at origin
    right = rel[rel[:, 0] >= 0]
    right = right[np.argsort(np.arctan2(right[:, 1], right[:, 0]))]  # right-basal -> apex
    left = right[::-1].copy()
    left[:, 0] *= -1                                  # apex -> left-basal (mirror of right)
    rel = np.vstack([right, left])                    # symmetric closed loop
    rel[:, 1] -= rel[:, 1].min()                      # base edge back to y=0
    rel /= rel[:, 1].max() or 1.0                     # apex at y≈1.0
    xs2, ys2 = rel[:, 0], rel[:, 1]
    half_w = max(abs(xs2.min()), abs(xs2.max())) or 1.0
    ymin, ymax = ys2.min(), ys2.max()
    span = (ymax - ymin) or 1.0

    def to_uv(p):
        return [0.5 + p[0] / (2.0 * half_w), 1.0 - (p[1] - ymin) / span]

    bxy = [[float(x), float(y)] for x, y in rel]
    buv = [to_uv(p) for p in rel]

    # 5 main lobe tips = the most prominent CONVEX spike in each lobe sector
    # (central / right-upper / left-upper / right-basal / left-basal), measured by
    # angle from the base (0deg=+x, 90deg=up). Picking by sector (not raw distance)
    # guarantees one vein per lobe, including the lower basal lobes.
    N = len(rel)
    area = 0.5 * np.sum(rel[:, 0] * np.roll(rel[:, 1], -1) - np.roll(rel[:, 0], -1) * rel[:, 1])
    sgn = np.sign(area) or 1.0
    conv = []
    for i in range(N):
        p0, p1, p2 = rel[(i - 1) % N], rel[i], rel[(i + 1) % N]
        if np.cross(p1 - p0, p2 - p1) * sgn < 0:
            conv.append(i)
    dist = np.hypot(xs2, ys2)
    ang = np.degrees(np.arctan2(ys2, xs2))
    # The 5 main lobe tips = the 5 most prominent (farthest) convex spikes that
    # are well separated in angle, so we get central + both laterals + both
    # basals (one vein per lobe) instead of clustering near the apex.
    def adist(a, b):
        return abs(((a - b + 180) % 360) - 180)
    main_idx = []
    for i in sorted(conv, key=lambda i: -dist[i]):
        if all(adist(ang[i], ang[j]) > 24 for j in main_idx):
            main_idx.append(i)
        if len(main_idx) >= 5:
            break
    main_idx.sort(key=lambda i: -ang[i])
    tip_uv = [to_uv(rel[i]) for i in main_idx]
    base_uv = to_uv(np.array([0.0, 0.0]))

    data = {"source": os.path.basename(SRC), "n_verts": len(bxy),
            "w_over_h": round(float((xs2.max() - xs2.min()) / (ys2.max() - ys2.min())), 3),
            "boundary_xy": bxy, "boundary_uv": buv,
            "tip_uv": tip_uv, "base_uv": base_uv}
    with open(OUT_JSON, "w") as f:
        json.dump(data, f)
    print(f"wrote {OUT_JSON}: {len(bxy)} verts, W/H={data['w_over_h']}, 5 vein tips")

    # Viz on the normalised outline.
    S = 460
    vis = Image.new("RGB", (S, S), (210, 215, 220))
    d = ImageDraw.Draw(vis)
    def px(p):
        return (S * 0.5 + p[0] * S * 0.32, S * 0.92 - p[1] * S * 0.7)
    d.line([px(p) for p in rel] + [px(rel[0])], fill=(40, 90, 40), width=2)
    for i in main_idx:
        q = px(rel[i])
        d.ellipse([q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6], outline=(200, 0, 0), width=3)
        d.line([px(np.array([0.0, 0.0])), q], fill=(150, 176, 120), width=2)
    vis.save(OUT_VIZ)
    print(f"wrote {OUT_VIZ}")


if __name__ == "__main__":
    main()
