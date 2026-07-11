#!/usr/bin/env python3
"""Build the committed london_plane leaf-back skeleton .npz files (SYSTEM PYTHON).

Stage 1 of the two-stage leaf-back build (Chris-approved 2026-07-08, AC-8):
  Stage 1 (this script, SYSTEM python + scipy):  bucket cloud -> trunk-scaffold skeleton -> .npz
  Stage 2 (generate_trees_mtree.py, BLENDER):    load .npz -> leafback_skinner -> GLB

Kept separate because scipy (cKDTree, used by the space-colonization skeleton) HANGS inside
Blender's bundled Python (documented gotcha). The .npz are committed build inputs so the
Blender stage never needs scipy.

Deterministic: seed 20260706, growth partition (spec v4 AC-14). Re-running reproduces the
exact skeletons byte-for-byte (m = 974 nodes, matching the validated m-tier REF).

Run:  python3 scripts/build_leafback_skeletons.py
Out:  models/trees/leafback_skeletons/london_plane_{s,m,l}.npz
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leafback_skeleton as lbk

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJ, "models", "trees", "leafback_skeletons")


def save_skeleton(g, path):
    nodes = g["nodes"]
    np.savez(
        path,
        pos=np.array([nd["pos"] for nd in nodes], float),
        parent=np.array([nd["parent"] for nd in nodes], int),
        radius=np.array([nd["radius"] for nd in nodes], float),
        strand=np.array(g["strand"], int),
        trunk_ids=np.array(g["trunk_ids"], int),
        origin_ids=np.array(g["origin_ids"], int),
        fork=g["fork"], root=g["root"], CB=g["CB"], H=g["H"],
        spine_top=g["spine_top"], RX=g["RX"], leftover=g["leftover_attractors"],
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for tier in ("s", "m", "l"):
        g = lbk.build_bucket_skeleton(tier, verbose=True)
        path = os.path.join(OUT_DIR, f"london_plane_{tier}.npz")
        save_skeleton(g, path)
        reach = 100.0 * (g["n_sprigs"] - g["leftover_attractors"]) / max(g["n_sprigs"], 1)
        kb = os.path.getsize(path) / 1024
        print(f"  -> {path}  ({kb:.0f} KB)  nodes={len(g['nodes'])} reach={reach:.1f}%"
              + ("  FLAGS: " + "; ".join(g["flags"]) if g["flags"] else ""))


if __name__ == "__main__":
    main()
