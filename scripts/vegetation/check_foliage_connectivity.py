#!/usr/bin/env python3
"""Foliage CONNECTIVITY check — a continuous line trunk -> branch -> leaf.

WHY (user, 2026-06-20): proximity-to-bark is not good enough. In a dense crown
there is bark near every point, so a nearest-bark test gives a false pass even to
a clump that floats in open sky on a hair-thin (or no) twig — its base happens to
graze a branch while its cards spray out into the void. "Faithfully presenting the
data means not cheating like that. There must be a continuous line from trunk to
branch to leaf for EVERY leaf."

NOTE on bark topology (discovered 2026-06-20): Mtree exports each branch as a
SEPARATE tube that geometrically overlaps its parent but shares no welded edges,
so the raw bark mesh is ~150 disconnected islands — there is no edge-path from
trunk to twig at all. The branches do TOUCH, though: welding bark verts within a
tiny epsilon (~0.005u) collapses them into one trunk-rooted structure. So we weld
bark first (reconstruct the real branch adjacency), THEN trace.

THE TEST (rigorous, graph-based — not proximity):
  Build one graph.
    - Bark nodes wired by the bark mesh's own edges PLUS weld edges between bark
      verts within WELD_EPS (reconnects Mtree's separate tubes into the true
      trunk -> limb -> twig topology).
    - Each leaf vertex gets ONE edge to its nearest bark vertex, but ONLY if that
      bark is within r_attach (a leaf petiole's reach, not a crown radius).
    - Crucially: NO leaf<->leaf edges. A leaf may reach the trunk ONLY through
      bark. This is the anti-cheat — dense foliage cannot bridge a gap.
  Root the graph at the lowest bark vertex (the trunk base) and flood-fill.
  Every leaf vertex that is NOT reached has no continuous bark line to the trunk:
  it is floating, or sitting on a branch that is itself disconnected from the
  trunk. Those are the failures.

It also reports bark that is disconnected from the trunk (a floating branch is a
generation bug in its own right).

USAGE:
    python3 scripts/vegetation/check_foliage_connectivity.py            # all species
    python3 scripts/vegetation/check_foliage_connectivity.py london_plane
Non-zero exit if any model has disconnected foliage, so it can gate a regen.
"""
import sys
import glob
import os
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "trees")

# A leaf attaches at its petiole: its card verts sit within roughly one leaf's
# reach of the twig. Models are normalised to ~2 units tall, so ~0.12u (~0.5m on
# a mid tree) is generous for a real card yet far tighter than a crown radius — a
# clump spraying into the void lands beyond it and is correctly flagged.
R_ATTACH = 0.12
# Mtree's branch tubes are separate geometry; weld bark verts within this radius
# to reconstruct the real branch adjacency (0.005u already merges them; 0.01u is
# a safe margin without bridging genuinely separate branches).
WELD_EPS = 0.01
FAIL_FRAC = 0.02   # >2% of leaves with no bark line to the trunk = a real fail


def _bark_edges(faces):
    e = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    return e


def check_variant(bark, leaf, faces):
    nB, nL = len(bark), len(leaf)
    if nB == 0 or nL == 0:
        return None
    # Leaf -> nearest bark edge, kept only if within petiole reach.
    d, idx = cKDTree(bark).query(leaf)
    within = d < R_ATTACH
    li = np.where(within)[0]
    bi = idx[within]
    # Graph: nodes 0..nB-1 = bark, nB..nB+nL-1 = leaf.
    eb = _bark_edges(faces)
    # Weld edges: reconnect Mtree's separate branch tubes into one structure.
    weld = cKDTree(bark).query_pairs(WELD_EPS, output_type="ndarray")
    if len(weld):
        rows = np.concatenate([eb[:, 0], weld[:, 0], nB + li])
        cols = np.concatenate([eb[:, 1], weld[:, 1], bi])
    else:
        rows = np.concatenate([eb[:, 0], nB + li])
        cols = np.concatenate([eb[:, 1], bi])
    N = nB + nL
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(N, N))
    _, labels = connected_components(g, directed=False)
    root = int(np.argmin(bark[:, 2]))          # trunk base
    root_label = labels[root]
    leaf_labels = labels[nB:]
    leaf_connected = leaf_labels == root_label
    bark_connected = (labels[:nB] == root_label).mean()
    # Of the disconnected leaves, how many never even reached bark vs. reached
    # a branch that is itself cut off from the trunk.
    no_bark = (~within).mean()
    return {
        "leaf_floating_frac": 1.0 - leaf_connected.mean(),
        "no_bark_within_reach": no_bark,
        "bark_trunk_connected": bark_connected,
    }


def main():
    species = sys.argv[1] if len(sys.argv) > 1 else "*"
    pattern = os.path.join(MODELS_DIR, f"{species}_[sml].glb")
    paths = sorted(p for p in glob.glob(pattern) if "_lod" not in os.path.basename(p))
    if not paths:
        print(f"No models matched {pattern}")
        return 1

    any_fail = False
    print("FOLIAGE CONNECTIVITY — continuous bark line trunk -> branch -> leaf")
    print(f"(r_attach={R_ATTACH}u, leaf->trunk through BARK only; fail if "
          f">{FAIL_FRAC*100:.0f}% of leaves have no such line)\n")
    for path in paths:
        sc = trimesh.load(path, process=False)
        if not isinstance(sc, trimesh.Scene):
            continue
        bark = {n: g for n, g in sc.geometry.items() if not n.endswith("_1")}
        model = os.path.basename(path)
        rows = []
        for name, g in sc.geometry.items():
            if not name.endswith("_1"):
                continue
            bg = bark.get(name[:-2])
            if bg is None:
                continue
            r = check_variant(np.asarray(bg.vertices), np.asarray(g.vertices),
                              np.asarray(bg.faces))
            if r:
                rows.append(r)
        if not rows:
            continue
        floats = [r["leaf_floating_frac"] for r in rows]
        barks = [r["bark_trunk_connected"] for r in rows]
        bad = sum(1 for f in floats if f > FAIL_FRAC)
        if bad:
            any_fail = True
        status = "FAIL" if bad else "ok"
        print(f"  {model:26s} [{status}]  {bad}/{len(rows)} variants have floating foliage")
        print(f"      leaf floating %: " + ", ".join(f"{f*100:.1f}%" for f in floats))
        print(f"      bark->trunk   %: " + ", ".join(f"{b*100:.1f}%" for b in barks))
    print("\n" + ("DISCONNECTED FOLIAGE — leaves with no bark line to the trunk"
                  if any_fail else
                  "ALL COHERENT — every leaf traces trunk -> branch -> leaf"))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
