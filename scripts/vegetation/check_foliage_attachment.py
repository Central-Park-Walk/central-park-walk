#!/usr/bin/env python3
"""Foliage-attachment sanity check for generated tree GLBs.

WHY THIS EXISTS (2026-06-19): the leaf-card placement in generate_trees_mtree.py
used to top up sparse crowns with a synthetic "crown-fill" that scattered
clusters inside the crown's bounding BOX — on open young crowns ~70% of clusters
landed in empty space, so leaves rendered as blobs floating with no visible
branch. We now anchor every supplemental cluster to a real branch vertex, but
that is an invariant worth ENFORCING, not just fixing once.

WHAT IT CHECKS: "is every leaf attached to a branch (and thus, transitively, to
the trunk)?" The leaf cards are separate geometry joined into the tree mesh, so
there is no topological edge to walk from a leaf to the trunk. Instead we use the
robust proximity proxy: the bark mesh is itself one connected skeleton from trunk
to twig, so if every leaf vertex sits within a card's reach of SOME bark vertex,
then every leaf hangs off the branch network and nothing floats. We flag any leaf
vertex whose nearest bark vertex is farther than a card could plausibly span.

USAGE:
    python3 scripts/vegetation/check_foliage_attachment.py            # all species
    python3 scripts/vegetation/check_foliage_attachment.py london_plane
Exit code is non-zero if any model floats, so it can gate a regen in a script.
"""
import sys
import glob
import os
import numpy as np
import trimesh
from scipy.spatial import cKDTree

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "trees")

# Threshold in GLB-normalised units. Models are normalised to MODEL_H (~2 units
# tall regardless of real height), and a leaf cluster card reaches ~0.25u from
# its anchor. 0.45u (~2m on a mid tree) is comfortably past any legitimate card
# while still catching a blob hanging in open air.
FLOAT_THR = 0.45
FAIL_FRAC = 0.04   # >4% of leaf verts floating = a real, visible problem


def check_glb(path):
    """Return list of (variant, float_fraction, max_dist) per variant in the GLB."""
    scene = trimesh.load(path, process=False)
    if not isinstance(scene, trimesh.Scene):
        return []
    # Pair each leaf geometry with the bark geometry of the same variant.
    bark = {n: g for n, g in scene.geometry.items() if not n.endswith("_1")}
    rows = []
    for name, g in scene.geometry.items():
        if not name.endswith("_1"):
            continue
        bark_g = bark.get(name[:-2])
        if bark_g is None:
            continue
        d, _ = cKDTree(bark_g.vertices).query(g.vertices)
        rows.append((name[:-2], float((d > FLOAT_THR).mean()), float(d.max())))
    return rows


def main():
    species = sys.argv[1] if len(sys.argv) > 1 else "*"
    pattern = os.path.join(MODELS_DIR, f"{species}_[sml].glb")
    paths = sorted(p for p in glob.glob(pattern) if "_lod" not in os.path.basename(p))
    if not paths:
        print(f"No models matched {pattern}")
        return 1

    any_fail = False
    print("FOLIAGE ATTACHMENT CHECK — leaf verts that float free of any branch")
    print(f"(threshold {FLOAT_THR}u; a model fails if >{FAIL_FRAC*100:.0f}% of its leaves float)\n")
    for path in paths:
        rows = check_glb(path)
        if not rows:
            continue
        model = os.path.basename(path)
        worst = max(r[1] for r in rows)
        bad = sum(1 for r in rows if r[1] > FAIL_FRAC)
        status = "FAIL" if bad else "ok"
        if bad:
            any_fail = True
        fracs = ", ".join(f"{r[1]*100:.1f}%" for r in rows)
        maxes = ", ".join(f"{r[2]:.2f}" for r in rows)
        print(f"  {model:26s} [{status}]  worst={worst*100:.1f}%  {bad}/{len(rows)} variants float")
        print(f"      per-variant float%: {fracs}")
        print(f"      per-variant maxd : {maxes}")
    print("\n" + ("SOME MODELS FLOAT — foliage not fully attached" if any_fail
                  else "ALL MODELS CLEAN — every leaf attaches to a branch"))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
